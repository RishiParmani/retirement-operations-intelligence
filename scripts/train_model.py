"""Train and evaluate the SLA-breach risk models; writes reports/model/*.json|csv|png."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.roip import config as C
from src.roip.modeling import run_model_study
from src.roip.utils import get_logger

if __name__ == "__main__":
    log = get_logger()
    df = pd.read_csv(C.PROCESSED_PATH)
    study = run_model_study(df)
    art = study.pop("_artifacts")
    out = C.REPORTS_DIR / "model"; out.mkdir(parents=True, exist_ok=True)
    (out / "model_metrics.json").write_text(json.dumps(study, indent=2))
    art["coefs"].to_csv(out / "logreg_coefficients.csv", index=False)
    art["importance"].to_csv(out / "permutation_importance.csv", index=False)
    art["calibration"].to_csv(out / "calibration_deciles.csv", index=False)
    for k, v in study["models"].items():
        log.info("%-18s AUC %.3f  PR-AUC %.3f  top20%% precision %.3f lift %.2f", k, v["roc_auc"], v["pr_auc"],
                 v["top20pct_review"]["precision"], v["top20pct_review"]["lift"])
    for k, v in study["baselines"].items():
        log.info("baseline %-36s AUC %.3f", k, v["roc_auc"])
    log.info("legacy RF (random split, uses exception/rework flags) AUC %.3f", study["legacy_model"]["roc_auc"])
