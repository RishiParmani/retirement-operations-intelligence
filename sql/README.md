# SQL

- `schema.sql` tables; `00_load_and_build.sql` builds the small dimensions.
- `queries/01-04_*.sql`: 19 named queries (`-- name: Qxx_...` with the business question above each). Features used: SELECT/WHERE/GROUP BY/HAVING, INNER and FULL OUTER joins, CROSS JOIN, CTEs, scalar subqueries, CASE, FILTER aggregates, UNION ALL, RANK/ROW_NUMBER/LAG, running totals, moving average, Pareto cumulative shares, ratio-to-total.
- Syntax is PostgreSQL-compatible; the only DuckDB-specific call is `DATE_DIFF('day', ...)` in Q16 (PostgreSQL: `(a::date - b::date)`).

Run without a server: `python scripts/run_sql.py` (DuckDB, results in `reports/sql_results/`). `tests/test_sql_python_reconciliation.py` checks SQL totals equal the Python KPIs.

PostgreSQL: create a database, run `schema.sql`, `\copy fact_operations FROM 'data/processed/operations_clean.csv' CSV HEADER`, `\copy dq_rejected_records FROM 'reports/data_quality/dq_rejected_records.csv' CSV HEADER`, then `00_load_and_build.sql`. Use your own `DATABASE_URL` (never commit it). The PostgreSQL path itself is **not tested here**; only DuckDB is.
