# Data Model

## Power BI semantic model (`powerbi/ROIP_PowerBI_Project/*.SemanticModel`)
| Table | Grain | Source | Role |
|---|---|---|---|
| `operations_clean` | one row per operation (199,200) | `data/processed/operations_clean.csv` | fact table + all measures |
| `Calendar` | one row per day | DAX `CALENDAR` | date dimension |
| `dq_rule_results` | one row per DQ rule (19) | `reports/data_quality/dq_rule_results.csv` | DQ page |
| `dq_run_summary` | one row per DQ metric (10) | `reports/data_quality/dq_run_summary.csv` | DQ page |

Relationships: `operations_clean[received_date]` -> `Calendar[Date]` (active, many-to-one, single direction); `operations_clean[completed_date]` -> `Calendar[Date]` (inactive; used only by `Operations Completed (by Completion Date)` through `USERELATIONSHIP`). The DQ tables are deliberately standalone; they describe the pipeline, not the operations.

Columns added in Power Query: `completed_date`, `priority_rank`, `age_days` (days to the latest received date, not today), `age_band`, `intake_completeness`, `exception_status`, `rework_status`, `workload_band` and sort helpers. Eight raw columns not needed for reporting (customer/account/plan ids, completed_at, year/month/week/day text) are removed to keep the model small.

Why one wide fact table: the source is a single event-style table with low-cardinality attributes; a snowflake would add joins without analytical value. The SQL layer shows the alternative: `fact_operations` plus `dim_operation_type` and `dim_priority` (`sql/schema.sql`).

## SQL schema (`sql/schema.sql`)
`fact_operations` (columns in the exact order of the clean CSV so it loads with a plain `COPY`), `dim_operation_type`, `dim_priority`, `dq_rejected_records`, `dq_rule_results`. The original schema omitted `received_date` and could not load the CSV; fixed.

## Parameter
`ProjectRoot` is the only setting to change (see `docs/POWERBI_GUIDE.md`). The previous version hard-coded a personal Windows path; that was removed.
