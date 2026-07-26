"""Tests for Stage126 — M1 Retained Design Freeze (decision-freeze-only, no execution).

These tests validate the frozen design package's structure, the retained
9-feature order, that the three retained configurations match
`stage126_m1_selected_configurations.json` exactly, that no winner-selection
or execution flag is true, and that the final-test firewall remains fully
locked. No model is fit or predicted by this test module.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE126 = os.path.join(REAL_ROOT, "stage126")

FREEZE_PATH = os.path.join(STAGE126, "stage126_m1_retained_design_freeze.json")
AUTH_PATH = os.path.join(
    STAGE126, "stage126_m1_retained_design_freeze_human_authorization_record.json"
)
METADATA_PATH = os.path.join(
    STAGE126, "metadata_and_hashes_stage126_m1_retained_design_freeze.json"
)
SELECTED_CONFIGS_PATH = os.path.join(
    STAGE126, "stage126_m1_selected_configurations.json"
)
STAGE125 = os.path.join(REAL_ROOT, "stage125")
METRICS_UNCERTAINTY_CONTRACT_PATH = os.path.join(
    STAGE125, "part4_metrics_uncertainty_contract_stage125.json"
)
PREPROCESSING_CONTRACT_PATH = os.path.join(
    STAGE125, "part4_preprocessing_contract_stage125.json"
)
TEMPORAL_SPLIT_CONTRACT_PATH = os.path.join(
    STAGE125, "part4_temporal_split_contract_stage125.json"
)
M1_ENTRY_CONTRACT_PATH = os.path.join(
    STAGE125, "part5_stage126_m1_entry_contract_stage125.json"
)
MODEL_SPECIFICATIONS_PATH = os.path.join(
    STAGE125, "part4_model_specifications_stage125.json"
)

EXPECTED_FEATURE_ORDER = (
    "log_total_assets",
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
)


@pytest.fixture(scope="module")
def freeze():
    with open(FREEZE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def auth_record():
    with open(AUTH_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def metadata():
    with open(METADATA_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def selected_configs():
    with open(SELECTED_CONFIGS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def metrics_uncertainty_contract():
    with open(METRICS_UNCERTAINTY_CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def preprocessing_contract_canonical():
    with open(PREPROCESSING_CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def temporal_split_contract_canonical():
    with open(TEMPORAL_SPLIT_CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def m1_entry_contract_canonical():
    with open(M1_ENTRY_CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def model_specifications_canonical():
    with open(MODEL_SPECIFICATIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Identity / scope
# --------------------------------------------------------------------------- #

def test_decision_id_and_scope(freeze):
    assert freeze["decision_id"] == "stage126-m1-retained-design-freeze"
    assert freeze["decision_type"] == "design_freeze_only_no_execution"
    scope = freeze["authorization_scope"]
    assert scope["authorized_action_id"] == "stage126-m1-retained-design-freeze"
    forbidden = {
        "final_test_access",
        "final_test_evaluation",
        "m2_start",
        "m3_start",
        "m4_start",
        "paper_winner_selection",
        "final_model_selection",
        "full_development_refit",
        "hyperparameter_retuning",
    }
    assert forbidden <= set(scope["not_authorized"])


def test_sample_and_target(freeze):
    assert freeze["sample"] == "main_rule_a_primary"
    assert freeze["target"] == "FD_target_main_t_plus_1"


def test_next_and_last_action_ids(freeze):
    assert freeze["last_completed_research_action_id"] == "stage126-m1-retained-design-freeze"
    assert freeze["next_research_action_id"] == "stage127-m2-market-data-gate"


# --------------------------------------------------------------------------- #
# Feature order
# --------------------------------------------------------------------------- #

def test_feature_order_exact(freeze):
    assert tuple(freeze["M1_PRIMARY_FEATURE_ORDER"]) == EXPECTED_FEATURE_ORDER


# --------------------------------------------------------------------------- #
# Retained configurations must match selected_configurations.json exactly
# --------------------------------------------------------------------------- #

def test_logistic_config_matches_selected(freeze, selected_configs):
    frozen = freeze["retained_model_families"]["logistic__C_0.1"]
    src = selected_configs["regularized_logistic_regression"]
    assert frozen["source_configuration_id"] == src["configuration_id"] == "logistic__C_0.1"
    assert frozen["hyperparameters"] == src["hyperparameters"] == {
        "C": 0.1, "max_iter": 5000, "penalty": "l2", "solver": "liblinear"
    }


def test_rf_config_matches_selected(freeze, selected_configs):
    key = "rf__depth_3__maxfeat_'sqrt'__leaf_10"
    frozen = freeze["retained_model_families"][key]
    src = selected_configs["random_forest"]
    assert frozen["source_configuration_id"] == src["configuration_id"] == key
    assert frozen["hyperparameters"] == src["hyperparameters"] == {
        "bootstrap": True,
        "max_depth": 3,
        "max_features": "sqrt",
        "min_samples_leaf": 10,
        "n_estimators": 500,
    }


def test_xgboost_config_matches_selected(freeze, selected_configs):
    key = "xgboost__lr_0.03__depth_2__mcw_1__lambda_1"
    frozen = freeze["retained_model_families"][key]
    src = selected_configs["xgboost"]
    assert frozen["source_configuration_id"] == src["configuration_id"] == key
    assert frozen["hyperparameters"] == src["hyperparameters"] == {
        "colsample_bytree": 0.8,
        "early_stopping": False,
        "eval_metric": "aucpr",
        "gamma": 0,
        "learning_rate": 0.03,
        "max_depth": 2,
        "min_child_weight": 1,
        "n_estimators": 300,
        "n_jobs": 1,
        "objective": "binary:logistic",
        "reg_lambda": 1,
        "subsample": 0.8,
        "tree_method": "hist",
    }


# --------------------------------------------------------------------------- #
# Preprocessing / imbalance / folds / metrics / procedures
# --------------------------------------------------------------------------- #

def test_preprocessing_contract_fields(freeze):
    pp = freeze["preprocessing_contract"]
    assert pp["clip_percentiles"] == [1, 99]
    assert pp["clip_bounds_trained_on"] == "training_fold_only"
    assert pp["missingness_indicators"].startswith("appended_unstandardized")
    assert "logistic_only" in pp["standardization"]


def test_imbalance_strategy(freeze):
    imb = freeze["imbalance_strategy"]
    assert imb["regularized_logistic_regression"] == {"class_weight": "balanced"}
    assert imb["random_forest"] == {"class_weight": "balanced_subsample"}
    assert "scale_pos_weight" in imb["xgboost"]
    assert imb["smotenc_status"] == "robustness_only_not_retained"


def test_temporal_folds(freeze):
    folds = freeze["temporal_folds"]
    assert folds["fold1"]["train_target_years"] == [1393, 1394, 1395]
    assert folds["fold1"]["validation_target_years"] == [1396, 1397]
    assert folds["fold2"]["train_target_years"] == [1393, 1394, 1395, 1396, 1397]
    assert folds["fold2"]["validation_target_years"] == [1398, 1399]
    assert folds["locked_final_test_target_years"] == [1400, 1401, 1402]
    assert folds["availability_lag_jalali_months"] == 4


def test_metric_definitions(freeze):
    md = freeze["metric_definitions"]
    assert md["primary_metric"] == "PR-AUC"
    assert set(md["secondary_metrics"]) == {"ROC-AUC", "Brier_score", "Recall@10%", "Lift@10%"}
    assert md["topk_rule"] == "K_y = ceil(0.10 * N_y)"


def test_calibration_procedure_not_executed(freeze):
    cal = freeze["calibration_reporting_procedure"]
    assert cal["isotonic_calibration_authorized"] is False
    assert cal["executed_in_this_freeze"] is False


def test_uncertainty_procedure_not_executed(freeze):
    unc = freeze["uncertainty_procedure"]
    assert unc["method"] == "paired_company_cluster_bootstrap"
    assert unc["cluster_unit"] == "ticker"
    assert unc["replicates"] == 2000
    assert unc["seed"] == 20260724
    assert unc["min_valid_replicates"] == 1000
    assert unc["executed_in_this_freeze"] is False


def test_multiplicity_plan_not_executed(freeze):
    mp = freeze["multiplicity_plan"]
    assert mp["correction"] == "Holm"
    assert mp["alpha"] == 0.05
    assert mp["executed_in_this_freeze"] is False


# --------------------------------------------------------------------------- #
# Source-derived completeness: compare against canonical stage125 contracts,
# not only hardcoded literals embedded in this test file. Fail-closed: if a
# canonical source is missing or its shape changes unexpectedly, these fail
# rather than silently passing against a stale hardcoded copy.
# --------------------------------------------------------------------------- #

def test_multiplicity_families_match_canonical_sap_exactly(
    freeze, metrics_uncertainty_contract
):
    mp = freeze["multiplicity_plan"]
    canonical = metrics_uncertainty_contract["multiplicity"]
    assert set(mp["families"]) == set(canonical["confirmatory_family_1"])
    assert set(mp["conditionally_admitted_families_if_later_stages_proceed"]) == set(
        canonical["confirmatory_family_2_adjacent_block_gains_if_admitted"]
    )
    assert mp["correction"] == canonical["correction"]
    assert mp["alpha"] == canonical["alpha"]


def test_metric_definitions_match_canonical_contract(
    freeze, metrics_uncertainty_contract
):
    md = freeze["metric_definitions"]
    assert md["primary_metric"] == metrics_uncertainty_contract["primary_metric"]
    assert set(md["secondary_metrics"]) == set(
        metrics_uncertainty_contract["secondary_metrics"]
    )
    assert (
        md["thresholded_secondary"]["rule"]
        == metrics_uncertainty_contract["thresholded_secondary"]["rule"]
    )
    assert (
        md["thresholded_secondary"]["tie_break"]
        == metrics_uncertainty_contract["thresholded_secondary"]["tie_break"]
    )
    assert (
        md["topk"]["ranking_order"]
        == metrics_uncertainty_contract["topk"]["ranking_order"]
    )
    assert md["topk"]["fraction"] == metrics_uncertainty_contract["topk"]["fraction"]


def test_uncertainty_procedure_matches_canonical_contract(
    freeze, metrics_uncertainty_contract
):
    unc = freeze["uncertainty_procedure"]
    canonical = metrics_uncertainty_contract["uncertainty"]
    assert unc["method"] == canonical["method"]
    assert unc["cluster_unit"] == canonical["cluster"]
    assert unc["replicates"] == canonical["replicates"]
    assert unc["seed"] == canonical["bootstrap_seed"]
    assert unc["min_valid_replicates"] == canonical["min_valid_replicates"]
    assert (
        unc["same_resampled_rows_across_compared_models"]
        == canonical["same_resampled_rows_for_all_compared_models"]
    )
    assert (
        unc["valid_replicate_requires_both_classes"]
        == canonical["valid_replicate_requires_both_classes"]
    )


def test_calibration_procedure_matches_canonical_contract(
    freeze, metrics_uncertainty_contract
):
    cal = freeze["calibration_reporting_procedure"]
    canonical = metrics_uncertainty_contract["calibration"]
    assert cal["isotonic_calibration_authorized"] == canonical["isotonic_authorized"]
    assert cal["logit_clip_epsilon"] == canonical["logit_clip_epsilon"]
    assert (
        cal["skip_recalibration_if_oof_positives_lt"]
        == canonical["skip_recalibration_if_oof_positives_lt"]
    )
    assert set(cal["reported_diagnostics"]) == set(canonical["report"])


def test_preprocessing_contract_matches_canonical_source(
    freeze, preprocessing_contract_canonical
):
    pp = freeze["preprocessing_contract"]
    assert pp["continuous_pipeline_order"] == preprocessing_contract_canonical[
        "continuous_pipeline_order"
    ]
    assert pp["fit_scope"] == preprocessing_contract_canonical["fit_scope"]
    assert (
        pp["forbidden_fit_on"] == preprocessing_contract_canonical["forbidden_fit_on"]
    )


def test_temporal_folds_match_canonical_source(
    freeze, temporal_split_contract_canonical
):
    folds = freeze["temporal_folds"]
    c = temporal_split_contract_canonical
    assert (
        folds["fold1"]["train_target_years"]
        == c["temporal_validation_fold_1"]["train_target_years"]
    )
    assert (
        folds["fold1"]["validation_target_years"]
        == c["temporal_validation_fold_1"]["validation_target_years"]
    )
    assert (
        folds["fold2"]["train_target_years"]
        == c["temporal_validation_fold_2"]["train_target_years"]
    )
    assert (
        folds["fold2"]["validation_target_years"]
        == c["temporal_validation_fold_2"]["validation_target_years"]
    )
    assert folds["locked_final_test_target_years"] == c["final_test_target_years"]


def test_sample_target_features_match_canonical_entry_contract(
    freeze, m1_entry_contract_canonical
):
    spec = m1_entry_contract_canonical["primary_specification"]
    assert freeze["sample"] == spec["sample"]
    assert freeze["target"] == spec["target"]
    assert freeze["M1_PRIMARY_FEATURE_ORDER"] == spec["features_exact_order"]
    assert len(freeze["M1_PRIMARY_FEATURE_ORDER"]) == spec["feature_count"]
    # Retained families must be exactly the canonical primary model set.
    frozen_families = {
        cfg["family"] for cfg in freeze["retained_model_families"].values()
    }
    assert frozen_families == set(spec["models"])
    assert freeze["metric_definitions"]["primary_metric"] == spec["primary_metric"]
    assert (
        freeze["sample_target_feature_canonical_source_path"]
        == "project/stage125/part5_stage126_m1_entry_contract_stage125.json"
    )


def test_imbalance_policy_matches_canonical_model_specifications(
    freeze, model_specifications_canonical
):
    imb = freeze["imbalance_strategy"]
    canonical = model_specifications_canonical["imbalance_handling_primary"]
    assert (
        imb["regularized_logistic_regression"]["class_weight"]
        == canonical["logistic_regression"]["class_weight"]
    )
    assert (
        imb["random_forest"]["class_weight"]
        == canonical["random_forest"]["class_weight"]
    )
    assert (
        imb["xgboost"]["scale_pos_weight"]
        == canonical["xgboost"]["scale_pos_weight"]
    )
    # SMOTENC stays robustness-only in the canonical source too.
    assert model_specifications_canonical["smote_robustness"]["primary"] is False
    assert imb["smotenc_status"] == "robustness_only_not_retained"
    assert (
        imb["canonical_source_path"]
        == "project/stage125/part4_model_specifications_stage125.json"
    )


def test_threshold_rule_matches_canonical_contract(
    freeze, metrics_uncertainty_contract
):
    frozen = freeze["metric_definitions"]["thresholded_secondary"]
    canonical = metrics_uncertainty_contract["thresholded_secondary"]
    assert frozen["rule"] == canonical["rule"]
    assert frozen["tie_break"] == canonical["tie_break"]
    assert frozen["never_optimize_on_final_test"] is True
    assert canonical["never_optimize_on_final_test"] is True


def test_topk_definition_and_ranking_match_canonical_contract(
    freeze, metrics_uncertainty_contract
):
    md = freeze["metric_definitions"]
    canonical = metrics_uncertainty_contract["topk"]
    assert md["topk_rule"] == canonical["definition"]
    assert md["topk"]["fraction"] == canonical["fraction"]
    assert md["topk"]["ranking_order"] == canonical["ranking_order"]
    assert md["topk"]["optimize_K_after_results"] is False
    assert canonical["optimize_K_after_results"] is False


def test_non_authoritative_summaries_are_labeled(freeze):
    for key in (
        "metric_definitions",
        "calibration_reporting_procedure",
        "uncertainty_procedure",
        "preprocessing_contract",
        "temporal_folds",
        "imbalance_strategy",
    ):
        assert freeze[key].get("non_authoritative_summary") is True, (
            f"{key} must be explicitly labeled non_authoritative_summary "
            "since a pinned canonical source (by path + SHA-256) exists"
        )


# --------------------------------------------------------------------------- #
# No winner-selection language / flags true
# --------------------------------------------------------------------------- #

def test_no_winner_selection_flags_true(freeze):
    sf = freeze["status_flags"]
    assert sf["paper_winner_selected"] is False
    assert sf["final_model_selected"] is False
    assert sf["full_development_refit_performed"] is False
    assert sf["final_test_unlocked"] is False
    assert sf["final_test_access_authorized"] is False
    assert sf["final_test_evaluation_performed"] is False
    assert sf["m2_started"] is False
    assert sf["retained_design_freeze_completed"] is True


def test_no_winner_language_in_json_text():
    with open(FREEZE_PATH, encoding="utf-8") as f:
        raw = f.read()
    forbidden_substrings = [
        '"paper_winner_selected": true',
        '"final_model_selected": true',
        '"m2_started": true',
        '"final_test_unlocked": true',
    ]
    for s in forbidden_substrings:
        assert s not in raw


# --------------------------------------------------------------------------- #
# Final-test firewall
# --------------------------------------------------------------------------- #

def test_final_test_firewall_locked(freeze):
    fw = freeze["final_test_firewall"]
    assert fw["final_test_locked"] is True
    assert fw["final_test_unlocked"] is False
    assert fw["final_test_access_authorized"] is False
    assert fw["final_test_predictor_values_inspected"] is False
    assert fw["final_test_target_values_inspected"] is False
    assert fw["final_test_evaluation_performed"] is False
    assert fw["full_development_refit_performed"] is False


# --------------------------------------------------------------------------- #
# Authorization provenance is referenced, never duplicated, by the freeze
# --------------------------------------------------------------------------- #

def test_freeze_does_not_duplicate_human_authorization_prose(freeze):
    # The freeze artifact must not carry any field whose name implies it holds
    # verbatim human authorization text -- the record is the single authority.
    for banned in (
        "human_decision_text",
        "human_decision_text_sha256",
        "human_authorization_text",
        "human_authorization_text_sha256",
        "human_source_utterance",
    ):
        assert banned not in freeze, f"freeze must not contain {banned}"


def test_freeze_references_authorization_record(freeze):
    rel = freeze["human_authorization_record_path"]
    assert rel == (
        "project/stage126/"
        "stage126_m1_retained_design_freeze_human_authorization_record.json"
    )
    assert freeze["authorized_action_id"] == "stage126-m1-retained-design-freeze"
    assert freeze["authorization_scope_limited_to_this_action_only"] is True
    abs_path = os.path.join(os.path.dirname(REAL_ROOT), rel)
    assert os.path.isfile(abs_path)
    with open(abs_path, "rb") as f:
        got = hashlib.sha256(f.read()).hexdigest()
    assert got == freeze["human_authorization_record_sha256"]


# --------------------------------------------------------------------------- #
# Source artifact hashes are real and verifiable on disk
# --------------------------------------------------------------------------- #

def test_source_artifact_hashes_verify_on_disk(freeze):
    repo_root = os.path.dirname(REAL_ROOT)
    for rel_path, expected_hash in freeze["source_artifacts_sha256"].items():
        abs_path = os.path.join(repo_root, rel_path)
        assert os.path.isfile(abs_path), f"missing source artifact: {rel_path}"
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            h.update(f.read())
        assert h.hexdigest() == expected_hash, f"hash mismatch for {rel_path}"


def test_rationale_cites_real_paths(freeze):
    rationale = freeze["robustness_rationale"]
    all_paths = []
    for entry in rationale.values():
        if "source_artifact" in entry:
            all_paths.append(entry["source_artifact"])
        if "source_artifacts" in entry:
            all_paths.extend(entry["source_artifacts"])
    repo_root = os.path.dirname(REAL_ROOT)
    assert all_paths, "rationale must cite at least one artifact"
    for rel_path in all_paths:
        assert os.path.isfile(os.path.join(repo_root, rel_path)), rel_path


# --------------------------------------------------------------------------- #
# Human authorization record — scope
# --------------------------------------------------------------------------- #

def test_authorization_record_scope(auth_record):
    assert auth_record["authorized_action_id"] == "stage126-m1-retained-design-freeze"
    assert auth_record["scope_limited_to_this_action_only"] is True
    does_not_extend_to = set(auth_record["does_not_extend_to"])
    assert "stage127-m2-market-data-gate" in does_not_extend_to
    assert "final_test_access" in does_not_extend_to
    assert "final_model_selection" in does_not_extend_to
    assert auth_record["final_test_access_authorized"] is False
    assert auth_record["m2_authorized"] is False
    assert auth_record["merge_authorized"] is False


def test_authorization_provenance_fields(auth_record):
    # human_source_utterance is the exact human-typed message; it must be
    # hashed SEPARATELY from the derived/normalized scope paraphrase, and
    # the normalized scope must be explicitly labeled as non-verbatim.
    got_source = hashlib.sha256(
        auth_record["human_source_utterance"].encode("utf-8")
    ).hexdigest()
    assert got_source == auth_record["human_source_utterance_sha256"]
    assert auth_record["resolved_authorized_action_id"] == "stage126-m1-retained-design-freeze"
    assert (
        auth_record["normalized_authorization_scope_is_derived_not_verbatim_human_text"]
        is True
    )
    got_scope = hashlib.sha256(
        auth_record["normalized_authorization_scope"].encode("utf-8")
    ).hexdigest()
    assert got_scope == auth_record["normalized_authorization_scope_sha256"]
    # The two hashes must never collide/alias one another.
    assert got_source != got_scope


def test_freeze_and_record_agree_on_authorized_action(freeze, auth_record):
    assert (
        freeze["authorized_action_id"]
        == auth_record["resolved_authorized_action_id"]
        == auth_record["authorized_action_id"]
        == "stage126-m1-retained-design-freeze"
    )
    assert freeze["authorization_scope_limited_to_this_action_only"] is True
    assert auth_record["scope_limited_to_this_action_only"] is True


# --------------------------------------------------------------------------- #
# Metadata / hashes package
# --------------------------------------------------------------------------- #

def test_metadata_package_hashes_verify(metadata):
    repo_root = os.path.dirname(REAL_ROOT)
    for rel_path, expected_hash in metadata["package_artifacts_sha256"].items():
        abs_path = os.path.join(repo_root, rel_path)
        assert os.path.isfile(abs_path)
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            h.update(f.read())
        assert h.hexdigest() == expected_hash


def test_metadata_decision_id(metadata):
    assert metadata["decision_id"] == "stage126-m1-retained-design-freeze"
