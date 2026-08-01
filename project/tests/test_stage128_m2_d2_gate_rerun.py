"""Fail-closed tests for the Stage128 canonical M2 Gate re-run under D2.

Every test here uses either synthetic in-memory windows or the already-written
Stage128 package artifacts. No model is fit, no prediction is produced, and no
final-test row is read.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
from datetime import date

import pytest

from src import stage127_m2_market_data_gate as g
from src import stage128_m2_d2_boundary_month_equity_return as d2
from src import stage128_m2_d2_gate_rerun as r

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
STAGE128 = os.path.join(REPO_ROOT, "project", "stage128")

DECISION_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_gate_rerun_decision.json")
AUTH_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_gate_rerun_human_authorization_record.json")
QC_PATH = os.path.join(STAGE128, "stage128_m2_d2_gate_rerun_qc_report.json")
META_PATH = os.path.join(
    STAGE128, "metadata_and_hashes_stage128_m2_d2_gate_rerun.json")
INTEGRITY_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_gate_rerun_bundle_integrity.json")
FEATURES_PATH = os.path.join(
    STAGE128, "stage128_m2_d2_development_features.csv")

RERUN_SRC = os.path.join(
    REPO_ROOT, "project", "src", "stage128_m2_d2_gate_rerun.py")
RERUN_RUNNER = os.path.join(
    REPO_ROOT, "project", "run_stage128_m2_d2_gate_rerun.py")

#: The verbatim authorization and its expected digest.
AUTHORIZATION_TEXT = (
    "من اجرای علمی stage128-m2-d2-gate-rerun را، فقط در محدوده canonical M2 "
    "Gate با Gregorian D2 فریز‌شده، مجاز می‌کنم."
)
AUTHORIZATION_SHA256 = (
    "8abbeac68868b859cc3a9fcda893af8f80eaf7d1f5c9471135bbeb4537ee9e95"
)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _package_present() -> bool:
    return os.path.isfile(DECISION_PATH)


requires_package = pytest.mark.skipif(
    not _package_present(),
    reason="Stage128 D2 Gate re-run package not built in this checkout",
)


@pytest.fixture(scope="module")
def decision():
    return _load(DECISION_PATH)


@pytest.fixture(scope="module")
def auth():
    return _load(AUTH_PATH)


@pytest.fixture(scope="module")
def qc():
    return _load(QC_PATH)


# --------------------------------------------------------------------------- #
# Synthetic windows — Gregorian boundary-month semantics
# --------------------------------------------------------------------------- #

def _obs(day: str, price, value: float = 1000.0) -> dict:
    return {
        "trading_date": day,
        "adjusted_close": price,
        "traded_value_rial": value,
        # Adjacency is evaluated by the frozen Stage127 daily_simple_returns,
        # which requires the retrieval-range identity of each observation.
        "range_id": "R1",
    }


def _window_with_daily_returns(n_days: int, start: str = "2016-01-04") -> list:
    """A dense synthetic window with `n_days` consecutive priced weekdays."""
    out = []
    d = date.fromisoformat(start)
    while len(out) < n_days:
        if d.weekday() < 5:
            out.append(_obs(d.isoformat(), 100.0 + len(out)))
        d = date.fromordinal(d.toordinal() + 1)
    return out


def test_start_boundary_is_first_priced_day_in_t0_gregorian_month():
    win = [
        _obs("2016-03-01", None), _obs("2016-03-02", None),
        _obs("2016-03-15", 50.0), _obs("2016-03-20", 60.0),
    ]
    got = d2.find_start_boundary_price(win, "2016-03-01")
    assert got["trading_date"] == "2016-03-15"
    assert got["adjusted_close"] == 50.0


def test_end_boundary_is_last_priced_day_in_tstar_gregorian_month():
    win = [
        _obs("2017-02-03", 10.0), _obs("2017-02-20", 70.0),
        _obs("2017-02-25", None),
    ]
    got = d2.find_end_boundary_price(win, "2017-02-25")
    assert got["trading_date"] == "2017-02-20"


def test_no_cross_month_fallback_at_either_boundary():
    """A priced day in an ADJACENT month must never be selected."""
    start_win = [
        _obs("2016-03-10", None), _obs("2016-03-28", None),
        _obs("2016-04-04", 99.0),  # next month — must NOT be used
    ]
    assert d2.find_start_boundary_price(start_win, "2016-03-10") == {}

    end_win = [
        _obs("2016-02-25", 88.0),  # previous month — must NOT be used
        _obs("2016-03-02", None), _obs("2016-03-09", None),
    ]
    assert d2.find_end_boundary_price(end_win, "2016-03-09") == {}


def test_start_search_never_looks_before_t0():
    win = [_obs("2016-05-02", 10.0), _obs("2016-05-09", 20.0)]
    got = d2.find_start_boundary_price(win, "2016-05-09")
    assert got["trading_date"] == "2016-05-09"


def test_zero_start_denominator_is_rejected():
    win = _window_with_daily_returns(200)
    win[0] = _obs(win[0]["trading_date"], 0.0)
    out = d2.compute_d2_equity_return(win, 199)
    assert out["equity_return_d2"] is None
    assert "start adjusted_close is zero" in out["d2_status"]


def test_zero_end_endpoint_is_allowed():
    """A literal 0.0 at the END endpoint is valid under inherited semantics."""
    win = _window_with_daily_returns(200)
    win[-1] = _obs(win[-1]["trading_date"], 0.0)
    out = d2.compute_d2_equity_return(win, 199)
    assert out["equity_return_d2"] == pytest.approx(-1.0)
    assert out["d2_status"] == "OBSERVED_COMPLETE"


def test_below_126_usable_returns_stays_unavailable():
    win = _window_with_daily_returns(200)
    out = d2.compute_d2_equity_return(win, 125)
    assert out["equity_return_d2"] is None
    assert "125 < 126" in out["d2_status"]
    assert d2.compute_d2_equity_return(win, 126)["equity_return_d2"] is not None


def test_126_floor_constant_matches_frozen_stage127():
    assert d2.MIN_USABLE_DAILY_RETURNS_D2 == g.MIN_VALID_RETURN_OBSERVATIONS


# --------------------------------------------------------------------------- #
# The re-run reuses the frozen Stage127 primitives, unmodified
# --------------------------------------------------------------------------- #

def _synthetic_observations(n: int = 300) -> list:
    return _window_with_daily_returns(n, start="2015-06-01")


def test_same_window_tstar_and_adjacency_as_stage127():
    obs = _synthetic_observations()
    cutoff = "2016-06-01"
    base = g.compute_pair_features(cutoff, obs)
    got = r.compute_pair_features_d2(cutoff, obs)
    for key in (
        "t_star", "window_start_calendar_date", "window_first_trading_date",
        "window_last_trading_date", "window_trading_day_count",
        "t0_trading_date", "tN_trading_date", "usable_daily_return_count",
        "usable_amihud_day_count", "missing_price_day_count",
        "zero_traded_value_day_count", "fewer_than_126_valid_returns",
        "fewer_than_126_amihud_days",
    ):
        assert got[key] == base[key], key


def test_realized_volatility_and_amihud_are_untouched():
    obs = _synthetic_observations()
    cutoff = "2016-06-01"
    base = g.compute_pair_features(cutoff, obs)
    got = r.compute_pair_features_d2(cutoff, obs)
    assert got["realized_volatility"] == base["realized_volatility"]
    assert got["amihud_illiquidity"] == base["amihud_illiquidity"]


def test_only_the_equity_return_slot_is_replaced():
    obs = _synthetic_observations()
    cutoff = "2016-06-01"
    base = g.compute_pair_features(cutoff, obs)
    got = r.compute_pair_features_d2(cutoff, obs)
    changed = {
        k for k in base
        if k in got and got[k] != base[k]
    }
    assert changed <= {"equity_return_window"}
    # The historical D0 value is preserved alongside, never discarded.
    assert got["equity_return_window_d0_historical"] == base[
        "equity_return_window"]


# --------------------------------------------------------------------------- #
# No modeling / no final-test access in the execution path
# --------------------------------------------------------------------------- #

_FORBIDDEN_CALL_NAMES = {
    "fit", "predict", "predict_proba", "fit_transform", "partial_fit",
    "roc_auc_score", "average_precision_score", "brier_score_loss",
    "train_test_split", "cross_val_score", "LogisticRegression",
    "RandomForestClassifier", "XGBClassifier", "SMOTE",
}


def _called_names(path: str) -> set[str]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                names.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                names.add(fn.attr)
    return names


@pytest.mark.parametrize("path", [RERUN_SRC, RERUN_RUNNER])
def test_no_model_or_prediction_call_in_gate_path(path):
    assert not (_called_names(path) & _FORBIDDEN_CALL_NAMES)


@pytest.mark.parametrize("path", [RERUN_SRC, RERUN_RUNNER])
def test_gate_path_imports_no_modeling_library(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert not (modules & {
        "sklearn", "xgboost", "lightgbm", "imblearn", "shap", "statsmodels",
    })


def test_final_test_target_years_are_structurally_excluded():
    assert g.FINAL_TEST_TARGET_YEARS == (1400, 1401, 1402)
    pairs = g.load_development_pairs(REPO_ROOT)
    assert len(pairs) == 666
    assert all(p["target_year"] in g.DEVELOPMENT_TARGET_YEARS for p in pairs)
    assert not any(
        p["target_year"] in g.FINAL_TEST_TARGET_YEARS for p in pairs
    )


# --------------------------------------------------------------------------- #
# Authorization is one-action-only
# --------------------------------------------------------------------------- #

def test_authorization_text_hash_is_exact():
    assert hashlib.sha256(
        AUTHORIZATION_TEXT.encode("utf-8")).hexdigest() == AUTHORIZATION_SHA256


@requires_package
def test_recorded_authorization_is_verbatim_and_one_action_only(auth):
    assert auth["human_source_utterance"] == AUTHORIZATION_TEXT
    assert auth["human_source_utterance_sha256"] == AUTHORIZATION_SHA256
    assert hashlib.sha256(
        auth["human_source_utterance"].encode("utf-8")).hexdigest() == (
        AUTHORIZATION_SHA256
    )
    assert auth["authorization_class"] == "ORIGINAL_SCIENTIFIC_AUTHORIZATION"
    assert auth["authorized_action_id"] == "stage128-m2-d2-gate-rerun"
    assert auth["authorizing_role"] == "human_supervisor_data_owner"
    assert auth["one_action_only"] is True
    assert auth["standing_authorization"] is False
    assert auth["non_transitive"] is True
    assert auth["authorization_consumed_by_this_execution"] is True


@requires_package
def test_authorization_grants_nothing_further(auth):
    for field in (
        "merge_authorized", "m2_incremental_evaluation_authorized",
        "model_fitting_authorized", "prediction_authorized",
        "hyperparameter_tuning_authorized", "feature_search_authorized",
        "design_search_authorized", "threshold_tuning_authorized",
        "final_test_access_authorized", "m3_authorized", "m4_authorized",
        "full_development_refit_authorized", "winner_selection_authorized",
        "shap_authorized", "calibration_evaluation_authorized",
        "bootstrap_holm_predictive_inference_authorized",
    ):
        assert auth[field] is False, field
    assert auth[
        "normalized_authorization_scope_is_derived_not_verbatim_human_text"
    ] is True
    assert auth["normalized_scope_never_replaces_original_text"] is True


# --------------------------------------------------------------------------- #
# Executed package: evidence integrity and frozen invariants
# --------------------------------------------------------------------------- #

@requires_package
def test_bundle_sha_matches_immutable_evidence(decision):
    integrity = _load(INTEGRITY_PATH)
    expected = "d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec"
    assert decision["external_delivery"]["bundle_sha256"] == expected
    assert integrity["bundle_sha256_matches_expected_immutable_evidence"] is True
    assert integrity["bundle_filename"] == (
        "stage127_m2_tsetmc_full_delivery.zip")
    assert decision["external_delivery"]["normalized_row_count"] == 163_230
    assert decision["external_delivery"]["mapping_rows"] == 110
    assert decision["external_delivery"]["manifest_rows"] == 111
    assert decision["external_delivery"]["restricted_raw_file_count"] == 222
    for field in (
        "fresher_dataset_retrieved", "requested_period_widened",
        "partial_ranges_replaced", "data_backfilled",
        "alternative_market_data_source_used",
    ):
        assert decision["external_delivery"][field] is False, field


def test_bundle_sha_mismatch_fails_closed():
    """A wrong-SHA bundle must be rejected before any scientific execution."""
    from src import stage127_m2_external_delivery_import as imp
    with pytest.raises(Exception):
        with imp.ExternalDelivery(__file__):
            pass


@requires_package
def test_gate_thresholds_unchanged(decision):
    assert decision["gate_thresholds_changed"] is False
    assert decision["threshold_reduced"] is False
    assert decision["fold_specific_coverage_threshold_added"] is False
    for var, _, _ in g.M2_VARIABLES:
        assert decision["candidate_coverage"][var]["threshold"] == 0.80
    assert decision["block_common_sample"]["threshold"] == 0.70
    assert decision["event_count_feasibility"]["threshold"] == 5
    assert g.CANDIDATE_VALID_COVERAGE_MIN == 0.80
    assert g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN == 0.70
    assert g.MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW == 5


@requires_package
def test_gate_conditions_are_exactly_a_to_f(decision):
    assert set(decision["gate_decision_conditions"]) == {
        "A_data_admission_g01_g08",
        "B_each_candidate_coverage_ge_0_80",
        "C_common_sample_coverage_ge_0_70",
        "D_both_validation_windows_ge_5_positives",
        "E_no_pit_leakage_join_provenance_blocker",
        "F_all_three_frozen_m2_variables_present",
    }
    assert decision["gate_criteria_added_or_removed"] is False


@requires_package
def test_three_variable_block_unchanged(decision):
    assert decision["m2_block_variable_count"] == 3
    assert decision["m2_block_variables"] == [v for v, _, _ in g.M2_VARIABLES]
    assert decision["zero_trade_day_ratio_added_to_primary_block"] is False
    assert decision["variable_dropped_from_frozen_block"] is False
    assert decision["realized_volatility_formula_changed"] is False
    assert decision["amihud_illiquidity_formula_changed"] is False


@requires_package
def test_frozen_construct_invariants_recorded(decision):
    for field in (
        "shared_window_W_changed", "t0_changed", "T_star_changed",
        "trading_day_sequence_changed", "daily_return_adjacency_changed",
        "imputation_or_fill_applied", "unadjusted_close_substituted",
        "synthetic_adjusted_prices_used", "annualization_applied",
        "rescaled_to_365_days",
    ):
        assert decision[field] is False, field
    assert decision["minimum_valid_return_observations"] == 126
    assert decision["minimum_valid_amihud_observations"] == 126


@requires_package
def test_historical_d0_result_preserved_and_artifacts_untouched(decision):
    assert decision["historical_d0_gate_status"] == "FAIL_M2_DATA_GATE"
    assert decision["historical_d0_artifacts_rewritten"] is False
    historical = _load(os.path.join(
        REPO_ROOT, "project", "stage127",
        "stage127_m2_market_data_gate_decision.json"))
    assert historical["gate_status"] == "FAIL_M2_DATA_GATE"
    assert historical["decision_id"] == "stage127-m2-market-data-gate"
    # The historical Gate keeps its own D0 coverage numbers.
    assert historical["candidate_coverage"]["equity_return_window"][
        "valid_rows"] == 269


@requires_package
def test_prelock_reference_is_a_cross_check_not_an_input(decision):
    x = decision["prelock_cross_check"]
    assert x["prelock_reference_used_as_gate_input"] is False
    assert x["prelock_reference_hardcoded_as_gate_outcome"] is False
    assert x["d2_specification_altered_to_force_agreement"] is False
    assert x["discrepancy_triggers_investigation_not_design_search"] is True
    # The canonical count is recomputed, not asserted from the reference.
    assert x["canonical_observed_usable"] == decision["candidate_coverage"][
        "equity_return_window"]["valid_rows"]


def test_prelock_539_is_not_hardcoded_as_the_gate_outcome():
    """539 may appear only as a labelled reference constant, never as a result."""
    src = open(RERUN_SRC, encoding="utf-8").read()
    assert "PRELOCK_D2_REFERENCE_USABLE = 539" in src
    # The only other occurrence is the docstring that explicitly states the
    # reference is NOT an input; it is never assigned to a Gate result.
    lines_with_539 = [ln for ln in src.splitlines() if "539" in ln]
    assert len(lines_with_539) == 2
    assert any("NOT an input to this Gate" in ln for ln in lines_with_539)
    assert "539" not in open(RERUN_RUNNER, encoding="utf-8").read()


@requires_package
def test_no_model_prediction_or_final_test_access_recorded(decision):
    assert decision["model_fit_calls"] == 0
    assert decision["prediction_calls"] == 0
    assert decision["modeling_performed"] is False
    assert decision["predictive_metric_computed"] is False
    assert decision["m2_vs_m1_performance_compared"] is False
    fw = decision["final_test_firewall"]
    assert fw["final_test_locked"] is True
    for field in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "final_test_coverage_used_for_admission",
    ):
        assert fw[field] is False, field
    assert fw["final_test_target_years_excluded"] == [1400, 1401, 1402]


@requires_package
def test_pass_does_not_authorize_m2_incremental_evaluation(decision):
    e = decision["eligibility_for_next_action"]
    assert e["m2_incremental_evaluation_authorized"] is False
    assert e["m2_modeling_started"] is False
    assert e["eligibility_is_not_authorization"] is True
    assert e["pointer_is_not_authorization"] is True
    assert e["next_action_id"] == "stage127-m2-incremental-evaluation"


@requires_package
def test_fail_would_not_trigger_redesign(decision):
    """Whatever the outcome, the design is not reopened by this Gate."""
    assert decision["gate_outcome_used_to_redesign_d2"] is False
    assert decision["d0_d1_d2_d3_jalali_selection_reopened"] is False
    assert decision["new_design_decision_made_in_this_action"] is False
    assert decision["block_not_redefined_on_candidate_failure"] is True
    assert decision["block_redefinition_requires_separate_human_decision"] is (
        True
    )


@requires_package
def test_post_lock_eligibility_audit_deferred_not_executed(decision):
    a = decision["post_lock_eligibility_audit"]
    assert a["executed_in_this_action"] is False
    assert a["is_a_condition_of_this_gate"] is False
    assert a["required_before_interpreting_m2_predictive_results"] is True
    assert a["smd_used_to_change_gate_status"] is False
    assert a["distress_rate_inspected_for_redesign"] is False


# --------------------------------------------------------------------------- #
# Artifacts
# --------------------------------------------------------------------------- #

@requires_package
def test_pair_level_artifact_is_target_free():
    with open(FEATURES_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 666
    header = set(rows[0])
    forbidden = {
        "target", g.PRIMARY_TARGET, "FD_target_main_t_plus_1", "distress",
        "label", "y",
    }
    assert not (header & forbidden)
    assert not any(
        "target" in c and c != "target_year" for c in header
    )
    # Auditable without any final-test join.
    for column in (
        "ticker", "fiscal_year_t", "target_year", "temporal_folds",
        "pair_cutoff_date", "t_star", "d2_start_trading_date",
        "d2_end_trading_date", "d2_status", "equity_return_d2",
        "usable_daily_return_count", "realized_volatility",
        "amihud_illiquidity", "in_three_variable_common_sample",
    ):
        assert column in header, column
    assert all(int(r_["target_year"]) in g.DEVELOPMENT_TARGET_YEARS
               for r_ in rows)


@requires_package
def test_qc_report_all_required_assertions_pass(qc):
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] == len(qc["assertions"])
    assert all(a["status"] == "PASS" for a in qc["assertions"])
    assert "REQUIRED" in qc["all_pass_semantics"]
    assert "NOT a statement about the Gate outcome" in qc["all_pass_semantics"]


@requires_package
def test_metadata_hashes_exact():
    meta = _load(META_PATH)
    for rel, expected in meta["package_artifacts_sha256"].items():
        with open(os.path.join(REPO_ROOT, rel), "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual == expected, rel
    assert meta["historical_stage127_d0_artifacts_modified"] is False
    assert meta["human_source_utterance_sha256"] == AUTHORIZATION_SHA256


@requires_package
def test_gate_result_is_terminal_and_internally_consistent(decision):
    assert decision["gate_status"] in (
        g.GATE_STATUS_PASS, g.GATE_STATUS_FAIL)
    cond = decision["gate_decision_conditions"]
    if decision["gate_status"] == g.GATE_STATUS_PASS:
        assert all(cond.values())
        assert decision["blocker_reasons"] == []
    else:
        assert not all(cond.values())
        assert decision["blocker_reasons"]


# --------------------------------------------------------------------------- #
# Authorization provenance — the recorded issue date
# --------------------------------------------------------------------------- #

#: The date on which the human supervisor issued the single Stage128 D2
#: Gate-rerun authorization. Provenance metadata only: correcting it changes
#: nothing about WHAT was authorized.
AUTHORIZATION_DATE = "2026-08-01"


@requires_package
def test_gate_rerun_authorization_date_is_exact(auth):
    assert auth["authorization_date"] == AUTHORIZATION_DATE


def test_gate_rerun_authorization_date_constant_in_runner():
    src = open(RERUN_RUNNER, encoding="utf-8").read()
    tree = ast.parse(src)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(
                node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    found[t.id] = node.value.value
    assert found.get("AUTHORIZATION_DATE") == AUTHORIZATION_DATE
    assert "2026-07-30" not in src, (
        "the Stage128 D2 Gate-rerun authorization date must not regress"
    )


@requires_package
def test_gate_rerun_authorization_utterance_and_sha_unchanged(auth):
    assert auth["human_source_utterance"] == AUTHORIZATION_TEXT
    assert auth["human_source_utterance_sha256"] == AUTHORIZATION_SHA256
    assert hashlib.sha256(
        auth["human_source_utterance"].encode("utf-8")
    ).hexdigest() == AUTHORIZATION_SHA256
    # The date correction is provenance maintenance, not a new authorization.
    assert auth["authorization_class"] == "ORIGINAL_SCIENTIFIC_AUTHORIZATION"
    assert auth["authorized_action_id"] == r.ACTION_ID
    assert auth["one_action_only"] is True
    assert auth["standing_authorization"] is False
    assert auth["authorization_consumed_by_this_execution"] is True


@requires_package
def test_qc_report_asserts_the_authorization_date(qc):
    names = {a["name"]: a for a in qc["assertions"]}
    assert names[
        "authorization_date_is_the_recorded_issue_date"]["status"] == "PASS"


# --------------------------------------------------------------------------- #
# Development target-label use — literally true, exhaustively declared
# --------------------------------------------------------------------------- #

_DECLARED_TARGET_USES = {
    "condition_d_validation_window_event_counts",
    "target_stratified_candidate_coverage",
    "common_sample_positive_negative_composition",
}


@requires_package
def test_target_use_declaration_is_literal_and_exhaustive(decision):
    tlu = decision["development_target_label_use"]
    # The Gate DOES read development labels; concealing that is the defect
    # this assertion exists to prevent.
    assert tlu["development_target_labels_accessed"] is True
    assert tlu["declared_uses_are_exhaustive"] is True
    assert {u["use_id"] for u in tlu["declared_uses"]} == _DECLARED_TARGET_USES
    assert "event-count" not in tlu["used_only_for"] or "descriptive" in tlu[
        "used_only_for"], "the statement must not claim event counts only"


@requires_package
def test_declared_target_uses_cover_every_actual_target_stratified_output(
        decision):
    """Every target-stratified value in the package has a declared use."""
    tlu = decision["development_target_label_use"]
    declared = {u["use_id"] for u in tlu["declared_uses"]}

    feas = decision["event_count_feasibility"]
    assert feas["m2_common_sample_positive_counts"]
    assert feas["m2_common_sample_negative_counts"]
    assert "condition_d_validation_window_event_counts" in declared

    for var, _, _ in g.M2_VARIABLES:
        cov = decision["candidate_coverage"][var]
        assert "positive_row_coverage" in cov
        assert "negative_row_coverage" in cov
    assert "target_stratified_candidate_coverage" in declared

    cs = decision["block_common_sample"]
    assert cs["positive_count"] is not None
    assert cs["negative_count"] is not None
    assert "common_sample_positive_negative_composition" in declared


@requires_package
def test_no_predictive_metric_or_model_action_from_targets(decision):
    tlu = decision["development_target_label_use"]
    for field in (
        "predictive_performance_computed",
        "predictive_metric_computed",
        "model_fit_on_targets",
        "prediction_generated",
        "target_based_feature_selection",
        "target_based_design_change",
        "target_based_threshold_tuning",
        "target_values_written_into_predictor_artifacts",
        "final_test_target_values_accessed",
        "final_test_predictor_values_accessed",
    ):
        assert tlu[field] is False, field
    assert decision["predictive_metric_computed"] is False
    assert decision["m2_vs_m1_performance_compared"] is False
    assert decision["modeling_performed"] is False
    assert decision["model_fit_calls"] == 0
    assert decision["prediction_calls"] == 0
    assert decision["d0_d1_d2_d3_jalali_selection_reopened"] is False
    assert decision["new_design_decision_made_in_this_action"] is False
    assert decision["gate_thresholds_changed"] is False
    assert decision["threshold_reduced"] is False


@requires_package
def test_predictor_artifact_carries_no_raw_target_column():
    with open(FEATURES_PATH, encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    forbidden = {
        "target", "y", "label", "distress", "distress_label",
        "target_label", "outcome", "event", "is_positive", "positive",
    }
    assert forbidden.isdisjoint({c.lower() for c in header})
    # `target_year` is a temporal key, not a label value.
    assert "target_year" in header


@requires_package
def test_final_test_labels_remain_untouched(decision):
    fw = decision["final_test_firewall"]
    assert fw["final_test_locked"] is True
    assert fw["final_test_unlocked"] is False
    assert fw["final_test_access_authorized"] is False
    assert fw["final_test_target_values_inspected"] is False
    assert fw["final_test_predictor_values_inspected"] is False
    assert fw["final_test_evaluation_performed"] is False
    assert fw["final_test_target_years_excluded"] == [1400, 1401, 1402]


@requires_package
def test_qc_report_replaces_the_misleading_target_use_assertion(qc):
    names = {a["name"]: a for a in qc["assertions"]}
    assert "development_targets_used_only_for_event_counts" not in names
    for name in (
        "development_target_use_limited_to_canonical_gate_"
        "descriptive_and_event_support_audits",
        "development_targets_not_used_for_prediction_design_or_tuning",
    ):
        assert names[name]["status"] == "PASS", name


@requires_package
def test_readme_states_target_use_literally():
    text = open(
        os.path.join(STAGE128, "README_STAGE128_M2_D2_GATE_RERUN.md"),
        encoding="utf-8").read()
    assert "How development target labels were used" in text
    assert "**were** read by this Gate" in text
    assert "no predictive performance metric" in text
    assert "target values accessed for predictive use = 0" not in text, (
        "the old absolute no-access phrasing is not literally true"
    )
