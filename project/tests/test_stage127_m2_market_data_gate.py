"""Tests for Stage127 — M2 market-data admission Gate (development-only).

No model is fit and no final-test row is read by this module.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import date

import pytest

from src import stage127_m2_market_data_gate as g

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(REAL_ROOT)
STAGE127 = os.path.join(REAL_ROOT, "stage127")

DECISION_PATH = os.path.join(STAGE127, "stage127_m2_market_data_gate_decision.json")
FEATURES_PATH = os.path.join(STAGE127, "stage127_m2_development_features.csv")
QC_PATH = os.path.join(STAGE127, "stage127_m2_gate_qc_report.json")
AUTH_PATH = os.path.join(
    STAGE127, "stage127_m2_market_data_gate_human_authorization_record.json")
MANIFEST_PATH = os.path.join(STAGE127, "stage127_m2_source_manifest.json")


@pytest.fixture(scope="module")
def decision():
    with open(DECISION_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def features():
    with open(FEATURES_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def qc():
    with open(QC_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def auth():
    with open(AUTH_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Frozen three-variable block / formula identity
# --------------------------------------------------------------------------- #

def test_m2_block_is_exactly_the_three_frozen_variables(decision):
    assert decision["m2_block_variable_count"] == 3
    assert decision["m2_block_variables"] == [
        "equity_return_window", "realized_volatility", "amihud_illiquidity",
    ]
    assert decision["m2_block"] == "M2_BLOCK"


def test_candidate_ids_and_formula_ids_match_canonical_contract(decision):
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    assert canonical["option_id"] == decision["formula_contract_option_id"]
    for cand in decision["candidates"]:
        cv = canonical["variables"][cand["variable"]]
        assert cand["candidate_id"] == cv["candidate_id"]
        assert cand["formula_id"] == cv["formula_id"]


def test_no_extra_market_variable_was_added(decision):
    forbidden = {
        "beta", "market_return", "turnover", "volume", "price_momentum",
        "momentum", "liquidity_proxy",
    }
    assert not (set(decision["m2_block_variables"]) & forbidden)


def test_block_not_silently_redefined_on_candidate_failure(decision):
    assert decision["no_variable_dropped_from_frozen_block"] is True
    assert decision["block_not_redefined_on_candidate_failure"] is True
    assert decision["block_redefinition_requires_separate_human_decision"] is True


# --------------------------------------------------------------------------- #
# Shared window / strict point-in-time rule
# --------------------------------------------------------------------------- #

def test_shared_window_is_12_calendar_months_for_all_variables():
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    sw = canonical["shared_window"]
    assert sw["applies_to_all_m2_variables"] is True
    assert sw["length"] == "12_calendar_months"
    assert g.SHARED_WINDOW_CALENDAR_MONTHS == 12
    assert sw["market_observation_end_predicate"] == (
        "market_observation_date < pair_cutoff_date")


def test_window_end_is_strictly_before_pair_cutoff(features):
    for row in features:
        cutoff = date.fromisoformat(row["pair_cutoff_date"])
        for col in ("window_t_star", "window_last_trading_date"):
            if row[col]:
                assert date.fromisoformat(row[col]) < cutoff, (
                    f"{col} must be strictly before the pair cutoff: {row}")


def test_window_is_exactly_twelve_calendar_months_ending_at_t_star(features):
    """W is recomputed from the frozen contract, not from the retrieval range."""
    for row in features:
        if not row["window_t_star"]:
            continue
        t_star = date.fromisoformat(row["window_t_star"])
        start = date.fromisoformat(row["window_start_calendar_date"])
        assert start == g.minus_calendar_months(t_star, 12)
        first = date.fromisoformat(row["window_first_trading_date"])
        last = date.fromisoformat(row["window_last_trading_date"])
        assert start <= first <= last == t_star


def test_retrieval_buffer_never_enters_the_scientific_window(decision):
    assert decision["retrieval_range_used_as_scientific_window"] is False
    assert decision["retrieval_buffer_days_entered_scientific_window"] is False
    assert decision["pair_specific_window_recomputed_from_frozen_contract"] is True


def test_same_day_cutoff_observation_is_never_accepted(decision):
    assert decision["join_leakage_audit"]["accepted_post_cutoff_observations"] == 0
    assert decision["candidates"][0]["G04_timing_verified"][
        "accepted_same_calendar_day_as_cutoff"] == 0


# --------------------------------------------------------------------------- #
# Thresholds must never be weakened
# --------------------------------------------------------------------------- #

def test_minimum_observation_thresholds_are_126():
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    assert g.MIN_VALID_RETURN_OBSERVATIONS == 126
    assert g.MIN_VALID_AMIHUD_OBSERVATIONS == 126
    assert canonical["minimum_valid_daily_return_observations"] == 126
    assert canonical["minimum_valid_amihud_observations"] == 126
    assert canonical["threshold_reduction_allowed"] is False


def test_no_imputation_scaling_or_extrapolation_allowed():
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    assert canonical["imputation_allowed"] is False
    assert canonical["scaling_or_extrapolation_allowed"] is False
    assert "not_annualized" in (
        canonical["variables"]["realized_volatility"]["transform"])


def test_adjusted_close_is_required_and_not_substituted(decision):
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    assert canonical["price_field"]["name"] == "adjusted_close"
    assert g.PRICE_FIELD == "adjusted_close"
    for cand in decision["candidates"]:
        assert cand["G05_extraction_quality_controlled"][
            "required_price_field"] == "adjusted_close"


def test_amihud_uses_traded_value_rial_and_excludes_nonpositive(decision):
    canonical = json.load(open(
        os.path.join(REPO_ROOT, g.M2_FORMULA_CONTRACT_REL), encoding="utf-8"))
    av = canonical["variables"]["amihud_illiquidity"]
    assert av["volume_field"] == "traded_value_rial"
    assert av["zero_volume_rule"] == "exclude_day_never_impute"
    assert g.VOLUME_FIELD == "traded_value_rial"


def test_required_diagnostics_present_in_feature_table(features):
    for col in ("missing_price_day_count", "zero_traded_value_day_count",
                "usable_daily_return_count", "usable_amihud_day_count"):
        assert col in features[0]


# --------------------------------------------------------------------------- #
# Accessibility scoring — fail-closed, never 0-2 without evidence
# --------------------------------------------------------------------------- #

def test_no_numeric_score_without_candidate_level_evidence():
    result = g.score_accessibility_from_evidence(
        {"candidate_level_endpoint_evidence": False})
    assert result["resolution"] == "UNRESOLVED"
    assert result["accessibility_score"] is None


def test_unreached_source_is_never_scored_zero_to_two(decision):
    for cand in decision["candidates"]:
        score = cand["G01_accessibility"]["accessibility_score"]
        assert score is None or score >= 3, (
            "scoring 0-2 asserts an observed hard-drop property of the source"
        )


def test_candidate_level_evidence_yields_a_derived_numeric_score():
    full = g.score_accessibility_from_evidence({
        "candidate_level_endpoint_evidence": True,
        "documented_api_or_portal": True,
        "reproducible_retrieval_with_provenance": True,
        "authoritative_source": True,
        "machine_readable_or_reliably_structured": True,
    })
    assert full["resolution"] == "PASS"
    assert full["accessibility_score"] == 5
    unstructured = g.score_accessibility_from_evidence({
        "candidate_level_endpoint_evidence": True,
        "documented_api_or_portal": True,
        "reproducible_retrieval_with_provenance": True,
        "authoritative_source": False,
        "machine_readable_or_reliably_structured": False,
    })
    assert unstructured["accessibility_score"] == 4
    weak = g.score_accessibility_from_evidence({
        "candidate_level_endpoint_evidence": True,
        "reproducible_retrieval_with_provenance": False,
    })
    assert weak["accessibility_score"] == 3


def test_score_three_is_not_automatic_admission():
    mapping = json.load(open(
        os.path.join(REPO_ROOT, g.RUBRIC_MAPPING_REL), encoding="utf-8"))
    assert mapping["operational_mapping"]["3"]["pilot_permission_only"] is True
    assert mapping["missing_evidence_rule"] == "null_or_unresolved_never_zero"
    assert mapping["source_origin_probe_alone_insufficient_for_numeric_score"] is True


# --------------------------------------------------------------------------- #
# Coverage thresholds — 0.80 candidate / 0.70 block, from the SAP
# --------------------------------------------------------------------------- #

def test_coverage_thresholds_match_canonical_sap():
    sap = json.load(open(os.path.join(REPO_ROOT, g.SAP_REL), encoding="utf-8"))
    cda = sap["candidate_data_admission"]
    assert g.CANDIDATE_VALID_COVERAGE_MIN == cda["candidate_valid_coverage_min"]
    assert g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN == cda["block_common_sample_coverage_min"]
    assert cda["replaces_pilot_G09_G14_for_modeling_path"] is True
    assert cda["final_test_predictor_inspection_for_admission"] is False


def test_event_threshold_matches_canonical_sap():
    sap = json.load(open(os.path.join(REPO_ROOT, g.SAP_REL), encoding="utf-8"))
    f = sap["development_model_comparison_feasibility"]
    assert g.MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW == (
        f["min_positive_evaluable_each_temporal_validation_window"])
    assert f["requires_both_locked_validation_windows"] is True


def test_coverage_denominator_is_the_full_development_subset(decision):
    for var in decision["candidate_coverage"]:
        assert decision["candidate_coverage"][var][
            "total_development_rows"] == g.EXPECTED_DEV_PAIRS


def test_observed_coverage_is_reported_with_an_observed_numerator(decision):
    for var, cov in decision["candidate_coverage"].items():
        assert cov["resolution"] == "PASS", var
        assert cov["valid_rows"] is not None
        assert cov["total_development_rows"] == g.EXPECTED_DEV_PAIRS
        assert cov["coverage_gate_passed"] is not None
        assert cov["valid_rows"] + cov["missing_or_unresolved_rows"] == (
            cov["total_development_rows"])


def test_unresolved_numerator_differs_from_observed_zero():
    pairs = g.load_development_pairs(REPO_ROOT)
    unresolved = g.candidate_coverage(pairs, None)
    observed_zero = g.candidate_coverage(pairs, set())
    assert unresolved["overall_coverage"] is None
    assert observed_zero["overall_coverage"] == 0.0
    assert unresolved["coverage_gate_passed"] is None
    assert observed_zero["coverage_gate_passed"] is False


def test_common_sample_requires_all_three_variables(decision):
    cs = decision["block_common_sample"]
    assert cs["requires_all_three_m2_variables_simultaneously_usable"] is True
    assert cs["threshold"] == 0.70
    assert cs["resolution"] == "PASS"
    assert cs["common_coverage_gate_passed"] is not None
    # The common sample can never exceed the weakest single-variable numerator.
    assert cs["common_usable_rows"] <= min(
        c["valid_rows"] for c in decision["candidate_coverage"].values())


def test_coverage_gate_passes_only_at_or_above_threshold():
    pairs = g.load_development_pairs(REPO_ROOT)
    all_keys = {(p["ticker"], p["fiscal_year_t"]) for p in pairs}
    full = g.candidate_coverage(pairs, all_keys)
    assert full["overall_coverage"] == 1.0
    assert full["coverage_gate_passed"] is True

    few = set(list(all_keys)[:100])  # 100/666 = 0.15 -> below 0.80
    low = g.candidate_coverage(pairs, few)
    assert low["coverage_gate_passed"] is False


# --------------------------------------------------------------------------- #
# Event-count feasibility — never fabricated, never asserted without evidence
# --------------------------------------------------------------------------- #

def test_event_feasibility_is_observed_and_needs_no_model(decision):
    f = decision["event_count_feasibility"]
    assert f["resolution"] == "PASS"
    assert f["sap_label_asserted"] in (
        "development_comparison_feasibility_met",
        "development_comparison_not_supported",
    )
    assert f["no_model_was_fit_to_assess_this"] is True
    # Negative counts are descriptive only: no minimum-negative rule exists.
    assert set(f["m2_common_sample_negative_counts"]) == {
        "fold1_validation", "fold2_validation"}


def test_event_feasibility_uses_both_validation_windows():
    pairs = g.load_development_pairs(REPO_ROOT)
    all_keys = {(p["ticker"], p["fiscal_year_t"]) for p in pairs}
    f = g.event_count_feasibility(pairs, all_keys)
    # On the full development sample both windows clear the >=5 rule.
    assert f["m2_common_sample_positive_counts"]["fold1_validation"] == 25
    assert f["m2_common_sample_positive_counts"]["fold2_validation"] == 10
    assert f["sap_label_asserted"] == "development_comparison_feasibility_met"

    # Starving ONE window must flip the conjunction to not_supported.
    starved = {
        (p["ticker"], p["fiscal_year_t"]) for p in pairs
        if "fold2_validation" not in p["folds"]
    }
    f2 = g.event_count_feasibility(pairs, starved)
    assert f2["m2_common_sample_positive_counts"]["fold2_validation"] == 0
    assert f2["sap_label_asserted"] == "development_comparison_not_supported"


def test_m1_reference_counts_are_labeled_as_not_the_m2_result(decision):
    f = decision["event_count_feasibility"]
    assert f["m1_reference_is_not_the_m2_result"] is True
    assert f["m1_development_reference_positive_counts"]["fold1_validation"] == 25
    assert f["m1_development_reference_positive_counts"]["fold2_validation"] == 10


# --------------------------------------------------------------------------- #
# Development-only restriction / final-test firewall
# --------------------------------------------------------------------------- #

def test_feature_table_has_exactly_the_666_development_rows(features):
    assert len(features) == g.EXPECTED_DEV_PAIRS


def test_feature_table_contains_no_final_test_row(features):
    years = {int(r["target_year"]) for r in features}
    assert years == set(g.DEVELOPMENT_TARGET_YEARS)
    assert not (years & set(g.FINAL_TEST_TARGET_YEARS))
    for r in features:
        assert r["dataset_split"] == "development"


def test_final_test_firewall_flags_all_locked(decision):
    fw = decision["final_test_firewall"]
    assert fw["final_test_locked"] is True
    assert fw["final_test_unlocked"] is False
    assert fw["final_test_access_authorized"] is False
    assert fw["final_test_predictor_values_inspected"] is False
    assert fw["final_test_target_values_inspected"] is False
    assert fw["final_test_evaluation_performed"] is False
    assert fw["final_test_coverage_used_for_admission"] is False
    assert fw["final_test_target_years_excluded"] == [1400, 1401, 1402]


def test_loader_never_returns_a_final_test_pair():
    pairs = g.load_development_pairs(REPO_ROOT)
    assert len(pairs) == g.EXPECTED_DEV_PAIRS
    for p in pairs:
        assert p["target_year"] in g.DEVELOPMENT_TARGET_YEARS


def test_join_audit_reports_zero_final_test_rows(decision):
    ja = decision["join_leakage_audit"]
    assert ja["final_test_rows_joined"] == 0
    assert ja["final_test_rows_read"] == 0


# --------------------------------------------------------------------------- #
# Join / duplicate guards
# --------------------------------------------------------------------------- #

def test_join_acceptance_criteria(decision):
    ja = decision["join_leakage_audit"]
    assert ja["duplicate_pair_key_violations"] == 0
    assert ja["accepted_post_cutoff_observations"] == 0
    assert ja["accepted_target_year_leakage_violations"] == 0
    assert ja["acceptance_criteria"]["zero_duplicate_output_pair_keys"] is True
    assert ja["matched_pair_count"] == g.EXPECTED_DEV_PAIRS


def test_no_duplicate_pair_keys_in_feature_table(features):
    keys = [(r["ticker"], r["fiscal_year_t"]) for r in features]
    assert len(keys) == len(set(keys))


def test_every_development_ticker_resolved_to_an_instrument(decision):
    ja = decision["join_leakage_audit"]
    assert ja["ticker_mapping_failures"] == 0
    assert ja["ticker_mapping_unresolved"] == 0


def test_join_targets_the_frozen_m1_design(decision):
    ja = decision["join_leakage_audit"]
    assert ja["sample"] == "main_rule_a_primary"
    assert ja["target"] == "FD_target_main_t_plus_1"
    assert ja["development_target_years"] == [1393, 1394, 1395, 1396, 1397, 1398, 1399]


# --------------------------------------------------------------------------- #
# Source discipline
# --------------------------------------------------------------------------- #

def test_only_the_authoritative_source_was_used(manifest, decision):
    assert manifest["source_id"] == "src_m2_tsetmc_market"
    assert manifest["authoritative_source_only"] is True
    assert manifest["substitute_sources_used"] == []
    assert manifest["source_universe_broadened_post_hoc"] is False
    assert decision["primary_source_id"] == "src_m2_tsetmc_market"


def test_forbidden_substitutes_are_named_and_unused(manifest):
    for forbidden in ("yahoo_finance", "kaggle", "unofficial_mirror"):
        assert forbidden in manifest["forbidden_substitute_sources_not_used"]
        assert forbidden not in manifest["substitute_sources_used"]


def test_endpoint_provenance_is_recorded_and_tsetmc_only(manifest):
    hosts = set(manifest["endpoint_hosts_observed"])
    assert hosts
    assert all(h.endswith("tsetmc.com") for h in hosts), hosts
    assert manifest["field_mapping_verified"] is True
    assert manifest["field_mapping_verified_rows"] > 0


def test_gate_is_reproducible_without_network(manifest, decision):
    assert manifest["network_required_to_reproduce_gate"] is False
    assert manifest["execution_environment"][
        "network_egress_used_for_this_gate"] is False
    assert decision["network_required_to_reproduce"] is False
    assert decision["gate_decided_from_endpoint_reachability"] is False
    assert decision["evidence_mode"] == g.EVIDENCE_MODE_IMPORTED_BUNDLE


# --------------------------------------------------------------------------- #
# No modeling
# --------------------------------------------------------------------------- #

def test_no_modeling_was_performed(decision):
    assert decision["modeling_performed"] is False
    assert decision["model_fit_calls"] == 0
    assert decision["prediction_calls"] == 0
    assert decision["m2_vs_m1_performance_compared"] is False


def test_gate_does_not_answer_the_performance_question(decision):
    assert decision["does_not_answer"] == "Does M2 improve prediction?"


def test_module_contains_no_estimator_import():
    src = open(
        os.path.join(REAL_ROOT, "src", "stage127_m2_market_data_gate.py"),
        encoding="utf-8").read()
    for banned in ("sklearn", "xgboost", "LogisticRegression",
                   "RandomForest", ".fit(", "predict_proba"):
        assert banned not in src


# --------------------------------------------------------------------------- #
# Gate status / next-action gating
# --------------------------------------------------------------------------- #

def test_gate_status_is_recognised_and_blockers_are_explicit(decision):
    assert decision["gate_status"] in (
        "PASS_FOR_M2_INCREMENTAL_EVALUATION",
        "FAIL_M2_DATA_GATE",
        "UNRESOLVED_M2_DATA_GATE",
    )
    if decision["gate_status"] != "PASS_FOR_M2_INCREMENTAL_EVALUATION":
        assert len(decision["blocker_reasons"]) >= 1
    else:
        assert decision["blocker_reasons"] == []


def test_observed_failure_is_not_softened_into_unresolved(decision):
    """A threshold failure computed from observed evidence must read FAIL."""
    cond = decision["gate_decision_conditions"]
    observed = [b for b in decision["blocker_reasons"] if "observed" in b]
    if observed:
        assert decision["gate_status"] == "FAIL_M2_DATA_GATE"
        assert not all(cond.values())


def test_pass_requires_the_full_conjunction(decision):
    cond = decision["gate_decision_conditions"]
    assert set(cond) == {
        "A_data_admission_g01_g08",
        "B_each_candidate_coverage_ge_0_80",
        "C_common_sample_coverage_ge_0_70",
        "D_both_validation_windows_ge_5_positives",
        "E_no_pit_leakage_join_provenance_blocker",
        "F_all_three_frozen_m2_variables_present",
    }
    assert (decision["gate_status"] == "PASS_FOR_M2_INCREMENTAL_EVALUATION") == (
        all(cond.values()))


def test_eligibility_tracks_the_gate_status_exactly(decision):
    e = decision["eligibility_for_next_action"]
    assert e["requires_data_admission_pass"] is True
    assert e["requires_development_comparison_feasibility_pass"] is True
    assert e["eligible_to_start_m2_incremental_evaluation"] == (
        decision["gate_status"] == "PASS_FOR_M2_INCREMENTAL_EVALUATION")


def test_pass_status_requires_every_requirement(decision):
    # A PASS must never be emitted while any blocker exists.
    if decision["blocker_reasons"]:
        assert decision["gate_status"] != "PASS_FOR_M2_INCREMENTAL_EVALUATION"


# --------------------------------------------------------------------------- #
# Authorization scope
# --------------------------------------------------------------------------- #

def test_authorization_provenance_is_truthful(auth):
    assert auth["human_source_utterance"] == "خوب بریم مرحله بعدی"
    assert hashlib.sha256(
        auth["human_source_utterance"].encode("utf-8")
    ).hexdigest() == auth["human_source_utterance_sha256"]
    assert auth["resolved_authorized_action_id"] == "stage127-m2-market-data-gate"
    assert auth["normalized_authorization_scope_is_derived_not_verbatim_human_text"] is True
    assert hashlib.sha256(
        auth["normalized_authorization_scope"].encode("utf-8")
    ).hexdigest() == auth["normalized_authorization_scope_sha256"]
    assert auth["human_source_utterance_sha256"] != auth[
        "normalized_authorization_scope_sha256"]


def test_authorization_does_not_extend_beyond_this_gate(auth):
    assert auth["scope_limited_to_this_action_only"] is True
    assert auth["standing_authorization"] is False
    assert auth["m2_incremental_evaluation_authorized"] is False
    assert auth["merge_authorized"] is False
    for excluded in ("stage127-m2-incremental-evaluation",
                     "any_model_fitting_or_prediction", "shap",
                     "final_test_predictor_access", "m3_work", "m4_work",
                     "merge"):
        assert excluded in auth["does_not_extend_to"]


def test_authorization_permits_retrieval_for_this_gate_only(auth):
    assert auth["permits_real_m2_source_retrieval_for_this_gate_only"] is True


# --------------------------------------------------------------------------- #
# Determinism / QC
# --------------------------------------------------------------------------- #

def test_qc_report_all_pass(qc):
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 10


def test_feature_computation_is_deterministic():
    obs = [
        {"trading_date": f"2016-{m:02d}-{d:02d}", "range_id": "R",
         "adjusted_close": 1000.0 + i, "adjusted_close_status": "OK",
         "traded_value_rial": 1_000_000.0}
        for i, (m, d) in enumerate(
            (m, d) for m in range(1, 13) for d in range(1, 21))
    ]
    a = g.compute_pair_features("2017-01-01", obs)
    b = g.compute_pair_features("2017-01-01", obs)
    assert a == b


def test_m2_incremental_evaluation_remains_unauthorized(decision):
    e = decision["eligibility_for_next_action"]
    assert e["m2_incremental_evaluation_authorized"] is False
    assert e["m2_modeling_started"] is False
    assert e["eligibility_is_not_authorization"] is True
    assert e["next_action_id"] == g.NEXT_GATED_ACTION_ID


def test_canonical_source_hashes_verify_on_disk(decision):
    for rel, expected in decision["canonical_sources_sha256"].items():
        path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(path), rel
        assert g.sha256_file(path) == expected, rel
