"""Robustness analyses (brief section 16). Reported separately; never replaces main.

To keep runtime bounded, robustness reuses the main models' tuned hyperparameters
(documented) and evaluates representative models (Logistic + XGBoost). Each variant
is fully fold-safe: winsorization / SMOTE / preprocessing fit on the train fold only.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from . import utils, cv, metrics, models, build_dataset as bd
from .preprocessing import build_preprocessor, coerce_frame


def _make_clf(model_name, params, seed, y_tr, imbalance):
    if model_name == "logistic":
        cw = None if imbalance == "smote" else "balanced"
        solver = "saga" if params.get("penalty") in ("l1", "elasticnet") else "lbfgs"
        return LogisticRegression(class_weight=cw, solver=solver,
                                  random_state=seed, **params)
    if model_name == "random_forest":
        p = dict(params);
        if imbalance == "smote": p["class_weight"] = None
        return RandomForestClassifier(random_state=seed, n_jobs=-1, **p)
    if model_name == "xgboost":
        spw = 1.0 if imbalance == "smote" else models.scale_pos_weight(y_tr)
        return XGBClassifier(objective="binary:logistic", eval_metric="aucpr",
                             tree_method="hist", random_state=seed, n_jobs=-1,
                             scale_pos_weight=spw, **params)
    raise ValueError(model_name)


def _fit_predict(model_name, params, X_tr, y_tr, X_eval, numeric, categorical,
                 seed, winsor, imbalance, cfg):
    pre = build_preprocessor(numeric, categorical,
                             scale=models.needs_scaling(model_name), winsor=winsor)
    Xtr = pre.fit_transform(coerce_frame(X_tr, numeric, categorical), np.asarray(y_tr))
    Xev = pre.transform(coerce_frame(X_eval, numeric, categorical))
    y_tr = np.asarray(y_tr)
    if imbalance == "smote":
        pos = int(y_tr.sum())
        k = min(cfg["imbalance"]["smote_k_neighbors"], max(pos - 1, 1))
        if pos >= 2:
            Xtr, y_tr = SMOTE(k_neighbors=k, random_state=seed).fit_resample(Xtr, y_tr)
    clf = _make_clf(model_name, params, seed, y_tr, imbalance)
    clf.fit(Xtr, y_tr)
    return clf.predict_proba(Xev)[:, 1]


def eval_variant(label, model_name, params, numeric, categorical, dev, test, cfg,
                 winsor=None, imbalance="class_weight"):
    y_dev = dev["target_next_year"].values
    # CV for oof + threshold
    oof_y, oof_p, fold_pr = [], [], []
    for fid, tr, va in cv.expanding_folds(dev, cfg):
        p = _fit_predict(model_name, params, dev[tr], y_dev[tr], dev[va],
                         numeric, categorical, cfg["seed"], winsor, imbalance, cfg)
        oof_y.append(y_dev[va]); oof_p.append(p)
        fold_pr.append(metrics.threshold_free(y_dev[va], p)["pr_auc"])
    oof_y = np.concatenate(oof_y); oof_p = np.concatenate(oof_p)
    thr = metrics.pick_threshold(oof_y, oof_p, cfg["threshold"]["primary_objective"],
                                 cfg["threshold"]["grid_points"])
    # final on dev -> test
    y_test = test["target_next_year"].values
    p_test = _fit_predict(model_name, params, dev, y_dev, test, numeric, categorical,
                          cfg["seed"], winsor, imbalance, cfg)
    mt = metrics.full_metrics(y_test, p_test, thr)
    return {"variant": label, "model": model_name,
            "cv_mean_pr_auc": float(np.nanmean(fold_pr)),
            "test_pr_auc": mt["pr_auc"], "test_roc_auc": mt["roc_auc"],
            "test_recall": mt["recall"], "test_precision": mt["precision"],
            "test_f1": mt["f1"], "test_balanced_acc": mt["balanced_accuracy"],
            "test_brier": mt["brier"], "threshold": thr, "imbalance": imbalance,
            "winsor": bool(winsor)}


def _same_year_frame(cfg):
    """Same-year classification frame (robustness #6): predict distress in year t."""
    _, cand = bd.load_raw(cfg)
    cand = bd._engineer(cand, cfg)
    cand = cand[cand[cfg["target"]["source_label_col"]].isin(["0", "1"])
                if cand[cfg["target"]["source_label_col"]].dtype == object
                else cand[cfg["target"]["source_label_col"]].notna()].copy()
    cand["target_next_year"] = pd.to_numeric(cand[cfg["target"]["source_label_col"]],
                                             errors="coerce").astype("Int64")
    cand = cand[cand["target_next_year"].notna()].copy()
    cand["target_next_year"] = cand["target_next_year"].astype(int)
    cand["predictor_year"] = cand["fiscal_year"]
    cand["target_year"] = cand["fiscal_year"]
    return bd._assign_split(cand, cfg)


def run(state, cfg):
    if not cfg["run"]["do_robustness"]:
        return
    out = utils.out_dir(cfg, "06_metrics")
    dev, test = state["dev"], state["test"]
    main, extended, cat = bd.feature_lists(cfg)
    num_main = cfg["features"]["numeric_main"]
    num_ext = cfg["features"]["numeric_main"] + cfg["features"]["numeric_extended_extra"]
    near_def = cfg["features"]["near_definition_vars"]
    w = (cfg["robustness"]["winsor_lower"], cfg["robustness"]["winsor_upper"])

    rows = []
    for model_name in ["logistic", "xgboost"]:
        bp = state["best_params"][model_name]
        # 1 & 2: Feature Set A (main, no gross profit) vs B (extended, incl GP)
        rows.append(eval_variant("A_main", model_name, bp, num_main, cat, dev, test, cfg))
        rows.append(eval_variant("B_extended", model_name, bp, num_ext, cat, dev, test, cfg))
        # 3: winsorization on/off (A)
        rows.append(eval_variant("A_winsorized", model_name, bp, num_main, cat, dev,
                                 test, cfg, winsor=w))
        # 4: class weighting vs SMOTE (A)
        rows.append(eval_variant("A_smote", model_name, bp, num_main, cat, dev, test,
                                 cfg, imbalance="smote"))
        # 7: drop near-definition vars from B
        num_b_drop = [c for c in num_ext if c not in near_def]
        rows.append(eval_variant("B_drop_near_definition", model_name, bp, num_b_drop,
                                 cat, dev, test, cfg))
        # 6: same-year classification (NOT forward prediction)
        sy = _same_year_frame(cfg)
        sy_dev = sy[sy["split"] == "dev"]; sy_test = sy[sy["split"] == "test"]
        rows.append(eval_variant("same_year_classification", model_name, bp, num_main,
                                 cat, sy_dev, sy_test, cfg))

    df = pd.DataFrame(rows)
    df.to_csv(out / "robustness_results.csv", index=False, encoding="utf-8-sig")
    state["robustness"] = df
    print(f"[06] robustness results saved -> {out}")
    return df
