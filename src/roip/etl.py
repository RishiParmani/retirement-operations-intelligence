"""ETL: raw CSV -> validated, enriched, analysis-ready CSV (+ rejected records + data-quality reports).

Design choices (see docs/DATA_QUALITY.md):
* Nothing is dropped silently: every removed row is written to the rejected file with a reason.
* The clean file keeps the same 33-column layout the Power BI model expects.
* Business logic that was already in the project is preserved (SLA breach = Completed AND
  processing_hours > sla_target_hours; data_quality_score penalties).
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from . import config as C
from . import dq
from .utils import get_logger

DATE_COLS = ["received_at", "assigned_at", "started_at", "completed_at"]


def run_etl(raw_path=None, processed_path=None, rejected_path=None, report_dir=None, logger=None) -> dict:
    raw_path = Path(raw_path or C.RAW_PATH)
    processed_path = Path(processed_path or C.PROCESSED_PATH)
    rejected_path = Path(rejected_path or C.REJECTED_PATH)
    report_dir = Path(report_dir or C.DQ_DIR)
    log = logger or get_logger()

    # ---- 1. load -------------------------------------------------------------------------------
    raw = pd.read_csv(raw_path, parse_dates=DATE_COLS)
    n_raw = len(raw)
    log.info("Loaded %s rows from %s", f"{n_raw:,}", raw_path)

    # ---- 2. reject rules (R01-R08) -------------------------------------------------------------
    df, rejected, reject_results = dq.apply_reject_rules(raw.copy(), log)

    # ---- 3. fixes -------------------------------------------------------------------------------
    fix_results = []
    n_region = int(df["region"].isna().sum())
    df["region"] = df["region"].fillna("Unknown")
    fix_results.append(dq.fix_result("X01", "Missing region set to 'Unknown'", n_region, n_raw,
        "region is missing for ~0.8% of records. The record is valid in every other respect, so it is kept and "
        "labelled 'Unknown' (excluded from region conclusions, included in all totals).",
        "Value imputed with the label 'Unknown'"))
    df["exception_flag"] = df["exception_flag"].astype(bool)
    df["rework_flag"] = df["rework_flag"].astype(bool)
    df["received_at"] = pd.to_datetime(df["received_at"], errors="coerce")
    df["received_year"] = df["received_at"].dt.year
    df["received_month"] = df["received_at"].dt.month
    df["received_week"] = df["received_at"].dt.isocalendar().week.astype(int)
    df["received_day_of_week"] = df["received_at"].dt.day_name()
    # SLA definition (project standard): breached only when Completed and slower than the target.
    breached = ((df["processing_hours"] > df["sla_target_hours"]) & (df["status"] == "Completed")).astype(int)
    n_changed = int((breached != df["sla_breached"]).sum())
    df["sla_breached"] = breached
    fix_results.append(dq.fix_result("X02", "sla_breached re-derived", n_changed, n_raw,
        "The generator marks Pending/Failed/Escalated items as breached when their (never realised) duration exceeds "
        "the target. SLA is only measurable on completed work, so breach = Completed AND processing_hours > target.",
        "Value recomputed"))
    df["data_quality_score"] = 100
    df.loc[df["region"] == "Unknown", "data_quality_score"] -= 10
    df.loc[df["exception_flag"], "data_quality_score"] -= 5

    # ---- 4. flag rules (F01-F09) ----------------------------------------------------------------
    flag_results, issue_log = dq.apply_flag_rules(df, n_raw, log)

    # ---- 5. write outputs -----------------------------------------------------------------------
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_path, index=False)
    (rejected if len(rejected) else pd.DataFrame()).to_csv(rejected_path, index=False)

    lean_cols = [c for c in ["operation_id", "rejection_rule", "rejection_reason", "operation_type", "received_at", "status"] if c in rejected.columns]
    (rejected[lean_cols] if len(rejected) else pd.DataFrame(columns=lean_cols)).to_csv(report_dir / "dq_rejected_records.csv", index=False)
    results = pd.DataFrame(reject_results + fix_results + flag_results)
    kpis = dq.dq_kpis(raw, df, reject_results, flag_results, fix_results)
    kpis["rejected_by_reason"] = (rejected["rejection_reason"].value_counts().to_dict() if len(rejected) else {})
    results.to_csv(report_dir / "dq_rule_results.csv", index=False)
    issue_log.to_csv(report_dir / "dq_issue_log.csv", index=False)
    pd.concat([dq.summary_stats(raw, "before"), dq.summary_stats(df, "after")]).to_csv(report_dir / "dq_before_after.csv", index=False)
    (report_dir / "dq_summary.json").write_text(json.dumps(kpis, indent=2))
    # long format table consumed by Power BI (disconnected 'dq_run_summary' table)
    run_rows = [{"metric": k, "value": v} for k, v in kpis.items() if not isinstance(v, dict)]
    pd.DataFrame(run_rows).to_csv(report_dir / "dq_run_summary.csv", index=False)

    assert n_raw == len(df) + len(rejected), "row accounting failed: raw != clean + rejected"
    log.info("ETL complete: %s raw -> %s clean + %s rejected", f"{n_raw:,}", f"{len(df):,}", f"{len(rejected):,}")
    return {"input_rows": n_raw, "clean_rows": len(df), "rejected_rows": len(rejected), "output": str(processed_path),
            "dq": kpis}
