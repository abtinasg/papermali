#!/usr/bin/env python3
"""Runner — Stage128 canonical M2 Gate RE-RUN under the frozen Gregorian D2.

Authorized action: ``stage128-m2-d2-gate-rerun`` (one action only, consumed by
this execution).

Executes the canonical M2 data-admission Gate ONCE, offline and
deterministically, from the immutable Stage127 external TSETMC bundle, with
the equity-return slot measured under the already-frozen Stage128 D2
specification. It fits no model, produces no prediction, computes no
predictive metric, and reads no final-test row.

Usage::

    PYTHONPATH=project python project/run_stage128_m2_d2_gate_rerun.py \
        --build --bundle /path/to/stage127_m2_tsetmc_full_delivery.zip
    PYTHONPATH=project python project/run_stage128_m2_d2_gate_rerun.py \
        --check --bundle /path/to/stage127_m2_tsetmc_full_delivery.zip
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_external_delivery_import as imp  # noqa: E402
from src import stage127_m2_market_data_gate as g  # noqa: E402
from src import stage128_m2_d2_gate_rerun as r  # noqa: E402

DEFAULT_BUNDLE_ENV = "STAGE127_M2_BUNDLE"

#: The verbatim human authorization for this one scientific action.
HUMAN_SOURCE_UTTERANCE = (
    "من اجرای علمی stage128-m2-d2-gate-rerun را، فقط در محدوده canonical M2 "
    "Gate با Gregorian D2 فریز‌شده، مجاز می‌کنم."
)
HUMAN_SOURCE_UTTERANCE_SHA256 = (
    "8abbeac68868b859cc3a9fcda893af8f80eaf7d1f5c9471135bbeb4537ee9e95"
)


def _git(repo_root: str, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return ""


def csv_text(fieldnames: list[str], rows: list[dict[str, object]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def _f(value: object) -> object:
    return "" if value is None else value


def accessibility_evidence_from_import(
    import_qc: dict, mapping: dict, manifest: dict,
) -> dict:
    """Identical R-A evidence derivation as the Stage127 runner."""
    return {
        "evidence_class": "candidate_endpoint_evidence",
        "candidate_level_endpoint_evidence": bool(mapping) and bool(manifest),
        "candidate_count_with_endpoint_evidence": len(manifest),
        "authoritative_source": import_qc["source_endpoints_tsetmc_only"],
        "documented_api_or_portal": True,
        "reproducible_retrieval_with_provenance": bool(
            import_qc["restricted_raw_hash_verification_passed"]
            and import_qc["provenance_sha_agrees_with_raw_manifest"]
        ),
        "machine_readable_or_reliably_structured": True,
        "instrument_mapping_evidence_present": all(
            bool(r_.get("mapping_evidence")) for r_ in mapping.values()
        ),
        "extraction_code_delivered": True,
        "raw_responses_preserved_and_hash_verified": import_qc[
            "restricted_raw_hashes_verified"],
        "source_origin_probe_alone_used_for_scoring": False,
        "score_pre_assumed": False,
    }


def authorization_record() -> dict:
    """The dedicated, one-action-only human authorization for this Gate."""
    actual = hashlib.sha256(
        HUMAN_SOURCE_UTTERANCE.encode("utf-8")).hexdigest()
    if actual != HUMAN_SOURCE_UTTERANCE_SHA256:
        raise r.GateRerunFail(
            f"authorization utterance SHA256 {actual} != expected "
            f"{HUMAN_SOURCE_UTTERANCE_SHA256}"
        )
    return {
        "authorization_id": "stage128-m2-d2-gate-rerun-human-authorization",
        "authorized_action_id": r.ACTION_ID,
        "authorization_class": "ORIGINAL_SCIENTIFIC_AUTHORIZATION",
        "authorizing_role": "human_supervisor_data_owner",
        "authorization_date": "2026-07-30",
        "human_source_utterance": HUMAN_SOURCE_UTTERANCE,
        "human_source_utterance_sha256": HUMAN_SOURCE_UTTERANCE_SHA256,
        "human_source_utterance_language": "fa",
        "human_source_utterance_availability": "available_and_recorded_verbatim",
        "human_source_utterance_source": (
            "verbatim text of the human supervisor's authorizing message for "
            "stage128-m2-d2-gate-rerun, reproduced unmodified in "
            "human_source_utterance. No other text is part of this "
            "authorization."
        ),
        "one_action_only": True,
        "standing_authorization": False,
        "non_transitive": True,
        "authorization_consumed_by_this_execution": True,
        "scope": (
            "canonical M2 data-admission Gate ONLY, executed under the "
            "already-frozen Gregorian D2 specification"
        ),
        "normalized_authorization_scope": (
            "Authorizes exactly one execution of the canonical M2 "
            "data-admission Gate with the frozen Gregorian D2 "
            "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN equity-return "
            "measurement. It authorizes no design change, no threshold "
            "change, no modeling, no prediction, no final-test access, no "
            "merge, and no successor action."
        ),
        "normalized_authorization_scope_is_derived_not_verbatim_human_text": (
            True
        ),
        "normalized_scope_never_replaces_original_text": True,
        "merge_authorized": False,
        "m2_incremental_evaluation_authorized": False,
        "model_fitting_authorized": False,
        "prediction_authorized": False,
        "hyperparameter_tuning_authorized": False,
        "feature_search_authorized": False,
        "design_search_authorized": False,
        "threshold_tuning_authorized": False,
        "final_test_access_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "full_development_refit_authorized": False,
        "winner_selection_authorized": False,
        "shap_authorized": False,
        "calibration_evaluation_authorized": False,
        "bootstrap_holm_predictive_inference_authorized": False,
        "does_not_extend_to": [
            "merge_of_this_pr",
            "stage127-m2-incremental-evaluation",
            "m2_incremental_evaluation",
            "model_fit",
            "prediction",
            "hyperparameter_tuning_or_retuning",
            "feature_search",
            "alternative_d2_d3_jalali_design_search",
            "threshold_tuning",
            "final_test_access",
            "final_test_evaluation",
            "m3_start",
            "m4_start",
            "full_development_refit",
            "winner_selection",
            "shap_execution",
            "calibration_evaluation",
            "bootstrap_or_holm_predictive_inference",
            "manuscript_winner_claim",
        ],
        "executes_frozen_design": r.DESIGN_FREEZE_ACTION_ID,
        "design_freeze_reopened": False,
    }


def build_package(repo_root: str, bundle_path: str) -> dict[str, str]:
    """Import, revalidate, re-run the Gate, and render every artifact."""
    auth = authorization_record()

    canonical = imp.load_canonical_ranges(repo_root)
    with imp.ExternalDelivery(bundle_path) as delivery:
        import_qc, observations, mapping, manifest = imp.validate_delivery(
            delivery, canonical
        )

    evidence = accessibility_evidence_from_import(import_qc, mapping, manifest)
    result = r.build(repo_root, import_qc, observations, evidence)
    decision = result["decision"]
    pairs = result["pairs"]
    features = result["features"]
    common = result["common_sample_keys"]

    files: dict[str, str] = {
        "stage128_m2_d2_gate_rerun_human_authorization_record.json":
            g.json_dumps(auth),
        "stage128_m2_d2_gate_rerun_decision.json": g.json_dumps(decision),
        "stage128_m2_d2_gate_rerun_import_qc.json": g.json_dumps(import_qc),
    }

    # -- bundle / import integrity ------------------------------------------ #
    integrity = {
        "bundle_filename": import_qc["bundle_filename"],
        "bundle_sha256": import_qc["bundle_sha256"],
        "bundle_size_bytes": import_qc["bundle_size_bytes"],
        "expected_bundle_sha256": imp.BUNDLE_SHA256,
        "bundle_sha256_matches_expected_immutable_evidence": (
            import_qc["bundle_sha256"] == imp.BUNDLE_SHA256
        ),
        "bundle_treated_as_immutable_source_evidence": True,
        "bundle_edited_in_place": False,
        "bundle_stored_outside_repository": True,
        "bundle_identified_by_sha256_not_by_path": True,
        "same_bundle_as_historical_stage127_gate": True,
        "fresher_dataset_retrieved": False,
        "requested_period_widened": False,
        "partial_ranges_replaced": False,
        "data_backfilled": False,
        "alternative_market_data_source_used": False,
        "network_reachability_used_as_scientific_evidence": False,
        "reproducible_offline_from_bundle": True,
        "canonical_request_file": imp.CANONICAL_REQUEST_REL,
        "canonical_request_sha256": imp.CANONICAL_REQUEST_SHA256,
        "delivered_request_matches_canonical": True,
        "mapping_rows": import_qc["mapping_rows"],
        "manifest_rows": import_qc["manifest_rows"],
        "normalized_row_count": import_qc["normalized_row_count"],
        "restricted_raw_file_count": import_qc["restricted_raw_file_count"],
        "restricted_raw_hash_verification_passed": import_qc[
            "restricted_raw_hash_verification_passed"],
        "external_qc_flag_trusted": False,
        "independently_revalidated_in_papermali": True,
        "importer_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_external_delivery_import.py")),
        "stage127_gate_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_market_data_gate.py")),
        "d2_module_sha256": g.sha256_file(os.path.join(
            repo_root,
            "project/src/stage128_m2_d2_boundary_month_equity_return.py")),
        "gate_rerun_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage128_m2_d2_gate_rerun.py")),
    }
    files["stage128_m2_d2_gate_rerun_bundle_integrity.json"] = g.json_dumps(
        integrity)

    # -- pair-level D2 development features (TARGET-FREE) ------------------- #
    fold_of = {(p["ticker"], p["fiscal_year_t"]): ",".join(p["folds"])
               for p in pairs}
    feature_fields = [
        "ticker", "fiscal_year_t", "target_year", "temporal_folds",
        "pair_cutoff_date", "window_start_calendar_date",
        "window_first_trading_date", "window_last_trading_date", "t_star",
        "window_trading_day_count", "usable_daily_return_count",
        "usable_amihud_day_count", "missing_price_day_count",
        "zero_traded_value_day_count",
        "d2_start_trading_date", "d2_end_trading_date",
        "d2_effective_span_days", "d2_status", "equity_return_d2",
        "d2_no_start_boundary_price", "d2_no_end_boundary_price",
        "d2_start_adjusted_close_is_zero", "fewer_than_126_valid_returns",
        "realized_volatility", "amihud_illiquidity",
        "equity_return_window_d0_historical",
        "in_three_variable_common_sample", "m2_value_status",
    ]
    feature_rows = []
    for p in pairs:
        key = (p["ticker"], p["fiscal_year_t"])
        f = features[key]
        feature_rows.append({
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "temporal_folds": fold_of[key],
            "pair_cutoff_date": p["pair_cutoff_date"],
            "window_start_calendar_date": f["window_start_calendar_date"],
            "window_first_trading_date": f["window_first_trading_date"],
            "window_last_trading_date": f["window_last_trading_date"],
            "t_star": f["t_star"],
            "window_trading_day_count": f["window_trading_day_count"],
            "usable_daily_return_count": f["usable_daily_return_count"],
            "usable_amihud_day_count": f["usable_amihud_day_count"],
            "missing_price_day_count": f["missing_price_day_count"],
            "zero_traded_value_day_count": f["zero_traded_value_day_count"],
            "d2_start_trading_date": f["d2_start_trading_date"],
            "d2_end_trading_date": f["d2_end_trading_date"],
            "d2_effective_span_days": _f(f["d2_effective_span_days"]),
            "d2_status": f["d2_status"],
            "equity_return_d2": _f(f["equity_return_window"]),
            "d2_no_start_boundary_price": f["d2_no_start_boundary_price"],
            "d2_no_end_boundary_price": f["d2_no_end_boundary_price"],
            "d2_start_adjusted_close_is_zero": f[
                "d2_start_adjusted_close_is_zero"],
            "fewer_than_126_valid_returns": f["fewer_than_126_valid_returns"],
            "realized_volatility": _f(f["realized_volatility"]),
            "amihud_illiquidity": _f(f["amihud_illiquidity"]),
            "equity_return_window_d0_historical": _f(
                f["equity_return_window_d0_historical"]),
            "in_three_variable_common_sample": key in common,
            "m2_value_status": f["m2_value_status"],
        })
    feature_rows.sort(key=lambda x: (x["ticker"], x["fiscal_year_t"]))
    files["stage128_m2_d2_development_features.csv"] = csv_text(
        feature_fields, feature_rows)

    # -- candidate coverage audit ------------------------------------------- #
    cov_fields = [
        "variable", "candidate_id", "measurement_specification",
        "total_development_rows", "valid_rows", "missing_or_unresolved_rows",
        "overall_coverage", "threshold", "coverage_gate_passed",
        "fold1_train_coverage", "fold1_validation_coverage",
        "fold2_train_coverage", "fold2_validation_coverage",
        "positive_row_coverage", "negative_row_coverage", "resolution",
    ]
    cov_rows = []
    for var, cid, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        cov_rows.append({
            "variable": var,
            "candidate_id": cid,
            "measurement_specification": (
                r.D2_SPECIFICATION if var == "equity_return_window"
                else "unchanged_from_stage125_frozen_contract"
            ),
            "total_development_rows": c["total_development_rows"],
            "valid_rows": _f(c["valid_rows"]),
            "missing_or_unresolved_rows": _f(c["missing_or_unresolved_rows"]),
            "overall_coverage": _f(c["overall_coverage"]),
            "threshold": c["threshold"],
            "coverage_gate_passed": _f(c["coverage_gate_passed"]),
            "fold1_train_coverage": _f(c["fold1_train_coverage"]),
            "fold1_validation_coverage": _f(c["fold1_validation_coverage"]),
            "fold2_train_coverage": _f(c["fold2_train_coverage"]),
            "fold2_validation_coverage": _f(c["fold2_validation_coverage"]),
            "positive_row_coverage": _f(c["positive_row_coverage"]),
            "negative_row_coverage": _f(c["negative_row_coverage"]),
            "resolution": c["resolution"],
        })
    files["stage128_m2_d2_candidate_coverage_audit.csv"] = csv_text(
        cov_fields, cov_rows)

    # -- three-variable common-sample audit --------------------------------- #
    files["stage128_m2_d2_common_sample_audit.json"] = g.json_dumps(
        decision["block_common_sample"])

    # -- event-count feasibility by locked validation window ---------------- #
    feas = decision["event_count_feasibility"]
    feas_fields = [
        "validation_window", "positive_evaluable_in_common_sample",
        "negative_evaluable_in_common_sample", "threshold", "condition_met",
        "m1_development_reference_positive_count",
    ]
    feas_rows = []
    for w in ("fold1_validation", "fold2_validation"):
        pos = feas["m2_common_sample_positive_counts"][w]
        neg = feas["m2_common_sample_negative_counts"][w]
        feas_rows.append({
            "validation_window": w,
            "positive_evaluable_in_common_sample": _f(pos),
            "negative_evaluable_in_common_sample": _f(neg),
            "threshold": feas["threshold"],
            "condition_met": (
                "" if pos is None else pos >= feas["threshold"]
            ),
            "m1_development_reference_positive_count": feas[
                "m1_development_reference_positive_counts"][w],
        })
    files["stage128_m2_d2_event_count_feasibility.csv"] = csv_text(
        feas_fields, feas_rows)
    files["stage128_m2_d2_event_count_feasibility.json"] = g.json_dumps(feas)

    # -- PIT / join / leakage audit ----------------------------------------- #
    files["stage128_m2_d2_join_leakage_audit.json"] = g.json_dumps(
        decision["join_leakage_audit"])

    # -- D2 endpoint / failure taxonomy audit -------------------------------- #
    files["stage128_m2_d2_endpoint_failure_taxonomy.json"] = g.json_dumps({
        "d2_failure_taxonomy": decision["d2_failure_taxonomy"],
        "d2_effective_span_summary": decision["d2_effective_span_summary"],
        "feature_unavailability_breakdown": decision[
            "feature_unavailability_breakdown"],
        "prelock_cross_check": decision["prelock_cross_check"],
        "diagnostics_are_descriptive_only": True,
        "no_threshold_created_from_diagnostics": True,
    })

    # -- QC report ----------------------------------------------------------- #
    files["stage128_m2_d2_gate_rerun_qc_report.json"] = g.json_dumps(
        qc_report(decision, import_qc, auth, features))

    # -- README / scientific interpretation ---------------------------------- #
    files["README_STAGE128_M2_D2_GATE_RERUN.md"] = write_readme(decision, auth)

    return files


def qc_report(
    decision: dict, import_qc: dict, auth: dict, features: dict,
) -> dict:
    """Internal-consistency QC for this Gate re-run package."""
    a = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({
            "name": name, "status": "PASS" if ok else "FAIL", "detail": detail,
        })

    cond = decision["gate_decision_conditions"]
    cov = decision["candidate_coverage"]
    cs = decision["block_common_sample"]

    add("authorization_utterance_sha256_verified",
        hashlib.sha256(auth["human_source_utterance"].encode("utf-8")).hexdigest()
        == HUMAN_SOURCE_UTTERANCE_SHA256)
    add("authorization_is_one_action_only", auth["one_action_only"] is True)
    add("authorization_not_standing", auth["standing_authorization"] is False)
    add("authorization_consumed_by_this_execution",
        auth["authorization_consumed_by_this_execution"] is True)
    add("merge_not_authorized", auth["merge_authorized"] is False)
    add("m2_incremental_evaluation_not_authorized",
        auth["m2_incremental_evaluation_authorized"] is False
        and decision["eligibility_for_next_action"][
            "m2_incremental_evaluation_authorized"] is False)
    add("bundle_sha256_matches_immutable_evidence",
        import_qc["bundle_sha256"] == imp.BUNDLE_SHA256)
    add("bundle_filename_matches", import_qc["bundle_filename"]
        == imp.BUNDLE_FILENAME)
    add("normalized_row_count_matches_historical_delivery",
        import_qc["normalized_row_count"] == imp.EXPECTED_NORMALIZED_ROWS)
    add("restricted_raw_files_match_historical_delivery",
        import_qc["restricted_raw_file_count"]
        == imp.EXPECTED_RESTRICTED_RAW_FILES)
    add("restricted_raw_hash_verification_passed",
        import_qc["restricted_raw_hash_verification_passed"] is True)
    add("evidence_mode_is_offline_imported_bundle",
        decision["evidence_mode"] == g.EVIDENCE_MODE_IMPORTED_BUNDLE)
    add("network_not_required_to_reproduce",
        decision["network_required_to_reproduce"] is False)
    add("gate_not_decided_from_reachability",
        decision["gate_decided_from_endpoint_reachability"] is False)
    add("development_pairs_666", cs["total_development_rows"] == 666)
    add("three_frozen_m2_variables_present",
        decision["m2_block_variable_count"] == 3
        and cond["F_all_three_frozen_m2_variables_present"] is True)
    add("zero_trade_day_ratio_not_added",
        decision["zero_trade_day_ratio_added_to_primary_block"] is False)
    add("equity_return_measured_under_frozen_d2",
        decision["equity_return_measurement_specification"]
        == r.D2_SPECIFICATION
        and decision["equity_return_calendar_convention"]
        == r.D2_CALENDAR_CONVENTION)
    add("only_equity_return_measurement_replaced",
        decision["only_equity_return_measurement_replaced"] is True)
    add("realized_volatility_unchanged",
        decision["realized_volatility_formula_changed"] is False)
    add("amihud_illiquidity_unchanged",
        decision["amihud_illiquidity_formula_changed"] is False)
    add("shared_window_t0_tstar_adjacency_unchanged",
        not any(decision[k] for k in (
            "shared_window_W_changed", "t0_changed", "T_star_changed",
            "trading_day_sequence_changed", "daily_return_adjacency_changed")))
    add("126_floors_unchanged",
        decision["minimum_valid_return_observations"] == 126
        and decision["minimum_valid_amihud_observations"] == 126)
    add("no_imputation_or_substitution",
        not any(decision[k] for k in (
            "imputation_or_fill_applied", "unadjusted_close_substituted",
            "synthetic_adjusted_prices_used", "annualization_applied",
            "rescaled_to_365_days")))
    add("gate_thresholds_unchanged",
        decision["gate_thresholds_changed"] is False
        and decision["threshold_reduced"] is False
        and cov["equity_return_window"]["threshold"]
        == g.CANDIDATE_VALID_COVERAGE_MIN
        and cs["threshold"] == g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN)
    add("gate_criteria_not_added_or_removed",
        decision["gate_criteria_added_or_removed"] is False
        and set(cond) == {
            "A_data_admission_g01_g08",
            "B_each_candidate_coverage_ge_0_80",
            "C_common_sample_coverage_ge_0_70",
            "D_both_validation_windows_ge_5_positives",
            "E_no_pit_leakage_join_provenance_blocker",
            "F_all_three_frozen_m2_variables_present"})
    add("no_fold_specific_coverage_threshold",
        decision["fold_specific_coverage_threshold_added"] is False)
    add("design_selection_not_reopened",
        decision["d0_d1_d2_d3_jalali_selection_reopened"] is False
        and decision["new_design_decision_made_in_this_action"] is False)
    add("gate_outcome_not_used_to_redesign_d2",
        decision["gate_outcome_used_to_redesign_d2"] is False)
    add("prelock_reference_not_used_as_gate_input",
        decision["prelock_cross_check"]["prelock_reference_used_as_gate_input"]
        is False
        and decision["prelock_cross_check"][
            "prelock_reference_hardcoded_as_gate_outcome"] is False)
    add("historical_d0_status_preserved",
        decision["historical_d0_gate_status"] == r.HISTORICAL_D0_GATE_STATUS
        and decision["historical_d0_artifacts_rewritten"] is False)
    add("no_model_fit", decision["model_fit_calls"] == 0
        and decision["modeling_performed"] is False)
    add("no_prediction", decision["prediction_calls"] == 0)
    add("no_predictive_metric_computed",
        decision["predictive_metric_computed"] is False
        and decision["m2_vs_m1_performance_compared"] is False)
    fw = decision["final_test_firewall"]
    add("final_test_firewall_intact",
        fw["final_test_locked"] is True
        and fw["final_test_unlocked"] is False
        and fw["final_test_access_authorized"] is False
        and fw["final_test_predictor_values_inspected"] is False
        and fw["final_test_target_values_inspected"] is False
        and fw["final_test_evaluation_performed"] is False)
    add("final_test_target_years_excluded",
        fw["final_test_target_years_excluded"] == [1400, 1401, 1402])
    add("development_targets_used_only_for_event_counts",
        decision["development_target_label_use"][
            "predictive_performance_computed"] is False
        and decision["development_target_label_use"][
            "target_values_written_into_predictor_artifacts"] is False)
    add("post_lock_eligibility_audit_not_executed_and_not_a_gate_condition",
        decision["post_lock_eligibility_audit"]["executed_in_this_action"]
        is False
        and decision["post_lock_eligibility_audit"][
            "is_a_condition_of_this_gate"] is False)
    add("d2_taxonomy_causes_non_exclusive",
        decision["d2_failure_taxonomy"]["causes_are_not_mutually_exclusive"]
        is True)
    add("no_cross_month_fallback",
        decision["d2_failure_taxonomy"]["cross_month_fallback_used"] is False
        and decision["d2_failure_taxonomy"]["boundary_tolerance_days_added"]
        == 0)
    add("gate_status_is_terminal",
        decision["gate_status"] in (g.GATE_STATUS_PASS, g.GATE_STATUS_FAIL))
    add("d2_usable_count_equals_observed_feature_count",
        cov["equity_return_window"]["valid_rows"]
        == sum(1 for f in features.values()
               if f["equity_return_window"] is not None))

    failed = sum(1 for x in a if x["status"] != "PASS")
    return {
        "contract_id": r.CONTRACT_ID,
        "decision_id": r.ACTION_ID,
        "stage": r.STAGE,
        "gate_status": decision["gate_status"],
        "assertion_count": len(a),
        "failed_count": failed,
        "all_pass": failed == 0,
        "all_pass_semantics": (
            "all_pass means every REQUIRED internal-consistency assertion of "
            "this Gate re-run package passed. It is NOT a statement about the "
            "Gate outcome itself: the Gate result is reported separately in "
            "gate_status and is decided only by the observed evidence."
        ),
        "scope_note": (
            "Internal consistency of the Stage128 D2 Gate re-run package: "
            "authorization scope, immutable-evidence integrity, frozen "
            "invariants, threshold immutability, firewall and no-execution "
            "guarantees. It is not itself a Gate decision."
        ),
        "assertions": a,
    }


def write_readme(decision: dict, auth: dict) -> str:
    cond = decision["gate_decision_conditions"]
    cov = decision["candidate_coverage"]
    cs = decision["block_common_sample"]
    feas = decision["event_count_feasibility"]
    tax = decision["d2_failure_taxonomy"]
    xcheck = decision["prelock_cross_check"]
    passed = decision["gate_status"] == g.GATE_STATUS_PASS

    def pct(v):
        return "n/a" if v is None else f"{v:.4f}"

    lines = [
        "# Stage128 — canonical M2 data-admission Gate RE-RUN (Gregorian D2)",
        "",
        f"**Action:** `{r.ACTION_ID}` — one authorized execution, consumed.",
        "",
        f"**Gate result: `{decision['gate_status']}`**",
        "",
        decision["gate_status_meaning"],
        "",
        "## What this Gate re-ran, and what it did not",
        "",
        "This is the SAME canonical M2 data-admission Gate that Stage127 "
        "executed, with exactly one difference: the equity-return slot of the "
        "frozen three-variable M2 block is measured under the already-frozen "
        f"Stage128 D2 specification `{r.D2_SPECIFICATION}` "
        f"({r.D2_CALENDAR_CONVENTION} calendar convention), frozen by "
        f"`{r.DESIGN_FREEZE_ACTION_ID}`.",
        "",
        "No new design decision was made here. D0/D1/D2/D3 selection was not "
        "reopened, Gregorian was not re-compared against Jalali, no threshold "
        "was changed, no boundary tolerance was searched, and the Gate "
        "outcome was not used to redesign D2. `W`, `t0`, `T*`, the "
        "trading-day sequence, daily-return adjacency, realized volatility, "
        "Amihud and both 126 floors are the unchanged frozen Stage127 "
        "primitives, called directly.",
        "",
        "The historical Stage127 D0 Gate result "
        f"(`{decision['historical_d0_gate_status']}`) is preserved unchanged "
        "in its own Stage127 artifacts; nothing here rewrites it.",
        "",
        "## Evidence",
        "",
        f"- Bundle: `{decision['external_delivery']['bundle_filename']}`",
        f"- SHA256: `{decision['external_delivery']['bundle_sha256']}` "
        "(independently verified before execution)",
        f"- Normalized daily observations: "
        f"{decision['external_delivery']['normalized_row_count']}",
        f"- Instrument mappings: {decision['external_delivery']['mapping_rows']}"
        f" — retrieval ranges: {decision['external_delivery']['manifest_rows']}"
        f" — restricted raw files: "
        f"{decision['external_delivery']['restricted_raw_file_count']}",
        "- The same immutable bundle as the historical Gate. No fresher "
        "dataset, no widened period, no replaced PARTIAL range, no backfill, "
        "no substitute source, and no reachability-based evidence.",
        "",
        "## Conditions A–F (each reported separately)",
        "",
        f"- **A — G01–G08 source/data-quality admission:** "
        f"{cond['A_data_admission_g01_g08']}",
        f"- **B — each candidate coverage ≥ {g.CANDIDATE_VALID_COVERAGE_MIN}:** "
        f"{cond['B_each_candidate_coverage_ge_0_80']}",
    ]
    for var, _, _ in g.M2_VARIABLES:
        c = cov[var]
        lines.append(
            f"  - `{var}`: {c['valid_rows']}/{c['total_development_rows']} = "
            f"{pct(c['overall_coverage'])} vs {c['threshold']} → "
            f"{c['coverage_gate_passed']}"
        )
    lines += [
        f"- **C — three-variable common-sample coverage ≥ "
        f"{g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN}:** "
        f"{cond['C_common_sample_coverage_ge_0_70']} "
        f"({cs['common_usable_rows']}/{cs['total_development_rows']} = "
        f"{pct(cs['common_coverage'])})",
        f"- **D — ≥ {feas['threshold']} positive evaluable observations in "
        f"BOTH locked validation windows:** "
        f"{cond['D_both_validation_windows_ge_5_positives']}",
    ]
    for w in ("fold1_validation", "fold2_validation"):
        lines.append(
            f"  - `{w}`: positives "
            f"{feas['m2_common_sample_positive_counts'][w]}, negatives "
            f"{feas['m2_common_sample_negative_counts'][w]} "
            f"(threshold {feas['threshold']} positives)"
        )
    lines += [
        f"- **E — no PIT/leakage/join/provenance blocker:** "
        f"{cond['E_no_pit_leakage_join_provenance_blocker']}",
        f"- **F — all three frozen M2 variables present:** "
        f"{cond['F_all_three_frozen_m2_variables_present']}",
        "",
        "## D2 diagnostics (descriptive only — never tuning inputs)",
        "",
        f"- D2 unusable: {tax['d2_unusable_total']}/"
        f"{tax['development_pairs']}",
        f"- `{r.D2_CAUSE_LT126}`: {tax[r.D2_CAUSE_LT126]}",
        f"- `{r.D2_CAUSE_NO_START}`: {tax[r.D2_CAUSE_NO_START]}",
        f"- `{r.D2_CAUSE_NO_END}`: {tax[r.D2_CAUSE_NO_END]}",
        f"- `{r.D2_CAUSE_ZERO_START}`: {tax[r.D2_CAUSE_ZERO_START]}",
        "- Causes are non-exclusive and do not sum to the unusable total.",
        "",
        "## Pre-lock cross-check (AFTER canonical reconstruction)",
        "",
        f"The pre-lock predictor-only reference was "
        f"{xcheck['prelock_reference_usable']}/"
        f"{xcheck['prelock_reference_total']}. The canonical re-run observed "
        f"{xcheck['canonical_observed_usable']} "
        f"(difference {xcheck['difference_vs_prelock_reference']:+d}). The "
        "reference was NOT an input to this Gate and was never hard-coded as "
        "its outcome; a discrepancy triggers provenance investigation, never "
        "a design search.",
        "",
        "## What this result does NOT authorize",
        "",
    ]
    if passed:
        lines += [
            "The Gate PASSED **data admission only**. It does not say that M2 "
            "improves prediction, and it authorizes nothing further.",
            "",
            f"`{r.NEXT_GATED_ACTION_ID}` is identified as a POINTER only. It "
            "requires a new, explicit human authorization "
            "(`m2_incremental_evaluation_authorized = false`). No model was "
            "fit, no prediction generated, no winner selected, and the final "
            "test remains locked.",
            "",
            "The post-lock eligibility audit frozen by the design-freeze "
            "contract remains REQUIRED before any M2 predictive result is "
            "interpreted. It was not executed here and is not a condition of "
            "this Gate.",
        ]
    else:
        lines += [
            "This is an OBSERVED negative result against the frozen "
            "thresholds. No threshold is relaxed, D2 is not redesigned, there "
            "is no fallback to D3/D1/Jalali, and M3 is not started. The "
            "action STOPS here for human review.",
        ]
    lines += [
        "",
        "## Counters",
        "",
        "target values accessed for predictive use = 0; model fits = 0; "
        "predictions = 0; final-test access = 0; canonical Gate executions in "
        "this action = 1 (the authorized re-run); historical D0 Gate changed "
        "= NO; M2 admitted for modeling = "
        f"{'DATA ADMISSION ONLY' if passed else 'NO'}.",
        "",
    ]
    return "\n".join(lines)


def resolve_bundle(arg: str | None) -> str:
    path = arg or os.environ.get(DEFAULT_BUNDLE_ENV, "")
    if not path:
        raise SystemExit(
            "the external evidence bundle is required: pass --bundle PATH or "
            f"set {DEFAULT_BUNDLE_ENV}. This Gate has no reachability-based "
            "fallback path."
        )
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--bundle", default=None)
    args = ap.parse_args()
    if args.build == args.check:
        print("exactly one of --build or --check is required", file=sys.stderr)
        return 2

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = g.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, r.OUT_DIR_REL)

    files = build_package(repo_root, resolve_bundle(args.bundle))
    decision = json.loads(files["stage128_m2_d2_gate_rerun_decision.json"])

    if args.check:
        drift = []
        for name, text in files.items():
            p = os.path.join(out_dir, name)
            if not os.path.isfile(p) or open(p, encoding="utf-8").read() != text:
                drift.append(name)
        if drift:
            print(f"DRIFT: {drift}")
            return 1
        print(
            "Stage128 D2 Gate re-run package is up to date "
            f"(status={decision['gate_status']})"
        )
        return 0

    os.makedirs(out_dir, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    meta = {
        "contract_id": r.CONTRACT_ID,
        "contract_version": r.CONTRACT_VERSION,
        "decision_id": r.ACTION_ID,
        "stage": r.STAGE,
        "gate_status": decision["gate_status"],
        "canonical_gate_rerun_of": r.HISTORICAL_D0_ACTION_ID,
        "design_freeze_action_id": r.DESIGN_FREEZE_ACTION_ID,
        "equity_return_measurement_specification": r.D2_SPECIFICATION,
        "evidence_mode": g.EVIDENCE_MODE_IMPORTED_BUNDLE,
        "external_bundle_filename": imp.BUNDLE_FILENAME,
        "external_bundle_sha256": imp.BUNDLE_SHA256,
        "external_bundle_size_bytes": imp.BUNDLE_SIZE_BYTES,
        "canonical_request_sha256": imp.CANONICAL_REQUEST_SHA256,
        "human_source_utterance_sha256": HUMAN_SOURCE_UTTERANCE_SHA256,
        "package_artifacts_sha256": {
            f"{r.OUT_DIR_REL}/{name}": g.sha256_text(text)
            for name, text in sorted(files.items())
        },
        "canonical_sources_sha256": decision["canonical_sources_sha256"],
        "composed_module_sha256": decision["composed_module_sha256"],
        "historical_stage127_d0_artifacts_modified": False,
        "source_main_commit": _git(repo_root, "rev-parse", "origin/main"),
        "source_repository": "abtinasg/papermali",
        "execution_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    with open(os.path.join(
            out_dir,
            "metadata_and_hashes_stage128_m2_d2_gate_rerun.json"),
            "w", encoding="utf-8") as f:
        f.write(g.json_dumps(meta))

    cs = decision["block_common_sample"]
    print(f"Stage128 D2 Gate re-run: status={decision['gate_status']}")
    print(f"  bundle sha256 verified: {imp.BUNDLE_SHA256}")
    print(f"  development pairs: {cs['total_development_rows']}")
    for var, _, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        print(f"  {var}: {c['valid_rows']}/{c['total_development_rows']} "
              f"= {c['overall_coverage']:.4f}")
    print(f"  common sample: {cs['common_usable_rows']}/"
          f"{cs['total_development_rows']} = {cs['common_coverage']:.4f}")
    for k, v in decision["gate_decision_conditions"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
