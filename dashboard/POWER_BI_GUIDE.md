# Power BI Dashboard Build Guide

## Page 1 — Executive Overview
- Cards: Total Operations, Completed, Open Backlog, SLA Compliance, Average Processing Hours, Exception Rate, Rework Rate.
- Line chart: Operations and SLA breach rate over Received Date.
- Bar chart: Operation volume by type.
- Slicers: Date, operation type, team, region, priority, status.

## Page 2 — Operations Performance
- Matrix: Team × operation type with volume, average processing time, SLA breach rate, exception rate.
- Bar chart: SLA breach rate by team.
- Column chart: Average processing hours by operation type.
- Backlog aging: create age bands from received date for incomplete records (0–1 day, 2–3 days, 4–7 days, 8+ days).
- Exception trend and rework trend.

## Page 3 — Process Improvement
- Pareto-style root cause chart for exceptions.
- Scatter plot: team workload vs average processing hours.
- Table of operation types with high volume + high breach rate.
- Highlight high-risk teams and operation types.
- Include a text box with recommendations based on actual findings.

## Suggested DAX measures
```DAX
Total Operations = COUNTROWS(Operations)
Completed Operations = CALCULATE([Total Operations], Operations[status] = "Completed")
Open Backlog = CALCULATE([Total Operations], Operations[completed_at] = BLANK())
SLA Breach Rate = DIVIDE(SUM(Operations[sla_breached]), [Completed Operations])
SLA Compliance = 1 - [SLA Breach Rate]
Average Processing Hours = AVERAGE(Operations[processing_hours])
Exception Rate = DIVIDE(CALCULATE([Total Operations], Operations[exception_flag] = TRUE()), [Total Operations])
Rework Rate = DIVIDE(CALCULATE([Total Operations], Operations[rework_flag] = TRUE()), [Total Operations])
```
Format SLA compliance/breach, exception, rework measures as percentages. Use a date table and relationship to received date for time analysis.
