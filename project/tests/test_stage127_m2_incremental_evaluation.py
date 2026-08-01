"""Fail-closed tests for the Stage127 M2 paired incremental evaluation.

Every test reads the already-written package artifacts or exercises the module
on the frozen development surface. No final-test row is loaded, no model is
retuned and no winner is selected.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from src import stage126_m1_primary_development_tuning as m1
from src import stage127_m2_incremental_evaluation as ev

REPO_ROOT = Path(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = REPO_ROOT / ev.OUT_DIR_REL


def _load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _rows(name: str) -> list[dict[str, str]]:
    with (OUT / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


requires_package = pytest.mark.skipif(
    not (OUT / ev.F_DECISION).is_file(),
    reason="Stage127 M2 incremental-evaluation package not built here",
)


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #

def test_authorization_utterance_and_digest_exact():
    assert ev.AUTHORIZATION_TEXT_FA == "بریم مرحله بعد"
    assert hashlib.sha256(
        ev.AUTHORIZATION_TEXT_FA.encode("utf-8")).hexdigest() == (
        "a9999c0cab0ec43d200cbc2d00112132e27c4bd7ed52e0db92ef0d5eb6c3cdc6"
    )
    assert ev.AUTHORIZATION_TEXT_SHA256 == (
        "a9999c0cab0ec43d200cbc2d00112132e27c4bd7ed52e0db92ef0d5eb6c3cdc6"
    )


def test_authorization_record_is_one_action_only_and_non_standing():
    rec = ev.build_authorization_record()
    ev.assert_authorization(rec)
    assert rec["authorization_date"] == "2026-08-01"
    assert rec["authorized_action_id"] == "stage127-m2-incremental-evaluation"
    assert rec["one_action_only"] is True
    assert rec["standing_authorization"] is False
    assert rec["non_transitive"] is True
    assert rec["authorization_consumed_by_this_execution"] is True


def test_authorization_forbids_merge_final_test_and_successors():
    rec = ev.build_authorization_record()
    for field in (
        "merge_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "full_development_refit_authorized",
        "hyperparameter_tuning_authorized", "grid_search_authorized",
        "feature_search_authorized", "design_change_authorized",
        "smote_authorized", "new_model_family_authorized",
        "winner_selection_authorized", "retained_block_selection_authorized",
        "shap_authorized", "m3_authorized", "m4_authorized",
        "successor_action_authorized",
    ):
        assert rec[field] is False, field
    for item in ("merge_of_this_pr", "final_test_access"[:0] or
                 "final_test_predictor_inspection", "m3_start", "m4_start"):
        assert item in rec["does_not_extend_to"]


def test_normalized_scope_never_replaces_the_original_utterance():
    rec = ev.build_authorization_record()
    assert rec["normalized_authorization_scope"] != rec[
        "human_source_utterance"]
    assert rec[
        "normalized_authorization_scope_is_derived_not_verbatim_human_text"
    ] is True
    assert rec["normalized_scope_never_replaces_original_text"] is True


def test_tampered_utterance_fails_closed():
    rec = ev.build_authorization_record()
    rec["human_source_utterance"] = "بریم مرحله بعد "
    with pytest.raises(ev.EvaluationFail):
        ev.assert_authorization(rec)


def test_weakened_authorization_flag_fails_closed():
    rec = ev.build_authorization_record()
    rec["merge_authorized"] = True
    with pytest.raises(ev.EvaluationFail):
        ev.assert_authorization(rec)


@requires_package
def test_written_authorization_record_matches():
    rec = _load(ev.F_AUTH)
    assert rec["human_source_utterance"] == ev.AUTHORIZATION_TEXT_FA
    assert rec["human_source_utterance_sha256"] == ev.AUTHORIZATION_TEXT_SHA256
    assert rec["authorization_date"] == "2026-08-01"


# --------------------------------------------------------------------------- #
# Frozen inputs
# --------------------------------------------------------------------------- #

def test_frozen_inputs_are_terminal_and_unchanged():
    frozen = ev.verify_frozen_inputs(REPO_ROOT)
    assert frozen["gate_status"] == "PASS_FOR_M2_INCREMENTAL_EVALUATION"
    assert frozen["historical_d0_gate_status"] == "FAIL_M2_DATA_GATE"
    assert frozen["external_bundle_sha256"] == (
        "d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec"
    )
    assert frozen["pr70_merge_commit"] == (
        "fb5f0e13cb806e0ba28f0372b3b2264881564950"
    )
    assert frozen["pr70_merge_commit_is_ancestor_of_head"] is True
    assert set(frozen["frozen_sources_sha256"]) == set(ev.FROZEN_SOURCES)


def test_stage127_historical_tree_is_untouched_by_this_package():
    # The package writes only under the Stage128 M2 workstream directory.
    assert ev.OUT_DIR_REL.startswith("project/stage128/")
    assert "stage127/" not in ev.OUT_DIR_REL


# --------------------------------------------------------------------------- #
# Feature blocks
# --------------------------------------------------------------------------- #

def test_m1_feature_order_is_the_retained_nine():
    assert ev.M1_FEATURE_ORDER == [
        "log_total_assets", "leverage_ratio", "current_ratio",
        "roa_period_adjusted", "ocf_to_assets_period_adjusted",
        "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    ]
    assert ev.M1_FEATURE_ORDER == list(m1.M1_PRIMARY_FEATURE_ORDER)


def test_m2_is_exactly_the_nested_m1_set_plus_three_market_features():
    assert len(ev.M2_FEATURE_ORDER) == 12
    assert ev.M2_FEATURE_ORDER[:9] == ev.M1_FEATURE_ORDER
    assert ev.M2_FEATURE_ORDER[9:] == [
        "equity_return_window", "realized_volatility", "amihud_illiquidity",
    ]


def test_equity_return_window_is_the_frozen_d2_construct():
    assert ev.D2_SPECIFICATION == "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN"
    assert ev.D2_CALENDAR_CONVENTION == "GREGORIAN"
    assert ev.EQUITY_RETURN_SOURCE_COLUMN == "equity_return_d2"
    assert ev.EQUITY_RETURN_CONTRACT_FIELD == "equity_return_window"


def test_forbidden_market_features_never_enter_the_block():
    for feat in ev.FORBIDDEN_MARKET_FEATURES:
        assert feat not in ev.M2_FEATURE_ORDER
    assert "zero_trade_day_ratio_W" in ev.FORBIDDEN_MARKET_FEATURES
    assert "equity_return_window_d0_historical" in ev.FORBIDDEN_MARKET_FEATURES


@requires_package
def test_written_manifest_matches_the_frozen_blocks():
    man = _load(ev.F_MANIFEST)
    assert man["m1_feature_count"] == 9
    assert man["m2_feature_count"] == 12
    assert man["m2_is_nested_superset_of_m1"] is True
    assert man["extra_market_features_added"] == []
    assert man["equity_return_window_implementation"] == ev.D2_SPECIFICATION


# --------------------------------------------------------------------------- #
# Sample and joins
# --------------------------------------------------------------------------- #

@requires_package
def test_common_sample_counts_exact():
    ja = _load(ev.F_JOIN_AUDIT)
    assert ja["parent_rows"] == 666
    assert ja["common_rows"] == 539
    assert ja["common_positive"] == 55
    assert ja["common_negative"] == 484
    assert ja["pooled_oof_rows"] == 366
    assert ja["pooled_oof_positive"] == 28


@requires_package
def test_join_is_one_to_one_and_final_test_free():
    ja = _load(ev.F_JOIN_AUDIT)
    assert ja["duplicate_join_keys"] == 0
    assert ja["many_to_many_joins"] == 0
    assert ja["unmatched_parent_rows"] == 0
    assert ja["target_year_disagreements"] == 0
    assert ja["fold_role_disagreements"] == 0
    assert ja["final_test_rows_in_join"] == 0
    assert ja["final_test_rows_loaded"] == 0
    assert ja["join_is_one_to_one"] is True


@requires_package
def test_common_fold_counts_and_validation_positives_exact():
    attr = _load(ev.F_ATTRITION)
    folds = attr["common_fold_counts"]
    assert folds["fold1_train"]["rows"] == 173
    assert folds["fold1_validation"]["rows"] == 159
    assert folds["fold2_train"]["rows"] == 332
    assert folds["fold2_validation"]["rows"] == 207
    assert folds["fold1_validation"]["positive"] == 18
    assert folds["fold2_validation"]["positive"] == 10


@requires_package
def test_no_final_test_target_year_in_any_prediction_row():
    rows = _rows(ev.F_OOF)
    assert len(rows) == 3 * 366
    for r in rows:
        assert int(r["target_year"]) in m1.DEVELOPMENT_TARGET_YEARS
        assert int(r["target_year"]) not in m1.FINAL_TEST_TARGET_YEARS


@requires_package
def test_attrition_is_reported_and_not_read_as_improvement():
    attr = _load(ev.F_ATTRITION)
    assert attr["attrition_rows"] == 666 - 539
    assert attr["attrition_is_reported_not_concealed"] is True
    assert attr["attrition_is_not_model_improvement"] is True
    assert attr["parent_development"]["rows"] == 666
    assert attr["common_sample"]["rows"] == 539
    assert attr["dropped_by_d2_ineligibility"]["rows"] == 127


# --------------------------------------------------------------------------- #
# Paired comparison validity
# --------------------------------------------------------------------------- #

@requires_package
def test_m1_and_m2_evaluated_on_identical_rows():
    rows = _rows(ev.F_OOF)
    by_family: dict[str, list[tuple[str, str, str]]] = {}
    for r in rows:
        by_family.setdefault(r["model_family"], []).append(
            (r["ticker"], r["fiscal_year_t"], r["temporal_fold"]))
    identities = list(by_family.values())
    for other in identities[1:]:
        assert other == identities[0]
    # Every paired row carries BOTH block probabilities for the same row.
    for r in rows:
        assert r["m1_probability"] != ""
        assert r["m2_probability"] != ""
        assert math.isclose(
            float(r["m2_minus_m1_probability"]),
            float(r["m2_probability"]) - float(r["m1_probability"]),
            abs_tol=1e-9,
        )


@requires_package
def test_row_identities_are_unique_within_each_family():
    rows = _rows(ev.F_OOF)
    for family in ev.MODEL_FAMILIES:
        keys = [
            (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
            for r in rows if r["model_family"] == family
        ]
        assert len(keys) == len(set(keys)) == 366


@requires_package
def test_m1_comparator_was_refitted_on_common_sample_training_rows():
    audit = _load(ev.F_FIT_AUDIT)
    train_rows = {e["train_rows"] for e in audit["fits"]}
    assert train_rows == {173, 332}, train_rows
    # Both blocks were fit the same number of times: no reuse of the original
    # unpaired 666-row M1 OOF predictions.
    assert audit["by_block"]["M1"] == audit["by_block"]["M2"] == 22


@requires_package
def test_validation_roles_are_the_locked_temporal_folds():
    rows = _rows(ev.F_OOF)
    assert {r["temporal_fold"] for r in rows} == {
        "fold1_validation", "fold2_validation"}


# --------------------------------------------------------------------------- #
# Modeling
# --------------------------------------------------------------------------- #

def test_exactly_three_frozen_families_and_configurations():
    assert set(ev.MODEL_FAMILIES) == {
        "regularized_logistic_regression", "random_forest", "xgboost"}
    ids = {f: c["configuration_id"]
           for f, c in ev.FROZEN_CONFIGURATIONS.items()}
    assert ids["regularized_logistic_regression"] == "logistic__C_0.1"
    assert ids["random_forest"] == "rf__depth_3__maxfeat_'sqrt'__leaf_10"
    assert ids["xgboost"] == "xgboost__lr_0.03__depth_2__mcw_1__lambda_1"


def test_configurations_match_the_stage126_selection_artifact():
    selected = json.loads(
        (REPO_ROOT / ev.SELECTED_CONFIGS_REL).read_text(encoding="utf-8"))
    for family, cfg in ev.FROZEN_CONFIGURATIONS.items():
        assert selected[family]["configuration_id"] == cfg["configuration_id"]


def test_frozen_seed_list_is_the_five_final_oof_seeds():
    assert tuple(ev.FINAL_OOF_SEEDS) == (
        20260719, 20260720, 20260721, 20260722, 20260723)
    assert ev.FINAL_OOF_SEEDS == m1.FINAL_OOF_SEEDS
    assert tuple(m1.TUNING_SEEDS) != tuple(ev.FINAL_OOF_SEEDS)


def test_no_early_stopping_in_the_xgboost_configuration():
    hp = ev.FROZEN_CONFIGURATIONS["xgboost"]["hyperparameters"]
    assert hp["early_stopping"] is False
    assert hp["n_estimators"] == 300
    assert hp["learning_rate"] == 0.03
    assert hp["max_depth"] == 2
    assert hp["min_child_weight"] == 1
    assert hp["reg_lambda"] == 1


@requires_package
def test_primary_predictive_fit_count_is_exactly_44():
    audit = _load(ev.F_FIT_AUDIT)
    assert ev.EXPECTED_PRIMARY_FIT_COUNT == 44
    assert audit["observed_primary_predictive_fit_count"] == 44
    assert audit["matches_expected"] is True
    assert audit["by_model_family"] == {
        "regularized_logistic_regression": 4,
        "random_forest": 20,
        "xgboost": 20,
    }
    assert audit["bootstrap_refits"] == 0
    assert audit["bootstrap_increases_fit_count"] is False
    assert audit["tuning_fits"] == 0
    assert audit["smote_fits"] == 0
    assert audit["final_test_fits"] == 0


@requires_package
def test_scale_pos_weight_uses_training_fold_counts_only():
    audit = _load(ev.F_FIT_AUDIT)
    xgb = [e for e in audit["fits"] if e["family"] == "xgboost"]
    assert xgb
    for e in xgb:
        assert e["scale_pos_weight"] is not None
        assert math.isclose(
            e["scale_pos_weight"],
            e["train_negative"] / e["train_positive"], rel_tol=1e-9)
        assert e["train_positive"] + e["train_negative"] == e["train_rows"]


@requires_package
def test_contract_declares_no_tuning_search_or_smote():
    c = _load(ev.F_CONTRACT)
    assert c["tuning_performed"] is False
    assert c["grid_search_performed"] is False
    assert c["feature_search_performed"] is False
    assert c["smote_used"] is False
    assert c["early_stopping_used"] is False
    assert c["configuration_reselection_performed"] is False
    assert c["tuning_seeds_used"] is False
    assert c["historical_d0_equity_return_used_as_predictor"] is False


@requires_package
def test_preprocessing_contract_is_the_frozen_one():
    p = _load(ev.F_CONTRACT)["preprocessing"]
    assert p["estimated_inside_each_temporal_training_fold_only"] is True
    assert p["missingness_indicators_standardized"] is False
    assert p["random_forest_standardized"] is False
    assert p["xgboost_standardized"] is False
    assert p["parameters_estimated_on_combined_train_and_validation"] is False
    assert p["final_test_influenced_preprocessing"] is False
    assert p["feature_screening_performed"] is False
    assert p["financial_expense_sign_preserved"] is True
    assert p["financial_expense_absolute_value_taken"] is False
    assert p["steps"][0] == "deterministic_source_to_feature_transformation"
    assert p["steps"][-1] == (
        "standardize_imputed_continuous_predictors_for_logistic_only")


def test_only_logistic_is_standardized():
    assert m1._requires_standardization("regularized_logistic_regression")
    assert not m1._requires_standardization("random_forest")
    assert not m1._requires_standardization("xgboost")


# --------------------------------------------------------------------------- #
# Metrics, calibration, uncertainty
# --------------------------------------------------------------------------- #

def test_metric_contract_exact():
    assert ev.PRIMARY_METRIC == "pr_auc"
    assert ev.SECONDARY_METRICS == (
        "roc_auc", "brier_score", "recall_at_10pct", "lift_at_10pct")


@requires_package
def test_metrics_reported_for_m1_m2_and_paired_delta():
    rows = _rows(ev.F_METRICS)
    assert {r["block"] for r in rows} == {"M1", "M2", "M2_minus_M1"}
    assert {r["model_family"] for r in rows} == set(ev.MODEL_FAMILIES)
    assert {r["scope"] for r in rows} == {
        "pooled_oof", "fold1_validation", "fold2_validation"}
    for family in ev.MODEL_FAMILIES:
        pooled = {
            r["block"]: r for r in rows
            if r["model_family"] == family and r["scope"] == "pooled_oof"
        }
        assert int(pooled["M1"]["n_rows"]) == 366
        assert int(pooled["M1"]["n_positive"]) == 28
        assert math.isclose(
            float(pooled["M2_minus_M1"]["pr_auc"]),
            float(pooled["M2"]["pr_auc"]) - float(pooled["M1"]["pr_auc"]),
            abs_tol=1e-9,
        )


@requires_package
def test_bootstrap_contract_and_valid_replicates():
    b = _load(ev.F_BOOTSTRAP)
    assert b["method"] == "paired_company_cluster_bootstrap"
    assert b["cluster"] == "ticker"
    assert b["replicates_attempted"] == 2000
    assert b["seed"] == 20260724
    assert b["confidence_interval"] == 0.95
    assert b["interval_type"] == "percentile"
    assert b["minimum_valid_replicates"] == 1000
    assert b["same_resampled_rows_for_both_blocks"] is True
    assert b["models_refit_during_bootstrap"] is False
    for family, v in b["by_family"].items():
        assert v["valid_replicates"] >= 1000, family
        assert v["minimum_valid_replicates_met"] is True
        assert v["metrics"]["pr_auc"]["ci_estimable"] is True


@requires_package
def test_calibration_is_raw_and_isotonic_free():
    c = _load(ev.F_CALIBRATION)
    assert c["primary_probabilities_are_raw"] is True
    assert c["isotonic_calibration_allowed"] is False
    assert c["isotonic_calibration_executed"] is False
    assert c["recalibrated_probabilities_used_as_primary_surface"] is False
    assert c["recalibration_influenced_conclusion"] is False
    assert c["bins"] == 5
    for family, entry in c["by_family"].items():
        assert set(entry) == {"M1", "M2"}
        for block, v in entry.items():
            assert v["brier_score"] is not None
            assert len(v["calibration_curve_quantile_bins"]) == 5
            if v["estimable"]:
                assert v["calibration_slope"] is not None
                assert v["calibration_intercept"] is not None
            else:
                assert v["calibration_slope"] is None
                assert v["reason"]


# --------------------------------------------------------------------------- #
# Post-lock eligibility audit
# --------------------------------------------------------------------------- #

@requires_package
def test_eligibility_audit_covers_every_required_dimension():
    a = _load(ev.F_ELIGIBILITY)
    assert a["executed_before_interpreting_predictive_results"] is True
    assert a["required_dimensions_attempted"] is True
    dims = {r["dimension"] for r in _rows(ev.F_ELIGIBILITY_CSV)}
    for required in (
        "prediction_cohort", "industry", "firm_size", "market_activity",
        "market_activity_and_traded_value", "m1_predictor_availability",
    ):
        assert required in dims, required


@requires_package
def test_smd_is_descriptive_and_removes_nothing():
    a = _load(ev.F_ELIGIBILITY)
    assert a["smd_flag_threshold"] == 0.10
    assert a["smd_is_descriptive_flag_only"] is True
    assert a["smd_is_not_an_exclusion_threshold"] is True
    assert a["rows_removed_due_to_smd"] == 0
    assert a["weighting_applied"] is False
    assert a["matching_applied"] is False
    assert a["sample_repair_applied"] is False
    assert a["m2_feature_changed_by_audit"] is False
    assert a["boundary_rule_changed_by_audit"] is False
    assert a["gate_result_revised_by_audit"] is False
    assert a["model_design_changed_by_audit"] is False
    assert a["audit_stops_model_execution"] is False
    # Eligible + ineligible must reconstitute the full parent surface.
    assert a["eligible_rows"] + a["ineligible_rows"] == 666


@requires_package
def test_distress_rate_comparison_is_separate_and_descriptive():
    o = _load(ev.F_ELIGIBILITY)["post_lock_outcome_side_comparison"]
    assert o["is_descriptive_only"] is True
    assert o["separated_from_predictor_side_audit"] is True
    assert o["permitted_because_design_is_locked"] is True
    assert o["used_to_change_d2"] is False
    assert o["used_to_change_sample_rule"] is False
    assert o["used_to_change_model_configuration"] is False
    assert o["used_to_change_interpretation_protocol"] is False
    assert o["eligible_positive"] + o["ineligible_positive"] == 68


@requires_package
def test_zero_trade_day_ratio_appears_only_in_the_audit():
    variables = {r["variable"] for r in _rows(ev.F_ELIGIBILITY_CSV)}
    assert "zero_trade_day_ratio_W" in variables
    assert "zero_trade_day_ratio_W" not in ev.M2_FEATURE_ORDER
    man = _load(ev.F_MANIFEST)
    assert "zero_trade_day_ratio_W" not in man["m2_feature_order"]


@requires_package
def test_unavailable_audit_fields_are_reported_not_fabricated():
    a = _load(ev.F_ELIGIBILITY)
    for entry in a["unavailable_fields"]:
        assert entry["note"], entry
    for row in _rows(ev.F_ELIGIBILITY_CSV):
        if row["availability"] == "unavailable":
            assert row["smd"] == ""


# --------------------------------------------------------------------------- #
# Multiplicity
# --------------------------------------------------------------------------- #

@requires_package
def test_multiplicity_family_is_incomplete_and_deferred():
    m = _load(ev.F_MULTIPLICITY)
    assert m["confirmatory_family"] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
    assert m["confirmatory_family_2_member"] == "M2_minus_M1"
    assert m["holm_family_complete"] is False
    assert m["holm_final_adjustment_deferred"] is True
    assert m["holm_adjustment_executed_in_this_action"] is False
    assert m["family_redefined_as_one_hypothesis"] is False
    assert m["one_comparison_holm_reported_as_complete_family"] is False
    assert m["additional_post_hoc_hypothesis_family_authorized"] is False
    assert m["raw_paired_uncertainty_preserved"] is True
    assert m["pending_members"] == ["M3_minus_M2", "M4_minus_M3"]


# --------------------------------------------------------------------------- #
# Firewall and interpretation
# --------------------------------------------------------------------------- #

@requires_package
def test_final_test_firewall_counts_are_zero():
    f = _load(ev.F_FIREWALL)
    assert f["final_test_predictor_values_read"] == 0
    assert f["final_test_target_values_read"] == 0
    assert f["final_test_predictions"] == 0
    assert f["final_test_model_fits"] == 0
    assert f["final_test_keys_in_any_artifact"] == 0
    assert f["final_test_unlocked"] is False
    assert f["final_test_access_authorized"] is False
    assert f["final_test_evaluation_performed"] is False
    assert f["full_development_refits"] == 0
    assert f["m3_executions"] == 0
    assert f["m4_executions"] == 0
    assert f["smote_executions"] == 0
    assert f["shap_executions"] == 0
    assert f["final_test_target_years_excluded"] == [1400, 1401, 1402]


@requires_package
def test_no_winner_or_retained_block_is_selected():
    d = _load(ev.F_DECISION)
    assert d["winner_selected"] is False
    assert d["retained_block_selected"] is False
    assert d["m2_automatically_retained"] is False
    assert d["m2_automatically_rejected"] is False
    assert d["superiority_claimed"] is False
    assert d["causal_interpretation_made"] is False
    assert d["new_pass_fail_threshold_created"] is False
    assert d["single_fabricated_score_reported"] is False
    assert d["design_changed_after_seeing_results"] is False
    assert d["human_retained_block_decision_required"] is True
    assert d["authorizes_next_action"] is False
    assert d["m3_started"] is False and d["m4_started"] is False
    assert d["merge_authorized"] is False


@requires_package
def test_decision_reports_direction_with_uncertainty_for_every_family():
    d = _load(ev.F_DECISION)
    per = d["per_family_primary_metric"]
    assert set(per) == set(ev.MODEL_FAMILIES)
    for family, e in per.items():
        assert e["primary_metric"] == "pr_auc"
        assert e["observed_direction"] in {
            "positive_with_interval_excluding_zero",
            "negative_with_interval_excluding_zero",
            "approximately_null_interval_includes_zero",
            "not_estimable",
        }
        assert e["m2_minus_m1_pr_auc"] is not None


@requires_package
def test_decision_limitations_cover_the_required_interpretation_inputs():
    d = _load(ev.F_DECISION)
    inputs = d["interpretation_inputs"]
    assert inputs["common_sample_attrition_rows"] == 127
    assert inputs["pooled_oof_positive"] == 28
    assert inputs["bootstrap_uncertainty_reported"] is True
    assert inputs["cross_family_agreement_reported"] is True
    assert inputs["multiplicity_family_complete"] is False
    assert len(d["limitations"]) >= 4


# --------------------------------------------------------------------------- #
# QC and package integrity
# --------------------------------------------------------------------------- #

@requires_package
def test_qc_report_all_pass():
    qc = _load(ev.F_QC)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])


@requires_package
def test_metadata_hashes_match_every_written_artifact():
    meta = _load(ev.F_METADATA)
    for rel, expected in meta["package_artifacts_sha256"].items():
        actual = hashlib.sha256(
            (REPO_ROOT / rel).read_bytes()).hexdigest()
        assert actual == expected, rel
    assert meta["decision_id"] == "stage127-m2-incremental-evaluation"
    assert meta["primary_predictive_model_fits"] == 44
    assert meta["stage127_historical_artifacts_modified"] is False


@requires_package
def test_every_required_artifact_is_present():
    for name in ev.TRACKED_CONTENT_FILES:
        assert (OUT / name).is_file(), name
    assert (OUT / ev.F_METADATA).is_file()


def test_handoff_markers_do_not_re_authorize_anything():
    markers = ev.handoff_markers({"fit_audit": {
        "observed_primary_predictive_fit_count": 44}})
    assert markers["stage127_m2_incremental_evaluation_completed"] is True
    assert markers["m2_incremental_evaluation_authorized"] is False
    assert markers["m2_modeling_started"] is False
    assert markers["m2_block_retained"] is False
    assert markers["m2_retained_block_decision_required"] is True
    assert markers["final_test_unlocked"] is False
    assert markers["m3_started"] is False and markers["m3_authorized"] is False
    assert markers["m4_started"] is False and markers["m4_authorized"] is False
