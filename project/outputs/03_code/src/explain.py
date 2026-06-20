"""Explainability: SHAP (trees, test only) + Logistic coefficients (brief 14)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

from . import utils
from .preprocessing import coerce_frame
from .plots import savefig


def _transform_test(pipe, test, numeric, categorical):
    pre = pipe.named_steps["pre"]; clf = pipe.named_steps["clf"]
    Xt = pre.transform(coerce_frame(test, numeric, categorical))
    names = list(pre.get_feature_names_out())
    return clf, np.asarray(Xt), names


def _to_class1(sv):
    if isinstance(sv, list):
        return np.asarray(sv[1])
    sv = np.asarray(sv)
    if sv.ndim == 3:
        return sv[:, :, 1]
    return sv


def logistic_explain(state, cfg):
    out = utils.out_dir(cfg, "07_explainability")
    pipe = state["finals"]["logistic"]
    pre = pipe.named_steps["pre"]; clf = pipe.named_steps["clf"]
    names = list(pre.get_feature_names_out())
    coef = clf.coef_.ravel()
    df = pd.DataFrame({"feature": names, "coefficient": coef,
                       "odds_ratio": np.exp(coef),
                       "direction": np.where(coef > 0, "increases_risk",
                                             np.where(coef < 0, "decreases_risk", "none")),
                       "is_industry": [n.startswith("cat__industry") for n in names]})
    df.sort_values("coefficient", key=lambda s: s.abs(), ascending=False, inplace=True)
    df.to_csv(out / "logistic_coefficients.csv", index=False, encoding="utf-8-sig")
    df[["feature", "odds_ratio", "direction", "is_industry"]].to_csv(
        out / "logistic_odds_ratios.csv", index=False, encoding="utf-8-sig")
    print("[07] logistic coefficients + odds ratios saved")


def tree_importance(state, cfg):
    out = utils.out_dir(cfg, "07_explainability")
    for m, short in [("random_forest", "rf"), ("xgboost", "xgb")]:
        pipe = state["finals"][m]
        clf, Xt, names = _transform_test(pipe, state["test"], state["numeric"],
                                         state["categorical"])
        imp = pd.DataFrame({"feature": names, "importance": clf.feature_importances_})
        imp.sort_values("importance", ascending=False, inplace=True)
        imp.to_csv(out / f"{short}_feature_importance.csv", index=False,
                   encoding="utf-8-sig")
    print("[07] tree feature importances saved")


def shap_explain(state, cfg):
    if not cfg["run"]["do_shap"]:
        return
    out = utils.out_dir(cfg, "07_explainability")
    test = state["test"]; numeric, categorical = state["numeric"], state["categorical"]
    y = test["target_next_year"].values
    for m, short in [("random_forest", "rf"), ("xgboost", "xgb")]:
        pipe = state["finals"][m]
        clf, Xt, names = _transform_test(pipe, test, numeric, categorical)
        try:
            explainer = shap.TreeExplainer(clf)
            sv_raw = explainer.shap_values(Xt)
            sv = _to_class1(sv_raw)
            base = explainer.expected_value
            base = np.atleast_1d(base)[-1] if np.ndim(base) else float(base)
        except Exception as e:  # noqa
            print(f"   ! SHAP failed for {m}: {e}")
            continue

        # global importance
        gi = pd.DataFrame({"feature": names,
                           "mean_abs_shap": np.abs(sv).mean(0)})
        gi.sort_values("mean_abs_shap", ascending=False, inplace=True)
        gi.to_csv(out / f"shap_global_importance_{short}.csv", index=False,
                  encoding="utf-8-sig")
        np.savez_compressed(out / f"shap_values_test_{short}.npz",
                            shap_values=sv, data=Xt, base_value=base,
                            feature_names=np.array(names, dtype=object))

        expl = shap.Explanation(values=sv, base_values=np.full(sv.shape[0], base),
                                data=Xt, feature_names=names)
        _shap_plots(expl, sv, Xt, names, gi, m, short, cfg, state, y)
    print("[07] SHAP global importance, values, and plots saved")


def _shap_plots(expl, sv, Xt, names, gi, model, short, cfg, state, y):
    # bar
    try:
        fig = plt.figure(figsize=(7, 6))
        shap.plots.bar(expl, max_display=15, show=False)
        savefig(plt.gcf(), cfg, f"fig_shap_bar_{short}")
    except Exception as e:
        print(f"   ! shap bar {short}: {e}"); plt.close("all")
    # beeswarm
    try:
        fig = plt.figure(figsize=(7, 6))
        shap.plots.beeswarm(expl, max_display=15, show=False)
        savefig(plt.gcf(), cfg, f"fig_shap_beeswarm_{short}")
    except Exception as e:
        print(f"   ! shap beeswarm {short}: {e}"); plt.close("all")
    # dependence for top 5
    top5 = gi["feature"].head(5).tolist()
    for feat in top5:
        j = names.index(feat)
        try:
            fig = plt.figure(figsize=(6, 5))
            shap.plots.scatter(expl[:, j], show=False)
            savefig(plt.gcf(), cfg, f"fig_shap_dependence_{short}_{_safe(feat)}")
        except Exception:
            plt.close("all")
    # waterfall for TP/TN/FP/FN at primary threshold
    t = state["thresholds"][model]["primary_threshold"]
    prob = state["finals"][model].predict_proba(
        coerce_frame(state["test"], state["numeric"], state["categorical"]))[:, 1]
    pred = (prob >= t).astype(int)
    cases = {"TP": (pred == 1) & (y == 1), "TN": (pred == 0) & (y == 0),
             "FP": (pred == 1) & (y == 0), "FN": (pred == 0) & (y == 1)}
    for tag, mask in cases.items():
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue
        i = int(idx[0])
        try:
            fig = plt.figure(figsize=(7, 6))
            shap.plots.waterfall(expl[i], max_display=12, show=False)
            savefig(plt.gcf(), cfg, f"fig_shap_waterfall_{short}_{tag}")
        except Exception:
            plt.close("all")
    # interaction (xgboost only, best effort)
    if model == "xgboost":
        try:
            explainer = shap.TreeExplainer(state["finals"][model].named_steps["clf"])
            inter = explainer.shap_interaction_values(Xt)
            np.savez_compressed(
                utils.out_dir(cfg, "07_explainability") / "shap_interaction_xgb.npz",
                interaction=np.asarray(inter), feature_names=np.array(names, dtype=object))
        except Exception as e:
            print(f"   ! shap interaction xgb: {e}")


def _safe(s):
    return "".join(c if c.isalnum() else "_" for c in s)[:40]


def run(state, cfg):
    logistic_explain(state, cfg)
    tree_importance(state, cfg)
    shap_explain(state, cfg)
