-- Executive KPI overview
SELECT COUNT(*) AS total_operations,
       COUNT(*) FILTER (WHERE status='Completed') AS completed,
       COUNT(*) FILTER (WHERE status='Pending') AS pending,
       ROUND(100.0*AVG(sla_breached) FILTER (WHERE status='Completed'),2) AS breach_rate_pct,
       ROUND(AVG(processing_hours) FILTER (WHERE status='Completed'),2) AS avg_processing_hours,
       ROUND(100.0*AVG(exception_flag::int),2) AS exception_rate_pct,
       ROUND(100.0*AVG(rework_flag::int),2) AS rework_rate_pct
FROM fact_operations;

-- Monthly trend
SELECT received_year,received_month,COUNT(*) operations,
       ROUND(AVG(sla_breached)*100,2) breach_rate_pct,
       ROUND(AVG(processing_hours),2) avg_processing_hours
FROM fact_operations GROUP BY received_year,received_month ORDER BY received_year,received_month;

-- Team performance and workload
SELECT processing_team,COUNT(*) operations,ROUND(AVG(team_workload),1) avg_workload,
       ROUND(AVG(processing_hours),2) avg_hours,ROUND(AVG(sla_breached)*100,2) breach_pct,
       ROUND(AVG(exception_flag::int)*100,2) exception_pct
FROM fact_operations GROUP BY processing_team ORDER BY breach_pct DESC;

-- Bottleneck operations
SELECT operation_type,COUNT(*) volume,ROUND(AVG(processing_hours),2) avg_hours,
       ROUND(AVG(sla_breached)*100,2) breach_pct,ROUND(AVG(rework_flag::int)*100,2) rework_pct
FROM fact_operations GROUP BY operation_type ORDER BY breach_pct DESC;

-- Exception root causes
SELECT root_cause,exception_type,COUNT(*) cases,ROUND(AVG(processing_hours),2) avg_hours
FROM fact_operations WHERE exception_flag GROUP BY root_cause,exception_type ORDER BY cases DESC;

-- Backlog aging (completed_at missing)
SELECT status,COUNT(*) backlog_count FROM fact_operations WHERE completed_at IS NULL GROUP BY status;

-- Ranking teams by SLA breach rate
SELECT processing_team,AVG(sla_breached) breach_rate,
       RANK() OVER(ORDER BY AVG(sla_breached) DESC) breach_rank
FROM fact_operations GROUP BY processing_team;
