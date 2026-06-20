"""Build the one-year-ahead modeling dataset and the time-based split.

Implements brief sections 3 (target shift), 4 (excluded columns), 5 (feature sets),
7 (temporal split). The original handoff files are read-only inputs; nothing here
overwrites them.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from . import utils


# Raw numeric columns we coerce to float (missing stays NaN, never zero-filled).
_RAW_NUMERIC = [
    "total_assets", "total_liabilities", "equity", "registered_capital",
    "accumulated_loss", "current_assets", "current_liabilities",
    "revenue_period_adjusted", "gross_profit_period_adjusted",
    "operating_profit_period_adjusted", "net_income_period_adjusted",
    "operating_cash_flow_period_adjusted", "financial_expense_period_adjusted",
    "leverage_ratio", "current_ratio", "roa_period_adjusted", "roe_period_adjusted",
    "equity_ratio", "ocf_to_assets_period_adjusted",
    "financial_expense_to_assets_period_adjusted", "profit_margin_period_adjusted",
    "operating_margin_period_adjusted", "gross_margin_period_adjusted",
    "net_margin_period_adjusted", "financial_expense_to_revenue_period_adjusted",
    "asset_turnover_period_adjusted", "revenue_growth_period_adjusted",
    "net_income_growth_period_adjusted", "sales_growth_period_adjusted",
    "accumulated_loss_to_capital_ratio", "debt_to_equity",
    "loss_dummy", "equity_negative_dummy",
]


def _read(path):
    # utf-8-sig strips the BOM so the first column is "row_key" not "﻿row_key".
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def load_raw(cfg) -> tuple[pd.DataFrame, pd.DataFrame]:
    allr = _read(utils.raw_path(cfg, "all_rows_csv"))
    cand = _read(utils.raw_path(cfg, "candidates_csv"))
    for df in (allr, cand):
        df["fiscal_year"] = df["fiscal_year"].astype(int)
        for c in _RAW_NUMERIC:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
    return allr, cand


def _engineer(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    size_col = cfg["features"]["size_source_col"]
    df["log_total_assets"] = np.log1p(df[size_col])
    gp = cfg["features"]["gross_profit_raw_col"]
    if gp in df.columns:
        x = df[gp].astype(float)
        df["gross_profit_period_adjusted_signedlog"] = np.sign(x) * np.log1p(np.abs(x))
    return df


def build_one_year_ahead(cfg) -> tuple[pd.DataFrame, dict]:
    """Shift target one year ahead. Predictor rows = training candidates at year t;
    target = distressed_target_reviewed of same ticker at year t+1 from all_rows."""
    allr, cand = load_raw(cfg)
    label = cfg["target"]["source_label_col"]
    tcol = cfg["target"]["ticker_col"]

    # (ticker, year) -> next-year label, taken from the FULL panel.
    next_label = {(r[tcol], int(r["fiscal_year"])): r[label] for _, r in allr.iterrows()}

    cand = _engineer(cand, cfg)
    audit = {"n_candidates": int(len(cand)), "dropped": {}}
    last_year = int(cand["fiscal_year"].max())
    rows = []
    drop = {"predictor_last_year_no_next_panel_row": 0,
            "next_year_gap_no_row": 0, "next_target_invalid": 0}
    for _, r in cand.iterrows():
        t = int(r["fiscal_year"])
        key = (r[tcol], t + 1)
        if key not in next_label:
            # the t+1 row is absent: either t is the last panel year, or a gap
            drop["predictor_last_year_no_next_panel_row" if t == last_year
                 else "next_year_gap_no_row"] += 1
            continue
        nxt = next_label[key]
        if nxt not in ("0", "1"):
            drop["next_target_invalid"] += 1
            continue
        rr = r.to_dict()
        rr["predictor_year"] = t
        rr["target_year"] = t + 1
        rr["target_next_year"] = int(nxt)
        rows.append(rr)

    built = pd.DataFrame(rows)
    audit["dropped"] = drop
    audit["n_built"] = int(len(built))
    audit["n_positive"] = int(built["target_next_year"].sum())
    audit["positive_rate"] = float(built["target_next_year"].mean())

    built = _assign_split(built, cfg)
    audit["split_counts"] = (
        built.groupby("split")["target_next_year"].agg(["size", "sum"]).rename(
            columns={"size": "n", "sum": "positives"}).to_dict("index"))
    return built, audit


def _assign_split(built: pd.DataFrame, cfg) -> pd.DataFrame:
    s = cfg["split"]
    dev, test = set(s["dev_years"]), set(s["test_years"])
    fold_val = {f["val_year"]: i + 1 for i, f in enumerate(s["cv_folds"])}

    def lab(y):
        if y in test:
            return "test"
        if y in dev:
            return "dev"
        return "unused_no_positive_post_test"

    built = built.copy()
    built["split"] = built["target_year"].map(lab)
    # validation fold id (only meaningful inside dev's expanding-window scheme)
    built["cv_val_fold"] = built["target_year"].map(fold_val).astype("Int64")
    return built


def feature_lists(cfg) -> tuple[list, list, list]:
    """Return (main_features, extended_features, categorical)."""
    num_main = list(cfg["features"]["numeric_main"])
    cat = list(cfg["features"]["categorical"])
    extra = list(cfg["features"]["numeric_extended_extra"])
    main = num_main + cat
    extended = num_main + extra + cat
    return main, extended, cat


def write_dataset_artifacts(cfg, built: pd.DataFrame, audit: dict):
    out02 = utils.out_dir(cfg, "02_modeling_data")
    # full built dataset
    built.to_csv(out02 / cfg["target"]["built_csv"], index=False, encoding="utf-8-sig")

    # split manifest (brief 18: ticker, predictor_year, target_year, split, target)
    manifest = built[["ticker", "predictor_year", "target_year", "split",
                      "cv_val_fold", "target_next_year", "row_key"]].copy()
    manifest.to_csv(out02 / "split_manifest.csv", index=False, encoding="utf-8-sig")

    main, extended, cat = feature_lists(cfg)
    utils.save_json({"numeric": cfg["features"]["numeric_main"], "categorical": cat,
                     "all": main}, out02 / "feature_list_main.json")
    utils.save_json({"numeric": cfg["features"]["numeric_main"]
                     + cfg["features"]["numeric_extended_extra"],
                     "categorical": cat, "all": extended},
                    out02 / "feature_list_extended.json")

    pre = {
        "numeric_imputation": "median (train-fold only)",
        "missing_indicator": True,
        "categorical_impute_value": "Unknown",
        "categorical_encoding": "one_hot (handle_unknown=ignore)",
        "logistic_scaler": "RobustScaler",
        "tree_scaler": "none",
        "fit_scope": "train fold only — no validation/test statistics used",
    }
    utils.save_json(pre, out02 / "preprocessing_config.json")
    return out02
