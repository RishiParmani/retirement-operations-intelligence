import os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_spec import gid
T="operations_clean"
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"powerbi","ROIP_PowerBI_Project")
RP=f"{OUT}/ROIP_Operations_Intelligence.Report"
shutil.rmtree(RP, ignore_errors=True)
SCH="https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
def wj(p,o):
    os.makedirs(os.path.dirname(p),exist_ok=True)
    json.dump(o,open(p,"w",encoding="utf-8"),indent=2)

NAVY="#0B1F3A"; BLUE="#2563EB"; TEAL="#0F9D8A"; ORANGE="#F59E0B"; RED="#DC2626"; GREY="#64748B"; INK="#1E293B"; CANVAS="#F4F6FA"; CARD="#FFFFFF"; LINE="#E2E8F0"
FONT="Segoe UI"
def lit(v): return {"expr":{"Literal":{"Value":v}}}
def s(v): return lit("'%s'"%v)
def n(v): return lit("%sD"%v)
def b(v): return lit("true" if v else "false")
def col(hexv): return {"solid":{"color":s(hexv)}}
def C(ent,prop): return {"Column":{"Expression":{"SourceRef":{"Entity":ent}},"Property":prop}}
def Mz(prop): return {"Measure":{"Expression":{"SourceRef":{"Entity":T}},"Property":prop}}
def proj(f, active=None):
    k=list(f.keys())[0]; ent=f[k]["Expression"]["SourceRef"]["Entity"]; p=f[k]["Property"]
    d={"field":f,"queryRef":f"{ent}.{p}","nativeQueryRef":p}
    return d
def vc_title(text, size=11):
    return {"title":[{"properties":{"show":b(True),"text":s(text),"fontColor":col(INK),"fontSize":n(size),"fontFamily":s(FONT+" Semibold"),"alignment":s("left")}}],
            "background":[{"properties":{"show":b(True),"color":col(CARD),"transparency":n(0)}}],
            "border":[{"properties":{"show":b(True),"color":col(LINE),"radius":n(8)}}],
            "dropShadow":[{"properties":{"show":b(False)}}]}
def vc_plain(show_title=False):
    return {"title":[{"properties":{"show":b(False)}}],
            "background":[{"properties":{"show":b(True),"color":col(CARD),"transparency":n(0)}}],
            "border":[{"properties":{"show":b(True),"color":col(LINE),"radius":n(8)}}],
            "dropShadow":[{"properties":{"show":b(False)}}]}

class Page:
    def __init__(self,name,display,h=720):
        self.name=gid("page-"+name); self.display=display; self.h=h; self.vis=[]; self.z=0
    def add(self,key,vtype,x,y,w,h,query=None,objects=None,vco=None,sync=None,extra=None):
        v={"visualType":vtype}
        if query: v["query"]=query
        if objects: v["objects"]=objects
        if vco: v["visualContainerObjects"]=vco
        v["drillFilterOtherVisuals"]=True
        o={"$schema":f"{SCH}/visualContainer/2.13.0/schema.json","name":gid(self.name+key)[:20].replace("-",""),
           "position":{"x":x,"y":y,"z":self.z,"height":h,"width":w,"tabOrder":self.z},"visual":v}
        if sync: v["syncGroup"]={"groupName":sync,"fieldChanges":True,"filterChanges":True}
        self.z+=1000
        self.vis.append(o)
    def write(self):
        d=f"{RP}/definition/pages/{self.name}"
        wj(f"{d}/page.json",{"$schema":f"{SCH}/page/2.1.0/schema.json","name":self.name,"displayName":self.display,
            "displayOption":"FitToPage","height":self.h,"width":1280,
            "objects":{"background":[{"properties":{"color":col(CANVAS),"transparency":n(0)}}],
                       "outspace":[{"properties":{"color":col(NAVY)}}]}})
        for o in self.vis: wj(f"{d}/visuals/{o['name']}/visual.json",o)

# ---------- building blocks
def header(p,title,sub):
    p.add("hdr_bg","shape",0,0,1280,66,objects={"shape":[{"properties":{"tileShape":s("rectangle")}}],
        "fill":[{"properties":{"fillColor":col(NAVY),"transparency":n(0)}}],"outline":[{"properties":{"show":b(False)}}]},
        vco={"title":[{"properties":{"show":b(False)}}]})
    def tb(key,x,y,w,h,text,size,color,bold=False):
        p.add(key,"textbox",x,y,w,h,objects={"general":[{"properties":{"paragraphs":[{"textRuns":[{"value":text,
            "textStyle":{"fontSize":f"{size}pt","color":color,"fontFamily":FONT,**({"fontWeight":"bold"} if bold else {})}}]}]}}]},
            vco={"title":[{"properties":{"show":b(False)}}],"background":[{"properties":{"show":b(False)}}],"border":[{"properties":{"show":b(False)}}]})
    tb("hdr_t",20,3,700,40,title,18,"#FFFFFF",True)
    tb("hdr_s",20,40,730,24,sub,10,"#B6C4DA")
    p.add("nav","pageNavigator",760,14,500,40,
        query=None,objects={"pages":[{"properties":{"showHiddenPages":b(False)}}]},
        vco={"title":[{"properties":{"show":b(False)}}],"background":[{"properties":{"show":b(False)}}],"border":[{"properties":{"show":b(False)}}]})

def slicer(p,key,x,w,field,label,mode="Dropdown",sync=None):
    p.add(key,"slicer",x,76,w,44,query={"queryState":{"Values":{"projections":[proj(field)]}}},
        objects={"data":[{"properties":{"mode":s(mode)}}],
                 "header":[{"properties":{"show":b(False)}}],
                 "items":[{"properties":{"fontColor":col(INK),"fontFamily":s(FONT),"textSize":n(10)}}]},
        vco={"title":[{"properties":{"show":b(True),"text":s(label),"fontColor":col(GREY),"fontSize":n(9),"fontFamily":s(FONT)}}],
             "background":[{"properties":{"show":b(True),"color":col(CARD),"transparency":n(0)}}],
             "border":[{"properties":{"show":b(True),"color":col(LINE),"radius":n(6)}}]},
        sync=sync)

def slicer_row(p, with_status=False):
    items=[("sl_date",C("Calendar","Date"),"Date range","Between","roip_date",300),
           ("sl_region",C(T,"region"),"Region","Dropdown","roip_region",180),
           ("sl_type",C(T,"operation_type"),"Operation type","Dropdown","roip_type",230),
           ("sl_prio",C(T,"priority"),"Priority","Dropdown","roip_prio",150),
           ("sl_chan",C(T,"channel"),"Channel","Dropdown","roip_chan",150)]
    if with_status: items.append(("sl_status",C(T,"status"),"Status","Dropdown","roip_status",150))
    x=24
    total=1232; gap=12; avail=total-gap*(len(items)-1); sw=sum(i[5] for i in items); sc=avail/sw
    for key,f,lab,mode,sg,w in items:
        ww=round(w*sc); slicer(p,key,x,ww,f,lab,mode,sg); x+=ww+gap

PREC={"Average Processing Hours":1,"Average SLA Target Hours":1,"Share of SLA Breaches":1,"Completion Rate %":1,"SLA Compliance %":1,"SLA Breach Rate":1,"Exception Rate %":1,"Rework Rate %":1}
def card(p,key,x,y,w,h,measure,label,color=NAVY,size=22):
    p.add(key,"card",x,y,w,h,query={"queryState":{"Values":{"projections":[proj(Mz(measure))]}}},
        objects={"labels":[{"properties":{"color":col(color),"fontSize":n(size),"fontFamily":s(FONT+" Semibold"),"labelDisplayUnits":n(1),"labelPrecision":n(PREC.get(measure,0))}}],
                 "categoryLabels":[{"properties":{"show":b(False)}}]},
        vco={**vc_plain(),"title":[{"properties":{"show":b(True),"text":s(label),"fontColor":col(GREY),"fontSize":n(10),"fontFamily":s(FONT),"alignment":s("left")}}],
             "border":[{"properties":{"show":b(True),"color":col(LINE),"radius":n(8)}}]})

def cards(p,y,h,spec):
    k=len(spec); gap=12; w=(1232-gap*(k-1))/k
    for i,(m,lab,color) in enumerate(spec):
        card(p,f"card{i}",round(24+i*(w+gap),1),y,round(w,1),h,m,lab,color)

def axes(vcolor=GREY, vmin0=True, show_val_axis=False, cat_size=9):
    return {"categoryAxis":[{"properties":{"show":b(True),"labelColor":col(INK),"fontSize":n(cat_size),"fontFamily":s(FONT),"showAxisTitle":b(False)}}],
            "valueAxis":[{"properties":{"show":b(show_val_axis),"labelColor":col(vcolor),"fontSize":n(9),"gridlineShow":b(False),"showAxisTitle":b(False),
                                         **({"start":n(0)} if vmin0 else {})}}],
            "legend":[{"properties":{"show":b(False)}}]}
def dlabels(fmt_units=None, color=INK, size=9):
    pr={"show":b(True),"color":col(color),"fontSize":n(size),"fontFamily":s(FONT)}
    if fmt_units is not None: pr["labelDisplayUnits"]=n(fmt_units)
    return [{"properties":pr}]
def dpoint(c): return [{"properties":{"fill":col(c)}}]

def bar(p,key,x,y,w,h,cat,measure,title,color=BLUE,horizontal=True,sort_desc=True,sort_by_cat=False):
    q={"queryState":{"Category":{"projections":[proj(cat)]},"Y":{"projections":[proj(Mz(measure))]}}}
    if sort_by_cat: pass
    elif sort_desc: q["sortDefinition"]={"sort":[{"field":Mz(measure),"direction":"Descending"}]}
    o=axes(); o["labels"]=dlabels(); o["dataPoint"]=dpoint(color)
    p.add(key,"clusteredBarChart" if horizontal else "clusteredColumnChart",x,y,w,h,query=q,objects=o,vco=vc_title(title))

def line(p,key,x,y,w,h,cat,measures,title,colors,legend=False,subtitle=None):
    q={"queryState":{"Category":{"projections":[proj(cat)]},"Y":{"projections":[proj(Mz(m)) for m in measures]}}}
    o=axes(show_val_axis=True,vmin0=False)
    o["valueAxis"][0]["properties"]["gridlineShow"]=b(True)
    o["valueAxis"][0]["properties"]["gridlineColor"]=col(LINE)
    o["legend"]=[{"properties":{"show":b(legend),"position":s("Top"),"labelColor":col(INK),"fontSize":n(9)}}]
    o["dataPoint"]=dpoint(colors[0])
    o["lineStyles"]=[{"properties":{"strokeWidth":n(3),"showMarker":b(True),"markerSize":n(5)}}]
    vco=vc_title(title)
    if subtitle: vco["subTitle"]=[{"properties":{"show":b(True),"text":s(subtitle),"fontColor":col(GREY),"fontSize":n(8),"fontFamily":s(FONT)}}]
    p.add(key,"lineChart",x,y,w,h,query=q,objects=o,vco=vco)

def donut(p,key,x,y,w,h,cat,measure,title):
    q={"queryState":{"Category":{"projections":[proj(cat)]},"Y":{"projections":[proj(Mz(measure))]}}}
    p.add(key,"donutChart",x,y,w,h,query=q,objects={"legend":[{"properties":{"show":b(True),"position":s("Right"),"labelColor":col(INK),"fontSize":n(9)}}],
        "labels":[{"properties":{"labelStyle":s("Percent of total"),"color":col(INK),"fontSize":n(9)}}]},vco=vc_title(title))

def insights(p,key,x,y,w,h,measures,title):
    p.add(key,"multiRowCard",x,y,w,h,query={"queryState":{"Values":{"projections":[proj(Mz(m)) for m in measures]}}},
        objects={"dataLabels":[{"properties":{"color":col(NAVY),"fontSize":n(11),"fontFamily":s(FONT+" Semibold")}}],
                 "cardTitle":[{"properties":{"color":col(GREY),"fontSize":n(8),"fontFamily":s(FONT)}}],
                 "card":[{"properties":{"outline":s("None"),"barShow":b(True),"barColor":col(BLUE)}}]},
        vco=vc_title(title))

def table(p,key,x,y,w,h,cat,measures,title):
    q={"queryState":{"Values":{"projections":[proj(cat)]+[proj(Mz(m)) for m in measures]}}}
    p.add(key,"tableEx",x,y,w,h,query=q,objects={"grid":[{"properties":{"gridVertical":b(False),"rowPadding":n(3),"textSize":n(9)}}],
        "columnHeaders":[{"properties":{"fontColor":col("#FFFFFF"),"backColor":col(NAVY),"fontSize":n(9),"fontFamily":s(FONT+" Semibold")}}],
        "values":[{"properties":{"fontColor":col(INK),"fontSize":n(9),"fontFamily":s(FONT)}}]},vco=vc_title(title))

MY=C("Calendar","Month Year")
OT=C(T,"operation_type"); RG=C(T,"region"); PR=C(T,"priority"); CH=C(T,"channel"); ST=C(T,"status")

# ================= PAGE 1
p1=Page("exec","Executive Operations Overview")
header(p1,"Executive Operations Overview","Retirement Operations Intelligence Platform  |  Volume, SLA and quality at a glance  |  Synthetic data, calendar year 2025")
slicer_row(p1)
cards(p1,128,82,[("Total Operations","Total operations",NAVY),("Completed Operations","Completed",TEAL),("Pending Operations","Pending",ORANGE),
    ("Failed Operations","Failed",RED),("Average Processing Hours","Avg processing hours",NAVY),("SLA Compliance %","SLA compliance",TEAL),
    ("Exception Rate %","Exception rate",ORANGE),("Rework Rate %","Rework rate",ORANGE)])
line(p1,"trend_vol",24,222,512,232,MY,["Total Operations"],"Operations received per month",[BLUE])
line(p1,"trend_sla",548,222,400,232,MY,["SLA Compliance %"],"SLA compliance % by month (completed ops)",[TEAL])
bar(p1,"status",960,222,296,232,ST,"Total Operations","Operations by status",NAVY)
bar(p1,"prio",24,466,296,232,PR,"Total Operations","Operations by priority",BLUE,horizontal=False,sort_desc=False,sort_by_cat=True)
bar(p1,"region",332,466,296,232,RG,"Total Operations","Operations by region",BLUE)
bar(p1,"chan",640,466,296,232,CH,"Total Operations","Operations by channel",BLUE)
insights(p1,"ins",948,466,308,232,["Insight - Top Volume Operation Type","Insight - Most SLA Breaches (Operation Type)","Insight - Highest SLA Breach Rate (Priority)","Insight - Region With Most Exceptions","Insight - Peak Month By Volume"],"Executive insights (live, follow filters)")

# ================= PAGE 2
p2=Page("perf","Operational Performance Analysis")
header(p2,"Operational Performance Analysis","Processing time, volume flow and status mix by operation type, region, priority and channel")
slicer_row(p2,with_status=True)
cards(p2,128,82,[("Total Operations","Total operations",NAVY),("Completed Operations","Completed",TEAL),("Pending Operations","Pending",ORANGE),
    ("Failed Operations","Failed",RED),("Escalated Operations","Escalated",RED),("Completion Rate %","Completion rate",TEAL),
    ("Average Processing Hours","Avg processing hours",NAVY),("Average SLA Target Hours","Avg SLA target (hrs)",GREY)])
line(p2,"flow",24,222,512,232,MY,["Total Operations","Operations Completed (by Completion Date)"],"Received vs completed per month",[BLUE,TEAL],legend=True,subtitle="Jan 2026: run-off of Dec 2025 receipts only (no receipts after 31 Dec 2025)")
bar(p2,"hrs_type",548,222,348,232,OT,"Average Processing Hours","Avg processing hours by operation type",BLUE)
bar(p2,"vol_type",908,222,348,232,OT,"Total Operations","Operations by operation type",NAVY)
bar(p2,"hrs_region",24,466,402,232,RG,"Average Processing Hours","Avg processing hours by region",BLUE)
bar(p2,"hrs_prio",438,466,402,232,PR,"Average Processing Hours","Avg processing hours by priority",BLUE,horizontal=False,sort_desc=False,sort_by_cat=True)
bar(p2,"hrs_chan",852,466,404,232,CH,"Average Processing Hours","Avg processing hours by channel",BLUE)

# ================= PAGE 3
p3=Page("risk","SLA & Operational Risk Analysis",h=900)
header(p3,"SLA & Operational Risk Analysis","SLA breaches, exceptions and rework  |  SLA covers completed operations; exception and rework rates cover all")
slicer_row(p3)
cards(p3,128,82,[("SLA Compliance %","SLA compliance",TEAL),("SLA Breach Count","SLA breaches",RED),("SLA Breach Rate","SLA breach rate",RED),
    ("Exception Count","Exceptions",ORANGE),("Exception Rate %","Exception rate",ORANGE),("Rework Count","Reworked ops",ORANGE),("Rework Rate %","Rework rate",ORANGE)])
W4=296
xs=[24,332,640,948]
bar(p3,"sla_type",xs[0],222,W4,210,OT,"SLA Compliance %","SLA compliance % by operation type",TEAL)
bar(p3,"sla_prio",xs[1],222,W4,210,PR,"SLA Compliance %","SLA compliance % by priority",TEAL,horizontal=False,sort_desc=False,sort_by_cat=True)
bar(p3,"sla_region",xs[2],222,W4,210,RG,"SLA Compliance %","SLA compliance % by region",TEAL)
line(p3,"sla_trend",xs[3],222,308,210,MY,["SLA Compliance %"],"SLA compliance % by month",[TEAL])
bar(p3,"exc_type",xs[0],444,W4,210,OT,"Exception Count","Exceptions by operation type",ORANGE)
bar(p3,"exc_region",xs[1],444,W4,210,RG,"Exception Rate %","Exception rate by region",ORANGE)
bar(p3,"exc_prio",xs[2],444,W4,210,PR,"Exception Rate %","Exception rate by priority",ORANGE,horizontal=False,sort_desc=False,sort_by_cat=True)
bar(p3,"exc_chan",xs[3],444,308,210,CH,"Exception Rate %","Exception rate by channel",ORANGE)
bar(p3,"rw_type",xs[0],666,W4,210,OT,"Rework Rate %","Rework rate by operation type",RED)
bar(p3,"rw_region",xs[1],666,W4,210,RG,"Rework Rate %","Rework rate by region",RED)
bar(p3,"rw_prio",xs[2],666,W4,210,PR,"Rework Rate %","Rework rate by priority",RED,horizontal=False,sort_desc=False,sort_by_cat=True)
insights(p3,"ins",xs[3],666,308,210,["Insight - Most SLA Breaches (Operation Type)","Insight - Highest SLA Breach Rate (Priority)","Insight - Highest Exception Rate (Channel)","Insight - Highest Rework Rate (Operation Type)"],"Where to look first (live)")

# ================= PAGE 4  Root cause & drivers
p4=Page("drivers","Root Cause & Drivers")
header(p4,"Root Cause & Drivers","What moves SLA breaches: intake completeness, exceptions, workload and priority  |  Associations, not proven causes")
slicer_row(p4)
cards(p4,128,82,[("SLA Breach Rate","SLA breach rate",RED),("SLA Breach Count","SLA breaches",RED),("Exception Rate %","Exception rate",ORANGE),
    ("Rework Rate %","Rework rate",ORANGE),("Open Backlog","Open backlog (pending + escalated)",NAVY),("Stale Pending (over 90 days)","Pending > 90 days",ORANGE)])
IC=C(T,"intake_completeness"); ES=C(T,"exception_status"); WB=C(T,"workload_band"); AB=C(T,"age_band")
bar(p4,"br_intake",24,222,296,232,IC,"SLA Breach Rate","SLA breach rate by intake completeness",RED)
bar(p4,"br_exc",332,222,296,232,ES,"SLA Breach Rate","SLA breach rate by exception status",RED)
bar(p4,"br_wl",640,222,296,232,WB,"SLA Breach Rate","SLA breach rate by team workload",ORANGE,horizontal=False,sort_by_cat=True)
bar(p4,"br_prio",948,222,308,232,PR,"SLA Breach Rate","SLA breach rate by priority",ORANGE,horizontal=False,sort_by_cat=True)
bar(p4,"exc_intake",24,466,296,232,IC,"Exception Rate %","Exception rate by intake completeness",ORANGE)
bar(p4,"share_prio",332,466,296,232,PR,"Share of SLA Breaches","Share of all breaches by priority",BLUE,horizontal=False,sort_by_cat=True)
bar(p4,"backlog_age",640,466,296,232,AB,"Open Backlog Operations (by age)","Open backlog by age (as of latest received date)",NAVY,horizontal=False,sort_by_cat=True)
p4.add("howto","textbox",948,466,308,232,objects={"general":[{"properties":{"paragraphs":[
  {"textRuns":[{"value":"How to read this page","textStyle":{"fontSize":"11pt","fontWeight":"bold","color":NAVY,"fontFamily":FONT}}]},
  {"textRuns":[{"value":"Bars compare breach rates for groups of completed operations. Large gaps (intake completeness, exceptions) are strong drivers; small gaps (region, channel) are not.","textStyle":{"fontSize":"9pt","color":INK,"fontFamily":FONT}}]},
  {"textRuns":[{"value":"These are associations in synthetic data. They show where to look first, not proven causes.","textStyle":{"fontSize":"9pt","color":INK,"fontFamily":FONT}}]},
  {"textRuns":[{"value":"Backlog age is measured against the latest received date in the data, not today.","textStyle":{"fontSize":"9pt","color":INK,"fontFamily":FONT}}]}]}}]},
  vco=vc_title("Notes"))

# ================= PAGE 5  Data quality & pipeline
p5=Page("dq","Data Quality & Pipeline")
header(p5,"Data Quality & Pipeline","What the pipeline loaded, rejected, repaired and flagged  |  Nothing is dropped silently")
cards(p5,84,82,[("DQ Raw Records","Raw records",NAVY),("DQ Clean Records","Loaded (clean)",TEAL),("DQ Rejected Records","Rejected",RED),
    ("DQ Acceptance Rate %","Acceptance rate %",TEAL),("DQ Uniqueness %","Uniqueness %",TEAL),("DQ Validity %","Validity %",TEAL),
    ("DQ Region Imputed","Region set to Unknown",ORANGE),("DQ Mean Quality Score","Mean quality score",NAVY)])
RR=lambda c: C("dq_rule_results",c)
p5.add("rules","tableEx",24,178,760,300,query={"queryState":{"Values":{"projections":[proj(RR("rule_id")),proj(RR("rule_name")),proj(RR("stage")),proj(RR("severity")),proj(RR("rows_affected")),proj(RR("pct_of_raw"))]}}},
  objects={"grid":[{"properties":{"gridVertical":b(False),"rowPadding":n(3),"textSize":n(9)}}],
   "columnHeaders":[{"properties":{"fontColor":col("#FFFFFF"),"backColor":col(NAVY),"fontSize":n(9),"fontFamily":s(FONT+" Semibold")}}],
   "values":[{"properties":{"fontColor":col(INK),"fontSize":n(9),"fontFamily":s(FONT)}}]},vco=vc_title("Validation rules: rows affected (reject = removed to rejected file, fix = repaired, flag = kept and marked)"))
bar(p5,"rule_bar",796,178,460,300,RR("rule_name"),"Rule Rows Affected","Rows affected per rule",ORANGE)
p5.add("diag","multiRowCard",24,490,760,214,query={"queryState":{"Values":{"projections":[proj(Mz(m)) for m in ["Total Operations","Diag - Row Count","Completed Operations","Diag - Completed Rows With Hours","Diag - Sum Processing Hours","Average Processing Hours","Average SLA Target Hours","SLA Compliance %"]]}}},
  objects={"dataLabels":[{"properties":{"color":col(NAVY),"fontSize":n(12),"fontFamily":s(FONT+" Semibold")}}],"cardTitle":[{"properties":{"color":col(GREY),"fontSize":n(8),"fontFamily":s(FONT)}}],
           "card":[{"properties":{"outline":s("None"),"barShow":b(True),"barColor":col(BLUE)}}]},
  vco=vc_title("Measure reconciliation (diagnostic): each pair should agree"))
p5.add("dqnote","textbox",796,490,460,214,objects={"general":[{"properties":{"paragraphs":[
  {"textRuns":[{"value":"Reading this page","textStyle":{"fontSize":"11pt","fontWeight":"bold","color":NAVY,"fontFamily":FONT}}]},
  {"textRuns":[{"value":"Raw = Loaded + Rejected. Rejected records are listed with a reason in reports/data_quality/dq_rejected_records.csv.","textStyle":{"fontSize":"9pt","color":INK,"fontFamily":FONT}}]},
  {"textRuns":[{"value":"The diagnostic card repeats the processing-hours and SLA-target measures next to the row counts they depend on. If a value here is blank, the column did not load as numbers; check the DataFolder parameter.","textStyle":{"fontSize":"9pt","color":INK,"fontFamily":FONT}}]}]}}]},
  vco=vc_title("Notes"))

pages=[p1,p2,p3,p4,p5]
for p in pages: p.write()
wj(f"{RP}/definition/pages/pages.json",{"$schema":f"{SCH}/pagesMetadata/1.1.0/schema.json","pageOrder":[p.name for p in pages],"activePageName":p1.name})
wj(f"{RP}/definition/version.json",{"$schema":f"{SCH}/versionMetadata/1.0.0/schema.json","version":"2.0.0"})

# theme
os.makedirs(f"{RP}/StaticResources/RegisteredResources",exist_ok=True)
os.makedirs(f"{RP}/StaticResources/SharedResources/BaseThemes",exist_ok=True)
shutil.copy(os.path.join(HERE,"Fluent2-CY26SU10.json"),f"{RP}/StaticResources/SharedResources/BaseThemes/Fluent2-CY26SU10.json")
theme={"name":"ROIP Navy","dataColors":[BLUE,TEAL,ORANGE,RED,GREY,"#7C3AED","#0EA5E9","#94A3B8"],
 "background":CARD,"foreground":INK,"tableAccent":NAVY,"good":TEAL,"neutral":ORANGE,"bad":RED,
 "textClasses":{"label":{"fontFace":FONT,"fontSize":10,"color":INK},"title":{"fontFace":FONT+" Semibold","fontSize":11,"color":INK},
  "callout":{"fontFace":FONT+" Semibold","fontSize":24,"color":NAVY},"header":{"fontFace":FONT+" Semibold","fontSize":11,"color":INK}}}
wj(f"{RP}/StaticResources/RegisteredResources/ROIP_Navy_Theme.json",theme)
wj(f"{RP}/definition/report.json",{"$schema":f"{SCH}/report/3.3.0/schema.json",
 "themeCollection":{"baseTheme":{"name":"Fluent2-CY26SU10","reportVersionAtImport":{"visual":"2.14.0","report":"3.4.0","page":"2.3.1"},"type":"SharedResources"},
                    "customTheme":{"name":"ROIP_Navy_Theme.json","reportVersionAtImport":{"visual":"2.14.0","report":"3.4.0","page":"2.3.1"},"type":"RegisteredResources"}},
 "resourcePackages":[{"name":"SharedResources","type":"SharedResources","items":[{"name":"Fluent2-CY26SU10","path":"BaseThemes/Fluent2-CY26SU10.json","type":"BaseTheme"}]},
                     {"name":"RegisteredResources","type":"RegisteredResources","items":[{"name":"ROIP_Navy_Theme.json","path":"ROIP_Navy_Theme.json","type":"CustomTheme"}]}],
 "settings":{"useStylableVisualContainerHeader":True,"exportDataMode":"AllowSummarized","defaultDrillFilterOtherVisuals":True,"allowChangeFilterTypes":True,"useEnhancedTooltips":True,"useDefaultAggregateDisplayName":True}})
wj(f"{RP}/definition.pbir",{"version":"4.0","datasetReference":{"byPath":{"path":"../ROIP_Operations_Intelligence.SemanticModel"}}})
wj(f"{OUT}/ROIP_Operations_Intelligence.pbip",{"version":"1.0","artifacts":[{"report":{"path":"ROIP_Operations_Intelligence.Report"}}],"settings":{"enableAutoRecovery":True}})
for item,name in (("Report","ROIP_Operations_Intelligence.Report"),("SemanticModel","ROIP_Operations_Intelligence.SemanticModel")):
    wj(f"{OUT}/{name}/.platform",{"$schema":"https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
       "metadata":{"type":item,"displayName":"ROIP Operations Intelligence"},"config":{"version":"2.0","logicalId":gid("logical-"+item)}})
open(f"{OUT}/.gitignore","w").write("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
print("report written:",sum(len(p.vis) for p in pages),"visuals")
