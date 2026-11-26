"""SLA-breach risk model - audited and rebuilt.

What was wrong with the original model (see docs/ML_AUDIT.md):
* It used exception_flag / exception_type / rework_flag, which only exist once work is under way, while the README
  presented it as a prediction made from "operationally available features".
* It used a random split on time-ordered data (optimistic) and had no baseline, so 0.715 AUC could not be judged.
* Interpretation was impossible (random forest, no importances, no confusion matrix).

This version defines three explicit PREDICTION POINTS, each with only the features known at that moment, evaluates on
a TIME-BASED hold-out (train Jan-Sep, test Oct-Dec 2025) and compares against simple rate-table baselines.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL = ["operation_type", "priority", "channel", "region", "customer_segment", "processing_team", "received_day_of_week"]
NUMERIC_INTAKE = ["team_workload", "received_month", "received_hour"]
BINARY = ["missing_info_flag", "exception_flag", "rework_flag"]   # left unscaled so odds ratios read as "flag on vs off"
INTAKE = CATEGORICAL + NUMERIC_INTAKE                       # known when the operation arrives
TRIAGE = INTAKE + ["missing_info_flag"]                      # + completeness check done at intake review
IN_FLIGHT = TRIAGE + ["exception_flag", "rework_flag"]       # + problems discovered while processing
FEATURE_SETS = {"A_intake": INTAKE, "B_triage": TRIAGE, "C_in_flight": IN_FLIGHT}
PREDICTION_POINT = {"A_intake": "When the operation is received", "B_triage": "After the intake completeness check",
                    "C_in_flight": "While work is in progress (monitoring)"}
# Columns that must never be features: they are the target, derived from it, or only known after completion.
FORBIDDEN = {"sla_breached", "processing_hours", "completed_at", "status", "assigned_at", "started_at",
             "data_quality_score",   # = 100 - penalties that include exception_flag
             "exception_type", "exception_severity", "root_cause"}   # only exist if an exception already happened
TEST_START = "2025-10-01"
RANDOM_STATE = 42


def assert_no_leakage(features) -> None:
    bad = FORBIDDEN & set(features)
    if bad:
        raise ValueError(f"Leakage risk - forbidden features requested: {sorted(bad)}")


def modeling_frame(df: pd.DataFrame) -> pd.DataFrame:
    c = df[df["status"] == "Completed"].copy()
    c["received_at"] = pd.to_datetime(c["received_at"])
    c["received_hour"] = c["received_at"].dt.hour
    for k in ["missing_info_flag", "exception_flag", "rework_flag"]:
        c[k] = c[k].astype(int)
    return c


def temporal_split(c: pd.DataFrame, test_start: str = TEST_START):
    return c[c["received_at"] < test_start], c[c["received_at"] >= test_start]


def build_pipeline(features, estimator="logreg") -> Pipeline:
    assert_no_leakage(features)
    cat = [f for f in features if f in CATEGORICAL]
    binary = [f for f in features if f in BINARY]
    num = [f for f in features if f not in cat and f not in binary]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
                             ("bin", "passthrough", binary), ("num", StandardScaler(), num)])
    if estimator == "logreg":
        est = LogisticRegression(max_iter=500)
    elif estimator == "hgb":
        est = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.07, max_depth=4, random_state=RANDOM_STATE)
    else:
        raise ValueError(estimator)
    return Pipeline([("pre", pre), ("model", est)])


def score_metrics(y, p, review_share: float = 0.20) -> dict:
    """Discrimination, calibration and a capacity-based operating point: 'review the top X% by risk'."""
    y = np.asarray(y)
    k = int(np.ceil(review_share * len(y)))
    order = np.argsort(-np.asarray(p))
    flagged = np.zeros(len(y), dtype=bool)
    flagged[order[:k]] = True
    tn, fp, fn, tp = confusion_matrix(y, flagged).ravel()
    prevalence = float(y.mean())
    precision = tp / (tp + fp)
    return {"roc_auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)), "prevalence": prevalence,
            f"top{int(review_share*100)}pct_review": {"flagged": int(k), "precision": float(precision),
                "recall": float(tp / (tp + fn)), "lift": float(precision / prevalence),
                "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}}}


def rate_table_baseline(train: pd.DataFrame, test: pd.DataFrame, keys) -> np.ndarray:
    rate = train.groupby(keys)["sla_breached"].mean()
    prior = train["sla_breached"].mean()
    idx = pd.MultiIndex.from_frame(test[keys]) if len(keys) > 1 else test[keys[0]]
    return pd.Series(idx.map(rate)).fillna(prior).to_numpy(dtype=float)


def run_model_study(df: pd.DataFrame, fast: bool = False) -> dict:
    c = modeling_frame(df)
    train, test = temporal_split(c)
    ytr, yte = train["sla_breached"].astype(int), test["sla_breached"].astype(int)
    out = {"split": {"train_rows": len(train), "test_rows": len(test), "train_period": "2025-01 to 2025-09",
                     "test_period": "2025-10 to 2025-12", "prevalence_train": float(ytr.mean()), "prevalence_test": float(yte.mean())},
           "models": {}, "baselines": {}}
    fitted = {}
    for name, feats in FEATURE_SETS.items():
        for est in (["logreg"] if fast else ["logreg", "hgb"]):
            pipe = build_pipeline(feats, est).fit(train[feats], ytr)
            p = pipe.predict_proba(test[feats])[:, 1]
            m = score_metrics(yte, p)
            m.update(prediction_point=PREDICTION_POINT[name], n_features=len(feats))
            out["models"][f"{name}|{est}"] = m
            fitted[(name, est)] = (pipe, p)
    # baselines
    out["baselines"]["prior_rate_only"] = {"roc_auc": 0.5}
    for label, keys in [("priority_rate_table", ["priority"]), ("priority_x_missing_info_rate_table", ["priority", "missing_info_flag"])]:
        out["baselines"][label] = score_metrics(yte, rate_table_baseline(train, test, keys))
    # stability: 5-fold CV AUC on the training period for the interpretable models
    if not fast:
        cv = StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE)
        for name in FEATURE_SETS:
            s = cross_val_score(build_pipeline(FEATURE_SETS[name], "logreg"), train[FEATURE_SETS[name]], ytr, cv=cv, scoring="roc_auc")
            out["models"][f"{name}|logreg"]["cv_auc_mean_train"] = float(s.mean())
            out["models"][f"{name}|logreg"]["cv_auc_std_train"] = float(s.std())
    # legacy model for comparison (random split, original features incl. exception/rework flags)
    if not fast:
        legacy_feats = ["operation_type", "priority", "channel", "region", "processing_team", "team_workload", "customer_segment",
                        "exception_flag", "exception_type", "rework_flag", "sla_target_hours", "received_month", "received_day_of_week"]
        L = c.copy()
        L["exception_type"] = L["exception_type"].fillna("None").astype(str)
        Xtr, Xte, ytr_l, yte_l = train_test_split(L[legacy_feats], L["sla_breached"], test_size=.2, random_state=42, stratify=L["sla_breached"])
        cat = [f for f in legacy_feats if not pd.api.types.is_numeric_dtype(L[f])]
        pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat),
                                 ("n", StandardScaler(), [f for f in legacy_feats if f not in cat])])
        rf = Pipeline([("pre", pre), ("m", RandomForestClassifier(n_estimators=150, max_depth=12, min_samples_leaf=4,
                       class_weight="balanced", random_state=42, n_jobs=-1))]).fit(Xtr, ytr_l)
        out["legacy_model"] = {"description": "Original random forest, random split, uses exception/rework flags",
                               "roc_auc": float(roc_auc_score(yte_l, rf.predict_proba(Xte)[:, 1]))}
    # interpretation for the recommended model (B_triage logistic regression)
    pipe_b, p_b = fitted[("B_triage", "logreg")]
    names = pipe_b.named_steps["pre"].get_feature_names_out()
    coefs = pd.DataFrame({"feature": names, "coef": pipe_b.named_steps["model"].coef_[0]})
    coefs["odds_ratio"] = np.exp(coefs["coef"])
    coefs = coefs.reindex(coefs["coef"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    sample = test.sample(min(15000, len(test)), random_state=RANDOM_STATE)
    perm = permutation_importance(pipe_b, sample[TRIAGE], sample["sla_breached"], scoring="roc_auc", n_repeats=3, random_state=RANDOM_STATE)
    imp = pd.DataFrame({"feature": TRIAGE, "auc_drop": perm.importances_mean}).sort_values("auc_drop", ascending=False).reset_index(drop=True)
    bins = pd.qcut(pd.Series(p_b), 10, duplicates="drop")
    calib = pd.DataFrame({"p": p_b, "y": yte.values}).groupby(bins, observed=True).agg(predicted=("p", "mean"), observed=("y", "mean"), n=("y", "size")).reset_index(drop=True)
    out["recommended"] = "B_triage|logreg"
    out["_artifacts"] = {"fitted": fitted, "coefs": coefs, "importance": imp, "calibration": calib, "test": test}
    return out


def train_sla_model(df: pd.DataFrame):
    """Backward-compatible entry point: returns (fitted pipeline, metrics) for the recommended model."""
    c = modeling_frame(df)
    train, test = temporal_split(c)
    pipe = build_pipeline(TRIAGE, "logreg").fit(train[TRIAGE], train["sla_breached"].astype(int))
    p = pipe.predict_proba(test[TRIAGE])[:, 1]
    m = score_metrics(test["sla_breached"].astype(int), p)
    m["test_rows"] = len(test)
    return pipe, m
