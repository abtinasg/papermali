"""Optuna hyperparameter tuning on expanding-window folds (brief section 11).

Selection metric = mean validation PR-AUC across folds. All models share the same
folds. The test set is never touched here.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import optuna

from . import models, cv, metrics

optuna.logging.set_verbosity(optuna.logging.WARNING)


def cv_predict(model_name, params, dev, numeric, categorical, cfg, seed):
    """Run expanding-window CV; return (mean_pr_auc, fold_records, oof_dataframe)."""
    y = dev["target_next_year"].values
    es = cfg["tuning"]["xgboost"]["early_stopping_rounds"]
    fold_recs, oof = [], []
    for fid, tr, va in cv.expanding_folds(dev, cfg):
        prob = models.fit_predict_fold(
            model_name, params, dev[tr], y[tr], dev[va], y[va],
            numeric, categorical, seed,
            early_stopping_rounds=es if model_name == "xgboost" else None)
        mt = metrics.threshold_free(y[va], prob)
        fold_recs.append({"fold": fid, "model": model_name,
                          "n_val": int(va.sum()), "pos_val": int(y[va].sum()),
                          **mt})
        sub = dev[va][["ticker", "predictor_year", "target_year"]].copy()
        sub["y_true"] = y[va]; sub["y_prob"] = prob; sub["fold"] = fid
        oof.append(sub)
    pr = np.nanmean([r["pr_auc"] for r in fold_recs])
    return float(pr), fold_recs, pd.concat(oof, ignore_index=True)


def tune_model(model_name, dev, numeric, categorical, cfg):
    seed = cfg["seed"]

    def objective(trial):
        params = models.suggest_params(trial, model_name, cfg)
        pr, _, _ = cv_predict(model_name, params, dev, numeric, categorical, cfg, seed)
        return pr if np.isfinite(pr) else -1.0

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=cfg["tuning"]["n_trials"], show_progress_bar=False)

    best = dict(study.best_params)
    best_params = _materialize(model_name, best, cfg)
    # recompute folds + oof at best params for reporting / threshold selection
    pr, fold_recs, oof = cv_predict(model_name, best_params, dev, numeric,
                                    categorical, cfg, seed)
    return {"model": model_name, "best_params": best_params, "best_cv_pr_auc": pr,
            "fold_records": fold_recs, "oof": oof, "study": study}


def _materialize(model_name, raw, cfg):
    """Convert Optuna raw params (with *_log10 etc.) into estimator kwargs."""
    if model_name == "logistic":
        p = {"penalty": raw["penalty"], "C": 10 ** raw["C_log10"],
             "max_iter": cfg["tuning"]["logistic"]["max_iter"]}
        if raw["penalty"] == "elasticnet":
            p["l1_ratio"] = raw["l1_ratio"]
        return p
    if model_name == "random_forest":
        return {k: raw[k] for k in ["n_estimators", "max_depth", "min_samples_split",
                                    "min_samples_leaf", "max_features", "class_weight"]}
    if model_name == "xgboost":
        return {
            "n_estimators": raw["n_estimators"],
            "learning_rate": 10 ** raw["lr_log10"],
            "max_depth": raw["max_depth"],
            "min_child_weight": raw["min_child_weight"],
            "subsample": raw["subsample"],
            "colsample_bytree": raw["colsample_bytree"],
            "gamma": raw["gamma"],
            "reg_alpha": 10 ** raw["reg_alpha_log10"],
            "reg_lambda": 10 ** raw["reg_lambda_log10"],
        }
    raise ValueError(model_name)
