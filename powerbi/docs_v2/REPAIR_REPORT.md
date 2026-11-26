# Repair report (v2)

Scope: targeted fixes to the working v1 project. Same pages, same visual IDs, same semantic model. A copy of v1 is included in `_backup_v1/`.

**Not tested in Power BI Desktop.** The checks below are file-level (schemas, references, IDs). I could not see your screenshots, so each cause below is derived from the visual definitions, and the clipping fix still needs your visual confirmation.

## 1. KPI clipping
**Cause (from the definitions):** all 23 cards were 82 px high but stacked three things: the container title, a 24 pt value, and a second "category label" (the measure name Power BI prints under the value, which duplicated the title). Together with the default card padding that is more than 82 px, so the value was cut off.

**Fix:** turned the duplicate category label off, reduced the value to 22 pt, and set decimals and display units explicitly per card (1 decimal for rates and hours, whole numbers for counts, no auto units). Card heights, positions, colours and fonts are otherwise unchanged and still consistent. Header title/subtitle text boxes were also enlarged slightly (title 34 to 40 px, subtitle 26 to 24 px but moved down) to avoid the same clipping, and the page 3 subtitle was shortened so it cannot wrap under the navigator.

## 2. Average Processing Hours card blank
**What I checked:**
- The measure: `CALCULATE(AVERAGE(operations_clean[processing_hours]), operations_clean[status] = "Completed")`. Correct. The column has 0 nulls; the data gives 37.3425 for completed operations, matching the 37.34 reference.
- The card's JSON compared with the Total Operations card: identical except position and label. It references the right measure, and has no visual-level filter.
- It uses the same pattern as the SLA measures, and the same measure already renders in the four bar charts.

**Result: I found no defect in the measure or the card binding, so I cannot name a confirmed root cause.** I did not hardcode a value or add a replacement measure. The measure is unchanged. What I changed is the card layout (see 1), which is the one factor that differs from the file's side. If the card is still blank in Desktop, please tell me what it shows when you drag the same measure into a Table visual, and what Power BI says in the visual's error/warning icon, if any.

## 3. January 2026 drop
**Cause: genuine data-window effect, not a calculation or date-model error.** The dataset contains operations received 1 Jan to 31 Dec 2025 and none after that. "Completed" is plotted on the completion date, so January 2026 can only contain the tail of December receipts finishing late.

| Month | Received | Completed (by completion date) |
|---|---|---|
| Dec 2025 | 17,053 | 16,205 |
| Jan 2026 | 0 | 796 |

All 796 January 2026 completions were received in December 2025 (796 of the 16,253 completed Dec receipts). The latest completion is 15 Jan 2026. The Calendar table correctly extends to 31 Jan 2026, the inactive completed-date relationship works as designed, and the received series is blank for January simply because nothing was received.

**Action:** kept January 2026 and the chart unchanged, and added a subtitle on the chart: "Jan 2026: run-off of Dec 2025 receipts only (no receipts after 31 Dec 2025)". The completed series is also below the received series every month because Pending, Failed and Escalated operations (9,627 in total) are never completed.

## 4. Other changes
- Header text boxes enlarged and the long page 3 subtitle shortened (above).
- Nothing else changed: 30 visual files differ from v1 (23 cards, 6 header text boxes, 1 chart). The semantic model, relationships, slicers, theme and all other visuals are byte-identical.

## 5. Validation performed
- Schema checks: 76 visuals, report, pages, pages list and version file, all against Microsoft's published schemas (0 errors).
- 109 visual field references resolved to existing measures and columns; no unresolved measure references in the 24 DAX measures.
- 76 unique visual IDs; 3 pages exist and are ordered; 2 relationships; 5 slicer sync groups across all 3 pages plus the page 2 status slicer.
- Data recomputed from `operations_clean.csv`: total 199,200 (raw 200,600, rejected 1,400), completed 189,573, pending 7,008, failed 2,353, SLA compliance 73.29%, average processing hours 37.34, exception rate 10.33%, rework rate 6.63%, transaction amount $441,830,129.55. All match the reference figures (see `VALIDATION_REPORT.md`).

## 6. Unresolved or unverified
- Blank Average Processing Hours card: cause not identified (section 2).
- Visual confirmation of the clipping fix and the header text in Desktop.
- DAX was not executed here; compare card values with the validation report.
- If you saved changes in Desktop after opening v1, those are not in this package. Apply v2 to a copy, or tell me what you changed.
