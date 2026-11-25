import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.roip.data_generation import generate_operations

def test_generator_schema_and_size():
    df=generate_operations(1000,7)
    assert len(df)>=1000
    assert "operation_id" in df.columns
    assert df.operation_type.notna().all()
    assert set(df.priority.unique()) <= {"Low","Medium","High","Critical"}
