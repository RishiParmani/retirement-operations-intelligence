"""Data-quality rule framework.

Every rule has an id, a plain-English description, a stage and a severity:

* stage ``reject`` - the record cannot be trusted or attributed; it is removed and written to the
  rejected-records file with a reason (nothing is dropped silently).
* stage ``fix``    - the record is kept and a documented correction is applied.
* stage ``flag``   - the record is kept unchanged; the issue is counted and logged so analysts
  know about it. Flags never change KPI values.

``apply_reject_rules`` / ``apply_flag_rules`` return both the data and a result table that is used
for the data-quality report and the Power BI "Data Quality" page.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import numpy as np
import pandas as pd

from . import config as C


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    description: str
    stage: str      # reject | fix | flag
    severity: str   # critical | warning | info
    check: Callable[[pd.DataFrame], pd.Series]
    reason: str = ""


def _completed(df): return df["status"] == "Completed"


# ----------------------------------------------------------------------------- reject rules
def _missing_required(df: pd.DataFrame) -> pd.Series:
    return df[C.REQUIRED_FIELDS].isna().any(axis=1)


def _bad_category(df: pd.DataFrame) -> pd.Series:
    bad = ~df["priority"].isin(C.VALID_PRIORITIES) | ~df["status"].isin(C.VALID_STATUSES)
    bad |= ~df["operation_type"].isin(C.SLA_POLICY_HOURS.keys())
    bad |= df["channel"].notna() & ~df["channel"].isin(C.VALID_CHANNELS)
    bad |= df["region"].notna() & ~df["region"].isin(C.VALID_REGIONS | {"Unknown"})
    return bad


REJECT_RULES: list[Rule] = [
    Rule("R01", "Required field missing", "operation_id, operation_type, received_at, priority, status and "
         "sla_target_hours must be present; without them the record cannot be classified or measured.",
         "reject", "critical", _missing_required, "Missing required field"),
    Rule("R02", "Duplicate operation_id", "operation_id is the primary key; the first occurrence is kept, repeats are "
         "exact duplicates created by replays/re-loads and would double count volume.",
         "reject", "critical", lambda d: d.duplicated(subset="operation_id", keep="first"), "Duplicate operation_id"),
    Rule("R03", "Invalid team category", "processing_team must be one of the five known teams; records with an "
         "unknown team cannot be attributed in workload analysis.",
         "reject", "critical", lambda d: ~d["processing_team"].isin(C.VALID_TEAMS), "Invalid team category"),
    Rule("R04", "Invalid category value", "priority, status, operation_type, channel and region must come from the "
         "reference lists.", "reject", "critical", _bad_category, "Invalid category value"),
    Rule("R05", "Negative processing hours", "A negative duration is impossible. (The original ETL silently clipped "
         "these to 0; they are now rejected and reported instead.)",
         "reject", "critical", lambda d: d["processing_hours"] < 0, "Negative processing_hours"),
    Rule("R06", "Negative transaction amount", "Transaction amounts are non-negative in this data set.",
         "reject", "critical", lambda d: d["transaction_amount"] < 0, "Negative transaction_amount"),
    Rule("R07", "Completion before receipt", "completed_at earlier than received_at is impossible.",
         "reject", "critical", lambda d: d["completed_at"].notna() & (d["completed_at"] < d["received_at"]),
         "completed_at earlier than received_at"),
    Rule("R08", "Completed without completion time", "status = Completed requires completed_at.",
         "reject", "critical", lambda d: _completed(d) & d["completed_at"].isna(), "Completed without completed_at"),
]

# ----------------------------------------------------------------------------- flag rules
def _stale_pending(df: pd.DataFrame) -> pd.Series:
    asof = df["received_at"].max()
    return (df["status"] == "Pending") & ((asof - df["received_at"]).dt.days > C.STALE_PENDING_DAYS)


def _outlier(df: pd.DataFrame) -> pd.Series:
    comp = df.loc[_completed(df), "processing_hours"]
    if comp.empty:
        return pd.Series(False, index=df.index)
    q1, q3 = comp.quantile([0.25, 0.75])
    fence = q3 + C.OUTLIER_IQR_MULTIPLIER * (q3 - q1)
    return _completed(df) & (df["processing_hours"] > fence)


FLAG_RULES: list[Rule] = [
    Rule("F01", "Work started after completion", "started_at is later than completed_at on a completed operation. "
         "processing_hours is measured received->completed, so KPIs are unaffected, but the started_at/assigned_at "
         "timestamps are unreliable for touch-time analysis.", "flag", "warning",
         lambda d: _completed(d) & d["started_at"].notna() & d["completed_at"].notna() & (d["started_at"] > d["completed_at"])),
    Rule("F02", "Assigned before received", "assigned_at earlier than received_at.", "flag", "warning",
         lambda d: d["assigned_at"].notna() & (d["assigned_at"] < d["received_at"])),
    Rule("F03", "Started before assigned", "started_at earlier than assigned_at.", "flag", "warning",
         lambda d: d["started_at"].notna() & d["assigned_at"].notna() & (d["started_at"] < d["assigned_at"])),
    Rule("F04", "SLA target differs from policy", "sla_target_hours does not equal the policy value for the "
         "operation type.", "flag", "warning",
         lambda d: d["sla_target_hours"] != d["operation_type"].map(C.SLA_POLICY_HOURS)),
    Rule("F05", "Exception flag / type mismatch", "exception_flag and exception_type disagree.", "flag", "warning",
         lambda d: d["exception_flag"].astype(bool) != d["exception_type"].notna()),
    Rule("F06", "Amount inconsistent with operation type", "Financial operation with a zero amount, or a "
         "non-financial operation with an amount.", "flag", "warning",
         lambda d: (d["operation_type"].isin(C.FINANCIAL_OPERATION_TYPES) & (d["transaction_amount"] <= 0))
         | (~d["operation_type"].isin(C.FINANCIAL_OPERATION_TYPES) & (d["transaction_amount"] > 0))),
    Rule("F07", "Extreme processing time (outlier)", "Completed operation above Q3 + 3xIQR of processing_hours. "
         "Retained: long-running cases are genuine operational findings, not errors.", "flag", "warning", _outlier),
    Rule("F08", "Processing hours on a non-completed operation", "processing_hours is populated for Pending, Failed "
         "and Escalated operations although they never completed, so the value is not a real duration. All KPIs "
         "therefore use Completed operations only.", "flag", "info",
         lambda d: ~_completed(d) & d["processing_hours"].notna()),
    Rule("F09", "Stale pending item", f"Pending for more than {C.STALE_PENDING_DAYS} days at the data cut-off.",
         "flag", "info", _stale_pending),
]


# ----------------------------------------------------------------------------- engines
def apply_reject_rules(df: pd.DataFrame, logger=None):
    """Apply reject rules sequentially. Returns (clean_df, rejected_df, results)."""
    n_raw = len(df)
    rejected, results = [], []
    for rule in REJECT_RULES:
        mask = rule.check(df).fillna(False).astype(bool)
        n = int(mask.sum())
        if n:
            reason = rule.reason
            if rule.id == "R01":  # name the first missing field(s) as the original ETL did
                first_missing = df.loc[mask, C.REQUIRED_FIELDS].isna().idxmax(axis=1)
                bad = df[mask].assign(rejection_reason="Missing required field: " + first_missing)
            else:
                bad = df[mask].assign(rejection_reason=reason)
            bad = bad.assign(rejection_rule=rule.id)
            rejected.append(bad)
            df = df[~mask]
        if logger:
            logger.info("%s %-34s rejected %6d", rule.id, rule.name, n)
        results.append(dict(rule_id=rule.id, rule_name=rule.name, stage=rule.stage, severity=rule.severity,
                            rows_affected=n, pct_of_raw=round(100 * n / n_raw, 4) if n_raw else 0.0,
                            action="Removed and written to the rejected-records file", description=rule.description))
    rej = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return df, rej, results


def apply_flag_rules(df: pd.DataFrame, n_raw: int, logger=None):
    """Apply flag rules to the cleaned frame. Returns (results, issue_log)."""
    results, logs = [], []
    for rule in FLAG_RULES:
        mask = rule.check(df).fillna(False).astype(bool)
        n = int(mask.sum())
        if logger:
            logger.info("%s %-48s flagged %6d (%s)", rule.id, rule.name, n, rule.severity)
        results.append(dict(rule_id=rule.id, rule_name=rule.name, stage=rule.stage, severity=rule.severity,
                            rows_affected=n, pct_of_raw=round(100 * n / n_raw, 4) if n_raw else 0.0,
                            action="Retained and flagged (no change to values)", description=rule.description))
        if n and rule.severity == "warning":   # row-level log only for warnings (info rows are counted only)
            logs.append(pd.DataFrame({"operation_id": df.loc[mask, "operation_id"].values,
                                      "rule_id": rule.id, "rule_name": rule.name, "severity": rule.severity}))
    log = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame(columns=["operation_id", "rule_id", "rule_name", "severity"])
    return results, log


def fix_result(rule_id: str, name: str, n: int, n_raw: int, description: str, action: str) -> dict:
    return dict(rule_id=rule_id, rule_name=name, stage="fix", severity="info", rows_affected=int(n),
                pct_of_raw=round(100 * n / n_raw, 4) if n_raw else 0.0, action=action, description=description)


def summary_stats(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Compact before/after profile used in the data-quality report."""
    rows = [dict(stage=label, metric="rows", detail="", value=len(df)),
            dict(stage=label, metric="unique_operation_ids", detail="", value=df["operation_id"].nunique())]
    for col in ["region", "completed_at", "exception_type", "processing_team"]:
        if col in df:
            rows.append(dict(stage=label, metric="null_count", detail=col, value=int(df[col].isna().sum())))
    for col in ["processing_hours", "transaction_amount", "team_workload"]:
        if col in df:
            s = pd.to_numeric(df[col], errors="coerce")
            for stat in ["mean", "50%", "max", "min"]:
                rows.append(dict(stage=label, metric=f"{col}_{'median' if stat == '50%' else stat}", detail="",
                                 value=round(float(s.describe()[stat]), 4)))
    for col in ["status", "region"]:
        if col in df:
            for k, v in df[col].fillna("<null>").value_counts().items():
                rows.append(dict(stage=label, metric=f"{col}_count", detail=str(k), value=int(v)))
    return pd.DataFrame(rows)


def dq_kpis(raw: pd.DataFrame, clean: pd.DataFrame, reject_results: list, flag_results: list, fix_results: list) -> dict:
    n_raw, n_clean = len(raw), len(clean)
    complete = (~raw[C.REQUIRED_FIELDS].isna().any(axis=1)).mean()
    dup = int(next(r["rows_affected"] for r in reject_results if r["rule_id"] == "R02"))
    invalid = sum(r["rows_affected"] for r in reject_results if r["rule_id"] in ("R03", "R04"))
    warn_rows = sum(r["rows_affected"] for r in flag_results if r["severity"] == "warning")
    return {
        "raw_records": n_raw, "clean_records": n_clean, "rejected_records": n_raw - n_clean,
        "acceptance_rate_pct": round(100 * n_clean / n_raw, 2) if n_raw else 0.0,
        "completeness_required_fields_pct": round(100 * float(complete), 2),
        "uniqueness_pct": round(100 * (1 - dup / n_raw), 2) if n_raw else 0.0,
        "validity_pct": round(100 * (1 - invalid / n_raw), 2) if n_raw else 0.0,
        "region_imputed_unknown": int(next((r["rows_affected"] for r in fix_results if r["rule_id"] == "X01"), 0)),
        "warning_flag_events": int(warn_rows),
        "mean_data_quality_score": round(float(clean["data_quality_score"].mean()), 2) if n_clean else 0.0,
    }
