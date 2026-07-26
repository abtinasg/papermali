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
    assert set(mp["families"]) == {"Logistic-RF", "Logistic-XGB", "RF-XGB"}
    assert mp["executed_in_this_freeze"] is False


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
# Human decision text hash
# --------------------------------------------------------------------------- #

def test_human_decision_text_hash_matches(freeze):
    got = hashlib.sha256(freeze["human_decision_text"].encode("utf-8")).hexdigest()
    assert got == freeze["human_decision_text_sha256"]


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


def test_authorization_text_hash_matches_freeze(freeze, auth_record):
    assert auth_record["human_authorization_text"] == freeze["human_decision_text"]
    assert auth_record["human_authorization_text_sha256"] == freeze["human_decision_text_sha256"]


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
