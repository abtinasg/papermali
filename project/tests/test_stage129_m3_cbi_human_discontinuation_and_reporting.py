"""Stage129 — human discontinuation of M3-CBI, and how it is reported.

M3-CBI is NOT M4. The M4 block never had a Gate run; M3-CBI's Gate WAS
executed and terminated at ``UNRESOLVED_M3_DATA_GATE``. So these tests pin the
decision against BOTH falsifications:

  * the Gate must stay recorded as EXECUTED -- calling it unrun would erase a
    completed research action;
  * its status must stay UNRESOLVED -- converting it to PASS or FAIL would
    assert an evaluation outcome the Gate never produced;
  * none of the 8 recorded unresolved reasons may be declared resolved, and no
    new coverage or threshold may appear.

They also pin that the prespecified comparison survives unexecuted with a null
p-value and no resolved hypothesis, that M3-LAG-WDI is not promoted into the
confirmatory role M3-CBI vacated, that M1/M2/M4 are untouched, that the Final
Test stays locked at zero rows, and that the generator fails closed.
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

_PKG_REL = "project/stage129/m3_cbi_human_discontinuation_and_reporting"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_GATE_PKG_REL = "project/stage128/m3_macro_data_gate"
_GATE_REL = f"{_GATE_PKG_REL}/stage128_m3_macro_data_gate_decision.json"
_SAP_REL = "project/stage125/part4_metrics_uncertainty_contract_stage125.json"

ACTION_ID = "stage129-m3-cbi-human-discontinuation-and-reporting"
DISPOSITION = (
    "M3_CBI_DISCONTINUED_BY_HUMAN_DECISION_UNRESOLVED_DATA_GATE_AND_UNPROVEN_POINT_IN_TIME")
GATE_TERMINAL = "UNRESOLVED_M3_DATA_GATE"
GATE_FORBIDDEN = ("PASS_FOR_M3_INCREMENTAL_EVALUATION", "FAIL_M3_DATA_GATE")
UNRESOLVED_REASON_COUNT = 8
COMPARISON_ID = "M3_CBI_minus_M2"
COMPARISON_STATUS = "NOT_EXECUTED_M3_CBI_DISCONTINUED"
FROZEN_SAP_ID = "M3_minus_M2"
HOLM_FAMILY = ["M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
FROZEN_SAP_FAMILY = ["M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
LAG_WDI_DISPOSITION = "SUPPLEMENTARY_EXPLORATORY_ONLY"

APPROVED_EN = (
    "M3-CBI was prespecified, but its executed Data Gate remained unresolved "
    "because point-in-time availability could not be established. The block was "
    "therefore not admitted to modeling. Consequently, the M3-CBI−M2 comparison "
    "was not executed, no p-value was computed, and no inferential conclusion is "
    "drawn for M3-CBI. The M3-LAG-WDI analysis is reported separately as "
    "supplementary exploratory evidence and is neither a substitute nor a proxy "
    "for confirmatory M3-CBI."
)


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def decision():
    return _load(f"{_PKG_REL}/stage129_m3_cbi_human_discontinuation_decision.json")


@pytest.fixture(scope="module")
def comparison():
    return _load(f"{_PKG_REL}/stage129_m3_cbi_confirmatory_comparison_record.json")


@pytest.fixture(scope="module")
def boundary():
    return _load(f"{_PKG_REL}/stage129_m3_cbi_governance_boundary.json")


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


# ------------------------------------ 1. the disposition is exact and resolved
def test_the_disposition_is_exact_and_resolved(decision, boundary, state,
                                               roadmap_front_matter):
    assert decision["decision_id"] == ACTION_ID
    assert decision["decision_type"] == "human_scientific_decision"
    assert decision["authorized_by_human"] is True
    assert decision["human_decision_verbatim"].strip()
    assert decision["m3_cbi_disposition"] == DISPOSITION
    assert boundary["m3_cbi_disposition"] == DISPOSITION
    assert state["m3_cbi_disposition"] == DISPOSITION
    assert state["stage129_m3_cbi_disposition"] == DISPOSITION
    assert roadmap_front_matter["m3_cbi_disposition"] == DISPOSITION
    assert state["stage129_m3_cbi_discontinuation_recorded"] is True
    assert state["stage129_m3_cbi_discontinuation_action_id"] == ACTION_ID
    assert "UNRESOLVED" not in DISPOSITION.replace("UNRESOLVED_DATA_GATE", "")


# --------------------------- 2/3. the Gate was executed and stays UNRESOLVED
def test_the_m3_data_gate_stays_recorded_as_executed(decision, boundary, state,
                                                     roadmap_front_matter):
    """Unlike M4, this Gate ran. Recording it as unrun would erase a completed
    research action."""
    assert decision["m3_macro_data_gate_executed"] is True
    assert decision["m3_macro_data_gate_recorded_as_not_executed"] is False
    assert boundary["m3_macro_data_gate_executed"] is True
    assert state["m3_macro_data_gate_executed"] is True
    assert state["stage129_m3_macro_data_gate_executed"] is True
    assert state["stage129_m3_macro_data_gate_recorded_as_not_executed"] is False
    assert roadmap_front_matter["m3_macro_data_gate_executed"] == "true"
    # the Gate artifact itself still says so
    gate = _load(_GATE_REL)
    assert gate["m3_macro_data_gate_executed"] is True
    assert gate["m3_macro_data_gate_authorization_consumed"] is True
    assert gate["action_id"] == "stage128-m3-macro-data-gate"


def test_the_gate_status_is_never_converted_to_pass_or_fail(
        decision, boundary, state, roadmap_front_matter):
    assert decision["m3_macro_data_gate_terminal_status"] == GATE_TERMINAL
    assert boundary["m3_macro_data_gate_terminal_status"] == GATE_TERMINAL
    assert state["m3_macro_data_gate_terminal_status"] == GATE_TERMINAL
    assert state["stage129_m3_macro_data_gate_terminal_status"] == GATE_TERMINAL
    assert roadmap_front_matter["m3_macro_data_gate_terminal_status"] == GATE_TERMINAL
    # the live Gate marker is untouched by this decision
    assert state["m3_macro_data_gate_status"] == GATE_TERMINAL
    assert _load(_GATE_REL)["gate_status"] == GATE_TERMINAL
    # and no forbidden verdict is published anywhere in this package's JSON
    for name in os.listdir(_PKG):
        if not name.endswith(".json"):
            continue
        blob = _load(f"{_PKG_REL}/{name}")
        found = []

        def walk(node):
            if isinstance(node, dict):
                for key, val in node.items():
                    if key == "gate_status_vocabulary_deliberately_not_reassigned":
                        continue           # the explicit not-used declaration
                    walk(val)
            elif isinstance(node, list):
                for val in node:
                    walk(val)
            elif isinstance(node, str) and node in GATE_FORBIDDEN:
                found.append(node)

        walk(blob)
        assert found == [], f"{name} publishes a Gate verdict {found}"


def test_it_is_not_recorded_as_a_formal_gate_failure(decision, boundary, state,
                                                     roadmap_front_matter):
    assert decision["m3_macro_data_gate_formal_failure"] is False
    assert decision["m3_macro_data_gate_status_reassigned_by_this_decision"] is False
    assert boundary["m3_macro_data_gate_formal_failure"] is False
    assert boundary["m3_macro_data_gate_status_reassigned_by_this_action"] is False
    assert boundary["m3_macro_data_gate_reexecuted_by_this_action"] is False
    assert boundary["m3_macro_data_gate_artifacts_modified_by_this_action"] is False
    assert state["stage129_m3_macro_data_gate_formal_failure"] is False
    assert state["stage129_m3_macro_data_gate_status_reassigned"] is False
    assert roadmap_front_matter["m3_macro_data_gate_formal_failure"] == "false"
    assert decision["why_not_recorded_as_fail_m3_data_gate"].strip()
    assert decision["why_not_recorded_as_gate_not_executed"].strip()


# ------------------------ 4. the 8 unresolved reasons stand, none fabricated
def test_the_eight_unresolved_reasons_survive_without_fabricated_resolution(
        decision, boundary, state, roadmap_front_matter):
    gate = _load(_GATE_REL)
    assert len(gate["unresolved_or_blocker_reasons"]) == UNRESOLVED_REASON_COUNT
    assert state["m3_macro_data_gate_unresolved_reason_count"] == UNRESOLVED_REASON_COUNT
    assert decision["m3_macro_data_gate_unresolved_reason_count"] == UNRESOLVED_REASON_COUNT
    assert boundary["m3_macro_data_gate_unresolved_reason_count"] == UNRESOLVED_REASON_COUNT
    assert state["stage129_m3_macro_data_gate_unresolved_reason_count"] == (
        UNRESOLVED_REASON_COUNT)
    assert roadmap_front_matter["m3_macro_data_gate_unresolved_reason_count"] == (
        str(UNRESOLVED_REASON_COUNT))
    # none of them is declared resolved
    assert decision["m3_macro_data_gate_unresolved_reasons_resolved_by_this_decision"] == 0
    assert boundary["m3_macro_data_gate_unresolved_reasons_resolved_by_this_action"] == 0
    assert state["stage129_m3_macro_data_gate_unresolved_reasons_resolved"] == 0
    assert roadmap_front_matter["m3_macro_data_gate_unresolved_reasons_resolved"] == "0"


def test_no_new_coverage_threshold_or_point_in_time_claim_is_made(
        decision, boundary, state, roadmap_front_matter):
    assert decision["new_coverage_or_threshold_computed"] is False
    assert decision["point_in_time_availability_established"] is False
    assert boundary["point_in_time_availability_established"] is False
    assert state["stage129_m3_cbi_new_coverage_or_threshold_computed"] is False
    assert state["stage129_m3_cbi_point_in_time_availability_established"] is False
    assert roadmap_front_matter["m3_cbi_point_in_time_availability_established"] == "false"
    assert decision["point_in_time_evidence_status"] == (
        "NOT_ESTABLISHED_NO_INDEPENDENTLY_VERIFIABLE_OFFICIAL_EVIDENCE")
    assert boundary["counters"]["coverage_calculations"] == 0
    assert boundary["counters"]["threshold_computations"] == 0
    assert boundary["counters"]["data_gate_executions"] == 0
    # the Gate's own evidence assessment still says nothing was verifiable
    gate = _load(_GATE_REL)
    assert gate["official_evidence_assessment"][
        "any_authoritative_data_evidence_obtained"] is False
    assert gate["official_evidence_assessment"][
        "access_probe_classification_independently_verifiable"] is False


def test_the_reason_is_evidence_not_a_model_result(decision, state):
    assert decision["reason_class"] == (
        "unresolved_executed_data_gate_and_unproven_point_in_time_availability")
    assert decision["reason_is_poor_model_result"] is False
    assert decision["reason_is_outcome_inspection"] is False
    assert decision["outcome_or_final_test_observation_used_for_this_decision"] is False
    assert decision["decision_made_before_any_m3_cbi_modeling"] is True
    assert state["stage129_m3_cbi_reason_is_poor_model_result"] is False
    assert state["stage129_m3_cbi_reason_is_outcome_inspection"] is False


# ------------------- 5. the block is not admitted and nothing downstream runs
def test_m3_cbi_is_not_admitted_and_nothing_downstream_is_authorized(
        decision, boundary, state, roadmap_front_matter):
    for field in ("m3_cbi_block_admitted", "m3_cbi_modeling_will_run",
                  "m3_cbi_incremental_evaluation_will_run",
                  "m3_cbi_retrieval_continues", "m3_cbi_reopening_authorized",
                  "m3_cbi_feature_materialization_authorized"):
        assert decision[field] is False, field
        assert boundary[field] is False, field
        assert state[field] is False, field
        if field in roadmap_front_matter:
            assert roadmap_front_matter[field] == "false", field
    assert decision["m3_cbi_reopening_requires_new_human_authorization"] is True
    assert state["m3_cbi_reopening_requires_new_human_authorization"] is True
    # the pre-existing live markers still agree
    assert state["m3_block_admitted_for_incremental_evaluation"] is False
    assert state["m3_modeling_started"] is False
    assert state["m3_incremental_evaluation_authorized"] is False
    # the pointer names no execution
    assert boundary["next_action_id"] == "human_decision_required"
    assert boundary["next_action_executes_m3_cbi"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert state["stage129_m3_cbi_next_action_authorized"] is False
    assert state["stage129_m3_cbi_next_action_executes_m3_cbi"] is False
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_id"] == "human-dataset-release-candidate-digest-review"
    assert roadmap_front_matter["next_research_action_authorized"] == "false"


def test_nothing_was_retrieved_computed_or_contacted(boundary):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("network_requests", "wdi_api_requests", "wdi_archive_downloads",
                "world_bank_followup_sent", "world_bank_new_inquiry_submitted",
                "official_source_contacts", "data_gate_executions",
                "coverage_calculations", "threshold_computations",
                "feature_materializations", "model_fits", "predictions",
                "predictive_metrics", "bootstrap_executions", "holm_executions",
                "shap_executions", "final_test_rows_read", "new_data_files_created"):
        assert counters[key] == 0, key
    assert boundary["new_official_source_contact_made"] is False


# --------------------- 6/7. the prespecified comparison survives, unexecuted
def test_the_frozen_comparison_is_not_removed_renamed_or_substituted(
        comparison, state, roadmap_front_matter):
    assert comparison["comparison_id"] == COMPARISON_ID
    assert comparison["alias_created_by_this_action"] is False
    assert comparison["comparison_removed_from_sap_history"] is False
    assert comparison["comparison_removed_from_holm_family"] is False
    assert comparison["comparison_renamed_by_this_action"] is False
    assert comparison["comparison_substituted_by_this_action"] is False
    assert comparison["confirmatory_holm_family_shrunk_by_this_action"] is False
    assert comparison["sap_history_preserved"] is True
    assert state["stage129_m3_cbi_comparison_id"] == COMPARISON_ID
    assert state["stage129_m3_cbi_comparison_removed_from_sap_history"] is False
    assert state["stage129_m3_cbi_comparison_renamed_or_substituted"] is False
    assert roadmap_front_matter["m3_cbi_comparison_id"] == COMPARISON_ID
    # the live family keeps all three members, in order
    assert comparison["confirmatory_holm_family_live"] == HOLM_FAMILY
    assert comparison["confirmatory_holm_family_member_count"] == 3
    assert state["stage129_m3_cbi_confirmatory_holm_family"] == HOLM_FAMILY
    assert state["stage129_m4_confirmatory_holm_family"] == HOLM_FAMILY
    # and the FROZEN SAP contract is byte-identical in content, untouched
    assert comparison["frozen_sap_identifier_for_this_comparison"] == FROZEN_SAP_ID
    assert comparison["frozen_sap_family_members"] == FROZEN_SAP_FAMILY
    assert comparison["frozen_sap_family_members_modified_by_this_action"] is False
    sap = _load(_SAP_REL)
    assert sap["multiplicity"][comparison["frozen_sap_family_key"]] == FROZEN_SAP_FAMILY
    assert FROZEN_SAP_ID in sap["multiplicity"][comparison["frozen_sap_family_key"]]
    assert sap["multiplicity"]["correction"] == "Holm"
    assert state["stage129_m3_cbi_frozen_sap_identifier"] == FROZEN_SAP_ID
    assert roadmap_front_matter["m3_cbi_comparison_frozen_sap_identifier"] == FROZEN_SAP_ID


def test_the_comparison_is_unexecuted_with_a_null_p_and_no_resolved_hypothesis(
        comparison, state, roadmap_front_matter):
    assert comparison["comparison_status"] == COMPARISON_STATUS
    assert comparison["comparison_p_value"] is None
    assert comparison["comparison_null_hypothesis_accepted"] is False
    assert comparison["comparison_null_hypothesis_rejected"] is False
    assert comparison["comparison_inferential_conclusion"] == "none"
    assert comparison["comparison_performance_claim"] == "none"
    assert comparison["comparison_reason"].strip()
    assert state["stage129_m3_cbi_comparison_status"] == COMPARISON_STATUS
    assert state["stage129_m3_cbi_comparison_p_value"] is None
    assert state["stage129_m3_cbi_comparison_null_hypothesis_accepted"] is False
    assert state["stage129_m3_cbi_comparison_null_hypothesis_rejected"] is False
    assert state["stage129_m3_cbi_comparison_inferential_conclusion"] == "none"
    assert state["stage129_m3_cbi_comparison_performance_claim"] == "none"
    assert roadmap_front_matter["m3_cbi_comparison_status"] == COMPARISON_STATUS
    assert roadmap_front_matter["m3_cbi_comparison_p_value"] == "null"
    # no numeric p-value anywhere in the package
    for name in os.listdir(_PKG):
        if not name.endswith(".json"):
            continue
        blob = _load(f"{_PKG_REL}/{name}")

        def walk(node, path=""):
            if isinstance(node, dict):
                for key, val in node.items():
                    assert not (key.endswith("p_value") and val is not None), \
                        f"{name}:{path}.{key} publishes a p-value"
                    walk(val, f"{path}.{key}")
            elif isinstance(node, list):
                for i, val in enumerate(node):
                    walk(val, f"{path}[{i}]")

        walk(blob)


def test_holm_is_not_executed_and_not_declared_complete(comparison, boundary,
                                                        state):
    assert comparison["holm_executed_by_this_action"] is False
    assert comparison["holm_final_adjustment_declared_complete"] is False
    assert comparison["confirmatory_holm_family_modified_by_this_action"] is False
    assert boundary["holm_final_adjustment_declared_complete"] is False
    assert boundary["counters"]["holm_executions"] == 0
    assert state["stage129_m3_cbi_holm_final_adjustment_declared_complete"] is False
    assert state["stage129_m3_cbi_confirmatory_holm_family_modified"] is False
    # the live handoff still defers the final adjustment
    assert state["holm_final_adjustment_deferred"] is True
    assert state["holm_family_complete"] is False
    assert state["stage129_m4_confirmatory_holm_family_executed"] is False


# ---------------------------- 8/9. M3-LAG-WDI is not promoted into the gap
def test_m3_lag_wdi_stays_supplementary_and_is_not_a_substitute(
        boundary, state):
    assert boundary["m3_lag_wdi_disposition"] == LAG_WDI_DISPOSITION
    assert boundary["m3_lag_wdi_scientific_role"] == (
        "supplementary_exploratory_robustness_block")
    for field in ("m3_lag_wdi_promoted_to_confirmatory_model",
                  "m3_lag_wdi_is_confirmatory_m3",
                  "m3_lag_wdi_is_substitute_for_m3_cbi",
                  "m3_lag_wdi_is_proxy_for_m3_cbi",
                  "m3_lag_wdi_is_representative_of_m3_cbi",
                  "m3_lag_wdi_results_used_to_fill_the_m3_cbi_comparison",
                  "m3_lag_wdi_disposition_modified_by_this_action",
                  "m3_lag_wdi_artifacts_modified_by_this_action",
                  "m3_lag_wdi_step_e_artifacts_modified_by_this_action"):
        assert boundary[field] is False, field
    assert state["stage129_m3_cbi_m3_lag_wdi_disposition_preserved"] == LAG_WDI_DISPOSITION
    assert state["stage129_m3_cbi_m3_lag_wdi_promoted_to_confirmatory"] is False
    assert state["stage129_m3_cbi_m3_lag_wdi_is_substitute_or_proxy"] is False
    assert state["stage129_m3_cbi_m3_lag_wdi_used_to_fill_the_comparison"] is False
    # the pre-existing live markers are unchanged
    assert state["stage128_m3_lag_wdi_final_research_disposition"] == LAG_WDI_DISPOSITION
    assert state["stage128_m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert state["stage128_m3_lag_wdi_is_confirmatory_m3"] is False
    assert state["stage128_m3_lag_wdi_scientific_role"] == (
        "supplementary_exploratory_robustness_block")


def test_no_exploratory_value_enters_the_confirmatory_holm_family(
        comparison, boundary, state):
    assert comparison["exploratory_value_admitted_into_confirmatory_family"] is False
    assert boundary["m3_lag_wdi_p_value_entered_confirmatory_holm_family"] is False
    assert state["stage129_m3_cbi_exploratory_value_in_confirmatory_family"] is False
    assert state["stage128_m3_lag_wdi_in_confirmatory_holm_family"] is False
    assert state["stage128_m3_lag_wdi_confirmatory_holm_executed"] is False
    assert state["stage128_m3_lag_wdi_confirmatory_holm_family_changed"] is False
    assert state["stage128_m3_lag_wdi_confirmatory_superiority_claim_made"] is False
    # M3_CBI_minus_M2 is a member of the family and is NOT filled by exploratory
    assert COMPARISON_ID in state["stage129_m3_cbi_confirmatory_holm_family"]
    assert state["stage129_m3_cbi_comparison_p_value"] is None


def test_existing_pull_requests_are_read_only(boundary, state):
    assert boundary["existing_pull_requests_modified_by_this_action"] is False
    assert boundary["m3_lag_wdi_pull_request_modified_by_this_action"] is False
    assert boundary["m3_lag_wdi_pull_request_number_read_only"] == 79
    assert boundary["m3_lag_wdi_pull_request_state_read_only"] == "MERGED"
    assert state["stage129_m3_cbi_existing_pull_requests_modified"] is False


# ------------------------------------------- 10. M1, M2 and M4 are untouched
def test_m1_m2_and_m4_are_scientifically_unchanged(boundary, state):
    for field in ("m1_status_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m2_retained_status_modified_by_this_action",
                  "m4_discontinuation_status_modified_by_this_action",
                  "m4_reporting_decision_modified_by_this_action",
                  "m3i2_artifacts_modified_by_this_action",
                  "prior_packages_modified_by_this_action"):
        assert boundary[field] is False, field
    # the merged M4 decisions still read exactly as they did
    assert state["m4_block_disposition"] == (
        "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY")
    assert state["stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison"] == (
        "REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE")
    assert state["stage129_m4_comparison_status"] == "NOT_EXECUTED_M4_DISCONTINUED"
    assert state["stage129_m4_comparison_p_value"] is None
    assert state["m4_data_gate_executed"] is False
    assert state["m4_formal_gate_verdict"] is None
    assert state["m1_robustness_completed"] is True
    assert state["m1_robustness_execution_authorized"] is False


# --------------------------------- 11/12. firewall and no endgame step opens
def test_final_test_stays_locked_with_zero_rows_read(decision, boundary, state):
    assert decision["final_test_locked"] is True
    assert decision["final_test_access_authorized"] is False
    assert decision["final_test_rows_read"] == 0
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_target_values_read"] == 0
    assert boundary["counters"]["final_test_predictor_values_read"] == 0
    assert state["final_test_locked"] is True
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this action. This
    # action's own zero is asserted above / below; the snapshot pins the
    # firewall state it ran under.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_m3_cbi_final_test_locked"] is True
    assert state["stage129_m3_cbi_final_test_rows_read"] == 0


def test_no_final_model_winner_refit_or_stage130(boundary, state):
    """THIS action selected no winner and opened no endgame step.

    The action-scoped facts in its own boundary are the authoritative statement
    and stay False forever. The live global `paper_winner_selected` is NOT a
    proxy for them: a later, separate governance decision
    (`stage129-final-model-human-selection-governance`) legitimately set it, and
    asserting it False here would misreport that later decision as belonging to
    this one.
    """
    for field in ("paper_winner_selected", "final_model_selected",
                  "full_development_refit_executed",
                  "stage130_or_next_stage_executed", "merge_authorized",
                  "ready_for_review_authorized"):
        assert boundary[field] is False, field
    # nothing this action could open has been opened, then or since
    # ACTION-SCOPED: this decision fitted nothing; its own boundary says so.
    assert boundary["full_development_refit_executed"] is False
    # MOVED from a live global proxy to an action-scoped historical fact.
    # `stage130_started` is now True in the live Handoff, because the
    # Stage130 Phase 1 manuscript evidence package exists. That happened
    # AFTER this action, and Phase 1 is PRESENTATION only. What this
    # action guarantees -- that no Stage130 SCIENTIFIC execution has
    # begun -- is asserted here instead, and its own artifacts above
    # still pin `stage130_started = False` for its own moment.
    assert state["stage130_scientific_execution_started"] is False
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this action. This
    # action's own zero is asserted above / below; the snapshot pins the
    # firewall state it ran under.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_m3_cbi_final_test_rows_read"] == 0


# ---------------------------------------------- 13. the approved text exists
def test_the_approved_english_and_persian_text_are_recorded(decision, state):
    en = decision["approved_manuscript_text_en"]
    fa = decision["approved_manuscript_text_fa"]
    assert en == APPROVED_EN
    assert fa.strip()
    assert state["stage129_m3_cbi_approved_manuscript_text_en"] == APPROVED_EN
    assert state["stage129_m3_cbi_approved_manuscript_text_fa"] == fa
    for phrase in ("prespecified", "remained unresolved",
                   "point-in-time availability could not be established",
                   "not admitted to modeling", "was not executed",
                   "no p-value was computed", "no inferential conclusion",
                   "supplementary exploratory evidence",
                   "neither a substitute nor a proxy"):
        assert phrase in en, phrase
    for phrase in ("از پیش تعریف شده", "حل‌نشده باقی ماند", "اجرا نشد",
                   "هیچ مقدار p محاسبه نشد", "هیچ نتیجه استنباطی",
                   "اکتشافی تکمیلی", "جایگزین یا نماینده"):
        assert phrase in fa, phrase
    # the README quotes both texts; it wraps them across blockquote lines, so
    # compare against the unwrapped form rather than the raw bytes
    readme = _text(f"{_PKG_REL}/"
                   "README_STAGE129_M3_CBI_HUMAN_DISCONTINUATION_AND_REPORTING.md")
    flat = re.sub(r"\s+", " ", readme.replace("\n> ", " ").replace("\n>", " "))
    assert re.sub(r"\s+", " ", en) in flat
    assert re.sub(r"\s+", " ", fa) in flat


def test_the_approved_text_claims_no_executed_result_and_no_gate_verdict(
        decision, boundary, state):
    forbidden = ("p =", "p-value of", "p<", "p >", "p <", "significant",
                 "outperform", "improved", "improvement", "we reject",
                 "we accept", "rejected the null", "accepted the null")
    for field in ("approved_manuscript_text_en", "approved_manuscript_text_fa"):
        lowered = decision[field].lower()
        for phrase in forbidden:
            assert phrase not in lowered, f"{field} contains {phrase!r}"
        for verdict in GATE_FORBIDDEN:
            assert verdict not in decision[field], f"{field} contains {verdict}"
    assert boundary["reporting_claims_an_executed_result"] is False
    assert boundary["reporting_claims_m3_cbi_performance"] is False
    assert state["stage129_m3_cbi_reporting_claims_an_executed_result"] is False
    assert decision["approved_text_status"] == (
        "APPROVED_REPORTING_TEXT_ONLY_NOT_A_MANUSCRIPT_WRITING_AUTHORIZATION")
    assert decision["approved_text_is_a_reporting_decision_not_a_writing_authorization"] is True
    assert boundary["manuscript_writing_or_rewriting_authorized"] is False
    assert state["stage129_m3_cbi_manuscript_writing_authorized"] is False


def test_the_supersede_targets_the_pending_review_not_the_verdict(decision, state):
    marker = decision["superseded_marker"]
    assert marker["artifact"] == _GATE_REL
    assert marker["key"] == "m3_macro_data_gate_human_review_required"
    assert marker["previous_value"] is True
    assert marker["resolved_value"] == DISPOSITION
    assert marker["supersede_scope"] == (
        "the_pending_human_review_only_not_the_gate_status")
    assert marker["historical_artifact_preserved_byte_for_byte"] is True
    assert state["stage129_m3_cbi_supersedes_artifact"] == _GATE_REL
    assert state["stage129_m3_cbi_supersedes_key"] == (
        "m3_macro_data_gate_human_review_required")
    assert state["stage129_m3_cbi_supersedes_previous_value"] is True
    assert state["stage129_m3_cbi_gate_artifact_preserved"] is True
    # the superseded artifact still carries its own historical value
    assert state["m3_macro_data_gate_human_review_required"] is True


# ------------------------------------------- 14. the generator fails closed
def _run_generator(root):
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_m3_cbi_human_discontinuation_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A minimal tree with this package, the Gate package and the frozen SAP."""
    for rel in (_PKG_REL, _GATE_PKG_REL):
        src = os.path.join(REPO_ROOT, rel)
        dst = tmp_path / rel
        dst.mkdir(parents=True, exist_ok=True)
        for name in os.listdir(src):
            path = os.path.join(src, name)
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    (dst / name).write_bytes(fh.read())
    sap_dst = tmp_path / os.path.dirname(_SAP_REL)
    sap_dst.mkdir(parents=True, exist_ok=True)
    with open(os.path.join(REPO_ROOT, _SAP_REL), "rb") as fh:
        (tmp_path / _SAP_REL).write_bytes(fh.read())
    return tmp_path


def _write(root, rel, blob):
    with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
        json.dump(blob, fh, ensure_ascii=False, indent=2, sort_keys=True)


def test_the_sandbox_baseline_derives_cleanly(sandbox):
    markers = _run_generator(str(sandbox))
    assert markers["m3_cbi_disposition"] == DISPOSITION


_DEC = f"{_PKG_REL}/stage129_m3_cbi_human_discontinuation_decision.json"
_CMP = f"{_PKG_REL}/stage129_m3_cbi_confirmatory_comparison_record.json"
_BND = f"{_PKG_REL}/stage129_m3_cbi_governance_boundary.json"


@pytest.mark.parametrize("rel,key,value,needle", [
    # forging a PASS or FAIL verdict the Gate never returned
    (_DEC, "m3_macro_data_gate_terminal_status", "FAIL_M3_DATA_GATE", "reassign"),
    (_DEC, "m3_macro_data_gate_terminal_status",
     "PASS_FOR_M3_INCREMENTAL_EVALUATION", "reassign"),
    (_BND, "m3_macro_data_gate_terminal_status", "FAIL_M3_DATA_GATE", "reassign"),
    (_DEC, "m3_macro_data_gate_formal_failure", True, "formal Gate failure"),
    (_BND, "m3_macro_data_gate_status_reassigned_by_this_action", True, "reassign"),
    # claiming the Gate never ran
    (_DEC, "m3_macro_data_gate_executed", False, "WAS executed"),
    (_BND, "m3_macro_data_gate_executed", False, "WAS executed"),
    (_DEC, "m3_macro_data_gate_recorded_as_not_executed", True, "unexecuted"),
    # fabricating resolution of the unresolved reasons or the evidence
    (_DEC, "m3_macro_data_gate_unresolved_reasons_resolved_by_this_decision", 3,
     "unresolved"),
    (_BND, "m3_macro_data_gate_unresolved_reasons_resolved_by_this_action", 1,
     "unresolved"),
    (_DEC, "m3_macro_data_gate_unresolved_reason_count", 2, "count"),
    (_DEC, "point_in_time_availability_established", True, "point_in_time"),
    (_BND, "point_in_time_availability_established", True, "point-in-time"),
    (_DEC, "new_coverage_or_threshold_computed", True, "new_coverage"),
    # inventing a p-value or resolving the hypothesis
    (_CMP, "comparison_p_value", 0.02, "p-value"),
    (_CMP, "comparison_null_hypothesis_accepted", True, "null_hypothesis_accepted"),
    (_CMP, "comparison_null_hypothesis_rejected", True, "null_hypothesis_rejected"),
    (_CMP, "comparison_inferential_conclusion", "M3-CBI helps", "inferential"),
    (_CMP, "comparison_performance_claim", "improves PR-AUC", "performance_claim"),
    # erasing or renaming the prespecified comparison
    (_CMP, "comparison_removed_from_sap_history", True, "removed_from_sap"),
    (_CMP, "comparison_renamed_by_this_action", True, "renamed"),
    (_CMP, "confirmatory_holm_family_shrunk_by_this_action", True, "shrunk"),
    (_CMP, "confirmatory_holm_family_live", ["M2_minus_M1", "M4_minus_M3_CBI"],
     "confirmatory Holm family"),
    (_CMP, "frozen_sap_family_members", ["M2_minus_M1", "M4_minus_M3"], "frozen"),
    (_CMP, "frozen_sap_identifier_for_this_comparison", "M3_CBI_minus_M2", "frozen"),
    (_CMP, "alias_created_by_this_action", True, "alias"),
    (_CMP, "holm_final_adjustment_declared_complete", True, "holm_final"),
    # promoting the supplementary block into the vacated confirmatory role
    (_BND, "m3_lag_wdi_promoted_to_confirmatory_model", True, "promoted"),
    (_BND, "m3_lag_wdi_is_confirmatory_m3", True, "confirmatory_m3"),
    (_BND, "m3_lag_wdi_is_substitute_for_m3_cbi", True, "substitute"),
    (_BND, "m3_lag_wdi_results_used_to_fill_the_m3_cbi_comparison", True, "fill"),
    (_BND, "m3_lag_wdi_p_value_entered_confirmatory_holm_family", True, "holm"),
    (_BND, "m3_lag_wdi_disposition", "CONFIRMATORY_M3", "SUPPLEMENTARY"),
    (_CMP, "exploratory_value_admitted_into_confirmatory_family", True, "exploratory"),
    # authorizing the Final Test or an endgame step
    (_BND, "final_test_access_authorized", True, "final_test_access"),
    (_BND, "final_test_rows_read", 1, "final_test_rows_read"),
    (_DEC, "final_test_rows_read", 1, "final_test_rows_read"),
    (_BND, "final_test_locked", False, "Final Test locked"),
    (_BND, "stage130_or_next_stage_executed", True, "stage130"),
    (_BND, "final_model_selected", True, "final_model_selected"),
    (_BND, "paper_winner_selected", True, "paper_winner_selected"),
    (_BND, "full_development_refit_executed", True, "refit"),
    (_BND, "next_research_action_authorized", True, "next_research_action_authorized"),
    # reopening the block, or touching an existing PR
    (_BND, "m3_cbi_reopening_authorized", True, "m3_cbi_reopening_authorized"),
    (_BND, "m3_cbi_modeling_will_run", True, "m3_cbi_modeling_will_run"),
    (_BND, "m3_cbi_block_admitted", True, "m3_cbi_block_admitted"),
    (_BND, "existing_pull_requests_modified_by_this_action", True, "pull_requests"),
    (_BND, "manuscript_writing_or_rewriting_authorized", True, "writing"),
])
def test_the_generator_fails_closed_on_tampering(sandbox, rel, key, value, needle):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob[key] = value
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


def test_the_generator_fails_closed_when_a_counter_is_nonzero(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _BND).read_text(encoding="utf-8"))
    blob["counters"]["data_gate_executions"] = 1
    _write(str(sandbox), _BND, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "data_gate_executions" in str(exc.value)


def test_the_generator_fails_closed_when_the_text_claims_a_result(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _DEC).read_text(encoding="utf-8"))
    blob["approved_manuscript_text_en"] = (
        "M3-CBI significantly improved discrimination over M2.")
    _write(str(sandbox), _DEC, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "claims an executed result" in str(exc.value)


def test_the_generator_fails_closed_if_the_gate_artifact_is_rewritten(sandbox):
    """The decision is anchored on the executed Gate's real terminal status. If
    the Gate artifact is quietly rewritten, the anchor is gone and the build
    must fail rather than inherit a forged status."""
    import update_ai_handoff as gen
    rel = _GATE_REL
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["gate_status"] = "FAIL_M3_DATA_GATE"
    blob["m3_macro_data_gate_status"] = "FAIL_M3_DATA_GATE"
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "byte-for-byte" in str(exc.value)


def test_the_generator_fails_closed_if_the_gate_reason_count_drifts(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _GATE_REL).read_text(encoding="utf-8"))
    blob["unresolved_or_blocker_reasons"] = blob["unresolved_or_blocker_reasons"][:2]
    _write(str(sandbox), _GATE_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "unresolved reason count" in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _DEC)
    assert _run_generator(str(sandbox)) == {}


# --------------------------------- 15. validator + semantic idempotency
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage129_m3_cbi_human_discontinuation_markers(REPO_ROOT)
    second = gen.derive_stage129_m3_cbi_human_discontinuation_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["m3_cbi_disposition"] == DISPOSITION


def test_current_state_renders_the_decision_without_a_gate_verdict():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert DISPOSITION in text
    assert "M3-CBI DISCONTINUED by human decision" in text
    assert GATE_TERMINAL in text
    assert "no inferential conclusion is drawn for M3-CBI" in text
    for verdict in GATE_FORBIDDEN:
        assert verdict not in text, verdict


def test_roadmap_records_the_decision_without_opening_a_new_stage(
        roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["m3_cbi_discontinuation_action_id"] == ACTION_ID
    assert fm["m3_cbi_next_action_id"] == "human_decision_required"
    assert fm["m3_cbi_next_action_authorized"] == "false"
    assert fm["m3_cbi_manuscript_writing_authorized"] == "false"
    # no live pointer chain moves, and none names an execution step
    assert fm["next_research_action_id"] == "human-dataset-release-candidate-digest-review"
    assert fm["next_research_action_authorized"] == "false"
    assert fm["m3_lag_wdi_next_action_id"] == "human_decision_required"
    assert fm["m4_next_action_id"] == "human_decision_required"
    assert fm["m3_lag_wdi_final_research_disposition"] == LAG_WDI_DISPOSITION
    for key in ("m3_cbi_next_action_id", "next_research_action_id",
                "m3_lag_wdi_next_action_id"):
        for forbidden in ("data-gate", "retrieval", "modeling", "stage130",
                          "final-test", "refit"):
            assert forbidden not in fm[key], (key, forbidden)
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert DISPOSITION in body


# --------------------------------------------------------- package hygiene
def test_no_new_data_or_metric_artifact_was_created():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_m3_cbi_human_discontinuation_and_reporting.json")
    assert manifest["m3_cbi_value_files_committed"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["m3_macro_data_gate_reexecuted"] is False


def test_package_hash_manifest_matches_every_file():
    import hashlib
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_m3_cbi_human_discontinuation_and_reporting.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_the_executed_gate_package_is_byte_for_byte_intact():
    """This decision answers the Gate's pending review. It may not edit it."""
    import hashlib
    manifest_rel = f"{_GATE_PKG_REL}/metadata_and_hashes_stage128_m3_macro_data_gate.json"
    if not os.path.isfile(os.path.join(REPO_ROOT, manifest_rel)):
        pytest.skip("the Gate package carries no hash manifest")
    manifest = _load(manifest_rel)
    for name, info in manifest.get("package_files", {}).items():
        with open(os.path.join(REPO_ROOT, _GATE_PKG_REL, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
