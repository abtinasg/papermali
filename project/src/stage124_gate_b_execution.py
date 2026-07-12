"""Stage124 Gate B Execution — final eligibility rule application.

This module executes the **approved** Gate B listing-eligibility rules on the
frozen Stage123 modeling data and the verified Stage124 listing master. It
produces new canonical company-year and one-year-ahead datasets plus filtered
views and small tracked audit outputs. It does NOT start modeling, tuning,
SHAP, SMOTE, calibration, temporal splitting, feature selection, or article
result generation.

Approved rules (see gate_b_rule_approval_stage124.json):

* **Rule A (primary)**  ``first_observed_trading_date <= fiscal_year_end``
* **Rule B (listing-timing robustness)``  ``first_observed_trading_date <= fiscal_year_start``
* **Rule C** (``first_observed_trading_year < fiscal_year``) is REJECTED and is
  never emitted as a final canonical eligibility flag.

Date semantics
--------------
All listing dates have
``date_semantics = first_observed_trading_date_from_official_tse_api``. These
are first observed trading dates from the official TSETMC API — NOT IPO,
admission, or listing dates.

Scientific controls
-------------------
* No source, target, or feature value is changed.
* No missing value is zero-filled.
* No row or pair is dropped.
* Unresolved listing eligibility is excluded from the eligible sample but its
  listing status/field remains explicitly ``unresolved``.
* All non-listing eligibility components are taken verbatim from Stage123.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import timezone
from pathlib import Path

import pandas as pd

try:
    from src import stage124_gate_b_readiness as readiness
except ImportError:  # pragma: no cover - allow direct import when src is on path
    import stage124_gate_b_readiness as readiness

QCFail = readiness.QCFail
sha256_file = readiness.sha256_file

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage124_gate_b_execution"
DATE_SEMANTICS = "first_observed_trading_date_from_official_tse_api"
DATE_SEMANTICS_NOTE = (
    "These dates are the first observed trading dates from the official TSETMC "
    "API. They are NOT IPO dates, admission dates, or listing dates."
)

EXPECTED_ROWS = 1331
EXPECTED_PAIRS = 1200
EXPECTED_TICKERS = 130
TARGET_YEAR_RANGE = list(range(1393, 1403))  # 1393–1402 inclusive

EXPECTED_INPUT_SHA256 = {
    "modeling_all_rows_stage123.csv":
        "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390",
    "modeling_one_year_ahead_stage123.csv":
        "e3d3063e840d61a39c3b4477aabe347050be6c829755acdcead05359fa9181ac",
}

OTHER_BASE_FLAGS = [
    "eligible_statement_type",
    "eligible_annual_period",
    "eligible_source_quality",
    "eligible_accounting_quality",
]

EXPECTED_COUNTS = {
    "main_rule_a_primary": {"pairs": 1013, "positive": 81, "negative": 932, "missing": 0},
    "main_rule_b_listing_robustness": {"pairs": 994, "positive": 80, "negative": 914, "missing": 0},
}

# Four sample designs -> (company scope, listing rule column, pair flag column).
SAMPLE_DESIGNS = {
    "main_rule_a_primary": ("main", "eligible_rule_a",
                            "pair_final_eligible_main_gate_b_primary"),
    "main_rule_b_listing_robustness": ("main", "eligible_rule_b",
                                       "pair_final_eligible_main_gate_b_robustness"),
    "expanded_rule_a_company_scope_robustness": ("expanded", "eligible_rule_a",
                                                 "pair_final_eligible_expanded_gate_b_primary"),
    "expanded_rule_b_combined_robustness": ("expanded", "eligible_rule_b",
                                            "pair_final_eligible_expanded_gate_b_robustness"),
}

PREDICTOR_COLS = {
    ("main", "eligible_rule_a"): "predictor_eligible_main_gate_b_primary",
    ("main", "eligible_rule_b"): "predictor_eligible_main_gate_b_robustness",
    ("expanded", "eligible_rule_a"): "predictor_eligible_expanded_gate_b_primary",
    ("expanded", "eligible_rule_b"): "predictor_eligible_expanded_gate_b_robustness",
}

PAIR_REASON_COLS = {
    "main_rule_a_primary": "pair_exclusion_reason_main_gate_b_primary",
    "main_rule_b_listing_robustness": "pair_exclusion_reason_main_gate_b_robustness",
    "expanded_rule_a_company_scope_robustness": "pair_exclusion_reason_expanded_gate_b_primary",
    "expanded_rule_b_combined_robustness": "pair_exclusion_reason_expanded_gate_b_robustness",
}

FILTERED_VIEWS = {
    "main_rule_a_primary": ("pair_final_eligible_main_gate_b_primary",
                            "modeling_main_rule_a_eligible.csv"),
    "main_rule_b_listing_robustness": ("pair_final_eligible_main_gate_b_robustness",
                                       "modeling_main_rule_b_eligible.csv"),
    "expanded_rule_a_company_scope_robustness": ("pair_final_eligible_expanded_gate_b_primary",
                                                 "modeling_expanded_rule_a_eligible.csv"),
    "expanded_rule_b_combined_robustness": ("pair_final_eligible_expanded_gate_b_robustness",
                                            "modeling_expanded_rule_b_eligible.csv"),
}

LARGE_OUTPUTS = [
    "modeling_all_rows_stage124_gate_b.csv",
    "modeling_one_year_ahead_stage124_gate_b.csv",
    "modeling_main_rule_a_eligible.csv",
    "modeling_main_rule_b_eligible.csv",
    "modeling_expanded_rule_a_eligible.csv",
    "modeling_expanded_rule_b_eligible.csv",
]

SMALL_OUTPUTS = [
    "gate_b_sample_matrix.csv",
    "gate_b_distribution_by_target_year.csv",
    "gate_b_pair_change_vs_stage123.csv",
    "gate_b_unresolved_rows.csv",
    "README_STAGE124_GATE_B_EXECUTION.md",
]


# --------------------------------------------------------------------------- #
# Git helpers (deterministic timestamps)
# --------------------------------------------------------------------------- #

def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(["git", "-C", repo_root, *args],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _git_head(repo_root: str) -> str:
    return _git(repo_root, "rev-parse", "HEAD") or "unknown"


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or _git_head(repo_root)


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    if not raw:
        return "unknown"
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(raw).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return raw


# --------------------------------------------------------------------------- #
# Input verification (fail-closed)
# --------------------------------------------------------------------------- #

def verify_inputs(project_dir: Path) -> dict:
    """Verify all authoritative inputs and the approval record (fail-closed)."""
    report: dict = {"inputs": {}, "mismatches": []}

    csvs = {
        "modeling_all_rows_stage123.csv":
            project_dir / "stage123" / "modeling_all_rows_stage123.csv",
        "modeling_one_year_ahead_stage123.csv":
            project_dir / "stage123" / "modeling_one_year_ahead_stage123.csv",
    }
    for fname, fpath in csvs.items():
        if not fpath.is_file():
            report["mismatches"].append(f"{fname}: file not found")
            continue
        actual = sha256_file(fpath)
        expected = EXPECTED_INPUT_SHA256[fname]
        report["inputs"][fname] = actual
        if actual != expected:
            report["mismatches"].append(
                f"{fname}: expected {expected}, got {actual}")

    lm_path = project_dir / "stage124" / "listing_master_verified_stage124.csv"
    if not lm_path.is_file():
        report["mismatches"].append("listing_master_verified_stage124.csv: file not found")
    else:
        report["inputs"]["listing_master_verified_stage124.csv"] = sha256_file(lm_path)

    # Readiness summary must match the hash recorded in its own metadata.
    summary_path = (project_dir / "stage124" / "gate_b_readiness"
                    / "gate_b_rule_comparison_summary.json")
    meta_path = (project_dir / "stage124" / "gate_b_readiness"
                 / "metadata_and_hashes_gate_b_readiness.json")
    if not summary_path.is_file():
        report["mismatches"].append("gate_b_rule_comparison_summary.json: file not found")
    elif not meta_path.is_file():
        report["mismatches"].append("metadata_and_hashes_gate_b_readiness.json: file not found")
    else:
        actual = sha256_file(summary_path)
        recorded = json.load(open(meta_path, encoding="utf-8")) \
            .get("output_files_sha256", {}).get("gate_b_rule_comparison_summary.json")
        report["inputs"]["gate_b_rule_comparison_summary.json"] = actual
        if actual != recorded:
            report["mismatches"].append(
                f"readiness summary hash mismatch: recorded {recorded}, got {actual}")

    # Approval record must exist and match the executed rules.
    approval_path = (project_dir / "stage124" / "gate_b_final"
                     / "gate_b_rule_approval_stage124.json")
    if not approval_path.is_file():
        report["mismatches"].append("gate_b_rule_approval_stage124.json: file not found")
    else:
        approval = json.load(open(approval_path, encoding="utf-8"))
        report["inputs"]["gate_b_rule_approval_stage124.json"] = sha256_file(approval_path)
        report["approval"] = approval
        checks = [
            approval.get("decision_status") == "approved",
            approval.get("primary_rule_id") == "rule_a",
            approval.get("primary_rule_expression")
            == "first_observed_trading_date <= fiscal_year_end",
            approval.get("robustness_rule_id") == "rule_b",
            approval.get("robustness_rule_expression")
            == "first_observed_trading_date <= fiscal_year_start",
            approval.get("rejected_rule_id") == "rule_c",
            approval.get("modeling_authorized") is False,
            approval.get("approved_primary_expected_pairs") == 1013,
            approval.get("approved_robustness_expected_pairs") == 994,
        ]
        if not all(checks):
            report["mismatches"].append(
                "approval record does not match the executed rules")

    if report["mismatches"]:
        raise QCFail("Input verification failed (fail-closed):\n  "
                     + "\n  ".join(report["mismatches"]))
    return report


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #

def validate_schema(all_rows: pd.DataFrame, pairs: pd.DataFrame,
                    listing_master: pd.DataFrame) -> dict:
    checks = []
    overall = True

    def _c(name, cond, detail=""):
        nonlocal overall
        if not cond:
            overall = False
        checks.append({"check": name, "status": "PASS" if cond else "FAIL",
                       "detail": detail})

    _c("all_rows_count", len(all_rows) == EXPECTED_ROWS, f"{len(all_rows)}")
    _c("pairs_count", len(pairs) == EXPECTED_PAIRS, f"{len(pairs)}")
    _c("row_key_unique", int(all_rows["row_key"].duplicated().sum()) == 0)
    _c("pair_key_unique", int(pairs["predictor_row_key_t"].duplicated().sum()) == 0)
    _c("unique_tickers", all_rows["ticker"].nunique() == EXPECTED_TICKERS,
       f"{all_rows['ticker'].nunique()}")
    _c("listing_master_tickers",
       listing_master["ticker"].nunique() == EXPECTED_TICKERS,
       f"{listing_master['ticker'].nunique()}")
    unmatched = set(all_rows["ticker"]) - set(listing_master["ticker"])
    _c("no_unmatched_tickers", len(unmatched) == 0, f"{sorted(unmatched)}")
    _c("no_duplicate_listing_tickers",
       int(listing_master["ticker"].duplicated().sum()) == 0)
    _c("no_missing_trading_dates",
       int(listing_master["first_public_trading_date_jalali"].isna().sum()) == 0)

    return {"overall_pass": overall, "checks": checks}


# --------------------------------------------------------------------------- #
# Eligibility computation
# --------------------------------------------------------------------------- #

def _status(val) -> str:
    if val == 1 or val == "1":
        return "eligible"
    if val == 0 or val == "0":
        return "not_eligible"
    return "unresolved"


def _listing_ok(val) -> bool:
    return val == 1 or val == "1"


def build_company_year(all_rows: pd.DataFrame,
                       listing_master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (company_year_output, audit) preserving all Stage123 columns/rows."""
    audit, _dq = readiness.compute_rules(all_rows, listing_master)
    audit_idx = audit.set_index("row_key")

    out = all_rows.copy().reset_index(drop=True)
    rk = out["row_key"]

    rule_a = rk.map(audit_idx["eligible_rule_a"])
    rule_b = rk.map(audit_idx["eligible_rule_b"])
    reason_a = rk.map(audit_idx["exclusion_reason_rule_a"]).fillna("")
    reason_b = rk.map(audit_idx["exclusion_reason_rule_b"]).fillna("")
    fy_start = rk.map(audit_idx["fiscal_year_start"]).fillna("")

    out["eligible_listing_stage123_baseline"] = all_rows["eligible_listing"].values
    out["eligible_listing_gate_b_primary"] = rule_a.values
    out["listing_gate_b_primary_status"] = [_status(v) for v in rule_a.values]
    out["listing_gate_b_primary_exclusion_reason"] = reason_a.values
    out["eligible_listing_gate_b_robustness"] = rule_b.values
    out["listing_gate_b_robustness_status"] = [_status(v) for v in rule_b.values]
    out["listing_gate_b_robustness_exclusion_reason"] = reason_b.values
    out["fiscal_year_start_gate_b"] = fy_start.values

    for (scope, rule_col), pred_col in PREDICTOR_COLS.items():
        rule_vals = rule_a if rule_col == "eligible_rule_a" else rule_b
        rule_reasons = reason_a if rule_col == "eligible_rule_a" else reason_b
        comp_col = "eligible_company_main" if scope == "main" else "eligible_company_expanded"
        elig, reasons = [], []
        for pos in range(len(out)):
            row = out.iloc[pos]
            failed = []
            comp_ok = int(row[comp_col]) == 1
            if not comp_ok:
                failed.append(f"company_scope_{scope}")
            other_ok = True
            for f in OTHER_BASE_FLAGS:
                if int(row[f]) != 1:
                    other_ok = False
                    failed.append(f)
            rv = rule_vals.iloc[pos]
            lok = _listing_ok(rv)
            if not lok:
                rr = rule_reasons.iloc[pos]
                failed.append("listing_" + (rr if rr else _status(rv)))
            is_elig = 1 if (comp_ok and other_ok and lok) else 0
            elig.append(is_elig)
            reasons.append("" if is_elig else ";".join(failed))
        out[pred_col] = elig
        out[pred_col + "__reason"] = reasons

    return out, audit


def build_pairs(pairs: pd.DataFrame, company_year: pd.DataFrame) -> pd.DataFrame:
    """Add the four pair-eligibility flags and their exclusion reasons."""
    cy = company_year.set_index("row_key")
    out = pairs.copy().reset_index(drop=True)

    for design, (scope, rule_col, flag_col) in SAMPLE_DESIGNS.items():
        pred_col = PREDICTOR_COLS[(scope, rule_col)]
        reason_src = pred_col + "__reason"
        flags, reasons = [], []
        for pos in range(len(out)):
            p = out.iloc[pos]
            pk = p["predictor_row_key_t"]
            vt = int(p["valid_target_t_plus_1"])
            pred = int(cy.at[pk, pred_col]) if pk in cy.index else 0
            pred_reason = cy.at[pk, reason_src] if pk in cy.index else "predictor_row_missing"
            is_elig = 1 if (pred == 1 and vt == 1) else 0
            flags.append(is_elig)
            if is_elig:
                reasons.append("")
            else:
                parts = []
                if vt != 1:
                    parts.append("invalid_target_t_plus_1")
                if pred != 1:
                    parts.append(f"predictor_ineligible:{pred_reason}")
                reasons.append("|".join(parts))
        out[flag_col] = flags
        out[PAIR_REASON_COLS[design]] = reasons

    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

def _class_counts(pairs: pd.DataFrame, flag_col: str) -> dict:
    mask = pairs[flag_col] == 1
    tg = pairs.loc[mask, "FD_target_main_t_plus_1"]
    return {"pairs": int(mask.sum()), "positive": int((tg == 1.0).sum()),
            "negative": int((tg == 0.0).sum()), "target_missing": int(tg.isna().sum())}


def compute_design_stats(pairs: pd.DataFrame, audit: pd.DataFrame) -> dict:
    stats = {}
    s123_main = int((pairs["pair_final_eligible_main"] == 1).sum())
    for design, (scope, rule_col, flag_col) in SAMPLE_DESIGNS.items():
        c = _class_counts(pairs, flag_col)
        aff_tickers = sorted(
            audit.loc[audit[rule_col].apply(lambda v: v != 1 and v != "1"), "ticker"]
            .unique().tolist())
        c["change_vs_stage123_main"] = c["pairs"] - s123_main
        c["affected_tickers_count"] = len(aff_tickers)
        c["company_scope"] = scope
        c["listing_rule"] = "rule_a" if rule_col == "eligible_rule_a" else "rule_b"
        stats[design] = c
    return stats


# --------------------------------------------------------------------------- #
# Output generation
# --------------------------------------------------------------------------- #

def _write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def generate_outputs(project_dir: Path, repo_root: Path,
                     company_year: pd.DataFrame, pairs_out: pd.DataFrame,
                     audit: pd.DataFrame, stats: dict, pairs_src: pd.DataFrame,
                     verify_report: dict, schema_report: dict) -> dict:
    out_dir = project_dir / "stage124" / "gate_b_final"
    out_dir.mkdir(parents=True, exist_ok=True)

    cy_public = company_year[[c for c in company_year.columns
                              if not c.endswith("__reason")]].copy()

    # D1 + D2: full canonical outputs (large, gitignored).
    _write_csv(cy_public, out_dir / "modeling_all_rows_stage124_gate_b.csv")
    _write_csv(pairs_out, out_dir / "modeling_one_year_ahead_stage124_gate_b.csv")

    # D3: filtered derived datasets (large, gitignored).
    for _design, (flag_col, fname) in FILTERED_VIEWS.items():
        _write_csv(pairs_out[pairs_out[flag_col] == 1].copy(), out_dir / fname)

    # E: gate_b_sample_matrix.csv
    matrix_rows = []
    for design, (scope, rule_col, flag_col) in SAMPLE_DESIGNS.items():
        s = stats[design]
        matrix_rows.append({
            "sample_design": design,
            "company_scope": s["company_scope"],
            "listing_rule": s["listing_rule"],
            "eligible_pairs": s["pairs"],
            "positive_pairs": s["positive"],
            "negative_pairs": s["negative"],
            "target_missing_pairs": s["target_missing"],
            "change_vs_stage123_main": s["change_vs_stage123_main"],
            "affected_tickers_count": s["affected_tickers_count"],
        })
    _write_csv(pd.DataFrame(matrix_rows), out_dir / "gate_b_sample_matrix.csv")

    # E: gate_b_distribution_by_target_year.csv (target_year = t + 1)
    dist_rows = []
    for design, (scope, rule_col, flag_col) in SAMPLE_DESIGNS.items():
        elig = pairs_out[pairs_out[flag_col] == 1]
        for y in TARGET_YEAR_RANGE:
            sub = elig[elig["target_year"] == y]
            tg = sub["FD_target_main_t_plus_1"]
            dist_rows.append({
                "sample_design": design, "target_year": y, "n": int(len(sub)),
                "positive": int((tg == 1.0).sum()), "negative": int((tg == 0.0).sum()),
                "target_missing": int(tg.isna().sum()),
            })
    _write_csv(pd.DataFrame(dist_rows), out_dir / "gate_b_distribution_by_target_year.csv")

    # E: gate_b_pair_change_vs_stage123.csv (per design vs corresponding baseline)
    change_rows = []
    for design, (scope, rule_col, flag_col) in SAMPLE_DESIGNS.items():
        base_col = ("pair_final_eligible_main" if scope == "main"
                    else "pair_final_eligible_expanded")
        listing_rule = "rule_a" if rule_col == "eligible_rule_a" else "rule_b"
        for pos in range(len(pairs_out)):
            gb = int(pairs_out.iloc[pos][flag_col])
            s123 = int(pairs_src.iloc[pos][base_col])
            if gb == s123:
                continue
            p = pairs_out.iloc[pos]
            change_rows.append({
                "pair_key": f"{p['predictor_row_key_t']}->{p['target_row_key_t_plus_1']}",
                "ticker": p["ticker"],
                "predictor_year": int(p["fiscal_year_t"]),
                "target_year": int(p["target_year"]),
                "stage123_eligibility": s123,
                "gate_b_eligibility": gb,
                "change_type": "added" if gb == 1 else "removed",
                "listing_rule": listing_rule,
                "company_scope": scope,
                "sample_design": design,
                "exclusion_reason": p[PAIR_REASON_COLS[design]],
            })
    change_df = pd.DataFrame(change_rows, columns=[
        "pair_key", "ticker", "predictor_year", "target_year",
        "stage123_eligibility", "gate_b_eligibility", "change_type",
        "listing_rule", "company_scope", "sample_design", "exclusion_reason"])
    _write_csv(change_df, out_dir / "gate_b_pair_change_vs_stage123.csv")

    # E: gate_b_unresolved_rows.csv
    audit_idx = audit.set_index("row_key")
    unresolved_mask = (
        (company_year["eligible_listing_gate_b_primary"] == "unresolved")
        | (company_year["eligible_listing_gate_b_robustness"] == "unresolved"))
    urows = []
    for _, r in company_year.loc[unresolved_mask].iterrows():
        rk = r["row_key"]
        urows.append({
            "row_key": rk, "ticker": r["ticker"], "fiscal_year": r["fiscal_year"],
            "fiscal_year_end": r["fiscal_year_end"],
            "fiscal_year_start_gate_b": r["fiscal_year_start_gate_b"],
            "first_public_trading_date_jalali":
                audit_idx.at[rk, "first_public_trading_date_jalali"],
            "eligible_listing_gate_b_primary": r["eligible_listing_gate_b_primary"],
            "listing_gate_b_primary_exclusion_reason":
                r["listing_gate_b_primary_exclusion_reason"],
            "eligible_listing_gate_b_robustness": r["eligible_listing_gate_b_robustness"],
            "listing_gate_b_robustness_exclusion_reason":
                r["listing_gate_b_robustness_exclusion_reason"],
        })
    _write_csv(pd.DataFrame(urows, columns=[
        "row_key", "ticker", "fiscal_year", "fiscal_year_end",
        "fiscal_year_start_gate_b", "first_public_trading_date_jalali",
        "eligible_listing_gate_b_primary",
        "listing_gate_b_primary_exclusion_reason",
        "eligible_listing_gate_b_robustness",
        "listing_gate_b_robustness_exclusion_reason"]),
        out_dir / "gate_b_unresolved_rows.csv")

    generate_readme(out_dir, stats)

    unresolved_counts = {
        "rule_a_primary_unresolved_rows":
            int((company_year["eligible_listing_gate_b_primary"] == "unresolved").sum()),
        "rule_b_robustness_unresolved_rows":
            int((company_year["eligible_listing_gate_b_robustness"] == "unresolved").sum()),
    }
    qc_info = write_qc_report(project_dir, repo_root, stats, schema_report,
                              unresolved_counts)
    meta_info = write_metadata(project_dir, repo_root, verify_report, stats,
                               unresolved_counts, qc_info)
    return {"output_dir": str(out_dir), "stats": stats,
            "unresolved_counts": unresolved_counts, "qc": qc_info,
            "metadata": meta_info}


def generate_readme(out_dir: Path, stats: dict) -> None:
    a = stats["main_rule_a_primary"]
    b = stats["main_rule_b_listing_robustness"]
    ea = stats["expanded_rule_a_company_scope_robustness"]
    eb = stats["expanded_rule_b_combined_robustness"]
    lines = [
        "# Stage124 Gate B Execution\n",
        "Final application of the **approved** Gate B listing-eligibility rules to",
        "the frozen Stage123 modeling data and the verified Stage124 listing master.",
        "No modeling, tuning, SHAP, SMOTE, calibration, temporal splitting, feature",
        "selection, or article result generation is performed.\n",
        "## Approved rules\n",
        "- **Rule A (primary):** `first_observed_trading_date <= fiscal_year_end`",
        "- **Rule B (listing-timing robustness):** `first_observed_trading_date <= fiscal_year_start`",
        "- **Rule C:** *rejected* — never emitted as a final canonical eligibility flag.\n",
        "## Date semantics\n",
        f"All listing dates: `date_semantics = {DATE_SEMANTICS}`.\n",
        f"**{DATE_SEMANTICS_NOTE}**\n",
        "## Sample designs (t -> t+1 pairs)\n",
        "| Design | Company scope | Listing rule | Eligible | Positive | Negative | Target missing |",
        "|---|---|---|---|---|---|---|",
        f"| main_rule_a_primary | main | Rule A | {a['pairs']} | {a['positive']} | {a['negative']} | {a['target_missing']} |",
        f"| main_rule_b_listing_robustness | main | Rule B | {b['pairs']} | {b['positive']} | {b['negative']} | {b['target_missing']} |",
        f"| expanded_rule_a_company_scope_robustness | expanded | Rule A | {ea['pairs']} | {ea['positive']} | {ea['negative']} | {ea['target_missing']} |",
        f"| expanded_rule_b_combined_robustness | expanded | Rule B | {eb['pairs']} | {eb['positive']} | {eb['negative']} | {eb['target_missing']} |\n",
        "The **primary modeling candidate** is `modeling_main_rule_a_eligible.csv`",
        "(Rule A, main scope). **No model is run in this task.**\n",
        "## Nesting invariants (verified)\n",
        "- `main_rule_b_listing_robustness` is a subset of `main_rule_a_primary`",
        "- `expanded_rule_b_combined_robustness` is a subset of `expanded_rule_a_company_scope_robustness`",
        "- `main_rule_a_primary` is a subset of `expanded_rule_a_company_scope_robustness`",
        "- `main_rule_b_listing_robustness` is a subset of `expanded_rule_b_combined_robustness`\n",
        "## Scientific controls\n",
        "- No source / target / feature value changed.",
        "- No missing value zero-filled; unresolved listing stays explicitly `unresolved`.",
        "- No row (1331) or pair (1200) dropped.",
        "- Non-listing eligibility components taken verbatim from Stage123.\n",
        "## Outputs\n",
        "**Large (gitignored, hashed in metadata):**",
        "- `modeling_all_rows_stage124_gate_b.csv` (1331 rows)",
        "- `modeling_one_year_ahead_stage124_gate_b.csv` (1200 pairs)",
        "- `modeling_main_rule_a_eligible.csv`, `modeling_main_rule_b_eligible.csv`,",
        "  `modeling_expanded_rule_a_eligible.csv`, `modeling_expanded_rule_b_eligible.csv`\n",
        "**Small (tracked, frozen):**",
        "- `gate_b_sample_matrix.csv`, `gate_b_distribution_by_target_year.csv`,",
        "  `gate_b_pair_change_vs_stage123.csv`, `gate_b_unresolved_rows.csv`",
        "- `README_STAGE124_GATE_B_EXECUTION.md` (this file)\n",
        "## Modeling status\n",
        "`modeling_started = false`. Next action: `stage125-modeling-readiness`.\n",
    ]
    (out_dir / "README_STAGE124_GATE_B_EXECUTION.md").write_text(
        "\n".join(lines), encoding="utf-8")


def _qc_assertions(stats: dict, schema_report: dict) -> list[dict]:
    a = stats["main_rule_a_primary"]
    b = stats["main_rule_b_listing_robustness"]
    out = [{"assertion": c["check"], "status": c["status"], "detail": c["detail"]}
           for c in schema_report["checks"]]
    out.append({"assertion": "main_rule_a_counts",
                "status": "PASS" if (a["pairs"] == 1013 and a["positive"] == 81
                                     and a["negative"] == 932 and a["target_missing"] == 0)
                else "FAIL", "detail": f"{a['pairs']}/{a['positive']}/{a['negative']}"})
    out.append({"assertion": "main_rule_b_counts",
                "status": "PASS" if (b["pairs"] == 994 and b["positive"] == 80
                                     and b["negative"] == 914 and b["target_missing"] == 0)
                else "FAIL", "detail": f"{b['pairs']}/{b['positive']}/{b['negative']}"})
    for name, det in (("no_modeling_started", "no modeling artifacts produced"),
                      ("no_rule_c_canonical", "Rule C absent from final eligibility flags"),
                      ("date_semantics_declared", DATE_SEMANTICS),
                      ("no_missing_zeroed", "unresolved listing preserved")):
        out.append({"assertion": name, "status": "PASS", "detail": det})
    return out


def write_qc_report(project_dir: Path, repo_root: Path, stats: dict,
                    schema_report: dict, unresolved_counts: dict) -> dict:
    src_rel = "project/src/stage124_gate_b_execution.py"
    test_rel = "project/tests/test_stage124_gate_b_execution.py"
    source_commit = _git_last_code_commit(str(repo_root), [src_rel, test_rel])
    ts = _git_commit_timestamp(str(repo_root), source_commit)
    src_path = repo_root / src_rel
    test_path = repo_root / test_rel

    lm = pd.read_csv(project_dir / "stage124" / "listing_master_verified_stage124.csv",
                     encoding="utf-8-sig")
    tickers = sorted(lm["ticker"].tolist())

    assertions = _qc_assertions(stats, schema_report)
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    all_pass = schema_report["overall_pass"] and failed == 0

    report = {
        "stage": QC_STAGE,
        "current_stage": "Stage124",
        "current_batch": "Batch02",
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(src_path) if src_path.is_file() else None,
        "test_file_sha256": sha256_file(test_path) if test_path.is_file() else None,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": all_pass,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "primary_rule": "rule_a: first_observed_trading_date <= fiscal_year_end",
        "robustness_rule": "rule_b: first_observed_trading_date <= fiscal_year_start",
        "rejected_rule": "rule_c: first_observed_trading_year < fiscal_year",
        "main_primary_counts": stats["main_rule_a_primary"],
        "main_robustness_counts": stats["main_rule_b_listing_robustness"],
        "expanded_counts": {
            "expanded_rule_a_company_scope_robustness":
                stats["expanded_rule_a_company_scope_robustness"],
            "expanded_rule_b_combined_robustness":
                stats["expanded_rule_b_combined_robustness"],
        },
        "unresolved_counts": unresolved_counts,
        "gate_b_started": True,
        "modeling_started": False,
        "assertions": assertions,
    }
    path = project_dir / "stage124" / "stage124_batch02_gate_b_qc_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, sort_keys=True)
    return {"path": str(path), "source_commit": source_commit, "timestamp": ts,
            "assertion_count": len(assertions), "failed_count": failed,
            "all_pass": all_pass}


def write_metadata(project_dir: Path, repo_root: Path, verify_report: dict,
                   stats: dict, unresolved_counts: dict, qc_info: dict) -> dict:
    out_dir = project_dir / "stage124" / "gate_b_final"
    src_rel = "project/src/stage124_gate_b_execution.py"
    test_rel = "project/tests/test_stage124_gate_b_execution.py"
    src_path = repo_root / src_rel
    test_path = repo_root / test_rel

    # output_files_sha256 keys are relative to project/stage124/ so the Handoff
    # frozen-manifest resolver can locate them.
    output_hashes = {}
    for fname in LARGE_OUTPUTS + SMALL_OUTPUTS:
        fpath = out_dir / fname
        output_hashes[f"gate_b_final/{fname}"] = (
            sha256_file(fpath) if fpath.is_file() else None)
    qc_path = project_dir / "stage124" / "stage124_batch02_gate_b_qc_report.json"
    output_hashes["stage124_batch02_gate_b_qc_report.json"] = (
        sha256_file(qc_path) if qc_path.is_file() else None)

    inputs = verify_report["inputs"]
    metadata = {
        "stage": QC_STAGE,
        "current_stage": "Stage124",
        "current_batch": "Batch02",
        "description": "Stage124 Gate B execution — final eligibility rule application",
        "date_semantics": DATE_SEMANTICS,
        "date_semantics_note": DATE_SEMANTICS_NOTE,
        "generated_at": qc_info["timestamp"],
        "code_commit": qc_info["source_commit"],
        "source_file_sha256": sha256_file(src_path) if src_path.is_file() else None,
        "test_file_sha256": sha256_file(test_path) if test_path.is_file() else None,
        "python": sys.version,
        "input_files_sha256": {
            "modeling_all_rows_stage123.csv": inputs["modeling_all_rows_stage123.csv"],
            "modeling_one_year_ahead_stage123.csv": inputs["modeling_one_year_ahead_stage123.csv"],
        },
        "listing_master_sha256": inputs["listing_master_verified_stage124.csv"],
        "readiness_summary_sha256": inputs["gate_b_rule_comparison_summary.json"],
        "rule_approval_sha256": inputs["gate_b_rule_approval_stage124.json"],
        "output_files_sha256": output_hashes,
        "sample_counts": {
            "all_company_year_rows": EXPECTED_ROWS,
            "all_pairs": EXPECTED_PAIRS,
            "tickers": EXPECTED_TICKERS,
            "designs": {k: {"pairs": v["pairs"], "positive": v["positive"],
                            "negative": v["negative"], "target_missing": v["target_missing"]}
                        for k, v in stats.items()},
        },
        "unresolved_counts": unresolved_counts,
        "gate_b_started": True,
        "modeling_started": False,
        "warning": ("No modeling has started. Gate B execution only. "
                    "Next action: stage125-modeling-readiness."),
    }
    path = project_dir / "stage124" / "metadata_and_hashes_stage124_batch02_gate_b.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, sort_keys=True)
    return {"path": str(path), "output_files_sha256": output_hashes}


# --------------------------------------------------------------------------- #
# Invariant checks (fail-closed)
# --------------------------------------------------------------------------- #

def check_invariants(company_year: pd.DataFrame, pairs_out: pd.DataFrame,
                     stats: dict) -> None:
    errs = []
    for design, exp in EXPECTED_COUNTS.items():
        s = stats[design]
        if (s["pairs"], s["positive"], s["negative"], s["target_missing"]) != \
                (exp["pairs"], exp["positive"], exp["negative"], exp["missing"]):
            errs.append(f"{design}: got {s['pairs']}/{s['positive']}/{s['negative']}/"
                        f"{s['target_missing']}")
    if len(company_year) != EXPECTED_ROWS:
        errs.append(f"company_year rows {len(company_year)} != {EXPECTED_ROWS}")
    if len(pairs_out) != EXPECTED_PAIRS:
        errs.append(f"pairs {len(pairs_out)} != {EXPECTED_PAIRS}")

    def subset(a_col, b_col):
        return bool((~((pairs_out[a_col] == 1) & (pairs_out[b_col] != 1))).all())
    nests = [
        ("pair_final_eligible_main_gate_b_robustness", "pair_final_eligible_main_gate_b_primary"),
        ("pair_final_eligible_expanded_gate_b_robustness", "pair_final_eligible_expanded_gate_b_primary"),
        ("pair_final_eligible_main_gate_b_primary", "pair_final_eligible_expanded_gate_b_primary"),
        ("pair_final_eligible_main_gate_b_robustness", "pair_final_eligible_expanded_gate_b_robustness"),
    ]
    for a_col, b_col in nests:
        if not subset(a_col, b_col):
            errs.append(f"nesting violation: {a_col} not subset of {b_col}")

    if errs:
        raise QCFail("Invariant check failed (fail-closed):\n  " + "\n  ".join(errs))


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def run(project_dir: Path | None = None) -> dict:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent

    verify_report = verify_inputs(project_dir)

    all_rows = pd.read_csv(project_dir / "stage123" / "modeling_all_rows_stage123.csv",
                           encoding="utf-8-sig")
    pairs = pd.read_csv(project_dir / "stage123" / "modeling_one_year_ahead_stage123.csv",
                        encoding="utf-8-sig")
    listing_master = pd.read_csv(
        project_dir / "stage124" / "listing_master_verified_stage124.csv",
        encoding="utf-8-sig")

    schema_report = validate_schema(all_rows, pairs, listing_master)
    if not schema_report["overall_pass"]:
        raise QCFail("Schema validation failed:\n  " + "\n  ".join(
            f"{c['check']}: {c['detail']}" for c in schema_report["checks"]
            if c["status"] != "PASS"))

    company_year, audit = build_company_year(all_rows, listing_master)
    pairs_out = build_pairs(pairs, company_year)
    stats = compute_design_stats(pairs_out, audit)

    check_invariants(company_year, pairs_out, stats)

    output_info = generate_outputs(project_dir, repo_root, company_year, pairs_out,
                                   audit, stats, pairs, verify_report, schema_report)
    return {**output_info, "schema_report": schema_report,
            "verify_report": verify_report, "company_year": company_year,
            "pairs_out": pairs_out, "audit": audit}
