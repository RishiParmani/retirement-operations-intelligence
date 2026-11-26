"""Run the project's SQL against the cleaned data using DuckDB (no server needed).

The .sql files use Postgres-compatible syntax; DuckDB accepts it, which lets the tests execute
every query and reconcile the results with the Python KPI layer.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from . import config

SQL_DIR = config.PROJECT_ROOT / "sql"


def split_statements(sql_text: str) -> list[str]:
    """Split on semicolons that end a line (the files contain no semicolons inside strings)."""
    return [s.strip() for s in re.split(r";\s*(?:\n|$)", sql_text) if s.strip()]


def parse_named_queries(path: Path) -> dict[str, str]:
    """A query file holds blocks introduced by '-- name: <id>'. Returns {id: sql}."""
    text = path.read_text()
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip().rstrip(";") for i in range(1, len(parts), 2)}


def all_queries() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted((SQL_DIR / "queries").glob("*.sql")):
        out.update(parse_named_queries(f))
    return out


def build_database(clean_path=None, rejected_path=None, rule_path=None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    for stmt in split_statements((SQL_DIR / "schema.sql").read_text()):
        con.execute(stmt)
    clean_path = clean_path or config.PROCESSED_PATH
    rejected_path = rejected_path or (config.DQ_DIR / "dq_rejected_records.csv")
    rule_path = rule_path or (config.DQ_DIR / "dq_rule_results.csv")
    con.execute(f"INSERT INTO fact_operations SELECT * FROM read_csv_auto('{clean_path}', header=true)")
    con.execute(f"INSERT INTO dq_rejected_records SELECT * FROM read_csv_auto('{rejected_path}', header=true)")
    con.execute(f"INSERT INTO dq_rule_results SELECT * FROM read_csv_auto('{rule_path}', header=true)")
    for stmt in split_statements((SQL_DIR / "00_load_and_build.sql").read_text()):
        con.execute(stmt)
    return con


def run_all(con=None) -> dict[str, pd.DataFrame]:
    con = con or build_database()
    return {name: con.execute(sql).df() for name, sql in all_queries().items()}
