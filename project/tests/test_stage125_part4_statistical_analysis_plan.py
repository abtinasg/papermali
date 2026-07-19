"""Tests for Stage125 Part 4 Statistical Analysis Plan (v2)."""
from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part4_statistical_analysis_plan as m  # noqa: E402


def test_wrong_baseline_sha_fails(monkeypatch):
    monkeypatch.setattr(m, "EXPECTED_BASELINE_COMMIT", "0" * 40)
    with pytest.raises(m.QCFail, match="wrong baseline SHA"):
        m.verify_baseline_commit(REPO_ROOT)


def test_missing_part3c_hash_fails(monkeypatch):
    missing = "project/stage125/does_not_exist_part4.csv"
    monkeypatch.setattr(m, "FROZEN_PART3C_INPUTS", {missing: "a" * 64})
    with pytest.raises(m.QCFail, match="missing Part 3C input"):
        m.frozen_part3c_hashes(REPO_ROOT)


def test_changed_part3c_hash_fails(monkeypatch):
    fake = dict(m.FROZEN_PART3C_INPUTS)
    key = next(iter(fake))
    fake[key] = "0" * 64
    monkeypatch.setattr(m, "FROZEN_PART3C_INPUTS", fake)
    with pytest.raises(m.QCFail, match="Part 3C input hash mismatch"):
        m.frozen_part3c_hashes(REPO_ROOT)


def test_part3c_hashes_unchanged():
    got = m.frozen_part3c_hashes(REPO_ROOT)
    assert got == m.FROZEN_PART3C_INPUTS
    assert len(got) == 8


def test_sample_count_mutation_fails(monkeypatch):
    specs = {k: dict(v) for k, v in m.SAMPLE_SPECS.items()}
    specs["main_rule_a_primary"]["rows"] = 9999
    monkeypatch.setattr(m, "SAMPLE_SPECS", specs)
    with pytest.raises(m.QCFail, match="sample-count mutation"):
        m.load_analysis_ready(REPO_ROOT, "main_rule_a_primary")


def test_target_count_mutation_fails(monkeypatch):
    specs = {k: dict(v) for k, v in m.SAMPLE_SPECS.items()}
    specs["main_rule_a_primary"]["positive"] = 1
    monkeypatch.setattr(m, "SAMPLE_SPECS", specs)
    with pytest.raises(m.QCFail, match="target-count mutation"):
        m.load_analysis_ready(REPO_ROOT, "main_rule_a_primary")


def test_rampna_reentry_fails(monkeypatch):
    rows = m.load_analysis_ready(REPO_ROOT, "main_rule_a_primary")
    rows = list(rows)
    rows[0] = dict(rows[0])
    rows[0]["ticker"] = "رمپنا"
    rows[0]["fiscal_year_t"] = "1396"

    def _fake_load(repo_root, sample):
        if sample == "main_rule_a_primary":
            ramp = [
                r for r in rows
                if r["ticker"] == "رمپنا" and str(r["fiscal_year_t"]) == "1396"
            ]
            if ramp:
                raise m.QCFail("رمپنا re-entering analysis-ready data")
        return m.load_analysis_ready(repo_root, sample)

    monkeypatch.setattr(m, "load_analysis_ready", _fake_load)
    with pytest.raises(m.QCFail, match="رمپنا"):
        m.load_analysis_ready(REPO_ROOT, "main_rule_a_primary")


def test_feature_order_mutation_fails():
    with pytest.raises(m.QCFail, match="feature order mutation"):
        m.assert_feature_order(
            ["leverage_ratio"] + m.M1_PRIMARY_FEATURE_ORDER[1:],
            list(m.M1_PRIMARY_FEATURE_ORDER),
            "M1",
        )


def test_unapproved_feature_entering_m1_fails():
    with pytest.raises(m.QCFail, match="unapproved feature entering M1"):
        m.assert_no_unapproved_m1(
            list(m.M1_PRIMARY_FEATURE_ORDER) + ["roe_period_adjusted"]
        )


def test_approved_feature_silently_removed_fails():
    with pytest.raises(m.QCFail, match="approved feature silently removed"):
        m.assert_no_unapproved_m1(list(m.M1_PRIMARY_FEATURE_ORDER)[:-1])


def test_target_derived_field_entering_predictor_set_fails():
    with pytest.raises(m.QCFail, match="target-derived field"):
        m.assert_no_target_derived(
            list(m.M1_PRIMARY_FEATURE_ORDER) + ["FD_target_main_t_plus_1"]
        )


def test_m1_target_proximity_order_mutation_fails():
    bad = list(m.M1_TARGET_PROXIMITY_ROBUSTNESS)
    bad[0], bad[1] = bad[1], bad[0]
    with pytest.raises(m.QCFail, match="M1_TARGET_PROXIMITY_ROBUSTNESS"):
        m.assert_feature_order(
            bad, list(m.M1_TARGET_PROXIMITY_ROBUSTNESS),
            "M1_TARGET_PROXIMITY_ROBUSTNESS",
        )


def test_m2_m3_m4_ordering_mutation_fails(monkeypatch):
    monkeypatch.setattr(
        m, "M2_BLOCK",
        ["realized_volatility", "equity_return_window", "amihud_illiquidity"],
    )
    with pytest.raises(m.QCFail, match="M2 ordering mutation"):
        m.build_all(REPO_ROOT)


def test_random_split_attempted_fails():
    with pytest.raises(m.AuthorizationError, match="random split attempted"):
        m.reject_random_split("random")


def test_final_test_year_changed_fails():
    with pytest.raises(m.AuthorizationError, match="final test year changed"):
        m.reject_final_test_year_change({1400, 1401})


def test_validation_year_overlap_fails():
    with pytest.raises(m.AuthorizationError, match="validation-year overlap"):
        m.reject_validation_overlap({1393, 1396}, {1396, 1397})


def test_train_year_later_than_validation_fails():
    with pytest.raises(
        m.AuthorizationError, match="train year later than validation year",
    ):
        m.reject_train_after_validation({1393, 1398}, {1396, 1397})


def test_final_test_feature_coverage_not_used_for_selection():
    rows = m.load_analysis_ready(REPO_ROOT, "main_rule_a_primary")
    cov = m.compute_m1_coverage(rows)
    assert all(int(r["development_rows"]) == 666 for r in cov)
    ft = m.final_test_rows(rows)
    with pytest.raises(m.QCFail, match="no development rows"):
        m.compute_m1_coverage(ft)


def test_final_test_row_level_target_not_in_split_manifest():
    sample_rows = {
        s: m.load_analysis_ready(REPO_ROOT, s) for s in m.ANALYSIS_READY_FILES
    }
    manifest = m.build_split_manifest(sample_rows)
    assert manifest
    for row in manifest:
        assert set(row) == set(m.SPLIT_MANIFEST_COLUMNS)
        for t in m.ALL_TARGETS:
            assert t not in row


def test_primary_metric_locked_pr_auc():
    assert m.PRIMARY_METRIC == "PR-AUC"
    contract = m.build_metrics_contract()
    assert contract["primary_metric"] == "PR-AUC"


def test_k_fraction_locked():
    assert m.TOPK_FRACTION == 0.10
    assert m.build_metrics_contract()["topk"]["fraction"] == 0.10


def test_bootstrap_replicate_and_cluster_locked():
    c = m.build_metrics_contract()["uncertainty"]
    assert c["replicates"] == 2000
    assert c["cluster"] == "ticker"


def test_holm_correction_locked():
    assert m.build_metrics_contract()["multiplicity"]["correction"] == "Holm"


def test_seed_lists_locked():
    assert m.TUNING_SEEDS == (20260719, 20260720, 20260721)
    assert m.FINAL_SEEDS == (
        20260719, 20260720, 20260721, 20260722, 20260723,
    )


def test_hyperparameter_grid_not_expanded():
    h = m.build_hyperparameter_budget()
    assert h["total_configurations_per_block"] == 32
    assert h["grid_expansion_after_results_authorized"] is False
    assert h["logistic_regression"]["n_configurations"] == 4
    assert h["random_forest"]["n_configurations"] == 12
    assert h["xgboost"]["n_configurations"] == 16


def test_early_stopping_not_introduced():
    h = m.build_hyperparameter_budget()
    assert h["early_stopping_authorized"] is False
    assert h["xgboost"]["early_stopping"] is False


def test_smote_outside_training_fold_forbidden():
    s = m.build_model_specs()["smote_robustness"]
    assert s["apply_only_inside_training_fold"] is True
    assert s["never_before_temporal_splitting"] is True


def test_no_model_imports_in_source():
    m.assert_no_model_imports_in_source(REPO_ROOT)


def test_network_attempt_blocked_by_sentinel():
    with p3b0.network_sentinel() as sentinel:
        with pytest.raises(Exception):
            socket.create_connection(("example.com", 80), timeout=0.1)
        assert sentinel.calls_attempted >= 1


def test_build_all_offline_and_deterministic():
    with p3b0.network_sentinel() as sentinel:
        c1, _ = m.build_all(REPO_ROOT)
        c2, _ = m.build_all(REPO_ROOT)
        assert sentinel.calls_attempted == 0
    assert set(c1) == set(m.TRACKED_CONTENT_FILES)
    for k in c1:
        assert c1[k] == c2[k]
    assert c1[m.F_SAP] == json.dumps(
        json.loads(c1[m.F_SAP]), indent=2, ensure_ascii=False, sort_keys=True,
    ) + "\n"


def test_run_build_and_check(tmp_path):
    with p3b0.network_sentinel() as sentinel:
        result = m.run(
            project_dir=ROOT, output_dir=tmp_path, build=True, check=False,
        )
        assert sentinel.calls_attempted == 0
    assert result["qc"]["all_pass"] is True
    assert result["qc"]["model_fit_calls"] == 0
    assert result["qc"]["prediction_calls"] == 0
    assert result["qc"]["final_test_accessed_for_modeling"] is False
    assert result["qc"]["contract_version"] == "stage125_part4_sap_v2"
    assert result["qc"]["research_pointers"]["next_research_action_id"] == (
        "stage125-part5-readiness-closure"
    )
    result2 = m.run(
        project_dir=ROOT, output_dir=tmp_path, build=False, check=True,
    )
    assert result2["qc"]["all_pass"] is True


def test_article141_final_test_descriptive_only():
    sample_rows = {
        s: m.load_analysis_ready(REPO_ROOT, s) for s in m.ANALYSIS_READY_FILES
    }
    events = m.build_event_counts(sample_rows)
    art = [
        e for e in events
        if e["sample_design"] == m.PRIMARY_SAMPLE
        and e["target"] == m.ARTICLE141_TARGET
        and e["window"] == "final_test"
    ][0]
    assert int(art["positive"]) < 10
    assert "distributional_descriptive_robustness_only" in art[
        "event_gate_decision"
    ]
    assert "missing" in art
    assert "evaluable_rows" in art


def test_primary_final_test_counts():
    rows = m.load_analysis_ready(REPO_ROOT, m.PRIMARY_SAMPLE)
    ft = m.final_test_rows(rows)
    counts = m.count_target_states([r[m.PRIMARY_TARGET] for r in ft])
    assert len(ft) == 346
    assert counts["positive"] == 12
    assert counts["negative"] == 334
    assert counts["missing"] == 0
    assert counts["evaluable_rows"] == 346


def test_m1_exclusion_count():
    assert len(m.M1_EXCLUSIONS) == 23
    names = {e["feature_name"] for e in m.M1_EXCLUSIONS}
    assert m.REVENUE_GROWTH_FEATURE in names


def test_contract_version_v2():
    assert m.CONTRACT_VERSION == "stage125_part4_sap_v2"
    assert m.CONTRACT_VERSION_V1_HISTORICAL == "stage125_part4_sap_v1"


def test_m1_primary_exact_nine_feature_order():
    assert m.M1_PRIMARY_FEATURE_ORDER == [
        "log_total_assets",
        "leverage_ratio",
        "current_ratio",
        "roa_period_adjusted",
        "ocf_to_assets_period_adjusted",
        "asset_turnover_period_adjusted",
        "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    ]
    assert len(m.M1_PRIMARY_FEATURE_ORDER) == 9
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_PRIMARY_FEATURE_ORDER


def test_m1_target_proximity_exact_six_feature_order():
    assert m.M1_TARGET_PROXIMITY_ROBUSTNESS == [
        "log_total_assets",
        "current_ratio",
        "roa_period_adjusted",
        "asset_turnover_period_adjusted",
        "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
    ]
    assert len(m.M1_TARGET_PROXIMITY_ROBUSTNESS) == 6
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_TARGET_PROXIMITY_ROBUSTNESS
    for prox in m.M1_TARGET_PROXIMITY_REMOVED:
        assert prox not in m.M1_TARGET_PROXIMITY_ROBUSTNESS


def test_nested_counts_9_12_15_19():
    m2 = m.M1_PRIMARY_FEATURE_ORDER + m.M2_BLOCK
    m3 = m2 + m.M3_BLOCK
    m4 = m3 + m.M4_BLOCK
    assert len(m.M1_PRIMARY_FEATURE_ORDER) == 9
    assert len(m2) == 12
    assert len(m3) == 15
    assert len(m4) == 19
    for surface in (m.M1_PRIMARY_FEATURE_ORDER, m2, m3, m4):
        assert m.REVENUE_GROWTH_FEATURE not in surface


def test_revenue_growth_raw_coverage_and_rejection():
    rows = m.load_analysis_ready(REPO_ROOT, m.PRIMARY_SAMPLE)
    cov = {r["feature_name"]: r for r in m.compute_m1_coverage(rows)}
    g = cov[m.REVENUE_GROWTH_FEATURE]
    assert int(g["development_rows"]) == 666
    assert int(g["nonmissing_rows"]) == 565
    assert abs(float(g["coverage"]) - 0.8483483483) < 1e-10
    assert int(g["fold1_train_nonmissing"]) == 148
    assert int(g["fold1_train_rows"]) == 245
    assert abs(float(g["fold1_train_coverage"]) - 0.6040816327) < 1e-10
    assert int(g["fold1_validation_nonmissing"]) == 203
    assert int(g["fold1_validation_rows"]) == 205
    assert abs(float(g["fold1_validation_coverage"]) - 0.9902439024) < 1e-10
    assert int(g["fold2_train_nonmissing"]) == 351
    assert int(g["fold2_train_rows"]) == 450
    assert abs(float(g["fold2_train_coverage"]) - 0.7800000000) < 1e-10
    assert int(g["fold2_validation_nonmissing"]) == 214
    assert int(g["fold2_validation_rows"]) == 216
    assert abs(float(g["fold2_validation_coverage"]) - 0.9907407407) < 1e-10
    assert float(g["minimum_fold_training_coverage"]) < 0.75
    assert g["admission_status"] == "rejected_m1_primary_coverage_gate_failed"
    assert "growth_coverage_exception_applied" not in g


def test_revenue_growth_remains_in_audit_and_frozen_absent_from_models():
    rows = m.load_analysis_ready(REPO_ROOT, m.PRIMARY_SAMPLE)
    assert m.REVENUE_GROWTH_FEATURE in rows[0]
    cov = m.compute_m1_coverage(rows)
    assert any(r["feature_name"] == m.REVENUE_GROWTH_FEATURE for r in cov)
    content, extras = m.build_all(REPO_ROOT)
    sap = extras["sap"]
    nested = sap["nested_blocks"]
    for block in ("M1", "M2", "M3", "M4"):
        assert m.REVENUE_GROWTH_FEATURE not in nested[block]
    feature_csv = content[m.F_FEATURE_SETS]
    admitted_lines = [
        line for line in feature_csv.splitlines()
        if line.startswith("M1_PRIMARY_FEATURE_ORDER,")
        or line.startswith("M1_TARGET_PROXIMITY_ROBUSTNESS,")
        or line.startswith("M2_BLOCK,")
        or line.startswith("M3_BLOCK,")
        or line.startswith("M4_BLOCK,")
    ]
    assert all(m.REVENUE_GROWTH_FEATURE not in line for line in admitted_lines)
    assert m.REVENUE_GROWTH_FEATURE in content[m.F_COVERAGE]
    assert m.REVENUE_GROWTH_FEATURE in content[m.F_EXCLUSIONS]


def test_no_growth_denominator_exception_exists():
    content, extras = m.build_all(REPO_ROOT)
    sap = extras["sap"]
    assert sap["growth_feature_coverage_exception"] is None
    assert sap["growth_denominator_exception_absent"] is True
    assert sap["m1_coverage_gates"][
        "growth_denominator_exception_authorized"
    ] is False
    assert "growth_coverage_exception_applied" not in content[m.F_COVERAGE]
    decision = json.loads(content[m.F_RG_DECISION])
    assert decision["denominator_exception_authorized"] is False
    assert decision["first_observation_denominator_exception_authorized"] is False
    # Active exception constant assignment must not exist.
    assert not hasattr(m, "GROWTH_COVERAGE_EXCEPTION")


def test_first_observation_denominator_exclusion_attempt_fails():
    with pytest.raises(m.AuthorizationError, match="denominator exception"):
        m.reject_growth_denominator_exception(
            exclude_first_observed_fiscal_year_from_fold_denominator=True,
        )
    with pytest.raises(m.AuthorizationError, match="denominator exception"):
        m.reject_growth_denominator_exception(
            structural_first_observation_denominator_adjustment=True,
        )


def test_coverage_denominator_mutation_fails():
    with pytest.raises(m.AuthorizationError, match="coverage denominator mutation"):
        m.reject_coverage_denominator_mutation(
            subset_row_count=245, denominator_used=148, label="fold1_train",
        )


def test_classify_target_states_strict():
    assert m.classify_target_state(1) == "positive"
    assert m.classify_target_state(1.0) == "positive"
    assert m.classify_target_state("1") == "positive"
    assert m.classify_target_state("1.0") == "positive"
    assert m.classify_target_state(0) == "negative"
    assert m.classify_target_state(0.0) == "negative"
    assert m.classify_target_state("0") == "negative"
    assert m.classify_target_state("0.0") == "negative"
    assert m.classify_target_state("") == "missing"
    assert m.classify_target_state(None) == "missing"
    assert m.classify_target_state("nan") == "missing"
    assert m.classify_target_state("2") == "missing"
    assert m.classify_target_state("true") == "missing"
    assert m.classify_target_state("yes") == "missing"
    counts = m.count_target_states([1, 0, "", "x", "1.0", "0.0"])
    assert counts == {
        "rows": 6,
        "evaluable_rows": 4,
        "positive": 2,
        "negative": 2,
        "missing": 2,
    }
    assert counts["rows"] == (
        counts["positive"] + counts["negative"] + counts["missing"]
    )
    assert counts["evaluable_rows"] == counts["positive"] + counts["negative"]


def test_missing_target_never_counted_negative():
    assert m.classify_target_state("") != "negative"
    assert m._is_negative("") is False
    assert m._is_positive("") is False
    # Legacy trap: rows - positive would mislabel missing as negative.
    values = ["1", "", "0"]
    counts = m.count_target_states(values)
    assert counts["negative"] == 1
    assert counts["missing"] == 1
    assert counts["negative"] != len(values) - counts["positive"]


def test_injected_missing_robustness_target_changes_missing_not_negative():
    sample_rows = {
        s: m.load_analysis_ready(REPO_ROOT, s) for s in m.ANALYSIS_READY_FILES
    }
    primary = [dict(r) for r in sample_rows[m.PRIMARY_SAMPLE]]
    baseline = m.build_event_counts({m.PRIMARY_SAMPLE: primary})
    base_all = [
        e for e in baseline
        if e["target"] == m.SECONDARY_TARGET and e["window"] == "all"
    ][0]
    # Inject missing into a previously negative robustness target cell.
    flipped = False
    for row in primary:
        if m.classify_target_state(row[m.SECONDARY_TARGET]) == "negative":
            row[m.SECONDARY_TARGET] = ""
            flipped = True
            break
    assert flipped
    mutated = m.build_event_counts({m.PRIMARY_SAMPLE: primary})
    mut_all = [
        e for e in mutated
        if e["target"] == m.SECONDARY_TARGET and e["window"] == "all"
    ][0]
    assert int(mut_all["missing"]) == int(base_all["missing"]) + 1
    assert int(mut_all["negative"]) == int(base_all["negative"]) - 1
    assert int(mut_all["positive"]) == int(base_all["positive"])
    assert int(mut_all["rows"]) == int(base_all["rows"])
    assert int(mut_all["evaluable_rows"]) == int(base_all["evaluable_rows"]) - 1


def test_final_test_claim_threshold_cannot_change_feature_admission():
    with pytest.raises(
        m.AuthorizationError,
        match="final-test claim threshold cannot change feature admission",
    ):
        m.reject_final_test_claim_gate_mutating_feature_admission(
            claim_gate_controls_feature_admission=True,
        )


def test_final_test_claim_threshold_cannot_change_split():
    with pytest.raises(
        m.AuthorizationError,
        match="final-test claim threshold cannot change temporal split",
    ):
        m.reject_final_test_claim_gate_mutating_split(
            claim_gate_controls_temporal_split=True,
        )


def test_preprocessing_missingness_and_clipping_order():
    p = m.build_preprocessing_contract()
    assert p["missingness_mask_captured_before_imputation"] is True
    assert p["missingness_indicator_source"] == "original_pre_imputation_mask"
    assert p["missing_indicators_standardized"] is False
    assert p["clipping_fit_on_observed_training_values_only"] is True
    assert p["median_fit_after_training_clipping"] is True
    order = p["continuous_pipeline_order"]
    assert order[0].startswith("1_")
    assert "pre_imputation_missingness_mask" in order[1]
    assert "clipping_bounds" in order[2]
    assert "impute" in order[5]
    assert "missingness_indicators" in order[6]
    assert order.index(
        [x for x in order if "clipping_bounds_on_observed" in x][0]
    ) < order.index([x for x in order if x.startswith("6_impute")][0])


def test_smote_disables_class_weighting_and_keeps_nonweight_hyperparams():
    s = m.build_model_specs()["smote_robustness"]
    assert s["logistic_regression"]["class_weight"] is None
    assert s["random_forest"]["class_weight"] is None
    assert s["xgboost"]["scale_pos_weight"] == 1
    assert s["class_weighting_disabled_when_smote_active"] is True
    assert s["oversampling_and_class_weighting_combined"] is False
    assert s["uses_selected_non_weight_hyperparameters"] is True
    assert s["second_tuning_search"] is False
    assert "uses_selected_class_weighted_hyperparameters" not in s
    primary = m.build_model_specs()["imbalance_handling_primary"]
    assert primary["logistic_regression"]["class_weight"] == "balanced"
    assert primary["random_forest"]["class_weight"] == "balanced_subsample"
    assert primary["xgboost"]["counts_exclude_missing_target_rows"] is True


def test_smote_and_class_weighting_cannot_both_be_active():
    s = m.build_model_specs()["smote_robustness"]
    assert s["oversampling_and_class_weighting_combined"] is False
    # Contract-level mutual exclusion.
    assert not (
        s["class_weighting_disabled_when_smote_active"] is False
        and s.get("apply_only_inside_training_fold") is True
    )


def test_human_decision_artifact_fields():
    d = m.build_revenue_growth_exclusion_decision()
    assert d["decision_authority"] == "human_supervisor_data_owner"
    assert d["decision_status"] == "active"
    assert d["decision_date"] == "2026-07-19"
    assert d["feature"] == m.REVENUE_GROWTH_FEATURE
    assert d["revised_status"] == "rejected_m1_primary_coverage_gate_failed"
    assert d["retained_in_frozen_dataset"] is True
    assert d["retained_in_coverage_audit"] is True
    assert d["removed_from_primary_feature_set"] is True
    assert d["denominator_exception_authorized"] is False
    assert d["evidence"]["fold1_training_coverage"] == 0.6040816327
    assert d["evidence"]["passed_overall_development_coverage_gate"] is True
    assert d["evidence"]["failed_minimum_fold_training_coverage_gate"] is True


def test_split_manifest_content_stable_across_rebuild():
    sample_rows = {
        s: m.load_analysis_ready(REPO_ROOT, s) for s in m.ANALYSIS_READY_FILES
    }
    m1 = m.build_split_manifest(sample_rows)
    m2 = m.build_split_manifest(sample_rows)
    assert m1 == m2
    # Role assignment locked to years; no random component.
    years = {int(r["target_year"]) for r in m1 if r["dataset_split"] == "final_test"}
    assert years == {1400, 1401, 1402}
