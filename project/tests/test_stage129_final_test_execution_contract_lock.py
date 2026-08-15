"""Stage129 — the prospectively locked Final Test execution contract.

This contract lock carries every risk its Full-Development Refit predecessor
carried, plus one more. The predecessor described a future fit on data that was
already open; this one describes a future read of the one partition the whole
project has kept sealed. So these tests pin four things shut:

  * the contract could DRIFT from the frozen artifacts it claims to extract
    from -- so every term is re-derived here from its cited source, and all 17
    pinned sources are re-hashed;
  * locking could be mistaken for AUTHORIZING -- so nothing is executed, every
    counter is zero, every expected output reports `exists_now: false`, and
    execution stays behind a new human authorization;
  * the contract could quietly WIDEN what it accepts -- so the accepted model
    and the four accepted refit artifacts are pinned by hash, and anything else
    must fail closed;
  * the missing threshold value could be silently INVENTED to make the future
    execution look ready -- so the absence is asserted directly, in the
    contract, in the provenance record and across the whole repository.

FT05 is the mirror image of the refit's FC03. There, Final Test years were
forbidden in the fit window. Here, development years are forbidden in the
evaluation window, because evaluating on development rows would silently report
an in-sample result.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

_PKG_REL = "project/stage129/final_test_execution_contract_lock"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_CON = f"{_PKG_REL}/stage129_final_test_execution_contract.json"
_PROV = f"{_PKG_REL}/stage129_final_test_execution_source_provenance.json"
_BND = f"{_PKG_REL}/stage129_final_test_execution_governance_boundary.json"
_MANIFEST_NAME = "metadata_and_hashes_stage129_final_test_execution_contract_lock.json"
_MAN = f"{_PKG_REL}/{_MANIFEST_NAME}"
_README_NAME = "README_STAGE129_FINAL_TEST_EXECUTION_CONTRACT_LOCK.md"

_PRE_REL = "project/stage125/part4_preprocessing_contract_stage125.json"
_SPLIT_REL = "project/stage125/part4_temporal_split_contract_stage125.json"
_METRICS_REL = "project/stage125/part4_metrics_uncertainty_contract_stage125.json"
_SAP_REL = "project/stage125/part4_statistical_analysis_plan_stage125.json"
_LOCK_REL = "project/stage126/stage126_m1_primary_development_lock.json"
_DEV_METRICS_REL = "project/stage126/stage126_m1_development_metrics.csv"
_FREEZE_REL = "project/stage126/stage126_m1_retained_design_freeze.json"
_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"

_REFIT_REL = "project/stage129/full_development_refit_execution"
_REFIT_MODEL_REL = f"{_REFIT_REL}/stage129_full_development_refit_model.json"
_REFIT_PREP_REL = f"{_REFIT_REL}/stage129_full_development_refit_preprocessing_parameters.json"
_REFIT_PROV_REL = f"{_REFIT_REL}/stage129_full_development_refit_provenance_record.json"
_REFIT_QC_REL = f"{_REFIT_REL}/stage129_full_development_refit_qc_report.json"

ACTION_ID = "stage129-final-test-execution-contract-lock"
STATUS = "PROSPECTIVELY_LOCKED_NOT_EXECUTED"
DEV_YEARS = [1393, 1394, 1395, 1396, 1397, 1398, 1399]
FINAL_TEST_YEARS = [1400, 1401, 1402]
FEATURES = [
    "log_total_assets", "leverage_ratio", "current_ratio", "roa_period_adjusted",
    "ocf_to_assets_period_adjusted", "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]
RUNTIME = {"jdatetime": "6.0.1", "numpy": "2.4.6", "pandas": "3.0.3",
           "python": "3.13.5", "scikit-learn": "1.9.0", "xgboost": "3.3.0"}
FT_IDS = [f"FT{i:02d}" for i in range(1, 22)]
NEXT_ACTION = "human_authorization_required_for_final_test_execution"

ACCEPTED = {
    "stage129_full_development_refit_model.json":
        "48faab1ef186206508385713fb3b885a88a55bb072fb586d56e63d2777c97690",
    "stage129_full_development_refit_preprocessing_parameters.json":
        "862c65ec37082be1e3e95c29d2bf8873df9105e90cc43ce1ecac4fd8901ba9f6",
    "stage129_full_development_refit_provenance_record.json":
        "4b1aa9a6c85208713f250b5ac3fe71f56c4a8398c3834855926e29a43ad8f07d",
    "stage129_full_development_refit_qc_report.json":
        "e874ee5bdf2510f6c630f170482ca7a13f50ab73c7838550e9412c372c5ee63c",
}


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _sha256(rel):
    with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def contract():
    return _load(_CON)


@pytest.fixture(scope="module")
def provenance():
    return _load(_PROV)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BND)


@pytest.fixture(scope="module")
def manifest():
    return _load(_MAN)


# ------------------------------------------------------------------ identity
def test_contract_identity_is_a_lock_not_an_execution(contract):
    assert contract["action_id"] == ACTION_ID
    assert contract["contract_id"] == "stage129_final_test_execution_contract"
    assert contract["contract_status"] == STATUS
    assert contract["every_term_is_extracted_from_a_prelocked_artifact"] is True
    assert contract["no_term_invented_by_this_action"] is True


def test_the_predecessor_contract_is_pinned_and_unmodified(contract):
    assert contract["predecessor_contract"] == "stage129_full_development_refit_contract"
    assert _sha256(contract["predecessor_contract_path"]) == \
        contract["predecessor_contract_sha256"]


# ------------------------------------------------- what the contract accepts
def test_only_the_selected_m1_model_is_accepted(contract):
    m = contract["accepted_model"]
    assert m["block"] == "M1"
    assert m["algorithm"] == "regularized_logistic_regression"
    assert m["configuration_id"] == "logistic__C_0.1"
    assert m["model_is_taken_as_given_not_refit"] is True
    assert m["no_other_model_block_algorithm_or_configuration_is_accepted"] is True
    for rejected in ("random_forest", "xgboost"):
        assert rejected in m["rejected_by_construction"]


def test_accepted_model_terms_match_the_merged_refit_artifact(contract):
    m = contract["accepted_model"]
    refit = _load(_REFIT_MODEL_REL)
    assert m["configuration_id"] == refit["configuration_id"]
    assert m["algorithm"] == refit["algorithm"]
    assert m["block"] == refit["block"]
    assert m["hyperparameters"] == refit["hyperparameters"]


def test_the_four_accepted_artifacts_hash_exactly(contract):
    arts = contract["accepted_artifacts"]["artifacts"]
    assert set(arts) == set(ACCEPTED)
    for name, info in arts.items():
        assert info["sha256"] == ACCEPTED[name], name
        assert _sha256(info["path"]) == info["sha256"], name


def test_the_accepted_refit_really_fitted_once_and_read_no_final_test(contract):
    acc = contract["accepted_artifacts"]
    assert acc["refit_model_fits_executed"] == 1
    assert acc["refit_final_test_rows_read"] == 0
    qc = _load(_REFIT_QC_REL)
    assert qc["model_fits_executed"] == 1
    assert all(v == 0 for v in qc["final_test_counters"].values())


# --------------------------------------------------------- the data boundary
def test_evaluation_window_is_final_test_years_only(contract):
    d = contract["final_test_data"]
    assert d["final_test_target_years"] == FINAL_TEST_YEARS
    assert d["development_target_years_excluded_from_evaluation"] == DEV_YEARS
    assert d["final_test_target_years"] == _load(_SPLIT_REL)["final_test_target_years"]
    assert d["random_split_authorized"] is False
    assert d["shuffle_authorized"] is False


def test_expected_counts_are_quoted_frozen_metadata_not_row_access(contract):
    d = contract["final_test_data"]
    frozen = _load(_SPLIT_REL)["primary_sample_final_test_expected"]
    got = d["expected_final_test_counts_metadata_only"]
    for k in ("pairs", "positive", "negative"):
        assert got[k] == frozen[k], k
    assert d["expected_counts_are_frozen_metadata_not_row_level_access"] is True
    assert d["manifest_forbids_predictor_values"] is True
    assert d["manifest_forbids_row_level_targets"] is True


def test_pinned_inputs_match_the_refit_provenance(contract):
    d = contract["final_test_data"]
    refit_inputs = _load(_REFIT_PROV_REL)["input_sha256"]
    assert refit_inputs[d["analysis_ready_path"]] == d["analysis_ready_sha256"]
    assert refit_inputs[d["audited_pairs_path"]] == d["audited_pairs_sha256"]


# -------------------------------------------------------------- the features
def test_feature_order_is_the_locked_order(contract):
    f = contract["features"]
    assert f["features_exact_order"] == FEATURES
    assert f["feature_count"] == 9
    assert f["features_exact_order"] == _load(_LOCK_REL)["feature_order"]
    assert f["feature_reselection_on_final_test_authorized"] is False
    assert f["excluded_feature"] == "revenue_growth_period_adjusted"
    assert f["excluded_feature"] not in f["features_exact_order"]


def test_design_matrix_matches_the_accepted_model(contract):
    f = contract["features"]
    cols = _load(_REFIT_MODEL_REL)["design_matrix_columns"]
    assert f["design_matrix_columns_expected"] == len(cols) == 18
    assert cols[:9] == FEATURES
    assert all(c.endswith("__missing") for c in cols[9:])


def test_forbidden_selection_methods_come_from_the_frozen_contract(contract):
    assert contract["features"]["feature_selection_forbidden"] == \
        _load(_PRE_REL)["forbidden_selection"]


# --------------------------------------------------------- the preprocessing
def test_nothing_is_re_estimated_on_the_final_test(contract):
    p = contract["preprocessing_application"]
    assert p["parameters_are_taken_from_the_refit_not_re_estimated"] is True
    assert p["nothing_is_fit_on_final_test"] is True
    assert p["never_fit_on_final_test"] is True
    assert p["clipping_bounds_recomputed_on_final_test"] is False
    assert p["medians_recomputed_on_final_test"] is False
    assert p["standardization_recomputed_on_final_test"] is False
    assert p["forbidden_fit_on"] == _load(_PRE_REL)["forbidden_fit_on"]


def test_application_order_drops_only_the_estimation_steps(contract):
    """The six applied steps must be the frozen eight minus the three
    estimation steps -- nothing added, nothing reordered."""
    steps = contract["preprocessing_application"]["application_order"]
    assert len(steps) == 6
    frozen = _load(_PRE_REL)["continuous_pipeline_order"]
    assert len(frozen) == 8
    # every applied step keeps the frozen relative ordering
    assert steps == sorted(steps, key=lambda s: int(s.split("_", 1)[0]))
    joined = " ".join(steps)
    assert "estimate" not in joined, "no estimation step may survive"
    for must in ("clipping", "impute", "missingness_indicators", "standardize"):
        assert must in joined, must


def test_masks_come_from_the_final_tests_own_positions(contract):
    p = contract["preprocessing_application"]
    assert p["final_test_masks_from_own_original_missing_positions"] is True
    assert _load(_PRE_REL)[
        "validation_and_final_test_masks_from_own_original_missing_positions"] is True
    assert p["do_not_infer_missingness_indicator_from_imputed_matrix"] is True
    assert p["missing_indicators_standardized"] is False


def test_target_state_contract_is_quoted_verbatim(contract):
    got = contract["preprocessing_application"]["target_state_contract"]
    frozen = _load(_SAP_REL)["target_state_contract"]
    for k, v in frozen.items():
        assert got[k] == v, k
    assert got["missing_never_counted_as_negative"] is True


# ----------------------------------------------------------- the threshold gap
def test_threshold_rule_is_quoted_and_never_optimized_on_final_test(contract):
    t = contract["threshold"]
    frozen = _load(_METRICS_REL)["thresholded_secondary"]
    assert t["rule"] == frozen["rule"]
    assert t["tie_break"] == frozen["tie_break"]
    assert t["never_optimize_on_final_test"] is True
    assert t["threshold_search_on_final_test_authorized"] is False
    assert t["threshold_is_derived_from_development_oof_only"] is True


def test_the_threshold_value_is_absent_and_not_invented(contract, provenance):
    t = contract["threshold"]
    assert t["threshold_value"] is None
    assert t["threshold_value_materialized"] is False
    assert t["threshold_value_status"] == "RULE_LOCKED_VALUE_NEVER_COMPUTED"
    assert t["threshold_materialization_authorized_by_this_contract"] is False
    assert t["thresholded_outputs_blocked_until_value_exists"] is True
    assert provenance["threshold_value_found_in_any_source"] is False


def test_the_frozen_metrics_contract_really_has_no_threshold_value():
    """The gap is a fact about the repository, not a claim in our own file."""
    frozen = _load(_METRICS_REL)["thresholded_secondary"]
    assert set(frozen) == {"never_optimize_on_final_test", "rule", "tie_break"}
    header = _text(_DEV_METRICS_REL).splitlines()[0].split(",")
    assert not any("threshold" in c.lower() for c in header), header


def test_threshold_derivation_needs_zero_final_test_rows(contract):
    d = contract["threshold"]["threshold_derivation_inputs_if_ever_authorized"]
    assert d["final_test_rows_required"] == 0
    assert d["derivation_is_development_side_only"] is True
    assert _sha256(d["pooled_development_oof_predictions_path"]) == \
        d["pooled_development_oof_predictions_sha256"]
    header = _text(_OOF_REL).splitlines()[0].split(",")
    for col in d["required_columns"]:
        assert col in header, col


def test_topk_independence_is_arithmetic_not_a_permission(contract):
    """Recall@10% and Lift@10% are top-K and need no threshold.

    That must never be read as licence to open the Final Test early for the
    metrics that happen to be computable. PRE02 has exactly one resolution.
    """
    topk = contract["metrics"]["topk"]
    assert topk["definition"] == "K_y = ceil(0.10 * N_y)"
    assert topk["optimize_K_after_results"] is False
    assert topk == {**topk, **{k: v for k, v in _load(_METRICS_REL)["topk"].items()
                               if k in topk}}
    thr = contract["threshold"]
    assert thr["topk_metrics_are_mathematically_independent_of_this_value"] is True
    assert thr["topk_independence_is_not_an_execution_permission"] is True
    assert thr["no_threshold_free_partial_execution_alternative"] is True


def test_pre02_has_no_threshold_free_escape_hatch(contract):
    pre02 = next(p for p in contract["execution_prerequisites"]["prerequisites"]
                 if p["id"] == "PRE02")
    assert pre02["satisfied_now"] is False
    assert pre02["no_partial_execution_alternative"] is True
    assert "threshold-free" in pre02["note"].lower()
    assert "committed artifact" in pre02["requirement"]


def test_contract_publishes_that_it_is_not_fully_executable(contract, boundary):
    exe = contract["executability_status"]
    for field in ("final_test_contract_fully_executable",
                  "final_test_execution_authorized", "final_test_access_authorized",
                  "partial_execution_authorized",
                  "threshold_free_execution_authorized",
                  "metric_subset_execution_authorized"):
        assert exe[field] is False, field
    assert exe["final_test_rows_read"] == 0
    assert exe["final_test_contract_fully_executable_blocked_by"] == ["PRE01", "PRE02"]
    assert exe["unresolved_prerequisite_count"] == 2
    assert exe["final_test_opens_once_after_all_prerequisites_are_resolved"] is True
    assert exe["final_test_may_not_be_opened_in_stages"] is True
    # and the boundary agrees
    assert boundary["final_test_contract_fully_executable"] is False
    assert boundary["final_test_partial_execution_authorized"] is False
    assert boundary["final_test_threshold_free_execution_authorized"] is False
    assert boundary["final_test_may_not_be_opened_in_stages"] is True


def test_ft21_blocks_partial_and_staged_execution(contract):
    ft21 = next(c for c in contract["fail_closed_controls"] if c["id"] == "FT21")
    check = ft21["check"].lower()
    assert "prerequisite" in check
    assert "threshold-free" in check
    assert "stages" in check
    assert ft21["on_failure"] == "ABORT_FINAL_TEST"


def test_threshold_derivation_is_a_separate_unauthorized_action(contract, boundary):
    thr = contract["threshold"]
    assert thr["threshold_derivation_requires_its_own_human_authorization"] is True
    assert thr["threshold_derivation_is_a_separate_development_only_action"] is True
    assert boundary["threshold_derivation_authorized"] is False
    assert boundary["threshold_extracted_from_oof_predictions_by_this_action"] is False
    assert contract["execution_authorization"]["threshold_derivation_authorized"] is False


# ----------------------------------------------------------------- the metrics
def test_metric_set_is_closed_and_quoted(contract):
    m = contract["metrics"]
    frozen = _load(_METRICS_REL)
    assert m["primary_metric"] == frozen["primary_metric"] == "PR-AUC"
    assert m["secondary_metrics"] == frozen["secondary_metrics"]
    assert m["metric_set_is_closed"] is True
    assert m["additional_metrics_authorized"] is False
    assert m["metric_substitution_authorized"] is False
    assert m["primary_metric_may_not_be_changed_after_seeing_final_test_results"] is True


def test_bootstrap_parameters_are_locked_but_unexecuted(contract):
    u = contract["uncertainty"]
    frozen = _load(_METRICS_REL)["uncertainty"]
    for k in ("method", "cluster", "confidence_interval", "replicates",
              "min_valid_replicates", "bootstrap_seed",
              "valid_replicate_requires_both_classes",
              "same_resampled_rows_for_all_compared_models"):
        assert u[k] == frozen[k], k
    assert u["bootstrap_execution_authorized_by_this_contract"] is False
    assert u["new_seed_introduction_authorized"] is False


def test_calibration_stays_raw_and_unexecuted(contract):
    c = contract["calibration"]
    frozen = _load(_METRICS_REL)["calibration"]
    assert c["primary_probabilities"] == frozen["primary_probabilities"]
    assert c["isotonic_authorized"] is False
    assert c["platt_fit_on"] == frozen["platt_fit_on"]
    assert c["platt_fit_on_final_test_authorized"] is False
    assert c["recalibration_execution_authorized_by_this_contract"] is False
    assert c["do_not_select_winner_on_calibrated_final_test"] is True
    # the skip rule is quoted correctly and genuinely does not trigger
    assert c["skip_recalibration_if_oof_positives_lt"] == \
        frozen["skip_recalibration_if_oof_positives_lt"]
    assert c["pooled_development_oof_positives_for_selected_model"] >= \
        c["skip_recalibration_if_oof_positives_lt"]
    assert c["skip_rule_triggered"] is False


def test_no_inference_is_created_by_evaluating_one_model(contract):
    m = contract["multiplicity_and_inference"]
    frozen = _load(_METRICS_REL)["multiplicity"]
    assert m["alpha"] == frozen["alpha"]
    assert m["correction"] == frozen["correction"]
    assert m["confirmatory_family_1"] == frozen["confirmatory_family_1"]
    assert m["confirmatory_family_1_status"] == "NEVER_EXECUTED"
    assert m["holm_reporting_status"] == "HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE"
    assert m["holm_family_complete"] is False
    assert m["holm_execution_authorized_by_this_contract"] is False
    assert m["family_may_not_be_shrunk_or_redefined_post_hoc"] is True
    assert m["final_test_results_may_not_be_used_to_select_a_winner"] is True
    assert m["final_test_results_may_not_reopen_model_selection"] is True
    assert m["inferential_superiority_claim_authorized"] is False


# ----------------------------------------------------------------- the outputs
def test_no_expected_output_exists_yet(contract):
    out = contract["expected_outputs"]
    assert len(out["artifacts"]) == 4
    for a in out["artifacts"]:
        assert a["exists_now"] is False, a["name"]
    assert out["thresholded_outputs_blocked_until_threshold_value_exists"] is True
    assert out["locked_primary_results_are_not_replaced_by_the_final_test"] is True


def test_forbidden_outputs_cover_every_prohibited_act(contract):
    forbidden = " ".join(contract["expected_outputs"]["forbidden_outputs"])
    for token in ("refit", "recalibrated", "hyperparameter_search",
                  "holm", "winner", "second_pass"):
        assert token in forbidden, token


def test_locked_development_results_are_pinned(contract):
    for rel, want in contract["expected_outputs"]["locked_development_results_pinned"].items():
        assert _sha256(rel) == want, rel


def test_required_counters_forbid_any_fit_or_search(contract):
    c = contract["required_counters"]
    for k in ("model_fits_executed", "refits_executed", "tuning_runs",
              "hyperparameter_searches", "feature_searches", "threshold_searches",
              "recalibration_executions", "isotonic_executions", "shap_executions",
              "holm_executions", "p_values_computed", "winner_selections"):
        assert c[k] == 0, k
    assert c["final_test_passes_executed"] == 1


# ------------------------------------------------------ fail-closed controls
def test_all_twenty_one_controls_exist_and_abort(contract):
    controls = contract["fail_closed_controls"]
    assert [c["id"] for c in controls] == FT_IDS
    for c in controls:
        assert c["on_failure"] == "ABORT_FINAL_TEST", c["id"]
        assert c["check"].strip()


def test_ft05_is_the_mirror_image_of_the_refit_fc03(contract):
    """The refit forbade Final Test years; this forbids development years."""
    ft05 = next(c for c in contract["fail_closed_controls"] if c["id"] == "FT05")
    assert "1400-1402" in ft05["check"]
    assert "1393-1399" in ft05["check"]
    assert "zero" in ft05["check"].lower()


def test_ft09_forbids_any_fit(contract):
    ft09 = next(c for c in contract["fail_closed_controls"] if c["id"] == "FT09")
    assert "model_fits_executed == 0" in ft09["check"]


def test_ft10_blocks_thresholded_outputs_when_no_value_exists(contract):
    ft10 = next(c for c in contract["fail_closed_controls"] if c["id"] == "FT10")
    assert "threshold" in ft10["check"].lower()
    assert "not produced" in ft10["check"].lower()


# --------------------------------------------------------------- environment
def test_runtime_matches_the_locked_development_runtime(contract):
    env = contract["environment"]
    assert env["runtime_versions"] == RUNTIME
    assert env["runtime_versions"] == _load(_REFIT_PROV_REL)["runtime_versions"]
    assert env["environment_mismatch_action"] == "FAIL_CLOSED_DO_NOT_EVALUATE"


# ------------------------------------------------------- prerequisites/boundary
def test_two_prerequisites_are_unsatisfied(contract, boundary):
    pres = {p["id"]: p for p in contract["execution_prerequisites"]["prerequisites"]}
    assert pres["PRE01"]["satisfied_now"] is False
    assert pres["PRE02"]["satisfied_now"] is False
    assert pres["PRE03"]["satisfied_now"] is True
    assert pres["PRE04"]["satisfied_now"] is True
    assert boundary["unresolved_prerequisites"] == ["PRE01", "PRE02"]
    assert boundary["unresolved_prerequisites_recorded"] == 2


def test_final_test_stays_locked_and_unread(contract, boundary):
    b = contract["final_test_boundary"]
    assert b["final_test_locked"] is True
    assert b["final_test_access_authorized"] is False
    assert b["final_test_unlock_authorized"] is False
    assert b["final_test_rows_read"] == 0
    assert b["this_contract_lock_is_read_only_over_committed_artifacts"] is True
    for k in ("final_test_rows_read_by_this_contract_lock",
              "final_test_predictor_values_read_by_this_contract_lock",
              "final_test_target_values_read_by_this_contract_lock",
              "final_test_predictions_by_this_contract_lock",
              "final_test_metrics_computed_by_this_contract_lock"):
        assert b[k] == 0, k
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0


def test_apply_once_is_acknowledged_not_taken(contract):
    b = contract["final_test_boundary"]
    assert b["apply_once_to_locked_final_test"] is True
    assert _load(_PRE_REL)["final_development_refit"][
        "apply_once_to_locked_final_test"] is True
    assert b["apply_once_means_exactly_one_pass_not_an_authorization_to_take_it"] is True


def test_locking_authorizes_nothing(contract, boundary):
    a = contract["execution_authorization"]
    assert a["final_test_contract_fully_executable"] is False
    assert a["final_test_rows_read"] == 0
    for k in ("final_test_execution_authorized", "final_test_access_authorized",
              "partial_execution_authorized", "threshold_free_execution_authorized",
              "threshold_derivation_authorized",
              "final_test_execution_authorized_by_this_contract",
              "recalibration_authorized", "refit_authorized", "second_fit_authorized",
              "tuning_authorized", "new_scientific_result_authorized",
              "stage130_authorized", "stage130_started",
              "ready_for_review_authorized", "merge_authorized",
              "next_action_authorized"):
        assert a[k] is False, k
    assert a["final_test_execution_requires_new_explicit_human_authorization"] is True
    assert a["contract_lock_is_not_an_execution_permission"] is True
    assert a["next_action_id"] == NEXT_ACTION
    assert a["pointer_is_not_authorization"] is True
    assert boundary["next_action_id"] == NEXT_ACTION
    assert boundary["next_action_executes_final_test"] is False


def test_every_governance_counter_is_zero(boundary):
    assert boundary["counters"], "counters block must not be empty"
    for k, v in boundary["counters"].items():
        assert v == 0, f"{k} must be 0 in a lock-only action, got {v}"


def test_the_action_modified_no_prior_package(boundary):
    for k in ("existing_pull_requests_modified_by_this_action",
              "historical_scientific_artifacts_modified_by_this_action",
              "locked_primary_development_results_modified_by_this_action",
              "m1_results_modified_by_this_action",
              "m2_status_modified_by_this_action",
              "m3_cbi_disposition_modified_by_this_action",
              "m4_disposition_modified_by_this_action",
              "prior_packages_modified_by_this_action",
              "source_contracts_modified_by_this_action",
              "new_contract_term_invented_by_this_action",
              "new_scientific_result_produced",
              "threshold_value_materialized_by_this_action"):
        assert boundary[k] is False, k


def test_dispositions_are_preserved(boundary):
    assert boundary["m2_role_preserved"] == "intermediate_confirmatory_block"
    assert boundary["m3_lag_wdi_disposition"] == "SUPPLEMENTARY_EXPLORATORY_ONLY"
    assert boundary["m3_lag_wdi_promoted_to_confirmatory_model"] is False
    assert boundary["inferential_superiority_claimed"] is False
    assert boundary["paper_winner_selected"] is True
    assert boundary["full_development_refit_performed"] is True
    assert boundary["full_development_refit_executed_by_this_action"] is False


# ------------------------------------------------------------------ provenance
def test_all_seventeen_sources_are_pinned_and_current(provenance):
    src = provenance["source_artifacts_sha256"]
    assert len(src) == provenance["source_artifact_count"] == 17
    for rel, info in src.items():
        assert _sha256(rel) == info["sha256"], rel
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            assert len(fh.read()) == info["bytes"], rel
        assert info["supplies"].strip(), rel


def test_no_source_is_a_final_test_artifact(provenance):
    assert provenance["no_final_test_artifact_is_a_source"] is True
    assert provenance["no_source_contains_final_test_row_level_data"] is True
    assert provenance["extraction_is_read_only"] is True
    assert provenance["sources_modified_by_this_action"] is False


def test_the_repository_really_has_no_committed_threshold_value():
    """Belt and braces: check the tracked tree, not just our own claim.

    Two frozen artifacts name the F2 rule -- the metrics contract and the
    retained design freeze. Both must carry the rule and the tie-break and
    NOTHING numeric, or the "never computed" finding is wrong.
    """
    named_in = subprocess.run(
        ["git", "grep", "-l", "-iE", r"development_OOF_F2_maximizing_threshold",
         "--", "project/stage125", "project/stage126"],
        cwd=REPO_ROOT, capture_output=True, text=True).stdout.split()
    assert named_in == [_METRICS_REL, _FREEZE_REL], named_in

    blocks = [_load(_METRICS_REL)["thresholded_secondary"],
              _load(_FREEZE_REL)["metric_definitions"]["thresholded_secondary"]]
    for block in blocks:
        assert block["rule"] == "development_OOF_F2_maximizing_threshold"
        assert block["tie_break"] == "higher_threshold"
        assert not any(isinstance(v, (int, float)) and not isinstance(v, bool)
                       for v in block.values()), block
    # and the two frozen statements of the rule agree with each other
    assert blocks[0]["rule"] == blocks[1]["rule"]
    assert blocks[0]["tie_break"] == blocks[1]["tie_break"]


# ------------------------------------------------------------ package hygiene
def test_no_binary_or_data_artifact_was_committed():
    names = sorted(os.listdir(_PKG))
    assert names
    for name in names:
        assert name.endswith((".json", ".md")), name


def test_package_hash_manifest_matches_every_file(manifest):
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != _MANIFEST_NAME}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_manifest_records_the_zero_counters(manifest):
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["final_test_rows_read"] == 0
    assert manifest["model_fits_executed"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["trained_model_artifacts_committed"] == 0
    assert manifest["threshold_values_materialized"] == 0
    assert manifest["final_test_execution_authorized"] is False
    assert manifest["unresolved_prerequisite_count"] == 2
    assert manifest["contract_status"] == STATUS


def test_the_readme_documents_the_lock_in_english_and_persian():
    readme = _text(f"{_PKG_REL}/{_README_NAME}")
    flat = re.sub(r"\s+", " ", readme)
    for phrase in ("prospectively_locked_not_executed",
                   "locking a contract is not permission to execute it",
                   "the model is applied, never refitted",
                   "was never computed"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("هیچ ردیف", "final_test_rows_read = 0", "مجوز انسانی"):
        assert phrase in flat, phrase


def test_readme_quotes_the_four_accepted_hashes():
    readme = _text(f"{_PKG_REL}/{_README_NAME}")
    for name, digest in ACCEPTED.items():
        assert digest in readme, name
