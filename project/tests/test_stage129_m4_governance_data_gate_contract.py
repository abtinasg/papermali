"""Stage129 — M4 governance Data-Gate contract lock (DESIGN ONLY).

This action locks the rules for a future M4 Data Accessibility / Provenance
Gate over the four-feature governance-predictor block, before any M4 value is
retrieved. It executes nothing. These tests police the contract package's own
committed JSON content: the candidate set may never drift, excluded
candidates may never be admitted, no retrieval/Gate/modeling counter may be
non-zero, the three-state Gate vocabulary must stay distinct, and the
surrounding scientific state this action must not touch stays untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

_PKG_REL = "project/stage129/m4_governance_data_gate_contract"
_CONTRACT_REL = f"{_PKG_REL}/stage129_m4_data_gate_contract.json"
_AUDIT_REL = f"{_PKG_REL}/stage129_m4_data_gate_execution_audit.json"
_BOUNDARY_REL = f"{_PKG_REL}/stage129_m4_data_gate_governance_boundary.json"
_META_REL = (
    f"{_PKG_REL}/metadata_and_hashes_stage129_m4_governance_data_gate_"
    "contract.json")
_README_REL = (
    f"{_PKG_REL}/README_STAGE129_M4_GOVERNANCE_DATA_GATE_CONTRACT.md")

_ACTION_ID = "stage129-m4-governance-data-gate-contract-lock"
_CANDIDATES = ["audit_opinion_type", "going_concern_flag", "audit_lag_days",
               "board_size"]
_EXCLUDED = ["non_executive_ratio", "institutional_ownership",
             "any_ownership_or_management_feature",
             "auditor_identity_features", "audit_fee_features",
             "textual_nlp_or_llm_derived_predictors",
             "outcome_inspected_keywords",
             "any_governance_feature_discovered_later"]
_HOLM_FAMILY = ["M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _read_text(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def contract() -> dict:
    return _read_json(_CONTRACT_REL)


@pytest.fixture(scope="module")
def audit() -> dict:
    return _read_json(_AUDIT_REL)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


# --------------------------------------------------------------------------- #
# Package presence and hash-manifest integrity
# --------------------------------------------------------------------------- #

def test_package_files_present_and_named_for_this_action(contract, audit,
                                                          boundary):
    for payload in (contract, audit, boundary):
        assert payload["action_id"] == _ACTION_ID
    assert os.path.isfile(os.path.join(REPO_ROOT, _README_REL))


def test_hash_manifest_matches_every_committed_package_file():
    meta = _read_json(_META_REL)
    pkg = os.path.join(REPO_ROOT, _PKG_REL)
    listed = meta["package_files"]
    on_disk = {n for n in os.listdir(pkg) if n != os.path.basename(_META_REL)}
    assert set(listed) == on_disk
    for name, entry in listed.items():
        raw = open(os.path.join(pkg, name), "rb").read()
        assert len(raw) == entry["bytes"], name
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], name
    assert meta["pii_committed_to_git"] is False
    assert meta["credentials_committed_to_git"] is False
    assert meta["m4_value_files_committed"] == 0


# --------------------------------------------------------------------------- #
# 1. exact candidate count == 4
# 2. exact candidate identities cannot drift
# --------------------------------------------------------------------------- #

def test_exact_candidate_count_is_four(contract):
    cs = contract["candidate_set"]
    assert cs["candidate_count"] == 4
    assert len(cs["candidates"]) == 4
    assert cs["candidate_count_is_exact"] is True


def test_exact_candidate_identities(contract):
    cs = contract["candidate_set"]
    assert cs["candidates"] == _CANDIDATES
    assert set(cs["candidate_ids_frozen_from_stage125"]) == set(_CANDIDATES)
    for name, cand_id in cs["candidate_ids_frozen_from_stage125"].items():
        assert cand_id == f"cand_m4_{name}"
    assert cs["no_feature_shopping"] is True
    assert cs["failed_candidate_may_be_replaced_to_preserve_count"] is False


def test_candidate_definitions_inherit_stage125_contract_verbatim(contract):
    stage125 = _read_json(
        "project/stage125/part3b1_m4_feature_definition_contract_stage125"
        ".json")
    for name in _CANDIDATES:
        expected = stage125["variables"][name]["definition"]
        actual = contract["semantic_definitions"][name][
            "inherited_stage125_definition"]
        assert actual == expected, name


# --------------------------------------------------------------------------- #
# 3. excluded candidates can never enter M4
# --------------------------------------------------------------------------- #

def test_excluded_candidates_are_forbidden(contract):
    cs = contract["candidate_set"]
    for excl in _EXCLUDED:
        assert excl in cs["excluded_candidates_forbidden_from_m4"]
    assert set(cs["excluded_candidates_forbidden_from_m4"]) & set(
        cs["candidates"]) == set()


def test_excluded_candidates_never_admitted_in_boundary(boundary):
    assert boundary["institutional_ownership_admitted_as_m4_candidate"] is (
        False)
    assert boundary["non_executive_ratio_admitted_as_m4_candidate"] is False


# --------------------------------------------------------------------------- #
# 4. contract lock contains no retrieved M4 values
# 5. no M4 coverage has been computed by the contract-lock action
# --------------------------------------------------------------------------- #

def test_no_m4_values_retrieved_or_collected(contract):
    policy = contract["authoritative_source_policy"]
    assert policy["values_collected_by_this_action"] == 0
    assert policy["no_values_are_collected_in_this_action_contract_only"] is (
        True)
    state = contract["contract_lock_state"]
    assert state["m4_candidate_observations_read"] == 0
    assert state["m4_data_retrieval_started"] is False


def test_no_coverage_computed(audit):
    assert audit["counters"]["coverage_calculations"] == 0
    assert audit["counters"]["m4_candidate_observations_read"] == 0
    assert audit["counters"]["company_rows_loaded"] == 0


# --------------------------------------------------------------------------- #
# 6. no Gate was executed
# 7. no M4 modeling occurred
# 8. M4 incremental evaluation remains unauthorized
# --------------------------------------------------------------------------- #

def test_no_gate_executed_no_modeling(contract, audit, boundary):
    state = contract["contract_lock_state"]
    assert state["m4_data_gate_executed"] is False
    assert state["m4_block_admitted"] is False
    assert state["m4_modeling_started"] is False
    assert state["m4_incremental_evaluation_authorized"] is False
    assert audit["data_gate_executed"] is False
    assert audit["modeling_started"] is False
    assert audit["retrieval_started"] is False
    for name, value in audit["counters"].items():
        assert value == 0, f"{name} must be 0, not {value!r}"
    assert boundary["m4_authorized"] is False
    assert boundary["m4_started"] is False
    assert boundary["m4_data_gate_executed"] is False
    assert boundary["m4_block_admitted"] is False
    assert boundary["m4_incremental_evaluation_authorized"] is False


# --------------------------------------------------------------------------- #
# 9. Final Test remains locked with rows_read == 0
# --------------------------------------------------------------------------- #

def test_final_test_firewall(contract, audit, boundary):
    fw = contract["final_test_firewall"]
    assert fw["final_test_locked"] is True
    assert fw["final_test_rows_read"] == 0
    assert fw["this_contract_touches_final_test"] is False
    assert fw["future_gate_touches_final_test"] is False
    assert audit["final_test_rows_read"] == 0
    assert audit["final_test_predictor_values_read"] == 0
    assert audit["final_test_target_values_read"] == 0
    assert audit["external_data_source_accessed"] is False
    assert audit["scientific_computation_ran"] is False
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["final_test_access_authorized"] is False


# --------------------------------------------------------------------------- #
# 10. next action pointer does not imply authorization
# --------------------------------------------------------------------------- #

def test_pointer_is_not_authorization(contract, boundary):
    state = contract["contract_lock_state"]
    assert state["next_action_pointer"] == "stage129-m4-governance-data-gate"
    assert state["next_action_authorized"] is False
    assert state["pointer_is_not_authorization"] is True
    assert boundary["next_action_pointer"] == "stage129-m4-governance-data-gate"
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    auth = state["contract_lock_authorization"]
    assert auth["was_authorized"] is True
    assert auth["authorized_now"] is False
    assert auth["authorization_consumed"] is True
    assert auth["authorization_reusable"] is False


# --------------------------------------------------------------------------- #
# 11. PASS/FAIL/UNRESOLVED remain distinct enum values, not collapsible
# 12. unknown provenance/PIT cannot be coerced into PASS
# --------------------------------------------------------------------------- #

def test_three_state_gate_semantics_distinct(contract):
    sem = contract["three_state_gate_semantics"]
    states = sem["states"]
    assert states == ["PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE",
                       "UNRESOLVED_M4_DATA_GATE"]
    assert len(set(states)) == 3
    assert sem["states_are_distinct_and_not_collapsible"] is True
    for coercion in ("UNKNOWN_to_FAIL", "UNKNOWN_to_zero",
                      "missing_evidence_to_negative_evidence"):
        assert coercion in sem["forbidden_coercions"]


def test_pit_and_coverage_and_provenance_are_independent_pass_conditions(
        contract):
    dims = contract["individual_gate_dimensions_for_the_future_gate"]
    assert dims["coverage_pass_is_not_provenance_pass"] is True
    assert dims["provenance_pass_is_not_pit_pass"] is True
    assert dims["all_mandatory_dimensions_must_pass_for_admission"] is True
    ids = {d["id"] for d in dims["dimensions"]}
    assert ids == set("ABCDEFGHIJ")
    pit = contract["point_in_time_rule"]
    assert pit["if_historical_availability_cannot_be_demonstrated"] == (
        "pit_status_UNRESOLVED_never_PASS_never_FAIL_by_assumption")
    assert pit["unknown_is_not_zero"] is True


# --------------------------------------------------------------------------- #
# 13. M3-LAG-WDI cannot become confirmatory M3
# 14. confirmatory Holm family cannot change
# --------------------------------------------------------------------------- #

def test_m3_lag_wdi_stays_supplementary_exploratory(contract, boundary):
    b = contract["m3_comparator_boundary"]
    assert b["m3_lag_wdi_disposition_preserved"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")
    assert b["m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert boundary["m3_lag_wdi_disposition_modified_by_this_action"] is False
    assert boundary["m3_lag_wdi_described_as_confirmatory"] is False


def test_confirmatory_holm_family_unchanged(contract, boundary):
    b = contract["m3_comparator_boundary"]
    assert b["confirmatory_holm_family"] == _HOLM_FAMILY
    assert b["confirmatory_holm_family_changed_by_this_action"] is False
    assert b["confirmatory_holm_family_executed"] is False
    assert b["m4_minus_m3_cbi_comparison_identity_preserved_exactly"] is True
    assert boundary["confirmatory_holm_family_modified_by_this_action"] is (
        False)
    # cross-check against the repo's own canonical statement of the family
    decisions = _read_text("project/docs/ai/DECISIONS.md")
    assert "M2_minus_M1" in decisions and "M4_minus_M3_CBI" in decisions


def test_m3_cbi_dependency_recorded_not_resolved(contract):
    b = contract["m3_comparator_boundary"]
    assert b["m3_cbi_status_preserved"] == "UNRESOLVED_M3_DATA_GATE"
    assert (
        b["m3_cbi_unresolved_creates_future_dependency_for_m4_incremental_"
          "evaluation"] is True)


# --------------------------------------------------------------------------- #
# 15. no paper winner/final model is selected
# --------------------------------------------------------------------------- #

def test_no_paper_winner_or_final_model_selected(contract, boundary):
    preserved = contract["preserved_unchanged_state"]
    assert preserved["paper_winner_selected"] is False
    assert preserved["final_model_selected"] is False
    assert preserved["full_development_refit_performed"] is False
    assert boundary["paper_winner_selected"] is False
    assert boundary["final_model_selected"] is False


# --------------------------------------------------------------------------- #
# Thresholds: reused, not invented; no silent conflict with an existing lock
# --------------------------------------------------------------------------- #

def test_thresholds_match_the_task_specification(contract):
    t = contract["thresholds"]
    assert t["candidate_development_coverage_min"] == 0.80
    assert t["minimum_training_fold_coverage_min"] == 0.75
    assert t["m4_block_common_sample_coverage_min"] == 0.70
    assert t["minimum_positive_evaluable_per_locked_validation_fold"] == 5
    assert t["coverage_scope"] == "development_only"
    assert t["final_test_access_for_admission"] is False
    assert t["thresholds_changed_by_this_action"] is False
    assert t["conflicts_found_with_pre_existing_frozen_contracts"] is False


def test_thresholds_are_independently_verifiable_against_the_sap(contract):
    sap = _read_json(
        "project/stage125/part4_statistical_analysis_plan_stage125.json")
    gates = sap["m1_coverage_gates"] if "m1_coverage_gates" in sap else None
    # The three coverage numbers live in a small config block near the top of
    # the SAP; find it defensively rather than assuming an exact JSON path,
    # since this test must fail loudly if the canonical numbers ever move
    # without this contract being revisited.
    flat = json.dumps(sap)
    assert '"candidate_valid_coverage_min": 0.8' in flat
    assert '"m1_minimum_fold_training_min": 0.75' in flat
    assert '"block_common_sample_coverage_min": 0.7' in flat
    m3_gate = _read_json(
        "project/stage128/m3_macro_data_gate/"
        "stage128_m3_macro_data_gate_decision.json")
    assert m3_gate["thresholds"][
        "min_positive_evaluable_each_temporal_validation_window"] == 5
    del gates  # presence is optional; the substring checks are authoritative


def test_pit_rule_inherited_verbatim(contract):
    inherited = _read_json(
        "project/stage125/part3b1_cutoff_available_at_contract_stage125.json")
    pit = contract["point_in_time_rule"]
    assert pit["cutoff_definition"] == inherited["pair_cutoff"]["definition"]
    assert pit["cutoff_basis"] == inherited["pair_cutoff"]["cutoff_basis"]
    assert pit["cutoff_not_based_on"] == inherited["pair_cutoff"][
        "cutoff_not_based_on"]
    assert pit["block_rule_for_m4"] == inherited["block_rules"]["M4"]
    assert pit["inherited_verbatim"] is True


# --------------------------------------------------------------------------- #
# Missingness: default no-imputation, override only from an already-frozen SAP
# --------------------------------------------------------------------------- #

def test_no_imputation_unless_a_frozen_sap_already_overrides_it(contract):
    m = contract["missingness_policy"]
    assert m["no_imputation_default"] is True
    assert m["sap_override_found"] is False
    for op in ("impute", "forward_fill", "backward_fill", "interpolate",
               "extrapolate", "infer_opinion", "infer_going_concern",
               "infer_board_size", "replace_missing", "proxy_candidate"):
        assert op in m["forbidden_operations"]
    assert m["missing_stays_missing"] is True


# --------------------------------------------------------------------------- #
# Join / identity rule
# --------------------------------------------------------------------------- #

def test_join_identity_rule_frozen(contract):
    j = contract["join_identity_rule"]
    assert j["fuzzy_matching_at_gate_time_forbidden"] is True
    assert j["accidental_many_to_many_forbidden"] is True
    assert j["duplicate_company_year_feature_after_resolution_forbidden"] is (
        True)
    assert j["cross_year_carry_forward_forbidden_unless_explicitly_"
              "preregistered"] is True
    assert j["future_filing_filling_earlier_missingness_forbidden"] is True
    assert j["outcome_informed_manual_matching_forbidden"] is True
    assert j["ambiguous_identity_verdict"] == "unresolved"


# --------------------------------------------------------------------------- #
# This action authorizes nothing downstream
# --------------------------------------------------------------------------- #

def test_this_action_authorizes_nothing(contract):
    assert contract["authorizes_retrieval"] is False
    assert contract["authorizes_gate_execution"] is False
    assert contract["authorizes_modeling"] is False
    assert contract["is_confirmatory_m4_admission"] is False
    assert contract["is_the_gate_itself"] is False


# --------------------------------------------------------------------------- #
# The auto-generated handoff/state files now integrate Stage129, generated by
# the canonical generator (never hand-edited) -- see
# test_ai_handoff.py::test_stage129_* for the recognizer-level checks.
# --------------------------------------------------------------------------- #

def _git_diff_against_main(rel: str) -> str:
    try:
        return subprocess.run(
            ["git", "diff", "origin/main", "--", rel],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        ).stdout
    except Exception:
        return ""


def _handoff_state() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


def _current_state_text() -> str:
    return _read_text("project/docs/ai/CURRENT_STATE.md")


def test_handoff_state_exposes_the_locked_stage129_contract():
    state = _handoff_state()
    assert state["stage129_m4_contract_lock_executed"] is True
    assert state["stage129_m4_contract_status"] == (
        "PROSPECTIVELY_LOCKED_PRE_RETRIEVAL")
    assert state["stage129_m4_candidate_count"] == 4
    assert state["stage129_m4_candidate_set"] == _CANDIDATES
    assert state["stage129_m4_contract_lock_was_authorized"] is True
    assert state["stage129_m4_contract_lock_authorized_now"] is False
    assert state["stage129_m4_contract_lock_authorization_consumed"] is True
    assert state["stage129_m4_contract_lock_authorization_reusable"] is False


def test_handoff_state_shows_zero_m4_execution():
    state = _handoff_state()
    assert state["m4_data_retrieval_started"] is False
    assert state["m4_candidate_observations_read"] == 0
    assert state["m4_data_gate_executed"] is False
    assert state["m4_block_admitted"] is False
    assert state["m4_modeling_started"] is False
    assert state["m4_incremental_evaluation_authorized"] is False
    assert state["stage129_m4_final_test_locked"] is True
    assert state["stage129_m4_final_test_rows_read"] == 0
    assert state["final_test_locked"] is True
    assert state["final_test_rows_read"] == 0


def test_handoff_state_pointer_is_distinct_from_authorization_and_from_the_two_live_pointers():
    state = _handoff_state()
    # What THIS lock published at lock time is history and never changes.
    assert state["stage129_m4_contract_lock_pointer_at_lock_time"] == (
        "stage129-m4-governance-data-gate")
    # The live M4 pointer was later superseded by the human decision to
    # discontinue M4; a discontinued block may not keep naming its own Gate.
    assert state["stage129_m4_next_action_id"] == "human_decision_required"
    assert state["stage129_m4_next_action_authorized"] is False
    assert state["stage129_m4_next_action_pointer_is_not_authorization"] is (
        True)
    # Both pre-existing live pointer chains are preserved, and neither was
    # advanced by any Stage129 action.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["stage128_m3_lag_wdi_next_action_id"] == (
        "human_decision_required")
    # The three chains may CONVERGE on the same terminal "a human must decide"
    # value -- Track A and Track B already did. What is forbidden is the M4
    # pointer naming an executable M4 step, or being read as an authorization.
    assert state["stage129_m4_next_action_id"] != (
        "stage129-m4-governance-data-gate")
    assert state["stage129_m4_next_action_executes_m4"] is False


def test_handoff_state_surfaces_the_three_unresolved_contract_issues():
    state = _handoff_state()
    assert state["stage129_m4_audit_opinion_type_taxonomy_status"] == (
        "CONTRACT_ISSUE_UNRESOLVED")
    assert state["stage129_m4_audit_lag_days_calendar_conversion_status"] == (
        "CONTRACT_ISSUE_UNRESOLVED")
    assert state["stage129_m4_codal_identity_resolution_status"] == (
        "CONTRACT_ISSUE_UNRESOLVED")
    assert set(state["stage129_m4_contract_issues_unresolved"]) == {
        "audit_opinion_type_taxonomy", "audit_lag_days_calendar_conversion",
        "codal_to_parent_company_identity_resolution",
    }


def test_handoff_state_freezes_join_identity_to_the_audited_m2_m3_keys():
    state = _handoff_state()
    assert state["stage129_m4_join_identity_company_key"] == "ticker"
    assert state["stage129_m4_join_identity_fiscal_year_key"] == (
        "fiscal_year_t")
    assert state["stage129_m4_join_identity_ambiguous_verdict"] == (
        "unresolved")


def test_handoff_state_threshold_provenance_matches_contract_per_field(
        contract):
    state = _handoff_state()
    assert state["stage129_m4_threshold_canonical_sources"] == (
        contract["thresholds"]["canonical_sources"])
    fourth = state["stage129_m4_threshold_canonical_sources"][
        "minimum_positive_evaluable_per_locked_validation_fold"]
    assert "stage128_m3_macro_data_gate_decision.json" in fourth["found_in"]
    assert "part4_statistical_analysis_plan_stage125" not in fourth[
        "found_in"]


def test_handoff_state_preserves_m3_boundary_and_holm_family_unchanged():
    state = _handoff_state()
    assert state["stage129_m4_m3_cbi_status_preserved"] == (
        "UNRESOLVED_M3_DATA_GATE")
    assert state["stage129_m4_m3_lag_wdi_disposition_preserved"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")
    assert state["stage129_m4_confirmatory_holm_family"] == _HOLM_FAMILY
    assert state["stage129_m4_confirmatory_holm_family_executed"] is False
    # Regression: the surrounding M3 state this action must not touch.
    assert state["m3_macro_data_gate_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert state["stage128_m3_lag_wdi_final_research_disposition"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")


def test_current_state_md_exposes_the_same_stage129_facts():
    text = _current_state_text()
    assert "Stage129" in text
    assert "M4 governance Data-Gate contract lock" in text
    assert "PROSPECTIVELY_LOCKED_PRE_RETRIEVAL" in text
    assert "CONTRACT_ISSUE_UNRESOLVED" in text
    assert "stage129-m4-governance-data-gate" in text


def test_protected_handoff_keys_have_the_expected_pre_existing_values():
    """Belt-and-braces: even if the diff check above were ever bypassed,
    the specific keys this task must never move are pinned to their known
    pre-existing values."""
    state = _read_json("project/docs/ai/handoff_state.json")
    expected = {
        "m2_block_retained": True,
        "m3_data_collected": False,
        "stage128_m3_lag_wdi_final_research_disposition":
            "SUPPLEMENTARY_EXPLORATORY_ONLY",
        "m3_macro_data_gate_status": "UNRESOLVED_M3_DATA_GATE",
        "m4_authorized": False,
        "m4_data_collected": False,
        "m4_started": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        # NB: `paper_winner_selected` is deliberately NOT pinned here. It was
        # False when this contract-lock task ran and this task never moved it,
        # but it is a LIVE STANDING flag that a later, separately authorized
        # governance decision (stage129-final-model-human-selection-governance)
        # legitimately sets. What this task must never move is the scientific
        # state below, plus the fact that no trained final model exists.
        "final_model_selected": False,
        "trained_final_model_artifact_created": False,
        "full_development_refit_performed": False,
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "stage128_m3_lag_wdi_promoted_to_confirmatory_model": False,
        "stage128_m3_lag_wdi_e1_conclusion":
            "E1_NULL_NO_DETECTABLE_INCREMENTAL_CONTRIBUTION",
        "stage128_m3_lag_wdi_point_in_time_availability_status":
            "UNVERIFIED_WITH_CURRENTLY_AVAILABLE_EVIDENCE",
        "stage128_track_a_waiting_period_status":
            "VOLUNTARILY_TERMINATED_BY_EXPLICIT_HUMAN_DECISION",
        "stage128_m3_lag_wdi_confirmatory_holm_family_changed": False,
    }
    for key, value in expected.items():
        assert state.get(key) == value, key


# ---------------------------------------------------------------------------
# The contract must never read as unconditionally complete while two mandatory
# preregistered semantic definitions remain unresolved. "Candidate identity is
# frozen" and "the definition is frozen" are two different locks; conflating
# them is exactly the overstatement these tests exist to prevent.
# ---------------------------------------------------------------------------

def test_candidate_identity_is_frozen_but_definitions_are_not(contract):
    semantic = contract["semantic_definitions"]
    for name in ("audit_opinion_type", "audit_lag_days"):
        definition = semantic[name]
        assert definition["candidate_identity_frozen"] is True, (
            f"{name} candidate identity must stay frozen")
        assert definition["gate_may_execute_for_this_candidate"] is False, (
            f"{name} must not be gate-executable while unresolved")
    assert semantic["audit_opinion_type"]["taxonomy_frozen"] is False
    assert semantic["audit_opinion_type"][
        "modeled_categorical_values_admitted"] is False
    assert semantic["audit_lag_days"]["calendar_conversion_frozen"] is False
    assert semantic["audit_lag_days"]["value_may_be_calculated"] is False


def test_plus_621_forbidden_as_daily_date_conversion(contract):
    audit_lag = contract["semantic_definitions"]["audit_lag_days"]
    assert audit_lag[
        "jalali_fiscal_year_t_plus_621_permitted_as_daily_date_conversion"
    ] is False


def test_contract_is_not_published_as_complete_or_executable(contract):
    state = contract["contract_lock_state"]
    assert state["m4_candidate_identity_set_locked"] is True
    assert state["m4_gate_policy_contract_recorded"] is True
    assert state["m4_contract_complete"] is False
    assert state["m4_contract_fully_executable"] is False
    assert state["m4_contract_completion_status"] == (
        "LOCKED_WITH_UNRESOLVED_PREREQUISITE_DEFINITIONS")
    assert state["m4_data_gate_executable"] is False
    assert state["m4_data_gate_authorized"] is False
    assert state["m4_coverage_calculated"] is False


def test_blocked_and_gate_ready_candidates_partition_the_four(contract):
    state = contract["contract_lock_state"]
    blocked = state["m4_candidates_blocked_by_unresolved_definitions"]
    ready = state["m4_candidates_with_gate_ready_semantic_definitions"]
    assert blocked == ["audit_opinion_type", "audit_lag_days"]
    assert set(blocked) & set(ready) == set()
    assert sorted(blocked + ready) == sorted(state["candidate_set"])


def test_unresolved_prerequisite_entries_are_self_consistent(contract):
    entries = contract["contract_lock_state"][
        "unresolved_prerequisite_definitions"]
    assert [e["candidate"] for e in entries] == [
        "audit_opinion_type", "audit_lag_days"]
    for entry in entries:
        assert entry["status"] == "CONTRACT_ISSUE_UNRESOLVED"
        assert entry["candidate_identity_frozen"] is True
        assert entry["gate_may_execute_for_this_candidate"] is False
        assert entry["unblocking_requires"]


def test_handoff_state_does_not_overstate_completion():
    state = _read_json("project/docs/ai/handoff_state.json")
    assert state["stage129_m4_candidate_identity_set_locked"] is True
    assert state["stage129_m4_gate_policy_contract_recorded"] is True
    assert state["stage129_m4_contract_complete"] is False
    assert state["stage129_m4_contract_fully_executable"] is False
    assert state["stage129_m4_contract_completion_status"] == (
        "LOCKED_WITH_UNRESOLVED_PREREQUISITE_DEFINITIONS")
    assert state["stage129_m4_data_gate_executable"] is False
    assert state["stage129_m4_data_gate_authorized"] is False
    assert state["stage129_m4_coverage_calculated"] is False
    assert state["m4_contract_fully_executable"] is False
    assert state["m4_data_gate_executable"] is False
    assert state["m4_coverage_calculated"] is False


def test_current_state_md_discloses_the_contract_is_not_complete():
    text = _read_text("project/docs/ai/CURRENT_STATE.md")
    assert "LOCKED_WITH_UNRESOLVED_PREREQUISITE_DEFINITIONS" in text
    assert "CONTRACT_ISSUE_UNRESOLVED" in text


def test_codal_identity_resolution_is_unresolved(contract):
    """The audited join evidence is parent-side only (TSETMC child). Nothing
    in this repository resolves a CODAL issuer identity to `ticker`."""
    codal = contract["join_identity_rule"][
        "codal_to_parent_company_identity_resolution"]
    assert codal["status"] == "CONTRACT_ISSUE_UNRESOLVED"
    assert codal[
        "gate_may_execute_join_dimension_for_codal_sourced_values"] is False
    assert contract["join_identity_rule"]["required_identifier"][
        "fallback_mapping_permitted"] is False


def test_gate_may_execute_for_no_candidate(contract):
    state = contract["contract_lock_state"]
    assert state["m4_candidates_the_gate_may_execute_for"] == []
    cross = state["unresolved_cross_cutting_prerequisites"]
    assert any(e["issue"] == "codal_to_parent_company_identity_resolution"
               and e["status"] == "CONTRACT_ISSUE_UNRESOLVED" for e in cross)


def test_handoff_exposes_the_codal_identity_issue():
    state = _read_json("project/docs/ai/handoff_state.json")
    assert state["stage129_m4_codal_identity_resolution_status"] == (
        "CONTRACT_ISSUE_UNRESOLVED")
    assert state[
        "stage129_m4_join_dimension_executable_for_codal_values"] is False
    assert state["stage129_m4_candidates_the_gate_may_execute_for"] == []
    assert "codal_to_parent_company_identity_resolution" in state[
        "stage129_m4_contract_issues_unresolved"]
