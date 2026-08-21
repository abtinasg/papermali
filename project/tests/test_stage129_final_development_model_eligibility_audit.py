"""Stage129 — the read-only final-development model eligibility audit.

The risk this audit carries is that an AUDIT quietly becomes a SELECTION. These
tests pin it shut:

  * the audit reads committed artifacts only and performs no row-level analysis
    and no metric recomputation;
  * the candidate matrix is exactly M1/M2 x the three frozen algorithms;
  * both verdicts come from the locked vocabularies;
  * a UNIQUE verdict is rejected unless it carries a real rule path, key,
    binding phrase and deterministic proof -- and a non-unique verdict may not
    smuggle a determined candidate;
  * `M2 retained` is never read as `M2 selected`, and M2's non-superiority
    stands;
  * robustness ordering instability is reported and never used to drop a
    candidate;
  * a selected configuration per algorithm is never a selected final algorithm;
  * M3-CBI and M4 stay discontinued, M3-LAG-WDI stays supplementary;
  * the Holm family keeps all three members with null p-values;
  * no winner, no final model, no refit, no Stage130, no Final Test.
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

_PKG_REL = "project/stage129/final_development_model_eligibility_audit"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_VERDICT_REL = f"{_PKG_REL}/stage129_final_model_eligibility_audit_verdict.json"
_MATRIX_REL = f"{_PKG_REL}/stage129_final_model_eligibility_matrix.json"
_ORDERING_REL = f"{_PKG_REL}/stage129_robustness_ordering_record.json"
_BOUNDARY_REL = (
    f"{_PKG_REL}/stage129_final_model_eligibility_audit_governance_boundary.json")

ACTION_ID = "stage129-final-development-model-eligibility-audit"
BLOCK_VERDICTS = (
    "UNIQUE_FINAL_BLOCK_DETERMINED_BY_FROZEN_RULE",
    "FINAL_BLOCK_REQUIRES_HUMAN_DECISION",
    "NO_BLOCK_CURRENTLY_ELIGIBLE_UNDER_FROZEN_RULES",
    "CONTRACT_CONFLICT_PREVENTS_BLOCK_DETERMINATION",
)
ALGORITHM_VERDICTS = (
    "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE",
    "FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION",
    "NO_ALGORITHM_CURRENTLY_ELIGIBLE_UNDER_FROZEN_RULES",
    "CONTRACT_CONFLICT_PREVENTS_ALGORITHM_DETERMINATION",
)
HOLM_REPORTING_VERDICT = (
    "HOLM_FINAL_REPORTING_REQUIRES_SEPARATE_HUMAN_OR_METHODS_DECISION")
BLOCKS = ["M1", "M2"]
ALGORITHMS = ["regularized_logistic_regression", "random_forest", "xgboost"]
HOLM_FAMILY = ["M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def verdict():
    return _load(_VERDICT_REL)


@pytest.fixture(scope="module")
def matrix():
    return _load(_MATRIX_REL)


@pytest.fixture(scope="module")
def ordering():
    return _load(_ORDERING_REL)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BOUNDARY_REL)


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


# --------------------------------- 1. read-only, no row-level, no recomputation
def test_the_audit_is_read_only_over_committed_artifacts(verdict, boundary,
                                                         state):
    assert verdict["audit_is_read_only"] is True
    assert verdict["sources_read_are_committed_artifacts_only"] is True
    assert verdict["audit_performed_row_level_analysis"] is False
    assert verdict["audit_recomputed_any_metric"] is False
    assert boundary["audit_read_only"] is True
    assert boundary["new_metric_computed_from_row_level_data"] is False
    assert boundary["new_p_value_created"] is False
    assert boundary["new_tie_breaker_rule_created"] is False
    assert boundary["calibration_executed"] is False
    assert state["stage129_final_model_eligibility_audit_is_read_only"] is True
    assert state["stage129_final_model_eligibility_audit_recorded"] is True
    assert state["stage129_final_model_eligibility_audit_action_id"] == ACTION_ID


def test_every_execution_counter_is_zero(boundary):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("model_fits", "predict_calls", "predict_proba_calls",
                "decision_function_calls", "tuning_runs", "feature_searches",
                "threshold_searches", "bootstrap_executions",
                "resampling_executions", "metrics_computed",
                "confidence_intervals_computed", "p_values_computed",
                "calibration_executions", "shap_executions", "holm_executions",
                "robustness_executions", "row_level_scientific_data_reads",
                "final_test_rows_read", "new_data_files_created"):
        assert counters[key] == 0, key


def test_every_quoted_number_matches_its_source_artifact(matrix, ordering):
    """The audit quotes; it never recomputes. Each quoted figure must be
    byte-equal to the committed artifact it cites."""
    lock = _load("project/stage126/stage126_m1_primary_development_lock.json")
    assert ordering["primary"]["pooled_oof_pr_auc"] == lock["pooled_oof_pr_auc"]
    assert ordering["primary"]["observed_ordering"] == ALGORITHMS
    for part in ordering["robustness_parts"]:
        n = part["part"]
        src = _load(f"project/stage126/stage126_m1_robustness_part{n}"
                    "_primary_comparison.json")
        assert part["pooled_pr_auc"] == src[f"part{n}_pooled_pr_auc"], n
    # the M1 matrix rows quote the primary lock
    for cand in matrix["candidates"]:
        if cand["block"] != "M1":
            continue
        assert cand["development_pooled_oof_pr_auc"] == \
            lock["pooled_oof_pr_auc"][cand["algorithm"]], cand["algorithm"]
        assert cand["configuration_id"] == \
            lock["selected_configurations"][cand["algorithm"]], cand["algorithm"]
    # the M2 matrix rows quote the paired bootstrap summary
    delta = _load("project/stage128/m2_incremental_evaluation/"
                  "stage127_m2_paired_bootstrap_delta_summary.json")
    for cand in matrix["candidates"]:
        if cand["block"] != "M2":
            continue
        fam = delta["by_family"][cand["algorithm"]]
        assert cand["development_pooled_oof_pr_auc"] == \
            fam["metrics"]["pr_auc"]["m2_estimate"], cand["algorithm"]
        assert cand["configuration_id"] == fam["configuration_id"], cand["algorithm"]


# ------------------------------------------- 2. the matrix shape is exactly right
def test_the_candidate_matrix_is_exactly_two_blocks_by_three_algorithms(
        matrix, state):
    assert matrix["blocks_audited"] == BLOCKS
    assert matrix["algorithms_audited"] == ALGORITHMS
    assert matrix["candidate_count"] == 6
    assert len(matrix["candidates"]) == 6
    seen = {(c["block"], c["algorithm"]) for c in matrix["candidates"]}
    assert seen == {(b, a) for b in BLOCKS for a in ALGORITHMS}
    assert state["stage129_audit_candidate_count"] == 6
    assert state["stage129_audit_blocks_audited"] == BLOCKS
    assert state["stage129_audit_algorithms_audited"] == ALGORITHMS
    # the three algorithms are the frozen ones, not a set this audit chose
    entry = _load("project/stage125/part5_stage126_m1_entry_contract_stage125.json")
    assert sorted(entry["primary_specification"]["models"]) == sorted(ALGORITHMS)


def test_every_candidate_carries_the_required_audit_fields(matrix):
    required = ("block", "algorithm", "configuration_id",
                "configuration_source_artifact", "development_evaluation_exists",
                "configuration_frozen", "robustness_evidence_available",
                "predictor_block_admitted", "eligible_for_final_selection",
                "disqualifying_rule", "unresolved_interpretation",
                "selection_rule_source")
    for cand in matrix["candidates"]:
        for field in required:
            assert field in cand, (cand.get("block"), cand.get("algorithm"), field)
        # every cited source artifact must actually exist
        src = cand["configuration_source_artifact"].split("#")[0].split(" (")[0]
        assert os.path.isfile(os.path.join(REPO_ROOT, src)), src
    assert matrix["eligibility_is_not_selection"] is True
    assert matrix["no_candidate_declared_winner_on_point_estimate"] is True
    assert matrix["metrics_are_quoted_never_recomputed"] is True
    assert matrix["point_estimates_are_quoted_from_committed_artifacts_only"] is True


def test_only_m1_and_m2_are_audited_because_m3_and_m4_never_produced_a_model(
        matrix):
    excluded = matrix["blocks_excluded"]
    assert set(excluded) == {"M3_CBI", "M4"}
    for name, blob in excluded.items():
        assert blob["modeling_ever_executed"] is False, name
        assert os.path.isfile(os.path.join(REPO_ROOT, blob["evidence_path"])), name
    assert excluded["M3_CBI"]["disposition"] == (
        "M3_CBI_DISCONTINUED_BY_HUMAN_DECISION_UNRESOLVED_DATA_GATE_AND_"
        "UNPROVEN_POINT_IN_TIME")
    assert excluded["M4"]["disposition"] == (
        "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY")


# ----------------------------------- 3/4. verdicts, vocabulary and proof burden
def test_the_verdicts_come_from_the_locked_vocabularies(verdict, state,
                                                        roadmap_front_matter):
    assert verdict["block_verdict"] in BLOCK_VERDICTS
    assert verdict["algorithm_verdict"] in ALGORITHM_VERDICTS
    assert verdict["holm_reporting_verdict"] == HOLM_REPORTING_VERDICT
    assert state["stage129_final_block_verdict"] == verdict["block_verdict"]
    assert state["stage129_final_algorithm_verdict"] == verdict["algorithm_verdict"]
    assert state["stage129_holm_reporting_verdict"] == HOLM_REPORTING_VERDICT
    assert roadmap_front_matter["final_block_verdict"] == verdict["block_verdict"]
    assert roadmap_front_matter["final_algorithm_verdict"] == verdict["algorithm_verdict"]
    # exactly one verdict per audit, not a list
    assert isinstance(verdict["block_verdict"], str)
    assert isinstance(verdict["algorithm_verdict"], str)


def test_the_recorded_verdicts_are_both_human_decision_with_no_candidate(
        verdict, state, roadmap_front_matter):
    """This audit's actual finding: neither is uniquely determined."""
    assert verdict["block_verdict"] == "FINAL_BLOCK_REQUIRES_HUMAN_DECISION"
    assert verdict["algorithm_verdict"] == "FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION"
    assert verdict["audit_determined_candidate"] is None
    assert verdict["block_verdict_basis"]["audit_determined_candidate"] is None
    assert verdict["algorithm_verdict_basis"]["audit_determined_candidate"] is None
    assert verdict["block_verdict_basis"]["deterministic_rule_found"] is False
    assert verdict["algorithm_verdict_basis"]["deterministic_rule_found"] is False
    assert state["stage129_final_block_determined_candidate"] is None
    assert state["stage129_final_algorithm_determined_candidate"] is None
    assert roadmap_front_matter["final_block_determined_candidate"] == "null"
    assert roadmap_front_matter["final_algorithm_determined_candidate"] == "null"


def test_the_non_unique_verdicts_cite_real_prohibition_evidence(verdict):
    """A 'requires human decision' verdict still has to show its work: the
    prohibitions and the absence of a rule must point at real files."""
    algo = verdict["algorithm_verdict_basis"]
    assert algo["prespecified_model_tie_breaker_exists"] is False
    assert algo["multiple_eligible_configurations"] is True
    assert algo["ordering_unstable_across_robustness"] is True
    assert algo["confirmatory_family_1_executed"] is False
    assert algo["retained_families_count"] == 3
    assert algo["frozen_rule_absent_detail"].strip()
    for citation in algo["explicit_prohibition_citations"]:
        assert os.path.isfile(os.path.join(REPO_ROOT, citation["path"])), citation
        assert citation["key"].strip()
        assert citation["binding_phrase"].strip()
    blk = verdict["block_verdict_basis"]
    assert blk["m2_retention_explicitly_excludes_selection"] is True
    assert blk["contract_states_what_happens_when_superiority_is_absent"] is False
    assert blk["eligible_blocks"] == BLOCKS
    for citation in blk["m2_retention_citations"]:
        assert os.path.isfile(os.path.join(REPO_ROOT, citation["path"])), citation
        assert citation["key"].strip()


def test_the_cited_prohibitions_really_exist_in_the_frozen_artifacts():
    """Negative control on the citations themselves: quoting a rule that is not
    there would make the verdict unfalsifiable."""
    closure = _load("project/stage126/stage126_m1_robustness_closure_synthesis_record.json")
    assert "winner_selection" in closure["prohibited_actions"]
    finding = closure["scientific_interpretation"]["E_overall_synthesis"]["finding"]
    assert "selecting a winning model family" in finding
    freeze = _load("project/stage126/stage126_m1_retained_design_freeze.json")
    not_auth = freeze["authorization_scope"]["not_authorized"]
    assert "paper_winner_selection" in not_auth
    assert "final_model_selection" in not_auth
    assert len(freeze["retained_model_families"]) == 3
    assert freeze["status_flags"]["final_model_selected"] is False
    # the metrics contract has no model-level selection rule, only a prohibition
    metrics = _load("project/stage125/part4_metrics_uncertainty_contract_stage125.json")
    assert metrics["primary_metric"] == "PR-AUC"
    assert metrics["calibration"]["do_not_select_winner_on_calibrated_final_test"] is True
    assert metrics["thresholded_secondary"]["tie_break"] == "higher_threshold"
    assert "model_selection_rule" not in metrics
    assert "winner_selection_rule" not in metrics


# ------------------------------------- 5/6. M2 retained != selected / superior
def test_m2_retention_is_never_read_as_a_final_selection(verdict, boundary,
                                                         state):
    assert verdict["terminology_distinctions_preserved"][
        "m2_retained_is_not_m2_final_block_selected"] is True
    assert boundary["m2_retention_treated_as_final_selection"] is False
    assert state["stage129_audit_m2_retained_is_not_final_selection"] is True
    # and the frozen retention decision really says so
    dec = _load("project/stage128/m2_retained_block_human_decision/"
                "stage128_m2_retained_block_human_decision.json")
    assert "final_model_selection" in dec["m2_retention_does_not_imply"]
    assert "paper_winner_selection" in dec["m2_retention_does_not_imply"]
    assert dec["decision_is_a_retained_block_decision_not_a_superiority_decision"] is True
    assert dec["m2_role"] == "intermediate_confirmatory_block"
    assert dec["m2_retention_basis"] == (
        "preregistered_nested_confirmatory_architecture_preservation_not_"
        "observed_predictive_superiority")
    assert dec["final_model_selected"] is False
    assert dec["paper_winner_selected"] is False


def test_m2_non_superiority_is_preserved(verdict, boundary, state):
    assert verdict["terminology_distinctions_preserved"][
        "m2_evaluated_is_not_m2_superiority_established"] is True
    assert boundary["m2_predictive_superiority_claim_supported"] is False
    assert state["stage129_audit_m2_superiority_claim_supported"] is False
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m2_superiority_established"] is False
    # no PR-AUC interval excludes zero, quoted from the committed summary
    delta = _load("project/stage128/m2_incremental_evaluation/"
                  "stage127_m2_paired_bootstrap_delta_summary.json")
    for fam, blob in delta["by_family"].items():
        assert blob["metrics"]["pr_auc"]["ci_excludes_zero"] is False, fam
    ev = _load("project/stage128/m2_incremental_evaluation/"
               "stage127_m2_incremental_evaluation_decision.json")
    assert ev["superiority_claimed"] is False
    assert ev["winner_selected"] is False
    assert ev["families_agree_on_point_estimate_sign"] is False


# --------------------------------- 7. robustness reported, never weaponized
def test_robustness_ordering_is_reported_in_full_without_cherry_picking(
        ordering, boundary, state):
    assert ordering["all_locked_robustness_parts_included"] is True
    assert [p["part"] for p in ordering["robustness_parts"]] == [1, 2, 3, 4, 5, 6]
    assert ordering["cherry_picking_performed"] is False
    assert ordering["used_to_exclude_a_candidate"] is False
    assert ordering["candidate_excluded_on_robustness_grounds"] is False
    assert ordering["promoted_any_robustness_to_primary"] is False
    assert ordering["new_tie_breaker_rule_created"] is False
    assert ordering["new_robustness_executed"] == 0
    assert ordering["values_are_quoted_not_recomputed"] is True
    assert boundary["robustness_used_for_outcome_driven_exclusion"] is False
    assert boundary["robustness_promoted_to_primary"] is False
    assert state["stage129_audit_robustness_used_to_exclude_a_candidate"] is False
    # every candidate stays eligible despite the instability
    assert state["stage129_audit_eligible_candidate_count"] == 6


def test_the_ordering_instability_is_recorded_not_hidden(ordering, state,
                                                         roadmap_front_matter):
    assert ordering["ordering_is_stable_across_all_robustness"] is False
    assert ordering["ordering_instability_reported"] is True
    assert ordering["parts_reversing_primary_ordering"] == [1]
    assert ordering["parts_preserving_primary_ordering"] == [2, 3, 4, 5, 6]
    assert state["stage129_audit_ordering_stable_across_robustness"] is False
    assert state["stage129_audit_parts_reversing_primary_ordering"] == [1]
    assert roadmap_front_matter["final_model_eligibility_audit_ordering_stable"] == "false"
    # Part 1 really does reverse, in the committed artifact
    p1 = _load("project/stage126/stage126_m1_robustness_part1_primary_comparison.json")
    assert p1["observed_ordering_differs_from_primary"] is True
    assert p1["part1_observed_sensitivity_ordering"] == [
        "xgboost", "random_forest", "regularized_logistic_regression"]
    # Part 5 really does invert the top two inside fold 1
    p5 = _load("project/stage126/stage126_m1_robustness_part5_primary_comparison.json")
    fold1 = {k: v["fold1_validation"] for k, v in p5["part5_perfold_pr_auc"].items()}
    assert fold1["random_forest"] > fold1["regularized_logistic_regression"]
    part5 = next(p for p in ordering["robustness_parts"] if p["part"] == 5)
    assert part5["per_fold_top_two_inverted_in_fold1"] is True


# ------------------- 8. selected configuration != selected final algorithm
def test_a_selected_configuration_is_not_a_selected_final_algorithm(
        verdict, boundary):
    assert verdict["terminology_distinctions_preserved"][
        "selected_configuration_per_algorithm_is_not_selected_final_algorithm"] is True
    assert verdict["terminology_distinctions_preserved"][
        "retained_design_is_not_final_model"] is True
    assert verdict["terminology_distinctions_preserved"][
        "best_point_estimate_is_not_paper_winner"] is True
    assert verdict["terminology_distinctions_preserved"][
        "eligible_candidate_is_not_authorized_refit"] is True
    assert verdict["terminology_distinctions_preserved"][
        "development_winner_is_not_final_test_result"] is True
    assert boundary["selected_configuration_treated_as_final_algorithm"] is False
    assert verdict["algorithm_verdict_basis"]["retained_families_count"] == 3


# ------------------------------------------- 9/10. M3, M4, M3-LAG-WDI intact
def test_m3_and_m4_stay_discontinued_and_unexecuted(boundary, state):
    assert boundary["m3_cbi_modeling_executed_or_authorized"] is False
    assert boundary["m4_modeling_executed_or_authorized"] is False
    assert boundary["m3_cbi_disposition_modified_by_this_action"] is False
    assert boundary["m4_disposition_modified_by_this_action"] is False
    assert state["m3_cbi_disposition"] == (
        "M3_CBI_DISCONTINUED_BY_HUMAN_DECISION_UNRESOLVED_DATA_GATE_AND_"
        "UNPROVEN_POINT_IN_TIME")
    assert state["m4_block_disposition"] == (
        "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY")
    assert state["m3_cbi_modeling_will_run"] is False
    assert state["m4_modeling_will_run"] is False
    assert state["m3_modeling_started"] is False
    assert state["m3_macro_data_gate_terminal_status"] == "UNRESOLVED_M3_DATA_GATE"


def test_m3_lag_wdi_stays_supplementary_exploratory(boundary, state):
    assert boundary["m3_lag_wdi_disposition"] == "SUPPLEMENTARY_EXPLORATORY_ONLY"
    assert boundary["m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert boundary["m3_lag_wdi_disposition_modified_by_this_action"] is False
    assert state["stage128_m3_lag_wdi_final_research_disposition"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")
    assert state["stage128_m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert state["stage128_m3_lag_wdi_in_confirmatory_holm_family"] is False


def test_m1_and_m2_scientific_state_is_untouched(boundary, state):
    for field in ("m1_status_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m2_retained_status_modified_by_this_action",
                  "historical_scientific_artifacts_modified_by_this_action",
                  "prior_packages_modified_by_this_action",
                  "existing_pull_requests_modified_by_this_action"):
        assert boundary[field] is False, field
    assert state["m1_robustness_completed"] is True
    assert state["m2_block_retained"] is True
    assert state["stage128_m2_retained_block_human_decision_outcome"] == (
        "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK")


# ------------------------------- 11. the Holm ledger is reconciled, not touched
def test_the_holm_family_keeps_all_three_members_with_null_p_values(
        verdict, boundary, state):
    ledger = verdict["holm_family_ledger"]
    assert ledger["family_members_live"] == HOLM_FAMILY
    assert ledger["family_member_count"] == 3
    assert ledger["family_members_removed_or_renamed_by_this_audit"] is False
    assert ledger["family_shrunk_post_hoc_by_this_audit"] is False
    assert ledger["holm_adjustment_executed_by_this_audit"] is False
    assert ledger["holm_family_complete"] is False
    assert ledger["new_p_values_created_by_this_audit"] == 0
    for member in HOLM_FAMILY:
        assert ledger[member]["p_value"] is None, member
        assert ledger[member]["status"].strip(), member
        src = ledger[member]["source"]
        assert os.path.isfile(os.path.join(REPO_ROOT, src)), member
    assert ledger["M3_CBI_minus_M2"]["status"] == "NOT_EXECUTED_M3_CBI_DISCONTINUED"
    assert ledger["M4_minus_M3_CBI"]["status"] == "NOT_EXECUTED_M4_DISCONTINUED"
    assert boundary["holm_family_complete"] is False
    assert boundary["holm_adjustment_executed"] is False
    assert boundary["holm_family_members_removed_or_renamed"] is False
    assert boundary["holm_family_shrunk_post_hoc"] is False
    assert state["stage129_audit_holm_family"] == HOLM_FAMILY
    assert state["stage129_audit_holm_new_p_values"] == 0
    assert state["holm_family_complete"] is False
    assert state["holm_final_adjustment_deferred"] is True
    # the frozen SAP family is unchanged too
    assert ledger["family_members_frozen_sap"] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
    sap = _load("project/stage125/part4_metrics_uncertainty_contract_stage125.json")
    assert sap["multiplicity"][
        "confirmatory_family_2_adjacent_block_gains_if_admitted"] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]


def test_the_holm_reporting_gap_is_recorded_not_filled(verdict):
    basis = verdict["holm_reporting_verdict_basis"]
    assert basis["contract_specifies_closure_with_unexecuted_members"] is False
    assert os.path.isfile(os.path.join(REPO_ROOT, basis["path"]))
    assert basis["key"] == "multiplicity"
    assert basis["detail"].strip()


# ------------------------------- 12/13/14. nothing selected, opened or unlocked
def test_no_winner_or_final_model_is_selected(boundary, state,
                                              roadmap_front_matter):
    """THE AUDIT selected nothing. Its own action-scoped markers say so and stay
    False forever.

    The live global `paper_winner_selected` is deliberately NOT asserted here.
    The audit's verdicts required a separate human decision, that decision was
    subsequently made (`stage129-final-model-human-selection-governance`), and
    it set the global flag. Pinning the global flag False in the audit's own
    test file would make the audit's finding un-actionable by construction.
    """
    assert boundary["paper_winner_selected"] is False
    assert boundary["final_model_selected"] is False
    assert state["stage129_audit_paper_winner_selected"] is False
    assert state["stage129_audit_final_model_selected"] is False
    assert boundary["audit_determined_candidate_is_not_a_final_selection"] is True
    assert state["stage129_audit_determined_candidate_is_not_a_final_selection"] is True
    # no trained model exists and no endgame step opened, then or since
    assert state["final_model_selected"] is False
    # ACTION-SCOPED: the audit fitted nothing. Its own boundary says so.
    assert boundary["full_development_refit_executed"] is False
    assert roadmap_front_matter["final_model_selected"] == "false"


def test_no_refit_stage130_or_final_test_is_executed_or_authorized(
        boundary, state, roadmap_front_matter):
    for field in ("full_development_refit_executed", "stage130_started",
                  "stage130_or_next_stage_executed", "final_test_access_authorized",
                  "next_research_action_authorized", "next_action_authorized",
                  "next_action_executes_refit", "next_action_executes_final_test",
                  "merge_authorized", "ready_for_review_authorized"):
        assert boundary[field] is False, field
    # ACTION-SCOPED above; the still-true global facts below.
    assert state["next_research_action_authorized"] is False
    # MOVED from a live global proxy to an action-scoped historical fact.
    # `stage130_started` is now True in the live Handoff, because the
    # Stage130 Phase 1 manuscript evidence package exists. That happened
    # AFTER this action, and Phase 1 is PRESENTATION only. What this
    # action guarantees -- that no Stage130 SCIENTIFIC execution has
    # begun -- is asserted here instead, and its own artifacts above
    # still pin `stage130_started = False` for its own moment.
    assert state["stage130_scientific_execution_started"] is False
    # MOVED from a live global proxy to an action-scoped historical fact. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this audit. What this
    # audit guarantees is that IT read nothing, which its own scoped marker
    # records permanently; the snapshot pins the firewall state it ran under.
    assert state["stage129_audit_final_test_rows_read"] == 0
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    # And the live surface must still refuse a second pass.
    assert state["final_test_access_authorized"] is False
    assert state["final_test_second_pass_authorized"] is False
    # MOVED, as above: the live ROADMAP front matter now records the
    # started Stage130 PRESENTATION phase, so the scientific pointer is
    # what this action guarantees.
    assert roadmap_front_matter[
        "stage130_scientific_execution_started"] == "false"
    assert roadmap_front_matter["next_research_action_authorized"] == "false"


def test_final_test_stays_locked_with_zero_rows_read(boundary, state):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_target_values_read"] == 0
    assert boundary["counters"]["final_test_predictor_values_read"] == 0
    assert state["final_test_locked"] is True
    # MOVED from a live global proxy to the action-scoped historical fact, as
    # above: the audit's own zero, plus the pre-pass firewall snapshot.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_audit_final_test_locked"] is True
    assert state["stage129_audit_final_test_rows_read"] == 0


def test_the_pointer_matches_the_verdict_and_names_no_execution(
        verdict, boundary, state, roadmap_front_matter):
    assert verdict["next_action_id"] == "human_decision_required"
    assert verdict["next_action_authorized"] is False
    assert boundary["next_action_id"] == "human_decision_required"
    assert boundary["pointer_is_not_authorization"] is True
    assert state["stage129_audit_next_action_id"] == "human_decision_required"
    assert state["stage129_audit_next_action_authorized"] is False
    assert roadmap_front_matter[
        "final_model_eligibility_audit_next_action_id"] == "human_decision_required"
    for bad in ("refit", "final_test", "final-test", "stage130", "retune",
                "bootstrap", "shap"):
        assert bad not in verdict["next_action_id"].lower(), bad
        assert bad not in boundary["next_action_id"].lower(), bad


# ------------------------------------------- 15. the generator fails closed
def _run_generator(root):
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_final_model_eligibility_audit_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A minimal tree with the audit package and every artifact it cites."""
    (tmp_path / _PKG_REL).mkdir(parents=True, exist_ok=True)
    for name in os.listdir(_PKG):
        with open(os.path.join(_PKG, name), "rb") as fh:
            (tmp_path / _PKG_REL / name).write_bytes(fh.read())
    for rel in ("project/stage126/stage126_m1_robustness_closure_synthesis_record.json",
                "project/stage126/stage126_m1_retained_design_freeze.json",
                "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
                "project/stage128/m2_retained_block_human_decision/"
                "stage128_m2_retained_block_human_decision.json",
                "project/stage129/m3_cbi_human_discontinuation_and_reporting/"
                "stage129_m3_cbi_human_discontinuation_decision.json",
                "project/stage129/m4_human_discontinuation_data_inadequacy/"
                "stage129_m4_human_discontinuation_governance_boundary.json",
                "project/stage128/m2_incremental_evaluation/"
                "stage127_m2_multiplicity_family_status.json",
                "project/stage129/m3_cbi_human_discontinuation_and_reporting/"
                "stage129_m3_cbi_confirmatory_comparison_record.json"):
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
    assert markers["stage129_final_block_verdict"] == (
        "FINAL_BLOCK_REQUIRES_HUMAN_DECISION")
    assert markers["stage129_final_algorithm_verdict"] == (
        "FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION")


@pytest.mark.parametrize("rel,key,value,needle", [
    # a verdict outside the locked vocabulary
    (_VERDICT_REL, "block_verdict", "M1_WINS", "vocabulary"),
    (_VERDICT_REL, "algorithm_verdict", "LOGISTIC_WINS", "vocabulary"),
    (_VERDICT_REL, "holm_reporting_verdict", "HOLM_DONE", "vocabulary"),
    # claiming uniqueness without the proof burden
    (_VERDICT_REL, "block_verdict", "UNIQUE_FINAL_BLOCK_DETERMINED_BY_FROZEN_RULE",
     "deterministic_rule_found"),
    (_VERDICT_REL, "algorithm_verdict",
     "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE", "deterministic_rule_found"),
    # smuggling a winner into a non-unique verdict
    (_VERDICT_REL, "audit_determined_candidate", "M1/regularized_logistic_regression",
     "determined candidate"),
    # selecting a winner, a final model or opening the endgame
    (_BOUNDARY_REL, "paper_winner_selected", True, "paper_winner_selected"),
    (_BOUNDARY_REL, "final_model_selected", True, "final_model_selected"),
    (_BOUNDARY_REL, "full_development_refit_executed", True, "refit"),
    (_BOUNDARY_REL, "stage130_started", True, "stage130"),
    (_BOUNDARY_REL, "next_action_executes_refit", True, "refit"),
    (_BOUNDARY_REL, "next_action_executes_final_test", True, "final_test"),
    # unlocking or reading the Final Test
    (_BOUNDARY_REL, "final_test_locked", False, "Final Test locked"),
    (_BOUNDARY_REL, "final_test_rows_read", 3, "final_test_rows_read"),
    (_BOUNDARY_REL, "final_test_access_authorized", True, "final_test_access"),
    # fabricating a p-value or closing / shrinking the Holm family
    (_BOUNDARY_REL, "new_p_value_created", True, "new_p_value_created"),
    (_BOUNDARY_REL, "holm_family_complete", True, "holm_family_complete"),
    (_BOUNDARY_REL, "holm_adjustment_executed", True, "holm_adjustment_executed"),
    (_BOUNDARY_REL, "holm_family_members_removed_or_renamed", True,
     "holm_family_members_removed_or_renamed"),
    (_BOUNDARY_REL, "holm_family_shrunk_post_hoc", True,
     "holm_family_shrunk_post_hoc"),
    # turning the audit into an execution
    (_BOUNDARY_REL, "audit_read_only", False, "read-only"),
    (_VERDICT_REL, "audit_recomputed_any_metric", True, "audit_recomputed_any_metric"),
    (_VERDICT_REL, "audit_performed_row_level_analysis", True, "row_level"),
    (_BOUNDARY_REL, "new_metric_computed_from_row_level_data", True, "new_metric"),
    (_BOUNDARY_REL, "new_tie_breaker_rule_created", True, "tie_breaker"),
    # collapsing the terminology distinctions
    (_BOUNDARY_REL, "m2_retention_treated_as_final_selection", True, "M2 retention"),
    (_BOUNDARY_REL, "selected_configuration_treated_as_final_algorithm", True,
     "selected configuration"),
    (_BOUNDARY_REL, "m2_predictive_superiority_claim_supported", True, "superiority"),
    # promoting the supplementary block or editing history
    (_BOUNDARY_REL, "m3_lag_wdi_promoted_to_confirmatory_model", True, "promoted"),
    (_BOUNDARY_REL, "m3_lag_wdi_disposition", "CONFIRMATORY_M3", "SUPPLEMENTARY"),
    (_BOUNDARY_REL, "historical_scientific_artifacts_modified_by_this_action", True,
     "historical_scientific_artifacts"),
    (_BOUNDARY_REL, "m3_cbi_modeling_executed_or_authorized", True, "m3_cbi_modeling"),
    (_BOUNDARY_REL, "m4_modeling_executed_or_authorized", True, "m4_modeling"),
    # weaponizing robustness
    (_ORDERING_REL, "used_to_exclude_a_candidate", True, "used_to_exclude"),
    (_ORDERING_REL, "cherry_picking_performed", True, "cherry_picking"),
    (_ORDERING_REL, "promoted_any_robustness_to_primary", True, "promoted"),
    (_ORDERING_REL, "new_robustness_executed", 2, "new robustness"),
    (_ORDERING_REL, "all_locked_robustness_parts_included", False, "robustness part"),
    # breaking the matrix shape
    (_MATRIX_REL, "algorithms_audited", ["regularized_logistic_regression"],
     "three frozen algorithms"),
    (_MATRIX_REL, "candidate_count", 5, "candidate_count"),
    (_MATRIX_REL, "eligibility_is_not_selection", False, "eligibility is not selection"),
    (_MATRIX_REL, "no_candidate_declared_winner_on_point_estimate", False,
     "no_candidate_declared_winner"),
    # moving the pointer somewhere it may not go
    (_VERDICT_REL, "next_action_id", "stage130-final-model-refit", "next_action_id"),
    (_VERDICT_REL, "next_action_authorized", True, "next_action_authorized"),
])
def test_the_generator_fails_closed_on_tampering(sandbox, rel, key, value, needle):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob[key] = value
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


def test_a_unique_verdict_needs_a_rule_file_that_actually_exists(sandbox):
    """The strongest forgery: claim uniqueness AND supply a full-looking rule
    citation whose file does not exist."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    blob["algorithm_verdict"] = "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE"
    blob["algorithm_verdict_basis"]["deterministic_rule_found"] = True
    blob["algorithm_verdict_basis"]["audit_determined_candidate"] = (
        "M1/regularized_logistic_regression")
    blob["algorithm_verdict_basis"]["determining_rule"] = {
        "path": "project/stage125/this_rule_does_not_exist.json",
        "key": "model_selection.rule",
        "binding_phrase": "select the highest PR-AUC",
        "deterministic_proof": "logistic has the highest pooled PR-AUC",
    }
    _write(str(sandbox), _VERDICT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "does not exist" in str(exc.value)


def test_a_unique_verdict_needs_a_deterministic_proof(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    blob["algorithm_verdict"] = "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE"
    blob["algorithm_verdict_basis"]["deterministic_rule_found"] = True
    blob["algorithm_verdict_basis"]["audit_determined_candidate"] = (
        "M1/regularized_logistic_regression")
    blob["algorithm_verdict_basis"]["determining_rule"] = {
        "path": "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
        "key": "primary_metric",
        "binding_phrase": "PR-AUC",
        "deterministic_proof": None,
    }
    _write(str(sandbox), _VERDICT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "deterministic_proof" in str(exc.value)


def test_a_candidate_may_not_cite_a_selection_rule_under_a_non_unique_verdict(
        sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _MATRIX_REL).read_text(encoding="utf-8"))
    blob["candidates"][0]["selection_rule_source"] = (
        "project/stage125/part4_metrics_uncertainty_contract_stage125.json#primary_metric")
    _write(str(sandbox), _MATRIX_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "selection rule" in str(exc.value).lower()


def test_the_matrix_may_not_drop_or_duplicate_a_candidate(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _MATRIX_REL).read_text(encoding="utf-8"))
    blob["candidates"] = blob["candidates"][:-1]
    blob["candidate_count"] = 5
    _write(str(sandbox), _MATRIX_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "cover exactly" in str(exc.value)


def test_the_holm_ledger_may_not_gain_a_p_value_or_lose_a_member(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    blob["holm_family_ledger"]["M2_minus_M1"]["p_value"] = 0.04
    _write(str(sandbox), _VERDICT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "p_value must stay null" in str(exc.value)

    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    blob["holm_family_ledger"]["M2_minus_M1"]["p_value"] = None
    blob["holm_family_ledger"]["family_members_live"] = [
        "M2_minus_M1", "M3_CBI_minus_M2"]
    _write(str(sandbox), _VERDICT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "confirmatory Holm family" in str(exc.value)


def test_a_counter_above_zero_fails_the_build(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _BOUNDARY_REL).read_text(encoding="utf-8"))
    blob["counters"]["model_fits"] = 1
    _write(str(sandbox), _BOUNDARY_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "model_fits" in str(exc.value)


def test_both_unique_verdicts_still_may_not_point_at_execution(sandbox):
    """Even if the frozen rules DID determine both uniquely, the pointer may
    only ever be a human authorization step."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    rule = {
        "path": "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
        "key": "primary_metric",
        "binding_phrase": "PR-AUC",
        "deterministic_proof": "hypothetical",
    }
    blob["block_verdict"] = "UNIQUE_FINAL_BLOCK_DETERMINED_BY_FROZEN_RULE"
    blob["block_verdict_basis"]["deterministic_rule_found"] = True
    blob["block_verdict_basis"]["audit_determined_candidate"] = "M1"
    blob["block_verdict_basis"]["determining_rule"] = rule
    blob["algorithm_verdict"] = "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE"
    blob["algorithm_verdict_basis"]["deterministic_rule_found"] = True
    blob["algorithm_verdict_basis"]["audit_determined_candidate"] = (
        "regularized_logistic_regression")
    blob["algorithm_verdict_basis"]["determining_rule"] = rule
    _write(str(sandbox), _VERDICT_REL, blob)
    # the pointer is still human_decision_required, which is now WRONG for the
    # both-unique case -- the generator must demand the authorization pointer
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "human_authorization_required_for_final_model_selection" in str(exc.value)


def test_a_contract_conflict_verdict_demands_the_methods_pointer(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _VERDICT_REL).read_text(encoding="utf-8"))
    blob["block_verdict"] = "CONTRACT_CONFLICT_PREVENTS_BLOCK_DETERMINATION"
    _write(str(sandbox), _VERDICT_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "human_methods_decision_required" in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _VERDICT_REL)
    assert _run_generator(str(sandbox)) == {}


# ------------------------------- 16. validator + semantic idempotency
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage129_final_model_eligibility_audit_markers(REPO_ROOT)
    second = gen.derive_stage129_final_model_eligibility_audit_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["stage129_final_block_verdict"] == (
        "FINAL_BLOCK_REQUIRES_HUMAN_DECISION")


def test_current_state_renders_the_audit_without_naming_a_winner():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert "final development model eligibility audit" in text.lower()
    assert "FINAL_BLOCK_REQUIRES_HUMAN_DECISION" in text
    assert "FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION" in text
    assert HOLM_REPORTING_VERDICT in text
    for forged in ("UNIQUE_FINAL_BLOCK_DETERMINED_BY_FROZEN_RULE",
                   "UNIQUE_FINAL_ALGORITHM_DETERMINED_BY_FROZEN_RULE"):
        assert forged not in text, forged


def test_roadmap_records_the_audit_without_opening_a_new_stage(
        roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["final_model_eligibility_audit_action_id"] == ACTION_ID
    assert fm["final_model_eligibility_audit_is_read_only"] == "true"
    assert fm["holm_reporting_verdict"] == HOLM_REPORTING_VERDICT
    assert fm["final_model_eligibility_audit_candidate_count"] == "6"
    assert fm["final_model_eligibility_audit_next_action_authorized"] == "false"
    # no live pointer chain moves
    assert fm["next_research_action_id"] == "human-dataset-release-candidate-digest-review"
    assert fm["m3_cbi_next_action_id"] == "human_decision_required"
    assert fm["m4_next_action_id"] == "human_decision_required"
    assert fm["m3_lag_wdi_next_action_id"] == "human_decision_required"
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert "FINAL_BLOCK_REQUIRES_HUMAN_DECISION" in body


# --------------------------------------------------------- package hygiene
def test_no_new_data_or_metric_artifact_was_created():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_final_development_model_eligibility_audit.json")
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["new_metric_files_committed"] == 0
    assert manifest["paper_winner_selected"] is False
    assert manifest["final_model_selected"] is False


def test_package_hash_manifest_matches_every_file():
    import hashlib
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_final_development_model_eligibility_audit.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
