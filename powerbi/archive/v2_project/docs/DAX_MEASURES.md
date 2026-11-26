# DAX measures

All measures live on `operations_clean`. Rates use `DIVIDE`. Status-specific measures use `CALCULATE`, so they stay correct under any slicer.

## Total Operations
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** All operations in the current filter context (operation_id verified unique).

```dax
Total Operations =
COUNTROWS(operations_clean)
```

## Completed Operations
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** status = Completed.

```dax
Completed Operations =
CALCULATE([Total Operations], operations_clean[status] = "Completed")
```

## Pending Operations
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** status = Pending.

```dax
Pending Operations =
CALCULATE([Total Operations], operations_clean[status] = "Pending")
```

## Failed Operations
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** status = Failed.

```dax
Failed Operations =
CALCULATE([Total Operations], operations_clean[status] = "Failed")
```

## Escalated Operations
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** status = Escalated (exists in the data; absent from the original KPI list).

```dax
Escalated Operations =
CALCULATE([Total Operations], operations_clean[status] = "Escalated")
```

## Completion Rate %
- **Folder:** 1 Volume  
- **Format:** `0.0%`  
- **Meaning:** Completed / Total.

```dax
Completion Rate % =
DIVIDE([Completed Operations], [Total Operations])
```

## Operations Completed (by Completion Date)
- **Folder:** 1 Volume  
- **Format:** `#,0`  
- **Meaning:** Completed operations counted on their completion date via the inactive relationship to Calendar; feeds the received-vs-completed chart.

```dax
Operations Completed (by Completion Date) =
CALCULATE([Completed Operations], USERELATIONSHIP(operations_clean[completed_date], Calendar[Date]))
```

## Average Processing Hours
- **Folder:** 2 Processing  
- **Format:** `#,0.0`  
- **Meaning:** Mean processing_hours of Completed operations (matches kpi_summary.json and SQL).

```dax
Average Processing Hours =
CALCULATE(AVERAGE(operations_clean[processing_hours]), operations_clean[status] = "Completed")
```

## Average SLA Target Hours
- **Folder:** 2 Processing  
- **Format:** `#,0.0`  
- **Meaning:** Mean sla_target_hours of Completed operations; benchmark for processing hours.

```dax
Average SLA Target Hours =
CALCULATE(AVERAGE(operations_clean[sla_target_hours]), operations_clean[status] = "Completed")
```

## SLA Breach Count
- **Folder:** 3 SLA  
- **Format:** `#,0`  
- **Meaning:** Completed operations with processing_hours > sla_target_hours (sla_breached = 1).

```dax
SLA Breach Count =
CALCULATE(SUM(operations_clean[sla_breached]), operations_clean[status] = "Completed")
```

## SLA Breach Rate
- **Folder:** 3 SLA  
- **Format:** `0.0%`  
- **Meaning:** Breaches / Completed. SLA is only evaluated on completed work (ETL rule).

```dax
SLA Breach Rate =
DIVIDE([SLA Breach Count], [Completed Operations])
```

## SLA Compliance %
- **Folder:** 3 SLA  
- **Format:** `0.0%`  
- **Meaning:** 1 - SLA Breach Rate. REPLACES the original measure, which divided by all rows.

```dax
SLA Compliance % =
DIVIDE([Completed Operations] - [SLA Breach Count], [Completed Operations])
```

## Exception Count
- **Folder:** 4 Exceptions & Rework  
- **Format:** `#,0`  
- **Meaning:** exception_flag = TRUE.

```dax
Exception Count =
CALCULATE([Total Operations], operations_clean[exception_flag] = TRUE())
```

## Exception Rate %
- **Folder:** 4 Exceptions & Rework  
- **Format:** `0.0%`  
- **Meaning:** Exceptions / all operations.

```dax
Exception Rate % =
DIVIDE([Exception Count], [Total Operations])
```

## Rework Count
- **Folder:** 4 Exceptions & Rework  
- **Format:** `#,0`  
- **Meaning:** rework_flag = TRUE.

```dax
Rework Count =
CALCULATE([Total Operations], operations_clean[rework_flag] = TRUE())
```

## Rework Rate %
- **Folder:** 4 Exceptions & Rework  
- **Format:** `0.0%`  
- **Meaning:** Rework / all operations.

```dax
Rework Rate % =
DIVIDE([Rework Count], [Total Operations])
```

## Total Transaction Amount
- **Folder:** 5 Financial  
- **Format:** `$#,0.0,,`  
- **Meaning:** SUM(transaction_amount), USD. Four operation types carry 0 by design. Not placed on a page; available for tooltips.

```dax
Total Transaction Amount =
SUM(operations_clean[transaction_amount])
```

## Insight - Top Volume Operation Type
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Top Volume Operation Type =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[operation_type]), "@v", [Total Operations])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[operation_type]) & " (" & FORMAT(_val, "#,0") & ")")
```

## Insight - Most SLA Breaches (Operation Type)
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Most SLA Breaches (Operation Type) =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[operation_type]), "@v", [SLA Breach Count])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[operation_type]) & " (" & FORMAT(_val, "#,0") & ")")
```

## Insight - Highest SLA Breach Rate (Priority)
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Highest SLA Breach Rate (Priority) =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[priority]), "@v", [SLA Breach Rate])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[priority]) & " (" & FORMAT(_val, "0.0%") & ")")
```

## Insight - Region With Most Exceptions
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Region With Most Exceptions =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[region]), "@v", [Exception Count])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[region]) & " (" & FORMAT(_val, "#,0") & ")")
```

## Insight - Highest Exception Rate (Channel)
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Highest Exception Rate (Channel) =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[channel]), "@v", [Exception Rate %])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[channel]) & " (" & FORMAT(_val, "0.0%") & ")")
```

## Insight - Highest Rework Rate (Operation Type)
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Highest Rework Rate (Operation Type) =
VAR _t = ADDCOLUMNS(VALUES(operations_clean[operation_type]), "@v", [Rework Rate %])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, operations_clean[operation_type]) & " (" & FORMAT(_val, "0.0%") & ")")
```

## Insight - Peak Month By Volume
- **Folder:** 6 Insights  
- **Format:** `text`  
- **Meaning:** Returns the category with the highest value of the named metric, with the value, under the current filters (ADDCOLUMNS + TOPN). Ties return one category.

```dax
Insight - Peak Month By Volume =
VAR _t = ADDCOLUMNS(VALUES(Calendar[Month Year]), "@v", [Total Operations])
VAR _top = TOPN(1, _t, [@v], DESC)
VAR _val = MAXX(_top, [@v])
RETURN IF(ISBLANK(_val), "n/a", MAXX(_top, Calendar[Month Year]) & " (" & FORMAT(_val, "#,0") & ")")
```

