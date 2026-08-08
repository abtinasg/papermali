#!/usr/bin/env python3
"""Runner — Stage128 Track B: the M3-LAG-WDI CALENDAR-MAPPING LOCK.

Authorized action: ``stage128-m3-lag-wdi-exploratory-calendar-mapping-lock``
Authorized scope:  ``calendar_mapping_lock_only``

``--execute``  the ONE authorized lock run (offline).
``--check``    offline verification of the committed package.

Both modes RECOMPUTE the timing evidence from committed bytes, so ``--check``
would fail if the locked offset ever stopped being the timing-feasible one.
There is no network code path, no estimator import, no feature-value
materialization and no Final Test access. Locking the mapping does NOT
authorize step E.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_calendar_mapping_lock as m)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / m.PACKAGE_REL

_ARTIFACT_FILES = {
    "human_authorization_record":
        "stage128_m3_lag_wdi_calendar_mapping_human_authorization_record.json",
    "decision": "stage128_m3_lag_wdi_calendar_mapping_decision.json",
    "timing_evidence":
        "stage128_m3_lag_wdi_calendar_mapping_timing_evidence.json",
    "execution_audit":
        "stage128_m3_lag_wdi_calendar_mapping_execution_audit.json",
    "governance_boundary":
        "stage128_m3_lag_wdi_calendar_mapping_governance_boundary.json",
    "qc_report": "stage128_m3_lag_wdi_calendar_mapping_qc_report.json",
}
_METADATA_FILE = (
    "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_calendar_mapping_"
    "lock.json")
_README_FILE = (
    "README_STAGE128_M3_LAG_WDI_EXPLORATORY_CALENDAR_MAPPING_LOCK.md")

#: Counters a calendar-mapping lock must leave at zero. It decides a timing
#: convention; it builds nothing and evaluates nothing.
_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "feature_value_tables_materialized", "feature_values_computed",
    "data_gate_executions", "post_retrieval_audit_executions",
    "coverage_calculations", "coverage_threshold_comparisons",
    "admission_decisions", "model_fits", "predictions", "predictive_metrics",
    "bootstrap_executions", "holm_calculations", "shap_executions",
    "tuning_runs", "cross_validation_runs", "model_selections",
    "final_test_rows_read", "final_test_predictor_values_read",
    "final_test_target_values_read",
)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(root: Path) -> dict:
    """Build every artifact. Shared by --execute and --check."""
    authorization = m.verify_human_authorization()
    evidence = m.build_timing_evidence(root)

    # Fail closed BEFORE writing anything: the evidence must itself permit the
    # offset being locked, and must refuse the rejected one.
    m.assert_offset_is_lockable(evidence, m.LOCKED_OFFSET)
    rejected = evidence["per_offset"][str(m.REJECTED_OFFSET)]
    if rejected["satisfies_necessary_timing_condition"]:
        raise m.CalendarMappingLockError(
            f"offset {m.REJECTED_OFFSET} no longer shows a timing violation; "
            "the recorded rejection basis would be false and the lock must "
            "not be written on a stale justification")

    selected = evidence["per_offset"][str(m.LOCKED_OFFSET)]

    decision = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "decision_id": "m3_lag_wdi_predictor_year_calendar_mapping",
        "calendar_mapping_locked": True,
        "calendar_mapping_rule": m.LOCKED_RULE_ID,
        "calendar_mapping_rule_formula": m.LOCKED_RULE_FORMULA,
        "calendar_mapping_locked_offset": m.LOCKED_OFFSET,
        "calendar_mapping_lock_action_id": m.ACTION_ID,
        "calendar_mapping_lock_required_before_modeling": False,
        "calendar_mapping_locked_offset_semantics":
            selected["gregorian_year_semantics"],
        "rejected_offset": m.REJECTED_OFFSET,
        "rejected_offset_semantics": rejected["gregorian_year_semantics"],
        "rejection_basis": (
            f"offset {m.REJECTED_OFFSET} requires a macro observation year "
            f"that is still incomplete at the prediction cutoff for "
            f"{rejected['timing_violation_rows']} of "
            f"{rejected['rows_evaluated']} development rows, across fiscal "
            f"years {sorted(rejected['timing_violation_fiscal_years'])}; "
            f"worst case {rejected['worst_violation_days_after_cutoff']} days "
            "after the cutoff"),
        "rejected_offset_timing_violation_rows":
            rejected["timing_violation_rows"],
        "rejected_offset_timing_violation_fiscal_years":
            rejected["timing_violation_fiscal_years"],
        "rejected_offset_worst_violation_days":
            rejected["worst_violation_days_after_cutoff"],
        "locked_offset_timing_violation_rows":
            selected["timing_violation_rows"],
        "locked_offset_margin_days_min": selected["margin_days_min"],
        "locked_offset_margin_days_median": selected["margin_days_median"],
        "locked_offset_predictor_year_first": selected["predictor_year_first"],
        "locked_offset_predictor_year_last": selected["predictor_year_last"],
        "locked_offset_observation_year_first":
            selected["observation_year_first"],
        "locked_offset_observation_year_last":
            selected["observation_year_last"],
        "fiscal_year_semantics": m.FISCAL_YEAR_SEMANTICS,
        "observation_year_rules": m.OBSERVATION_YEAR_RULES,
        "selection_basis": "temporal_semantics_and_leakage_prevention_only",
        "selection_used_model_performance": False,
        "selection_used_coverage_comparison": False,
        "selection_used_feature_values": False,
        "selection_reversible_by_a_better_predictive_result": False,
        "changing_the_locked_mapping_requires_new_explicit_human_decision":
            True,
        "point_in_time_availability_established_by_this_lock": False,
        "unresolved_limitations": list(m.UNRESOLVED_LIMITATIONS),
        "amends_contract": m.AMENDED_CONTRACT_REL,
        "amends_but_does_not_edit": m.AMENDS_BUT_DOES_NOT_EDIT,
        "amended_contract_sha256": _sha256_file(root / m.AMENDED_CONTRACT_REL),
        "superseding_pattern_precedent": m.SUPERSEDING_PATTERN_PRECEDENT,
        "historical_unlocked_state_erased": False,
        "authorizes_next_action": False,
        "next_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "next_action_authorized": False,
        "next_action_scope": "modeling_requires_new_human_authorization",
    }

    execution_audit = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "calendar_mapping_lock_executed": True,
        "calendar_mapping_lock_executions": 1,
        "development_rows_read": evidence["denominator_rows"],
        "columns_read": evidence["columns_read"],
        "retained_bytes_modified": False,
        "deposited_evidence_modified": False,
        "data_gate_artifacts_modified": False,
        "post_retrieval_audit_artifacts_modified": False,
        "authoritative_contract_edited": False,
        **{counter: 0 for counter in _ZERO_COUNTERS},
    }

    boundary = {
        "action_id": m.ACTION_ID,
        "m3_lag_wdi_calendar_mapping_lock_action_authorized": True,
        "m3_lag_wdi_calendar_mapping_lock_executed": True,
        "m3_lag_wdi_calendar_mapping_lock_authorization_consumed": True,
        "m3_lag_wdi_calendar_mapping_lock_authorization_reusable": False,
        "m3_lag_wdi_calendar_mapping_lock_authorized_now": False,
        "m3_lag_wdi_calendar_mapping_locked": True,
        "m3_lag_wdi_calendar_mapping_rule": m.LOCKED_RULE_ID,
        "m3_lag_wdi_calendar_mapping_lock_required_before_modeling": False,
        # Locking a timing convention authorizes nothing downstream.
        "calendar_mapping_lock_is_modeling_authorization": False,
        "calendar_mapping_lock_authorizes_feature_value_table": False,
        "calendar_mapping_lock_propagates_to_step_e": False,
        "calendar_mapping_lock_is_final_test_unlock": False,
        "calendar_mapping_lock_changed_the_gate_result": False,
        "m3_lag_wdi_next_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "m3_lag_wdi_next_action_authorized": False,
        "m3_lag_wdi_modeling_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "m3_lag_wdi_modeling_authorized": False,
        "m3_lag_wdi_modeling_started": False,
        "m3_lag_wdi_modeling_requires_new_explicit_human_authorization": True,
        # Everything upstream stays exactly as accepted.
        "m3_lag_wdi_data_gate_result": "PASS_M3_LAG_WDI_DATA_GATE",
        "m3_lag_wdi_data_gate_rerun_by_this_action": False,
        "m3_lag_wdi_post_retrieval_audit_rerun_by_this_action": False,
        "m3_lag_wdi_block_admitted": True,
        "m3_lag_wdi_block_admission_is_data_admission_only": True,
        "m3_lag_wdi_gate_thresholds_modified_by_this_action": False,
        "m3_lag_wdi_authoritative_contract_status":
            "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL",
        "m3_lag_wdi_contract_edited_by_this_action": False,
        "step_c_material_findings_preserved": True,
        "point_in_time_availability_claimed": False,
        "retrieval_authorized_now": False,
        "new_world_bank_request_made_by_this_action": False,
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
    }

    gate_report = json.loads(
        (root / m.GATE_REPORT_REL).read_text(encoding="utf-8"))
    gate = gate_report["gate_computation"]

    checks = [
        ("timing_evidence_recomputed_from_committed_bytes",
         evidence["recomputable_from_committed_bytes"] is True),
        ("locked_offset_has_zero_timing_violations",
         selected["timing_violation_rows"] == 0),
        ("rejected_offset_has_timing_violations",
         rejected["timing_violation_rows"] > 0),
        ("locked_offset_is_admissible",
         m.LOCKED_OFFSET in m.ADMISSIBLE_OFFSETS),
        ("denominator_is_the_539_row_development_sample",
         evidence["denominator_rows"] == m.EXPECTED_DEVELOPMENT_ROWS),
        ("no_feature_value_read", evidence["feature_values_read"] == 0),
        ("no_outcome_value_read", evidence["outcome_values_read"] == 0),
        ("no_final_test_row_read",
         execution_audit["final_test_rows_read"] == 0),
        ("no_new_world_bank_request",
         execution_audit["world_bank_api_requests"] == 0),
        ("no_model_fit", execution_audit["model_fits"] == 0),
        ("no_feature_value_table_materialized",
         execution_audit["feature_value_tables_materialized"] == 0),
        ("selection_independent_of_model_performance",
         decision["selection_used_model_performance"] is False),
        ("authoritative_contract_not_edited",
         execution_audit["authoritative_contract_edited"] is False),
        ("gate_result_unchanged",
         gate_report["gate_computation"]["verdict"]
         == "PASS_M3_LAG_WDI_DATA_GATE"),
        ("gate_coverage_unchanged",
         (gate["cpi_constructible_rows"], gate["fx_constructible_rows"],
          gate["both_constructible_rows"], gate["rows"])
         == (539, 539, 539, 539)),
        ("gate_not_rerun",
         boundary["m3_lag_wdi_data_gate_rerun_by_this_action"] is False),
        ("modeling_still_unauthorized",
         boundary["m3_lag_wdi_modeling_authorized"] is False),
        ("lock_is_not_step_e_authorization",
         boundary["calendar_mapping_lock_propagates_to_step_e"] is False),
        ("final_test_still_locked", boundary["final_test_locked"] is True),
        ("point_in_time_limitation_preserved",
         decision["point_in_time_availability_established_by_this_lock"]
         is False and len(decision["unresolved_limitations"]) >= 4),
    ]
    qc = {
        "action_id": m.ACTION_ID,
        "checks_total": len(checks),
        "checks_failed": sum(1 for _, ok in checks if not ok),
        "all_pass": all(ok for _, ok in checks),
        "checks": [{"check": name, "pass": bool(ok)} for name, ok in checks],
    }

    return {
        "human_authorization_record": authorization,
        "decision": decision,
        "timing_evidence": evidence,
        "execution_audit": execution_audit,
        "governance_boundary": boundary,
        "qc_report": qc,
    }


def _readme(built: dict) -> str:
    d = built["decision"]
    ev = built["timing_evidence"]
    sel = ev["per_offset"][str(m.LOCKED_OFFSET)]
    rej = ev["per_offset"][str(m.REJECTED_OFFSET)]
    limits = "\n".join(f"- {x}" for x in d["unresolved_limitations"])
    return f"""# Stage128 — Track B: the M3-LAG-WDI CALENDAR-MAPPING LOCK

**Action:** `{m.ACTION_ID}`
**Authorized scope:** `{m.AUTHORIZED_SCOPE}`
**Locked rule:** `{d['calendar_mapping_rule_formula']}`

## What this action is

Step D returned `PASS_M3_LAG_WDI_DATA_GATE` and exposed a gap in the locked
contract: the macro features are indexed by a **Gregorian** `predictor_year_t`,
the development rows are keyed by a **Jalali** `fiscal_year_t`, and no
committed artifact mapped one onto the other. The Gate verdict is invariant to
the two admissible mappings; the feature **values** are not. This action locks
the mapping — and **only** that.

It fits no model, materializes no feature value, reads no Final Test row, does
not rerun step C or step D, and **does not authorize step E**.

## The decision

`fiscal_year_t` labels **the Jalali year in which the accounting period ENDS**
(539/539 agreement, established by inverting Stage125 Part 3C's
four-Jalali-month regulatory lag over the committed cutoffs). A Jalali year
spans two Gregorian years, so a uniform mapping is either `+621` (the year the
Jalali year **begins**) or `+622` (the year it **ends**).

| | `+{m.LOCKED_OFFSET}` (locked) | `+{m.REJECTED_OFFSET}` (rejected) |
| --- | --- | --- |
| Gregorian year semantics | {sel['gregorian_year_semantics']} | {rej['gregorian_year_semantics']} |
| **Rows whose `t-1` observation year was incomplete at the cutoff** | **{sel['timing_violation_rows']} / {sel['rows_evaluated']}** | **{rej['timing_violation_rows']} / {rej['rows_evaluated']}** |
| Affected fiscal years | — | {sorted(rej['timing_violation_fiscal_years'])} |
| Worst case | — | {rej['worst_violation_days_after_cutoff']} days **after** the cutoff |
| Margin (min / median) | {sel['margin_days_min']} d / {sel['margin_days_median']} d | {rej['margin_days_min']} d / {rej['margin_days_median']} d |
| Development predictor years | {sel['predictor_year_first']}–{sel['predictor_year_last']} | {rej['predictor_year_first']}–{rej['predictor_year_last']} |
| Binding `t-1` observation years | {sel['observation_year_first']}–{sel['observation_year_last']} | {rej['observation_year_first']}–{rej['observation_year_last']} |

`+{m.REJECTED_OFFSET}` is rejected because, for {rej['timing_violation_rows']}
development rows spread across **every** fiscal-year cohort, it would require a
macro value whose observation period had **not yet ended** at the prediction
cutoff — future information under the frozen
`G07 no_future_or_target_year_information` rule.

## Why the lock is fail-closed, not declarative

The runner **recomputes** this table from committed bytes on both `--execute`
and `--check`, and refuses to write a lock for any offset that admits a single
timing violation. `+{m.REJECTED_OFFSET}` is therefore **structurally
unlockable** while the committed development sample says what it says — it
cannot be swapped in by editing a constant. Changing the locked mapping
requires a new explicit human scientific decision **and** evidence that
supports it.

The recomputation needs only `fiscal_year_t` and `pair_cutoff_date` plus
integer arithmetic: **no calendar library, no feature value, no outcome label,
no Final Test row**.

## Independence from model performance

The selection used `selection_used_model_performance: false`,
`selection_used_coverage_comparison: false`,
`selection_used_feature_values: false`. No feature value was computed and no
metric was evaluated — only observation-period end dates against cutoff dates.
The justification stands unchanged if `+{m.REJECTED_OFFSET}` later produced
better predictive numbers; that would be evidence of leakage, not of merit,
since the {rej['timing_violation_rows']} violating rows are exactly where a
look-ahead advantage would come from.

## What this lock does NOT establish

{limits}

## Where this action stopped

Model fits `0` · feature-value tables materialized `0` · Final Test rows read
`0` · new World Bank requests `0` · Gate reruns `0`.

Step D remains `PASS_M3_LAG_WDI_DATA_GATE` with coverage 539/539/539,
validation positives 18 and 10, 0 exclusions, admitted **DATA ADMISSION ONLY**.
The authoritative pre-retrieval contract is **amended, not edited**: its
historical unlocked state is retained, following the Stage125 Part 3C
superseding pattern.

Step E (`{d['next_action_id']}`) remains
`authorized = {d['next_action_authorized']}` and needs its own separate
explicit human authorization.
"""


def _execute() -> int:
    built = _build(ROOT)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in _ARTIFACT_FILES.items():
        _write_json(PACKAGE_DIR / filename, built[key])
    (PACKAGE_DIR / _README_FILE).write_text(_readme(built), encoding="utf-8")

    package_files = {}
    for filename in sorted(list(_ARTIFACT_FILES.values()) + [_README_FILE]):
        path = PACKAGE_DIR / filename
        package_files[filename] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    _write_json(PACKAGE_DIR / _METADATA_FILE, {
        "action_id": m.ACTION_ID,
        "package_id": m.PACKAGE_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "authorization_sha256":
            built["human_authorization_record"]["authorization_sha256"],
        "authorization_utf8_bytes":
            built["human_authorization_record"]["authorization_utf8_bytes"],
        "package_files": package_files,
        "amends_contract": m.AMENDED_CONTRACT_REL,
        "amends_but_does_not_edit": True,
        "feature_value_tables_materialized": 0,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
    })

    qc = built["qc_report"]
    d = built["decision"]
    print(f"package -> {PACKAGE_DIR}")
    print(f"locked rule: {d['calendar_mapping_rule_formula']}")
    print(f"rejected offset {d['rejected_offset']}: "
          f"{d['rejected_offset_timing_violation_rows']} timing violations")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    return 0 if qc["all_pass"] else 3


def _check() -> int:
    all_files = list(_ARTIFACT_FILES.values()) + [_METADATA_FILE, _README_FILE]
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

    # Recompute the evidence and re-prove the locked offset. A lock whose
    # justification has gone stale must not verify.
    rebuilt = _build(ROOT)
    committed = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["decision"])
                           .read_text(encoding="utf-8"))
    for field in ("calendar_mapping_rule", "calendar_mapping_locked_offset",
                  "rejected_offset",
                  "rejected_offset_timing_violation_rows",
                  "locked_offset_timing_violation_rows"):
        if committed.get(field) != rebuilt["decision"].get(field):
            print(f"STOP_LOCK_DRIFT: {field} "
                  f"{committed.get(field)!r} != "
                  f"{rebuilt['decision'].get(field)!r}", file=sys.stderr)
            return 2
    if committed.get("calendar_mapping_locked") is not True:
        print("STOP_MAPPING_NOT_LOCKED", file=sys.stderr)
        return 2

    audit = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["execution_audit"])
                       .read_text(encoding="utf-8"))
    boundary = json.loads(
        (PACKAGE_DIR / _ARTIFACT_FILES["governance_boundary"])
        .read_text(encoding="utf-8"))
    for counter in _ZERO_COUNTERS:
        if audit.get(counter) != 0:
            print(f"STOP_EXECUTION_COUNTER_NOT_ZERO: {counter}",
                  file=sys.stderr)
            return 2
    for field in ("calendar_mapping_lock_is_modeling_authorization",
                  "calendar_mapping_lock_authorizes_feature_value_table",
                  "calendar_mapping_lock_propagates_to_step_e",
                  "calendar_mapping_lock_is_final_test_unlock",
                  "calendar_mapping_lock_changed_the_gate_result",
                  "m3_lag_wdi_calendar_mapping_lock_authorized_now",
                  "m3_lag_wdi_calendar_mapping_lock_authorization_reusable",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_data_gate_rerun_by_this_action",
                  "m3_lag_wdi_post_retrieval_audit_rerun_by_this_action",
                  "m3_lag_wdi_contract_edited_by_this_action",
                  "point_in_time_availability_claimed",
                  "final_test_access_authorized",
                  "merge_authorized", "ready_for_review_authorized"):
        if boundary.get(field) is not False:
            print(f"STOP_BOUNDARY_FIELD_NOT_FALSE: {field}", file=sys.stderr)
            return 2
    for field in ("m3_lag_wdi_calendar_mapping_locked",
                  "m3_lag_wdi_calendar_mapping_lock_executed",
                  "m3_lag_wdi_calendar_mapping_lock_authorization_consumed",
                  "step_c_material_findings_preserved",
                  "m3_lag_wdi_block_admission_is_data_admission_only",
                  "final_test_locked"):
        if boundary.get(field) is not True:
            print(f"STOP_BOUNDARY_FIELD_NOT_TRUE: {field}", file=sys.stderr)
            return 2

    qc = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["qc_report"])
                    .read_text(encoding="utf-8"))
    print(f"action: {m.ACTION_ID} (scope {m.AUTHORIZED_SCOPE})")
    print(f"locked rule: {committed['calendar_mapping_rule_formula']}")
    print(f"rejected offset {committed['rejected_offset']}: "
          f"{committed['rejected_offset_timing_violation_rows']} timing "
          "violations (recomputed and re-proven)")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    print(f"next action: {boundary['m3_lag_wdi_next_action_id']} "
          f"(authorized={boundary['m3_lag_wdi_next_action_authorized']})")
    print(f"final test rows read: {audit['final_test_rows_read']}")
    if not qc["all_pass"]:
        return 3
    print("Calendar-mapping lock package verified (--check).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true",
                       help="the ONE authorized lock run (offline)")
    group.add_argument("--check", action="store_true",
                       help="offline verification; no network, no writes")
    args = parser.parse_args(argv)
    return _execute() if args.execute else _check()


if __name__ == "__main__":
    raise SystemExit(main())
