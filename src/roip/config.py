"""Central configuration. No machine-specific paths: everything is relative to the project
root unless overridden with environment variables (see .env.example)."""
from __future__ import annotations
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines) so no extra dependency is required."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.environ.get("ROIP_DATA_DIR", PROJECT_ROOT / "data"))
REPORTS_DIR = Path(os.environ.get("ROIP_REPORTS_DIR", PROJECT_ROOT / "reports"))
RAW_PATH = DATA_DIR / "raw" / "operations_raw.csv"
PROCESSED_PATH = DATA_DIR / "processed" / "operations_clean.csv"
REJECTED_PATH = DATA_DIR / "rejected" / "operations_rejected.csv"
DQ_DIR = REPORTS_DIR / "data_quality"
LOG_DIR = PROJECT_ROOT / "logs"

SEED = int(os.environ.get("ROIP_SEED", 42))
N_ROWS = int(os.environ.get("ROIP_ROWS", 200_000))

# ---- reference data used by validation rules -------------------------------------------------
VALID_TEAMS = {"Team Alpha", "Team Beta", "Team Gamma", "Team Delta", "Team Epsilon"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}
VALID_STATUSES = {"Completed", "Pending", "Failed", "Escalated"}
VALID_CHANNELS = {"Online", "Phone", "Branch", "Mail", "Advisor"}
VALID_REGIONS = {"North", "South", "East", "West", "Central"}   # 'Unknown' is assigned by the ETL
SLA_POLICY_HOURS = {  # business rule: SLA target by operation type (hours)
    "Contribution Processing": 24, "Withdrawal Processing": 48, "Fund Transfer": 24,
    "Rollover Processing": 72, "Account Maintenance": 48, "Beneficiary Update": 48,
    "Distribution Request": 72, "Plan Administration": 96, "Customer Service Request": 24,
}
FINANCIAL_OPERATION_TYPES = {"Contribution Processing", "Withdrawal Processing", "Fund Transfer",
                             "Rollover Processing", "Distribution Request"}
REQUIRED_FIELDS = ["operation_id", "operation_type", "received_at", "priority", "status", "sla_target_hours"]

# ---- thresholds ------------------------------------------------------------------------------
STALE_PENDING_DAYS = 90        # pending longer than this at the data cut-off is flagged as stale
OUTLIER_IQR_MULTIPLIER = 3.0   # "far out" fence on processing_hours of completed operations
