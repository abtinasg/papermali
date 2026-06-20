"""Expanding-window temporal cross-validation (brief section 7)."""
from __future__ import annotations
import numpy as np
import pandas as pd


def expanding_folds(dev: pd.DataFrame, cfg):
    """Yield (fold_id, train_mask, val_mask) over dev using target_year.

    Fold k: train on target_year <= train_max_year, validate on val_year.
    If a validation year has no positives the adjacent later validation rows are
    merged in (documented), preserving chronological order (brief allowance).
    """
    folds = cfg["split"]["cv_folds"]
    y = dev["target_year"].values
    tgt = dev["target_next_year"].values
    out = []
    for i, f in enumerate(folds, 1):
        train_mask = y <= f["train_max_year"]
        val_mask = y == f["val_year"]
        # merge-forward safeguard if validation fold has no positive
        if tgt[val_mask].sum() == 0:
            merged = val_mask.copy()
            for later in sorted(set(y[y > f["val_year"]])):
                merged = merged | (y == later)
                if tgt[merged].sum() > 0:
                    break
            val_mask = merged & (y > f["train_max_year"])
        out.append((i, train_mask, val_mask))
    return out


def fold_summary(dev: pd.DataFrame, cfg) -> pd.DataFrame:
    recs = []
    for fid, tr, va in expanding_folds(dev, cfg):
        recs.append({
            "fold": fid,
            "n_train": int(tr.sum()), "pos_train": int(dev["target_next_year"].values[tr].sum()),
            "n_val": int(va.sum()), "pos_val": int(dev["target_next_year"].values[va].sum()),
            "train_years": sorted(set(dev["target_year"].values[tr].tolist())),
            "val_years": sorted(set(dev["target_year"].values[va].tolist())),
        })
    return pd.DataFrame(recs)
