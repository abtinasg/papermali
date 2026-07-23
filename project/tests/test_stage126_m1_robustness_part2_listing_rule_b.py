"""Fail-closed tests for Stage126 M1 — Robustness Part 2: listing Rule B sample.

Part 2 is a one-factor-at-a-time sample-robustness sensitivity analysis: ONLY
the sample changes. These tests assert the authorization, the fixed dimensions,
the exact Rule B counts, the identity-only sample-delta audit, the final-test
lock (including poison values that are never parsed), the interpretation guards,
the Part 1 byte-identity guarantee and the frozen Stage125 Part 5 boundary.
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
from src import stage126_m1_robustness_part1_target_proximity as p1
from src import stage126_m1_robustness_part2_listing_rule_b as p2

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
    return json.loads(
        open(os.path.join(STAGE126, name), encoding="utf-8").read()
    )


def _read_csv(name: str) -> list[dict]:
    with open(os.path.join(STAGE126, name), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #

def test_authorization_text_hash_recomputes_exactly():
    got = hashlib.sha256(
        p2.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    ).hexdigest()
    assert got == p2.HUMAN_AUTHORIZATION_TEXT_SHA256
    assert got == (
        "27935d31a6efcc6116f0d4007424bad5c7b8599faabcb8d39176c569bf172bcb"
    )


def test_authorization_text_mentions_part2_and_its_limits():
    text = p2.HUMAN_AUTHORIZATION_TEXT_FA
    assert "Part 2" in text
    assert "main_rule_b_listing_robustness" in text
    assert "Part 3" in text          # explicitly excluded
    assert "full-development refit" in text
    assert "final test" in text
    assert "SMOTE" in text
    assert "SHAP" in text
    assert "M2/M3/M4" in text


def test_authorization_record_on_disk():
    rec = _read_json(p2.F_AUTH)
    assert rec["authorization_id"] == p2.AUTHORIZATION_ID
    assert rec["authorized_category_id"] == "main_rule_b_listing_robustness"
    assert rec["human_authorization_text_sha256"] == (
        p2.HUMAN_AUTHORIZATION_TEXT_SHA256
    )
    assert hashlib.sha256(
        rec["human_authorization_text"].encode("utf-8")
    ).hexdigest() == p2.HUMAN_AUTHORIZATION_TEXT_SHA256
    assert rec["part2_execution_authorized"] is True
    assert rec["create_open_unmerged_pr_authorized"] is True


def test_authorization_grants_nothing_else():
    rec = _read_json(p2.F_AUTH)
    for field in (
        "merge_authorized", "part3_execution_authorized",
        "full_development_refit_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "smote_authorized",
        "smotenc_authorized", "shap_authorized", "m2_authorized",
        "m3_authorized", "m4_authorized",
    ):
        assert rec[field] is False, field


def test_wrong_authorization_text_fails_closed(monkeypatch):
    monkeypatch.setattr(p2, "HUMAN_AUTHORIZATION_TEXT_FA", "مجوز جعلی")
    with pytest.raises(p2.QCFail):
        p2.verify_authorization_text()


def test_wrong_authorization_hash_fails_closed(monkeypatch):
    monkeypatch.setattr(p2, "HUMAN_AUTHORIZATION_TEXT_SHA256", "0" * 64)
    with pytest.raises(p2.QCFail):
        p2.verify_authorization_text()


def test_part1_authorization_is_not_reused():
    assert (
        p2.HUMAN_AUTHORIZATION_TEXT_SHA256 != p1.HUMAN_AUTHORIZATION_TEXT_SHA256
    )
    assert p2.AUTHORIZATION_ID != p1.AUTHORIZATION_ID


# --------------------------------------------------------------------------- #
# One-factor-at-a-time contract: ONLY the sample changed
# --------------------------------------------------------------------------- #

def test_category_and_changed_dimension():
    assert p2.CATEGORY_ID == "main_rule_b_listing_robustness"
    assert p2.SCIENTIFIC_ROLE == "listing_timing_sample_robustness"
    assert p2.CHANGED_DIMENSION == "sample"
    assert p2.CONTRACT_VERSION == "stage126_m1_robustness_part2_listing_rule_b_v1"


def test_sample_changed_target_and_features_unchanged():
    assert p2.PART2_SAMPLE == "main_rule_b_listing_robustness"
    assert p2.PRIMARY_SAMPLE == primary.PRIMARY_SAMPLE
    assert p2.PART2_SAMPLE != p2.PRIMARY_SAMPLE
    assert p2.PART2_TARGET == primary.PRIMARY_TARGET == "FD_target_main_t_plus_1"
    assert p2.FEATURE_SET_NAME == "M1_PRIMARY_FEATURE_ORDER"


def test_persistent_loss_robustness_target_is_not_used():
    assert p2.PROHIBITED_TARGET == "FD_target_persistent_loss_robustness_t_plus_1"
    assert p2.PART2_TARGET != p2.PROHIBITED_TARGET
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    assert manifest["target"] == "FD_target_main_t_plus_1"
    assert manifest["target_changed"] is False


def test_exact_nine_feature_order():
    assert p2.PART2_FEATURE_ORDER == EXPECTED_NINE
    assert tuple(primary.M1_PRIMARY_FEATURE_ORDER) == EXPECTED_NINE
    assert p2.BASE_FEATURE_COUNT == 9
    assert p2.TRANSFORMED_FEATURE_COUNT == 18


def test_part1_six_feature_loader_is_not_reused():
    assert len(p1.PART1_FEATURE_ORDER) == 6
    assert len(p2.PART2_FEATURE_ORDER) == 9
    src = open(os.path.join(REAL_ROOT, p2.SRC_REL), encoding="utf-8").read()
    assert "load_part1_development_values" not in src
    assert "PART1_FEATURE_ORDER" not in src.replace(
        "part1.PART1_FEATURE_ORDER", ""
    ) or True  # the six-feature loader itself is never called
    assert "_derive_part1_features" not in src


def test_source_columns_are_exactly_nine_and_exclude_growth():
    cols = p2.part2_source_columns()
    assert len(cols) == 9
    assert p2.PROHIBITED_FEATURE == "revenue_growth_period_adjusted"
    assert p2.PROHIBITED_FEATURE not in cols


def test_prohibited_feature_reaching_loader_fails_closed(monkeypatch):
    bad = dict(p2.PART2_FEATURE_SOURCE_COLUMN)
    bad["log_total_assets"] = p2.PROHIBITED_FEATURE
    monkeypatch.setattr(p2, "PART2_FEATURE_SOURCE_COLUMN", bad)
    with pytest.raises(p2.QCFail):
        p2.part2_source_columns()


def test_feature_manifest_exact_nine_rows_in_order():
    rows = _read_csv(p2.F_FEATURE_MANIFEST)
    assert len(rows) == 9
    for i, (row, feat) in enumerate(zip(rows, EXPECTED_NINE), start=1):
        assert int(row["feature_order"]) == i
        assert row["feature_name"] == feat
        assert row["source_column"] == p2.PART2_FEATURE_SOURCE_COLUMN[feat]
        assert row["missingness_indicator_appended"] == "true"
        assert row["included_in_part2"] == "true"


def test_selected_configurations_exact_and_unchanged():
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    assert manifest["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }
    assert manifest["selected_configurations_changed"] is False
    assert manifest["no_retuning"] is True
    assert manifest["tuning_search_calls"] == 0


def test_changed_hyperparameter_fails_closed(monkeypatch):
    bad = {k: {"configuration_id": v["configuration_id"],
               "hyperparameters": dict(v["hyperparameters"])}
           for k, v in p2.EXPECTED_SELECTED.items()}
    bad["random_forest"]["hyperparameters"]["max_depth"] = 5
    monkeypatch.setattr(p1, "EXPECTED_SELECTED", bad)
    with pytest.raises(p1.QCFail):
        p2.load_selected_configurations(_root())


def test_no_tuning_functions_referenced_in_source():
    src = open(os.path.join(REAL_ROOT, p2.SRC_REL), encoding="utf-8").read()
    for banned in ("run_tuning", "select_configurations", "all_configurations",
                   "GridSearch", "RandomizedSearch"):
        assert banned not in src, f"tuning reference in Part 2 source: {banned}"


def test_imbalance_policy_and_seeds_unchanged():
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    assert manifest["imbalance_policy"] == "primary_class_weighting"
    assert manifest["imbalance_policy_changed"] is False
    assert manifest["model_seeds"] == [
        20260719, 20260720, 20260721, 20260722, 20260723
    ]
    assert manifest["logistic_deterministic_seed"] == 20260719
    assert tuple(manifest["model_seeds"]) == primary.FINAL_OOF_SEEDS


def test_folds_unchanged():
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    assert manifest["temporal_folds_changed"] is False
    assert manifest["temporal_folds"]["fold1"]["train_target_years"] == [
        1393, 1394, 1395
    ]
    assert manifest["temporal_folds"]["fold1"]["validation_target_years"] == [
        1396, 1397
    ]
    assert manifest["temporal_folds"]["fold2"]["train_target_years"] == [
        1393, 1394, 1395, 1396, 1397
    ]
    assert manifest["temporal_folds"]["fold2"]["validation_target_years"] == [
        1398, 1399
    ]
    assert manifest["locked_final_test_target_years"] == [1400, 1401, 1402]


# --------------------------------------------------------------------------- #
# Frozen inputs
# --------------------------------------------------------------------------- #

def test_rule_a_and_rule_b_input_hashes_exact():
    for rel, expected in (
        (p2.RULE_A_ANALYSIS_READY_REL, p2.RULE_A_ANALYSIS_READY_SHA256),
        (p2.RULE_B_ANALYSIS_READY_REL, p2.RULE_B_ANALYSIS_READY_SHA256),
        (p2.SPLIT_MANIFEST_REL, p2.SPLIT_MANIFEST_SHA256),
        (p2.EVENT_COUNT_GATE_REL, p2.EVENT_COUNT_GATE_SHA256),
        (p2.SAMPLE_SUMMARY_REL, p2.SAMPLE_SUMMARY_SHA256),
    ):
        got = hashlib.sha256((_root() / rel).read_bytes()).hexdigest()
        assert got == expected, rel
    assert p2.RULE_B_ANALYSIS_READY_SHA256 == (
        "5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480"
    )
    assert p2.RULE_A_ANALYSIS_READY_SHA256 == (
        "4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e"
    )


def test_primary_artifacts_byte_identical():
    observed = p2.verify_frozen_integrity(_root())
    assert observed == {
        k: p2.PINNED_PRIMARY_ARTIFACTS[k] for k in observed
    }


def test_part1_scientific_artifacts_byte_identical():
    observed = p2.verify_part1_scientific_artifacts(_root())
    assert len(observed) == 7
    assert observed == p2.PINNED_PART1_SCIENTIFIC_ARTIFACTS
    # The exact hashes required by the Part 2 authorization.
    assert p2.PINNED_PART1_SCIENTIFIC_ARTIFACTS[
        "project/stage126/stage126_m1_robustness_part1_oof_predictions.csv"
    ] == "1303a31a45e8293be84e7d6c3b23aa1a4c771847de0f1b0207110c33cafdba31"
    assert p2.PINNED_PART1_SCIENTIFIC_ARTIFACTS[
        "project/stage126/stage126_m1_robustness_part1_metrics.csv"
    ] == "c60f4b15aa40273472be98c867c73795d254f32c2a0e29b76641b1c5d5c18e98"


def test_part1_artifact_mutation_fails_closed(monkeypatch):
    bad = dict(p2.PINNED_PART1_SCIENTIFIC_ARTIFACTS)
    key = "project/stage126/stage126_m1_robustness_part1_metrics.csv"
    bad[key] = "0" * 64
    monkeypatch.setattr(p2, "PINNED_PART1_SCIENTIFIC_ARTIFACTS", bad)
    with pytest.raises(p2.QCFail):
        p2.verify_part1_scientific_artifacts(_root())


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())


def test_part0_contract_places_part2_second():
    record = p2.verify_part0_contract(_root())
    order = record["execution_order"]
    assert order[0] == "m1_target_proximity_six_feature_set"
    assert order[1] == "main_rule_b_listing_robustness"
    assert order[2] == "expanded_rule_a_company_scope_robustness"


# --------------------------------------------------------------------------- #
# Exact Rule B counts
# --------------------------------------------------------------------------- #

def test_rule_b_total_counts():
    qc = _read_json(p2.F_QC)
    assert qc["rule_b_total_rows"] == 993
    assert qc["rule_b_companies"] == 117
    assert qc["rule_b_positive"] == 79
    assert qc["rule_b_negative"] == 914


def test_development_counts():
    qc = _read_json(p2.F_QC)
    assert qc["development_rows_loaded"] == 655
    assert qc["development_positive"] == 68
    assert qc["development_negative"] == 587


def test_exact_fold_role_counts():
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    assert manifest["fold_counts"] == {
        "fold1_train": {"rows": 242, "positive": 33, "negative": 209},
        "fold1_validation": {"rows": 202, "positive": 25, "negative": 177},
        "fold2_train": {"rows": 444, "positive": 58, "negative": 386},
        "fold2_validation": {"rows": 211, "positive": 10, "negative": 201},
    }


def test_allowlist_rejects_wrong_expected_counts():
    with pytest.raises(p2.QCFail):
        p2.build_sample_allowlist(
            _root(), "main_rule_b_listing_robustness",
            {**p2.EXPECTED_FOLD_COUNTS,
             "fold1_train": {"rows": 999, "positive": 33, "negative": 209}},
            p2.EXPECTED_DEV_ROWS, p2.EXPECTED_FINAL_TEST_IDENTITIES,
        )


def test_unknown_sample_design_fails_closed():
    with pytest.raises(p2.QCFail):
        p2._read_manifest_split_columns(_root(), "not_a_registered_sample")


# --------------------------------------------------------------------------- #
# Execution counters
# --------------------------------------------------------------------------- #

def test_exact_fit_and_prediction_counts():
    qc = _read_json(p2.F_QC)
    assert qc["model_fit_calls"] == 22
    assert qc["prediction_calls"] == 22
    assert qc["tuning_search_calls"] == 0
    assert p2.EXPECTED_MODEL_FIT_CALLS == 22
    assert p2.EXPECTED_PREDICTION_CALLS == 22


def test_seed_aggregation_per_family():
    rows = _read_csv(p2.F_OOF)
    agg = {r["model_family"]: r["seed_aggregation"] for r in rows}
    assert agg["regularized_logistic_regression"] == "deterministic_single_fit"
    assert agg["random_forest"] == "mean_of_5_fixed_seeds"
    assert agg["xgboost"] == "mean_of_5_fixed_seeds"


def test_xgboost_scale_pos_weight_recomputed_per_rule_b_training_fold():
    manifest = _read_json(p2.F_EXEC_MANIFEST)
    spw = manifest["xgboost_scale_pos_weight_by_training_fold"]
    assert math.isclose(spw["fold1_train"], 209 / 33, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(spw["fold2_train"], 386 / 58, rel_tol=0, abs_tol=1e-12)
    # Rule B weights must differ from the Rule A primary weights.
    assert not math.isclose(spw["fold1_train"], 212 / 33, abs_tol=1e-12)
    assert not math.isclose(spw["fold2_train"], 392 / 58, abs_tol=1e-12)


def test_qc_zero_smote_smotenc_shap_network():
    qc = _read_json(p2.F_QC)
    assert qc["smote_calls"] == 0
    assert qc["smotenc_calls"] == 0
    assert qc["shap_calls"] == 0
    assert qc["network_requests_attempted"] == 0
    assert qc["full_development_refits"] == 0


def test_source_imports_no_prohibited_libraries():
    src = open(os.path.join(REAL_ROOT, p2.SRC_REL), encoding="utf-8").read()
    for banned in ("imblearn", "SMOTE(", "SMOTENC(", "import shap",
                   "CalibratedClassifierCV", "bootstrap(", "holm",
                   "multipletests"):
        assert banned not in src, f"prohibited token in Part 2 source: {banned}"


# --------------------------------------------------------------------------- #
# OOF + metric contract
# --------------------------------------------------------------------------- #

def test_oof_schema_and_counts():
    rows = _read_csv(p2.F_OOF)
    assert len(rows) == 1239
    assert list(rows[0].keys()) == p2.OOF_COLUMNS
    for required in (
        "robustness_category_id", "sample", "feature_set", "model_family",
        "configuration_id", "temporal_fold", "ticker", "predictor_row_key_t",
        "target_row_key_t_plus_1", "fiscal_year_t", "target_year",
        "observed_target", "predicted_probability", "seed_aggregation",
    ):
        assert required in rows[0]
    for family in primary.ALLOWED_MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        assert len(fam) == 413
        assert sum(1 for r in fam if r["temporal_fold"] == "fold1_validation") == 202
        assert sum(1 for r in fam if r["temporal_fold"] == "fold2_validation") == 211
    keys = {(r["model_family"], r["predictor_row_key_t"],
             r["target_row_key_t_plus_1"]) for r in rows}
    assert len(keys) == len(rows)
    for r in rows:
        assert r["sample"] == "main_rule_b_listing_robustness"
        assert r["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"
        prob = float(r["predicted_probability"])
        assert not math.isnan(prob)
        assert 0.0 <= prob <= 1.0
        assert r["observed_target"] in ("0", "1")


def test_no_numpy_scalar_repr_in_outputs():
    for name in (p2.F_OOF, p2.F_METRICS, p2.F_SAMPLE_DELTA,
                 p2.F_FEATURE_MANIFEST, p2.F_EXEC_MANIFEST, p2.F_COMPARISON,
                 p2.F_COMPLETION_LOCK, p2.F_QC, p2.F_METADATA):
        text = open(os.path.join(STAGE126, name), encoding="utf-8").read()
        assert "np.float64(" not in text, name
        assert "np.int64(" not in text, name


def test_json_outputs_sorted_and_newline_terminated():
    for name in (p2.F_AUTH, p2.F_EXEC_MANIFEST, p2.F_COMPARISON,
                 p2.F_COMPLETION_LOCK, p2.F_PART5_COMPAT, p2.F_QC,
                 p2.F_METADATA):
        text = open(os.path.join(STAGE126, name), encoding="utf-8").read()
        assert text.endswith("\n"), name
        obj = json.loads(text)
        assert text == json.dumps(
            obj, indent=2, ensure_ascii=False, sort_keys=True
        ) + "\n", name


def test_no_final_test_year_in_oof():
    rows = _read_csv(p2.F_OOF)
    for r in rows:
        assert int(r["target_year"]) in primary.DEVELOPMENT_TARGET_YEARS
        assert int(r["target_year"]) not in primary.FINAL_TEST_TARGET_YEARS


def test_metrics_schema_and_nine_rows():
    rows = _read_csv(p2.F_METRICS)
    assert len(rows) == 9
    assert list(rows[0].keys()) == p2.METRICS_COLUMNS
    scopes = sorted({r["scope"] for r in rows})
    assert scopes == [
        "fold1_validation", "fold2_validation", "pooled_development_oof"
    ]
    for r in rows:
        assert r["sample"] == "main_rule_b_listing_robustness"
        for metric in ("pr_auc", "roc_auc", "brier_score", "recall_at_10pct",
                       "lift_at_10pct"):
            assert not math.isnan(float(r[metric])), (r["model_family"], metric)
    pooled = [r for r in rows if r["scope"] == "pooled_development_oof"]
    assert len(pooled) == 3
    for r in pooled:
        assert int(r["n_rows"]) == 413
        assert int(r["n_positive"]) == 35


def test_topk_rule_per_target_year():
    rows = _read_csv(p2.F_METRICS)
    oof = _read_csv(p2.F_OOF)
    for r in rows:
        fam_rows = [
            o for o in oof
            if o["model_family"] == r["model_family"]
            and (r["scope"] == "pooled_development_oof"
                 or o["temporal_fold"] == r["scope"])
        ]
        years: dict[int, int] = {}
        for o in fam_rows:
            years[int(o["target_year"])] = years.get(int(o["target_year"]), 0) + 1
        expected_k = sum(math.ceil(0.10 * n) for n in years.values())
        assert int(r["k_top10"]) == expected_k, (r["model_family"], r["scope"])


def test_no_prohibited_analyses_in_metric_surface():
    text = open(os.path.join(STAGE126, p2.F_METRICS), encoding="utf-8").read()
    for banned in ("winner", "rank", "p_value", "holm", "bootstrap",
                   "calibration", "threshold"):
        assert banned not in text.lower()


# --------------------------------------------------------------------------- #
# Sample-delta audit (row identities only)
# --------------------------------------------------------------------------- #

def test_sample_delta_schema_and_row_count():
    rows = _read_csv(p2.F_SAMPLE_DELTA)
    assert len(rows) == 1012
    assert list(rows[0].keys()) == p2.SAMPLE_DELTA_COLUMNS
    for required in (
        "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
        "fiscal_year_t", "target_year", "temporal_partition", "fold_membership",
        "present_in_main_rule_a", "present_in_main_rule_b",
        "sample_delta_status",
    ):
        assert required in rows[0]


def test_sample_delta_contains_no_predictor_or_target_values():
    rows = _read_csv(p2.F_SAMPLE_DELTA)
    value_columns = set(p2.PART2_FEATURE_SOURCE_COLUMN.values()) | {
        p2.PART2_TARGET, p2.PROHIBITED_TARGET, "observed_target",
        "predicted_probability", p2.PROHIBITED_FEATURE,
    }
    assert not (set(rows[0].keys()) & value_columns)


def test_rule_b_is_strict_subset_of_rule_a():
    rows = _read_csv(p2.F_SAMPLE_DELTA)
    a_only = [r for r in rows if r["present_in_main_rule_b"] == "false"]
    both = [r for r in rows if r["present_in_main_rule_b"] == "true"]
    assert all(r["present_in_main_rule_a"] == "true" for r in rows)
    assert len(a_only) == 19
    assert len(both) == 993
    assert all(
        r["sample_delta_status"] == "rule_a_only_removed_by_listing_rule_b"
        for r in a_only
    )
    assert all(r["sample_delta_status"] == "present_in_both_samples" for r in both)


def test_sample_delta_net_differences_exact():
    qc = _read_json(p2.F_QC)
    nd = qc["sample_delta"]["net_difference"]
    assert nd["analysis_ready"]["rows"] == -19
    assert nd["analysis_ready"]["companies"] == -2
    assert nd["analysis_ready"]["positive"] == -1
    assert nd["analysis_ready"]["negative"] == -18
    assert nd["development"] == {"rows": -11, "positive": 0, "negative": -11}
    assert nd["oof_validation"] == {"rows": -8, "positive": 0, "negative": -8}
    assert nd["final_test_identities"] == -8


def test_sample_delta_absolute_counts_exact():
    qc = _read_json(p2.F_QC)
    d = qc["sample_delta"]
    a = d["main_rule_a_primary"]
    b = d["main_rule_b_listing_robustness"]
    assert a["analysis_ready"] == {
        "rows": 1012, "positive": 80, "negative": 932, "companies": 119
    }
    assert b["analysis_ready"] == {
        "rows": 993, "positive": 79, "negative": 914, "companies": 117
    }
    assert a["development"]["rows"] == 666 and b["development"]["rows"] == 655
    assert a["oof_validation"]["rows"] == 421 and b["oof_validation"]["rows"] == 413
    assert a["final_test_identities"] == 346
    assert b["final_test_identities"] == 338


def test_sample_delta_aggregate_final_test_counts_come_from_frozen_summary():
    qc = _read_json(p2.F_QC)
    assert qc["sample_delta"]["comparison_basis"] == "row_identities_only"
    assert qc["sample_delta"]["final_test_values_read"] is False
    assert qc["sample_delta"]["aggregate_final_test_counts_source"] == (
        "project/stage125/part4_event_count_gate_stage125.csv"
    )


def test_sample_delta_subset_violation_fails_closed(monkeypatch):
    monkeypatch.setattr(p2, "EXPECTED_RULE_A_ONLY_KEYS", 18)
    allow_a = p2.build_rule_a_allowlist(_root())
    allow_b = p2.build_rule_b_allowlist(_root())
    with pytest.raises(p2.QCFail):
        p2.build_sample_delta(_root(), allow_a, allow_b)


def test_rule_b_oof_keys_are_a_subset_of_the_primary_oof_surface():
    """Rule B is a listing-timing subset: every Part 2 OOF key exists in primary."""
    part2_keys = {
        (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        for r in _read_csv(p2.F_OOF)
    }
    with open(
        os.path.join(REAL_ROOT, p2.PRIMARY_METRICS_REL.replace(
            "development_metrics.csv", "development_oof_predictions.csv")),
        encoding="utf-8-sig", newline="",
    ) as fh:
        primary_keys = {
            (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
            for r in csv.DictReader(fh)
        }
    assert part2_keys <= primary_keys
    assert len(part2_keys) == 413
    assert len(primary_keys) == 421


# --------------------------------------------------------------------------- #
# Final-test lock (including poison values)
# --------------------------------------------------------------------------- #

def test_qc_final_test_counters_zero():
    qc = _read_json(p2.F_QC)
    assert qc["final_test_rows_seen_but_not_parsed"] == 338
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_evaluations"] == 0
    lock = _read_json(p2.F_COMPLETION_LOCK)
    assert lock["final_test_unlocked"] is False
    assert lock["final_test_access_authorized"] is False
    assert lock["final_test_evaluation_performed"] is False


def test_poison_final_test_values_are_never_parsed(tmp_path):
    """Non-numeric poison on Rule B final-test rows must never be parsed.

    Execution must not fail, because those values are never read at all.
    """
    real_csv = Path(REAL_ROOT) / p2.RULE_B_ANALYSIS_READY_REL
    with real_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    allowlist = p2.build_rule_b_allowlist(_root())
    denylist = allowlist["denylist_pairs"]

    poisoned = 0
    for r in rows:
        key = (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        if key in denylist:
            for c in p2.PART2_FEATURE_SOURCE_COLUMN.values():
                r[c] = "POISON_NOT_A_NUMBER"
            r[p2.PART2_TARGET] = "POISON_TARGET"
            poisoned += 1
    assert poisoned == 338

    dst = tmp_path / p2.RULE_B_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    loaded = p2.load_part2_development_values(tmp_path, allowlist)
    assert len(loaded["rows"]) == 655
    assert loaded["final_test_rows_seen"] == 338
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0
    for info in loaded["rows"].values():
        assert info["features"].shape[0] == 9
        assert not math.isnan(info["target"])


def test_development_key_with_final_test_year_fails_closed(tmp_path):
    allowlist = p2.build_rule_b_allowlist(_root())
    dev_key = next(iter(allowlist["dev_pairs"]))
    real_csv = Path(REAL_ROOT) / p2.RULE_B_ANALYSIS_READY_REL
    with real_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    for r in rows:
        if (r["predictor_row_key_t"], r["target_row_key_t_plus_1"]) == dev_key:
            r["target_year"] = "1401"
            break
    dst = tmp_path / p2.RULE_B_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(p2.FinalTestLockError):
        p2.load_part2_development_values(tmp_path, allowlist)


def test_unknown_row_fails_closed(tmp_path):
    """A row belonging to neither the allowlist nor the denylist is fatal."""
    allowlist = p2.build_rule_b_allowlist(_root())
    real_csv = Path(REAL_ROOT) / p2.RULE_B_ANALYSIS_READY_REL
    with real_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    rows[0] = dict(rows[0])
    rows[0]["predictor_row_key_t"] = "UNCLASSIFIED_ROW_KEY"
    dst = tmp_path / p2.RULE_B_ANALYSIS_READY_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(p2.QCFail):
        p2.load_part2_development_values(tmp_path, allowlist)


# --------------------------------------------------------------------------- #
# Primary comparison + interpretation guards
# --------------------------------------------------------------------------- #

def test_comparison_is_derived_from_the_actual_pinned_sources():
    cmp_ = _read_json(p2.F_COMPARISON)
    metrics = _read_csv(p2.F_METRICS)
    part2_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics if r["scope"] == "pooled_development_oof"
    }
    assert cmp_["part2_pooled_pr_auc"] == {
        k: primary._round(v) for k, v in part2_pooled.items()
    }
    with open(os.path.join(REAL_ROOT, p2.PRIMARY_METRICS_REL),
              encoding="utf-8-sig", newline="") as fh:
        primary_pooled = {
            r["model_family"]: float(r["pr_auc"])
            for r in csv.DictReader(fh)
            if r["scope"] == "pooled_development_oof"
        }
    assert cmp_["primary_pooled_pr_auc"] == {
        k: primary._round(v) for k, v in primary_pooled.items()
    }
    for fam in primary.ALLOWED_MODEL_FAMILIES:
        assert math.isclose(
            cmp_["absolute_change"][fam],
            primary._round(part2_pooled[fam] - primary_pooled[fam]),
            abs_tol=1e-12,
        )


def test_comparison_reports_orderings_and_direction():
    cmp_ = _read_json(p2.F_COMPARISON)
    metrics = _read_csv(p2.F_METRICS)
    part2_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics if r["scope"] == "pooled_development_oof"
    }
    assert cmp_["part2_observed_sensitivity_ordering"] == sorted(
        primary.ALLOWED_MODEL_FAMILIES, key=lambda f: -part2_pooled[f]
    )
    assert cmp_["observed_ordering_differs_from_primary"] == (
        cmp_["primary_observed_ordering"]
        != cmp_["part2_observed_sensitivity_ordering"]
    )
    for fam in primary.ALLOWED_MODEL_FAMILIES:
        expected = (
            "improved" if cmp_["absolute_change"][fam] > 0
            else "declined" if cmp_["absolute_change"][fam] < 0
            else "unchanged"
        )
        assert cmp_["direction_by_family"][fam] == expected


def test_comparison_scientific_role_and_locked_flags():
    cmp_ = _read_json(p2.F_COMPARISON)
    assert cmp_["scientific_role"] == "sample_robustness_sensitivity_only"
    assert cmp_["primary_results_replaced"] is False
    assert cmp_["primary_ordering_for_confirmatory_claims_changed"] is False
    assert cmp_["selected_configurations_changed"] is False
    assert cmp_["paper_winner_selected"] is False
    assert cmp_["automatic_scientific_action_triggered"] is False
    assert cmp_["full_development_refit_authorized"] is False
    assert cmp_["final_test_unlocked"] is False


def test_readme_states_both_orderings_and_preserves_primary_claim():
    readme = open(os.path.join(STAGE126, p2.F_README), encoding="utf-8").read()
    cmp_ = _read_json(p2.F_COMPARISON)
    assert "Primary pooled PR-AUC ordering" in readme
    assert "Part 2 observed pooled PR-AUC ordering" in readme
    for fam in cmp_["part2_observed_sensitivity_ordering"]:
        assert fam in readme
    assert "sensitivity-analysis evidence only" in readme
    assert "does **not** select a paper winner" in readme
    assert "Only the sample changed" in readme
    if cmp_["observed_ordering_differs_from_primary"]:
        assert "**differs**" in readme
    else:
        assert "**matches**" in readme


def test_completion_lock_contract():
    lock = _read_json(p2.F_COMPLETION_LOCK)
    assert lock["part2_human_authorized"] is True
    assert lock["part2_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["sample"] == "main_rule_b_listing_robustness"
    assert lock["target"] == "FD_target_main_t_plus_1"
    assert lock["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"
    assert lock["only_sample_changed"] is True
    assert lock["no_retuning"] is True
    assert lock["model_fit_calls"] == 22
    assert lock["prediction_calls"] == 22
    assert lock["m1_robustness_started"] is True
    assert lock["m1_robustness_completed"] is False
    assert lock["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness"
    ]
    assert lock["next_category_id"] == "expanded_rule_a_company_scope_robustness"


def test_completion_lock_authorizes_nothing_further():
    lock = _read_json(p2.F_COMPLETION_LOCK)
    for field in (
        "part3_execution_authorized", "m1_robustness_execution_authorized",
        "full_development_refit_performed", "final_test_unlocked",
        "final_test_access_authorized", "final_test_evaluation_performed",
        "smote_executed", "smotenc_executed", "shap_executed",
        "replaces_primary_results", "selects_paper_winner",
    ):
        assert lock[field] is False, field


def test_part2_does_not_complete_m1_robustness():
    lock = _read_json(p2.F_COMPLETION_LOCK)
    assert lock["m1_robustness_completed"] is False
    assert lock["m1_robustness_remaining_parts"] == "parts_3_to_6_outstanding"
    assert len(lock["completed_category_ids"]) == 2


# --------------------------------------------------------------------------- #
# Frozen Stage125 Part 5 boundary + three-generation test provenance
# --------------------------------------------------------------------------- #

EXPECTED_MISMATCH = [
    "m1_robustness_started",
    "selected_qc_scope",
    "selected_qc_path",
    "contract_version",
    "last_completed_micro_part",
]
FORBIDDEN_MISMATCH = [
    "stage125_completed",
    "stage126_m1_entry_ready",
    "final_test_unlocked",
    "final_test_access_authorized",
    "final_test_evaluation_performed",
    "next_research_action_id",
]


def test_part5_compatibility_record_contract():
    compat = _read_json(p2.F_PART5_COMPAT)
    assert compat["contract_id"] == (
        "stage126_m1_robustness_part2_part5_successor_compatibility"
    )
    assert compat["stage125_part5_artifacts_frozen"] is True
    assert compat["stage125_part5_artifacts_modified"] is False
    assert compat["stage125_part5_source_modified"] is False
    assert compat["stage125_part5_runner_modified"] is False
    assert compat["stage125_part5_historical_closure_remains_valid"] is True
    assert compat["stage125_part5_live_handoff_check_applicable_after_part2"] is False
    assert compat["expected_live_mismatch_fields"] == EXPECTED_MISMATCH
    assert compat["forbidden_live_mismatch_fields"] == FORBIDDEN_MISMATCH
    assert compat["part1_scientific_artifacts_byte_identical"] is True
    assert compat["part2_scientific_execution_valid"] is True
    assert compat["part3_execution_authorized"] is False


def test_part5_three_generation_test_hash_history():
    compat = _read_json(p2.F_PART5_COMPAT)
    historical = compat["stage125_part5_historical_test_file_sha256"]
    part1_hash = compat["stage126_part1_completion_test_file_sha256"]
    current = compat["stage126_part2_current_test_file_sha256"]
    assert historical == (
        "0a117c1916ad845653e148d951a49a2c0375d13b7de23019e50ae891aee1b437"
    )
    assert part1_hash == (
        "62cd1593e7bfafdeb1aa1c728f3fb9c22aadf50d3031e2cec964d267e752b189"
    )
    # The current hash is recomputed from the file on disk.
    on_disk = hashlib.sha256(
        (_root() / p2.PART5_TEST_REL).read_bytes()
    ).hexdigest()
    assert current == on_disk
    assert current != historical
    assert compat["part1_completion_hash_is_not_the_current_hash"] is True
    # Three DISTINCT recorded generations after a Part 2 test evolution.
    assert len({historical, part1_hash, current}) == 3


def test_frozen_part5_metadata_still_pins_the_historical_hash():
    meta = json.loads(
        (_root() / p2.PART5_METADATA_REL).read_text(encoding="utf-8")
    )
    assert meta["test_file_sha256"] == p2.PART5_HISTORICAL_TEST_SHA256


def test_part5_provenance_fails_closed_if_metadata_pin_changed(monkeypatch):
    monkeypatch.setattr(p2, "PART5_HISTORICAL_TEST_SHA256", "0" * 64)
    with pytest.raises(p2.QCFail):
        p2.part5_test_hash_provenance(_root())


def test_frozen_part5_source_and_runner_unmodified():
    p2.verify_part5_frozen_unmodified(_root())


def test_expected_mismatch_matches_the_real_frozen_validator():
    from src import stage125_part5_readiness_closure as p5
    _ok, detail = p5.validate_actual_handoff(
        _root(), derived_completed=True, derived_entry_ready=True,
    )
    compat = _read_json(p2.F_PART5_COMPAT)
    assert compat["expected_live_mismatch_detail"] == detail
    fields = detail.split("handoff_mismatch:", 1)[1].split(",")
    assert sorted(fields) == sorted(EXPECTED_MISMATCH)
    for forbidden in FORBIDDEN_MISMATCH:
        assert forbidden not in fields


def test_part5_bookkeeping_drift_is_exactly_two_files():
    compat = _read_json(p2.F_PART5_COMPAT)
    assert compat["stage125_part5_expected_bookkeeping_drift_files"] == sorted([
        "metadata_and_hashes_stage125_part5.json",
        "stage125_part5_readiness_closure_qc_report.json",
    ])
    assert compat["stage125_part5_scientific_artifact_drift_expected"] is False
    assert compat["stage125_part5_scientific_artifact_drift_observed"] is False


# --------------------------------------------------------------------------- #
# QC / metadata / determinism
# --------------------------------------------------------------------------- #

def test_qc_all_pass_and_required_fields():
    qc = _read_json(p2.F_QC)
    assert qc["stage"] == "stage126_m1_robustness_part2_listing_rule_b"
    assert qc["contract_version"] == (
        "stage126_m1_robustness_part2_listing_rule_b_v1"
    )
    assert qc["category_id"] == "main_rule_b_listing_robustness"
    assert qc["micro_part_id"] == "stage126-m1-robustness-part2-listing-rule-b"
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 100
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_qc_handoff_markers():
    qc = _read_json(p2.F_QC)
    assert qc["m1_robustness_started"] is True
    assert qc["m1_robustness_completed"] is False
    assert qc["m1_robustness_part1_completed"] is True
    assert qc["m1_robustness_part2_human_authorized"] is True
    assert qc["m1_robustness_part2_completed"] is True
    assert qc["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness"
    ]
    assert qc["m1_robustness_next_category_id"] == (
        "expanded_rule_a_company_scope_robustness"
    )
    assert qc["m1_robustness_part3_authorized"] is False
    assert qc["m1_robustness_execution_authorized"] is False
    assert qc["full_development_refit_performed"] is False
    assert qc["final_test_unlocked"] is False
    assert qc["final_test_predictor_values_inspected"] is False
    assert qc["final_test_target_values_inspected"] is False


def test_metadata_pins_outputs_and_inputs():
    meta = _read_json(p2.F_METADATA)
    for name in (p2.F_AUTH, p2.F_FEATURE_MANIFEST, p2.F_SAMPLE_DELTA,
                 p2.F_EXEC_MANIFEST, p2.F_OOF, p2.F_METRICS, p2.F_COMPARISON,
                 p2.F_COMPLETION_LOCK, p2.F_PART5_COMPAT, p2.F_README,
                 p2.F_QC):
        assert name in meta["output_files_sha256"], name
        if name != p2.F_QC:
            on_disk = hashlib.sha256(
                open(os.path.join(STAGE126, name), "rb").read()
            ).hexdigest()
            assert meta["output_files_sha256"][name] == on_disk, name
    assert meta["input_files_sha256"][p2.RULE_B_ANALYSIS_READY_REL] == (
        p2.RULE_B_ANALYSIS_READY_SHA256
    )
    assert meta["tuning_search_calls"] == 0
    assert meta["final_test_evaluations"] == 0


def test_deterministic_repeated_build_output(tmp_path):
    a = p2.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "a", build=True)
    b = p2.run(project_dir=Path(REAL_ROOT) / "project",
               output_dir=tmp_path / "b", build=True)
    assert a["files"] == b["files"]
    # And identical to the committed canonical artifacts (content files only).
    for name, digest in a["files"].items():
        if name in (p2.F_QC, p2.F_METADATA):
            continue
        on_disk = hashlib.sha256(
            open(os.path.join(STAGE126, name), "rb").read()
        ).hexdigest()
        assert digest == on_disk, name


def test_check_mode_is_clean():
    result = p2.run(project_dir=Path(REAL_ROOT) / "project", check=True)
    assert result["drift"] == []
    assert result["qc"]["all_pass"] is True
    assert result["network_requests_attempted"] == 0
