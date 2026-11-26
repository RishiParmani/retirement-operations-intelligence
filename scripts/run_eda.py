"""EDA + business-analysis figures and tables.  Usage: python scripts/run_eda.py
Reads data/processed/operations_clean.csv (run scripts/run_pipeline.py first); writes reports/figures/*.png and
reports/insights/*.csv + headline.json.  Every number shown is computed here - none typed by hand."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from roip import config as C
from roip.analysis import build_insights

NAVY, BLUE, TEAL, ORANGE, RED, GREY = "#0B1F3A", "#2563EB", "#0F9D8A", "#F59E0B", "#DC2626", "#64748B"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
                     "axes.titlesize": 12, "font.size": 10, "axes.edgecolor": GREY, "axes.labelcolor": NAVY})
FIG = C.REPORTS_DIR / "figures"; INS = C.REPORTS_DIR / "insights"
FIG.mkdir(parents=True, exist_ok=True); INS.mkdir(parents=True, exist_ok=True)


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, bbox_inches="tight"); plt.close(fig)


def main():
    df = pd.read_csv(C.PROCESSED_PATH, parse_dates=["received_at", "assigned_at", "started_at", "completed_at"])
    ins = build_insights(df)
    h = ins["headline"]
    overall = h["breach_rate_overall"] * 100

    # 1 Received vs completed (Jan 2026 run-off made explicit)
    f = ins["flow"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(f["month"], f["received"], marker="o", color=BLUE, label="Received (by received month)")
    ax.plot(f["month"], f["completed_by_completion_month"], marker="o", color=TEAL, label="Completed (by completion month)")
    ax.axvspan(len(f) - 1.5, len(f) - 0.5, color=ORANGE, alpha=.15)
    ax.annotate("Jan 2026: run-off of Dec-2025\nreceipts. No receipts after 31 Dec 2025.", xy=(len(f) - 1, f["completed_by_completion_month"].iloc[-1]),
                xytext=(len(f) - 5.2, 6500), arrowprops=dict(arrowstyle="->", color=GREY), color=NAVY, fontsize=9)
    ax.set_title("Received vs completed per month"); ax.set_ylabel("operations"); ax.legend(frameon=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right"); save(fig, "01_received_vs_completed.png")

    # 2 breach rate by priority with share of breaches
    p = ins["by_priority"].copy()
    order = ["Critical", "High", "Medium", "Low"]; p = p.set_index("priority").loc[order].reset_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(p["priority"], p["breach_rate"] * 100, color=[RED if v > h["breach_rate_overall"] else BLUE for v in p["breach_rate"]])
    ax.axhline(overall, color=GREY, ls="--"); ax.text(3.45, overall + .6, f"overall {overall:.1f}%", ha="right", color=GREY)
    for i, r in p.iterrows(): ax.text(i, r["breach_rate"] * 100 + .5, f"{r['breach_rate']*100:.1f}%\n({r['share_of_breaches']*100:.0f}% of breaches)", ha="center", fontsize=8.5)
    ax.set_ylim(0, p["breach_rate"].max() * 100 * 1.3); ax.set_title("SLA breach rate by priority"); ax.set_ylabel("% of completed breaching SLA")
    save(fig, "02_breach_by_priority.png")

    # 3 drivers: breach rate with / without
    rows = [("Information missing", h["breach_rate_info_missing"], h["breach_rate_info_complete"]),
            ("Exception raised", h["breach_rate_exception"], h["breach_rate_no_exception"])]
    fig, ax = plt.subplots(figsize=(7, 3.6)); w = .35
    for i, (lab, a, b) in enumerate(rows):
        ax.bar(i - w / 2, a * 100, w, color=RED, label="with factor" if i == 0 else None)
        ax.bar(i + w / 2, b * 100, w, color=BLUE, label="without" if i == 0 else None)
        ax.text(i - w / 2, a * 100 + 1, f"{a*100:.1f}%", ha="center"); ax.text(i + w / 2, b * 100 + 1, f"{b*100:.1f}%", ha="center")
    ax.set_xticks(range(len(rows))); ax.set_xticklabels([r[0] for r in rows]); ax.set_ylabel("breach rate %"); ax.legend(frameon=False)
    ax.set_title("Breach rate with vs without each operational factor"); save(fig, "03_driver_pairs.png")

    # 4 effect sizes
    a = ins["assoc"].sort_values("cramers_v")
    colors = [RED if v == "strong driver" else ORANGE if v == "moderate driver" else GREY for v in a["verdict"]]
    fig, ax = plt.subplots(figsize=(7.5, 4.5)); ax.barh(a["dimension"], a["cramers_v"], color=colors)
    ax.axvline(.08, color=GREY, ls=":"); ax.axvline(.20, color=GREY, ls=":")
    ax.set_title("Association with SLA breach (Cramér's V effect size)"); ax.set_xlabel("effect size  (grey = no practical effect; dotted = heuristic thresholds)")
    save(fig, "04_effect_sizes.png")

    # 5 processing-time distribution vs SLA targets
    c = df[df.status == "Completed"]
    fig, ax = plt.subplots(figsize=(8, 4)); ax.hist(c["processing_hours"].clip(upper=c["processing_hours"].quantile(.99)), bins=60, color=BLUE, alpha=.85)
    ax.axvline(c["processing_hours"].mean(), color=RED, label=f"mean {c['processing_hours'].mean():.1f} h")
    ax.axvline(c["processing_hours"].median(), color=TEAL, label=f"median {c['processing_hours'].median():.1f} h")
    ax.set_title("Processing hours, completed operations (clipped at P99)"); ax.set_xlabel("hours"); ax.legend(frameon=False)
    save(fig, "05_processing_distribution.png")

    # 6 avg hours vs target by type
    t = ins["by_type"]
    fig, ax = plt.subplots(figsize=(8, 4.5)); y = range(len(t))
    ax.barh([i + .2 for i in y], t["avg_processing_hours"], .4, color=BLUE, label="avg hours")
    ax.barh([i - .2 for i in y], t["sla_target_hours"], .4, color=GREY, label="SLA target")
    ax.set_yticks(list(y)); ax.set_yticklabels(t["operation_type"]); ax.legend(frameon=False); ax.set_title("Average processing hours vs SLA target")
    save(fig, "06_hours_vs_target.png")

    # 7 backlog age
    b = ins["backlog"].pivot(index="age_band", columns="status", values="operations")
    fig, ax = plt.subplots(figsize=(7, 4)); b.plot.bar(stacked=True, ax=ax, color=[ORANGE, BLUE]); ax.set_xlabel("")
    ax.set_title(f"Open backlog by age (as of {h['backlog_as_of'][:10]})"); plt.setp(ax.get_xticklabels(), rotation=0); ax.legend(frameon=False)
    save(fig, "07_backlog_age.png")

    # 8 team heatmap-ish
    from roip.kpis import group_kpis
    tm = group_kpis(df, "processing_team").sort_values("sla_compliance")
    fig, ax = plt.subplots(figsize=(7, 3.6)); ax.barh(tm["processing_team"], tm["sla_compliance"] * 100, color=TEAL)
    ax.set_xlim(60, 80); ax.set_title("SLA compliance by team (axis starts at 60% - differences are small)")
    for i, v in enumerate(tm["sla_compliance"] * 100): ax.text(v + .1, i, f"{v:.1f}%", va="center")
    save(fig, "08_team_compliance.png")

    # 9 model comparison + calibration if available
    mpath = C.REPORTS_DIR / "model" / "model_metrics.json"
    if mpath.exists():
        m = json.loads(mpath.read_text())["models"]
        names = [k for k in m if k.endswith("logreg")]; aucs = [m[k]["roc_auc"] for k in names]
        fig, ax = plt.subplots(figsize=(7, 3.8)); ax.bar([n.split("|")[0] for n in names], aucs, color=[GREY, BLUE, TEAL])
        ax.axhline(.5, color=RED, ls="--"); ax.set_ylim(.45, .8); ax.set_title("Temporal hold-out ROC-AUC by information stage")
        for i, v in enumerate(aucs): ax.text(i, v + .005, f"{v:.3f}", ha="center")
        save(fig, "09_model_auc_by_stage.png")

    for k in ["assoc", "by_priority", "by_missing", "by_exception", "by_rework", "by_workload", "by_type", "flow", "monthly_breach",
              "backlog", "distribution", "segments", "cascade"]:
        ins[k].to_csv(INS / f"{k}.csv", index=False)
    (INS / "headline.json").write_text(json.dumps(h, indent=2, default=str))
    print("figures:", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
