"""Tests — Stage128 Track B step E: the M3-LAG-WDI EXPLORATORY INCREMENTAL
EVALUATION.

Step E is the first Track B action that fits a model, so it is the first one
whose RESULT could be misread as changing the paper. These tests police that,
not the numbers themselves.

The interesting tests are the ones that try to promote the result: move E1
into the confirmatory Holm family, publish a superiority claim, select a
winner, mark a data limitation resolved because the numbers came out well, or
evaluate the two blocks on quietly different samples. Every one of those must
be rejected by the generator and by the independent current-state validator —
and must stay rejected regardless of whether E1 was positive, negative or
null, which is exactly why they are asserted as rules rather than against the
observed outcome.
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
from src import stage126_current_state_validator as val  # noqa: E402
from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_incremental_evaluation as m)

_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_incremental_evaluation"
_DECISION_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_decision.json"
_BOUNDARY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_governance_boundary.json")
_AUDIT_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_execution_audit.json"
_SAMPLE_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_common_sample_audit.json")
_FITS_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_predictive_fit_count_audit"
    ".json")
_MULTIPLICITY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_multiplicity_family_status"
    ".json")
_BOOTSTRAP_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_paired_bootstrap_delta_summary"
    ".json")
_MANIFEST_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_feature_configuration_manifest"
    ".json")
_QC_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_qc_report.json"
_AUTH_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_human_authorization_record"
    ".json")


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _read_json(_DECISION_REL)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


@pytest.fixture(scope="module")
def audit() -> dict:
    return _read_json(_AUDIT_REL)


@pytest.fixture(scope="module")
def sample() -> dict:
    return _read_json(_SAMPLE_REL)


@pytest.fixture(scope="module")
def fits() -> dict:
    return _read_json(_FITS_REL)


@pytest.fixture(scope="module")
def multiplicity() -> dict:
    return _read_json(_MULTIPLICITY_REL)


@pytest.fixture(scope="module")
def handoff() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


@pytest.fixture(scope="module")
def markers() -> dict:
    return gen.derive_stage128_m3_lag_wdi_incremental_evaluation_markers(
        REPO_ROOT)


# --------------------------------------------------------------------------- #
# The package exists and is what it says it is
# --------------------------------------------------------------------------- #

def test_action_identity(decision):
    assert decision["action_id"] == m.ACTION_ID
    assert decision["authorized_scope"] == "exploratory_incremental_evaluation_only"


def test_authorization_is_single_use_and_narrow():
    auth = _read_json(_AUTH_REL)
    assert auth["authorization_is_single_use"] is True
    assert auth["standing_authorization"] is False
    assert auth["prior_authorizations_reused"] is False
    for field in ("authorization_covers_final_test",
                  "authorization_covers_final_test_unlock",
                  "authorization_covers_new_retrieval",
                  "authorization_covers_step_c_rerun",
                  "authorization_covers_step_d_rerun",
                  "authorization_covers_calendar_mapping_change",
                  "authorization_covers_retuning",
                  "authorization_covers_feature_search",
                  "authorization_covers_new_scientific_design_choice",
                  "authorization_covers_confirmatory_holm",
                  "authorization_covers_paper_winner_selection",
                  "authorization_covers_m4",
                  "authorization_covers_ready_for_review",
                  "authorization_covers_merge"):
        assert auth[field] is False, field


def test_every_prior_track_b_authorization_is_named_as_not_reused():
    auth = _read_json(_AUTH_REL)
    assert set(auth["prior_authorizations_not_reused"]) == set(
        m.NON_REUSABLE_PRIOR_AUTHORIZATIONS)


def test_qc_passes():
    qc = _read_json(_QC_REL)
    assert qc["failed"] == 0
    assert qc["all_pass"] is True
    assert qc["assertions"] > 0


# --------------------------------------------------------------------------- #
# One sample, two nested blocks, 12 versus 14
# --------------------------------------------------------------------------- #

def test_both_blocks_share_one_identical_sample(sample):
    assert sample["identical_sample_for_both_blocks"] is True
    assert sample["composition"]["rows"] == 539
    assert sample["composition"]["positive"] == 55
    assert sample["composition"]["negative"] == 484
    assert sample["composition"]["companies"] == 108


def test_no_exclusions_outside_the_frozen_complete_case_rule(sample):
    attrition = sample["attrition_from_parent"]
    assert attrition["dropped_rows"] == 0
    assert attrition["exclusions_outside_the_frozen_complete_case_rule"] == 0
    assert attrition["imputation_used"] is False
    assert attrition["feature_substitution_used"] is False


def test_feature_architecture_is_exactly_12_versus_14(fits):
    assert fits["feature_counts_by_block"]["M2"] == [12]
    assert fits["feature_counts_by_block"]["M3_LAG_WDI"] == [14]
    assert fits["primary_predictive_fits"] == 44
    assert fits["tuning_fits"] == 0
    assert fits["grid_search_fits"] == 0
    assert fits["final_test_fits"] == 0


def test_m2_is_nested_in_the_exploratory_block():
    assert m.M3_LAG_WDI_FEATURE_ORDER[:12] == m.M2_FEATURE_ORDER
    assert m.M3_LAG_WDI_FEATURE_ORDER[12:] == m.WDI_FEATURE_ORDER
    assert len(m.WDI_FEATURE_ORDER) == 2


def test_exactly_the_two_admitted_indicators_and_no_third():
    manifest = _read_json(_MANIFEST_REL)
    codes = [f["indicator_code"] for f in manifest["wdi_features"]]
    assert codes == ["FP.CPI.TOTL.ZG", "PA.NUS.FCRF"]
    assert manifest["feature_search_executed"] is False
    assert manifest["feature_selection_executed"] is False
    assert manifest["retuning_executed"] is False


def test_calendar_mapping_is_the_locked_plus_621(sample):
    assert sample["calendar_mapping_rule"] == "jalali_fiscal_year_t_plus_621"
    assert m.LOCKED_CALENDAR_OFFSET == 621
    assert m.REJECTED_CALENDAR_OFFSET == 622
    assert sample["predictor_year_first"] == 2013
    assert sample["predictor_year_last"] == 2019


def test_no_same_year_t_observation_was_read(sample):
    assert sample["same_year_t_observations_read"] == 0
    assert sample["cpi_observation_year_rule"] == "t-1"
    assert sample["cpi_observation_year_last"] == sample[
        "predictor_year_last"] - 1
    assert sample["fx_observation_year_numerator_last"] == sample[
        "predictor_year_last"] - 1


def test_the_two_features_carry_no_missing_values(sample):
    missing = sample["missingness_after_construction"]
    assert missing["new_wdi_feature_missing_values"] == 0
    assert missing["complete_case_violations"] == 0
    assert missing["new_imputation_introduced_by_this_action"] is False


def test_m1_missingness_is_reported_as_pre_existing_not_hidden(sample):
    """The nine M1 features carry pre-existing missingness the frozen
    preprocessor handles. Reporting it as zero would be a false claim; treating
    it as a step E imputation would be an equally false one."""
    missing = sample["missingness_after_construction"]
    assert missing["m1_pre_existing_missing_values"] > 0
    assert missing[
        "m1_missingness_is_pre_existing_and_identical_for_both_blocks"] is True
    assert missing["m1_missingness_introduced_by_this_action"] is False


def test_macro_features_are_constant_within_a_predictor_year(sample):
    years = len(sample["predictor_years"])
    for feature, distinct in sample["wdi_distinct_values"].items():
        assert distinct <= years, feature


# --------------------------------------------------------------------------- #
# The comparator was refit, not imported
# --------------------------------------------------------------------------- #

def test_comparator_was_refit_and_reconciled_against_the_committed_m2():
    """The published M2 numbers are not the comparator; the refit is. Because
    the sample is identical they must agree — and if they ever stopped
    agreeing, the two actions would no longer be evaluating the same thing."""
    metrics_path = os.path.join(
        REPO_ROOT, _PKG_REL,
        "stage128_m3_lag_wdi_evaluation_block_model_metrics.csv")
    committed_path = os.path.join(
        REPO_ROOT, "project/stage128/m2_incremental_evaluation",
        "stage127_m2_block_model_metrics.csv")
    import csv
    with open(metrics_path, encoding="utf-8", newline="") as fh:
        step_e = {(r["model_family"], r["scope"]): r
                  for r in csv.DictReader(fh) if r["block"] == "M2"}
    with open(committed_path, encoding="utf-8", newline="") as fh:
        retained = {(r["model_family"], r["scope"]): r
                    for r in csv.DictReader(fh) if r["block"] == "M2"}
    assert step_e and retained
    for key, row in step_e.items():
        for metric in m.ALL_METRICS:
            assert float(row[metric]) == float(retained[key][metric]), (
                key, metric)


# --------------------------------------------------------------------------- #
# The result stayed exploratory — the checks that matter most
# --------------------------------------------------------------------------- #

def test_e1_lives_in_the_exploratory_family_only(multiplicity):
    assert multiplicity["exploratory_family_id"] == (
        "M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY")
    assert multiplicity["exploratory_family_members"] == ["E1"]
    assert multiplicity[
        "exploratory_comparison_inserted_into_confirmatory_family"] is False
    assert multiplicity["e1_is_confirmatory"] is False


def test_confirmatory_holm_family_is_untouched(multiplicity):
    assert multiplicity["confirmatory_holm_family"] == [
        "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
    assert multiplicity["confirmatory_holm_family_changed_by_this_action"] is False
    assert multiplicity["confirmatory_holm_executed_by_this_action"] is False
    assert multiplicity["confirmatory_holm_modified_by_this_action"] is False


def test_no_confirmatory_claim_and_no_winner(decision, multiplicity):
    assert decision["confirmatory_superiority_claim_made"] is False
    assert decision["confirmatory_conclusions_changed"] is False
    assert decision["paper_winner_selected"] is False
    assert decision["block_promoted_to_confirmatory"] is False
    assert multiplicity[
        "main_confirmatory_conclusion_changed_by_this_action"] is False
    assert decision["results_label"] == (
        "supplementary_exploratory_robustness_only")


def test_the_scientific_role_did_not_move(decision, boundary):
    assert decision["scientific_role"] == (
        "supplementary_exploratory_robustness_block")
    for field in ("m3_lag_wdi_is_confirmatory_m3",
                  "m3_lag_wdi_replaces_m3_cbi",
                  "m3_lag_wdi_repairs_m3_cbi",
                  "m3_lag_wdi_replaces_m3i2",
                  "m3_lag_wdi_is_historical_vintage_wdi",
                  "m3_lag_wdi_is_real_time_wdi",
                  "m3_lag_wdi_in_confirmatory_holm_family",
                  "m3_lag_wdi_can_select_paper_winner"):
        assert boundary[field] is False, field


# --------------------------------------------------------------------------- #
# Nothing moved because of what the result showed
# --------------------------------------------------------------------------- #

def test_every_forbidden_counter_is_zero(audit):
    for counter in gen._STAGE128_M3_LAG_EVAL_ZERO_COUNTERS:
        assert audit[counter] == 0, counter


def test_no_upstream_artifact_was_mutated(audit):
    for field in ("retained_bytes_modified", "deposited_evidence_modified",
                  "step_c_artifacts_modified", "step_d_artifacts_modified",
                  "calendar_lock_artifacts_modified",
                  "authoritative_contract_edited",
                  "confirmatory_holm_state_modified"):
        assert audit[field] is False, field


def test_no_method_surface_moved(boundary):
    for field in ("retuning_executed", "grid_search_executed",
                  "model_family_search_executed", "feature_search_executed",
                  "feature_substitution_executed", "imputation_executed",
                  "metric_definition_changed",
                  "validation_architecture_changed", "seed_policy_changed",
                  "thresholds_changed", "shap_executed"):
        assert boundary[field] is False, field


def test_shap_was_not_run_because_the_contract_does_not_require_it():
    """SHAP runs only if the frozen contract explicitly requires it. It does
    not, so there must be no SHAP code path at all."""
    src = open(os.path.join(REPO_ROOT, m.SRC_REL), encoding="utf-8").read()
    assert "import shap" not in src
    assert "shap_required_by_frozen_contract" in src


def test_the_bootstrap_seed_was_not_changed_after_seeing_results():
    bootstrap = _read_json(_BOOTSTRAP_REL)
    assert bootstrap["seed"] == m.BOOTSTRAP_SEED == 20260724
    assert bootstrap["replicates_attempted"] == 2000
    assert bootstrap["seed_changed_after_seeing_results"] is False
    assert bootstrap["models_refit_during_bootstrap"] is False
    assert bootstrap["same_resampled_rows_for_both_blocks"] is True
    for entry in bootstrap["by_family"].values():
        assert entry["minimum_valid_replicates_met"] is True


# --------------------------------------------------------------------------- #
# Limitations survive whatever the numbers said
# --------------------------------------------------------------------------- #

def test_no_limitation_was_resolved_or_erased_by_the_result(decision):
    limitations = decision["limitations"]
    assert limitations
    for item in limitations:
        assert item["resolved_by_this_action"] is False, item["id"]
        assert item["erased_by_a_favourable_predictive_result"] is False, (
            item["id"])


def test_the_four_mandated_data_limitations_are_preserved(decision):
    ids = {item["id"] for item in decision["limitations"]}
    for required in ("point_in_time_wdi_availability_unproven",
                     "lagging_does_not_create_point_in_time_data",
                     "fx_degenerate_2021_2024", "fx_missing_2024_2025"):
        assert required in ids, required


def test_point_in_time_availability_is_not_claimed(boundary, handoff):
    assert boundary["m3_lag_wdi_point_in_time_availability_proven"] is False
    assert handoff["stage128_m3_lag_wdi_point_in_time_availability_claimed"] \
        is False


# --------------------------------------------------------------------------- #
# Hard locks
# --------------------------------------------------------------------------- #

def test_final_test_was_never_opened(boundary, audit):
    firewall = _read_json(
        f"{_PKG_REL}/stage128_m3_lag_wdi_evaluation_final_test_firewall_audit"
        ".json")
    assert firewall["final_test_rows_read"] == 0
    assert firewall["final_test_predictor_values_read"] == 0
    assert firewall["final_test_target_values_read"] == 0
    assert firewall["final_test_locked"] is True
    assert firewall["firewall_intact"] is True
    assert boundary["final_test_rows_read"] == 0
    assert audit["final_test_rows_read"] == 0


def test_nothing_downstream_is_authorized(decision, boundary):
    assert decision["next_action_authorized"] is False
    assert decision["authorizes_next_action"] is False
    assert boundary["merge_authorized"] is False
    assert boundary["ready_for_review_authorized"] is False
    assert boundary["m4_authorized"] is False
    assert boundary["m3_lag_wdi_next_action_authorized"] is False
    assert boundary["next_action_requires_new_explicit_human_decision"] is True


def test_the_step_e_authorization_is_consumed_never_standing(boundary):
    assert boundary["m3_lag_wdi_modeling_authorization_consumed"] is True
    assert boundary["m3_lag_wdi_modeling_authorized_now"] is False
    assert boundary["m3_lag_wdi_modeling_authorization_reusable"] is False


def test_no_prior_one_time_authorization_reads_as_standing(boundary):
    for field in ("retrieval_authorized_now",
                  "post_retrieval_audit_authorized_now",
                  "data_gate_authorized_now",
                  "calendar_mapping_lock_authorized_now",
                  "prior_authorization_reused_by_this_action"):
        assert boundary[field] is False, field


# --------------------------------------------------------------------------- #
# The published Handoff state
# --------------------------------------------------------------------------- #

def test_handoff_publishes_modeling_as_started_and_consumed(handoff):
    assert handoff["stage128_m3_lag_wdi_modeling_started"] is True
    assert handoff["stage128_m3_lag_wdi_modeling_executed"] is True
    assert handoff["stage128_m3_lag_wdi_modeling_was_authorized"] is True
    # STANDING permission — False before step E and False after it.
    assert handoff["stage128_m3_lag_wdi_modeling_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_modeling_authorized_now"] is False
    assert handoff[
        "stage128_m3_lag_wdi_modeling_authorization_consumed"] is True
    assert handoff[
        "stage128_m3_lag_wdi_modeling_authorization_reusable"] is False


def test_modeling_started_is_derived_not_hard_coded():
    """The generator must not publish a moment as if it were a rule. Every
    step before E hard-coded `modeling_started: False`; that must now come
    from the presence of step E's own package."""
    src = open(os.path.join(REPO_ROOT, "project/scripts/update_ai_handoff.py"),
               encoding="utf-8").read()
    assert '"stage128_m3_lag_wdi_modeling_started": False' not in src
    assert "_stage128_m3_lag_modeling_started(root)" in src


def test_handoff_pointer_names_no_next_action(handoff):
    assert handoff["stage128_m3_lag_wdi_next_action_id"] == (
        "human_decision_required")
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_next_action_scope"] == (
        "no_further_action_is_authorized")


def test_handoff_keeps_the_result_out_of_the_confirmatory_family(handoff):
    assert handoff["stage128_m3_lag_wdi_in_confirmatory_holm_family"] is False
    assert handoff["stage128_m3_lag_wdi_confirmatory_holm_family_changed"] \
        is False
    assert handoff["stage128_m3_lag_wdi_confirmatory_holm_executed"] is False
    assert handoff[
        "stage128_m3_lag_wdi_confirmatory_superiority_claim_made"] is False
    assert handoff["stage128_m3_lag_wdi_paper_winner_selected"] is False


def test_pr_79_stays_a_draft(handoff):
    assert handoff["stage128_m3i2_live_pr_number"] == 79
    assert handoff["stage128_m3i2_live_pr_is_draft"] is True
    assert handoff["stage128_m3i2_live_pr_merged"] is False
    assert handoff["stage128_m3i2_live_pr_ready_for_review_authorized"] \
        is False


# --------------------------------------------------------------------------- #
# Tamper tests — the generator must reject a promoted result
# --------------------------------------------------------------------------- #

def _tampered(monkeypatch, rel: str, mutate) -> None:
    """Serve a mutated copy of one artifact to the generator."""
    original = gen._require_json_artifact

    def fake(root: str, path: str):
        payload = original(root, path)
        if path == rel:
            payload = copy.deepcopy(payload)
            mutate(payload)
        return payload

    monkeypatch.setattr(gen, "_require_json_artifact", fake)


@pytest.mark.parametrize("label,rel,mutate", [
    ("e1_moved_into_the_confirmatory_family", _MULTIPLICITY_REL,
     lambda p: p.update(
         exploratory_comparison_inserted_into_confirmatory_family=True)),
    ("confirmatory_holm_family_changed", _MULTIPLICITY_REL,
     lambda p: p.update(confirmatory_holm_family_changed_by_this_action=True)),
    ("confirmatory_holm_executed", _MULTIPLICITY_REL,
     lambda p: p.update(confirmatory_holm_executed_by_this_action=True)),
    ("holm_family_membership_rewritten", _MULTIPLICITY_REL,
     lambda p: p.update(confirmatory_holm_family=[
         "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI", "E1"])),
    ("superiority_claim_published", _MULTIPLICITY_REL,
     lambda p: p.update(confirmatory_superiority_claim_made=True)),
    ("paper_winner_selected", _MULTIPLICITY_REL,
     lambda p: p.update(paper_winner_selected_by_this_action=True)),
    ("e1_declared_confirmatory", _MULTIPLICITY_REL,
     lambda p: p.update(e1_is_confirmatory=True)),
    ("decision_claims_superiority", _DECISION_REL,
     lambda p: p.update(confirmatory_superiority_claim_made=True)),
    ("decision_changes_conclusions", _DECISION_REL,
     lambda p: p.update(confirmatory_conclusions_changed=True)),
    ("decision_promotes_the_block", _DECISION_REL,
     lambda p: p.update(block_promoted_to_confirmatory=True)),
    ("decision_authorizes_a_next_action", _DECISION_REL,
     lambda p: p.update(next_action_authorized=True)),
    ("scientific_role_changed", _DECISION_REL,
     lambda p: p.update(scientific_role="confirmatory_m3")),
    ("results_relabelled_as_confirmatory", _DECISION_REL,
     lambda p: p.update(results_label="confirmatory")),
    ("limitation_marked_resolved", _DECISION_REL,
     lambda p: p["limitations"][0].update(resolved_by_this_action=True)),
    ("limitation_erased_by_a_good_result", _DECISION_REL,
     lambda p: p["limitations"][0].update(
         erased_by_a_favourable_predictive_result=True)),
    ("limitations_emptied", _DECISION_REL,
     lambda p: p.update(limitations=[])),
    ("point_in_time_limitation_dropped", _DECISION_REL,
     lambda p: p.update(limitations=[
         item for item in p["limitations"]
         if item["id"] != "point_in_time_wdi_availability_unproven"])),
    ("different_samples_for_the_two_blocks", _SAMPLE_REL,
     lambda p: p.update(identical_sample_for_both_blocks=False)),
    ("sample_size_changed", _SAMPLE_REL,
     lambda p: p["composition"].update(rows=500)),
    ("rows_excluded_outside_the_frozen_rule", _SAMPLE_REL,
     lambda p: p["attrition_from_parent"].update(
         exclusions_outside_the_frozen_complete_case_rule=3)),
    ("calendar_mapping_swapped_to_622", _SAMPLE_REL,
     lambda p: p.update(calendar_mapping_rule="jalali_fiscal_year_t_plus_622",
                        calendar_mapping_locked_offset=622)),
    ("same_year_t_observation_read", _SAMPLE_REL,
     lambda p: p.update(same_year_t_observations_read=1)),
    ("final_test_row_in_the_sample", _SAMPLE_REL,
     lambda p: p.update(final_test_rows_in_sample=1)),
    ("fit_count_changed", _FITS_REL,
     lambda p: p.update(primary_predictive_fits=48)),
    ("comparator_given_extra_features", _FITS_REL,
     lambda p: p["feature_counts_by_block"].update(M2=[14])),
    ("block_given_a_third_macro_feature", _FITS_REL,
     lambda p: p["feature_counts_by_block"].update(M3_LAG_WDI=[15])),
    ("retuning_executed", _BOUNDARY_REL,
     lambda p: p.update(retuning_executed=True)),
    ("grid_search_executed", _BOUNDARY_REL,
     lambda p: p.update(grid_search_executed=True)),
    ("feature_search_executed", _BOUNDARY_REL,
     lambda p: p.update(feature_search_executed=True)),
    ("imputation_executed", _BOUNDARY_REL,
     lambda p: p.update(imputation_executed=True)),
    ("seed_policy_changed", _BOUNDARY_REL,
     lambda p: p.update(seed_policy_changed=True)),
    ("metric_definition_changed", _BOUNDARY_REL,
     lambda p: p.update(metric_definition_changed=True)),
    ("validation_architecture_changed", _BOUNDARY_REL,
     lambda p: p.update(validation_architecture_changed=True)),
    ("shap_executed", _BOUNDARY_REL,
     lambda p: p.update(shap_executed=True)),
    ("calendar_mapping_changed", _BOUNDARY_REL,
     lambda p: p.update(calendar_mapping_changed_by_this_action=True)),
    ("step_d_rerun", _BOUNDARY_REL,
     lambda p: p.update(step_d_rerun_by_this_action=True)),
    ("final_test_row_read", _BOUNDARY_REL,
     lambda p: p.update(final_test_rows_read=1)),
    ("final_test_unlocked", _BOUNDARY_REL,
     lambda p: p.update(final_test_unlocked_by_this_action=True)),
    ("final_test_declared_open", _BOUNDARY_REL,
     lambda p: p.update(final_test_locked=False)),
    ("merge_authorized", _BOUNDARY_REL,
     lambda p: p.update(merge_authorized=True)),
    ("ready_for_review_authorized", _BOUNDARY_REL,
     lambda p: p.update(ready_for_review_authorized=True)),
    ("m4_authorized", _BOUNDARY_REL,
     lambda p: p.update(m4_authorized=True)),
    ("modeling_authorization_reads_as_standing", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_modeling_authorized_now=True)),
    ("modeling_authorization_declared_reusable", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_modeling_authorization_reusable=True)),
    ("prior_authorization_reused", _BOUNDARY_REL,
     lambda p: p.update(prior_authorization_reused_by_this_action=True)),
    ("world_bank_request_made", _AUDIT_REL,
     lambda p: p.update(world_bank_api_requests=1)),
    ("alternative_indicator_searched", _AUDIT_REL,
     lambda p: p.update(alternative_indicators_searched=1)),
    ("third_macro_feature_added", _AUDIT_REL,
     lambda p: p.update(third_macro_features_added=1)),
    ("tuning_run_executed", _AUDIT_REL,
     lambda p: p.update(tuning_runs=1)),
    ("holm_calculated", _AUDIT_REL,
     lambda p: p.update(holm_calculations=1)),
    ("paper_winner_counter_moved", _AUDIT_REL,
     lambda p: p.update(paper_winner_selections=1)),
    ("pr_merged", _AUDIT_REL,
     lambda p: p.update(pr_merges=1)),
    ("step_d_artifacts_mutated", _AUDIT_REL,
     lambda p: p.update(step_d_artifacts_modified=True)),
    ("calendar_lock_artifacts_mutated", _AUDIT_REL,
     lambda p: p.update(calendar_lock_artifacts_modified=True)),
    ("confirmatory_holm_state_mutated", _AUDIT_REL,
     lambda p: p.update(confirmatory_holm_state_modified=True)),
])
def test_generator_rejects_a_tampered_step_e(monkeypatch, label, rel, mutate):
    _tampered(monkeypatch, rel, mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_incremental_evaluation_markers(
            REPO_ROOT)


# --------------------------------------------------------------------------- #
# The independent validator agrees
# --------------------------------------------------------------------------- #

def test_independent_validator_recognizes_step_e():
    from pathlib import Path
    assert val.stage128_m3_lag_wdi_modeling_executed(
        Path(REPO_ROOT)) is True


def test_independent_validator_has_a_no_next_action_pointer():
    assert val.STAGE128_M3_LAG_NO_NEXT_ACTION_ID == "human_decision_required"


def test_consumed_authorization_invariant_covers_modeling():
    assert "stage128_m3_lag_wdi_modeling" in (
        gen._ONE_TIME_AUTHORIZATION_PREFIXES)
    with pytest.raises(gen.HandoffError):
        gen._assert_no_consumed_authorization_is_standing({
            "stage128_m3_lag_wdi_modeling_authorization_consumed": True,
            "stage128_m3_lag_wdi_modeling_was_authorized": True,
            "stage128_m3_lag_wdi_modeling_authorized": True,
        })
