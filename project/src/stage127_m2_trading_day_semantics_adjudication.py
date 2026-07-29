"""Stage127 — adjudication of "trading day" against the FROZEN Stage125 contract.

This module answers exactly one question:

    Which trading-day interpretation is ALREADY REQUIRED by the frozen
    contract?

It never asks which interpretation improves coverage. The reasoning order is
CONTRACT -> EVIDENCE -> IMPLEMENTATION, never implementation -> desired Gate
result -> interpretation.

The counterfactual computed at the end is DIAGNOSTIC ONLY. It exists so a human
reviewer can see the consequence of the semantic choice, and it is never written
to a canonical output. No model is fitted, no prediction is generated, no
final-test row is read, and the canonical Gate is not touched.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

# --------------------------------------------------------------------------- #
# Frozen sources of authority
# --------------------------------------------------------------------------- #

FORMULA_CONTRACT_REL = (
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json"
)
CUTOFF_CONTRACT_REL = (
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json"
)
GATE_PROTOCOL_REL = "project/stage125/part3_gate_decision_protocol_stage125.csv"
ANALYSIS_PLAN_REL = "project/stage125/part4_statistical_analysis_plan_stage125.json"
DECISION_LOCK_QC_REL = (
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json"
)
SELECTED_DECISIONS_REL = (
    "project/stage125/part3b1_selected_decisions_stage125.csv"
)

FROZEN_SOURCES: tuple[str, ...] = (
    FORMULA_CONTRACT_REL,
    CUTOFF_CONTRACT_REL,
    GATE_PROTOCOL_REL,
    ANALYSIS_PLAN_REL,
    DECISION_LOCK_QC_REL,
    SELECTED_DECISIONS_REL,
)

# Implication strength vocabulary. Nothing is upgraded beyond what the frozen
# text actually supports.
EXPLICIT = "EXPLICIT"
DERIVED = "DERIVED_UNAMBIGUOUSLY"
AMBIGUOUS = "AMBIGUOUS"
NOT_SPECIFIED = "NOT_SPECIFIED"

# --------------------------------------------------------------------------- #
# Adjudication outcomes
# --------------------------------------------------------------------------- #

OUTCOME_A = "FROZEN_CONTRACT_UNAMBIGUOUS_CURRENT_IMPLEMENTATION_CONFORMANT"
OUTCOME_B = "FROZEN_CONTRACT_UNAMBIGUOUS_IMPLEMENTATION_DEFECT"
OUTCOME_C = "SEMANTIC_AMBIGUITY_REQUIRES_HUMAN_DECISION"

COUNTERFACTUAL_LABEL = "DIAGNOSTIC_COUNTERFACTUAL_NOT_CANONICAL_RESULT"

READING_1 = "INSTRUMENT_CALENDAR_MEMBERSHIP_READING"
READING_2 = "POSITIVE_EXECUTED_TRADE_DAY_READING"


def sha256_file(path: str) -> str:
    """Hash a frozen source so the trace pins the exact text it cites."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# --------------------------------------------------------------------------- #
# The contract trace
# --------------------------------------------------------------------------- #

#: Each entry: source file, exact key path, verbatim short value, the semantic
#: implication it carries, and how strongly the frozen text supports it.
CONTRACT_STATEMENTS: tuple[dict[str, Any], ...] = (
    {
        "statement_id": "S01_window_start_rule",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "shared_window.start_rule",
        "verbatim": (
            "inclusive_trading_days_on_or_after_calendar_date_T_star_minus_12_"
            "calendar_months"
        ),
        "semantic_implication": (
            "W begins at the first TRADING DAY on or after the calendar date "
            "T* minus 12 calendar months. The start carries no price condition "
            "and no executed-trade condition."
        ),
        "implication_strength": EXPLICIT,
    },
    {
        "statement_id": "S02_window_end_rule",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "shared_window.end_rule",
        "verbatim": (
            "last_trading_day_with_verified_available_at_strictly_before_pair_"
            "cutoff"
        ),
        "semantic_implication": (
            "T* is selected by an availability TIMESTAMP condition, not by the "
            "presence of a price value."
        ),
        "implication_strength": EXPLICIT,
    },
    {
        "statement_id": "S03_available_at_definition",
        "source_file": CUTOFF_CONTRACT_REL,
        "field": "feature_availability.rule",
        "verbatim": (
            "A feature value is usable at prediction time only if it has a "
            "verified available_at and available_at <= pair_cutoff."
        ),
        "semantic_implication": (
            "'verified available_at' is an availability timestamp. It is "
            "nowhere defined as 'the adjusted_close value is present', so the "
            "end rule cannot be read as 'last PRICED day'."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S04_missing_price_rule",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "price_field.missing_price_rule",
        "verbatim": "exclude_day_from_window_computations",
        "semantic_implication": (
            "A day whose adjusted_close is missing is excluded from the "
            "COMPUTATIONS performed over W, not deleted from W itself. The "
            "rule scopes the exclusion to 'window_computations', not to window "
            "membership."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S05_endpoint_missing_clause",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "variables.equity_return_window.formula",
        "verbatim": (
            "Require P_{t0} and P_{tN} present ... If either endpoint missing "
            "OR usable daily return count < 126 => null/UNRESOLVED."
        ),
        "semantic_implication": (
            "The contract explicitly contemplates an endpoint of W whose price "
            "is MISSING. If missing-price days were deleted from W, an "
            "endpoint could never be missing and this clause would be a dead "
            "letter. Therefore missing-price days remain in W and endpoints "
            "are not re-chosen to find a priced day."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S06_diagnostics_are_window_level",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "diagnostics_recorded",
        "verbatim": (
            "missing_price_day_count, zero_traded_value_day_count, "
            "usable_daily_return_count, usable_amihud_day_count"
        ),
        "semantic_implication": (
            "The contract requires COUNTING missing-price days and "
            "zero-traded-value days. Such days are therefore members of W: a "
            "day removed from W could not be counted as a day of W."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S07_zero_volume_rule_is_amihud_scoped",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "variables.amihud_illiquidity.zero_volume_rule",
        "verbatim": "exclude_day_never_impute",
        "semantic_implication": (
            "Zero traded value excludes a day from the AMIHUD usable-day set "
            "only. The rule is declared inside the amihud variable block and "
            "is not declared for equity_return_window or realized_volatility."
        ),
        "implication_strength": EXPLICIT,
    },
    {
        "statement_id": "S08_frozen_synthetic_validation_arithmetic",
        "source_file": DECISION_LOCK_QC_REL,
        "field": "assertions[synth_window_nonempty|synth_diagnostics_recorded]",
        "verbatim": (
            "len=248 ; {'missing_price_day_count': 0, "
            "'zero_traded_value_day_count': 1, 'usable_daily_return_count': "
            "247, 'usable_amihud_day_count': 246}"
        ),
        "semantic_implication": (
            "DECISIVE. In the frozen validation that LOCKED this contract, a "
            "window of 248 days containing 1 zero-traded-value day produced "
            "247 usable daily returns (= 248 - 1, i.e. every adjacent pair) "
            "and 246 usable amihud days (= 247 - 1). The zero-trade day was "
            "therefore RETAINED in the trading-day sequence and still "
            "contributed daily returns; only amihud dropped it. A "
            "positive-executed-trade reading would have produced 246 returns, "
            "not 247."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S09_consecutive_days_both_prices",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "variables.realized_volatility.formula",
        "verbatim": (
            "Daily simple returns r_t = (P_t / P_{t-1}) - 1 for consecutive "
            "trading days in shared window W with both prices present."
        ),
        "semantic_implication": (
            "The return is defined over pairs of CONSECUTIVE TRADING DAYS OF "
            "W, filtered to those where both prices are present. Since a "
            "missing-price day stays in W (S04-S06), two priced days separated "
            "by it are not consecutive trading days of W, so returns are not "
            "bridged across it."
        ),
        "implication_strength": DERIVED,
    },
    {
        "statement_id": "S10_no_imputation_or_threshold_relief",
        "source_file": FORMULA_CONTRACT_REL,
        "field": "imputation_allowed / threshold_reduction_allowed",
        "verbatim": "false / false",
        "semantic_implication": (
            "Missing evidence may not be repaired and the 126-observation "
            "minimum may not be relaxed to obtain coverage."
        ),
        "implication_strength": EXPLICIT,
    },
    {
        "statement_id": "S11_trading_day_never_defined_as_calendar_member",
        "source_file": "ALL_FROZEN_STAGE125_STAGE126_ARTIFACTS",
        "field": "(absent)",
        "verbatim": "(no occurrence)",
        "semantic_implication": (
            "No frozen artifact defines 'trading day' as membership of the "
            "official TSETMC InstrumentCalendar; the terms "
            "'InstrumentCalendar', 'market calendar' and 'calendar member' do "
            "not occur anywhere in the frozen Stage125/Stage126 corpus. The "
            "term is used but never given an operational source definition."
        ),
        "implication_strength": NOT_SPECIFIED,
    },
    {
        "statement_id": "S12_trading_day_never_requires_executed_trade",
        "source_file": "ALL_FROZEN_STAGE125_STAGE126_ARTIFACTS",
        "field": "(absent)",
        "verbatim": "(no occurrence)",
        "semantic_implication": (
            "No frozen artifact conditions membership of the trading-day "
            "sequence on a positive executed trade. The only executed-trade "
            "condition in the corpus is amihud's V_t > 0 usable-day filter "
            "(S07), which is scoped to one variable's computation."
        ),
        "implication_strength": NOT_SPECIFIED,
    },
    {
        "statement_id": "S13_no_authoritative_state_code_mapping",
        "source_file": "ALL_FROZEN_STAGE125_STAGE126_ARTIFACTS",
        "field": "(absent)",
        "verbatim": "(no occurrence)",
        "semantic_implication": (
            "The frozen project contains no authoritative mapping for TSETMC "
            "instrument state codes ('A ', 'IS', 'AR', 'I ', 'AS'). They "
            "remain literal evidence with UNRESOLVED meaning and may not be "
            "given a third-party definition."
        ),
        "implication_strength": NOT_SPECIFIED,
    },
    {
        "statement_id": "S14_gate_thresholds_pending_user_approval",
        "source_file": GATE_PROTOCOL_REL,
        "field": "G10.lock_status",
        "verbatim": "pending_user_approval",
        "semantic_implication": (
            "The minimum common-sample coverage threshold is not frozen; it "
            "may not be invented, and no semantic choice may be justified by "
            "the coverage it produces."
        ),
        "implication_strength": EXPLICIT,
    },
)

#: The seven questions posed for this adjudication, answered ONLY from the trace.
CONTRACT_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "question_id": "A",
        "question": (
            "Does 'trading day' explicitly mean an official TSETMC "
            "InstrumentCalendar member?"
        ),
        "answer": "NO_NOT_EXPLICITLY_DEFINED",
        "implication_strength": NOT_SPECIFIED,
        "supporting_statements": ["S11_trading_day_never_defined_as_calendar_member"],
        "note": (
            "The frozen corpus never names a calendar authority. This textual "
            "gap is NON-OPERATIVE for the imported evidence: the delivery "
            "shows the InstrumentCalendar date set equals the "
            "ClosingPriceDailyList date set for 27/27 bounded RANGE requests, "
            "and the observation universe the Gate consumes IS the daily list. "
            "The two candidate day universes therefore coincide on this "
            "dataset and no computed value depends on the gap."
        ),
    },
    {
        "question_id": "B",
        "question": "Does 'trading day' explicitly require positive executed trade?",
        "answer": "NO",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S07_zero_volume_rule_is_amihud_scoped",
            "S08_frozen_synthetic_validation_arithmetic",
            "S12_trading_day_never_requires_executed_trade",
        ],
        "note": (
            "No membership condition on executed trade exists, and the frozen "
            "synthetic validation that locked the contract retained a "
            "zero-traded-value day in the return sequence."
        ),
    },
    {
        "question_id": "C",
        "question": "Does zero trade remove a date from W?",
        "answer": "NO",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S06_diagnostics_are_window_level",
            "S07_zero_volume_rule_is_amihud_scoped",
            "S08_frozen_synthetic_validation_arithmetic",
        ],
        "note": (
            "zero_traded_value_day_count is a REQUIRED DIAGNOSTIC OF W, and "
            "the locking validation counted 247 = 248 - 1 usable returns over "
            "a window containing one zero-trade day. A removed day could "
            "neither be counted nor contribute a return."
        ),
    },
    {
        "question_id": "D",
        "question": (
            "Does missing_price_rule = exclude_day_from_window_computations "
            "mean (1) remove the date from the scientific trading-day "
            "sequence, or (2) keep the day in W but exclude its missing price "
            "from calculations?"
        ),
        "answer": "READING_2_KEEP_DAY_IN_W_EXCLUDE_FROM_CALCULATIONS",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S04_missing_price_rule",
            "S05_endpoint_missing_clause",
            "S06_diagnostics_are_window_level",
        ],
        "note": (
            "The rule is scoped to 'window_computations'. Reading (1) would "
            "make the frozen clause 'If either endpoint missing => null' "
            "structurally unreachable, and would make the required diagnostic "
            "missing_price_day_count identically zero."
        ),
    },
    {
        "question_id": "E",
        "question": (
            "For realized volatility, does 'consecutive trading days with both "
            "prices present' permit bridging over an intervening calendar "
            "member with no price?"
        ),
        "answer": "NO_BRIDGING_PERMITTED",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S09_consecutive_days_both_prices",
            "S04_missing_price_rule",
            "S10_no_imputation_or_threshold_relief",
        ],
        "note": (
            "'Consecutive' qualifies TRADING DAYS OF W; 'both prices present' "
            "is a filter applied to those adjacent pairs, not a re-definition "
            "of adjacency over the priced subsequence. Bridging would "
            "manufacture a return across an unobserved day, which the "
            "no-imputation rule forbids."
        ),
    },
    {
        "question_id": "F",
        "question": (
            "Is t0 the first calendar-member trading day of W, or the first "
            "positive-trade/priced day?"
        ),
        "answer": "FIRST_TRADING_DAY_OF_W_NOT_FIRST_PRICED_OR_TRADED_DAY",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S01_window_start_rule",
            "S05_endpoint_missing_clause",
        ],
        "note": (
            "The start rule carries no price or trade condition, and the "
            "endpoint-missing clause presupposes that t0 may be unpriced."
        ),
    },
    {
        "question_id": "G",
        "question": "Is T* defined independently of adjusted_close availability?",
        "answer": "YES",
        "implication_strength": DERIVED,
        "supporting_statements": [
            "S02_window_end_rule",
            "S03_available_at_definition",
            "S05_endpoint_missing_clause",
        ],
        "note": (
            "The end rule is keyed to a verified availability timestamp. "
            "Selecting T* from priced days only would move T* backwards purely "
            "to obtain a usable value."
        ),
    },
)


def build_contract_trace(repo_root: str) -> dict[str, Any]:
    """Build the semantics contract trace with hashes of every frozen source."""
    sources: list[dict[str, Any]] = []
    for rel in FROZEN_SOURCES:
        path = os.path.join(repo_root, rel)
        sources.append({
            "source_file": rel,
            "present": os.path.isfile(path),
            "sha256": sha256_file(path) if os.path.isfile(path) else None,
        })
    missing = [s["source_file"] for s in sources if not s["present"]]
    if missing:
        raise FileNotFoundError(f"frozen source(s) missing: {missing}")

    strengths: dict[str, int] = {}
    for st in CONTRACT_STATEMENTS:
        key = st["implication_strength"]
        strengths[key] = strengths.get(key, 0) + 1

    return {
        "artifact": "stage127_m2_trading_day_semantics_contract_trace",
        "purpose": (
            "Trace every frozen statement bearing on the meaning of 'trading "
            "day' in the M2 shared window, and answer questions A-G from the "
            "frozen text alone."
        ),
        "reasoning_order": "CONTRACT -> EVIDENCE -> IMPLEMENTATION",
        "frozen_sources": sources,
        "frozen_sources_modified_by_this_task": False,
        "statements": list(CONTRACT_STATEMENTS),
        "statement_count": len(CONTRACT_STATEMENTS),
        "implication_strength_counts": dict(sorted(strengths.items())),
        "questions": list(CONTRACT_QUESTIONS),
        "inference_beyond_frozen_text_performed": False,
    }


# --------------------------------------------------------------------------- #
# Adjudication
# --------------------------------------------------------------------------- #

def adjudicate(trace: dict[str, Any]) -> dict[str, Any]:
    """Select outcome A, B or C from the contract trace alone.

    The decision rule is mechanical: an outcome is only available if the
    questions that actually govern the disputed behaviour are answered at
    EXPLICIT or DERIVED_UNAMBIGUOUSLY strength.
    """
    by_id = {q["question_id"]: q for q in trace["questions"]}
    governing = ("B", "C", "D", "E", "F", "G")
    unresolved = [
        qid for qid in governing
        if by_id[qid]["implication_strength"] not in (EXPLICIT, DERIVED)
    ]

    # What the frozen contract REQUIRES of the trading-day sequence.
    required = {
        "zero_trade_calendar_day_remains_a_trading_day_in_W": True,
        "missing_price_day_remains_a_trading_day_in_W": True,
        "t0_is_first_trading_day_of_W": True,
        "tN_is_T_star_selected_independently_of_price": True,
        "endpoint_missing_price_yields_null": True,
        "returns_bridged_across_unpriced_days": False,
        "zero_traded_value_excluded_from_amihud_only": True,
    }

    if unresolved:
        outcome = OUTCOME_C
        conformant = "UNRESOLVED"
    else:
        outcome = OUTCOME_A
        conformant = "YES"

    return {
        "adjudication_outcome": outcome,
        "governing_questions": list(governing),
        "questions_not_unambiguously_answered": unresolved,
        "frozen_contract_required_behaviour": required,
        "current_implementation_conformant": conformant,
        "question_A_gap_is_operative": False,
        "question_A_gap_note": by_id["A"]["note"],
        "justification": [
            by_id[qid]["question_id"] + ": " + by_id[qid]["answer"]
            for qid in ("A",) + governing
        ],
        "interpretation_chosen_to_obtain_PASS": False,
        "canonical_gate_changed": False,
        "canonical_gate_status": "FAIL_M2_DATA_GATE",
        "t0_changed": False,
        "t_star_changed": False,
        "thresholds_changed": False,
        "features_changed": False,
        "frozen_stage125_contract_modified": False,
        "equity_return_window_dropped": False,
    }


# --------------------------------------------------------------------------- #
# Diagnostic counterfactuals — NEVER a canonical result
# --------------------------------------------------------------------------- #

def _retain_all(_observation: dict[str, Any]) -> bool:
    """Reading 1: a date stays in the trading-day sequence."""
    return True


def _retain_positive_trade(observation: dict[str, Any]) -> bool:
    """Reading 2: a date stays only if positive executed trade is demonstrated."""
    return (observation["traded_value_rial"] or 0) > 0


READINGS = {
    READING_1: _retain_all,
    READING_2: _retain_positive_trade,
}


def counterfactual_for_reading(
    reading: str,
    pairs: list[dict[str, Any]],
    observations: dict[str, list[dict[str, Any]]],
    gate: Any,
) -> dict[str, Any]:
    """Development-only consequence of one trading-day reading.

    No model is fitted, no PR-AUC is computed, no selection is performed and no
    final-test row is touched: this reports usable counts only.
    """
    keep = READINGS[reading]
    usable: dict[str, set[tuple[str, str]]] = {
        var: set() for var, _, _ in gate.M2_VARIABLES
    }
    for pair in pairs:
        obs = [o for o in observations.get(pair["ticker"], []) if keep(o)]
        features = gate.compute_pair_features(pair["pair_cutoff_date"], obs)
        key = (pair["ticker"], pair["fiscal_year_t"])
        for var, _, _ in gate.M2_VARIABLES:
            if features[var] is not None:
                usable[var].add(key)
    common = set.intersection(*usable.values())
    total = len(pairs)

    return {
        "label": COUNTERFACTUAL_LABEL,
        "reading": reading,
        "development_pairs": total,
        "equity_return_window_usable": len(usable["equity_return_window"]),
        "equity_return_window_coverage": round(
            len(usable["equity_return_window"]) / total, 10),
        "realized_volatility_usable": len(usable["realized_volatility"]),
        "realized_volatility_coverage": round(
            len(usable["realized_volatility"]) / total, 10),
        "amihud_illiquidity_usable": len(usable["amihud_illiquidity"]),
        "amihud_illiquidity_coverage": round(
            len(usable["amihud_illiquidity"]) / total, 10),
        "three_variable_common_sample": len(common),
        "three_variable_common_sample_coverage": round(len(common) / total, 10),
        "event_counts_by_locked_validation_fold": gate.event_count_feasibility(
            pairs, common),
        "model_fits": 0,
        "predictions_generated": 0,
        "pr_auc_computed": False,
        "selection_performed": False,
        "threshold_weakened": False,
        "final_test_access": 0,
    }


def build_counterfactuals(
    pairs: list[dict[str, Any]],
    observations: dict[str, list[dict[str, Any]]],
    gate: Any,
) -> dict[str, Any]:
    """Both readings, side by side, explicitly labelled as non-canonical."""
    results = {
        reading: counterfactual_for_reading(reading, pairs, observations, gate)
        for reading in (READING_1, READING_2)
    }
    canonical_reading = results[READING_1]
    return {
        "label": COUNTERFACTUAL_LABEL,
        "purpose": (
            "Show the consequence of the semantic choice for a human reviewer. "
            "These figures never replace a canonical output."
        ),
        "readings": results,
        "reading_1_reproduces_canonical_coverage": (
            canonical_reading["equity_return_window_usable"] == 269
            and canonical_reading["realized_volatility_usable"] == 576
            and canonical_reading["amihud_illiquidity_usable"] == 576
            and canonical_reading["three_variable_common_sample"] == 269
        ),
        "reading_2_supported_by_frozen_contract": False,
        "reading_2_status": (
            "COUNTERFACTUAL_ONLY. The frozen contract does not support removing "
            "a zero-trade day from the trading-day sequence (questions B and C), "
            "and the frozen synthetic validation that locked the contract "
            "retained such a day. Reading 2 raises coverage and is therefore "
            "exactly the interpretation that must NOT be adopted on the basis "
            "of the Gate result it produces."
        ),
        "canonical_outputs_modified": False,
    }
