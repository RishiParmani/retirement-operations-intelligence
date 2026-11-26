import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from roip import config  # noqa: E402
from roip.data_generation import generate_operations  # noqa: E402,F401


@pytest.fixture(scope="session")
def raw_small():
    """Small deterministic raw extract (fast) - the same generator as the full project."""
    return generate_operations(n=6000, seed=config.SEED)


@pytest.fixture(scope="session")
def pipeline_small(tmp_path_factory, raw_small):
    from roip.etl import run_etl
    d = tmp_path_factory.mktemp("etl")
    raw_path = d / "raw.csv"
    raw_small.to_csv(raw_path, index=False)
    out = run_etl(raw_path=raw_path, processed_path=d / "clean.csv", rejected_path=d / "rej.csv", report_dir=d / "dq")
    return dict(dir=d, raw=raw_small, out=out)


@pytest.fixture(scope="session")
def full_clean():
    p = config.PROCESSED_PATH
    if not p.exists():
        pytest.skip("run scripts/run_pipeline.py first")
    return pd.read_csv(p, parse_dates=["received_at", "completed_at"])
