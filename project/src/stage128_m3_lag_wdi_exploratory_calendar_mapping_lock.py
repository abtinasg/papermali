"""Stage128 — Track B: the M3-LAG-WDI CALENDAR-MAPPING LOCK.

Authorized action: ``stage128-m3-lag-wdi-exploratory-calendar-mapping-lock``
Authorized scope:  ``calendar_mapping_lock_only``

Step D returned ``PASS_M3_LAG_WDI_DATA_GATE`` and, in doing so, exposed a gap
in the locked contract: the two macro features are indexed by a **Gregorian**
``predictor_year_t``, but the development rows are keyed by a **Jalali**
``fiscal_year_t``, and no committed artifact maps one onto the other. The Gate
verdict is invariant to the two admissible mappings, but the feature VALUES are
not — so no modeling feature table may exist until the mapping is locked.

This action locks exactly one rule, under its own new human scientific
decision::

    predictor_year_t = jalali_fiscal_year_t + 621

and nothing else. It fits no model, materializes no feature value, reads no
Final Test row, and does not authorize step E.

Why the lock is fail-closed rather than declarative
---------------------------------------------------
A lock that merely *records* a chosen offset can be edited to the other one by
anyone who prefers it. This module instead **recomputes the decisive timing
evidence from committed bytes** and refuses to lock any offset that admits a
single timing violation. ``+622`` is therefore not merely discouraged here: it
is structurally unlockable while the committed development sample says what it
says.

The decisive criterion is the repository's own frozen availability rule —
``G07 no_future_or_target_year_information`` and "a feature value is usable at
prediction time only if available_at <= pair_cutoff". A **necessary** condition
is that the macro observation year be COMPLETE at the prediction cutoff: an
annual value cannot exist before its calendar year ends, whatever the
publication practice. That condition needs only the committed
``fiscal_year_t`` and ``pair_cutoff_date`` columns plus integer arithmetic — no
calendar library, no feature value, no target label.

What this module deliberately does NOT recompute
------------------------------------------------
That ``fiscal_year_t`` labels the Jalali year in which the accounting period
ENDS is recorded here as an input finding with its provenance (Stage125
Part 3C's four-Jalali-month regulatory lag, inverted over the 539 committed
cutoffs during the authorized decision-support analysis). It is **not**
recomputed here, because doing so would require a second Jalali calendar
implementation inside this action, and the project already pins a canonical one
(``jdatetime==6.0.1``, Stage125 Part 3B1A). A divergent second converter is a
worse risk than an unrecomputed finding — and the finding is not what decides
the lock. The **leakage test is what decides the lock**, and that is recomputed
in full.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import os
from pathlib import Path
from typing import Any

ACTION_ID = "stage128-m3-lag-wdi-exploratory-calendar-mapping-lock"
AUTHORIZED_SCOPE = "calendar_mapping_lock_only"
PACKAGE_ID = "stage128_m3_lag_wdi_exploratory_calendar_mapping_lock"
PACKAGE_REL = "project/stage128/m3_lag_wdi_exploratory_calendar_mapping_lock"

#: The frozen contract this decision AMENDS. It is never edited: its historical
#: unlocked state is part of the record, and erasing it would hide that the
#: gap existed when step D ran. This mirrors Stage125 Part 3C, which locked a
#: new four-month regulatory lag in its own artifact while leaving the
#: superseded six-month lock intact.
AMENDED_CONTRACT_REL = (
    "project/stage128/m3_lag_wdi_exploratory_contract_lock/"
    "stage128_m3_lag_wdi_exploratory_contract.json")
AMENDS_BUT_DOES_NOT_EDIT = True
SUPERSEDING_PATTERN_PRECEDENT = (
    "project/stage125/part3c_four_month_regulatory_lag_revision_decision_"
    "stage125.json")

D2_FEATURES_REL = "project/stage128/stage128_m2_d2_development_features.csv"
GATE_REPORT_REL = ("project/stage128/m3_lag_wdi_exploratory_data_gate/"
                   "stage128_m3_lag_wdi_data_gate_report.json")

#: The NEW single-use human scientific decision authorizing THIS action,
#: verbatim opening lines, pinned by byte length and digest. Distinct from the
#: contract-lock, retrieval, audit and Gate authorizations, all of which stay
#: historical and consumed.
HUMAN_AUTHORIZATION_TEXT = (
    "HUMAN SCIENTIFIC DECISION — AUTHORIZE CALENDAR-MAPPING LOCK ONLY\n"
    "\n"
    "I accept the independently audited recommendation:\n"
    "\n"
    "RECOMMEND_LOCK_JALALI_PLUS_621\n"
    "\n"
    "I explicitly authorize ONLY the new calendar-mapping lock action:\n"
    "\n"
    "stage128-m3-lag-wdi-exploratory-calendar-mapping-lock"
)

#: The two admissible mappings. A Jalali year spans exactly two Gregorian
#: years, so any faithful uniform convention is one of these.
OFFSET_JALALI_YEAR_BEGINS = 621
OFFSET_JALALI_YEAR_ENDS = 622
ADMISSIBLE_OFFSETS: tuple[int, ...] = (
    OFFSET_JALALI_YEAR_BEGINS, OFFSET_JALALI_YEAR_ENDS)

#: The locked rule.
LOCKED_OFFSET = OFFSET_JALALI_YEAR_BEGINS
LOCKED_RULE_ID = "jalali_fiscal_year_t_plus_621"
LOCKED_RULE_FORMULA = "predictor_year_t = jalali_fiscal_year_t + 621"
REJECTED_OFFSET = OFFSET_JALALI_YEAR_ENDS

EXPECTED_DEVELOPMENT_ROWS = 539
FINAL_TEST_TARGET_YEARS: tuple[str, ...] = ("1400", "1401", "1402")


class CalendarMappingLockError(RuntimeError):
    """Raised whenever a fail-closed precondition of the lock is violated."""


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_human_authorization() -> dict[str, Any]:
    """The calendar-lock decision, pinned by its own byte length and digest."""
    raw = HUMAN_AUTHORIZATION_TEXT.encode("utf-8")
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "authorization_text": HUMAN_AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": len(raw),
        "authorization_sha256": _sha256_bytes(raw),
        "authorization_is_single_use": True,
        "authorization_covers_step_e": False,
        "authorization_covers_modeling": False,
        "authorization_covers_model_fitting": False,
        "authorization_covers_feature_value_table": False,
        "authorization_covers_final_test": False,
        "authorization_covers_new_retrieval": False,
        "authorization_covers_gate_rerun": False,
        "authorization_covers_audit_rerun": False,
        "authorization_covers_merge": False,
        "authorization_covers_ready_for_review": False,
        "prior_data_gate_authorization_reused": False,
        "prior_step_c_authorization_reused": False,
        "prior_retrieval_authorization_reused": False,
        "standing_authorization": False,
    }


# --------------------------------------------------------------------------- #
# The decisive timing evidence — recomputed, never asserted
# --------------------------------------------------------------------------- #

def load_development_rows(root: Path) -> list[dict[str, str]]:
    """The retained-M2 development common sample, from committed bytes.

    Only ``fiscal_year_t``, ``target_year`` and ``pair_cutoff_date`` are read.
    No feature column, no outcome column and no final-test row is touched.
    """
    with (root / D2_FEATURES_REL).open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["in_three_variable_common_sample"].strip() == "True"]
    if len(rows) != EXPECTED_DEVELOPMENT_ROWS:
        raise CalendarMappingLockError(
            f"development sample is {len(rows)} rows, not "
            f"{EXPECTED_DEVELOPMENT_ROWS}")
    leaked = sorted({r["target_year"] for r in rows}
                    & set(FINAL_TEST_TARGET_YEARS))
    if leaked:
        raise CalendarMappingLockError(
            f"final-test target years in the development sample: {leaked}")
    return [{"fiscal_year_t": r["fiscal_year_t"],
             "target_year": r["target_year"],
             "pair_cutoff_date": r["pair_cutoff_date"]} for r in rows]


def evaluate_offset(rows: list[dict[str, str]], offset: int) -> dict[str, Any]:
    """Timing feasibility of one candidate mapping, over every development row.

    The necessary condition, applied to the binding ``t-1`` observation year
    (binding for BOTH features: CPI needs ``t-1``; FX needs ``t-1`` and
    ``t-2``, and ``t-1`` is the later of the two)::

        31 December of (predictor_year_t - 1)  <=  pair_cutoff_date

    A row failing this would require a macro value whose observation period had
    not yet ended at the prediction cutoff — future information, regardless of
    when the value was published.
    """
    if offset not in ADMISSIBLE_OFFSETS:
        raise CalendarMappingLockError(
            f"offset {offset} is not one of the admissible mappings "
            f"{ADMISSIBLE_OFFSETS}")

    violations: list[dict[str, Any]] = []
    margins: list[int] = []
    predictor_years: list[int] = []
    observation_years: list[int] = []
    violating_fiscal_years: dict[str, int] = {}

    for row in rows:
        fiscal_year = int(row["fiscal_year_t"])
        predictor_year = fiscal_year + offset
        observation_year = predictor_year - 1
        cutoff = datetime.date.fromisoformat(row["pair_cutoff_date"])
        observation_period_end = datetime.date(observation_year, 12, 31)
        margin_days = (cutoff - observation_period_end).days

        predictor_years.append(predictor_year)
        observation_years.append(observation_year)
        margins.append(margin_days)
        if margin_days < 0:
            violating_fiscal_years[row["fiscal_year_t"]] = (
                violating_fiscal_years.get(row["fiscal_year_t"], 0) + 1)
            violations.append({
                "fiscal_year_t": row["fiscal_year_t"],
                "pair_cutoff_date": row["pair_cutoff_date"],
                "required_observation_year": observation_year,
                "observation_year_completes_days_after_cutoff": -margin_days,
            })

    margins.sort()
    return {
        "offset": offset,
        "rule_formula": f"predictor_year_t = jalali_fiscal_year_t + {offset}",
        "gregorian_year_semantics": (
            "the Gregorian year in which the Jalali year BEGINS"
            if offset == OFFSET_JALALI_YEAR_BEGINS else
            "the Gregorian year in which the Jalali year ENDS"),
        "rows_evaluated": len(rows),
        "timing_violation_rows": len(violations),
        "timing_violation_fiscal_years": dict(
            sorted(violating_fiscal_years.items())),
        "timing_violations": violations,
        "worst_violation_days_after_cutoff": (
            max(v["observation_year_completes_days_after_cutoff"]
                for v in violations) if violations else None),
        "margin_days_min": margins[0],
        "margin_days_median": margins[len(margins) // 2],
        "margin_days_max": margins[-1],
        "predictor_year_first": min(predictor_years),
        "predictor_year_last": max(predictor_years),
        "observation_year_first": min(observation_years),
        "observation_year_last": max(observation_years),
        "satisfies_necessary_timing_condition": not violations,
    }


def build_timing_evidence(root: Path) -> dict[str, Any]:
    """Evaluate BOTH admissible mappings and prove the selection follows."""
    rows = load_development_rows(root)
    per_offset = {offset: evaluate_offset(rows, offset)
                  for offset in ADMISSIBLE_OFFSETS}

    feasible = [offset for offset, result in per_offset.items()
                if result["satisfies_necessary_timing_condition"]]
    return {
        "action_id": ACTION_ID,
        "criterion": (
            "G07 no_future_or_target_year_information: the binding t-1 macro "
            "observation year must be COMPLETE at the prediction cutoff"),
        "criterion_source": (
            "project/stage125/part3b1_cutoff_available_at_contract_stage125"
            ".json"),
        "criterion_is_necessary_not_sufficient": True,
        "criterion_note": (
            "This is a NECESSARY condition only. It does not establish that "
            "the value had been PUBLISHED by the cutoff — the repository "
            "deliberately does not claim point-in-time WDI availability, and "
            "that limitation is unchanged by this lock."),
        "denominator_rows": len(rows),
        "denominator_source": D2_FEATURES_REL,
        "denominator_source_sha256": _sha256_file(root / D2_FEATURES_REL),
        "columns_read": ["fiscal_year_t", "target_year", "pair_cutoff_date"],
        "feature_values_read": 0,
        "outcome_values_read": 0,
        "final_test_rows_read": 0,
        "evaluated_offsets": list(ADMISSIBLE_OFFSETS),
        "per_offset": {str(k): v for k, v in per_offset.items()},
        "timing_feasible_offsets": feasible,
        "selection_basis": "temporal_semantics_and_leakage_prevention_only",
        "selection_used_model_performance": False,
        "selection_used_coverage_comparison": False,
        "selection_used_feature_values": False,
        "recomputable_from_committed_bytes": True,
        "calendar_library_required": False,
    }


def assert_offset_is_lockable(evidence: dict[str, Any], offset: int) -> None:
    """Fail closed unless the evidence itself permits locking ``offset``.

    This is what makes ``+622`` structurally unlockable rather than merely
    discouraged: an offset admitting even one timing violation cannot be
    written into the lock, no matter what a future editor prefers.
    """
    result = evidence["per_offset"].get(str(offset))
    if result is None:
        raise CalendarMappingLockError(
            f"offset {offset} was not evaluated against the development "
            "sample")
    if not result["satisfies_necessary_timing_condition"]:
        raise CalendarMappingLockError(
            f"offset {offset} cannot be locked: it requires a macro "
            f"observation year that is still incomplete at the prediction "
            f"cutoff for {result['timing_violation_rows']} of "
            f"{result['rows_evaluated']} development rows. Locking it would "
            "admit future-period information.")


def assert_feature_table_permitted(state: dict[str, Any]) -> None:
    """No modeling feature-value table may exist while the mapping is unlocked.

    Feature VALUES depend on the mapping (the Gate verdict does not), so a
    table built before the lock would silently embed whichever convention its
    author happened to pick.
    """
    if state.get("calendar_mapping_locked") is not True:
        raise CalendarMappingLockError(
            "no M3-LAG-WDI modeling feature-value table may be materialized "
            "while calendar_mapping_locked is not True: feature values are "
            "not invariant to the Jalali-to-Gregorian mapping")


# --------------------------------------------------------------------------- #
# Recorded input findings — provenance, not recomputation
# --------------------------------------------------------------------------- #

#: Established during the authorized decision-support analysis by inverting
#: Stage125 Part 3C's four-Jalali-month regulatory lag over the 539 committed
#: ``pair_cutoff_date`` values. Every recovered fiscal-year-end fell in the
#: Jalali year named by ``fiscal_year_t`` — 539/539, no exceptions — and every
#: recovered end was a canonical Iranian fiscal-year-end, which independently
#: corroborated both the lag rule and the conversion.
FISCAL_YEAR_SEMANTICS = {
    "fiscal_year_t_labels": "the Jalali year in which the accounting period ENDS",
    "established_by": (
        "inverting the Stage125 Part 3C four-Jalali-month regulatory lag over "
        "the 539 committed pair_cutoff_date values"),
    "provenance": (
        "project/stage125/part3c_four_month_regulatory_lag_revision_decision_"
        "stage125.json"),
    "agreement_rows": 539,
    "agreement_total_rows": 539,
    "mismatches": 0,
    "recovered_fiscal_year_ends_are_canonical_iranian": True,
    "recomputed_by_this_action": False,
    "not_recomputed_reason": (
        "recomputation would require a second Jalali calendar implementation "
        "inside this action; the project pins a canonical one "
        "(jdatetime==6.0.1, Stage125 Part 3B1A) and a divergent second "
        "converter is a worse risk than an unrecomputed input finding. This "
        "finding is NOT what decides the lock — the recomputed timing "
        "evidence is."),
    "decides_the_lock": False,
}

#: The locked observation-year rules, restated from the frozen contract. They
#: are unchanged by this action; only the Jalali-to-Gregorian mapping of
#: ``predictor_year_t`` is newly locked.
OBSERVATION_YEAR_RULES = {
    "intl_cpi_inflation_lag1_wdi": {
        "indicator_code": "FP.CPI.TOTL.ZG",
        "required_observation_years": ["t-1"],
        "transformation": "identity",
        "same_year_t_observation_permitted": False,
    },
    "intl_fx_change_official_lag1_wdi": {
        "indicator_code": "PA.NUS.FCRF",
        "required_observation_years": ["t-1", "t-2"],
        "transformation": "FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))",
        "same_year_t_observation_permitted": False,
    },
    "binding_observation_year": "t-1",
    "changed_by_this_action": False,
}

#: Limitations this lock does NOT resolve. Locking a calendar mapping is a
#: timing decision; it establishes nothing about what was published when.
UNRESOLVED_LIMITATIONS: tuple[str, ...] = (
    "point-in-time WDI availability remains UNPROVEN: the retained values are "
    "current/latest revised WDI and may contain later revisions, and locking "
    "the calendar mapping does not turn revised WDI into point-in-time data",
    "the one-year lag remains a conservative temporal-separation design only; "
    "it does not prove historical publication availability",
    "the FX feature remains defined but identically ZERO for predictor years "
    "2021-2024 (outside the development sample under the locked mapping, but "
    "real for any future extension of the block)",
    "PA.NUS.FCRF still carries no value for observation years 2024-2025, so "
    "the jointly constructible predictor-year ceiling remains 2024",
)
