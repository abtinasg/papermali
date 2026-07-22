"""Tests for Stage126 M1 — Robustness Part 0 Decision Lock.

Decision lock only: these tests confirm the contract is recorded correctly and
fail-closed, and that NO robustness execution / model fit / prediction / SMOTE /
SMOTENC / SHAP / network / final-test access is declared or performed. They must
never fit a model.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os

import pytest

from src import stage126_m1_robustness_part0_decision_lock as p0

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGE126 = os.path.join(REAL_ROOT, "project", "stage126")

EXPECTED_CATEGORY_ORDER = (
    "m1_target_proximity_six_feature_set",
    "main_rule_b_listing_robustness",
    "expanded_rule_a_company_scope_robustness",
    "expanded_rule_b_combined_robustness",
    "persistent_loss_robustness_target",
    "smote_training_fold_only_robustness",
)


def _record() -> dict:
    return p0.build_decision_record()


def _on_disk_record() -> dict:
    with open(os.path.join(STAGE126, p0.F_RECORD), encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Human decision text
# --------------------------------------------------------------------------- #

def test_decision_text_sha256_recomputes():
    got = hashlib.sha256(p0.HUMAN_DECISION_TEXT_FA.encode("utf-8")).hexdigest()
    assert got == p0.HUMAN_DECISION_TEXT_SHA256


def test_wrong_decision_text_hash_fails_closed():
    orig = p0.HUMAN_DECISION_TEXT_SHA256
    p0.HUMAN_DECISION_TEXT_SHA256 = "0" * 64
    try:
        with pytest.raises(p0.QCFail):
            p0.verify_decision_text()
    finally:
        p0.HUMAN_DECISION_TEXT_SHA256 = orig


def test_on_disk_record_decision_text_byte_identical():
    rec = _on_disk_record()
    assert rec["human_decision_text"] == p0.HUMAN_DECISION_TEXT_FA
    assert (
        hashlib.sha256(rec["human_decision_text"].encode("utf-8")).hexdigest()
        == p0.HUMAN_DECISION_TEXT_SHA256
    )
    assert rec["human_decision_text_sha256"] == p0.HUMAN_DECISION_TEXT_SHA256


# --------------------------------------------------------------------------- #
# Positive contract facts
# --------------------------------------------------------------------------- #

def test_positive_top_level_flags():
    r = _record()
    assert r["decision_locked"] is True
    assert r["execution_authorized"] is False
    assert r["m1_robustness_started"] is False
    assert r["m1_robustness_completed"] is False
    assert r["full_development_refit_authorized"] is False
    assert r["full_development_refit_performed"] is False
    assert r["final_test_access_authorized"] is False
    assert r["final_test_unlocked"] is False
    assert r["final_test_evaluation_authorized"] is False
    assert r["final_test_evaluation_performed"] is False
    assert r["shap_authorized"] is False
    assert r["m2_m3_m4_authorized"] is False
    assert r["one_category_per_micro_part_pr"] is True
    assert r["part0_authorizes_part1"] is False


def test_exactly_six_categories_in_binding_order():
    r = _record()
    ids = tuple(c["category_id"] for c in r["categories"])
    assert ids == EXPECTED_CATEGORY_ORDER
    assert tuple(r["execution_order"]) == EXPECTED_CATEGORY_ORDER
    assert len(r["categories"]) == 6
    assert [c["order"] for c in r["categories"]] == [1, 2, 3, 4, 5, 6]


def test_no_extra_or_missing_category():
    r = _record()
    ids = {c["category_id"] for c in r["categories"]}
    assert ids == set(EXPECTED_CATEGORY_ORDER)


def test_model_families_all_three_no_others():
    r = _record()
    assert r["global_execution_rules"]["model_families"] == [
        "regularized_logistic_regression", "random_forest", "xgboost",
    ]


def test_no_retuning_and_selected_configs_locked():
    r = _record()
    nr = r["global_execution_rules"]["no_retuning"]
    assert nr["second_tuning_search"] is False
    assert nr["robustness_may_not_replace_selected_configurations"] is True
    assert nr["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }


def test_fold_years_locked():
    r = _record()
    tf = r["global_execution_rules"]["temporal_folds"]
    assert tf["fold1"]["train_target_years"] == [1393, 1394, 1395]
    assert tf["fold1"]["validation_target_years"] == [1396, 1397]
    assert tf["fold2"]["train_target_years"] == [1393, 1394, 1395, 1396, 1397]
    assert tf["fold2"]["validation_target_years"] == [1398, 1399]
    assert tf["only_development_years_loaded"] == [
        1393, 1394, 1395, 1396, 1397, 1398, 1399,
    ]


def test_seed_list_locked():
    r = _record()
    seeds = r["global_execution_rules"]["seeds_without_retuning"]
    assert seeds["rf_xgboost_model_seeds"] == [
        20260719, 20260720, 20260721, 20260722, 20260723,
    ]
    assert seeds["no_tuning_seeds_used"] is True


def test_metric_list_locked():
    r = _record()
    m = r["global_execution_rules"]["metrics"]
    assert m["report"] == ["PR-AUC", "ROC-AUC", "Brier_score", "Recall@10%", "Lift@10%"]
    assert m["scopes"] == [
        "fold1_validation", "fold2_validation", "pooled_development_oof",
    ]
    assert m["topk_rule"] == "K_y = ceil(0.10 * N_y)"


def test_bootstrap_holm_winner_not_executed():
    r = _record()
    forbidden = r["global_execution_rules"]["metrics"][
        "not_executed_in_robustness_micro_parts"
    ]
    for key in ("paired_bootstrap", "holm_correction", "p_values", "winner_selection"):
        assert key in forbidden


def test_scientific_interpretation_sensitivity_only():
    r = _record()
    si = r["global_execution_rules"]["scientific_interpretation"]
    assert si["all_categories"] == "sensitivity_analysis_only"
    for k in (
        "change_a_selected_configuration",
        "change_the_locked_primary_model_family_ordering",
        "select_a_final_paper_winner",
        "unlock_the_final_test",
        "trigger_an_automatic_refit",
        "advance_m2_m3_m4",
    ):
        assert k in si["may_not"]


# --------------------------------------------------------------------------- #
# Category-specific mappings
# --------------------------------------------------------------------------- #

def test_category_sample_target_feature_mapping():
    r = _record()
    by_id = {c["category_id"]: c for c in r["categories"]}
    assert by_id["m1_target_proximity_six_feature_set"]["sample"] == "main_rule_a_primary"
    assert by_id["m1_target_proximity_six_feature_set"]["target"] == "FD_target_main_t_plus_1"
    assert by_id["m1_target_proximity_six_feature_set"]["feature_set"] == \
        "M1_TARGET_PROXIMITY_ROBUSTNESS"
    assert by_id["m1_target_proximity_six_feature_set"]["features_exact_order"] == [
        "log_total_assets", "current_ratio", "roa_period_adjusted",
        "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
    ]
    for cid in (
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
    ):
        assert by_id[cid]["sample"] == cid
        assert by_id[cid]["target"] == "FD_target_main_t_plus_1"
        assert by_id[cid]["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"


def test_persistent_loss_restricted_to_primary_sample():
    r = _record()
    by_id = {c["category_id"]: c for c in r["categories"]}
    cat = by_id["persistent_loss_robustness_target"]
    assert cat["sample"] == "main_rule_a_primary"
    assert cat["target"] == "FD_target_persistent_loss_robustness_t_plus_1"
    # Not multiplied across all four samples.
    assert cat["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"


def test_smote_category_rules():
    r = _record()
    by_id = {c["category_id"]: c for c in r["categories"]}
    s = by_id["smote_training_fold_only_robustness"]["smote_rules"]
    assert s["class_weighting_disabled"] is True
    assert s["xgboost_scale_pos_weight"] == 1
    assert s["second_tuning_search"] is False
    assert s["uses_selected_non_weight_hyperparameters"] is True
    assert s["applied_only_inside_each_training_fold"] is True
    assert s["validation_data_never_resampled"] is True
    assert s["final_test_never_accessed_or_resampled"] is True
    assert s["k_neighbors"] == "min(5, training_minority_count - 1)"
    assert s["sampler_random_state"] == 20260725
    # SMOTENC categorical missingness-indicator rule must be present.
    assert "SMOTENC" in s["missingness_indicator_rule"]
    assert "categorical" in s["missingness_indicator_rule"]
    assert "binary 0/1" in s["missingness_indicator_rule"]


# --------------------------------------------------------------------------- #
# Cross-validation against frozen contracts / immutable artifacts
# --------------------------------------------------------------------------- #

def test_frozen_contract_crosscheck_passes_on_real_repo():
    # Must not raise on the real repository.
    p0.verify_against_frozen_contracts(_path())


def _path():
    from pathlib import Path
    return Path(REAL_ROOT)


def test_primary_artifacts_byte_identical():
    observed = p0.verify_primary_artifacts_immutable(_path())
    assert observed == p0.PRIMARY_ARTIFACT_SHA256


def test_primary_artifact_hash_change_fails_closed(tmp_path):
    # Corrupt a copy of a primary artifact and confirm fail-closed.
    import shutil
    from pathlib import Path
    fake = tmp_path / "project" / "stage126"
    fake.mkdir(parents=True)
    # Copy every pinned artifact, then tamper one.
    for rel in p0.PRIMARY_ARTIFACT_SHA256:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REAL_ROOT, rel), dst)
    tampered = tmp_path / "project/stage126/stage126_m1_selected_configurations.json"
    tampered.write_text(tampered.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(p0.QCFail):
        p0.verify_primary_artifacts_immutable(Path(tmp_path))


def test_registered_categories_match_frozen_entry_contract():
    entry_path = os.path.join(
        REAL_ROOT, "project", "stage125",
        "part5_stage126_m1_entry_contract_stage125.json",
    )
    with open(entry_path, encoding="utf-8") as f:
        entry = json.load(f)
    registered = tuple(
        c["category_id"]
        for c in entry["registered_m1_robustness_after_primary_lock"]
    )
    assert registered == EXPECTED_CATEGORY_ORDER


# --------------------------------------------------------------------------- #
# QC report: zero-execution counters
# --------------------------------------------------------------------------- #

def test_qc_report_zero_execution_counters():
    with open(os.path.join(STAGE126, p0.F_QC), encoding="utf-8") as f:
        qc = json.load(f)
    assert qc["stage"] == "stage126_m1_robustness_part0_decision_lock"
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["model_fit_calls"] == 0
    assert qc["prediction_calls"] == 0
    assert qc["smote_calls"] == 0
    assert qc["smotenc_calls"] == 0
    assert qc["shap_calls"] == 0
    assert qc["network_requests_attempted"] == 0
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_evaluations"] == 0


def test_qc_report_carries_robustness_decision_markers():
    with open(os.path.join(STAGE126, p0.F_QC), encoding="utf-8") as f:
        qc = json.load(f)
    assert qc["m1_robustness_decision_locked"] is True
    assert qc["m1_robustness_execution_authorized"] is False
    assert qc["m1_robustness_started"] is False
    assert qc["m1_robustness_next_category_id"] == "m1_target_proximity_six_feature_set"
    assert qc["m1_robustness_packaging_policy"] == "one_category_per_micro_part_pr"


# --------------------------------------------------------------------------- #
# QC assertion builder fail-closed behaviour on a tampered record
# --------------------------------------------------------------------------- #

def _assert_names(assertions):
    return {a["name"]: a["status"] for a in assertions}


def test_qc_assertions_all_pass_on_valid_record():
    r = _record()
    observed = dict(p0.PRIMARY_ARTIFACT_SHA256)
    a = p0.build_qc_assertions(_path(), r, observed, 0)
    assert all(x["status"] == "PASS" for x in a)


def test_qc_assertion_flags_execution_authorized_true():
    r = _record()
    r["execution_authorized"] = True  # tamper
    a = p0.build_qc_assertions(_path(), r, dict(p0.PRIMARY_ARTIFACT_SHA256), 0)
    assert _assert_names(a)["execution_authorized_false"] == "FAIL"


def test_qc_assertion_flags_robustness_started_true():
    r = _record()
    r["m1_robustness_started"] = True  # tamper
    a = p0.build_qc_assertions(_path(), r, dict(p0.PRIMARY_ARTIFACT_SHA256), 0)
    assert _assert_names(a)["m1_robustness_started_false"] == "FAIL"


def test_qc_assertion_flags_wrong_execution_order():
    r = _record()
    r["execution_order"] = list(reversed(r["execution_order"]))  # tamper
    a = p0.build_qc_assertions(_path(), r, dict(p0.PRIMARY_ARTIFACT_SHA256), 0)
    assert _assert_names(a)["execution_order_exact"] == "FAIL"


def test_qc_assertion_flags_network_attempt():
    r = _record()
    a = p0.build_qc_assertions(_path(), r, dict(p0.PRIMARY_ARTIFACT_SHA256), 1)
    assert _assert_names(a)["network_requests_attempted_zero"] == "FAIL"


def test_qc_assertion_flags_primary_artifact_change():
    r = _record()
    tampered = dict(p0.PRIMARY_ARTIFACT_SHA256)
    key = next(iter(tampered))
    tampered[key] = "0" * 64
    a = p0.build_qc_assertions(_path(), r, tampered, 0)
    assert _assert_names(a)["primary_artifacts_byte_identical"] == "FAIL"


# --------------------------------------------------------------------------- #
# Handoff-marker derivation helper
# --------------------------------------------------------------------------- #

def test_load_decision_markers_from_real_record():
    markers = p0.load_decision_markers(REAL_ROOT)
    assert markers == {
        "m1_robustness_decision_locked": True,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m1_robustness_next_category_id": "m1_target_proximity_six_feature_set",
        "m1_robustness_packaging_policy": "one_category_per_micro_part_pr",
    }


def test_module_imports_no_model_or_resampling_libraries():
    import sys
    # The Part 0 module must not have imported model/resampling/SHAP libraries.
    src_file = os.path.join(
        REAL_ROOT, "project", "src",
        "stage126_m1_robustness_part0_decision_lock.py",
    )
    text = open(src_file, encoding="utf-8").read()
    for banned in ("imblearn", "SMOTE(", "SMOTENC(", "import shap", ".fit(", ".predict("):
        assert banned not in text, f"forbidden token in source: {banned}"
