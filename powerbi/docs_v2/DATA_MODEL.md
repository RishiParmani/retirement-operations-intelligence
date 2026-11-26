# Data model

Single fact table plus a calendar. A larger star schema would add complexity with no analytic benefit here.

| Table | Role | Grain |
|---|---|---|
| `operations_clean` | Fact (Import, from `operations_clean.csv`) | one row per operation, 199,200 rows |
| `Calendar` | Date dimension (calculated, 1 Jan 2025 to 31 Jan 2026) | one row per day |

## Relationships
| From | To | Cardinality | State |
|---|---|---|---|
| `operations_clean[received_date]` | `Calendar[Date]` | many-to-one, single direction | active |
| `operations_clean[completed_date]` | `Calendar[Date]` | many-to-one, single direction | inactive (used by `USERELATIONSHIP`) |

## Changes to the source columns
- Removed from the model: `customer_id`, `account_id`, `plan_id`, `completed_at`, `received_year/month/week/day_of_week` (unused; the Calendar replaces them). Remove a drop from the Power Query step if you need them.
- Added in Power Query: `completed_date` (date of completed_at) and `priority_rank` (sort helper: Critical, High, Medium, Low).
- Hidden: timestamps and `priority_rank`.

## Columns
| Column | Type | Note |
|---|---|---|
| `operation_id` | string |  Unique operation identifier. |
| `operation_type` | string |   |
| `priority` | string |   |
| `channel` | string |   |
| `region` | string |   |
| `processing_team` | string |   |
| `team_workload` | int64 |   |
| `customer_segment` | string |   |
| `received_at` | dateTime | hidden  |
| `assigned_at` | dateTime | hidden  |
| `started_at` | dateTime | hidden  |
| `status` | string |   |
| `exception_flag` | boolean |   |
| `exception_type` | string |   |
| `exception_severity` | string |   |
| `root_cause` | string |   |
| `rework_flag` | boolean |   |
| `sla_target_hours` | int64 |   |
| `processing_hours` | double |   |
| `sla_breached` | int64 |   |
| `transaction_amount` | double |   |
| `currency` | string |   |
| `missing_info_flag` | boolean |   |
| `received_date` | dateTime |   |
| `data_quality_score` | int64 |   |
| `completed_date` | dateTime |  derived |
| `priority_rank` | int64 | hidden sort helper |
