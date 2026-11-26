-- 01 | KPI OVERVIEW
-- Population rules: volume, exception and rework use ALL operations; SLA and processing time use COMPLETED only.

-- name: Q01_headline_kpis
-- Business question: how is the operation performing overall? (matches reports/kpi_summary.json and the Power BI cards)
SELECT COUNT(*)                                                             AS total_operations,
       COUNT(*) FILTER (WHERE status = 'Completed')                         AS completed_operations,
       COUNT(*) FILTER (WHERE status = 'Pending')                           AS pending_operations,
       COUNT(*) FILTER (WHERE status = 'Failed')                            AS failed_operations,
       COUNT(*) FILTER (WHERE status = 'Escalated')                         AS escalated_operations,
       COUNT(*) FILTER (WHERE status IN ('Pending', 'Escalated'))           AS open_backlog,
       SUM(sla_breached) FILTER (WHERE status = 'Completed')                AS sla_breach_count,
       ROUND(CAST(100.0 * (1 - AVG(sla_breached) FILTER (WHERE status = 'Completed')) AS NUMERIC(14,4)), 2) AS sla_compliance_pct,
       ROUND(CAST(AVG(processing_hours) FILTER (WHERE status = 'Completed') AS NUMERIC(14,4)), 2)  AS avg_processing_hours,
       ROUND(CAST(percentile_cont(0.5) WITHIN GROUP (ORDER BY processing_hours) FILTER (WHERE status = 'Completed') AS NUMERIC(14,4)), 2) AS median_processing_hours,
       SUM(CAST(exception_flag AS INTEGER))                                 AS exception_count,
       ROUND(CAST(100.0 * AVG(CAST(exception_flag AS INTEGER)) AS NUMERIC(14,4)), 2) AS exception_rate_pct,
       SUM(CAST(rework_flag AS INTEGER))                                    AS rework_count,
       ROUND(CAST(100.0 * AVG(CAST(rework_flag AS INTEGER)) AS NUMERIC(14,4)), 2)    AS rework_rate_pct,
       ROUND(CAST(SUM(transaction_amount) AS NUMERIC(18,2)), 2)             AS total_transaction_amount
FROM fact_operations;

-- name: Q02_status_distribution
-- Business question: what share of work sits in each status? (window function for the percentage of total)
SELECT status,
       COUNT(*)                                                     AS operations,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC(14,4)), 2) AS pct_of_total
FROM fact_operations
GROUP BY status
ORDER BY operations DESC;

-- name: Q03_kpis_by_priority
-- Business question: does service differ by priority? HAVING keeps only groups large enough to trust.
SELECT f.priority,
       COUNT(*) FILTER (WHERE f.status = 'Completed')                                       AS completed,
       ROUND(CAST(100.0 * AVG(f.sla_breached) FILTER (WHERE f.status = 'Completed') AS NUMERIC(14,4)), 2) AS sla_breach_rate_pct,
       ROUND(CAST(AVG(f.processing_hours) FILTER (WHERE f.status = 'Completed') AS NUMERIC(14,4)), 2)     AS avg_processing_hours,
       ROUND(CAST(100.0 * AVG(CAST(f.exception_flag AS INTEGER)) AS NUMERIC(14,4)), 2)                  AS exception_rate_pct
FROM fact_operations f
JOIN dim_priority p ON p.priority = f.priority
GROUP BY f.priority, p.priority_rank
HAVING COUNT(*) FILTER (WHERE f.status = 'Completed') >= 1000
ORDER BY p.priority_rank;

-- name: Q04_kpis_by_operation_type_with_policy
-- Business question: which operation types are slow, judged against their own SLA policy (JOIN to the dimension)?
SELECT f.operation_type,
       d.sla_target_hours,
       d.is_financial,
       COUNT(*) FILTER (WHERE f.status = 'Completed')                                        AS completed,
       ROUND(CAST(AVG(f.processing_hours) FILTER (WHERE f.status = 'Completed') AS NUMERIC(14,4)), 2)     AS avg_processing_hours,
       ROUND(CAST(AVG(f.processing_hours) FILTER (WHERE f.status = 'Completed') / d.sla_target_hours AS NUMERIC(14,4)), 3) AS avg_hours_vs_target,
       ROUND(CAST(100.0 * AVG(f.sla_breached) FILTER (WHERE f.status = 'Completed') AS NUMERIC(14,4)), 2) AS sla_breach_rate_pct
FROM fact_operations f
JOIN dim_operation_type d ON d.operation_type = f.operation_type
GROUP BY f.operation_type, d.sla_target_hours, d.is_financial
ORDER BY d.sla_target_hours, f.operation_type;
