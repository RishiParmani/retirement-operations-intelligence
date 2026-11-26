# Data Quality Framework

Implemented in `src/roip/dq.py` and `src/roip/etl.py`; run with `python scripts/run_pipeline.py`. Principle: **nothing is dropped silently**. Every record is either loaded, loaded with a documented repair, loaded with a warning flag, or written to the rejected file with a rule id and reason. The ETL asserts `raw = clean + rejected`.

## Rule stages
| Stage | Meaning | Rules |
|---|---|---|
| **reject** (critical) | Record cannot be trusted or would double count; removed and written to `data/rejected/operations_rejected.csv` | R01 required field missing, R02 duplicate operation_id, R03 invalid team category, R04 invalid category value, R05 negative processing hours, R06 negative amount, R07 completion before receipt, R08 completed without completion time |
| **fix** (info) | Deterministic repair, logged | X01 missing region -> `Unknown`; X02 `sla_breached` re-derived from the documented definition |
| **flag** (warning/info) | Record kept, issue logged in `dq_issue_log.csv` | F01 started after completion, F02-F03 timestamp order, F04 SLA target differs from policy, F05 exception flag/type mismatch, F06 amount inconsistent with type, F07 extreme processing time, F08 processing hours on non-completed operation, F09 stale pending (>90 days) |

## Run result on the project data (from `reports/data_quality/dq_rule_results.csv`)
- Raw 200,600 -> loaded 199,200 + rejected 1,400 (600 duplicate ids R02, 800 invalid team R03). Acceptance rate 99.3%.
- Fixes: 1,594 missing regions labelled `Unknown`; 2,748 `sla_breached` values re-derived (1.37% of raw).
- Flags (kept): F01 16,821; F07 3,486; F08 9,627; F09 5,238.
- Reject rules R01, R04-R08 and flag rules F02-F06 found **0** rows on this data. They are kept because they are cheap guards and are unit-tested with injected bad rows (`tests/test_etl_and_dq.py`).

## Outputs (`reports/data_quality/`)
`dq_rule_results.csv`, `dq_rejected_records.csv`, `dq_issue_log.csv`, `dq_before_after.csv`, `dq_run_summary.csv`, `dq_summary.json`; run log in `logs/pipeline.log`. `dq_run_summary.csv` and `dq_rule_results.csv` feed the "Data Quality & Pipeline" Power BI page.

## DQ KPIs
Acceptance rate, completeness of required fields, uniqueness, validity, region imputed, warning-flag events, mean `data_quality_score` (starts at 100; -10 for Unknown region, -5 for an exception; preserved from the original project).

## Decisions worth defending
- **Duplicates:** the first occurrence is kept; repeats are exact re-loads.
- **Missing region:** imputed as `Unknown` rather than guessed or dropped (dropping would bias volume).
- **Outliers and odd timestamps:** flagged, not deleted; they are real-looking records and the dashboard must still count them.
- **`sla_breached` recomputed** so that only Completed operations can breach.
- **Zero `transaction_amount`:** exactly the four non-financial operation types carry 0 (tested in `test_non_financial_types_have_zero_amount`). An earlier note that "some zero-value financial rows exist" was wrong and is corrected here.
- **Error handling:** missing input file or schema mismatch raises a clear error before anything is written; row accounting is asserted at the end.
