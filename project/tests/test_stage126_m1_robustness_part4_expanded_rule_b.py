"""Fail-closed tests for Stage126 M1 — Robustness Part 4: expanded Rule B.

Part 4 is a one-factor-at-a-time sample-robustness sensitivity analysis: ONLY
the combined (expanded Rule B) sample changes. These tests assert the exact
authorization, the fixed dimensions, the exact combined-sample counts, the
THREE independently recomputed identity-only sample-delta audits (versus
Part 2 — strict superset; versus Part 3 — strict subset; versus the locked
primary sample — a general, neither-sub-nor-super-set comparison), the
final-test lock, the zero counters for every forbidden operation, the
interpretation guards, and the byte-identity of the closed Part 1 / Part 2 /
Part 3 packages and Stage125.
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
from src import stage126_m1_robustness_part4_expanded_rule_b as p4

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
    raw = p4.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    assert len(raw) == 418
    assert len(raw) == p4.HUMAN_AUTHORIZATION_TEXT_BYTES
    assert hashlib.sha256(raw).hexdigest() == (
        "e40852d9e2a78cc6d9b3079379abd0fed8f4921b65bec00ecf58d5aad78fd1b4"
    )
    assert hashlib.sha256(raw).hexdigest() == p4.HUMAN_AUTHORIZATION_TEXT_SHA256


def test_authorization_text_shape_and_content():
    text = p4.HUMAN_AUTHORIZATION_TEXT_FA
    assert not text.endswith("\n")
    paragraphs = text.split("\n\n")
    assert len(paragraphs) == 2
    assert "Part 4" in paragraphs[0]
    assert "expanded_rule_b_combined_robustness" in paragraphs[0]
    for excluded in ("Merge", "Part 5", "full-development refit", "final test",
                     "calibration", "bootstrap", "Holm", "winner selection",
                     "SMOTE", "SHAP", "M2/M3/M4"):
        assert excluded in paragraphs[1], excluded


def test_wrong_authorization_text_fails_closed(monkeypatch):
    monkeypatch.setattr(p4, "HUMAN_AUTHORIZATION_TEXT_FA", "مجوز جعلی")
    with pytest.raises(p4.QCFail):
        p4.verify_authorization_text()


def test_wrong_authorization_hash_fails_closed(monkeypatch):
    monkeypatch.setattr(p4, "HUMAN_AUTHORIZATION_TEXT_SHA256", "0" * 64)
    with pytest.raises(p4.QCFail):
        p4.verify_authorization_text()


def test_authorization_record_on_disk():
    rec = _read_json(p4.F_AUTH)
    assert rec["authorization_id"] == p4.AUTHORIZATION_ID
    assert rec["authorized_category_id"] == "expanded_rule_b_combined_robustness"
    assert rec["human_authorization_text_utf8_bytes"] == 418
    assert hashlib.sha256(
        rec["human_authorization_text"].encode("utf-8")
    ).hexdigest() == p4.HUMAN_AUTHORIZATION_TEXT_SHA256
    assert rec["part4_execution_authorized"] is True
    assert rec["development_fold_execution_authorized"] is True
    assert rec["create_open_unmerged_pr_authorized"] is True
    assert rec["authorized_base_main_commit"] == (
        "853a8deff5e0953ba4018e7406230fdf5ed5a3ae"
    )


def test_authorization_grants_nothing_else():
    rec = _read_json(p4.F_AUTH)
    for field in (
        "merge_authorized", "part5_execution_authorized",
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

def test_part0_places_part4_fourth_and_part5_next():
    record = p4.verify_part0_contract(_root())
    order = record["execution_order"]
    assert order[0] == "m1_target_proximity_six_feature_set"
    assert order[1] == "main_rule_b_listing_robustness"
    assert order[2] == "expanded_rule_a_company_scope_robustness"
    assert order[3] == "expanded_rule_b_combined_robustness"
    assert order[4] == "persistent_loss_robustness_target"


def test_parts_1_2_3_must_precede_part4():
    assert p4.verify_predecessors_completed(_root()) == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
    ]


def test_missing_predecessor_fails_closed(tmp_path):
    (tmp_path / "project" / "stage126").mkdir(parents=True)
    with pytest.raises(p4.QCFail):
        p4.verify_predecessors_completed(tmp_path)


# --------------------------------------------------------------------------- #
# Frozen contract: only the sample changed
# --------------------------------------------------------------------------- #

def test_category_role_and_changed_dimension():
    assert p4.CATEGORY_ID == "expanded_rule_b_combined_robustness"
    assert p4.SCIENTIFIC_ROLE == "combined_sample_robustness"
    assert p4.CHANGED_DIMENSION == "sample"
    assert p4.MICRO_PART_ID == "stage126-m1-robustness-part4-expanded-rule-b"
    assert p4.NEXT_CATEGORY_ID == "persistent_loss_robustness_target"


def test_sample_changed_everything_else_fixed():
    em = _read_json(p4.F_EXEC_MANIFEST)
    assert em["sample"] == "expanded_rule_b_combined_robustness"
    assert em["primary_sample"] == "main_rule_a_primary"
    assert em["target_changed"] is False
    assert em["feature_set_changed"] is False
    assert em["preprocessing_changed"] is False
    assert em["missingness_indicator_logic_changed"] is False
    assert em["selected_configurations_changed"] is False
    assert em["imbalance_policy_changed"] is False
    assert em["temporal_folds_changed"] is False
    assert em["seeds_changed"] is False


def test_canonical_sample_path_and_hash():
    assert p4.PART4_ANALYSIS_READY_REL == (
        "project/stage125/part3c_outputs/"
        "analysis_ready_expanded_rule_b_stage125.csv"
    )
    assert p4.PART4_ANALYSIS_READY_SHA256 == (
        "2e61a282165ccdaef37bac61a460c83878f2ae633b10535945cc33897d3b4c22"
    )
    assert p4.sha256_file(_root() / p4.PART4_ANALYSIS_READY_REL) == (
        p4.PART4_ANALYSIS_READY_SHA256
    )


def test_exact_nine_feature_order_and_matrix_width():
    assert p4.PART4_FEATURE_ORDER == EXPECTED_NINE
    assert p4.BASE_FEATURE_COUNT == 9
    assert p4.TRANSFORMED_FEATURE_COUNT == 18
    assert p4.PROHIBITED_FEATURE not in p4.PART4_FEATURE_ORDER


def test_feature_manifest_declares_indicator_column_order():
    rows = _read_csv(p4.F_FEATURE_MANIFEST)
    assert len(rows) == 9
    for i, row in enumerate(rows, start=1):
        assert int(row["feature_order"]) == i
        assert row["feature_name"] == EXPECTED_NINE[i - 1]
        assert int(row["missingness_indicator_column_index"]) == 9 + i
        assert row["missingness_indicator_appended"] == "true"
        assert row["included_in_part4"] == "true"


def test_prohibited_feature_and_target_absent():
    em = _read_json(p4.F_EXEC_MANIFEST)
    assert p4.PROHIBITED_FEATURE not in em["features_exact_order"]
    assert p4.PROHIBITED_FEATURE not in em["feature_source_columns"].values()
    assert em["target"] != p4.PROHIBITED_TARGET


def test_prohibited_feature_reaching_loader_fails_closed(monkeypatch):
    bad = dict(p4.PART4_FEATURE_SOURCE_COLUMN)
    bad[EXPECTED_NINE[0]] = p4.PROHIBITED_FEATURE
    monkeypatch.setattr(p4, "PART4_FEATURE_SOURCE_COLUMN", bad)
    with pytest.raises(p4.QCFail):
        p4.part4_source_columns()


# --------------------------------------------------------------------------- #
# Exact counts
# --------------------------------------------------------------------------- #

def test_analysis_ready_counts():
    assert p4.EXPECTED_ROWS == 1035
    assert p4.EXPECTED_COMPANIES == 122
    assert p4.EXPECTED_POSITIVE == 79
    assert p4.EXPECTED_NEGATIVE == 956
    assert p4.EXPECTED_MISSING_TARGET == 0


def test_development_counts_and_no_missing_target():
    qc = _read_json(p4.F_QC)
    assert qc["development_rows_loaded"] == 682
    assert qc["development_positive"] == 68
    assert qc["development_negative"] == 614


def test_exact_fold_counts():
    em = _read_json(p4.F_EXEC_MANIFEST)
    expected = {
        "fold1_train": {"rows": 250, "positive": 33, "negative": 217},
        "fold1_validation": {"rows": 211, "positive": 25, "negative": 186},
        "fold2_train": {"rows": 461, "positive": 58, "negative": 403},
        "fold2_validation": {"rows": 221, "positive": 10, "negative": 211},
    }
    for role, exp in expected.items():
        assert em["fold_counts"][role] == exp, role


# --------------------------------------------------------------------------- #
# Selected configurations / execution
# --------------------------------------------------------------------------- #

def test_selected_configurations_exact_and_no_tuning():
    em = _read_json(p4.F_EXEC_MANIFEST)
    assert em["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }
    assert em["no_retuning"] is True


def test_seeds_and_deterministic_logistic():
    em = _read_json(p4.F_EXEC_MANIFEST)
    assert em["model_seeds"] == list(primary.FINAL_OOF_SEEDS)
    assert em["logistic_deterministic_seed"] == primary.TUNING_SEEDS[0]


def test_xgboost_scale_pos_weight_recomputed_per_training_fold():
    em = _read_json(p4.F_EXEC_MANIFEST)
    spw = em["xgboost_scale_pos_weight_by_training_fold"]
    assert abs(spw["fold1_train"] - (217 / 33)) < 1e-9
    assert abs(spw["fold2_train"] - (403 / 58)) < 1e-9


def test_exact_fit_prediction_and_zero_counters():
    qc = _read_json(p4.F_QC)
    assert qc["model_fit_calls"] == 22
    assert qc["prediction_calls"] == 22
    for k, v in qc["zero_counters"].items():
        assert v == 0, k


# --------------------------------------------------------------------------- #
# OOF / metrics
# --------------------------------------------------------------------------- #

def test_oof_schema_counts_and_identities():
    rows = _read_csv(p4.F_OOF)
    assert len(rows) == 1296
    for family in p4.MODEL_FAMILIES:
        fam_rows = [r for r in rows if r["model_family"] == family]
        assert len(fam_rows) == 432, family
        keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                for r in fam_rows}
        assert len(keys) == len(fam_rows)


def test_no_final_test_year_in_oof():
    rows = _read_csv(p4.F_OOF)
    for r in rows:
        assert int(r["target_year"]) not in primary.FINAL_TEST_TARGET_YEARS


def test_metrics_schema_scopes_and_names():
    rows = _read_csv(p4.F_METRICS)
    assert len(rows) == 9
    assert {r["scope"] for r in rows} == {
        "fold1_validation", "fold2_validation", "pooled_development_oof",
    }
    for r in rows:
        assert set(r) == set(p4.METRICS_COLUMNS)


def test_pooled_metric_rows_have_full_oof_surface():
    rows = _read_csv(p4.F_METRICS)
    for r in rows:
        if r["scope"] == "pooled_development_oof":
            assert int(r["n_rows"]) == 432
            assert int(r["n_positive"]) == 35


# --------------------------------------------------------------------------- #
# Sample delta A — versus Part 2 (Part 4 is a strict superset)
# --------------------------------------------------------------------------- #

def test_delta_vs_part2_relationship_and_counts():
    d = _read_json(p4.F_EXEC_MANIFEST)["sample_delta"]["vs_part2"]
    assert d["relationship"] == "part4_is_strict_superset_of_part2"
    assert d["part4_only_rows"] == 42
    assert d["part2_only_rows"] == 0
    assert d["company_delta"] == 5
    assert d["positive_delta"] == 0
    assert d["negative_delta"] == 42
    assert d["development_rows_added"] == 27
    assert d["development_added_all_negative"] is True
    assert d["oof_identities_added"] == 19
    assert d["oof_identities_added_all_target_zero"] is True
    assert d["final_test_identities_added"] == 15


def test_delta_vs_part2_violation_fails_closed():
    allow_pr = p4.build_primary_allowlist(_root())
    allow_p2 = p4.build_part2_allowlist(_root())
    allow_p3 = p4.build_part3_allowlist(_root())
    allow_p4 = p4.build_part4_allowlist(_root())
    # Corrupt Part 4's identities so it is no longer a superset of Part 2.
    broken_p4 = dict(allow_p4)
    broken_p4["dev_pairs"] = {}
    broken_p4["role_pairs"] = {r: set() for r in primary.DEV_ROLES}
    broken_p4["role_pairs"][primary.FINAL_TEST_ROLE] = set()
    broken_p4["final_test_identities"] = {}
    loaded = p4.load_part4_development_values(_root(), allow_p4)
    with pytest.raises(p4.QCFail):
        p4.build_sample_delta(_root(), allow_pr, allow_p2, allow_p3, broken_p4, loaded)


# --------------------------------------------------------------------------- #
# Sample delta B — versus Part 3 (Part 4 is a strict subset)
# --------------------------------------------------------------------------- #

def test_delta_vs_part3_relationship_and_counts():
    d = _read_json(p4.F_EXEC_MANIFEST)["sample_delta"]["vs_part3"]
    assert d["relationship"] == "part4_is_strict_subset_of_part3"
    assert d["part3_only_rows"] == 21
    assert d["part4_only_rows"] == 0
    assert d["company_delta"] == -2
    assert d["positive_delta"] == -1
    assert d["negative_delta"] == -20
    assert d["development_rows_removed"] == 13
    assert d["development_removed_all_negative"] is True
    assert d["oof_identities_removed"] == 9
    assert d["final_test_identities_removed"] == 8


def test_delta_vs_part3_violation_fails_closed():
    allow_pr = p4.build_primary_allowlist(_root())
    allow_p2 = p4.build_part2_allowlist(_root())
    allow_p3 = p4.build_part3_allowlist(_root())
    allow_p4 = p4.build_part4_allowlist(_root())
    loaded = p4.load_part4_development_values(_root(), allow_p4)
    broken_p3 = dict(allow_p3)
    broken_p3["dev_pairs"] = {}
    broken_p3["role_pairs"] = {r: set() for r in primary.DEV_ROLES}
    broken_p3["role_pairs"][primary.FINAL_TEST_ROLE] = set()
    broken_p3["final_test_identities"] = {}
    with pytest.raises(p4.QCFail):
        p4.build_sample_delta(_root(), allow_pr, allow_p2, broken_p3, allow_p4, loaded)


# --------------------------------------------------------------------------- #
# Sample delta C — versus locked primary (mixed relationship)
# --------------------------------------------------------------------------- #

def test_delta_vs_primary_is_mixed_and_exact():
    d = _read_json(p4.F_EXEC_MANIFEST)["sample_delta"]["vs_primary"]
    assert d["relationship"] == "neither_strict_subset_nor_strict_superset"
    assert d["part4_only_rows"] == 42
    assert d["primary_only_rows"] == 19
    assert d["net_row_delta"] == 23
    assert d["company_delta"] == 3
    assert d["positive_delta"] == -1
    assert d["negative_delta"] == 24
    assert d["development_part4_only"] == 27
    assert d["development_primary_only"] == 11
    assert d["development_net_delta"] == 16
    assert d["oof_part4_only"] == 19
    assert d["oof_primary_only"] == 8
    assert d["oof_net_delta"] == 11
    assert d["final_test_part4_only"] == 15
    assert d["final_test_primary_only"] == 8
    assert d["final_test_net_delta"] == 7


def test_sample_delta_uses_identities_only():
    d = _read_json(p4.F_EXEC_MANIFEST)["sample_delta"]
    assert d["comparison_basis"] == "row_identities_only"
    assert d["final_test_values_read"] is False


def test_sample_delta_csv_schema_and_part4_flag_count():
    rows = _read_csv(p4.F_SAMPLE_DELTA)
    for r in rows:
        assert set(r) == set(p4.SAMPLE_DELTA_COLUMNS)
    part4_flagged = sum(
        1 for r in rows
        if r["present_in_expanded_rule_b_combined_robustness"] == "true"
    )
    assert part4_flagged == 1035


# --------------------------------------------------------------------------- #
# Final-test lock
# --------------------------------------------------------------------------- #

def test_final_test_counters_zero_and_identities_only():
    qc = _read_json(p4.F_QC)
    assert qc["final_test_identities_counted"] == 353
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_predictions_generated"] == 0
    assert qc["final_test_metrics_computed"] == 0
    assert qc["final_test_evaluations"] == 0


def test_poison_final_test_values_are_never_parsed(tmp_path):
    """A poisoned final-test row must never surface a parsed value."""
    src = _root() / p4.PART4_ANALYSIS_READY_REL
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)

    allow = p4.build_part4_allowlist(_root())
    denylist = allow["denylist_pairs"]
    poisoned = False
    for row in rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        if key in denylist:
            row[p4.PART4_TARGET] = "POISON_VALUE_MUST_NEVER_PARSE"
            poisoned = True
            break
    assert poisoned

    dest_dir = tmp_path / "project" / "stage125" / "part3c_outputs"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / os.path.basename(p4.PART4_ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Direct call against the poisoned copy: only the identity is counted, the
    # poisoned target value is never parsed into a float.
    loaded = p4.load_part4_development_values(tmp_path, allow)
    assert loaded["final_test_rows_seen"] == p4.EXPECTED_FINAL_TEST_IDENTITIES
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0


def test_development_key_with_final_test_year_fails_closed(tmp_path):
    allow = p4.build_part4_allowlist(_root())
    dev_pairs = allow["dev_pairs"]
    any_key = next(iter(dev_pairs))
    src = _root() / p4.PART4_ANALYSIS_READY_REL
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    for row in rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        if key == any_key:
            row["target_year"] = str(min(primary.FINAL_TEST_TARGET_YEARS))
    dest_dir = tmp_path / "project" / "stage125" / "part3c_outputs"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / os.path.basename(p4.PART4_ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(p4.FinalTestLockError):
        p4.load_part4_development_values(tmp_path, allow)


def test_unknown_row_fails_closed(tmp_path):
    allow = p4.build_part4_allowlist(_root())
    src = _root() / p4.PART4_ANALYSIS_READY_REL
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    rows[0]["predictor_row_key_t"] = "unknown_key_not_in_manifest"
    dest_dir = tmp_path / "project" / "stage125" / "part3c_outputs"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / os.path.basename(p4.PART4_ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(p4.QCFail):
        p4.load_part4_development_values(tmp_path, allow)


# --------------------------------------------------------------------------- #
# Immutability
# --------------------------------------------------------------------------- #

def test_primary_stage126_artifacts_byte_identical():
    observed = p4.verify_frozen_integrity(_root())
    assert observed == {
        k: p4.PINNED_PRIMARY_ARTIFACTS[k] for k in observed
    }


def test_part1_part2_part3_artifacts_byte_identical():
    observed = p4.verify_closed_parts_immutable(_root())
    assert observed == {
        k: p4.PINNED_CLOSED_PART_ARTIFACTS[k] for k in observed
    }
    assert len(observed) == len(p4.PINNED_CLOSED_PART_ARTIFACTS)


def test_closed_part_drift_fails_closed(monkeypatch):
    bad = dict(p4.PINNED_CLOSED_PART_ARTIFACTS)
    any_key = next(iter(bad))
    bad[any_key] = "0" * 64
    monkeypatch.setattr(p4, "PINNED_CLOSED_PART_ARTIFACTS", bad)
    with pytest.raises(p4.QCFail):
        p4.verify_closed_parts_immutable(_root())


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())


def test_no_part5_compatibility_artifact_created():
    for name in os.listdir(STAGE126):
        assert "part5" not in name.lower() or "part4" not in name.lower()


def test_part4_source_does_not_touch_part5():
    src_text = (_root() / p4.SRC_REL).read_text(encoding="utf-8")
    assert "run_stage125_part5" not in src_text
    assert "stage125_part5_readiness_closure" not in src_text


# --------------------------------------------------------------------------- #
# Comparison / interpretation
# --------------------------------------------------------------------------- #

def test_comparison_uses_the_locked_primary_values():
    cmp_ = _read_json(p4.F_COMPARISON)
    ref = cmp_["primary_reference"]
    assert ref["locked_values_match_observed"] is True
    assert ref["locked_pooled_pr_auc"] == {
        "regularized_logistic_regression": 0.445756964048,
        "random_forest": 0.402441830020,
        "xgboost": 0.356545008162,
    }


def test_part2_and_part3_comparisons_are_separated_and_descriptive():
    cmp_ = _read_json(p4.F_COMPARISON)
    dp2 = cmp_["descriptive_part2_comparison"]
    dp3 = cmp_["descriptive_part3_comparison"]
    assert dp2["preferred_robustness_sample_selected"] is False
    assert dp2["claims_multiplied"] is False
    assert dp3["preferred_robustness_sample_selected"] is False
    assert dp3["claims_multiplied"] is False


def test_interpretation_guards():
    cmp_ = _read_json(p4.F_COMPARISON)
    assert cmp_["primary_results_replaced"] is False
    assert cmp_["primary_ordering_lock_changed"] is False
    assert cmp_["paper_winner_selected"] is False
    assert cmp_["new_confirmatory_model_comparison"] is False
    assert cmp_["final_test_evaluation_authorized"] is False
    assert cmp_["full_development_refit_authorized"] is False


def test_comparison_corrected_aggregate_fields():
    """The corrected comparison artifact must distinguish development/OOF
    (always target-0) from the full-sample/final-test aggregate level (where
    Part 4 has exactly one fewer positive event than Part 3 and primary)."""
    cmp_ = _read_json(p4.F_COMPARISON)
    assert cmp_["development_and_oof_identity_differences_negative_only"] is True
    assert cmp_["full_sample_identity_differences_all_negative_only"] is False
    assert cmp_["full_sample_positive_delta_vs_part3"] == -1
    assert cmp_["full_sample_positive_delta_vs_primary"] == -1
    assert cmp_["final_test_positive_count_primary"] == 12
    assert cmp_["final_test_positive_count_part3"] == 12
    assert cmp_["final_test_positive_count_part4"] == 11
    assert cmp_["final_test_row_level_targets_inspected"] is False


def test_qc_new_structured_assertions_present_and_pass():
    qc = _read_json(p4.F_QC)
    names = {a["name"]: a["status"] for a in qc["assertions"]}
    required = (
        "part4_vs_part2_development_added_target_zero",
        "part4_vs_part2_oof_added_target_zero",
        "part4_vs_part3_development_removed_target_zero",
        "part4_vs_part3_oof_removed_target_zero",
        "part4_vs_primary_development_differences_target_zero",
        "part4_vs_primary_oof_differences_target_zero",
        "full_sample_positive_delta_vs_part3_is_negative_one",
        "full_sample_positive_delta_vs_primary_is_negative_one",
        "final_test_positive_counts_frozen_12_12_11",
        "final_test_row_level_targets_never_inspected",
        "development_and_oof_negative_only_flag_true",
        "full_sample_negative_only_flag_correctly_false",
    )
    for name in required:
        assert name in names, name
        assert names[name] == "PASS", name


_BANNED_OVERBROAD_PHRASES = (
    "every identity difference",
    "all identity differences involve only negative-target rows",
    "all sample differences are negative-only",
)


def _artifact_prose_texts() -> dict[str, str]:
    """Human-authored prose only (README + the JSON 'interpretation'/'note'
    strings) — excludes machine-readable JSON key names, which legitimately
    contain tokens like '..._negative_only' as boolean-flag identifiers."""
    cmp_ = _read_json(p4.F_COMPARISON)
    prose = [
        cmp_["interpretation"],
        cmp_["descriptive_part2_comparison"]["note"],
        cmp_["descriptive_part3_comparison"]["note"],
    ]
    return {
        p4.F_README: open(
            os.path.join(STAGE126, p4.F_README), encoding="utf-8"
        ).read(),
        p4.F_COMPARISON: "\n".join(prose),
    }


def test_no_overbroad_negative_only_claims_in_artifacts():
    """Fails closed if a generated artifact again claims that every identity
    difference (or every sample difference) across all three comparisons is
    negative-only — the frozen aggregate contracts make that claim false at
    the full-sample and final-test level (Part 4 has one fewer positive event
    than Part 3 and primary)."""
    for name, text in _artifact_prose_texts().items():
        lowered = text.lower()
        for phrase in _BANNED_OVERBROAD_PHRASES:
            assert phrase not in lowered, f"{name} contains banned phrase: {phrase!r}"


def _find_all(haystack: str, needle: str) -> list[int]:
    positions = []
    start = 0
    while True:
        start = haystack.find(needle, start)
        if start == -1:
            return positions
        positions.append(start)
        start += len(needle)


def test_negative_only_mentions_are_scoped():
    """Every remaining 'negative-only' / 'negative_only' prose mention must be
    scoped to development, OOF/validation, or the Part 2 strict-superset
    aggregate relationship — never to the unscoped full-sample or final-test
    comparisons versus Part 3 or primary."""
    allowed_scope_markers = (
        "development", "oof", "fold", "part 2", "part2", "superset",
    )
    for name, text in _artifact_prose_texts().items():
        lowered = text.lower()
        for needle in ("negative-only", "negative_only"):
            for idx in _find_all(lowered, needle):
                window = lowered[max(0, idx - 200):idx + 200]
                assert any(m in window for m in allowed_scope_markers), (
                    f"{name}: unscoped {needle!r} mention: ...{window}..."
                )


def test_completion_lock_contract():
    lock = _read_json(p4.F_COMPLETION_LOCK)
    assert lock["category_id"] == "expanded_rule_b_combined_robustness"
    assert lock["part4_human_authorized"] is True
    assert lock["part4_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
    ]
    assert lock["next_category_id"] == "persistent_loss_robustness_target"


def test_completion_lock_authorizes_nothing_further():
    lock = _read_json(p4.F_COMPLETION_LOCK)
    for field in (
        "part5_execution_authorized", "m1_robustness_execution_authorized",
        "full_development_refit_performed", "final_test_unlocked",
        "final_test_access_authorized", "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
        "smote_executed", "smotenc_executed", "shap_executed",
        "calibration_executed", "bootstrap_executed", "holm_executed",
        "winner_selected", "threshold_optimization_executed", "p_values_computed",
    ):
        assert lock[field] is False, field
    assert lock["m1_robustness_completed"] is False


# --------------------------------------------------------------------------- #
# QC / determinism
# --------------------------------------------------------------------------- #

def test_qc_all_pass_and_identity():
    qc = _read_json(p4.F_QC)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_qc_handoff_markers():
    qc = _read_json(p4.F_QC)
    assert qc["m1_robustness_part4_completed"] is True
    assert qc["m1_robustness_part4_authorized"] is False
    assert qc["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
    ]
    assert qc["m1_robustness_next_category_id"] == "persistent_loss_robustness_target"
    assert qc["final_test_unlocked"] is False


def test_metadata_pins_outputs_and_inputs():
    meta = _read_json(p4.F_METADATA)
    assert meta["input_files_sha256"][p4.PART4_ANALYSIS_READY_REL] == (
        p4.PART4_ANALYSIS_READY_SHA256
    )
    assert set(meta["output_files_sha256"]) >= {
        p4.F_AUTH, p4.F_FEATURE_MANIFEST, p4.F_SAMPLE_DELTA, p4.F_EXEC_MANIFEST,
        p4.F_OOF, p4.F_METRICS, p4.F_COMPARISON, p4.F_COMPLETION_LOCK, p4.F_QC,
    }


def test_deterministic_repeated_build(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    r1 = p4.run(project_dir=_root() / "project", output_dir=out1, build=True)
    r2 = p4.run(project_dir=_root() / "project", output_dir=out2, build=True)
    assert r1["files"] == r2["files"]


def test_check_mode_is_clean():
    result = p4.run(project_dir=_root() / "project", check=True)
    assert result["drift"] == []
    assert result["qc"]["all_pass"] is True
