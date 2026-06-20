"""Final-model training, threshold selection, seed stability (brief 11-13)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib

from . import utils, models, metrics


def select_threshold(oof: pd.DataFrame, cfg) -> dict:
    """Thresholds chosen on validation (out-of-fold) predictions only."""
    g = cfg["threshold"]["grid_points"]
    prim = cfg["threshold"]["primary_objective"]
    sec = cfg["threshold"]["secondary_objective"]
    t_prim = metrics.pick_threshold(oof["y_true"], oof["y_prob"], prim, g)
    t_sec = metrics.pick_threshold(oof["y_true"], oof["y_prob"], sec, g)
    return {"primary_objective": prim, "primary_threshold": t_prim,
            "secondary_objective": sec, "secondary_threshold": t_sec}


def finalize_models(state, cfg):
    """Fit final pipelines on full dev; pick thresholds; save artifacts."""
    out04 = utils.out_dir(cfg, "04_models")
    dev = state["dev"]; numeric = state["numeric"]; categorical = state["categorical"]
    y_dev = dev["target_next_year"].values
    seed = cfg["seed"]
    finals, thresholds, best_params = {}, {}, {}

    for m in models.MODELS:
        tune = state["tuning"][m]
        params = dict(tune["best_params"])
        if m == "random_forest":
            mn = cfg["tuning"]["random_forest"]["final_min_trees"]
            if params.get("n_estimators", 0) < mn:
                params["n_estimators"] = mn  # brief: >=500 unless documented
        pipe = models.build_final_pipeline(m, params, numeric, categorical, seed,
                                           X_dev=dev, y_dev=y_dev)
        finals[m] = pipe
        best_params[m] = params
        thresholds[m] = select_threshold(tune["oof"], cfg)
        joblib.dump(pipe, out04 / f"pipeline_{m}.joblib")

    utils.save_json(best_params, out04 / "best_hyperparameters.json")
    utils.save_json(thresholds, out04 / "final_thresholds.json")
    state["finals"] = finals
    state["thresholds"] = thresholds
    state["best_params"] = best_params
    print(f"[04] final models + thresholds saved -> {out04}")
    return finals, thresholds


def seed_stability(state, cfg):
    """Refit RF & XGB with many seeds; report test-metric dispersion (brief 13)."""
    if not cfg["run"]["do_seed_stability"]:
        return pd.DataFrame()
    out06 = utils.out_dir(cfg, "06_metrics")
    dev, test = state["dev"], state["test"]
    numeric, categorical = state["numeric"], state["categorical"]
    y_dev = dev["target_next_year"].values
    y_test = test["target_next_year"].values
    n = cfg["stability"]["n_seeds"]
    seeds = list(range(cfg["stability"]["seeds_start"],
                       cfg["stability"]["seeds_start"] + n))
    keys = ["pr_auc", "roc_auc", "brier", "recall", "precision", "f1",
            "balanced_accuracy", "mcc"]
    recs = []
    for m in ["random_forest", "xgboost"]:
        params = state["best_params"][m]
        t_prim = state["thresholds"][m]["primary_threshold"]
        for s in seeds:
            pipe = models.build_final_pipeline(m, params, numeric, categorical, s,
                                               X_dev=dev, y_dev=y_dev)
            from .preprocessing import coerce_frame
            prob = pipe.predict_proba(coerce_frame(test, numeric, categorical))[:, 1]
            mt = metrics.full_metrics(y_test, prob, t_prim)
            recs.append({"model": m, "seed": s, **{k: mt[k] for k in keys}})
    df = pd.DataFrame(recs)
    summary = (df.groupby("model")[keys]
               .agg(["mean", "std", "min", "max"]).reset_index())
    df.to_csv(out06 / "seed_stability_results.csv", index=False, encoding="utf-8-sig")
    summary.columns = ["_".join([c for c in col if c]).strip("_")
                       for col in summary.columns]
    summary.to_csv(out06 / "seed_stability_summary.csv", index=False,
                   encoding="utf-8-sig")
    state["seed_stability"] = df
    print(f"[06] seed stability ({n} seeds) saved -> {out06}")
    return df
