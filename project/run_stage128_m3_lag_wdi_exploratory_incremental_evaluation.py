#!/usr/bin/env python3
"""Runner — Stage128 Track B step E: the M3-LAG-WDI EXPLORATORY INCREMENTAL
EVALUATION.

Authorized action: ``stage128-m3-lag-wdi-exploratory-incremental-evaluation``
Authorized scope:  ``exploratory_incremental_evaluation_only``

``--execute BUNDLE_DIR``  the ONE authorized modeling run (offline).
``--check``               offline verification of the committed package.

Both modes deterministically recompute the same 44 model fits from committed
bytes, so ``--check`` fails if any committed number stops being reproducible.
A ``--check`` recomputation is verification, never a new scientific execution.

There is no network code path, no tuning code path, no feature-search code
path, no SHAP code path and no Final Test code path. The result is labelled
``supplementary_exploratory_robustness_only`` and never enters the
confirmatory Holm family.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_incremental_evaluation as m)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / m.PACKAGE_REL

_ARTIFACT_FILES = {
    "human_authorization_record":
        "stage128_m3_lag_wdi_evaluation_human_authorization_record.json",
    "execution_contract":
        "stage128_m3_lag_wdi_evaluation_execution_contract.json",
    "common_sample_audit":
        "stage128_m3_lag_wdi_evaluation_common_sample_audit.json",
    "feature_configuration_manifest":
        "stage128_m3_lag_wdi_evaluation_feature_configuration_manifest.json",
    "fit_count_audit":
        "stage128_m3_lag_wdi_evaluation_predictive_fit_count_audit.json",
    "calibration_report":
        "stage128_m3_lag_wdi_evaluation_calibration_report.json",
    "bootstrap_summary":
        "stage128_m3_lag_wdi_evaluation_paired_bootstrap_delta_summary.json",
    "multiplicity_status":
        "stage128_m3_lag_wdi_evaluation_multiplicity_family_status.json",
    "execution_audit":
        "stage128_m3_lag_wdi_evaluation_execution_audit.json",
    "governance_boundary":
        "stage128_m3_lag_wdi_evaluation_governance_boundary.json",
    "firewall_audit":
        "stage128_m3_lag_wdi_evaluation_final_test_firewall_audit.json",
    "decision": "stage128_m3_lag_wdi_evaluation_decision.json",
    "qc_report": "stage128_m3_lag_wdi_evaluation_qc_report.json",
}
_FEATURES_CSV = "stage128_m3_lag_wdi_evaluation_feature_values.csv"
_OOF_CSV = "stage128_m3_lag_wdi_evaluation_paired_oof_predictions.csv"
_METRICS_CSV = "stage128_m3_lag_wdi_evaluation_block_model_metrics.csv"
_METADATA_FILE = (
    "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_incremental_"
    "evaluation.json")
_README_FILE = (
    "README_STAGE128_M3_LAG_WDI_EXPLORATORY_INCREMENTAL_EVALUATION.md")

#: Counters this action must leave at exactly zero. Step E fits models; it does
#: not retrieve, re-gate, retune, search, unlock or decide the paper.
_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "step_c_reruns", "step_d_reruns", "data_gate_executions",
    "calendar_mapping_lock_reruns", "calendar_mapping_changes",
    "third_macro_features_added", "feature_searches", "feature_selections",
    "feature_substitutions", "imputations",
    "rows_excluded_outside_frozen_complete_case_rule",
    "tuning_runs", "grid_searches", "hyperparameter_searches",
    "model_family_searches", "model_selections",
    "metric_definitions_created", "metric_definitions_changed",
    "validation_windows_changed", "thresholds_changed",
    "seed_policy_changes", "shap_executions", "holm_calculations",
    "confirmatory_holm_executions", "confirmatory_family_modifications",
    "paper_winner_selections", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
    "final_test_unlocks", "m4_actions",
    "pr_ready_for_review_transitions", "pr_merges",
)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c) for c in columns})


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Building the package
# --------------------------------------------------------------------------- #

def _build(bundle_dir: str, *, scientific: bool) -> dict:
    authorization = m.verify_human_authorization()
    preconditions = m.verify_frozen_preconditions(ROOT)
    values = m.load_retained_values(ROOT, bundle_dir)
    sample = m.build_step_e_sample(ROOT, values)
    evaluation = m.run_paired_evaluation(sample)
    oof = m.oof_rows(evaluation)
    metrics = m.build_metrics_rows(oof)
    calibration = m.build_calibration_report(oof)
    bootstrap = m.run_paired_bootstrap(oof)
    multiplicity = m.build_multiplicity_record()
    firewall = m.build_firewall_audit(sample)
    execution_audit = m.build_execution_audit(evaluation["fit_log"], sample)
    limitations = m.build_limitations(sample)
    feature_rows = m.feature_value_rows(sample)

    # ---- the comparator is REFIT, and that refit is reconciled ---------- #
    comparator = _reconcile_refit_comparator(metrics)

    # ---- E1 ------------------------------------------------------------- #
    e1 = _build_e1(bootstrap, metrics)

    decision = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "hypothesis_id": m.EXPLORATORY_HYPOTHESIS_ID,
        "comparison": m.EXPLORATORY_COMPARISON,
        "comparison_family": m.EXPLORATORY_FAMILY_ID,
        "results_label": m.RESULTS_LABEL,
        "scientific_role": m.SCIENTIFIC_ROLE,
        "e1_conclusion": e1["conclusion"],
        "e1_conclusion_statement": e1["conclusion_statement"],
        "e1_direction_by_family": e1["direction_by_family"],
        "e1_any_family_interval_excludes_zero":
            e1["any_family_interval_excludes_zero"],
        "e1_primary_metric": e1["primary_metric"],
        "e1_secondary_metric_intervals_excluding_zero":
            e1["secondary_metric_intervals_excluding_zero"],
        "e1_secondary_metric_signal_present":
            e1["secondary_metric_signal_present"],
        "e1_secondary_metric_signal_is_confirmatory": False,
        "predictive_result": e1["predictive_result"],
        "exploratory_interpretation": e1["exploratory_interpretation"],
        "statistical_uncertainty": e1["statistical_uncertainty"],
        "limitations": limitations,
        "confirmatory_superiority_claim_made": False,
        "confirmatory_conclusions_changed": False,
        "confirmatory_holm_family_changed": False,
        "paper_winner_selected": False,
        "block_promoted_to_confirmatory": False,
        "m3_cbi_repaired_by_this_action": False,
        "m3i2_replaced_by_this_action": False,
        "authorizes_next_action": False,
        "next_action_id": "human_decision_required",
        "next_action_authorized": False,
        "next_action_scope": "no_further_action_is_authorized",
        "final_test_remains_locked": True,
    }

    execution_contract = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "contract_id": m.PACKAGE_ID,
        "preconditions": preconditions,
        "blocks": {
            "comparator": {
                "block_id": "M2",
                "block_name": "retained_m2",
                "feature_count": m.EXPECTED_M2_FEATURE_COUNT,
                "feature_order": m.M2_FEATURE_ORDER,
                "refit_on_step_e_sample": True,
                "reused_666_row_m1_results_as_comparator": False,
            },
            "exploratory": {
                "block_id": "M3_LAG_WDI",
                "block_name": "m3_lag_wdi_exploratory",
                "feature_count": m.EXPECTED_M3_LAG_WDI_FEATURE_COUNT,
                "feature_order": m.M3_LAG_WDI_FEATURE_ORDER,
                "added_features": m.WDI_FEATURE_ORDER,
                "added_feature_count": len(m.WDI_FEATURE_ORDER),
                "nested_in_comparator": True,
            },
        },
        "identical_sample_for_both_blocks": True,
        "model_families": list(m.MODEL_FAMILIES),
        "frozen_configurations": m.FROZEN_CONFIGURATIONS,
        "deterministic_families": list(m.DETERMINISTIC_FAMILIES),
        "final_oof_seeds": list(m.FINAL_OOF_SEEDS),
        "logistic_fit_seed": m.LOGISTIC_FIT_SEED,
        "expected_primary_fit_count": m.EXPECTED_PRIMARY_FIT_COUNT,
        "primary_metric": m.PRIMARY_METRIC,
        "secondary_metrics": list(m.SECONDARY_METRICS),
        "bootstrap": {
            "method": m.BOOTSTRAP_METHOD,
            "cluster": m.BOOTSTRAP_CLUSTER,
            "replicates": m.BOOTSTRAP_REPLICATES,
            "seed": m.BOOTSTRAP_SEED,
            "confidence_interval": m.BOOTSTRAP_CI,
            "minimum_valid_replicates": m.BOOTSTRAP_MIN_VALID_REPLICATES,
        },
        "inherited_from": "stage127-m2-incremental-evaluation",
        "inherits_locked_validation_architecture": True,
        "inherits_canonical_metric_definitions": True,
        "inherits_seed_policy": True,
        "inherits_bootstrap_and_paired_comparison_machinery": True,
        "retained_configurations_used_unchanged": True,
        "execution_count_semantics": m.EXECUTION_COUNT_SEMANTICS,
        "original_authorized_scientific_execution":
            m.execution_environment(scientific=scientific),
    }

    manifest = {
        "action_id": m.ACTION_ID,
        "m2_feature_order": m.M2_FEATURE_ORDER,
        "m2_feature_count": m.EXPECTED_M2_FEATURE_COUNT,
        "m3_lag_wdi_feature_order": m.M3_LAG_WDI_FEATURE_ORDER,
        "m3_lag_wdi_feature_count": m.EXPECTED_M3_LAG_WDI_FEATURE_COUNT,
        "wdi_features": [
            {
                "feature_id": m.CPI_FEATURE_ID,
                "indicator_code": m.CPI_CODE,
                "country": m.LOCKED_COUNTRY_CODE,
                "observation_year": "t-1",
                "transformation": "identity",
                "same_year_t_observation_used": False,
            },
            {
                "feature_id": m.FX_FEATURE_ID,
                "indicator_code": m.FX_CODE,
                "country": m.LOCKED_COUNTRY_CODE,
                "observation_years": ["t-1", "t-2"],
                "transformation": "FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))",
                "same_year_t_observation_used": False,
            },
        ],
        "calendar_mapping_rule": m.LOCKED_CALENDAR_RULE,
        "calendar_mapping_rule_formula": m.LOCKED_CALENDAR_FORMULA,
        "calendar_mapping_locked_offset": m.LOCKED_CALENDAR_OFFSET,
        "frozen_configurations": m.FROZEN_CONFIGURATIONS,
        "feature_search_executed": False,
        "feature_selection_executed": False,
        "retuning_executed": False,
    }

    boundary = _build_boundary(decision, sample)

    built = {
        "human_authorization_record": authorization,
        "execution_contract": execution_contract,
        "common_sample_audit": {
            "action_id": m.ACTION_ID,
            "parent_surface": "retained_m2_development_common_sample",
            "parent_join_audit": sample["parent"]["join_audit"],
            "composition": sample["composition"],
            "attrition_from_parent": sample["attrition"],
            "missingness_after_construction":
                sample["missingness_after_construction"],
            "calendar_mapping_rule": m.LOCKED_CALENDAR_RULE,
            "calendar_mapping_rule_formula": m.LOCKED_CALENDAR_FORMULA,
            "predictor_years": sample["predictor_years"],
            "predictor_year_first": sample["predictor_year_first"],
            "predictor_year_last": sample["predictor_year_last"],
            "cpi_observation_year_rule": sample["cpi_observation_year_rule"],
            "cpi_observation_year_first":
                sample["cpi_observation_year_first"],
            "cpi_observation_year_last": sample["cpi_observation_year_last"],
            "fx_observation_year_rule": sample["fx_observation_year_rule"],
            "fx_observation_year_numerator_first":
                sample["fx_observation_year_numerator_first"],
            "fx_observation_year_numerator_last":
                sample["fx_observation_year_numerator_last"],
            "fx_observation_year_denominator_first":
                sample["fx_observation_year_denominator_first"],
            "fx_observation_year_denominator_last":
                sample["fx_observation_year_denominator_last"],
            "same_year_t_observations_read":
                sample["same_year_t_observations_read"],
            "wdi_distinct_values": sample["wdi_distinct_values"],
            "wdi_values_by_predictor_year":
                sample["wdi_values_by_predictor_year"],
            "wdi_features_are_constant_within_a_predictor_year": True,
            "fx_zero_change_rows": sample["fx_zero_change_rows"],
            "identical_sample_for_both_blocks": True,
            "final_test_rows_in_sample": 0,
        },
        "feature_configuration_manifest": manifest,
        "fit_count_audit": {
            "action_id": m.ACTION_ID,
            "primary_predictive_fits": len(evaluation["fit_log"]),
            "expected_primary_predictive_fits":
                m.EXPECTED_PRIMARY_FIT_COUNT,
            "fits_by_block": {
                block: sum(1 for f in evaluation["fit_log"]
                           if f["block"] == block)
                for block in m.BLOCKS},
            "fits_by_family": {
                family: sum(1 for f in evaluation["fit_log"]
                            if f["family"] == family)
                for family in m.MODEL_FAMILIES},
            "feature_counts_by_block": {
                block: sorted({f["feature_count"]
                               for f in evaluation["fit_log"]
                               if f["block"] == block})
                for block in m.BLOCKS},
            "fit_log": evaluation["fit_log"],
            "tuning_fits": 0,
            "grid_search_fits": 0,
            "final_test_fits": 0,
        },
        "calibration_report": calibration,
        "bootstrap_summary": bootstrap,
        "multiplicity_status": multiplicity,
        "execution_audit": execution_audit,
        "governance_boundary": boundary,
        "firewall_audit": firewall,
        "decision": decision,
        "_comparator_reconciliation": comparator,
        "_feature_rows": feature_rows,
        "_oof_rows": oof,
        "_metrics_rows": metrics,
        "_sample": sample,
        "_e1": e1,
    }
    built["qc_report"] = _build_qc(built)
    return built


def _reconcile_refit_comparator(metrics: list[dict]) -> dict:
    """Compare the REFIT M2 comparator against the committed retained-M2 run.

    This is a reconciliation, not a substitution: the comparator actually used
    is the refit one. Because the step-E sample turned out to be exactly the
    retained-M2 539-row sample, the refit must reproduce the committed M2
    numbers — and if it ever stopped doing so, that would mean the two actions
    are no longer evaluating the same thing, which must surface loudly.
    """
    committed_path = (ROOT / "project/stage128/m2_incremental_evaluation/"
                      "stage127_m2_block_model_metrics.csv")
    committed: dict[tuple[str, str], dict] = {}
    with committed_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["block"] == "M2":
                committed[(row["model_family"], row["scope"])] = row

    checks = []
    for row in metrics:
        if row["block"] != "M2":
            continue
        ref = committed.get((row["model_family"], row["scope"]))
        if ref is None:
            continue
        for metric in m.ALL_METRICS:
            a = float(ref[metric])
            b = float(row[metric])
            checks.append({
                "model_family": row["model_family"],
                "scope": row["scope"],
                "metric": metric,
                "committed_retained_m2": a,
                "refit_m2_on_step_e_sample": b,
                "identical": a == b,
            })
    mismatches = [c for c in checks if not c["identical"]]
    return {
        "purpose": (
            "reconciliation only — the comparator used everywhere in this "
            "package is the M2 block REFIT on the step E sample, never the "
            "previously published numbers"),
        "committed_source":
            "project/stage128/m2_incremental_evaluation/"
            "stage127_m2_block_model_metrics.csv",
        "comparisons": len(checks),
        "mismatches": len(mismatches),
        "mismatch_detail": mismatches,
        "refit_reproduces_committed_retained_m2": not mismatches,
        "reason_reproduction_is_expected": (
            "both lagged WDI features are constructible for all 539 rows, so "
            "the frozen complete-case rule removes nothing and the step E "
            "sample is mechanically the retained-M2 539-row sample"),
        "committed_m1_666_row_results_used_as_comparator": False,
    }


def _build_e1(bootstrap: dict, metrics: list[dict]) -> dict:
    """The E1 exploratory conclusion, stated in the four mandated registers."""
    direction = {}
    deltas = {}
    for family, entry in bootstrap["by_family"].items():
        pr = entry["metrics"][m.PRIMARY_METRIC]
        direction[family] = m._direction(
            pr["m3_lag_wdi_minus_m2_delta"], pr["ci_lower"], pr["ci_upper"])
        deltas[family] = pr
    any_excl = any(v["ci_excludes_zero"] for v in deltas.values())
    all_null = all(d == "approximately_null_interval_includes_zero"
                   for d in direction.values())

    # The E1 conclusion is a statement about the PRIMARY metric. Reporting only
    # that would let a secondary-metric signal disappear, so every secondary
    # metric whose paired interval excludes zero is enumerated explicitly —
    # including the direction, since for Brier score lower is better and a
    # negative delta is an IMPROVEMENT.
    secondary_excl = []
    for family, entry in bootstrap["by_family"].items():
        for metric in m.SECONDARY_METRICS:
            stat = entry["metrics"][metric]
            if stat["ci_excludes_zero"]:
                delta = stat["m3_lag_wdi_minus_m2_delta"]
                lower_is_better = metric == "brier_score"
                secondary_excl.append({
                    "model_family": family,
                    "metric": metric,
                    "delta": delta,
                    "ci_lower": stat["ci_lower"],
                    "ci_upper": stat["ci_upper"],
                    "lower_is_better": lower_is_better,
                    "favours": (
                        "M3_LAG_WDI"
                        if (delta < 0) == lower_is_better else "retained_M2"),
                })

    if all_null:
        conclusion = "E1_NULL_NO_DETECTABLE_INCREMENTAL_CONTRIBUTION"
        statement = (
            "Adding the two lagged WDI macro features to the retained M2 "
            "block produced no detectable change in out-of-fold DISCRIMINATION "
            "on the identical 539-row development sample. In every one of the "
            f"three frozen model families the paired {m.PRIMARY_METRIC} "
            "difference is small and its 95% paired company-cluster bootstrap "
            "interval includes zero.")
        if secondary_excl:
            statement += (
                " This conclusion is about the PRIMARY metric. It is not a "
                "claim that nothing moved anywhere: "
                + "; ".join(
                    f"{s['model_family']} {s['metric']} "
                    f"{s['delta']:+.6f} "
                    f"[{s['ci_lower']:+.6f}, {s['ci_upper']:+.6f}] favouring "
                    f"{s['favours']}"
                    for s in secondary_excl)
                + ". Brier score measures CALIBRATION, not ranking, so a "
                "better Brier alongside an unchanged PR-AUC is the coherent "
                "reading that the macro features shift the probability LEVEL "
                "within a year without improving the company-level ORDERING "
                "inside it — which is exactly what year-constant features "
                "would be expected to do, and is not evidence of incremental "
                "discriminative value. It remains exploratory and "
                "supplementary, and it is not a confirmatory claim.")
    elif any_excl:
        conclusion = "E1_INTERVAL_EXCLUDES_ZERO_IN_AT_LEAST_ONE_FAMILY"
        statement = (
            "At least one frozen model family shows a paired "
            f"{m.PRIMARY_METRIC} difference whose 95% interval excludes zero. "
            "This is an EXPLORATORY signal in a supplementary family; it is "
            "not a confirmatory superiority claim and cannot select the paper "
            "winner.")
    else:
        conclusion = "E1_UNCERTAINTY_NOT_ESTIMABLE_IN_AT_LEAST_ONE_FAMILY"
        statement = (
            "The paired uncertainty could not be estimated in at least one "
            "family under the frozen bootstrap validity floor, so no "
            "exploratory direction is asserted there.")

    return {
        "hypothesis_id": m.EXPLORATORY_HYPOTHESIS_ID,
        "comparison": m.EXPLORATORY_COMPARISON,
        "family": m.EXPLORATORY_FAMILY_ID,
        "conclusion": conclusion,
        "conclusion_statement": statement,
        "direction_by_family": direction,
        "primary_metric": m.PRIMARY_METRIC,
        "primary_metric_deltas": deltas,
        # Named for what it actually measures, so it can never be read as
        # "nothing anywhere excluded zero".
        "any_family_primary_metric_interval_excludes_zero": any_excl,
        "any_family_interval_excludes_zero": any_excl,
        "secondary_metric_intervals_excluding_zero": secondary_excl,
        "secondary_metric_signal_present": bool(secondary_excl),
        "secondary_metric_signal_is_confirmatory": False,
        "predictive_result": {
            "register": "1_predictive_result",
            "statement": (
                "On the identical post-complete-case development sample of "
                "539 rows (55 positives, 108 companies; 366 pooled "
                "out-of-fold rows carrying 28 positives), the 14-feature "
                "M3-LAG-WDI block was compared against the refit 12-feature "
                f"retained M2 block. Paired {m.PRIMARY_METRIC} differences "
                "by family: " + ", ".join(
                    f"{fam} {deltas[fam]['m3_lag_wdi_minus_m2_delta']:+.6f}"
                    for fam in m.MODEL_FAMILIES) + "."),
        },
        "exploratory_interpretation": {
            "register": "2_exploratory_supplementary_interpretation",
            "statement": (
                "This result belongs to the supplementary exploratory family "
                f"`{m.EXPLORATORY_FAMILY_ID}` and is labelled "
                f"`{m.RESULTS_LABEL}`. It is not a confirmatory test, it was "
                "not inserted into the confirmatory Holm family, and it "
                "neither supports nor retires any confirmatory conclusion. "
                "The block's frozen role as a "
                f"`{m.SCIENTIFIC_ROLE}` is unchanged by it."),
        },
        "statistical_uncertainty": {
            "register": "3_statistical_uncertainty",
            "statement": (
                f"Uncertainty is quantified by the frozen paired "
                f"{m.BOOTSTRAP_METHOD} on `{m.BOOTSTRAP_CLUSTER}` with "
                f"{m.BOOTSTRAP_REPLICATES} replicates at seed "
                f"{m.BOOTSTRAP_SEED}, percentile intervals at "
                f"{m.BOOTSTRAP_CI}, with the same resampled companies and "
                "rows used for both blocks in every replicate and no model "
                "refit inside the bootstrap. With 28 pooled out-of-fold "
                "positives the intervals are wide relative to the observed "
                "differences; an interval that includes zero is evidence of "
                "an undetectably small effect at this event count, not proof "
                "that the effect is exactly zero."),
            "seed_changed_after_seeing_results": False,
        },
    }


def _build_boundary(decision: dict, sample: dict) -> dict:
    """What step E is, and the long list of what it is not."""
    return {
        "action_id": m.ACTION_ID,
        # This step's own one-time authorization.
        "m3_lag_wdi_modeling_action_authorized": True,
        "m3_lag_wdi_modeling_executed": True,
        "m3_lag_wdi_modeling_started": True,
        "m3_lag_wdi_modeling_authorization_consumed": True,
        "m3_lag_wdi_modeling_authorization_reusable": False,
        "m3_lag_wdi_modeling_authorized_now": False,
        # Scientific role, unchanged.
        "m3_lag_wdi_scientific_role": m.SCIENTIFIC_ROLE,
        "m3_lag_wdi_is_confirmatory_m3": False,
        "m3_lag_wdi_replaces_m3_cbi": False,
        "m3_lag_wdi_repairs_m3_cbi": False,
        "m3_lag_wdi_replaces_m3i2": False,
        "m3_lag_wdi_is_historical_vintage_wdi": False,
        "m3_lag_wdi_is_real_time_wdi": False,
        "m3_lag_wdi_in_confirmatory_holm_family": False,
        "m3_lag_wdi_can_select_paper_winner": False,
        "m3_lag_wdi_point_in_time_availability_proven": False,
        # Prior grants stay historical and consumed.
        "retrieval_authorized_now": False,
        "post_retrieval_audit_authorized_now": False,
        "data_gate_authorized_now": False,
        "calendar_mapping_lock_authorized_now": False,
        "prior_authorization_reused_by_this_action": False,
        # Upstream state untouched.
        "step_c_rerun_by_this_action": False,
        "step_d_rerun_by_this_action": False,
        "data_gate_rerun_by_this_action": False,
        "calendar_mapping_lock_rerun_by_this_action": False,
        "calendar_mapping_changed_by_this_action": False,
        "m3_lag_wdi_contract_edited_by_this_action": False,
        "m3_lag_wdi_gate_thresholds_modified_by_this_action": False,
        "step_c_material_findings_preserved": True,
        "step_d_gate_result_preserved": True,
        "m3_lag_wdi_data_gate_result": "PASS_M3_LAG_WDI_DATA_GATE",
        "m3_lag_wdi_block_admission_is_data_admission_only": True,
        # Confirmatory surface untouched.
        "confirmatory_holm_family_changed_by_this_action": False,
        "confirmatory_holm_executed_by_this_action": False,
        "confirmatory_superiority_claim_made": False,
        "main_confirmatory_conclusion_changed_by_this_action": False,
        "paper_winner_selected_by_this_action": False,
        # Method surface untouched.
        "retuning_executed": False,
        "grid_search_executed": False,
        "model_family_search_executed": False,
        "feature_search_executed": False,
        "feature_substitution_executed": False,
        "imputation_executed": False,
        "metric_definition_changed": False,
        "validation_architecture_changed": False,
        "seed_policy_changed": False,
        "thresholds_changed": False,
        "shap_executed": False,
        # Hard locks.
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_unlocked_by_this_action": False,
        "final_test_rows_read": 0,
        "new_world_bank_request_made_by_this_action": False,
        "world_bank_inquiry_terminated_by_this_action": False,
        "m4_authorized": False,
        "merge_authorized": False,
        "ready_for_review_authorized": False,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
        # Nothing downstream is authorized by this result.
        "m3_lag_wdi_next_action_authorized": False,
        "next_action_requires_new_explicit_human_decision": True,
    }


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def _build_qc(built: dict) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    sample = built["_sample"]
    comp = sample["composition"]
    audit = built["execution_audit"]
    boundary = built["governance_boundary"]
    decision = built["decision"]
    multiplicity = built["multiplicity_status"]
    bootstrap = built["bootstrap_summary"]

    # ---- sample ---------------------------------------------------------- #
    add("common_sample_is_539_rows", comp["rows"] == 539, str(comp["rows"]))
    add("composition_55_positive_484_negative",
        comp["positive"] == 55 and comp["negative"] == 484)
    add("companies_108", comp["companies"] == 108)
    add("pooled_oof_366_rows_28_positive",
        comp["pooled_oof_rows"] == 366 and comp["pooled_oof_positive"] == 28)
    add("validation_positives_18_and_10",
        comp["validation_positives"] == {"fold1_validation": 18,
                                         "fold2_validation": 10})
    add("zero_attrition_from_the_admitted_gate_sample",
        sample["attrition"]["dropped_rows"] == 0)
    add("no_exclusions_outside_the_frozen_complete_case_rule",
        sample["attrition"]["exclusions_outside_the_frozen_complete_case_rule"]
        == 0)
    add("identical_sample_for_both_blocks",
        sample["identical_sample_for_both_blocks"] is True)
    add("no_final_test_rows_in_sample",
        sample["final_test_rows_in_sample"] == 0)

    # ---- features -------------------------------------------------------- #
    add("m2_has_exactly_12_features",
        len(m.M2_FEATURE_ORDER) == 12, str(len(m.M2_FEATURE_ORDER)))
    add("m3_lag_wdi_has_exactly_14_features",
        len(m.M3_LAG_WDI_FEATURE_ORDER) == 14,
        str(len(m.M3_LAG_WDI_FEATURE_ORDER)))
    add("exactly_two_wdi_features_added",
        len(m.WDI_FEATURE_ORDER) == 2)
    add("m2_is_nested_in_m3_lag_wdi",
        m.M3_LAG_WDI_FEATURE_ORDER[:12] == m.M2_FEATURE_ORDER)
    add("no_new_wdi_feature_missing_values",
        sample["missingness_after_construction"][
            "new_wdi_feature_missing_values"] == 0)
    add("no_new_imputation_introduced",
        sample["missingness_after_construction"][
            "new_imputation_introduced_by_this_action"] is False)
    add("calendar_mapping_is_plus_621",
        m.LOCKED_CALENDAR_OFFSET == 621)
    add("no_same_year_t_observation_read",
        sample["same_year_t_observations_read"] == 0)
    add("predictor_years_2013_to_2019",
        sample["predictor_year_first"] == 2013
        and sample["predictor_year_last"] == 2019)

    # ---- fits ------------------------------------------------------------ #
    fits = built["fit_count_audit"]
    add("primary_predictive_fits_44", fits["primary_predictive_fits"] == 44)
    add("22_fits_per_block",
        all(v == 22 for v in fits["fits_by_block"].values()))
    add("m2_fit_on_12_features",
        fits["feature_counts_by_block"]["M2"] == [12])
    add("m3_lag_wdi_fit_on_14_features",
        fits["feature_counts_by_block"]["M3_LAG_WDI"] == [14])
    add("no_tuning_or_grid_search_fits",
        fits["tuning_fits"] == 0 and fits["grid_search_fits"] == 0)
    add("no_final_test_fits", fits["final_test_fits"] == 0)

    # ---- comparator refit ------------------------------------------------ #
    rec = built["_comparator_reconciliation"]
    add("refit_m2_reproduces_committed_retained_m2",
        rec["refit_reproduces_committed_retained_m2"] is True,
        f"{rec['mismatches']} mismatches over {rec['comparisons']} values")
    add("m1_666_row_results_not_used_as_comparator",
        rec["committed_m1_666_row_results_used_as_comparator"] is False)

    # ---- uncertainty ----------------------------------------------------- #
    add("bootstrap_seed_is_the_frozen_one",
        bootstrap["seed"] == m.BOOTSTRAP_SEED)
    add("bootstrap_2000_replicates",
        bootstrap["replicates_attempted"] == 2000)
    add("every_family_meets_the_valid_replicate_floor",
        all(v["minimum_valid_replicates_met"]
            for v in bootstrap["by_family"].values()))
    add("same_resampled_rows_for_both_blocks",
        bootstrap["same_resampled_rows_for_both_blocks"] is True)
    add("models_not_refit_during_bootstrap",
        bootstrap["models_refit_during_bootstrap"] is False)
    add("bootstrap_seed_not_changed_after_seeing_results",
        bootstrap["seed_changed_after_seeing_results"] is False)

    # ---- family separation ----------------------------------------------- #
    add("e1_is_in_the_exploratory_family",
        multiplicity["exploratory_family_id"] == m.EXPLORATORY_FAMILY_ID)
    add("e1_not_inserted_into_confirmatory_holm_family",
        multiplicity[
            "exploratory_comparison_inserted_into_confirmatory_family"]
        is False)
    add("confirmatory_holm_family_unchanged",
        multiplicity["confirmatory_holm_family_changed_by_this_action"]
        is False)
    add("confirmatory_holm_not_executed",
        multiplicity["confirmatory_holm_executed_by_this_action"] is False)
    add("confirmatory_holm_family_is_the_three_frozen_members",
        multiplicity["confirmatory_holm_family"]
        == list(m.CONFIRMATORY_HOLM_FAMILY))
    add("no_confirmatory_superiority_claim",
        decision["confirmatory_superiority_claim_made"] is False)
    add("no_paper_winner_selected", decision["paper_winner_selected"] is False)
    add("results_labelled_supplementary_exploratory_only",
        decision["results_label"] == m.RESULTS_LABEL)
    # A secondary-metric signal must be REPORTED, not silently dropped behind
    # a primary-metric null — and must not be promoted either.
    add("secondary_metric_signals_are_enumerated_not_hidden",
        isinstance(decision["e1_secondary_metric_intervals_excluding_zero"],
                   list),
        f"{len(decision['e1_secondary_metric_intervals_excluding_zero'])} "
        "secondary interval(s) exclude zero")
    add("secondary_metric_signal_is_not_confirmatory",
        decision["e1_secondary_metric_signal_is_confirmatory"] is False)

    # ---- limitations preserved ------------------------------------------- #
    ids = {item["id"] for item in decision["limitations"]}
    for required in ("point_in_time_wdi_availability_unproven",
                     "lagging_does_not_create_point_in_time_data",
                     "fx_degenerate_2021_2024", "fx_missing_2024_2025",
                     "exploratory_role_is_frozen",
                     "macro_features_are_year_level_not_company_level"):
        add(f"limitation_preserved__{required}", required in ids)
    add("no_limitation_marked_resolved_by_this_action",
        all(item["resolved_by_this_action"] is False
            for item in decision["limitations"]))
    add("no_limitation_erased_by_a_favourable_result",
        all(item["erased_by_a_favourable_predictive_result"] is False
            for item in decision["limitations"]))

    # ---- zero counters --------------------------------------------------- #
    for counter in _ZERO_COUNTERS:
        add(f"zero_counter__{counter}", audit[counter] == 0,
            str(audit[counter]))

    # ---- firewall and locks ---------------------------------------------- #
    fw = built["firewall_audit"]
    add("final_test_rows_read_is_zero", fw["final_test_rows_read"] == 0)
    add("final_test_target_values_read_is_zero",
        fw["final_test_target_values_read"] == 0)
    add("final_test_locked", fw["final_test_locked"] is True)
    add("final_test_not_unlocked",
        fw["final_test_unlocked_by_this_action"] is False)
    add("firewall_intact", fw["firewall_intact"] is True)

    # ---- authorization semantics ----------------------------------------- #
    add("modeling_authorization_consumed",
        boundary["m3_lag_wdi_modeling_authorization_consumed"] is True)
    add("modeling_authorization_not_standing",
        boundary["m3_lag_wdi_modeling_authorized_now"] is False)
    add("modeling_authorization_not_reusable",
        boundary["m3_lag_wdi_modeling_authorization_reusable"] is False)
    add("no_prior_authorization_reused",
        boundary["prior_authorization_reused_by_this_action"] is False)
    add("next_action_not_authorized",
        decision["next_action_authorized"] is False)
    add("merge_not_authorized", boundary["merge_authorized"] is False)
    add("ready_for_review_not_authorized",
        boundary["ready_for_review_authorized"] is False)
    add("m4_not_authorized", boundary["m4_authorized"] is False)

    failed = [c for c in checks if not c["pass"]]
    return {
        "action_id": m.ACTION_ID,
        "assertions": len(checks),
        "failed": len(failed),
        "all_pass": not failed,
        "failed_checks": failed,
        "checks": checks,
    }


# --------------------------------------------------------------------------- #
# Write / verify
# --------------------------------------------------------------------------- #

def _secondary_table(e1: dict) -> str:
    rows = e1["secondary_metric_intervals_excluding_zero"]
    if not rows:
        return ("No secondary metric's paired interval excludes zero in any "
                "family.")
    body = "\n".join(
        f"| `{s['model_family']}` | `{s['metric']}` | {s['delta']:+.6f} | "
        f"[{s['ci_lower']:+.6f}, {s['ci_upper']:+.6f}] | "
        f"{'lower is better' if s['lower_is_better'] else 'higher is better'} "
        f"| {s['favours']} |"
        for s in rows)
    return ("| Family | Metric | Delta | 95% CI | Direction | Favours |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + body)


def _readme(built: dict) -> str:
    e1 = built["_e1"]
    sample = built["_sample"]
    comp = sample["composition"]
    bs = built["bootstrap_summary"]["by_family"]
    rows = "\n".join(
        f"| `{fam}` | "
        f"{bs[fam]['metrics']['pr_auc']['m2_estimate']:.6f} | "
        f"{bs[fam]['metrics']['pr_auc']['m3_lag_wdi_estimate']:.6f} | "
        f"{bs[fam]['metrics']['pr_auc']['m3_lag_wdi_minus_m2_delta']:+.6f} | "
        f"[{bs[fam]['metrics']['pr_auc']['ci_lower']:+.6f}, "
        f"{bs[fam]['metrics']['pr_auc']['ci_upper']:+.6f}] | "
        f"`{e1['direction_by_family'][fam]}` |"
        for fam in m.MODEL_FAMILIES)
    limits = "\n".join(
        f"- **{item['id']}** — {item['statement']}"
        for item in built["decision"]["limitations"])
    years = "\n".join(
        f"| {year} | {v['rows']} | {v[m.CPI_FEATURE_ID]:.6f} | "
        f"{v[m.FX_FEATURE_ID]:.6f} |"
        for year, v in sample["wdi_values_by_predictor_year"].items())
    return f"""# Stage128 — Track B step E: the M3-LAG-WDI EXPLORATORY INCREMENTAL EVALUATION

**Action:** `{m.ACTION_ID}`
**Authorized scope:** `{m.AUTHORIZED_SCOPE}`
**Comparison:** `{m.EXPLORATORY_COMPARISON}` (hypothesis `{m.EXPLORATORY_HYPOTHESIS_ID}`)
**Family:** `{m.EXPLORATORY_FAMILY_ID}`
**Results label:** `{m.RESULTS_LABEL}`
**E1 conclusion:** `{e1['conclusion']}`

## What this action is

The one authorized execution of the pre-frozen step-E modeling contract. It
materialized the M3-LAG-WDI modeling feature-value table for the first time
(step D deliberately produced row STATUSES only, because feature values are
not invariant to the calendar convention that was unlocked at the time),
refit the retained M2 comparator and the 14-feature M3-LAG-WDI block on the
IDENTICAL development sample, and computed the paired exploratory comparison.

**It made no new scientific design choice.** Every rule it applied — the
calendar mapping, the two features, the complete-case policy, the three model
configurations, the validation windows, the metric definitions, the seed
policy and the bootstrap machinery — was frozen before it ran, and is re-read
from committed bytes at run time so drift fails closed.

## The sample

| Quantity | Value |
| --- | --- |
| Rows | {comp['rows']} |
| Positives / negatives | {comp['positive']} / {comp['negative']} |
| Companies | {comp['companies']} |
| Event rate | {comp['event_rate']:.6f} |
| Pooled out-of-fold rows | {comp['pooled_oof_rows']} |
| Pooled out-of-fold positives | {comp['pooled_oof_positive']} |
| Validation positives | fold1 {comp['validation_positives']['fold1_validation']}, fold2 {comp['validation_positives']['fold2_validation']} |
| Attrition from the step D admitted sample | {sample['attrition']['dropped_rows']} |
| Final Test rows | 0 |

Both blocks were evaluated on exactly these rows. The retained M2 comparator
was **refit** here, never imported: the previously published M1 666-row
results were not used as the comparator. Because both WDI features are
constructible for all 539 rows, the frozen complete-case rule removed
nothing, so the step-E sample is mechanically the retained-M2 sample — and
the refit M2 reproduces the committed retained-M2 metrics exactly
({built['_comparator_reconciliation']['comparisons']} values compared,
{built['_comparator_reconciliation']['mismatches']} mismatches).

## The features

Calendar mapping: `{m.LOCKED_CALENDAR_FORMULA}` (locked; offset
{m.LOCKED_CALENDAR_OFFSET}, rejected offset {m.REJECTED_CALENDAR_OFFSET}).

* `{m.CPI_FEATURE_ID}` — `{m.CPI_CODE}`, observation year **t-1**, identity.
* `{m.FX_FEATURE_ID}` — `{m.FX_CODE}`,
  `FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))`, observation years **t-1** and
  **t-2**.

No same-year `t` observation was read ({sample['same_year_t_observations_read']}).
Comparator = **{m.EXPECTED_M2_FEATURE_COUNT}** features; exploratory block =
**{m.EXPECTED_M3_LAG_WDI_FEATURE_COUNT}** features. No third macro feature, no
feature search, no selection, no substitution, no imputation.

Both are NATIONAL annual series, so within a predictor year every company
carries the same value:

| Predictor year | Rows | CPI lag1 | FX change lag1 |
| --- | --- | --- | --- |
{years}

## Result — exploratory, supplementary

Primary metric `{m.PRIMARY_METRIC}`, pooled out-of-fold, paired
{m.BOOTSTRAP_METHOD} on `{m.BOOTSTRAP_CLUSTER}`
({m.BOOTSTRAP_REPLICATES} replicates, seed {m.BOOTSTRAP_SEED},
percentile intervals at {m.BOOTSTRAP_CI}):

| Family | retained M2 | M3-LAG-WDI | delta | 95% CI | Direction |
| --- | --- | --- | --- | --- | --- |
{rows}

{e1['conclusion_statement']}

### Secondary metrics — reported, not hidden behind the primary null

The conclusion above is about the **primary** metric. Every secondary metric
whose paired interval excludes zero is enumerated here so it cannot vanish
behind a primary-metric null:

{_secondary_table(e1)}

### The four mandated registers

1. **Predictive result.** {e1['predictive_result']['statement']}
2. **Exploratory interpretation.** {e1['exploratory_interpretation']['statement']}
3. **Statistical uncertainty.** {e1['statistical_uncertainty']['statement']}
4. **Limitations.** Below — none of them resolved by this action.

## Limitations that survive this result

{limits}

## Where this action stopped

Final Test rows read: `0` · new World Bank requests: `0` · step C reruns:
`0` · step D / Gate reruns: `0` · calendar-lock reruns: `0` · retuning or
grid searches: `0` · SHAP executions: `0` · confirmatory Holm executions:
`0` · paper-winner selections: `0`.

The step-E authorization is **consumed** and is not reusable. No next action
is authorized: PR #79 stays a Draft, the Final Test stays locked, M4 stays
unauthorized, and the confirmatory conclusions are exactly what they were
before this ran.
"""


def _execute(bundle_dir: str) -> int:
    built = _build(bundle_dir, scientific=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    for key, filename in _ARTIFACT_FILES.items():
        _write_json(PACKAGE_DIR / filename, built[key])
    _write_csv(PACKAGE_DIR / _FEATURES_CSV, m.FEATURE_VALUE_COLUMNS,
               built["_feature_rows"])
    _write_csv(PACKAGE_DIR / _OOF_CSV, m.OOF_COLUMNS, built["_oof_rows"])
    _write_csv(PACKAGE_DIR / _METRICS_CSV, m.METRICS_COLUMNS,
               built["_metrics_rows"])
    (PACKAGE_DIR / _README_FILE).write_text(_readme(built), encoding="utf-8")

    tracked = (list(_ARTIFACT_FILES.values())
               + [_FEATURES_CSV, _OOF_CSV, _METRICS_CSV, _README_FILE])
    _write_json(PACKAGE_DIR / _METADATA_FILE, {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "package_id": m.PACKAGE_ID,
        "source_module": m.SRC_REL,
        "source_module_sha256": _sha256_file(ROOT / m.SRC_REL),
        "runner": m.RUN_REL,
        "runner_sha256": _sha256_file(ROOT / m.RUN_REL),
        "artifacts": {name: _sha256_file(PACKAGE_DIR / name)
                      for name in sorted(tracked)},
        "artifact_count": len(tracked),
        "execution_environment": m.execution_environment(scientific=True),
        "execution_count_semantics": m.EXECUTION_COUNT_SEMANTICS,
    })
    return _report(built)


def _check() -> int:
    manifest_path = PACKAGE_DIR / _METADATA_FILE
    if not manifest_path.is_file():
        print(f"MISSING: {manifest_path}", file=sys.stderr)
        return 1
    bundle_dir = os.environ.get("M3_LAG_WDI_BUNDLE_DIR", "")
    if not bundle_dir:
        # Offline verification of the committed artifacts only. The retained
        # payloads live outside the repository (they carry no PII, but the
        # repo stores digests, not bytes), so a full recomputation needs the
        # bundle path; without it the committed package is still verified for
        # internal consistency and digest integrity.
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bad = [name for name, digest in manifest["artifacts"].items()
               if _sha256_file(PACKAGE_DIR / name) != digest]
        if bad:
            print(f"DIGEST MISMATCH: {bad}", file=sys.stderr)
            return 1
        qc = json.loads(
            (PACKAGE_DIR / _ARTIFACT_FILES["qc_report"]).read_text(
                encoding="utf-8"))
        print("Stage128 — M3-LAG-WDI step E (committed-package check)")
        print(f"  artifacts verified: {len(manifest['artifacts'])}")
        print(f"  QC: {qc['assertions']} assertions, {qc['failed']} failed, "
              f"all_pass={qc['all_pass']}")
        print("  NOTE: set M3_LAG_WDI_BUNDLE_DIR to also recompute the models.")
        return 0 if qc["all_pass"] and not bad else 1

    built = _build(bundle_dir, scientific=False)
    failures: list[str] = []
    for key, filename in _ARTIFACT_FILES.items():
        if key in ("execution_contract",):
            continue  # carries the environment of the current interpreter
        committed = json.loads(
            (PACKAGE_DIR / filename).read_text(encoding="utf-8"))
        if committed != built[key]:
            failures.append(filename)
    if failures:
        print(f"RECOMPUTATION MISMATCH: {failures}", file=sys.stderr)
        return 1
    return _report(built)


def _report(built: dict) -> int:
    qc = built["qc_report"]
    e1 = built["_e1"]
    bs = built["bootstrap_summary"]["by_family"]
    print("=" * 70)
    print("Stage128 — M3-LAG-WDI step E: exploratory incremental evaluation")
    print("=" * 70)
    print(f"Action: {m.ACTION_ID}")
    print(f"Sample: {built['_sample']['composition']['rows']} rows — "
          f"pooled OOF: "
          f"{built['_sample']['composition']['pooled_oof_rows']}")
    print(f"Blocks: M2 = {m.EXPECTED_M2_FEATURE_COUNT} features | "
          f"M3-LAG-WDI = {m.EXPECTED_M3_LAG_WDI_FEATURE_COUNT} features")
    print(f"Primary predictive model fits: "
          f"{built['fit_count_audit']['primary_predictive_fits']}")
    for family in m.MODEL_FAMILIES:
        pr = bs[family]["metrics"][m.PRIMARY_METRIC]
        print(f"  {family}: M2 PR-AUC {pr['m2_estimate']:.12f} | "
              f"M3-LAG-WDI {pr['m3_lag_wdi_estimate']:.12f} | "
              f"delta {pr['m3_lag_wdi_minus_m2_delta']:+.12f} | "
              f"95% CI [{pr['ci_lower']:+.12f}, {pr['ci_upper']:+.12f}] | "
              f"{e1['direction_by_family'][family]}")
    print(f"E1: {e1['conclusion']}")
    print(f"QC: {qc['assertions']} assertions, {qc['failed']} failed, "
          f"all_pass={qc['all_pass']}")
    print("Family: EXPLORATORY SUPPLEMENTARY — confirmatory Holm untouched.")
    print("Final-test access: 0 — Final Test remains locked.")
    if not qc["all_pass"]:
        for check in qc["failed_checks"]:
            print(f"  FAILED: {check['check']} {check['detail']}",
                  file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", metavar="BUNDLE_DIR",
                       help="the ONE authorized step E run (offline)")
    group.add_argument("--check", action="store_true",
                       help="offline verification of the committed package")
    args = parser.parse_args(argv)
    if args.execute:
        return _execute(args.execute)
    return _check()


if __name__ == "__main__":
    raise SystemExit(main())
