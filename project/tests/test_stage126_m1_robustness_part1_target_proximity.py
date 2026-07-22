"""Tests for Stage126 M1 — Robustness Part 1: target-proximity six-feature set.

Development-only sensitivity analysis. These tests never fit a full-development
model, never touch the locked final test, and never run SMOTE/SMOTENC/SHAP.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from src import stage126_m1_robustness_part1_target_proximity as p1
from src import stage126_m1_primary_development_tuning as primary

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGE126 = os.path.join(REAL_ROOT, "project", "stage126")

EXPECTED_SIX = (
    "log_total_assets",
    "current_ratio",
    "roa_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
)


def _root() -> Path:
    return Path(REAL_ROOT)


def _read_json(name: str) -> dict:
    with open(os.path.join(STAGE126, name), encoding="utf-8") as f:
        return json.load(f)


def _read_csv(name: str) -> list[dict]:
    with open(os.path.join(STAGE126, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #

def test_authorization_text_exact_and_hash_recomputes():
    assert p1.HUMAN_AUTHORIZATION_TEXT_FA == "مجوز انجام مرحله بعدی رو میدم"
    got = hashlib.sha256(p1.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")).hexdigest()
    assert got == "7364a67ce5761c69f6705ae0ee4b0563fc092a576e960df471ebb4581ae1b5ea"
    assert got == p1.HUMAN_AUTHORIZATION_TEXT_SHA256


def test_authorization_record_on_disk():
    rec = _read_json(p1.F_AUTH)
    assert rec["authorization_id"] == "stage126-m1-robustness-part1-human-authorization"
    assert rec["human_authorization_text"] == "مجوز انجام مرحله بعدی رو میدم"
    assert hashlib.sha256(
        rec["human_authorization_text"].encode("utf-8")
    ).hexdigest() == rec["human_authorization_text_sha256"]
    assert rec["authorized_category_id"] == "m1_target_proximity_six_feature_set"
    assert rec["part1_execution_authorized"] is True
    assert rec["part2_execution_authorized"] is False
    assert rec["merge_authorized"] is False
    assert rec["final_test_access_authorized"] is False


def test_wrong_authorization_hash_fails_closed():
    orig = p1.HUMAN_AUTHORIZATION_TEXT_SHA256
    p1.HUMAN_AUTHORIZATION_TEXT_SHA256 = "0" * 64
    try:
        with pytest.raises(p1.QCFail):
            p1.verify_authorization_text()
    finally:
        p1.HUMAN_AUTHORIZATION_TEXT_SHA256 = orig


def test_wrong_authorization_text_fails_closed():
    orig = p1.HUMAN_AUTHORIZATION_TEXT_FA
    p1.HUMAN_AUTHORIZATION_TEXT_FA = "tampered"
    try:
        with pytest.raises(p1.QCFail):
            p1.verify_authorization_text()
    finally:
        p1.HUMAN_AUTHORIZATION_TEXT_FA = orig


# --------------------------------------------------------------------------- #
# Category / sample / target / feature set
# --------------------------------------------------------------------------- #

def test_exact_category_and_fixed_dimensions():
    assert p1.CATEGORY_ID == "m1_target_proximity_six_feature_set"
    assert p1.CHANGED_DIMENSION == "feature_set"
    assert p1.PART1_SAMPLE == "main_rule_a_primary"
    assert p1.PART1_TARGET == "FD_target_main_t_plus_1"
    assert p1.FEATURE_SET_NAME == "M1_TARGET_PROXIMITY_ROBUSTNESS"
    assert p1.IMBALANCE_POLICY == "primary_class_weighting"
    assert p1.SCIENTIFIC_INTERPRETATION == "sensitivity_analysis_only"


def test_exact_six_feature_order():
    assert p1.PART1_FEATURE_ORDER == EXPECTED_SIX
    assert len(p1.PART1_FEATURE_ORDER) == 6


def test_exact_source_column_mapping():
    assert p1.PART1_FEATURE_SOURCE_COLUMN == {
        "log_total_assets": "total_assets",
        "current_ratio": "current_ratio",
        "roa_period_adjusted": "roa_period_adjusted",
        "asset_turnover_period_adjusted": "asset_turnover_period_adjusted",
        "operating_margin_period_adjusted": "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted":
            "financial_expense_to_assets_period_adjusted",
    }


def test_source_columns_are_exactly_six_and_exclude_removed_features():
    cols = p1.part1_source_columns()
    assert len(cols) == 6
    for banned in ("leverage_ratio", "ocf_to_assets_period_adjusted",
                   "accumulated_loss_to_capital_ratio",
                   "revenue_growth_period_adjusted"):
        assert banned not in cols


def test_excluded_primary_features_declared():
    assert p1.EXCLUDED_PRIMARY_FEATURES == (
        "leverage_ratio",
        "ocf_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    )
    assert p1.PROHIBITED_FEATURE == "revenue_growth_period_adjusted"


def test_excluded_feature_source_column_fails_closed(monkeypatch):
    # If an excluded feature were mapped in, the loader guard must fail closed.
    monkeypatch.setitem(p1.PART1_FEATURE_SOURCE_COLUMN,
                        "current_ratio", "leverage_ratio")
    with pytest.raises(p1.QCFail):
        p1.part1_source_columns()


def test_feature_manifest_exact_six_rows_in_order():
    rows = _read_csv(p1.F_FEATURE_MANIFEST)
    assert len(rows) == 6
    assert list(rows[0].keys()) == [
        "feature_order", "feature_name", "source_column", "transformation",
        "missingness_indicator_appended", "included_in_part1",
    ]
    assert [r["feature_name"] for r in rows] == list(EXPECTED_SIX)
    assert [int(r["feature_order"]) for r in rows] == [1, 2, 3, 4, 5, 6]
    for r in rows:
        assert r["included_in_part1"] == "true"
        assert r["missingness_indicator_appended"] == "true"
    assert rows[0]["transformation"] == "ln(total_assets) if total_assets > 0 else missing"


# --------------------------------------------------------------------------- #
# Transformed matrix width (12 columns) and standardization policy
# --------------------------------------------------------------------------- #

def test_transformed_matrix_is_twelve_columns():
    X = np.array([[1.0, 2.0, np.nan, 4.0, 5.0, 6.0],
                  [2.0, 3.0, 4.0, 5.0, 6.0, 7.0]])
    pre = primary.fit_preprocessor(X, standardize=False)
    out = primary.transform(X, pre)
    assert out.shape[1] == 12
    assert p1.TRANSFORMED_FEATURE_COUNT == 12
    assert p1.BASE_FEATURE_COUNT == 6


def test_indicators_never_standardized_for_logistic():
    X = np.array([[1.0, 2.0, np.nan, 4.0, 5.0, 6.0],
                  [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                  [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]])
    pre = primary.fit_preprocessor(X, standardize=True)
    out = primary.transform(X, pre)
    # Last six columns are the raw 0/1 mask (never standardized).
    mask = out[:, 6:]
    assert set(np.unique(mask)).issubset({0.0, 1.0})
    assert mask[0, 2] == 1.0


def test_rf_and_xgb_not_standardized():
    assert primary._requires_standardization("random_forest") is False
    assert primary._requires_standardization("xgboost") is False
    assert primary._requires_standardization(
        "regularized_logistic_regression") is True


# --------------------------------------------------------------------------- #
# Selected configurations / no retuning
# --------------------------------------------------------------------------- #

def test_selected_configurations_exact():
    sel = p1.load_selected_configurations(_root())
    assert sel["regularized_logistic_regression"]["configuration_id"] == \
        "logistic__C_0.1"
    assert sel["random_forest"]["configuration_id"] == \
        "rf__depth_3__maxfeat_'sqrt'__leaf_10"
    assert sel["xgboost"]["configuration_id"] == \
        "xgboost__lr_0.03__depth_2__mcw_1__lambda_1"
    lr = sel["regularized_logistic_regression"]["hyperparameters"]
    assert lr["penalty"] == "l2" and lr["solver"] == "liblinear"
    assert lr["max_iter"] == 5000 and lr["C"] == 0.1
    rf = sel["random_forest"]["hyperparameters"]
    assert rf["n_estimators"] == 500 and rf["bootstrap"] is True
    assert rf["max_depth"] == 3 and rf["max_features"] == "sqrt"
    assert rf["min_samples_leaf"] == 10
    xg = sel["xgboost"]["hyperparameters"]
    assert xg["objective"] == "binary:logistic" and xg["eval_metric"] == "aucpr"
    assert xg["n_estimators"] == 300 and xg["tree_method"] == "hist"
    assert xg["subsample"] == 0.8 and xg["colsample_bytree"] == 0.8
    assert xg["gamma"] == 0 and xg["learning_rate"] == 0.03
    assert xg["max_depth"] == 2 and xg["min_child_weight"] == 1
    assert xg["reg_lambda"] == 1 and xg["early_stopping"] is False


def test_changed_hyperparameter_fails_closed(monkeypatch):
    bad = {k: {"configuration_id": v["configuration_id"],
               "hyperparameters": dict(v["hyperparameters"])}
           for k, v in p1.EXPECTED_SELECTED.items()}
    bad["random_forest"]["hyperparameters"]["max_depth"] = 5
    monkeypatch.setattr(p1, "EXPECTED_SELECTED", bad)
    with pytest.raises(p1.QCFail):
        p1.load_selected_configurations(_root())


def test_wrong_selected_configuration_id_fails_closed(monkeypatch):
    bad = {k: {"configuration_id": v["configuration_id"],
               "hyperparameters": dict(v["hyperparameters"])}
           for k, v in p1.EXPECTED_SELECTED.items()}
    bad["xgboost"]["configuration_id"] = "xgboost__WRONG"
    monkeypatch.setattr(p1, "EXPECTED_SELECTED", bad)
    with pytest.raises(p1.QCFail):
        p1.load_selected_configurations(_root())


def test_no_tuning_functions_referenced_in_source():
    src = open(os.path.join(REAL_ROOT, p1.SRC_REL), encoding="utf-8").read()
    for banned in ("run_tuning", "select_configurations", "all_configurations",
                   "_logistic_configs", "_rf_configs", "_xgb_configs"):
        assert banned not in src, f"tuning symbol referenced: {banned}"


def test_qc_reports_zero_tuning_calls():
    qc = _read_json(p1.F_QC)
    assert qc["tuning_search_calls"] == 0


# --------------------------------------------------------------------------- #
# Execution counts / seeds
# --------------------------------------------------------------------------- #

def test_exact_seeds():
    assert p1.MODEL_SEEDS == (20260719, 20260720, 20260721, 20260722, 20260723)
    assert p1.LOGISTIC_DETERMINISTIC_SEED == 20260719


def test_exact_fit_and_prediction_counts():
    qc = _read_json(p1.F_QC)
    assert qc["model_fit_calls"] == 22
    assert qc["prediction_calls"] == 22
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["model_fit_calls"] == 22
    assert lock["prediction_calls"] == 22


def test_seed_aggregation_per_family():
    rows = _read_csv(p1.F_OOF)
    agg = {r["model_family"]: r["probability_seed_aggregation"] for r in rows}
    assert agg["regularized_logistic_regression"] == "deterministic_single_fit"
    assert agg["random_forest"] == "mean_of_5_fixed_seeds"
    assert agg["xgboost"] == "mean_of_5_fixed_seeds"


def test_xgboost_scale_pos_weight_per_fold():
    em = _read_json(p1.F_EXEC_MANIFEST)
    spw = em["xgboost_scale_pos_weight_by_training_fold"]
    assert abs(spw["fold1_train"] - (212 / 33)) < 1e-9
    assert abs(spw["fold2_train"] - (392 / 58)) < 1e-9


# --------------------------------------------------------------------------- #
# Folds / rows / key parity with the primary surface
# --------------------------------------------------------------------------- #

def test_exact_fold_specification():
    em = _read_json(p1.F_EXEC_MANIFEST)
    f1 = em["temporal_folds"]["fold1"]
    f2 = em["temporal_folds"]["fold2"]
    assert f1["train_target_years"] == [1393, 1394, 1395]
    assert f1["validation_target_years"] == [1396, 1397]
    assert f2["train_target_years"] == [1393, 1394, 1395, 1396, 1397]
    assert f2["validation_target_years"] == [1398, 1399]


def test_exact_development_and_fold_counts():
    qc = _read_json(p1.F_QC)
    assert qc["development_rows_loaded"] == 666
    assert qc["development_positive"] == 68
    assert qc["development_negative"] == 598
    assert qc["fold1_train_rows"] == 245
    assert qc["fold1_validation_rows"] == 205
    assert qc["fold2_train_rows"] == 450
    assert qc["fold2_validation_rows"] == 216
    em = _read_json(p1.F_EXEC_MANIFEST)
    fc = em["fold_counts"]
    assert fc["fold1_train"] == {"rows": 245, "positive": 33, "negative": 212}
    assert fc["fold1_validation"] == {"rows": 205, "positive": 25, "negative": 180}
    assert fc["fold2_train"] == {"rows": 450, "positive": 58, "negative": 392}
    assert fc["fold2_validation"] == {"rows": 216, "positive": 10, "negative": 206}


def test_part1_keys_and_targets_equal_primary_oof_surface():
    part1 = _read_csv(p1.F_OOF)
    with open(os.path.join(STAGE126, "stage126_m1_development_oof_predictions.csv"),
              encoding="utf-8-sig", newline="") as f:
        prim = list(csv.DictReader(f))
    assert len(part1) == len(prim) == 1263
    key = lambda r: (r["model_family"], r["predictor_row_key_t"],
                     r["target_row_key_t_plus_1"])
    p_idx = {key(r): r for r in prim}
    assert {key(r) for r in part1} == set(p_idx)
    for r in part1:
        ref = p_idx[key(r)]
        assert r["ticker"] == ref["ticker"]
        assert r["fiscal_year_t"] == ref["fiscal_year_t"]
        assert r["target_year"] == ref["target_year"]
        assert r["temporal_fold"] == ref["temporal_fold"]
        assert r["observed_target"] == ref["observed_target"]


def test_primary_oof_hash_pinned_and_unchanged():
    path = os.path.join(STAGE126, "stage126_m1_development_oof_predictions.csv")
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    assert got == "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"


# --------------------------------------------------------------------------- #
# OOF + metrics schema and content
# --------------------------------------------------------------------------- #

def test_oof_schema_and_counts():
    rows = _read_csv(p1.F_OOF)
    assert list(rows[0].keys()) == p1.OOF_COLUMNS
    assert len(rows) == 1263
    for fam in p1.MODEL_FAMILIES:
        fam_rows = [r for r in rows if r["model_family"] == fam]
        assert len(fam_rows) == 421
        assert sum(1 for r in fam_rows
                   if r["temporal_fold"] == "fold1_validation") == 205
        assert sum(1 for r in fam_rows
                   if r["temporal_fold"] == "fold2_validation") == 216
    keys = {(r["model_family"], r["predictor_row_key_t"],
             r["target_row_key_t_plus_1"]) for r in rows}
    assert len(keys) == len(rows)
    for r in rows:
        assert r["robustness_category_id"] == "m1_target_proximity_six_feature_set"
        assert r["feature_set"] == "M1_TARGET_PROXIMITY_ROBUSTNESS"
        pr = float(r["predicted_probability"])
        assert not math.isnan(pr)
        assert 0.0 <= pr <= 1.0


def test_no_final_test_year_in_oof():
    rows = _read_csv(p1.F_OOF)
    for r in rows:
        assert int(r["target_year"]) in (1393, 1394, 1395, 1396, 1397, 1398, 1399)
        assert int(r["target_year"]) not in (1400, 1401, 1402)


def test_metrics_schema_and_nine_rows():
    rows = _read_csv(p1.F_METRICS)
    assert list(rows[0].keys()) == p1.METRICS_COLUMNS
    assert len(rows) == 9
    scopes = {"fold1_validation", "fold2_validation", "pooled_development_oof"}
    for fam in p1.MODEL_FAMILIES:
        fam_rows = [r for r in rows if r["model_family"] == fam]
        assert len(fam_rows) == 3
        assert {r["scope"] for r in fam_rows} == scopes
    for r in rows:
        assert r["robustness_category_id"] == "m1_target_proximity_six_feature_set"
        for m in ("pr_auc", "roc_auc", "brier_score", "recall_at_10pct",
                  "lift_at_10pct"):
            assert r[m] != ""


def test_topk_rule_per_target_year():
    # K = sum over years of ceil(0.10 * N_y); verify against pooled scope.
    rows = _read_csv(p1.F_OOF)
    fam = "random_forest"
    fam_rows = [r for r in rows if r["model_family"] == fam]
    years: dict[int, int] = {}
    for r in fam_rows:
        years[int(r["target_year"])] = years.get(int(r["target_year"]), 0) + 1
    expected_k = sum(math.ceil(0.10 * n) for n in years.values())
    metrics = _read_csv(p1.F_METRICS)
    pooled = [r for r in metrics
              if r["model_family"] == fam
              and r["scope"] == "pooled_development_oof"][0]
    assert int(pooled["k_top10"]) == expected_k


# --------------------------------------------------------------------------- #
# Final-test lock (including poison values)
# --------------------------------------------------------------------------- #

def test_qc_final_test_counters_zero():
    qc = _read_json(p1.F_QC)
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_evaluations"] == 0
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["final_test_unlocked"] is False
    assert lock["final_test_access_authorized"] is False
    assert lock["final_test_evaluation_performed"] is False


def test_poison_final_test_values_are_never_parsed(tmp_path, monkeypatch):
    """Final-test rows carrying non-numeric poison must never be parsed.

    The loader must succeed on the development rows and never raise a numeric
    parse error from the poisoned final-test rows.
    """
    real_csv = Path(REAL_ROOT) / primary.ANALYSIS_READY_REL
    with real_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    allowlist = primary.build_development_allowlist(_root())
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]

    poisoned = 0
    for r in rows:
        key = (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        if key in denylist:
            for c in list(p1.PART1_FEATURE_SOURCE_COLUMN.values()):
                r[c] = "POISON_NOT_A_NUMBER"
            r[p1.PART1_TARGET] = "POISON_TARGET"
            poisoned += 1
    assert poisoned > 0

    fake_root = tmp_path
    dst = fake_root / primary.ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # Loader must complete cleanly: poisoned final-test values are never parsed.
    loaded = p1.load_part1_development_values(fake_root, allowlist)
    assert len(loaded["rows"]) == 666
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0
    assert loaded["final_test_rows_seen"] == poisoned
    # And no loaded feature value is a poisoned/NaN-from-poison artifact.
    for info in loaded["rows"].values():
        assert info["features"].shape[0] == 6


def test_development_key_with_final_test_year_fails_closed(tmp_path):
    allowlist = primary.build_development_allowlist(_root())
    dev_key = next(iter(allowlist["dev_pairs"]))
    real_csv = Path(REAL_ROOT) / primary.ANALYSIS_READY_REL
    with real_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for r in rows:
        if (r["predictor_row_key_t"], r["target_row_key_t_plus_1"]) == dev_key:
            r["target_year"] = "1400"  # final-test year on a development key
            break
    dst = tmp_path / primary.ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(p1.FinalTestLockError):
        p1.load_part1_development_values(tmp_path, allowlist)


# --------------------------------------------------------------------------- #
# Prohibited execution + source hygiene
# --------------------------------------------------------------------------- #

def test_source_imports_no_prohibited_libraries():
    src = open(os.path.join(REAL_ROOT, p1.SRC_REL), encoding="utf-8").read()
    for banned in ("imblearn", "SMOTE(", "SMOTENC(", "import shap",
                   "average_precision_score(", "CalibratedClassifierCV",
                   "bootstrap(", "holm", "multipletests"):
        assert banned not in src, f"prohibited token in Part 1 source: {banned}"


def test_qc_zero_smote_smotenc_shap_network():
    qc = _read_json(p1.F_QC)
    assert qc["smote_calls"] == 0
    assert qc["smotenc_calls"] == 0
    assert qc["shap_calls"] == 0
    assert qc["network_requests_attempted"] == 0


def test_completion_lock_no_execution_flags():
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["smote_executed"] is False
    assert lock["smotenc_executed"] is False
    assert lock["shap_executed"] is False
    assert lock["full_development_refit_performed"] is False


def test_no_winner_selection_or_reranking_fields():
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["selects_paper_winner"] is False
    assert lock["replaces_primary_results"] is False
    assert lock["changes_primary_model_family_ordering"] is False
    assert lock["scientific_interpretation"] == "sensitivity_analysis_only"
    metrics_text = open(os.path.join(STAGE126, p1.F_METRICS), encoding="utf-8").read()
    for banned in ("winner", "rank", "p_value", "holm", "bootstrap", "calibration"):
        assert banned not in metrics_text.lower()


# --------------------------------------------------------------------------- #
# Completion lock / Part 2 gating
# --------------------------------------------------------------------------- #

def test_completion_lock_contract():
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["contract_version"] == \
        "stage126_m1_robustness_part1_target_proximity_v1"
    assert lock["category_id"] == "m1_target_proximity_six_feature_set"
    assert lock["part1_human_authorized"] is True
    assert lock["part1_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["development_only"] is True
    assert lock["sample"] == "main_rule_a_primary"
    assert lock["target"] == "FD_target_main_t_plus_1"
    assert lock["feature_set"] == "M1_TARGET_PROXIMITY_ROBUSTNESS"
    assert lock["base_feature_count"] == 6
    assert lock["transformed_feature_count"] == 12
    assert lock["no_retuning"] is True
    assert lock["m1_robustness_started"] is True
    assert lock["m1_robustness_completed"] is False
    assert lock["completed_category_ids"] == ["m1_target_proximity_six_feature_set"]
    assert lock["next_category_id"] == "main_rule_b_listing_robustness"


def test_part2_not_authorized():
    lock = _read_json(p1.F_COMPLETION_LOCK)
    assert lock["part2_execution_authorized"] is False
    auth = _read_json(p1.F_AUTH)
    assert auth["part2_execution_authorized"] is False
    markers = p1.part1_handoff_markers()
    assert markers["m1_robustness_part2_authorized"] is False
    assert markers["m1_robustness_execution_authorized"] is False
    assert markers["m1_robustness_completed"] is False


# --------------------------------------------------------------------------- #
# Frozen integrity + determinism
# --------------------------------------------------------------------------- #

def test_primary_artifacts_byte_identical():
    observed = p1.verify_frozen_integrity(_root())
    for rel, expected in p1.PINNED_PRIMARY_ARTIFACTS.items():
        assert observed[rel] == expected


def test_primary_source_hash_pinned():
    got = hashlib.sha256(
        open(os.path.join(REAL_ROOT, p1.PRIMARY_SRC_REL), "rb").read()
    ).hexdigest()
    assert got == "ae63bee24c3b868919b008cb15a0d4f4bfb8300ee6e3002a61e1e105d9391d82"


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())
    part0.verify_frozen_stage125_contract_hashes(_root())


def test_part0_contract_verified():
    rec = p1.verify_part0_contract(_root())
    assert rec["contract_id"] == "stage126_m1_robustness_execution_contract"
    assert rec["execution_order"][0] == "m1_target_proximity_six_feature_set"


def test_deterministic_repeated_build_output(tmp_path):
    """Two builds into temp dirs must produce byte-identical tracked outputs."""
    a = p1.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "a", build=True)
    b = p1.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "b", build=True)
    assert a["files"] == b["files"]
    # And identical to the committed canonical outputs (excluding volatile QC).
    for name, sha in a["files"].items():
        if name in (p1.F_QC, p1.F_METADATA):
            continue
        on_disk = hashlib.sha256(
            open(os.path.join(STAGE126, name), "rb").read()
        ).hexdigest()
        assert on_disk == sha, f"{name} not deterministic vs committed output"


def test_qc_all_pass_and_required_fields():
    qc = _read_json(p1.F_QC)
    assert qc["stage"] == "stage126_m1_robustness_part1_target_proximity"
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 40
    for field in ("human_authorization_hash_valid", "part0_contract_hash_valid",
                  "sample", "target", "feature_set", "base_feature_count",
                  "transformed_feature_count", "development_rows_loaded",
                  "development_positive", "development_negative",
                  "fold1_train_rows", "fold1_validation_rows",
                  "fold2_train_rows", "fold2_validation_rows",
                  "oof_rows_per_family", "oof_rows_total", "metrics_rows",
                  "selected_configuration_ids", "model_seeds",
                  "model_fit_calls", "prediction_calls", "tuning_search_calls",
                  "smote_calls", "smotenc_calls", "shap_calls",
                  "network_requests_attempted",
                  "final_test_predictor_rows_loaded",
                  "final_test_target_rows_loaded", "final_test_evaluations",
                  "primary_artifact_sha256", "output_sha256"):
        assert field in qc, f"QC missing required field: {field}"
