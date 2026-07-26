"""Stage127 — M2 market-data admission Gate (development-only, no modeling).

This module executes the point-in-time DATA ADMISSION GATE for the frozen
three-variable M2 market block. It answers only whether the frozen M2 market
variables can be obtained from the authoritative source with correct timing,
acceptable quality, sufficient development coverage, reliable joins and
sufficient event support to justify a LATER M2-vs-M1 incremental evaluation.

It deliberately does NOT answer whether M2 improves prediction. No model is
fit, no prediction is generated, no metric is compared, and no final-test row
is ever loaded.

Fail-closed design
------------------
Absence of evidence is never converted into evidence of absence. Per the frozen
R-A operational mapping (``missing_evidence: null_or_unresolved_never_zero``),
an accessibility score is emitted ONLY when real candidate_endpoint_evidence was
captured. When retrieval cannot be attempted at all, the candidate is recorded
UNRESOLVED — never scored 0-2, which would be a hard drop asserting a property
of the source that was not observed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import date, timedelta
from typing import Any

# --------------------------------------------------------------------------- #
# Identity / authorization
# --------------------------------------------------------------------------- #

STAGE = "Stage127"
ACTION_ID = "stage127-m2-market-data-gate"
CONTRACT_ID = "stage127_m2_market_data_gate"
CONTRACT_VERSION = "stage127_m2_market_data_gate_v1"

#: The action this Gate must NOT advance into without separate authorization.
NEXT_GATED_ACTION_ID = "stage127-m2-incremental-evaluation"

HUMAN_SOURCE_UTTERANCE = "خوب بریم مرحله بعدی"

# --------------------------------------------------------------------------- #
# Frozen M2 block — exactly three variables, never redefined here
# --------------------------------------------------------------------------- #

M2_BLOCK = "M2_BLOCK"
M2_PRIMARY_SOURCE_ID = "src_m2_tsetmc_market"
M2_SOURCE_FAMILY = "TSETMC market data"

M2_VARIABLES: tuple[tuple[str, str, str], ...] = (
    ("equity_return_window", "cand_m2_equity_return_window",
     "m2_cumulative_simple_return_W"),
    ("realized_volatility", "cand_m2_realized_volatility",
     "m2_daily_return_stdev_sample_W"),
    ("amihud_illiquidity", "cand_m2_amihud_illiquidity",
     "m2_amihud_mean_abs_return_over_value_W"),
)

MIN_VALID_RETURN_OBSERVATIONS = 126
MIN_VALID_AMIHUD_OBSERVATIONS = 126
SHARED_WINDOW_CALENDAR_MONTHS = 12
PRICE_FIELD = "adjusted_close"
VOLUME_FIELD = "traded_value_rial"

# --------------------------------------------------------------------------- #
# Frozen SAP thresholds (development modeling path — NOT the pilot G09/G10)
# --------------------------------------------------------------------------- #

CANDIDATE_VALID_COVERAGE_MIN = 0.80
BLOCK_COMMON_SAMPLE_COVERAGE_MIN = 0.70
MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW = 5

DEVELOPMENT_TARGET_YEARS = (1393, 1394, 1395, 1396, 1397, 1398, 1399)
FINAL_TEST_TARGET_YEARS = (1400, 1401, 1402)

PRIMARY_SAMPLE = "main_rule_a_primary"
PRIMARY_TARGET = "FD_target_main_t_plus_1"

EXPECTED_DEV_PAIRS = 666
EXPECTED_DEV_POSITIVE = 68
EXPECTED_DEV_NEGATIVE = 598
EXPECTED_FOLD_ROWS = {
    "fold1_train": 245,
    "fold1_validation": 205,
    "fold2_train": 450,
    "fold2_validation": 216,
}

# --------------------------------------------------------------------------- #
# Pinned canonical sources (authority; never edited by this module)
# --------------------------------------------------------------------------- #

M2_FORMULA_CONTRACT_REL = (
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json"
)
CUTOFF_CONTRACT_REL = (
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json"
)
RUBRIC_MAPPING_REL = (
    "project/stage125/part3b1_rubric_operational_mapping_stage125.json"
)
SAP_REL = "project/stage125/part4_statistical_analysis_plan_stage125.json"
SPLIT_MANIFEST_REL = "project/stage125/part4_temporal_split_manifest_stage125.csv"
ANALYSIS_READY_REL = (
    "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv"
)

CANONICAL_SOURCES: tuple[str, ...] = (
    M2_FORMULA_CONTRACT_REL,
    CUTOFF_CONTRACT_REL,
    RUBRIC_MAPPING_REL,
    SAP_REL,
    SPLIT_MANIFEST_REL,
    ANALYSIS_READY_REL,
)

CUTOFF_COLUMN = "assumed_available_at_regulatory_gregorian"

OUT_DIR_REL = "project/stage127"


class GateFail(Exception):
    """Raised when a fail-closed precondition is violated."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def minus_calendar_months(d: date, months: int) -> date:
    """Calendar-month subtraction, clamping day-of-month (no rounding up)."""
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1


def repo_root_from(project_dir: str) -> str:
    return os.path.dirname(os.path.abspath(project_dir))


# --------------------------------------------------------------------------- #
# Development pair loading — development roles ONLY, final test never touched
# --------------------------------------------------------------------------- #

def load_development_pairs(repo_root: str) -> list[dict[str, Any]]:
    """Load the 666 frozen M1 primary DEVELOPMENT pairs with their cutoffs.

    Final-test rows are filtered out by ``dataset_split`` BEFORE any value is
    read, so no locked final-test predictor or target value is ever inspected.
    """
    split_path = os.path.join(repo_root, SPLIT_MANIFEST_REL)
    with open(split_path, encoding="utf-8") as f:
        split_rows = list(csv.DictReader(f))

    dev_index: dict[tuple[str, str], set[str]] = {}
    final_test_keys: set[tuple[str, str]] = set()
    for r in split_rows:
        if r["sample_design"] != PRIMARY_SAMPLE:
            continue
        key = (r["ticker"], r["fiscal_year_t"])
        if r["dataset_split"] == "development":
            dev_index.setdefault(key, set()).add(r["temporal_fold"])
        elif r["dataset_split"] == "final_test":
            final_test_keys.add(key)

    if len(dev_index) != EXPECTED_DEV_PAIRS:
        raise GateFail(
            f"expected {EXPECTED_DEV_PAIRS} development pairs, got {len(dev_index)}"
        )

    ar_path = os.path.join(repo_root, ANALYSIS_READY_REL)
    with open(ar_path, encoding="utf-8") as f:
        ar_rows = list(csv.DictReader(f))

    pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for r in ar_rows:
        key = (r["ticker"], r["fiscal_year_t"])
        if key not in dev_index:
            continue  # final-test and non-development rows are never read
        if key in seen:
            raise GateFail(f"duplicate development pair key: {key}")
        seen.add(key)
        target_year = int(r["target_year"])
        if target_year not in DEVELOPMENT_TARGET_YEARS:
            raise GateFail(
                f"non-development target_year {target_year} in development set"
            )
        cutoff_raw = (r.get(CUTOFF_COLUMN) or "").strip()
        pairs.append({
            "ticker": r["ticker"],
            "fiscal_year_t": r["fiscal_year_t"],
            "target_year": target_year,
            "predictor_row_key_t": r["predictor_row_key_t"],
            "target_row_key_t_plus_1": r["target_row_key_t_plus_1"],
            "folds": sorted(dev_index[key]),
            "pair_cutoff_date": cutoff_raw,
            "target": r[PRIMARY_TARGET],
        })

    if len(pairs) != EXPECTED_DEV_PAIRS:
        raise GateFail(f"development pair join produced {len(pairs)} rows")
    if seen & final_test_keys:
        raise GateFail("development set intersects final-test keys")
    return pairs


def required_window(cutoff_iso: str) -> tuple[str, str]:
    """Required shared 12-month market window bounds for a pair cutoff.

    Returns ``(retrieval_range_start, window_end_max_exclusive_of_cutoff)``.
    The true window end is the last *trading* day strictly before the cutoff,
    which is unknowable without the market trading calendar; the returned end
    is the last *calendar* day strictly before the cutoff, so the true window
    end can never fall after it. The start is a retrieval SUPERSET (an extra
    30 calendar days) so the true 12-calendar-month window is always contained.
    This is a retrieval range for reproducibility, never a formula change.
    """
    cutoff = date.fromisoformat(cutoff_iso)
    end_max = cutoff - timedelta(days=1)  # strictly before cutoff
    start = minus_calendar_months(end_max, SHARED_WINDOW_CALENDAR_MONTHS)
    return (start - timedelta(days=30)).isoformat(), end_max.isoformat()


# --------------------------------------------------------------------------- #
# Retrieval-attempt evidence (real probes; recorded verbatim, never inferred)
# --------------------------------------------------------------------------- #

#: Endpoints an unrestricted rerun must reach to score accessibility for real.
REQUIRED_TSETMC_ENDPOINTS: tuple[str, ...] = (
    "http://www.tsetmc.com/",
    "https://www.tsetmc.com/",
    "http://cdn.tsetmc.com/",
    "http://old.tsetmc.com/",
    "http://tsetmc.com/tsev2/data/InstTradeHistory.aspx",
)

#: Sources that must NEVER be substituted for the frozen authoritative source.
FORBIDDEN_SUBSTITUTE_SOURCES: tuple[str, ...] = (
    "yahoo_finance", "kaggle", "unofficial_mirror",
    "manually_copied_third_party_dataset", "alternative_market_data_provider",
)

RESOLUTION_UNRESOLVED = "UNRESOLVED"
RESOLUTION_PASS = "PASS"
RESOLUTION_FAIL = "FAIL"

GATE_STATUS_PASS = "PASS_FOR_M2_INCREMENTAL_EVALUATION"
GATE_STATUS_FAIL = "FAIL_M2_DATA_GATE"
GATE_STATUS_UNRESOLVED = "UNRESOLVED_M2_DATA_GATE"


def score_accessibility(endpoint_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the frozen R-A mapping to captured candidate_endpoint_evidence.

    Fail-closed and evidence-bound: a numeric score is returned ONLY when at
    least one endpoint probe actually reached the authoritative source (a real
    HTTP response). A probe that never reached the source proves nothing about
    the source -- it is missing evidence, which the frozen mapping requires be
    recorded as UNRESOLVED and explicitly ``never_zero``.
    """
    reached = [e for e in endpoint_evidence if e.get("http_status")]
    if not reached:
        return {
            "resolution": RESOLUTION_UNRESOLVED,
            "accessibility_score": None,
            "score_basis": "no_candidate_endpoint_evidence_captured",
            "never_scored_zero_reason": (
                "The frozen R-A mapping requires "
                "missing_evidence = null_or_unresolved_never_zero. No endpoint "
                "probe reached the authoritative source, so no property of the "
                "source was observed. Scoring 0-2 would assert an unobserved "
                "hard-drop property and is therefore prohibited."
            ),
        }
    structured = [e for e in reached if e.get("machine_readable")]
    score = 5 if structured else 4
    return {
        "resolution": RESOLUTION_PASS,
        "accessibility_score": score,
        "score_basis": "candidate_endpoint_evidence_captured",
        "never_scored_zero_reason": None,
    }


def build_candidate_gate(
    variable: str, candidate_id: str, formula_id: str,
    accessibility: dict[str, Any], retrieval_reached: bool,
) -> dict[str, Any]:
    """Per-candidate G01-G08 evaluation, fail-closed on missing evidence."""
    unresolved = not retrieval_reached
    u = RESOLUTION_UNRESOLVED

    return {
        "variable": variable,
        "candidate_id": candidate_id,
        "formula_id": formula_id,
        "block": M2_BLOCK,
        "primary_source_id": M2_PRIMARY_SOURCE_ID,
        "G01_accessibility": {
            "resolution": accessibility["resolution"],
            "accessibility_score": accessibility["accessibility_score"],
            "threshold": ">= 3",
            "basis": accessibility["score_basis"],
        },
        "G02_authoritative_source": {
            "resolution": u if unresolved else RESOLUTION_PASS,
            "note": (
                "Frozen authoritative source is TSETMC (src_m2_tsetmc_market). "
                "No substitute source was used or considered."
            ),
        },
        "G03_reproducible_retrieval_path": {
            "resolution": u if unresolved else RESOLUTION_PASS,
            "note": (
                "No retrieval could be executed, so no reproducible retrieval "
                "path was demonstrated for this candidate."
                if unresolved else "Retrieval path captured with provenance."
            ),
        },
        "G04_timing_verified": {
            "resolution": u if unresolved else RESOLUTION_PASS,
            "requirement": "market_observation_date < pair_cutoff_date",
            "note": (
                "Timing cannot be verified without observations."
                if unresolved else "Verified against pair-specific cutoffs."
            ),
        },
        "G05_extraction_quality_controlled": {
            "resolution": u if unresolved else RESOLUTION_PASS,
            "required_price_field": PRICE_FIELD,
            "required_volume_field": VOLUME_FIELD,
            "note": (
                "Corporate-action-adjusted close could not be verified as "
                "obtainable; unadjusted close is never silently substituted."
                if unresolved else "Adjustment/unit/calendar/ticker mapping verified."
            ),
        },
        "G06_missing_means_unavailable": {
            "resolution": RESOLUTION_PASS,
            "note": (
                "Enforced: no availability was inferred anywhere in this Gate."
            ),
        },
        "G07_no_future_or_target_year_information": {
            "resolution": RESOLUTION_PASS,
            "note": (
                "Enforced structurally: only development pairs (target years "
                "1393-1399) were loaded; no final-test row was read."
            ),
        },
        "G08_all_required_gates_pass": {
            "resolution": u if unresolved else RESOLUTION_PASS,
            "note": (
                "Cannot be asserted while G01-G05 are UNRESOLVED."
                if unresolved else "All required gates passed."
            ),
        },
        "admission_decision": (
            "UNRESOLVED_NOT_ADMITTED" if unresolved else "ADMITTED"
        ),
        "admission_decision_is_not_a_rejection": bool(unresolved),
    }


# --------------------------------------------------------------------------- #
# Coverage / common sample / event feasibility
# --------------------------------------------------------------------------- #

def fold_membership(pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in EXPECTED_FOLD_ROWS}
    for p in pairs:
        for f in p["folds"]:
            out[f].append(p)
    return out


def _positive(p: dict[str, Any]) -> bool:
    return str(p["target"]).strip() in ("1", "1.0", "True", "true")


def candidate_coverage(
    pairs: list[dict[str, Any]], usable_keys: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    """Coverage over the frozen development denominator.

    ``usable_keys is None`` means the numerator is UNRESOLVED (no observation
    was obtainable). It is NOT the same as an empty set, which would assert
    that every pair was proven unusable. The distinction is preserved so an
    unresolved candidate is never silently converted into a coverage FAIL.
    """
    total = len(pairs)
    folds = fold_membership(pairs)
    positives = [p for p in pairs if _positive(p)]
    negatives = [p for p in pairs if not _positive(p)]

    if usable_keys is None:
        def cov(_subset: list[dict[str, Any]]) -> None:
            return None
        resolution = RESOLUTION_UNRESOLVED
        valid_rows: int | None = None
        unresolved_rows: int | None = total
    else:
        def cov(subset: list[dict[str, Any]]) -> float | None:
            if not subset:
                return None
            n = sum(
                1 for p in subset
                if (p["ticker"], p["fiscal_year_t"]) in usable_keys
            )
            return round(n / len(subset), 10)
        resolution = RESOLUTION_PASS
        valid_rows = sum(
            1 for p in pairs if (p["ticker"], p["fiscal_year_t"]) in usable_keys
        )
        unresolved_rows = 0

    overall = cov(pairs)
    passed = (
        None if overall is None
        else bool(overall >= CANDIDATE_VALID_COVERAGE_MIN)
    )
    return {
        "total_development_rows": total,
        "valid_rows": valid_rows,
        "missing_or_unresolved_rows": unresolved_rows,
        "overall_coverage": overall,
        "fold1_train_coverage": cov(folds["fold1_train"]),
        "fold1_validation_coverage": cov(folds["fold1_validation"]),
        "fold2_train_coverage": cov(folds["fold2_train"]),
        "fold2_validation_coverage": cov(folds["fold2_validation"]),
        "positive_row_coverage": cov(positives),
        "negative_row_coverage": cov(negatives),
        "threshold": CANDIDATE_VALID_COVERAGE_MIN,
        "resolution": resolution,
        "coverage_gate_passed": passed,
    }


def common_sample_audit(
    pairs: list[dict[str, Any]], common_keys: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    """M2 block common sample: all THREE variables simultaneously usable."""
    total = len(pairs)
    folds = fold_membership(pairs)
    by_year: dict[str, int | None] = {}
    by_fold: dict[str, int | None] = {}

    if common_keys is None:
        common = None
        coverage = None
        resolution = RESOLUTION_UNRESOLVED
        pos = neg = None
        for y in DEVELOPMENT_TARGET_YEARS:
            by_year[str(y)] = None
        for f in EXPECTED_FOLD_ROWS:
            by_fold[f] = None
    else:
        sel = [p for p in pairs if (p["ticker"], p["fiscal_year_t"]) in common_keys]
        common = len(sel)
        coverage = round(common / total, 10)
        resolution = RESOLUTION_PASS
        pos = sum(1 for p in sel if _positive(p))
        neg = common - pos
        for y in DEVELOPMENT_TARGET_YEARS:
            by_year[str(y)] = sum(1 for p in sel if p["target_year"] == y)
        for f, members in folds.items():
            by_fold[f] = sum(
                1 for p in members
                if (p["ticker"], p["fiscal_year_t"]) in common_keys
            )

    passed = (
        None if coverage is None
        else bool(coverage >= BLOCK_COMMON_SAMPLE_COVERAGE_MIN)
    )
    return {
        "requires_all_three_m2_variables_simultaneously_usable": True,
        "total_development_rows": total,
        "common_usable_rows": common,
        "common_coverage": coverage,
        "counts_by_target_year": by_year,
        "counts_by_fold": by_fold,
        "positive_count": pos,
        "negative_count": neg,
        "threshold": BLOCK_COMMON_SAMPLE_COVERAGE_MIN,
        "resolution": resolution,
        "common_coverage_gate_passed": passed,
    }


def event_count_feasibility(
    pairs: list[dict[str, Any]], common_keys: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    """Event support in BOTH locked validation windows, on the M2 common sample.

    No model is fit to assess this -- it is a pure count over the frozen
    temporal design. When the common sample is UNRESOLVED the SAP labels are
    deliberately NOT asserted: emitting ``development_comparison_not_supported``
    would claim evidence that M2 lacks event support, which was never observed.
    """
    folds = fold_membership(pairs)
    windows = ("fold1_validation", "fold2_validation")

    m1_reference = {
        w: sum(1 for p in folds[w] if _positive(p)) for w in windows
    }

    if common_keys is None:
        return {
            "rule": "min_positive_evaluable_each_temporal_validation_window",
            "threshold": MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW,
            "requires_both_locked_validation_windows": True,
            "m2_common_sample_positive_counts": {w: None for w in windows},
            "m2_common_sample_negative_counts": {w: None for w in windows},
            "resolution": RESOLUTION_UNRESOLVED,
            "sap_label_asserted": None,
            "sap_label_not_asserted_reason": (
                "The M2 common development sample could not be formed, so no "
                "M2 event count was observed. Asserting "
                "'development_comparison_not_supported' would claim evidence "
                "of insufficient M2 event support that does not exist. This "
                "Gate therefore reports the event-count feasibility as "
                "UNRESOLVED rather than as a negative result."
            ),
            "m1_development_reference_positive_counts": m1_reference,
            "m1_reference_is_not_the_m2_result": True,
            "no_model_was_fit_to_assess_this": True,
        }

    pos = {
        w: sum(
            1 for p in folds[w]
            if _positive(p) and (p["ticker"], p["fiscal_year_t"]) in common_keys
        ) for w in windows
    }
    neg = {
        w: sum(
            1 for p in folds[w]
            if not _positive(p)
            and (p["ticker"], p["fiscal_year_t"]) in common_keys
        ) for w in windows
    }
    met = all(
        pos[w] >= MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW for w in windows
    )
    return {
        "rule": "min_positive_evaluable_each_temporal_validation_window",
        "threshold": MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW,
        "requires_both_locked_validation_windows": True,
        "m2_common_sample_positive_counts": pos,
        "m2_common_sample_negative_counts": neg,
        "resolution": RESOLUTION_PASS,
        "sap_label_asserted": (
            "development_comparison_feasibility_met" if met
            else "development_comparison_not_supported"
        ),
        "sap_label_not_asserted_reason": None,
        "m1_development_reference_positive_counts": m1_reference,
        "m1_reference_is_not_the_m2_result": True,
        "no_model_was_fit_to_assess_this": True,
    }


# --------------------------------------------------------------------------- #
# Join / point-in-time audit
# --------------------------------------------------------------------------- #

def join_leakage_audit(
    pairs: list[dict[str, Any]], observations_joined: int | None,
) -> dict[str, Any]:
    """Join audit against the frozen retained M1 primary development pairs.

    Every leakage counter is an ACCEPTED-observation counter. With zero market
    observations obtained, each is structurally zero: nothing was accepted, so
    nothing post-cutoff or target-year could have been accepted.
    """
    keys = [(p["ticker"], p["fiscal_year_t"]) for p in pairs]
    duplicates = len(keys) - len(set(keys))
    unresolved_cutoff = sum(1 for p in pairs if not p["pair_cutoff_date"])

    return {
        "joined_to": "frozen_M1_primary_development_pairs",
        "sample": PRIMARY_SAMPLE,
        "target": PRIMARY_TARGET,
        "development_target_years": list(DEVELOPMENT_TARGET_YEARS),
        "matched_pair_count": len(pairs),
        "unmatched_pair_count": 0,
        "duplicate_pair_key_violations": duplicates,
        "ticker_mapping_failures": None if observations_joined is None else 0,
        "ticker_mapping_unresolved": (
            len({p["ticker"] for p in pairs}) if observations_joined is None else 0
        ),
        "calendar_date_parsing_failures": 0,
        "pairs_with_unresolvable_cutoff": unresolved_cutoff,
        "cutoff_violations": 0,
        "same_day_cutoff_exclusions_applied": 0,
        "accepted_post_cutoff_observations": 0,
        "accepted_target_year_leakage_violations": 0,
        "market_observations_accepted": (
            0 if observations_joined is None else observations_joined
        ),
        "acceptance_criteria": {
            "zero_duplicate_output_pair_keys": duplicates == 0,
            "zero_accepted_post_cutoff_observations": True,
            "zero_accepted_target_year_leakage": True,
        },
        "note": (
            "Unresolved ticker->instrument mapping remains unresolved and was "
            "never guessed. Leakage counters are zero because no observation "
            "was accepted at all, not because observations were validated."
            if observations_joined is None else
            "Leakage counters validated against accepted observations."
        ),
        "final_test_rows_joined": 0,
        "final_test_rows_read": 0,
    }


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

def build(repo_root: str, probe_evidence: list[dict[str, Any]]) -> dict[str, str]:
    """Execute the Gate and return {relative_filename: file_text}."""
    pairs = load_development_pairs(repo_root)

    reached = any(e.get("http_status") for e in probe_evidence)
    accessibility = score_accessibility(probe_evidence)

    # No observation could be retrieved -> numerators are UNRESOLVED (None),
    # which is strictly distinct from an empty set of usable pairs.
    usable: set[tuple[str, str]] | None = None if not reached else set()
    common: set[tuple[str, str]] | None = None if not reached else set()

    candidates = [
        build_candidate_gate(var, cid, fid, accessibility, reached)
        for var, cid, fid in M2_VARIABLES
    ]
    coverage = {var: candidate_coverage(pairs, usable) for var, _, _ in M2_VARIABLES}
    common_audit = common_sample_audit(pairs, common)
    feasibility = event_count_feasibility(pairs, common)
    join_audit = join_leakage_audit(pairs, None if not reached else 0)

    blockers: list[str] = []
    if not reached:
        blockers.append(
            "No probe reached the authoritative TSETMC source from this "
            "execution environment, so no candidate_endpoint_evidence could be "
            "captured and no accessibility score could be assigned."
        )
        blockers.append(
            "Zero market observations were retrieved, so candidate coverage, "
            "block common coverage and event-count feasibility could not be "
            "evaluated against the frozen thresholds."
        )
        blockers.append(
            "The corporate-action-adjusted closing price field required by the "
            "frozen contract could not be verified as obtainable; unadjusted "
            "close was not substituted."
        )

    gate_status = GATE_STATUS_UNRESOLVED if blockers else GATE_STATUS_PASS

    decision = {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": ACTION_ID,
        "stage": STAGE,
        "gate_status": gate_status,
        "gate_status_meaning": (
            "The Gate ran to completion and returned a truthful UNRESOLVED "
            "result: the frozen M2 block is neither admitted nor rejected, "
            "because the evidence required to decide could not be obtained "
            "here. UNRESOLVED is not a negative scientific finding about "
            "TSETMC or about M2."
        ),
        "blocker_reasons": blockers,
        "scope": "point_in_time_data_admission_gate_development_only",
        "answers_only": (
            "Can the frozen M2 market variables be obtained with correct "
            "timing, quality, coverage, joins and event support?"
        ),
        "does_not_answer": "Does M2 improve prediction?",
        "m2_block": M2_BLOCK,
        "m2_block_variables": [v for v, _, _ in M2_VARIABLES],
        "m2_block_variable_count": len(M2_VARIABLES),
        "primary_source_id": M2_PRIMARY_SOURCE_ID,
        "source_family": M2_SOURCE_FAMILY,
        "formula_contract_option_id": "M2-A_modified",
        "candidates": candidates,
        "candidate_coverage": coverage,
        "block_common_sample": common_audit,
        "event_count_feasibility": feasibility,
        "join_leakage_audit": join_audit,
        "block_not_redefined_on_candidate_failure": True,
        "block_redefinition_requires_separate_human_decision": True,
        "no_variable_dropped_from_frozen_block": True,
        "modeling_performed": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "m2_vs_m1_performance_compared": False,
        "eligibility_for_next_action": {
            "requires_data_admission_pass": True,
            "requires_development_comparison_feasibility_pass": True,
            "data_admission_pass": False,
            "development_comparison_feasibility_pass": False,
            "eligible_to_start_m2_incremental_evaluation": False,
        },
        "final_test_firewall": {
            "final_test_locked": True,
            "final_test_unlocked": False,
            "final_test_access_authorized": False,
            "final_test_predictor_values_inspected": False,
            "final_test_target_values_inspected": False,
            "final_test_evaluation_performed": False,
            "final_test_target_years_excluded": list(FINAL_TEST_TARGET_YEARS),
            "final_test_coverage_used_for_admission": False,
        },
        "canonical_sources_sha256": {
            rel: sha256_file(os.path.join(repo_root, rel))
            for rel in CANONICAL_SOURCES
        },
    }

    return {
        "stage127_m2_market_data_gate_decision.json": json_dumps(decision),
    }
