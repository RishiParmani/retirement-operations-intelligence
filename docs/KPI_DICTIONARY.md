# KPI Dictionary

One definition per KPI, implemented identically in Python (`src/roip/kpis.py`), SQL (`sql/queries/`) and DAX (`powerbi/.../operations_clean.tmdl`). `tests/test_sql_python_reconciliation.py` proves SQL = Python on the full data; `tests/test_powerbi_project.py` checks the DAX mirrors the Python logic. DAX itself can only be executed in Power BI Desktop.

**Population rules** - the reason three tools can disagree if you are careless:
- Volume, exception and rework measures use **all** operations.
- SLA and processing-time measures use **Completed** operations only. Pending/Failed/Escalated items never finished, so a processing time on them is not a real duration (rule F08 flags 9,627 such rows).
- SLA breach = `status = Completed AND processing_hours > sla_target_hours`.
- Open Backlog = Pending + Escalated (Failed is closed, not backlog).
- Backlog age is measured against the latest `received_at` in the data, not today's date, so results are reproducible.

| KPI | Population | Logic | Python | SQL | DAX | Business meaning |
|---|---|---|---|---|---|---|
| Total Operations | All | count of rows (operation_id is unique) | `len(df)` | `COUNT(*)` | `COUNTROWS(operations_clean)` | Workload received in the period. |
| Completed Operations | All | status = 'Completed' | `(df.status=='Completed').sum()` | `COUNT(*) FILTER (WHERE status='Completed')` | `CALCULATE([Total Operations], status = "Completed")` | Throughput. |
| Pending Operations | All | status = 'Pending' | `(df.status=='Pending').sum()` | `COUNT(*) FILTER (WHERE status='Pending')` | `CALCULATE([Total Operations], status = "Pending")` | Work in progress / queued. |
| Failed Operations | All | status = 'Failed' | `(df.status=='Failed').sum()` | `COUNT(*) FILTER (WHERE status='Failed')` | `CALCULATE([Total Operations], status = "Failed")` | Operations that could not be completed. |
| Escalated Operations | All | status = 'Escalated' | `(df.status=='Escalated').sum()` | `COUNT(*) FILTER (WHERE status='Escalated')` | `CALCULATE([Total Operations], status = "Escalated")` | Cases handed to a senior team; all carry an exception. |
| Open Backlog | All | status in ('Pending','Escalated') (unresolved, still owned) | `df.status.isin(['Pending','Escalated']).sum()` | `COUNT(*) FILTER (WHERE status IN ('Pending','Escalated'))` | `[Pending Operations] + [Escalated Operations]` | Work still waiting to be finished. Failed items are closed, not backlog. |
| Completion Rate % | All | Completed / Total | `completed/total` | `100.0*COUNT(*) FILTER (WHERE status='Completed')/COUNT(*)` | `DIVIDE([Completed Operations],[Total Operations])` | Share of received work that finished. |
| Average Processing Hours | Completed | mean(processing_hours) where Completed; processing_hours = completed_at - received_at (cycle time) | `completed.processing_hours.mean()` | `AVG(processing_hours) FILTER (WHERE status='Completed')` | `CALCULATE(AVERAGE(processing_hours), status = "Completed")` | Typical end-to-end cycle time (mean is pulled up by a long tail). |
| Median Processing Hours | Completed | median(processing_hours) where Completed | `completed.processing_hours.median()` | `percentile_cont(0.5) WITHIN GROUP (ORDER BY processing_hours)` | `CALCULATE(MEDIAN(processing_hours), status = "Completed")` | Typical case, robust to the long tail. |
| SLA Breach Count | Completed | Completed AND processing_hours > sla_target_hours | `completed.sla_breached.sum()` | `SUM(sla_breached) FILTER (WHERE status='Completed')` | `CALCULATE(SUM(sla_breached), status = "Completed")` | Service failures. |
| SLA Breach Rate % | Completed | breaches / Completed | `completed.sla_breached.mean()` | `100.0*AVG(sla_breached) FILTER (WHERE status='Completed')` | `DIVIDE([SLA Breach Count],[Completed Operations])` | Probability a finished case missed its SLA. |
| SLA Compliance % | Completed | 1 - SLA Breach Rate | `1-breach_rate` | `100 - breach rate` | `DIVIDE([Completed Operations]-[SLA Breach Count],[Completed Operations])` | Headline service level. (The first Power BI draft divided by ALL rows and showed 74.58% instead of 73.29%.) |
| Exception Rate % | All | exception_flag = TRUE / Total | `df.exception_flag.mean()` | `100.0*AVG(exception_flag::int)` | `DIVIDE([Exception Count],[Total Operations])` | Share of work that hit a problem needing intervention. |
| Rework Rate % | All | rework_flag = TRUE / Total | `df.rework_flag.mean()` | `100.0*AVG(rework_flag::int)` | `DIVIDE([Rework Count],[Total Operations])` | Share of work that had to be redone. |
| Total Transaction Amount | All | sum(transaction_amount) (USD, synthetic; non-financial operation types are 0) | `df.transaction_amount.sum()` | `SUM(transaction_amount)` | `SUM(transaction_amount)` | Value of money-movement work handled. |

## v3 additions in Power BI only

- `Average Processing Hours` and `Average SLA Target Hours` are now `ROUND(DIVIDE(SUM over Completed, Completed Operations), 2)` instead of `AVERAGE(column)`; same number, see `docs/POWERBI_GUIDE.md` for why.
- `Open Backlog`, `Stale Pending (over 90 days)`, `Share of SLA Breaches`, `DQ *` (read from `dq_run_summary.csv`) and `Diag *` reconciliation measures.
