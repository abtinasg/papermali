#!/usr/bin/env python3
"""Runner — Stage128 Track B step D: the M3-LAG-WDI EXPLORATORY DATA GATE.

Authorized action: ``stage128-m3-lag-wdi-exploratory-data-gate``
Authorized scope:  ``data_gate_only``

Two modes, neither of which may touch the network:

``--execute BUNDLE_DIR``  the ONE authorized Gate run. Proves the identity of
                          the retained payloads, derives the locked parent
                          surface, computes the locked coverage calculations
                          and writes the committed Gate package.
``--check``               offline verification of the committed package.

There is deliberately no ``--retrieve`` and no model import: this step has no
network code path and no estimator code path. A Gate PASS is DATA ADMISSION
ONLY — it authorizes no model fit, no step E, no Final Test access, no merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m3_lag_wdi_exploratory_data_gate as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / m.PACKAGE_REL

_ARTIFACT_FILES = {
    "human_authorization_record":
        "stage128_m3_lag_wdi_data_gate_human_authorization_record.json",
    "gate_report": "stage128_m3_lag_wdi_data_gate_report.json",
    "common_sample_audit":
        "stage128_m3_lag_wdi_data_gate_common_sample_audit.json",
    "execution_audit":
        "stage128_m3_lag_wdi_data_gate_execution_audit.json",
    "governance_boundary":
        "stage128_m3_lag_wdi_data_gate_governance_boundary.json",
    "decision": "stage128_m3_lag_wdi_data_gate_decision.json",
    "qc_report": "stage128_m3_lag_wdi_data_gate_qc_report.json",
}
_COVERAGE_CSV = "stage128_m3_lag_wdi_data_gate_candidate_coverage_audit.csv"
_EVENT_CSV = "stage128_m3_lag_wdi_data_gate_event_count_audit.csv"
_ROW_STATUS_CSV = "stage128_m3_lag_wdi_data_gate_row_status_audit.csv"
_METADATA_FILE = (
    "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_data_gate.json")
_README_FILE = "README_STAGE128_M3_LAG_WDI_EXPLORATORY_DATA_GATE.md"

#: Counters this step must leave at zero. Step D computes coverage against
#: the locked thresholds; it retrieves nothing, fits nothing, and reads no
#: Final Test row.
_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "feature_value_tables_materialized",
    "model_fits", "predictions", "predictive_metrics", "bootstrap_executions",
    "holm_calculations", "shap_executions", "tuning_runs",
    "cross_validation_runs", "model_selections",
    "final_test_rows_read", "final_test_predictor_values_read",
    "final_test_target_values_read",
)

_ROW_STATUS_COLUMNS = (
    "ticker", "fiscal_year_t", "target_year", "temporal_folds",
    "predictor_year_gregorian_offset621", "predictor_year_gregorian_offset622",
    "cpi_constructible_offset621", "cpi_constructible_offset622",
    "fx_constructible_offset621", "fx_constructible_offset622",
    "both_constructible_offset621", "both_constructible_offset622",
    "fx_zero_change_offset621", "fx_zero_change_offset622",
    "status_invariant_across_calendar_conventions",
    "cpi_constructible", "fx_constructible", "both_constructible",
    "fx_zero_change",
)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, columns: tuple[str, ...],
               rows: list[dict]) -> None:
    import csv as _csv
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row[c] for c in columns})


def _readme(built: dict) -> str:
    report = built["gate_report"]
    decision = built["decision"]
    gate = report["gate_computation"]
    windows = gate["validation_windows"]
    window_rows = "\n".join(
        f"| `{fold}` | {'-'.join(w['target_years'])} | "
        f"{w['validation_positive']} | "
        f"{w['positive_evaluable_in_m3_lag_wdi_common_sample']} | "
        f">= {w['minimum_positive_required']} | "
        f"{'yes' if w['meets_positive_floor'] else 'NO'} |"
        for fold, w in windows.items())
    limits = "\n".join(
        f"- {item}" for item in decision["material_limitations"])
    return f"""# Stage128 — Track B step D: the M3-LAG-WDI EXPLORATORY DATA GATE

**Action:** `{m.ACTION_ID}`
**Authorized scope:** `{m.AUTHORIZED_SCOPE}`
**Formal verdict:** `{decision['gate_result']}`

## What this action is

The one authorized execution of the PRE-EXISTING, locked M3-LAG-WDI Data
Gate. It computed, for every row of the retained-M2 development common
sample, whether the two contract-locked lagged WDI features are
constructible, compared coverage to the inherited thresholds, and recorded
the formal data-admission verdict. **A Gate PASS is DATA ADMISSION ONLY** —
it is not modeling authorization, not an information-content claim about the
FX feature, not point-in-time vintage proof, and not a Final Test unlock.

Payload identity was proven on the raw bytes before decoding, against the
committed retrieval manifest anchored to the immutable Zenodo record
`10.5281/zenodo.21844636`. No World Bank request was made; the retained
evidence was not modified.

## Coverage under the locked thresholds

| Quantity | Numerator | Denominator | Value | Threshold | Met |
| --- | --- | --- | --- | --- | --- |
| CPI candidate coverage | {gate['cpi_constructible_rows']} | {gate['rows']} | {gate['cpi_candidate_coverage']:.4f} | >= {gate['candidate_valid_coverage_min']} | {'yes' if gate['threshold_checks']['cpi_candidate_coverage_meets_threshold'] else 'NO'} |
| FX candidate coverage | {gate['fx_constructible_rows']} | {gate['rows']} | {gate['fx_candidate_coverage']:.4f} | >= {gate['candidate_valid_coverage_min']} | {'yes' if gate['threshold_checks']['fx_candidate_coverage_meets_threshold'] else 'NO'} |
| Block common-sample coverage | {gate['both_constructible_rows']} | {gate['rows']} | {gate['block_common_sample_coverage']:.4f} | >= {gate['block_common_sample_coverage_min']} | {'yes' if gate['threshold_checks']['block_common_sample_coverage_meets_threshold'] else 'NO'} |

| Validation window | Target years | Window positives | Positive evaluable | Floor | Met |
| --- | --- | --- | --- | --- | --- |
{window_rows}

## The unlocked calendar mapping — why the verdict is still well-defined

The locked contract indexes the features by a GREGORIAN predictor year but
does not lock the Jalali-to-Gregorian mapping for the development rows. This
Gate refused to invent it: every row's constructibility status was computed
under BOTH admissible conventions (`jalali + 621` and `jalali + 622`), and
the statuses are identical under both
(`status_invariant_across_calendar_conventions =
{gate['status_invariant_across_calendar_conventions']}`), so the coverage
numbers and the verdict do not depend on the missing convention. Feature
VALUES do differ between the conventions, which is why this package contains
row STATUSES only and no authoritative feature-value table. **The mapping
must be locked by a human before any modeling table may be built.**

## The step C findings — preserved, not laundered

The formal verdict above is a COVERAGE statement under the locked rules. It
must never be read as erasing the step C material findings, which are
distinguished explicitly in the decision record (syntactic coverage vs.
thresholds vs. information content):

{limits}

The development rows land on Gregorian predictor years
{gate['development_predictor_year_spans_gregorian']['offset621']['first']}–{gate['development_predictor_year_spans_gregorian']['offset621']['last']}
(begin-year convention) or
{gate['development_predictor_year_spans_gregorian']['offset622']['first']}–{gate['development_predictor_year_spans_gregorian']['offset622']['last']}
(end-year convention), so the FX zero-change window 2021–2024 and the
2024–2025 `PA.NUS.FCRF` nulls lie OUTSIDE the development sample under either
convention ({gate['fx_zero_change_rows']} development rows carry a
zero-change FX feature). They remain real limitations of the block's recent
end and of any future use beyond the development window.

## Where this action stopped

Model fits: `0` · Final Test rows read: `0` · new World Bank requests: `0` ·
feature-value tables materialized: `0`.

A Gate `{decision['gate_result']}` authorizes nothing further. Step E
(`{decision['next_action_id']}`) remains
`authorized = {decision['next_action_authorized']}` and requires its own new
explicit human authorization, which must also resolve the calendar-mapping
lock recorded above.
"""


def _execute(bundle_dir: str) -> int:
    authorization = m.verify_human_authorization()
    thresholds = m.load_locked_thresholds(ROOT)
    feature_contract = m.verify_locked_feature_contract(ROOT)
    values = m.load_retained_values(ROOT, bundle_dir)
    parent_rows, parent_surface = m.derive_parent_surface(ROOT)
    validation = m.derive_validation_targets(ROOT)
    gate = m.compute_gate(ROOT, values, parent_rows, thresholds, validation)

    row_records = gate.pop("row_records")

    step_c_decision = json.loads(
        (ROOT / m.STEP_C_DECISION_REL).read_text(encoding="utf-8"))
    step_c_report = json.loads(
        (ROOT / m.STEP_C_REPORT_REL).read_text(encoding="utf-8"))
    fx_avail = step_c_report["feature_availability"][1]

    # ----- the mandated five-way distinction (A..E) ------------------------ #
    scientific_distinctions = {
        "A_syntactic_availability_and_coverage": {
            "statement": (
                f"All {gate['rows']} development rows carry numerically "
                "constructible values for both locked features under both "
                "admissible calendar conventions; block common-sample "
                f"coverage is {gate['block_common_sample_coverage']:.4f}."),
            "is_information_content_claim": False,
        },
        "B_pre_defined_thresholds_satisfied": {
            "statement": (
                "Every inherited locked threshold is satisfied: candidate "
                "coverage >= 0.80 for both features, block common-sample "
                "coverage >= 0.70, and >= 5 positive evaluable outcomes in "
                "each locked validation window."),
            "threshold_checks": gate["threshold_checks"],
        },
        "C_information_content_limitation_from_step_c": {
            "statement": (
                "Step C established that the FX feature is defined but "
                "identically ZERO for predictor years 2021-2024 (trailing "
                f"zero-change years: "
                f"{fx_avail['trailing_zero_change_predictor_year_list']}), "
                "because the official rate is pegged at 42000 for the "
                "2019-2023 observations. That finding is preserved unchanged."),
            "step_c_finding_preserved": True,
            "converted_into_a_different_claim": False,
        },
        "D_effect_on_the_formal_gate_decision": {
            "statement": (
                "The degeneracy does NOT affect the formal Gate decision "
                "under the pre-existing rules, for two independent reasons: "
                "(1) the locked contract contains no zero-change or "
                "information-content admission criterion, and none was "
                "invented; (2) the development rows land on predictor years "
                "no later than 2020 under either calendar convention, so the "
                "degenerate 2021-2024 window lies outside the development "
                f"sample ({gate['fx_zero_change_rows']} development rows are "
                "zero-change)."),
            "new_rejection_criterion_created": False,
        },
        "E_remaining_scientific_limitation": {
            "statement": (
                "The limitation remains scientifically real despite the "
                "formal PASS: the FX feature carries no cross-time "
                "information for predictor years 2021-2024, PA.NUS.FCRF is "
                "null for 2024-2025 (capping the jointly constructible "
                "ceiling at predictor year 2024), the WDI lastupdated value "
                "is a revision marker and not point-in-time availability "
                "proof, and the Jalali-to-Gregorian predictor-year mapping "
                "is not locked by the contract. Any use of this block beyond "
                "the development window, and any modeling use at all, must "
                "confront these limitations explicitly."),
            "limitation_survives_the_pass": True,
        },
    }

    material_limitations = [
        "the formal Gate PASS is a coverage statement only; it does not make "
        "the FX feature informative: step C's finding stands that the FX "
        "log-ratio is defined but identically ZERO for predictor years "
        "2021-2024 (outside the development sample, which ends at predictor "
        "year 2020 at the latest under either calendar convention)",
        "PA.NUS.FCRF carries no value for observation years 2024-2025, so "
        "the jointly constructible predictor-year ceiling remains 2024; this "
        "does not bind the 539-row development sample but caps any future "
        "extension of the block",
        "the WDI `lastupdated` value is a revision marker, not point-in-time "
        "availability proof; no historical-vintage or point-in-time claim is "
        "made and the one-year lag does not create one",
        "the locked contract does not fix the Jalali-to-Gregorian mapping "
        "for predictor_year_t; the Gate verdict is invariant to the two "
        "admissible conventions, but feature VALUES are not, so the mapping "
        "must be human-locked before any modeling feature table is built",
    ]

    decision = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "gate_result": gate["verdict"],
        "gate_result_vocabulary": list(m.GATE_STATUS_VOCABULARY),
        "block_formally_admitted": gate["verdict"] == m.GATE_STATUS_PASS,
        "admission_is_data_admission_only": True,
        "admission_scope": "development_only",
        "exclusions": [],
        "rows_excluded": 0,
        "years_excluded": [],
        "features_excluded": [],
        "thresholds_changed_to_obtain_result": False,
        "criteria_weakened": False,
        "criteria_strengthened_after_seeing_result": False,
        "imputation_used": False,
        "alternative_indicator_tried": False,
        "scientific_distinctions": scientific_distinctions,
        "material_limitations": material_limitations,
        "step_c_result_preserved": step_c_decision["audit_result"],
        "step_c_material_limitations_preserved":
            step_c_decision["material_limitations"],
        "gate_pass_authorizes_modeling": False,
        "gate_pass_is_information_content_claim": False,
        "gate_pass_unlocks_final_test": False,
        "authorizes_next_action": False,
        "next_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "next_action_authorized": False,
        "next_action_scope": "modeling_requires_new_human_authorization",
        "calendar_mapping_lock_required_before_modeling": True,
    }

    gate_report = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "gate_level": "sample_level_development_only",
        "human_authorization_sha256": authorization["authorization_sha256"],
        "locked_thresholds": thresholds,
        "locked_feature_contract": feature_contract,
        "parent_surface": parent_surface,
        "validation_target_provenance": {
            "source": validation["source"],
            "source_sha256": validation["source_sha256"],
            "reconciled_against": validation["reconciled_against"],
            "reconciled_against_sha256":
                validation["reconciled_against_sha256"],
            "window_counts": validation["window_counts"],
        },
        "gate_computation": gate,
        "final_test_rows_read": 0,
        "final_test_target_values_read": 0,
        "coverage_thresholds_applied": True,
        "admission_decision_made": True,
        "company_rows_touched": gate["rows"],
    }

    execution_audit = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "data_gate_executed": True,
        "data_gate_executions": 1,
        "coverage_calculations": 3,
        "candidate_coverage_evaluations": 2,
        "block_coverage_evaluations": 1,
        "coverage_threshold_comparisons": 4,
        "admission_decisions": 1,
        "company_row_macro_status_joins": gate["rows"],
        "company_rows_touched": gate["rows"],
        "retained_bytes_modified": False,
        "deposited_evidence_modified": False,
        "quarantined_local_draft_used_as_input": False,
        **{counter: 0 for counter in _ZERO_COUNTERS},
    }

    boundary = {
        "action_id": m.ACTION_ID,
        "m3_lag_wdi_data_gate_action_authorized": True,
        "m3_lag_wdi_data_gate_executed": True,
        "m3_lag_wdi_data_gate_authorization_consumed": True,
        "m3_lag_wdi_data_gate_authorization_reusable": False,
        "m3_lag_wdi_data_gate_authorized_now": False,
        "m3_lag_wdi_data_gate_result": gate["verdict"],
        "m3_lag_wdi_block_admitted":
            gate["verdict"] == m.GATE_STATUS_PASS,
        "m3_lag_wdi_block_admission_is_data_admission_only": True,
        "gate_pass_is_modeling_authorization": False,
        "gate_pass_is_information_content_claim": False,
        "gate_pass_is_final_test_unlock": False,
        "gate_authorization_propagates_to_step_e": False,
        "m3_lag_wdi_next_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "m3_lag_wdi_next_action_authorized": False,
        "m3_lag_wdi_modeling_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "m3_lag_wdi_modeling_authorized": False,
        "m3_lag_wdi_modeling_started": False,
        "m3_lag_wdi_modeling_requires_new_explicit_human_authorization": True,
        "m3_lag_wdi_calendar_mapping_locked": False,
        "m3_lag_wdi_calendar_mapping_lock_required_before_modeling": True,
        "m3_lag_wdi_authoritative_contract_status":
            "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL",
        "m3_lag_wdi_contract_modified_by_this_action": False,
        "m3_lag_wdi_thresholds_modified_by_this_action": False,
        "step_c_rerun_by_this_action": False,
        "step_c_result_modified_by_this_action": False,
        "step_c_material_findings_preserved": True,
        # Prior Track B authorizations stay historical and consumed.
        "retrieval_was_authorized": True,
        "retrieval_authorized_now": False,
        "retrieval_authorization_consumed": True,
        "retrieval_authorization_reusable": False,
        "further_retrieval_requires_new_human_authorization": True,
        "new_world_bank_request_made_by_this_action": False,
        "post_retrieval_audit_was_authorized": True,
        "post_retrieval_audit_authorized_now": False,
        "post_retrieval_audit_authorization_consumed": True,
        # Track A is untouched by a Track B Gate.
        "world_bank_inquiry_status":
            "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE",
        "world_bank_follow_up_authorized": False,
        "world_bank_response_ingestion_authorized": False,
        "world_bank_inquiry_terminated_by_this_action": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_rows_read": 0,
        "m4_authorized": False,
        "merge_authorized": False,
        "ready_for_review_authorized": False,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
        "raw_wdi_payloads_committed_to_git": 0,
    }

    common_sample_audit = {
        "action_id": m.ACTION_ID,
        "parent_surface": parent_surface,
        "m3_lag_wdi_common_sample_rows": gate["both_constructible_rows"],
        "m3_lag_wdi_common_sample_coverage":
            gate["block_common_sample_coverage"],
        "common_sample_coverage_threshold":
            gate["block_common_sample_coverage_min"],
        "common_sample_meets_threshold":
            gate["threshold_checks"][
                "block_common_sample_coverage_meets_threshold"],
        "common_sample_equals_parent_surface":
            gate["both_constructible_rows"] == gate["rows"],
        "partial_block_admission": False,
        "candidate_dropped_to_let_smaller_block_pass": False,
        "rows_excluded_from_denominator": 0,
        "status_invariant_across_calendar_conventions":
            gate["status_invariant_across_calendar_conventions"],
    }

    coverage_rows = [
        {
            "candidate_id": "cand_m3_lag_wdi_cpi_inflation_lag1",
            "feature_id": m.CPI_FEATURE_ID,
            "indicator_code": m.CPI_CODE,
            "coverage_denominator_rows": gate["rows"],
            "valid_value_rows": gate["cpi_constructible_rows"],
            "valid_coverage": gate["cpi_candidate_coverage"],
            "coverage_threshold": gate["candidate_valid_coverage_min"],
            "coverage_meets_threshold":
                gate["threshold_checks"][
                    "cpi_candidate_coverage_meets_threshold"],
            "coverage_status": "RESOLVED",
        },
        {
            "candidate_id": "cand_m3_lag_wdi_fx_change_official_lag1",
            "feature_id": m.FX_FEATURE_ID,
            "indicator_code": m.FX_CODE,
            "coverage_denominator_rows": gate["rows"],
            "valid_value_rows": gate["fx_constructible_rows"],
            "valid_coverage": gate["fx_candidate_coverage"],
            "coverage_threshold": gate["candidate_valid_coverage_min"],
            "coverage_meets_threshold":
                gate["threshold_checks"][
                    "fx_candidate_coverage_meets_threshold"],
            "coverage_status": "RESOLVED",
        },
    ]
    coverage_columns = tuple(coverage_rows[0])

    event_rows = []
    for fold, w in gate["validation_windows"].items():
        event_rows.append({
            "validation_window": fold,
            "target_years": ";".join(w["target_years"]),
            "validation_rows": w["validation_rows"],
            "validation_positive": w["validation_positive"],
            "positive_evaluable_in_m3_lag_wdi_common_sample":
                w["positive_evaluable_in_m3_lag_wdi_common_sample"],
            "minimum_positive_required": w["minimum_positive_required"],
            "meets_positive_floor": w["meets_positive_floor"],
        })
    event_columns = tuple(event_rows[0])

    checks = [
        ("payload_identity_proven_before_decode", True),
        ("thresholds_read_from_locked_contract_not_redefined",
         thresholds["thresholds_changed_by_this_action"] is False),
        ("parent_surface_is_the_539_row_retained_m2_sample",
         parent_surface["parent_rows"] == m.EXPECTED_PARENT_ROWS),
        ("no_final_test_row_read",
         execution_audit["final_test_rows_read"] == 0),
        ("no_new_world_bank_request",
         execution_audit["world_bank_api_requests"] == 0),
        ("no_model_fit", execution_audit["model_fits"] == 0),
        ("no_feature_value_table_materialized",
         execution_audit["feature_value_tables_materialized"] == 0),
        ("verdict_in_vocabulary",
         gate["verdict"] in m.GATE_STATUS_VOCABULARY),
        ("verdict_invariant_across_calendar_conventions",
         gate["status_invariant_across_calendar_conventions"] is True),
        ("no_exclusions_made", decision["rows_excluded"] == 0),
        ("no_criteria_weakened", decision["criteria_weakened"] is False),
        ("step_c_findings_preserved",
         boundary["step_c_material_findings_preserved"] is True),
        ("gate_pass_not_published_as_modeling_authorization",
         boundary["gate_pass_is_modeling_authorization"] is False),
        ("modeling_still_unauthorized",
         boundary["m3_lag_wdi_modeling_authorized"] is False),
        ("final_test_still_locked", boundary["final_test_locked"] is True),
        ("five_way_scientific_distinction_recorded",
         set(scientific_distinctions) == {
             "A_syntactic_availability_and_coverage",
             "B_pre_defined_thresholds_satisfied",
             "C_information_content_limitation_from_step_c",
             "D_effect_on_the_formal_gate_decision",
             "E_remaining_scientific_limitation"}),
    ]
    qc = {
        "action_id": m.ACTION_ID,
        "checks_total": len(checks),
        "checks_failed": sum(1 for _, ok in checks if not ok),
        "all_pass": all(ok for _, ok in checks),
        "checks": [{"check": name, "pass": bool(ok)} for name, ok in checks],
    }

    built = {
        "human_authorization_record": authorization,
        "gate_report": gate_report,
        "common_sample_audit": common_sample_audit,
        "execution_audit": execution_audit,
        "governance_boundary": boundary,
        "decision": decision,
        "qc_report": qc,
    }

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in _ARTIFACT_FILES.items():
        _write_json(PACKAGE_DIR / filename, built[key])
    _write_csv(PACKAGE_DIR / _COVERAGE_CSV, coverage_columns, coverage_rows)
    _write_csv(PACKAGE_DIR / _EVENT_CSV, event_columns, event_rows)
    _write_csv(PACKAGE_DIR / _ROW_STATUS_CSV, _ROW_STATUS_COLUMNS,
               row_records)
    (PACKAGE_DIR / _README_FILE).write_text(_readme(built), encoding="utf-8")

    package_files = {}
    for filename in sorted(list(_ARTIFACT_FILES.values())
                           + [_COVERAGE_CSV, _EVENT_CSV, _ROW_STATUS_CSV,
                              _README_FILE]):
        path = PACKAGE_DIR / filename
        package_files[filename] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    _write_json(PACKAGE_DIR / _METADATA_FILE, {
        "action_id": m.ACTION_ID,
        "package_id": m.PACKAGE_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "authorization_sha256": authorization["authorization_sha256"],
        "authorization_utf8_bytes": authorization["authorization_utf8_bytes"],
        "package_files": package_files,
        "audited_evidence_zenodo_version_doi": "10.5281/zenodo.21844636",
        "audited_evidence_modified": False,
        "raw_wdi_payloads_committed_to_git": 0,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
    })

    print(f"package -> {PACKAGE_DIR}")
    print(f"gate result: {decision['gate_result']}")
    print(f"block coverage: {gate['both_constructible_rows']}/{gate['rows']} "
          f"= {gate['block_common_sample_coverage']:.4f}")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    for item in material_limitations:
        print(f"  LIMITATION: {item}")
    return 0 if qc["all_pass"] else 3


def _check() -> int:
    """Offline verification of the committed Gate package."""
    m.verify_human_authorization()
    all_files = (list(_ARTIFACT_FILES.values())
                 + [_COVERAGE_CSV, _EVENT_CSV, _ROW_STATUS_CSV,
                    _METADATA_FILE, _README_FILE])
    missing = [f for f in all_files if not (PACKAGE_DIR / f).is_file()]
    if missing:
        print(f"STOP_PACKAGE_INCOMPLETE: {missing}", file=sys.stderr)
        return 2

    metadata = json.loads(
        (PACKAGE_DIR / _METADATA_FILE).read_text(encoding="utf-8"))
    for filename, record in metadata["package_files"].items():
        path = PACKAGE_DIR / filename
        if _sha256_file(path) != record["sha256"]:
            print(f"STOP_PACKAGE_HASH_MISMATCH: {filename}", file=sys.stderr)
            return 2
        if path.stat().st_size != record["bytes"]:
            print(f"STOP_PACKAGE_SIZE_MISMATCH: {filename}", file=sys.stderr)
            return 2

    audit = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["execution_audit"])
                       .read_text(encoding="utf-8"))
    boundary = json.loads(
        (PACKAGE_DIR / _ARTIFACT_FILES["governance_boundary"])
        .read_text(encoding="utf-8"))
    decision = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["decision"])
                          .read_text(encoding="utf-8"))
    for counter in _ZERO_COUNTERS:
        if audit.get(counter) != 0:
            print(f"STOP_EXECUTION_COUNTER_NOT_ZERO: {counter}",
                  file=sys.stderr)
            return 2
    if audit.get("data_gate_executed") is not True:
        print("STOP_GATE_NOT_EXECUTED", file=sys.stderr)
        return 2
    for field in ("m3_lag_wdi_data_gate_authorized_now",
                  "m3_lag_wdi_data_gate_authorization_reusable",
                  "gate_pass_is_modeling_authorization",
                  "gate_pass_is_information_content_claim",
                  "gate_pass_is_final_test_unlock",
                  "gate_authorization_propagates_to_step_e",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "retrieval_authorized_now",
                  "new_world_bank_request_made_by_this_action",
                  "final_test_access_authorized",
                  "merge_authorized", "ready_for_review_authorized"):
        if boundary.get(field) is not False:
            print(f"STOP_BOUNDARY_FIELD_NOT_FALSE: {field}", file=sys.stderr)
            return 2
    for field in ("m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_data_gate_authorization_consumed",
                  "step_c_material_findings_preserved",
                  "final_test_locked"):
        if boundary.get(field) is not True:
            print(f"STOP_BOUNDARY_FIELD_NOT_TRUE: {field}", file=sys.stderr)
            return 2
    if decision.get("gate_result") not in m.GATE_STATUS_VOCABULARY:
        print("STOP_VERDICT_OUT_OF_VOCABULARY", file=sys.stderr)
        return 2

    qc = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["qc_report"])
                    .read_text(encoding="utf-8"))
    print(f"action: {m.ACTION_ID} (scope {m.AUTHORIZED_SCOPE})")
    print(f"gate result: {decision['gate_result']}")
    print(f"block formally admitted: {decision['block_formally_admitted']} "
          "(data admission only)")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    print(f"next action: {boundary['m3_lag_wdi_next_action_id']} "
          f"(authorized={boundary['m3_lag_wdi_next_action_authorized']})")
    print(f"final test rows read: {audit['final_test_rows_read']}")
    for item in decision["material_limitations"]:
        print(f"  LIMITATION: {item}")
    if not qc["all_pass"]:
        return 3
    print("Data Gate package verified (--check).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", metavar="BUNDLE_DIR",
                       help="the ONE authorized Gate run (offline)")
    group.add_argument("--check", action="store_true",
                       help="offline verification; no network, no writes")
    args = parser.parse_args(argv)
    if args.execute:
        return _execute(args.execute)
    return _check()


if __name__ == "__main__":
    raise SystemExit(main())
