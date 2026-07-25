"""Fail-closed tests for Stage126 M1 — Robustness Part 5: persistent-loss target.

Part 5 is a one-factor-at-a-time target-robustness sensitivity analysis: ONLY
the modeling target changes (to
`FD_target_persistent_loss_robustness_t_plus_1`). The `main_rule_a_primary`
sample, the nine-feature primary set, the selected configurations, the temporal
folds, the imbalance policy, the seeds and the metric contract are all held
fixed. These tests assert the exact authorization, the fixed dimensions, the
exact persistent-loss counts, the development-only target-transition
reconciliation, the unchanged sample and OOF identity sets versus primary, the
final-test lock (aggregate counts only), the zero counters for every forbidden
operation, the interpretation guards, and the byte-identity of the closed
Part 1-4 packages and Stage125.
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
from src import stage126_m1_robustness_part5_persistent_loss_target as p5

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
    raw = p5.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    assert len(raw) == 512
    assert len(raw) == p5.HUMAN_AUTHORIZATION_TEXT_BYTES
    assert hashlib.sha256(raw).hexdigest() == (
        "e00b43d812b3da2104bfedb30a1dd63276a7f28347b93ff7f4bbcad60fd23678"
    )
    assert hashlib.sha256(raw).hexdigest() == p5.HUMAN_AUTHORIZATION_TEXT_SHA256


def test_authorization_text_shape_and_content():
    text = p5.HUMAN_AUTHORIZATION_TEXT_FA
    assert not text.endswith("\n")
    paragraphs = text.split("\n\n")
    assert len(paragraphs) == 2
    assert "Part 5" in paragraphs[0]
    assert "persistent_loss_robustness_target" in paragraphs[0]
    for excluded in ("Merge", "Part 6", "retuning", "full-development refit",
                     "final test", "calibration", "bootstrap", "Holm",
                     "winner selection", "SMOTE", "SHAP", "M2/M3/M4"):
        assert excluded in paragraphs[1], excluded


def test_wrong_authorization_text_fails_closed(monkeypatch):
    monkeypatch.setattr(p5, "HUMAN_AUTHORIZATION_TEXT_FA", "مجوز جعلی")
    with pytest.raises(p5.QCFail):
        p5.verify_authorization_text()


def test_wrong_authorization_hash_fails_closed(monkeypatch):
    monkeypatch.setattr(p5, "HUMAN_AUTHORIZATION_TEXT_SHA256", "0" * 64)
    with pytest.raises(p5.QCFail):
        p5.verify_authorization_text()


def test_authorization_record_on_disk():
    rec = _read_json(p5.F_AUTH)
    assert rec["authorization_id"] == p5.AUTHORIZATION_ID
    assert rec["authorized_category_id"] == "persistent_loss_robustness_target"
    assert rec["human_authorization_text_utf8_bytes"] == 512
    assert hashlib.sha256(
        rec["human_authorization_text"].encode("utf-8")
    ).hexdigest() == p5.HUMAN_AUTHORIZATION_TEXT_SHA256
    assert rec["part5_execution_authorized"] is True
    assert rec["development_fold_execution_authorized"] is True
    assert rec["create_open_unmerged_pr_authorized"] is True
    assert rec["authorized_base_main_commit"] == (
        "0962bfee463500ca572e9df23cd137904a24ef4b"
    )


def test_authorization_grants_nothing_else():
    rec = _read_json(p5.F_AUTH)
    for field in (
        "merge_authorized", "part6_execution_authorized", "retuning_authorized",
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

def test_part0_places_part5_fifth_and_part6_next():
    record = p5.verify_part0_contract(_root())
    order = record["execution_order"]
    assert order[0] == "m1_target_proximity_six_feature_set"
    assert order[1] == "main_rule_b_listing_robustness"
    assert order[2] == "expanded_rule_a_company_scope_robustness"
    assert order[3] == "expanded_rule_b_combined_robustness"
    assert order[4] == "persistent_loss_robustness_target"
    assert order[5] == "smote_training_fold_only_robustness"


def test_parts_1_2_3_4_must_precede_part5():
    assert p5.verify_predecessors_completed(_root()) == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
    ]


def test_missing_predecessor_fails_closed(tmp_path):
    (tmp_path / "project" / "stage126").mkdir(parents=True)
    with pytest.raises(p5.QCFail):
        p5.verify_predecessors_completed(tmp_path)


# --------------------------------------------------------------------------- #
# Frozen contract: only the target changed
# --------------------------------------------------------------------------- #

def test_category_role_and_changed_dimension():
    assert p5.CATEGORY_ID == "persistent_loss_robustness_target"
    assert p5.SCIENTIFIC_ROLE == "secondary_target_robustness"
    assert p5.CHANGED_DIMENSION == "target"
    assert p5.MICRO_PART_ID == "stage126-m1-robustness-part5-persistent-loss-target"
    assert p5.NEXT_CATEGORY_ID == "smote_training_fold_only_robustness"


def test_only_target_changed_everything_else_fixed():
    em = _read_json(p5.F_EXEC_MANIFEST)
    assert em["sample"] == "main_rule_a_primary"
    assert em["primary_sample"] == "main_rule_a_primary"
    assert em["sample_changed"] is False
    assert em["target"] == "FD_target_persistent_loss_robustness_t_plus_1"
    assert em["primary_target"] == "FD_target_main_t_plus_1"
    assert em["target_changed"] is True
    assert em["feature_set_changed"] is False
    assert em["preprocessing_changed"] is False
    assert em["missingness_indicator_logic_changed"] is False
    assert em["selected_configurations_changed"] is False
    assert em["imbalance_policy_changed"] is False
    assert em["temporal_folds_changed"] is False
    assert em["seeds_changed"] is False


def test_nine_feature_order_and_matrix_width():
    em = _read_json(p5.F_EXEC_MANIFEST)
    assert tuple(em["features_exact_order"]) == EXPECTED_NINE
    assert em["base_feature_count"] == 9
    assert em["transformed_feature_count"] == 18
    assert p5.PROHIBITED_FEATURE not in em["features_exact_order"]
    rows = _read_csv(p5.F_FEATURE_MANIFEST)
    assert [r["feature_name"] for r in rows] == list(EXPECTED_NINE)
    assert all(r["included_in_part5"] == "true" for r in rows)


def test_selected_configurations_reused_verbatim():
    em = _read_json(p5.F_EXEC_MANIFEST)
    assert em["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }
    assert em["no_retuning"] is True


# --------------------------------------------------------------------------- #
# Counts
# --------------------------------------------------------------------------- #

def test_sample_and_fold_counts():
    em = _read_json(p5.F_EXEC_MANIFEST)
    assert em["analysis_ready_rows"] == 1012
    assert em["analysis_ready_companies"] == 119
    assert em["development_rows_loaded"] == 666
    assert em["development_missing_target"] == 0
    fc = em["fold_counts"]
    assert fc["fold1_train"] == {"rows": 245, "positive": 42, "negative": 203}
    assert fc["fold1_validation"] == {"rows": 205, "positive": 30, "negative": 175}
    assert fc["fold2_train"] == {"rows": 450, "positive": 72, "negative": 378}
    assert fc["fold2_validation"] == {"rows": 216, "positive": 13, "negative": 203}


def test_qc_reports_persistent_loss_counts():
    qc = _read_json(p5.F_QC)
    assert qc["analysis_ready_positive"] == 100
    assert qc["analysis_ready_negative"] == 912
    assert qc["development_positive"] == 85
    assert qc["development_negative"] == 581
    assert qc["oof_rows_total"] == 1263
    assert qc["oof_rows_per_family"] == 421
    assert qc["metrics_rows"] == 9


# --------------------------------------------------------------------------- #
# Target transitions (development only)
# --------------------------------------------------------------------------- #

def test_target_transitions_reconcile():
    em = _read_json(p5.F_EXEC_MANIFEST)
    t = em["development_target_transitions"]
    assert t["total_rows"] == 666
    assert t["primary_positive"] == 68
    assert t["persistent_positive"] == 85
    assert t["net_positive_delta"] == 17
    # Reconcile the four cells against the aggregates.
    assert t["primary1_persistent0"] + t["primary1_persistent1"] == 68
    assert t["primary0_persistent1"] + t["primary1_persistent1"] == 85
    assert (t["primary0_persistent0"] + t["primary0_persistent1"]
            + t["primary1_persistent0"] + t["primary1_persistent1"]) == 666
    for k in ("primary0_persistent0", "primary0_persistent1",
              "primary1_persistent0", "primary1_persistent1"):
        assert t[k] >= 0


# --------------------------------------------------------------------------- #
# Unchanged sample / OOF identities versus primary
# --------------------------------------------------------------------------- #

def test_sample_and_oof_identities_unchanged_vs_primary():
    cmp_ = _read_json(p5.F_COMPARISON)
    assert cmp_["sample_unchanged"] is True
    assert cmp_["sample_identities_unchanged_vs_primary"] is True
    assert cmp_["oof_identity_sets_unchanged_vs_primary"] is True
    assert cmp_["primary_target_unchanged"] is True


def test_part5_dev_identities_equal_primary_identities():
    allow5 = p5.build_part5_allowlist(_root())
    allow_pr = primary.build_development_allowlist(_root())
    assert set(allow5["dev_pairs"]) == set(allow_pr["dev_pairs"])
    for role in primary.DEV_ROLES:
        assert allow5["role_pairs"][role] == allow_pr["role_pairs"][role]


# --------------------------------------------------------------------------- #
# Execution counters
# --------------------------------------------------------------------------- #

def test_execution_counters_and_xgb_weights():
    em = _read_json(p5.F_EXEC_MANIFEST)
    assert em["model_fit_calls"] == 22
    assert em["prediction_calls"] == 22
    assert em["xgboost_scale_pos_weight_by_training_fold"] == {
        "fold1_train": 4.833333333333,
        "fold2_train": 5.25,
    }
    for k, v in em["zero_counters"].items():
        assert v == 0, k


# --------------------------------------------------------------------------- #
# Final-test lock (aggregate only)
# --------------------------------------------------------------------------- #

def test_final_test_counters_zero_and_identities_only():
    qc = _read_json(p5.F_QC)
    assert qc["final_test_identities_counted"] == 346
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_predictions_generated"] == 0
    assert qc["final_test_metrics_computed"] == 0
    assert qc["final_test_evaluations"] == 0


def test_final_test_aggregate_counts_only():
    cmp_ = _read_json(p5.F_COMPARISON)
    ftc = cmp_["final_test_aggregate_comparison"]
    assert ftc["final_test_identities"] == 346
    assert ftc["primary_target_positive"] == 12
    assert ftc["primary_target_negative"] == 334
    assert ftc["persistent_loss_positive"] == 15
    assert ftc["persistent_loss_negative"] == 331
    assert ftc["final_test_row_identities_inspected"] is False
    assert ftc["final_test_target_transitions_derived"] is False


def test_poison_final_test_values_are_never_parsed(tmp_path):
    """A poisoned final-test row must never surface a parsed value."""
    src = _root() / p5.ANALYSIS_READY_REL
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)

    allow = p5.build_part5_allowlist(_root())
    denylist = allow["denylist_pairs"]
    poisoned = False
    for row in rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        if key in denylist:
            row[p5.PART5_TARGET] = "POISON_VALUE_MUST_NEVER_PARSE"
            row[p5.PRIMARY_TARGET] = "POISON_VALUE_MUST_NEVER_PARSE"
            poisoned = True
            break
    assert poisoned

    dest_dir = tmp_path / "project" / "stage125" / "part3c_outputs"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / os.path.basename(p5.ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    loaded = p5.load_part5_development_values(tmp_path, allow)
    assert loaded["final_test_rows_seen"] == p5.EXPECTED_FINAL_TEST_IDENTITIES
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0


def test_development_key_with_final_test_year_fails_closed(tmp_path):
    allow = p5.build_part5_allowlist(_root())
    dev_pairs = allow["dev_pairs"]
    any_key = next(iter(dev_pairs))
    src = _root() / p5.ANALYSIS_READY_REL
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
    dest = dest_dir / os.path.basename(p5.ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(p5.FinalTestLockError):
        p5.load_part5_development_values(tmp_path, allow)


# --------------------------------------------------------------------------- #
# Immutability
# --------------------------------------------------------------------------- #

def test_primary_stage126_artifacts_byte_identical():
    observed = p5.verify_frozen_integrity(_root())
    assert observed == {
        k: p5.PINNED_PRIMARY_ARTIFACTS[k] for k in observed
    }


def test_parts_1_2_3_4_artifacts_byte_identical():
    observed = p5.verify_closed_parts_immutable(_root())
    assert observed == {
        k: p5.PINNED_CLOSED_PART_ARTIFACTS[k] for k in observed
    }
    assert len(observed) == len(p5.PINNED_CLOSED_PART_ARTIFACTS)


def test_closed_part_drift_fails_closed(monkeypatch):
    bad = dict(p5.PINNED_CLOSED_PART_ARTIFACTS)
    any_key = next(iter(bad))
    bad[any_key] = "0" * 64
    monkeypatch.setattr(p5, "PINNED_CLOSED_PART_ARTIFACTS", bad)
    with pytest.raises(p5.QCFail):
        p5.verify_closed_parts_immutable(_root())


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())


def test_no_sample_delta_artifact_created():
    for name in os.listdir(STAGE126):
        assert not (name.startswith("stage126_m1_robustness_part5")
                    and "sample_delta" in name)


# --------------------------------------------------------------------------- #
# Comparison / interpretation
# --------------------------------------------------------------------------- #

def test_comparison_uses_locked_primary_values():
    cmp_ = _read_json(p5.F_COMPARISON)
    ref = cmp_["primary_reference"]
    assert ref["locked_values_match_observed"] is True
    assert ref["locked_pooled_pr_auc"] == {
        "regularized_logistic_regression": 0.445756964048,
        "random_forest": 0.402441830020,
        "xgboost": 0.356545008162,
    }


def test_interpretation_guards():
    cmp_ = _read_json(p5.F_COMPARISON)
    assert cmp_["primary_results_replaced"] is False
    assert cmp_["primary_target_replaced"] is False
    assert cmp_["primary_ordering_lock_changed"] is False
    assert cmp_["paper_winner_selected"] is False
    assert cmp_["new_confirmatory_model_comparison"] is False
    assert cmp_["persistent_loss_target_multiplied_across_samples"] is False
    assert cmp_["final_test_evaluation_authorized"] is False
    assert cmp_["full_development_refit_authorized"] is False


def test_aggregate_counts_primary_vs_persistent():
    cmp_ = _read_json(p5.F_COMPARISON)
    ag = cmp_["aggregate_counts"]
    assert ag["primary_target"]["all"] == {"positive": 80, "negative": 932}
    assert ag["primary_target"]["development"] == {"positive": 68, "negative": 598}
    assert ag["persistent_loss_target"]["all"] == {"positive": 100, "negative": 912}
    assert ag["persistent_loss_target"]["development"] == {
        "positive": 85, "negative": 581,
    }


def test_completion_lock_contract():
    lock = _read_json(p5.F_COMPLETION_LOCK)
    assert lock["category_id"] == "persistent_loss_robustness_target"
    assert lock["part5_human_authorized"] is True
    assert lock["part5_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["only_target_changed"] is True
    assert lock["sample_changed"] is False
    assert lock["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
    ]
    assert lock["next_category_id"] == "smote_training_fold_only_robustness"


def test_completion_lock_authorizes_nothing_further():
    lock = _read_json(p5.F_COMPLETION_LOCK)
    for field in (
        "part6_execution_authorized", "m1_robustness_execution_authorized",
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
    qc = _read_json(p5.F_QC)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_qc_handoff_markers():
    qc = _read_json(p5.F_QC)
    assert qc["m1_robustness_part5_completed"] is True
    assert qc["m1_robustness_part5_authorized"] is False
    assert qc["m1_robustness_part6_authorized"] is False
    assert qc["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
    ]
    assert qc["m1_robustness_next_category_id"] == "smote_training_fold_only_robustness"
    assert qc["final_test_unlocked"] is False


def test_metadata_pins_outputs_and_inputs():
    meta = _read_json(p5.F_METADATA)
    assert meta["input_files_sha256"][p5.ANALYSIS_READY_REL] == (
        p5.ANALYSIS_READY_SHA256
    )
    assert set(meta["output_files_sha256"]) >= {
        p5.F_AUTH, p5.F_FEATURE_MANIFEST, p5.F_EXEC_MANIFEST,
        p5.F_OOF, p5.F_METRICS, p5.F_COMPARISON, p5.F_COMPLETION_LOCK, p5.F_QC,
    }
    assert meta["runtime_versions"]["python"] == "3.13.5"


def test_deterministic_repeated_build(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    r1 = p5.run(project_dir=_root() / "project", output_dir=out1, build=True)
    r2 = p5.run(project_dir=_root() / "project", output_dir=out2, build=True)
    assert r1["files"] == r2["files"]


def test_check_mode_is_clean():
    result = p5.run(project_dir=_root() / "project", check=True)
    assert result["drift"] == []
    assert result["qc"]["all_pass"] is True
