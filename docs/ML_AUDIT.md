# ML Audit: SLA-breach risk model

Code: `src/roip/modeling.py`, `scripts/train_model.py`; results: `reports/model/`; tests: `tests/test_modeling.py`.

## What was wrong with the original model
| Issue | Why it matters | Fix |
|---|---|---|
| `exception_flag`, `exception_type`, `rework_flag` used as features without saying when they are known | They only exist *during* processing. A model using them cannot be run at intake, yet was described as using "operationally available features" | Features split into three stages by when they are known (below); each stage reported separately |
| Random 80/20 split | Rows from the same weeks sit in both sets; overstates how well the model works on future work | Temporal split: train Jan-Sep 2025, test Oct-Dec 2025 |
| Only ROC-AUC and a threshold-0.5 report on a `class_weight="balanced"` forest | AUC alone is hard to turn into an operational decision | Added PR-AUC, Brier score, calibration deciles, and "review the top 20%" precision/recall/lift |
| No baseline | A model is only worth keeping if it beats simple rules | Added prior-rate and rate-table baselines |
| Random forest, no interpretation | Hard to explain to operations | Logistic regression (odds ratios) compared with HistGradientBoosting; permutation importance |
| Binary flags standardised | Made odds ratios meaningless | Binary flags pass through unscaled |

Leakage guard: `assert_no_leakage` rejects `processing_hours`, `completed_at`, `sla_breached` and other outcome columns; tested.

## Feature stages
- **A intake:** operation type, priority, channel, region, team, workload, segment, month, weekday, SLA target.
- **B triage:** A + `missing_info_flag` (known when the request is reviewed).
- **C in-flight:** B + `exception_flag`, `rework_flag` (known only once work has started).

## Results (temporal hold-out, 47,668 completed operations, prevalence 26.7%)
| Stage | Model | ROC-AUC | PR-AUC | Top-20% precision | Lift |
|---|---|---|---|---|---|
| A intake | logistic regression | 0.638 | 0.369 | 0.400 | 1.50x |
| B triage (recommended) | logistic regression | 0.677 | 0.451 | 0.462 | 1.73x |
| C in-flight | logistic regression | 0.723 | 0.519 | 0.538 | 2.02x |
| baselines | priority rate table / priority x missing-info table / prior | 0.606 / 0.648 / 0.500 | | | |
| legacy | original random forest on a random split | 0.715 | | | not comparable |

HistGradientBoosting matches logistic regression at every stage (differences in the third decimal), so the simple model is preferred. Permutation importance (AUC drop): priority (0.082 AUC drop), missing information (0.054; odds ratio 7.0), team workload (0.040); region about 0.0004.

## Honest assessment
- **The model adds modest value.** Stage B beats the best rate-table baseline by about 0.03 AUC. Reviewing the top 20% of risk scores catches 35% of breaches (precision 46% vs 27% base rate). Useful for prioritising a queue; not good enough to automate decisions.
- **Why the ceiling is low:** the generator adds lognormal noise to duration, so much of breach risk is irreproducible randomness. Real data could be better or worse.
- **Stage C is a monitoring tool, not an early warning:** it knows about exceptions that have already happened.
- **Scores are not probabilities by default.** Check `calibration_deciles.csv` before quoting them.
- **When ML is not the right tool:** the same story is told by a two-column rate table (priority x missing information) with most of the lift (top-20% lift 1.63x vs 1.73x for the model). For operations teams a rule such as "missing info + Low/Medium priority -> review first" is easier to audit and maintain. ML earns its keep only with real, richer data and a monitoring plan.
- **Not done:** hyper-parameter search, fairness analysis, drift monitoring, deployment. Synthetic data cannot justify them.
