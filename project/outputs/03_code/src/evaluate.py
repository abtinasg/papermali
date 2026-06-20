"""Test-set evaluation, predictions, bootstrap CIs, threshold analysis (brief 12)."""
from __future__ import annotations
import numpy as np
import pandas as pd

from . import utils, metrics
from .preprocessing import coerce_frame


def _prob(pipe, df, numeric, categorical):
    return pipe.predict_proba(coerce_frame(df, numeric, categorical))[:, 1]


def cv_metric_tables(state, cfg):
    out06 = utils.out_dir(cfg, "06_metrics")
    rows = []
    for m, tune in state["tuning"].items():
        for r in tune["fold_records"]:
            rows.append(r)
    by_fold = pd.DataFrame(rows)
    by_fold.to_csv(out06 / "cv_metrics_by_fold.csv", index=False, encoding="utf-8-sig")
    summ = (by_fold.groupby("model")[["pr_auc", "roc_auc", "brier"]]
            .agg(["mean", "std"]).reset_index())
    summ.columns = ["_".join([c for c in col if c]).strip("_") for col in summ.columns]
    summ.to_csv(out06 / "cv_metrics_summary.csv", index=False, encoding="utf-8-sig")
    return by_fold


def predictions_table(state, cfg):
    out05 = utils.out_dir(cfg, "05_predictions")
    test = state["test"]; numeric, categorical = state["numeric"], state["categorical"]
    df = test[["row_key", "ticker", "predictor_year", "target_year"]].copy()
    df["y_true"] = test["target_next_year"].values
    name = {"logistic": "logistic", "random_forest": "random_forest", "xgboost": "xgboost"}
    for m, pipe in state["finals"].items():
        prob = _prob(pipe, test, numeric, categorical)
        t05, topt = 0.5, state["thresholds"][m]["primary_threshold"]
        df[f"probability_{name[m]}"] = prob
        df[f"pred_{name[m]}_thr0.5"] = (prob >= t05).astype(int)
        df[f"pred_{name[m]}_thropt"] = (prob >= topt).astype(int)
    df.to_csv(out05 / "test_predictions_all_models.csv", index=False, encoding="utf-8-sig")
    state["test_predictions"] = df
    print(f"[05] test predictions saved -> {out05}")
    return df


def test_metrics(state, cfg):
    out06 = utils.out_dir(cfg, "06_metrics")
    test = state["test"]; numeric, categorical = state["numeric"], state["categorical"]
    y = test["target_next_year"].values
    rows, boot_rows, thr_rows = [], [], []
    for m, pipe in state["finals"].items():
        prob = _prob(pipe, test, numeric, categorical)
        th = state["thresholds"][m]
        for tag, t in [("thr_0.5", 0.5),
                       ("thr_opt_primary", th["primary_threshold"]),
                       ("thr_opt_secondary", th["secondary_threshold"])]:
            mt = metrics.full_metrics(y, prob, t)
            rows.append({"model": m, "threshold_kind": tag, **mt})
        # bootstrap CI at primary threshold
        bdf = pd.DataFrame({"ticker": test["ticker"].values, "y": y, "prob": prob})
        ci = metrics.cluster_bootstrap_ci(
            bdf, "prob", "y", "ticker", th["primary_threshold"],
            n=cfg["evaluation"]["bootstrap_n"], alpha=cfg["evaluation"]["ci_alpha"],
            seed=cfg["seed"])
        ci["model"] = m
        boot_rows.append(ci)
        # threshold sweep on validation oof (threshold chosen there)
        oof = state["tuning"][m]["oof"]
        for t in np.linspace(0.05, 0.95, 19):
            mm = metrics.thresholded(oof["y_true"].values, oof["y_prob"].values, t)
            thr_rows.append({"model": m, "source": "validation_oof",
                             "threshold": round(float(t), 3),
                             "f1": mm["f1"], "recall": mm["recall"],
                             "precision": mm["precision"],
                             "balanced_accuracy": mm["balanced_accuracy"]})

    tm = pd.DataFrame(rows)
    tm.to_csv(out06 / "test_metrics.csv", index=False, encoding="utf-8-sig")
    pd.concat(boot_rows, ignore_index=True).to_csv(
        out06 / "test_metrics_bootstrap_ci.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(thr_rows).to_csv(out06 / "threshold_analysis.csv", index=False,
                                  encoding="utf-8-sig")
    state["test_metrics"] = tm
    print(f"[06] test metrics + bootstrap CI + threshold analysis saved -> {out06}")
    return tm


def comparison_workbook(state, cfg):
    out06 = utils.out_dir(cfg, "06_metrics")
    tm = state["test_metrics"]
    main = tm[tm["threshold_kind"] == "thr_opt_primary"].copy()
    with pd.ExcelWriter(out06 / "model_comparison_table.xlsx") as xw:
        main.to_excel(xw, sheet_name="test_primary_threshold", index=False)
        tm.to_excel(xw, sheet_name="test_all_thresholds", index=False)
        if "seed_stability" in state and len(state["seed_stability"]):
            state["seed_stability"].groupby("model").mean(numeric_only=True)\
                .reset_index().to_excel(xw, sheet_name="seed_stability_mean", index=False)
    print(f"[06] model_comparison_table.xlsx saved")
