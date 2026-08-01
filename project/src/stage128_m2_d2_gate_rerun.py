"""Stage128 — canonical M2 data-admission Gate RE-RUN under Gregorian D2.

Authorized action: ``stage128-m2-d2-gate-rerun`` (one action only).

This module executes the SAME canonical M2 data-admission Gate that Stage127
executed, with EXACTLY ONE difference: the equity-return slot of the frozen
three-variable M2 block is measured under the already-frozen Stage128 D2
specification ``BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN`` (Gregorian
calendar convention) instead of the historical D0 exact-endpoint rule.

Composition discipline (no duplicated science):

* the immutable external TSETMC bundle is imported and independently
  revalidated by the existing
  :mod:`stage127_m2_external_delivery_import`;
* ``W`` / ``t0`` / ``T*`` / trading-day sequence / daily-return adjacency /
  realized volatility / Amihud / the 126 floors all come from the frozen
  :mod:`stage127_m2_market_data_gate` primitives — none is reimplemented;
* ONLY the equity-return value is replaced, by the frozen
  :func:`stage128_m2_d2_boundary_month_equity_return.compute_d2_equity_return`;
* the Gate conditions A-F, their thresholds, the coverage/common-sample/
  event-count/join-leakage audits and the decision rule are the frozen
  Stage127 functions, called unchanged. Nothing here re-derives a threshold.

The M2 block therefore remains exactly three variables. The equity-return
BLOCK SLOT keeps its frozen canonical name ``equity_return_window`` — the
variable identity is unchanged; only its measurement specification was
amended by the Stage128 design freeze — so condition F ("all three frozen M2
variables present") is evaluated against the frozen block definition itself
rather than against a renamed copy. Every artifact records the measurement
amendment explicitly, and the historical D0 value is carried alongside the D2
value for audit (never mixed into the Gate decision).

This module performs no model fit, no prediction, no target-based comparison,
and reads no final-test row. Development target labels ARE read, by the
unchanged frozen Stage127 machinery, for three limited audits only: the
condition-D event counts in the two locked validation windows, the
target-stratified descriptive candidate coverage, and the descriptive
positive/negative composition of the common sample. They drive no predictive
metric, no model fit, no prediction, no design or feature selection, and no
threshold tuning, and no target value is written into the pair-level
predictor artifact. See ``development_target_label_use`` in the decision.
"""

from __future__ import annotations

import os
import statistics
from typing import Any

from src import stage127_m2_market_data_gate as g
from src import stage128_m2_d2_boundary_month_equity_return as d2

STAGE = "Stage128"
ACTION_ID = "stage128-m2-d2-gate-rerun"
CONTRACT_ID = "stage128_m2_d2_gate_rerun"
CONTRACT_VERSION = "stage128_m2_d2_gate_rerun_v1"

#: The action this Gate's result may POINT to. Identifying it is never an
#: authorization; it requires a separate, explicit human authorization.
NEXT_GATED_ACTION_ID = "stage127-m2-incremental-evaluation"

#: The design freeze whose specification this Gate executes.
DESIGN_FREEZE_ACTION_ID = "stage128-m2-boundary-month-return-design-freeze"
D2_SPECIFICATION = "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN"
D2_CALENDAR_CONVENTION = "GREGORIAN"

#: The historical Stage127 D0 Gate result. Never recomputed, never rewritten.
HISTORICAL_D0_GATE_STATUS = "FAIL_M2_DATA_GATE"
HISTORICAL_D0_ACTION_ID = "stage127-m2-market-data-gate"

OUT_DIR_REL = "project/stage128"

#: Historical PRE-LOCK predictor-only feasibility counts. Recorded for
#: cross-check AFTER canonical reconstruction only; never an input to the
#: decision and never hard-coded as the Gate outcome.
PRELOCK_D2_REFERENCE_USABLE = 539
PRELOCK_D2_REFERENCE_TOTAL = 666

#: Non-exclusive D2 unusability causes (descriptive taxonomy only).
D2_CAUSE_LT126 = "LT126_VALID_RETURNS"
D2_CAUSE_NO_START = "NO_START_BOUNDARY_PRICE"
D2_CAUSE_NO_END = "NO_END_BOUNDARY_PRICE"
D2_CAUSE_ZERO_START = "ZERO_START_BOUNDARY_PRICE"


class GateRerunFail(Exception):
    """Fail-closed error for the D2 Gate re-run."""


# --------------------------------------------------------------------------- #
# D2 pair features — frozen primitives + the D2 equity-return substitution
# --------------------------------------------------------------------------- #

def compute_pair_features_d2(
    cutoff_iso: str, observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Frozen Stage127 pair features with the equity-return slot re-measured.

    ``realized_volatility``, ``amihud_illiquidity``, ``W``, ``t0``, ``T*``,
    the trading-day sequence, the daily-return adjacency and both 126 floors
    are taken verbatim from :func:`stage127_m2_market_data_gate.
    compute_pair_features`. Only ``equity_return_window`` is replaced, by the
    frozen D2 boundary-month endpoint selection, evaluated over the SAME
    window and the SAME ``usable_daily_return_count``.
    """
    base = g.compute_pair_features(cutoff_iso, observations)
    win = g.pair_scientific_window(cutoff_iso, observations)
    window = win["window"]

    d2_result = d2.compute_d2_equity_return(
        window, base["usable_daily_return_count"],
    )

    start = d2.find_start_boundary_price(
        window, window[0]["trading_date"]) if window else {}
    end = d2.find_end_boundary_price(
        window, window[-1]["trading_date"]) if window else {}

    out = dict(base)
    # The historical D0 value is preserved for audit, never used by the Gate.
    out["equity_return_window_d0_historical"] = base["equity_return_window"]
    out["equity_return_window"] = d2_result["equity_return_d2"]
    out["equity_return_measurement_specification"] = D2_SPECIFICATION
    out["d2_start_trading_date"] = d2_result["d2_start_trading_date"]
    out["d2_end_trading_date"] = d2_result["d2_end_trading_date"]
    out["d2_status"] = d2_result["d2_status"]
    out["d2_start_adjusted_close_present"] = bool(start)
    out["d2_end_adjusted_close_present"] = bool(end)
    out["d2_start_adjusted_close_is_zero"] = bool(
        start and start["adjusted_close"] == 0
    )
    out["d2_no_start_boundary_price"] = not bool(start)
    out["d2_no_end_boundary_price"] = not bool(end)
    out["d2_effective_span_days"] = _span_days(
        d2_result["d2_start_trading_date"], d2_result["d2_end_trading_date"],
    )
    return out


def _span_days(start_iso: str, end_iso: str) -> int | None:
    """Calendar days between the two selected D2 endpoints (descriptive)."""
    if not start_iso or not end_iso:
        return None
    from datetime import date
    return (date.fromisoformat(end_iso) - date.fromisoformat(start_iso)).days


# --------------------------------------------------------------------------- #
# Descriptive diagnostics (never tuning inputs)
# --------------------------------------------------------------------------- #

def d2_failure_taxonomy(
    features: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Non-exclusive observed causes of D2 unusability.

    Purely descriptive. A pair may trip more than one cause, so the counts do
    NOT sum to the unusable total. No threshold is derived from any of these.
    """
    vals = list(features.values())

    def _n(pred) -> int:
        return sum(1 for f in vals if pred(f))

    unusable = _n(lambda f: f["equity_return_window"] is None)
    return {
        "development_pairs": len(vals),
        "d2_unusable_total": unusable,
        "causes_are_not_mutually_exclusive": True,
        D2_CAUSE_LT126: _n(lambda f: f["fewer_than_126_valid_returns"]),
        D2_CAUSE_NO_START: _n(lambda f: f["d2_no_start_boundary_price"]),
        D2_CAUSE_NO_END: _n(lambda f: f["d2_no_end_boundary_price"]),
        D2_CAUSE_ZERO_START: _n(
            lambda f: f["d2_start_adjusted_close_is_zero"]),
        "pairs_failing_only_lt126": _n(
            lambda f: f["fewer_than_126_valid_returns"]
            and not f["d2_no_start_boundary_price"]
            and not f["d2_no_end_boundary_price"]),
        "pairs_failing_only_no_start_boundary_price": _n(
            lambda f: f["d2_no_start_boundary_price"]
            and not f["d2_no_end_boundary_price"]
            and not f["fewer_than_126_valid_returns"]),
        "pairs_failing_only_no_end_boundary_price": _n(
            lambda f: f["d2_no_end_boundary_price"]
            and not f["d2_no_start_boundary_price"]
            and not f["fewer_than_126_valid_returns"]),
        "pairs_missing_both_boundary_prices": _n(
            lambda f: f["d2_no_start_boundary_price"]
            and f["d2_no_end_boundary_price"]),
        "minimum_usable_daily_returns": d2.MIN_USABLE_DAILY_RETURNS_D2,
        "cross_month_fallback_used": False,
        "boundary_tolerance_days_added": 0,
        "thresholds_reduced_to_improve_coverage": False,
        "missing_values_imputed": False,
        "diagnostics_used_as_tuning_input": False,
    }


def d2_effective_span_summary(
    features: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Descriptive effective-span summary over D2-usable pairs only.

    Recorded because the construct is an APPROXIMATELY 12-month as-of return.
    No minimum-span rule is created, and no pair is excluded by span.
    """
    spans = [
        f["d2_effective_span_days"] for f in features.values()
        if f["equity_return_window"] is not None
        and f["d2_effective_span_days"] is not None
    ]
    if not spans:
        return {
            "usable_pairs_with_measurable_span": 0,
            "minimum_span_days": None, "median_span_days": None,
            "maximum_span_days": None, "mean_span_days": None,
            "descriptive_only_no_span_threshold_created": True,
        }
    return {
        "usable_pairs_with_measurable_span": len(spans),
        "minimum_span_days": min(spans),
        "median_span_days": statistics.median(spans),
        "maximum_span_days": max(spans),
        "mean_span_days": round(statistics.fmean(spans), 6),
        "descriptive_only_no_span_threshold_created": True,
        "minimum_effective_span_threshold_added": False,
    }


def prelock_cross_check(observed_usable: int) -> dict[str, Any]:
    """Compare the canonical count to the pre-lock reference, AFTER the fact.

    The pre-lock 539/666 predictor-only figure is NOT an input to this Gate.
    This block exists only so a discrepancy is surfaced for provenance
    investigation instead of being silently reconciled or forced to agree.
    """
    delta = observed_usable - PRELOCK_D2_REFERENCE_USABLE
    return {
        "prelock_reference_usable": PRELOCK_D2_REFERENCE_USABLE,
        "prelock_reference_total": PRELOCK_D2_REFERENCE_TOTAL,
        "prelock_reference_is_predictor_only_historical_evidence": True,
        "prelock_reference_used_as_gate_input": False,
        "prelock_reference_hardcoded_as_gate_outcome": False,
        "canonical_observed_usable": observed_usable,
        "difference_vs_prelock_reference": delta,
        "matches_prelock_reference": delta == 0,
        "discrepancy_triggers_investigation_not_design_search": True,
        "d2_specification_altered_to_force_agreement": False,
    }


# --------------------------------------------------------------------------- #
# Canonical Gate re-run
# --------------------------------------------------------------------------- #

def build(
    repo_root: str,
    import_qc: dict[str, Any],
    observations: dict[str, list[dict[str, Any]]],
    accessibility_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Execute the canonical Gate once, under the frozen Gregorian D2 spec.

    Deterministic and OFFLINE from the immutable bundle. Endpoint
    reachability can never produce a PASS.
    """
    pairs = g.load_development_pairs(repo_root)
    accessibility = g.score_accessibility_from_evidence(accessibility_evidence)

    features: dict[tuple[str, str], dict[str, Any]] = {}
    accepted_observations = 0
    post_cutoff = 0
    same_day = 0
    target_year_leak = 0
    tickers_without_observations: set[str] = set()

    for p in pairs:
        obs = observations.get(p["ticker"], [])
        if not obs:
            tickers_without_observations.add(p["ticker"])
        cutoff = p["pair_cutoff_date"]
        win = g.pair_scientific_window(cutoff, obs)
        f = compute_pair_features_d2(cutoff, obs)
        for o in win["window"]:
            if not cutoff or o["trading_date"] > cutoff:
                post_cutoff += 1
            elif o["trading_date"] == cutoff:
                same_day += 1
            if o["trading_date"][:4] and int(o["trading_date"][:4]) >= 2021:
                target_year_leak += 1
        accepted_observations += f["window_trading_day_count"]
        features[(p["ticker"], p["fiscal_year_t"])] = f

    usable_by_var: dict[str, set[tuple[str, str]]] = {}
    for var, _, _ in g.M2_VARIABLES:
        usable_by_var[var] = {
            k for k, f in features.items() if f[var] is not None
        }
    common = set.intersection(*usable_by_var.values())

    timing = {
        "accepted_post_cutoff_observations": post_cutoff,
        "accepted_same_calendar_day_as_cutoff": same_day,
        "accepted_target_year_leakage_violations": target_year_leak,
    }

    # Frozen Stage127 condition machinery, called unchanged.
    candidates = [
        g.build_candidate_gate(var, cid, fid, accessibility, import_qc, timing)
        for var, cid, fid in g.M2_VARIABLES
    ]
    coverage = {
        var: g.candidate_coverage(pairs, usable_by_var[var])
        for var, _, _ in g.M2_VARIABLES
    }
    common_audit = g.common_sample_audit(pairs, common)
    feasibility = g.event_count_feasibility(pairs, common)
    join_audit = g.join_leakage_audit(pairs, accepted_observations)
    join_audit.update({
        "ticker_mapping_failures": len(tickers_without_observations),
        "ticker_mapping_unresolved": 0,
        "same_day_cutoff_exclusions_applied": sum(
            f["same_calendar_day_as_cutoff_rejected"] for f in features.values()
        ),
        "accepted_post_cutoff_observations": post_cutoff,
        "accepted_target_year_leakage_violations": target_year_leak,
    })
    join_audit["acceptance_criteria"][
        "zero_accepted_post_cutoff_observations"] = post_cutoff == 0
    join_audit["acceptance_criteria"][
        "zero_accepted_target_year_leakage"] = target_year_leak == 0
    join_audit["note"] = (
        "Leakage counters were validated against actually accepted market "
        "observations imported from the immutable external bundle, re-run "
        "under the Stage128 Gregorian D2 equity-return measurement."
    )

    blocking_defects: list[str] = []
    if post_cutoff:
        blocking_defects.append(
            f"{post_cutoff} accepted observations fall at or after a pair cutoff"
        )
    if import_qc["raw_to_normalized_field_mismatches"]:
        blocking_defects.append("raw -> normalized field mapping mismatch")
    if import_qc["adjusted_close_exact_date_mismatches"]:
        blocking_defects.append("adjusted-close exact-date join mismatch")
    if import_qc["final_test_period_observations_imported"]:
        blocking_defects.append("final-test period observation imported")
    if not import_qc["restricted_raw_hash_verification_passed"]:
        blocking_defects.append("restricted raw SHA256 verification failed")
    if tickers_without_observations:
        blocking_defects.append(
            f"{len(tickers_without_observations)} development tickers have no "
            "imported market observation"
        )

    gate_status, blockers, conditions = g.decide_gate_status(
        candidates, coverage, common_audit, feasibility, blocking_defects
    )

    status_meaning = {
        g.GATE_STATUS_PASS: (
            "Re-run on real imported evidence under the frozen Gregorian D2 "
            "equity-return specification, every frozen data-admission "
            "condition, coverage threshold and event-support requirement is "
            "satisfied. This is DATA ADMISSION only: it makes M2 incremental "
            "evaluation scientifically ELIGIBLE for a new explicit human "
            "authorization; it does not authorize it, and it says nothing "
            "about whether M2 improves prediction."
        ),
        g.GATE_STATUS_FAIL: (
            "The re-run completed on real imported evidence and OBSERVED a "
            "failure against a frozen requirement. This is a truthful "
            "negative result about the observed data, not missing evidence, "
            "and it is deliberately not softened into UNRESOLVED. It does not "
            "reopen the D2 design."
        ),
        g.GATE_STATUS_UNRESOLVED: (
            "Evidence required to decide is genuinely unavailable. The frozen "
            "M2 block is neither admitted nor rejected."
        ),
    }[gate_status]

    d2_usable = len(usable_by_var["equity_return_window"])

    decision = {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": ACTION_ID,
        "stage": STAGE,
        "gate_status": gate_status,
        "gate_status_meaning": status_meaning,
        "blocker_reasons": blockers,
        "gate_decision_conditions": conditions,
        "gate_decision_rule": (
            "PASS_FOR_M2_INCREMENTAL_EVALUATION requires A AND B AND C AND D "
            "AND E AND F, evaluated by the UNCHANGED frozen Stage127 "
            "decide_gate_status with the unchanged frozen thresholds. "
            "Endpoint reachability, an HTTP status code, or the external "
            "party's own QC flag can never produce a PASS."
        ),
        "gate_decided_from_endpoint_reachability": False,
        "evidence_mode": g.EVIDENCE_MODE_IMPORTED_BUNDLE,
        "network_required_to_reproduce": False,
        # -- what makes this a RE-RUN, and what is unchanged --------------- #
        "canonical_gate_rerun": True,
        "rerun_of_action_id": HISTORICAL_D0_ACTION_ID,
        "design_freeze_action_id": DESIGN_FREEZE_ACTION_ID,
        "equity_return_measurement_specification": D2_SPECIFICATION,
        "equity_return_calendar_convention": D2_CALENDAR_CONVENTION,
        "only_equity_return_measurement_replaced": True,
        "new_design_decision_made_in_this_action": False,
        "d0_d1_d2_d3_jalali_selection_reopened": False,
        "gate_thresholds_changed": False,
        "gate_criteria_added_or_removed": False,
        "fold_specific_coverage_threshold_added": False,
        "boundary_tolerance_search_performed": False,
        "gate_outcome_used_to_redesign_d2": False,
        "historical_d0_gate_status": HISTORICAL_D0_GATE_STATUS,
        "historical_d0_gate_status_preserved_unchanged": True,
        "historical_d0_artifacts_rewritten": False,
        # -- frozen block identity ------------------------------------------ #
        "scope": "point_in_time_data_admission_gate_development_only",
        "answers_only": (
            "Under the already-frozen Gregorian D2 M2 block, does the "
            "pre-specified M2 data-admission Gate PASS or FAIL on the "
            "development sample?"
        ),
        "does_not_answer": "Does M2 improve prediction?",
        "m2_block": g.M2_BLOCK,
        "m2_block_variables": [v for v, _, _ in g.M2_VARIABLES],
        "m2_block_variable_count": len(g.M2_VARIABLES),
        "m2_block_slot_note": (
            "The equity-return BLOCK SLOT keeps its frozen canonical name "
            "'equity_return_window'; the Stage128 design freeze amended its "
            "MEASUREMENT to BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN "
            "(Gregorian). The variable identity, the block membership and "
            "condition F are therefore unchanged. Each pair-level row also "
            "carries the historical D0 value in "
            "'equity_return_window_d0_historical' for audit only; it never "
            "enters this decision."
        ),
        "primary_source_id": g.M2_PRIMARY_SOURCE_ID,
        "source_family": g.M2_SOURCE_FAMILY,
        "zero_trade_day_ratio_added_to_primary_block": False,
        "variable_dropped_from_frozen_block": False,
        "realized_volatility_formula_changed": False,
        "amihud_illiquidity_formula_changed": False,
        "shared_window_W_changed": False,
        "t0_changed": False,
        "T_star_changed": False,
        "trading_day_sequence_changed": False,
        "daily_return_adjacency_changed": False,
        "minimum_valid_return_observations": g.MIN_VALID_RETURN_OBSERVATIONS,
        "minimum_valid_amihud_observations": g.MIN_VALID_AMIHUD_OBSERVATIONS,
        "imputation_or_fill_applied": False,
        "unadjusted_close_substituted": False,
        "synthetic_adjusted_prices_used": False,
        "annualization_applied": False,
        "rescaled_to_365_days": False,
        "threshold_reduced": False,
        # -- observed evidence ---------------------------------------------- #
        "external_delivery": {
            "bundle_filename": import_qc["bundle_filename"],
            "bundle_sha256": import_qc["bundle_sha256"],
            "bundle_size_bytes": import_qc["bundle_size_bytes"],
            "canonical_request_sha256": import_qc["canonical_request_check"][
                "delivered_request_sha256"],
            "mapping_rows": import_qc["mapping_rows"],
            "manifest_rows": import_qc["manifest_rows"],
            "retrieval_status_counts": import_qc["retrieval_status_counts"],
            "partial_ranges_preserved": import_qc["partial_ranges_preserved"],
            "normalized_row_count": import_qc["normalized_row_count"],
            "restricted_raw_file_count": import_qc["restricted_raw_file_count"],
            "external_qc_report_trusted": False,
            "independently_revalidated_in_papermali": True,
            "fresher_dataset_retrieved": False,
            "requested_period_widened": False,
            "partial_ranges_replaced": False,
            "data_backfilled": False,
            "alternative_market_data_source_used": False,
        },
        "candidates": candidates,
        "candidate_coverage": coverage,
        "block_common_sample": common_audit,
        "event_count_feasibility": feasibility,
        "join_leakage_audit": join_audit,
        "d2_failure_taxonomy": d2_failure_taxonomy(features),
        "d2_effective_span_summary": d2_effective_span_summary(features),
        "prelock_cross_check": prelock_cross_check(d2_usable),
        "feature_unavailability_breakdown": g.unavailability_breakdown(features),
        "block_not_redefined_on_candidate_failure": True,
        "block_redefinition_requires_separate_human_decision": True,
        "no_variable_dropped_from_frozen_block": True,
        # -- no modeling ever ------------------------------------------------ #
        "modeling_performed": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "m2_vs_m1_performance_compared": False,
        "predictive_metric_computed": False,
        "eligibility_for_next_action": {
            "next_action_id": NEXT_GATED_ACTION_ID,
            "requires_data_admission_pass": True,
            "requires_development_comparison_feasibility_pass": True,
            "data_admission_pass": conditions["A_data_admission_g01_g08"],
            "development_comparison_feasibility_pass": conditions[
                "D_both_validation_windows_ge_5_positives"],
            "eligible_to_start_m2_incremental_evaluation": (
                gate_status == g.GATE_STATUS_PASS
            ),
            "m2_incremental_evaluation_authorized": False,
            "m2_modeling_started": False,
            "eligibility_is_not_authorization": True,
            "pointer_is_not_authorization": True,
        },
        "post_lock_eligibility_audit": {
            "required_before_interpreting_m2_predictive_results": True,
            "executed_in_this_action": False,
            "is_a_condition_of_this_gate": False,
            "smd_used_to_change_gate_status": False,
            "distress_rate_inspected_for_redesign": False,
            "contract": (
                "project/docs/ai/STAGE128_M2_D2_DESIGN_FREEZE.md"
            ),
        },
        "final_test_firewall": {
            "final_test_locked": True,
            "final_test_unlocked": False,
            "final_test_access_authorized": False,
            "final_test_predictor_values_inspected": False,
            "final_test_target_values_inspected": False,
            "final_test_evaluation_performed": False,
            "final_test_target_years_excluded": list(g.FINAL_TEST_TARGET_YEARS),
            "final_test_coverage_used_for_admission": False,
            "final_test_rows_structurally_excluded_before_value_load": True,
        },
        "development_target_label_use": {
            # Literal, non-euphemistic statement. Development target labels
            # ARE read by this Gate — the frozen canonical Stage127 machinery
            # computes target-stratified descriptive audits in addition to the
            # condition-D event counts. Enumerating them honestly is what
            # makes the surrounding negative claims verifiable.
            "development_target_labels_accessed": True,
            "used_only_for": (
                "the frozen canonical Gate's limited descriptive and "
                "event-support audits: (1) condition-D positive evaluable "
                "event counts in the two locked validation windows, "
                "(2) target-stratified descriptive candidate coverage, and "
                "(3) the descriptive positive/negative composition of the "
                "three-variable common sample"
            ),
            "declared_uses": [
                {
                    "use_id": "condition_d_validation_window_event_counts",
                    "artifact_fields": [
                        "event_count_feasibility."
                        "m2_common_sample_positive_counts",
                        "event_count_feasibility."
                        "m2_common_sample_negative_counts",
                    ],
                    "role": "frozen_gate_condition_d_event_support",
                },
                {
                    "use_id": "target_stratified_candidate_coverage",
                    "artifact_fields": [
                        "candidate_coverage.*.positive_row_coverage",
                        "candidate_coverage.*.negative_row_coverage",
                    ],
                    "role": "descriptive_only",
                },
                {
                    "use_id": "common_sample_positive_negative_composition",
                    "artifact_fields": [
                        "block_common_sample.positive_count",
                        "block_common_sample.negative_count",
                    ],
                    "role": "descriptive_only",
                },
            ],
            "declared_uses_are_exhaustive": True,
            "predictive_performance_computed": False,
            "predictive_metric_computed": False,
            "model_fit_on_targets": False,
            "prediction_generated": False,
            "target_based_feature_selection": False,
            "target_based_design_change": False,
            "target_based_threshold_tuning": False,
            "target_values_written_into_predictor_artifacts": False,
            "final_test_target_values_accessed": False,
            "final_test_predictor_values_accessed": False,
        },
        "canonical_sources_sha256": {
            rel: g.sha256_file(os.path.join(repo_root, rel))
            for rel in g.CANONICAL_SOURCES
        },
        "composed_module_sha256": {
            rel: g.sha256_file(os.path.join(repo_root, rel))
            for rel in (
                "project/src/stage127_m2_market_data_gate.py",
                "project/src/stage127_m2_external_delivery_import.py",
                "project/src/stage128_m2_d2_boundary_month_equity_return.py",
                "project/src/stage128_m2_d2_gate_rerun.py",
            )
        },
    }

    for cand in decision["candidates"]:
        cov = decision["candidate_coverage"][cand["variable"]]
        cand["admission_scope"] = "source_and_data_quality_gates_G01_G08_only"
        cand["admission_decision_does_not_mean_admitted_into_m2_modeling"] = True
        cand["candidate_modeling_path_coverage_threshold"] = (
            g.CANDIDATE_VALID_COVERAGE_MIN)
        cand["candidate_modeling_path_coverage"] = cov["overall_coverage"]
        cand["candidate_modeling_path_coverage_pass"] = cov[
            "coverage_gate_passed"]
        cand["admitted_into_m2_modeling_path"] = bool(
            cand["G08_all_required_gates_pass"]["resolution"] == g.RESOLUTION_PASS
            and cov["coverage_gate_passed"]
        )

    return {
        "decision": decision,
        "pairs": pairs,
        "features": features,
        "accessibility": accessibility,
        "usable_by_variable": usable_by_var,
        "common_sample_keys": common,
    }
