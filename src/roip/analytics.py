"""Backwards-compatible entry points. KPI logic now lives in ``kpis.py`` (single source of truth).

NOTE: the original ``group_performance`` averaged sla_breached and processing_hours over ALL statuses, which
disagreed with ``kpi_summary`` (completed only). It now delegates to ``group_kpis`` so both agree."""
from __future__ import annotations
from .kpis import kpi_summary, group_kpis


def group_performance(df, group_col):
    return group_kpis(df, group_col).set_index(group_col).sort_values("operations", ascending=False)

__all__ = ["kpi_summary", "group_performance", "group_kpis"]
