import os, sys, json, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_spec import *
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "powerbi", "ROIP_PowerBI_Project")
SM = f"{OUT}/ROIP_Operations_Intelligence.SemanticModel"
os.makedirs(f"{SM}/definition/tables", exist_ok=True)
def w(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as f: f.write(s)
def q(n): return f"'{n}'" if any(c in n for c in " %()-&") else n
def ind(txt, n): return "\n".join("\t"*n + l for l in txt.split("\n"))

w(f"{SM}/definition.pbism", json.dumps({"version":"4.0","settings":{}}, indent=2))
w(f"{SM}/definition/database.tmdl", "database\n\tcompatibilityLevel: 1601\n")
w(f"{SM}/definition/model.tmdl", """model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	discourageImplicitMeasures
	sourceQueryCulture: en-US
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

annotation PBI_QueryOrder = ["ProjectRoot","DataFolderPath","DQFolderPath","operations_clean","dq_rule_results","dq_run_summary"]

ref table operations_clean
ref table Calendar
ref table dq_rule_results
ref table dq_run_summary

ref expression ProjectRoot
ref expression DataFolderPath
ref expression DQFolderPath
""")
w(f"{SM}/definition/expressions.tmdl",
 'expression ProjectRoot = "C:\\path\\to\\ROIP" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
 f'\tlineageTag: {gid("expr-root")}\n\tannotation PBI_ResultType = Text\n\n'
 'expression DataFolderPath = Text.TrimEnd(ProjectRoot, "\\") & "\\data\\processed"\n'
 f'\tlineageTag: {gid("expr-datafolder3")}\n\tannotation PBI_ResultType = Text\n\n'
 'expression DQFolderPath = Text.TrimEnd(ProjectRoot, "\\") & "\\reports\\data_quality"\n'
 f'\tlineageTag: {gid("expr-dqfolder")}\n\tannotation PBI_ResultType = Text\n')
w(f"{SM}/definition/relationships.tmdl",
 f"relationship {gid('rel-received')}\n\tfromColumn: operations_clean.received_date\n\ttoColumn: Calendar.Date\n\n"
 f"relationship {gid('rel-completed')}\n\tisActive: false\n\tfromColumn: operations_clean.completed_date\n\ttoColumn: Calendar.Date\n")

types = {"string":"type text","int64":"Int64.Type","double":"type number","dateTime":"type datetime","boolean":"type logical"}
raw_types = {"customer_id":"type text","account_id":"type text","plan_id":"type text","completed_at":"type datetime",
 "received_year":"Int64.Type","received_month":"Int64.Type","received_week":"Int64.Type","received_day_of_week":"type text"}
for c in COLUMNS:
    if c[0] not in ("completed_date","priority_rank"):
        raw_types[c[0]] = "type date" if c[0]=="received_date" else types[c[1]]
hdr = next(csv.reader(open(os.path.join(ROOT, "data", "processed", "operations_clean.csv"))))
assert len(hdr)==33 and all(h in raw_types for h in hdr)
changed = ",\n\t\t\t\t".join('{"%s", %s}' % (h, raw_types[h]) for h in hdr)
dropped = ["customer_id","account_id","plan_id","completed_at","received_year","received_month","received_week","received_day_of_week"]
kept = [h for h in hdr if h not in dropped] + ["completed_date","priority_rank","age_days","age_band","age_band_order","intake_completeness","exception_status","rework_status","workload_band","workload_band_order"]
assert kept == [c[0] for c in COLUMNS], (kept, [c[0] for c in COLUMNS])
mq = f'''let
	Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolderPath, "\\") & "\\operations_clean.csv"), [Delimiter=",", Columns=33, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
	Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
	Typed = Table.TransformColumnTypes(Promoted, {{
				{changed}
			}}, "en-US"),
	AddCompletedDate = Table.AddColumn(Typed, "completed_date", each if [completed_at] = null then null else DateTime.Date([completed_at]), type nullable date),
	AddPriorityRank = Table.AddColumn(AddCompletedDate, "priority_rank", each if [priority] = "Critical" then 1 else if [priority] = "High" then 2 else if [priority] = "Medium" then 3 else 4, Int64.Type),
	AsOf = List.Max(Typed[received_at]),
	AddAge = Table.AddColumn(AddPriorityRank, "age_days", each Duration.Days(AsOf - [received_at]), Int64.Type),
	AddAgeBand = Table.AddColumn(AddAge, "age_band", each if [age_days] <= 30 then "0-30 days" else if [age_days] <= 90 then "31-90 days" else if [age_days] <= 180 then "91-180 days" else "181+ days", type text),
	AddAgeOrder = Table.AddColumn(AddAgeBand, "age_band_order", each if [age_days] <= 30 then 1 else if [age_days] <= 90 then 2 else if [age_days] <= 180 then 3 else 4, Int64.Type),
	AddIntake = Table.AddColumn(AddAgeOrder, "intake_completeness", each if [missing_info_flag] = true then "Information missing" else "Information complete", type text),
	AddExc = Table.AddColumn(AddIntake, "exception_status", each if [exception_flag] = true then "Exception raised" else "No exception", type text),
	AddRw = Table.AddColumn(AddExc, "rework_status", each if [rework_flag] = true then "Reworked" else "No rework", type text),
	AddWl = Table.AddColumn(AddRw, "workload_band", each if [team_workload] <= 54 then "35-54" else if [team_workload] <= 74 then "55-74" else if [team_workload] <= 94 then "75-94" else "95+", type text),
	AddWlOrder = Table.AddColumn(AddWl, "workload_band_order", each if [team_workload] <= 54 then 1 else if [team_workload] <= 74 then 2 else if [team_workload] <= 94 then 3 else 4, Int64.Type),
	Trimmed = Table.RemoveColumns(AddWlOrder, {{{", ".join('"%s"'%d for d in dropped)}}}),
	Reordered = Table.ReorderColumns(Trimmed, {{{", ".join('"%s"'%d for d in kept)}}})
in
	Reordered'''
s = f"table {TABLE}\n\tlineageTag: {gid('tbl-ops')}\n\n"
for m in M:
    nm = q(m["name"])
    if m["desc"]: s += f"\t/// {m['desc']}\n"
    s += (f"\tmeasure {nm} =\n{ind(m['dax'],3)}\n" if "\n" in m["dax"] else f"\tmeasure {nm} = {m['dax']}\n")
    if m["fmt"]: s += f"\t\tformatString: {m['fmt']}\n"
    s += f"\t\tdisplayFolder: {m['folder']}\n\t\tlineageTag: {gid('m-'+m['name'])}\n\n"
for name,dt,fmt,summ,hid,sort,desc in COLUMNS:
    s += f"\tcolumn {name}\n\t\tdataType: {dt}\n"
    if fmt: s += f"\t\tformatString: {fmt}\n"
    if hid: s += "\t\tisHidden\n"
    s += f"\t\tlineageTag: {gid('c-'+name)}\n\t\tsummarizeBy: {summ}\n\t\tsourceColumn: {name}\n"
    if sort: s += f"\t\tsortByColumn: {sort}\n"
    s += "\n"
s += f"\tpartition {TABLE} = m\n\t\tmode: import\n\t\tsource =\n{ind(mq,3)}\n"
w(f"{SM}/definition/tables/{TABLE}.tmdl", s)

s = f"table Calendar\n\tlineageTag: {gid('tbl-cal')}\n\tdataCategory: Time\n\n"
for name,dt,fmt,sort in CAL_COLS:
    s += f"\tcolumn {q(name)}\n\t\tdataType: {dt}\n"
    if fmt: s += f"\t\tformatString: {fmt}\n"
    if name=="Date": s += "\t\tisKey\n"
    if name in ("Month Number","Year Month","Weekday Number"): s += "\t\tisHidden\n"
    s += f"\t\tlineageTag: {gid('cc-'+name)}\n\t\tsummarizeBy: none\n\t\tsourceColumn: [{name}]\n"
    if sort: s += f"\t\tsortByColumn: {q(sort)}\n"
    s += "\n"
s += f"\tpartition Calendar = calculated\n\t\tmode: import\n\t\tsource =\n{ind(CAL_DAX,3)}\n"
w(f"{SM}/definition/tables/Calendar.tmdl", s)

def csv_table(name, path_expr, cols):
    t = f"table {name}\n\tlineageTag: {gid('tbl-'+name)}\n\n"
    for cn, dt, fmt, summ in cols:
        t += f"\tcolumn {cn}\n\t\tdataType: {dt}\n"
        if fmt: t += f"\t\tformatString: {fmt}\n"
        t += f"\t\tlineageTag: {gid('c-'+name+cn)}\n\t\tsummarizeBy: {summ}\n\t\tsourceColumn: {cn}\n\n"
    tm = {"string": "type text", "int64": "Int64.Type", "double": "type number"}
    ch = ", ".join('{"%s", %s}' % (cn, tm[dt]) for cn, dt, _, _ in cols)
    mq = (f'let\n\tSource = Csv.Document(File.Contents(DQFolderPath & "\\{path_expr}"), [Delimiter=",", Columns={len(cols)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
          f'\tPromoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n'
          f'\tTyped = Table.TransformColumnTypes(Promoted, {{{ch}}}, "en-US")\nin\n\tTyped')
    t += f"\tpartition {name} = m\n\t\tmode: import\n\t\tsource =\n{ind(mq,3)}\n"
    w(f"{SM}/definition/tables/{name}.tmdl", t)
csv_table("dq_rule_results", "dq_rule_results.csv", [("rule_id","string",None,"none"),("rule_name","string",None,"none"),("stage","string",None,"none"),
    ("severity","string",None,"none"),("rows_affected","int64","#,0","none"),("pct_of_raw","double","0.00","none"),("action","string",None,"none"),("description","string",None,"none")])
csv_table("dq_run_summary", "dq_run_summary.csv", [("metric","string",None,"none"),("value","double","#,0.0","none")])
print("TMDL written")
