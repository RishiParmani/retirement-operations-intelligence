# Power BI Guide

Open `powerbi/ROIP_PowerBI_Project/ROIP_Operations_Intelligence.pbip` in Power BI Desktop (PBIP/TMDL support: current Desktop with "Power BI Project" format enabled).

## First open
1. Run `python scripts/run_pipeline.py` so `data/processed/` and `reports/data_quality/` exist.
2. Home > Transform data > Manage parameters > set **ProjectRoot** to your repository folder, e.g. `C:\Users\you\ROIP`. Nothing else is hard-coded.
3. Refresh. Expected totals: Total Operations 199,200; Completed 189,573; SLA compliance 73.3%; Average processing hours 37.3 (these come from `reports/kpi_summary.json`, not from the dashboard).

## Pages
1. Executive Operations Overview. 2. Operational Performance Analysis. 3. SLA & Operational Risk Analysis (all three preserved from v2). 4. **Root Cause & Drivers** (new: breach rate by intake completeness, exception status, workload band, priority; backlog age). 5. **Data Quality & Pipeline** (new: raw/loaded/rejected, rule table, measure reconciliation).

## January 2026 in "Received vs completed"
No operations were received after 31 Dec 2025; 796 operations received in December were *completed* in January. The completion line therefore has a small January value while receipts are zero. It is correct and stays visible; the chart carries the subtitle "Jan 2026: run-off of Dec 2025 receipts only (no receipts after 31 Dec 2025)". To exclude partial periods, use the date slicer.

## Blank KPI cards: what is known
- **Symptom (reported):** `Average Processing Hours` blank on pages 1-2; `Average SLA Target Hours` blank on page 2.
- **Not reproduced.** Desktop is not available here, so the real cause is **unconfirmed**. Both measures were `CALCULATE(AVERAGE(column), status = "Completed")` with a one-decimal format; the measures built from `COUNTROWS`/`SUM` rendered fine.
- **Changes made (unverified in Desktop):** both measures are now `ROUND(DIVIDE(SUM over Completed, Completed Operations), 2)` with explicit format `0.0`, using only patterns that already worked; card display units fixed to "None"; decimals set per measure.
- **Built-in diagnosis:** the Data Quality page shows `Diag - Row Count`, `Diag - Completed Rows With Hours` and `Diag - Sum Processing Hours` beside the averages. If an average is still blank, these tell you immediately whether `processing_hours` loaded as numbers (blank sum = column typed as text, usually a wrong `ProjectRoot` or an old CSV) or whether the card itself is the problem (diagnostics show values but the card is blank -> open the card's Format pane and check display units / precision; send me the result).

## Card clipping
Cause (v2): 82 px cards were stacking title + 24 pt value + category label. Fix: category label off, value 22 pt, title in the container header, display units None. Visual check in Desktop is still needed.

## Verification status
| Item | Status |
|---|---|
| JSON valid, matches Microsoft schemas (123 files), all visual fields exist in the model, visuals inside pages | Verified by `scripts/validate_powerbi.py` and tests |
| DAX logic = Python/SQL numbers | Verified by mirroring the logic in pandas; **DAX itself not executed** |
| Opens, refreshes, renders, cards not clipped/blank | **Needs Power BI Desktop** (v2 was reported working by you; v3 changes are untested) |
| New pages (4, 5), new Power Query columns, `ProjectRoot` parameter | **Needs Power BI Desktop** |

## Folder map
- `powerbi/ROIP_PowerBI_Project/` - **current v3 project** (open the `.pbip`).
- `powerbi/generator/` - scripts that generate it. `powerbi/archive/v2_project/` - previous working v2 (fallback; contains the old personal data path). `powerbi/original/` - your original PBIX. `powerbi/docs_v2/` - v2 docs.
- `data/` ships with the full raw, clean and rejected CSVs, so `ProjectRoot` is the only thing to set.
