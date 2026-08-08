"""Tests — Stage128 Track B: the M3-LAG-WDI CALENDAR-MAPPING LOCK.

These tests police one narrow claim: exactly one timing convention was locked,
for timing reasons, and *nothing else happened*.

The interesting tests are the ones that try to make `+622` lockable. It cannot
be: the runner recomputes the timing evidence from committed bytes and refuses
any offset admitting a single violation, so swapping the constant is not
enough. Equally important, the lock must not become a licence — it authorizes
no feature table, no model, no step E and no Final Test access.
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project"))

import update_ai_handoff as gen  # noqa: E402
from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_calendar_mapping_lock as m)

_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_calendar_mapping_lock"
_DECISION_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_calendar_mapping_decision.json")
_EVIDENCE_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_calendar_mapping_timing_evidence.json")
_AUDIT_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_calendar_mapping_execution_audit.json")
_BOUNDARY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_calendar_mapping_governance_boundary"
    ".json")
_QC_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_calendar_mapping_qc_report.json"

_FORBIDDEN_RUNTIME = ("sklearn", "xgboost", "imblearn", "shap", "lightgbm",
                      "catboost", "statsmodels")


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _read_json(_DECISION_REL)


@pytest.fixture(scope="module")
def evidence() -> dict:
    return _read_json(_EVIDENCE_REL)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


@pytest.fixture(scope="module")
def handoff() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


# --------------------------------------------------------------------------- #
# STRUCTURAL: no network, no estimator, no calendar library
# --------------------------------------------------------------------------- #

def test_no_forbidden_runtime_is_bound_in_the_module():
    bound = {name for name, value in vars(m).items()
             if getattr(value, "__name__", "") in _FORBIDDEN_RUNTIME}
    assert bound == set(), bound


def test_the_module_has_no_network_or_estimator_source():
    for rel in ("project/src/"
                "stage128_m3_lag_wdi_exploratory_calendar_mapping_lock.py",
                "project/"
                "run_stage128_m3_lag_wdi_exploratory_calendar_mapping_lock.py"):
        text = open(os.path.join(REPO_ROOT, rel), encoding="utf-8").read()
        for token in ("urllib", "requests.", "http.client", "socket",
                      "sklearn", "xgboost", "predict_proba", "fit_predict"):
            assert token not in text, (rel, token)


def test_the_decisive_evidence_needs_no_calendar_library(evidence):
    """The leakage test is integer arithmetic on committed columns.

    A second Jalali implementation inside this action could drift from the
    project's canonical pinned one, so the decisive computation deliberately
    does not need one.
    """
    assert evidence["calendar_library_required"] is False
    assert evidence["recomputable_from_committed_bytes"] is True
    assert set(evidence["columns_read"]) == {
        "fiscal_year_t", "target_year", "pair_cutoff_date"}


# --------------------------------------------------------------------------- #
# The authorization is its own, single-use, and reaches no later step
# --------------------------------------------------------------------------- #

def test_the_authorization_is_this_decision_and_single_use():
    import hashlib
    rec = m.verify_human_authorization()
    assert "CALENDAR-MAPPING LOCK ONLY" in rec["authorization_text"]
    assert "RECOMMEND_LOCK_JALALI_PLUS_621" in rec["authorization_text"]
    assert m.ACTION_ID in rec["authorization_text"]
    raw = rec["authorization_text"].encode("utf-8")
    assert rec["authorization_utf8_bytes"] == len(raw)
    assert rec["authorization_sha256"] == hashlib.sha256(raw).hexdigest()
    assert rec["authorization_is_single_use"] is True
    for field in ("authorization_covers_step_e",
                  "authorization_covers_modeling",
                  "authorization_covers_feature_value_table",
                  "authorization_covers_final_test",
                  "authorization_covers_new_retrieval",
                  "authorization_covers_gate_rerun",
                  "authorization_covers_audit_rerun",
                  "prior_data_gate_authorization_reused",
                  "standing_authorization"):
        assert rec[field] is False, field


def test_the_authorization_differs_from_every_prior_track_b_one():
    digest = m.verify_human_authorization()["authorization_sha256"]
    from src import (
        stage128_m3_lag_wdi_exploratory_post_retrieval_audit as step_c)
    from src import stage128_m3_lag_wdi_exploratory_data_gate as step_d
    prior = {
        "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b",
        "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604",
        step_c.verify_human_authorization()["authorization_sha256"],
        step_d.verify_human_authorization()["authorization_sha256"],
    }
    assert digest not in prior


# --------------------------------------------------------------------------- #
# THE CORE: +622 is structurally unlockable
# --------------------------------------------------------------------------- #

def test_the_locked_offset_has_zero_timing_violations(evidence):
    selected = evidence["per_offset"][str(m.LOCKED_OFFSET)]
    assert selected["timing_violation_rows"] == 0
    assert selected["satisfies_necessary_timing_condition"] is True
    assert selected["rows_evaluated"] == 539


def test_the_rejected_offset_really_does_violate_the_timing_rule(evidence):
    rejected = evidence["per_offset"][str(m.REJECTED_OFFSET)]
    assert rejected["timing_violation_rows"] == 22
    assert rejected["satisfies_necessary_timing_condition"] is False
    # spread across every cohort, not an edge case
    assert set(rejected["timing_violation_fiscal_years"]) == {
        "1392", "1393", "1394", "1395", "1396", "1397", "1398"}
    assert rejected["worst_violation_days_after_cutoff"] > 0
    assert rejected["margin_days_min"] < 0


def test_a_violating_offset_cannot_be_locked(evidence):
    """The whole point: preferring +622 is not enough to lock it."""
    with pytest.raises(m.CalendarMappingLockError):
        m.assert_offset_is_lockable(evidence, m.REJECTED_OFFSET)


def test_the_locked_offset_passes_the_same_gate(evidence):
    m.assert_offset_is_lockable(evidence, m.LOCKED_OFFSET)


def test_an_unevaluated_offset_cannot_be_locked(evidence):
    with pytest.raises(m.CalendarMappingLockError):
        m.assert_offset_is_lockable(evidence, 620)


@pytest.mark.parametrize("offset", [0, 620, 623, 1400, -621])
def test_only_the_two_admissible_offsets_can_be_evaluated(offset):
    with pytest.raises(m.CalendarMappingLockError):
        m.evaluate_offset([], offset)


def test_the_evaluation_is_reproducible_from_committed_bytes(evidence):
    """Recompute independently and require the committed numbers back."""
    from pathlib import Path
    rows = m.load_development_rows(Path(REPO_ROOT))
    assert len(rows) == 539
    for offset in m.ADMISSIBLE_OFFSETS:
        fresh = m.evaluate_offset(rows, offset)
        stored = evidence["per_offset"][str(offset)]
        for field in ("timing_violation_rows", "margin_days_min",
                      "margin_days_median", "predictor_year_first",
                      "predictor_year_last", "observation_year_first",
                      "observation_year_last"):
            assert fresh[field] == stored[field], (offset, field)


# --------------------------------------------------------------------------- #
# No feature-value table without a locked mapping
# --------------------------------------------------------------------------- #

def test_a_feature_table_is_refused_while_the_mapping_is_unlocked():
    for state in ({}, {"calendar_mapping_locked": False},
                  {"calendar_mapping_locked": None}):
        with pytest.raises(m.CalendarMappingLockError):
            m.assert_feature_table_permitted(state)


def test_a_feature_table_is_permitted_once_the_mapping_is_locked():
    m.assert_feature_table_permitted({"calendar_mapping_locked": True})


def test_no_feature_value_table_exists_in_the_lock_package():
    pkg = os.path.join(REPO_ROOT, _PKG_REL)
    for name in os.listdir(pkg):
        assert "development_features" not in name, name
        assert "feature_values" not in name, name


def test_the_lock_read_no_feature_or_outcome_value(evidence):
    assert evidence["feature_values_read"] == 0
    assert evidence["outcome_values_read"] == 0
    assert evidence["final_test_rows_read"] == 0


# --------------------------------------------------------------------------- #
# The decision is a TIMING decision, recorded as such
# --------------------------------------------------------------------------- #

def test_the_locked_rule_is_exactly_plus_621(decision):
    assert decision["calendar_mapping_locked"] is True
    assert decision["calendar_mapping_rule"] == "jalali_fiscal_year_t_plus_621"
    assert decision["calendar_mapping_rule_formula"] == (
        "predictor_year_t = jalali_fiscal_year_t + 621")
    assert decision["calendar_mapping_locked_offset"] == 621
    assert decision["rejected_offset"] == 622
    assert decision["calendar_mapping_lock_action_id"] == m.ACTION_ID
    assert decision["calendar_mapping_lock_required_before_modeling"] is False


def test_the_selection_is_independent_of_model_performance(decision):
    assert decision["selection_basis"] == (
        "temporal_semantics_and_leakage_prevention_only")
    assert decision["selection_used_model_performance"] is False
    assert decision["selection_used_coverage_comparison"] is False
    assert decision["selection_used_feature_values"] is False
    assert decision["selection_reversible_by_a_better_predictive_result"] is (
        False)


def test_the_recorded_semantics_are_complete(decision):
    fy = decision["fiscal_year_semantics"]
    assert fy["fiscal_year_t_labels"] == (
        "the Jalali year in which the accounting period ENDS")
    assert fy["agreement_rows"] == 539 and fy["mismatches"] == 0
    # honest about what is recomputed and what is recorded provenance
    assert fy["recomputed_by_this_action"] is False
    assert fy["decides_the_lock"] is False
    assert fy["not_recomputed_reason"]

    rules = decision["observation_year_rules"]
    assert rules["intl_cpi_inflation_lag1_wdi"][
        "required_observation_years"] == ["t-1"]
    assert rules["intl_fx_change_official_lag1_wdi"][
        "required_observation_years"] == ["t-1", "t-2"]
    assert rules["binding_observation_year"] == "t-1"
    assert rules["changed_by_this_action"] is False
    for feat in ("intl_cpi_inflation_lag1_wdi",
                 "intl_fx_change_official_lag1_wdi"):
        assert rules[feat]["same_year_t_observation_permitted"] is False


def test_changing_the_mapping_needs_a_new_human_decision(decision):
    assert decision[
        "changing_the_locked_mapping_requires_new_explicit_human_decision"] is (
            True)


def test_the_point_in_time_limitation_survives_the_lock(decision):
    assert decision[
        "point_in_time_availability_established_by_this_lock"] is False
    limits = decision["unresolved_limitations"]
    assert len(limits) >= 4
    joined = " ".join(limits).lower()
    assert "point-in-time" in joined
    assert "2021-2024" in joined
    assert "2024-2025" in joined
    assert "conservative temporal-separation" in joined


def test_the_contract_is_amended_not_edited(decision):
    assert decision["amends_but_does_not_edit"] is True
    assert decision["historical_unlocked_state_erased"] is False
    assert decision["amends_contract"] == m.AMENDED_CONTRACT_REL
    assert decision["superseding_pattern_precedent"] == (
        m.SUPERSEDING_PATTERN_PRECEDENT)
    # the frozen contract's own bytes still carry no mapping field
    contract = _read_json(m.AMENDED_CONTRACT_REL)
    assert "predictor_year_calendar_mapping" not in json.dumps(contract)
    assert contract["contract_status"] == (
        "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL")


# --------------------------------------------------------------------------- #
# The lock authorizes NOTHING downstream
# --------------------------------------------------------------------------- #

def test_the_lock_is_not_an_authorization_for_anything(boundary):
    for field in ("calendar_mapping_lock_is_modeling_authorization",
                  "calendar_mapping_lock_authorizes_feature_value_table",
                  "calendar_mapping_lock_propagates_to_step_e",
                  "calendar_mapping_lock_is_final_test_unlock",
                  "calendar_mapping_lock_changed_the_gate_result",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_data_gate_rerun_by_this_action",
                  "m3_lag_wdi_post_retrieval_audit_rerun_by_this_action",
                  "m3_lag_wdi_contract_edited_by_this_action",
                  "m3_lag_wdi_gate_thresholds_modified_by_this_action",
                  "new_world_bank_request_made_by_this_action",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "ready_for_review_authorized"):
        assert boundary[field] is False, field
    assert boundary["m3_lag_wdi_next_action_id"] == (
        "stage128-m3-lag-wdi-exploratory-incremental-evaluation")


def test_its_own_authorization_is_consumed_and_never_standing(boundary):
    assert boundary[
        "m3_lag_wdi_calendar_mapping_lock_authorization_consumed"] is True
    assert boundary[
        "m3_lag_wdi_calendar_mapping_lock_authorization_reusable"] is False
    assert boundary["m3_lag_wdi_calendar_mapping_lock_authorized_now"] is False


def test_upstream_results_are_preserved(boundary):
    assert boundary["m3_lag_wdi_data_gate_result"] == (
        "PASS_M3_LAG_WDI_DATA_GATE")
    assert boundary["m3_lag_wdi_block_admitted"] is True
    assert boundary["m3_lag_wdi_block_admission_is_data_admission_only"] is True
    assert boundary["step_c_material_findings_preserved"] is True
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["point_in_time_availability_claimed"] is False


def test_execution_counters_hold_the_boundary():
    audit = _read_json(_AUDIT_REL)
    assert audit["calendar_mapping_lock_executed"] is True
    assert audit["calendar_mapping_lock_executions"] == 1
    for counter in ("world_bank_api_requests", "feature_value_tables_"
                    "materialized", "feature_values_computed", "model_fits",
                    "predictions", "data_gate_executions",
                    "post_retrieval_audit_executions", "tuning_runs",
                    "cross_validation_runs", "shap_executions",
                    "final_test_rows_read"):
        assert audit[counter] == 0, counter
    assert audit["authoritative_contract_edited"] is False
    assert audit["data_gate_artifacts_modified"] is False


def test_qc_all_pass():
    qc = _read_json(_QC_REL)
    assert qc["all_pass"] is True
    assert qc["checks_failed"] == 0


# --------------------------------------------------------------------------- #
# The Handoff publishes the lock, and publishes it as a timing fact only
# --------------------------------------------------------------------------- #

def test_the_handoff_publishes_the_locked_mapping(handoff):
    assert handoff["stage128_m3_lag_wdi_calendar_mapping_locked"] is True
    assert handoff["stage128_m3_lag_wdi_calendar_mapping_rule"] == (
        "jalali_fiscal_year_t_plus_621")
    assert handoff["stage128_m3_lag_wdi_calendar_mapping_lock_action_id"] == (
        m.ACTION_ID)
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_lock_required_before_modeling"
    ] is False
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_rejected_offset"] == 622
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_rejected_offset_violations"
    ] == 22


def test_the_handoff_keeps_step_e_closed_after_the_lock(handoff):
    assert handoff["stage128_m3_lag_wdi_modeling_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_modeling_started"] is False
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_next_action_id"] == (
        "stage128-m3-lag-wdi-exploratory-incremental-evaluation")
    assert handoff["final_test_locked"] is True
    assert handoff["stage128_m3_lag_wdi_final_test_rows_read"] == 0


def test_the_handoff_preserves_step_d_after_the_lock(handoff):
    assert handoff["stage128_m3_lag_wdi_data_gate_result"] == (
        "PASS_M3_LAG_WDI_DATA_GATE")
    assert handoff["stage128_m3_lag_wdi_block_admitted"] is True
    assert handoff["stage128_m3_lag_wdi_gate_cpi_valid_rows"] == 539
    assert handoff["stage128_m3_lag_wdi_gate_fx_valid_rows"] == 539
    assert handoff["stage128_m3_lag_wdi_gate_block_common_sample_rows"] == 539
    assert handoff["stage128_m3_lag_wdi_gate_fold1_positive_evaluable"] == 18
    assert handoff["stage128_m3_lag_wdi_gate_fold2_positive_evaluable"] == 10
    assert handoff["stage128_m3_lag_wdi_gate_rows_excluded"] == 0
    assert handoff["stage128_m3_lag_wdi_post_retrieval_audit_result"] == (
        "PASS_WITH_MATERIAL_FINDINGS")


def test_the_lock_authorization_is_consumed_in_the_handoff(handoff):
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorization_consumed"
    ] is True
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorized"] is False
    assert handoff[
        "stage128_m3_lag_wdi_calendar_mapping_lock_was_authorized"] is True


# --------------------------------------------------------------------------- #
# FAIL-CLOSED DRIFT TESTS on the generator recognizer
# --------------------------------------------------------------------------- #

_MUTATIONS = (
    {"calendar_mapping_locked": False},
    {"calendar_mapping_rule": "jalali_fiscal_year_t_plus_622"},
    {"calendar_mapping_locked_offset": 622},
    {"rejected_offset": 621},
    {"rejected_offset_timing_violation_rows": 0},
    {"locked_offset_timing_violation_rows": 3},
    {"selection_used_model_performance": True},
    {"selection_used_feature_values": True},
    {"point_in_time_availability_established_by_this_lock": True},
    {"changing_the_locked_mapping_requires_new_explicit_human_decision":
        False},
    {"amends_but_does_not_edit": False},
    {"historical_unlocked_state_erased": True},
    {"next_action_authorized": True},
    {"calendar_mapping_lock_required_before_modeling": True},
    {"unresolved_limitations": []},
)


@pytest.mark.parametrize("mutation", _MUTATIONS)
def test_the_recognizer_refuses_a_mutated_decision(tmp_path, mutation):
    root = _clone_repo_subset(tmp_path)
    payload = copy.deepcopy(_read_json(_DECISION_REL))
    payload.update(mutation)
    _write(root, _DECISION_REL, payload)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(str(root))


def test_the_recognizer_refuses_a_lock_whose_evidence_contradicts_it(tmp_path):
    """A lock justified by evidence that no longer supports it must fail."""
    root = _clone_repo_subset(tmp_path)
    ev = copy.deepcopy(_read_json(_EVIDENCE_REL))
    ev["per_offset"]["622"]["timing_violation_rows"] = 0
    ev["per_offset"]["622"]["satisfies_necessary_timing_condition"] = True
    _write(root, _EVIDENCE_REL, ev)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(str(root))


def test_the_recognizer_refuses_a_locked_offset_that_violates_timing(tmp_path):
    root = _clone_repo_subset(tmp_path)
    ev = copy.deepcopy(_read_json(_EVIDENCE_REL))
    ev["per_offset"]["621"]["timing_violation_rows"] = 4
    ev["per_offset"]["621"]["satisfies_necessary_timing_condition"] = False
    _write(root, _EVIDENCE_REL, ev)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(str(root))


@pytest.mark.parametrize("field", [
    "calendar_mapping_lock_propagates_to_step_e",
    "calendar_mapping_lock_is_modeling_authorization",
    "calendar_mapping_lock_authorizes_feature_value_table",
    "calendar_mapping_lock_is_final_test_unlock",
    "m3_lag_wdi_modeling_authorized",
    "m3_lag_wdi_modeling_started",
    "m3_lag_wdi_data_gate_rerun_by_this_action",
    "m3_lag_wdi_contract_edited_by_this_action",
])
def test_the_recognizer_refuses_a_leaking_boundary(tmp_path, field):
    root = _clone_repo_subset(tmp_path)
    payload = copy.deepcopy(_read_json(_BOUNDARY_REL))
    payload[field] = True
    _write(root, _BOUNDARY_REL, payload)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(str(root))


@pytest.mark.parametrize("counter", [
    "model_fits", "feature_value_tables_materialized",
    "feature_values_computed", "final_test_rows_read",
    "world_bank_api_requests", "data_gate_executions",
])
def test_the_recognizer_refuses_a_moved_counter(tmp_path, counter):
    root = _clone_repo_subset(tmp_path)
    payload = copy.deepcopy(_read_json(_AUDIT_REL))
    payload[counter] = 1
    _write(root, _AUDIT_REL, payload)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(str(root))


def test_the_recognizer_returns_empty_before_the_package_exists(tmp_path):
    assert gen.derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(
        str(tmp_path)) == {}


# --------------------------------------------------------------------------- #

_CLONE_RELS = (_DECISION_REL, _EVIDENCE_REL, _AUDIT_REL, _BOUNDARY_REL,
               _QC_REL)


def _clone_repo_subset(tmp_path):
    root = tmp_path / "repo"
    for rel in _CLONE_RELS:
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        _write(root, rel, _read_json(rel))
    return root


def _write(root, rel, payload) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
