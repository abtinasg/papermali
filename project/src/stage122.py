"""Stage122 — target rebuild + eligibility + one-year-ahead pairs + QC.

NO modeling here (no LR/RF/XGB/SHAP/SMOTE/tuning). This stage only freezes the
financial-distress target, builds eligibility flags, constructs t->t+1 pairs, writes
a leakage manifest, and runs QC. Original Stage121 files are read-only; every output
lands in a separate `stage122/` folder. No row or company is dropped from the panel.

Approved interpretation (user-confirmed 2026-06-20):
  Stage121 has NO standalone verified Article-141 source. `fd_article141_direct` is
  therefore created but is missing for every row. Because it has zero observed values,
  it does not block a definite-zero conclusion for FD_target_main (and likewise for
  FD_target_article141_only). Aggregation is a "modified three-valued OR with
  non-blocking unavailable direct Article-141 evidence" (not a standard Kleene-OR).
  FD_target_main is the composite operational financial distress target;
  FD_target_article141_only is a stricter Article-141 robustness definition.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

from . import utils

ROOT = Path(__file__).resolve().parents[1]
RAWDIRKEY = "raw_dir"


def stage_dir(cfg) -> Path:
    d = ROOT / "stage122"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace("", np.nan), errors="coerce")


def load_all_rows(cfg) -> pd.DataFrame:
    p = utils.raw_path(cfg, "all_rows_csv")
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)


# ==========================================================================
# Part 1 — target criteria (three-valued: 1.0 / 0.0 / NaN)
# ==========================================================================
def compute_criteria(df: pd.DataFrame) -> pd.DataFrame:
    al = _num(df["accumulated_loss"])
    rc = _num(df["registered_capital"])
    eq = _num(df["equity"])
    oc = _num(df["operating_cash_flow_period_adjusted"])
    ta = _num(df["total_assets"])
    tl = _num(df["total_liabilities"])

    out = pd.DataFrame(index=df.index)

    # 1) Article-141 direct: no verified source in Stage121 -> missing everywhere.
    out["fd_article141_direct"] = np.nan

    # 2) Accumulated loss / registered capital >= 0.5  (accumulated_loss is |loss|)
    cap_ok = rc.notna() & (rc > 0)
    ratio = al / rc.where(cap_ok)
    fd_acc = np.where(~(cap_ok & al.notna()), np.nan,
                      np.where(ratio >= 0.5, 1.0, 0.0))
    out["fd_accumulated_loss"] = fd_acc

    # 3) Negative equity
    out["fd_negative_equity"] = np.where(eq.isna(), np.nan,
                                         np.where(eq < 0, 1.0, 0.0))

    # 4) OCF<0 AND liabilities/assets>0.70  (three-valued)
    ta_ok = ta.notna() & (ta > 0)
    lev = tl / ta.where(ta_ok)
    lev_known = lev.notna()
    ocf_known = oc.notna()
    res = np.full(len(df), np.nan)
    # definite 0: OCF>=0 (known) OR leverage<=0.70 (known)
    res = np.where(ocf_known & (oc >= 0), 0.0, res)
    res = np.where(lev_known & (lev <= 0.70), 0.0, res)
    # definite 1: OCF<0 (known) AND leverage>0.70 (known)
    res = np.where(ocf_known & (oc < 0) & lev_known & (lev > 0.70), 1.0, res)
    out["fd_ocf_high_leverage"] = res

    # keep the raw leverage for audit/leakage transparency (not a feature)
    out["_ocf_leverage_value"] = lev
    out["_accumulated_loss_ratio"] = ratio
    return out


def _kleene_or(cols: list[pd.Series]) -> pd.Series:
    """Three-valued OR over evaluable criteria: any 1 ->1; else any NaN ->NaN; else 0.
    Columns that are entirely unobserved (all-NaN) are excluded from the aggregation
    per the approved interpretation, so they cannot block a definite-zero."""
    usable = [c for c in cols if c.notna().any()]
    if not usable:
        return pd.Series(np.nan, index=cols[0].index)
    arr = np.vstack([c.values.astype(float) for c in usable])
    any1 = np.nansum(arr == 1, axis=0) > 0
    anymiss = np.isnan(arr).any(axis=0)
    out = np.where(any1, 1.0, np.where(anymiss, np.nan, 0.0))
    return pd.Series(out, index=cols[0].index)


def _persistent_loss_flag(df: pd.DataFrame) -> pd.Series:
    """Two consecutive years of NET loss (three-valued)."""
    ni = _num(df["net_income_period_adjusted"])
    tmp = pd.DataFrame({"ticker": df["ticker"], "year": _num(df["fiscal_year"]),
                        "ni": ni})
    prev = tmp.set_index(["ticker", "year"])["ni"]
    out = np.full(len(df), np.nan)
    for i, (_, row) in enumerate(tmp.iterrows()):
        ni_t = row["ni"]
        key_prev = (row["ticker"], row["year"] - 1)
        ni_prev = prev.get(key_prev, np.nan)
        if np.isnan(ni_t) or np.isnan(ni_prev):
            out[i] = np.nan
        else:
            out[i] = 1.0 if (ni_t < 0 and ni_prev < 0) else 0.0
    return pd.Series(out, index=df.index)


def compute_targets(df: pd.DataFrame, crit: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    main_cols = [crit["fd_article141_direct"], crit["fd_accumulated_loss"],
                 crit["fd_negative_equity"], crit["fd_ocf_high_leverage"]]
    out["FD_target_main"] = _kleene_or(main_cols)

    # robustness 1: main OR two-consecutive-year net loss
    pl = _persistent_loss_flag(df)
    out["_persistent_loss_flag"] = pl
    out["FD_target_persistent_loss_robustness"] = _kleene_or([out["FD_target_main"], pl])

    # robustness 2: article141 direct OR accumulated_loss>=50%
    out["FD_target_article141_only"] = _kleene_or(
        [crit["fd_article141_direct"], crit["fd_accumulated_loss"]])
    return out


# ==========================================================================
# Audits
# ==========================================================================
def _lab(s: pd.Series) -> pd.Series:
    """Float 1/0/NaN -> string '1'/'0'/'missing' for human-readable audit."""
    return s.map(lambda v: "missing" if pd.isna(v) else str(int(v)))


def _csvnum(s: pd.Series) -> pd.Series:
    """Float 1/0/NaN -> '1'/'0'/'' (missing stays EMPTY, never zero)."""
    return s.map(lambda v: "" if pd.isna(v) else str(int(v)))


def build_targets(cfg) -> dict:
    df = load_all_rows(cfg)
    crit = compute_criteria(df)
    tgt = compute_targets(df, crit)
    out = stage_dir(cfg)

    # ---- target_row_audit -------------------------------------------------
    audit = df[["row_key", "ticker", "company_name", "fiscal_year"]].copy()
    for c in ["fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
              "fd_ocf_high_leverage"]:
        audit[c] = _lab(crit[c])
    audit["accumulated_loss_ratio"] = crit["_accumulated_loss_ratio"].round(4)
    audit["ocf_leverage_value"] = crit["_ocf_leverage_value"].round(4)
    audit["persistent_loss_flag"] = _lab(tgt["_persistent_loss_flag"])
    for c in ["FD_target_main", "FD_target_persistent_loss_robustness",
              "FD_target_article141_only"]:
        audit[c] = _lab(tgt[c])
    prior = df["distressed_target_reviewed"].replace("", "missing")
    audit["prior_distressed_target_reviewed"] = prior
    new_main = _lab(tgt["FD_target_main"])
    audit["target_changed_vs_prior"] = (new_main != prior).astype(int)
    audit["change_reason"] = _change_reason(crit, tgt, prior, new_main)
    audit.to_csv(out / "target_audit_stage122.csv", index=False, encoding="utf-8-sig")

    # ---- target_definition ------------------------------------------------
    definition = pd.DataFrame([
        {"criterion": "fd_article141_direct",
         "rule": "1 if direct Article-141 inclusion verified from a controlled source; "
                 "0 if non-inclusion verified; else missing. Stage121 has NO such source "
                 "-> missing for ALL rows (documented)."},
        {"criterion": "fd_accumulated_loss",
         "rule": "1 if accumulated_loss/registered_capital >= 0.5; 0 if < 0.5; "
                 "missing if registered_capital <=0/missing OR accumulated_loss missing."},
        {"criterion": "fd_negative_equity",
         "rule": "1 if equity<0; 0 if equity>=0; missing if equity missing."},
        {"criterion": "fd_ocf_high_leverage",
         "rule": "1 if OCF<0 AND liabilities/assets>0.70; definite 0 if OCF>=0 OR "
                 "leverage<=0.70; missing otherwise (3-valued)."},
        {"criterion": "FD_target_main",
         "label": "composite operational financial distress target",
         "rule": "Aggregation = modified three-valued OR with non-blocking unavailable "
                 "direct Article-141 evidence: 1 if any criterion is definitely 1; 0 if "
                 "all evaluable quantitative criteria are definitely 0; missing otherwise. "
                 "Because direct Article-141 evidence is unavailable for every row, its "
                 "missingness does NOT block a definite-zero based on the three "
                 "quantitative criteria (methodological decision). NOT an Article-141 "
                 "target."},
        {"criterion": "FD_target_persistent_loss_robustness",
         "label": "robustness target (composite + two-year persistent loss)",
         "rule": "Modified three-valued OR(FD_target_main, two-consecutive-year net "
                 "loss). Robustness target only; does not replace FD_target_main."},
        {"criterion": "FD_target_article141_only",
         "label": "stricter Article-141 robustness definition",
         "rule": "Modified three-valued OR(fd_article141_direct, fd_accumulated_loss). "
                 "With direct 141 absent, reduces to accumulated_loss>=50%. Stricter "
                 "robustness definition only."},
    ])
    definition.to_csv(out / "target_definition_stage122.csv", index=False,
                      encoding="utf-8-sig")

    # ---- annual distribution ---------------------------------------------
    dist = _annual_distribution(df, tgt)
    dist.to_csv(out / "target_distribution_stage122.csv", index=False,
                encoding="utf-8-sig")

    # ---- change log vs prior target --------------------------------------
    changed = audit[audit["target_changed_vs_prior"] == 1][
        ["row_key", "ticker", "fiscal_year", "prior_distressed_target_reviewed",
         "FD_target_main", "change_reason"]].copy()
    changed = changed.rename(columns={"FD_target_main": "new_FD_target_main"})
    changed.to_csv(out / "stage122_target_changelog.csv", index=False,
                   encoding="utf-8-sig")

    summary = {
        "n_rows": int(len(df)),
        "FD_target_main": _counts(tgt["FD_target_main"]),
        "FD_target_persistent_loss_robustness": _counts(
            tgt["FD_target_persistent_loss_robustness"]),
        "FD_target_article141_only": _counts(tgt["FD_target_article141_only"]),
        "criteria": {c: _counts(crit[c]) for c in
                     ["fd_article141_direct", "fd_accumulated_loss",
                      "fd_negative_equity", "fd_ocf_high_leverage"]},
        "prior_target": {k: int(v) for k, v in
                         df["distressed_target_reviewed"].replace("", "missing")
                         .value_counts().items()},
        "n_changed_vs_prior": int(audit["target_changed_vs_prior"].sum()),
    }
    utils.save_json(summary, out / "stage122_target_summary.json")
    return {"df": df, "crit": crit, "tgt": tgt, "audit": audit, "dist": dist,
            "summary": summary, "out": out}


def _counts(s: pd.Series) -> dict:
    return {"1": int((s == 1).sum()), "0": int((s == 0).sum()),
            "missing": int(s.isna().sum())}


def _annual_distribution(df, tgt) -> pd.DataFrame:
    yr = _num(df["fiscal_year"]).astype(int)
    recs = []
    for y in sorted(yr.unique()):
        m = yr == y
        for name in ["FD_target_main", "FD_target_persistent_loss_robustness",
                     "FD_target_article141_only"]:
            s = tgt.loc[m, name]
            recs.append({"fiscal_year": int(y), "target": name,
                         "n": int(m.sum()), "pos_1": int((s == 1).sum()),
                         "neg_0": int((s == 0).sum()),
                         "missing": int(s.isna().sum())})
    return pd.DataFrame(recs)


def _change_reason(crit, tgt, prior, new_main) -> pd.Series:
    reasons = []
    for i in range(len(prior)):
        if new_main.iloc[i] == prior.iloc[i]:
            reasons.append("")
            continue
        parts = []
        if crit["fd_accumulated_loss"].iloc[i] == 1:
            parts.append("accumulated_loss>=50%")
        if crit["fd_negative_equity"].iloc[i] == 1:
            parts.append("negative_equity")
        if crit["fd_ocf_high_leverage"].iloc[i] == 1:
            parts.append("ocf_neg_high_leverage")
        if new_main.iloc[i] == "missing":
            parts.append("became_missing_insufficient_data")
        if new_main.iloc[i] == "0" and not parts:
            parts.append("all_criteria_definite_zero")
        reasons.append(" | ".join(parts) if parts else "criteria_recomputed")
    return pd.Series(reasons, index=prior.index)


# ==========================================================================
# Enhanced per-row reasons (positive reasons + missing reasons)
# ==========================================================================
def positive_target_reasons(crit: pd.DataFrame, main: pd.Series) -> pd.Series:
    """For every definite-positive row, list ALL active criteria (not just changes)."""
    out = []
    for i in range(len(main)):
        if main.iloc[i] != 1:
            out.append("")
            continue
        parts = []
        if crit["fd_accumulated_loss"].iloc[i] == 1:
            parts.append("accumulated_loss")
        if crit["fd_negative_equity"].iloc[i] == 1:
            parts.append("negative_equity")
        if crit["fd_ocf_high_leverage"].iloc[i] == 1:
            parts.append("ocf_high_leverage")
        if crit["fd_article141_direct"].iloc[i] == 1:
            parts.append("article141_direct")
        out.append(" | ".join(parts))
    return pd.Series(out, index=main.index)


def target_missing_reason(df: pd.DataFrame, crit: pd.DataFrame,
                          main: pd.Series) -> pd.Series:
    """For every missing row, state exactly which inputs blocked the target."""
    al = _num(df["accumulated_loss"]); rc = _num(df["registered_capital"])
    eq = _num(df["equity"]); oc = _num(df["operating_cash_flow_period_adjusted"])
    ta = _num(df["total_assets"]); tl = _num(df["total_liabilities"])
    ta_ok = ta.notna() & (ta > 0)
    lev = tl / ta.where(ta_ok)
    out = []
    for i in range(len(main)):
        if not pd.isna(main.iloc[i]):
            out.append("")
            continue
        toks = []
        # accumulated-loss criterion unavailable
        if pd.isna(crit["fd_accumulated_loss"].iloc[i]):
            if pd.isna(rc.iloc[i]) or rc.iloc[i] <= 0:
                if pd.isna(al.iloc[i]):
                    toks.append("missing_accumulated_loss_and_capital")
                else:
                    toks.append("missing_or_invalid_registered_capital")
            elif pd.isna(al.iloc[i]):
                toks.append("missing_accumulated_loss")
        # negative-equity criterion unavailable
        if pd.isna(crit["fd_negative_equity"].iloc[i]):
            toks.append("missing_equity")
        # ocf/leverage criterion unavailable
        if pd.isna(crit["fd_ocf_high_leverage"].iloc[i]):
            ocf_known = not pd.isna(oc.iloc[i]); lev_known = not pd.isna(lev.iloc[i])
            if lev_known and lev.iloc[i] > 0.70 and not ocf_known:
                toks.append("missing_ocf_with_leverage_above_threshold")
            elif ocf_known and oc.iloc[i] < 0 and not lev_known:
                toks.append("missing_leverage_with_ocf_negative")
            else:
                toks.append("missing_ocf_and_leverage")
        out.append(" & ".join(toks) if toks else "undetermined")
    return pd.Series(out, index=main.index)


def fill_company_name(df: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Fill empty company_name from the in-data canonical (ticker->name) master."""
    name = df["company_name"].copy()
    empty = name.str.strip() == ""
    master = (df[~empty].drop_duplicates("ticker").set_index("ticker")["company_name"])
    filled, unfilled = 0, []
    for idx in df.index[empty]:
        tk = df.at[idx, "ticker"]
        if tk in master.index and str(master[tk]).strip():
            name.at[idx] = master[tk]; filled += 1
        else:
            unfilled.append(tk)
    info = {"n_empty": int(empty.sum()), "n_filled": filled,
            "n_unfilled": int(empty.sum()) - filled,
            "unfilled_tickers": sorted(set(unfilled))}
    return name, info


# ==========================================================================
# Part 2 — eligibility, one-year-ahead pairs, leakage manifest, QC, metadata
# ==========================================================================
import json, subprocess, time, platform, sys  # noqa: E402

FINANCIAL_KEYWORDS = ["سرمایه‌گذاری", "سرمایه گذاری", "سرمايه‌گذاري", "بانک",
                      "بیمه", "لیزینگ", "تأمین سرمایه", "تامین سرمایه",
                      "صندوق", "واسطه‌گری مالی", "واسطه گری مالی"]
HOLDING_KEYWORD = "هلدینگ"

VALID_STATEMENT = {"separate_or_parent_only_indicated", "separate",
                   "parent_only_user_confirmed", "separate_company_user_confirmed",
                   "parent_company_section_user_confirmed",
                   "separate_parent_only_user_confirmed",
                   "user_confirmed_correct_source"}
UNRESOLVED_STATEMENT = {"possible_consolidated_statement", "statement_scope_unknown"}


def _is_financial(industry: str) -> bool:
    s = industry or ""
    return any(k in s for k in FINANCIAL_KEYWORDS)


def compute_eligibility(df: pd.DataFrame, main: pd.Series) -> pd.DataFrame:
    """All 9 eligibility columns. No row is dropped — only flagged out of the sample."""
    n = len(df)
    A,L,E = _num(df["total_assets"]), _num(df["total_liabilities"]), _num(df["equity"])
    el = pd.DataFrame(index=df.index)

    # 1) listing — use the controlled pre-listing marker (not mere registration date)
    el["eligible_listing"] = np.where(
        df["ocf_resolution_status"] == "pre_listing_missing_excluded", 0, 1)

    # 2) nonfinancial — PROVISIONAL auto-flag; manual review table is authoritative
    el["eligible_nonfinancial"] = np.where(
        df["industry"].map(_is_financial), 0, 1)
    el["nonfinancial_status"] = np.where(
        df["industry"].map(_is_financial), "suspected_financial_pending_review",
        np.where(df["industry"].str.contains(HOLDING_KEYWORD, na=False),
                 "operating_holding_pending_review", "nonfinancial_clear"))

    # 3) statement type — only separate/parent valid; consolidated/unknown -> 0
    def stmt(v):
        if v in VALID_STATEMENT:
            return 1
        return 0
    el["eligible_statement_type"] = df["statement_scope_status"].map(stmt)
    el["statement_status"] = np.where(
        df["statement_scope_status"].isin(VALID_STATEMENT), "valid_separate_or_parent",
        np.where(df["statement_scope_status"] == "possible_consolidated_statement",
                 "possible_consolidated", "statement_scope_unknown"))

    # 4) annual 12-month period — non-12-month/transitional -> 0 (kept for robustness)
    el["eligible_annual_period"] = np.where(df["non_12_month_period_flag"] == "1", 0, 1)

    # 5) source quality — source_file traceability + unit present
    no_src = (df["source_file"].str.strip() == "")
    no_unit = (df["unit"].str.strip() == "")
    el["eligible_source_quality"] = np.where(no_src | no_unit, 0, 1)

    # 6) accounting quality — serious unresolved equation residual -> 0
    res = (A - (L + E)).abs()
    rel = res / A.abs().clip(lower=1)
    serious = rel.notna() & (rel > 0.005)
    el["eligible_accounting_quality"] = np.where(serious, 0, 1)
    el["accounting_status"] = np.where(
        serious, "serious_equation_residual",
        np.where(rel.isna(), "unverifiable_missing_components",
                 np.where(rel > 1e-9, "minor_rounding", "ok")))
    el["accounting_rel_residual"] = rel.round(8)

    # 7) target eligibility — row's own FD_target_main is definite (0/1)
    el["eligible_target"] = np.where(main.isna(), 0, 1)

    # final
    flags = ["eligible_listing", "eligible_nonfinancial", "eligible_statement_type",
             "eligible_annual_period", "eligible_source_quality",
             "eligible_accounting_quality", "eligible_target"]
    el["final_model_eligible"] = (el[flags] == 1).all(axis=1).astype(int)

    reason_map = {
        "eligible_listing": "pre_listing",
        "eligible_nonfinancial": "financial_industry",
        "eligible_statement_type": "consolidated_or_unresolved_statement",
        "eligible_annual_period": "non_12_month_period",
        "eligible_source_quality": "source_not_traceable",
        "eligible_accounting_quality": "accounting_quality_issue",
        "eligible_target": "unresolved_target",
    }
    reasons = []
    for i in df.index:
        rs = [reason_map[f] for f in flags if el.at[i, f] == 0]
        reasons.append(" | ".join(rs))
    el["model_exclusion_reason"] = reasons
    return el


def company_review_table(df: pd.DataFrame) -> pd.DataFrame:
    """Independent review of suspected financial/investment + operating-holding firms.
    Classification is NOT finalized automatically (manual confirmation before freeze)."""
    recs = []
    for tk, g in df.groupby("ticker"):
        inds = sorted(set(g["industry"]))
        ind = inds[0] if inds else ""
        fin = any(_is_financial(x) for x in inds)
        hold = any(HOLDING_KEYWORD in (x or "") for x in inds)
        if not (fin or hold):
            continue
        recs.append({
            "ticker": tk,
            "company_name": g["company_name"].replace("", np.nan).dropna().iloc[0]
            if g["company_name"].replace("", np.nan).notna().any() else "",
            "industry": " ; ".join(inds), "n_rows": int(len(g)),
            "auto_classification": "suspected_financial" if fin else "operating_holding",
            "provisional_eligible_nonfinancial": 0 if fin else 1,
            "review_status": "pending_manual_review",
            "final_decision": ""})
    return pd.DataFrame(recs).sort_values(
        ["auto_classification", "ticker"]).reset_index(drop=True)


def build_pairs(df: pd.DataFrame, tgt: pd.DataFrame, el: pd.DataFrame,
                name: pd.Series) -> pd.DataFrame:
    """Exact t -> t+1 pairs. Features come from t; target from t+1; no year gaps;
    no t+1 variable enters predictors (only ids + t+1 targets + flags here)."""
    work = pd.DataFrame({
        "ticker": df["ticker"], "company_name": name,
        "year": _num(df["fiscal_year"]).astype(int), "row_key": df["row_key"],
        "FD_main": tgt["FD_target_main"].values,
        "FD_art141": tgt["FD_target_article141_only"].values,
        "FD_persist": tgt["FD_target_persistent_loss_robustness"].values,
        "final_elig": el["final_model_eligible"].values,
        "excl_reason": el["model_exclusion_reason"].values,
    })
    by = {(r.ticker, r.year): r for r in work.itertuples(index=False)}
    rows = []
    for r in work.itertuples(index=False):
        nxt = by.get((r.ticker, r.year + 1))
        if nxt is None:
            continue  # no exact next-year row -> no pair (no gap filling)
        target_valid = 0 if pd.isna(nxt.FD_main) else 1
        pair_elig = int(r.final_elig == 1 and target_valid == 1)
        pr = []
        if r.final_elig != 1:
            pr.append("predictor_not_eligible:" + (r.excl_reason or "unknown"))
        if target_valid != 1:
            pr.append("target_t+1_missing")
        rows.append({
            "ticker": r.ticker, "company_name": r.company_name,
            "fiscal_year_t": r.year, "target_year": r.year + 1,
            "FD_target_main_t_plus_1": _scalar(nxt.FD_main),
            "FD_target_article141_only_t_plus_1": _scalar(nxt.FD_art141),
            "FD_target_persistent_loss_robustness_t_plus_1": _scalar(nxt.FD_persist),
            "final_model_eligible_t": int(r.final_elig),
            "target_valid_t_plus_1": target_valid,
            "pair_final_eligible": pair_elig,
            "pair_exclusion_reason": " | ".join(pr),
            "predictor_row_key_t": r.row_key, "target_row_key_t_plus_1": nxt.row_key,
        })
    return pd.DataFrame(rows)


def _scalar(v):
    return "" if pd.isna(v) else str(int(v))


def leakage_manifest(df: pd.DataFrame) -> pd.DataFrame:
    """Flag columns that directly define the target / are aliases / use t+1 info.
    Removal of predictors happens later in feature design — here we only record."""
    recs = [
        ("article_141", "direct_target_definition", "Article-141 inclusion (absent in data)"),
        ("accumulated_loss", "target_component", "used in fd_accumulated_loss"),
        ("registered_capital", "target_component", "denominator of accumulated_loss ratio"),
        ("accumulated_loss_to_capital_ratio", "target_alias", "alias of fd_accumulated_loss"),
        ("equity", "target_component", "used in fd_negative_equity"),
        ("equity_negative_dummy", "target_alias", "alias of fd_negative_equity"),
        ("operating_cash_flow_period_adjusted", "target_component", "used in fd_ocf_high_leverage"),
        ("total_liabilities", "target_component", "leverage numerator in fd_ocf_high_leverage"),
        ("total_assets", "target_component", "leverage denominator in fd_ocf_high_leverage"),
        ("leverage_ratio", "target_component", "leverage used in fd_ocf_high_leverage"),
        ("net_income_period_adjusted", "target_component", "used in persistent-loss robustness target"),
        ("loss_dummy", "target_alias", "net-loss indicator, near target definition"),
        ("distressed_target_reviewed", "previous_target", "Stage121 target label"),
        ("target_status_reviewed", "target_source", "target provenance"),
        ("distressed_flag_source_reviewed", "target_source", "target provenance"),
        ("fd_article141_direct", "target_criterion", "FD criterion"),
        ("fd_accumulated_loss", "target_criterion", "FD criterion"),
        ("fd_negative_equity", "target_criterion", "FD criterion"),
        ("fd_ocf_high_leverage", "target_criterion", "FD criterion"),
        ("FD_target_main", "target_column", "main target"),
        ("FD_target_article141_only", "target_column", "robustness target"),
        ("FD_target_persistent_loss_robustness", "target_column", "robustness target"),
        ("FD_target_main_t_plus_1", "next_year_derived", "t+1 target — never a predictor"),
        ("FD_target_article141_only_t_plus_1", "next_year_derived", "t+1 target"),
        ("FD_target_persistent_loss_robustness_t_plus_1", "next_year_derived", "t+1 target"),
    ]
    out = pd.DataFrame(recs, columns=["column", "leakage_type", "note"])
    out["present_in_stage121"] = out["column"].isin(df.columns).astype(int)
    return out


# ==========================================================================
# Distributions after each filter (requirement H)
# ==========================================================================
def distribution_tables(df, tgt, el, pairs):
    yr = _num(df["fiscal_year"]).astype(int)
    main = tgt["FD_target_main"]
    elig = el["final_model_eligible"] == 1
    recs = []
    def add(stage, mask):
        s = main[mask]
        recs.append({"stage": stage, "scope": "all_years", "n": int(mask.sum()),
                     "pos_1": int((s == 1).sum()), "neg_0": int((s == 0).sum()),
                     "missing": int(s.isna().sum())})
    add("1_before_eligibility", pd.Series(True, index=df.index))
    add("2_after_eligibility", elig)
    for y in sorted(yr.unique()):
        s = main[(yr == y)]
        recs.append({"stage": "before_eligibility_by_year", "scope": int(y),
                     "n": int((yr == y).sum()), "pos_1": int((s == 1).sum()),
                     "neg_0": int((s == 0).sum()), "missing": int(s.isna().sum())})
    for y in sorted(yr.unique()):
        m = (yr == y) & elig
        s = main[m]
        recs.append({"stage": "after_eligibility_by_year", "scope": int(y),
                     "n": int(m.sum()), "pos_1": int((s == 1).sum()),
                     "neg_0": int((s == 0).sum()), "missing": int(s.isna().sum())})
    before = pd.DataFrame(recs)

    # pair-level distribution (requirement H.3, H.4) over pair_final_eligible
    pe = pairs[pairs["pair_final_eligible"] == 1]
    prec = []
    tv = pe["FD_target_main_t_plus_1"]
    prec.append({"stage": "3_after_pair_all", "target_year": "all", "n": int(len(pe)),
                 "pos_1": int((tv == "1").sum()), "neg_0": int((tv == "0").sum())})
    for y in sorted(pe["target_year"].unique()):
        sub = pe[pe["target_year"] == y]["FD_target_main_t_plus_1"]
        prec.append({"stage": "after_pair_by_target_year", "target_year": int(y),
                     "n": int(len(sub)), "pos_1": int((sub == "1").sum()),
                     "neg_0": int((sub == "0").sum())})
    pair_dist = pd.DataFrame(prec)
    return before, pair_dist


def exclusion_breakdown(el, pairs):
    rows = []
    # row-level: count each reason token among non-eligible rows
    from collections import Counter
    rc = Counter()
    for r in el.loc[el["final_model_eligible"] == 0, "model_exclusion_reason"]:
        for tok in str(r).split(" | "):
            if tok:
                rc[tok] += 1
    for k, v in sorted(rc.items(), key=lambda x: -x[1]):
        rows.append({"level": "row", "reason": k, "count": v})
    pc = Counter()
    for r in pairs.loc[pairs["pair_final_eligible"] == 0, "pair_exclusion_reason"]:
        for tok in str(r).split(" | "):
            tok = tok.split(":")[0] if tok.startswith("predictor_not_eligible") else tok
            if tok:
                pc[tok] += 1
    for k, v in sorted(pc.items(), key=lambda x: -x[1]):
        rows.append({"level": "pair", "reason": k, "count": v})
    return pd.DataFrame(rows)


# ==========================================================================
# Full Stage122 build (Part 1 + Part 2)
# ==========================================================================
def build_full(cfg) -> dict:
    t0 = time.time()
    out = stage_dir(cfg)
    df = load_all_rows(cfg)
    n_before = len(df)
    dup_before = int(df.duplicated(["ticker", "fiscal_year"]).sum())

    crit = compute_criteria(df)
    tgt = compute_targets(df, crit)
    main = tgt["FD_target_main"]
    name, name_info = fill_company_name(df)

    # ---- enhanced target audit (self-verifiable: raw inputs included) -----
    aud = pd.DataFrame(index=df.index)
    aud["row_key"] = df["row_key"]; aud["ticker"] = df["ticker"]
    aud["company_name"] = name; aud["fiscal_year"] = df["fiscal_year"]
    # raw inputs
    aud["registered_capital"] = df["registered_capital"]
    aud["accumulated_loss"] = df["accumulated_loss"]
    aud["equity"] = df["equity"]
    aud["operating_cash_flow"] = df["operating_cash_flow_period_adjusted"]
    aud["total_liabilities"] = df["total_liabilities"]
    aud["total_assets"] = df["total_assets"]
    aud["net_income"] = df["net_income_period_adjusted"]
    aud["leverage_ratio_used"] = crit["_ocf_leverage_value"].round(6)
    aud["accumulated_loss_ratio_used"] = crit["_accumulated_loss_ratio"].round(6)
    # criteria
    for c in ["fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
              "fd_ocf_high_leverage"]:
        aud[c] = _lab(crit[c])
    aud["persistent_loss_flag"] = _lab(tgt["_persistent_loss_flag"])
    # targets (human label + csv numeric with missing=empty)
    aud["FD_target_main"] = _lab(main)
    aud["FD_target_article141_only"] = _lab(tgt["FD_target_article141_only"])
    aud["FD_target_persistent_loss_robustness"] = _lab(
        tgt["FD_target_persistent_loss_robustness"])
    aud["positive_target_reasons"] = positive_target_reasons(crit, main)
    aud["target_missing_reason"] = target_missing_reason(df, crit, main)
    # source/status fields for verification without another file
    for c in ["distressed_target_reviewed", "target_status_reviewed",
              "distressed_flag_source_reviewed", "ocf_resolution_status",
              "statement_scope_status", "non_12_month_period_flag", "audit_status_clean",
              "data_quality_flag", "source_file", "industry"]:
        aud[c] = df[c]
    prior = df["distressed_target_reviewed"].replace("", "missing")
    aud["prior_distressed_target_reviewed"] = prior
    aud["target_changed_vs_prior"] = (aud["FD_target_main"] != prior).astype(int)
    aud["change_reason"] = _change_reason(crit, tgt, prior, aud["FD_target_main"])
    aud.to_csv(out / "target_audit_stage122.csv", index=False, encoding="utf-8-sig")

    # ---- eligibility -----------------------------------------------------
    el = compute_eligibility(df, main)
    elig_audit = pd.concat([df[["row_key", "ticker", "fiscal_year"]].reset_index(drop=True),
                            name.rename("company_name").reset_index(drop=True),
                            el.reset_index(drop=True)], axis=1)
    elig_audit.to_csv(out / "eligibility_audit_stage122.csv", index=False,
                      encoding="utf-8-sig")
    review = company_review_table(df)
    review.to_csv(out / "eligibility_company_review.csv", index=False,
                  encoding="utf-8-sig")

    # ---- modeling_all_rows_stage122 (all rows + new cols, none dropped) ---
    allrows = df.copy()
    allrows["company_name"] = name
    for c in ["fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
              "fd_ocf_high_leverage"]:
        allrows[c] = _csvnum(crit[c])
    allrows["FD_target_main"] = _csvnum(main)
    allrows["FD_target_article141_only"] = _csvnum(tgt["FD_target_article141_only"])
    allrows["FD_target_persistent_loss_robustness"] = _csvnum(
        tgt["FD_target_persistent_loss_robustness"])
    allrows["positive_target_reasons"] = aud["positive_target_reasons"].values
    allrows["target_missing_reason"] = aud["target_missing_reason"].values
    for c in el.columns:
        allrows[c] = el[c].values
    allrows.to_csv(out / "modeling_all_rows_stage122.csv", index=False,
                   encoding="utf-8-sig")
    n_after = len(allrows)
    dup_after = int(allrows.duplicated(["ticker", "fiscal_year"]).sum())

    # ---- pairs t -> t+1 --------------------------------------------------
    pairs = build_pairs(df, tgt, el, name)
    pairs.to_csv(out / "modeling_one_year_ahead_stage122.csv", index=False,
                 encoding="utf-8-sig")

    # ---- leakage manifest, distributions, exclusion breakdown -------------
    leak = leakage_manifest(df)
    leak.to_csv(out / "leakage_manifest_stage122.csv", index=False, encoding="utf-8-sig")
    before_dist, pair_dist = distribution_tables(df, tgt, el, pairs)
    excl = exclusion_breakdown(el, pairs)
    # rewrite annual target distribution (Part1) too
    _annual_distribution(df, tgt).to_csv(out / "target_distribution_stage122.csv",
                                         index=False, encoding="utf-8-sig")

    # ---- QC + verification ----------------------------------------------
    qc = _qc_report(df, crit, tgt, el, pairs, name_info, n_before, n_after,
                    dup_before, dup_after)
    utils.save_json(qc, out / "stage122_qc_report.json")
    verify = _verification_table(qc)

    # ---- change log ------------------------------------------------------
    changelog = _change_log(df, crit, tgt, el, pairs, qc)
    changelog.to_csv(out / "stage122_change_log.csv", index=False, encoding="utf-8-sig")

    # ---- target definition (re-emit with updated naming) -----------------
    _write_definition(out)

    # ---- Excel workbook (9 sheets) ---------------------------------------
    _write_excel(out, df, tgt, aud, el, review, pairs, leak, verify, before_dist,
                 pair_dist, excl)

    # ---- metadata + hashes ----------------------------------------------
    meta = _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0)
    utils.save_json(meta, out / "metadata_and_hashes_stage122.json")
    print(f"[stage122] full build complete in {time.time()-t0:.1f}s -> {out}")
    return {"qc": qc, "meta": meta, "out": out, "pairs": pairs,
            "before_dist": before_dist, "pair_dist": pair_dist, "excl": excl}


def _write_definition(out):
    definition = pd.DataFrame([
        {"criterion": "fd_article141_direct", "label": "direct Article-141 evidence",
         "rule": "1 if direct Article-141 inclusion verified from a controlled source; 0 "
                 "if non-inclusion verified; else missing. Stage121 has NO such source -> "
                 "missing for ALL rows."},
        {"criterion": "fd_accumulated_loss", "label": "accumulated loss >= 50% capital",
         "rule": "1 if accumulated_loss/registered_capital >= 0.5; 0 if < 0.5; missing if "
                 "registered_capital <=0/missing OR accumulated_loss missing."},
        {"criterion": "fd_negative_equity", "label": "negative equity",
         "rule": "1 if equity<0; 0 if equity>=0; missing if equity missing."},
        {"criterion": "fd_ocf_high_leverage", "label": "negative OCF & high leverage",
         "rule": "1 if OCF<0 AND liabilities/assets>0.70; definite 0 if OCF>=0 OR "
                 "leverage<=0.70; missing otherwise (three-valued)."},
        {"criterion": "FD_target_main",
         "label": "composite operational financial distress target",
         "rule": "modified three-valued OR with non-blocking unavailable direct "
                 "Article-141 evidence. 1 if any criterion definitely 1; 0 if all "
                 "evaluable quantitative criteria definitely 0; missing otherwise. NOT an "
                 "Article-141 target."},
        {"criterion": "FD_target_persistent_loss_robustness",
         "label": "robustness target (composite + 2-year persistent loss)",
         "rule": "modified three-valued OR(FD_target_main, two-consecutive-year net "
                 "loss). Robustness only."},
        {"criterion": "FD_target_article141_only",
         "label": "stricter Article-141 robustness definition",
         "rule": "modified three-valued OR(fd_article141_direct, fd_accumulated_loss); "
                 "with 141 absent reduces to accumulated_loss>=50%. Robustness only."},
    ])
    definition.to_csv(out / "target_definition_stage122.csv", index=False,
                      encoding="utf-8-sig")
    return definition


# ==========================================================================
# QC, verification, change log, Excel, metadata
# ==========================================================================
def _qc_report(df, crit, tgt, el, pairs, name_info, n_before, n_after,
               dup_before, dup_after):
    main = tgt["FD_target_main"]
    yr = _num(df["fiscal_year"]).astype(int)
    per_year = {}
    for y in sorted(yr.unique()):
        s = main[yr == y]
        per_year[int(y)] = {"0": int((s == 0).sum()), "1": int((s == 1).sum()),
                            "missing": int(s.isna().sum())}
    prior = df["distressed_target_reviewed"].replace("", "missing")
    changed = (_lab(main) != prior)

    # assertions (mandatory controls)
    pre_listing = set(df.loc[df["ocf_resolution_status"] ==
                             "pre_listing_missing_excluded", "row_key"])
    pairs_prelisting_in_final = int(
        pairs[(pairs["predictor_row_key_t"].isin(pre_listing)) &
              (pairs["pair_final_eligible"] == 1)].shape[0])
    fin_in_main = int(((el["eligible_nonfinancial"] == 0) &
                       (el["final_model_eligible"] == 1)).sum())
    cons_in_main = int(((el["eligible_statement_type"] == 0) &
                        (el["final_model_eligible"] == 1)).sum())
    non12_in_main = int(((el["eligible_annual_period"] == 0) &
                         (el["final_model_eligible"] == 1)).sum())
    # no missing -> zero: emitted FD_target_main empty count must equal missing count
    emitted_empty = int((_csvnum(main) == "").sum())

    from collections import Counter
    rc = Counter()
    for r in el.loc[el["final_model_eligible"] == 0, "model_exclusion_reason"]:
        for tok in str(r).split(" | "):
            if tok:
                rc[tok] += 1

    return {
        "stage": "stage122",
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "n_companies_before": int(df["ticker"].nunique()),
        "n_companies_after": int(df["ticker"].nunique()),
        "target_counts": {"0": int((main == 0).sum()), "1": int((main == 1).sum()),
                          "missing": int(main.isna().sum())},
        "target_counts_by_year": per_year,
        "n_target_changed_vs_prior": int(changed.sum()),
        "criteria_counts": {c: {"1": int((crit[c] == 1).sum()),
                                "0": int((crit[c] == 0).sum()),
                                "missing": int(crit[c].isna().sum())}
                            for c in ["fd_article141_direct", "fd_accumulated_loss",
                                      "fd_negative_equity", "fd_ocf_high_leverage"]},
        "robustness_target_counts": {
            "FD_target_article141_only": {
                "1": int((tgt["FD_target_article141_only"] == 1).sum()),
                "0": int((tgt["FD_target_article141_only"] == 0).sum()),
                "missing": int(tgt["FD_target_article141_only"].isna().sum())},
            "FD_target_persistent_loss_robustness": {
                "1": int((tgt["FD_target_persistent_loss_robustness"] == 1).sum()),
                "0": int((tgt["FD_target_persistent_loss_robustness"] == 0).sum()),
                "missing": int(tgt["FD_target_persistent_loss_robustness"].isna().sum())},
        },
        "eligibility_counts": {c: int((el[c] == 1).sum()) for c in
                               ["eligible_listing", "eligible_nonfinancial",
                                "eligible_statement_type", "eligible_annual_period",
                                "eligible_source_quality", "eligible_accounting_quality",
                                "eligible_target", "final_model_eligible"]},
        "exclusion_reason_counts_row": dict(rc),
        "pairs_total": int(len(pairs)),
        "pairs_final_eligible": int((pairs["pair_final_eligible"] == 1).sum()),
        "company_name_fill": name_info,
        "assertions": {
            "no_missing_target_converted_to_zero":
                emitted_empty == int(main.isna().sum()),
            "pre_listing_rows_in_final_pairs": pairs_prelisting_in_final,
            "financial_rows_in_main_sample": fin_in_main,
            "consolidated_rows_in_main_sample": cons_in_main,
            "non12month_rows_in_main_sample": non12_in_main,
            "no_duplicate_keys": dup_after == 0,
            "rows_preserved": n_before == n_after,
        },
        "notes": [
            "fd_article141_direct has no verified source in Stage121 -> missing for all "
            "1331 rows; excluded from FD_target_main aggregation (approved).",
            "eligible_nonfinancial is PROVISIONAL; eligibility_company_review.csv must be "
            "manually confirmed before final freeze.",
            "eligible_listing uses the controlled pre_listing_missing_excluded marker as "
            "a public-trading-start proxy (no explicit trading-start-date column exists).",
        ],
    }


def _verification_table(qc) -> pd.DataFrame:
    a = qc["assertions"]
    rows = [
        ("rows preserved (before==after)", f"{qc['rows_before']}=={qc['rows_after']}",
         "PASS" if a["rows_preserved"] else "FAIL"),
        ("no duplicate ticker+year", str(qc["duplicate_keys_after"]),
         "PASS" if a["no_duplicate_keys"] else "FAIL"),
        ("no missing target -> zero", "ok" if a["no_missing_target_converted_to_zero"]
         else "violation", "PASS" if a["no_missing_target_converted_to_zero"] else "FAIL"),
        ("pre-listing rows in final pairs", str(a["pre_listing_rows_in_final_pairs"]),
         "PASS" if a["pre_listing_rows_in_final_pairs"] == 0 else "FAIL"),
        ("financial rows in main sample", str(a["financial_rows_in_main_sample"]),
         "PASS" if a["financial_rows_in_main_sample"] == 0 else "FAIL"),
        ("consolidated rows in main sample", str(a["consolidated_rows_in_main_sample"]),
         "PASS" if a["consolidated_rows_in_main_sample"] == 0 else "FAIL"),
        ("non-12-month rows in main sample", str(a["non12month_rows_in_main_sample"]),
         "PASS" if a["non12month_rows_in_main_sample"] == 0 else "FAIL"),
        ("target changed vs prior", str(qc["n_target_changed_vs_prior"]), "INFO"),
        ("final_model_eligible rows", str(qc["eligibility_counts"]["final_model_eligible"]),
         "INFO"),
        ("pairs_final_eligible", str(qc["pairs_final_eligible"]), "INFO"),
        ("company_name unfilled", str(qc["company_name_fill"]["n_unfilled"]), "INFO"),
    ]
    return pd.DataFrame(rows, columns=["control", "value", "status"])


def _change_log(df, crit, tgt, el, pairs, qc) -> pd.DataFrame:
    rows = [
        {"change": "new_target_columns_added",
         "detail": "FD_target_main, FD_target_article141_only, "
                   "FD_target_persistent_loss_robustness + 4 criteria"},
        {"change": "target_changed_vs_stage121",
         "detail": f"{qc['n_target_changed_vs_prior']} rows differ from "
                   f"distressed_target_reviewed"},
        {"change": "eligibility_columns_added",
         "detail": "9 eligibility columns + model_exclusion_reason"},
        {"change": "rows_excluded_from_model_not_db",
         "detail": f"{qc['rows_after']-qc['eligibility_counts']['final_model_eligible']} "
                   f"rows flagged out of model sample; 0 rows removed from database"},
        {"change": "one_year_ahead_pairs_built",
         "detail": f"{qc['pairs_total']} pairs; {qc['pairs_final_eligible']} final-eligible"},
        {"change": "company_name_filled",
         "detail": f"{qc['company_name_fill']['n_filled']} filled, "
                   f"{qc['company_name_fill']['n_unfilled']} unfilled "
                   f"({qc['company_name_fill']['unfilled_tickers']})"},
    ]
    for tok, c in qc["exclusion_reason_counts_row"].items():
        rows.append({"change": f"exclusion_reason::{tok}", "detail": f"{c} rows"})
    return pd.DataFrame(rows)


def _write_excel(out, df, tgt, aud, el, review, pairs, leak, verify, before_dist,
                 pair_dist, excl):
    defs = _write_definition(out)
    annual = _annual_distribution(df, tgt)
    elig_audit = pd.concat([df[["row_key", "ticker", "fiscal_year"]].reset_index(drop=True),
                            el.reset_index(drop=True)], axis=1)
    with pd.ExcelWriter(out / "stage122_workbook.xlsx") as xw:
        defs.to_excel(xw, sheet_name="target_definition_stage122", index=False)
        aud.head(2000).to_excel(xw, sheet_name="target_row_audit_stage122", index=False)
        annual.to_excel(xw, sheet_name="target_annual_distribution", index=False)
        review.to_excel(xw, sheet_name="eligibility_company_review", index=False)
        elig_audit.head(2000).to_excel(xw, sheet_name="eligibility_row_audit", index=False)
        pairs.head(2000).to_excel(xw, sheet_name="one_year_ahead_pairs", index=False)
        pair_dist.to_excel(xw, sheet_name="pair_annual_distribution", index=False)
        leak.to_excel(xw, sheet_name="leakage_manifest", index=False)
        verify.to_excel(xw, sheet_name="stage122_verification", index=False)


def _metadata(cfg, out, n_before, n_after, dup_before, dup_after, t0):
    inp = utils.raw_path(cfg, "all_rows_csv")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    out_hashes = {}
    for p in sorted(out.glob("*")):
        if p.is_file() and p.name != "metadata_and_hashes_stage122.json":
            out_hashes[p.name] = utils.sha256_file(p)
    return {
        "stage": "stage122",
        "input_file": {"name": inp.name, "sha256": utils.sha256_file(inp)},
        "output_files_sha256": out_hashes,
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": commit,
        "python": sys.version, "platform": platform.platform(),
        "library_versions": utils.env_report(),
        "seed": cfg.get("seed", 42),
        "rows_before": n_before, "rows_after": n_after,
        "duplicate_keys_before": dup_before, "duplicate_keys_after": dup_after,
        "runtime_seconds": round(time.time() - t0, 2),
    }
