"""Tests for the Stage128 D2 machine-readable design-freeze package.

Validates internal consistency of project/stage128/*.json against the
authorization scope, the frozen-vs-changed invariants, historical
preservation, and provenance-honesty guarantees. Does not execute any
model, prediction, or canonical Gate.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

STAGE128 = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stage128"
)

FREEZE_PATH = os.path.join(STAGE128, "stage128_m2_d2_design_freeze.json")
AUTH_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_human_authorization_record.json"
)
QC_PATH = os.path.join(STAGE128, "stage128_m2_d2_design_freeze_qc_report.json")
META_PATH = os.path.join(
    STAGE128, "metadata_and_hashes_stage128_m2_d2_design_freeze.json"
)
PROVENANCE_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_feasibility_provenance.json"
)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def freeze():
    return _load(FREEZE_PATH)


@pytest.fixture(scope="module")
def auth():
    return _load(AUTH_PATH)


@pytest.fixture(scope="module")
def qc():
    return _load(QC_PATH)


@pytest.fixture(scope="module")
def meta():
    return _load(META_PATH)


@pytest.fixture(scope="module")
def provenance():
    return _load(PROVENANCE_PATH)


# --------------------------------------------------------------------------- #
# Authorization scope
# --------------------------------------------------------------------------- #

def test_authorization_action_id_consistent(freeze, auth):
    assert (
        freeze["decision_id"]
        == freeze["authorized_action_id"]
        == auth["authorized_action_id"]
        == "stage128-m2-boundary-month-return-design-freeze"
    )


def test_authorization_scope_matches_not_authorized_list(freeze):
    not_authorized = set(freeze["authorization_scope"]["not_authorized"])
    for required in (
        "canonical_m2_gate_rerun", "m2_incremental_evaluation", "model_fit",
        "prediction", "final_test_access", "m3_start", "m4_start",
        "reopen_d2_vs_d3_design_selection", "change_gregorian_d2",
        "merge_without_later_explicit_authorization",
    ):
        assert required in not_authorized


def test_merge_authorization_false(freeze, auth):
    assert auth["merge_authorized"] is False
    assert freeze["status_flags"]["merged"] is False


def test_gate_rerun_authorization_false(freeze, auth):
    assert auth["d2_gate_rerun_authorized"] is False
    assert freeze["stage128_m2_d2_gate_rerun_authorized"] is False


def test_m2_incremental_evaluation_authorization_false(freeze, auth):
    assert auth["m2_incremental_evaluation_authorized"] is False
    assert freeze["M2_incremental_evaluation_authorized"] is False


def test_human_authorization_record_hash_matches(freeze, auth):
    with open(AUTH_PATH, "rb") as f:
        actual = hashlib.sha256(f.read()).hexdigest()
    assert freeze["human_authorization_record_sha256"] == actual


def test_authorization_utterance_hash_matches_recorded_text(auth):
    text = auth["human_source_utterance"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == (
        auth["human_source_utterance_sha256"]
    )


def test_normalized_scope_marked_as_derived_not_verbatim(auth):
    assert auth["normalized_authorization_scope_is_derived_not_verbatim_human_text"] is True
    text = auth["normalized_authorization_scope"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == (
        auth["normalized_authorization_scope_sha256"]
    )


# --------------------------------------------------------------------------- #
# D2 formula contract vs implementation
# --------------------------------------------------------------------------- #

def test_formula_contract_matches_implementation_module(freeze):
    from src import stage128_m2_d2_boundary_month_equity_return as d2mod
    contract = freeze["d2_formula_contract"]
    assert contract["implementation_path"].endswith(
        os.path.basename(d2mod.__file__)
    )
    assert d2mod.MIN_USABLE_DAILY_RETURNS_D2 == freeze[
        "minimum_usable_daily_returns"
    ]


def test_calendar_convention_gregorian(freeze):
    assert freeze["calendar_convention"] == "GREGORIAN"


def test_no_forbidden_construction_mechanisms(freeze):
    contract = freeze["d2_formula_contract"]
    for flag in (
        "annualization", "rescaling_to_365_days", "interpolation",
        "extrapolation", "forward_fill", "backward_fill", "imputation",
        "unadjusted_close_substitution", "synthetic_adjusted_prices",
        "cross_month_fallback",
    ):
        assert contract[flag] is False, flag
    assert contract["boundary_tolerance_days_added"] == 0


# --------------------------------------------------------------------------- #
# Unchanged invariants
# --------------------------------------------------------------------------- #

def test_shared_construct_invariants_unchanged(freeze):
    for key in (
        "shared_window_changed", "t0_changed", "T_star_changed",
        "trading_day_sequence_changed", "daily_return_adjacency_changed",
        "realized_volatility_changed", "amihud_illiquidity_changed",
    ):
        assert freeze[key] is False, key


def test_126_floor_unchanged(freeze):
    assert freeze["minimum_usable_daily_returns"] == 126


def test_no_fourth_primary_feature(freeze):
    assert len(freeze["m2_primary_block_after_amendment"]) == 3
    assert freeze["fourth_primary_market_feature_added"] is False
    assert freeze["zero_trade_day_ratio_primary_feature"] is False


# --------------------------------------------------------------------------- #
# Endpoint validity semantics
# --------------------------------------------------------------------------- #

def test_endpoint_validity_semantics_present_and_asymmetric(freeze):
    sem = freeze["endpoint_price_validity_semantics"]
    assert sem["eligibility_rule"] == "adjusted_close is not None"
    assert sem["end_zero_permitted_under_inherited_d0_semantics"] is True
    assert sem["silently_replaced_with_adjusted_close_gt_0"] is False
    assert sem["observed_539_of_666_universe_changed_in_this_action"] is False


# --------------------------------------------------------------------------- #
# D0 historical preservation, D1/D3/Jalali status
# --------------------------------------------------------------------------- #

def test_d0_historical_fail_preserved(freeze):
    assert freeze["historical_D0_gate_status"] == "FAIL_M2_DATA_GATE"
    assert freeze["historical_D0_equity_coverage"] == "269/666"
    assert freeze["historical_state_rewritten"] is False
    assert freeze["historical_artifacts_preserved_byte_for_byte"] is True


def test_d1_diagnostic_only(freeze):
    assert freeze["d1_status"] == "diagnostic_upper_bound_only_never_a_specification"


def test_d3_not_adopted(freeze):
    assert freeze["d3_status"] == "not_adopted"
    assert freeze["d3_not_adopted_reason"]


def test_jalali_not_adopted(freeze):
    jd = freeze["jalali_diagnostic"]
    assert jd["status"] == "pre_lock_diagnostic_only_not_adopted"
    assert jd["adopted_because_it_clears_a_threshold"] is False
    assert jd["dual_usable_return_value_difference"] == 0


# --------------------------------------------------------------------------- #
# Eligibility-audit contract
# --------------------------------------------------------------------------- #

def test_eligibility_audit_contract_present_not_executed(freeze):
    contract = freeze["eligibility_audit_contract"]
    assert contract["executed_in_this_action"] is False
    assert set(contract["minimum_dimensions"]) >= {
        "prediction_cohort_year", "industry", "firm_size",
        "zero_trade_day_ratio_W", "m1_predictor_availability",
    }
    assert contract["row_removal_based_on_smd"] is False


# --------------------------------------------------------------------------- #
# No-execution guarantees
# --------------------------------------------------------------------------- #

def test_no_execution_guarantees(freeze):
    assert freeze["canonical_gate_executed_in_this_action"] is False
    assert freeze["M2_admitted_in_this_action"] is False
    assert freeze["model_fits"] == 0
    assert freeze["predictions"] == 0
    assert freeze["final_test_access"] == 0
    assert freeze["target_values_accessed"] == 0


def test_final_test_firewall_intact(freeze):
    fw = freeze["final_test_firewall"]
    assert fw["final_test_locked"] is True
    assert fw["final_test_unlocked"] is False
    assert fw["final_test_access_authorized"] is False


# --------------------------------------------------------------------------- #
# Research-action-id consistency
# --------------------------------------------------------------------------- #

def test_research_action_ids_internally_consistent(freeze):
    assert freeze["last_completed_research_action_id_if_this_pr_is_merged"] == (
        "stage128-m2-boundary-month-return-design-freeze"
    )
    assert freeze["next_research_action_id_if_this_pr_is_merged"] == (
        "stage128-m2-d2-gate-rerun"
    )
    assert freeze["next_action_identified_does_not_mean_authorized"] is True
    assert "stage128-m2-d2-gate-rerun" in freeze["not_authorized_successor_actions"]


# --------------------------------------------------------------------------- #
# QC report
# --------------------------------------------------------------------------- #

def test_qc_report_all_pass(qc):
    assert qc["all_pass"] is True
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])


# --------------------------------------------------------------------------- #
# Metadata / hash manifest
# --------------------------------------------------------------------------- #

def test_metadata_hashes_exact(meta):
    for rel_path, expected_sha in meta["package_artifacts_sha256"].items():
        abs_path = os.path.join(
            os.path.dirname(os.path.dirname(STAGE128)), rel_path
        )
        with open(abs_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual == expected_sha, rel_path
    for rel_path, expected_sha in meta["source_artifacts_sha256"].items():
        abs_path = os.path.join(
            os.path.dirname(os.path.dirname(STAGE128)), rel_path
        )
        with open(abs_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual == expected_sha, rel_path


# --------------------------------------------------------------------------- #
# Feasibility provenance honesty
# --------------------------------------------------------------------------- #

def test_d0_independently_reproduced(provenance):
    assert provenance["d0_independently_reproduced_in_repository"] is True
    assert provenance["d0_reproduction_matches_authorizing_utterance"] is True
    assert provenance["d0_reproduction"]["target_values_accessed"] == 0


def test_d1_d2_d3_jalali_marked_not_reproduced(provenance):
    assert provenance[
        "d1_d2_d3_jalali_independently_reproduced_in_repository"
    ] is False
    assert provenance["d1_d2_d3_jalali_non_reproduction_reason"]


def test_provenance_no_model_or_gate_execution(provenance):
    assert provenance["model_fits"] == 0
    assert provenance["predictions"] == 0
    assert provenance["canonical_gate_executions_in_this_reproduction"] == 0
    assert provenance["new_candidate_design_introduced"] is False
    assert provenance["new_threshold_introduced"] is False


def test_provenance_matches_authorizing_utterance_counts(provenance):
    ev = provenance["externally_supplied_feasibility_evidence"]
    assert ev["D0"] == {"usable": 269, "total": 666}
    assert ev["D2_gregorian"] == {"usable": 539, "total": 666}
    assert ev["D3_monthly_as_of"] == {"usable": 555, "total": 666, "common": 553}
    assert ev["jalali_boundary_diagnostic"] == {"usable": 459, "total": 666}
    assert ev["d2_failure_taxonomy_non_exclusive"] == {
        "LT126_VALID_RETURNS": 90,
        "NO_START_BOUNDARY_PRICE": 55,
        "NO_END_BOUNDARY_PRICE": 17,
    }
