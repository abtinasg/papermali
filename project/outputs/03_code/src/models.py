"""Model factories, Optuna search spaces, fold-fit helpers (brief sections 10-11)."""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from .preprocessing import build_preprocessor, coerce_frame

MODELS = ["logistic", "random_forest", "xgboost"]


def needs_scaling(model_name: str) -> bool:
    return model_name == "logistic"


def scale_pos_weight(y) -> float:
    y = np.asarray(y)
    pos = max(int(y.sum()), 1)
    neg = int((y == 0).sum())
    return neg / pos


# ---------------------------------------------------------------------------
# Optuna search spaces (ranges live in config -> reproducible).
# ---------------------------------------------------------------------------
def suggest_params(trial, model_name: str, cfg) -> dict:
    t = cfg["tuning"]
    if model_name == "logistic":
        sp = t["logistic"]
        penalty = trial.suggest_categorical("penalty", sp["penalty"])
        params = {
            "penalty": penalty,
            "C": 10 ** trial.suggest_float("C_log10", sp["C_log10_low"], sp["C_log10_high"]),
            "max_iter": sp["max_iter"],
        }
        if penalty == "elasticnet":
            params["l1_ratio"] = trial.suggest_float("l1_ratio", sp["l1_ratio_low"],
                                                     sp["l1_ratio_high"])
        return params
    if model_name == "random_forest":
        sp = t["random_forest"]
        return {
            "n_estimators": trial.suggest_int("n_estimators", sp["n_estimators_low"],
                                              sp["n_estimators_high"]),
            "max_depth": trial.suggest_categorical("max_depth", sp["max_depth_choices"]),
            "min_samples_split": trial.suggest_int("min_samples_split",
                                                   sp["min_samples_split_low"],
                                                   sp["min_samples_split_high"]),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf",
                                                  sp["min_samples_leaf_low"],
                                                  sp["min_samples_leaf_high"]),
            "max_features": trial.suggest_categorical("max_features",
                                                      sp["max_features_choices"]),
            "class_weight": trial.suggest_categorical("class_weight",
                                                      sp["class_weight_choices"]),
        }
    if model_name == "xgboost":
        sp = t["xgboost"]
        return {
            "n_estimators": trial.suggest_int("n_estimators", sp["n_estimators_low"],
                                              sp["n_estimators_high"]),
            "learning_rate": 10 ** trial.suggest_float("lr_log10",
                                                       sp["learning_rate_log10_low"],
                                                       sp["learning_rate_log10_high"]),
            "max_depth": trial.suggest_int("max_depth", sp["max_depth_low"],
                                           sp["max_depth_high"]),
            "min_child_weight": trial.suggest_int("min_child_weight",
                                                  sp["min_child_weight_low"],
                                                  sp["min_child_weight_high"]),
            "subsample": trial.suggest_float("subsample", sp["subsample_low"],
                                             sp["subsample_high"]),
            "colsample_bytree": trial.suggest_float("colsample_bytree",
                                                    sp["colsample_bytree_low"],
                                                    sp["colsample_bytree_high"]),
            "gamma": trial.suggest_float("gamma", sp["gamma_low"], sp["gamma_high"]),
            "reg_alpha": 10 ** trial.suggest_float("reg_alpha_log10",
                                                   sp["reg_alpha_log10_low"],
                                                   sp["reg_alpha_log10_high"]),
            "reg_lambda": 10 ** trial.suggest_float("reg_lambda_log10",
                                                    sp["reg_lambda_log10_low"],
                                                    sp["reg_lambda_log10_high"]),
        }
    raise ValueError(model_name)


def make_estimator(model_name: str, params: dict, seed: int, spw: float | None = None):
    p = dict(params)
    if model_name == "logistic":
        solver = "saga" if p.get("penalty") in ("l1", "elasticnet") else "lbfgs"
        return LogisticRegression(class_weight="balanced", solver=solver,
                                  random_state=seed, **p)
    if model_name == "random_forest":
        return RandomForestClassifier(random_state=seed, n_jobs=-1, **p)
    if model_name == "xgboost":
        return XGBClassifier(
            objective="binary:logistic", eval_metric="aucpr",
            tree_method="hist", random_state=seed, n_jobs=-1,
            scale_pos_weight=spw if spw is not None else 1.0, **p)
    raise ValueError(model_name)


def build_final_pipeline(model_name, params, numeric_features, categorical_features,
                         seed, X_dev=None, y_dev=None, early_stopping_rounds=None):
    """Fit a full Pipeline (preprocess + estimator) on dev for saving/SHAP/test."""
    pre = build_preprocessor(numeric_features, categorical_features,
                             scale=needs_scaling(model_name))
    spw = scale_pos_weight(y_dev) if model_name == "xgboost" else None
    est = make_estimator(model_name, params, seed, spw=spw)
    pipe = Pipeline([("pre", pre), ("clf", est)])
    if X_dev is not None:
        Xc = coerce_frame(X_dev, numeric_features, categorical_features)
        pipe.fit(Xc, np.asarray(y_dev))
    return pipe


def fit_predict_fold(model_name, params, X_tr, y_tr, X_va, y_va, numeric_features,
                     categorical_features, seed, early_stopping_rounds=None):
    """Fold-safe fit on train, return predicted probabilities on validation.

    XGBoost uses the fold's validation as eval_set for early stopping (allowed:
    validation, never test). Preprocessor is fit on train only.
    """
    pre = build_preprocessor(numeric_features, categorical_features,
                             scale=needs_scaling(model_name))
    Xtr = coerce_frame(X_tr, numeric_features, categorical_features)
    Xva = coerce_frame(X_va, numeric_features, categorical_features)
    Xtr_t = pre.fit_transform(Xtr, np.asarray(y_tr))
    Xva_t = pre.transform(Xva)
    y_tr = np.asarray(y_tr)
    y_va = np.asarray(y_va, dtype=int)

    if model_name == "xgboost":
        est = XGBClassifier(
            objective="binary:logistic", eval_metric="aucpr", tree_method="hist",
            random_state=seed, n_jobs=-1, scale_pos_weight=scale_pos_weight(y_tr),
            early_stopping_rounds=early_stopping_rounds, **dict(params))
        est.fit(Xtr_t, y_tr, eval_set=[(Xva_t, y_va)], verbose=False)
        return est.predict_proba(Xva_t)[:, 1]

    est = make_estimator(model_name, params, seed)
    est.fit(Xtr_t, y_tr)
    return est.predict_proba(Xva_t)[:, 1]
