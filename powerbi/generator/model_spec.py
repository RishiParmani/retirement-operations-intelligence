import uuid
NS = uuid.UUID("6f1c2d3e-1111-4222-8333-444455556666")
def gid(key): return str(uuid.uuid5(NS, key))
TABLE = "operations_clean"
COLUMNS = [
 ("operation_id","string",None,"none",False,None,"Unique operation identifier."),
 ("operation_type","string",None,"none",False,None,""),
 ("priority","string",None,"none",False,"priority_rank",""),
 ("channel","string",None,"none",False,None,""),
 ("region","string",None,"none",False,None,""),
 ("processing_team","string",None,"none",False,None,""),
 ("team_workload","int64","#,0","none",False,None,""),
 ("customer_segment","string",None,"none",False,None,""),
 ("received_at","dateTime","dd mmm yyyy hh:nn","none",True,None,""),
 ("assigned_at","dateTime","dd mmm yyyy hh:nn","none",True,None,""),
 ("started_at","dateTime","dd mmm yyyy hh:nn","none",True,None,""),
 ("status","string",None,"none",False,None,""),
 ("exception_flag","boolean",None,"none",False,None,""),
 ("exception_type","string",None,"none",False,None,""),
 ("exception_severity","string",None,"none",False,None,""),
 ("root_cause","string",None,"none",False,None,""),
 ("rework_flag","boolean",None,"none",False,None,""),
 ("sla_target_hours","int64","#,0","none",False,None,""),
 ("processing_hours","double","#,0.00","none",False,None,""),
 ("sla_breached","int64","0","none",False,None,""),
 ("transaction_amount","double","$#,0.00","none",False,None,""),
 ("currency","string",None,"none",False,None,""),
 ("missing_info_flag","boolean",None,"none",False,None,""),
 ("received_date","dateTime","dd mmm yyyy","none",False,None,""),
 ("data_quality_score","int64","0","none",False,None,""),
 ("completed_date","dateTime","dd mmm yyyy","none",False,None,"derived"),
 ("priority_rank","int64","0","none",True,None,"sort helper"),
 ("age_days","int64","0","none",True,None,"days between received_at and the latest received_at in the data (NOT today)"),
 ("age_band","string",None,"none",False,"age_band_order","0-30 / 31-90 / 91-180 / 181+ days"),
 ("age_band_order","int64","0","none",True,None,"sort helper"),
 ("intake_completeness","string",None,"none",False,None,"Information missing / Information complete (from missing_info_flag)"),
 ("exception_status","string",None,"none",False,None,"Exception raised / No exception"),
 ("rework_status","string",None,"none",False,None,"Reworked / No rework"),
 ("workload_band","string",None,"none",False,"workload_band_order","35-54 / 55-74 / 75-94 / 95+"),
 ("workload_band_order","int64","0","none",True,None,"sort helper"),
]
M=[]
def add(name,dax,fmt,folder,desc): M.append(dict(name=name,dax=dax,fmt=fmt,folder=folder,desc=desc))
def ins(dim, measure, fmt):
    return ("VAR _t = ADDCOLUMNS(VALUES(%s), \"@v\", %s)\n"
            "VAR _top = TOPN(1, _t, [@v], DESC)\n"
            "VAR _val = MAXX(_top, [@v])\n"
            "RETURN IF(ISBLANK(_val), \"n/a\", MAXX(_top, %s) & \" (\" & FORMAT(_val, \"%s\") & \")\")") % (dim, measure, dim, fmt)
F1,F2,F3,F4,F5,F6="1 Volume","2 Processing","3 SLA","4 Exceptions & Rework","5 Financial","6 Insights"
T=TABLE
add("Total Operations",f"COUNTROWS({T})","#,0",F1,"Count of operations.")
add("Completed Operations",f'CALCULATE([Total Operations], {T}[status] = "Completed")',"#,0",F1,"")
add("Pending Operations",f'CALCULATE([Total Operations], {T}[status] = "Pending")',"#,0",F1,"")
add("Failed Operations",f'CALCULATE([Total Operations], {T}[status] = "Failed")',"#,0",F1,"")
add("Escalated Operations",f'CALCULATE([Total Operations], {T}[status] = "Escalated")',"#,0",F1,"")
add("Completion Rate %","DIVIDE([Completed Operations], [Total Operations])","0.0%",F1,"")
add("Operations Completed (by Completion Date)",f"CALCULATE([Completed Operations], USERELATIONSHIP({T}[completed_date], Calendar[Date]))","#,0",F1,"")
# v3: AVERAGE(column) replaced by SUM / count (same population: Completed only). Same result, but built only from the
# SUM + COUNTROWS patterns that render correctly elsewhere in this model, and ROUND removes any float noise.
add("Completed Processing Hours",f'CALCULATE(SUM({T}[processing_hours]), {T}[status] = "Completed")',"#,0.00",F2,"Helper: total processing hours of completed operations.")
add("Completed SLA Target Hours",f'CALCULATE(SUM({T}[sla_target_hours]), {T}[status] = "Completed")',"#,0",F2,"Helper: total SLA target hours of completed operations.")
add("Average Processing Hours","ROUND(DIVIDE([Completed Processing Hours], [Completed Operations]), 2)","0.0",F2,"Mean processing hours, Completed operations only.")
add("Average SLA Target Hours","ROUND(DIVIDE([Completed SLA Target Hours], [Completed Operations]), 2)","0.0",F2,"Mean SLA target hours, Completed operations only.")
add("Open Backlog","[Pending Operations] + [Escalated Operations]","#,0",F1,"Pending + Escalated.")
add("Stale Pending (over 90 days)",f'CALCULATE([Total Operations], {T}[status] = "Pending", {T}[age_days] > 90)',"#,0",F1,"Pending for more than 90 days as of the latest received date.")
add("SLA Breach Count",f'CALCULATE(SUM({T}[sla_breached]), {T}[status] = "Completed")',"#,0",F3,"")
add("SLA Breach Rate","DIVIDE([SLA Breach Count], [Completed Operations])","0.0%",F3,"")
add("SLA Compliance %","DIVIDE([Completed Operations] - [SLA Breach Count], [Completed Operations])","0.0%",F3,"")
add("Exception Count",f"CALCULATE([Total Operations], {T}[exception_flag] = TRUE())","#,0",F4,"")
add("Exception Rate %","DIVIDE([Exception Count], [Total Operations])","0.0%",F4,"")
add("Rework Count",f"CALCULATE([Total Operations], {T}[rework_flag] = TRUE())","#,0",F4,"")
add("Rework Rate %","DIVIDE([Rework Count], [Total Operations])","0.0%",F4,"")
add("Share of SLA Breaches",f"DIVIDE([SLA Breach Count], CALCULATE([SLA Breach Count], ALLSELECTED({T})))","0.0%",F3,"This slice's share of all breaches in the current filter context.")
add("Open Backlog Operations (by age)",f'CALCULATE([Total Operations], {T}[status] IN {{"Pending","Escalated"}})',"#,0",F1,"Same as Open Backlog; used on the age chart.")
add("Total Transaction Amount",f"SUM({T}[transaction_amount])",'$#,0.0,,',F5,"")
add("Insight - Top Volume Operation Type",ins(f"{T}[operation_type]","[Total Operations]","#,0"),None,F6,"")
add("Insight - Most SLA Breaches (Operation Type)",ins(f"{T}[operation_type]","[SLA Breach Count]","#,0"),None,F6,"")
add("Insight - Highest SLA Breach Rate (Priority)",ins(f"{T}[priority]","[SLA Breach Rate]","0.0%"),None,F6,"")
add("Insight - Region With Most Exceptions",ins(f"{T}[region]","[Exception Count]","#,0"),None,F6,"")
add("Insight - Highest Exception Rate (Channel)",ins(f"{T}[channel]","[Exception Rate %]","0.0%"),None,F6,"")
add("Insight - Highest Rework Rate (Operation Type)",ins(f"{T}[operation_type]","[Rework Rate %]","0.0%"),None,F6,"")
add("Insight - Peak Month By Volume",ins("Calendar[Month Year]","[Total Operations]","#,0"),None,F6,"")
CAL_COLS = [("Date","dateTime","dd mmm yyyy",None),("Year","int64","0",None),("Quarter","string",None,None),
 ("Month Number","int64","0",None),("Month","string",None,"Month Number"),("Month Year","string",None,"Year Month"),
 ("Year Month","int64","0",None),("Weekday","string",None,"Weekday Number"),("Weekday Number","int64","0",None)]
CAL_DAX = ('VAR _start = DATE(YEAR(MIN(operations_clean[received_date])), 1, 1)\n'
 'VAR _end = EOMONTH(MAX(MAX(operations_clean[received_date]), MAX(operations_clean[completed_date])), 0)\n'
 'RETURN\n ADDCOLUMNS(\n  CALENDAR(_start, _end),\n  "Year", YEAR([Date]),\n  "Quarter", "Q" & ROUNDUP(MONTH([Date]) / 3, 0),\n'
 '  "Month Number", MONTH([Date]),\n  "Month", FORMAT([Date], "mmm"),\n  "Month Year", FORMAT([Date], "mmm yyyy"),\n'
 '  "Year Month", YEAR([Date]) * 100 + MONTH([Date]),\n  "Weekday", FORMAT([Date], "ddd"),\n  "Weekday Number", WEEKDAY([Date], 2)\n )')

F7,F8="7 Data Quality","8 Diagnostics"
DQ="dq_run_summary"
def dqm(name,key,fmt,desc):
    add(name,f'CALCULATE(SUM({DQ}[value]), {DQ}[metric] = "{key}")',fmt,F7,desc)
dqm("DQ Raw Records","raw_records","#,0","Records in the raw extract.")
dqm("DQ Clean Records","clean_records","#,0","Records loaded after validation.")
dqm("DQ Rejected Records","rejected_records","#,0","Records refused by reject rules (see dq_rejected_records.csv).")
dqm("DQ Acceptance Rate %","acceptance_rate_pct","0.0",  "Clean / raw, in percent.")
dqm("DQ Uniqueness %","uniqueness_pct","0.0","Share of raw records with a unique operation_id.")
dqm("DQ Validity %","validity_pct","0.0","Share of raw records passing category / range rules.")
dqm("DQ Region Imputed","region_imputed_unknown","#,0","Missing region labelled Unknown (not dropped).")
dqm("DQ Warning Flags","warning_flag_events","#,0","Flag-stage rule hits (records retained).")
dqm("DQ Mean Quality Score","mean_data_quality_score","0.0","Mean per-record data_quality_score.")
add("Rule Rows Affected","SUM(dq_rule_results[rows_affected])","#,0",F7,"")
add("Rule Pct of Raw","SUM(dq_rule_results[pct_of_raw])","0.00",F7,"")
add("Diag - Row Count","COUNTROWS(operations_clean)","#,0",F8,"Diagnostic: should equal Total Operations.")
add("Diag - Completed Rows With Hours",f'CALCULATE(COUNTROWS({T}), {T}[status] = "Completed", NOT ISBLANK({T}[processing_hours]))',"#,0",F8,"Diagnostic: completed rows where processing_hours loaded as a number. If lower than Completed Operations, the CSV column is not typed numeric.")
add("Diag - Sum Processing Hours",f"SUM({T}[processing_hours])","#,0",F8,"Diagnostic: if blank, processing_hours did not load as numbers.")
add("Diag - Min Sla Target",f"MIN({T}[sla_target_hours])","0",F8,"")
