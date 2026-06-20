"""Publication figures (brief section 18 -> 08_figures). PNG (>=300 dpi) + PDF."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix
from sklearn.calibration import calibration_curve

from . import utils
from .preprocessing import coerce_frame

plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3})
COLORS = {"logistic": "#1f77b4", "random_forest": "#2ca02c", "xgboost": "#d62728"}
LABEL = {"logistic": "Logistic Reg.", "random_forest": "Random Forest",
         "xgboost": "XGBoost"}


def savefig(fig, cfg, name):
    out = utils.out_dir(cfg, "08_figures")
    dpi = cfg["figures"]["dpi"]
    for ext in cfg["figures"]["formats"]:
        fig.savefig(out / f"{name}.{ext}", dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _probs(state):
    test = state["test"]; numeric, categorical = state["numeric"], state["categorical"]
    y = test["target_next_year"].values
    return {m: pipe.predict_proba(coerce_frame(test, numeric, categorical))[:, 1]
            for m, pipe in state["finals"].items()}, y


def class_distribution(state, cfg):
    built = state["built"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    cd = built.groupby("split")["target_next_year"].agg(["size", "sum"])
    cd.columns = ["n", "positives"]
    cd = cd.reindex(["dev", "test", "unused_no_positive_post_test"]).dropna()
    ax[0].bar(cd.index, cd["n"], color="#bbb", label="total")
    ax[0].bar(cd.index, cd["positives"], color="#d62728", label="distressed")
    ax[0].set_title("Rows & positives by split"); ax[0].legend()
    ax[0].tick_params(axis="x", rotation=20)
    yr = built.groupby("target_year")["target_next_year"].agg(["size", "sum"])
    ax[1].bar(yr.index, yr["size"], color="#bbb", label="total")
    ax[1].bar(yr.index, yr["sum"], color="#d62728", label="distressed")
    ax[1].set_title("Rows & positives by target_year"); ax[1].legend()
    fig.tight_layout(); savefig(fig, cfg, "fig_class_distribution")


def missing_data(state, cfg):
    import pandas as pd
    p = utils.out_dir(cfg, "01_data_audit") / "missingness_by_split.csv"
    if not p.exists():
        return
    md = pd.read_csv(p)
    piv = md.pivot(index="feature", columns="split", values="pct_missing").fillna(0)
    fig, ax = plt.subplots(figsize=(8, 6))
    piv.plot(kind="barh", ax=ax)
    ax.set_xlabel("% missing"); ax.set_title("Missingness by split")
    fig.tight_layout(); savefig(fig, cfg, "fig_missing_data")


def roc_pr_curves(state, cfg):
    probs, y = _probs(state)
    fig, ax = plt.subplots(figsize=(6, 6))
    for m, p in probs.items():
        fpr, tpr, _ = roc_curve(y, p)
        from sklearn.metrics import roc_auc_score
        ax.plot(fpr, tpr, color=COLORS[m], label=f"{LABEL[m]} (AUC={roc_auc_score(y,p):.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR"); ax.set_title("ROC — test")
    ax.legend(); fig.tight_layout(); savefig(fig, cfg, "fig_roc_curves")

    fig, ax = plt.subplots(figsize=(6, 6))
    for m, p in probs.items():
        prec, rec, _ = precision_recall_curve(y, p)
        from sklearn.metrics import average_precision_score
        ax.plot(rec, prec, color=COLORS[m], label=f"{LABEL[m]} (AP={average_precision_score(y,p):.3f})")
    ax.axhline(y.mean(), ls="--", color="k", alpha=0.5, label=f"baseline={y.mean():.3f}")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_title("Precision-Recall — test")
    ax.legend(); fig.tight_layout(); savefig(fig, cfg, "fig_precision_recall_curves")


def confusion_matrices(state, cfg):
    probs, y = _probs(state)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (m, p) in zip(axes, probs.items()):
        t = state["thresholds"][m]["primary_threshold"]
        cm = confusion_matrix(y, (p >= t).astype(int), labels=[0, 1])
        ax.imshow(cm, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=14)
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["pred 0", "pred 1"]); ax.set_yticklabels(["true 0", "true 1"])
        ax.set_title(f"{LABEL[m]} @thr={t:.2f}")
    fig.suptitle("Confusion matrices — test (primary threshold)")
    fig.tight_layout(); savefig(fig, cfg, "fig_confusion_matrices")


def calibration_curves(state, cfg):
    probs, y = _probs(state)
    fig, ax = plt.subplots(figsize=(6, 6))
    for m, p in probs.items():
        try:
            frac, mean_pred = calibration_curve(y, p, n_bins=5, strategy="quantile")
            ax.plot(mean_pred, frac, "o-", color=COLORS[m], label=LABEL[m])
        except Exception:
            pass
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("Mean predicted prob"); ax.set_ylabel("Observed frequency")
    ax.set_title("Calibration — test"); ax.legend()
    fig.tight_layout(); savefig(fig, cfg, "fig_calibration_curves")

    # predicted-probability distributions per class
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, (m, p) in zip(axes, probs.items()):
        ax.hist(p[y == 0], bins=20, alpha=0.6, label="non-distressed", color="#888")
        ax.hist(p[y == 1], bins=20, alpha=0.8, label="distressed", color="#d62728")
        ax.set_title(LABEL[m]); ax.set_xlabel("predicted prob")
    axes[0].legend(); fig.suptitle("Predicted probability distribution — test")
    fig.tight_layout(); savefig(fig, cfg, "fig_prob_distribution")


def threshold_performance(state, cfg):
    import pandas as pd
    p = utils.out_dir(cfg, "06_metrics") / "threshold_analysis.csv"
    if not p.exists():
        return
    ta = pd.read_csv(p)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, m in zip(axes, ["logistic", "random_forest", "xgboost"]):
        sub = ta[ta["model"] == m]
        for col in ["f1", "recall", "precision", "balanced_accuracy"]:
            ax.plot(sub["threshold"], sub[col], label=col)
        tp = state["thresholds"][m]["primary_threshold"]
        ax.axvline(tp, ls="--", color="k", alpha=0.6)
        ax.set_title(f"{LABEL[m]} (val OOF)"); ax.set_xlabel("threshold")
    axes[0].legend(fontsize=8); fig.suptitle("Threshold-performance (validation)")
    fig.tight_layout(); savefig(fig, cfg, "fig_threshold_performance")


def coefficient_plot(state, cfg):
    import pandas as pd
    p = utils.out_dir(cfg, "07_explainability") / "logistic_coefficients.csv"
    if not p.exists():
        return
    co = pd.read_csv(p).reindex(
        pd.read_csv(p)["coefficient"].abs().sort_values(ascending=False).index)
    co = co.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh(co["feature"], co["coefficient"],
            color=["#d62728" if v > 0 else "#1f77b4" for v in co["coefficient"]])
    ax.axvline(0, color="k", lw=0.8)
    ax.set_title("Logistic Regression — top |coefficients|")
    fig.tight_layout(); savefig(fig, cfg, "fig_coefficient_plot")


def feature_importance(state, cfg):
    import pandas as pd
    out = utils.out_dir(cfg, "07_explainability")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, m in zip(axes, ["random_forest", "xgboost"]):
        f = out / f"{ 'rf' if m=='random_forest' else 'xgb'}_feature_importance.csv"
        if not f.exists():
            continue
        fi = pd.read_csv(f).head(15).iloc[::-1]
        ax.barh(fi["feature"], fi["importance"], color=COLORS[m])
        ax.set_title(f"{LABEL[m]} importance")
    fig.tight_layout(); savefig(fig, cfg, "fig_feature_importance")


def run_all_basic(state, cfg):
    class_distribution(state, cfg)
    missing_data(state, cfg)
    roc_pr_curves(state, cfg)
    confusion_matrices(state, cfg)
    calibration_curves(state, cfg)
    threshold_performance(state, cfg)
    coefficient_plot(state, cfg)
    feature_importance(state, cfg)
    print("[08] base figures saved")
