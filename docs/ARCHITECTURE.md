# Architecture

```
data_generation.py --> data/raw/operations_raw.csv (200,600 rows incl. deliberate defects)
        |
   etl.py + dq.py --> data/processed/operations_clean.csv (199,200)   --> sql/ (DuckDB or PostgreSQL)
        |                data/rejected/operations_rejected.csv (1,400)    --> src/roip/kpis.py (KPI single source of truth)
        |                reports/data_quality/*  (rules, issue log, before/after, run summary)
        v
 analysis.py / run_eda.py --> reports/figures, reports/insights
 modeling.py / train_model.py --> reports/model
        v
 powerbi/ROIP_PowerBI_Project (PBIP: 5 pages, reads the processed CSV and the DQ CSVs)
```

| Layer | Files | Responsibility |
|---|---|---|
| Config | `src/roip/config.py`, `.env.example` | paths, seed, row count, business constants (SLA policy, valid categories); env overrides; no secrets needed |
| Generation | `data_generation.py` (unchanged from the original project) | reproducible synthetic data |
| ETL / DQ | `etl.py`, `dq.py` | rules, repairs, rejected-record file, DQ reports, logging, row accounting |
| KPIs | `kpis.py` | the one place KPI logic lives in Python; `KPI_DEFINITIONS` also documents the SQL and DAX equivalents |
| Analysis | `analysis.py`, `scripts/run_eda.py` | drivers, effect sizes, backlog age, run-off, segments, figures |
| ML | `modeling.py` | staged features, leakage guard, temporal split, baselines |
| SQL | `sql/schema.sql`, `sql/queries/*.sql`, `src/roip/sqlrun.py` | 19 documented queries; executed by DuckDB in tests |
| BI | `powerbi/generator/*.py` generate the PBIP; `scripts/validate_powerbi.py` checks it | the PBIP is text (TMDL + PBIR) so it is reviewable in Git |

Reproduce everything: `make all` (or the four commands in the README). The pipeline is deterministic: `test_etl_is_deterministic` checks byte-identical output.
