import pandas as pd

def kpi_summary(df):
    completed=df[df.status=="Completed"]
    return {
        "total_operations":int(len(df)),"completed_operations":int(len(completed)),"pending_operations":int((df.status=="Pending").sum()),
        "failed_operations":int((df.status=="Failed").sum()),"sla_compliance_pct":round(100*(1-completed.sla_breached.mean()),2) if len(completed) else 0,
        "avg_processing_hours":round(completed.processing_hours.mean(),2) if len(completed) else 0,
        "exception_rate_pct":round(100*df.exception_flag.mean(),2),"rework_rate_pct":round(100*df.rework_flag.mean(),2),
        "total_transaction_amount":round(float(df.transaction_amount.sum()),2)
    }

def group_performance(df, group_col):
    return df.groupby(group_col,dropna=False).agg(operations=("operation_id","count"),avg_processing_hours=("processing_hours","mean"),sla_breach_rate=("sla_breached","mean"),exception_rate=("exception_flag","mean"),rework_rate=("rework_flag","mean")).sort_values("operations",ascending=False)
