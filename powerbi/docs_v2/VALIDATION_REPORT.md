# Validation report

Method: each measure's logic was recomputed in pandas from `operations_clean.csv` and compared with the project's own outputs (`reports/kpi_summary.json`, `reports/initial_results.md`).

**Important:** the DAX itself was not executed, because Power BI Desktop is not available in this environment. These checks confirm the definitions and the expected on-screen values. Compare the cards in Desktop against the table below.

| Metric | Definition | Computed from data | Project reference | Source | Result |
|---|---|---|---|---|---|
| Total Operations | COUNTROWS | 199,200.00 | 199,200.00 | kpi_summary.json | PASS |
| Completed Operations | status=Completed | 189,573.00 | 189,573.00 | kpi_summary.json | PASS |
| Pending Operations | status=Pending | 7,008.00 | 7,008.00 | kpi_summary.json | PASS |
| Failed Operations | status=Failed | 2,353.00 | 2,353.00 | kpi_summary.json | PASS |
| Escalated Operations | status=Escalated | 266.00 | 266.00 | status counts add to total | PASS |
| SLA Breach Count | SUM(sla_breached) over Completed | 50,638.00 | 50,638.00 | recomputed: processing_hours>sla_target_hours | PASS |
| SLA Compliance % | (Completed-Breaches)/Completed *100 | 73.29 | 73.29 | kpi_summary.json | PASS |
| Average Processing Hours | AVERAGE(processing_hours) over Completed | 37.34 | 37.34 | kpi_summary.json | PASS |
| Exception Rate % | exceptions/all *100 | 10.33 | 10.33 | kpi_summary.json | PASS |
| Rework Rate % | rework/all *100 | 6.63 | 6.63 | kpi_summary.json | PASS |
| Total Transaction Amount | SUM(transaction_amount) | 441,830,129.55 | 441,830,129.55 | kpi_summary.json | PASS |
| Row accounting | clean + rejected = raw | 200,600.00 | 200,600.00 | initial_results.md (raw 200,600) | PASS |
| Rejected rows | rejected csv | 1,400.00 | 1,400.00 | initial_results.md | PASS |
| Unique operation_id | nunique = rows | 199,200.00 | 199,200.00 | primary key check | PASS |
| Breach only on Completed | breaches among non-completed | 0.00 | 0.00 | ETL rule | PASS |
| Original PBIX "SLA Compliance %" | 1-SUM(breached)/ALL rows | 74.58 | 73.29 | kpi_summary.json | MISMATCH (fixed) |

## Findings in the original PBIX
1. **SLA Compliance % was wrong.** It computed `1 - SUM(sla_breached) / all rows` = 74.58%. Pending, Failed and Escalated operations can never breach, so they inflated compliance. The project definition (completed only) gives **73.29%**. Fixed.
2. **Average Processing Hours** averaged all statuses (37.40) instead of Completed (37.34, the project figure). Fixed.
3. `Exception Rate %` / `Rework Rate %` used `SUM()` on boolean columns; replaced with an explicit count measure (same values: 10.33% / 6.63%).
4. The five visuals were unformatted single-measure column charts with no category axis. All were replaced.
5. `Total Operations` used `COUNT(operation_id)`; now `COUNTROWS` (same result, as the key is unique and non-null).
6. The model had six auto date tables and no relationships. Replaced with one `Calendar` table and an explicit relationship.

## Data observations (as measured; synthetic data)
- Breach rate by priority is the one strong signal: Low 37.9%, Medium 29.6%, High 18.3%, Critical 10.5%.
- Breach rate by operation type, region, channel, team and month is nearly flat (about 26% to 27%), as are exception and rework rates. The dashboard shows this honestly and does not flag any region or channel as a risk on this basis.
- Largest number of breaches by type is Contribution Processing (8,168), a volume effect, not a rate effect.
- 796 completed operations finished in January 2026; the Calendar extends to cover them.
- 81,396 operations have a transaction amount of 0 (the four non-financial operation types plus some zero-value rows).
