import pytest
from roip import modeling


def test_leakage_guard_rejects_outcome_columns():
    for bad in ["processing_hours", "completed_at", "sla_breached"]:
        with pytest.raises(Exception):
            modeling.assert_no_leakage(modeling.TRIAGE + [bad])


def test_feature_sets_clean():
    for fs in (modeling.INTAKE, modeling.TRIAGE, modeling.IN_FLIGHT):
        modeling.assert_no_leakage(fs)
    assert set(modeling.INTAKE) < set(modeling.TRIAGE) < set(modeling.IN_FLIGHT)


def test_temporal_split_has_no_overlap(full_clean):
    frame = modeling.modeling_frame(full_clean)
    tr, te = modeling.temporal_split(frame)
    assert tr["received_at"].max() <= te["received_at"].min()
    assert len(tr) > len(te) > 0


def test_model_beats_chance_on_small_sample(full_clean):
    res = modeling.run_model_study(full_clean.sample(30000, random_state=1), fast=True)
    assert res["models"]["B_triage|logreg"]["roc_auc"] > 0.55
