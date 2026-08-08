"""Stage128 — Track B: the M3-LAG-WDI-EXPLORATORY contract lock.

These tests police one narrow claim: the M3-LAG-WDI exploratory contract was
frozen **before** any retrieval, and *nothing else happened*. The contract is
the whole deliverable, so the tests are mostly drift tests — they assert that
the recognizers in both the Handoff generator and the independent current-state
validator FAIL CLOSED the moment any locked term changes: the `t-1` rule, an
indicator code, the FX formula, the feature count, the parent sample, the
exploratory role, a point-in-time claim, a Gate threshold, the Holm family, or
any execution counter.

They also police the two things a parallel activation must never quietly do:
terminate the still-active World Bank inquiry, and re-render the merged PR #77
as the live Draft.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project"))

import update_ai_handoff as gen  # noqa: E402
from src import stage126_current_state_validator as v  # noqa: E402

_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_contract_lock"
_CONTRACT_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_contract.json"
_DECISION_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_contract_decision.json")
_BOUNDARY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_governance_boundary.json")
_GATE_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_data_gate_contract.json")
_MODELING_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_modeling_contract.json")
_AUDIT_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_execution_audit.json")
_AUTH_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_human_authorization_record"
    ".json")
_TOPOLOGY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_exploratory_pr_topology.json")
_META_REL = (
    f"{_PKG_REL}/metadata_and_hashes_stage128_m3_lag_wdi_exploratory_contract"
    "_lock.json")
_README_REL = (
    f"{_PKG_REL}/README_STAGE128_M3_LAG_WDI_EXPLORATORY_CONTRACT_LOCK.md")

_ALL_RELS = (_CONTRACT_REL, _DECISION_REL, _BOUNDARY_REL, _GATE_REL,
             _MODELING_REL, _AUDIT_REL, _AUTH_REL, _TOPOLOGY_REL)

_ACTION_ID = "stage128-m3-lag-wdi-exploratory-contract-lock"
_LOCKED_STATUS = "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL"
_ROLE = "supplementary_exploratory_robustness_block"
_AUTH_SHA256 = (
    "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b")
_AUTH_UTF8_BYTES = 158
_BASELINE = "93de6bae9344ce893b0261f818abce8a991cf842"
_MERGED_PREDECESSOR_PR = 77
_DOCS = ("project/docs/ai/ROADMAP.md", "project/docs/ai/OPEN_TASKS.md")


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
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


@pytest.fixture(scope="module")
def gate() -> dict:
    return _read_json(_GATE_REL)


@pytest.fixture(scope="module")
def modeling() -> dict:
    return _read_json(_MODELING_REL)


@pytest.fixture(scope="module")
def audit() -> dict:
    return _read_json(_AUDIT_REL)


@pytest.fixture(scope="module")
def handoff() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


# --------------------------------------------------------------------------- #
# The package exists and is internally addressed
# --------------------------------------------------------------------------- #

def test_every_package_file_is_present_and_names_this_action():
    for rel in _ALL_RELS:
        payload = _read_json(rel)
        assert payload.get("action_id") == _ACTION_ID, rel
    assert os.path.isfile(os.path.join(REPO_ROOT, _README_REL))


def test_the_hash_manifest_matches_every_committed_package_file():
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
    assert meta["wdi_value_files_committed"] == 0


# --------------------------------------------------------------------------- #
# The authorization: exact bytes, exact digest, consumed, never reusable
# --------------------------------------------------------------------------- #

def test_the_authorization_digest_is_recomputable_from_its_own_text():
    auth = _read_json(_AUTH_REL)
    raw = auth["authorization_text"].encode("utf-8")
    assert len(raw) == _AUTH_UTF8_BYTES == auth["authorization_utf8_bytes"]
    assert hashlib.sha256(raw).hexdigest() == _AUTH_SHA256 == (
        auth["authorization_sha256"])


def test_the_authorization_is_one_action_and_not_reusable():
    auth = _read_json(_AUTH_REL)
    assert auth["authorization_type"] == "one_action_authorization"
    assert auth["authorization_consumed"] is True
    assert auth["authorization_consumed_by_this_contract_lock"] is True
    assert auth["standing_authorization"] is False
    for field in ("authorization_is_reusable_for_retrieval",
                  "authorization_is_reusable_for_data_gate",
                  "authorization_is_reusable_for_modeling",
                  "prior_local_draft_authorization_reused",
                  "merge_authorized"):
        assert auth[field] is False, field
    assert auth["expected_baseline_sha"] == _BASELINE


def test_the_authorization_supersedes_only_the_wait_only_restriction():
    auth = _read_json(_AUTH_REL)
    assert auth[
        "supersedes_only_the_prior_wait_for_terminal_inquiry_restriction"
    ] is True
    assert auth["terminates_or_resolves_the_world_bank_inquiry"] is False


def test_no_timestamp_was_invented_for_the_authorization():
    auth = _read_json(_AUTH_REL)
    assert auth["timestamp_utc"] is None
    assert auth["timestamp_independently_establishable"] is False


# --------------------------------------------------------------------------- #
# The frozen scientific terms
# --------------------------------------------------------------------------- #

def test_the_role_is_exploratory_and_never_confirmatory(contract):
    assert contract["scientific_role"] == _ROLE
    for field in ("is_confirmatory_m3", "is_replacement_for_m3_cbi",
                  "is_repair_of_m3_cbi",
                  "is_continuation_or_replacement_of_m3i2",
                  "is_real_time_wdi", "is_historical_vintage_wdi",
                  "in_original_confirmatory_holm_family",
                  "can_select_paper_winner_alone",
                  "exploratory_result_can_rewrite_main_confirmatory_"
                  "conclusion"):
        assert contract[field] is False, field
    assert contract[
        "one_year_lag_is_conservative_temporal_separation_design_only"] is True


def test_exactly_two_features_with_the_exact_locked_identities(contract):
    assert contract["additional_macro_feature_count"] == 2
    cpi, fx = contract["features"]
    assert cpi["feature_id"] == "intl_cpi_inflation_lag1_wdi"
    assert cpi["indicator_code"] == "FP.CPI.TOTL.ZG"
    assert fx["feature_id"] == "intl_fx_change_official_lag1_wdi"
    assert fx["indicator_code"] == "PA.NUS.FCRF"
    for feature in (cpi, fx):
        assert feature["country_code"] == "IRN"
        assert feature["source_identity"] == "World Bank WDI"
        assert feature["lag_years"] == 1
        assert feature["same_year_t_observation_permitted"] is False
        assert feature["imputation_permitted"] is False
        assert feature["alternative_indicator_after_failure_permitted"] is False
    assert contract["third_macro_feature_permitted"] is False
    assert contract["financing_rate_feature_permitted"] is False
    assert contract["indicator_search_permitted"] is False


def test_the_cpi_feature_uses_the_t_minus_one_identity_rule(contract):
    cpi = contract["features"][0]
    assert cpi["observation_year_rule"] == "t - 1"
    assert cpi["observation_year_formula"] == (
        "wdi_observation_year = predictor_year_t - 1")
    assert cpi["transformation"] == "identity"
    assert cpi["required_observation_years"] == ["t-1"]
    # the worked example the human authorization named explicitly
    assert cpi["worked_example"] == {"predictor_year": 2019,
                                     "wdi_observation_year": 2018}


def test_the_fx_feature_uses_the_exact_log_change_formula(contract):
    fx = contract["features"][1]
    assert fx["observation_year_rule"] == "y = t - 1"
    assert fx["transformation"] == "FX_LAG1_t = 100 * ln(E_y / E_(y-1))"
    assert fx["transformation_equivalent"] == "100 * ln(E_(t-1) / E_(t-2))"
    assert fx["required_observation_years"] == ["t-1", "t-2"]
    assert fx["observation_requirements"] == [
        "present", "numeric", "strictly_positive",
        "consecutive_gregorian_annual_observations"]
    for forbidden in ("PA.NUS.ATLS", "free-market exchange rates",
                      "unofficial rates", "aggregator-derived rates",
                      "post-hoc alternative transformations"):
        assert forbidden in fx["forbidden_substitutions"], forbidden


def test_the_sample_and_feature_architecture_is_frozen(contract):
    parent = contract["parent_sample"]
    assert parent["expected_parent_rows"] == 539
    assert parent["expected_parent_positive"] == 55
    assert parent["expected_parent_negative"] == 484
    assert parent["scope"] == "development_only"
    assert parent["original_666_row_m1_comparison_sample_permitted"] is False
    assert contract["m2_comparator"]["feature_count"] == 12
    assert len(contract["m2_comparator"]["feature_order"]) == 12
    assert contract["m2_comparator"]["m2_status"] == (
        "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK")
    assert contract["feature_count_total"] == 14
    order = contract["m3_lag_wdi_feature_order"]
    assert len(order) == 14
    assert order[:12] == contract["m2_comparator"]["feature_order"]
    assert order[12:] == ["intl_cpi_inflation_lag1_wdi",
                          "intl_fx_change_official_lag1_wdi"]
    policy = contract["complete_case_policy"]
    assert policy["both_lagged_wdi_features_required_complete"] is True
    assert policy[
        "m2_and_m3_lag_wdi_refit_on_the_same_resulting_common_sample"] is True
    assert policy["previous_666_row_m1_results_reusable_as_comparator"] is False
    assert policy["imputation_permitted"] is False


def test_the_contract_claims_no_point_in_time_availability(contract):
    vintage = contract["wdi_vintage_semantics"]
    assert vintage["current_or_latest_revised_wdi_allowed"] is True
    assert vintage["revisions_may_be_present"] is True
    assert vintage[
        "limitation_is_why_the_analysis_is_exploratory_supplementary"] is True
    for field in ("historical_vintage_availability_claimed",
                  "point_in_time_availability_claimed",
                  "lagging_transforms_revised_wdi_into_point_in_time_data",
                  "release_date_proof_attempted"):
        assert vintage[field] is False, field
    assert contract[
        "proves_historical_point_in_time_wdi_availability"] is False
    assert contract["reuses_m3i2_historical_vintage_availability_logic"] is (
        False)


# --------------------------------------------------------------------------- #
# The Data Gate is frozen and was NOT executed
# --------------------------------------------------------------------------- #

def test_the_gate_thresholds_are_inherited_not_redesigned(gate):
    inherited = _read_json(
        "project/stage128/m3_intl_macro_contract_lock/"
        "stage128_m3_intl_macro_data_gate_contract.json")["thresholds"]
    t = gate["thresholds"]
    assert t["candidate_valid_coverage_min"] == 0.8
    assert t["block_common_sample_coverage_min"] == 0.7
    assert t["minimum_positive_evaluable_each_locked_validation_window"] == 5
    assert t["coverage_scope"] == "development_only"
    assert t["final_test_access_for_admission"] is False
    for field in ("candidate_valid_coverage_min",
                  "block_common_sample_coverage_min",
                  "minimum_positive_evaluable_each_locked_validation_window",
                  "expected_parent_rows"):
        assert t[field] == inherited[field], field
    assert gate["thresholds_inherited_not_redesigned"] is True


def test_no_coverage_was_calculated_and_no_value_is_zero_by_accident(gate):
    assert gate["gate_executed"] is False
    assert gate["gate_result"] == "NOT_EXECUTED"
    assert gate["coverage_calculations"] == 0
    assert gate["unresolved_values_are_null_not_zero"] is True
    assert gate["observed_values"], "the observed-value slots must be explicit"
    for name, value in gate["observed_values"].items():
        assert value is None, f"{name} must be null, not {value!r}"


def test_a_gate_pass_would_admit_data_and_authorize_nothing_else(gate):
    assert gate["gate_pass_is_data_admission_only"] is True
    assert gate["gate_pass_authorizes_modeling"] is False
    assert gate["gate_pass_unlocks_final_test"] is False
    assert gate["modeling_requires_separate_explicit_human_authorization"] is (
        True)


# --------------------------------------------------------------------------- #
# The modeling contract is frozen and separate from the confirmatory family
# --------------------------------------------------------------------------- #

def test_exactly_the_three_retained_model_families_with_no_search(modeling):
    manifest = _read_json(
        "project/stage128/m2_incremental_evaluation/"
        "stage127_m2_feature_configuration_manifest.json")
    assert modeling["model_families"] == [
        "regularized_logistic_regression", "random_forest", "xgboost"]
    assert set(modeling["model_families"]) == set(manifest["configurations"])
    for field in ("retuning_permitted", "grid_search_permitted",
                  "hyperparameter_search_permitted",
                  "model_family_search_permitted",
                  "new_secondary_metrics_defined_by_this_action"):
        assert modeling[field] is False, field
    for field in ("inherits_canonical_metric_definitions",
                  "inherits_locked_validation_architecture",
                  "inherits_seed_policy",
                  "inherits_bootstrap_and_paired_comparison_machinery",
                  "retained_configurations_used_unchanged"):
        assert modeling[field] is True, field


def test_the_exploratory_comparison_stays_out_of_the_holm_family(modeling):
    family = ["M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
    assert modeling["confirmatory_holm_family"] == family
    assert modeling["confirmatory_holm_family_changed_by_this_action"] is False
    assert modeling[
        "exploratory_comparison_inserted_into_confirmatory_holm_family"] is (
        False)
    assert modeling["comparison_family_id"] not in family
    assert modeling["primary_comparison"] == "M3_LAG_WDI_minus_retained_M2"
    assert modeling["results_label"] == (
        "supplementary_exploratory_robustness_only")
    assert modeling["confirmatory_superiority_claim_permitted"] is False
    assert modeling["supplementary_family_size_now"] == 0
    for entry in modeling["supplementary_family"]:
        assert entry["exists_now"] is False


# --------------------------------------------------------------------------- #
# Zero execution, and the Final Test firewall
# --------------------------------------------------------------------------- #

def test_every_execution_counter_is_zero(audit):
    assert audit["counters"], "the audit must enumerate its counters"
    for name, value in audit["counters"].items():
        assert value == 0, f"{name} must be 0, not {value!r}"
    for field in ("retrieval_started", "data_gate_executed",
                  "modeling_started",
                  "earlier_historical_vintage_bundle_used_as_value_input"):
        assert audit[field] is False, field
    assert audit["quarantined_local_draft_left_untouched"] is True


def test_no_final_test_value_was_read(audit, boundary):
    assert audit["final_test_rows_read"] == 0
    assert audit["final_test_predictor_values_read"] == 0
    assert audit["final_test_target_values_read"] == 0
    assert boundary["final_test_locked"] is True
    for field in ("final_test_access_authorized",
                  "final_test_unlock_implied_by_contract_lock",
                  "final_test_unlock_implied_by_gate_pass",
                  "final_test_unlock_implied_by_successful_retrieval"):
        assert boundary[field] is False, field


# --------------------------------------------------------------------------- #
# Track A is untouched; Track B is locked but unauthorized
# --------------------------------------------------------------------------- #

def test_the_world_bank_inquiry_is_still_active_and_unresolved(boundary):
    assert boundary["world_bank_inquiry_status"] == (
        "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE")
    assert boundary["world_bank_waiting_period_status"] == "ACTIVE"
    assert boundary["world_bank_waiting_period_completion_date"] == "2026-08-20"
    assert boundary[
        "world_bank_waiting_period_earliest_follow_up_date"] == "2026-08-21"
    for field in ("world_bank_inquiry_terminated_by_this_action",
                  "world_bank_follow_up_authorized",
                  "world_bank_response_ingestion_authorized",
                  "parallel_activation_implies_inquiry_failed",
                  "parallel_activation_implies_inquiry_terminated",
                  "parallel_activation_implies_inquiry_unnecessary"):
        assert boundary[field] is False, field


def test_locked_is_not_authorized(boundary):
    assert boundary["m3_lag_wdi_authoritative_contract_status"] == (
        _LOCKED_STATUS)
    assert boundary["m3_lag_wdi_exploratory_contract_locked"] is True
    assert boundary["m3_lag_wdi_next_action_id"] == (
        "stage128-m3-lag-wdi-exploratory-data-retrieval")
    assert boundary["m3_lag_wdi_next_action_authorized"] is False
    assert boundary["next_action_pointer_is_not_authorization"] is True
    for field in ("merge_authorized", "auto_merge",
                  "ready_for_review_authorized", "m4_authorized", "m4_started",
                  "paper_winner_selected"):
        assert boundary[field] is False, field


def test_the_existing_scientific_state_is_preserved(boundary):
    assert boundary["m3_cbi_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert boundary["m3i2_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
    assert boundary["m3i2_block_admitted"] is False
    for field in ("m3_cbi_modified_by_this_action",
                  "m3i2_conclusions_modified_by_this_action",
                  "observed_m1_m2_results_modified_by_this_action"):
        assert boundary[field] is False, field
    decision = _read_json(_DECISION_REL)
    assert decision["scientific_effect"] == "NONE"
    assert decision["verified_wdi_release_dates"] == 0
    assert decision["verified_pre_cutoff_editions"] == 0
    assert decision["unresolved_cutoffs"] == decision[
        "unresolved_cutoffs_total"] == 37
    assert decision["unresolved_development_pairs"] == decision[
        "unresolved_development_pairs_total"] == 539


def test_track_b_does_not_take_over_the_track_a_research_pointers():
    decision = _read_json(_DECISION_REL)
    assert decision["last_completed_research_action_id"] == (
        "stage128-m3i2-final-official-inquiry-human-submission")
    assert decision["next_research_action_id"] == (
        "stage128-m3i2-final-official-inquiry-response-ingestion")
    assert decision["next_research_action_authorized"] is False


def test_the_quarantined_local_draft_was_not_promoted(boundary):
    assert boundary["m3_lag_wdi_local_partial_draft_authoritative"] is False
    assert boundary[
        "m3_lag_wdi_local_partial_draft_committed_by_this_action"] is False
    assert boundary[
        "m3_lag_wdi_local_partial_draft_modified_by_this_action"] is False
    assert boundary["m3_lag_wdi_prior_authorization_reusable"] is False
    supersession = _read_json(
        "project/stage128/m3i2_final_official_documentary_recovery/"
        "stage128_m3_lag_partial_local_execution_supersession_record.json")
    assert supersession["authoritative_repository_contract_locked"] is False
    assert supersession["prior_authorization_reusable"] is False


# --------------------------------------------------------------------------- #
# PR topology: a MERGED PR is never the live Draft
# --------------------------------------------------------------------------- #

def test_pr_77_is_merged_history_and_the_new_pr_is_the_live_draft():
    topo = _read_json(_TOPOLOGY_REL)
    assert topo["predecessor_pr_number"] == _MERGED_PREDECESSOR_PR
    assert topo["predecessor_pr_merged"] is True
    assert topo["predecessor_pr_merge_commit"] == _BASELINE
    assert topo["live_pr_number"] > _MERGED_PREDECESSOR_PR
    assert topo["live_pr_is_draft"] is True
    assert topo["live_pr_merged"] is False
    assert topo["live_pr_base_branch"] == "main"
    assert topo["live_pr_base_commit"] == _BASELINE
    assert topo["pr_is_stacked_on_open_predecessor"] is False
    # the head shown for a live PR is a generation anchor, never pinned
    assert topo["live_pr_head_commit_pinned"] is False
    assert topo["live_pr_head_is_github_pr_head"] is False
    assert topo["live_pr_head_semantics"] == (
        "repository_head_at_generation_not_github_pr_head")


def test_the_handoff_publishes_the_new_pr_as_live_and_pr_77_as_history(
        handoff):
    topo = _read_json(_TOPOLOGY_REL)
    assert handoff["stage128_m3i2_live_pr_number"] == topo["live_pr_number"]
    assert handoff["stage128_m3i2_live_pr_is_draft"] is True
    assert handoff["stage128_m3i2_live_pr_merged"] is False
    # PR #77 is history under its OWN role — the human inquiry submission
    # recording. It is NOT the documentary-recovery PR: that is PR #76, and
    # `stage128_m3i2_recovery_pr_*` keeps naming it (see the PR-role tests
    # below).
    assert handoff["stage128_m3i2_human_submission_pr_number"] == (
        _MERGED_PREDECESSOR_PR)
    assert handoff["stage128_m3i2_human_submission_pr_merged"] is True
    assert handoff["stage128_m3i2_human_submission_pr_merge_commit"] == (
        _BASELINE)


# --------------------------------------------------------------------------- #
# The published Handoff and the human docs agree with the contract
# --------------------------------------------------------------------------- #

def test_the_handoff_publishes_the_locked_contract(handoff):
    assert handoff["stage128_m3_lag_wdi_exploratory_contract_locked"] is True
    assert handoff["stage128_m3_lag_wdi_authoritative_contract_status"] == (
        _LOCKED_STATUS)
    assert handoff["stage128_m3_lag_wdi_scientific_role"] == _ROLE
    assert handoff["stage128_m3_lag_wdi_feature_count"] == 14
    assert handoff["stage128_m3_lag_wdi_m2_comparator_feature_count"] == 12
    assert handoff["stage128_m3_lag_wdi_parent_sample_rows"] == 539
    assert handoff["stage128_m3_lag_wdi_cpi_indicator_code"] == (
        "FP.CPI.TOTL.ZG")
    assert handoff["stage128_m3_lag_wdi_fx_indicator_code"] == "PA.NUS.FCRF"
    assert handoff["stage128_m3_lag_wdi_observation_year_rule"] == "t - 1"
    assert handoff["stage128_m3_lag_wdi_authorization_sha256"] == _AUTH_SHA256
    assert handoff["stage128_m3_lag_wdi_authorization_utf8_bytes"] == (
        _AUTH_UTF8_BYTES)


def test_the_handoff_records_zero_execution(handoff):
    # Retrieval (step B) is a SEPARATE, later, separately authorized action, so
    # whether it has run is owned by its own test module, not by the lock's.
    # What the LOCK must never have caused is asserted here and stays asserted
    # for the whole life of the branch.
    assert handoff["stage128_m3_lag_wdi_data_gate_executed"] is False
    assert handoff["stage128_m3_lag_wdi_data_gate_result"] == "NOT_EXECUTED"
    assert handoff["stage128_m3_lag_wdi_modeling_started"] is False
    assert handoff["stage128_m3_lag_wdi_modeling_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_final_test_rows_read"] == 0
    assert handoff["final_test_locked"] is True
    assert handoff["m4_authorized"] is False


def test_the_handoff_keeps_the_world_bank_inquiry_open(handoff):
    assert handoff["stage128_m3i2_inquiry_waiting_period_status"] == "ACTIVE"
    assert handoff[
        "stage128_m3i2_inquiry_substantive_response_received"] is False
    assert handoff["stage128_m3i2_inquiry_follow_up_authorized_now"] is False
    assert handoff["stage128_m3i2_response_adjudication_authorized"] is False
    assert handoff["stage128_m3i2_inquiry_terminated_by_track_b"] is False


def test_the_human_docs_show_both_tracks_and_keep_the_old_rule_as_history():
    roadmap = _read_text("project/docs/ai/ROADMAP.md")
    assert (f"m3_lag_wdi_authoritative_contract_status: {_LOCKED_STATUS}"
            in roadmap)
    assert "m3_lag_wdi_next_action_authorized: false" in roadmap
    assert "TRACK A" in roadmap and "TRACK B" in roadmap
    for text in _DOCS:
        body = _read_text(text)
        # the superseded rule survives, explicitly labelled as history
        assert "UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY" in body
        assert "SUPERSEDED" in body.upper()
    # and no document may still call the merged PR #77 the live Draft
    for text in _DOCS + ("project/docs/ai/CURRENT_STATE.md",):
        body = _read_text(text)
        assert "live Draft **PR #77**" not in body
        assert "live Draft PR #77" not in body


# --------------------------------------------------------------------------- #
# FAIL-CLOSED DRIFT TESTS
# --------------------------------------------------------------------------- #

def _root(tmp_path, name: str, overrides: dict[str, dict]) -> str:
    """A minimal repository root carrying (optionally mutated) package files.

    Only the M3-LAG-WDI package is materialized: the recognizers under test
    read nothing else, so a drifted contract has nowhere to hide.
    """
    root = tmp_path / name
    (root / _PKG_REL).mkdir(parents=True)
    for rel in _ALL_RELS:
        payload = overrides.get(rel) or _read_json(rel)
        with open(os.path.join(str(root), rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    return str(root)


def _mutated(rel: str, mutate) -> dict[str, dict]:
    payload = copy.deepcopy(_read_json(rel))
    mutate(payload)
    return {rel: payload}


def test_the_unmutated_package_is_accepted_by_both_recognizers(tmp_path):
    """The drift tests below are only meaningful if the real one passes."""
    root = _root(tmp_path, "clean", {})
    markers = gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)
    assert markers["stage128_m3_lag_wdi_authoritative_contract_status"] == (
        _LOCKED_STATUS)
    from pathlib import Path
    assert v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root)) is True


def _set_lag_to_t(payload: dict) -> None:
    payload["features"][0]["observation_year_rule"] = "t"
    payload["features"][0]["observation_year_formula"] = (
        "wdi_observation_year = predictor_year_t")


def _change_cpi_code(payload: dict) -> None:
    payload["features"][0]["indicator_code"] = "FP.CPI.TOTL"


def _change_fx_code(payload: dict) -> None:
    payload["features"][1]["indicator_code"] = "PA.NUS.ATLS"


def _change_fx_formula(payload: dict) -> None:
    payload["features"][1]["transformation"] = (
        "FX_LAG1_t = 100 * (E_y / E_(y-1) - 1)")


def _add_third_feature(payload: dict) -> None:
    payload["features"].append(dict(payload["features"][0],
                                    feature_id="intl_financing_rate_lag1_wdi"))
    payload["additional_macro_feature_count"] = 3
    payload["feature_count_total"] = 15


def _break_parent_sample(payload: dict) -> None:
    payload["parent_sample"]["expected_parent_rows"] = 666


def _break_m2_feature_count(payload: dict) -> None:
    payload["m2_comparator"]["feature_count"] = 9


def _break_total_feature_count(payload: dict) -> None:
    payload["feature_count_total"] = 12


def _make_confirmatory(payload: dict) -> None:
    payload["scientific_role"] = "confirmatory_m3"


def _claim_point_in_time(payload: dict) -> None:
    payload["wdi_vintage_semantics"]["point_in_time_availability_claimed"] = (
        True)


def _drop_revised_wdi_semantics(payload: dict) -> None:
    payload["wdi_vintage_semantics"][
        "current_or_latest_revised_wdi_allowed"] = False


_CONTRACT_DRIFTS = (
    ("t_minus_1_becomes_t", _set_lag_to_t),
    ("cpi_indicator_code_changes", _change_cpi_code),
    ("fx_indicator_code_changes", _change_fx_code),
    ("fx_formula_changes", _change_fx_formula),
    ("a_third_macro_feature_is_added", _add_third_feature),
    ("parent_sample_is_not_539", _break_parent_sample),
    ("m2_is_not_12_features", _break_m2_feature_count),
    ("m3_lag_wdi_is_not_14_features", _break_total_feature_count),
    ("exploratory_becomes_confirmatory", _make_confirmatory),
    ("point_in_time_availability_becomes_true", _claim_point_in_time),
    ("current_revised_wdi_semantics_disappear", _drop_revised_wdi_semantics),
)


@pytest.mark.parametrize("label,mutate",
                         _CONTRACT_DRIFTS,
                         ids=[label for label, _ in _CONTRACT_DRIFTS])
def test_contract_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_CONTRACT_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate",
                         _CONTRACT_DRIFTS,
                         ids=[label for label, _ in _CONTRACT_DRIFTS])
def test_contract_drift_fails_closed_in_the_validator(tmp_path, label, mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_CONTRACT_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


_GATE_DRIFTS = (
    ("candidate_coverage_threshold_changes",
     lambda p: p["thresholds"].__setitem__("candidate_valid_coverage_min",
                                           0.5)),
    ("block_coverage_threshold_changes",
     lambda p: p["thresholds"].__setitem__("block_common_sample_coverage_min",
                                           0.3)),
    ("positive_event_minimum_changes",
     lambda p: p["thresholds"].__setitem__(
         "minimum_positive_evaluable_each_locked_validation_window", 1)),
    ("gate_becomes_executed",
     lambda p: p.update({"gate_executed": True, "gate_result": "PASS"})),
    ("a_coverage_value_becomes_zero_instead_of_null",
     lambda p: p["observed_values"].__setitem__(
         "block_common_sample_coverage", 0)),
    ("a_gate_pass_starts_authorizing_modeling",
     lambda p: p.update({"gate_pass_authorizes_modeling": True})),
)


@pytest.mark.parametrize("label,mutate", _GATE_DRIFTS,
                         ids=[label for label, _ in _GATE_DRIFTS])
def test_gate_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_GATE_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


_MODELING_DRIFTS = (
    ("exploratory_family_enters_the_confirmatory_holm_family",
     lambda p: p.update({
         "exploratory_comparison_inserted_into_confirmatory_holm_family":
             True})),
    ("the_exploratory_family_id_becomes_a_confirmatory_one",
     lambda p: p.update({"comparison_family_id": "M3_CBI_minus_M2"})),
    ("the_confirmatory_holm_family_is_rewritten",
     lambda p: p.update({"confirmatory_holm_family": [
         "M2_minus_M1", "M3_LAG_WDI_minus_M2", "M4_minus_M3_CBI"]})),
    ("a_fourth_model_family_appears",
     lambda p: p.update({"model_families": [
         "regularized_logistic_regression", "random_forest", "xgboost",
         "lightgbm"]})),
    ("retuning_becomes_permitted",
     lambda p: p.update({"retuning_permitted": True})),
    ("modeling_becomes_started",
     lambda p: p.update({"modeling_started": True})),
)


@pytest.mark.parametrize("label,mutate", _MODELING_DRIFTS,
                         ids=[label for label, _ in _MODELING_DRIFTS])
def test_modeling_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_MODELING_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


_AUDIT_DRIFTS = (
    ("retrieval_becomes_started",
     lambda p: p.update({"retrieval_started": True})),
    ("the_gate_becomes_executed",
     lambda p: p.update({"data_gate_executed": True})),
    ("modeling_becomes_started",
     lambda p: p.update({"modeling_started": True})),
    ("a_final_test_row_is_read",
     lambda p: p.update({"final_test_rows_read": 1})),
    ("a_wdi_value_is_read",
     lambda p: p["counters"].__setitem__("wdi_observation_values_read", 12)),
    ("a_world_bank_request_is_made",
     lambda p: p["counters"].__setitem__("world_bank_api_requests", 1)),
    ("a_model_is_fit",
     lambda p: p["counters"].__setitem__("model_fits", 3)),
    ("the_quarantined_bundle_is_used_as_value_input",
     lambda p: p.update({
         "earlier_historical_vintage_bundle_used_as_value_input": True})),
)


@pytest.mark.parametrize("label,mutate", _AUDIT_DRIFTS,
                         ids=[label for label, _ in _AUDIT_DRIFTS])
def test_execution_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_AUDIT_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate", _AUDIT_DRIFTS,
                         ids=[label for label, _ in _AUDIT_DRIFTS])
def test_execution_drift_fails_closed_in_the_validator(tmp_path, label,
                                                       mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_AUDIT_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


_BOUNDARY_DRIFTS = (
    ("the_world_bank_inquiry_is_terminated",
     lambda p: p.update({
         "world_bank_inquiry_status": "UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY",
     })),
    ("the_waiting_period_is_closed_early",
     lambda p: p.update({"world_bank_waiting_period_status": "COMPLETE"})),
    ("a_follow_up_becomes_authorized",
     lambda p: p.update({"world_bank_follow_up_authorized": True})),
    ("response_ingestion_becomes_authorized",
     lambda p: p.update({"world_bank_response_ingestion_authorized": True})),
    ("the_parallel_lock_claims_the_inquiry_failed",
     lambda p: p.update({"parallel_activation_implies_inquiry_failed": True})),
    ("retrieval_becomes_authorized",
     lambda p: p.update({"m3_lag_wdi_next_action_authorized": True})),
    ("the_final_test_is_unlocked",
     lambda p: p.update({"final_test_locked": False})),
    ("m3_cbi_is_quietly_resolved",
     lambda p: p.update({"m3_cbi_status": "PASS"})),
    ("m3i2_is_quietly_resolved",
     lambda p: p.update({"m3i2_evidence_status": "RESOLVED"})),
    ("the_superseded_rule_is_deleted_instead_of_kept",
     lambda p: p.update({"prior_restriction_retained_as_history": False})),
    ("merge_becomes_authorized",
     lambda p: p.update({"merge_authorized": True})),
)


@pytest.mark.parametrize("label,mutate", _BOUNDARY_DRIFTS,
                         ids=[label for label, _ in _BOUNDARY_DRIFTS])
def test_governance_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate", _BOUNDARY_DRIFTS,
                         ids=[label for label, _ in _BOUNDARY_DRIFTS])
def test_governance_drift_fails_closed_in_the_validator(tmp_path, label,
                                                        mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


_TOPOLOGY_DRIFTS = (
    ("pr_77_is_rendered_as_the_live_draft",
     lambda p: p.update({"live_pr_number": 77, "predecessor_pr_number": 76})),
    ("the_merged_predecessor_is_called_unmerged",
     lambda p: p.update({"predecessor_pr_merged": False})),
    ("the_live_pr_is_marked_ready_instead_of_draft",
     lambda p: p.update({"live_pr_is_draft": False})),
    ("the_live_pr_is_marked_merged",
     lambda p: p.update({"live_pr_merged": True})),
    ("the_live_head_is_pinned",
     lambda p: p.update({"live_pr_head_commit_pinned": True})),
    ("the_pr_stops_targeting_main",
     lambda p: p.update({"live_pr_base_branch": "stage128-something"})),
)


@pytest.mark.parametrize("label,mutate", _TOPOLOGY_DRIFTS,
                         ids=[label for label, _ in _TOPOLOGY_DRIFTS])
def test_topology_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_TOPOLOGY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


# --------------------------------------------------------------------------- #
# BLOCKER 1 REGRESSION — the three historical PR roles are pinned facts
#
# PR #76 initiated the final official documentary RECOVERY; PR #77 recorded the
# later HUMAN inquiry SUBMISSION; PR #78 is the current LIVE Draft contract
# lock. Three actions, three PRs, three merge states. "The recovery PR" is a
# NAME for the first of them — it must never be re-derived to mean "whichever
# PR merged immediately before the live one", because that quietly rewrites
# history every time a new Draft is opened.
# --------------------------------------------------------------------------- #

_RECOVERY_PR = 76
_RECOVERY_MERGE_COMMIT = "89d8e6ff2d12ec82903cd28aa7ab839eb946b658"
_HUMAN_SUBMISSION_PR = 77
_HUMAN_SUBMISSION_MERGE_COMMIT = "93de6bae9344ce893b0261f818abce8a991cf842"
_LIVE_PR = 78


def test_the_three_historical_pr_roles_are_recorded_separately():
    topo = _read_json(_TOPOLOGY_REL)
    assert topo["documentary_recovery_pr_number"] == _RECOVERY_PR
    assert topo["documentary_recovery_pr_merged"] is True
    assert topo["documentary_recovery_pr_merge_commit"] == (
        _RECOVERY_MERGE_COMMIT)
    assert topo["documentary_recovery_pr_action_id"] == (
        "stage128-m3i2-final-official-documentary-recovery-initiation")
    assert topo["documentary_recovery_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr77")
    assert topo["human_submission_pr_number"] == _HUMAN_SUBMISSION_PR
    assert topo["human_submission_pr_merged"] is True
    assert topo["human_submission_pr_merge_commit"] == (
        _HUMAN_SUBMISSION_MERGE_COMMIT)
    assert topo["human_submission_pr_action_id"] == (
        "stage128-m3i2-final-official-inquiry-human-submission")
    assert topo["live_pr_number"] == _LIVE_PR
    assert topo["live_pr_is_draft"] is True
    assert topo["live_pr_merged"] is False
    # the two merged PRs are two different merges, not one relabelled twice
    assert (topo["documentary_recovery_pr_merge_commit"]
            != topo["human_submission_pr_merge_commit"])
    assert topo["pr_roles_re_derived_from_adjacency"] is False
    assert topo["pr_roles_are_historical_facts_not_positional"] is True
    assert [(e["pr_number"], e["merged"]) for e in topo["pr_role_sequence"]] \
        == [(_RECOVERY_PR, True), (_HUMAN_SUBMISSION_PR, True),
            (_LIVE_PR, False)]


def test_the_handoff_keeps_pr76_as_the_documentary_recovery(handoff):
    """The regression this test exists for: #76's fields becoming #77's."""
    assert handoff["stage128_m3i2_recovery_pr_number"] == _RECOVERY_PR
    assert handoff["stage128_m3i2_recovery_pr_merged"] is True
    assert handoff["stage128_m3i2_recovery_pr_merge_commit"] == (
        _RECOVERY_MERGE_COMMIT)
    assert handoff["stage128_m3i2_recovery_pr_role"] == (
        "final_official_documentary_recovery_initiation_pr")
    # superseded by the human-submission PR, NOT by whatever is live now
    assert handoff["stage128_m3i2_recovery_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr77")


def test_the_handoff_keeps_pr77_as_the_human_submission_recording(handoff):
    assert handoff["stage128_m3i2_human_submission_pr_number"] == (
        _HUMAN_SUBMISSION_PR)
    assert handoff["stage128_m3i2_human_submission_pr_merged"] is True
    assert handoff["stage128_m3i2_human_submission_pr_merge_commit"] == (
        _HUMAN_SUBMISSION_MERGE_COMMIT)
    assert handoff["stage128_m3i2_human_submission_pr_role"] == (
        "final_official_inquiry_human_submission_recording_pr")


def test_the_handoff_keeps_pr78_as_the_live_draft(handoff):
    assert handoff["stage128_m3i2_live_pr_number"] == _LIVE_PR
    assert handoff["stage128_m3i2_live_pr_is_draft"] is True
    assert handoff["stage128_m3i2_live_pr_merged"] is False
    assert handoff["stage128_m3i2_live_pr_role"] == (
        "m3_lag_wdi_exploratory_contract_lock_pr")
    assert handoff["stage128_m3i2_live_pr_ready_for_review_authorized"] is (
        False)
    assert handoff["stage128_m3i2_merge_authorized"] is False


def test_the_three_pr_roles_cannot_be_collapsed_or_shifted(handoff):
    numbers = (handoff["stage128_m3i2_recovery_pr_number"],
               handoff["stage128_m3i2_human_submission_pr_number"],
               handoff["stage128_m3i2_live_pr_number"])
    assert numbers == (_RECOVERY_PR, _HUMAN_SUBMISSION_PR, _LIVE_PR)
    assert len(set(numbers)) == 3
    assert (handoff["stage128_m3i2_recovery_pr_merge_commit"]
            != handoff["stage128_m3i2_human_submission_pr_merge_commit"])
    assert handoff["stage128_m3i2_pr_roles_are_historical_facts_not_"
                   "positional"] is True
    assert [(e["pr_number"], e["role"]) for e
            in handoff["stage128_m3i2_pr_role_sequence"]] == [
        (_RECOVERY_PR, "final_official_documentary_recovery_initiation_pr"),
        (_HUMAN_SUBMISSION_PR,
         "final_official_inquiry_human_submission_recording_pr"),
        (_LIVE_PR, "m3_lag_wdi_exploratory_contract_lock_pr")]


def test_the_docs_state_the_pr_roles_explicitly():
    for rel in _DOCS:
        body = _read_text(rel)
        assert _RECOVERY_MERGE_COMMIT in body, rel
        assert _HUMAN_SUBMISSION_MERGE_COMMIT in body, rel
        assert (
            "stage128-m3i2-final-official-documentary-recovery-initiation"
            in body), rel
        assert (
            "stage128-m3i2-final-official-inquiry-human-submission"
            in body), rel


_PR_ROLE_DRIFTS = (
    # the exact regression that PR #78 shipped: the recovery fields slid from
    # PR #76 onto the immediately preceding PR #77
    ("the_recovery_pr_slides_onto_pr77",
     lambda p: p.update({
         "documentary_recovery_pr_number": 77,
         "documentary_recovery_pr_merge_commit": (
             _HUMAN_SUBMISSION_MERGE_COMMIT)})),
    ("the_recovery_merge_commit_is_replaced_by_the_submission_merge",
     lambda p: p.update({
         "documentary_recovery_pr_merge_commit": (
             _HUMAN_SUBMISSION_MERGE_COMMIT)})),
    ("the_recovery_semantics_are_re_anchored_onto_the_live_pr",
     lambda p: p.update({
         "documentary_recovery_pr_semantics":
             "merged_predecessor_superseded_by_pr78"})),
    ("the_recovery_role_is_relabelled_as_the_human_submission",
     lambda p: p.update({
         "documentary_recovery_pr_role":
             "final_official_inquiry_human_submission_recording_pr"})),
    ("the_human_submission_pr_is_dropped",
     lambda p: p.pop("human_submission_pr_number")),
    ("the_human_submission_pr_is_collapsed_into_the_recovery_pr",
     lambda p: p.update({
         "human_submission_pr_number": 76,
         "human_submission_pr_merge_commit": _RECOVERY_MERGE_COMMIT})),
    ("the_two_merged_prs_are_given_one_merge_commit",
     lambda p: p.update({
         "human_submission_pr_merge_commit": _RECOVERY_MERGE_COMMIT})),
    ("roles_are_declared_re_derivable_from_adjacency",
     lambda p: p.update({"pr_roles_re_derived_from_adjacency": True})),
    ("the_role_sequence_drops_the_recovery_pr",
     lambda p: p.update({
         "pr_role_sequence": p["pr_role_sequence"][1:]})),
    ("the_role_sequence_is_reordered",
     lambda p: p.update({
         "pr_role_sequence": list(reversed(p["pr_role_sequence"]))})),
)


@pytest.mark.parametrize("label,mutate", _PR_ROLE_DRIFTS,
                         ids=[label for label, _ in _PR_ROLE_DRIFTS])
def test_pr_role_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_TOPOLOGY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate", _PR_ROLE_DRIFTS,
                         ids=[label for label, _ in _PR_ROLE_DRIFTS])
def test_pr_role_drift_fails_closed_in_the_validator(tmp_path, label, mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_TOPOLOGY_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


# --------------------------------------------------------------------------- #
# BLOCKER 2 REGRESSION — retrieval, the Data Gate and modeling are SEPARATE
#
# An authorization boundary only exists where an action boundary exists. If one
# action both retrieved and Gated, the human authorization to retrieve would
# silently become an authorization to ADMIT data; if a Gate PASS authorized
# modeling, admission would silently become evaluation. Each of these tests
# asserts that a surface which erases one of those boundaries fails closed.
# --------------------------------------------------------------------------- #

_RETRIEVAL_ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-retrieval"
_POST_RETRIEVAL_AUDIT_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit")
_DATA_GATE_ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-gate"
_MODELING_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-incremental-evaluation")


def test_the_next_action_is_a_separated_step_and_never_the_gate(handoff):
    # The pointer ADVANCES as Track B steps complete, so pinning it to one
    # action id would encode a moment. The rule that must hold at every step:
    # the pointer is one of the separated steps, it is never the Data Gate
    # itself, it never executes the Gate, and it is never an authorization.
    assert handoff["stage128_m3_lag_wdi_next_action_id"] in (
        _RETRIEVAL_ACTION_ID, _POST_RETRIEVAL_AUDIT_ACTION_ID)
    assert handoff["stage128_m3_lag_wdi_next_action_id"] != _DATA_GATE_ACTION_ID
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    assert handoff[
        "stage128_m3_lag_wdi_next_action_executes_data_gate"] is False
    assert handoff["stage128_m3_lag_wdi_retrieval_executes_data_gate"] is False
    # retrieval may have been authorized once, but never as a standing grant
    if handoff["stage128_m3_lag_wdi_retrieval_authorized"] is True:
        assert handoff[
            "stage128_m3_lag_wdi_retrieval_authorization_consumed"] is True
        assert handoff[
            "stage128_m3_lag_wdi_retrieval_authorization_reusable"] is False
    else:
        assert handoff["stage128_m3_lag_wdi_data_retrieval_started"] is False


def test_the_data_gate_is_a_separate_unauthorized_action(handoff):
    assert handoff["stage128_m3_lag_wdi_data_gate_action_id"] == (
        _DATA_GATE_ACTION_ID)
    assert (handoff["stage128_m3_lag_wdi_data_gate_action_id"]
            != handoff["stage128_m3_lag_wdi_retrieval_action_id"])
    assert handoff["stage128_m3_lag_wdi_data_gate_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_data_gate_is_a_separate_action"] is True
    assert handoff[
        "stage128_m3_lag_wdi_data_gate_requires_new_human_authorization"] is (
            True)
    # a pointer to the Gate is not an authorization to execute it
    assert handoff[
        "stage128_m3_lag_wdi_data_gate_pointer_is_not_authorization"] is True
    assert handoff["stage128_m3_lag_wdi_data_gate_executed"] is False
    assert handoff["stage128_m3_lag_wdi_data_gate_result"] == "NOT_EXECUTED"


def test_a_retrieval_authorization_never_authorizes_the_gate(handoff):
    assert handoff[
        "stage128_m3_lag_wdi_retrieval_authorization_implies_gate_"
        "authorization"] is False
    assert handoff[
        "stage128_m3_lag_wdi_combined_retrieval_and_gate_action_permitted"] is (
            False)


def test_a_gate_pass_admits_data_and_authorizes_no_modeling(handoff, gate,
                                                            modeling):
    assert handoff[
        "stage128_m3_lag_wdi_gate_pass_is_data_admission_only"] is True
    assert handoff["stage128_m3_lag_wdi_gate_pass_authorizes_modeling"] is (
        False)
    assert handoff["stage128_m3_lag_wdi_modeling_action_id"] == (
        _MODELING_ACTION_ID)
    assert handoff["stage128_m3_lag_wdi_modeling_authorized"] is False
    assert handoff[
        "stage128_m3_lag_wdi_modeling_requires_new_human_authorization"] is (
            True)
    assert gate["gate_pass_authorizes_modeling"] is False
    assert gate["gate_pass_is_data_admission_only"] is True
    assert modeling["gate_pass_authorizes_modeling"] is False
    assert modeling["modeling_authorized_by_gate_pass"] is False


def test_the_published_action_sequence_separates_every_step(handoff):
    sequence = handoff["stage128_m3_lag_wdi_action_sequence"]
    assert [(e["step"], e["action_id"]) for e in sequence] == [
        ("A", _ACTION_ID),
        ("B", _RETRIEVAL_ACTION_ID),
        ("C", _POST_RETRIEVAL_AUDIT_ACTION_ID),
        ("D", _DATA_GATE_ACTION_ID),
        ("E", _MODELING_ACTION_ID)]
    # exactly one step retrieves, exactly one Gates, exactly one models, and
    # no single step does two of them
    assert sum(e["executes_retrieval"] for e in sequence) == 1
    assert sum(e["executes_data_gate"] for e in sequence) == 1
    assert sum(e["executes_modeling"] for e in sequence) == 1
    for entry in sequence:
        assert sum((entry["executes_retrieval"], entry["executes_data_gate"],
                    entry["executes_modeling"])) <= 1, entry["action_id"]
    # every step that has NOT been carried out under its own authorization is
    # unauthorized; steps C, D and E are always unauthorized here, whatever has
    # already completed
    by_step = {e["step"]: e for e in sequence}
    for step in ("C", "D", "E"):
        assert by_step[step]["authorized"] is False, step
    assert by_step["A"]["authorized"] is True


def test_the_docs_separate_retrieval_from_the_gate():
    for rel in _DOCS:
        body = _read_text(rel)
        assert _DATA_GATE_ACTION_ID in body, rel
        assert _MODELING_ACTION_ID in body, rel
        assert (
            "m3_lag_wdi_retrieval_authorization_implies_gate_authorization: "
            "false" in body
            or "m3_lag_wdi_retrieval_authorization_implies_gate_authorization:"
            "\n  false" in body
            or "`m3_lag_wdi_retrieval_authorization_implies_gate_"
               "authorization:\n  false`" in body), rel
    roadmap = _read_text("project/docs/ai/ROADMAP.md")
    # The pointer scope advances with the sequence, so what must always hold is
    # that retrieval keeps its OWN action id, separate from the Gate's, and
    # that the current pointer never claims to execute the Gate.
    assert f"m3_lag_wdi_retrieval_action_id: {_RETRIEVAL_ACTION_ID}" in roadmap
    assert f"m3_lag_wdi_data_gate_action_id: {_DATA_GATE_ACTION_ID}" in roadmap
    assert "m3_lag_wdi_data_gate_authorized: false" in roadmap
    assert "m3_lag_wdi_next_action_executes_data_gate: false" in roadmap
    assert "m3_lag_wdi_data_gate_authorized: false" in roadmap
    assert "m3_lag_wdi_gate_pass_authorizes_modeling: false" in roadmap


_GATE_SEPARATION_DRIFTS = (
    ("retrieval_authorization_is_said_to_authorize_the_gate",
     lambda p: p.update({
         "retrieval_authorization_implies_gate_authorization": True})),
    ("the_retrieval_action_is_said_to_execute_the_gate",
     lambda p: p.update({"gate_executed_by_retrieval_action": True})),
    ("a_combined_retrieval_and_gate_action_is_permitted",
     lambda p: p.update({
         "combined_retrieval_and_gate_action_permitted": True})),
    ("the_gate_is_given_the_retrieval_action_identity",
     lambda p: p.update({"gate_action_id": _RETRIEVAL_ACTION_ID})),
    ("the_gate_becomes_authorized",
     lambda p: p.update({"gate_action_authorized": True})),
    ("the_gate_stops_needing_its_own_human_authorization",
     lambda p: p.update({
         "gate_requires_new_explicit_human_authorization": False})),
    ("the_gate_pointer_is_treated_as_an_authorization",
     lambda p: p.update({"gate_pointer_is_not_authorization": False})),
    ("a_gate_pass_is_said_to_authorize_modeling",
     lambda p: p.update({"gate_pass_authorizes_modeling": True})),
    ("a_gate_pass_stops_being_data_admission_only",
     lambda p: p.update({"gate_pass_is_data_admission_only": False})),
    ("the_post_retrieval_audit_is_said_to_execute_the_gate",
     lambda p: p.update({"post_retrieval_audit_action_executes_gate": True})),
)


@pytest.mark.parametrize("label,mutate", _GATE_SEPARATION_DRIFTS,
                         ids=[label for label, _ in _GATE_SEPARATION_DRIFTS])
def test_gate_separation_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_GATE_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate", _GATE_SEPARATION_DRIFTS,
                         ids=[label for label, _ in _GATE_SEPARATION_DRIFTS])
def test_gate_separation_drift_fails_closed_in_the_validator(tmp_path, label,
                                                             mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_GATE_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


def _conflated_sequence(payload: dict) -> None:
    """One action that both retrieves and Gates — the boundary erased."""
    payload["m3_lag_wdi_action_sequence"] = [
        {"step": "A", "action_id": _ACTION_ID, "authorized": True,
         "executes_retrieval": False, "executes_data_gate": False,
         "executes_modeling": False},
        {"step": "B", "action_id": _RETRIEVAL_ACTION_ID, "authorized": False,
         "executes_retrieval": True, "executes_data_gate": True,
         "executes_modeling": False},
    ]


_BOUNDARY_SEPARATION_DRIFTS = (
    ("the_pointer_scope_grows_to_include_the_gate",
     lambda p: p.update({
         "m3_lag_wdi_next_action_scope": "retrieval_and_data_gate"})),
    ("the_pointer_is_said_to_execute_the_gate",
     lambda p: p.update({
         "m3_lag_wdi_next_action_executes_data_gate": True})),
    ("the_retrieval_action_is_said_to_execute_the_gate",
     lambda p: p.update({
         "m3_lag_wdi_retrieval_action_executes_data_gate": True})),
    ("retrieval_authorization_implies_gate_authorization",
     lambda p: p.update({
         "m3_lag_wdi_retrieval_authorization_implies_gate_authorization":
             True})),
    ("a_combined_retrieval_and_gate_action_is_permitted",
     lambda p: p.update({
         "m3_lag_wdi_combined_retrieval_and_gate_action_permitted": True})),
    ("the_gate_becomes_authorized",
     lambda p: p.update({"m3_lag_wdi_data_gate_action_authorized": True})),
    ("retrieval_becomes_authorized",
     lambda p: p.update({"m3_lag_wdi_retrieval_action_authorized": True})),
    ("the_gate_and_retrieval_share_one_action_identity",
     lambda p: p.update({
         "m3_lag_wdi_data_gate_action_id": _RETRIEVAL_ACTION_ID})),
    ("a_gate_pass_is_said_to_authorize_modeling",
     lambda p: p.update({
         "m3_lag_wdi_gate_pass_authorizes_modeling": True})),
    ("a_gate_pass_stops_being_data_admission_only",
     lambda p: p.update({
         "m3_lag_wdi_gate_pass_is_data_admission_only": False})),
    ("the_gate_stops_needing_its_own_human_authorization",
     lambda p: p.update({
         "m3_lag_wdi_data_gate_requires_new_explicit_human_authorization":
             False})),
    ("one_action_both_retrieves_and_gates", _conflated_sequence),
    ("a_future_action_is_marked_authorized",
     lambda p: p["m3_lag_wdi_action_sequence"][3].update(
         {"authorized": True})),
    ("the_gate_step_is_dropped_from_the_sequence",
     lambda p: p.update({
         "m3_lag_wdi_action_sequence": [
             e for e in p["m3_lag_wdi_action_sequence"]
             if e["step"] != "D"]})),
)


@pytest.mark.parametrize("label,mutate", _BOUNDARY_SEPARATION_DRIFTS,
                         ids=[label for label, _ in
                              _BOUNDARY_SEPARATION_DRIFTS])
def test_boundary_separation_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, label, _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


@pytest.mark.parametrize("label,mutate", _BOUNDARY_SEPARATION_DRIFTS,
                         ids=[label for label, _ in
                              _BOUNDARY_SEPARATION_DRIFTS])
def test_boundary_separation_drift_fails_closed_in_the_validator(
        tmp_path, label, mutate):
    from pathlib import Path
    root = _root(tmp_path, f"v_{label}", _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_exploratory_contract_locked(Path(root))


def test_modeling_contract_drift_on_gate_pass_fails_closed(tmp_path):
    for label, mutate in (
        ("gate_pass_authorizes_modeling",
         lambda p: p.update({"gate_pass_authorizes_modeling": True})),
        ("modeling_authorized_by_gate_pass",
         lambda p: p.update({"modeling_authorized_by_gate_pass": True})),
        ("modeling_stops_needing_its_own_authorization",
         lambda p: p.update({
             "modeling_requires_new_explicit_human_authorization": False})),
    ):
        root = _root(tmp_path, f"m_{label}", _mutated(_MODELING_REL, mutate))
        with pytest.raises(gen.HandoffError):
            gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


def test_a_forged_authorization_digest_fails_closed(tmp_path):
    root = _root(tmp_path, "forged", _mutated(
        _AUTH_REL,
        lambda p: p.update({"authorization_text": "بله"})))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


def test_a_reusable_authorization_fails_closed(tmp_path):
    root = _root(tmp_path, "reusable", _mutated(
        _AUTH_REL,
        lambda p: p.update({"authorization_is_reusable_for_retrieval": True})))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_exploratory_markers(root)


def test_an_absent_package_yields_no_markers(tmp_path):
    """Before the lock exists the generator must stay silent, not guess."""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert gen.derive_stage128_m3_lag_wdi_exploratory_markers(str(empty)) == {}
    from pathlib import Path
    assert v.stage128_m3_lag_wdi_exploratory_contract_locked(
        Path(str(empty))) is False
