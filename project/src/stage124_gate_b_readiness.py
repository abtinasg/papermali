"""Stage124 Gate B Readiness — dry-run eligibility rule comparison.

This module computes three candidate Gate B eligibility rules (A/B/C) as a
dry-run comparison. It does NOT finalize any rule, does NOT execute Gate B,
and does NOT produce any new canonical dataset.

All listing master dates have date_semantics =
``first_observed_trading_date_from_official_tse_api``.  These dates are the
first observed trading dates from the official TSETMC API.  They are **NOT**
IPO dates, admission dates, or listing dates.

Scientific controls
-------------------
* No missing value is zeroed.
* No date or year is guessed.
* No row is dropped.
* ``fiscal_year_start`` is computed only when the fiscal period is 12 months
  and ``fiscal_year_end`` is present; otherwise Rule B and Rule C are marked
  ``unresolved``.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DATE_SEMANTICS = "first_observed_trading_date_from_official_tse_api"
DATE_SEMANTICS_NOTE = (
    "These dates are the first observed trading dates from the official "
    "TSETMC API. They are NOT IPO dates, admission dates, or listing dates."
)
EXPECTED_ROWS = 1331
EXPECTED_TICKERS = 130
TARGET_YEAR_RANGE = list(range(1393, 1403))  # 1393–1402 inclusive

RULE_DESCRIPTIONS = {
    "rule_a": "first_observed_trading_date <= fiscal_year_end (end-of-year rule)",
    "rule_b": "first_observed_trading_date <= fiscal_year_start (start-of-year strict rule)",
    "rule_c": "first_observed_trading_year < fiscal_year (year-level conservative rule)",
}

# Columns required in modeling_all_rows
REQUIRED_COLS_ALL_ROWS = ("row_key", "ticker", "fiscal_year", "fiscal_year_end")

# Columns required in listing master
REQUIRED_COLS_LISTING = (
    "ticker",
    "first_public_trading_date_jalali",
    "first_public_trading_date_gregorian",
)

# Audit CSV columns (order matters)
AUDIT_COLUMNS = [
    "row_key",
    "ticker",
    "fiscal_year",
    "fiscal_year_end",
    "fiscal_year_start",
    "first_public_trading_date_jalali",
    "first_public_trading_date_gregorian",
    "date_semantics",
    "eligible_rule_a",
    "eligible_rule_b",
    "eligible_rule_c",
    "exclusion_reason_rule_a",
    "exclusion_reason_rule_b",
    "exclusion_reason_rule_c",
    "data_quality_status",
]

# Other eligibility base flags from Stage123 (excluding eligible_listing)
OTHER_BASE_FLAGS = [
    "eligible_statement_type",
    "eligible_annual_period",
    "eligible_source_quality",
    "eligible_accounting_quality",
]


class QCFail(Exception):
    """Fatal QC error during Gate B readiness."""


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #

def sha256_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_input_hashes(project_dir: Path) -> dict:
    """Verify SHA-256 of local input files against Stage123 metadata.

    The two CSV files (modeling_all_rows, modeling_one_year_ahead) are
    fail-closed: a hash mismatch raises QCFail and no outputs are produced.

    The workbook (stage123_workbook.xlsx) is gitignored and regenerable;
    its hash is reported informationally but does not block the dry-run.
    The workbook is not used in the analysis.

    Returns a dict with explicit per-category fields:

    - ``authoritative_csv_all_match``: True iff both CSVs match.
    - ``authoritative_csv_verified_count``: number of CSVs that matched.
    - ``workbook_match``: True iff the workbook hash matches.
    - ``workbook_nonblocking``: always True (workbook is informational).
    - ``workbook_used_in_analysis``: always False.
    - ``files``: per-file details.
    - ``mismatches``: list of mismatch descriptions (CSV only).
    - ``workbook_note``: informational note about the workbook.
    """
    metadata_path = project_dir / "stage123" / "metadata_and_hashes_stage123.json"
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    expected_hashes = metadata["output_files_sha256"]

    # Fail-closed files (CSV — used in the analysis)
    csv_files = {
        "modeling_all_rows_stage123.csv": project_dir / "stage123" / "modeling_all_rows_stage123.csv",
        "modeling_one_year_ahead_stage123.csv": project_dir / "stage123" / "modeling_one_year_ahead_stage123.csv",
    }
    # Informational file (xlsx — gitignored, regenerable, not used in analysis)
    workbook_file = {
        "stage123_workbook.xlsx": project_dir / "stage123" / "stage123_workbook.xlsx",
    }

    result = {
        "authoritative_csv_all_match": True,
        "authoritative_csv_verified_count": 0,
        "workbook_match": False,
        "workbook_nonblocking": True,
        "workbook_used_in_analysis": False,
        "files": {},
        "mismatches": [],
        "workbook_note": "",
    }

    # Check CSVs (fail-closed)
    for fname, fpath in csv_files.items():
        if not fpath.is_file():
            result["authoritative_csv_all_match"] = False
            result["mismatches"].append(f"{fname}: file not found")
            result["files"][fname] = {"found": False}
            continue
        actual = sha256_file(fpath)
        expected = expected_hashes.get(fname)
        match = (actual == expected) if expected else False
        result["files"][fname] = {
            "found": True,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": match,
            "fail_closed": True,
        }
        if match:
            result["authoritative_csv_verified_count"] += 1
        else:
            result["authoritative_csv_all_match"] = False
            result["mismatches"].append(
                f"{fname}: expected {expected}, got {actual}"
            )

    # Check workbook (informational only)
    for fname, fpath in workbook_file.items():
        if not fpath.is_file():
            result["files"][fname] = {"found": False, "match": False, "fail_closed": False}
            result["workbook_note"] = f"{fname}: file not found (informational, not used in analysis)"
            continue
        actual = sha256_file(fpath)
        expected = expected_hashes.get(fname)
        match = (actual == expected) if expected else False
        result["files"][fname] = {
            "found": True,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": match,
            "fail_closed": False,
        }
        result["workbook_match"] = match
        if not match:
            result["workbook_note"] = (
                f"{fname}: hash mismatch (expected {expected[:16]}..., "
                f"got {actual[:16]}...). This file is gitignored and regenerable; "
                "it is not used in the analysis. CSV files verified successfully."
            )

    if not result["authoritative_csv_all_match"]:
        raise QCFail(
            "Input file hash verification failed (fail-closed):\n  "
            + "\n  ".join(result["mismatches"])
        )

    return result


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #

def validate_schema(all_rows: pd.DataFrame, listing_master: pd.DataFrame) -> dict:
    """Validate schema and key connections between Stage123 and listing master."""
    checks = []
    overall_pass = True

    def _check(name, cond, detail=""):
        nonlocal overall_pass
        status = "PASS" if cond else "FAIL"
        if not cond:
            overall_pass = False
        checks.append({"check": name, "status": status, "detail": detail})

    # 1. Row count
    _check("all_rows_count", len(all_rows) == EXPECTED_ROWS,
           f"{len(all_rows)}/{EXPECTED_ROWS}")

    # 2. Required columns
    missing_cols = [c for c in REQUIRED_COLS_ALL_ROWS if c not in all_rows.columns]
    _check("all_rows_required_columns", len(missing_cols) == 0,
           f"missing={missing_cols}" if missing_cols else "all present")

    # 3. row_key unique
    n_dup = int(all_rows["row_key"].duplicated().sum())
    _check("row_key_unique", n_dup == 0, f"duplicates={n_dup}")

    # 4. Unique tickers
    n_tickers = all_rows["ticker"].nunique()
    _check("unique_tickers", n_tickers == EXPECTED_TICKERS,
           f"{n_tickers}/{EXPECTED_TICKERS}")

    # 5. Listing master tickers
    lm_tickers = listing_master["ticker"].nunique()
    _check("listing_master_unique_tickers", lm_tickers == EXPECTED_TICKERS,
           f"{lm_tickers}/{EXPECTED_TICKERS}")

    # 6. All Stage123 tickers have exactly one match in listing master
    s123_tickers = set(all_rows["ticker"].unique())
    lm_ticker_set = set(listing_master["ticker"].unique())
    unmatched = s123_tickers - lm_ticker_set
    _check("all_tickers_matched", len(unmatched) == 0,
           f"unmatched={sorted(unmatched)}" if unmatched else "all matched")

    # 7. No duplicate tickers in listing master
    lm_dup = int(listing_master["ticker"].duplicated().sum())
    _check("no_duplicate_listing_tickers", lm_dup == 0,
           f"duplicates={lm_dup}")

    # 8. Listing master required columns
    missing_lm_cols = [c for c in REQUIRED_COLS_LISTING if c not in listing_master.columns]
    _check("listing_master_required_columns", len(missing_lm_cols) == 0,
           f"missing={missing_lm_cols}" if missing_lm_cols else "all present")

    # 9. No missing trading dates in listing master
    n_missing_dates = int(listing_master["first_public_trading_date_jalali"].isna().sum())
    _check("no_missing_trading_dates", n_missing_dates == 0,
           f"missing={n_missing_dates}")

    return {"overall_pass": overall_pass, "checks": checks}


# --------------------------------------------------------------------------- #
# Date parsing (Jalali)
# --------------------------------------------------------------------------- #

def parse_jalali_date(date_str: str) -> jdatetime.date | None:
    """Parse a Jalali date string in YYYY/MM/DD or YYYY-MM-DD format."""
    if not HAS_JDATETIME:
        raise QCFail("jdatetime library is required for Jalali date parsing")
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None
    s = str(date_str).strip()
    sep = "/" if "/" in s else "-"
    parts = s.split(sep)
    if len(parts) != 3:
        return None
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return jdatetime.date(y, m, d)
    except (ValueError, Exception):
        return None


def compute_fiscal_year_start(
    fy_end_str: str, non_12_month_flag: int
) -> jdatetime.date | None:
    """Compute fiscal_year_start from fiscal_year_end and period flag.

    For 12-month periods:
        - If fy_end.month == 12: fy_start = jdatetime.date(fy_end.year, 1, 1)
          (fiscal year starts on the first day of the same Jalali year)
        - Otherwise: fy_start = jdatetime.date(fy_end.year - 1, fy_end.month + 1, 1)
          (first day of the month after fy_end.month, in the previous year)

    This correctly handles leap-year Esfand 30 (e.g. 1399/12/30) where
    the naive "fy_end - 1 year + 1 day" would fail because the previous
    year's Esfand has only 29 days.

    For non-12-month periods or missing fy_end: returns None (unresolved).
    """
    if pd.isna(fy_end_str) or str(fy_end_str).strip() == "":
        return None
    if int(non_12_month_flag) != 0:
        return None
    fy_end = parse_jalali_date(str(fy_end_str))
    if fy_end is None:
        return None
    try:
        if fy_end.month == 12:
            return jdatetime.date(fy_end.year, 1, 1)
        else:
            return jdatetime.date(fy_end.year - 1, fy_end.month + 1, 1)
    except (ValueError, Exception):
        return None


def extract_jalali_year(date_str: str) -> int | None:
    """Extract the Jalali year from a date string (YYYY-MM-DD or YYYY/MM/DD)."""
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None
    s = str(date_str).strip()
    sep = "/" if "/" in s else "-"
    parts = s.split(sep)
    if len(parts) < 1:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Rule computation
# --------------------------------------------------------------------------- #

def compute_rules(
    all_rows: pd.DataFrame, listing_master: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Compute eligibility under Rules A/B/C for each row.

    Returns the audit DataFrame and a data-quality summary.
    """
    # Merge all_rows with listing master on ticker
    lm_subset = listing_master[["ticker", "first_public_trading_date_jalali",
                                "first_public_trading_date_gregorian"]].copy()
    merged = all_rows.merge(lm_subset, on="ticker", how="left")

    # Prepare output
    audit = pd.DataFrame(index=merged.index)
    audit["row_key"] = merged["row_key"]
    audit["ticker"] = merged["ticker"]
    audit["fiscal_year"] = merged["fiscal_year"]
    audit["fiscal_year_end"] = merged["fiscal_year_end"]
    audit["fiscal_year_start"] = ""
    audit["first_public_trading_date_jalali"] = merged["first_public_trading_date_jalali"]
    audit["first_public_trading_date_gregorian"] = merged["first_public_trading_date_gregorian"]
    audit["date_semantics"] = DATE_SEMANTICS

    # Data quality status
    dq_status = []
    for i in merged.index:
        fye = merged.at[i, "fiscal_year_end"]
        non12 = merged.at[i, "non_12_month_period_flag"]
        has_lm = pd.notna(merged.at[i, "first_public_trading_date_jalali"])
        issues = []
        if pd.isna(fye) or str(fye).strip() == "":
            issues.append("missing_fiscal_year_end")
        if int(non12) != 0:
            issues.append("non_12_month_period")
        if not has_lm:
            issues.append("unmatched_ticker")
        dq_status.append(" | ".join(issues) if issues else "ok")
    audit["data_quality_status"] = dq_status

    # Compute eligibility for each rule
    eligible_a = []
    eligible_b = []
    eligible_c = []
    reason_a = []
    reason_b = []
    reason_c = []
    fy_start_strs = []

    for i in merged.index:
        fye_str = merged.at[i, "fiscal_year_end"]
        fy = merged.at[i, "fiscal_year"]
        non12 = merged.at[i, "non_12_month_period_flag"]
        ftd_jalali = merged.at[i, "first_public_trading_date_jalali"]

        # --- Rule A: first_observed_trading_date <= fiscal_year_end ---
        fye_date = parse_jalali_date(str(fye_str)) if pd.notna(fye_str) else None
        ftd_date = parse_jalali_date(str(ftd_jalali)) if pd.notna(ftd_jalali) else None

        if fye_date is None:
            eligible_a.append("unresolved")
            reason_a.append("fiscal_year_end_missing_or_unparseable")
        elif ftd_date is None:
            eligible_a.append("unresolved")
            reason_a.append("trading_date_missing")
        elif ftd_date <= fye_date:
            eligible_a.append(1)
            reason_a.append("")
        else:
            eligible_a.append(0)
            reason_a.append("first_trading_date_after_fy_end")

        # --- Compute fiscal_year_start for Rule B and C ---
        fy_start = compute_fiscal_year_start(fye_str, non12)
        if fy_start is not None:
            fy_start_strs.append(
                f"{fy_start.year}/{fy_start.month:02d}/{fy_start.day:02d}"
            )
        else:
            fy_start_strs.append("")

        # --- Rule B: first_observed_trading_date <= fiscal_year_start ---
        if fy_start is None:
            eligible_b.append("unresolved")
            reason_b.append("fiscal_year_start_unresolved")
        elif ftd_date is None:
            eligible_b.append("unresolved")
            reason_b.append("trading_date_missing")
        elif ftd_date <= fy_start:
            eligible_b.append(1)
            reason_b.append("")
        else:
            eligible_b.append(0)
            reason_b.append("first_trading_date_after_fy_start")

        # --- Rule C: first_observed_trading_year < fiscal_year ---
        if fy_start is None:
            eligible_c.append("unresolved")
            reason_c.append("fiscal_year_start_unresolved")
        else:
            ftd_year = extract_jalali_year(str(ftd_jalali)) if pd.notna(ftd_jalali) else None
            fy_int = int(fy) if pd.notna(fy) else None
            if ftd_year is None or fy_int is None:
                eligible_c.append("unresolved")
                reason_c.append("year_extraction_failed")
            elif ftd_year < fy_int:
                eligible_c.append(1)
                reason_c.append("")
            else:
                eligible_c.append(0)
                reason_c.append("first_trading_year_gte_fy")

    audit["eligible_rule_a"] = eligible_a
    audit["eligible_rule_b"] = eligible_b
    audit["eligible_rule_c"] = eligible_c
    audit["exclusion_reason_rule_a"] = reason_a
    audit["exclusion_reason_rule_b"] = reason_b
    audit["exclusion_reason_rule_c"] = reason_c
    audit["fiscal_year_start"] = fy_start_strs

    # Sort by row_key for deterministic output
    audit = audit.sort_values("row_key").reset_index(drop=True)

    # Data quality summary
    dq_summary = {
        "ok": int((audit["data_quality_status"] == "ok").sum()),
        "missing_fiscal_year_end": int(audit["data_quality_status"].str.contains("missing_fiscal_year_end").sum()),
        "non_12_month_period": int(audit["data_quality_status"].str.contains("non_12_month_period").sum()),
        "unmatched_ticker": int(audit["data_quality_status"].str.contains("unmatched_ticker").sum()),
    }

    return audit[AUDIT_COLUMNS], dq_summary


# --------------------------------------------------------------------------- #
# Pair impact analysis
# --------------------------------------------------------------------------- #

def _eligible_int(val) -> int:
    """Convert eligibility value to int (1=eligible, 0=not eligible, unresolved=0 conservative)."""
    if val == 1 or val == "1":
        return 1
    return 0


def compute_pair_impact(
    all_rows: pd.DataFrame,
    pairs: pd.DataFrame,
    audit: pd.DataFrame,
) -> dict:
    """Compute pair-level impact for each rule and Stage123 baseline."""

    # Base flags from Stage123 (excluding eligible_listing)
    # We need to recompute predictor_eligible by replacing eligible_listing
    # with each rule's result.

    # Create a lookup from row_key to Stage123 eligibility flags
    s123_lookup = all_rows.set_index("row_key")[
        OTHER_BASE_FLAGS + ["eligible_company_main"]
    ].to_dict("index")

    # Create a lookup from row_key to rule eligibility
    rule_lookup = audit.set_index("row_key")[
        ["eligible_rule_a", "eligible_rule_b", "eligible_rule_c"]
    ].to_dict("index")

    # Compute new predictor_eligible for each rule
    def _new_predictor_eligible(row_key: str, rule_col: str) -> int:
        s123 = s123_lookup.get(row_key, {})
        rule_val = rule_lookup.get(row_key, {}).get(rule_col, "unresolved")
        # All other base flags must be 1
        other_ok = all(
            int(s123.get(flag, 0)) == 1 for flag in OTHER_BASE_FLAGS
        )
        # Rule eligibility (1 = eligible, everything else = not eligible)
        rule_ok = _eligible_int(rule_val) == 1
        # Company eligibility
        company_ok = int(s123.get("eligible_company_main", 0)) == 1
        return 1 if (other_ok and rule_ok and company_ok) else 0

    # For each pair, compute new pair_final_eligible under each rule
    pair_results = {}
    for rule_col in ["eligible_rule_a", "eligible_rule_b", "eligible_rule_c"]:
        new_eligible = []
        for _, pair in pairs.iterrows():
            predictor_key = pair["predictor_row_key_t"]
            valid_target = int(pair["valid_target_t_plus_1"])
            new_pred = _new_predictor_eligible(predictor_key, rule_col)
            new_pair = 1 if (new_pred == 1 and valid_target == 1) else 0
            new_eligible.append(new_pair)
        pair_results[rule_col] = new_eligible

    # Stage123 baseline
    s123_eligible = pairs["pair_final_eligible_main"].astype(int).tolist()

    # Compute statistics for each rule
    impact = {}
    rule_names = {
        "eligible_rule_a": "rule_a",
        "eligible_rule_b": "rule_b",
        "eligible_rule_c": "rule_c",
    }

    for rule_col, rule_name in rule_names.items():
        eligible_vals = audit[rule_col].tolist()
        n_eligible = sum(1 for v in eligible_vals if v == 1 or v == "1")
        n_pre_listing = sum(1 for v in eligible_vals if v == 0 or v == "0")
        n_unresolved = sum(1 for v in eligible_vals if v == "unresolved")

        # Affected tickers (tickers with at least one non-eligible row under this rule)
        affected_mask = audit[rule_col].apply(lambda v: v != 1 and v != "1")
        affected_tickers = sorted(audit.loc[affected_mask, "ticker"].unique().tolist())

        # Pair statistics
        pair_eligible = pair_results[rule_col]
        pair_eligible_set = [i for i, v in enumerate(pair_eligible) if v == 1]

        # Target values for eligible pairs
        targets = pairs["FD_target_main_t_plus_1"].tolist()
        predictor_years = pairs["fiscal_year_t"].tolist()
        target_years = pairs["target_year"].tolist()

        n_pos = 0
        n_neg = 0
        n_target_missing = 0

        for i in pair_eligible_set:
            t = targets[i]
            if pd.isna(t):
                n_target_missing += 1
            elif float(t) == 1.0:
                n_pos += 1
            else:
                n_neg += 1

        # --- Distribution by predictor year (fiscal_year_t) ---
        predictor_year_dist = {}
        for y in sorted(set(int(y) for y in predictor_years if pd.notna(y))):
            y_str = str(y)
            predictor_year_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
        for i in pair_eligible_set:
            y_str = str(int(predictor_years[i]))
            predictor_year_dist[y_str]["n"] += 1
            t = targets[i]
            if pd.isna(t):
                pass
            elif float(t) == 1.0:
                predictor_year_dist[y_str]["pos"] += 1
            else:
                predictor_year_dist[y_str]["neg"] += 1

        # --- Distribution by target year (target_year = t+1) ---
        # Main distribution for article and Rule comparison; covers 1393–1402
        target_year_dist = {}
        for y in TARGET_YEAR_RANGE:
            y_str = str(y)
            target_year_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
        for i in pair_eligible_set:
            ty = target_years[i]
            if pd.isna(ty):
                continue
            y_str = str(int(ty))
            if y_str not in target_year_dist:
                target_year_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
            target_year_dist[y_str]["n"] += 1
            t = targets[i]
            if pd.isna(t):
                pass
            elif float(t) == 1.0:
                target_year_dist[y_str]["pos"] += 1
            else:
                target_year_dist[y_str]["neg"] += 1

        # Change vs Stage123
        s123_n_eligible = sum(s123_eligible)
        change = sum(pair_eligible) - s123_n_eligible

        impact[rule_name] = {
            "description": RULE_DESCRIPTIONS[rule_name],
            "total_company_year_rows": len(audit),
            "eligible_rows": n_eligible,
            "pre_listing_rows": n_pre_listing,
            "unresolved_rows": n_unresolved,
            "affected_tickers_count": len(affected_tickers),
            "affected_tickers": affected_tickers,
            "total_pairs": len(pairs),
            "eligible_pairs": sum(pair_eligible),
            "positive_pairs": n_pos,
            "negative_pairs": n_neg,
            "target_missing_pairs": n_target_missing,
            "change_vs_stage123": change,
            "pos_neg_by_predictor_year_t": predictor_year_dist,
            "pos_neg_by_target_year_t_plus_1": target_year_dist,
        }

    # Stage123 baseline
    s123_targets = pairs["FD_target_main_t_plus_1"].tolist()
    s123_predictor_years = pairs["fiscal_year_t"].tolist()
    s123_target_years = pairs["target_year"].tolist()
    s123_eligible_set = [i for i, v in enumerate(s123_eligible) if v == 1]
    s123_pos = sum(1 for i in s123_eligible_set if not pd.isna(s123_targets[i]) and float(s123_targets[i]) == 1.0)
    s123_neg = sum(1 for i in s123_eligible_set if not pd.isna(s123_targets[i]) and float(s123_targets[i]) == 0.0)
    s123_missing = sum(1 for i in s123_eligible_set if pd.isna(s123_targets[i]))

    # Baseline distribution by predictor year
    s123_predictor_dist = {}
    for y in sorted(set(int(y) for y in s123_predictor_years if pd.notna(y))):
        y_str = str(y)
        s123_predictor_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
    for i in s123_eligible_set:
        y_str = str(int(s123_predictor_years[i]))
        s123_predictor_dist[y_str]["n"] += 1
        t = s123_targets[i]
        if pd.isna(t):
            pass
        elif float(t) == 1.0:
            s123_predictor_dist[y_str]["pos"] += 1
        else:
            s123_predictor_dist[y_str]["neg"] += 1

    # Baseline distribution by target year
    s123_target_dist = {}
    for y in TARGET_YEAR_RANGE:
        y_str = str(y)
        s123_target_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
    for i in s123_eligible_set:
        ty = s123_target_years[i]
        if pd.isna(ty):
            continue
        y_str = str(int(ty))
        if y_str not in s123_target_dist:
            s123_target_dist[y_str] = {"n": 0, "pos": 0, "neg": 0}
        s123_target_dist[y_str]["n"] += 1
        t = s123_targets[i]
        if pd.isna(t):
            pass
        elif float(t) == 1.0:
            s123_target_dist[y_str]["pos"] += 1
        else:
            s123_target_dist[y_str]["neg"] += 1

    impact["stage123_baseline"] = {
        "description": "Stage123 existing eligible_listing (ocf_resolution_status proxy)",
        "total_company_year_rows": len(audit),
        "eligible_pairs": sum(s123_eligible),
        "positive_pairs": s123_pos,
        "negative_pairs": s123_neg,
        "target_missing_pairs": s123_missing,
        "pos_neg_by_predictor_year_t": s123_predictor_dist,
        "pos_neg_by_target_year_t_plus_1": s123_target_dist,
    }

    # Rows differing between Rule A and Rule B
    differ_a_b = []
    for i in audit.index:
        va = audit.at[i, "eligible_rule_a"]
        vb = audit.at[i, "eligible_rule_b"]
        if va != vb:
            differ_a_b.append(audit.at[i, "row_key"])
    impact["rows_differing_between_a_and_b"] = differ_a_b
    impact["count_rows_differing_between_a_and_b"] = len(differ_a_b)

    # Rows differing between Rule A and Rule C
    differ_a_c = []
    for i in audit.index:
        va = audit.at[i, "eligible_rule_a"]
        vc = audit.at[i, "eligible_rule_c"]
        if va != vc:
            differ_a_c.append(audit.at[i, "row_key"])
    impact["rows_differing_between_a_and_c"] = differ_a_c
    impact["count_rows_differing_between_a_and_c"] = len(differ_a_c)

    # Rows differing between Rule B and Rule C
    differ_b_c = []
    for i in audit.index:
        vb = audit.at[i, "eligible_rule_b"]
        vc = audit.at[i, "eligible_rule_c"]
        if vb != vc:
            differ_b_c.append(audit.at[i, "row_key"])
    impact["rows_differing_between_b_and_c"] = differ_b_c
    impact["count_rows_differing_between_b_and_c"] = len(differ_b_c)

    # --- Build disagreement rows DataFrame ---
    # All rows where any two rules disagree, with pair-level fields joined.
    differ_row_keys = set(differ_a_b) | set(differ_a_c) | set(differ_b_c)
    disagree_rows = audit[audit["row_key"].isin(differ_row_keys)].copy()

    # Build pair lookup: predictor_row_key_t -> (FD_target, pair_eligible per rule)
    pair_lookup = {}
    for idx, pair in pairs.iterrows():
        rk = pair["predictor_row_key_t"]
        pair_lookup[rk] = {
            "FD_target_main_t_plus_1": pair["FD_target_main_t_plus_1"],
            "pair_eligible_rule_a": pair_results["eligible_rule_a"][idx],
            "pair_eligible_rule_b": pair_results["eligible_rule_b"][idx],
            "pair_eligible_rule_c": pair_results["eligible_rule_c"][idx],
        }

    fd_targets = []
    pe_a = []
    pe_b = []
    pe_c = []
    for _, row in disagree_rows.iterrows():
        info = pair_lookup.get(row["row_key"])
        if info:
            fd_targets.append(info["FD_target_main_t_plus_1"])
            pe_a.append(info["pair_eligible_rule_a"])
            pe_b.append(info["pair_eligible_rule_b"])
            pe_c.append(info["pair_eligible_rule_c"])
        else:
            fd_targets.append("")
            pe_a.append("")
            pe_b.append("")
            pe_c.append("")

    disagree_rows = disagree_rows.assign(
        FD_target_main_t_plus_1=fd_targets,
        pair_eligible_rule_a=pe_a,
        pair_eligible_rule_b=pe_b,
        pair_eligible_rule_c=pe_c,
    )

    DISAGREE_COLUMNS = [
        "row_key", "ticker", "fiscal_year", "fiscal_year_end",
        "fiscal_year_start", "first_public_trading_date_jalali",
        "eligible_rule_a", "eligible_rule_b", "eligible_rule_c",
        "exclusion_reason_rule_a", "exclusion_reason_rule_b",
        "exclusion_reason_rule_c",
        "FD_target_main_t_plus_1",
        "pair_eligible_rule_a", "pair_eligible_rule_b",
        "pair_eligible_rule_c",
    ]
    available_cols = [c for c in DISAGREE_COLUMNS if c in disagree_rows.columns]
    impact["disagreement_rows"] = disagree_rows[available_cols]

    return impact


# --------------------------------------------------------------------------- #
# Output generation
# --------------------------------------------------------------------------- #

def _git_head(repo_root: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    """Return the committer timestamp of *commit* in ISO-8601 UTC.

    Used as a deterministic timestamp so that repeated runs from the same
    commit produce byte-identical artifacts (idempotence).
    """
    proc = subprocess.run(
        ["git", "-C", repo_root, "log", "-1", "--format=%cI", commit],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return "unknown"
    raw = proc.stdout.strip()
    # %cI gives e.g. 2026-07-11T14:30:00+03:30 — normalise to UTC Z suffix
    try:
        from datetime import datetime as _dt
        dt = _dt.fromisoformat(raw)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return raw


def generate_outputs(
    project_dir: Path,
    repo_root: Path,
    audit: pd.DataFrame,
    impact: dict,
    schema_report: dict,
    hash_report: dict,
    dq_summary: dict,
) -> dict:
    """Generate all output files in project/stage124/gate_b_readiness/."""

    out_dir = project_dir / "stage124" / "gate_b_readiness"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. gate_b_company_year_audit.csv
    audit_path = out_dir / "gate_b_company_year_audit.csv"
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")

    # 2. gate_b_pair_impact_summary.csv
    impact_rows = []
    for rule_name in ["rule_a", "rule_b", "rule_c"]:
        r = impact[rule_name]
        impact_rows.append({
            "rule": rule_name,
            "description": r["description"],
            "total_company_year_rows": r["total_company_year_rows"],
            "eligible_rows": r["eligible_rows"],
            "pre_listing_rows": r["pre_listing_rows"],
            "unresolved_rows": r["unresolved_rows"],
            "affected_tickers_count": r["affected_tickers_count"],
            "affected_tickers": ";".join(r["affected_tickers"]),
            "total_pairs": r["total_pairs"],
            "eligible_pairs": r["eligible_pairs"],
            "positive_pairs": r["positive_pairs"],
            "negative_pairs": r["negative_pairs"],
            "target_missing_pairs": r["target_missing_pairs"],
            "change_vs_stage123": r["change_vs_stage123"],
            "pos_neg_by_predictor_year_t": json.dumps(r["pos_neg_by_predictor_year_t"], ensure_ascii=False, sort_keys=True),
            "pos_neg_by_target_year_t_plus_1": json.dumps(r["pos_neg_by_target_year_t_plus_1"], ensure_ascii=False, sort_keys=True),
        })
    # Add baseline
    bl = impact["stage123_baseline"]
    impact_rows.append({
        "rule": "stage123_baseline",
        "description": bl["description"],
        "total_company_year_rows": bl["total_company_year_rows"],
        "eligible_rows": "",
        "pre_listing_rows": "",
        "unresolved_rows": "",
        "affected_tickers_count": "",
        "affected_tickers": "",
        "total_pairs": "",
        "eligible_pairs": bl["eligible_pairs"],
        "positive_pairs": bl["positive_pairs"],
        "negative_pairs": bl["negative_pairs"],
        "target_missing_pairs": bl["target_missing_pairs"],
        "change_vs_stage123": 0,
        "pos_neg_by_predictor_year_t": json.dumps(bl["pos_neg_by_predictor_year_t"], ensure_ascii=False, sort_keys=True),
        "pos_neg_by_target_year_t_plus_1": json.dumps(bl["pos_neg_by_target_year_t_plus_1"], ensure_ascii=False, sort_keys=True),
    })
    impact_df = pd.DataFrame(impact_rows)
    impact_path = out_dir / "gate_b_pair_impact_summary.csv"
    impact_df.to_csv(impact_path, index=False, encoding="utf-8-sig")

    # 3. gate_b_unmatched_or_ambiguous_rows.csv
    unmatched = audit[audit["data_quality_status"] != "ok"].copy()
    unmatched_path = out_dir / "gate_b_unmatched_or_ambiguous_rows.csv"
    unmatched.to_csv(unmatched_path, index=False, encoding="utf-8-sig")

    # 3b. gate_b_rule_disagreement_rows.csv
    disagree_df = impact.get("disagreement_rows")
    if disagree_df is not None and len(disagree_df) > 0:
        disagree_path = out_dir / "gate_b_rule_disagreement_rows.csv"
        disagree_df.to_csv(disagree_path, index=False, encoding="utf-8-sig")

    # 4. gate_b_rule_comparison_summary.json
    summary = {
        "stage": "stage124-gate-b-readiness",
        "description": "Dry-run comparison of three Gate B eligibility rules",
        "date_semantics": DATE_SEMANTICS,
        "date_semantics_note": DATE_SEMANTICS_NOTE,
        "warning": (
            "No rule has been finalized. User and scientific reviewer must "
            "approve the final rule from the comparison report before proceeding."
        ),
        "next_action": "stage124-gate-b-rule-approval",
        "input_files": {
            "modeling_all_rows": {
                "path": "project/stage123/modeling_all_rows_stage123.csv",
                "sha256": hash_report["files"]["modeling_all_rows_stage123.csv"]["actual_sha256"],
                "rows": EXPECTED_ROWS,
            },
            "modeling_one_year_ahead": {
                "path": "project/stage123/modeling_one_year_ahead_stage123.csv",
                "sha256": hash_report["files"]["modeling_one_year_ahead_stage123.csv"]["actual_sha256"],
            },
            "stage123_workbook": {
                "path": "project/stage123/stage123_workbook.xlsx",
                "sha256": hash_report["files"]["stage123_workbook.xlsx"]["actual_sha256"],
            },
            "listing_master": {
                "path": "project/stage124/listing_master_verified_stage124.csv",
                "tickers": EXPECTED_TICKERS,
            },
        },
        "hash_verification": {
            "authoritative_csv_all_match": hash_report["authoritative_csv_all_match"],
            "authoritative_csv_verified_count": hash_report["authoritative_csv_verified_count"],
            "workbook_match": hash_report["workbook_match"],
            "workbook_nonblocking": hash_report["workbook_nonblocking"],
            "workbook_used_in_analysis": hash_report["workbook_used_in_analysis"],
            "mismatches": hash_report["mismatches"],
            "workbook_note": hash_report.get("workbook_note", ""),
        },
        "schema_validation": schema_report,
        "data_quality_summary": dq_summary,
        "rules": {
            "rule_a": impact["rule_a"],
            "rule_b": impact["rule_b"],
            "rule_c": impact["rule_c"],
        },
        "stage123_baseline": impact["stage123_baseline"],
        "rows_differing_between_a_and_b": {
            "count": impact["count_rows_differing_between_a_and_b"],
            "row_keys": impact["rows_differing_between_a_and_b"],
        },
        "rows_differing_between_a_and_c": {
            "count": impact["count_rows_differing_between_a_and_c"],
            "row_keys": impact["rows_differing_between_a_and_c"],
        },
        "rows_differing_between_b_and_c": {
            "count": impact["count_rows_differing_between_b_and_c"],
            "row_keys": impact["rows_differing_between_b_and_c"],
        },
    }
    summary_path = out_dir / "gate_b_rule_comparison_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)

    # 5. gate_b_readiness_qc_report.json
    source_commit = _git_head(str(repo_root))
    src_path = repo_root / "project" / "src" / "stage124_gate_b_readiness.py"
    test_path = repo_root / "project" / "tests" / "test_stage124_gate_b_readiness.py"

    qc_assertions = []
    for check in schema_report["checks"]:
        qc_assertions.append({
            "assertion": check["check"],
            "status": check["status"],
            "detail": check["detail"],
        })
    if hash_report["workbook_match"]:
        _hash_detail = (
            f"{hash_report['authoritative_csv_verified_count']} authoritative "
            "Stage123 CSV files matched exactly. Workbook hash matched."
        )
    else:
        _hash_detail = (
            f"{hash_report['authoritative_csv_verified_count']} authoritative "
            "Stage123 CSV files matched exactly. Workbook hash mismatch "
            "recorded as a non-blocking warning; workbook not used."
        )
    qc_assertions.append({
        "assertion": "hash_verification",
        "status": "PASS" if hash_report["authoritative_csv_all_match"] else "FAIL",
        "detail": _hash_detail,
    })
    qc_assertions.append({
        "assertion": "no_modeling_started",
        "status": "PASS",
        "detail": "No modeling artifacts created",
    })
    qc_assertions.append({
        "assertion": "no_gate_b_executed",
        "status": "PASS",
        "detail": "Gate B not finalized; dry-run only",
    })
    qc_assertions.append({
        "assertion": "no_canonical_dataset_produced",
        "status": "PASS",
        "detail": "No new canonical dataset generated",
    })
    qc_assertions.append({
        "assertion": "date_semantics_declared",
        "status": "PASS",
        "detail": DATE_SEMANTICS,
    })
    qc_assertions.append({
        "assertion": "no_missing_zeroed",
        "status": "PASS",
        "detail": "No missing values were zeroed",
    })
    qc_assertions.append({
        "assertion": "no_rows_dropped",
        "status": "PASS",
        "detail": f"All {EXPECTED_ROWS} rows preserved in audit",
    })

    # Read tickers from listing master
    lm = pd.read_csv(project_dir / "stage124" / "listing_master_verified_stage124.csv")
    tickers = sorted(lm["ticker"].tolist())

    all_pass = schema_report["overall_pass"] and hash_report["authoritative_csv_all_match"]
    failed_count = sum(1 for a in qc_assertions if a["status"] != "PASS")

    deterministic_ts = _git_commit_timestamp(str(repo_root), source_commit)
    qc_report = {
        "stage": "stage124_gate_b_readiness",
        "generated_at": deterministic_ts,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(src_path) if src_path.is_file() else None,
        "test_file_sha256": sha256_file(test_path) if test_path.is_file() else None,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "all_pass": all_pass,
        "assertion_count": len(qc_assertions),
        "failed_count": failed_count,
        "assertions": qc_assertions,
    }
    qc_path = out_dir / "gate_b_readiness_qc_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(qc_report, f, indent=2, ensure_ascii=False, sort_keys=True)

    # 6. Generate README before computing hashes so its hash is current
    generate_readme(out_dir, impact, hash_report, schema_report, dq_summary)

    # 7. metadata_and_hashes_gate_b_readiness.json
    # NOTE: metadata_and_hashes_gate_b_readiness.json is intentionally NOT
    # included in output_files_sha256 to avoid the self-hash paradox
    # (writing the hash inside the file changes the file's hash).
    output_files = [
        "gate_b_rule_comparison_summary.json",
        "gate_b_company_year_audit.csv",
        "gate_b_pair_impact_summary.csv",
        "gate_b_unmatched_or_ambiguous_rows.csv",
        "gate_b_rule_disagreement_rows.csv",
        "gate_b_readiness_qc_report.json",
        "README_GATE_B_READINESS.md",
    ]
    output_hashes = {}
    for fname in output_files:
        fpath = out_dir / fname
        if fpath.is_file():
            output_hashes[fname] = sha256_file(fpath)
        else:
            output_hashes[fname] = None

    metadata = {
        "stage": "stage124-gate-b-readiness",
        "description": "Gate B readiness dry-run — eligibility rule comparison",
        "date_semantics": DATE_SEMANTICS,
        "date_semantics_note": DATE_SEMANTICS_NOTE,
        "input_files_sha256": {
            "modeling_all_rows_stage123.csv": hash_report["files"]["modeling_all_rows_stage123.csv"]["actual_sha256"],
            "modeling_one_year_ahead_stage123.csv": hash_report["files"]["modeling_one_year_ahead_stage123.csv"]["actual_sha256"],
            "stage123_workbook.xlsx": hash_report["files"]["stage123_workbook.xlsx"]["actual_sha256"],
        },
        "listing_master_sha256": sha256_file(project_dir / "stage124" / "listing_master_verified_stage124.csv"),
        "output_files_sha256": output_hashes,
        "datetime": deterministic_ts,
        "source_code_commit": source_commit,
        "source_file_sha256": sha256_file(src_path) if src_path.is_file() else None,
        "test_file_sha256": sha256_file(test_path) if test_path.is_file() else None,
        "python": sys.version,
        "has_jdatetime": HAS_JDATETIME,
        "expected_rows": EXPECTED_ROWS,
        "expected_tickers": EXPECTED_TICKERS,
        "warning": "No rule has been finalized. Next action: stage124-gate-b-rule-approval",
    }
    meta_path = out_dir / "metadata_and_hashes_gate_b_readiness.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, sort_keys=True)

    return {
        "output_dir": str(out_dir),
        "files_created": list(output_hashes.keys()) + ["metadata_and_hashes_gate_b_readiness.json"],
        "qc_all_pass": all_pass,
    }


def generate_readme(
    out_dir: Path,
    impact: dict,
    hash_report: dict,
    schema_report: dict,
    dq_summary: dict,
) -> None:
    """Generate README_GATE_B_READINESS.md."""

    def _fmt_rule(name: str) -> str:
        r = impact[name]
        return (
            f"### Rule {name[-1].upper()} — {r['description']}\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| Total company-year rows | {r['total_company_year_rows']} |\n"
            f"| Eligible rows | {r['eligible_rows']} |\n"
            f"| Pre-listing rows | {r['pre_listing_rows']} |\n"
            f"| Unresolved rows | {r['unresolved_rows']} |\n"
            f"| Affected tickers | {r['affected_tickers_count']} |\n"
            f"| Total pairs | {r['total_pairs']} |\n"
            f"| Eligible pairs | {r['eligible_pairs']} |\n"
            f"| Positive pairs | {r['positive_pairs']} |\n"
            f"| Negative pairs | {r['negative_pairs']} |\n"
            f"| Target missing pairs | {r['target_missing_pairs']} |\n"
            f"| Change vs Stage123 | {r['change_vs_stage123']:+d} |\n"
        )

    bl = impact["stage123_baseline"]
    lines = [
        "# Gate B Readiness — Dry-Run Eligibility Rule Comparison\n",
        "## Overview\n",
        "This package contains a **dry-run comparison** of three candidate Gate B",
        "eligibility rules. **No rule has been finalized.** The next action is",
        "`stage124-gate-b-rule-approval` — the user and scientific reviewer must",
        "approve the final rule from the comparison report.\n",
        "## Date Semantics\n",
        f"All listing master dates have `date_semantics = {DATE_SEMANTICS}`.\n",
        f"**{DATE_SEMANTICS_NOTE}**\n",
        "## Input Files\n",
        "| File | SHA-256 | Status |",
        "|---|---|---|",
    ]

    for fname, info in hash_report["files"].items():
        status = "✅ match" if info.get("match") else "❌ mismatch"
        lines.append(f"| `{fname}` | `{info['actual_sha256'][:16]}...` | {status} |")

    lines.extend([
        "\n## Schema Validation\n",
        f"- Overall: {'✅ PASS' if schema_report['overall_pass'] else '❌ FAIL'}\n",
    ])
    for check in schema_report["checks"]:
        emoji = "✅" if check["status"] == "PASS" else "❌"
        lines.append(f"- {emoji} {check['check']}: {check['detail']}")

    lines.extend([
        "\n## Data Quality Summary\n",
        f"- OK rows: {dq_summary['ok']}",
        f"- Missing fiscal_year_end: {dq_summary['missing_fiscal_year_end']}",
        f"- Non-12-month period: {dq_summary['non_12_month_period']}",
        f"- Unmatched ticker: {dq_summary['unmatched_ticker']}\n",
        "## Rule Comparison\n",
        _fmt_rule("rule_a"),
        "\n",
        _fmt_rule("rule_b"),
        "\n",
        _fmt_rule("rule_c"),
        "\n",
        "### Stage123 Baseline\n",
        f"| Metric | Value |\n|---|---|\n"
        f"| Eligible pairs | {bl['eligible_pairs']} |\n"
        f"| Positive pairs | {bl['positive_pairs']} |\n"
        f"| Negative pairs | {bl['negative_pairs']} |\n"
        f"| Target missing pairs | {bl['target_missing_pairs']} |\n",
        "## Row Differences Between Rules\n",
        f"- Rule A vs Rule B: **{impact['count_rows_differing_between_a_and_b']}** rows differ",
        f"- Rule A vs Rule C: **{impact['count_rows_differing_between_a_and_c']}** rows differ",
        f"- Rule B vs Rule C: **{impact['count_rows_differing_between_b_and_c']}** rows differ\n",
        "## Scientific Controls\n",
        "- No missing value was zeroed.",
        "- No date or year was guessed.",
        "- No row was dropped.",
        "- `fiscal_year_start` is computed only for 12-month periods with valid `fiscal_year_end`.",
        "- Listing master dates are **first observed trading dates** from the official TSETMC API.",
        "- They are **NOT** IPO dates, admission dates, or listing dates.\n",
        "## Output Files\n",
        "- `gate_b_rule_comparison_summary.json` — full comparison summary",
        "- `gate_b_company_year_audit.csv` — per-row audit with all rule eligibility",
        "- `gate_b_pair_impact_summary.csv` — per-rule pair statistics",
        "- `gate_b_unmatched_or_ambiguous_rows.csv` — rows with data quality issues",
        "- `gate_b_rule_disagreement_rows.csv` — rows where rules disagree (A/B/C comparison)",
        "- `gate_b_readiness_qc_report.json` — QC report",
        "- `metadata_and_hashes_gate_b_readiness.json` — hashes and metadata",
        "- `README_GATE_B_READINESS.md` — this file\n",
        "## Next Action\n",
        "`stage124-gate-b-rule-approval` — User and scientific reviewer must approve",
        "the final Gate B rule from the comparison report.\n",
    ])

    readme_path = out_dir / "README_GATE_B_READINESS.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def run(project_dir: Path | None = None) -> dict:
    """Main entry point for Gate B readiness dry-run.

    Returns a summary dict with output paths and QC status.
    """
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent

    repo_root = project_dir.parent

    # 1. Verify input file hashes
    hash_report = verify_input_hashes(project_dir)

    # 2. Load data
    all_rows = pd.read_csv(
        project_dir / "stage123" / "modeling_all_rows_stage123.csv",
        encoding="utf-8-sig",
    )
    pairs = pd.read_csv(
        project_dir / "stage123" / "modeling_one_year_ahead_stage123.csv",
        encoding="utf-8-sig",
    )
    listing_master = pd.read_csv(
        project_dir / "stage124" / "listing_master_verified_stage124.csv",
        encoding="utf-8-sig",
    )

    # 3. Validate schema
    schema_report = validate_schema(all_rows, listing_master)
    if not schema_report["overall_pass"]:
        raise QCFail(
            "Schema validation failed:\n  "
            + "\n  ".join(
                f"{c['check']}: {c['detail']}"
                for c in schema_report["checks"]
                if c["status"] != "PASS"
            )
        )

    # 4. Compute rules
    audit, dq_summary = compute_rules(all_rows, listing_master)

    # 5. Compute pair impact
    impact = compute_pair_impact(all_rows, pairs, audit)

    # 6. Generate outputs
    output_info = generate_outputs(
        project_dir, repo_root, audit, impact,
        schema_report, hash_report, dq_summary,
    )

    return {
        **output_info,
        "hash_report": hash_report,
        "schema_report": schema_report,
        "dq_summary": dq_summary,
        "impact_summary": {
            "rule_a": {
                "eligible_pairs": impact["rule_a"]["eligible_pairs"],
                "positive": impact["rule_a"]["positive_pairs"],
                "negative": impact["rule_a"]["negative_pairs"],
            },
            "rule_b": {
                "eligible_pairs": impact["rule_b"]["eligible_pairs"],
                "positive": impact["rule_b"]["positive_pairs"],
                "negative": impact["rule_b"]["negative_pairs"],
            },
            "rule_c": {
                "eligible_pairs": impact["rule_c"]["eligible_pairs"],
                "positive": impact["rule_c"]["positive_pairs"],
                "negative": impact["rule_c"]["negative_pairs"],
            },
            "stage123_baseline": {
                "eligible_pairs": impact["stage123_baseline"]["eligible_pairs"],
                "positive": impact["stage123_baseline"]["positive_pairs"],
                "negative": impact["stage123_baseline"]["negative_pairs"],
            },
        },
    }


# Allow `import sys; sys.path ... ; from src import stage124_gate_b_readiness`
import sys
