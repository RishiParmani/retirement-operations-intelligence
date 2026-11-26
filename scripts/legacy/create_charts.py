import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import matplotlib.pyplot as plt

if __name__=='__main__':
    df=pd.read_csv('data/processed/operations_clean.csv')
    Path('reports/figures').mkdir(parents=True,exist_ok=True)
    monthly=df.groupby(['received_year','received_month']).agg(volume=('operation_id','count'),breach=('sla_breached','mean')).reset_index()
    monthly['month']=monthly.received_year.astype(str)+'-'+monthly.received_month.astype(str).str.zfill(2)
    plt.figure(figsize=(12,5)); plt.plot(monthly.month,monthly.volume); plt.xticks(rotation=60); plt.title('Monthly Operations Volume'); plt.tight_layout(); plt.savefig('reports/figures/monthly_volume.png',dpi=150); plt.close()
    bytype=df.groupby('operation_type').agg(volume=('operation_id','count'),breach=('sla_breached','mean')).sort_values('breach')
    plt.figure(figsize=(10,6)); bytype.breach.plot(kind='barh'); plt.title('SLA Breach Rate by Operation Type'); plt.xlabel('Breach rate'); plt.tight_layout(); plt.savefig('reports/figures/breach_by_operation.png',dpi=150); plt.close()
    team=df.groupby('processing_team').agg(avg_hours=('processing_hours','mean'),workload=('team_workload','mean'))
    plt.figure(figsize=(8,6)); plt.scatter(team.workload,team.avg_hours); 
    for name,row in team.iterrows(): plt.annotate(name,(row.workload,row.avg_hours))
    plt.title('Team Workload vs Processing Hours'); plt.xlabel('Average workload'); plt.ylabel('Average processing hours'); plt.tight_layout(); plt.savefig('reports/figures/workload_vs_hours.png',dpi=150); plt.close()
