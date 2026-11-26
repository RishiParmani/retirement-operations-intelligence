import pandas as pd
from roip import kpis


def _toy():
    return pd.DataFrame({
        "operation_id": list("abcdef"),
        "status": ["Completed", "Completed", "Completed", "Pending", "Escalated", "Failed"],
        "processing_hours": [10, 30, 50, 999, 999, 999],
        "sla_target_hours": [24] * 6,
        "sla_breached": [0, 1, 1, 0, 0, 0],
        "exception_flag": [False, True, False, False, True, True],
        "rework_flag": [False, False, True, False, False, False],
        "transaction_amount": [1.0] * 6,
    })


def test_population_rules_toy():
    k = kpis.kpi_summary(_toy())
    assert k["total_operations"] == 6 and k["completed_operations"] == 3
    assert k["open_backlog"] == 2
    assert k["sla_breach_count"] == 2
    assert k["sla_compliance_pct"] == 33.33
    assert k["avg_processing_hours"] == 30.0          # non-completed hours (999) must NOT leak in
    assert k["exception_rate_pct"] == 50.0           # exceptions use all operations
    assert k["rework_rate_pct"] == 16.67


def test_group_kpis_consistent_with_summary():
    g = kpis.group_kpis(_toy(), "status")
    assert g["operations"].sum() == 6
    assert g.loc[g.status == "Pending", "completed"].iloc[0] == 0


def test_reference_values_on_full_data(full_clean):
    k = kpis.kpi_summary(full_clean)
    assert k["total_operations"] == 199200
    assert k["sla_compliance_pct"] == 73.29
    assert k["avg_processing_hours"] == 37.34
    assert k["open_backlog"] == 7274


def test_kpi_dictionary_complete():
    for d in kpis.KPI_DEFINITIONS:
        assert all(d[k] for k in ["kpi", "population", "logic", "python", "sql", "dax", "meaning"])
