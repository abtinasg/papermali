"""Stage123 — statement-scope correction + eligibility/panel rebuild (no modeling).

Built ON TOP of the approved Stage122 output (does NOT use the old build_dataset.py
candidate/target/split logic). The data owner confirmed every numeric value comes from
the ANNUAL SEPARATE/PARENT company statements, even when the Codal package was titled
"consolidated" — so the prior possible_consolidated / statement_scope_unknown labels were
file-title/metadata artifacts. This stage:
  * corrects statement scope -> annual_separate_company_user_confirmed (eligible),
  * rebuilds eligibility (predictor_eligible_main / _expanded; target NOT a predictor
    condition) and exact t->t+1 pairs,
  * uses an EXPLICIT, version-controlled 9-company main/expanded mapping (no keyword
    re-guessing),
  * uses an explicit target aggregator where ONLY fd_article141_direct is non-blocking;
    any all-missing QUANTITATIVE criterion makes QC FAIL,
  * preserves raw provenance untouched (prior scope only in an immutable audit log),
  * carries the Stage122 target unchanged,
  * runs INDEPENDENT QC (re-reads outputs from disk and checks against raw Stage121),
  * runs NO model / tuning / SHAP / SMOTE / calibration / report. Stage121/Stage122
    files are never overwritten.
"""
from __future__ import annotations
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import utils
from . import stage122 as s122

ROOT = Path(__file__).resolve().parents[1]


class QCFail(Exception):
    """Raised when an independent QC gate fails — halts Stage123."""


# --------------------------------------------------------------------------
# Explicit, version-controlled company decision (NO keyword re-guessing)
# --------------------------------------------------------------------------
COMPANY_SAMPLE_MAPPING = {
    "برکت":  {"main": 0, "expanded": 1, "classification": "operating_holding"},
    "تاپیکو": {"main": 0, "expanded": 1, "classification": "operating_holding"},
    "سفارس":  {"main": 0, "expanded": 1, "classification": "operating_holding"},
    "فارس":   {"main": 0, "expanded": 1, "classification": "operating_holding"},
    "پارسان": {"main": 0, "expanded": 1, "classification": "operating_holding"},
    "ومعادن": {"main": 0, "expanded": 0, "classification": "financial_investment"},
    "وملی":   {"main": 0, "expanded": 0, "classification": "financial_investment"},
    "وکغدیر": {"main": 0, "expanded": 0, "classification": "financial_investment"},
    "کروی":   {"main": 0, "expanded": 0, "classification": "financial_investment"},
}

CONSOLIDATED_SCOPES = {"possible_consolidated_statement", "statement_scope_unknown"}
CORRECTED_SCOPE = "annual_separate_company_user_confirmed"
DISPLAY_LABEL_FA = "صورت‌های مالی سالانه شرکت اصلی/جداگانه"
DISPLAY_LABEL_EN = "annual separate financial statements of the company"

OWNER_CONFIRMATION_FA = (
    "براساس تأیید مستقیم مالک و استخراج‌کننده داده، همه داده‌های عددی از صورت‌های مالی "
    "سالانه شرکت اصلی/جداگانه استخراج شده‌اند؛ حتی در مواردی که بسته گزارش کدال شامل "
    "صورت‌های مالی تلفیقی نیز بوده است.")

QUANT_CRITERIA = ["fd_accumulated_loss", "fd_negative_equity", "fd_ocf_high_leverage"]

# Required output columns; a missing required column halts the run (req 8.13).
REQUIRED_SCHEMA = {
    "modeling_all_rows_stage123.csv": [
        "row_key", "ticker", "fiscal_year", "statement_scope_status", "source_file",
        "FD_target_main", "predictor_eligible_main", "predictor_eligible_expanded",
        "eligible_company_main", "eligible_company_expanded"],
    "modeling_one_year_ahead_stage123.csv": [
        "ticker", "fiscal_year_t", "target_year", "FD_target_main_t_plus_1",
        "predictor_eligible_main_t", "predictor_eligible_expanded_t",
        "valid_target_t_plus_1", "pair_final_eligible_main",
        "pair_final_eligible_expanded", "predictor_row_key_t", "target_row_key_t_plus_1"],
    "eligibility_audit_stage123.csv": [
        "row_key", "ticker", "fiscal_year", "eligible_listing",
        "eligible_statement_type", "eligible_annual_period", "eligible_source_quality",
        "eligible_accounting_quality", "eligible_company_main",
        "eligible_company_expanded", "predictor_eligible_main",
        "predictor_eligible_expanded"],
}


def stage_dir() -> Path:
    d = ROOT / "stage123"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_float(s: pd.Series) -> pd.Series:
    """'0'/'1'/'' -> 0.0/1.0/NaN."""
    return pd.to_numeric(s.replace("", np.nan), errors="coerce")


SOURCE_FILES = ["src/stage122.py", "src/stage123.py",
                "run_stage122.py", "run_stage123.py"]
INTENDED_FREEZE_TAG = "stage123-frozen-v1"


def align_base_to_raw(raw: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Align the Stage122 base to raw by row_key so results never depend on row order.
    Any duplicate / missing / extra row_key raises QCFail."""
    rk_raw, rk_base = raw["row_key"], base["row_key"]
    if rk_raw.duplicated().any():
        raise QCFail("duplicate row_key in raw Stage121")
    if rk_base.duplicated().any():
        raise QCFail("duplicate row_key in Stage122 base")
    sr, sb = set(rk_raw), set(rk_base)
    if sr != sb:
        raise QCFail(f"row_key set mismatch raw vs Stage122 base: "
                     f"missing_in_base={len(sr - sb)}, extra_in_base={len(sb - sr)}")
    return base.set_index("row_key").loc[rk_raw.values].reset_index()


def _source_info() -> dict:
    """git commit + dirtiness of the SOURCE files only (generated outputs ignored) +
    content SHA-256 of the executed source files."""
    hashes = {f: (utils.sha256_file(ROOT / f) if (ROOT / f).exists() else None)
              for f in SOURCE_FILES}
    commit = dirty = tag = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout.strip() or None
        # cwd is the project dir; pathspecs are relative to it (git resolves to repo root)
        st = subprocess.run(["git", "status", "--porcelain", "--", *SOURCE_FILES],
                            cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
        dirty = bool(st)
        tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], cwd=str(ROOT),
                             capture_output=True, text=True).stdout.strip() or None
    except Exception:
        pass
    return {"source_code_commit": commit, "source_tree_dirty_before_run": dirty,
            "source_file_sha256": hashes, "nearest_tag": tag,
            "intended_freeze_tag": INTENDED_FREEZE_TAG}


# --------------------------------------------------------------------------
# Base = approved Stage122 output (NOT the old build_dataset.py pipeline)
# --------------------------------------------------------------------------
def load_stage122_base(cfg) -> pd.DataFrame:
    p = s122.stage_dir(cfg) / "modeling_all_rows_stage122.csv"
    if not p.exists():
        raise QCFail(f"approved Stage122 output not found: {p} — run Stage122 first")
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)


# --------------------------------------------------------------------------
# Explicit target aggregator: only fd_article141_direct is non-blocking;
# an all-missing QUANTITATIVE criterion is a hard failure (req 3 & 12).
# --------------------------------------------------------------------------
def aggregate_fd_target(article141: pd.Series, acc: pd.Series, neg: pd.Series,
                        ocf: pd.Series) -> pd.Series:
    for name, c in [("fd_accumulated_loss", acc), ("fd_negative_equity", neg),
                    ("fd_ocf_high_leverage", ocf)]:
        if int(c.notna().sum()) == 0:
            raise QCFail(f"quantitative criterion {name} is entirely missing — "
                         f"Stage123 aborted (cannot silently drop it)")
    quant = np.vstack([acc.values.astype(float), neg.values.astype(float),
                       ocf.values.astype(float)])
    art = article141.values.astype(float)  # non-blocking direct evidence
    any1 = (np.nansum(quant == 1, axis=0) > 0) | (art == 1)
    anymiss_quant = np.isnan(quant).any(axis=0)  # article141 missingness ignored
    out = np.where(any1, 1.0, np.where(anymiss_quant, np.nan, 0.0))
    return pd.Series(out, index=acc.index)


# --------------------------------------------------------------------------
# Eligibility (main vs expanded) after statement-scope correction
# --------------------------------------------------------------------------
def compute_eligibility123(df, main_target, corrected_mask):
    el = pd.DataFrame(index=df.index)
    A, L, E = (s122._num(df["total_assets"]), s122._num(df["total_liabilities"]),
               s122._num(df["equity"]))

    el["eligible_listing"] = np.where(
        df["ocf_resolution_status"] == "pre_listing_missing_excluded", 0, 1)

    el["eligible_statement_type"] = 1  # all separate/parent after correction
    el["statement_scope_canonical"] = np.where(
        corrected_mask, CORRECTED_SCOPE, df["statement_scope_status"])

    el["eligible_annual_period"] = np.where(df["non_12_month_period_flag"] == "1", 0, 1)
    no_src = df["source_file"].str.strip() == ""
    no_unit = df["unit"].str.strip() == ""
    el["eligible_source_quality"] = np.where(no_src | no_unit, 0, 1)
    rel = (A - (L + E)).abs() / A.abs().clip(lower=1)
    el["eligible_accounting_quality"] = np.where(rel.notna() & (rel > 0.005), 0, 1)

    # explicit, version-controlled company mapping (no keyword guess)
    el["eligible_company_main"] = df["ticker"].map(
        lambda t: COMPANY_SAMPLE_MAPPING.get(t, {}).get("main", 1)).astype(int)
    el["eligible_company_expanded"] = df["ticker"].map(
        lambda t: COMPANY_SAMPLE_MAPPING.get(t, {}).get("expanded", 1)).astype(int)

    el["eligible_target"] = np.where(main_target.isna(), 0, 1)  # column only, NOT predictor

    base = ["eligible_listing", "eligible_statement_type", "eligible_annual_period",
            "eligible_source_quality", "eligible_accounting_quality"]
    base_ok = (el[base] == 1).all(axis=1)
    el["predictor_eligible_main"] = (
        base_ok & (el["eligible_company_main"] == 1)).astype(int)
    el["predictor_eligible_expanded"] = (
        base_ok & (el["eligible_company_expanded"] == 1)).astype(int)

    reason_map = {"eligible_listing": "pre_listing",
                  "eligible_annual_period": "non_12_month_period",
                  "eligible_source_quality": "source_not_traceable",
                  "eligible_accounting_quality": "accounting_quality_issue"}
    rmain, rexp = [], []
    for i in df.index:
        common = [v for k, v in reason_map.items() if el.at[i, k] == 0]
        rmain.append(" | ".join(common + (["financial_or_holding_company"]
                     if el.at[i, "eligible_company_main"] == 0 else [])))
        rexp.append(" | ".join(common + (["financial_company"]
                    if el.at[i, "eligible_company_expanded"] == 0 else [])))
    el["model_exclusion_reason_main"] = rmain
    el["model_exclusion_reason_expanded"] = rexp
    return el


def build_pairs123(df, tgt_main, tgt_a141, tgt_pers, el, name):
    work = pd.DataFrame({
        "ticker": df["ticker"], "company_name": name,
        "year": s122._num(df["fiscal_year"]).astype(int), "row_key": df["row_key"],
        "FD_main": tgt_main.values, "FD_art141": tgt_a141.values,
        "FD_persist": tgt_pers.values,
        "pe_main": el["predictor_eligible_main"].values,
        "pe_exp": el["predictor_eligible_expanded"].values,
        "rsn_main": el["model_exclusion_reason_main"].values,
        "rsn_exp": el["model_exclusion_reason_expanded"].values})
    by = {(r.ticker, r.year): r for r in work.itertuples(index=False)}
    rows = []
    for r in work.itertuples(index=False):
        nxt = by.get((r.ticker, r.year + 1))
        if nxt is None:
            continue
        valid_t1 = 0 if pd.isna(nxt.FD_main) else 1
        pem = int(r.pe_main == 1 and valid_t1 == 1)
        pex = int(r.pe_exp == 1 and valid_t1 == 1)

        def reason(pe, rsn):
            p = []
            if pe != 1:
                p.append("predictor_not_eligible:" + (rsn or "unknown"))
            if valid_t1 != 1:
                p.append("target_t+1_missing")
            return " | ".join(p)
        rows.append({
            "ticker": r.ticker, "company_name": r.company_name,
            "fiscal_year_t": r.year, "target_year": r.year + 1,
            "FD_target_main_t_plus_1": s122._scalar(nxt.FD_main),
            "FD_target_article141_only_t_plus_1": s122._scalar(nxt.FD_art141),
            "FD_target_persistent_loss_robustness_t_plus_1": s122._scalar(nxt.FD_persist),
            "predictor_eligible_main_t": int(r.pe_main),
            "predictor_eligible_expanded_t": int(r.pe_exp),
            "valid_target_t_plus_1": valid_t1,
            "pair_final_eligible_main": pem,
            "pair_final_eligible_expanded": pex,
            "pair_exclusion_reason_main": reason(r.pe_main, r.rsn_main),
            "pair_exclusion_reason_expanded": reason(r.pe_exp, r.rsn_exp),
            "predictor_row_key_t": r.row_key, "target_row_key_t_plus_1": nxt.row_key})
    return pd.DataFrame(rows)


# Year-t predictor feature universe (used by leakage manifest + QC no-future check)
ALLOWED_T_PREDICTORS = [
    ("leverage_ratio", "year-t leverage"),
    ("operating_cash_flow_period_adjusted", "year-t operating cash flow"),
    ("equity", "year-t equity"),
    ("total_assets", "year-t total assets"),
    ("total_liabilities", "year-t total liabilities"),
    ("accumulated_loss", "year-t raw accumulated loss"),
    ("registered_capital", "year-t registered capital"),
    ("net_income_period_adjusted", "year-t net income"),
    ("current_ratio", "year-t liquidity"),
    ("roa_period_adjusted", "year-t profitability"),
    ("roe_period_adjusted", "year-t profitability"),
    ("ocf_to_assets_period_adjusted", "year-t cash-flow ratio"),
    ("financial_expense_to_assets_period_adjusted", "year-t expense ratio"),
    ("operating_margin_period_adjusted", "year-t margin"),
    ("net_margin_period_adjusted", "year-t margin"),
    ("gross_margin_period_adjusted", "year-t margin"),
    ("asset_turnover_period_adjusted", "year-t efficiency"),
    ("revenue_growth_period_adjusted", "year-t growth"),
    ("net_income_growth_period_adjusted", "year-t growth"),
    ("log_total_assets", "year-t size (engineered)"),
    ("industry", "year-t sector"),
]
NEAR_TARGET_PREDICTORS = [
    ("accumulated_loss_to_capital_ratio", "year-t accumulated-loss/capital ratio"),
    ("equity_negative_dummy", "year-t negative-equity dummy"),
    ("loss_dummy", "year-t net-loss dummy"),
    ("fd_accumulated_loss", "year-t accumulated-loss criterion"),
    ("fd_negative_equity", "year-t negative-equity criterion"),
    ("fd_ocf_high_leverage", "year-t OCF<0 & leverage>0.70 criterion"),
    ("fd_article141_direct", "year-t article-141 criterion (unobserved)"),
    ("ocf_neg_high_leverage_combo_t", "year-t direct OCF<0 AND leverage>0.70 combination"),
    ("FD_target_main", "year-t (lagged) target — only if explicitly used as lag"),
]
PROHIBITED_LEAKAGE = [
    ("FD_target_main_t_plus_1", "next-year (t+1) target outcome"),
    ("FD_target_article141_only_t_plus_1", "next-year (t+1) robustness target"),
    ("FD_target_persistent_loss_robustness_t_plus_1", "next-year (t+1) robustness target"),
    ("target_valid_t_plus_1", "derived from t+1 target"),
    ("distressed_target_reviewed", "Stage121 target label / provenance"),
    ("target_status_reviewed", "target provenance"),
    ("distressed_flag_source_reviewed", "target provenance"),
    ("positive_target_reasons", "derived from the target"),
    ("target_missing_reason", "derived from the target"),
]


def leakage_manifest123() -> pd.DataFrame:
    rows = []
    for c, n in PROHIBITED_LEAKAGE:
        rows.append({"column": c, "group": "prohibited_leakage", "note": n})
    for c, n in ALLOWED_T_PREDICTORS:
        rows.append({"column": c, "group": "allowed_t_predictor", "note": n})
    for c, n in NEAR_TARGET_PREDICTORS:
        rows.append({"column": c, "group": "near_target_predictor", "note": n})
    return pd.DataFrame(rows)


def write_company_mapping(out: Path) -> pd.DataFrame:
    rows = [{"ticker": t, "main": m["main"], "expanded": m["expanded"],
             "classification": m["classification"],
             "decision_basis": "user_confirmed_manual_review"}
            for t, m in COMPANY_SAMPLE_MAPPING.items()]
    df = pd.DataFrame(rows)
    df.to_csv(out / "company_sample_mapping_stage123.csv", index=False,
              encoding="utf-8-sig")
    return df


# ==========================================================================
# Orchestrator
# ==========================================================================
def build_full(cfg) -> dict:
    t0 = time.time()
    out = stage_dir()
    src_info = _source_info()                     # capture BEFORE any output is written
    raw = s122.load_all_rows(cfg)                 # raw Stage121 (read-only)
    base_raw = load_stage122_base(cfg)            # approved Stage122 output (req 2)
    base = align_base_to_raw(raw, base_raw)       # row_key align; QCFail on mismatch/dup
    base_path = s122.stage_dir(cfg) / "modeling_all_rows_stage122.csv"

    # recompute criteria/target from RAW via the guarded aggregator and verify they
    # match the (row_key-aligned) Stage122 target — order-independent by construction.
    crit = s122.compute_criteria(raw)
    target = aggregate_fd_target(crit["fd_article141_direct"], crit["fd_accumulated_loss"],
                                 crit["fd_negative_equity"], crit["fd_ocf_high_leverage"])
    base_target = _to_float(base["FD_target_main"])
    same = ((target.isna() & base_target.isna()) | (target == base_target))
    if not bool(same.all()):
        raise QCFail(f"recomputed FD_target_main disagrees with Stage122 on "
                     f"{int((~same).sum())} rows after row_key alignment")

    n_before = len(raw)
    dup_before = int(raw.duplicated(["ticker", "fiscal_year"]).sum())
    main = target
    a141 = _to_float(base["FD_target_article141_only"])
    pers = _to_float(base["FD_target_persistent_loss_robustness"])
    name, name_info = s122.fill_company_name(raw)

    # ---- statement-scope correction (canonical only; provenance untouched) ----
    prev_scope = base["statement_scope_status"]
    corrected_mask = prev_scope.isin(CONSOLIDATED_SCOPES)
    n_corrected = int(corrected_mask.sum())
    corr = base.loc[corrected_mask, ["row_key", "ticker", "fiscal_year",
                                     "source_file", "source_url"]].copy()
    corr["previous_statement_scope"] = prev_scope[corrected_mask].values
    corr["corrected_statement_scope"] = CORRECTED_SCOPE
    corr["correction_basis"] = "explicit_data_owner_confirmation"
    corr["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    corr.to_csv(out / "statement_scope_correction_audit_stage123.csv", index=False,
                encoding="utf-8-sig")

    el = compute_eligibility123(base, main, corrected_mask)

    # pre-correction eligibility (isolate the correction effect, all else held equal)
    base_pre_stmt = np.where(corrected_mask, 0, 1)
    base_ok_pre = ((el["eligible_listing"] == 1) & (base_pre_stmt == 1) &
                   (el["eligible_annual_period"] == 1) &
                   (el["eligible_source_quality"] == 1) &
                   (el["eligible_accounting_quality"] == 1))
    pe_main_pre = (base_ok_pre & (el["eligible_company_main"] == 1)).astype(int)
    pe_exp_pre = (base_ok_pre & (el["eligible_company_expanded"] == 1)).astype(int)

    pairs = build_pairs123(base, main, a141, pers, el, name)
    el_pre = el.copy()
    el_pre["predictor_eligible_main"] = pe_main_pre.values
    el_pre["predictor_eligible_expanded"] = pe_exp_pre.values
    pairs_pre = build_pairs123(base, main, a141, pers, el_pre, name)

    # ---- modeling_all_rows_stage123 -------------------------------------
    allrows = raw.copy()
    allrows["company_name"] = name
    allrows["statement_scope_status"] = el["statement_scope_canonical"].values  # canonical
    allrows["statement_scope_display_fa"] = DISPLAY_LABEL_FA
    for c in ["fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
              "fd_ocf_high_leverage"]:
        allrows[c] = s122._csvnum(crit[c])
    allrows["FD_target_main"] = s122._csvnum(main)
    allrows["FD_target_article141_only"] = base["FD_target_article141_only"].values
    allrows["FD_target_persistent_loss_robustness"] = base[
        "FD_target_persistent_loss_robustness"].values
    allrows["positive_target_reasons"] = s122.positive_target_reasons(crit, main).values
    allrows["target_missing_reason"] = s122.target_missing_reason(raw, crit, main).values
    for c in ["eligible_listing", "eligible_statement_type", "eligible_annual_period",
              "eligible_source_quality", "eligible_accounting_quality",
              "eligible_company_main", "eligible_company_expanded", "eligible_target",
              "predictor_eligible_main", "predictor_eligible_expanded",
              "model_exclusion_reason_main", "model_exclusion_reason_expanded"]:
        allrows[c] = el[c].values
    allrows.to_csv(out / "modeling_all_rows_stage123.csv", index=False,
                   encoding="utf-8-sig")
    n_after = len(allrows)
    dup_after = int(allrows.duplicated(["ticker", "fiscal_year"]).sum())

    pairs.to_csv(out / "modeling_one_year_ahead_stage123.csv", index=False,
                 encoding="utf-8-sig")
    ea = pd.concat([base[["row_key", "ticker", "fiscal_year"]].reset_index(drop=True),
                    name.rename("company_name").reset_index(drop=True),
                    el.reset_index(drop=True)], axis=1)
    ea.to_csv(out / "eligibility_audit_stage123.csv", index=False, encoding="utf-8-sig")

    review = _company_review(base, name)
    review.to_csv(out / "eligibility_company_review_stage123.csv", index=False,
                  encoding="utf-8-sig")
    listing = _listing_review(base, name)
    listing.to_csv(out / "listing_date_review_stage123.csv", index=False,
                   encoding="utf-8-sig")
    leak = leakage_manifest123()
    leak.to_csv(out / "leakage_manifest_stage123.csv", index=False, encoding="utf-8-sig")
    mapping = write_company_mapping(out)

    # ---- INDEPENDENT QC (re-read from disk; compare to raw) ---------------
    qc = independent_qc(cfg, out, raw, n_before, n_after, dup_before, dup_after,
                        n_corrected, name_info, pairs, pairs_pre, el, pe_main_pre,
                        pe_exp_pre, main)
    # QC report is ALWAYS saved first; on failure we raise BEFORE writing metadata
    # so a successful metadata file never accompanies a failed QC (req 5).
    utils.save_json(qc, out / "stage123_qc_report.json")
    if not qc["overall_pass"]:
        failed = [c["check"] for c in qc["checks"] if c["status"] == "FAIL"]
        raise QCFail(f"independent QC failed (report saved): {failed}")

    changelog = _change_log(qc, n_corrected)
    changelog.to_csv(out / "stage123_change_log.csv", index=False, encoding="utf-8-sig")
    _excel(out, base, el, ea, review, listing, pairs, leak, mapping, corr, qc)
    meta = _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0,
                     base_path, base, src_info)
    utils.save_json(meta, out / "metadata_and_hashes_stage123.json")
    print(f"[stage123] complete in {time.time()-t0:.1f}s -> {out} | "
          f"QC overall_pass={qc['overall_pass']}")
    return {"qc": qc, "pairs": pairs, "out": out, "meta": meta}


# ==========================================================================
# Independent QC — re-reads written files from disk and checks vs RAW
# ==========================================================================
def independent_qc(cfg, out, raw, n_before, n_after, dup_before, dup_after,
                   n_corrected, name_info, pairs_mem, pairs_pre, el, pe_main_pre,
                   pe_exp_pre, main_target):
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                       "detail": str(detail)})

    # schema validation first (req 13) — missing required column halts
    for fn, cols in REQUIRED_SCHEMA.items():
        p = out / fn
        if not p.exists():
            raise QCFail(f"required output missing: {fn}")
        hdr = pd.read_csv(p, nrows=0, encoding="utf-8-sig").columns.tolist()
        miss = [c for c in cols if c not in hdr]
        if miss:
            raise QCFail(f"{fn} missing required columns: {miss}")
        add(f"schema::{fn}", True, "all required columns present")

    # re-read from disk
    mar = pd.read_csv(out / "modeling_all_rows_stage123.csv", dtype=str,
                      encoding="utf-8-sig", keep_default_na=False)
    pairs = pd.read_csv(out / "modeling_one_year_ahead_stage123.csv", dtype=str,
                        encoding="utf-8-sig", keep_default_na=False)
    ead = pd.read_csv(out / "eligibility_audit_stage123.csv", dtype=str,
                      encoding="utf-8-sig", keep_default_na=False)
    mapping_disk = pd.read_csv(out / "company_sample_mapping_stage123.csv", dtype=str,
                               keep_default_na=False)

    # 1) missing target stays EMPTY (not 0) after round-trip vs independent recompute
    crit = s122.compute_criteria(raw)
    target = aggregate_fd_target(crit["fd_article141_direct"], crit["fd_accumulated_loss"],
                                 crit["fd_negative_equity"], crit["fd_ocf_high_leverage"])
    exp_missing = int(target.isna().sum())
    disk_empty = int((mar["FD_target_main"] == "").sum())
    disk_zero = int((mar["FD_target_main"] == "0").sum())
    add("missing_target_not_zero_on_disk",
        disk_empty == exp_missing and (target == 0).sum() == disk_zero,
        f"disk_empty={disk_empty}, expected_missing={exp_missing}, disk_zero={disk_zero}")

    # 2) rows & companies preserved
    add("rows_preserved", n_before == n_after == len(mar) == len(raw),
        f"{n_before}/{n_after}/{len(mar)}")
    add("companies_preserved",
        mar["ticker"].nunique() == raw["ticker"].nunique(),
        f"{mar['ticker'].nunique()} vs {raw['ticker'].nunique()}")

    # 3) duplicate ticker+fiscal_year == 0
    add("no_duplicate_row_keys",
        int(mar.duplicated(["ticker", "fiscal_year"]).sum()) == 0)

    # 4) duplicate pair ticker+fiscal_year_t == 0
    add("no_duplicate_pairs",
        int(pairs.duplicated(["ticker", "fiscal_year_t"]).sum()) == 0)

    # 5) target_year == fiscal_year_t + 1
    yt = pd.to_numeric(pairs["fiscal_year_t"]); ty = pd.to_numeric(pairs["target_year"])
    add("pairs_exact_plus_one", bool((ty == yt + 1).all()))

    # 6) no year gaps (same as 5 by construction; verify no |gap|!=1)
    add("no_year_gaps", bool(((ty - yt) == 1).all()))

    # 7) source_file & source_url unchanged vs raw (by row_key)
    rawk = raw.set_index("row_key"); disk = mar.set_index("row_key")
    sf_ok = bool((disk.loc[rawk.index, "source_file"] == rawk["source_file"]).all())
    su_ok = bool((disk.loc[rawk.index, "source_url"] == rawk["source_url"]).all())
    add("source_file_unchanged", sf_ok)
    add("source_url_unchanged", su_ok)

    # 7b) NO financial value changed (all numeric cols identical vs raw)
    num_cols = ["total_assets", "total_liabilities", "equity", "registered_capital",
                "accumulated_loss", "operating_cash_flow_period_adjusted",
                "net_income_period_adjusted", "leverage_ratio", "current_ratio",
                "roa_period_adjusted", "net_margin_period_adjusted"]
    fin_ok = all(bool((disk.loc[rawk.index, c] == rawk[c]).all()) for c in num_cols)
    add("no_financial_value_changed", fin_ok, f"checked {len(num_cols)} numeric columns")

    # 8) all 9 companies match manual mapping exactly; no other ticker excluded
    map_ok = True; detail = []
    for t, m in COMPANY_SAMPLE_MAPPING.items():
        sub = ead[ead["ticker"] == t]
        if sub.empty:
            map_ok = False; detail.append(f"{t}:absent"); continue
        if not (sub["eligible_company_main"] == str(m["main"])).all():
            map_ok = False; detail.append(f"{t}:main")
        if not (sub["eligible_company_expanded"] == str(m["expanded"])).all():
            map_ok = False; detail.append(f"{t}:expanded")
    others_excluded = ead[(~ead["ticker"].isin(COMPANY_SAMPLE_MAPPING)) &
                          (ead["eligible_company_main"] == "0")]
    if len(others_excluded):
        map_ok = False; detail.append(f"unexpected_excluded={others_excluded['ticker'].unique().tolist()}")
    add("manual_company_mapping_exact", map_ok, detail or "9 tickers match; no others excluded")

    # 9) statement-scope corrections counted & logged; none consolidated remain
    corr_disk = pd.read_csv(out / "statement_scope_correction_audit_stage123.csv",
                            dtype=str, keep_default_na=False)
    raw_consol = int(raw["statement_scope_status"].isin(CONSOLIDATED_SCOPES).sum())
    add("statement_corrections_logged", len(corr_disk) == n_corrected == raw_consol,
        f"logged={len(corr_disk)}, raw_consolidated={raw_consol}")
    add("no_consolidated_in_canonical",
        int(mar["statement_scope_status"].isin(CONSOLIDATED_SCOPES).sum()) == 0)

    # 10) no pre-listing row in final pairs (independent of eligibility flag, from raw)
    pre = set(raw.loc[raw["ocf_resolution_status"] == "pre_listing_missing_excluded",
                      "row_key"])
    bad_main = pairs[(pairs["predictor_row_key_t"].isin(pre)) &
                     (pairs["pair_final_eligible_main"] == "1")]
    bad_exp = pairs[(pairs["predictor_row_key_t"].isin(pre)) &
                    (pairs["pair_final_eligible_expanded"] == "1")]
    add("no_pre_listing_in_final_pairs", len(bad_main) == 0 and len(bad_exp) == 0,
        f"main={len(bad_main)}, expanded={len(bad_exp)}")

    # 11) no future (t+1 / prohibited) columns in the predictor feature universe
    predictor_universe = [c for c, _ in ALLOWED_T_PREDICTORS + NEAR_TARGET_PREDICTORS]
    prohibited = {c for c, _ in PROHIBITED_LEAKAGE}
    future_like = [c for c in predictor_universe
                   if c.endswith("_t_plus_1") or c in prohibited]
    add("no_future_columns_in_predictor_manifest", len(future_like) == 0,
        f"offenders={future_like}")

    # 12) no quantitative criterion all-missing (already enforced by aggregator)
    allmiss = [c for c in QUANT_CRITERIA if int(crit[c].notna().sum()) == 0]
    add("no_quantitative_criterion_all_missing", len(allmiss) == 0,
        f"all_missing={allmiss}")

    # 13) non-financial controls still hold (independent: from raw markers)
    non12 = set(raw.loc[raw["non_12_month_period_flag"] == "1", "row_key"])
    bad_non12 = pairs[(pairs["predictor_row_key_t"].isin(non12)) &
                      (pairs["pair_final_eligible_main"] == "1")]
    add("no_non12month_in_final_pairs_main", len(bad_non12) == 0, f"{len(bad_non12)}")

    overall = all(c["status"] == "PASS" for c in checks)

    # distributions (reported, not pass/fail)
    def posneg(pf, flag):
        pe = pf[pf[flag] == 1]["FD_target_main_t_plus_1"] if pf[flag].dtype != object \
            else pf[pf[flag] == "1"]["FD_target_main_t_plus_1"]
        return {"n": int(len(pe)), "pos": int((pe.astype(str) == "1").sum()),
                "neg": int((pe.astype(str) == "0").sum())}

    def dist_year(pf, flag):
        pe = pf[pf[flag].astype(str) == "1"]
        d = {}
        for y in sorted(pd.to_numeric(pe["target_year"]).unique()):
            s = pe[pd.to_numeric(pe["target_year"]) == y]["FD_target_main_t_plus_1"]
            d[int(y)] = {"n": int(len(s)), "pos": int((s.astype(str) == "1").sum())}
        return d

    return {
        "stage": "stage123", "owner_confirmation": OWNER_CONFIRMATION_FA,
        "overall_pass": overall,
        "checks": checks,
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "statement_scope_correction": {"affected_row_count": n_corrected,
                                       "corrected_to": CORRECTED_SCOPE},
        "rows_re_eligible_due_to_correction": {
            "main": int(((el["predictor_eligible_main"] == 1) & (pe_main_pre == 0)
                         & pd.Series(raw["statement_scope_status"].isin(
                             CONSOLIDATED_SCOPES).values, index=el.index)).sum()),
            "expanded": int(((el["predictor_eligible_expanded"] == 1) &
                             (pe_exp_pre == 0) & pd.Series(
                                 raw["statement_scope_status"].isin(
                                     CONSOLIDATED_SCOPES).values, index=el.index)).sum())},
        "predictor_eligible_counts": {
            "main": int((el["predictor_eligible_main"] == 1).sum()),
            "expanded": int((el["predictor_eligible_expanded"] == 1).sum())},
        "pairs_total": int(len(pairs_mem)),
        "pair_final_eligible_main_before_after": {
            "before": int((pairs_pre["pair_final_eligible_main"] == 1).sum()),
            "after": int((pairs_mem["pair_final_eligible_main"] == 1).sum())},
        "pair_final_eligible_expanded_before_after": {
            "before": int((pairs_pre["pair_final_eligible_expanded"] == 1).sum()),
            "after": int((pairs_mem["pair_final_eligible_expanded"] == 1).sum())},
        "pair_posneg_main_after": posneg(pairs_mem, "pair_final_eligible_main"),
        "pair_posneg_expanded_after": posneg(pairs_mem, "pair_final_eligible_expanded"),
        "annual_target_dist_main_after": dist_year(pairs_mem, "pair_final_eligible_main"),
        "annual_target_dist_main_before": dist_year(pairs_pre, "pair_final_eligible_main"),
        "events_1401_1402_main": {
            "1401_before": int(((pairs_pre["pair_final_eligible_main"] == 1) &
                                (pairs_pre["target_year"] == 1401) &
                                (pairs_pre["FD_target_main_t_plus_1"] == "1")).sum()),
            "1401_after": int(((pairs_mem["pair_final_eligible_main"] == 1) &
                               (pairs_mem["target_year"] == 1401) &
                               (pairs_mem["FD_target_main_t_plus_1"] == "1")).sum()),
            "1402_before": int(((pairs_pre["pair_final_eligible_main"] == 1) &
                                (pairs_pre["target_year"] == 1402) &
                                (pairs_pre["FD_target_main_t_plus_1"] == "1")).sum()),
            "1402_after": int(((pairs_mem["pair_final_eligible_main"] == 1) &
                               (pairs_mem["target_year"] == 1402) &
                               (pairs_mem["FD_target_main_t_plus_1"] == "1")).sum())},
        "target_unchanged_from_stage122": {
            "1": int((main_target == 1).sum()), "0": int((main_target == 0).sum()),
            "missing": int(main_target.isna().sum())},
        "company_name_fill": name_info,
    }


def _company_review(base, name):
    recs = []
    for tk, m in COMPANY_SAMPLE_MAPPING.items():
        g = base[base["ticker"] == tk]
        nm = name[base["ticker"] == tk]
        recs.append({"ticker": tk,
                     "company_name": nm.iloc[0] if len(nm) else "",
                     "industry": " ; ".join(sorted(set(g["industry"]))) if len(g) else "",
                     "n_rows": int(len(g)), "classification": m["classification"],
                     "in_main_sample": m["main"], "in_expanded_sample": m["expanded"],
                     "decision_basis": "user_confirmed_manual_review"})
    return pd.DataFrame(recs)


def _listing_review(base, name):
    m = base["ocf_resolution_status"] == "pre_listing_missing_excluded"
    sub = base[m]
    return pd.DataFrame({
        "ticker": sub["ticker"].values, "company_name": name[m].values,
        "fiscal_year": sub["fiscal_year"].values,
        "pre_listing_marker": "pre_listing_missing_excluded", "eligible_listing": 0,
        "review_note": "excluded as pre-listing; no explicit public-trading-start-date "
                       "column in data — confirm manually if a listing master appears",
        "review_status": "pending_manual_confirmation"})


def _change_log(qc, n_corrected):
    rows = [
        {"change": "statement_scope_corrected",
         "detail": f"{n_corrected} rows possible_consolidated/unknown -> {CORRECTED_SCOPE} "
                   f"(explicit_data_owner_confirmation)"},
        {"change": "rows_re_eligible",
         "detail": f"{qc['rows_re_eligible_due_to_correction']}"},
        {"change": "pairs_main_before_after",
         "detail": f"{qc['pair_final_eligible_main_before_after']}"},
        {"change": "pairs_expanded_before_after",
         "detail": f"{qc['pair_final_eligible_expanded_before_after']}"},
        {"change": "company_mapping_explicit",
         "detail": "main excludes 9; expanded excludes 4 financials; version-controlled"},
        {"change": "pair_eligibility_independent_of_target_t", "detail": "fixed"},
        {"change": "leakage_3_class",
         "detail": "prohibited_leakage / allowed_t_predictor / near_target_predictor"},
        {"change": "target_unchanged",
         "detail": f"{qc['target_unchanged_from_stage122']}"},
        {"change": "independent_qc_overall_pass", "detail": str(qc["overall_pass"])},
    ]
    return pd.DataFrame(rows)


def _excel(out, base, el, ea, review, listing, pairs, leak, mapping, corr, qc):
    annual = pd.DataFrame(
        [{"target_year": y, "stage": "main_after", **v}
         for y, v in qc["annual_target_dist_main_after"].items()] +
        [{"target_year": y, "stage": "main_before", **v}
         for y, v in qc["annual_target_dist_main_before"].items()])
    verify = pd.DataFrame(qc["checks"])
    with pd.ExcelWriter(out / "stage123_workbook.xlsx") as xw:
        pd.DataFrame([{"owner_confirmation_fa": OWNER_CONFIRMATION_FA}]).to_excel(
            xw, sheet_name="owner_confirmation", index=False)
        corr.head(2000).to_excel(xw, sheet_name="statement_scope_correction", index=False)
        ea.head(2000).to_excel(xw, sheet_name="eligibility_row_audit", index=False)
        mapping.to_excel(xw, sheet_name="company_sample_mapping", index=False)
        review.to_excel(xw, sheet_name="company_review", index=False)
        listing.to_excel(xw, sheet_name="listing_date_review", index=False)
        pairs.head(2000).to_excel(xw, sheet_name="one_year_ahead_pairs", index=False)
        annual.to_excel(xw, sheet_name="pair_annual_distribution", index=False)
        leak.to_excel(xw, sheet_name="leakage_manifest", index=False)
        verify.to_excel(xw, sheet_name="stage123_independent_qc", index=False)


def _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0,
              base_path, base_aligned, src_info):
    inp = utils.raw_path(cfg, "all_rows_csv")
    out_hashes = {p.name: utils.sha256_file(p) for p in sorted(out.glob("*"))
                  if p.is_file() and p.name != "metadata_and_hashes_stage123.json"}
    stage122_base = {
        "name": base_path.name,
        "sha256": utils.sha256_file(base_path) if base_path.exists() else None,
        "n_rows": int(len(base_aligned)),
        "n_duplicate_keys": int(base_aligned.duplicated(["ticker", "fiscal_year"]).sum()),
    }
    return {
        "stage": "stage123", "owner_confirmation": OWNER_CONFIRMATION_FA,
        "input_file_stage121": {"name": inp.name, "sha256": utils.sha256_file(inp)},
        "stage122_base_file": stage122_base,
        "output_files_sha256": out_hashes,
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        # source provenance (req 2 & 3): commit, source-only dirtiness, source hashes
        "source_code_commit": src_info["source_code_commit"],
        "source_tree_dirty_before_run": src_info["source_tree_dirty_before_run"],
        "source_file_sha256": src_info["source_file_sha256"],
        "nearest_tag": src_info["nearest_tag"],
        "intended_freeze_tag": src_info["intended_freeze_tag"],
        "python": sys.version, "platform": platform.platform(),
        "library_versions": utils.env_report(), "seed": cfg.get("seed", 42),
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "runtime_seconds": round(time.time() - t0, 2),
    }
