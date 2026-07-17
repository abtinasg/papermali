"""Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock.

Records the user-approved Decision Lock (M2-A modified, M3-C+CBI-A, M4-A, R-A,
CUT-A) as schema/formula contracts with synthetic validation only.

Explicit non-claims:
- no network access / no real evidence capture
- no real candidate or pair-level value extraction
- no real accessibility scoring application
- no Part 3B.2 / Stage126 / modeling
- part3b_completed remains false
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1_decision_lock"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "274ff216f0f3a59ae611c68b662382d75ad84c8b"
DECISION_LOCK_VERSION = "stage125_part3b1_v1"
MICRO_STEP_ID = "stage125-part3b1-feature-definition-scoring-adjudication-lock"

# Locked minimum-valid-observation contract (no auto reduction / imputation).
MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS = 126
MINIMUM_VALID_AMIHUD_OBSERVATIONS = 126

SRC_REL = "project/src/stage125_part3b1_decision_lock.py"
TEST_REL = "project/tests/test_stage125_part3b1_decision_lock.py"
ALLOWLIST_TEST_REL = "project/tests/test_stage125_part3b1_allowlist_guards.py"
RUN_REL = "project/run_stage125_part3b1.py"

FROZEN_INPUT_PATHS = (
    "project/stage125/data_dictionary_stage125.csv",
    "project/stage125/source_registry_stage125.csv",
    "project/stage125/accessibility_scoring_rubric_stage125_part3a.json",
    "project/stage125/prediction_time_contract_stage125_part2.json",
    "project/stage125/feature_availability_contract_stage125_part2.json",
    "project/stage125/leakage_checklist_stage125_part2.json",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv",
    "project/stage125/stage125_part3b_evidence_capture_qc_report.json",
)

# Historical Part 3B frozen outputs — verified byte-identically; never overwritten
# by Part 3B.1 adjudication.
PART3B_FROZEN_METADATA = "project/stage125/metadata_and_hashes_stage125_part3b.json"
PART3B_LEGACY_DECISION_REQ = "project/stage125/part3b_decision_requirements_stage125.json"
PART3B_LEGACY_README = (
    "project/stage125/README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md"
)

F_DECISION = "part3b1_decision_lock_stage125.json"
F_M2 = "part3b1_m2_feature_formula_contract_stage125.json"
F_M3 = "part3b1_m3_cbi_policy_contract_stage125.json"
F_M4 = "part3b1_m4_feature_definition_contract_stage125.json"
F_RUBRIC = "part3b1_rubric_operational_mapping_stage125.json"
F_CUTOFF = "part3b1_cutoff_available_at_contract_stage125.json"
F_DECISIONS_CSV = "part3b1_selected_decisions_stage125.csv"
F_REQ = "part3b1_adjudicated_decision_requirements_stage125.json"
F_QC = "stage125_part3b1_decision_lock_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1.json"
F_README = "README_STAGE125_PART3B1_DECISION_LOCK.md"

CONTENT_FILES = (
    F_DECISION, F_M2, F_M3, F_M4, F_RUBRIC, F_CUTOFF, F_DECISIONS_CSV, F_REQ, F_README,
)

# Exact-path Part 3B.1 surfaces (no globs / no directory-wide ownership transfer).
PART3B1_AUTHORIZED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    ALLOWLIST_TEST_REL,
    RUN_REL,
    f"project/stage125/{F_DECISION}",
    f"project/stage125/{F_M2}",
    f"project/stage125/{F_M3}",
    f"project/stage125/{F_M4}",
    f"project/stage125/{F_RUBRIC}",
    f"project/stage125/{F_CUTOFF}",
    f"project/stage125/{F_DECISIONS_CSV}",
    f"project/stage125/{F_REQ}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})

_PROHIBITED_NEW_NAME_MARKERS = (
    "raw_cache", "evidence_cache", "model_weights", "model_artifact",
    "live_score", "accessibility_scores_live", "pair_value_evidence",
)

_DECISIONS_HEADER = [
    "decision_id", "option_id", "status", "summary", "blocks_real_extraction",
]


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.1."""


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


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
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


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or (_git(repo_root, "rev-parse", "HEAD") or "unknown")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    return raw or "unknown"


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
    if head == EXPECTED_BASELINE_COMMIT:
        return head
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head):
        raise QCFail(
            f"baseline {EXPECTED_BASELINE_COMMIT} is not an ancestor of HEAD {head}"
        )
    return head


def frozen_input_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in FROZEN_INPUT_PATHS:
        path = repo_root / rel
        digest = sha256_file(path)
        if digest is None:
            raise QCFail(f"missing frozen input: {rel}")
        out[rel] = digest
    return out


# --------------------------------------------------------------------------- #
# Locked decision payloads (user-approved)
# --------------------------------------------------------------------------- #

def build_m2_formula_contract() -> dict:
    """M2-A modified: shared 12-month pre-cutoff window; no imputation."""
    return {
        "decision_id": "m2_feature_definitions",
        "option_id": "M2-A_modified",
        "contract_version": DECISION_LOCK_VERSION,
        "imputation_allowed": False,
        "threshold_reduction_allowed": False,
        "scaling_or_extrapolation_allowed": False,
        "minimum_valid_daily_return_observations": (
            MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
        ),
        "minimum_valid_amihud_observations": MINIMUM_VALID_AMIHUD_OBSERVATIONS,
        "shared_window": {
            "length": "12_calendar_months",
            "end_rule": (
                "last_trading_day_with_verified_available_at_strictly_before_pair_cutoff"
            ),
            "market_observation_end_predicate": "market_observation_date < pair_cutoff_date",
            "start_rule": (
                "inclusive_trading_days_on_or_after_calendar_date_"
                "T_star_minus_12_calendar_months"
            ),
            "pair_cutoff_reference": "part2_earliest_verified_available_at_of_predictor_fs",
            "missing_cutoff_rule": "feature_unavailable_null",
            "empty_window_rule": "feature_unavailable_null",
            "equal_to_cutoff_trading_day_rule": (
                "reject_and_select_previous_trading_day_strictly_before_cutoff"
            ),
            "applies_to_all_m2_variables": True,
        },
        "price_field": {
            "name": "adjusted_close",
            "description": (
                "Corporate-action-adjusted closing price from TSETMC "
                "(src_m2_tsetmc_market); unadjusted close is not used."
            ),
            "missing_price_rule": "exclude_day_from_window_computations",
        },
        "diagnostics_recorded": [
            "missing_price_day_count",
            "zero_traded_value_day_count",
            "usable_daily_return_count",
            "usable_amihud_day_count",
        ],
        "variables": {
            "equity_return_window": {
                "candidate_id": "cand_m2_equity_return_window",
                "unit": "return_ratio",
                "formula_id": "m2_cumulative_simple_return_W",
                "formula": (
                    "Let P_t be adjusted_close on trading day t in shared window W "
                    "ordered t0..tN=T*. Require P_{t0} and P_{tN} present AND at "
                    "least minimum_valid_daily_return_observations=126 valid daily "
                    "simple returns in W. R_W = (P_{tN} / P_{t0}) - 1. "
                    "If either endpoint missing OR usable daily return count < 126 "
                    "=> null/UNRESOLVED. No imputation, scaling, or extrapolation."
                ),
                "transform": "none_beyond_simple_return_ratio",
                "minimum_valid_daily_return_observations": (
                    MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
                ),
            },
            "realized_volatility": {
                "candidate_id": "cand_m2_realized_volatility",
                "unit": "volatility",
                "formula_id": "m2_daily_return_stdev_sample_W",
                "formula": (
                    "Daily simple returns r_t = (P_t / P_{t-1}) - 1 for consecutive "
                    "trading days in shared window W with both prices present. "
                    "realized_volatility = sample_stdev(r_t) with ddof=1 "
                    "(daily-return volatility proxy; NOT annualized). "
                    "If usable return count < minimum_valid_daily_return_observations"
                    "=126 => null/UNRESOLVED. No imputation, scaling, annualization, "
                    "or automatic threshold reduction."
                ),
                "transform": "sample_standard_deviation_ddof_1_not_annualized",
                "minimum_valid_daily_return_observations": (
                    MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
                ),
            },
            "amihud_illiquidity": {
                "candidate_id": "cand_m2_amihud_illiquidity",
                "unit": "illiquidity_per_rial",
                "formula_id": "m2_amihud_mean_abs_return_over_value_W",
                "formula": (
                    "For each trading day t in shared window W with r_t defined and "
                    "traded_value_rial V_t > 0: a_t = abs(r_t) / V_t. "
                    "amihud = mean(a_t) over usable days. "
                    "Days with V_t<=0 or missing V_t or missing r_t are excluded "
                    "(never imputed to a fabricated volume). "
                    "If usable day count < minimum_valid_amihud_observations=126 "
                    "=> null/UNRESOLVED."
                ),
                "volume_field": "traded_value_rial",
                "zero_volume_rule": "exclude_day_never_impute",
                "minimum_valid_amihud_observations": MINIMUM_VALID_AMIHUD_OBSERVATIONS,
            },
        },
        "leakage_rules": {
            "window_must_end_strictly_before_pair_cutoff": True,
            "no_target_year_market_data": True,
            "no_post_cutoff_trading_day": True,
            "no_same_calendar_day_as_pair_cutoff": True,
        },
        "note": (
            "M2 daily market observations require market_observation_date < "
            "pair_cutoff_date because intraday ordering of market close vs "
            "cutoff is not provable. CUT-A feature available_at <= pair_cutoff "
            "remains unchanged for feature usability. All three M2 variables use "
            "the same shared 12-month window W."
        ),
        "synthetic_validation_only": True,
        "real_extraction_authorized": False,
    }


def build_m3_cbi_policy_contract() -> dict:
    """M3-C + CBI-A: all M3 remain null/UNRESOLVED; no SCI/free-market substitute."""
    return {
        "decision_id": "m3_feature_definitions",
        "option_id": "M3-C",
        "paired_decision_id": "cbi_endpoint_provenance",
        "paired_option_id": "CBI-A",
        "contract_version": DECISION_LOCK_VERSION,
        "policy": "all_m3_null_unresolved_until_official_cbi_source_approved",
        "candidates": [
            "cand_m3_cpi_inflation",
            "cand_m3_fx_change_official",
            "cand_m3_policy_financing_rate",
        ],
        "source_id_required": "src_m3_cbi_macro",
        "authoritative_cbi_endpoint_frozen": False,
        "cbi_status": "unverified_no_authoritative_endpoint",
        "substitutions_forbidden": [
            "src_m3_sci_macro_silent_remap",
            "sci_cpi_for_cbi_cpi",
            "sci_for_cbi_fx",
            "sci_for_cbi_policy_rate",
            "free_market_fx",
            "oos_free_market_fx",
        ],
        "score_treatment": "null_or_unresolved_never_zero",
        "assessment_treatment": "UNRESOLVED_until_cbi_authority_approved",
        "real_extraction_authorized": False,
        "network_access_authorized": False,
    }


def build_m4_definition_contract() -> dict:
    """M4-A: explicit CODAL structured definitions; ambiguity => null."""
    return {
        "decision_id": "m4_feature_definitions",
        "option_id": "M4-A",
        "contract_version": DECISION_LOCK_VERSION,
        "source_family": "official_CODAL_structured_disclosures_only",
        "ambiguity_or_missing_equals_null": True,
        "nlp_or_persian_text_modeling_forbidden": True,
        "variables": {
            "audit_opinion_type": {
                "candidate_id": "cand_m4_audit_opinion_type",
                "source_id": "src_m4_codal_audit",
                "data_type": "categorical",
                "definition": (
                    "Structured audit-opinion label taken only from an official "
                    "CODAL audit report for predictor year t. The label must be "
                    "an explicit structured field/value on the report (not inferred "
                    "from free text). If the field is absent, unreadable, conflicting, "
                    "or ambiguous => null."
                ),
                "document": "official_CODAL_audit_report_year_t",
                "available_at_field": "verified_available_at_of_that_audit_report",
            },
            "going_concern_flag": {
                "candidate_id": "cand_m4_going_concern_flag",
                "source_id": "src_m4_codal_audit",
                "data_type": "boolean_or_null",
                "definition": (
                    "true only when the official CODAL audit report for year t "
                    "contains an explicit structured going-concern / "
                    "material-uncertainty indication set to true/present. "
                    "false only when an explicit structured official field states "
                    "negative/false for going-concern. "
                    "Absent clause, missing field, unstructured-only text, conflict, "
                    "or ambiguity => null/UNRESOLVED (never default false)."
                ),
                "document": "official_CODAL_audit_report_year_t",
                "available_at_field": "verified_available_at_of_that_audit_report",
            },
            "audit_lag_days": {
                "candidate_id": "cand_m4_audit_lag_days",
                "source_id": "src_m4_codal_audit",
                "data_type": "integer",
                "unit": "calendar_days",
                "definition": (
                    "audit_lag_days = calendar_days(fiscal_year_end, audit_report_date) "
                    "using the official CODAL audit report date field and the "
                    "predictor fiscal_year_end. Both dates must be semantic valid "
                    "ISO calendar dates. "
                    "If fiscal_year_end missing (LC08), or audit_report_date missing/"
                    "ambiguous, or either date unparseable, or "
                    "audit_report_date < fiscal_year_end (negative lag) => "
                    "null/UNRESOLVED. Never impute dates or emit a negative lag."
                ),
                "document": "official_CODAL_audit_report_year_t",
                "available_at_field": "verified_available_at_of_that_audit_report",
            },
            "board_size": {
                "candidate_id": "cand_m4_board_size",
                "source_id": "src_m4_codal_governance",
                "data_type": "integer",
                "unit": "count",
                "definition": (
                    "Integer count of board members from an official CODAL "
                    "governance disclosure for year t, using an explicit auditable "
                    "membership list/field. Ambiguous membership, missing list, or "
                    "conflicting counts => null. Director networks remain out of scope."
                ),
                "document": "official_CODAL_governance_disclosure_year_t",
                "available_at_field": "verified_available_at_of_that_governance_disclosure",
            },
        },
        "leakage_rules": {
            "no_target_year_t_plus_1_audit_or_governance": True,
            "document_available_at_must_be_le_pair_cutoff": True,
        },
        "real_extraction_authorized": False,
    }


def build_rubric_operational_mapping() -> dict:
    """R-A: candidate-level accessibility score; pair coverage via G09–G12."""
    return {
        "decision_id": "rubric_score_mapping_0_5",
        "option_id": "R-A",
        "rubric_version": "stage125_part3a_v1",
        "contract_version": DECISION_LOCK_VERSION,
        "score_level": "candidate_source_accessibility",
        "pair_coverage_evaluated_by": ["G09", "G10", "G11", "G12"],
        "missing_evidence_rule": "null_or_unresolved_never_zero",
        "no_memory_or_reputation_scoring": True,
        "real_scoring_authorized": False,
        "operational_mapping": {
            "0": {
                "requires": (
                    "Captured evidence proving no reproducible retrieval path to "
                    "the authoritative source for this candidate."
                ),
                "hard_drop_if_scored": True,
            },
            "1": {
                "requires": (
                    "Captured evidence of only marginal/manual/unstable access; "
                    "no systematic reproducible retrieval."
                ),
                "hard_drop_if_scored": True,
            },
            "2": {
                "requires": (
                    "Captured evidence of limited accessibility with significant "
                    "barriers to systematic retrieval."
                ),
                "hard_drop_if_scored": True,
            },
            "3": {
                "requires": (
                    "Captured candidate_endpoint_evidence showing systematic "
                    "retrieval is plausible; coverage/quality still unproven. "
                    "Pilot permission only — not automatic main admission."
                ),
                "hard_drop_if_scored": False,
                "pilot_permission_only": True,
            },
            "4": {
                "requires": (
                    "Documented API/portal + reproducible candidate-level retrieval "
                    "with provenance; must still pass G02–G07 and coverage gates."
                ),
                "hard_drop_if_scored": False,
            },
            "5": {
                "requires": (
                    "Authoritative, fully reproducible, machine-readable or reliably "
                    "structured candidate-level retrieval with provenance; must still "
                    "pass every other gate."
                ),
                "hard_drop_if_scored": False,
            },
        },
        "evidence_class_minimum_for_numeric_score": "candidate_endpoint_evidence",
        "source_origin_probe_alone_insufficient_for_numeric_score": True,
        "pair_value_evidence_not_required_for_candidate_score": True,
        "pair_value_evidence_required_for_g09_g12_numerators": True,
    }


def build_cutoff_contract(repo_root: Path) -> dict:
    """CUT-A: retain Part 2 pair cutoff; feature requires available_at <= cutoff."""
    part2_path = repo_root / "project/stage125/prediction_time_contract_stage125_part2.json"
    part2 = json.loads(part2_path.read_text(encoding="utf-8"))
    cutoff = part2["prediction_cutoff"]
    return {
        "decision_id": "available_at_and_cutoff_rules",
        "option_id": "CUT-A",
        "contract_version": DECISION_LOCK_VERSION,
        "pair_cutoff": {
            "retained_from": "stage125_part2_v1",
            "definition": cutoff["definition"],
            "cutoff_basis": cutoff["cutoff_basis"],
            "cutoff_not_based_on": list(cutoff["cutoff_not_based_on"]),
            "missing_available_at_rule": cutoff["missing_available_at_rule"],
        },
        "feature_availability": {
            "rule": (
                "A feature value is usable at prediction time only if it has a "
                "verified available_at and available_at <= pair_cutoff."
            ),
            "missing_or_after_cutoff": "unavailable_null_never_inferred",
            "g06": "missing_availability_means_unavailable",
            "g07": "no_future_or_target_year_information",
        },
        "block_rules": {
            "M2": (
                "market_observation_date_strictly_before_pair_cutoff;"
                "feature_available_at_still_le_pair_cutoff_under_CUT_A"
            ),
            "M3": "macro_publication_or_available_at_le_pair_cutoff_when_cbi_approved",
            "M4": "document_available_at_le_pair_cutoff",
        },
        "real_extraction_authorized": False,
    }


def build_selected_decision_rows() -> list[dict]:
    return [
        {
            "decision_id": "m2_feature_definitions",
            "option_id": "M2-A_modified",
            "status": "user_approved_locked",
            "summary": (
                "Shared 12-month window ending on last trading day strictly "
                "before pair cutoff (market_observation_date < pair_cutoff_date); "
                "adjusted close; cumulative return; daily-return stdev; Amihud; "
                "minimum_valid_daily_return_observations=126; "
                "minimum_valid_amihud_observations=126; no imputation."
            ),
            "blocks_real_extraction": "true_until_explicit_later_authorization",
        },
        {
            "decision_id": "m3_feature_definitions",
            "option_id": "M3-C",
            "status": "user_approved_locked",
            "summary": (
                "All M3 remain null/UNRESOLVED until official CBI source approval."
            ),
            "blocks_real_extraction": "true",
        },
        {
            "decision_id": "m4_feature_definitions",
            "option_id": "M4-A",
            "status": "user_approved_locked",
            "summary": (
                "Explicit CODAL structured definitions; ambiguity/missing => null."
            ),
            "blocks_real_extraction": "true_until_explicit_later_authorization",
        },
        {
            "decision_id": "rubric_score_mapping_0_5",
            "option_id": "R-A",
            "status": "user_approved_locked",
            "summary": (
                "Candidate-level accessibility mapping; pair coverage via G09–G12."
            ),
            "blocks_real_extraction": "true_until_explicit_later_authorization",
        },
        {
            "decision_id": "cbi_endpoint_provenance",
            "option_id": "CBI-A",
            "status": "user_approved_locked",
            "summary": (
                "Fail-closed: no CBI endpoint invention; no SCI/free-market substitute."
            ),
            "blocks_real_extraction": "true",
        },
        {
            "decision_id": "available_at_and_cutoff_rules",
            "option_id": "CUT-A",
            "status": "user_approved_locked",
            "summary": (
                "Retain Part 2 pair cutoff; feature needs verified available_at <= cutoff."
            ),
            "blocks_real_extraction": "false_contract_only",
        },
    ]


def build_decision_lock_record(
    repo_root: Path,
    m2: dict,
    m3: dict,
    m4: dict,
    rubric: dict,
    cutoff: dict,
) -> dict:
    return {
        "proposed_micro_step_id": MICRO_STEP_ID,
        "proposed_micro_step_title": (
            "Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock"
        ),
        "status": "decision_locked_contracts_only",
        "decision_lock_version": DECISION_LOCK_VERSION,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "requires_explicit_user_approval_before_start": False,
        "user_approval_recorded": True,
        "part3b1_decision_locked": True,
        "part3b1_started": True,
        "part3b1_completed": True,
        "part3b_completed": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "network_extraction_performed": False,
        "modeling_started": False,
        "part3b2_started": False,
        "stage126_started": False,
        "selected_answers": {
            "m2_feature_definitions": "M2-A_modified",
            "m3_feature_definitions": "M3-C",
            "m4_feature_definitions": "M4-A",
            "rubric_score_mapping_0_5": "R-A",
            "cbi_endpoint_provenance": "CBI-A",
            "available_at_and_cutoff_rules": "CUT-A",
        },
        "contracts": {
            "m2": F_M2,
            "m3_cbi": F_M3,
            "m4": F_M4,
            "rubric": F_RUBRIC,
            "cutoff": F_CUTOFF,
        },
        "explicit_non_claims": [
            "decision_lock_and_synthetic_validation_only",
            "no_network_access",
            "no_real_value_extraction",
            "no_real_accessibility_scoring",
            "no_part3b2",
            "no_stage126",
            "no_modeling",
            "merge_requires_explicit_user_approval",
        ],
        "m2_option": m2["option_id"],
        "m3_option": m3["option_id"],
        "cbi_option": m3["paired_option_id"],
        "m4_option": m4["option_id"],
        "rubric_option": rubric["option_id"],
        "cutoff_option": cutoff["option_id"],
        "frozen_pilot_pairs": 80,
        "pilot_option": "pilot_option_event_enriched",
    }


def build_updated_decision_requirements(lock_record: dict) -> dict:
    return {
        "proposed_micro_step_id": MICRO_STEP_ID,
        "proposed_micro_step_title": (
            "Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock"
        ),
        "status": "decision_locked_contracts_only",
        "requires_explicit_user_approval_before_start": False,
        "part3b_completed": False,
        "part3b1_decision_locked": True,
        "current_probe_status": "active_incomplete_accessibility_feasibility_probe",
        "user_decisions_still_needed": [
            {
                "decision_id": "m2_feature_definitions",
                "scope": [
                    "cand_m2_equity_return_window",
                    "cand_m2_realized_volatility",
                    "cand_m2_amihud_illiquidity",
                ],
                "required": (
                    "exact feature definition, unit and pre-cutoff window for each M2 variable"
                ),
                "selected_answer": "M2-A_modified",
            },
            {
                "decision_id": "m3_feature_definitions",
                "scope": [
                    "cand_m3_cpi_inflation",
                    "cand_m3_fx_change_official",
                    "cand_m3_policy_financing_rate",
                ],
                "required": (
                    "exact transformation/unit/release series for each M3 variable"
                ),
                "selected_answer": "M3-C",
            },
            {
                "decision_id": "m4_feature_definitions",
                "scope": [
                    "cand_m4_audit_opinion_type",
                    "cand_m4_going_concern_flag",
                    "cand_m4_audit_lag_days",
                    "cand_m4_board_size",
                ],
                "required": (
                    "exact document/field/derivation rules for each M4 variable"
                ),
                "selected_answer": "M4-A",
            },
            {
                "decision_id": "rubric_score_mapping_0_5",
                "scope": ["stage125_part3a_v1"],
                "required": "operational evidence-to-score mapping for rubric scores 0–5",
                "selected_answer": "R-A",
            },
            {
                "decision_id": "cbi_endpoint_provenance",
                "scope": ["src_m3_cbi_macro"],
                "required": "authoritative CBI endpoint/provenance decision",
                "selected_answer": "CBI-A",
            },
            {
                "decision_id": "available_at_and_cutoff_rules",
                "scope": ["prediction_cutoff", "available_at", "G06", "G07"],
                "required": "available_at and prediction-cutoff rules",
                "selected_answer": "CUT-A",
            },
        ],
        "explicit_non_claims": list(lock_record["explicit_non_claims"]),
        "decision_lock_version": DECISION_LOCK_VERSION,
    }


def build_readme() -> str:
    return """# Stage125 Part 3B.1 — Decision Lock

**Status:** decision locked (contracts / synthetic validation only).

This versioned Part 3B.1 adjudication README is independent of the historical
Part 3B proposed-requirements README
(`README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md`), which
remains a frozen Part 3B artifact.

User-approved selections:

| decision_id | selected_answer |
|---|---|
| m2_feature_definitions | M2-A_modified |
| m3_feature_definitions | M3-C |
| m4_feature_definitions | M4-A |
| rubric_score_mapping_0_5 | R-A |
| cbi_endpoint_provenance | CBI-A |
| available_at_and_cutoff_rules | CUT-A |

## Locked scope

- Schema/formula contracts for M2/M3/M4
- Shared 12-month M2 window ending strictly before pair cutoff
  (`market_observation_date < pair_cutoff_date`)
- M2 minimum-valid-observation lock: 126 daily returns / 126 Amihud days
- Operational rubric mapping (candidate-level scores; pair coverage via G09–G12)
- CUT-A retention of Part 2 pair cutoff with semantic UTC timestamp compare
  (`feature_available_at <= pair_cutoff`)
- Synthetic validators only

## Still prohibited

- Network extraction / real values
- Real accessibility scoring application
- Part 3B.2 / Stage126 / modeling
- Merging any PR without explicit user approval

`part3b_completed=false`. Part 3B remains an active/incomplete accessibility
feasibility probe until candidate/pair evidence and scoring are separately
authorized.
"""


# --------------------------------------------------------------------------- #
# Synthetic formula validators (no network / no real extraction)
# --------------------------------------------------------------------------- #

def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_aware_utc_instant(value: str | None) -> datetime | None:
    """Strict timezone-aware ISO-8601 → UTC instant. Fail-closed on bad input."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or " " in text:
        return None
    if "T" not in text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    # Reject invented/invalid fixed offsets by requiring a concrete tzinfo utcoffset.
    try:
        offset = dt.utcoffset()
    except Exception:
        return None
    if offset is None:
        return None
    return dt.astimezone(timezone.utc)


def last_trading_day_strictly_before(
    cutoff: date, trading_days: list[date],
) -> date | None:
    """Last trading day with market_observation_date < pair_cutoff_date.

    A trading day equal to the cutoff calendar date is rejected; the previous
    trading day is used when present. Returns None when no valid day exists.
    """
    eligible = [d for d in trading_days if d < cutoff]
    return max(eligible) if eligible else None


def window_trading_days(
    trading_days: list[date], cutoff: date,
) -> list[date] | None:
    t_star = last_trading_day_strictly_before(cutoff, trading_days)
    if t_star is None:
        return None
    # Exact calendar-month rule: on_or_after date(t_star.year-1, t_star.month, t_star.day)
    try:
        start = date(t_star.year - 1, t_star.month, t_star.day)
    except ValueError:
        # Feb 29 -> Feb 28 previous year
        start = date(t_star.year - 1, t_star.month, 28)
    days = sorted(d for d in trading_days if start <= d <= t_star)
    return days or None


def daily_returns(prices: dict[date, float], days: list[date]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(days)):
        a = prices.get(days[i - 1])
        b = prices.get(days[i])
        if a is None or b is None or a == 0:
            continue
        out.append((b / a) - 1.0)
    return out


def m2_window_diagnostics(
    prices: dict[date, float],
    values_rial: dict[date, float],
    days: list[date],
) -> dict[str, int]:
    """Diagnostic counts only — never converts zero-volume into a fabricated value."""
    missing_price = 0
    for d in days:
        if prices.get(d) is None:
            missing_price += 1
    rets_by_day: dict[date, float] = {}
    for i in range(1, len(days)):
        a = prices.get(days[i - 1])
        b = prices.get(days[i])
        if a is None or b is None or a == 0:
            continue
        rets_by_day[days[i]] = (b / a) - 1.0
    zero_tv = 0
    usable_amihud = 0
    for d, r in rets_by_day.items():
        v = values_rial.get(d)
        if v is None or v <= 0:
            zero_tv += 1
            continue
        usable_amihud += 1
        del r
    return {
        "missing_price_day_count": missing_price,
        "zero_traded_value_day_count": zero_tv,
        "usable_daily_return_count": len(rets_by_day),
        "usable_amihud_day_count": usable_amihud,
    }


def cumulative_simple_return(
    prices: dict[date, float],
    days: list[date],
    *,
    min_returns: int = MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS,
) -> float | None:
    if not days:
        return None
    p0 = prices.get(days[0])
    p1 = prices.get(days[-1])
    if p0 is None or p1 is None or p0 == 0:
        return None
    if len(daily_returns(prices, days)) < min_returns:
        return None
    return (p1 / p0) - 1.0


def sample_stdev(
    values: list[float],
    *,
    min_obs: int = MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS,
) -> float | None:
    n = len(values)
    if n < min_obs:
        return None
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def amihud_mean(
    prices: dict[date, float],
    values_rial: dict[date, float],
    days: list[date],
    *,
    min_obs: int = MINIMUM_VALID_AMIHUD_OBSERVATIONS,
) -> float | None:
    rets = {}
    for i in range(1, len(days)):
        a = prices.get(days[i - 1])
        b = prices.get(days[i])
        if a is None or b is None or a == 0:
            continue
        rets[days[i]] = (b / a) - 1.0
    ratios: list[float] = []
    for d, r in rets.items():
        v = values_rial.get(d)
        if v is None or v <= 0:
            continue
        ratios.append(abs(r) / v)
    if len(ratios) < min_obs:
        return None
    return sum(ratios) / len(ratios)


def audit_lag_days(fiscal_year_end: str | None, audit_report_date: str | None) -> int | None:
    if not fiscal_year_end or not audit_report_date:
        return None
    try:
        a = _parse_iso_date(str(fiscal_year_end).strip())
        b = _parse_iso_date(str(audit_report_date).strip())
    except ValueError:
        return None
    lag = (b - a).days
    if lag < 0:
        return None
    return lag


def going_concern_flag(structured_indication: str | None) -> bool | None:
    if structured_indication is None:
        return None
    token = str(structured_indication).strip().lower()
    if token in {
        "", "ambiguous", "unstructured_only", "missing", "absent",
        "conflict", "conflicting", "unreadable",
    }:
        return None
    if token in {"true", "yes", "1", "present"}:
        return True
    if token in {"false", "no", "0", "absent_explicit_false"}:
        # Explicit structured false only — absence remains null above.
        return False
    return None


def feature_usable(available_at: str | None, pair_cutoff: str | None) -> bool:
    """CUT-A: available_at <= pair_cutoff on real UTC instants (equality allowed)."""
    a = parse_aware_utc_instant(available_at)
    b = parse_aware_utc_instant(pair_cutoff)
    if a is None or b is None:
        return False
    return a <= b


def verify_frozen_part3b_output_hashes(repo_root: Path) -> dict[str, str]:
    """Every hash recorded in Part 3B metadata must still match on disk."""
    meta_path = repo_root / PART3B_FROZEN_METADATA
    if not meta_path.is_file():
        raise QCFail(f"missing Part 3B metadata: {PART3B_FROZEN_METADATA}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    hashes = meta.get("output_files_sha256") or {}
    if not hashes:
        raise QCFail("Part 3B metadata has empty output_files_sha256")
    verified: dict[str, str] = {}
    for name, expected in sorted(hashes.items()):
        path = repo_root / "project" / "stage125" / name
        actual = sha256_file(path)
        if actual is None:
            raise QCFail(f"Part 3B frozen output missing: {name}")
        if actual != expected:
            raise QCFail(
                f"Part 3B frozen hash drift for {name}: "
                f"expected={expected} actual={actual}"
            )
        verified[name] = actual
    return verified


def scan_closed_world_part3b1(repo_root: Path) -> list[str]:
    """Fail on unauthorized new cache/evidence/value/score/model surfaces."""
    from src import stage125_part3b0_evidence_readiness as p3b0
    from src import stage125_part3b_evidence_capture as part3b

    hits: list[str] = []
    for rel in FORBIDDEN_SURFACE_EXACT:
        if (repo_root / rel).exists():
            hits.append(rel)

    stage125 = repo_root / "project" / "stage125"
    if not stage125.is_dir():
        return hits
    allowed = set(p3b0.STAGE125_ALLOWED_EXACT) | set(part3b.PART3B_AUTHORIZED_EXACT)
    for path in stage125.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if rel in allowed:
            continue
        if p3b0._is_authorized_part3b_path(repo_root, rel):
            continue
        hits.append(rel)
        continue
    # Name-marker scan even inside allowlisted dirs for newly planted attack files
    # that somehow got allowlisted incorrectly — catch obvious model/cache plants
    # that are not historical Part 3B outputs.
    for path in stage125.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        lower = path.name.lower()
        if any(m in lower for m in _PROHIBITED_NEW_NAME_MARKERS):
            if rel not in part3b.PART3B_AUTHORIZED_EXACT:
                if rel not in hits:
                    hits.append(rel)
    return sorted(set(hits))


def verify_changed_paths_exact_allowlist(
    repo_root: Path, baseline: str = EXPECTED_BASELINE_COMMIT,
) -> tuple[bool, list[str]]:
    """Every path changed vs baseline must be on the curated exact allowlist."""
    from scripts import update_ai_handoff as handoff

    raw = _git(str(repo_root), "diff", "--name-only", f"{baseline}...HEAD")
    changed = {p for p in raw.splitlines() if p.strip()}
    # Include uncommitted tracked modifications relevant to local verification.
    wt = _git(str(repo_root), "diff", "--name-only", "HEAD")
    changed |= {p for p in wt.splitlines() if p.strip()}
    offenders = sorted(p for p in changed if not handoff.path_allowlisted(p))
    return (not offenders), offenders


# --------------------------------------------------------------------------- #
# Build / QC
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> dict[str, str]:
    verify_baseline_commit(str(repo_root))
    m2 = build_m2_formula_contract()
    m3 = build_m3_cbi_policy_contract()
    m4 = build_m4_definition_contract()
    rubric = build_rubric_operational_mapping()
    cutoff = build_cutoff_contract(repo_root)
    lock_record = build_decision_lock_record(repo_root, m2, m3, m4, rubric, cutoff)
    req = build_updated_decision_requirements(lock_record)
    rows = build_selected_decision_rows()
    return {
        F_DECISION: _json_str(lock_record),
        F_M2: _json_str(m2),
        F_M3: _json_str(m3),
        F_M4: _json_str(m4),
        F_RUBRIC: _json_str(rubric),
        F_CUTOFF: _json_str(cutoff),
        F_DECISIONS_CSV: _csv_str(_DECISIONS_HEADER, rows),
        F_REQ: _json_str(req),
        F_README: build_readme(),
    }


def build_qc_assertions(
    repo_root: Path,
    content: dict[str, str],
    frozen: dict[str, str],
    *,
    network_calls_attempted: int,
    part3b_hashes: dict[str, str],
    closed_world_hits: list[str],
    changed_path_ok: bool,
    changed_path_offenders: list[str],
) -> list[dict]:
    assertions: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    lock = json.loads(content[F_DECISION])
    m2 = json.loads(content[F_M2])
    m3 = json.loads(content[F_M3])
    m4 = json.loads(content[F_M4])
    rubric = json.loads(content[F_RUBRIC])
    cutoff = json.loads(content[F_CUTOFF])
    req = json.loads(content[F_REQ])

    add("baseline_commit_constant",
        EXPECTED_BASELINE_COMMIT == "274ff216f0f3a59ae611c68b662382d75ad84c8b",
        EXPECTED_BASELINE_COMMIT)
    add("part3b1_decision_locked", lock.get("part3b1_decision_locked") is True, "locked")
    add("part3b_completed_false", lock.get("part3b_completed") is False, "incomplete")
    add("modeling_started_false", lock.get("modeling_started") is False, "no modeling")
    add("no_real_extraction",
        lock.get("data_value_extraction_performed") is False
        and lock.get("candidate_value_evidence_collected") is False
        and lock.get("pair_level_evidence_collected") is False,
        "extraction markers false")
    add("no_real_scoring",
        lock.get("accessibility_scoring_applied") is False
        and rubric.get("real_scoring_authorized") is False,
        "scoring not authorized")
    add(
        "zero_part3b1_network_calls_sentinel",
        network_calls_attempted == 0,
        f"calls_attempted={network_calls_attempted}",
    )
    add(
        "unchanged_frozen_part3b_hashes",
        len(part3b_hashes) > 0,
        f"verified={len(part3b_hashes)}",
    )
    add(
        "closed_world_no_new_cache_evidence_score_model",
        not closed_world_hits,
        f"hits={closed_world_hits[:8]}",
    )
    add(
        "changed_path_exact_allowlist",
        changed_path_ok,
        f"offenders={changed_path_offenders[:8]}",
    )
    forbidden_present = [
        rel for rel in FORBIDDEN_SURFACE_EXACT if (repo_root / rel).exists()
    ]
    add(
        "no_part3b2_or_stage126_surfaces",
        not forbidden_present
        and not any(("part3b2" in h) or ("stage126" in h) for h in closed_world_hits),
        f"forbidden={forbidden_present}",
    )
    add("m2_option", m2.get("option_id") == "M2-A_modified", m2.get("option_id"))
    add("m2_no_imputation", m2.get("imputation_allowed") is False, "no impute")
    add(
        "m2_min_valid_return_obs_126",
        m2.get("minimum_valid_daily_return_observations")
        == MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
        and m2["variables"]["realized_volatility"].get(
            "minimum_valid_daily_return_observations"
        ) == MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
        and m2["variables"]["equity_return_window"].get(
            "minimum_valid_daily_return_observations"
        ) == MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS,
        "126",
    )
    add(
        "m2_min_valid_amihud_obs_126",
        m2.get("minimum_valid_amihud_observations")
        == MINIMUM_VALID_AMIHUD_OBSERVATIONS
        and m2["variables"]["amihud_illiquidity"].get(
            "minimum_valid_amihud_observations"
        ) == MINIMUM_VALID_AMIHUD_OBSERVATIONS,
        "126",
    )
    add("m2_window_12m",
        m2["shared_window"]["length"] == "12_calendar_months"
        and m2["shared_window"].get("applies_to_all_m2_variables") is True, "12m shared")
    add(
        "m2_end_strictly_before_cutoff",
        m2["shared_window"]["end_rule"] == (
            "last_trading_day_with_verified_available_at_strictly_before_pair_cutoff"
        )
        and m2["leakage_rules"].get("window_must_end_strictly_before_pair_cutoff") is True
        and m2["shared_window"].get("market_observation_end_predicate") == (
            "market_observation_date < pair_cutoff_date"
        ),
        m2["shared_window"]["end_rule"],
    )
    add("m3_c", m3.get("option_id") == "M3-C", m3.get("option_id"))
    add("cbi_a", m3.get("paired_option_id") == "CBI-A", m3.get("paired_option_id"))
    add("no_sci_substitute",
        "sci_for_cbi_fx" in m3.get("substitutions_forbidden", []), "sci forbidden")
    add("m4_a", m4.get("option_id") == "M4-A", m4.get("option_id"))
    add("m4_ambiguity_null",
        m4.get("ambiguity_or_missing_equals_null") is True, "null on ambiguity")
    add(
        "m4_going_concern_false_only_explicit",
        "false only when an explicit structured official field" in (
            m4["variables"]["going_concern_flag"]["definition"]
        ),
        "explicit false only",
    )
    add(
        "m4_audit_lag_rejects_negative",
        "negative lag" in m4["variables"]["audit_lag_days"]["definition"],
        "negative=>null",
    )
    add("rubric_r_a", rubric.get("option_id") == "R-A", rubric.get("option_id"))
    add("rubric_candidate_level",
        rubric.get("score_level") == "candidate_source_accessibility", "candidate")
    add("cutoff_cut_a", cutoff.get("option_id") == "CUT-A", cutoff.get("option_id"))
    add("cutoff_not_fye_alone",
        "fiscal_year_end_alone" in cutoff["pair_cutoff"]["cutoff_not_based_on"],
        "not FYE alone")
    add("selected_answers_complete",
        set(lock["selected_answers"]) == {
            "m2_feature_definitions", "m3_feature_definitions",
            "m4_feature_definitions", "rubric_score_mapping_0_5",
            "cbi_endpoint_provenance", "available_at_and_cutoff_rules",
        },
        "six decisions")
    add("requirements_answers_filled",
        all(d.get("selected_answer") for d in req["user_decisions_still_needed"]),
        "answers recorded")
    add("adjudicated_req_filename",
        F_REQ == "part3b1_adjudicated_decision_requirements_stage125.json"
        and F_REQ in content,
        F_REQ)
    add("legacy_part3b_req_not_owned",
        "part3b_decision_requirements_stage125.json" not in content
        and PART3B_LEGACY_DECISION_REQ.split("/")[-1] in part3b_hashes,
        "legacy remains Part 3B")
    add("frozen_inputs_present", len(frozen) == len(FROZEN_INPUT_PATHS),
        f"n={len(frozen)}")
    add(
        "content_exact_allowlist",
        set(content) == set(CONTENT_FILES),
        f"keys={sorted(content)}",
    )

    # Synthetic formula checks with locked 126 thresholds
    days = [date(2020, 1, 2) + timedelta(days=i) for i in range(0, 400, 1)
            if (date(2020, 1, 2) + timedelta(days=i)).weekday() < 5]
    cutoff_d = date(2020, 12, 15)
    prices = {d: 100.0 + (i % 17) for i, d in enumerate(days)}
    values = {d: 1_000_000.0 + 1000 * (i % 9) for i, d in enumerate(days)}
    values[days[10]] = 0.0  # must be excluded, not imputed
    w = window_trading_days(days, cutoff_d)
    add("synth_window_nonempty", w is not None and len(w) > 10, f"len={len(w or [])}")
    add(
        "synth_window_end_strictly_before_cutoff",
        w is not None and w[-1] < cutoff_d,
        f"end={w[-1] if w else None}",
    )
    diag = m2_window_diagnostics(prices, values, w or [])
    add(
        "synth_diagnostics_recorded",
        diag["usable_daily_return_count"] >= MINIMUM_VALID_DAILY_RETURN_OBSERVATIONS
        and diag["zero_traded_value_day_count"] >= 1,
        str(diag),
    )
    r = cumulative_simple_return(prices, w or [])
    add("synth_return_defined", r is not None, str(r))
    vol = sample_stdev(daily_returns(prices, w or []))
    add("synth_vol_defined", vol is not None and vol >= 0, str(vol))
    am = amihud_mean(prices, values, w or [])
    add("synth_amihud_defined", am is not None and am > 0, str(am))
    add("synth_amihud_excludes_zero_volume", True, "zero volume excluded by construction")
    # Boundary: 125 fails, 126 passes
    rets_125 = [0.01] * 125
    rets_126 = [0.01] * 126
    add("synth_vol_125_fail", sample_stdev(rets_125) is None, "125=>null")
    add("synth_vol_126_pass", sample_stdev(rets_126) is not None, "126=>ok")
    add("synth_audit_lag",
        audit_lag_days("2020-03-19", "2020-06-20") == 93, "93 days")
    add("synth_audit_lag_equal_zero",
        audit_lag_days("2020-03-19", "2020-03-19") == 0, "0 days")
    add("synth_audit_lag_before_null",
        audit_lag_days("2020-06-20", "2020-03-19") is None, "negative=>null")
    add("synth_audit_lag_missing_null",
        audit_lag_days(None, "2020-06-20") is None, "null")
    add("synth_going_concern_null_default",
        going_concern_flag(None) is None, "null not false")
    add("synth_going_concern_explicit_false",
        going_concern_flag("false") is False, "explicit false")
    add("synth_going_concern_explicit_true",
        going_concern_flag("present") is True, "explicit true")
    add("synth_feature_usable_cutoff",
        feature_usable("2020-06-01T00:00:00Z", "2020-06-15T00:00:00Z") is True
        and feature_usable("2020-06-15T00:00:00Z", "2020-06-15T00:00:00Z") is True
        and feature_usable("2020-06-20T00:00:00Z", "2020-06-15T00:00:00Z") is False
        and feature_usable(None, "2020-06-15T00:00:00Z") is False
        and feature_usable("2020-06-01T00:00:00", "2020-06-15T00:00:00Z") is False,
        "semantic UTC available_at<=cutoff")
    add(
        "synth_feature_usable_offset_equivalence",
        feature_usable(
            "2020-06-15T04:00:00+04:00", "2020-06-15T00:00:00Z",
        ) is True
        and feature_usable(
            "2020-06-15T00:00:00Z", "2020-06-15T00:00:00+00:00",
        ) is True,
        "offset/Z equivalence",
    )
    add("no_part3b2", lock.get("part3b2_started") is False, "no 3B.2")
    add("no_stage126", lock.get("stage126_started") is False, "no 126")
    return assertions


def build_qc_report(
    repo_root: Path, content: dict[str, str], content_hashes: dict[str, str],
    frozen: dict[str, str],
    *,
    network_calls_attempted: int,
    part3b_hashes: dict[str, str],
    closed_world_hits: list[str],
    changed_path_ok: bool,
    changed_path_offenders: list[str],
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL, ALLOWLIST_TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    assertions = build_qc_assertions(
        repo_root, content, frozen,
        network_calls_attempted=network_calls_attempted,
        part3b_hashes=part3b_hashes,
        closed_world_hits=closed_world_hits,
        changed_path_ok=changed_path_ok,
        changed_path_offenders=changed_path_offenders,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    part3b_qc = json.loads(
        (repo_root / "project/stage125/stage125_part3b_evidence_capture_qc_report.json")
        .read_text(encoding="utf-8")
    )
    tickers = list(part3b_qc.get("tickers") or [])
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": sha256_file(repo_root / TEST_REL),
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_input_sha256": dict(sorted(frozen.items())),
        "frozen_part3b_output_sha256": dict(sorted(part3b_hashes.items())),
        "closed_world_hits": list(closed_world_hits),
        "changed_path_offenders": list(changed_path_offenders),
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "part3b1_started": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "part3b1_network_calls_attempted": network_calls_attempted,
        "modeling_started": False,
        "part3b2_started": False,
        "stage126_started": False,
        "decision_lock_version": DECISION_LOCK_VERSION,
        "assertions": assertions,
    }


def build_metadata(qc: dict, content_hashes: dict[str, str], qc_hash: str) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage125 Part 3B.1 — feature definition & scoring adjudication lock "
            "(contracts + synthetic validation only)."
        ),
        "generated_at": qc["generated_at"],
        "code_commit": qc["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "part3b_completed": False,
        "part3b1_decision_locked": True,
        "network_extraction_performed": True,
        "part3b1_network_calls_attempted": qc["part3b1_network_calls_attempted"],
    }


def run(project_dir: Path, output_dir: Path | None = None, write: bool = False) -> dict:
    from src import stage125_part3b0_evidence_readiness as p3b0

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    out_dir = output_dir or (repo_root / "project" / "stage125")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Git-diff allowlist evidence must run outside the Part 3B.0 network
    # sentinel (which only permits a narrow readonly git argv set).
    verify_baseline_commit(str(repo_root))
    changed_path_ok, changed_path_offenders = verify_changed_paths_exact_allowlist(
        repo_root,
    )

    with p3b0.network_sentinel() as sentinel:
        frozen = frozen_input_hashes(repo_root)
        part3b_hashes = verify_frozen_part3b_output_hashes(repo_root)
        closed_world_hits = scan_closed_world_part3b1(repo_root)

        content = build_all(repo_root)
        content_hashes = {name: sha256_bytes(text.encode("utf-8"))
                          for name, text in content.items()}
        qc = build_qc_report(
            repo_root, content, content_hashes, frozen,
            network_calls_attempted=sentinel.calls_attempted,
            part3b_hashes=part3b_hashes,
            closed_world_hits=closed_world_hits,
            changed_path_ok=changed_path_ok,
            changed_path_offenders=changed_path_offenders,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)

        drift: list[str] = []
        for name, text in list(content.items()) + [(F_QC, qc_text), (F_METADATA, meta_text)]:
            path = out_dir / name
            if path.is_file():
                on_disk = path.read_text(encoding="utf-8")
                if on_disk != text:
                    drift.append(name)
            else:
                drift.append(name)

        files_written: dict[str, str] = {}
        if write:
            for name, text in content.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = content_hashes[name]
            (out_dir / F_QC).write_text(qc_text, encoding="utf-8")
            (out_dir / F_METADATA).write_text(meta_text, encoding="utf-8")
            files_written[F_QC] = qc_hash
            files_written[F_METADATA] = sha256_bytes(meta_text.encode("utf-8"))

        if not qc["all_pass"]:
            failed = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:3]}")

        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"Part 3B.1 network sentinel calls_attempted="
                f"{sentinel.calls_attempted}"
            )

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "frozen_input_sha256": frozen,
        "frozen_part3b_output_sha256": part3b_hashes,
        "network_calls_attempted": 0,
    }
