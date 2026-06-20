"""Data-audit outputs (brief section 18 -> 01_data_audit)."""
from __future__ import annotations
import numpy as np
import pandas as pd

from . import utils
from . import build_dataset as bd


def _roles(cfg):
    main, extended, cat = bd.feature_lists(cfg)
    idset = set(cfg["id_leakage_columns"])
    main_set, ext_set = set(main), set(extended)

    def role(c):
        if c in idset:
            return "id_or_leakage"
        if c in main_set:
            return "feature_main"
        if c in ext_set:
            return "feature_extended_only"
        return "other_not_used"
    return role


def run(cfg, built: pd.DataFrame, audit: dict):
    out = utils.out_dir(cfg, "01_data_audit")
    allr, cand = bd.load_raw(cfg)
    role = _roles(cfg)

    # ---- schema check -----------------------------------------------------
    schema = pd.DataFrame({
        "column": built.columns,
        "dtype": [str(built[c].dtype) for c in built.columns],
        "role": [role(c) for c in built.columns],
        "n_missing": [int(built[c].isna().sum()) if built[c].dtype != object
                      else int((built[c].astype(str) == "").sum())
                      for c in built.columns],
    })
    schema.to_csv(out / "schema_check.csv", index=False, encoding="utf-8-sig")

    # ---- duplicate check --------------------------------------------------
    dup = pd.DataFrame({
        "check": ["all_rows (ticker,fiscal_year)", "built (ticker,predictor_year)"],
        "n_rows": [len(allr), len(built)],
        "n_duplicate_keys": [
            int(allr.duplicated(["ticker", "fiscal_year"]).sum()),
            int(built.duplicated(["ticker", "predictor_year"]).sum())],
    })
    dup.to_csv(out / "duplicate_check.csv", index=False, encoding="utf-8-sig")

    # ---- class distribution ----------------------------------------------
    by_split = (built.groupby("split")["target_next_year"]
                .agg(n="size", positives="sum"))
    by_split["positive_rate"] = by_split["positives"] / by_split["n"]
    by_year = (built.groupby("target_year")["target_next_year"]
               .agg(n="size", positives="sum"))
    by_year["positive_rate"] = by_year["positives"] / by_year["n"]
    cls = pd.concat([
        by_split.reset_index().rename(columns={"split": "group"}).assign(level="split"),
        by_year.reset_index().rename(columns={"target_year": "group"}).assign(level="target_year"),
    ], ignore_index=True)
    cls.to_csv(out / "class_distribution.csv", index=False, encoding="utf-8-sig")

    # ---- target-shift audit ----------------------------------------------
    rows = [{"key": "n_candidates", "value": audit["n_candidates"]},
            {"key": "n_built_one_year_ahead", "value": audit["n_built"]},
            {"key": "n_positive", "value": audit["n_positive"]},
            {"key": "positive_rate", "value": round(audit["positive_rate"], 5)}]
    for k, v in audit["dropped"].items():
        rows.append({"key": f"dropped::{k}", "value": v})
    for sp, d in audit["split_counts"].items():
        rows.append({"key": f"split::{sp}::n", "value": d["n"]})
        rows.append({"key": f"split::{sp}::positives", "value": d["positives"]})
    pd.DataFrame(rows).to_csv(out / "target_shift_audit.csv", index=False,
                              encoding="utf-8-sig")

    # ---- missingness by split --------------------------------------------
    main, _, _ = bd.feature_lists(cfg)
    feat_cols = [c for c in main if c != "industry"] + ["industry"]
    recs = []
    for c in feat_cols:
        for sp in ["dev", "test"]:
            sub = built[built["split"] == sp]
            if c == "industry":
                miss = int((sub[c].astype(str).isin(["", "nan", "None"])).sum())
            else:
                miss = int(pd.to_numeric(sub[c], errors="coerce").isna().sum())
            recs.append({"feature": c, "split": sp, "n": len(sub),
                         "n_missing": miss,
                         "pct_missing": round(miss / max(len(sub), 1) * 100, 2)})
    pd.DataFrame(recs).to_csv(out / "missingness_by_split.csv", index=False,
                              encoding="utf-8-sig")

    # ---- outlier report (p1/p99 on DEV only; count beyond) ---------------
    dev = built[built["split"] == "dev"]
    orec = []
    for c in [c for c in main if c != "industry"]:
        x = pd.to_numeric(dev[c], errors="coerce").dropna()
        if len(x) == 0:
            continue
        p1, p99 = np.percentile(x, [1, 99])
        full = pd.to_numeric(built[c], errors="coerce")
        orec.append({
            "feature": c, "dev_p1": p1, "dev_p99": p99,
            "dev_min": float(x.min()), "dev_max": float(x.max()),
            "dev_median": float(x.median()),
            "n_below_p1_full": int((full < p1).sum()),
            "n_above_p99_full": int((full > p99).sum()),
        })
    pd.DataFrame(orec).to_csv(out / "outlier_report.csv", index=False,
                              encoding="utf-8-sig")

    # ---- excel workbook ---------------------------------------------------
    with pd.ExcelWriter(out / "data_audit_report.xlsx") as xw:
        schema.to_excel(xw, sheet_name="schema_check", index=False)
        dup.to_excel(xw, sheet_name="duplicate_check", index=False)
        cls.to_excel(xw, sheet_name="class_distribution", index=False)
        pd.DataFrame(rows).to_excel(xw, sheet_name="target_shift_audit", index=False)
        pd.DataFrame(recs).to_excel(xw, sheet_name="missingness_by_split", index=False)
        pd.DataFrame(orec).to_excel(xw, sheet_name="outlier_report", index=False)
    print(f"[01] data audit written -> {out}")
    return out
