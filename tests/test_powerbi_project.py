"""Structural tests for the PBIP project. These prove the files are consistent with the model and schema-shaped;
they do NOT prove Power BI Desktop renders them (that needs Desktop)."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_powerbi", ROOT / "scripts" / "validate_powerbi.py")
vp = importlib.util.module_from_spec(spec); spec.loader.exec_module(vp)


def test_structure_valid():
    errors, info = vp.run()
    assert errors == []
    assert info["pages"] == 5 and info["visuals"] > 100


def test_no_hardcoded_personal_path():
    txt = (vp.SM / "expressions.tmdl").read_text()
    assert "Users" not in txt and "ProjectRoot" in txt


def test_blank_prone_measures_use_sum_over_count():
    t = (vp.SM / "tables" / "operations_clean.tmdl").read_text()
    assert "AVERAGE(operations_clean[processing_hours])" not in t
    assert "DIVIDE([Completed Processing Hours], [Completed Operations])" in t


def test_dax_logic_mirrors_python(full_clean):
    """Re-implements the DAX definitions in pandas (SUM/COUNT over Completed) and compares with the KPI layer."""
    from roip import kpis
    c = full_clean[full_clean.status == "Completed"]
    assert round(c.processing_hours.sum() / len(c), 2) == kpis.kpi_summary(full_clean)["avg_processing_hours"]
    assert round(c.sla_target_hours.sum() / len(c), 2) == round(c.sla_target_hours.mean(), 2)


def test_dq_run_summary_matches_row_counts():
    s = pd.read_csv(vp.ROOT / "reports" / "data_quality" / "dq_run_summary.csv").set_index("metric")["value"]
    assert s["raw_records"] == s["clean_records"] + s["rejected_records"]
