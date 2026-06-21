"""Stage123 — statement-scope correction + eligibility/panel rebuild (no modeling).

The data owner explicitly confirmed that every numeric value was extracted from the
ANNUAL SEPARATE/PARENT company statements, even when the Codal package was titled
"consolidated". So the prior `possible_consolidated_statement` / `statement_scope_unknown`
labels reflected file-title/metadata ambiguity, NOT consolidated numbers. This stage:
  * corrects statement scope -> annual_separate_company_user_confirmed (eligible),
  * rebuilds eligibility with main vs expanded company sets,
  * rebuilds t->t+1 pairs with pair eligibility that does NOT depend on the year-t
    target (only on year-(t+1) target validity),
  * preserves all raw provenance untouched (the prior scope lives only in an immutable
    correction audit log),
  * carries the Stage122 target unchanged (no target rebuild),
  * runs NO model / tuning / SHAP / SMOTE. Stage121/Stage122 files are not overwritten.
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

# Finalized company decision (user-confirmed manual review of Stage122 suspects)
MAIN_EXCLUDE_TICKERS = {"برکت", "تاپیکو", "سفارس", "فارس", "پارسان",
                        "ومعادن", "وملی", "وکغدیر", "کروی"}
EXPANDED_EXCLUDE_TICKERS = {"ومعادن", "وملی", "وکغدیر", "کروی"}  # only financials

CONSOLIDATED_SCOPES = {"possible_consolidated_statement", "statement_scope_unknown"}
CORRECTED_SCOPE = "annual_separate_company_user_confirmed"
DISPLAY_LABEL_EN = "annual separate financial statements of the company"
DISPLAY_LABEL_FA = "صورت‌های مالی سالانه شرکت اصلی/جداگانه"

OWNER_CONFIRMATION_FA = (
    "براساس تأیید مستقیم مالک و استخراج‌کننده داده، همه داده‌های عددی از صورت‌های مالی "
    "سالانه شرکت اصلی/جداگانه استخراج شده‌اند؛ حتی در مواردی که بسته گزارش کدال شامل "
    "صورت‌های مالی تلفیقی نیز بوده است.")


def stage_dir() -> Path:
    d = ROOT / "stage123"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ==========================================================================
# Eligibility (main vs expanded) after statement-scope correction
# ==========================================================================
def compute_eligibility123(df, main_target, corrected_scope_mask):
    """Return eligibility frame. Statement type is 1 for every row after correction
    (the only prior 0s were the consolidated/unknown rows now confirmed separate)."""
    el = pd.DataFrame(index=df.index)
    A, L, E = (s122._num(df["total_assets"]), s122._num(df["total_liabilities"]),
               s122._num(df["equity"]))

    # listing (controlled pre-listing marker)
    el["eligible_listing"] = np.where(
        df["ocf_resolution_status"] == "pre_listing_missing_excluded", 0, 1)

    # statement type — corrected: separate/parent for all -> 1 everywhere
    el["eligible_statement_type"] = 1
    el["statement_scope_canonical"] = np.where(
        corrected_scope_mask, CORRECTED_SCOPE, df["statement_scope_status"])
    el["statement_scope_display_fa"] = DISPLAY_LABEL_FA
    el["statement_scope_display_en"] = DISPLAY_LABEL_EN

    # annual 12-month period
    el["eligible_annual_period"] = np.where(df["non_12_month_period_flag"] == "1", 0, 1)

    # source quality
    no_src = df["source_file"].str.strip() == ""
    no_unit = df["unit"].str.strip() == ""
    el["eligible_source_quality"] = np.where(no_src | no_unit, 0, 1)

    # accounting quality (serious equation residual -> 0)
    rel = (A - (L + E)).abs() / A.abs().clip(lower=1)
    el["eligible_accounting_quality"] = np.where(rel.notna() & (rel > 0.005), 0, 1)

    # company decision (finalized): main excludes 9, expanded excludes 4 financials
    el["eligible_company_main"] = (~df["ticker"].isin(MAIN_EXCLUDE_TICKERS)).astype(int)
    el["eligible_company_expanded"] = (
        ~df["ticker"].isin(EXPANDED_EXCLUDE_TICKERS)).astype(int)

    # target (kept as a column; NOT part of predictor eligibility — see item 7)
    el["eligible_target"] = np.where(main_target.isna(), 0, 1)

    base = ["eligible_listing", "eligible_statement_type", "eligible_annual_period",
            "eligible_source_quality", "eligible_accounting_quality"]
    base_ok = (el[base] == 1).all(axis=1)
    el["predictor_eligible_main"] = (
        base_ok & (el["eligible_company_main"] == 1)).astype(int)
    el["predictor_eligible_expanded"] = (
        base_ok & (el["eligible_company_expanded"] == 1)).astype(int)

    # exclusion reasons (predictor-level; target NOT included)
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


def build_pairs123(df, tgt, el, name):
    work = pd.DataFrame({
        "ticker": df["ticker"], "company_name": name,
        "year": s122._num(df["fiscal_year"]).astype(int), "row_key": df["row_key"],
        "FD_main": tgt["FD_target_main"].values,
        "FD_art141": tgt["FD_target_article141_only"].values,
        "FD_persist": tgt["FD_target_persistent_loss_robustness"].values,
        "pe_main": el["predictor_eligible_main"].values,
        "pe_exp": el["predictor_eligible_expanded"].values,
        "rsn_main": el["model_exclusion_reason_main"].values,
        "rsn_exp": el["model_exclusion_reason_expanded"].values,
    })
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
            "predictor_row_key_t": r.row_key, "target_row_key_t_plus_1": nxt.row_key,
        })
    return pd.DataFrame(rows)


def leakage_manifest123() -> pd.DataFrame:
    """Three groups (item 8). Year-t financials are NOT leakage merely because they
    resemble the t+1 target definition — they are allowed/near-target predictors."""
    rows = []
    prohibited = [
        ("FD_target_main", "target column (year t+1 outcome)"),
        ("FD_target_article141_only", "robustness target column"),
        ("FD_target_persistent_loss_robustness", "robustness target column"),
        ("FD_target_main_t_plus_1", "next-year target"),
        ("FD_target_article141_only_t_plus_1", "next-year target"),
        ("FD_target_persistent_loss_robustness_t_plus_1", "next-year target"),
        ("fd_article141_direct", "target criterion"),
        ("fd_accumulated_loss", "target criterion"),
        ("fd_negative_equity", "target criterion"),
        ("fd_ocf_high_leverage", "target criterion"),
        ("positive_target_reasons", "derived from target"),
        ("target_missing_reason", "derived from target"),
        ("distressed_target_reviewed", "Stage121 target label"),
        ("target_status_reviewed", "target provenance"),
        ("distressed_flag_source_reviewed", "target provenance"),
        ("accumulated_loss_to_capital_ratio", "alias of accumulated-loss criterion"),
        ("equity_negative_dummy", "alias of negative-equity criterion"),
        ("loss_dummy", "alias of net-loss component"),
    ]
    near = [
        ("accumulated_loss", "year-t input to accumulated-loss criterion"),
        ("registered_capital", "year-t denominator of accumulated-loss ratio"),
        ("equity", "year-t input to negative-equity criterion"),
        ("operating_cash_flow_period_adjusted", "year-t input to OCF criterion"),
        ("total_liabilities", "year-t leverage numerator"),
        ("total_assets", "year-t leverage denominator"),
        ("leverage_ratio", "year-t leverage"),
        ("net_income_period_adjusted", "year-t input to persistent-loss target"),
    ]
    allowed = [
        ("current_ratio", "year-t liquidity ratio"),
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
    for c, n in prohibited:
        rows.append({"column": c, "group": "prohibited_leakage", "note": n})
    for c, n in near:
        rows.append({"column": c, "group": "near_target_predictor", "note": n})
    for c, n in allowed:
        rows.append({"column": c, "group": "allowed_t_predictor", "note": n})
    return pd.DataFrame(rows)


# ==========================================================================
# Orchestrator
# ==========================================================================
def build_full(cfg) -> dict:
    t0 = time.time()
    out = stage_dir()
    df = s122.load_all_rows(cfg)
    n_before = len(df)
    dup_before = int(df.duplicated(["ticker", "fiscal_year"]).sum())

    crit = s122.compute_criteria(df)
    tgt = s122.compute_targets(df, crit)
    main = tgt["FD_target_main"]
    name, name_info = s122.fill_company_name(df)

    # ---- statement-scope correction --------------------------------------
    prev_scope = df["statement_scope_status"]
    corrected_mask = prev_scope.isin(CONSOLIDATED_SCOPES)
    n_corrected = int(corrected_mask.sum())
    corr_audit = df.loc[corrected_mask, ["row_key", "ticker", "fiscal_year",
                                         "source_file", "source_url"]].copy()
    corr_audit["previous_statement_scope"] = prev_scope[corrected_mask].values
    corr_audit["corrected_statement_scope"] = CORRECTED_SCOPE
    corr_audit["correction_basis"] = "explicit_data_owner_confirmation"
    corr_audit.to_csv(out / "statement_scope_correction_audit_stage123.csv",
                      index=False, encoding="utf-8-sig")

    # ---- eligibility (main/expanded) -------------------------------------
    el = compute_eligibility123(df, main, corrected_mask)

    # ---- pre-correction eligibility (to isolate the correction effect) ----
    el_pre = el.copy()
    el_pre_stmt = np.where(corrected_mask, 0, 1)  # statement type BEFORE correction
    base_pre = ((el["eligible_listing"] == 1) & (el_pre_stmt == 1) &
                (el["eligible_annual_period"] == 1) &
                (el["eligible_source_quality"] == 1) &
                (el["eligible_accounting_quality"] == 1))
    pe_main_pre = (base_pre & (el["eligible_company_main"] == 1)).astype(int)
    pe_exp_pre = (base_pre & (el["eligible_company_expanded"] == 1)).astype(int)

    # ---- pairs (post-correction) -----------------------------------------
    pairs = build_pairs123(df, tgt, el, name)
    # pairs pre-correction (same formula, statement type pre)
    el_preframe = el.copy()
    el_preframe["predictor_eligible_main"] = pe_main_pre
    el_preframe["predictor_eligible_expanded"] = pe_exp_pre
    pairs_pre = build_pairs123(df, tgt, el_preframe, name)

    # ---- modeling_all_rows_stage123 (all rows; no drops) -----------------
    allrows = df.copy()
    allrows["company_name"] = name
    # corrected analytical scope replaces the prior label; raw provenance untouched
    allrows["statement_scope_status"] = el["statement_scope_canonical"].values
    allrows["statement_scope_display_fa"] = DISPLAY_LABEL_FA
    for c in ["fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
              "fd_ocf_high_leverage"]:
        allrows[c] = s122._csvnum(crit[c])
    allrows["FD_target_main"] = s122._csvnum(main)
    allrows["FD_target_article141_only"] = s122._csvnum(tgt["FD_target_article141_only"])
    allrows["FD_target_persistent_loss_robustness"] = s122._csvnum(
        tgt["FD_target_persistent_loss_robustness"])
    allrows["positive_target_reasons"] = s122.positive_target_reasons(crit, main).values
    allrows["target_missing_reason"] = s122.target_missing_reason(df, crit, main).values
    for c in ["eligible_listing", "eligible_statement_type", "eligible_annual_period",
              "eligible_source_quality", "eligible_accounting_quality",
              "eligible_company_main", "eligible_company_expanded", "eligible_target",
              "predictor_eligible_main", "predictor_eligible_expanded",
              "model_exclusion_reason_main", "model_exclusion_reason_expanded"]:
        allrows[c] = el[c].values
    allrows.to_csv(out / "modeling_all_rows_stage123.csv", index=False,
                   encoding="utf-8-sig")
    n_after = len(allrows); dup_after = int(allrows.duplicated(
        ["ticker", "fiscal_year"]).sum())

    pairs.to_csv(out / "modeling_one_year_ahead_stage123.csv", index=False,
                 encoding="utf-8-sig")

    # ---- eligibility audit ----------------------------------------------
    ea = pd.concat([df[["row_key", "ticker", "fiscal_year"]].reset_index(drop=True),
                    name.rename("company_name").reset_index(drop=True),
                    el.reset_index(drop=True)], axis=1)
    ea.to_csv(out / "eligibility_audit_stage123.csv", index=False, encoding="utf-8-sig")

    # ---- company review (finalized decision) -----------------------------
    review = _company_review(df, name)
    review.to_csv(out / "eligibility_company_review_stage123.csv", index=False,
                  encoding="utf-8-sig")

    # ---- listing-date review --------------------------------------------
    listing = _listing_review(df, name)
    listing.to_csv(out / "listing_date_review_stage123.csv", index=False,
                   encoding="utf-8-sig")

    # ---- leakage manifest -----------------------------------------------
    leak = leakage_manifest123()
    leak.to_csv(out / "leakage_manifest_stage123.csv", index=False, encoding="utf-8-sig")

    # ---- QC + change log + metadata + excel ------------------------------
    qc = _qc(df, tgt, el, pairs, pairs_pre, pe_main_pre, pe_exp_pre, corrected_mask,
             name_info, n_before, n_after, dup_before, dup_after, n_corrected)
    utils.save_json(qc, out / "stage123_qc_report.json")
    changelog = _change_log(qc, n_corrected)
    changelog.to_csv(out / "stage123_change_log.csv", index=False, encoding="utf-8-sig")
    _excel(out, df, tgt, el, ea, review, listing, pairs, leak, qc)
    meta = _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0)
    utils.save_json(meta, out / "metadata_and_hashes_stage123.json")
    print(f"[stage123] complete in {time.time()-t0:.1f}s -> {out}")
    return {"qc": qc, "pairs": pairs, "out": out}


def _company_review(df, name):
    recs = []
    allt = sorted(MAIN_EXCLUDE_TICKERS)
    for tk in allt:
        g = df[df["ticker"] == tk]
        nm = name[df["ticker"] == tk]
        recs.append({
            "ticker": tk,
            "company_name": nm.iloc[0] if len(nm) else "",
            "industry": " ; ".join(sorted(set(g["industry"]))) if len(g) else "",
            "n_rows": int(len(g)),
            "classification": "financial_investment" if tk in EXPANDED_EXCLUDE_TICKERS
            else "operating_holding",
            "in_main_sample": 0,
            "in_expanded_sample": 0 if tk in EXPANDED_EXCLUDE_TICKERS else 1,
            "decision_basis": "user_confirmed_manual_review"})
    return pd.DataFrame(recs)


def _listing_review(df, name):
    m = df["ocf_resolution_status"] == "pre_listing_missing_excluded"
    sub = df[m]
    rec = pd.DataFrame({
        "ticker": sub["ticker"].values,
        "company_name": name[m].values,
        "fiscal_year": sub["fiscal_year"].values,
        "pre_listing_marker": "pre_listing_missing_excluded",
        "eligible_listing": 0,
        "review_note": "excluded as pre-listing; explicit public-trading-start-date "
                       "column not available in data — confirm manually if a listing "
                       "master becomes available",
        "review_status": "pending_manual_confirmation"})
    return rec


def _dist_by_year(pairs, col, flagcol):
    pe = pairs[pairs[flagcol] == 1]
    out = {}
    for y in sorted(pe["target_year"].unique()):
        s = pe[pe["target_year"] == y][col]
        out[int(y)] = {"n": int(len(s)), "pos": int((s == "1").sum()),
                       "neg": int((s == "0").sum())}
    return out


def _qc(df, tgt, el, pairs, pairs_pre, pe_main_pre, pe_exp_pre, corrected_mask,
        name_info, n_before, n_after, dup_before, dup_after, n_corrected):
    main = tgt["FD_target_main"]
    # rows re-eligible (main) purely due to the statement correction
    became_main = int(((el["predictor_eligible_main"] == 1) & (pe_main_pre == 0)
                       & corrected_mask).sum())
    became_exp = int(((el["predictor_eligible_expanded"] == 1) & (pe_exp_pre == 0)
                      & corrected_mask).sum())
    pre_main = int((pairs_pre["pair_final_eligible_main"] == 1).sum())
    post_main = int((pairs["pair_final_eligible_main"] == 1).sum())
    pre_exp = int((pairs_pre["pair_final_eligible_expanded"] == 1).sum())
    post_exp = int((pairs["pair_final_eligible_expanded"] == 1).sum())

    def posneg(pframe, flag):
        pe = pframe[pframe[flag] == 1]["FD_target_main_t_plus_1"]
        return {"pos": int((pe == "1").sum()), "neg": int((pe == "0").sum()),
                "n": int(len(pe))}

    # 1401 & 1402 target-year pair positives, before vs after
    def yr_pos(pframe, flag, y):
        pe = pframe[(pframe[flag] == 1) & (pframe["target_year"] == y)]
        return int((pe["FD_target_main_t_plus_1"] == "1").sum())

    return {
        "stage": "stage123",
        "owner_confirmation": OWNER_CONFIRMATION_FA,
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "statement_scope_correction": {
            "affected_row_count": n_corrected,
            "previous_labels_corrected": ["possible_consolidated_statement",
                                          "statement_scope_unknown"],
            "corrected_to": CORRECTED_SCOPE},
        "rows_re_eligible_due_to_correction": {"main": became_main,
                                               "expanded": became_exp},
        "predictor_eligible_counts": {
            "main": int((el["predictor_eligible_main"] == 1).sum()),
            "expanded": int((el["predictor_eligible_expanded"] == 1).sum())},
        "pairs_total": int(len(pairs)),
        "pair_final_eligible_main_before_after": {"before": pre_main, "after": post_main,
                                                  "new_pairs": post_main - pre_main},
        "pair_final_eligible_expanded_before_after": {"before": pre_exp, "after": post_exp,
                                                      "new_pairs": post_exp - pre_exp},
        "pair_posneg_main_before": posneg(pairs_pre, "pair_final_eligible_main"),
        "pair_posneg_main_after": posneg(pairs, "pair_final_eligible_main"),
        "pair_posneg_expanded_after": posneg(pairs, "pair_final_eligible_expanded"),
        "annual_target_dist_main_after": _dist_by_year(
            pairs, "FD_target_main_t_plus_1", "pair_final_eligible_main"),
        "annual_target_dist_main_before": _dist_by_year(
            pairs_pre, "FD_target_main_t_plus_1", "pair_final_eligible_main"),
        "events_1401_1402_main": {
            "1401_before": yr_pos(pairs_pre, "pair_final_eligible_main", 1401),
            "1401_after": yr_pos(pairs, "pair_final_eligible_main", 1401),
            "1402_before": yr_pos(pairs_pre, "pair_final_eligible_main", 1402),
            "1402_after": yr_pos(pairs, "pair_final_eligible_main", 1402)},
        "target_unchanged_from_stage122": {
            "1": int((main == 1).sum()), "0": int((main == 0).sum()),
            "missing": int(main.isna().sum())},
        "company_name_fill": name_info,
        "assertions": {
            "rows_preserved": n_before == n_after,
            "no_duplicate_keys": dup_after == 0,
            "no_consolidated_in_canonical_scope": int(
                el["statement_scope_canonical"].isin(CONSOLIDATED_SCOPES).sum()) == 0,
            "non12month_excluded_main": int(((el["eligible_annual_period"] == 0) &
                                             (el["predictor_eligible_main"] == 1)).sum()),
            "pre_listing_excluded_main": int(((el["eligible_listing"] == 0) &
                                             (el["predictor_eligible_main"] == 1)).sum()),
            "financials_excluded_main": int((df["ticker"].isin(MAIN_EXCLUDE_TICKERS) &
                                            (el["predictor_eligible_main"] == 1)).sum()),
            "financials_excluded_expanded": int(
                (df["ticker"].isin(EXPANDED_EXCLUDE_TICKERS) &
                 (el["predictor_eligible_expanded"] == 1)).sum()),
            "pair_eligibility_independent_of_t_target": True,
        },
        "notes": [
            "Target is carried unchanged from Stage122 (no rebuild).",
            "pair_final_eligible = predictor_eligible_t AND valid_target_(t+1); it does "
            "NOT depend on the year-t target.",
            "Raw provenance (source_file/source_url/codal id/hash) is untouched; the "
            "prior scope label is preserved only in the immutable correction audit.",
        ],
    }


def _change_log(qc, n_corrected):
    sc = qc["statement_scope_correction"]
    rows = [
        {"change": "statement_scope_corrected",
         "detail": f"{n_corrected} rows: {sc['previous_labels_corrected']} -> "
                   f"{sc['corrected_to']} (basis: explicit_data_owner_confirmation)"},
        {"change": "rows_re_eligible_main",
         "detail": f"{qc['rows_re_eligible_due_to_correction']['main']} rows re-eligible "
                   f"(main) due to correction"},
        {"change": "rows_re_eligible_expanded",
         "detail": f"{qc['rows_re_eligible_due_to_correction']['expanded']} rows "
                   f"re-eligible (expanded)"},
        {"change": "pairs_main_before_after",
         "detail": f"{qc['pair_final_eligible_main_before_after']}"},
        {"change": "pairs_expanded_before_after",
         "detail": f"{qc['pair_final_eligible_expanded_before_after']}"},
        {"change": "company_decision_finalized",
         "detail": f"main excludes 9 tickers {sorted(MAIN_EXCLUDE_TICKERS)}; expanded "
                   f"excludes 4 financials {sorted(EXPANDED_EXCLUDE_TICKERS)}"},
        {"change": "pair_eligibility_formula_fixed",
         "detail": "pair_final_eligible no longer depends on year-t target"},
        {"change": "leakage_manifest_regrouped",
         "detail": "prohibited_leakage / near_target_predictor / allowed_t_predictor"},
        {"change": "target_unchanged",
         "detail": f"FD_target_main carried from Stage122: "
                   f"{qc['target_unchanged_from_stage122']}"},
    ]
    return pd.DataFrame(rows)


def _excel(out, df, tgt, el, ea, review, listing, pairs, leak, qc):
    corr = pd.read_csv(out / "statement_scope_correction_audit_stage123.csv",
                       dtype=str, keep_default_na=False)
    annual = pd.DataFrame([
        {"target_year": y, "stage": "main_after", **v}
        for y, v in qc["annual_target_dist_main_after"].items()] + [
        {"target_year": y, "stage": "main_before", **v}
        for y, v in qc["annual_target_dist_main_before"].items()])
    verify = pd.DataFrame([
        {"control": k, "value": str(v)} for k, v in qc["assertions"].items()])
    with pd.ExcelWriter(out / "stage123_workbook.xlsx") as xw:
        pd.DataFrame([{"owner_confirmation_fa": OWNER_CONFIRMATION_FA}]).to_excel(
            xw, sheet_name="owner_confirmation", index=False)
        corr.head(2000).to_excel(xw, sheet_name="statement_scope_correction", index=False)
        ea.head(2000).to_excel(xw, sheet_name="eligibility_row_audit", index=False)
        review.to_excel(xw, sheet_name="company_review", index=False)
        listing.to_excel(xw, sheet_name="listing_date_review", index=False)
        pairs.head(2000).to_excel(xw, sheet_name="one_year_ahead_pairs", index=False)
        annual.to_excel(xw, sheet_name="pair_annual_distribution", index=False)
        leak.to_excel(xw, sheet_name="leakage_manifest", index=False)
        verify.to_excel(xw, sheet_name="stage123_verification", index=False)


def _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0):
    inp = utils.raw_path(cfg, "all_rows_csv")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    out_hashes = {p.name: utils.sha256_file(p) for p in sorted(out.glob("*"))
                  if p.is_file() and p.name != "metadata_and_hashes_stage123.json"}
    return {
        "stage": "stage123",
        "owner_confirmation": OWNER_CONFIRMATION_FA,
        "input_file": {"name": inp.name, "sha256": utils.sha256_file(inp)},
        "stage122_inputs_referenced": "regenerated from Stage121 raw via stage122 logic",
        "output_files_sha256": out_hashes,
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": commit, "python": sys.version,
        "platform": platform.platform(), "library_versions": utils.env_report(),
        "seed": cfg.get("seed", 42),
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "runtime_seconds": round(time.time() - t0, 2),
    }
