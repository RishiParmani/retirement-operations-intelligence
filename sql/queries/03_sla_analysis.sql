-- 03 | SLA ANALYSIS (where do breaches come from, and why?)

-- name: Q09_breach_pareto_by_priority
-- Business question: which priority tiers generate most breaches? (share + cumulative share = Pareto)
WITH p AS (
    SELECT f.priority, d.priority_rank,
           COUNT(*)           AS completed,
           SUM(f.sla_breached) AS breaches
    FROM fact_operations f
    JOIN dim_priority d ON d.priority = f.priority
    WHERE f.status = 'Completed'
    GROUP BY f.priority, d.priority_rank
)
SELECT priority,
       completed,
       breaches,
       ROUND(CAST(100.0 * breaches / completed AS NUMERIC(14,4)), 2)                                  AS breach_rate_pct,
       ROUND(CAST(100.0 * breaches / SUM(breaches) OVER () AS NUMERIC(14,4)), 2)                      AS share_of_breaches_pct,
       ROUND(CAST(100.0 * SUM(breaches) OVER (ORDER BY breaches DESC) / SUM(breaches) OVER () AS NUMERIC(14,4)), 2) AS cumulative_share_pct
FROM p
ORDER BY breaches DESC;

-- name: Q10_sla_driver_scan
-- Business question: which factors change the breach rate? One row per factor level, with lift vs the overall rate.
-- CASE builds comparable levels; the scalar subquery supplies the overall baseline.
WITH completed AS (
    SELECT sla_breached, processing_hours,
           CASE WHEN missing_info_flag THEN 'Information missing' ELSE 'Information complete' END AS intake_completeness,
           CASE WHEN exception_flag    THEN 'Exception raised'    ELSE 'No exception'          END AS exception_status,
           CASE WHEN rework_flag       THEN 'Reworked'            ELSE 'No rework'              END AS rework_status,
           CASE WHEN team_workload < 55 THEN '35-54' WHEN team_workload < 75 THEN '55-74'
                WHEN team_workload < 95 THEN '75-94' ELSE '95+' END                                AS workload_band,
           priority, region, channel, operation_type
    FROM fact_operations
    WHERE status = 'Completed'
), levels AS (
              SELECT 'intake_completeness' AS factor, intake_completeness AS level, sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'exception_status', exception_status, sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'rework_status',    rework_status,    sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'workload_band',    workload_band,    sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'priority',         priority,         sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'region',           region,           sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'channel',          channel,          sla_breached, processing_hours FROM completed
    UNION ALL SELECT 'operation_type',   operation_type,   sla_breached, processing_hours FROM completed
)
SELECT factor, level,
       COUNT(*)                                                                           AS completed,
       ROUND(CAST(100.0 * AVG(sla_breached) AS NUMERIC(14,4)), 2)                         AS breach_rate_pct,
       ROUND(CAST(AVG(sla_breached) / (SELECT AVG(sla_breached) FROM completed) AS NUMERIC(14,4)), 2) AS lift_vs_overall,
       ROUND(CAST(AVG(processing_hours) AS NUMERIC(14,4)), 2)                             AS avg_processing_hours
FROM levels
GROUP BY factor, level
ORDER BY factor, breach_rate_pct DESC;

-- name: Q11_high_risk_segments
-- Business question: which combinations are the riskiest and big enough to matter? (HAVING + RANK)
WITH seg AS (
    SELECT priority,
           CASE WHEN missing_info_flag THEN 'Information missing' ELSE 'Information complete' END AS intake_completeness,
           CASE WHEN exception_flag    THEN 'Exception raised'    ELSE 'No exception'          END AS exception_status,
           COUNT(*)            AS completed,
           SUM(sla_breached)   AS breaches
    FROM fact_operations
    WHERE status = 'Completed'
    GROUP BY 1, 2, 3
    HAVING COUNT(*) >= 500
)
SELECT RANK() OVER (ORDER BY 100.0 * breaches / completed DESC) AS risk_rank,
       priority, intake_completeness, exception_status, completed, breaches,
       ROUND(CAST(100.0 * breaches / completed AS NUMERIC(14,4)), 2) AS breach_rate_pct
FROM seg
ORDER BY risk_rank
LIMIT 10;

-- name: Q12_slowest_operation_type_within_each_priority
-- Business question: inside each priority tier, which operation types take longest in absolute hours? (RANK per partition)
WITH t AS (
    SELECT priority, operation_type, AVG(processing_hours) AS avg_hours
    FROM fact_operations
    WHERE status = 'Completed'
    GROUP BY priority, operation_type
), ranked AS (
    SELECT priority, operation_type, avg_hours,
           RANK() OVER (PARTITION BY priority ORDER BY avg_hours DESC) AS slowest_rank
    FROM t
)
SELECT priority, operation_type,
       ROUND(CAST(avg_hours AS NUMERIC(14,4)), 2) AS avg_processing_hours,
       slowest_rank
FROM ranked
WHERE slowest_rank <= 2
ORDER BY priority, slowest_rank;
