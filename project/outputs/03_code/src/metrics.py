"""Evaluation metrics, threshold selection, cluster bootstrap (brief section 12)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, roc_auc_score, precision_score, recall_score,
    f1_score, fbeta_score, balanced_accuracy_score, matthews_corrcoef,
    brier_score_loss, log_loss, confusion_matrix,
)


def threshold_free(y_true, y_prob) -> dict:
    y_true = np.asarray(y_true); y_prob = np.asarray(y_prob)
    out = {}
    out["pr_auc"] = float(average_precision_score(y_true, y_prob)) if y_true.sum() > 0 else np.nan
    try:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob)) if len(set(y_true)) > 1 else np.nan
    except ValueError:
        out["roc_auc"] = np.nan
    out["brier"] = float(brier_score_loss(y_true, y_prob))
    try:
        out["log_loss"] = float(log_loss(y_true, np.clip(y_prob, 1e-7, 1 - 1e-7),
                                         labels=[0, 1]))
    except ValueError:
        out["log_loss"] = np.nan
    return out


def thresholded(y_true, y_prob, threshold: float) -> dict:
    y_true = np.asarray(y_true)
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    spec = tn / (tn + fp) if (tn + fp) else np.nan
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "f2": float(fbeta_score(y_true, y_pred, beta=2, zero_division=0)),
        "specificity": float(spec),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)) if len(set(y_pred)) > 1 or len(set(y_true)) > 1 else 0.0,
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def full_metrics(y_true, y_prob, threshold: float) -> dict:
    d = threshold_free(y_true, y_prob)
    d.update(thresholded(y_true, y_prob, threshold))
    return d


def pick_threshold(y_true, y_prob, objective: str, grid_points: int = 200) -> float:
    """Choose threshold maximizing objective (validation only)."""
    y_true = np.asarray(y_true)
    grid = np.unique(np.concatenate([[0.0, 1.0], np.linspace(0, 1, grid_points),
                                     np.asarray(y_prob)]))
    best_t, best_v = 0.5, -np.inf
    for t in grid:
        m = thresholded(y_true, y_prob, t)
        v = m[objective]
        if v > best_v:
            best_v, best_t = v, float(t)
    return best_t


def cluster_bootstrap_ci(df: pd.DataFrame, prob_col: str, y_col: str,
                         cluster_col: str, threshold: float, *, n: int = 1000,
                         alpha: float = 0.05, seed: int = 42) -> pd.DataFrame:
    """95% CIs by resampling clusters (tickers) with replacement (brief section 12)."""
    rng = np.random.default_rng(seed)
    clusters = df[cluster_col].unique()
    groups = {c: df[df[cluster_col] == c] for c in clusters}
    keys = ["pr_auc", "roc_auc", "brier", "precision", "recall", "f1", "f2",
            "specificity", "balanced_accuracy", "mcc"]
    samples = {k: [] for k in keys}
    for _ in range(n):
        drawn = rng.choice(clusters, size=len(clusters), replace=True)
        boot = pd.concat([groups[c] for c in drawn], ignore_index=True)
        if boot[y_col].nunique() < 2:
            continue
        m = full_metrics(boot[y_col].values, boot[prob_col].values, threshold)
        for k in keys:
            samples[k].append(m[k])
    point = full_metrics(df[y_col].values, df[prob_col].values, threshold)
    recs = []
    for k in keys:
        arr = np.asarray(samples[k], float)
        arr = arr[~np.isnan(arr)]
        lo, hi = (np.percentile(arr, [100 * alpha / 2, 100 * (1 - alpha / 2)])
                  if len(arr) else (np.nan, np.nan))
        recs.append({"metric": k, "point": point[k], "ci_low": lo, "ci_high": hi,
                     "n_boot_valid": len(arr)})
    return pd.DataFrame(recs)
