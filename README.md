# Retirement Operations Intelligence Platform (ROIP)

**Enterprise analytics portfolio project** simulating retirement/financial operations to study operational performance, SLA risk, exceptions, rework, workload, data quality, and process improvement.

> All records are synthetic and generated for this project. No real customers, accounts, plans, or financial institution data are represented.

## Project goals
- Build a reproducible 200,000-row synthetic operational dataset.
- Practice data validation, ETL, cleaning, rejected-record handling, and data quality scoring.
- Analyze KPIs, team performance, operation bottlenecks, trends, exceptions, and rework.
- Use PostgreSQL and SQL analytics.
- Develop a machine-learning model to estimate SLA breach risk using only operationally available features.
- Create a Power BI executive and operations dashboard (dashboard build guide to follow).

## Quick start
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py
```
The pipeline creates raw and processed CSV files, rejection output, KPI JSON, and group-performance summaries.

## Architecture
Synthetic Generator → Raw CSV → Validation/ETL → Clean Processed Data → KPI/SQL Analytics → ML SLA Risk → Power BI.

## Dataset
The generator uses a fixed random seed and operation-type-specific SLA targets. It simulates operations such as contributions, withdrawals, fund transfers, rollovers, account maintenance, beneficiary updates, distributions, plan administration, and service requests. Deliberate quality issues include missing region values, invalid team categories, and duplicate operation IDs for pipeline validation practice.

## Structure
- `src/roip/data_generation.py` — synthetic data generator
- `src/roip/etl.py` — ETL, duplicate/category validation, rejected records
- `src/roip/analytics.py` — KPI and group analysis
- `src/roip/modeling.py` — SLA breach classifier (feature set excludes post-completion outcomes)
- `sql/schema.sql` — PostgreSQL table and indexes
- `sql/analytics.sql` — business analytics query examples
- `scripts/run_pipeline.py` — end-to-end generator and ETL runner
- `tests/` — automated tests

## Important modeling note
The current SLA label is a synthetic outcome. Model features deliberately omit final completion time and the target itself. For a production-style deployment, add time-based validation and verify each feature's availability at the prediction point.

## Business questions
1. Which operation types have the highest SLA breach rate?
2. Which teams have the greatest workload and bottlenecks?
3. What exception/root causes are associated with longer processing times?
4. How do volume and operational performance change over time?
5. Where could documentation, automation, or workload balancing improve operations?

## Next build milestones
1. Generate and inspect dataset.
2. Run ETL and quality checks.
3. Complete EDA and business analysis notebooks.
4. Load clean data into PostgreSQL.
5. Train/evaluate breach-risk and anomaly detection.
6. Design Power BI dashboard and business recommendations.
7. Add screenshots, documentation, and interview walkthrough.
