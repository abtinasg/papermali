"""Probability calibration (brief section 15). Calibrators fit on validation only."""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from . import utils
from .preprocessing import coerce_frame


def run(state, cfg):
    if not cfg["run"]["do_calibration"]:
        return
    out04 = utils.out_dir(cfg, "04_models")
    out06 = utils.out_dir(cfg, "06_metrics")
    test = state["test"]; numeric, categorical = state["numeric"], state["categorical"]
    y_test = test["target_next_year"].values
    recs = []
    for m, pipe in state["finals"].items():
        oof = state["tuning"][m]["oof"]
        p_oof = oof["y_prob"].values; y_oof = oof["y_true"].values
        p_test = pipe.predict_proba(coerce_frame(test, numeric, categorical))[:, 1]
        recs.append({"model": m, "method": "uncalibrated",
                     "brier_test": float(brier_score_loss(y_test, p_test))})

        # Platt (sigmoid) fit on validation OOF
        platt = LogisticRegression()
        platt.fit(p_oof.reshape(-1, 1), y_oof)
        p_platt = platt.predict_proba(p_test.reshape(-1, 1))[:, 1]
        recs.append({"model": m, "method": "platt",
                     "brier_test": float(brier_score_loss(y_test, p_platt))})

        # Isotonic fit on validation OOF
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_oof, y_oof)
        p_iso = iso.predict(p_test)
        recs.append({"model": m, "method": "isotonic",
                     "brier_test": float(brier_score_loss(y_test, p_iso))})

        joblib.dump({"platt": platt, "iso": iso},
                    out04 / f"calibrators_{m}.joblib")
    df = pd.DataFrame(recs)
    df.to_csv(out06 / "calibration_metrics.csv", index=False, encoding="utf-8-sig")
    state["calibration"] = df
    print(f"[06] calibration metrics saved -> {out06}")
    return df
