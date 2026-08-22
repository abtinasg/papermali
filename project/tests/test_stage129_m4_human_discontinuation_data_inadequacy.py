"""Stage129 — human discontinuation of M4 for data inadequacy.

This action is a HUMAN GOVERNANCE DECISION ONLY. These tests pin:

  * that the decision is recorded exactly, and as a human decision;
  * that it is NOT a formal Gate verdict and never borrows Gate vocabulary;
  * that observational coverage is never presented as formal Gate coverage;
  * that everything downstream of M4 stays unauthorized and reopening needs a
    new human authorization;
  * that the four frozen candidates, the Holm family, the earlier packages and
    the Final Test lock all survive untouched;
  * that the generated Handoff docs agree with the package and were produced by
    the canonical generator, not by hand.
"""
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PKG_REL = "project/stage129/m4_human_discontinuation_data_inadequacy"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_OBS_REL = "project/stage129/m4_observational_audit_extraction_v4_3_1"

ACTION_ID = "stage129-m4-human-discontinuation-data-inadequacy"
STATUS = "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY"
GATE_VERDICT_VOCAB = ("PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE",
                      "UNRESOLVED_M4_DATA_GATE")
CANDIDATES = ["audit_opinion_type", "going_concern_flag", "audit_lag_days", "board_size"]
OBS_STATUS = "OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT"


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def decision():
    return _load(f"{_PKG_REL}/stage129_m4_human_discontinuation_decision.json")


@pytest.fixture(scope="module")
def boundary():
    return _load(f"{_PKG_REL}/stage129_m4_human_discontinuation_governance_boundary.json")


@pytest.fixture(scope="module")
def evidence():
    return _load(f"{_PKG_REL}/stage129_m4_human_discontinuation_evidence_references.json")


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


# ------------------------------------------------- 1. the decision is recorded
def test_the_human_decision_is_recorded_exactly(decision):
    assert decision["decision_id"] == ACTION_ID
    assert decision["decision_type"] == "human_scientific_decision"
    assert decision["decision_status"] == STATUS
    assert decision["authorized_by_human"] is True
    assert decision["human_decision_verbatim"].strip()
    assert decision["authorized_scope"].strip()
    assert decision["m4_block_disposition_for_this_study"] == "discontinued"


def test_readme_records_the_decision_and_its_limits():
    text = _text(f"{_PKG_REL}/README_STAGE129_M4_HUMAN_DISCONTINUATION_DATA_INADEQUACY.md")
    assert STATUS in text
    assert "human_decision_required" in text
    assert "NOT a formal Gate failure" in text
    assert "UNRESOLVED_REPORTING_DECISION" in text


# --------------------------------------- 2/3/4. not a Gate verdict, no forgery
def test_the_formal_gate_was_never_executed(decision, boundary, state):
    assert decision["formal_m4_data_gate_executed"] is False
    assert decision["formal_m4_gate_verdict"] is None
    assert decision["is_a_formal_gate_failure"] is False
    assert boundary["m4_data_gate_executed"] is False
    assert boundary["m4_formal_gate_verdict"] is None
    assert boundary["m4_coverage_calculated"] is False
    assert state["m4_data_gate_executed"] is False
    assert state["m4_formal_gate_verdict"] is None
    assert state["stage129_m4_discontinuation_is_formal_gate_failure"] is False


def test_no_gate_verdict_vocabulary_is_forged_anywhere_in_the_package():
    """A discontinuation that never ran the Gate may not emit Gate verdicts.

    The README may NAME the vocabulary to explain why it is not used, so JSON
    artifacts are checked value-by-value rather than by raw substring.
    """
    for name in os.listdir(_PKG):
        if not name.endswith(".json"):
            continue
        blob = _load(f"{_PKG_REL}/{name}")
        found = []

        def walk(node):
            if isinstance(node, dict):
                for key, val in node.items():
                    if key == "gate_verdict_vocabulary_deliberately_not_used":
                        continue          # the explicit not-used declaration
                    walk(val)
            elif isinstance(node, list):
                for val in node:
                    walk(val)
            elif isinstance(node, str) and node in GATE_VERDICT_VOCAB:
                found.append(node)

        walk(blob)
        assert found == [], f"{name} publishes Gate verdict vocabulary {found}"


def test_observational_coverage_is_never_called_formal_gate_coverage(
        decision, state):
    assert decision["observational_coverage_is_not_formal_gate_coverage"] is True
    assert state[
        "stage129_m4_observational_coverage_is_not_formal_gate_coverage"] is True
    basis = decision["decision_basis"]
    # the figures behind the decision must be the observational ones, over the
    # WHOLE canonical population -- never a development/fold Gate computation
    assert basis["canonical_population_rows"] == 1331
    assert basis["canonical_population_tickers"] == 130
    assert basis["observational_verified_auditor_opinion_rows"] == 444
    assert basis["observational_auditor_report_date_rows"] == 446
    assert basis["observational_field_level_missing"] == 2214
    assert state["stage129_m4_observational_verified_opinion_rows"] == 444
    assert state["stage129_m4_observational_report_date_rows"] == 446
    # and they must agree with the committed observational extraction itself
    obs_qa = _load(f"{_OBS_REL}/qa_report_v4_3_1.json")
    assert obs_qa["rows_with_verified_opinion"] == 444
    assert obs_qa["rows_with_verified_report_date"] == 446
    assert obs_qa["field_level_missing"] == 2214


def test_the_reason_is_data_not_a_model_result(decision):
    assert decision["reason_class"] == "data_accessibility_coverage_and_definition_mismatch"
    assert decision["reason_is_poor_model_result"] is False
    assert decision["reason_is_outcome_inspection"] is False
    assert decision["outcome_or_final_test_observation_used_for_this_decision"] is False
    assert decision["decision_made_before_any_m4_modeling"] is True


# ------------------------------------------- 5/7. everything downstream is shut
def test_m4_retrieval_and_manual_completion_are_stopped(decision, boundary, state):
    assert decision["m4_retrieval_to_continue"] is False
    assert decision["m4_manual_completion_to_continue"] is False
    assert boundary["m4_retrieval_continues"] is False
    assert boundary["m4_manual_completion_continues"] is False
    assert state["m4_retrieval_continues"] is False
    assert state["m4_manual_completion_continues"] is False


def test_feature_materialization_modeling_and_evaluation_are_unauthorized(
        decision, boundary, state):
    for src, keys in (
        (decision, ("m4_feature_materialization_authorized", "m4_modeling_authorized",
                    "m4_incremental_evaluation_authorized")),
        (boundary, ("m4_feature_materialization_authorized", "m4_modeling_will_run",
                    "m4_incremental_evaluation_will_run", "m4_block_admitted")),
        (state, ("m4_feature_materialization_authorized", "m4_modeling_will_run",
                 "m4_incremental_evaluation_will_run", "m4_block_admitted",
                 "m4_modeling_started")),
    ):
        for key in keys:
            assert src[key] is False, key


def test_nothing_was_computed_by_this_action(boundary, evidence):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("m4_features_materialized", "formal_gate_coverage_computations",
                "model_fits", "predictions", "bootstrap_executions",
                "holm_calculations", "shap_executions", "final_test_rows_read",
                "new_data_files_created"):
        assert counters[key] == 0, key
    assert evidence["new_data_created_by_this_action"] is False


def test_evidence_references_only_already_committed_artifacts(evidence):
    import hashlib
    assert evidence["references"], "the decision must cite its evidence"
    for ref in evidence["references"]:
        path = os.path.join(REPO_ROOT, ref["path"])
        assert os.path.isfile(path), ref["path"]
        assert ref["hash_scope"] == "committed_repository_artifact"
        with open(path, "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == ref["sha256"], ref["path"]
        assert len(blob) == ref["bytes"], ref["path"]


# --------------------------------------------- 16. reopening needs a new human
def test_reopening_requires_a_new_explicit_human_authorization(
        decision, boundary, state):
    assert decision["reopening_requires_new_explicit_human_authorization"] is True
    assert decision["reopening_authorized_now"] is False
    assert boundary["m4_reopening_authorized"] is False
    assert boundary["m4_reopening_requires_new_human_authorization"] is True
    assert state["m4_reopening_authorized"] is False
    assert state["m4_reopening_requires_new_human_authorization"] is True


# ------------------------------------------ 6. the four candidates are frozen
def test_the_four_frozen_candidates_survive_unchanged(decision, state):
    assert decision["m4_candidate_count"] == 4
    assert decision["m4_candidate_set"] == CANDIDATES
    assert decision["m4_candidate_count_changed_by_this_decision"] is False
    assert decision["m4_candidates_removed_or_renamed_by_this_decision"] is False
    assert decision["m4_candidates_substituted_by_this_decision"] is False
    assert state["stage129_m4_candidate_count_after_discontinuation"] == 4
    assert state["stage129_m4_candidate_set_after_discontinuation"] == CANDIDATES
    assert state["stage129_m4_candidates_removed_or_renamed"] is False
    # the ORIGINAL contract's candidate list is still intact and identical
    contract = _load("project/stage129/m4_governance_data_gate_contract/"
                     "stage129_m4_data_gate_contract.json")
    assert contract["candidate_set"]["candidates"] == CANDIDATES
    assert state["stage129_m4_candidate_set"] == CANDIDATES
    assert state["stage129_m4_candidate_count"] == 4


# ------------------------------------------------------- 11. the Holm family
def test_holm_family_unchanged_and_m4_comparison_unexecuted(boundary, state):
    assert boundary["confirmatory_holm_family_modified_by_this_action"] is False
    assert boundary["m4_comparison_id"] == "M4_minus_M3_CBI"
    assert boundary["m4_comparison_status"] == "NOT_EXECUTED_M4_DISCONTINUED"
    assert boundary["m4_comparison_p_value"] is None
    assert boundary["m4_comparison_null_hypothesis_accepted_or_rejected"] is None
    assert boundary["family_shrunk_post_hoc_after_observing_a_result"] is False
    assert state["stage129_m4_comparison_status"] == "NOT_EXECUTED_M4_DISCONTINUED"
    assert state["stage129_m4_comparison_p_value"] is None
    assert state["stage129_m4_confirmatory_holm_family_modified"] is False
    assert state["stage129_m4_family_shrunk_post_hoc"] is False
    # the family membership list itself is untouched
    assert state["stage129_m4_confirmatory_holm_family"] == [
        "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
    assert state["stage129_m4_confirmatory_holm_family_executed"] is False


def test_the_unresolved_reporting_decision_is_recorded_not_invented(
        boundary, state):
    """The frozen contract makes family-2 membership conditional on admission,
    but says nothing about presenting a never-admitted block's comparison. At
    the time of THIS decision that gap was unresolved, and this artifact must
    still say so -- it is the historical record of what was true then.

    The gap was resolved later, by the separate
    ``stage129-m4-manuscript-reporting-decision``, which supersedes this single
    marker on the live Handoff surface while leaving this package byte-for-byte
    intact. So the artifact keeps `UNRESOLVED_REPORTING_DECISION` and the live
    state carries the resolved value; the resolved value is pinned by that
    decision's own test file.
    """
    assert boundary["family_membership_is_prospectively_conditional_on_block_admission"] is True
    assert boundary[
        "manuscript_reporting_decision_for_the_unexecuted_m4_comparison"
    ] == "UNRESOLVED_REPORTING_DECISION"
    assert state[
        "stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison"
    ] == "REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE"
    assert state[
        "stage129_m4_manuscript_reporting_decision_previous_value"
    ] == "UNRESOLVED_REPORTING_DECISION"
    # and the conditional wording must really exist in the frozen contract
    metrics = _load("project/stage125/part4_metrics_uncertainty_contract_stage125.json")
    assert "confirmatory_family_2_adjacent_block_gains_if_admitted" in metrics["multiplicity"]
    assert metrics["multiplicity"]["correction"] == "Holm"


# ------------------------------------------------ 8. Final Test firewall
def test_final_test_stays_locked_with_zero_rows_read(decision, boundary, state):
    assert decision["final_test_locked"] is True
    assert decision["final_test_access_authorized"] is False
    assert decision["final_test_rows_read"] == 0
    assert boundary["final_test_rows_read"] == 0
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this action. This
    # action's own zero is asserted above / below; the snapshot pins the
    # firewall state it ran under.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_m4_final_test_rows_read"] == 0
    assert state["stage129_m4_final_test_locked"] is True


# ------------------------------------------------- 9/10. M1/M2/M3 untouched
def test_prior_blocks_and_dispositions_are_untouched(boundary, state):
    for key in ("m1_status_modified_by_this_action",
                "m2_status_modified_by_this_action",
                "m2_retained_status_modified_by_this_action",
                "m3_cbi_status_modified_by_this_action",
                "m3_cbi_declared_successful_by_this_action",
                "m3_lag_wdi_disposition_modified_by_this_action",
                "m3_lag_wdi_promoted_to_confirmatory_model",
                "paper_winner_selected", "final_model_selected",
                "full_development_refit_executed",
                "stage130_or_next_stage_executed"):
        assert boundary[key] is False, key
    assert state["stage129_m4_m3_cbi_status_preserved"] == "UNRESOLVED_M3_DATA_GATE"
    assert state["stage129_m4_m3_lag_wdi_disposition_preserved"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")
    assert state["stage128_m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert state["stage128_m3_lag_wdi_is_confirmatory_m3"] is False


# ---------------------------------- 12. the V4.3.1 package stays observational
def test_the_observational_package_is_untouched_and_not_a_model_input(
        boundary, state):
    assert boundary["observational_package_modified_by_this_action"] is False
    assert boundary["observational_extraction_admitted_as_model_input"] is False
    assert boundary["observational_extraction_may_be_reported_in_limitations"] is True
    assert boundary["observational_package_status_preserved"] == OBS_STATUS
    assert state["stage129_m4_observational_package_status_preserved"] == OBS_STATUS
    # the package itself still declares the same status, unedited
    obs_boundary = _load(f"{_OBS_REL}/"
                         "stage129_m4_observational_extraction_governance_boundary.json")
    assert obs_boundary["package_status"] == OBS_STATUS
    assert obs_boundary["m4_data_gate_executed"] is False


def test_prior_stage129_packages_keep_their_historical_markers(boundary):
    assert boundary["prior_contract_lock_history_preserved"] is True
    assert boundary["prior_prerequisite_resolution_history_preserved"] is True
    assert boundary["prior_packages_modified_by_this_action"] is False
    contract = _load("project/stage129/m4_governance_data_gate_contract/"
                     "stage129_m4_data_gate_contract.json")
    blob = json.dumps(contract, ensure_ascii=False)
    assert '"m4_contract_complete": false' in blob
    assert '"m4_data_gate_executable": false' in blob
    prereq = _load("project/stage129/m4_authoritative_prerequisite_resolution/"
                   "stage129_m4_prerequisite_resolution_decision.json")
    assert prereq  # present and readable; its own tests pin its content


# ------------------------------- 13/14. generated docs come from the generator
def test_generated_docs_are_consistent_with_the_generator():
    """--check must pass, i.e. the committed generated docs are exactly what the
    canonical generator produces. This is what makes hand-editing detectable."""
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_decision_is_visible_in_the_handoff(state):
    assert state["stage129_m4_discontinuation_recorded"] is True
    assert state["stage129_m4_discontinuation_action_id"] == ACTION_ID
    assert state["stage129_m4_discontinuation_authorized_by_human"] is True
    assert state["m4_block_disposition"] == STATUS
    assert state["stage129_m4_block_disposition"] == STATUS


def test_current_state_renders_the_discontinuation_without_a_gate_claim():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert STATUS in text
    assert "NOT a formal Gate failure" in text
    for verdict in ("PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE"):
        assert verdict not in text, verdict


def test_roadmap_records_the_decision_and_the_disposition(roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["m4_block_disposition"] == STATUS
    assert fm["m4_discontinuation_action_id"] == ACTION_ID
    assert fm["m4_data_gate_executed"] == "false"
    assert fm["m4_formal_gate_verdict"] == "null"
    assert fm["m4_retrieval_continues"] == "false"
    assert fm["m4_modeling_will_run"] == "false"
    assert fm["m4_incremental_evaluation_will_run"] == "false"
    assert fm["m4_reopening_authorized"] == "false"
    assert fm["m4_reopening_requires_new_human_authorization"] == "true"
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert STATUS in body


# --------------------------------- 15. the next pointer does not execute M4
def test_the_next_pointer_does_not_point_at_m4_execution(boundary, state,
                                                         roadmap_front_matter):
    assert boundary["next_action_id"] == "human_decision_required"
    assert boundary["next_action_authorized"] is False
    assert boundary["next_action_executes_m4"] is False
    assert boundary["pointer_is_not_authorization"] is True
    # the M4 pointer must no longer name the Gate action it used to name
    assert state["stage129_m4_next_action_id"] == "human_decision_required"
    assert state["stage129_m4_next_action_id"] != "stage129-m4-governance-data-gate"
    assert state["stage129_m4_next_action_scope"] == (
        "m4_discontinued_no_further_m4_action_is_authorized")
    assert state["stage129_m4_next_action_authorized"] is False
    assert state["stage129_m4_next_action_executes_m4"] is False
    assert roadmap_front_matter["m4_next_action_id"] == "human_decision_required"
    assert roadmap_front_matter["m4_next_action_authorized"] == "false"


def test_the_live_research_pointers_are_not_advanced_by_this_action(state):
    """This decision owns the M4 pointer only. It must not move either live
    research pointer chain."""
    assert state["next_research_action_id"] == "human-zenodo-publication-decision"
    assert state["next_research_action_authorized"] is False
    assert state["stage128_m3_lag_wdi_next_action_id"] == "human_decision_required"


# --------------------------------------------- 17. nothing new was produced
def test_no_new_data_or_metric_artifact_was_created():
    """The package may contain only the decision record itself."""
    allowed_suffixes = (".json", ".md")
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith(allowed_suffixes), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_m4_human_discontinuation_data_inadequacy.json")
    assert manifest["m4_value_files_committed"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0


def test_package_hash_manifest_matches_every_file():
    import hashlib
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_m4_human_discontinuation_data_inadequacy.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG)
               if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
