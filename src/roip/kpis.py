"""Single source of truth for KPI logic (Python).  SQL and DAX implement the same definitions;
tests/test_sql_python_reconciliation.py proves the numbers agree.

Population rules (the reason three systems can disagree if you are careless):
* Volume, exception and rework measures use ALL operations.
* SLA and processing-time measures use COMPLETED operations only - Pending/Failed/Escalated items never
  finished, so their (generated) processing_hours is not a real duration.
"""
from __future__ import annotations
import pandas as pd

KPI_DEFINITIONS = [
    dict(kpi="Total Operations", population="All", logic="count of rows (operation_id is unique)",
         python="len(df)", sql="COUNT(*)", dax="COUNTROWS(operations_clean)",
         meaning="Workload received in the period."),
    dict(kpi="Completed Operations", population="All", logic="status = 'Completed'",
         python="(df.status=='Completed').sum()", sql="COUNT(*) FILTER (WHERE status='Completed')",
         dax="CALCULATE([Total Operations], status = \"Completed\")", meaning="Throughput."),
    dict(kpi="Pending Operations", population="All", logic="status = 'Pending'",
         python="(df.status=='Pending').sum()", sql="COUNT(*) FILTER (WHERE status='Pending')",
         dax="CALCULATE([Total Operations], status = \"Pending\")", meaning="Work in progress / queued."),
    dict(kpi="Failed Operations", population="All", logic="status = 'Failed'",
         python="(df.status=='Failed').sum()", sql="COUNT(*) FILTER (WHERE status='Failed')",
         dax="CALCULATE([Total Operations], status = \"Failed\")", meaning="Operations that could not be completed."),
    dict(kpi="Escalated Operations", population="All", logic="status = 'Escalated'",
         python="(df.status=='Escalated').sum()", sql="COUNT(*) FILTER (WHERE status='Escalated')",
         dax="CALCULATE([Total Operations], status = \"Escalated\")", meaning="Cases handed to a senior team; all carry an exception."),
    dict(kpi="Open Backlog", population="All", logic="status in ('Pending','Escalated') (unresolved, still owned)",
         python="df.status.isin(['Pending','Escalated']).sum()", sql="COUNT(*) FILTER (WHERE status IN ('Pending','Escalated'))",
         dax="[Pending Operations] + [Escalated Operations]", meaning="Work still waiting to be finished. Failed items are closed, not backlog."),
    dict(kpi="Completion Rate %", population="All", logic="Completed / Total", python="completed/total",
         sql="100.0*COUNT(*) FILTER (WHERE status='Completed')/COUNT(*)", dax="DIVIDE([Completed Operations],[Total Operations])",
         meaning="Share of received work that finished."),
    dict(kpi="Average Processing Hours", population="Completed", logic="mean(processing_hours) where Completed; processing_hours = completed_at - received_at (cycle time)",
         python="completed.processing_hours.mean()", sql="AVG(processing_hours) FILTER (WHERE status='Completed')",
         dax="CALCULATE(AVERAGE(processing_hours), status = \"Completed\")", meaning="Typical end-to-end cycle time (mean is pulled up by a long tail)."),
    dict(kpi="Median Processing Hours", population="Completed", logic="median(processing_hours) where Completed",
         python="completed.processing_hours.median()", sql="percentile_cont(0.5) WITHIN GROUP (ORDER BY processing_hours)",
         dax="CALCULATE(MEDIAN(processing_hours), status = \"Completed\")", meaning="Typical case, robust to the long tail."),
    dict(kpi="SLA Breach Count", population="Completed", logic="Completed AND processing_hours > sla_target_hours",
         python="completed.sla_breached.sum()", sql="SUM(sla_breached) FILTER (WHERE status='Completed')",
         dax="CALCULATE(SUM(sla_breached), status = \"Completed\")", meaning="Service failures."),
    dict(kpi="SLA Breach Rate %", population="Completed", logic="breaches / Completed", python="completed.sla_breached.mean()",
         sql="100.0*AVG(sla_breached) FILTER (WHERE status='Completed')", dax="DIVIDE([SLA Breach Count],[Completed Operations])",
         meaning="Probability a finished case missed its SLA."),
    dict(kpi="SLA Compliance %", population="Completed", logic="1 - SLA Breach Rate", python="1-breach_rate",
         sql="100 - breach rate", dax="DIVIDE([Completed Operations]-[SLA Breach Count],[Completed Operations])",
         meaning="Headline service level. (The first Power BI draft divided by ALL rows and showed 74.58% instead of 73.29%.)"),
    dict(kpi="Exception Rate %", population="All", logic="exception_flag = TRUE / Total", python="df.exception_flag.mean()",
         sql="100.0*AVG(exception_flag::int)", dax="DIVIDE([Exception Count],[Total Operations])", meaning="Share of work that hit a problem needing intervention."),
    dict(kpi="Rework Rate %", population="All", logic="rework_flag = TRUE / Total", python="df.rework_flag.mean()",
         sql="100.0*AVG(rework_flag::int)", dax="DIVIDE([Rework Count],[Total Operations])", meaning="Share of work that had to be redone."),
    dict(kpi="Total Transaction Amount", population="All", logic="sum(transaction_amount) (USD, synthetic; non-financial operation types are 0)",
         python="df.transaction_amount.sum()", sql="SUM(transaction_amount)", dax="SUM(transaction_amount)",
         meaning="Value of money-movement work handled."),
]


def completed(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "Completed"]


def _safe_pct(num, den) -> float:
    return round(100 * num / den, 2) if den else 0.0


def kpi_summary(df: pd.DataFrame) -> dict:
    """Headline KPIs (keys kept compatible with the original reports/kpi_summary.json)."""
    c = completed(df)
    n, nc = len(df), len(c)
    breaches = int(c["sla_breached"].sum()) if nc else 0
    return {
        "total_operations": int(n),
        "completed_operations": int(nc),
        "pending_operations": int((df["status"] == "Pending").sum()),
        "failed_operations": int((df["status"] == "Failed").sum()),
        "escalated_operations": int((df["status"] == "Escalated").sum()),
        "open_backlog": int(df["status"].isin(["Pending", "Escalated"]).sum()),
        "completion_rate_pct": _safe_pct(nc, n),
        "sla_breach_count": breaches,
        "sla_breach_rate_pct": _safe_pct(breaches, nc),
        "sla_compliance_pct": round(100 - _safe_pct(breaches, nc), 2) if nc else 0.0,
        "avg_processing_hours": round(float(c["processing_hours"].mean()), 2) if nc else 0.0,
        "median_processing_hours": round(float(c["processing_hours"].median()), 2) if nc else 0.0,
        "exception_count": int(df["exception_flag"].sum()),
        "exception_rate_pct": _safe_pct(df["exception_flag"].sum(), n),
        "rework_count": int(df["rework_flag"].sum()),
        "rework_rate_pct": _safe_pct(df["rework_flag"].sum(), n),
        "total_transaction_amount": round(float(df["transaction_amount"].sum()), 2),
    }


def group_kpis(df: pd.DataFrame, by) -> pd.DataFrame:
    """KPIs per group using the same population rules as ``kpi_summary``."""
    by = [by] if isinstance(by, str) else list(by)
    g_all = df.groupby(by, dropna=False)
    out = g_all.agg(operations=("operation_id", "count"), exceptions=("exception_flag", "sum"), reworks=("rework_flag", "sum"))
    c = completed(df).groupby(by, dropna=False)
    comp = c.agg(completed=("operation_id", "count"), sla_breaches=("sla_breached", "sum"),
                 avg_processing_hours=("processing_hours", "mean"), median_processing_hours=("processing_hours", "median"),
                 p90_processing_hours=("processing_hours", lambda s: s.quantile(0.9)))
    out = out.join(comp).fillna({"completed": 0, "sla_breaches": 0})
    out["sla_breach_rate"] = (out["sla_breaches"] / out["completed"]).where(out["completed"] > 0)
    out["sla_compliance"] = 1 - out["sla_breach_rate"]
    out["exception_rate"] = out["exceptions"] / out["operations"]
    out["rework_rate"] = out["reworks"] / out["operations"]
    out["share_of_breaches"] = out["sla_breaches"] / out["sla_breaches"].sum() if out["sla_breaches"].sum() else 0.0
    return out.reset_index()
