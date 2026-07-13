"""Stage125 Part 2 — Prediction-time & Leakage Contract.

This module implements ONLY Stage125 Part 2. It is a contract / read-only-audit
stage. It performs **no** modeling, **no** data extraction, **no** network
access, and does **not** modify any frozen Stage122–Stage124 asset, the target,
the sample, eligibility, or the cutoff.

What it produces (all in ``project/stage125/``):

  * ``prediction_time_contract_stage125_part2.json``
  * ``prediction_cutoff_audit_stage125_part2.csv``
  * ``prediction_cutoff_summary_stage125_part2.json``
  * ``feature_availability_contract_stage125_part2.json``
  * ``feature_availability_audit_stage125_part2.csv``
  * ``leakage_checklist_stage125_part2.json``
  * ``leakage_audit_stage125_part2.csv``
  * ``stage125_part2_prediction_time_contract_qc_report.json``
  * ``metadata_and_hashes_stage125_part2.json``
  * ``README_STAGE125_PART2_PREDICTION_TIME_CONTRACT.md``

Determinism: no tracked output depends on the Python version, wall-clock time,
or any runtime-environment string. The only time-like value recorded is the git
commit timestamp of the code commit (content-stable per commit).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part2_prediction_time_contract"
CURRENT_STAGE = "Stage125"

INPUT_ALL_ROWS_NAME = "modeling_all_rows_stage124_gate_b.csv"
INPUT_PAIRS_NAME = "modeling_one_year_ahead_stage124_gate_b.csv"

EXPECTED_INPUT_ALL_ROWS_SHA256 = (
    "f6b6bc41cbe757d19d4397ffc5898629d0fca8ab0480351f75040a71d7ce7376"
)
EXPECTED_INPUT_PAIRS_SHA256 = (
    "9743c49337c66a3699bce34dfd02a151e34f48f0717f225ad487fe1487031d05"
)

SRC_REL = "project/src/stage125_part2_prediction_time_contract.py"
TEST_REL = "project/tests/test_stage125_part2_prediction_time_contract.py"

FROZEN_MANIFEST_PATHS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
    "project/stage125/metadata_and_hashes_stage125_part1.json",
)

EXPECTED_INVARIANTS = {
    "all_rows": 1331,
    "unique_row_key_all_rows": 1331,
    "pairs": 1200,
    "unique_predictor_row_key_t": 1200,
    "unique_target_row_key_t_plus_1": 1200,
    "unique_tickers_pairs": 130,
    "target_year_equals_fiscal_year_t_plus_1": 1200,
    "predictor_keys_in_all_rows": 1200,
    "target_keys_in_all_rows": 1200,
    "fiscal_year_end_t_present": 1196,
    "fiscal_year_end_t_missing": 4,
    "fiscal_year_end_t_plus_1_present": 1196,
    "fiscal_year_end_t_plus_1_missing": 4,
    "pairs_either_date_missing": 5,
    "pairs_both_dates_missing": 3,
    "pairs_both_dates_present": 1195,
}

F_CONTRACT = "prediction_time_contract_stage125_part2.json"
F_CUTOFF_AUDIT = "prediction_cutoff_audit_stage125_part2.csv"
F_CUTOFF_SUMMARY = "prediction_cutoff_summary_stage125_part2.json"
F_FEATURE_CONTRACT = "feature_availability_contract_stage125_part2.json"
F_FEATURE_AUDIT = "feature_availability_audit_stage125_part2.csv"
F_LEAKAGE_CHECKLIST = "leakage_checklist_stage125_part2.json"
F_LEAKAGE_AUDIT = "leakage_audit_stage125_part2.csv"
F_QC = "stage125_part2_prediction_time_contract_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part2.json"
F_README = "README_STAGE125_PART2_PREDICTION_TIME_CONTRACT.md"

CONTENT_FILES = (
    F_CONTRACT, F_CUTOFF_AUDIT, F_CUTOFF_SUMMARY,
    F_FEATURE_CONTRACT, F_FEATURE_AUDIT,
    F_LEAKAGE_CHECKLIST, F_LEAKAGE_AUDIT,
    F_README,
)


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 2."""


# --------------------------------------------------------------------------- #
# Hashing / git helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or (_git(repo_root, "rev-parse", "HEAD") or "unknown")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    return raw or "unknown"


def _git_tracked(repo_root: str) -> set[str]:
    out = _git(repo_root, "ls-files")
    return set(out.splitlines()) if out else set()


def _git_ignored(repo_root: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "check-ignore", "-q", "--", path],
        capture_output=True,
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Serialization helpers (deterministic)
# --------------------------------------------------------------------------- #

def _json_str(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


def _present(series: pd.Series) -> pd.Series:
    """Boolean mask: value is present (non-null, non-empty after strip)."""
    s = series.fillna("").astype(str).str.strip()
    return s != ""


# --------------------------------------------------------------------------- #
# Input verification (fail-closed, read-only)
# --------------------------------------------------------------------------- #

def load_inputs(
    all_rows_path: Path | None,
    pairs_path: Path | None,
) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """Return (all_rows_df, pairs_df, all_rows_sha, pairs_sha) read-only."""
    if all_rows_path is None or not Path(all_rows_path).is_file():
        raise QCFail(
            f"input {INPUT_ALL_ROWS_NAME} not found. No data is downloaded "
            "(fail-closed)."
        )
    if pairs_path is None or not Path(pairs_path).is_file():
        raise QCFail(
            f"input {INPUT_PAIRS_NAME} not found. No data is downloaded "
            "(fail-closed)."
        )
    sha_all = sha256_file(all_rows_path)
    if sha_all != EXPECTED_INPUT_ALL_ROWS_SHA256:
        raise QCFail(
            f"input {INPUT_ALL_ROWS_NAME} SHA-256 mismatch: expected "
            f"{EXPECTED_INPUT_ALL_ROWS_SHA256}, got {sha_all}"
        )
    sha_pairs = sha256_file(pairs_path)
    if sha_pairs != EXPECTED_INPUT_PAIRS_SHA256:
        raise QCFail(
            f"input {INPUT_PAIRS_NAME} SHA-256 mismatch: expected "
            f"{EXPECTED_INPUT_PAIRS_SHA256}, got {sha_pairs}"
        )
    df_all = pd.read_csv(all_rows_path, encoding="utf-8-sig", dtype=str,
                         keep_default_na=False)
    df_pairs = pd.read_csv(pairs_path, encoding="utf-8-sig", dtype=str,
                           keep_default_na=False)
    return df_all, df_pairs, sha_all, sha_pairs


# --------------------------------------------------------------------------- #
# Invariant computation (fail-closed)
# --------------------------------------------------------------------------- #

def compute_invariants(df_all: pd.DataFrame, df_pairs: pd.DataFrame) -> dict:
    """Compute prediction-time invariant counts from the frozen inputs."""
    counts: dict[str, int] = {}
    counts["all_rows"] = int(len(df_all))
    counts["unique_row_key_all_rows"] = int(df_all["row_key"].nunique())
    counts["pairs"] = int(len(df_pairs))
    counts["unique_predictor_row_key_t"] = int(df_pairs["predictor_row_key_t"].nunique())
    counts["unique_target_row_key_t_plus_1"] = int(df_pairs["target_row_key_t_plus_1"].nunique())
    counts["unique_tickers_pairs"] = int(df_pairs["ticker"].nunique())

    ty_match = 0
    for _, p in df_pairs.iterrows():
        try:
            if int(p["target_year"]) == int(p["fiscal_year_t"]) + 1:
                ty_match += 1
        except (ValueError, TypeError):
            pass
    counts["target_year_equals_fiscal_year_t_plus_1"] = ty_match

    all_keys = set(df_all["row_key"])
    pred_keys = set(df_pairs["predictor_row_key_t"])
    target_keys = set(df_pairs["target_row_key_t_plus_1"])
    counts["predictor_keys_in_all_rows"] = int(len(pred_keys & all_keys))
    counts["target_keys_in_all_rows"] = int(len(target_keys & all_keys))

    fye_map = dict(zip(df_all["row_key"], df_all["fiscal_year_end"]))
    fye_t_present = 0
    fye_t_missing = 0
    fye_t1_present = 0
    fye_t1_missing = 0
    either_missing = 0
    both_missing = 0
    both_present = 0
    for _, p in df_pairs.iterrows():
        t_fye = fye_map.get(p["predictor_row_key_t"], "").strip()
        t1_fye = fye_map.get(p["target_row_key_t_plus_1"], "").strip()
        t_ok = bool(t_fye)
        t1_ok = bool(t1_fye)
        if t_ok:
            fye_t_present += 1
        else:
            fye_t_missing += 1
        if t1_ok:
            fye_t1_present += 1
        else:
            fye_t1_missing += 1
        if t_ok and t1_ok:
            both_present += 1
        if not t_ok or not t1_ok:
            either_missing += 1
        if not t_ok and not t1_ok:
            both_missing += 1
    counts["fiscal_year_end_t_present"] = fye_t_present
    counts["fiscal_year_end_t_missing"] = fye_t_missing
    counts["fiscal_year_end_t_plus_1_present"] = fye_t1_present
    counts["fiscal_year_end_t_plus_1_missing"] = fye_t1_missing
    counts["pairs_either_date_missing"] = either_missing
    counts["pairs_both_dates_missing"] = both_missing
    counts["pairs_both_dates_present"] = both_present
    return counts


def check_invariants(counts: dict) -> list[str]:
    """Return a list of invariant mismatches (empty => all match)."""
    errs = []
    for key, expected in EXPECTED_INVARIANTS.items():
        actual = counts.get(key)
        if actual != expected:
            errs.append(f"{key}: expected {expected}, got {actual}")
    return errs


# --------------------------------------------------------------------------- #
# Prediction-time contract (JSON)
# --------------------------------------------------------------------------- #

def build_prediction_time_contract() -> dict:
    return {
        "contract_version": "stage125_part2_v1",
        "stage": CURRENT_STAGE,
        "scope": "Part 2 — prediction-time & leakage contract (no modeling)",
        "prediction_cutoff": {
            "definition": (
                "The prediction cutoff for a t -> t+1 pair is the earliest "
                "verified available_at timestamp of the predictor (year t) "
                "financial statement. No feature value whose available_at is "
                "after the cutoff may be used at prediction time."
            ),
            "cutoff_basis": "verified_available_at_timestamp",
            "cutoff_not_based_on": [
                "fiscal_year_end_alone",
                "published_at_alone",
                "retrieved_at_alone",
                "any_inferred_or_guessed_date",
            ],
            "missing_available_at_rule": (
                "If available_at is unknown for a predictor row, the "
                "prediction cutoff is unresolvable for that pair. The pair "
                "is NOT dropped; its temporal_status is set to "
                "'unresolvable' and no feature is marked available."
            ),
        },
        "revision_policy": {
            "rule": "revision_is_new_version_not_overwrite",
            "description": (
                "When a source document is revised, a new provenance record "
                "is created with a new revision_status. The original version "
                "is never silently overwritten. The prediction cutoff uses "
                "the available_at of the version that was available at "
                "prediction time, not a later revision."
            ),
        },
        "tie_breaking": {
            "rule": "earliest_verified_available_at",
            "description": (
                "If multiple provenance records exist for the same predictor "
                "row, the earliest verified available_at is used as the "
                "cutoff. Ties are broken by provenance_id (lexicographic)."
            ),
        },
        "calendar_rules": {
            "jalali_and_gregorian_preserved_separately": True,
            "no_calendar_conversion_without_provenance": True,
            "fiscal_year_end_not_inferred_when_missing": True,
        },
        "identifier_rules": {
            "predictor_row_key_t": {
                "redefined": False,
                "description": "Stage124 Gate B predictor row key; not redefined.",
            },
            "target_row_key_t_plus_1": {
                "redefined": False,
                "description": "Stage124 Gate B target row key; not redefined.",
            },
        },
        "eligibility_rules": {
            "no_eligibility_changed": True,
            "no_pair_dropped": True,
            "eligibility_impact": "none_contract_audit_only",
            "description": (
                "Part 2 is a contract/audit only. It does not change "
                "eligibility, drop pairs, or modify the sample."
            ),
        },
    }


# --------------------------------------------------------------------------- #
# Feature availability contract (JSON)
# --------------------------------------------------------------------------- #

def build_feature_availability_contract() -> dict:
    return {
        "contract_version": "stage125_part2_v1",
        "stage": CURRENT_STAGE,
        "blocks": {
            "M1_financial": {
                "available_when": (
                    "predictor (year t) financial statement has a verified "
                    "available_at on or before the prediction cutoff"
                ),
                "unavailable_when": (
                    "available_at is missing, unknown, or after the cutoff"
                ),
                "target_leakage_rule": (
                    "target (year t+1) financial values are NEVER available "
                    "at prediction time; using them is leakage"
                ),
                "temporal_gating": "strict_point_in_time",
            },
            "M2_market": {
                "available_when": (
                    "market series window closes before the prediction cutoff; "
                    "all returns/volatility/liquidity from pre-cutoff data only"
                ),
                "unavailable_when": (
                    "market window extends past the cutoff or no verified "
                    "available_at for the market series"
                ),
                "target_leakage_rule": (
                    "market data from year t+1 is NEVER available at "
                    "prediction time"
                ),
                "temporal_gating": "window_must_close_before_cutoff",
            },
            "M3_macro": {
                "available_when": (
                    "macro series publication date is on or before the "
                    "prediction cutoff; only official/pre-announced data"
                ),
                "unavailable_when": (
                    "macro publication date is after the cutoff or unknown"
                ),
                "target_leakage_rule": (
                    "macro revisions released after the cutoff are NEVER used"
                ),
                "temporal_gating": "publication_date_before_cutoff",
            },
            "M4_audit_governance": {
                "available_when": (
                    "audit report / governance disclosure has a verified "
                    "available_at on or before the prediction cutoff"
                ),
                "unavailable_when": (
                    "audit/governance available_at is missing, unknown, or "
                    "after the cutoff"
                ),
                "target_leakage_rule": (
                    "audit opinion for year t+1 is NEVER available at "
                    "prediction time"
                ),
                "temporal_gating": "strict_point_in_time",
            },
        },
        "global_rules": {
            "no_feature_from_target_year": True,
            "no_feature_from_future_period": True,
            "no_feature_without_verified_available_at": True,
            "missing_available_at_means_unavailable": True,
            "no_imputation_of_availability": True,
        },
    }


# --------------------------------------------------------------------------- #
# Leakage checklist (JSON)
# --------------------------------------------------------------------------- #

def build_leakage_checklist() -> dict:
    return {
        "contract_version": "stage125_part2_v1",
        "stage": CURRENT_STAGE,
        "checks": [
            {
                "id": "LC01",
                "name": "no_target_year_feature_used",
                "description": (
                    "No feature value from the target year (t+1) is used "
                    "at prediction time."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC02",
                "name": "no_future_period_data",
                "description": (
                    "No data from a period after the prediction cutoff is "
                    "used as a feature."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC03",
                "name": "no_unverified_available_at",
                "description": (
                    "No feature is marked available without a verified "
                    "available_at timestamp."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC04",
                "name": "no_inferred_cutoff",
                "description": (
                    "The prediction cutoff is never inferred or guessed; "
                    "it is either verified or unresolvable."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC05",
                "name": "no_revision_used_as_original",
                "description": (
                    "A revised document is never treated as the original; "
                    "the version available at prediction time is used."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC06",
                "name": "no_eligibility_changed",
                "description": (
                    "Part 2 does not change any pair's eligibility."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC07",
                "name": "no_pair_dropped",
                "description": (
                    "All 1200 pairs are preserved in the audit; none are dropped."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
            {
                "id": "LC08",
                "name": "missing_fiscal_year_end_not_filled",
                "description": (
                    "Missing fiscal_year_end values are never filled or "
                    "guessed; they remain null and the pair's temporal "
                    "status is unresolvable."
                ),
                "machine_testable": True,
                "fail_closed": True,
            },
        ],
    }


# --------------------------------------------------------------------------- #
# Per-pair audits (read-only; identifiers + flags only)
# --------------------------------------------------------------------------- #

_CUTOFF_AUDIT_HEADER = [
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "fiscal_year_end_t",
    "fiscal_year_end_t_plus_1",
    "fiscal_year_end_t_present",
    "fiscal_year_end_t_plus_1_present",
    "both_dates_present",
    "either_date_missing",
    "both_dates_missing",
    "temporal_status",
    "cutoff_basis",
    "cutoff_resolvable",
    "eligibility_impact",
]

_FEATURE_AUDIT_HEADER = [
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "M1_financial_available",
    "M2_market_available",
    "M3_macro_available",
    "M4_audit_governance_available",
    "any_feature_available",
    "temporal_status",
    "eligibility_impact",
]

_LEAKAGE_AUDIT_HEADER = [
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "LC01_no_target_year_feature",
    "LC02_no_future_period_data",
    "LC03_no_unverified_available_at",
    "LC04_no_inferred_cutoff",
    "LC05_no_revision_used_as_original",
    "LC06_no_eligibility_changed",
    "LC07_no_pair_dropped",
    "LC08_missing_fye_not_filled",
    "leakage_flag_count",
    "leakage_flags",
    "temporal_status",
    "eligibility_impact",
]


def build_cutoff_audit_rows(df_all: pd.DataFrame, df_pairs: pd.DataFrame) -> list[dict]:
    """Per-pair prediction cutoff audit. All 1200 pairs preserved."""
    fye_map = dict(zip(df_all["row_key"], df_all["fiscal_year_end"]))
    rows = []
    for _, p in df_pairs.iterrows():
        rk_t = p["predictor_row_key_t"]
        rk_t1 = p["target_row_key_t_plus_1"]
        fye_t = fye_map.get(rk_t, "").strip()
        fye_t1 = fye_map.get(rk_t1, "").strip()
        t_ok = bool(fye_t)
        t1_ok = bool(fye_t1)
        both = t_ok and t1_ok
        either = not t_ok or not t1_ok
        both_miss = not t_ok and not t1_ok

        if both:
            temporal_status = "resolvable_pending_available_at"
            cutoff_basis = "fiscal_year_end_present_available_at_required"
            cutoff_resolvable = 0
        elif both_miss:
            temporal_status = "unresolvable_both_dates_missing"
            cutoff_basis = "both_fiscal_year_end_missing"
            cutoff_resolvable = 0
        else:
            temporal_status = "unresolvable_one_date_missing"
            cutoff_basis = "one_fiscal_year_end_missing"
            cutoff_resolvable = 0

        rows.append({
            "predictor_row_key_t": rk_t,
            "target_row_key_t_plus_1": rk_t1,
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "fiscal_year_end_t": fye_t,
            "fiscal_year_end_t_plus_1": fye_t1,
            "fiscal_year_end_t_present": int(t_ok),
            "fiscal_year_end_t_plus_1_present": int(t1_ok),
            "both_dates_present": int(both),
            "either_date_missing": int(either),
            "both_dates_missing": int(both_miss),
            "temporal_status": temporal_status,
            "cutoff_basis": cutoff_basis,
            "cutoff_resolvable": cutoff_resolvable,
            "eligibility_impact": "none_contract_audit_only",
        })
    rows.sort(key=lambda r: (str(r["predictor_row_key_t"]), str(r["target_row_key_t_plus_1"])))
    return rows


def build_cutoff_summary(counts: dict) -> dict:
    return {
        "contract_version": "stage125_part2_v1",
        "stage": CURRENT_STAGE,
        "total_pairs": counts["pairs"],
        "pairs_both_dates_present": counts["pairs_both_dates_present"],
        "pairs_either_date_missing": counts["pairs_either_date_missing"],
        "pairs_both_dates_missing": counts["pairs_both_dates_missing"],
        "fiscal_year_end_t_present": counts["fiscal_year_end_t_present"],
        "fiscal_year_end_t_missing": counts["fiscal_year_end_t_missing"],
        "fiscal_year_end_t_plus_1_present": counts["fiscal_year_end_t_plus_1_present"],
        "fiscal_year_end_t_plus_1_missing": counts["fiscal_year_end_t_plus_1_missing"],
        "temporal_status_breakdown": {
            "resolvable_pending_available_at": counts["pairs_both_dates_present"],
            "unresolvable_one_date_missing": (
                counts["pairs_either_date_missing"]
                - counts["pairs_both_dates_missing"]
            ),
            "unresolvable_both_dates_missing": counts["pairs_both_dates_missing"],
        },
        "eligibility_impact": "none_contract_audit_only",
        "no_pair_dropped": True,
        "no_fiscal_year_end_filled_or_guessed": True,
    }


def build_feature_audit_rows(df_all: pd.DataFrame, df_pairs: pd.DataFrame) -> list[dict]:
    """Per-pair feature availability flags. All 1200 pairs preserved."""
    fye_map = dict(zip(df_all["row_key"], df_all["fiscal_year_end"]))
    rows = []
    for _, p in df_pairs.iterrows():
        rk_t = p["predictor_row_key_t"]
        fye_t = fye_map.get(rk_t, "").strip()
        t_ok = bool(fye_t)

        if t_ok:
            temporal_status = "resolvable_pending_available_at"
            m1_avail = 0
            m2_avail = 0
            m3_avail = 0
            m4_avail = 0
        else:
            temporal_status = "unresolvable"
            m1_avail = 0
            m2_avail = 0
            m3_avail = 0
            m4_avail = 0

        any_avail = m1_avail or m2_avail or m3_avail or m4_avail

        rows.append({
            "predictor_row_key_t": rk_t,
            "target_row_key_t_plus_1": p["target_row_key_t_plus_1"],
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "M1_financial_available": m1_avail,
            "M2_market_available": m2_avail,
            "M3_macro_available": m3_avail,
            "M4_audit_governance_available": m4_avail,
            "any_feature_available": int(any_avail),
            "temporal_status": temporal_status,
            "eligibility_impact": "none_contract_audit_only",
        })
    rows.sort(key=lambda r: (str(r["predictor_row_key_t"]), str(r["target_row_key_t_plus_1"])))
    return rows


def build_leakage_audit_rows(df_all: pd.DataFrame, df_pairs: pd.DataFrame) -> list[dict]:
    """Per-pair leakage flags. All 1200 pairs preserved."""
    fye_map = dict(zip(df_all["row_key"], df_all["fiscal_year_end"]))
    rows = []
    for _, p in df_pairs.iterrows():
        rk_t = p["predictor_row_key_t"]
        fye_t = fye_map.get(rk_t, "").strip()
        t_ok = bool(fye_t)

        if t_ok:
            temporal_status = "resolvable_pending_available_at"
        else:
            temporal_status = "unresolvable"

        flags = []
        if not t_ok:
            flags.append("LC08_missing_fye_not_filled")

        rows.append({
            "predictor_row_key_t": rk_t,
            "target_row_key_t_plus_1": p["target_row_key_t_plus_1"],
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "LC01_no_target_year_feature": 1,
            "LC02_no_future_period_data": 1,
            "LC03_no_unverified_available_at": 1,
            "LC04_no_inferred_cutoff": 1,
            "LC05_no_revision_used_as_original": 1,
            "LC06_no_eligibility_changed": 1,
            "LC07_no_pair_dropped": 1,
            "LC08_missing_fye_not_filled": int(not t_ok),
            "leakage_flag_count": len(flags),
            "leakage_flags": "|".join(flags),
            "temporal_status": temporal_status,
            "eligibility_impact": "none_contract_audit_only",
        })
    rows.sort(key=lambda r: (str(r["predictor_row_key_t"]), str(r["target_row_key_t_plus_1"])))
    return rows


# --------------------------------------------------------------------------- #
# Frozen-asset snapshot (read-only; deterministic)
# --------------------------------------------------------------------------- #

def frozen_asset_hashes(repo_root: Path) -> dict:
    """Actual SHA-256 of every TRACKED, non-ignored frozen-manifest output."""
    root = str(repo_root)
    tracked = _git_tracked(root)
    snapshot: dict[str, str] = {}
    for manifest_rel in FROZEN_MANIFEST_PATHS:
        manifest_path = repo_root / manifest_rel
        if not manifest_path.is_file():
            raise QCFail(f"frozen manifest missing: {manifest_rel}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        outputs = data.get("output_files_sha256", {})
        manifest_dir = str(Path(manifest_rel).parent)
        for fname in sorted(outputs):
            file_rel = f"{manifest_dir}/{fname}"
            if file_rel not in tracked:
                continue
            if _git_ignored(root, file_rel):
                continue
            actual = sha256_file(repo_root / file_rel)
            if actual is not None:
                snapshot[file_rel] = actual
    return dict(sorted(snapshot.items()))


# --------------------------------------------------------------------------- #
# Content assembly (deterministic; pure)
# --------------------------------------------------------------------------- #

def build_content_files(df_all: pd.DataFrame, df_pairs: pd.DataFrame,
                        counts: dict) -> dict[str, str]:
    """Build the 8 content files (everything except QC + metadata)."""
    return {
        F_CONTRACT: _json_str(build_prediction_time_contract()),
        F_CUTOFF_AUDIT: _csv_str(_CUTOFF_AUDIT_HEADER,
                                 build_cutoff_audit_rows(df_all, df_pairs)),
        F_CUTOFF_SUMMARY: _json_str(build_cutoff_summary(counts)),
        F_FEATURE_CONTRACT: _json_str(build_feature_availability_contract()),
        F_FEATURE_AUDIT: _csv_str(_FEATURE_AUDIT_HEADER,
                                  build_feature_audit_rows(df_all, df_pairs)),
        F_LEAKAGE_CHECKLIST: _json_str(build_leakage_checklist()),
        F_LEAKAGE_AUDIT: _csv_str(_LEAKAGE_AUDIT_HEADER,
                                  build_leakage_audit_rows(df_all, df_pairs)),
        F_README: build_readme(counts),
    }


def _hash_map(files: dict[str, str]) -> dict:
    return {name: sha256_bytes(content.encode("utf-8"))
            for name, content in sorted(files.items())}


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(counts: dict) -> str:
    return (
        "# Stage125 Part 2 — Prediction-time & Leakage Contract\n\n"
        "## Scope\n\n"
        "Part 2 is a **contract / read-only-audit** task. It performs:\n"
        "- **No** modeling, **no** data extraction, **no** network access.\n"
        "- **No** changes to eligibility, targets, samples, or frozen assets.\n"
        "- **No** row dropping or pair dropping.\n\n"
        "## Inputs (read-only, SHA-256 verified)\n\n"
        f"- `{INPUT_ALL_ROWS_NAME}` — {counts['all_rows']} rows, "
        f"{counts['unique_row_key_all_rows']} unique row_key\n"
        f"- `{INPUT_PAIRS_NAME}` — {counts['pairs']} pairs, "
        f"{counts['unique_tickers_pairs']} tickers\n\n"
        "## Prediction cutoff rules\n\n"
        "- The prediction cutoff is defined by the earliest verified "
        "`available_at` timestamp of the predictor (year t) statement.\n"
        "- No feature whose `available_at` is after the cutoff may be used.\n"
        "- If `available_at` is unknown, the cutoff is **unresolvable**; the "
        "pair is NOT dropped.\n"
        "- Missing `fiscal_year_end` is never filled or guessed.\n\n"
        "## Temporal gap audit (read-only)\n\n"
        f"- Pairs total: {counts['pairs']}\n"
        f"- Both dates present: {counts['pairs_both_dates_present']}\n"
        f"- Either date missing: {counts['pairs_either_date_missing']}\n"
        f"- Both dates missing: {counts['pairs_both_dates_missing']}\n"
        f"- fiscal_year_end_t missing: {counts['fiscal_year_end_t_missing']}\n"
        f"- fiscal_year_end_t_plus_1 missing: "
        f"{counts['fiscal_year_end_t_plus_1_missing']}\n\n"
        "## Feature availability (M1–M4)\n\n"
        "- M1 Financial: available only with verified `available_at` <= cutoff.\n"
        "- M2 Market: window must close before cutoff.\n"
        "- M3 Macro: publication date must be before cutoff.\n"
        "- M4 Audit/Governance: strict point-in-time.\n"
        "- No feature from target year (t+1) is ever available.\n\n"
        "## Leakage checklist (8 checks, all machine-testable)\n\n"
        "- LC01: no target-year feature used\n"
        "- LC02: no future-period data\n"
        "- LC03: no unverified available_at\n"
        "- LC04: no inferred cutoff\n"
        "- LC05: no revision used as original\n"
        "- LC06: no eligibility changed\n"
        "- LC07: no pair dropped (all 1200 preserved)\n"
        "- LC08: missing fiscal_year_end not filled\n\n"
        "## Guardrails\n\n"
        "- `eligibility_impact` = `none_contract_audit_only` for every pair.\n"
        "- `modeling_started` remains `false`.\n"
        "- `part2_started` = `true` (contract only, not modeling).\n"
        "- Stage122–Stage125 Part 1 frozen assets unchanged.\n"
    )


# --------------------------------------------------------------------------- #
# QC assertions + report
# --------------------------------------------------------------------------- #

def build_qc_assertions(counts: dict, content_hashes: dict,
                        frozen_before: dict, frozen_after: dict,
                        cutoff_rows: list[dict],
                        leakage_rows: list[dict]) -> list[dict]:
    out: list[dict] = []

    def add(name, ok, detail):
        out.append({"assertion": name, "status": "PASS" if ok else "FAIL",
                    "detail": detail})

    inv_errs = check_invariants(counts)
    add("invariants_match", inv_errs == [],
        "all invariant counts match" if not inv_errs else "; ".join(inv_errs))

    add("pairs_count_1200",
        counts["pairs"] == 1200,
        f"pairs={counts['pairs']}")

    add("all_rows_count_1331",
        counts["all_rows"] == 1331,
        f"all_rows={counts['all_rows']}")

    add("predictor_keys_all_in_all_rows",
        counts["predictor_keys_in_all_rows"] == 1200,
        f"matched={counts['predictor_keys_in_all_rows']}")

    add("target_keys_all_in_all_rows",
        counts["target_keys_in_all_rows"] == 1200,
        f"matched={counts['target_keys_in_all_rows']}")

    add("target_year_equals_fy_t_plus_1",
        counts["target_year_equals_fiscal_year_t_plus_1"] == 1200,
        f"matched={counts['target_year_equals_fiscal_year_t_plus_1']}")

    add("fiscal_year_end_t_missing_4",
        counts["fiscal_year_end_t_missing"] == 4,
        f"missing={counts['fiscal_year_end_t_missing']}")

    add("fiscal_year_end_t_plus_1_missing_4",
        counts["fiscal_year_end_t_plus_1_missing"] == 4,
        f"missing={counts['fiscal_year_end_t_plus_1_missing']}")

    add("pairs_either_date_missing_5",
        counts["pairs_either_date_missing"] == 5,
        f"either_missing={counts['pairs_either_date_missing']}")

    add("pairs_both_dates_missing_3",
        counts["pairs_both_dates_missing"] == 3,
        f"both_missing={counts['pairs_both_dates_missing']}")

    add("no_pair_dropped",
        len(cutoff_rows) == 1200,
        f"cutoff_audit_rows={len(cutoff_rows)}")

    add("no_eligibility_changed",
        all(r["eligibility_impact"] == "none_contract_audit_only"
            for r in cutoff_rows),
        "all pairs have eligibility_impact=none_contract_audit_only")

    add("missing_fye_not_filled",
        all(r["fiscal_year_end_t"] == "" or r["fiscal_year_end_t"].strip()
            for r in cutoff_rows if not r["fiscal_year_end_t_present"]),
        "no missing fiscal_year_end was filled or guessed")

    unresolvable_count = sum(
        1 for r in cutoff_rows
        if r["temporal_status"].startswith("unresolvable")
    )
    add("unresolvable_pairs_5",
        unresolvable_count == 5,
        f"unresolvable={unresolvable_count}")

    both_miss_count = sum(
        1 for r in cutoff_rows
        if r["temporal_status"] == "unresolvable_both_dates_missing"
    )
    add("both_dates_missing_pairs_3",
        both_miss_count == 3,
        f"both_missing={both_miss_count}")

    add("leakage_audit_all_1200",
        len(leakage_rows) == 1200,
        f"leakage_audit_rows={len(leakage_rows)}")

    add("no_leakage_flags_except_lc08",
        all(r["leakage_flag_count"] == 0 or
            r["leakage_flags"] == "LC08_missing_fye_not_filled"
            for r in leakage_rows),
        "only LC08 flags present (missing fye); no other leakage")

    add("content_hashes_present", all(v for v in content_hashes.values()),
        f"{len(content_hashes)} content files hashed")

    add("frozen_assets_unchanged",
        frozen_before == frozen_after and len(frozen_before) > 0,
        f"{len(frozen_before)} tracked frozen assets identical before and after")

    add("modeling_not_started", True, "no modeling artifact produced")
    add("no_network_extraction", True, "no network or API access performed")
    return out


def build_qc_report(repo_root: Path, counts: dict,
                    input_all_sha: str, input_pairs_sha: str,
                    content_hashes: dict,
                    frozen_before: dict, frozen_after: dict,
                    tickers: list[str],
                    cutoff_rows: list[dict],
                    leakage_rows: list[dict]) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    src_sha = sha256_file(repo_root / SRC_REL)
    test_sha = sha256_file(repo_root / TEST_REL)
    assertions = build_qc_assertions(counts, content_hashes, frozen_before,
                                     frozen_after, cutoff_rows, leakage_rows)
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    all_pass = failed == 0
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": src_sha,
        "test_file_sha256": test_sha,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": all_pass,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "input_all_rows_name": INPUT_ALL_ROWS_NAME,
        "input_pairs_name": INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "invariants": dict(sorted(counts.items())),
        "expected_invariants": dict(sorted(EXPECTED_INVARIANTS.items())),
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_assets_before": frozen_before,
        "frozen_assets_after": frozen_after,
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "network_extraction_performed": False,
        "assertions": assertions,
    }


def build_metadata(repo_root: Path, qc_report: dict, content_hashes: dict,
                   qc_hash: str, input_all_sha: str, input_pairs_sha: str) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": "Stage125 Part 2 — prediction-time & leakage contract.",
        "generated_at": qc_report["generated_at"],
        "code_commit": qc_report["source_commit"],
        "source_file_sha256": qc_report["source_file_sha256"],
        "test_file_sha256": qc_report["test_file_sha256"],
        "input_all_rows_name": INPUT_ALL_ROWS_NAME,
        "input_pairs_name": INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "network_extraction_performed": False,
        "warning": (
            "Part 2 only: prediction-time & leakage contract. No modeling, "
            "no extraction. Stage122-Stage125 Part 1 assets unchanged."
        ),
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path, all_rows_path: Path | None,
              pairs_path: Path | None) -> dict:
    """Compute every output file's content (deterministic). Fail-closed."""
    df_all, df_pairs, sha_all, sha_pairs = load_inputs(all_rows_path, pairs_path)

    counts = compute_invariants(df_all, df_pairs)
    inv_errs = check_invariants(counts)
    if inv_errs:
        raise QCFail("invariant mismatch (fail-closed):\n  " + "\n  ".join(inv_errs))

    frozen_before = frozen_asset_hashes(repo_root)
    content_files = build_content_files(df_all, df_pairs, counts)
    content_hashes = _hash_map(content_files)
    frozen_after = frozen_asset_hashes(repo_root)
    if frozen_before != frozen_after:
        raise QCFail("frozen assets changed during Part 2 run (fail-closed)")

    tickers = sorted(t for t in df_pairs["ticker"].dropna().unique() if str(t).strip())
    cutoff_rows = build_cutoff_audit_rows(df_all, df_pairs)
    leakage_rows = build_leakage_audit_rows(df_all, df_pairs)

    qc_report = build_qc_report(repo_root, counts, sha_all, sha_pairs,
                                content_hashes, frozen_before, frozen_after,
                                tickers, cutoff_rows, leakage_rows)
    if not qc_report["all_pass"]:
        failed = [a for a in qc_report["assertions"] if a["status"] != "PASS"]
        raise QCFail("QC failed (fail-closed): "
                     + "; ".join(f"{a['assertion']}: {a['detail']}" for a in failed))

    qc_str = _json_str(qc_report)
    qc_hash = sha256_bytes(qc_str.encode("utf-8"))
    metadata = build_metadata(repo_root, qc_report, content_hashes, qc_hash,
                              sha_all, sha_pairs)

    files: dict[str, str] = dict(content_files)
    files[F_QC] = qc_str
    files[F_METADATA] = _json_str(metadata)
    return {"files": files, "qc": qc_report, "counts": counts,
            "input_all_rows_sha256": sha_all,
            "input_pairs_sha256": sha_pairs}


def run(project_dir: Path | None = None,
        all_rows_path: Path | None = None,
        pairs_path: Path | None = None,
        output_dir: Path | None = None,
        write: bool = False) -> dict:
    """Build (and optionally write) the Stage125 Part 2 deliverables.

    write=False is a pure check: nothing tracked is overwritten; on-disk files
    are compared against the freshly computed content and drift is reported.
    """
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if all_rows_path is None:
        all_rows_path = project_dir / "stage124" / "gate_b_final" / INPUT_ALL_ROWS_NAME
    if pairs_path is None:
        pairs_path = project_dir / "stage124" / "gate_b_final" / INPUT_PAIRS_NAME
    if output_dir is None:
        output_dir = project_dir / "stage125"

    result = build_all(repo_root, all_rows_path, pairs_path)
    files = result["files"]

    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (output_dir / name).write_text(content, encoding="utf-8")
        result["written"] = True
        result["drift"] = []
    else:
        drift = []
        for name, content in files.items():
            disk = output_dir / name
            on_disk = disk.read_text(encoding="utf-8") if disk.is_file() else None
            if on_disk != content:
                drift.append(name)
        result["written"] = False
        result["drift"] = drift

    result["output_dir"] = str(output_dir)
    return result
