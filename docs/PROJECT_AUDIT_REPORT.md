# PROJECT AUDIT REPORT

Scope: audit, repair and upgrade of ROIP. "Verified" = executed here with the evidence shown. "Needs Desktop" = could not be checked without Power BI Desktop.

## Summary table
| Category | Status | Changes made | Validation |
|---|---|---|---|
| Python pipeline | Done | Config module (no hard-coded paths), logging, `etl.py`/`dq.py` split; `data_generation.py` untouched | Fresh copy regenerates a clean CSV byte-identical to the original project's output; determinism test |
| Data quality | Done | 8 reject / 2 fix / 9 flag rules, rejected-records file with reasons, issue log, before/after profile, DQ KPIs, row accounting assert | 200,600 = 199,200 + 1,400 asserted; 9 DQ tests incl. injected bad rows |
| KPI consistency | Done | Single `kpis.py` + dictionary; Python had averaged hours over all statuses vs SQL Completed-only: unified | SQL = Python on full data (tests); reference 73.29% / 37.34 h reproduced |
| SQL | Done | Original 7 basic queries replaced by 19 documented queries (CTEs, joins, subqueries, CASE, windows, Pareto, MoM, moving average); schema fixed (original lacked `received_date`, could not load the CSV) | All 19 run on DuckDB; headline/priority/monthly reconciliation tests. **PostgreSQL not run** |
| EDA & analysis | Done | 9 figures, 13 insight tables, effect-size ranking, excess-breach attribution, backlog age, Jan-2026 run-off | Regenerated from scratch; numbers cited in docs read from `headline.json` |
| ML | Done, limited value | Leakage by timing removed, temporal split, 3 feature stages, baselines, calibration, importance | Leakage guard + split tests; result: modest lift, stated plainly |
| Power BI: KPI blanks | **Unconfirmed root cause** | Averages rewritten as SUM/COUNT with explicit format; diagnostic reconciliation panel added | DAX logic mirrored in pandas. **Needs Desktop** |
| Power BI: card clipping/units | Changed in v2 and kept | No category label, 22 pt, display units None, per-measure precision | **Needs Desktop** |
| Power BI: Jan 2026 | Explained + annotated | Data unchanged; chart subtitle; documented | Counts verified (796 completions, 0 receipts) |
| Power BI: new content | Done | Page 4 Root Cause & Drivers; page 5 Data Quality & Pipeline; 45 measures; Power Query columns; `ProjectRoot` parameter replaces a personal absolute path | Schema (123 files) + reference checks pass; checker negative-tested. **Needs Desktop** to render |
| DAX | Done | Fixed original SLA Compliance denominator (all rows -> Completed: 74.58% -> 73.29%); display folders; descriptions | Logic mirrored; DAX not executed |
| Tests | Done | 28 pytest tests (was 1) | 28 passed, `reports/test_results.txt` |
| Reproducibility | Done | requirements trimmed to what is used (dropped psycopg2, sqlalchemy, dotenv, seaborn; added scipy, duckdb), Makefile, `.env.example` (no secrets), `.gitignore` | Fresh-copy run of all scripts + tests |
| Documentation | Done | README, 9 docs, SQL README, interview guide | No screenshots claimed; verification status stated |
| Interview prep | Done | 30 s / 1 min / 2 min scripts + 32 Q&A | Facts cross-checked against outputs; two wrong numbers caught and corrected while writing |

## Bugs found
1. Original PBIX/Power BI `SLA Compliance %` used all rows (74.58%) instead of Completed (73.29%).
2. Python vs SQL KPI population mismatch (processing hours).
3. `schema.sql` could not load the clean CSV (missing column).
4. Model features included exception/rework (not known at intake), random split, no baseline.
5. Hard-coded personal Windows path in the Power BI parameter.
6. Earlier doc error: zero amounts are exactly the four non-financial types, not "some financial rows".
7. Unused dependencies (psycopg2, sqlalchemy, dotenv, seaborn); `.gitignore` excluded `reports/*.json` so KPI results could not be versioned.
8. Blank Average Processing Hours / Average SLA Target cards and card clipping (see Power BI rows; cause of the blanks not found).

## Test results
`python -m pytest -q` -> **28 passed**. Also: `scripts/validate_powerbi.py --schemas <local copy of Microsoft schemas>` -> 123 JSON files valid; negative test (injected bad property and wrong type) correctly fails.

## Limitations
- Synthetic data; relationships are generator rules; `Pending` is random.
- Model ceiling low; no calibration fix, drift or deployment work.
- No business-day SLA calendar.

## Remaining tasks that need Power BI Desktop (not done here)
1. Open the `.pbip`, set `ProjectRoot`, refresh.
2. Check pages 1-2: Average Processing Hours (expect about 37.3) and Average SLA Target Hours show values. If blank, read the diagnostic panel on page 5 and report what it shows.
3. Check card clipping at 100% zoom on all five pages.
4. Check pages 4 and 5 render and slicers sync.
5. Take your own screenshots for the README.
