-- 04 | DATA QUALITY AND BACKLOG

-- name: Q13_rejected_records_by_rule
-- Business question: what did the pipeline refuse to load, and why? (nothing is silently dropped)
SELECT rejection_rule, rejection_reason, COUNT(*) AS records,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC(14,4)), 2) AS pct_of_rejected
FROM dq_rejected_records
GROUP BY rejection_rule, rejection_reason
ORDER BY records DESC;

-- name: Q14_row_reconciliation
-- Business question: do loaded + rejected records equal the raw extract? (raw count comes from the DQ rule table's source file)
SELECT (SELECT COUNT(*) FROM fact_operations)       AS loaded_records,
       (SELECT COUNT(*) FROM dq_rejected_records)   AS rejected_records,
       (SELECT COUNT(*) FROM fact_operations) + (SELECT COUNT(*) FROM dq_rejected_records) AS raw_records;

-- name: Q15_data_quality_score_by_team
-- Business question: do some teams hand us lower-quality records? (HAVING on a sensible minimum group size)
SELECT processing_team,
       COUNT(*)                                                    AS operations,
       ROUND(CAST(AVG(data_quality_score) AS NUMERIC(14,4)), 2)    AS mean_dq_score,
       COUNT(*) FILTER (WHERE region = 'Unknown')                  AS unknown_region
FROM fact_operations
GROUP BY processing_team
HAVING COUNT(*) > 100
ORDER BY mean_dq_score;

-- name: Q16_open_backlog_age_buckets
-- Business question: how old is the open backlog? Age is measured against the latest received_at in the data
-- (NOT today's date), so the result is reproducible. Pending older than 90 days is flagged as stale (config.STALE_PENDING_DAYS).
WITH latest AS (SELECT MAX(received_at) AS as_of FROM fact_operations),
backlog AS (
    SELECT f.status, DATE_DIFF('day', f.received_at, a.as_of) AS age_days
    FROM fact_operations f CROSS JOIN latest a
    WHERE f.status IN ('Pending', 'Escalated')
)
SELECT status,
       CASE WHEN age_days <= 30 THEN '0-30 days' WHEN age_days <= 90 THEN '31-90 days'
            WHEN age_days <= 180 THEN '91-180 days' ELSE '181+ days' END AS age_bucket,
       COUNT(*) AS operations
FROM backlog
GROUP BY 1, 2
ORDER BY status, MIN(age_days);

-- name: Q17_team_ranking_and_gap_to_best
-- Business question: how does each team rank on SLA compliance, and how far is it from the best team? (RANK + MAX window)
WITH t AS (
    SELECT processing_team,
           COUNT(*) AS completed,
           100.0 * (1 - AVG(sla_breached)) AS compliance_pct,
           AVG(processing_hours)           AS avg_hours
    FROM fact_operations WHERE status = 'Completed'
    GROUP BY processing_team
)
SELECT processing_team, completed,
       ROUND(CAST(compliance_pct AS NUMERIC(14,4)), 2) AS sla_compliance_pct,
       ROUND(CAST(avg_hours AS NUMERIC(14,4)), 2)      AS avg_processing_hours,
       RANK() OVER (ORDER BY compliance_pct DESC)       AS compliance_rank,
       ROUND(CAST(MAX(compliance_pct) OVER () - compliance_pct AS NUMERIC(14,4)), 2) AS gap_to_best_pts
FROM t
ORDER BY compliance_rank;

-- name: Q18_exception_root_causes_pareto
-- Business question: which root causes explain most exceptions? (subquery denominator + cumulative share)
SELECT root_cause, exceptions,
       ROUND(CAST(100.0 * exceptions / total AS NUMERIC(14,4)), 2) AS share_pct,
       ROUND(CAST(100.0 * SUM(exceptions) OVER (ORDER BY exceptions DESC) / total AS NUMERIC(14,4)), 2) AS cumulative_share_pct
FROM (
    SELECT root_cause, COUNT(*) AS exceptions,
           (SELECT COUNT(*) FROM fact_operations WHERE exception_flag) AS total
    FROM fact_operations
    WHERE exception_flag
    GROUP BY root_cause
) x
ORDER BY exceptions DESC;

-- name: Q19_largest_transactions_per_type
-- Business question: which are the largest financial operations per type, and did they breach SLA? (ROW_NUMBER)
SELECT * FROM (
    SELECT operation_type, operation_id, transaction_amount, status, sla_breached,
           ROW_NUMBER() OVER (PARTITION BY operation_type ORDER BY transaction_amount DESC) AS rn
    FROM fact_operations
    WHERE transaction_amount > 0
) x
WHERE rn <= 3
ORDER BY operation_type, rn;
