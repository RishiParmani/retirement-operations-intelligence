# ROIP Power BI project (PBIP)

Source-controlled Power BI Project (TMDL semantic model + PBIR report). It was generated programmatically and checked against Microsoft's published JSON schemas. **It has not been opened in Power BI Desktop** (not available where it was built), so first-open issues are possible.

## Open it
1. Enable PBIP support if needed: Power BI Desktop > Options > Preview features > *Power BI Project (.pbip) save option* and *Store semantic model using TMDL format*.
2. Double-click `ROIP_Operations_Intelligence.pbip`.
3. Home > Transform data > Edit parameters: set `DataFolderPath` to the folder holding `operations_clean.csv` (default is the path from your original file: `C:\Users\Rishi Parmani\Downloads\ROIP_Full_Project\ROIP\data\processed`). Refresh.
4. Compare the cards with `docs/VALIDATION_REPORT.md`. Expected overall: 199,200 total; 189,573 completed; 7,008 pending; 2,353 failed; SLA compliance 73.3%; avg hours 37.3; exceptions 10.3%; rework 6.6%.
5. File > Save as .pbix if you want a single file to share.

## Contents
- `ROIP_Operations_Intelligence.SemanticModel/` : tables, 24 measures, relationships, Power Query (TMDL)
- `ROIP_Operations_Intelligence.Report/` : 3 pages, 76 visual definitions, custom theme (PBIR)
- `docs/` : DAX, data model, layout, validation, theme
