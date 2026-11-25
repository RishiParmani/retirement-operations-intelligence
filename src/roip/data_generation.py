from pathlib import Path
import numpy as np
import pandas as pd


OPERATION_SLA = {
    "Contribution Processing": 24, "Withdrawal Processing": 48,
    "Fund Transfer": 24, "Rollover Processing": 72,
    "Account Maintenance": 48, "Beneficiary Update": 48,
    "Distribution Request": 72, "Plan Administration": 96,
    "Customer Service Request": 24,
}

def generate_operations(n=200_000, seed=42):
    """Create reproducible synthetic retirement operations with realistic relationships."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2025-01-01")
    received = start + pd.to_timedelta(rng.integers(0, 365, n), unit="D") + pd.to_timedelta(rng.integers(0, 24, n), unit="h")
    operation_types = list(OPERATION_SLA)
    op_type = rng.choice(operation_types, n, p=[.16,.12,.13,.10,.13,.09,.08,.07,.12])
    priorities = rng.choice(["Low","Medium","High","Critical"], n, p=[.18,.48,.27,.07])
    teams = rng.choice(["Team Alpha","Team Beta","Team Gamma","Team Delta","Team Epsilon"], n)
    regions = rng.choice(["North","South","East","West","Central"], n)
    channels = rng.choice(["Online","Phone","Branch","Mail","Advisor"], n, p=[.38,.22,.16,.08,.16])
    segments = rng.choice(["Retail","High Net Worth","Institutional","Small Business"], n, p=[.60,.15,.15,.10])
    workload = rng.integers(35, 125, n)
    missing_info = rng.random(n) < .055
    exception = rng.random(n) < (.08 + missing_info*.42)
    rework = rng.random(n) < (.035 + exception*.30)
    base_hours = np.array([OPERATION_SLA[x] for x in op_type]) * rng.uniform(.15,.80,n)
    priority_multiplier = np.select([priorities=="Critical", priorities=="High", priorities=="Low"],[.65,.8,1.15],default=1.0)
    duration = base_hours * priority_multiplier * (1 + workload/170) * (1 + exception*.65 + rework*.55 + missing_info*.8)
    duration *= rng.lognormal(mean=0, sigma=.38, size=n)
    sla = np.array([OPERATION_SLA[x] for x in op_type])
    status = np.where(rng.random(n)<.035,"Pending", "Completed")
    status = np.where((status=="Completed") & (rng.random(n)<.012),"Failed",status)
    status = np.where((status=="Completed") & (exception) & (rng.random(n)<.012),"Escalated",status)
    completed = received + pd.to_timedelta(duration, unit="h")
    completed = pd.Series(completed).where(status=="Completed", pd.NaT)
    assigned = received + pd.to_timedelta(rng.integers(0,6,n), unit="h")
    started = assigned + pd.to_timedelta(rng.integers(0,12,n), unit="h")
    amount = np.where(np.isin(op_type,["Contribution Processing","Withdrawal Processing","Fund Transfer","Rollover Processing","Distribution Request"]), rng.lognormal(7.5,1.2,n),0).round(2)
    exception_types = rng.choice(["Missing Information","Documentation Issue","Validation Failure","System Error","Manual Review","Account Verification","Processing Error","Compliance Review"], n)
    severity = rng.choice(["Low","Medium","High","Critical"],n,p=[.36,.34,.22,.08])
    root_cause = rng.choice(["Incomplete Documentation","Incorrect Data","System Dependency","High Workload","Manual Processing","Validation Failure","Customer Dependency","Operational Error"],n)
    df = pd.DataFrame({
        "operation_id":[f"OP-{i:07d}" for i in range(n)], "customer_id":[f"C-{rng.integers(1,80000):06d}" for _ in range(n)],
        "account_id":[f"A-{rng.integers(1,100000):07d}" for _ in range(n)], "plan_id":[f"P-{rng.integers(1,5000):05d}" for _ in range(n)],
        "operation_type":op_type,"priority":priorities,"channel":channels,"region":regions,"processing_team":teams,
        "team_workload":workload,"customer_segment":segments,"received_at":received,"assigned_at":assigned,"started_at":started,
        "completed_at":completed,"status":status,"exception_flag":exception,"exception_type":np.where(exception,exception_types,"None"),
        "exception_severity":np.where(exception,severity,"None"),"root_cause":np.where(exception,root_cause,"None"),
        "rework_flag":rework,"sla_target_hours":sla,"processing_hours":duration.round(2),
        "sla_breached":(duration>sla).astype(int),"transaction_amount":amount,"currency":"USD",
        "missing_info_flag":missing_info,"received_date":received.date,
    })
    # Inject controlled data quality problems for pipeline testing.
    if n >= 100:
        idx = rng.choice(n, max(1,int(n*.008)), replace=False)
        df.loc[idx,"region"] = None
        idx2 = rng.choice(n, max(1,int(n*.004)), replace=False)
        df.loc[idx2,"processing_team"] = "Unknown Team"
        idx3 = rng.choice(n, max(1,int(n*.003)), replace=False)
        df = pd.concat([df,df.loc[idx3]],ignore_index=True)
    return df

if __name__ == "__main__":
    out=Path("data/raw/operations_raw.csv")
    out.parent.mkdir(parents=True,exist_ok=True)
    data=generate_operations()
    data.to_csv(out,index=False)
    print(f"Generated {len(data):,} rows -> {out}")
    print(data.head())
