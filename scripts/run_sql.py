"""Run every query in sql/queries/ on DuckDB and write each result to reports/sql_results/<id>.csv."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from roip import config, sqlrun

out = config.REPORTS_DIR / "sql_results"
out.mkdir(parents=True, exist_ok=True)
for name, df in sqlrun.run_all().items():
    df.to_csv(out / f"{name}.csv", index=False)
    print(f"{name}: {len(df)} rows")
