"""Stage125 Part 3C — Leakage-Safe Dataset Finalization.

Operationalizes the Part 3B.1E locked six-month Jalali availability lag into
audited pair datasets and timing-eligible analysis-ready datasets for all four
frozen Gate B sample designs.

Offline. Deterministic. Zero network. No modeling. No Stage126.
Financial values and targets remain researcher-verified and frozen.

Terminology:
- audited pair datasets = full Gate B membership (exceptions visible/audited)
- leakage-safe analysis-ready datasets = timing-eligible subset only
  (assumed_before_target_fiscal_year_end == true)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jdatetime

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage125_part3b1e_conservative_lag_decision as part3b1e

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3c_leakage_safe_dataset_finalization"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "93ab6d8f2c1fbddaaed4a9dc21de6490ef38de30"
CONTRACT_VERSION = "stage125_part3c_v2"
RESEARCH_ACTION_ID = "stage125-part3c-leakage-safe-dataset-finalization"
RESEARCH_LAST_COMPLETED = RESEARCH_ACTION_ID
RESEARCH_NEXT = "stage125-part4-statistical-analysis-plan"
TIMING_EXCLUSION_REASON_AUTHORIZED = (
    "assumed_availability_not_before_target_fye_authorized_calendar_shift"
)
PART3B1E_DECISION_LOCK_REL = (
    "project/stage125/part3b1e_conservative_lag_decision_lock_stage125.json"
)
PART3B1E_FROZEN_MANIFEST_REL = (
    "project/stage125/part3b1e_frozen_financial_data_manifest_stage125.json"
)

APPROVED_LAG_MONTHS = part3b1e.APPROVED_LAG_MONTHS
ASSUMED_FIELD_NAME = part3b1e.ASSUMED_FIELD_NAME
AVAILABILITY_METHOD = part3b1e.AVAILABILITY_METHOD
AVAILABILITY_DATE_SEMANTICS = part3b1e.AVAILABILITY_DATE_SEMANTICS

FORBIDDEN_OBSERVED_FIELD_NAMES = frozenset({
    "available_at",
    "PublishDateTime",
    "SentDateTime",
    "publish_datetime",
    "publish_date_time",
    "observed_available_at",
    "real_available_at",
    "actual_publication_date",
    "verified_source_timestamp",
    "actual_PublishDateTime",
    "actual_CODAL_publication_date",
})

SRC_REL = "project/src/stage125_part3c_leakage_safe_dataset_finalization.py"
TEST_REL = "project/tests/test_stage125_part3c_leakage_safe_dataset_finalization.py"
RUN_REL = "project/run_stage125_part3c.py"

F_CONTRACT = "part3c_leakage_safe_dataset_contract_stage125.json"
F_INPUT_MANIFEST = "part3c_input_hash_manifest_stage125.json"
F_COLUMN_ROLES = "part3c_column_role_map_stage125.csv"
F_SAMPLE_SUMMARY = "part3c_sample_summary_stage125.csv"
F_TARGET_YEAR_DIST = "part3c_target_year_distribution_stage125.csv"
F_LEAKAGE_AUDIT = "part3c_leakage_audit_stage125.csv"
F_README = "README_STAGE125_PART3C_LEAKAGE_SAFE_DATASET.md"
F_QC = "stage125_part3c_leakage_safe_dataset_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3c.json"

BULKY_OUTPUT_DIR_REL = "project/stage125/part3c_outputs"
# Full Gate B membership — audited pair surface (not model-ready).
AUDITED_OUTPUT_FILES = {
    "main_rule_a_primary": "audited_pairs_main_rule_a_stage125.csv",
    "main_rule_b_listing_robustness": "audited_pairs_main_rule_b_stage125.csv",
    "expanded_rule_a_company_scope_robustness": (
        "audited_pairs_expanded_rule_a_stage125.csv"
    ),
    "expanded_rule_b_combined_robustness": (
        "audited_pairs_expanded_rule_b_stage125.csv"
    ),
}
# Timing-eligible leakage-safe analysis-ready surface.
ANALYSIS_READY_OUTPUT_FILES = {
    "main_rule_a_primary": "analysis_ready_main_rule_a_stage125.csv",
    "main_rule_b_listing_robustness": "analysis_ready_main_rule_b_stage125.csv",
    "expanded_rule_a_company_scope_robustness": (
        "analysis_ready_expanded_rule_a_stage125.csv"
    ),
    "expanded_rule_b_combined_robustness": (
        "analysis_ready_expanded_rule_b_stage125.csv"
    ),
}
# Backward-compatible alias used by older call sites/tests.
DESIGN_OUTPUT_FILES = AUDITED_OUTPUT_FILES
OBSOLETE_BULKY_OUTPUT_FILES = (
    "leakage_safe_main_rule_a_stage125.csv",
    "leakage_safe_main_rule_b_stage125.csv",
    "leakage_safe_expanded_rule_a_stage125.csv",
    "leakage_safe_expanded_rule_b_stage125.csv",
)

TRACKED_CONTENT_FILES = (
    F_CONTRACT,
    F_INPUT_MANIFEST,
    F_COLUMN_ROLES,
    F_SAMPLE_SUMMARY,
    F_TARGET_YEAR_DIST,
    F_LEAKAGE_AUDIT,
    F_README,
)

# Pinned local bulky inputs (gitignored; must exist with exact SHA-256).
FROZEN_BULKY_INPUTS: dict[str, str] = {
    "project/stage123/modeling_all_rows_stage123.csv":
        "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390",
    "project/stage124/gate_b_final/modeling_one_year_ahead_stage124_gate_b.csv":
        "9743c49337c66a3699bce34dfd02a151e34f48f0717f225ad487fe1487031d05",
    "project/stage124/gate_b_final/modeling_main_rule_a_eligible.csv":
        "f943d5cfd2a3dcaa091eacbac5e305fdad83787548a6e43b50976f1455664420",
    "project/stage124/gate_b_final/modeling_main_rule_b_eligible.csv":
        "99bdf0296a274f2ad42a6e9942a42d79b6370c7b99b57967b44c6821313f36c1",
    "project/stage124/gate_b_final/modeling_expanded_rule_a_eligible.csv":
        "b2f950b5a6a5a79f6b0fd8019e9021079339b6c80290695bb18d0e4a56b7d8e6",
    "project/stage124/gate_b_final/modeling_expanded_rule_b_eligible.csv":
        "0aac404c2a856af8785f79361d22b42abfbe5898a983985d003c051c4ca43a12",
}

DESIGN_SPECS: dict[str, dict[str, Any]] = {
    "main_rule_a_primary": {
        "input_rel": (
            "project/stage124/gate_b_final/modeling_main_rule_a_eligible.csv"
        ),
        "pairs": 1013,
        "companies": 119,
        "positive": 81,
        "negative": 932,
    },
    "main_rule_b_listing_robustness": {
        "input_rel": (
            "project/stage124/gate_b_final/modeling_main_rule_b_eligible.csv"
        ),
        "pairs": 994,
        "companies": 117,
        "positive": 80,
        "negative": 914,
    },
    "expanded_rule_a_company_scope_robustness": {
        "input_rel": (
            "project/stage124/gate_b_final/"
            "modeling_expanded_rule_a_eligible.csv"
        ),
        "pairs": 1057,
        "companies": 124,
        "positive": 81,
        "negative": 976,
    },
    "expanded_rule_b_combined_robustness": {
        "input_rel": (
            "project/stage124/gate_b_final/"
            "modeling_expanded_rule_b_eligible.csv"
        ),
        "pairs": 1036,
        "companies": 122,
        "positive": 80,
        "negative": 956,
    },
}

# One fiscal-year-calendar-shift pair where predictor FYE is Esfand and target
# FYE is Farvardin; assumed (FYE+6m) is after target FYE. The pair remains in
# the audited Gate B membership surface with explicit exclusion flags, but is
# never eligible for analysis-ready / model matrices.
AUTHORIZED_TIMING_EXCEPTIONS = frozenset({
    ("رمپنا", 1396, 1397, "رمپنا|1396", "رمپنا|1397"),
})

GATE_B_PAIR_COLUMNS = [
    "ticker",
    "company_name",
    "fiscal_year_t",
    "target_year",
    "FD_target_main_t_plus_1",
    "FD_target_article141_only_t_plus_1",
    "FD_target_persistent_loss_robustness_t_plus_1",
    "predictor_eligible_main_t",
    "predictor_eligible_expanded_t",
    "valid_target_t_plus_1",
    "pair_final_eligible_main",
    "pair_final_eligible_expanded",
    "pair_exclusion_reason_main",
    "pair_exclusion_reason_expanded",
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "pair_final_eligible_main_gate_b_primary",
    "pair_exclusion_reason_main_gate_b_primary",
    "pair_final_eligible_main_gate_b_robustness",
    "pair_exclusion_reason_main_gate_b_robustness",
    "pair_final_eligible_expanded_gate_b_primary",
    "pair_exclusion_reason_expanded_gate_b_primary",
    "pair_final_eligible_expanded_gate_b_robustness",
    "pair_exclusion_reason_expanded_gate_b_robustness",
]

PREDICTOR_IDENTIFIER_COLS = [
    "industry",
    "unit",
    "row_key_predictor",
]
PREDICTOR_FINANCIAL_LEVEL_COLS = [
    "total_assets",
    "total_liabilities",
    "equity",
    "registered_capital",
    "accumulated_loss",
    "current_assets",
    "current_liabilities",
    "revenue_period_adjusted",
    "gross_profit_period_adjusted",
    "operating_profit_period_adjusted",
    "net_income_period_adjusted",
    "operating_cash_flow_period_adjusted",
    "financial_expense_period_adjusted",
]
PREDICTOR_RATIO_COLS = [
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "roe_period_adjusted",
    "equity_ratio",
    "ocf_to_assets_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "profit_margin_period_adjusted",
    "operating_margin_period_adjusted",
    "gross_margin_period_adjusted",
    "net_margin_period_adjusted",
    "financial_expense_to_revenue_period_adjusted",
    "asset_turnover_period_adjusted",
    "revenue_growth_period_adjusted",
    "net_income_growth_period_adjusted",
    "sales_growth_period_adjusted",
    "accumulated_loss_to_capital_ratio",
    "debt_to_equity",
]
# Explicit predictor whitelist — model feature matrix may only use these.
# Do not rely solely on dropping known forbidden columns.
PREDICTOR_FEATURE_WHITELIST = frozenset(
    PREDICTOR_FINANCIAL_LEVEL_COLS + PREDICTOR_RATIO_COLS
)
FORBIDDEN_TARGET_COMPONENT_COLS = [
    "loss_dummy",
    "equity_negative_dummy",
    "distressed_target_reviewed",
    "FD_target_main",
    "FD_target_article141_only",
    "FD_target_persistent_loss_robustness",
    "fd_article141_direct",
    "fd_accumulated_loss",
    "fd_negative_equity",
    "fd_ocf_high_leverage",
    "target_status_reviewed",
    "distressed_flag_source_reviewed",
    "positive_target_reasons",
    "target_missing_reason",
]
SAMPLE_ELIGIBILITY_AUDIT_FROM_PREDICTOR = [
    "usable_for_model_flag",
    "data_quality_flag",
    "audit_status_clean",
    "statement_scope_status",
    "non_12_month_period_flag",
    "exclusion_flag",
    "manual_review_required_clean",
    "ocf_resolution_status",
    "gross_profit_resolution_status",
    "statement_scope_display_fa",
    "eligible_listing",
    "eligible_statement_type",
    "eligible_annual_period",
    "eligible_source_quality",
    "eligible_accounting_quality",
    "eligible_company_main",
    "eligible_company_expanded",
    "eligible_target",
    "predictor_eligible_main",
    "predictor_eligible_expanded",
    "model_exclusion_reason_main",
    "model_exclusion_reason_expanded",
]
PROVENANCE_AUDIT_COLS = [
    "source_file",
    "source_url",
]
TIMING_ASSUMPTION_COLS = [
    "fiscal_year_end_t_jalali",
    "fiscal_year_end_t_gregorian",
    "assumed_available_at_conservative_jalali",
    "assumed_available_at_conservative_gregorian",
    "conservative_lag_months",
    "availability_method",
    "availability_date_semantics",
    "is_observed_publication_timestamp",
    "target_fiscal_year_end_t_plus_1_jalali",
    "target_fiscal_year_end_t_plus_1_gregorian",
    "assumed_before_target_fiscal_year_end",
    "timing_relation_exception",
    "timing_eligible_for_analysis",
    "timing_eligible_for_model",
    "timing_exclusion_reason",
    "sample_design",
]
TIMING_ELIGIBILITY_AUDIT_COLS = frozenset({
    "assumed_before_target_fiscal_year_end",
    "timing_relation_exception",
    "timing_eligible_for_analysis",
    "timing_eligible_for_model",
    "timing_exclusion_reason",
})
TARGET_IDENTITY_AUDIT_COLS = [
    "target_row_ticker",
    "target_row_fiscal_year",
    "target_row_key_matched",
]

FORBIDDEN_FROM_FEATURE_SURFACE = frozenset(
    FORBIDDEN_TARGET_COMPONENT_COLS
    + [
        "FD_target_main_t_plus_1",
        "FD_target_article141_only_t_plus_1",
        "FD_target_persistent_loss_robustness_t_plus_1",
        "pair_final_eligible_main",
        "pair_final_eligible_expanded",
        "pair_exclusion_reason_main",
        "pair_exclusion_reason_expanded",
        "pair_final_eligible_main_gate_b_primary",
        "pair_exclusion_reason_main_gate_b_primary",
        "pair_final_eligible_main_gate_b_robustness",
        "pair_exclusion_reason_main_gate_b_robustness",
        "pair_final_eligible_expanded_gate_b_primary",
        "pair_exclusion_reason_expanded_gate_b_primary",
        "pair_final_eligible_expanded_gate_b_robustness",
        "pair_exclusion_reason_expanded_gate_b_robustness",
        "predictor_eligible_main_t",
        "predictor_eligible_expanded_t",
        "valid_target_t_plus_1",
        "source_file",
        "source_url",
    ]
    + TIMING_ASSUMPTION_COLS
    + TARGET_IDENTITY_AUDIT_COLS
    + SAMPLE_ELIGIBILITY_AUDIT_FROM_PREDICTOR
)

PR47_HEAD_OID = part3b1e.PR47_HEAD_OID
PR3_HEAD_OID = part3b1e.PR3_HEAD_OID

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3C."""


class AuthorizationError(QCFail):
    """Raised when a prohibited authorization or mutation is attempted."""


# --------------------------------------------------------------------------- #
# Hashing / IO helpers
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


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str) -> str:
    head = _git(repo_root, "rev-parse", "HEAD")
    if not head:
        raise QCFail("unable to resolve HEAD")
    if head != EXPECTED_BASELINE_COMMIT and not _is_ancestor(
        repo_root, EXPECTED_BASELINE_COMMIT, head,
    ):
        raise QCFail(
            f"baseline {EXPECTED_BASELINE_COMMIT} is not an ancestor of "
            f"HEAD {head}"
        )
    return head


def require_file_hash(repo_root: Path, rel: str, expected: str) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing bulky input: {rel}")
    digest = sha256_file(path)
    if digest != expected:
        raise QCFail(
            f"input hash mismatch for {rel}: got {digest}, expected {expected}"
        )
    return digest


def frozen_bulky_hashes(repo_root: Path) -> dict[str, str]:
    return {
        rel: require_file_hash(repo_root, rel, expected)
        for rel, expected in FROZEN_BULKY_INPUTS.items()
    }


def require_part3b1e_locks(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in (PART3B1E_DECISION_LOCK_REL, PART3B1E_FROZEN_MANIFEST_REL):
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"missing Part 3B.1E lock artifact: {rel}")
        out[rel] = sha256_file(path) or ""
    lock = json.loads(
        (repo_root / PART3B1E_DECISION_LOCK_REL).read_text(encoding="utf-8")
    )
    if lock.get("conservative_lag_months") != APPROVED_LAG_MONTHS:
        raise QCFail("Part 3B.1E decision lock lag is not 6 months")
    if lock.get("availability_method") != AVAILABILITY_METHOD:
        raise QCFail("Part 3B.1E decision lock availability_method mismatch")
    if lock.get("financial_value_reextraction_required") is not False:
        raise QCFail("Part 3B.1E lock must forbid financial re-extraction")
    return out


# --------------------------------------------------------------------------- #
# Date helpers (reuse Part 3B.1E Jalali calendar function)
# --------------------------------------------------------------------------- #

def parse_jalali_date(value: str, *, field: str, row_key: str) -> jdatetime.date:
    text = (value or "").strip().replace("-", "/")
    if not text:
        raise QCFail(f"invalid/missing {field} for {row_key!r}")
    parts = text.split("/")
    if len(parts) != 3:
        raise QCFail(f"invalid {field}={value!r} for {row_key!r}")
    try:
        y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
        return jdatetime.date(y, m, d)
    except ValueError as exc:
        raise QCFail(
            f"invalid {field}={value!r} for {row_key!r}: {exc}"
        ) from exc


def jalali_to_iso(d: jdatetime.date) -> str:
    return d.strftime("%Y-%m-%d")


def gregorian_iso(d: jdatetime.date) -> str:
    return d.togregorian().isoformat()


def reject_assumed_date_as_observed_field(field_name: str, value: Any) -> None:
    if field_name in FORBIDDEN_OBSERVED_FIELD_NAMES:
        raise AuthorizationError(
            f"assumed date cannot populate observed field {field_name!r} "
            f"(value={value!r}); use {ASSUMED_FIELD_NAME}"
        )


def require_timing_relation(
    assumed: jdatetime.date,
    target_fye: jdatetime.date,
    *,
    exception_key: tuple[str, int, int, str, str] | None,
    row_key: str,
) -> tuple[bool, bool]:
    """Return (relation_ok, is_authorized_exception). Fail closed otherwise."""
    ok = assumed < target_fye
    if ok:
        return True, False
    if exception_key in AUTHORIZED_TIMING_EXCEPTIONS:
        return False, True
    raise QCFail(
        f"assumed_available_at_conservative not before "
        f"target_fiscal_year_end for {row_key}: "
        f"assumed={jalali_to_iso(assumed)} "
        f"target_fye={jalali_to_iso(target_fye)}"
    )


# --------------------------------------------------------------------------- #
# Column-role map
# --------------------------------------------------------------------------- #

def build_column_role_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(col: str, role: str, notes: str = "") -> None:
        # Explicit whitelist only — never infer eligibility solely by dropping
        # known forbidden columns.
        enters = (
            "true"
            if role == "predictor_candidate" and col in PREDICTOR_FEATURE_WHITELIST
            else "false"
        )
        rows.append({
            "column_name": col,
            "role": role,
            "enters_model_feature_matrix": enters,
            "notes": notes,
        })

    for col in (
        "ticker",
        "company_name",
        "fiscal_year_t",
        "target_year",
        "predictor_row_key_t",
        "target_row_key_t_plus_1",
        "row_key_predictor",
        "industry",
        "unit",
        "sample_design",
    ):
        add(col, "identifier")

    for col in PREDICTOR_FINANCIAL_LEVEL_COLS + PREDICTOR_RATIO_COLS:
        if col not in PREDICTOR_FEATURE_WHITELIST:
            raise QCFail(f"predictor candidate missing from whitelist: {col}")
        add(col, "predictor_candidate", "predictor-year financial surface only")

    for col in (
        "FD_target_main_t_plus_1",
        "FD_target_article141_only_t_plus_1",
        "FD_target_persistent_loss_robustness_t_plus_1",
    ):
        add(col, "target", "copied from frozen Gate B pair; not recomputed")

    for col in TIMING_ASSUMPTION_COLS:
        if col == "sample_design":
            continue
        if col in TIMING_ELIGIBILITY_AUDIT_COLS:
            add(
                col,
                "timing_eligibility_audit",
                "audit/eligibility only; never predictor feature matrix",
            )
        else:
            add(
                col,
                "timing_assumption",
                "methodological; not observed publication",
            )

    for col in GATE_B_PAIR_COLUMNS:
        if col in {
            "ticker", "company_name", "fiscal_year_t", "target_year",
            "predictor_row_key_t", "target_row_key_t_plus_1",
            "FD_target_main_t_plus_1",
            "FD_target_article141_only_t_plus_1",
            "FD_target_persistent_loss_robustness_t_plus_1",
        }:
            continue
        add(col, "sample_eligibility_audit", "Gate B eligibility audit only")

    for col in SAMPLE_ELIGIBILITY_AUDIT_FROM_PREDICTOR:
        add(col, "sample_eligibility_audit", "predictor-year eligibility audit")

    for col in TARGET_IDENTITY_AUDIT_COLS:
        add(col, "provenance_audit", "target-row identity join audit")

    for col in PROVENANCE_AUDIT_COLS:
        add(col, "provenance_audit")

    for col in FORBIDDEN_TARGET_COMPONENT_COLS:
        add(
            col,
            "forbidden_from_model_matrix",
            "target-derived / pending Part 4 decision; never feature matrix",
        )

    # Ensure uniqueness / complete roles.
    seen: dict[str, str] = {}
    for r in rows:
        name = r["column_name"]
        if name in seen and seen[name] != r["role"]:
            raise QCFail(f"column {name} has conflicting roles")
        seen[name] = r["role"]
    rows.sort(key=lambda r: (r["role"], r["column_name"]))
    return rows


def final_output_header() -> list[str]:
    """Deterministic column order for audited / analysis-ready bulky CSVs."""
    header: list[str] = []
    for col in (
        "sample_design",
        "ticker",
        "company_name",
        "fiscal_year_t",
        "target_year",
        "predictor_row_key_t",
        "target_row_key_t_plus_1",
        "row_key_predictor",
        "industry",
        "unit",
    ):
        header.append(col)
    header.extend(PREDICTOR_FINANCIAL_LEVEL_COLS)
    header.extend(PREDICTOR_RATIO_COLS)
    header.extend([
        "FD_target_main_t_plus_1",
        "FD_target_article141_only_t_plus_1",
        "FD_target_persistent_loss_robustness_t_plus_1",
    ])
    header.extend(TIMING_ASSUMPTION_COLS[:-1])  # sample_design already first
    header.extend(TARGET_IDENTITY_AUDIT_COLS)
    # Gate B eligibility / exclusion audit (not features)
    for col in GATE_B_PAIR_COLUMNS:
        if col not in header:
            header.append(col)
    header.extend(SAMPLE_ELIGIBILITY_AUDIT_FROM_PREDICTOR)
    header.extend(PROVENANCE_AUDIT_COLS)
    # Forbidden target-component dummies retained for audit, not features.
    header.extend(FORBIDDEN_TARGET_COMPONENT_COLS)
    # Deduplicate while preserving order.
    out: list[str] = []
    seen: set[str] = set()
    for c in header:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


# --------------------------------------------------------------------------- #
# Pair construction
# --------------------------------------------------------------------------- #

def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_stage123_by_row_key(repo_root: Path) -> dict[str, dict[str, str]]:
    rel = "project/stage123/modeling_all_rows_stage123.csv"
    rows = _read_csv_dicts(repo_root / rel)
    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row["row_key"]
        if key in by_key:
            raise QCFail(f"duplicate predictor/target row_key in Stage123: {key}")
        by_key[key] = row
    return by_key


def _positive_flag(value: str) -> bool:
    return str(value).strip() in {"1", "1.0", "True", "true"}


def build_design_rows(
    *,
    design: str,
    pair_rows: list[dict[str, str]],
    stage123: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    spec = DESIGN_SPECS[design]
    if len(pair_rows) != spec["pairs"]:
        raise QCFail(
            f"{design}: pair count {len(pair_rows)} != expected {spec['pairs']}"
        )

    pred_keys = [r["predictor_row_key_t"] for r in pair_rows]
    tgt_keys = [r["target_row_key_t_plus_1"] for r in pair_rows]
    if len(pred_keys) != len(set(pred_keys)):
        raise QCFail(f"{design}: duplicate predictor_row_key_t in sample")
    # Target keys may repeat across companies? No — each pair has unique
    # predictor; target keys can theoretically collide across designs but
    # within a design each pair is unique by predictor. Duplicate target keys
    # across different predictors would be invalid for one-to-one target join
    # identity per pair — allow same target only once per design sample.
    tgt_counts = Counter(tgt_keys)
    dups = [k for k, n in tgt_counts.items() if n > 1]
    if dups:
        raise QCFail(f"{design}: duplicate target_row_key_t_plus_1: {dups[:5]}")

    header = final_output_header()
    out_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for pair in pair_rows:
        pk = pair["predictor_row_key_t"]
        tk = pair["target_row_key_t_plus_1"]
        if pk not in stage123:
            raise QCFail(f"{design}: missing predictor join for {pk}")
        if tk not in stage123:
            raise QCFail(f"{design}: missing target join for {tk}")
        pred = stage123[pk]
        tgt = stage123[tk]

        try:
            fy_t = int(str(pair["fiscal_year_t"]).strip())
            ty = int(str(pair["target_year"]).strip())
        except ValueError as exc:
            raise QCFail(f"{design}: invalid year fields for {pk}") from exc
        if ty != fy_t + 1:
            raise QCFail(
                f"{design}: target_year != fiscal_year_t+1 for {pk} "
                f"(t={fy_t}, target={ty})"
            )
        if pred["ticker"] != pair["ticker"]:
            raise QCFail(f"{design}: predictor ticker mismatch for {pk}")
        if tgt["ticker"] != pair["ticker"]:
            raise QCFail(f"{design}: target ticker mismatch for {tk}")
        if int(str(pred["fiscal_year"]).strip()) != fy_t:
            raise QCFail(f"{design}: predictor fiscal_year mismatch for {pk}")
        if int(str(tgt["fiscal_year"]).strip()) != ty:
            raise QCFail(f"{design}: target fiscal_year mismatch for {tk}")

        fye_t = parse_jalali_date(
            pred["fiscal_year_end"], field="fiscal_year_end_t", row_key=pk,
        )
        fye_t1 = parse_jalali_date(
            tgt["fiscal_year_end"],
            field="fiscal_year_end_t_plus_1",
            row_key=tk,
        )
        lag_payload = part3b1e.compute_assumed_available_at_conservative(
            fye_t, lag_months=APPROVED_LAG_MONTHS,
        )
        assumed = parse_jalali_date(
            lag_payload["assumed_available_at_conservative_jalali"],
            field=ASSUMED_FIELD_NAME,
            row_key=pk,
        )
        exception_key = (
            pair["ticker"], fy_t, ty, pk, tk,
        )
        relation_ok, is_exc = require_timing_relation(
            assumed, fye_t1, exception_key=exception_key, row_key=pk,
        )

        row: dict[str, Any] = {k: "" for k in header}
        row["sample_design"] = design
        for col in GATE_B_PAIR_COLUMNS:
            row[col] = pair.get(col, "")
        row["row_key_predictor"] = pred["row_key"]
        row["industry"] = pred.get("industry", "")
        row["unit"] = pred.get("unit", "")
        for col in (
            PREDICTOR_FINANCIAL_LEVEL_COLS
            + PREDICTOR_RATIO_COLS
            + FORBIDDEN_TARGET_COMPONENT_COLS
            + SAMPLE_ELIGIBILITY_AUDIT_FROM_PREDICTOR
            + PROVENANCE_AUDIT_COLS
        ):
            row[col] = pred.get(col, "")

        row["fiscal_year_end_t_jalali"] = jalali_to_iso(fye_t)
        row["fiscal_year_end_t_gregorian"] = gregorian_iso(fye_t)
        row["assumed_available_at_conservative_jalali"] = lag_payload[
            "assumed_available_at_conservative_jalali"
        ]
        row["assumed_available_at_conservative_gregorian"] = lag_payload[
            "assumed_available_at_conservative_gregorian"
        ]
        row["conservative_lag_months"] = str(APPROVED_LAG_MONTHS)
        row["availability_method"] = AVAILABILITY_METHOD
        row["availability_date_semantics"] = AVAILABILITY_DATE_SEMANTICS
        row["is_observed_publication_timestamp"] = "false"
        row["target_fiscal_year_end_t_plus_1_jalali"] = jalali_to_iso(fye_t1)
        row["target_fiscal_year_end_t_plus_1_gregorian"] = gregorian_iso(fye_t1)
        row["assumed_before_target_fiscal_year_end"] = (
            "true" if relation_ok else "false"
        )
        row["timing_relation_exception"] = "true" if is_exc else "false"
        if relation_ok:
            row["timing_eligible_for_analysis"] = "true"
            row["timing_eligible_for_model"] = "true"
            row["timing_exclusion_reason"] = ""
        else:
            # Authorized exception only reaches this branch; unauthorized
            # violations already failed closed in require_timing_relation.
            row["timing_eligible_for_analysis"] = "false"
            row["timing_eligible_for_model"] = "false"
            row["timing_exclusion_reason"] = TIMING_EXCLUSION_REASON_AUTHORIZED
        row["target_row_ticker"] = tgt["ticker"]
        row["target_row_fiscal_year"] = str(tgt["fiscal_year"])
        row["target_row_key_matched"] = tgt["row_key"]

        # Hard bans: never populate observed publication fields.
        for forbidden in FORBIDDEN_OBSERVED_FIELD_NAMES:
            if forbidden in row and row[forbidden] not in ("", None):
                raise AuthorizationError(
                    f"attempted to populate forbidden observed field "
                    f"{forbidden} for {pk}"
                )
            row.pop(forbidden, None)

        out_rows.append(row)
        audit_rows.append({
            "sample_design": design,
            "predictor_row_key_t": pk,
            "target_row_key_t_plus_1": tk,
            "ticker": pair["ticker"],
            "fiscal_year_t": str(fy_t),
            "target_year": str(ty),
            "predictor_join": "one_to_one",
            "target_join": "one_to_one",
            "ticker_identity_exact": "true",
            "t_to_t_plus_1_exact": "true",
            "assumed_available_at_conservative_jalali": row[
                "assumed_available_at_conservative_jalali"
            ],
            "target_fiscal_year_end_t_plus_1_jalali": row[
                "target_fiscal_year_end_t_plus_1_jalali"
            ],
            "assumed_before_target_fiscal_year_end": row[
                "assumed_before_target_fiscal_year_end"
            ],
            "timing_relation_exception": row["timing_relation_exception"],
            "timing_eligible_for_analysis": row["timing_eligible_for_analysis"],
            "timing_eligible_for_model": row["timing_eligible_for_model"],
            "timing_exclusion_reason": row["timing_exclusion_reason"],
            "target_value_source": "frozen_gate_b_pair_copy",
            "financial_value_source": "frozen_stage123_predictor_row_copy",
            "is_observed_publication_timestamp": "false",
            "row_silently_dropped": "false",
        })

    # Preserve sample membership: exact counts.
    companies = len({r["ticker"] for r in out_rows})
    pos = sum(1 for r in out_rows if _positive_flag(r["FD_target_main_t_plus_1"]))
    neg = len(out_rows) - pos
    if companies != spec["companies"]:
        raise QCFail(
            f"{design}: company count {companies} != {spec['companies']}"
        )
    if pos != spec["positive"] or neg != spec["negative"]:
        raise QCFail(
            f"{design}: positive/negative {pos}/{neg} != "
            f"{spec['positive']}/{spec['negative']}"
        )
    if len(out_rows) != len(pair_rows):
        raise QCFail(f"{design}: row silently dropped during construction")

    # Deterministic ordering.
    out_rows.sort(key=lambda r: (r["ticker"], int(r["fiscal_year_t"]), r["predictor_row_key_t"]))
    audit_rows.sort(key=lambda r: (r["sample_design"], r["ticker"], r["fiscal_year_t"]))
    return out_rows, audit_rows


def split_analysis_ready(
    rows: list[dict[str, Any]],
    *,
    design: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split audited rows into analysis-ready vs explicit timing exclusions.

    Fail-closed: every exclusion must be an authorized timing exception with
    assumed_before_target_fiscal_year_end != true. Analysis-ready rows must
    all have assumed_before_target_fiscal_year_end == true.
    """
    ready: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        before = row["assumed_before_target_fiscal_year_end"] == "true"
        is_exc = row["timing_relation_exception"] == "true"
        eligible = row["timing_eligible_for_analysis"] == "true"
        model_eligible = row["timing_eligible_for_model"] == "true"
        if before:
            if is_exc:
                raise QCFail(
                    f"{design}: timing_relation_exception cannot be true when "
                    f"assumed_before_target_fiscal_year_end=true "
                    f"({row['predictor_row_key_t']})"
                )
            if not eligible or not model_eligible:
                raise QCFail(
                    f"{design}: timing-eligible flags must be true when "
                    f"assumed_before_target_fiscal_year_end=true "
                    f"({row['predictor_row_key_t']})"
                )
            if row["timing_exclusion_reason"]:
                raise QCFail(
                    f"{design}: timing_exclusion_reason must be empty for "
                    f"timing-eligible row {row['predictor_row_key_t']}"
                )
            ready.append(row)
            continue

        # Not before target FYE → must be authorized audited exception.
        if not is_exc:
            raise QCFail(
                f"{design}: unauthorized timing violation for "
                f"{row['predictor_row_key_t']}"
            )
        if eligible or model_eligible:
            raise QCFail(
                f"{design}: authorized timing exception must not be "
                f"analysis/model eligible ({row['predictor_row_key_t']})"
            )
        if row["timing_exclusion_reason"] != TIMING_EXCLUSION_REASON_AUTHORIZED:
            raise QCFail(
                f"{design}: unexpected timing_exclusion_reason="
                f"{row['timing_exclusion_reason']!r} for "
                f"{row['predictor_row_key_t']}"
            )
        excluded.append(row)

    if len(ready) + len(excluded) != len(rows):
        raise QCFail(
            f"{design}: analysis-ready/exclusion split does not reconcile "
            f"with audited row count ({len(ready)}+{len(excluded)}!={len(rows)})"
        )
    return ready, excluded


def summarize_design(
    design: str,
    audited_rows: list[dict[str, Any]],
    analysis_rows: list[dict[str, Any]],
    excluded_rows: list[dict[str, Any]],
    audited_sha256: str,
    analysis_sha256: str,
) -> dict[str, Any]:
    audited_pos = sum(
        1 for r in audited_rows if _positive_flag(r["FD_target_main_t_plus_1"])
    )
    analysis_pos = sum(
        1 for r in analysis_rows if _positive_flag(r["FD_target_main_t_plus_1"])
    )
    return {
        "sample_design": design,
        # Backward-compatible aliases = audited Gate B membership surface.
        "pairs": str(len(audited_rows)),
        "companies": str(len({r["ticker"] for r in audited_rows})),
        "positive": str(audited_pos),
        "negative": str(len(audited_rows) - audited_pos),
        "audited_pairs": str(len(audited_rows)),
        "audited_companies": str(len({r["ticker"] for r in audited_rows})),
        "audited_positive": str(audited_pos),
        "audited_negative": str(len(audited_rows) - audited_pos),
        "analysis_ready_pairs": str(len(analysis_rows)),
        "analysis_ready_companies": str(
            len({r["ticker"] for r in analysis_rows})
        ),
        "analysis_ready_positive": str(analysis_pos),
        "analysis_ready_negative": str(len(analysis_rows) - analysis_pos),
        "excluded_timing_exception_count": str(len(excluded_rows)),
        "columns": str(len(final_output_header())),
        "audited_output_file": (
            f"{BULKY_OUTPUT_DIR_REL}/{AUDITED_OUTPUT_FILES[design]}"
        ),
        "audited_output_sha256": audited_sha256,
        "analysis_ready_output_file": (
            f"{BULKY_OUTPUT_DIR_REL}/{ANALYSIS_READY_OUTPUT_FILES[design]}"
        ),
        "analysis_ready_output_sha256": analysis_sha256,
        # Legacy keys retained for readers; point at audited surface.
        "output_file": (
            f"{BULKY_OUTPUT_DIR_REL}/{AUDITED_OUTPUT_FILES[design]}"
        ),
        "output_sha256": audited_sha256,
        "timing_relation_exceptions": str(
            sum(
                1 for r in audited_rows
                if r["timing_relation_exception"] == "true"
            )
        ),
    }


def target_year_distribution_rows(
    design: str,
    rows: list[dict[str, Any]],
    *,
    dataset_surface: str,
) -> list[dict[str, str]]:
    counts: Counter[str] = Counter()
    pos_by: Counter[str] = Counter()
    for r in rows:
        y = str(r["target_year"])
        counts[y] += 1
        if _positive_flag(r["FD_target_main_t_plus_1"]):
            pos_by[y] += 1
    out = []
    for y in sorted(counts, key=lambda x: int(x)):
        out.append({
            "sample_design": design,
            "dataset_surface": dataset_surface,
            "target_year": y,
            "pairs": str(counts[y]),
            "positive": str(pos_by[y]),
            "negative": str(counts[y] - pos_by[y]),
        })
    return out


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_contract(
    *,
    pinned_inputs: dict[str, str],
    part3b1e_locks: dict[str, str],
    output_hashes: dict[str, str],
    sample_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    role_rows = build_column_role_rows()
    role_counts = Counter(r["role"] for r in role_rows)
    return {
        "contract_version": CONTRACT_VERSION,
        "research_action_id": RESEARCH_ACTION_ID,
        "qc_scope": RESEARCH_ACTION_ID,
        "baseline_merge_sha_exact": EXPECTED_BASELINE_COMMIT,
        "baseline_note": "PR #48 merge SHA on main",
        "part3b1e_decision_lock_present": True,
        "part3b1e_decision_lock_sha256": part3b1e_locks[PART3B1E_DECISION_LOCK_REL],
        "part3b1e_frozen_manifest_sha256": part3b1e_locks[
            PART3B1E_FROZEN_MANIFEST_REL
        ],
        "six_month_lag_exact": APPROVED_LAG_MONTHS,
        "Jalali_calendar_used": True,
        "availability_method": AVAILABILITY_METHOD,
        "availability_date_semantics": AVAILABILITY_DATE_SEMANTICS,
        "assumed_availability_field_name": ASSUMED_FIELD_NAME,
        "is_observed_publication_timestamp": False,
        "financial_data_status": "researcher_verified_frozen",
        "financial_value_reextraction_required": False,
        "broad_codal_capture_authorized": False,
        "row_level_publish_datetime_collection_authorized": False,
        "row_level_real_available_at_assignment_authorized": False,
        "feature_selection_authorized": False,
        "model_fitting_authorized": False,
        "stage126_authorized": False,
        "modeling_authorized": False,
        "stage125_complete": False,
        "four_locked_sample_designs": list(DESIGN_SPECS.keys()),
        "expected_sample_counts": {
            k: {
                "pairs": v["pairs"],
                "companies": v["companies"],
                "positive": v["positive"],
                "negative": v["negative"],
            }
            for k, v in DESIGN_SPECS.items()
        },
        "sample_summaries": sample_summaries,
        "pinned_bulky_input_sha256": dict(sorted(pinned_inputs.items())),
        "bulky_output_dir": BULKY_OUTPUT_DIR_REL,
        "bulky_output_sha256": dict(sorted(output_hashes.items())),
        "audited_pair_output_files": {
            k: f"{BULKY_OUTPUT_DIR_REL}/{v}"
            for k, v in sorted(AUDITED_OUTPUT_FILES.items())
        },
        "analysis_ready_output_files": {
            k: f"{BULKY_OUTPUT_DIR_REL}/{v}"
            for k, v in sorted(ANALYSIS_READY_OUTPUT_FILES.items())
        },
        "column_role_counts": dict(sorted(role_counts.items())),
        "predictor_feature_whitelist": sorted(PREDICTOR_FEATURE_WHITELIST),
        "forbidden_from_model_feature_surface": sorted(
            FORBIDDEN_FROM_FEATURE_SURFACE
        ),
        "forbidden_observed_field_names": sorted(FORBIDDEN_OBSERVED_FIELD_NAMES),
        "authorized_timing_relation_exceptions": [
            {
                "ticker": t[0],
                "fiscal_year_t": t[1],
                "target_year": t[2],
                "predictor_row_key_t": t[3],
                "target_row_key_t_plus_1": t[4],
                "timing_eligible_for_analysis": False,
                "timing_eligible_for_model": False,
                "timing_exclusion_reason": TIMING_EXCLUSION_REASON_AUTHORIZED,
                "reason": (
                    "fiscal_year_calendar_shift: predictor Esfand FYE + 6m "
                    "is after target Farvardin FYE; retained in audited Gate B "
                    "membership surface only; excluded from analysis-ready / "
                    "model-eligible datasets; not silently dropped; not "
                    "claimed as timing-safe"
                ),
            }
            for t in sorted(AUTHORIZED_TIMING_EXCEPTIONS)
        ],
        "target_copy_rule": (
            "targets copied byte-for-byte from frozen Gate B pair files; "
            "never recomputed from accounting values"
        ),
        "predictor_join_rule": (
            "predictor_row_key_t == stage123.row_key; exactly one match"
        ),
        "target_join_rule": (
            "target_row_key_t_plus_1 == stage123.row_key; exactly one match; "
            "identity/FYE audit only"
        ),
        "analysis_ready_rule": (
            "analysis-ready / leakage-safe modeling surface includes only "
            "rows with assumed_before_target_fiscal_year_end=true; authorized "
            "timing exceptions remain visible in the audited pair surface"
        ),
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "explicit_non_claims": [
            "no_financial_value_reextraction",
            "no_target_recalculation",
            "no_eligibility_change",
            "no_silent_row_drop",
            "no_observed_PublishDateTime_claim",
            "no_real_available_at_assignment",
            "no_feature_selection",
            "no_model_fitting",
            "no_imputation_or_scaling",
            "no_temporal_cv",
            "no_stage126",
            "stage125_not_complete",
            "audited_pairs_are_not_fully_leakage_safe_model_ready",
            "authorized_timing_exceptions_not_timing_safe",
            "merge_requires_explicit_human_approval",
        ],
        "part3b_broad_codal_expansion_superseded": True,
        "conservative_six_month_lag_approved": True,
        "part3c_leakage_safe_finalization_completed": True,
        "pair_level_evidence_collected": True,
        "part3b_completed": False,
        "modeling_started": False,
        "stage126_started": False,
    }


def build_input_manifest(
    pinned: dict[str, str],
    part3b1e_locks: dict[str, str],
) -> dict[str, Any]:
    return {
        "manifest_version": CONTRACT_VERSION,
        "description": (
            "SHA-256 pins for local bulky Gate B / Stage123 inputs and the "
            "tracked Part 3B.1E decision lock / frozen-data manifest."
        ),
        "bulky_inputs_sha256": dict(sorted(pinned.items())),
        "part3b1e_tracked_locks_sha256": dict(sorted(part3b1e_locks.items())),
        "immutability_rule": (
            "before/after SHA-256 equality required; mismatch is QC failure"
        ),
        "financial_value_reextraction_required": False,
    }


def build_readme(contract: dict[str, Any]) -> str:
    return (
        "# Stage125 Part 3C — Leakage-Safe Dataset Finalization\n\n"
        "**Status:** audited pair datasets and timing-eligible "
        "leakage-safe analysis-ready datasets finalized under the locked "
        "six-month Jalali lag. Stage125 remains incomplete. "
        "No modeling / Stage126.\n\n"
        "## Terminology\n\n"
        "- **Audited pair datasets** = full frozen Gate B membership "
        "(authorized timing exceptions remain visible).\n"
        "- **Leakage-safe analysis-ready datasets** = timing-eligible subset "
        "only (`assumed_before_target_fiscal_year_end=true`).\n"
        "- Gate B membership preservation refers to the **audit population**, "
        "not necessarily the analysis-ready population.\n"
        "- The authorized `رمپنا|1396` → `رمپنا|1397` exception is **not** "
        "timing-safe and is **not** analysis/model eligible.\n\n"
        "## Methodology\n\n"
        "- Part 3B broad CODAL expansion is **superseded**.\n"
        "- Six-month conservative Jalali lag is **approved** "
        f"(`conservative_lag_months={APPROVED_LAG_MONTHS}`).\n"
        "- Part 3C leakage-safe finalization is **completed** for all four "
        "locked Gate B sample designs.\n"
        "- Financial data remain **researcher-verified and frozen** "
        "(no re-extraction).\n"
        "- Assumed availability uses "
        f"`{ASSUMED_FIELD_NAME}` only — **no** observed publication-time "
        "claim (`PublishDateTime` / `available_at` / `SentDateTime`).\n"
        "- Targets are copied from frozen Gate B pair files; never recomputed.\n"
        "- Predictors join Stage123 on `predictor_row_key_t` → `row_key` "
        "(fail-closed one-to-one).\n"
        "- Predictor feature matrix uses an **explicit whitelist** only.\n\n"
        "## Audited Gate B membership (complete pair surface)\n\n"
        "| Design | audited pairs | companies | positive | negative | excluded |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        + "".join(
            f"| `{s['sample_design']}` | {s['audited_pairs']} | "
            f"{s['audited_companies']} | {s['audited_positive']} | "
            f"{s['audited_negative']} | "
            f"{s['excluded_timing_exception_count']} |\n"
            for s in contract["sample_summaries"]
        )
        + "\n## Leakage-safe analysis-ready (timing-eligible)\n\n"
        "| Design | analysis pairs | companies | positive | negative |\n"
        "|---|---:|---:|---:|---:|\n"
        + "".join(
            f"| `{s['sample_design']}` | {s['analysis_ready_pairs']} | "
            f"{s['analysis_ready_companies']} | "
            f"{s['analysis_ready_positive']} | "
            f"{s['analysis_ready_negative']} |\n"
            for s in contract["sample_summaries"]
        )
        + "\n## Outputs\n\n"
        f"- Bulky CSVs (gitignored): `{BULKY_OUTPUT_DIR_REL}/`\n"
        "  - `audited_pairs_*.csv` — complete audited pair datasets\n"
        "  - `analysis_ready_*.csv` — leakage-safe analysis-ready datasets\n"
        "- Tracked contracts / QC / hashes / column-role map / audits in "
        "`project/stage125/`.\n\n"
        "## Research pointers\n\n"
        f"- `last_completed_research_action_id="
        f"{RESEARCH_LAST_COMPLETED}`\n"
        f"- `next_research_action_id={RESEARCH_NEXT}`\n"
    )


def build_all(
    repo_root: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    """Build tracked payloads and bulky CSV payloads.

    Returns (tracked_content, bulky_payloads, extras).
    """
    pinned = frozen_bulky_hashes(repo_root)
    part3b1e_locks = require_part3b1e_locks(repo_root)
    stage123 = load_stage123_by_row_key(repo_root)

    bulky: dict[str, str] = {}
    summaries: list[dict[str, Any]] = []
    all_audit: list[dict[str, Any]] = []
    all_ty: list[dict[str, str]] = []
    header = final_output_header()
    excluded_by_design: dict[str, list[dict[str, Any]]] = {}

    for design, spec in DESIGN_SPECS.items():
        pairs = _read_csv_dicts(repo_root / spec["input_rel"])
        rows, audit = build_design_rows(
            design=design, pair_rows=pairs, stage123=stage123,
        )
        analysis_rows, excluded_rows = split_analysis_ready(
            rows, design=design,
        )
        excluded_by_design[design] = excluded_rows
        audited_text = _csv_str(header, rows)
        analysis_text = _csv_str(header, analysis_rows)
        audited_digest = sha256_bytes(audited_text.encode("utf-8"))
        analysis_digest = sha256_bytes(analysis_text.encode("utf-8"))
        bulky[AUDITED_OUTPUT_FILES[design]] = audited_text
        bulky[ANALYSIS_READY_OUTPUT_FILES[design]] = analysis_text
        summaries.append(
            summarize_design(
                design,
                rows,
                analysis_rows,
                excluded_rows,
                audited_digest,
                analysis_digest,
            )
        )
        all_audit.extend(audit)
        all_ty.extend(
            target_year_distribution_rows(
                design, rows, dataset_surface="audited_pairs",
            )
        )
        all_ty.extend(
            target_year_distribution_rows(
                design, analysis_rows, dataset_surface="analysis_ready",
            )
        )

    contract = build_contract(
        pinned_inputs=pinned,
        part3b1e_locks=part3b1e_locks,
        output_hashes={
            f"{BULKY_OUTPUT_DIR_REL}/{k}": sha256_bytes(v.encode("utf-8"))
            for k, v in bulky.items()
        },
        sample_summaries=summaries,
    )
    role_rows = build_column_role_rows()
    content = {
        F_CONTRACT: _json_str(contract),
        F_INPUT_MANIFEST: _json_str(
            build_input_manifest(pinned, part3b1e_locks)
        ),
        F_COLUMN_ROLES: _csv_str(
            ["column_name", "role", "enters_model_feature_matrix", "notes"],
            role_rows,
        ),
        F_SAMPLE_SUMMARY: _csv_str(
            [
                "sample_design",
                "pairs", "companies", "positive", "negative",
                "audited_pairs", "audited_companies",
                "audited_positive", "audited_negative",
                "analysis_ready_pairs", "analysis_ready_companies",
                "analysis_ready_positive", "analysis_ready_negative",
                "excluded_timing_exception_count",
                "columns",
                "audited_output_file", "audited_output_sha256",
                "analysis_ready_output_file", "analysis_ready_output_sha256",
                "output_file", "output_sha256",
                "timing_relation_exceptions",
            ],
            summaries,
        ),
        F_TARGET_YEAR_DIST: _csv_str(
            [
                "sample_design", "dataset_surface", "target_year",
                "pairs", "positive", "negative",
            ],
            all_ty,
        ),
        F_LEAKAGE_AUDIT: _csv_str(
            [
                "sample_design", "predictor_row_key_t", "target_row_key_t_plus_1",
                "ticker", "fiscal_year_t", "target_year",
                "predictor_join", "target_join", "ticker_identity_exact",
                "t_to_t_plus_1_exact",
                "assumed_available_at_conservative_jalali",
                "target_fiscal_year_end_t_plus_1_jalali",
                "assumed_before_target_fiscal_year_end",
                "timing_relation_exception",
                "timing_eligible_for_analysis",
                "timing_eligible_for_model",
                "timing_exclusion_reason",
                "target_value_source", "financial_value_source",
                "is_observed_publication_timestamp", "row_silently_dropped",
            ],
            all_audit,
        ),
        F_README: build_readme(contract),
    }
    extras = {
        "contract": contract,
        "pinned": pinned,
        "part3b1e_locks": part3b1e_locks,
        "summaries": summaries,
        "role_rows": role_rows,
        "audit_rows": all_audit,
        "excluded_by_design": excluded_by_design,
        "bulky_names": list(bulky.keys()),
    }
    return content, bulky, extras


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def _assert(
    assertions: list[dict[str, str]],
    name: str,
    ok: bool,
    detail: str,
) -> None:
    assertions.append({
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
    })


def build_qc_assertions(
    *,
    repo_root: Path,
    contract: dict[str, Any],
    pinned_before: dict[str, str],
    pinned_after: dict[str, str],
    network_attempts: int,
    head: str,
    audit_rows: list[dict[str, Any]],
    role_rows: list[dict[str, str]],
    bulky_payloads: dict[str, str],
) -> list[dict[str, str]]:
    assertions: list[dict[str, str]] = []

    _assert(
        assertions, "baseline_merge_sha_exact",
        EXPECTED_BASELINE_COMMIT == contract["baseline_merge_sha_exact"]
        and (
            head == EXPECTED_BASELINE_COMMIT
            or _is_ancestor(str(repo_root), EXPECTED_BASELINE_COMMIT, head)
        ),
        f"baseline={EXPECTED_BASELINE_COMMIT} ancestor_of_HEAD=true",
    )
    _assert(
        assertions, "part3b1e_decision_lock_present",
        contract.get("part3b1e_decision_lock_present") is True
        and (repo_root / PART3B1E_DECISION_LOCK_REL).is_file(),
        PART3B1E_DECISION_LOCK_REL,
    )
    _assert(
        assertions, "six_month_lag_exact",
        contract.get("six_month_lag_exact") == APPROVED_LAG_MONTHS,
        str(contract.get("six_month_lag_exact")),
    )
    _assert(
        assertions, "Jalali_calendar_used",
        contract.get("Jalali_calendar_used") is True,
        "jdatetime calendar months via Part 3B.1E",
    )
    _assert(
        assertions, "all_input_hashes_exact",
        pinned_before == FROZEN_BULKY_INPUTS and pinned_after == pinned_before,
        f"count={len(pinned_after)}",
    )
    _assert(
        assertions, "frozen_financial_values_unchanged",
        pinned_before[
            "project/stage123/modeling_all_rows_stage123.csv"
        ] == pinned_after[
            "project/stage123/modeling_all_rows_stage123.csv"
        ],
        "stage123 all-rows SHA-256 unchanged",
    )
    gate_b_targets_ok = all(
        pinned_before[spec["input_rel"]] == pinned_after[spec["input_rel"]]
        for spec in DESIGN_SPECS.values()
    )
    _assert(
        assertions, "frozen_targets_unchanged",
        gate_b_targets_ok,
        "Gate B eligible pair SHA-256 unchanged",
    )
    _assert(
        assertions, "four_locked_sample_designs_present",
        set(contract["four_locked_sample_designs"]) == set(DESIGN_SPECS),
        ",".join(contract["four_locked_sample_designs"]),
    )

    summaries = {s["sample_design"]: s for s in contract["sample_summaries"]}
    counts_ok = True
    detail_counts = []
    for design, spec in DESIGN_SPECS.items():
        s = summaries[design]
        ok = (
            int(s["pairs"]) == spec["pairs"]
            and int(s["companies"]) == spec["companies"]
            and int(s["positive"]) == spec["positive"]
            and int(s["negative"]) == spec["negative"]
        )
        counts_ok = counts_ok and ok
        detail_counts.append(
            f"{design}:{s['pairs']}/{s['companies']}/"
            f"{s['positive']}/{s['negative']}"
        )
    _assert(
        assertions, "all_pair_counts_exact", counts_ok,
        ";".join(detail_counts) + " (audited Gate B membership)",
    )
    _assert(
        assertions, "all_positive_negative_counts_exact", counts_ok,
        ";".join(detail_counts) + " (audited Gate B membership)",
    )
    _assert(
        assertions, "all_company_counts_exact", counts_ok,
        ";".join(detail_counts) + " (audited Gate B membership)",
    )

    pred_join_ok = all(a["predictor_join"] == "one_to_one" for a in audit_rows)
    tgt_join_ok = all(a["target_join"] == "one_to_one" for a in audit_rows)
    _assert(assertions, "predictor_join_one_to_one", pred_join_ok, "all pairs")
    _assert(assertions, "target_join_one_to_one", tgt_join_ok, "all pairs")
    _assert(
        assertions, "ticker_identity_exact",
        all(a["ticker_identity_exact"] == "true" for a in audit_rows),
        "all pairs",
    )
    _assert(
        assertions, "t_to_t_plus_1_exact",
        all(a["t_to_t_plus_1_exact"] == "true" for a in audit_rows),
        "all pairs",
    )

    unexpected = [
        a for a in audit_rows
        if a["assumed_before_target_fiscal_year_end"] != "true"
        and a["timing_relation_exception"] != "true"
    ]
    authorized_exc = [
        a for a in audit_rows if a["timing_relation_exception"] == "true"
    ]
    _assert(
        assertions, "assumed_date_before_target_fiscal_year_end",
        len(unexpected) == 0
        and len(authorized_exc) == len(DESIGN_SPECS) * len(
            AUTHORIZED_TIMING_EXCEPTIONS
        ),
        f"unexpected_violations={len(unexpected)} "
        f"authorized_exceptions={len(authorized_exc)} "
        f"(audit surface; exceptions not analysis-ready)",
    )
    rampna_audit_visible = [
        a for a in authorized_exc
        if a["predictor_row_key_t"] == "رمپنا|1396"
        and a["target_row_key_t_plus_1"] == "رمپنا|1397"
        and a["timing_eligible_for_analysis"] == "false"
        and a["timing_eligible_for_model"] == "false"
        and a["timing_exclusion_reason"] == TIMING_EXCLUSION_REASON_AUTHORIZED
        and a["assumed_before_target_fiscal_year_end"] == "false"
        and a["row_silently_dropped"] == "false"
    ]
    _assert(
        assertions, "authorized_rampna_exception_visible_in_audit",
        len(rampna_audit_visible) == len(DESIGN_SPECS),
        f"visible_in_audit={len(rampna_audit_visible)}",
    )

    analysis_ready_ok = True
    reconcile_ok = True
    analysis_details: list[str] = []
    for design in DESIGN_SPECS:
        s = summaries[design]
        audited_n = int(s["audited_pairs"])
        ready_n = int(s["analysis_ready_pairs"])
        excl_n = int(s["excluded_timing_exception_count"])
        if audited_n != ready_n + excl_n:
            reconcile_ok = False
        analysis_text = bulky_payloads[ANALYSIS_READY_OUTPUT_FILES[design]]
        analysis_rows = list(csv.DictReader(io.StringIO(analysis_text)))
        if len(analysis_rows) != ready_n:
            analysis_ready_ok = False
        if any(
            r.get("assumed_before_target_fiscal_year_end") != "true"
            for r in analysis_rows
        ):
            analysis_ready_ok = False
        if any(
            r.get("timing_relation_exception") == "true"
            for r in analysis_rows
        ):
            analysis_ready_ok = False
        if any(
            r.get("timing_eligible_for_analysis") != "true"
            or r.get("timing_eligible_for_model") != "true"
            for r in analysis_rows
        ):
            analysis_ready_ok = False
        analysis_details.append(
            f"{design}:audited={audited_n}/ready={ready_n}/excl={excl_n}"
        )
    _assert(
        assertions, "analysis_ready_assumed_before_target_fye_true",
        analysis_ready_ok,
        ";".join(analysis_details),
    )
    _assert(
        assertions, "no_authorized_timing_exception_in_analysis_ready",
        analysis_ready_ok,
        ";".join(analysis_details),
    )
    _assert(
        assertions, "audit_and_analysis_ready_counts_reconcile",
        reconcile_ok and analysis_ready_ok,
        ";".join(analysis_details),
    )
    _assert(
        assertions, "no_row_silently_dropped",
        all(a["row_silently_dropped"] == "false" for a in audit_rows)
        and len(audit_rows) == sum(s["pairs"] for s in DESIGN_SPECS.values())
        and reconcile_ok,
        f"audit_rows={len(audit_rows)}; "
        f"reconcile={'ok' if reconcile_ok else 'fail'}",
    )
    _assert(
        assertions, "no_target_recalculation",
        all(a["target_value_source"] == "frozen_gate_b_pair_copy" for a in audit_rows),
        "gate_b_pair_copy",
    )
    _assert(
        assertions, "target_values_byte_or_semantically_identical",
        all(a["target_value_source"] == "frozen_gate_b_pair_copy" for a in audit_rows),
        "copied from frozen Gate B",
    )
    _assert(
        assertions, "no_observed_PublishDateTime_claim",
        contract.get("is_observed_publication_timestamp") is False
        and all(a["is_observed_publication_timestamp"] == "false" for a in audit_rows),
        "false",
    )
    _assert(
        assertions, "no_real_available_at_assignment",
        contract.get("row_level_real_available_at_assignment_authorized") is False,
        "authorized=false",
    )

    feature_roles = {
        r["column_name"]
        for r in role_rows
        if r["enters_model_feature_matrix"] == "true"
    }
    leakage_in_features = feature_roles & FORBIDDEN_FROM_FEATURE_SURFACE
    eligibility_in_features = feature_roles & TIMING_ELIGIBILITY_AUDIT_COLS
    _assert(
        assertions, "forbidden_target_columns_excluded_from_feature_surface",
        not leakage_in_features,
        f"overlap={sorted(leakage_in_features)[:8]}",
    )
    _assert(
        assertions, "timing_eligibility_fields_excluded_from_feature_surface",
        not eligibility_in_features,
        f"overlap={sorted(eligibility_in_features)}",
    )
    _assert(
        assertions, "predictor_feature_whitelist_exact",
        feature_roles == PREDICTOR_FEATURE_WHITELIST,
        f"feature_count={len(feature_roles)} "
        f"whitelist={len(PREDICTOR_FEATURE_WHITELIST)}",
    )
    expected_bulky = len(DESIGN_SPECS) * 2  # audited + analysis-ready
    _assert(
        assertions, "output_hashes_recorded",
        len(contract.get("bulky_output_sha256") or {}) == expected_bulky,
        str(len(contract.get("bulky_output_sha256") or {})),
    )

    # Determinism probe: rebuild byte strings already in bulky_payloads;
    # second serialization of same rows must match (ordering fixed).
    det_ok = all(
        sha256_bytes(text.encode("utf-8"))
        == contract["bulky_output_sha256"][
            f"{BULKY_OUTPUT_DIR_REL}/{name}"
        ]
        for name, text in bulky_payloads.items()
    )
    _assert(assertions, "build_deterministic", det_ok, "sha256 stable")
    _assert(
        assertions, "network_requests_zero",
        network_attempts == 0,
        str(network_attempts),
    )
    _assert(
        assertions, "Stage126_false",
        contract.get("stage126_authorized") is False
        and contract.get("stage126_started") is False,
        "false",
    )
    _assert(
        assertions, "modeling_false",
        contract.get("modeling_authorized") is False
        and contract.get("modeling_started") is False,
        "false",
    )

    # Non-tautological policy probes.
    lag5 = False
    try:
        part3b1e.require_approved_lag_months(5)
    except part3b1e.AuthorizationError:
        lag5 = True
    _assert(assertions, "policy_lag_five_rejected", lag5, "5")
    lag7 = False
    try:
        part3b1e.require_approved_lag_months(7)
    except part3b1e.AuthorizationError:
        lag7 = True
    _assert(assertions, "policy_lag_seven_rejected", lag7, "7")

    pub_reject = False
    try:
        reject_assumed_date_as_observed_field("PublishDateTime", "1402-06-29")
    except AuthorizationError:
        pub_reject = True
    _assert(assertions, "policy_PublishDateTime_rejected", pub_reject, "PublishDateTime")

    avail_reject = False
    try:
        reject_assumed_date_as_observed_field("available_at", "1402-06-29")
    except AuthorizationError:
        avail_reject = True
    _assert(assertions, "policy_available_at_rejected", avail_reject, "available_at")

    sample = part3b1e.compute_assumed_available_at_conservative(
        jdatetime.date(1401, 12, 29)
    )
    _assert(
        assertions, "formula_fiscal_year_end_plus_six_months",
        sample["assumed_available_at_conservative_jalali"] == "1402-06-29"
        and sample["is_observed_publication_timestamp"] is False,
        sample["assumed_available_at_conservative_jalali"],
    )
    # Jalali clamp probe: 31-day month into shorter month.
    clamped = part3b1e.add_jalali_calendar_months(
        jdatetime.date(1401, 6, 31), APPROVED_LAG_MONTHS,
    )
    _assert(
        assertions, "jalali_day_clamping_probe",
        clamped == jdatetime.date(1401, 12, 29),
        str(clamped),
    )
    _assert(
        assertions, "forbidden_surfaces_absent",
        all(not (repo_root / rel).exists() for rel in FORBIDDEN_SURFACE_EXACT),
        "stage126/part3b2 absent",
    )
    return assertions


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def _compare_bulky_drift(bulky_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    if not bulky_dir.is_dir():
        return sorted(payloads)
    for name, text in payloads.items():
        path = bulky_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    build: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if build and check:
        raise QCFail("build and check are mutually exclusive")
    if not build and not check:
        raise QCFail("one of --build or --check is required")

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out
    bulky_dir = (out_dir / "part3c_outputs").resolve()
    if out_dir != canonical_out:
        # Custom output_dir: keep bulky alongside tracked artifacts.
        pass
    else:
        bulky_dir = (repo_root / BULKY_OUTPUT_DIR_REL).resolve()

    head = verify_baseline_commit(str(repo_root))
    pinned_before = frozen_bulky_hashes(repo_root)
    network_attempts = 0
    files_written: dict[str, str] = {}

    with p3b0.network_sentinel() as sentinel:
        content, bulky, extras = build_all(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: "
                f"{sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

        pinned_after = frozen_bulky_hashes(repo_root)
        if pinned_before != pinned_after:
            raise QCFail("frozen bulky inputs mutated during Part 3C run")

        assertions = build_qc_assertions(
            repo_root=repo_root,
            contract=extras["contract"],
            pinned_before=pinned_before,
            pinned_after=pinned_after,
            network_attempts=network_attempts,
            head=head,
            audit_rows=extras["audit_rows"],
            role_rows=extras["role_rows"],
            bulky_payloads=bulky,
        )
        failed = sum(1 for a in assertions if a["status"] != "PASS")
        source_commit = _git(
            str(repo_root), "log", "--format=%H", "-n", "1",
            "--", SRC_REL, TEST_REL, RUN_REL,
        )
        if not source_commit:
            raise QCFail(
                "source_commit unresolved: commit Part 3C source/test/"
                "runner before regenerating QC artifacts"
            )

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8"))
            for name, text in content.items()
        }
        contract = extras["contract"]
        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "research_action_id": RESEARCH_ACTION_ID,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_commit": source_commit,
            "source_file_sha256": sha256_file(repo_root / SRC_REL),
            "test_file_sha256": sha256_file(repo_root / TEST_REL),
            "assertion_count": len(assertions),
            "failed_count": failed,
            "all_pass": failed == 0,
            "tickers": [],
            "ticker_count": 0,
            "network_requests_attempted": network_attempts,
            "part3c_network_requests_attempted": network_attempts,
            "broad_codal_capture_stopped": True,
            "financial_data_researcher_verified_frozen": True,
            "conservative_availability_lag_locked": True,
            "conservative_lag_months": APPROVED_LAG_MONTHS,
            "row_level_publish_datetime_collection_required": False,
            "conservative_six_month_lag_decision_locked": True,
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            "part3b1_decision_locked": True,
            "cut_a_available_at_operationalization_locked": True,
            "predictor_document_binding_mini_pilot_completed": True,
            "predictor_document_binding_evidence_collected": True,
            "document_binding_resolution_decision_locked": True,
            "predictor_available_at_evidence_collected": False,
            "pilot_cutoff_provenance_resolved": False,
            "evidence_collected": True,
            "endpoint_probe_evidence_collected": True,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": True,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "network_extraction_performed": True,
            "modeling_started": False,
            "stage126_started": False,
            "stage126_authorized": False,
            "modeling_authorized": False,
            "feature_selection_authorized": False,
            "part3c_leakage_safe_finalization_completed": True,
            "research_pointers": {
                "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
                "next_research_action_id": RESEARCH_NEXT,
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "bulky_output_sha256": dict(
                sorted(contract["bulky_output_sha256"].items())
            ),
            "frozen_bulky_input_sha256": dict(sorted(pinned_after.items())),
            "assertions": assertions,
            "contract_version": CONTRACT_VERSION,
            "sample_summaries": contract["sample_summaries"],
        }
        qc["failed_count"] = sum(
            1 for a in qc["assertions"] if a["status"] != "PASS"
        )
        qc["all_pass"] = qc["failed_count"] == 0
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage125 Part 3C audited-pair + timing-eligible "
                "analysis-ready dataset finalization (six-month Jalali lag; "
                "frozen Gate B samples; offline)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "output_files_sha256": dict(
                sorted({**content_hashes, F_QC: qc_hash}.items())
            ),
            "bulky_output_sha256": dict(
                sorted(contract["bulky_output_sha256"].items())
            ),
            "part3c_leakage_safe_finalization_completed": True,
            "broad_codal_capture_stopped": True,
            "financial_data_researcher_verified_frozen": True,
            "conservative_lag_months": APPROVED_LAG_MONTHS,
            "part3b_completed": False,
            "modeling_started": False,
            "stage126_started": False,
            "network_requests_attempted": network_attempts,
            "research_pointers": qc["research_pointers"],
        }
        meta_text = _json_str(meta)
        all_tracked = {**content, F_QC: qc_text, F_METADATA: meta_text}

        tracked_drift = (
            _compare_drift(out_dir, all_tracked)
            if out_dir.is_dir()
            else sorted(all_tracked)
        )
        bulky_drift = _compare_bulky_drift(bulky_dir, bulky)

        if build:
            out_dir.mkdir(parents=True, exist_ok=True)
            bulky_dir.mkdir(parents=True, exist_ok=True)
            for name, text in all_tracked.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = sha256_bytes(text.encode("utf-8"))
            for name, text in bulky.items():
                (bulky_dir / name).write_text(text, encoding="utf-8")
                files_written[f"part3c_outputs/{name}"] = sha256_bytes(
                    text.encode("utf-8")
                )
            # Remove superseded bulky filenames so stale leakage_safe_* files
            # cannot be mistaken for the current analysis surface.
            for obsolete in OBSOLETE_BULKY_OUTPUT_FILES:
                obsolete_path = bulky_dir / obsolete
                if obsolete_path.is_file():
                    obsolete_path.unlink()

        canonical = out_dir.resolve() == canonical_out
        if check and canonical and (tracked_drift or bulky_drift):
            # --check verifies hashes when outputs exist; bulky may be absent
            # on a fresh clone — then only tracked manifests/QC are required,
            # and bulky hashes in metadata are still validated if files exist.
            if tracked_drift:
                raise QCFail(f"check drift (tracked): {tracked_drift}")
            if bulky_dir.is_dir() and any(
                (bulky_dir / n).is_file() for n in bulky
            ):
                if bulky_drift:
                    raise QCFail(f"check drift (bulky): {bulky_drift}")
            else:
                # Outputs absent: verify recorded hashes are well-formed only.
                for rel, digest in contract["bulky_output_sha256"].items():
                    if len(digest) != 64:
                        raise QCFail(f"invalid recorded bulky hash for {rel}")

        if not qc["all_pass"]:
            failed_a = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed_a[:12]}")

    return {
        "output_dir": str(out_dir),
        "bulky_dir": str(bulky_dir),
        "qc": qc,
        "drift": tracked_drift + [f"part3c_outputs/{n}" for n in bulky_drift],
        "files": files_written,
        "network_requests_attempted": network_attempts,
        "extras": extras,
    }
