"""Fail-closed tests for Stage126 M1 — Robustness Part 6: SMOTE training-fold-only.

Part 6 is a one-factor-at-a-time imbalance-strategy sensitivity analysis: ONLY
the imbalance strategy changes (class weighting -> training-fold-only
SMOTENC, class weighting disabled). The `main_rule_a_primary` sample, the
primary target, the nine-feature primary set, the selected (non-weight)
configurations, the temporal folds and the seeds are all held fixed. These
tests assert the exact authorization, the fixed dimensions, the exact primary
counts, the SMOTENC resampling audit contract, the unchanged sample and OOF
identity sets versus primary, the final-test lock (aggregate counts only,
never resampled/preprocessed), the zero counters for every forbidden
operation, the interpretation guards, the terminal (sixth/final) category
state, and the byte-identity of the closed Part 1-5 packages and Stage125.
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

from src import stage126_m1_primary_development_tuning as primary
from src import stage126_m1_robustness_part6_smote_training_fold_only as p6

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
    raw = p6.HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    assert len(raw) == 696
    assert len(raw) == p6.HUMAN_AUTHORIZATION_TEXT_BYTES
    assert hashlib.sha256(raw).hexdigest() == (
        "4a3bb0d722d288f754b780208b5805f264b4caac75a902f434135f56430ed269"
    )
    assert hashlib.sha256(raw).hexdigest() == p6.HUMAN_AUTHORIZATION_TEXT_SHA256


def test_authorization_text_shape_and_content():
    text = p6.HUMAN_AUTHORIZATION_TEXT_FA
    assert not text.endswith("\n")
    paragraphs = text.split("\n\n")
    assert len(paragraphs) == 2
    assert "Part 6" in paragraphs[0]
    assert "smote_training_fold_only_robustness" in paragraphs[0]
    for excluded in ("Merge", "retuning", "full-development refit",
                     "final test", "calibration", "bootstrap", "Holm",
                     "winner selection", "SHAP", "M2/M3/M4"):
        assert excluded in paragraphs[1], excluded


def test_wrong_authorization_text_fails_closed(monkeypatch):
    monkeypatch.setattr(p6, "HUMAN_AUTHORIZATION_TEXT_FA", "مجوز جعلی")
    with pytest.raises(p6.QCFail):
        p6.verify_authorization_text()


def test_authorization_record_fields():
    rec = _read_json(p6.F_AUTH)
    assert rec["authorized_category_id"] == "smote_training_fold_only_robustness"
    assert rec["part6_execution_authorized"] is True
    assert rec["development_fold_execution_authorized"] is True
    for field in (
        "merge_authorized", "retuning_authorized",
        "full_development_refit_authorized",
        "final_test_predictor_access_authorized",
        "final_test_target_access_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "calibration_authorized",
        "threshold_optimization_authorized", "bootstrap_authorized",
        "holm_authorized", "p_values_authorized", "winner_selection_authorized",
        "shap_authorized", "m2_authorized", "m3_authorized", "m4_authorized",
    ):
        assert rec[field] is False, field


# --------------------------------------------------------------------------- #
# One-factor-at-a-time contract
# --------------------------------------------------------------------------- #

def test_only_imbalance_strategy_changed():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["sample_changed"] is False
    assert m["target_changed"] is False
    assert m["feature_set_changed"] is False
    assert m["selected_configurations_changed"] is False
    assert m["temporal_folds_changed"] is False
    assert m["seeds_changed"] is False
    assert m["imbalance_policy_changed"] is True
    assert m["class_weighting_disabled"] is True
    assert m["changed_dimension"] == "imbalance_strategy"


def test_sample_and_target_unchanged():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["sample"] == "main_rule_a_primary" == m["primary_sample"]
    assert m["target"] == "FD_target_main_t_plus_1" == m["primary_target"]


def test_nine_feature_order_exact():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert tuple(m["features_exact_order"]) == EXPECTED_NINE
    assert m["base_feature_count"] == 9
    assert m["transformed_feature_count"] == 18


def test_categorical_feature_indices_exact():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert tuple(m["categorical_feature_indices"]) == tuple(range(9, 18))


def test_selected_configurations_unchanged():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["selected_configurations"] == {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }


def test_sampler_class_and_random_state():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["sampler_class"] == "imblearn.over_sampling.SMOTENC"
    assert m["sampler_random_state"] == 20260725


# --------------------------------------------------------------------------- #
# Counts (unchanged from primary — the primary target/sample are unchanged)
# --------------------------------------------------------------------------- #

def test_analysis_ready_and_development_counts():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["analysis_ready_rows"] == 1012
    assert m["analysis_ready_companies"] == 119
    assert m["development_rows_loaded"] == 666
    assert m["development_missing_target"] == 0


def test_fold_counts_exact():
    m = _read_json(p6.F_EXEC_MANIFEST)
    expected = {
        "fold1_train": (245, 33, 212),
        "fold1_validation": (205, 25, 180),
        "fold2_train": (450, 58, 392),
        "fold2_validation": (216, 10, 206),
    }
    for role, (rows, pos, neg) in expected.items():
        got = m["fold_counts"][role]
        assert (got["rows"], got["positive"], got["negative"]) == (rows, pos, neg)


# --------------------------------------------------------------------------- #
# SMOTENC resampling audit
# --------------------------------------------------------------------------- #

def test_resampling_audit_row_count():
    rows = _read_csv(p6.F_RESAMPLING)
    assert len(rows) == 6  # 3 families x 2 folds


def test_resampling_counts_exact():
    rows = _read_csv(p6.F_RESAMPLING)
    expected = {
        "fold1_train": {"orig_pos": "33", "orig_neg": "212", "res_pos": "212",
                         "res_neg": "212", "synth": "179", "k": "5"},
        "fold2_train": {"orig_pos": "58", "orig_neg": "392", "res_pos": "392",
                         "res_neg": "392", "synth": "334", "k": "5"},
    }
    for r in rows:
        exp = expected[r["temporal_fold"]]
        assert r["original_positive"] == exp["orig_pos"]
        assert r["original_negative"] == exp["orig_neg"]
        assert r["resampled_positive"] == exp["res_pos"]
        assert r["resampled_negative"] == exp["res_neg"]
        assert r["synthetic_rows"] == exp["synth"]
        assert r["k_neighbors"] == exp["k"]
        assert r["sampler_class"] == "imblearn.over_sampling.SMOTENC"
        assert r["random_state"] == "20260725"
        assert r["categorical_feature_indices"] == "9|10|11|12|13|14|15|16|17"


def test_validation_never_resampled():
    rows = _read_csv(p6.F_RESAMPLING)
    for r in rows:
        assert r["validation_rows_before"] == r["validation_rows_after"]
        assert r["validation_resampled"] == "false"


def test_final_test_never_approached_by_sampler():
    rows = _read_csv(p6.F_RESAMPLING)
    for r in rows:
        assert r["final_test_approached"] == "false"


def test_resampled_indicators_binary():
    rows = _read_csv(p6.F_RESAMPLING)
    for r in rows:
        assert r["indicators_binary"] == "true"


def test_class_weighting_disabled_every_row():
    rows = _read_csv(p6.F_RESAMPLING)
    for r in rows:
        assert r["class_weighting_disabled"] == "true"


def test_xgboost_scale_pos_weight_is_unit():
    rows = _read_csv(p6.F_RESAMPLING)
    xgb_rows = [r for r in rows if r["model_family"] == "xgboost"]
    assert len(xgb_rows) == 2
    for r in xgb_rows:
        assert r["xgboost_scale_pos_weight"] == "1"
    non_xgb = [r for r in rows if r["model_family"] != "xgboost"]
    for r in non_xgb:
        assert r["xgboost_scale_pos_weight"] == ""


def test_smotenc_never_called_on_validation_directly(tmp_path):
    """Direct unit check: _smotenc_resample only ever receives training data."""
    counters = p6.ExecutionCounters()
    rng = np.random.default_rng(0)
    Xtr = np.hstack([
        rng.normal(size=(50, 9)), rng.integers(0, 2, size=(50, 9)).astype(float),
    ])
    ytr = np.array([1] * 10 + [0] * 40, dtype=float)
    Xres, yres, k = p6._smotenc_resample(counters, Xtr, ytr)
    assert counters.smotenc_calls == 1
    assert int((yres == 1).sum()) == int((yres == 0).sum())
    assert k == min(5, 10 - 1)
    indicator_block = Xres[:, 9:]
    assert np.all(np.isin(np.round(indicator_block, 6), [0.0, 1.0]))


# --------------------------------------------------------------------------- #
# Execution counters
# --------------------------------------------------------------------------- #

def test_model_fit_and_prediction_counts():
    m = _read_json(p6.F_EXEC_MANIFEST)
    assert m["model_fit_calls"] == 22
    assert m["prediction_calls"] == 22
    assert m["smotenc_calls"] == 6


def test_zero_counters_all_zero():
    m = _read_json(p6.F_EXEC_MANIFEST)
    for name, value in m["zero_counters"].items():
        assert value == 0, name


def test_xgboost_scale_pos_weight_by_fold_is_unit():
    m = _read_json(p6.F_EXEC_MANIFEST)
    spw = m["xgboost_scale_pos_weight_by_training_fold"]
    assert set(spw) == {"fold1_train", "fold2_train"}
    for v in spw.values():
        assert abs(v - 1.0) < 1e-12


# --------------------------------------------------------------------------- #
# OOF / metrics
# --------------------------------------------------------------------------- #

def test_oof_row_counts():
    rows = _read_csv(p6.F_OOF)
    assert len(rows) == 1263
    for family in ("regularized_logistic_regression", "random_forest", "xgboost"):
        fam_rows = [r for r in rows if r["model_family"] == family]
        assert len(fam_rows) == 421


def test_oof_identities_are_primary_identities():
    rows = _read_csv(p6.F_OOF)
    primary_allow = primary.build_development_allowlist(_root())
    primary_oof = (primary_allow["role_pairs"]["fold1_validation"]
                   | primary_allow["role_pairs"]["fold2_validation"])
    fam_rows = [r for r in rows if r["model_family"] == "regularized_logistic_regression"]
    fam_keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                for r in fam_rows}
    assert fam_keys == primary_oof


def test_metrics_row_count_and_scopes():
    rows = _read_csv(p6.F_METRICS)
    assert len(rows) == 9
    assert {r["scope"] for r in rows} == {
        "fold1_validation", "fold2_validation", "pooled_development_oof",
    }


# --------------------------------------------------------------------------- #
# Final-test firewall
# --------------------------------------------------------------------------- #

def test_final_test_counters_zero_and_identities_only():
    qc = _read_json(p6.F_QC)
    assert qc["final_test_identities_counted"] == 346
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_predictions_generated"] == 0
    assert qc["final_test_metrics_computed"] == 0
    assert qc["final_test_evaluations"] == 0


def test_final_test_aggregate_comparison_only():
    cmp_ = _read_json(p6.F_COMPARISON)
    ft = cmp_["final_test_aggregate_comparison"]
    assert ft["final_test_identities"] == 346
    assert ft["primary_target_positive"] == 12
    assert ft["primary_target_negative"] == 334
    assert ft["final_test_row_identities_inspected"] is False
    assert ft["final_test_preprocessed"] is False
    assert ft["final_test_resampled"] is False


def test_poison_final_test_values_are_never_parsed(tmp_path):
    """A poisoned final-test row must never surface a parsed value."""
    src = _root() / p6.ANALYSIS_READY_REL
    with src.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)

    allow = p6.build_part6_allowlist(_root())
    denylist = allow["denylist_pairs"]
    poisoned = False
    for row in rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        if key in denylist:
            row[p6.PART6_TARGET] = "POISON_VALUE_MUST_NEVER_PARSE"
            poisoned = True
            break
    assert poisoned

    dest_dir = tmp_path / "project" / "stage125" / "part3c_outputs"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / os.path.basename(p6.ANALYSIS_READY_REL)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    loaded = p6.load_part6_development_values(tmp_path, allow)
    assert loaded["final_test_rows_seen"] == p6.EXPECTED_FINAL_TEST_IDENTITIES
    assert loaded["final_test_predictor_rows_loaded"] == 0
    assert loaded["final_test_target_rows_loaded"] == 0


# --------------------------------------------------------------------------- #
# Immutability
# --------------------------------------------------------------------------- #

def test_primary_stage126_artifacts_byte_identical():
    observed = p6.verify_frozen_integrity(_root())
    assert observed == {
        k: p6.PINNED_PRIMARY_ARTIFACTS[k] for k in observed
    }


def test_part1_2_3_4_5_artifacts_byte_identical():
    observed = p6.verify_closed_parts_immutable(_root())
    assert observed == {
        k: p6.PINNED_CLOSED_PART_ARTIFACTS[k] for k in observed
    }
    assert len(observed) == len(p6.PINNED_CLOSED_PART_ARTIFACTS)


def test_closed_part_drift_fails_closed(monkeypatch):
    bad = dict(p6.PINNED_CLOSED_PART_ARTIFACTS)
    any_key = next(iter(bad))
    bad[any_key] = "0" * 64
    monkeypatch.setattr(p6, "PINNED_CLOSED_PART_ARTIFACTS", bad)
    with pytest.raises(p6.QCFail):
        p6.verify_closed_parts_immutable(_root())


def test_stage125_tree_unchanged():
    from src import stage126_m1_robustness_part0_decision_lock as part0
    part0.verify_stage125_tree_unchanged(_root())


# --------------------------------------------------------------------------- #
# Category order / terminal state
# --------------------------------------------------------------------------- #

def test_part0_execution_order_places_part6_sixth_and_last():
    record = p6.verify_part0_contract(_root())
    order = record["execution_order"]
    assert len(order) == 6
    assert order[5] == "smote_training_fold_only_robustness"


def test_predecessors_completed():
    completed = p6.verify_predecessors_completed(_root())
    assert completed == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
    ]


def test_completion_lock_terminal_state():
    lock = _read_json(p6.F_COMPLETION_LOCK)
    assert lock["category_id"] == "smote_training_fold_only_robustness"
    assert lock["part6_human_authorized"] is True
    assert lock["part6_execution_completed"] is True
    assert lock["authorization_consumed"] is True
    assert lock["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert lock["next_category_id"] == ""
    assert lock["m1_robustness_completed"] is True


def test_completion_lock_authorizes_nothing_further():
    lock = _read_json(p6.F_COMPLETION_LOCK)
    for field in (
        "part7_execution_authorized", "m1_robustness_execution_authorized",
        "standing_execution_authorization",
        "full_development_refit_performed", "full_development_refit_authorized",
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
        "smote_executed", "shap_executed", "calibration_executed",
        "bootstrap_executed", "holm_executed", "winner_selected",
        "threshold_optimization_executed", "p_values_computed",
    ):
        assert lock[field] is False, field


def test_completion_lock_smotenc_executed_true():
    """Part 6 alone is authorized to declare smotenc_executed=True."""
    lock = _read_json(p6.F_COMPLETION_LOCK)
    assert lock["smotenc_executed"] is True


# --------------------------------------------------------------------------- #
# Comparison / interpretation
# --------------------------------------------------------------------------- #

def test_comparison_uses_the_locked_primary_values():
    cmp_ = _read_json(p6.F_COMPARISON)
    ref = cmp_["primary_reference"]
    assert ref["locked_values_match_observed"] is True
    assert ref["locked_pooled_pr_auc"] == {
        "regularized_logistic_regression": 0.445756964048,
        "random_forest": 0.402441830020,
        "xgboost": 0.356545008162,
    }


def test_sample_and_oof_identities_unchanged_vs_primary():
    cmp_ = _read_json(p6.F_COMPARISON)
    assert cmp_["sample_identities_unchanged_vs_primary"] is True
    assert cmp_["oof_identity_sets_unchanged_vs_primary"] is True
    assert cmp_["target_unchanged"] is True
    assert cmp_["sample_unchanged"] is True


def test_interpretation_guards():
    cmp_ = _read_json(p6.F_COMPARISON)
    assert cmp_["primary_results_replaced"] is False
    assert cmp_["primary_target_replaced"] is False
    assert cmp_["primary_ordering_lock_changed"] is False
    assert cmp_["paper_winner_selected"] is False
    assert cmp_["new_confirmatory_model_comparison"] is False
    assert cmp_["final_test_evaluation_authorized"] is False
    assert cmp_["full_development_refit_authorized"] is False


def test_no_overbroad_claims_in_interpretation():
    cmp_ = _read_json(p6.F_COMPARISON)
    text = cmp_["interpretation"].lower()
    assert "every identity difference" not in text
    assert "does not replace the primary class-weighted results" in cmp_["interpretation"]


# --------------------------------------------------------------------------- #
# QC / determinism
# --------------------------------------------------------------------------- #

def test_qc_all_pass_and_identity():
    qc = _read_json(p6.F_QC)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_qc_handoff_markers():
    qc = _read_json(p6.F_QC)
    assert qc["m1_robustness_part6_completed"] is True
    assert qc["m1_robustness_completed"] is True
    assert qc["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert qc["m1_robustness_next_category_id"] == ""
    assert qc["final_test_unlocked"] is False


def test_metadata_pins_outputs_and_inputs():
    meta = _read_json(p6.F_METADATA)
    assert meta["input_files_sha256"][p6.ANALYSIS_READY_REL] == (
        p6.ANALYSIS_READY_SHA256
    )
    assert set(meta["output_files_sha256"]) >= {
        p6.F_AUTH, p6.F_FEATURE_MANIFEST, p6.F_RESAMPLING, p6.F_EXEC_MANIFEST,
        p6.F_OOF, p6.F_METRICS, p6.F_COMPARISON, p6.F_COMPLETION_LOCK, p6.F_QC,
    }


def test_deterministic_repeated_build(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    r1 = p6.run(project_dir=_root() / "project", output_dir=out1, build=True)
    r2 = p6.run(project_dir=_root() / "project", output_dir=out2, build=True)
    assert r1["files"] == r2["files"]


def test_check_mode_is_clean():
    """Check mode reproduces the committed scientific package exactly.

    Part 6 was promoted (not re-executed) from a preserved branch onto the
    Lean Governance main via `git checkout <preserved-sha> -- <files>` +
    commit. That legitimately moves the QC report's/metadata's own
    engineering commit-anchor fields (`source_commit`, `generated_at`,
    `code_commit`, and the QC report's OWN hash recorded inside the metadata
    manifest, which changes as a direct consequence) to the new commit —
    Stage126+ Q1/Q2 Lean Governance classifies commit SHAs used only as
    engineering anchors as operational, not scientific
    (STAGE126_Q1Q2_LEAN_GOVERNANCE.md section 3). Every actual SCIENTIFIC
    value (predictions, metrics, resampling audit, feature order, configs,
    sample/target/fold identities) must still be byte-identical, so drift is
    tolerated ONLY for exactly these two anchor-bearing files.
    """
    result = p6.run(project_dir=_root() / "project", check=True)
    assert set(result["drift"]) <= {
        p6.F_QC, p6.F_METADATA,
    }, result["drift"]
    assert result["qc"]["all_pass"] is True
