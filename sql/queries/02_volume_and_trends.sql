-- 02 | VOLUME AND TRENDS (CTEs, FULL JOIN, LAG, running totals, moving averages)

-- name: Q05_monthly_received_vs_completed
-- Business question: are we completing as much as we receive? Completion is attributed to the month it HAPPENED,
-- so January 2026 shows the run-off of December 2025 receipts (there are no receipts after 31 Dec 2025).
WITH received AS (
    SELECT CAST(date_trunc('month', received_at) AS DATE) AS month, COUNT(*) AS received
    FROM fact_operations
    GROUP BY 1
), completed AS (
    SELECT CAST(date_trunc('month', completed_at) AS DATE) AS month, COUNT(*) AS completed
    FROM fact_operations
    WHERE status = 'Completed'
    GROUP BY 1
)
SELECT COALESCE(r.month, c.month)       AS month,
       COALESCE(r.received, 0)          AS received,
       COALESCE(c.completed, 0)         AS completed,
       COALESCE(c.completed, 0) - COALESCE(r.received, 0) AS net_flow
FROM received r
FULL OUTER JOIN completed c ON c.month = r.month
ORDER BY month;

-- name: Q06_monthly_volume_mom_and_running_total
-- Business question: how does monthly demand move, and what is the cumulative load? (LAG + running SUM)
WITH monthly AS (
    SELECT CAST(date_trunc('month', received_at) AS DATE) AS month, COUNT(*) AS operations
    FROM fact_operations
    GROUP BY 1
)
SELECT month,
       operations,
       LAG(operations) OVER (ORDER BY month)                                         AS prev_month,
       ROUND(CAST(100.0 * (operations - LAG(operations) OVER (ORDER BY month))
                  / LAG(operations) OVER (ORDER BY month) AS NUMERIC(14,4)), 2)      AS mom_change_pct,
       SUM(operations) OVER (ORDER BY month)                                         AS running_total
FROM monthly
ORDER BY month;

-- name: Q07_sla_breach_rate_3_month_moving_average
-- Business question: is SLA performance trending? A 3-month moving average smooths month-to-month noise.
WITH monthly AS (
    SELECT CAST(date_trunc('month', received_at) AS DATE) AS month,
           COUNT(*)                     AS completed,
           SUM(sla_breached)            AS breaches
    FROM fact_operations
    WHERE status = 'Completed'
    GROUP BY 1
)
SELECT month,
       completed,
       ROUND(CAST(100.0 * breaches / completed AS NUMERIC(14,4)), 2) AS breach_rate_pct,
       ROUND(CAST(100.0 * SUM(breaches)  OVER w / SUM(completed) OVER w AS NUMERIC(14,4)), 2) AS breach_rate_3m_pct
FROM monthly
WINDOW w AS (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
ORDER BY month;

-- name: Q08_weekday_demand_and_breach
-- Business question: does day of week change demand or service? (answer in this data: demand yes, breach no)
SELECT received_day_of_week                                   AS weekday,
       COUNT(*)                                               AS operations,
       ROUND(CAST(100.0 * AVG(sla_breached) FILTER (WHERE status = 'Completed') AS NUMERIC(14,4)), 2) AS sla_breach_rate_pct
FROM fact_operations
GROUP BY received_day_of_week
ORDER BY CASE received_day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
         WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END;
