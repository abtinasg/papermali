"""Stage129 — the prospectively locked Full-Development Refit contract.

A contract lock is a description of a future execution, which creates two
distinctive risks. These tests pin both shut:

  * the contract could DRIFT from the frozen artifacts it claims to extract
    from -- so every term is re-derived here from its cited source, and the
    generator re-hashes all 12 sources;
  * locking could be mistaken for AUTHORIZING -- so nothing is executed, every
    counter is zero, the expected outputs all report `exists_now: false`, and
    the refit stays behind a new human authorization.

The Final Test years may never appear in the fit window, and the threshold must
stay a development-OOF quantity rather than something re-derived from the
refit's own in-sample predictions.
"""
import copy
import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

_PKG_REL = "project/stage129/full_development_refit_contract_lock"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_CON = f"{_PKG_REL}/stage129_full_development_refit_contract.json"
_PROV = f"{_PKG_REL}/stage129_full_development_refit_source_provenance.json"
_BND = f"{_PKG_REL}/stage129_full_development_refit_governance_boundary.json"

_PRE_REL = "project/stage125/part4_preprocessing_contract_stage125.json"
_SPLIT_REL = "project/stage125/part4_temporal_split_contract_stage125.json"
_METRICS_REL = "project/stage125/part4_metrics_uncertainty_contract_stage125.json"
_BUDGET_REL = "project/stage125/part4_hyperparameter_budget_stage125.json"
_SPECS_REL = "project/stage125/part4_model_specifications_stage125.json"
_SAP_REL = "project/stage125/part4_statistical_analysis_plan_stage125.json"
_FREEZE_REL = "project/stage126/stage126_m1_retained_design_freeze.json"
_LOCK_REL = "project/stage126/stage126_m1_primary_development_lock.json"
_TUNING_META_REL = (
    "project/stage126/metadata_and_hashes_stage126_m1_primary_development_tuning.json")

ACTION_ID = "stage129-full-development-refit-contract-lock"
STATUS = "PROSPECTIVELY_LOCKED_NOT_EXECUTED"
FIT_YEARS = [1393, 1394, 1395, 1396, 1397, 1398, 1399]
FINAL_TEST_YEARS = [1400, 1401, 1402]
FEATURES = [
    "log_total_assets", "leverage_ratio", "current_ratio", "roa_period_adjusted",
    "ocf_to_assets_period_adjusted", "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]
HYPERPARAMS = {"C": 0.1, "max_iter": 5000, "penalty": "l2", "solver": "liblinear"}
RUNTIME = {"jdatetime": "6.0.1", "numpy": "2.4.6", "pandas": "3.0.3",
           "python": "3.13.5", "scikit-learn": "1.9.0", "xgboost": "3.3.0"}
FC_IDS = [f"FC{i:02d}" for i in range(1, 13)]
NEXT_ACTION = "human_authorization_required_for_full_development_refit_execution"


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


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


# ---------------------------------------- the contract is an extraction
def test_the_contract_is_locked_but_not_executed(contract, boundary, state,
                                                 roadmap_front_matter):
    assert contract["contract_status"] == STATUS
    assert boundary["contract_status"] == STATUS
    assert state["stage129_refit_contract_status"] == STATUS
    assert roadmap_front_matter["refit_contract_status"] == STATUS
    assert state["stage129_refit_contract_recorded"] is True
    assert state["stage129_refit_contract_action_id"] == ACTION_ID
    assert contract["contract_id"] == "stage129_full_development_refit_contract"


def test_every_term_is_extracted_and_every_source_is_pinned(contract,
                                                            provenance, state):
    assert contract["every_term_is_extracted_from_a_prelocked_artifact"] is True
    assert contract["no_term_invented_by_this_action"] is True
    assert provenance["extraction_is_read_only"] is True
    assert provenance["sources_modified_by_this_action"] is False
    sources = provenance["source_artifacts_sha256"]
    assert len(sources) == provenance["source_artifact_count"] == 12
    assert state["stage129_refit_source_artifact_count"] == 12
    for rel, info in sources.items():
        path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(path), rel
        with open(path, "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], rel
        assert len(blob) == info["bytes"], rel


# ---------- each extracted term is re-derived here from its cited source
def test_the_fit_window_matches_the_frozen_preprocessing_contract(contract):
    frozen = _load(_PRE_REL)
    assert frozen["final_development_refit"]["fit_years"] == FIT_YEARS
    assert contract["authorized_development_data"]["fit_target_years"] == FIT_YEARS
    # and the development window in the split contract agrees
    assert _load(_SPLIT_REL)["development_target_years"] == FIT_YEARS


def test_the_preprocessing_pipeline_order_is_verbatim(contract):
    frozen = _load(_PRE_REL)
    pre = contract["preprocessing"]
    assert pre["continuous_pipeline_order"] == frozen["continuous_pipeline_order"]
    assert pre["clip_percentiles"] == [1, 99]
    assert pre["clipping_fit_on_observed_training_values_only"] is (
        frozen["clipping_fit_on_observed_training_values_only"])
    assert pre["do_not_compute_clipping_quantiles_after_median_imputation"] is (
        frozen["do_not_compute_clipping_quantiles_after_median_imputation"])
    assert pre["median_fit_after_training_clipping"] is (
        frozen["median_fit_after_training_clipping"])
    assert pre["forbidden_fit_on"] == frozen["forbidden_fit_on"]
    assert pre["never_fit_on_final_test"] is True


def test_the_refit_fit_scope_is_the_single_development_window(contract):
    """A refit has no folds, so every training-derived statistic must be
    re-estimated on the one 1393-1399 fit set. The contract must say so."""
    pre = contract["preprocessing"]
    assert pre["refit_fit_scope"] == "the_single_full_development_fit_set_1393_1399"
    note = pre["refit_fit_scope_note"]
    assert "No statistic may be carried over from a fold." in note
    # the development-time fold scope is still what the frozen contract says
    assert _load(_PRE_REL)["fit_scope"] == "each_temporal_training_fold_separately"


def test_missing_handling_matches_the_frozen_contract(contract):
    frozen = _load(_PRE_REL)
    miss = contract["missing_handling"]
    assert miss["missingness_mask_captured_before_imputation"] is (
        frozen["missingness_mask_captured_before_imputation"])
    assert miss["missingness_indicator_source"] == frozen["missingness_indicator_source"]
    assert miss["do_not_infer_missingness_indicator_from_imputed_matrix"] is (
        frozen["do_not_infer_missingness_indicator_from_imputed_matrix"])
    assert miss["missingness_indicators"] == "appended_unstandardized_binary_0_1"
    sap = _load(_SAP_REL)
    assert miss["target_state_contract"] == sap["target_state_contract"]
    assert miss["target_state_contract"]["missing_never_counted_as_negative"] is True


def test_features_match_the_primary_development_lock(contract, state):
    lock = _load(_LOCK_REL)
    feats = contract["features"]
    assert feats["features_exact_order"] == FEATURES == lock["feature_order"]
    assert feats["feature_count"] == 9 == len(lock["feature_order"])
    assert feats["feature_set"] == lock["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"
    assert state["stage129_refit_feature_order"] == FEATURES
    assert state["stage129_refit_feature_count"] == 9
    # feature selection stays forbidden, verbatim
    assert feats["feature_selection_forbidden"] == _load(_PRE_REL)["forbidden_selection"]
    # the excluded growth feature keeps its frozen rejection
    sap = _load(_SAP_REL)
    assert feats["excluded_feature"] == "revenue_growth_period_adjusted"
    assert sap["revenue_growth_period_adjusted_status"]["admission_status"] == (
        "rejected_m1_primary_coverage_gate_failed")


def test_hyperparameters_and_imbalance_match_the_frozen_sources(contract):
    freeze = _load(_FREEZE_REL)
    model = contract["selected_model"]
    assert model["hyperparameters"] == HYPERPARAMS
    assert freeze["retained_model_families"]["logistic__C_0.1"]["hyperparameters"] == (
        HYPERPARAMS)
    assert model["configuration_id"] == "logistic__C_0.1"
    assert model["algorithm"] == "regularized_logistic_regression"
    assert model["block"] == "M1"
    specs = _load(_SPECS_REL)
    imb = contract["imbalance_handling"]
    assert imb["regularized_logistic_regression"] == (
        specs["imbalance_handling_primary"]["logistic_regression"])
    assert imb["regularized_logistic_regression"]["class_weight"] == "balanced"
    assert imb["smote_or_smotenc_authorized"] is False


def test_the_threshold_rule_matches_and_stays_development_only(contract, state,
                                                               roadmap_front_matter):
    frozen = _load(_METRICS_REL)["thresholded_secondary"]
    thr = contract["threshold"]
    assert thr["rule"] == frozen["rule"] == "development_OOF_F2_maximizing_threshold"
    assert thr["tie_break"] == frozen["tie_break"] == "higher_threshold"
    assert thr["never_optimize_on_final_test"] is True
    assert thr["threshold_is_derived_from_development_oof_only"] is True
    assert thr["threshold_search_on_refit_output_authorized"] is False
    assert state["stage129_refit_threshold_rule"] == thr["rule"]
    assert roadmap_front_matter["refit_threshold_rule"] == thr["rule"]
    # topk definition is quoted, not restated loosely
    topk = _load(_METRICS_REL)["topk"]
    assert thr["topk"]["definition"] == topk["definition"]
    assert thr["topk"]["ranking_order"] == topk["ranking_order"]
    assert thr["topk"]["optimize_K_after_results"] is False


def test_seeds_reflect_that_the_logistic_fit_is_deterministic(contract, state):
    budget = _load(_BUDGET_REL)
    seeds = contract["seeds_and_determinism"]
    assert budget["logistic_regression_deterministic"] is True
    assert seeds["logistic_regression_deterministic"] is True
    assert seeds["logistic_regression_requires_seed_for_fit"] is False
    # the 5-seed averaging rule is scoped to RF/XGB, not logistic
    assert budget["final_rf_xgb_probability"] == (
        "mean_predicted_probability_across_5_fixed_seeds")
    assert seeds["locked_final_seeds_for_reference"] == budget["final_seeds"]
    assert seeds["locked_final_seeds_for_reference"] == _load(_LOCK_REL)["final_oof_seeds"]
    assert seeds["bootstrap_seed_for_reference"] == (
        _load(_METRICS_REL)["uncertainty"]["bootstrap_seed"])
    assert seeds["new_seed_introduction_authorized"] is False
    assert seeds["bootstrap_execution_authorized_by_this_contract"] is False
    assert state["stage129_refit_logistic_is_deterministic"] is True


def test_the_environment_matches_the_locked_development_runtime(contract, state):
    meta = _load(_TUNING_META_REL)
    env = contract["environment"]
    assert env["runtime_versions"] == RUNTIME == meta["runtime_versions"]
    assert env["environment_must_match_the_locked_development_environment"] is True
    assert env["environment_mismatch_action"] == "FAIL_CLOSED_DO_NOT_REFIT"
    assert state["stage129_refit_runtime_versions"] == RUNTIME
    assert state["stage129_refit_runtime_python"] == "3.13.5"


def test_the_pinned_input_hashes_match_the_frozen_sap(contract):
    sap = _load(_SAP_REL)
    pins = sap["pinned_part3c_input_sha256"]
    data = contract["authorized_development_data"]
    assert pins[data["analysis_ready_path"]] == data["analysis_ready_sha256"]
    assert pins[data["audited_pairs_path"]] == data["audited_pairs_sha256"]
    assert data["sample"] == sap["primary_sample"] == "main_rule_a_primary"
    assert data["target"] == sap["primary_target"] == "FD_target_main_t_plus_1"
    assert data["sample_spec"]["rows"] == sap["sample_specs"]["main_rule_a_primary"]["rows"]
    assert data["random_split_authorized"] is False
    assert data["shuffle_authorized"] is False


def test_the_calibration_terms_and_the_quoted_positive_count_are_right(contract):
    frozen = _load(_METRICS_REL)["calibration"]
    cal = contract["calibration"]
    assert cal["primary_probabilities"] == frozen["primary_probabilities"]
    assert cal["isotonic_authorized"] is False is frozen["isotonic_authorized"]
    assert cal["platt_fit_on"] == frozen["platt_fit_on"]
    assert cal["skip_recalibration_if_oof_positives_lt"] == (
        frozen["skip_recalibration_if_oof_positives_lt"]) == 20
    assert cal["do_not_select_winner_on_calibrated_final_test"] is True
    assert cal["recalibration_execution_authorized_by_this_contract"] is False
    # the quoted positive count must equal the committed metrics artifact
    import csv
    with open(os.path.join(REPO_ROOT, "project/stage126/"
                           "stage126_m1_development_metrics.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    pooled = [r for r in rows
              if r["model_family"] == "regularized_logistic_regression"
              and r["scope"] == "pooled_development_oof"]
    assert len(pooled) == 1
    assert cal["pooled_development_oof_positives_for_selected_model"] == int(
        pooled[0]["n_positive"]) == 35
    # 35 >= 20, so the skip rule does not fire
    assert cal["skip_rule_triggered"] is False


# --------------------------------------- the Final Test firewall, by construction
def test_the_final_test_years_can_never_enter_the_fit_window(contract, state):
    data = contract["authorized_development_data"]
    ft = contract["final_test_boundary"]
    assert ft["final_test_target_years"] == FINAL_TEST_YEARS
    assert _load(_SPLIT_REL)["final_test_target_years"] == FINAL_TEST_YEARS
    assert set(data["fit_target_years"]).isdisjoint(FINAL_TEST_YEARS)
    assert max(data["fit_target_years"]) < min(FINAL_TEST_YEARS)
    assert state["stage129_refit_fit_target_years"] == FIT_YEARS
    assert state["stage129_refit_final_test_years"] == FINAL_TEST_YEARS


def test_the_refit_may_not_touch_the_final_test(contract, boundary, state):
    ft = contract["final_test_boundary"]
    for field in ("refit_may_read_final_test", "refit_may_predict_on_final_test",
                  "refit_may_evaluate_on_final_test", "final_test_access_authorized"):
        assert ft[field] is False, field
    assert ft["final_test_locked"] is True
    assert ft["final_test_rows_read"] == 0
    assert ft["apply_once_to_locked_final_test_is_a_future_separately_authorized_step"] is True
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_unlock_authorized"] is False
    assert state["final_test_locked"] is True
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this lock. The lock's own
    # contract and boundary (asserted above) carry its zero.
    assert state["stage129_refit_final_test_rows_read"] == 0
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_refit_may_read_final_test"] is False
    # the expected counts are frozen metadata, quoted not read
    assert ft["expected_counts_are_frozen_metadata_not_row_level_access"] is True
    assert ft["expected_final_test_counts_metadata_only"] == {
        "pairs": 346, "positive": 12, "negative": 334}
    assert _load(_SPLIT_REL)["primary_sample_final_test_expected"]["pairs"] == 346


# --------------------------------------------- locking authorizes nothing
def test_the_expected_outputs_do_not_exist_yet(contract, state):
    outputs = contract["expected_outputs"]
    assert len(outputs["artifacts"]) == 4
    for entry in outputs["artifacts"]:
        assert entry["exists_now"] is False, entry["name"]
        assert entry["description"].strip()
    assert outputs["forbidden_outputs"]
    assert "any_final_test_prediction" in outputs["forbidden_outputs"]
    assert outputs["locked_primary_results_are_not_replaced_by_the_refit"] is True
    assert state["stage129_refit_expected_output_count"] == 4
    assert state["stage129_refit_expected_outputs_exist_now"] is False


def test_the_twelve_fail_closed_controls_are_complete(contract, state,
                                                      roadmap_front_matter):
    controls = contract["fail_closed_controls"]
    assert [c["id"] for c in controls] == FC_IDS
    for c in controls:
        assert c["on_failure"] == "ABORT_REFIT", c["id"]
        assert c["check"].strip(), c["id"]
    assert state["stage129_refit_fail_closed_control_count"] == 12
    assert roadmap_front_matter["refit_fail_closed_control_count"] == "12"
    joined = " ".join(c["check"] for c in controls)
    for needle in ("SHA-256", "runtime versions", "1400-1402",
                   "M1_PRIMARY_FEATURE_ORDER", "final_test_rows_loaded == 0",
                   "exactly one model is fitted"):
        assert needle in joined, needle


def test_locking_the_contract_authorizes_nothing(contract, boundary, state,
                                                 roadmap_front_matter):
    ex = contract["execution_authorization"]
    assert ex["refit_execution_authorized_by_this_contract"] is False
    assert ex["refit_execution_requires_new_explicit_human_authorization"] is True
    assert ex["contract_lock_is_not_an_execution_permission"] is True
    assert ex["stage130_authorized"] is False
    assert ex["final_test_unlock_authorized"] is False
    for field in ("full_development_refit_executed", "full_development_refit_performed",
                  "trained_final_model_artifact_created", "refit_execution_authorized",
                  "stage130_authorized", "stage130_started", "retuning_authorized",
                  "final_model_reselected_by_this_action", "next_action_authorized",
                  "next_action_executes_refit", "next_action_executes_final_test",
                  "next_research_action_authorized", "merge_authorized",
                  "ready_for_review_authorized"):
        assert boundary[field] is False, field
    assert boundary["refit_execution_requires_new_explicit_human_authorization"] is True
    # ACTION-SCOPED: locking executed nothing. `stage129_refit_executed` is a
    # LIVE fact owned by the execution action, so it is not asserted here.
    assert state["stage129_refit_contract_locked_but_not_executed_at_lock_time"] is True
    assert state["stage129_refit_execution_authorized"] is False
    assert state["stage129_refit_execution_requires_new_human_authorization"] is True
    # ACTION-SCOPED: LOCKING the contract executed nothing. Its own boundary
    # records that permanently; the live global is set by the later,
    # separately authorized execution of this very contract.
    assert boundary["full_development_refit_executed"] is False
    assert boundary["full_development_refit_performed"] is False
    assert boundary["trained_final_model_artifact_created"] is False
    # MOVED from a live global proxy to an action-scoped historical fact.
    # `stage130_started` is now True in the live Handoff, because the
    # Stage130 Phase 1 manuscript evidence package exists. That happened
    # AFTER this action, and Phase 1 is PRESENTATION only. What this
    # action guarantees -- that no Stage130 SCIENTIFIC execution has
    # begun -- is asserted here instead, and its own artifacts above
    # still pin `stage130_started = False` for its own moment.
    assert state["stage130_scientific_execution_started"] is False
    # MOVED from a live global proxy to the action-scoped historical fact, as
    # above: locking read nothing, and the later authorized pass is not this
    # action's doing.
    assert state["stage129_refit_final_test_rows_read"] == 0
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert roadmap_front_matter["refit_executed"] == "false"
    assert roadmap_front_matter["refit_execution_authorized"] == "false"
    assert roadmap_front_matter["refit_next_action_authorized"] == "false"


def test_every_execution_counter_is_zero(boundary):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("model_fits", "predict_calls", "predict_proba_calls",
                "decision_function_calls", "tuning_runs", "feature_searches",
                "threshold_searches", "bootstrap_executions", "calibration_executions",
                "shap_executions", "metrics_computed", "p_values_computed",
                "row_level_scientific_data_reads", "trained_model_artifacts_written",
                "full_development_refits_executed", "final_test_rows_read",
                "new_data_files_created"):
        assert counters[key] == 0, key


def test_nothing_historical_was_modified(boundary, state):
    for field in ("historical_scientific_artifacts_modified_by_this_action",
                  "source_contracts_modified_by_this_action",
                  "locked_primary_development_results_modified_by_this_action",
                  "m1_results_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m3_cbi_disposition_modified_by_this_action",
                  "m4_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "prior_packages_modified_by_this_action",
                  "existing_pull_requests_modified_by_this_action",
                  "new_contract_term_invented_by_this_action",
                  "new_metric_computed", "new_p_value_created",
                  "inferential_superiority_claimed"):
        assert boundary[field] is False, field
    # the selection and the Holm state upstream are unchanged
    assert state["paper_winner_selected"] is True
    assert state["final_algorithm"] == "regularized_logistic_regression"
    assert state["final_configuration"] == "logistic__C_0.1"
    assert state["stage129_final_holm_reporting_status"] == (
        "HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE")
    assert state["holm_family_complete"] is False
    assert state["m2_predictive_superiority_claim_supported"] is False


# ------------------------------------------- the generator fails closed
def _run_generator(root):
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_full_development_refit_contract_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A tree with this package plus every artifact the deriver re-checks."""
    (tmp_path / _PKG_REL).mkdir(parents=True, exist_ok=True)
    for name in os.listdir(_PKG):
        with open(os.path.join(_PKG, name), "rb") as fh:
            (tmp_path / _PKG_REL / name).write_bytes(fh.read())
    prov = _load(_PROV)["source_artifacts_sha256"]
    for rel in prov:
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
    assert markers["stage129_refit_contract_status"] == STATUS
    assert markers["stage129_refit_fit_target_years"] == FIT_YEARS


@pytest.mark.parametrize("rel,key,value,needle", [
    # letting Final Test years into the fit window, or moving the window
    (_CON, "authorized_development_data", {"fit_target_years": [1393, 1400]},
     "fit window"),
    # changing the target model, its configuration or its hyperparameters
    (_CON, "selected_model", {"block": "M2", "algorithm": "xgboost",
                              "configuration_id": "logistic__C_0.1"},
     "selected model"),
    # status no longer "locked, not executed"
    (_CON, "contract_status", "EXECUTED", "status must be"),
    (_BND, "contract_status", "EXECUTED", "status must be"),
    # claiming terms were invented / not extracted
    (_CON, "every_term_is_extracted_from_a_prelocked_artifact", False, "extracted"),
    (_CON, "no_term_invented_by_this_action", False, "invent"),
    (_BND, "new_contract_term_invented_by_this_action", True, "invent"),
    # executing, authorizing or unlocking anything
    (_BND, "full_development_refit_executed", True, "full_development_refit_executed"),
    (_BND, "full_development_refit_performed", True, "full_development_refit_performed"),
    (_BND, "trained_final_model_artifact_created", True, "trained_final_model"),
    (_BND, "refit_execution_authorized", True, "refit_execution_authorized"),
    (_BND, "stage130_authorized", True, "stage130_authorized"),
    (_BND, "stage130_started", True, "stage130_started"),
    (_BND, "final_test_access_authorized", True, "final_test_access_authorized"),
    (_BND, "final_test_unlock_authorized", True, "final_test_unlock_authorized"),
    (_BND, "final_test_locked", False, "Final Test locked"),
    (_BND, "final_test_rows_read", 1, "Final Test locked"),
    (_BND, "next_action_authorized", True, "next_action_authorized"),
    (_BND, "next_action_executes_refit", True, "next_action_executes_refit"),
    (_BND, "next_action_id", "stage130-refit-execution", "pointer must be"),
    (_BND, "refit_execution_requires_new_explicit_human_authorization", False,
     "new human"),
    # re-selecting or retuning the model
    (_BND, "retuning_authorized", True, "retune"),
    (_BND, "final_model_reselected_by_this_action", True, "re-select"),
    # editing history or the sources
    (_BND, "source_contracts_modified_by_this_action", True, "source contracts"),
    (_PROV, "sources_modified_by_this_action", True, "source contracts"),
    (_BND, "historical_scientific_artifacts_modified_by_this_action", True,
     "historical_scientific_artifacts"),
    (_BND, "new_metric_computed", True, "new_metric_computed"),
    (_BND, "new_p_value_created", True, "new_p_value_created"),
    (_BND, "new_seed_introduced_by_this_action", True, "seed"),
    (_BND, "m3_lag_wdi_promoted_to_confirmatory_model", True, "promoted"),
])
def test_the_generator_fails_closed_on_tampering(sandbox, rel, key, value, needle):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob[key] = value
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


@pytest.mark.parametrize("year", FINAL_TEST_YEARS)
def test_any_final_test_year_in_the_fit_window_fails_closed(sandbox, year):
    """The single most important negative control in this package."""
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["authorized_development_data"]["fit_target_years"] = FIT_YEARS + [year]
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "fit window" in str(exc.value)


@pytest.mark.parametrize("field", [
    "refit_may_read_final_test", "refit_may_predict_on_final_test",
    "refit_may_evaluate_on_final_test", "final_test_access_authorized",
])
def test_opening_the_final_test_boundary_fails_closed(sandbox, field):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["final_test_boundary"][field] = True
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert field in str(exc.value)


@pytest.mark.parametrize("field", [
    "refit_execution_authorized_by_this_contract", "stage130_authorized",
    "final_test_unlock_authorized",
])
def test_self_authorizing_execution_fails_closed(sandbox, field):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["execution_authorization"][field] = True
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert field in str(exc.value)


def test_an_expected_output_that_already_exists_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["expected_outputs"]["artifacts"][0]["exists_now"] = True
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "may not already exist" in str(exc.value)


@pytest.mark.parametrize("mutation,needle", [
    ({"rule": "refit_in_sample_F2_threshold"}, "threshold rule"),
    ({"tie_break": "lower_threshold"}, "threshold rule"),
    ({"never_optimize_on_final_test": False}, "never_optimize_on_final_test"),
    ({"threshold_is_derived_from_development_oof_only": False},
     "threshold_is_derived_from_development_oof_only"),
    ({"threshold_search_on_refit_output_authorized": True}, "threshold search"),
])
def test_moving_the_threshold_off_development_oof_fails_closed(sandbox, mutation,
                                                               needle):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["threshold"].update(mutation)
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


def test_a_drifted_feature_order_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["features"]["features_exact_order"] = list(reversed(FEATURES))
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "feature order" in str(exc.value)


def test_drifted_hyperparameters_fail_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["selected_model"]["hyperparameters"] = dict(HYPERPARAMS, C=1.0)
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "hyperparameters" in str(exc.value)


def test_a_drifted_runtime_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["environment"]["runtime_versions"] = dict(RUNTIME, python="3.14.0")
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "runtime_versions" in str(exc.value)


def test_a_drifted_preprocessing_order_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    order = list(blob["preprocessing"]["continuous_pipeline_order"])
    order[2], order[5] = order[5], order[2]      # clip after impute
    blob["preprocessing"]["continuous_pipeline_order"] = order
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "pipeline order" in str(exc.value)


@pytest.mark.parametrize("drop", FC_IDS[:3])
def test_a_missing_fail_closed_control_fails_closed(sandbox, drop):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["fail_closed_controls"] = [
        c for c in blob["fail_closed_controls"] if c["id"] != drop]
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "fail-closed controls" in str(exc.value)


def test_a_control_that_does_not_abort_fails_closed(sandbox):
    import update_ai_handoff as gen
    blob = _load(_CON)
    blob["fail_closed_controls"][0]["on_failure"] = "WARN"
    _write(str(sandbox), _CON, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "abort on failure" in str(exc.value)


def test_a_drifted_source_artifact_fails_closed(sandbox):
    """If a cited frozen contract changes, the extraction is no longer anchored
    and the build must fail rather than publish a stale contract."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _PRE_REL).read_text(encoding="utf-8"))
    blob["clip_percentiles_note"] = "tampered"
    _write(str(sandbox), _PRE_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "drifted from its pinned SHA-256" in str(exc.value)


def test_a_nonzero_counter_fails_closed(sandbox):
    import update_ai_handoff as gen
    for key in ("model_fits", "full_development_refits_executed",
                "trained_model_artifacts_written", "final_test_rows_read"):
        blob = _load(_BND)
        blob["counters"][key] = 1
        _write(str(sandbox), _BND, blob)
        with pytest.raises(gen.HandoffError) as exc:
            _run_generator(str(sandbox))
        assert key in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _CON)
    assert _run_generator(str(sandbox)) == {}


# --------------------------- validator, idempotency and rendered documents
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage129_full_development_refit_contract_markers(REPO_ROOT)
    second = gen.derive_stage129_full_development_refit_contract_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["stage129_refit_contract_locked_but_not_executed_at_lock_time"] is True


def test_current_state_renders_the_contract_as_locked_not_executed():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert "Full-Development Refit contract LOCKED (not executed)" in text
    assert STATUS in text
    assert "development_OOF_F2_maximizing_threshold" in text
    assert "logistic__C_0.1" in text
    assert NEXT_ACTION in text


def test_the_readme_documents_the_contract_in_english_and_persian():
    # the README wraps prose across lines, so compare against the unwrapped
    # form rather than depending on where a line happens to break
    readme = _text(f"{_PKG_REL}/"
                   "README_STAGE129_FULL_DEVELOPMENT_REFIT_CONTRACT_LOCK.md")
    flat = re.sub(r"\s+", " ", readme)
    for phrase in ("PROSPECTIVELY_LOCKED_NOT_EXECUTED",
                   "no statistic carried over from any fold",
                   "development-OOF quantity",
                   "FAIL_CLOSED_DO_NOT_REFIT",
                   "future, separately authorized step"):
        assert phrase in flat, phrase
    for phrase in ("ممیزی و قفل‌کردن قرارداد", "هیچ برازشی انجام نشده است",
                   "مجوز انسانی جداگانه", "قفل و خوانده‌نشده"):
        assert phrase in flat, phrase


def test_roadmap_records_the_contract_lock(roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["refit_contract_action_id"] == ACTION_ID
    assert fm["refit_contract_status"] == STATUS
    assert fm["refit_fit_target_years"] == "1393-1399"
    assert fm["refit_final_test_target_years"] == "1400-1402"
    assert fm["refit_terms_extracted_not_invented"] == "true"
    assert fm["refit_execution_requires_new_human_authorization"] == "true"
    assert fm["next_research_action_authorized"] == "false"
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert STATUS in body


# --------------------------------------------------------- package hygiene
def test_no_model_or_data_artifact_was_committed():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_full_development_refit_contract_lock.json")
    assert manifest["trained_model_artifacts_committed"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["full_development_refit_executed"] is False
    assert manifest["refit_execution_authorized"] is False


def test_package_hash_manifest_matches_every_file():
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_full_development_refit_contract_lock.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
