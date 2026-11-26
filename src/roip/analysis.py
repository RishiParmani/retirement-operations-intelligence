"""Business analysis: SLA drivers, exceptions/rework cascade, backlog age, run-off, stability checks.

Every function returns tidy DataFrames; ``build_insights`` assembles them plus a ``headline`` dict that the
documentation generator reads, so no figure in the written findings is typed by hand."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

from .kpis import completed, kpi_summary, group_kpis

WORKLOAD_BINS = [0, 54, 74, 94, 10_000]
WORKLOAD_LABELS = ["35-54", "55-74", "75-94", "95+"]
AGE_BINS = [-1, 30, 90, 180, 10_000]
AGE_LABELS = ["0-30 days", "31-90 days", "91-180 days", "181+ days"]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ["received_at", "assigned_at", "started_at", "completed_at"]:
        d[c] = pd.to_datetime(d[c], errors="coerce")
    d["workload_band"] = pd.cut(d["team_workload"], WORKLOAD_BINS, labels=WORKLOAD_LABELS).astype(str)
    d["intake_completeness"] = np.where(d["missing_info_flag"], "Information missing", "Information complete")
    d["exception_status"] = np.where(d["exception_flag"], "Exception raised", "No exception")
    d["rework_status"] = np.where(d["rework_flag"], "Reworked", "No rework")
    d["received_month_start"] = d["received_at"].dt.to_period("M").dt.to_timestamp()
    d["received_hour"] = d["received_at"].dt.hour
    return d


def driver_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
    c = completed(df)
    base = c["sla_breached"].mean()
    t = c.groupby(col, observed=True).agg(completed=("operation_id", "count"), breaches=("sla_breached", "sum"),
                                           avg_hours=("processing_hours", "mean"), median_hours=("processing_hours", "median"))
    t["breach_rate"] = t["breaches"] / t["completed"]
    t["lift_vs_overall"] = t["breach_rate"] / base
    t["share_of_breaches"] = t["breaches"] / t["breaches"].sum()
    t["share_of_completed"] = t["completed"] / t["completed"].sum()
    return t.reset_index()


def cramers_v(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """(Cramer's V effect size, chi-square p-value). With ~190k rows p-values are tiny for any difference,
    so V (0 = no association, 1 = perfect) is what we actually interpret."""
    ct = pd.crosstab(x, y)
    chi2, p, _, _ = stats.chi2_contingency(ct, correction=False)
    n = ct.values.sum()
    v = float(np.sqrt((chi2 / n) / (min(ct.shape) - 1))) if min(ct.shape) > 1 else 0.0
    return v, float(p)


def association_with_breach(df: pd.DataFrame) -> pd.DataFrame:
    """Effect size of each candidate driver against SLA breach (completed operations)."""
    c = completed(df)
    dims = ["priority", "intake_completeness", "exception_status", "rework_status", "workload_band", "operation_type",
            "region", "channel", "processing_team", "customer_segment", "received_month", "received_day_of_week",
            "received_hour", "exception_type", "exception_severity", "root_cause"]
    rows = []
    for d in dims:
        sub = c[c[d].notna()] if d in ("exception_type", "exception_severity", "root_cause") else c
        v, p = cramers_v(sub[d], sub["sla_breached"])
        rates = sub.groupby(d)["sla_breached"].mean()
        rows.append(dict(dimension=d, cramers_v=v, p_value=p, min_breach_rate=rates.min(), max_breach_rate=rates.max(),
                         spread_pts=100 * (rates.max() - rates.min()), n_levels=int(rates.size)))
    out = pd.DataFrame(rows).sort_values("cramers_v", ascending=False).reset_index(drop=True)
    out["verdict"] = np.select([out.cramers_v >= 0.20, out.cramers_v >= 0.08], ["strong driver", "moderate driver"], "no practical effect")
    return out


def attributable_breaches(df: pd.DataFrame, flag: str) -> dict:
    """Priority-adjusted 'excess breaches' for operations with ``flag`` True: how many fewer breaches would there be if
    they breached at the rate of same-priority operations without the flag. Association, not proof of causation."""
    c = completed(df)
    g = c.groupby(["priority", flag])["sla_breached"].agg(["size", "mean"]).unstack(flag)
    excess = 0.0
    n_flag = 0
    for p in g.index:
        n1, r1 = g.loc[p, ("size", True)], g.loc[p, ("mean", True)]
        r0 = g.loc[p, ("mean", False)]
        excess += n1 * (r1 - r0)
        n_flag += n1
    return {"flag": flag, "operations": int(n_flag), "excess_breaches": float(excess),
            "share_of_all_breaches": float(excess / c["sla_breached"].sum())}


def monthly_flow(df: pd.DataFrame) -> pd.DataFrame:
    rec = df.groupby(df["received_at"].dt.to_period("M")).size().rename("received")
    comp = completed(df)
    done = comp.groupby(comp["completed_at"].dt.to_period("M")).size().rename("completed_by_completion_month")
    cohort = comp.groupby(comp["received_at"].dt.to_period("M")).size().rename("completed_from_month_cohort")
    t = pd.concat([rec, done, cohort], axis=1).fillna(0).astype(int)
    t.index = t.index.astype(str)
    return t.reset_index(names="month")


def monthly_breach(df: pd.DataFrame) -> pd.DataFrame:
    c = completed(df)
    t = c.groupby(c["received_at"].dt.to_period("M")).agg(completed=("operation_id", "count"), breach_rate=("sla_breached", "mean"))
    t.index = t.index.astype(str)
    return t.reset_index(names="month")


def backlog_age(df: pd.DataFrame) -> pd.DataFrame:
    asof = df["received_at"].max()
    b = df[df["status"].isin(["Pending", "Escalated"])].copy()
    b["age_days"] = (asof - b["received_at"]).dt.days
    b["age_band"] = pd.cut(b["age_days"], AGE_BINS, labels=AGE_LABELS)
    t = b.groupby(["status", "age_band"], observed=False).size().rename("operations").reset_index()
    t.attrs["as_of"] = str(asof)
    return t


def processing_distribution(df: pd.DataFrame) -> pd.DataFrame:
    c = completed(df)
    q = c["processing_hours"].quantile([0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).rename("hours").reset_index()
    q["percentile"] = (q["index"] * 100).astype(int)
    return q[["percentile", "hours"]]


def type_vs_target(df: pd.DataFrame) -> pd.DataFrame:
    t = group_kpis(df, "operation_type")
    tgt = df.groupby("operation_type")["sla_target_hours"].first().rename("sla_target_hours")
    t = t.merge(tgt, on="operation_type")
    t["avg_hours_vs_target"] = t["avg_processing_hours"] / t["sla_target_hours"]
    t["share_over_2x_target"] = t["operation_type"].map(
        completed(df).assign(x=lambda d: d["processing_hours"] > 2 * d["sla_target_hours"]).groupby("operation_type")["x"].mean())
    return t.sort_values("sla_target_hours")


def risk_segments(df: pd.DataFrame, min_n: int = 500) -> pd.DataFrame:
    c = completed(df)
    t = c.groupby(["priority", "intake_completeness", "exception_status"], observed=True).agg(
        completed=("operation_id", "count"), breaches=("sla_breached", "sum"), breach_rate=("sla_breached", "mean"),
        avg_hours=("processing_hours", "mean")).reset_index()
    t = t[t["completed"] >= min_n].sort_values("breach_rate", ascending=False)
    t["share_of_breaches"] = t["breaches"] / c["sla_breached"].sum()
    return t


def exception_cascade(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, mask in [("Information complete", ~df["missing_info_flag"]), ("Information missing", df["missing_info_flag"])]:
        s = df[mask]
        rows.append(dict(group=label, operations=len(s), exception_rate=s["exception_flag"].mean(),
                         rework_rate=s["rework_flag"].mean()))
    for label, mask in [("No exception", ~df["exception_flag"]), ("Exception raised", df["exception_flag"])]:
        s = df[mask]
        rows.append(dict(group=label, operations=len(s), exception_rate=s["exception_flag"].mean(),
                         rework_rate=s["rework_flag"].mean()))
    return pd.DataFrame(rows)


def build_insights(df_raw: pd.DataFrame) -> dict:
    df = prepare(df_raw)
    c = completed(df)
    ins = {
        "kpis": kpi_summary(df),
        "assoc": association_with_breach(df),
        "by_priority": driver_table(df, "priority"),
        "by_missing": driver_table(df, "intake_completeness"),
        "by_exception": driver_table(df, "exception_status"),
        "by_rework": driver_table(df, "rework_status"),
        "by_workload": driver_table(df, "workload_band"),
        "by_type": type_vs_target(df),
        "flow": monthly_flow(df),
        "monthly_breach": monthly_breach(df),
        "backlog": backlog_age(df),
        "distribution": processing_distribution(df),
        "segments": risk_segments(df),
        "cascade": exception_cascade(df),
    }
    ins["attrib_missing"] = attributable_breaches(df, "missing_info_flag")
    ins["attrib_exception"] = attributable_breaches(df, "exception_flag")
    ins["attrib_rework"] = attributable_breaches(df, "rework_flag")
    p = ins["by_priority"].set_index("priority")
    miss, exc = ins["by_missing"].set_index("intake_completeness"), ins["by_exception"].set_index("exception_status")
    wl = ins["by_workload"].set_index("workload_band")
    flow = ins["flow"].set_index("month")
    bl = ins["backlog"]
    top = ins["segments"].iloc[0]
    ins["headline"] = {
        "breach_rate_overall": float(c["sla_breached"].mean()),
        "breach_rate_by_priority": {k: float(v) for k, v in p["breach_rate"].items()},
        "breach_share_low_medium": float(p.loc[["Low", "Medium"], "share_of_breaches"].sum()),
        "breach_share_medium": float(p.loc["Medium", "share_of_breaches"]),
        "avg_hours_by_priority": {k: float(v) for k, v in p["avg_hours"].items()},
        "breach_rate_info_missing": float(miss.loc["Information missing", "breach_rate"]),
        "breach_rate_info_complete": float(miss.loc["Information complete", "breach_rate"]),
        "completed_info_missing": int(miss.loc["Information missing", "completed"]),
        "breach_rate_exception": float(exc.loc["Exception raised", "breach_rate"]),
        "breach_rate_no_exception": float(exc.loc["No exception", "breach_rate"]),
        "avg_hours_exception": float(exc.loc["Exception raised", "avg_hours"]),
        "avg_hours_no_exception": float(exc.loc["No exception", "avg_hours"]),
        "breach_rate_by_workload": {k: float(v) for k, v in wl["breach_rate"].items()},
        "exception_rate_info_missing": float(ins["cascade"].set_index("group").loc["Information missing", "exception_rate"]),
        "exception_rate_info_complete": float(ins["cascade"].set_index("group").loc["Information complete", "exception_rate"]),
        "rework_rate_exception": float(ins["cascade"].set_index("group").loc["Exception raised", "rework_rate"]),
        "rework_rate_no_exception": float(ins["cascade"].set_index("group").loc["No exception", "rework_rate"]),
        "excess_breaches_missing_info": ins["attrib_missing"]["excess_breaches"],
        "excess_share_missing_info": ins["attrib_missing"]["share_of_all_breaches"],
        "excess_breaches_exception": ins["attrib_exception"]["excess_breaches"],
        "excess_share_exception": ins["attrib_exception"]["share_of_all_breaches"],
        "total_breaches": int(c["sla_breached"].sum()),
        "jan2026_completed": int(flow.loc["2026-01", "completed_by_completion_month"]),
        "jan2026_received": int(flow.loc["2026-01", "received"]),
        "backlog_as_of": ins["backlog"].attrs.get("as_of"),
        "pending_over_90d": int(df[(df.status == "Pending")].assign(a=lambda d: (df.received_at.max() - d.received_at).dt.days).query("a > 90").shape[0]),
        "pending_total": int((df.status == "Pending").sum()),
        "p50_hours": float(c["processing_hours"].quantile(.5)), "p90_hours": float(c["processing_hours"].quantile(.9)),
        "p99_hours": float(c["processing_hours"].quantile(.99)), "max_hours": float(c["processing_hours"].max()),
        "top_segment": {k: (v if not isinstance(v, (np.floating, np.integer)) else float(v)) for k, v in top.to_dict().items()},
        "strong_drivers": ins["assoc"].query("verdict=='strong driver'").dimension.tolist(),
        "moderate_drivers": ins["assoc"].query("verdict=='moderate driver'").dimension.tolist(),
        "no_effect_dims": ins["assoc"].query("verdict=='no practical effect'").dimension.tolist(),
    }
    return ins
