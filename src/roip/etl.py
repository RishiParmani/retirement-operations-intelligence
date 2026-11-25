from pathlib import Path
import pandas as pd

VALID_TEAMS={"Team Alpha","Team Beta","Team Gamma","Team Delta","Team Epsilon"}
REQUIRED=["operation_id","operation_type","received_at","priority","status","sla_target_hours"]

def run_etl(raw_path="data/raw/operations_raw.csv", processed_path="data/processed/operations_clean.csv", rejected_path="data/rejected/operations_rejected.csv"):
    df=pd.read_csv(raw_path,parse_dates=["received_at","assigned_at","started_at","completed_at"])
    issues=[]
    for col in REQUIRED:
        bad=df[col].isna()
        if bad.any():
            issues.append(df[bad].assign(rejection_reason=f"Missing required field: {col}"))
            df=df[~bad]
    duplicates=df.duplicated(subset="operation_id",keep="first")
    if duplicates.any():
        issues.append(df[duplicates].assign(rejection_reason="Duplicate operation_id"))
        df=df[~duplicates]
    invalid_team=~df.processing_team.isin(VALID_TEAMS)
    if invalid_team.any():
        issues.append(df[invalid_team].assign(rejection_reason="Invalid team category"))
        df=df[~invalid_team]
    df["region"]=df.region.fillna("Unknown")
    df["exception_flag"]=df.exception_flag.astype(bool)
    df["rework_flag"]=df.rework_flag.astype(bool)
    df["received_at"]=pd.to_datetime(df.received_at,errors="coerce")
    df["received_year"]=df.received_at.dt.year
    df["received_month"]=df.received_at.dt.month
    df["received_week"]=df.received_at.dt.isocalendar().week.astype(int)
    df["received_day_of_week"]=df.received_at.dt.day_name()
    df["processing_hours"]=df.processing_hours.clip(lower=0)
    df["sla_breached"]=((df.processing_hours>df.sla_target_hours)&(df.status=="Completed")).astype(int)
    df["data_quality_score"]=100
    df.loc[df.region=="Unknown","data_quality_score"]-=10
    df.loc[df.exception_flag,"data_quality_score"]-=5
    Path(processed_path).parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(processed_path,index=False)
    if issues:
        pd.concat(issues,ignore_index=True).to_csv(rejected_path,index=False)
    else:
        pd.DataFrame().to_csv(rejected_path,index=False)
    return {"input_rows":len(pd.read_csv(raw_path)),"clean_rows":len(df),"rejected_rows":sum(len(x) for x in issues),"output":processed_path}
