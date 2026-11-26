"""Every SQL query must execute, and the SQL headline numbers must equal the Python KPI layer."""
import pytest
from roip import kpis, sqlrun


@pytest.fixture(scope="module")
def con(full_clean):
    return sqlrun.build_database()


def test_all_queries_run(con):
    qs = sqlrun.all_queries()
    assert len(qs) >= 19
    for name, sql in qs.items():
        df = con.execute(sql).df()
        assert len(df) > 0, name


def test_headline_sql_equals_python(con, full_clean):
    s = con.execute(sqlrun.all_queries()["Q01_headline_kpis"]).df().iloc[0]
    k = kpis.kpi_summary(full_clean)
    for key in ["total_operations", "completed_operations", "open_backlog", "sla_breach_count",
                "exception_count", "rework_count"]:
        assert int(s[key]) == k[key], key
    for key in ["sla_compliance_pct", "avg_processing_hours", "median_processing_hours",
                "exception_rate_pct", "rework_rate_pct"]:
        assert abs(float(s[key]) - k[key]) < 0.011, key
    assert abs(float(s["total_transaction_amount"]) - k["total_transaction_amount"]) < 0.5


def test_priority_breach_rate_matches(con, full_clean):
    sql = con.execute(sqlrun.all_queries()["Q03_kpis_by_priority"]).df().set_index("priority")
    py = kpis.group_kpis(full_clean, "priority").set_index("priority")
    for p in sql.index:
        assert abs(sql.loc[p, "sla_breach_rate_pct"] - 100 * py.loc[p, "sla_breach_rate"]) < 0.011


def test_row_reconciliation(con):
    r = con.execute(sqlrun.all_queries()["Q14_row_reconciliation"]).df().iloc[0]
    assert r.loaded_records + r.rejected_records == r.raw_records == 200600


def test_monthly_flow_sums(con):
    m = con.execute(sqlrun.all_queries()["Q05_monthly_received_vs_completed"]).df()
    assert m.received.sum() == 199200 and m.completed.sum() == 189573
    jan = m[m.month.astype(str).str.startswith("2026-01")].iloc[0]
    assert jan.received == 0 and jan.completed > 0        # documented run-off, not a bug


def test_running_total_ends_at_total(con):
    d = con.execute(sqlrun.all_queries()["Q06_monthly_volume_mom_and_running_total"]).df()
    assert d.running_total.iloc[-1] == 199200
