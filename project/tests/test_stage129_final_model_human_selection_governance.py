"""Stage129 — the human governance decision naming the final model.

This is the first action in the programme that sets `paper_winner_selected`.
The two things most likely to go wrong are therefore pinned hardest:

  * a GOVERNANCE choice must never be recorded as an INFERENCE -- not a tested
    superiority, not a Holm result, not a statistical proof;
  * SELECTED must never be read as FITTED -- the configuration was pre-locked,
    no full-development refit ran, no trained artifact exists and the Final
    Test is still locked and unread.

Also pinned: M2 keeps its intermediate-confirmatory role and is not reported as
having failed statistically; random forest and XGBoost are not removed,
rejected or declared inferior; and the Holm family survives with all three
members, all p-values null and nothing accepted or rejected.
"""
import copy
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

_PKG_REL = "project/stage129/final_model_human_selection_governance"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_DEC = f"{_PKG_REL}/stage129_final_model_human_selection_decision.json"
_HOLM = f"{_PKG_REL}/stage129_final_holm_family_status.json"
_BND = f"{_PKG_REL}/stage129_final_model_selection_governance_boundary.json"
_AUDIT_REL = ("project/stage129/final_development_model_eligibility_audit/"
              "stage129_final_model_eligibility_audit_verdict.json")
_FREEZE_REL = "project/stage126/stage126_m1_retained_design_freeze.json"
_SAP_REL = "project/stage125/part4_metrics_uncertainty_contract_stage125.json"

ACTION_ID = "stage129-final-model-human-selection-governance"
BLOCK = "M1"
ALGORITHM = "regularized_logistic_regression"
CONFIGURATION = "logistic__C_0.1"
BASIS = "HUMAN_DECISION_BASED_ON_PRELOCKED_DEVELOPMENT_EVIDENCE"
HOLM_STATUS = "HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE"
NOT_SELECTED_STATUS = "NOT_SELECTED_BY_HUMAN_DECISION_ONLY"
HOLM_FAMILY = ["M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
HOLM_MEMBER_STATUS = {
    "M2_minus_M1": "EVALUATED_NO_SUPERIORITY_ESTABLISHED",
    "M3_CBI_minus_M2": "NOT_EXECUTED_M3_CBI_DISCONTINUED",
    "M4_minus_M3_CBI": "NOT_EXECUTED_M4_DISCONTINUED",
}
NEXT_ACTION = "human_authorization_required_for_full_development_refit_and_final_test"

#: The exact live markers the governance decision is required to publish.
REQUIRED_STATE = {
    "paper_winner_selected": True,
    "final_development_block_selected": True,
    "final_development_block": "M1",
    "final_algorithm_selected": True,
    "final_algorithm": "regularized_logistic_regression",
    "final_configuration": "logistic__C_0.1",
    "selection_is_human_governance_decision": True,
    "inferential_superiority_claimed": False,
    # NB: `full_development_refit_performed` and
    # `trained_final_model_artifact_created` were False when this decision was
    # recorded and this decision set neither. They are LIVE flags now owned by
    # the separately authorized Stage129 refit execution, so they are asserted
    # action-scoped below rather than pinned globally here.
    "stage130_started": False,
    "final_test_access_authorized": False,
    "final_test_locked": True,
    "final_test_second_pass_authorized": False,
    # MOVED from a live global to the pre-pass historical snapshot:
    # `final_test_rows_read` is an EVENT key that the separately authorized
    # Stage129 Final Test pass set to 346, long after this selection. The
    # firewall this selection ran under is pinned here permanently, and the
    # live PERMISSION keys above are still pinned exactly.
    "final_test_prior_to_authorized_pass_rows_read": 0,
}


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def decision():
    return _load(_DEC)


@pytest.fixture(scope="module")
def holm():
    return _load(_HOLM)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BND)


@pytest.fixture(scope="module")
def state():
    return _load("project/docs/ai/handoff_state.json")


@pytest.fixture(scope="module")
def roadmap_front_matter():
    text = _text("project/docs/ai/ROADMAP.md")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert m, "ROADMAP.md must carry YAML front matter"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


# ------------------------------------------------ the fourteen live markers
def test_every_required_live_marker_is_exact(state):
    for key, want in REQUIRED_STATE.items():
        assert key in state, key
        assert state[key] == want, (key, state[key], want)
        # bool identity matters: 1 == True would otherwise slip through
        if isinstance(want, bool):
            assert state[key] is want, key


def test_the_selection_is_recorded_in_all_three_artifacts(decision, boundary,
                                                          state):
    assert decision["decision_id"] == ACTION_ID
    assert decision["decision_type"] == "human_governance_selection_decision"
    assert decision["authorized_by_human"] is True
    for src in (decision, boundary):
        assert src["final_development_block"] == BLOCK
        assert src["final_algorithm"] == ALGORITHM
        assert src["final_configuration"] == CONFIGURATION
        assert src["final_development_block_selected"] is True
        assert src["final_algorithm_selected"] is True
        assert src["paper_winner_selected"] is True
        assert src["selection_is_human_governance_decision"] is True
    assert state["stage129_final_selection_recorded"] is True
    assert state["stage129_final_selection_action_id"] == ACTION_ID
    assert state["stage129_final_selection_block"] == BLOCK
    assert state["stage129_final_selection_algorithm"] == ALGORITHM
    assert state["stage129_final_selection_configuration"] == CONFIGURATION


# ------------------------------- the basis is human decision, not inference
def test_the_selection_basis_is_the_human_decision_basis(decision, boundary,
                                                         state,
                                                         roadmap_front_matter):
    assert decision["selection_basis"] == BASIS
    assert boundary["selection_basis"] == BASIS
    assert state["selection_basis"] == BASIS
    assert state["stage129_final_selection_basis"] == BASIS
    assert roadmap_front_matter["selection_basis"] == BASIS


def test_the_selection_is_never_presented_as_an_inference(decision, boundary,
                                                          holm, state,
                                                          roadmap_front_matter):
    for field in ("inferential_superiority_claimed", "is_tested_superiority",
                  "is_holm_result", "is_statistical_proof"):
        assert decision[field] is False, field
    assert boundary["inferential_superiority_claimed"] is False
    assert boundary["selection_used_holm_result"] is False
    assert holm["final_selection_used_holm_result"] is False
    assert state["inferential_superiority_claimed"] is False
    assert state["stage129_final_selection_is_tested_superiority"] is False
    assert state["stage129_final_selection_is_holm_result"] is False
    assert state["stage129_final_selection_is_statistical_proof"] is False
    assert state["stage129_final_selection_used_holm_result"] is False
    assert roadmap_front_matter["inferential_superiority_claimed"] == "false"
    assert decision["why_this_is_not_an_inferential_claim"].strip()
    # the mechanism that could have produced an inference was never run
    assert holm["confirmatory_family_1_executed"] is False


# ------------------------------------ selected != fitted (the key firewall)
def test_the_configuration_was_prelocked_and_not_chosen_here(decision, boundary,
                                                             state):
    for src in (decision, boundary):
        assert src["final_configuration_was_prelocked_before_this_decision"] is True
        assert src["final_configuration_selected_by_this_decision"] is False
    assert state["final_configuration_was_prelocked_before_this_decision"] is True
    assert state["final_configuration_selected_by_this_decision"] is False
    # and the named configuration really is the frozen one
    freeze = _load(_FREEZE_REL)
    entry = freeze["retained_model_families"][CONFIGURATION]
    assert entry["family"] == ALGORITHM
    assert entry["source_configuration_id"] == CONFIGURATION
    assert decision["final_configuration_source_artifact"].split("#")[0] == _FREEZE_REL


def test_nothing_was_fitted_and_no_artifact_was_produced(decision, boundary,
                                                         state,
                                                         roadmap_front_matter):
    for src in (decision, boundary):
        assert src["full_development_refit_performed"] is False
        assert src["trained_final_model_artifact_created"] is False
        assert src["stage130_started"] is False
    # ACTION-SCOPED: the selection fitted nothing; its own artifacts say so.
    assert decision["full_development_refit_performed"] is False
    assert decision["trained_final_model_artifact_created"] is False
    assert boundary["full_development_refit_performed"] is False
    assert state["stage130_started"] is False
    # MOVED from a live global proxy to an action-scoped historical fact. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this selection. The
    # selection's own decision and boundary artifacts (asserted above) carry
    # its zero; the snapshot pins the firewall state it ran under.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert roadmap_front_matter["full_development_refit_performed"] == "false"
    assert roadmap_front_matter["trained_final_model_artifact_created"] == "false"
    assert roadmap_front_matter["stage130_started"] == "false"
    assert boundary["counters"]["trained_model_artifacts_written"] == 0
    assert boundary["counters"]["model_fits"] == 0


def test_every_execution_counter_is_zero(boundary):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("model_fits", "predict_calls", "predict_proba_calls",
                "decision_function_calls", "tuning_runs", "calibration_executions",
                "threshold_searches", "bootstrap_executions", "shap_executions",
                "metrics_computed", "confidence_intervals_computed",
                "p_values_computed", "holm_executions",
                "row_level_scientific_data_reads", "trained_model_artifacts_written",
                "final_test_rows_read", "new_data_files_created"):
        assert counters[key] == 0, key


def test_final_test_stays_locked_with_zero_rows_read(decision, boundary, state):
    for src in (decision, boundary):
        assert src["final_test_locked"] is True
        assert src["final_test_access_authorized"] is False
        assert src["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_target_values_read"] == 0
    assert boundary["counters"]["final_test_predictor_values_read"] == 0
    assert state["final_test_locked"] is True
    # MOVED from a live global proxy to the pre-pass historical snapshot, as
    # above; `decision` and `boundary` above carry this action's own zero.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["final_test_access_authorized"] is False
    assert state["final_test_second_pass_authorized"] is False


# --------------------------------------------- M2 keeps its role, not blamed
def test_m2_remains_an_intermediate_confirmatory_block(decision, boundary,
                                                       state):
    for src in (decision, boundary):
        assert src["m2_role_preserved"] == "intermediate_confirmatory_block"
        assert src["m2_predictive_superiority_claim_supported"] is False
    assert decision["m2_reported_as_statistically_failed"] is False
    assert decision["m2_not_selected_is_not_a_statistical_failure"] is True
    assert boundary["m2_declared_statistically_failed"] is False
    assert boundary["m2_status_modified_by_this_action"] is False
    assert state["stage129_final_selection_m2_role_preserved"] == (
        "intermediate_confirmatory_block")
    assert state["stage129_final_selection_m2_declared_statistically_failed"] is False
    assert state["m2_predictive_superiority_claim_supported"] is False
    # the merged retention decision is untouched and still says the same
    dec = _load("project/stage128/m2_retained_block_human_decision/"
                "stage128_m2_retained_block_human_decision.json")
    assert dec["m2_role"] == "intermediate_confirmatory_block"
    assert dec["m2_block_retained"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_superiority_established"] is False


# ------------------------- RF and XGBoost are not selected, and nothing more
def test_the_non_selected_algorithms_are_not_rejected_or_declared_inferior(
        decision, boundary, state):
    entries = decision["non_selected_algorithms"]
    assert [e["algorithm"] for e in entries] == ["random_forest", "xgboost"]
    for entry in entries:
        assert entry["status"] == NOT_SELECTED_STATUS, entry["algorithm"]
        assert entry["declared_rejected"] is False, entry["algorithm"]
        assert entry["declared_removed"] is False, entry["algorithm"]
        assert entry["declared_statistically_inferior"] is False, entry["algorithm"]
    assert boundary["non_selected_algorithms_declared_rejected"] is False
    assert boundary["non_selected_algorithms_declared_statistically_inferior"] is False
    assert state["stage129_final_selection_non_selected_algorithms"] == [
        "random_forest", "xgboost"]
    assert state["stage129_final_selection_non_selected_status"] == NOT_SELECTED_STATUS
    assert state["stage129_final_selection_non_selected_declared_rejected"] is False
    assert state["stage129_final_selection_non_selected_declared_inferior"] is False
    # their frozen configurations survive untouched
    freeze = _load(_FREEZE_REL)
    for entry in entries:
        assert freeze["retained_model_families"][entry["configuration"]]["family"] == \
            entry["algorithm"]
    assert len(freeze["retained_model_families"]) == 3


# ------------------------------------- the Holm family: preserved, unexecuted
def test_the_holm_family_keeps_three_members_with_null_p_values(
        holm, boundary, state, roadmap_front_matter):
    assert holm["family_members_live"] == HOLM_FAMILY
    assert holm["family_member_count"] == 3
    assert holm["holm_reporting_status"] == HOLM_STATUS
    assert boundary["holm_reporting_status"] == HOLM_STATUS
    assert state["stage129_final_holm_reporting_status"] == HOLM_STATUS
    assert roadmap_front_matter["final_holm_reporting_status"] == HOLM_STATUS
    for name, want in HOLM_MEMBER_STATUS.items():
        entry = holm["members"][name]
        assert entry["status"] == want, name
        assert entry["p_value"] is None, name
        assert entry["null_hypothesis_accepted"] is False, name
        assert entry["null_hypothesis_rejected"] is False, name
        assert os.path.isfile(os.path.join(REPO_ROOT, entry["source"])), name
    assert state["stage129_final_holm_m2_minus_m1_status"] == (
        HOLM_MEMBER_STATUS["M2_minus_M1"])
    assert state["stage129_final_holm_m3_cbi_minus_m2_status"] == (
        HOLM_MEMBER_STATUS["M3_CBI_minus_M2"])
    assert state["stage129_final_holm_m4_minus_m3_cbi_status"] == (
        HOLM_MEMBER_STATUS["M4_minus_M3_CBI"])


def test_no_holm_adjustment_and_no_hypothesis_resolved(holm, boundary, state):
    for field in ("holm_adjustment_executed_by_this_action",
                  "family_shrunk_by_this_action", "family_redefined_by_this_action",
                  "family_removed_or_renamed_by_this_action",
                  "any_hypothesis_accepted", "any_hypothesis_rejected",
                  "holm_family_complete"):
        assert holm[field] is False, field
    assert holm["new_p_values_created_by_this_action"] == 0
    for field in ("holm_adjustment_executed", "holm_family_complete",
                  "holm_family_members_removed_or_renamed",
                  "holm_family_shrunk_post_hoc",
                  "any_hypothesis_accepted_or_rejected"):
        assert boundary[field] is False, field
    assert state["stage129_final_holm_family_complete"] is False
    assert state["stage129_final_holm_adjustment_executed"] is False
    assert state["stage129_final_holm_new_p_values"] == 0
    assert state["stage129_final_holm_any_hypothesis_resolved"] is False
    assert state["holm_family_complete"] is False
    assert state["holm_final_adjustment_deferred"] is True
    # the frozen SAP family is untouched
    assert holm["family_members_frozen_sap"] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
    sap = _load(_SAP_REL)
    assert sap["multiplicity"][holm["frozen_sap_family_key"]] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
    assert sap["multiplicity"]["correction"] == "Holm"


# ------------------------------------------- supersede, history and pointer
def test_the_supersede_targets_the_pending_decision_not_the_audit_findings(
        decision, state):
    marker = decision["superseded_marker"]
    assert marker["artifact"] == _AUDIT_REL
    assert marker["historical_artifact_preserved_byte_for_byte"] is True
    assert marker["supersede_scope"] == (
        "the_pending_human_decision_only_not_the_audit_findings")
    prev = marker["previous_values"]
    assert prev["block_verdict"] == "FINAL_BLOCK_REQUIRES_HUMAN_DECISION"
    assert prev["algorithm_verdict"] == "FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION"
    assert prev["next_action_id"] == "human_decision_required"
    # the audit artifact still carries its own historical verdicts
    audit = _load(_AUDIT_REL)
    assert audit["block_verdict"] == prev["block_verdict"]
    assert audit["algorithm_verdict"] == prev["algorithm_verdict"]
    assert audit["audit_determined_candidate"] is None
    assert state["stage129_final_selection_supersedes_artifact"] == _AUDIT_REL
    assert state["stage129_final_selection_audit_package_preserved"] is True
    # the audit's own action-scoped markers stay false -- IT selected nothing
    assert state["stage129_audit_paper_winner_selected"] is False
    assert state["stage129_audit_final_model_selected"] is False


def test_no_historical_artifact_or_pull_request_was_modified(boundary):
    for field in ("historical_scientific_artifacts_modified_by_this_action",
                  "prior_packages_modified_by_this_action",
                  "existing_pull_requests_modified_by_this_action",
                  "m1_results_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m3_cbi_disposition_modified_by_this_action",
                  "m4_disposition_modified_by_this_action",
                  "m3_lag_wdi_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "new_metric_computed", "new_p_value_created"):
        assert boundary[field] is False, field
    assert boundary["m3_lag_wdi_disposition"] == "SUPPLEMENTARY_EXPLORATORY_ONLY"


def test_the_pointer_authorizes_nothing(boundary, state, roadmap_front_matter):
    assert boundary["next_action_id"] == NEXT_ACTION
    assert boundary["next_action_authorized"] is False
    assert boundary["next_action_executes_refit"] is False
    assert boundary["next_action_executes_final_test"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert boundary["next_research_action_authorized"] is False
    assert state["stage129_final_selection_next_action_id"] == NEXT_ACTION
    assert state["stage129_final_selection_next_action_authorized"] is False
    assert state["next_research_action_authorized"] is False
    assert roadmap_front_matter["final_selection_next_action_authorized"] == "false"
    assert roadmap_front_matter["next_research_action_authorized"] == "false"


# ------------------------------------------- the generator fails closed
def _run_generator(root):
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_final_model_human_selection_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A minimal tree with this package and every artifact it is checked against."""
    (tmp_path / _PKG_REL).mkdir(parents=True, exist_ok=True)
    for name in os.listdir(_PKG):
        with open(os.path.join(_PKG, name), "rb") as fh:
            (tmp_path / _PKG_REL / name).write_bytes(fh.read())
    for rel in (_AUDIT_REL, _FREEZE_REL, _SAP_REL):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            dst.write_bytes(fh.read())
    return tmp_path


def _write(root, rel, blob):
    with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
        json.dump(blob, fh, ensure_ascii=False, indent=2, sort_keys=True)


def test_the_sandbox_baseline_derives_cleanly(sandbox):
    """The tamper tests below are only meaningful if the untampered copy passes."""
    markers = _run_generator(str(sandbox))
    assert markers["final_development_block"] == BLOCK
    assert markers["final_algorithm"] == ALGORITHM
    assert markers["paper_winner_selected"] is True


@pytest.mark.parametrize("rel,key,value,needle", [
    # dressing the governance choice up as an inference
    (_DEC, "inferential_superiority_claimed", True, "inferential_superiority_claimed"),
    (_DEC, "is_tested_superiority", True, "is_tested_superiority"),
    (_DEC, "is_holm_result", True, "is_holm_result"),
    (_DEC, "is_statistical_proof", True, "is_statistical_proof"),
    (_BND, "inferential_superiority_claimed", True, "inferential superiority"),
    (_BND, "selection_used_holm_result", True, "Holm result"),
    (_HOLM, "final_selection_used_holm_result", True, "Holm result"),
    # forging a different basis
    (_DEC, "selection_basis", "TESTED_SUPERIORITY", "basis must be"),
    (_DEC, "selection_basis", "HOLM_ADJUSTED_RESULT", "basis must be"),
    (_BND, "selection_basis", "BEST_POINT_ESTIMATE", "basis must be"),
    # naming a different block, algorithm or configuration
    (_DEC, "final_development_block", "M2", "block must be"),
    (_DEC, "final_algorithm", "xgboost", "algorithm must be"),
    (_DEC, "final_configuration", "logistic__C_1.0", "configuration must be"),
    (_BND, "final_development_block", "M2", "block must be"),
    # claiming this decision chose the configuration
    (_DEC, "final_configuration_selected_by_this_decision", True, "already locked"),
    (_DEC, "final_configuration_was_prelocked_before_this_decision", False,
     "pre-locked"),
    # turning SELECTED into FITTED
    (_DEC, "full_development_refit_performed", True, "full_development_refit"),
    (_DEC, "trained_final_model_artifact_created", True, "trained_final_model"),
    (_BND, "full_development_refit_performed", True, "full_development_refit"),
    (_BND, "trained_final_model_artifact_created", True, "trained_final_model"),
    (_BND, "stage130_started", True, "stage130_started"),
    # unlocking or reading the Final Test
    (_DEC, "final_test_locked", False, "Final Test locked"),
    (_DEC, "final_test_rows_read", 1, "final_test_rows_read"),
    (_BND, "final_test_locked", False, "Final Test locked"),
    (_BND, "final_test_rows_read", 5, "final_test_rows_read"),
    (_BND, "final_test_access_authorized", True, "final_test_access_authorized"),
    # blaming M2 or demoting its role
    (_DEC, "m2_reported_as_statistically_failed", True, "statistically failed"),
    (_DEC, "m2_not_selected_is_not_a_statistical_failure", False, "statistical failure"),
    (_DEC, "m2_role_preserved", "rejected_block", "M2 role"),
    (_BND, "m2_declared_statistically_failed", True, "M2 failed"),
    (_BND, "m2_predictive_superiority_claim_supported", True, "superiority"),
    (_BND, "m2_role_preserved", "discarded", "M2 role"),
    # rejecting or defeating the non-selected algorithms
    (_BND, "non_selected_algorithms_declared_rejected", True, "declared_rejected"),
    (_BND, "non_selected_algorithms_declared_statistically_inferior", True,
     "declared_statistically_inferior"),
    # touching the Holm family
    (_HOLM, "holm_reporting_status", "HOLM_COMPLETE", "Holm status"),
    (_BND, "holm_reporting_status", "HOLM_COMPLETE", "Holm status"),
    (_HOLM, "family_members_live", ["M2_minus_M1", "M3_CBI_minus_M2"],
     "confirmatory Holm family"),
    (_HOLM, "family_member_count", 2, "3 members"),
    (_HOLM, "holm_adjustment_executed_by_this_action", True, "holm_adjustment_executed"),
    (_HOLM, "family_shrunk_by_this_action", True, "family_shrunk"),
    (_HOLM, "family_redefined_by_this_action", True, "family_redefined"),
    (_HOLM, "any_hypothesis_accepted", True, "any_hypothesis_accepted"),
    (_HOLM, "any_hypothesis_rejected", True, "any_hypothesis_rejected"),
    (_HOLM, "holm_family_complete", True, "holm_family_complete"),
    (_HOLM, "new_p_values_created_by_this_action", 1, "p-value"),
    (_HOLM, "confirmatory_family_1_executed", True, "confirmatory_family_1_executed"),
    (_BND, "holm_family_complete", True, "holm_family_complete"),
    (_BND, "any_hypothesis_accepted_or_rejected", True,
     "any_hypothesis_accepted_or_rejected"),
    # editing history, other PRs, or opening the next step
    (_BND, "historical_scientific_artifacts_modified_by_this_action", True,
     "historical_scientific_artifacts"),
    (_BND, "existing_pull_requests_modified_by_this_action", True, "pull_requests"),
    (_BND, "m3_lag_wdi_promoted_to_confirmatory_model", True, "promoted"),
    (_BND, "next_action_authorized", True, "next_action_authorized"),
    (_BND, "next_action_executes_refit", True, "next_action_executes_refit"),
    (_BND, "next_action_executes_final_test", True, "next_action_executes_final_test"),
    (_BND, "next_action_id", "stage130-final-model-refit", "pointer must be"),
    (_BND, "new_p_value_created", True, "new_p_value_created"),
])
def test_the_generator_fails_closed_on_tampering(sandbox, rel, key, value, needle):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob[key] = value
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


@pytest.mark.parametrize("member", HOLM_FAMILY)
def test_a_fabricated_p_value_on_any_member_fails_closed(sandbox, member):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _HOLM).read_text(encoding="utf-8"))
    blob["members"][member]["p_value"] = 0.031
    _write(str(sandbox), _HOLM, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "p_value must be null" in str(exc.value)


@pytest.mark.parametrize("member", HOLM_FAMILY)
def test_resolving_a_hypothesis_on_any_member_fails_closed(sandbox, member):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _HOLM).read_text(encoding="utf-8"))
    blob["members"][member]["null_hypothesis_rejected"] = True
    _write(str(sandbox), _HOLM, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "null_hypothesis_rejected" in str(exc.value)


@pytest.mark.parametrize("member", HOLM_FAMILY)
def test_changing_any_member_status_fails_closed(sandbox, member):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _HOLM).read_text(encoding="utf-8"))
    blob["members"][member]["status"] = "EXECUTED_SUPERIORITY_ESTABLISHED"
    _write(str(sandbox), _HOLM, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "status must be" in str(exc.value)


@pytest.mark.parametrize("index,algorithm", [(0, "random_forest"), (1, "xgboost")])
def test_declaring_a_non_selected_algorithm_defeated_fails_closed(
        sandbox, index, algorithm):
    import update_ai_handoff as gen
    for field in ("declared_rejected", "declared_removed",
                  "declared_statistically_inferior"):
        # start from the PRISTINE artifact each time, so one tampered field is
        # tested in isolation rather than stacking on the previous iteration
        blob = _load(_DEC)
        blob["non_selected_algorithms"][index][field] = True
        _write(str(sandbox), _DEC, blob)
        with pytest.raises(gen.HandoffError) as exc:
            _run_generator(str(sandbox))
        assert algorithm in str(exc.value)
        assert field in str(exc.value)


def test_dropping_a_non_selected_algorithm_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _DEC).read_text(encoding="utf-8"))
    blob["non_selected_algorithms"] = blob["non_selected_algorithms"][:1]
    _write(str(sandbox), _DEC, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "not selected" in str(exc.value).lower()


def test_a_nonzero_counter_fails_closed(sandbox):
    import update_ai_handoff as gen
    for key in ("model_fits", "trained_model_artifacts_written", "p_values_computed",
                "row_level_scientific_data_reads", "final_test_rows_read"):
        # pristine each time: one non-zero counter in isolation
        blob = _load(_BND)
        blob["counters"][key] = 1
        _write(str(sandbox), _BND, blob)
        with pytest.raises(gen.HandoffError) as exc:
            _run_generator(str(sandbox))
        assert key in str(exc.value)


def test_a_configuration_that_is_not_the_frozen_one_fails_closed(sandbox):
    """The named configuration must really be the frozen logistic configuration
    in the retained design freeze -- not merely a matching string."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _FREEZE_REL).read_text(encoding="utf-8"))
    blob["retained_model_families"][CONFIGURATION]["family"] = "xgboost"
    _write(str(sandbox), _FREEZE_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "frozen" in str(exc.value).lower()


def test_an_unanchored_supersede_fails_closed(sandbox):
    """If the audit package is quietly rewritten so its verdicts no longer read
    'requires human decision', the supersede has no anchor and the build must
    fail rather than inherit a rewritten history."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _AUDIT_REL).read_text(encoding="utf-8"))
    blob["block_verdict"] = "UNIQUE_FINAL_BLOCK_DETERMINED_BY_FROZEN_RULE"
    _write(str(sandbox), _AUDIT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "byte-for-byte" in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _DEC)
    assert _run_generator(str(sandbox)) == {}


# ------------------------------- validator, idempotency and rendered docs
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage129_final_model_human_selection_markers(REPO_ROOT)
    second = gen.derive_stage129_final_model_human_selection_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["paper_winner_selected"] is True


def test_current_state_renders_the_selection_without_an_inferential_claim():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert "FINAL MODEL SELECTED by human governance decision" in text
    assert BASIS in text
    assert ALGORITHM in text
    assert CONFIGURATION in text
    assert HOLM_STATUS in text
    assert "NOT an inferential result" in text


def test_the_readme_carries_both_english_and_persian_manuscript_text():
    readme = _text(f"{_PKG_REL}/"
                   "README_STAGE129_FINAL_MODEL_HUMAN_SELECTION_GOVERNANCE.md")
    for phrase in ("human decision on pre-locked development evidence",
                   "not an inferential superiority claim",
                   "intermediate confirmatory block",
                   "no trained final-model artifact was created",
                   "the Final Test remains locked and unread"):
        assert phrase in readme, phrase
    for phrase in ("تصمیم انسانی بر", "شواهد توسعه‌ای از پیش قفل‌شده",
                   "بلوک تأییدی میانی", "قفل و\nخوانده‌نشده"):
        assert phrase in readme, phrase


def test_roadmap_records_the_selection(roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["final_selection_action_id"] == ACTION_ID
    assert fm["paper_winner_selected"] == "true"
    assert fm["final_development_block"] == BLOCK
    assert fm["final_algorithm"] == ALGORITHM
    assert fm["final_configuration"] == CONFIGURATION
    assert fm["final_configuration_selected_by_this_decision"] == "false"
    assert fm["selection_is_human_governance_decision"] == "true"
    # final_model_selected stays false: no trained final model exists
    assert fm["final_model_selected"] == "false"
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert BASIS in body


# --------------------------------------------------------- package hygiene
def test_no_model_or_data_artifact_was_committed():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_final_model_human_selection_governance.json")
    assert manifest["trained_model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["new_metric_files_committed"] == 0
    assert manifest["trained_final_model_artifact_created"] is False
    assert manifest["full_development_refit_performed"] is False
    assert manifest["inferential_superiority_claimed"] is False


def test_package_hash_manifest_matches_every_file():
    import hashlib
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_final_model_human_selection_governance.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_the_audit_package_is_byte_for_byte_intact():
    """This decision supersedes the audit's pointer. It may not edit it."""
    import hashlib
    manifest = _load("project/stage129/final_development_model_eligibility_audit/"
                     "metadata_and_hashes_stage129_final_development_model_eligibility_audit.json")
    base = os.path.join(REPO_ROOT,
                        "project/stage129/final_development_model_eligibility_audit")
    for name, info in manifest["package_files"].items():
        with open(os.path.join(base, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
