"""Fail-closed tests for Stage126 M1 — Robustness Part 3: expanded Rule A.

Part 3 is a one-factor-at-a-time sample-robustness sensitivity analysis: ONLY
the company-scope sample changes. These tests assert the exact authorization,
the fixed dimensions, the exact Expanded Rule A counts, the identity-only
sample-delta audit (including the negative-only additions), the final-test lock,
the zero counters for every forbidden operation, the interpretation guards, and
the byte-identity of the closed Part 1 / Part 2 packages and Stage125.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from src import stage126_m1_primary_development_tuning as primary
from src import stage126_m1_robustness_part3_expanded_rule_a as p3

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGE126 = os.path.join(REAL_ROOT, "project", "stage126")

EXPECTED_NINE = (
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


def _root() -> Path:
    return Path(REAL_ROOT)


def _read_json(name: str) -> dict:
    return json.loads(open(os.path.join(STAGE126, name), encoding="utf-8").read())


def _read_csv(name: str) -> list[dict]:
    with open(os.path.join(STAGE126, name), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #

def test_authorization_text_bytes_and_hash_exact():
    raw = p3.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    assert len(raw) == 423
    assert len(raw) == p3.HUMAN_AUTHORIZATION_TEXT_BYTES
    assert hashlib.sha256(raw).hexdigest() == (
        "f1230aa0dac18670695d41d99709cfd4ba5619e96e6f93c2e0678387ab28dab1"
    )
    assert hashlib.sha256(raw).hexdigest() == p3.HUMAN_AUTHORIZATION_TEXT_SHA256


def test_authorization_text_shape_and_content():
    text = p3.HUMAN_AUTHORIZATION_TEXT_FA
    assert not text.endswith("\n")
    paragraphs = text.split("\n\n")
    assert len(paragraphs) == 2
    assert "Part 3" in paragraphs[0]
    assert "expanded_rule_a_company_scope_robustness" in paragraphs[0]
    for excluded in ("Merge", "Part 4", "full-development refit", "final test",
                     "calibration", "bootstrap", "Holm", "winner selection",
                     "SMOTE", "SHAP", "M2/M3/M4"):
        assert excluded in paragraphs[1], excluded


def test_wrong_authorization_text_fails_closed(monkeypatch):
    monkeypatch.setattr(p3, "HUMAN_AUTHORIZATION_TEXT_FA", "مجوز جعلی")
    with pytest.raises(p3.QCFail):
        p3.verify_authorization_text()


def test_wrong_authorization_hash_fails_closed(monkeypatch):
    monkeypatch.setattr(p3, "HUMAN_AUTHORIZATION_TEXT_SHA256", "0" * 64)
    with pytest.raises(p3.QCFail):
        p3.verify_authorization_text()


def test_authorization_record_on_disk():
    rec = _read_json(p3.F_AUTH)
    assert rec["authorization_id"] == p3.AUTHORIZATION_ID
    assert rec["authorized_category_id"] == (
        "expanded_rule_a_company_scope_robustness"
    )
    assert rec["human_authorization_text_utf8_bytes"] == 423
    assert hashlib.sha256(
        rec["human_authorization_text"].encode("utf-8")
    ).hexdigest() == p3.HUMAN_AUTHORIZATION_TEXT_SHA256
    assert rec["part3_execution_authorized"] is True
    assert rec["development_fold_execution_authorized"] is True
    assert rec["create_open_unmerged_pr_authorized"] is True
    assert rec["authorized_base_main_commit"] == (
        "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
    )


def test_authorization_grants_nothing_else():
    rec = _read_json(p3.F_AUTH)
    for field in (
        "merge_authorized", "part4_execution_authorized",
        "full_development_refit_authorized",
        "final_test_predictor_access_authorized",
        "final_test_target_access_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "calibration_authorized",
        "threshold_optimization_authorized", "bootstrap_authorized",
        "holm_authorized", "p_values_authorized", "winner_selection_authorized",
        "smote_authorized", "smotenc_authorized", "shap_authorized",
        "m2_authorized", "m3_authorized", "m4_authorized",
    ):
        assert rec[field] is False, field


# --------------------------------------------------------------------------- #
# Category order
# --------------------------------------------------------------------------- #

def test_part0_places_part3_third_and_part4_next():
    record = p3.verify_part0_contract(_root())
    order = record["execution_order"]
    assert order[0] == "m1_target_proximity_six_feature_set"
    assert order[1] == "main_rule_b_listing_robustness"
    assert order[2] == "expanded_rule_a_company_scope_robustness"
    assert order[3] == "expanded_rule_b_combined_robustness"


def test_parts_1_and_2_must_precede_part3():
    assert p3.verify_predecessors_completed(_root()) == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
    ]


def test_missing_predecessor_fails_closed(tmp_path):
    (tmp_path / "project" / "stage126").mkdir(parents=True)
    with pytest.raises(p3.QCFail):
        p3.verify_predecessors_completed(tmp_path)


# --------------------------------------------------------------------------- #
# Frozen contract: only the sample changed
# --------------------------------------------------------------------------- #

def test_category_role_and_changed_dimension():
    assert p3.CATEGORY_ID == "expanded_rule_a_company_scope_robustness"
    assert p3.SCIENTIFIC_ROLE == "expanded_company_scope_sample_robustness"
    assert p3.CHANGED_DIMENSION == "sample"
    assert p3.MICRO_PART_ID == "stage126-m1-robustness-part3-expanded-rule-a"
    assert p3.NEXT_CATEGORY_ID == "expanded_rule_b_combined_robustness"


def test_sample_changed_everything_else_fixed():
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert m["sample"] == "expanded_rule_a_company_scope_robustness"
    assert m["primary_sample"] == "main_rule_a_primary"
    assert m["target"] == "FD_target_main_t_plus_1"
    assert m["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"
    assert m["imbalance_policy"] == "primary_class_weighting"
    for flag in ("target_changed", "feature_set_changed",
                 "preprocessing_changed", "missingness_indicator_logic_changed",
                 "imbalance_policy_changed", "selected_configurations_changed",
                 "temporal_folds_changed", "seeds_changed"):
        assert m[flag] is False, flag


def test_canonical_sample_path_and_hash():
    assert p3.PART3_ANALYSIS_READY_REL == (
        "project/stage125/part3c_outputs/"
        "analysis_ready_expanded_rule_a_stage125.csv"
    )
    got = hashlib.sha256((_root() / p3.PART3_ANALYSIS_READY_REL).read_bytes())
    assert got.hexdigest() == (
        "fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9"
    )
    assert got.hexdigest() == p3.PART3_ANALYSIS_READY_SHA256


def test_exact_nine_feature_order_and_matrix_width():
    assert p3.PART3_FEATURE_ORDER == EXPECTED_NINE
    assert tuple(primary.M1_PRIMARY_FEATURE_ORDER) == EXPECTED_NINE
    assert p3.BASE_FEATURE_COUNT == 9
    assert p3.TRANSFORMED_FEATURE_COUNT == 18


def test_feature_manifest_declares_indicator_column_order():
    rows = _read_csv(p3.F_FEATURE_MANIFEST)
    assert len(rows) == 9
    for i, (row, feat) in enumerate(zip(rows, EXPECTED_NINE), start=1):
        assert int(row["feature_order"]) == i
        assert row["feature_name"] == feat
        assert row["source_column"] == p3.PART3_FEATURE_SOURCE_COLUMN[feat]
        assert row["missingness_indicator_appended"] == "true"
        assert int(row["missingness_indicator_column_index"]) == 9 + i
        assert row["included_in_part3"] == "true"


def test_model_matrix_is_eighteen_columns_features_then_indicators():
    allow = p3.build_part3_allowlist(_root())
    loaded = p3.load_part3_development_values(_root(), allow)
    fd = primary._role_matrix(loaded["rows"], allow["role_pairs"], "fold1_train")
    assert fd["X"].shape[1] == 9
    pre = primary.fit_preprocessor(fd["X"], standardize=False)
    X = primary.transform(fd["X"], pre)
    assert X.shape[1] == 18
    # The trailing nine columns are binary indicators of the ORIGINAL missingness.
    indicators = X[:, 9:]
    assert set(indicators.flatten().tolist()) <= {0.0, 1.0}
    import numpy as np
    assert np.array_equal(indicators, np.isnan(fd["X"]).astype(float))


def test_prohibited_feature_and_target_absent():
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert p3.PROHIBITED_FEATURE == "revenue_growth_period_adjusted"
    assert p3.PROHIBITED_FEATURE not in m["features_exact_order"]
    assert p3.PROHIBITED_FEATURE not in set(m["feature_source_columns"].values())
    assert m["target"] != p3.PROHIBITED_TARGET


def test_prohibited_feature_reaching_loader_fails_closed(monkeypatch):
    bad = dict(p3.PART3_FEATURE_SOURCE_COLUMN)
    bad["log_total_assets"] = p3.PROHIBITED_FEATURE
    monkeypatch.setattr(p3, "PART3_FEATURE_SOURCE_COLUMN", bad)
    with pytest.raises(p3.QCFail):
        p3.part3_source_columns()


# --------------------------------------------------------------------------- #
# Exact counts
# --------------------------------------------------------------------------- #

def test_analysis_ready_counts():
    qc = _read_json(p3.F_QC)
    assert qc["analysis_ready_rows"] == 1056
    assert qc["analysis_ready_companies"] == 124
    assert qc["analysis_ready_positive"] == 80
    assert qc["analysis_ready_negative"] == 976


def test_development_counts_and_no_missing_target():
    qc = _read_json(p3.F_QC)
    assert qc["development_rows_loaded"] == 695
    assert qc["development_positive"] == 68
    assert qc["development_negative"] == 627
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert m["development_missing_target"] == 0


def test_exact_fold_counts():
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert m["fold_counts"] == {
        "fold1_train": {"rows": 254, "positive": 33, "negative": 221},
        "fold1_validation": {"rows": 215, "positive": 25, "negative": 190},
        "fold2_train": {"rows": 469, "positive": 58, "negative": 411},
        "fold2_validation": {"rows": 226, "positive": 10, "negative": 216},
    }


def test_wrong_expected_counts_fail_closed():
    with pytest.raises(p3.QCFail):
        p3.build_sample_allowlist(
            _root(), "expanded_rule_a_company_scope_robustness",
            {**p3.EXPECTED_FOLD_COUNTS,
             "fold1_train": {"rows": 999, "positive": 33, "negative": 221}},
            p3.EXPECTED_DEV_ROWS, p3.EXPECTED_FINAL_TEST_IDENTITIES,
        )


# --------------------------------------------------------------------------- #
# Configurations, seeds, class weights, execution counters
# --------------------------------------------------------------------------- #

def test_selected_configurations_exact_and_no_tuning():
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert m["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }
    assert m["no_retuning"] is True
    assert m["zero_counters"]["tuning_search_calls"] == 0


def test_no_tuning_or_search_referenced_in_source():
    src = open(os.path.join(REAL_ROOT, p3.SRC_REL), encoding="utf-8").read()
    for banned in ("GridSearchCV", "RandomizedSearchCV", "optuna", "Optuna",
                   "BayesSearch", "run_tuning", "select_configurations"):
        assert banned not in src, banned


def test_seeds_and_deterministic_logistic():
    m = _read_json(p3.F_EXEC_MANIFEST)
    assert m["model_seeds"] == [20260719, 20260720, 20260721, 20260722, 20260723]
    assert m["logistic_deterministic_seed"] == 20260719
    rows = _read_csv(p3.F_OOF)
    agg = {r["model_family"]: r["seed_aggregation"] for r in rows}
    assert agg["regularized_logistic_regression"] == "deterministic_single_fit"
    assert agg["random_forest"] == "mean_of_5_fixed_seeds"
    assert agg["xgboost"] == "mean_of_5_fixed_seeds"


def test_xgboost_scale_pos_weight_recomputed_per_training_fold():
    m = _read_json(p3.F_EXEC_MANIFEST)
    spw = m["xgboost_scale_pos_weight_by_training_fold"]
    assert math.isclose(spw["fold1_train"], 221 / 33, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(spw["fold2_train"], 411 / 58, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(spw["fold1_train"], 6.696969696969697, abs_tol=1e-12)
    assert math.isclose(spw["fold2_train"], 7.086206896551724, abs_tol=1e-12)
    # Not the primary-sample weights, and not computed from validation rows.
    assert not math.isclose(spw["fold1_train"], 212 / 33, abs_tol=1e-12)
    assert not math.isclose(spw["fold2_train"], 392 / 58, abs_tol=1e-12)
    assert m["class_weights_use_validation_rows"] is False
    assert m["class_weights_reused_from_primary_sample"] is False


def test_exact_fit_prediction_and_zero_counters():
    qc = _read_json(p3.F_QC)
    assert qc["model_fit_calls"] == 22
    assert qc["prediction_calls"] == 22
    assert qc["network_requests_attempted"] == 0
    for name, value in qc["zero_counters"].items():
        assert value == 0, name
    for name in ("tuning_search_calls", "smote_calls", "smotenc_calls",
                 "shap_calls", "calibration_calls",
                 "threshold_optimization_calls", "bootstrap_calls",
                 "holm_calls", "p_value_calls", "winner_selection_calls",
                 "final_test_evaluations", "final_test_predictions",
                 "full_development_refits"):
        assert name in qc["zero_counters"], name


def test_source_imports_no_prohibited_libraries():
    src = open(os.path.join(REAL_ROOT, p3.SRC_REL), encoding="utf-8").read()
    for banned in ("imblearn", "SMOTE(", "SMOTENC(", "import shap",
                   "CalibratedClassifierCV", "calibration_curve",
                   "multipletests"):
        assert banned not in src, banned


# --------------------------------------------------------------------------- #
# OOF + metrics
# --------------------------------------------------------------------------- #

def test_oof_schema_counts_and_identities():
    rows = _read_csv(p3.F_OOF)
    assert len(rows) == 1323
    assert list(rows[0].keys()) == p3.OOF_COLUMNS
    for family in primary.ALLOWED_MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        assert len(fam) == 441
        keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                for r in fam}
        assert len(keys) == 441, "duplicate OOF identities"
        assert sum(1 for r in fam if r["temporal_fold"] == "fold1_validation") == 215
        assert sum(1 for r in fam if r["temporal_fold"] == "fold2_validation") == 226
    for r in rows:
        assert r["sample"] == "expanded_rule_a_company_scope_robustness"
        prob = float(r["predicted_probability"])
        assert not math.isnan(prob)
        assert 0.0 <= prob <= 1.0
        assert r["observed_target"] in ("0", "1")


def test_oof_identities_match_the_validation_folds_exactly():
    """No missing and no extra OOF identity versus the frozen split contract."""
    allow = p3.build_part3_allowlist(_root())
    expected = (allow["role_pairs"]["fold1_validation"]
                | allow["role_pairs"]["fold2_validation"])
    assert len(expected) == 441
    rows = _read_csv(p3.F_OOF)
    for family in primary.ALLOWED_MODEL_FAMILIES:
        keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                for r in rows if r["model_family"] == family}
        assert keys == expected, family


def test_no_validation_leakage_and_no_final_test_year_in_oof():
    rows = _read_csv(p3.F_OOF)
    allowed = {
        "fold1_validation": set(primary.FOLD_SPEC["fold1"]["validation_target_years"]),
        "fold2_validation": set(primary.FOLD_SPEC["fold2"]["validation_target_years"]),
    }
    for r in rows:
        year = int(r["target_year"])
        assert year in allowed[r["temporal_fold"]]
        assert year not in primary.FINAL_TEST_TARGET_YEARS


def test_metrics_schema_scopes_and_names():
    rows = _read_csv(p3.F_METRICS)
    assert len(rows) == 9
    assert list(rows[0].keys()) == p3.METRICS_COLUMNS
    assert sorted({r["scope"] for r in rows}) == [
        "fold1_validation", "fold2_validation", "pooled_development_oof",
    ]
    for r in rows:
        for metric in ("pr_auc", "roc_auc", "brier_score", "recall_at_10pct",
                       "lift_at_10pct"):
            assert not math.isnan(float(r[metric])), (r["model_family"], metric)
    pooled = [r for r in rows if r["scope"] == "pooled_development_oof"]
    assert len(pooled) == 3
    for r in pooled:
        assert int(r["n_rows"]) == 441
        assert int(r["n_positive"]) == 35


def test_topk_rule_is_ceiling_of_ten_percent_per_target_year():
    metrics = _read_csv(p3.F_METRICS)
    oof = _read_csv(p3.F_OOF)
    for r in metrics:
        fam_rows = [
            o for o in oof
            if o["model_family"] == r["model_family"]
            and (r["scope"] == "pooled_development_oof"
                 or o["temporal_fold"] == r["scope"])
        ]
        years: dict[int, int] = {}
        for o in fam_rows:
            years[int(o["target_year"])] = years.get(int(o["target_year"]), 0) + 1
        assert int(r["k_top10"]) == sum(
            math.ceil(0.10 * n) for n in years.values()
        ), (r["model_family"], r["scope"])


def test_no_prohibited_analysis_in_metric_surface():
    text = open(os.path.join(STAGE126, p3.F_METRICS), encoding="utf-8").read()
    for banned in ("winner", "rank", "p_value", "holm", "bootstrap",
                   "calibration", "threshold"):
        assert banned not in text.lower(), banned


def test_no_numpy_scalar_repr_in_outputs():
    for name in (p3.F_OOF, p3.F_METRICS, p3.F_SAMPLE_DELTA,
                 p3.F_FEATURE_MANIFEST, p3.F_EXEC_MANIFEST, p3.F_COMPARISON,
                 p3.F_COMPLETION_LOCK, p3.F_QC, p3.F_METADATA):
        text = open(os.path.join(STAGE126, name), encoding="utf-8").read()
        assert "np.float64(" not in text, name
        assert "np.int64(" not in text, name


def test_json_outputs_sorted_and_newline_terminated():
    for name in (p3.F_AUTH, p3.F_EXEC_MANIFEST, p3.F_COMPARISON,
                 p3.F_COMPLETION_LOCK, p3.F_QC, p3.F_METADATA):
        text = open(os.path.join(STAGE126, name), encoding="utf-8").read()
        assert text.endswith("\n"), name
        obj = json.loads(text)
        assert text == json.dumps(
            obj, indent=2, ensure_ascii=False, sort_keys=True
        ) + "\n", name


# --------------------------------------------------------------------------- #
# Sample delta (identities only)
# --------------------------------------------------------------------------- #

def test_sample_delta_schema_and_row_count():
    rows = _read_csv(p3.F_SAMPLE_DELTA)
    assert len(rows) == 1056
    assert list(rows[0].keys()) == p3.SAMPLE_DELTA_COLUMNS


def test_sample_delta_contains_no_predictor_or_target_values():
    rows = _read_csv(p3.F_SAMPLE_DELTA)
    forbidden = set(p3.PART3_FEATURE_SOURCE_COLUMN.values()) | {
        p3.PART3_TARGET, p3.PROHIBITED_TARGET, "observed_target",
        "predicted_probability", p3.PROHIBITED_FEATURE,
    }
    assert not (set(rows[0].keys()) & forbidden)


def test_expanded_is_strict_superset_of_primary():
    rows = _read_csv(p3.F_SAMPLE_DELTA)
    expanded_only = [r for r in rows
                     if r["present_in_main_rule_a_primary"] == "false"]
    both = [r for r in rows if r["present_in_main_rule_a_primary"] == "true"]
    assert all(r["present_in_expanded_rule_a"] == "true" for r in rows)
    assert len(expanded_only) == 44
    assert len(both) == 1012
    assert all(
        r["sample_delta_status"] == "expanded_only_added_by_company_scope"
        for r in expanded_only
    )


def test_aggregate_and_fold_deltas_exact():
    d = _read_json(p3.F_QC)["sample_delta"]
    assert d["expanded_only_rows"] == 44
    assert d["primary_only_rows"] == 0
    assert d["company_delta"] == 5
    assert d["positive_delta"] == 0
    assert d["negative_delta"] == 44
    assert d["development_rows_added"] == 29
    assert d["development_positives_added"] == 0
    assert d["development_negatives_added"] == 29
    assert d["fold_delta"] == {
        "fold1_train": {"rows_added": 9, "positives_added": 0,
                        "negatives_added": 9, "rows_removed": 0},
        "fold1_validation": {"rows_added": 10, "positives_added": 0,
                             "negatives_added": 10, "rows_removed": 0},
        "fold2_train": {"rows_added": 19, "positives_added": 0,
                        "negatives_added": 19, "rows_removed": 0},
        "fold2_validation": {"rows_added": 10, "positives_added": 0,
                             "negatives_added": 10, "rows_removed": 0},
    }


def test_oof_and_final_test_identity_deltas_exact():
    d = _read_json(p3.F_QC)["sample_delta"]
    assert d["expanded_rule_a_company_scope_robustness"]["oof_identities"] == 441
    assert d["main_rule_a_primary"]["oof_identities"] == 421
    assert d["oof_identities_added"] == 20
    assert d["oof_identities_added_all_target_zero"] is True
    assert d["expanded_rule_a_company_scope_robustness"][
        "final_test_identities"] == 361
    assert d["main_rule_a_primary"]["final_test_identities"] == 346
    assert d["final_test_identities_added"] == 15


def test_added_oof_identities_all_have_target_zero():
    """Independently recompute: every added OOF identity is a negative row."""
    allow_e = p3.build_part3_allowlist(_root())
    allow_p = p3.build_primary_allowlist(_root())
    added = (
        (allow_e["role_pairs"]["fold1_validation"]
         | allow_e["role_pairs"]["fold2_validation"])
        - (allow_p["role_pairs"]["fold1_validation"]
           | allow_p["role_pairs"]["fold2_validation"])
    )
    assert len(added) == 20
    oof = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"]):
           r["observed_target"] for r in _read_csv(p3.F_OOF)}
    assert all(oof[k] == "0" for k in added)


def test_final_test_delta_is_identity_only():
    d = _read_json(p3.F_QC)["sample_delta"]
    assert d["comparison_basis"] == "row_identities_only"
    assert d["final_test_values_read"] is False
    assert d["final_test_identity_source"] == (
        "project/stage125/part4_temporal_split_manifest_stage125.csv"
    )


def test_superset_violation_fails_closed(monkeypatch):
    monkeypatch.setattr(p3, "EXPECTED_EXPANDED_ONLY_KEYS", 43)
    allow_e = p3.build_part3_allowlist(_root())
    allow_p = p3.build_primary_allowlist(_root())
    loaded = p3.load_part3_development_values(_root(), allow_e)
    with pytest.raises(p3.QCFail):
        p3.build_sample_delta(_root(), allow_p, allow_e, loaded)


# --------------------------------------------------------------------------- #
# Final-test lock
# --------------------------------------------------------------------------- #

def test_final_test_counters_zero_and_identities_only():
    qc = _read_json(p3.F_QC)
    assert qc["final_test_identities_counted"] == 361
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_predictions_generated"] == 0
    assert qc["final_test_metrics_computed"] == 0
    assert qc["final_test_evaluations"] == 0
    lock = _read_json(p3.F_COMPLETION_LOCK)
    for field in ("final_test_unlocked", "final_test_access_authorized",
                  "final_test_predictor_values_inspected",
                  "final_test_target_values_inspected",
                  "final_test_evaluation_performed"):
        assert lock[field] is False, field


def test_poison_final_test_values_are_never_parsed(tmp_path):
    """Non-numeric poison on final-test rows must never be parsed."""
    real = _root() / p3.PART3_ANALYSIS_READY_REL
    with real.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    allow = p3.build_part3_allowlist(_root())
    poisoned = 0
    for r in rows:
        key = (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        if key in allow["denylist_pairs"]:
            for c in p3.PART3_FEATURE_SOURCE_COLUMN.values():
                r[c] = "POISON_NOT_A_NUMBER"
            r[p3.PART3_TARGET] = "POISON_TARGET"
            poisoned += 1
    assert poisoned == 361
    dst = tmp_path / p3.PART3_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    loaded = p3.load_part3_development_values(tmp_path, allow)
    assert len(loaded["rows"]) == 695
    assert loaded["final_test_rows_seen"] == 361
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0


def test_development_key_with_final_test_year_fails_closed(tmp_path):
    allow = p3.build_part3_allowlist(_root())
    dev_key = next(iter(allow["dev_pairs"]))
    real = _root() / p3.PART3_ANALYSIS_READY_REL
    with real.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for r in rows:
        if (r["predictor_row_key_t"], r["target_row_key_t_plus_1"]) == dev_key:
            r["target_year"] = "1402"
            break
    dst = tmp_path / p3.PART3_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(p3.FinalTestLockError):
        p3.load_part3_development_values(tmp_path, allow)


def test_unknown_row_fails_closed(tmp_path):
    allow = p3.build_part3_allowlist(_root())
    real = _root() / p3.PART3_ANALYSIS_READY_REL
    with real.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    rows[0] = dict(rows[0])
    rows[0]["predictor_row_key_t"] = "UNCLASSIFIED"
    dst = tmp_path / p3.PART3_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(p3.QCFail):
        p3.load_part3_development_values(tmp_path, allow)


# --------------------------------------------------------------------------- #
# Immutability of everything closed
# --------------------------------------------------------------------------- #

def test_primary_stage126_artifacts_byte_identical():
    observed = p3.verify_frozen_integrity(_root())
    assert observed == {k: p3.PINNED_PRIMARY_ARTIFACTS[k] for k in observed}


def test_part1_and_part2_artifacts_byte_identical():
    observed = p3.verify_closed_parts_immutable(_root())
    assert observed == p3.PINNED_CLOSED_PART_ARTIFACTS
    assert len(observed) == 15


def test_closed_part_drift_fails_closed(monkeypatch):
    bad = dict(p3.PINNED_CLOSED_PART_ARTIFACTS)
    bad["project/stage126/stage126_m1_robustness_part2_metrics.csv"] = "0" * 64
    monkeypatch.setattr(p3, "PINNED_CLOSED_PART_ARTIFACTS", bad)
    with pytest.raises(p3.QCFail):
        p3.verify_closed_parts_immutable(_root())


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())


def test_no_part5_compatibility_artifact_created():
    assert not os.path.isfile(os.path.join(
        STAGE126,
        "stage126_m1_robustness_part3_part5_successor_compatibility.json",
    ))
    qc = _read_json(p3.F_QC)
    assert qc["stage125_part5_used_as_gate"] is False


def test_part3_source_does_not_touch_part5():
    import ast
    src = open(os.path.join(REAL_ROOT, p3.SRC_REL), encoding="utf-8").read()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "stage125_part5" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "stage125_part5" not in (node.module or "")


# --------------------------------------------------------------------------- #
# Comparison + interpretation
# --------------------------------------------------------------------------- #

def test_comparison_uses_the_locked_primary_values():
    cmp_ = _read_json(p3.F_COMPARISON)
    locked = cmp_["primary_reference"]["locked_pooled_pr_auc"]
    assert locked == {
        "regularized_logistic_regression": 0.445756964048,
        "random_forest": 0.402441830020,
        "xgboost": 0.356545008162,
    }
    assert cmp_["primary_reference"]["locked_values_match_observed"] is True


def test_comparison_derived_from_actual_metrics():
    cmp_ = _read_json(p3.F_COMPARISON)
    pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in _read_csv(p3.F_METRICS)
        if r["scope"] == "pooled_development_oof"
    }
    assert cmp_["part3_pooled_pr_auc"] == {
        k: primary._round(v) for k, v in pooled.items()
    }
    for fam in primary.ALLOWED_MODEL_FAMILIES:
        expected = primary._round(
            pooled[fam] - cmp_["primary_reference"]["observed_pooled_pr_auc"][fam]
        )
        assert math.isclose(
            cmp_["absolute_change_vs_primary"][fam], expected, abs_tol=1e-12
        )
    assert cmp_["part3_observed_ordering"] == sorted(
        primary.ALLOWED_MODEL_FAMILIES, key=lambda f: -pooled[f]
    )
    assert cmp_["primary_ordering_preserved"] == (
        cmp_["primary_observed_ordering"] == cmp_["part3_observed_ordering"]
    )


def test_part2_comparison_is_separated_and_descriptive():
    cmp_ = _read_json(p3.F_COMPARISON)
    d = cmp_["descriptive_part2_comparison"]
    assert d["part2_sample"] == "main_rule_b_listing_robustness"
    assert d["preferred_robustness_sample_selected"] is False
    assert d["claims_multiplied"] is False
    assert set(d["part2_pooled_pr_auc"]) == set(primary.ALLOWED_MODEL_FAMILIES)


def test_interpretation_guards():
    cmp_ = _read_json(p3.F_COMPARISON)
    for field in ("primary_results_replaced", "primary_ordering_lock_changed",
                  "selected_configurations_changed", "paper_winner_selected",
                  "new_confirmatory_model_comparison",
                  "automatic_scientific_action_triggered",
                  "final_test_evaluation_authorized",
                  "full_development_refit_authorized"):
        assert cmp_[field] is False, field
    assert cmp_["scientific_interpretation"] == (
        "development_only_sample_sensitivity_evidence"
    )


def test_readme_is_cautious_and_states_the_guards():
    readme = open(os.path.join(STAGE126, p3.F_README), encoding="utf-8").read()
    assert "development-only sample-sensitivity evidence" in readme
    assert "Only the company-scope sample changed" in readme
    assert "no paper winner was selected" in readme
    assert "strict superset" in readme
    assert "Every added" in readme and "development row is negative" in readme
    assert "Stage125 Part 5 remains historical and immutable" in readme
    assert "Part 4 is not authorized" in readme


# --------------------------------------------------------------------------- #
# Completion lock
# --------------------------------------------------------------------------- #

def test_completion_lock_contract():
    lock = _read_json(p3.F_COMPLETION_LOCK)
    assert lock["category_id"] == "expanded_rule_a_company_scope_robustness"
    assert lock["micro_part_id"] == "stage126-m1-robustness-part3-expanded-rule-a"
    assert lock["part3_human_authorized"] is True
    assert lock["part3_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["development_only"] is True
    assert lock["replaces_primary_results"] is False
    assert lock["selects_paper_winner"] is False
    assert lock["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
    ]
    assert lock["next_category_id"] == "expanded_rule_b_combined_robustness"


def test_completion_lock_authorizes_nothing_further():
    lock = _read_json(p3.F_COMPLETION_LOCK)
    for field in (
        "part4_execution_authorized", "m1_robustness_execution_authorized",
        "full_development_refit_performed", "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed", "smote_executed", "smotenc_executed",
        "shap_executed", "calibration_executed", "bootstrap_executed",
        "holm_executed", "winner_selected", "threshold_optimization_executed",
        "p_values_computed", "m1_robustness_completed",
    ):
        assert lock[field] is False, field


# --------------------------------------------------------------------------- #
# QC / metadata / determinism
# --------------------------------------------------------------------------- #

def test_qc_all_pass_and_identity():
    qc = _read_json(p3.F_QC)
    assert qc["stage"] == "stage126_m1_robustness_part3_expanded_rule_a"
    assert qc["category_id"] == "expanded_rule_a_company_scope_robustness"
    assert qc["micro_part_id"] == "stage126-m1-robustness-part3-expanded-rule-a"
    assert qc["base_main_commit"] == "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 120
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_qc_handoff_markers():
    qc = _read_json(p3.F_QC)
    assert qc["m1_robustness_part3_completed"] is True
    assert qc["m1_robustness_part3_human_authorized"] is True
    assert qc["m1_robustness_part3_authorized"] is False
    assert qc["m1_robustness_part4_authorized"] is False
    assert qc["m1_robustness_execution_authorized"] is False
    assert qc["m1_robustness_completed"] is False
    assert qc["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
    ]
    assert qc["m1_robustness_next_category_id"] == (
        "expanded_rule_b_combined_robustness"
    )
    assert qc["full_development_refit_performed"] is False
    assert qc["final_test_unlocked"] is False


def test_metadata_pins_outputs_and_inputs():
    meta = _read_json(p3.F_METADATA)
    for name in (p3.F_AUTH, p3.F_FEATURE_MANIFEST, p3.F_SAMPLE_DELTA,
                 p3.F_EXEC_MANIFEST, p3.F_OOF, p3.F_METRICS, p3.F_COMPARISON,
                 p3.F_COMPLETION_LOCK, p3.F_README, p3.F_QC):
        assert name in meta["output_files_sha256"], name
        if name != p3.F_QC:
            on_disk = hashlib.sha256(
                open(os.path.join(STAGE126, name), "rb").read()
            ).hexdigest()
            assert meta["output_files_sha256"][name] == on_disk, name
    assert meta["input_files_sha256"][p3.PART3_ANALYSIS_READY_REL] == (
        p3.PART3_ANALYSIS_READY_SHA256
    )
    assert all(v == 0 for v in meta["zero_counters"].values())


def test_deterministic_repeated_build(tmp_path):
    a = p3.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "a", build=True)
    b = p3.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "b", build=True)
    assert a["files"] == b["files"]
    for name, digest in a["files"].items():
        if name in (p3.F_QC, p3.F_METADATA):
            continue
        on_disk = hashlib.sha256(
            open(os.path.join(STAGE126, name), "rb").read()
        ).hexdigest()
        assert digest == on_disk, name


def test_check_mode_is_clean():
    result = p3.run(project_dir=Path(REAL_ROOT) / "project", check=True)
    assert result["drift"] == []
    assert result["qc"]["all_pass"] is True
    assert result["network_requests_attempted"] == 0
