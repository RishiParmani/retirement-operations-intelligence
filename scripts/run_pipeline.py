"""End-to-end pipeline: generate synthetic data -> ETL/validation -> KPI + group summaries.

    python scripts/run_pipeline.py                 # full 200,000-row run (seed 42)
    python scripts/run_pipeline.py --rows 20000    # quick run
    python scripts/run_pipeline.py --skip-generate # reuse existing data/raw/operations_raw.csv
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.roip import config as C
from src.roip.data_generation import generate_operations
from src.roip.etl import run_etl
from src.roip.kpis import kpi_summary, group_kpis
from src.roip.utils import get_logger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=C.N_ROWS)
    ap.add_argument("--seed", type=int, default=C.SEED)
    ap.add_argument("--skip-generate", action="store_true")
    a = ap.parse_args()
    log = get_logger(log_file=C.LOG_DIR / "pipeline.log")
    if not a.skip_generate:
        log.info("Generating %s synthetic rows (seed %s)", f"{a.rows:,}", a.seed)
        C.RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_operations(a.rows, a.seed).to_csv(C.RAW_PATH, index=False)
    result = run_etl(logger=log)
    clean = pd.read_csv(C.PROCESSED_PATH)
    C.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = kpi_summary(clean)
    (C.REPORTS_DIR / "kpi_summary.json").write_text(json.dumps(summary, indent=2))
    for col, name in [("processing_team", "team_performance"), ("operation_type", "operation_performance")]:
        group_kpis(clean, col).round(4).to_csv(C.REPORTS_DIR / f"{name}.csv", index=False)
    log.info("KPI summary written: %s", json.dumps(summary))
    print(json.dumps({"etl": {k: v for k, v in result.items() if k != "dq"}, "kpis": summary}, indent=2))


if __name__ == "__main__":
    main()
