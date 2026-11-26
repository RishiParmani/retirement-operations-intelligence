import pandas as pd
from roip import dq, config


def test_row_accounting(pipeline_small):
    o = pipeline_small["out"]
    assert o["input_rows"] == o["clean_rows"] + o["rejected_rows"]
    assert o["input_rows"] == len(pipeline_small["raw"])


def test_primary_key_unique_and_required_fields(pipeline_small):
    clean = pd.read_csv(pipeline_small["dir"] / "clean.csv")
    assert clean["operation_id"].is_unique
    assert clean[config.REQUIRED_FIELDS].notna().all().all()


def test_every_rejected_row_has_a_reason(pipeline_small):
    rej = pd.read_csv(pipeline_small["dir"] / "rej.csv")
    assert "rejection_rule" in rej.columns and rej["rejection_rule"].notna().all()
    assert rej["rejection_reason"].notna().all()


def test_region_filled_not_dropped(pipeline_small):
    clean = pd.read_csv(pipeline_small["dir"] / "clean.csv")
    assert clean["region"].notna().all()


def test_sla_breach_definition(pipeline_small):
    c = pd.read_csv(pipeline_small["dir"] / "clean.csv")
    expect = ((c.processing_hours > c.sla_target_hours) & (c.status == "Completed")).astype(int)
    assert (c.sla_breached == expect).all()
    assert c.loc[c.status != "Completed", "sla_breached"].eq(0).all()


def test_dq_reports_written(pipeline_small):
    d = pipeline_small["dir"] / "dq"
    for f in ["dq_rule_results.csv", "dq_issue_log.csv", "dq_before_after.csv", "dq_run_summary.csv", "dq_rejected_records.csv"]:
        assert (d / f).exists(), f


def test_non_financial_types_have_zero_amount(pipeline_small):
    c = pd.read_csv(pipeline_small["dir"] / "clean.csv")
    nonfin = ~c.operation_type.isin(config.FINANCIAL_OPERATION_TYPES)
    assert (c.loc[nonfin, "transaction_amount"] == 0).all()
    assert (c.loc[~nonfin, "transaction_amount"] > 0).all()


def test_etl_is_deterministic(tmp_path, raw_small):
    from roip.etl import run_etl
    raw_small.to_csv(tmp_path / "r.csv", index=False)
    for i in (1, 2):
        run_etl(raw_path=tmp_path / "r.csv", processed_path=tmp_path / f"c{i}.csv",
                rejected_path=tmp_path / f"x{i}.csv", report_dir=tmp_path / f"d{i}")
    assert (tmp_path / "c1.csv").read_bytes() == (tmp_path / "c2.csv").read_bytes()


def test_reject_rules_catch_injected_bad_rows(raw_small):
    bad = raw_small.head(50).copy()
    bad.loc[bad.index[0], "operation_id"] = None
    bad = pd.concat([bad, bad.iloc[[5]]])  # duplicate id
    clean, rejected, results = dq.apply_reject_rules(bad)
    assert len(clean) + len(rejected) == len(bad)
    assert len(rejected) >= 2
