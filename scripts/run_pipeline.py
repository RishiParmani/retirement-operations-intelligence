import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.roip.data_generation import generate_operations
from src.roip.etl import run_etl
from src.roip.analytics import kpi_summary,group_performance
import json
from pathlib import Path

if __name__=="__main__":
    Path("data/raw").mkdir(parents=True,exist_ok=True)
    raw=generate_operations(200_000,42)
    raw.to_csv("data/raw/operations_raw.csv",index=False)
    result=run_etl()
    clean=__import__('pandas').read_csv("data/processed/operations_clean.csv")
    summary=kpi_summary(clean)
    with open("reports/kpi_summary.json","w") as f: json.dump(summary,f,indent=2)
    group_performance(clean,"processing_team").to_csv("reports/team_performance.csv")
    group_performance(clean,"operation_type").to_csv("reports/operation_performance.csv")
    print(result); print(json.dumps(summary,indent=2))
