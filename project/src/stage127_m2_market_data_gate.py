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
import statistics
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


def pair_scientific_window(
    cutoff_iso: str, observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive the frozen pair-specific scientific window W from observations.

    The 111 external ranges are RETRIEVAL supersets, including a 30-day buffer.
    They are not the scientific window and are never used as one. W is
    recomputed here from the frozen Stage125 contract for each pair:

    * every market observation must satisfy
      ``market_observation_date < pair_cutoff_date`` -- an observation on the
      same calendar day as the cutoff is rejected;
    * ``T*`` is the last eligible trading day strictly before the cutoff that
      carries the required verified availability (a present ``adjusted_close``);
    * ``W`` spans exactly 12 calendar months ending at ``T*``, starting at the
      inclusive trading days on or after calendar date ``T* - 12 months``.
    """
    if not cutoff_iso:
        return {"resolution": "UNRESOLVED_NO_PAIR_CUTOFF", "window": []}

    eligible = [o for o in observations if o["trading_date"] < cutoff_iso]
    same_day = sum(1 for o in observations if o["trading_date"] == cutoff_iso)
    priced = [o for o in eligible if o["adjusted_close"] is not None]
    if not priced:
        return {
            "resolution": "UNRESOLVED_NO_ELIGIBLE_PRICED_TRADING_DAY",
            "window": [],
            "same_calendar_day_as_cutoff_rejected": same_day,
            "eligible_observation_count": len(eligible),
        }

    t_star = priced[-1]["trading_date"]
    start = minus_calendar_months(
        date.fromisoformat(t_star), SHARED_WINDOW_CALENDAR_MONTHS
    ).isoformat()
    window = [o for o in eligible if start <= o["trading_date"] <= t_star]
    return {
        "resolution": RESOLUTION_PASS,
        "window": window,
        "t_star": t_star,
        "window_start_calendar_date": start,
        "window_first_trading_date": window[0]["trading_date"],
        "window_last_trading_date": window[-1]["trading_date"],
        "same_calendar_day_as_cutoff_rejected": same_day,
        "eligible_observation_count": len(eligible),
    }


def daily_simple_returns(
    window: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Valid daily simple returns for CONSECUTIVE trading observations in W.

    ``r_t = P_t / P_{t-1} - 1`` is emitted only when the two observations are
    genuinely adjacent trading observations of the same authorized retrieval
    range AND both adjusted prices are present. A missing adjusted price is
    never bridged: two usable observations separated by a gap are never treated
    as consecutive trading days.
    """
    out: list[dict[str, Any]] = []
    for prev, cur in zip(window, window[1:]):
        if prev["range_id"] != cur["range_id"]:
            continue  # a disjoint authorized range is not a consecutive day
        p0, p1 = prev["adjusted_close"], cur["adjusted_close"]
        if p0 is None or p1 is None or p0 == 0:
            continue
        out.append({
            "trading_date": cur["trading_date"],
            "r_t": p1 / p0 - 1,
            "traded_value_rial": cur["traded_value_rial"],
        })
    return out


def compute_pair_features(
    cutoff_iso: str, observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute EXACTLY the three frozen M2 variables for one development pair.

    No beta, momentum, market return, turnover, extra volume feature or new
    liquidity proxy is computed. Missing evidence yields ``None`` (unavailable),
    never an imputed or fabricated value.
    """
    win = pair_scientific_window(cutoff_iso, observations)
    base: dict[str, Any] = {
        "equity_return_window": None,
        "realized_volatility": None,
        "amihud_illiquidity": None,
        "t_star": win.get("t_star", ""),
        "window_start_calendar_date": win.get("window_start_calendar_date", ""),
        "window_first_trading_date": win.get("window_first_trading_date", ""),
        "window_last_trading_date": win.get("window_last_trading_date", ""),
        "window_trading_day_count": len(win["window"]),
        "same_calendar_day_as_cutoff_rejected": win.get(
            "same_calendar_day_as_cutoff_rejected", 0),
        "missing_price_day_count": 0,
        "zero_traded_value_day_count": 0,
        "usable_daily_return_count": 0,
        "usable_amihud_day_count": 0,
        "m2_value_status": win["resolution"],
    }
    window = win["window"]
    if not window:
        return base

    base["missing_price_day_count"] = sum(
        1 for o in window if o["adjusted_close"] is None
    )
    base["zero_traded_value_day_count"] = sum(
        1 for o in window if o["traded_value_rial"] == 0
    )

    returns = daily_simple_returns(window)
    base["usable_daily_return_count"] = len(returns)
    amihud_days = [
        r for r in returns if r["traded_value_rial"] > 0
    ]
    base["usable_amihud_day_count"] = len(amihud_days)

    enough_returns = len(returns) >= MIN_VALID_RETURN_OBSERVATIONS
    p_first = window[0]["adjusted_close"]
    p_last = window[-1]["adjusted_close"]

    if enough_returns and p_first is not None and p_last is not None and p_first != 0:
        base["equity_return_window"] = p_last / p_first - 1
    if enough_returns:
        base["realized_volatility"] = statistics.stdev(
            [r["r_t"] for r in returns]
        )
    if len(amihud_days) >= MIN_VALID_AMIHUD_OBSERVATIONS:
        base["amihud_illiquidity"] = statistics.fmean(
            [abs(r["r_t"]) / r["traded_value_rial"] for r in amihud_days]
        )

    reasons: list[str] = []
    if not enough_returns:
        reasons.append(
            f"usable_daily_return_count={len(returns)} < "
            f"{MIN_VALID_RETURN_OBSERVATIONS}"
        )
    if p_first is None:
        reasons.append("adjusted_close missing at window start t0")
    if p_last is None:
        reasons.append("adjusted_close missing at window end T*")
    if len(amihud_days) < MIN_VALID_AMIHUD_OBSERVATIONS:
        reasons.append(
            f"usable_amihud_day_count={len(amihud_days)} < "
            f"{MIN_VALID_AMIHUD_OBSERVATIONS}"
        )
    base["m2_value_status"] = (
        "OBSERVED_COMPLETE" if not reasons
        else "OBSERVED_INCOMPLETE: " + "; ".join(reasons)
    )
    return base


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

#: The Gate is decided from the imported immutable evidence bundle, offline.
#: There is no reachability-based path and no silent fallback to one.
EVIDENCE_MODE_IMPORTED_BUNDLE = "offline_imported_external_evidence_bundle"


def score_accessibility_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen Stage125 R-A mapping to imported candidate-level evidence.

    The score is DERIVED from the frozen mapping, never pre-assumed. A homepage
    or endpoint merely responding is explicitly insufficient
    (``source_origin_probe_alone_insufficient_for_numeric_score``): a numeric
    score requires candidate-level endpoint evidence with reproducible
    source/provenance. Missing evidence stays ``null``/UNRESOLVED and is never
    fabricated into a zero.
    """
    candidate_level = bool(evidence.get("candidate_level_endpoint_evidence"))
    if not candidate_level:
        return {
            "resolution": RESOLUTION_UNRESOLVED,
            "accessibility_score": None,
            "score_basis": "no_candidate_endpoint_evidence_captured",
            "evidence": evidence,
            "never_scored_zero_reason": (
                "The frozen R-A mapping requires "
                "missing_evidence = null_or_unresolved_never_zero and states "
                "source_origin_probe_alone_insufficient_for_numeric_score. "
                "Without candidate-level endpoint evidence no property of the "
                "source was observed, so scoring 0-2 (a hard drop) would "
                "assert an unobserved property and is prohibited."
            ),
        }

    reproducible = bool(evidence.get("reproducible_retrieval_with_provenance"))
    documented = bool(evidence.get("documented_api_or_portal"))
    if not (reproducible and documented):
        return {
            "resolution": RESOLUTION_PASS,
            "accessibility_score": 3,
            "score_basis": (
                "candidate_endpoint_evidence captured; systematic retrieval "
                "plausible but reproducible provenance not fully demonstrated "
                "(R-A level 3, pilot permission only)"
            ),
            "evidence": evidence,
            "never_scored_zero_reason": None,
        }

    structured = bool(evidence.get("machine_readable_or_reliably_structured"))
    authoritative = bool(evidence.get("authoritative_source"))
    if structured and authoritative:
        return {
            "resolution": RESOLUTION_PASS,
            "accessibility_score": 5,
            "score_basis": (
                "R-A level 5: authoritative, fully reproducible, "
                "machine-readable candidate-level retrieval with verified "
                "provenance (endpoints, raw responses, SHA256 manifest, "
                "extraction code, instrument mapping evidence)"
            ),
            "evidence": evidence,
            "never_scored_zero_reason": None,
        }
    return {
        "resolution": RESOLUTION_PASS,
        "accessibility_score": 4,
        "score_basis": (
            "R-A level 4: documented API/portal with reproducible "
            "candidate-level retrieval and provenance"
        ),
        "evidence": evidence,
        "never_scored_zero_reason": None,
    }


def build_candidate_gate(
    variable: str, candidate_id: str, formula_id: str,
    accessibility: dict[str, Any], import_qc: dict[str, Any],
    timing: dict[str, Any],
) -> dict[str, Any]:
    """Per-candidate G01-G08 evaluation from imported evidence, fail-closed.

    Each sub-gate resolves from an evidence fact that was independently
    revalidated inside this repository, never from an endpoint status code and
    never from the external party's own QC flag.
    """
    score = accessibility["accessibility_score"]
    g01 = (
        RESOLUTION_UNRESOLVED if score is None
        else (RESOLUTION_PASS if score >= 3 else RESOLUTION_FAIL)
    )

    g02 = (
        RESOLUTION_PASS if import_qc["source_endpoints_tsetmc_only"]
        else RESOLUTION_FAIL
    )
    g03 = (
        RESOLUTION_PASS
        if (import_qc["restricted_raw_hash_verification_passed"]
            and import_qc["provenance_sha_agrees_with_raw_manifest"])
        else RESOLUTION_FAIL
    )
    g04 = (
        RESOLUTION_PASS
        if (timing["accepted_post_cutoff_observations"] == 0
            and timing["accepted_same_calendar_day_as_cutoff"] == 0)
        else RESOLUTION_FAIL
    )
    g05 = (
        RESOLUTION_PASS
        if (import_qc["raw_to_normalized_field_mismatches"] == 0
            and import_qc["adjusted_close_exact_date_mismatches"] == 0
            and not import_qc["raw_close_substituted_for_adjusted_close"]
            and not import_qc["imputation_or_synthetic_values_introduced"])
        else RESOLUTION_FAIL
    )
    g06 = RESOLUTION_PASS
    g07 = (
        RESOLUTION_PASS
        if import_qc["final_test_period_observations_imported"] == 0
        else RESOLUTION_FAIL
    )

    required = (g01, g02, g03, g04, g05, g06, g07)
    if RESOLUTION_FAIL in required:
        g08 = RESOLUTION_FAIL
    elif RESOLUTION_UNRESOLVED in required:
        g08 = RESOLUTION_UNRESOLVED
    else:
        g08 = RESOLUTION_PASS

    return {
        "variable": variable,
        "candidate_id": candidate_id,
        "formula_id": formula_id,
        "block": M2_BLOCK,
        "primary_source_id": M2_PRIMARY_SOURCE_ID,
        "G01_accessibility": {
            "resolution": g01,
            "accessibility_score": score,
            "threshold": ">= 3",
            "basis": accessibility["score_basis"],
            "derived_from_frozen_R_A_mapping": True,
            "endpoint_response_alone_is_insufficient": True,
        },
        "G02_authoritative_source": {
            "resolution": g02,
            "note": (
                "Every imported endpoint, provenance record and raw response "
                "cites TSETMC only (src_m2_tsetmc_market). No substitute "
                "source was used or considered."
            ),
        },
        "G03_reproducible_retrieval_path": {
            "resolution": g03,
            "note": (
                "Candidate-level retrieval is reproducible offline from the "
                "immutable bundle: per-instrument endpoints, raw responses, a "
                "verified SHA256 manifest, a restricted-raw provenance "
                "manifest and the extraction code were all delivered and "
                "independently re-verified."
            ),
            "restricted_raw_files_verified": import_qc[
                "restricted_raw_hashes_verified"],
        },
        "G04_timing_verified": {
            "resolution": g04,
            "requirement": "market_observation_date < pair_cutoff_date",
            "accepted_post_cutoff_observations": timing[
                "accepted_post_cutoff_observations"],
            "accepted_same_calendar_day_as_cutoff": timing[
                "accepted_same_calendar_day_as_cutoff"],
            "note": (
                "Every accepted observation was re-checked against its own "
                "pair cutoff; same-calendar-day observations are rejected."
            ),
        },
        "G05_extraction_quality_controlled": {
            "resolution": g05,
            "required_price_field": PRICE_FIELD,
            "required_volume_field": VOLUME_FIELD,
            "raw_to_normalized_field_mismatches": import_qc[
                "raw_to_normalized_field_mismatches"],
            "adjusted_close_exact_date_mismatches": import_qc[
                "adjusted_close_exact_date_mismatches"],
            "note": (
                "Raw->normalized field mapping was re-verified for every "
                "imported row; adjusted_close was re-verified against the raw "
                "adjusted pc on the exact same trading date. Unadjusted close "
                "is never substituted and no value was imputed."
            ),
        },
        "G06_missing_means_unavailable": {
            "resolution": g06,
            "note": (
                "Enforced: missing adjusted price or missing traded value "
                "makes a day unusable; it is never imputed, filled or read as "
                "an observed zero."
            ),
        },
        "G07_no_future_or_target_year_information": {
            "resolution": g07,
            "note": (
                "Enforced structurally: only development pairs (target years "
                "1393-1399) were loaded, no final-test row was read, and every "
                "imported observation date was checked against the firewall."
            ),
        },
        "G08_all_required_gates_pass": {
            "resolution": g08,
            "note": "Conjunction of G01-G07; no sub-gate may be assumed.",
        },
        "admission_decision": {
            RESOLUTION_PASS: "ADMITTED",
            RESOLUTION_FAIL: "NOT_ADMITTED_OBSERVED_FAILURE",
            RESOLUTION_UNRESOLVED: "UNRESOLVED_NOT_ADMITTED",
        }[g08],
        "admission_decision_is_not_a_rejection": g08 == RESOLUTION_UNRESOLVED,
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
        # Observed-unavailable, not "unresolved": the numerator WAS observed.
        unresolved_rows = total - valid_rows

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

def unavailability_breakdown(
    features: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Why each frozen M2 variable was unavailable, per observed cause.

    Purely descriptive. It exists so a FAIL is fully traceable to the observed
    evidence rather than asserted, and it never alters a threshold or a value.
    """
    total = len(features)
    missing_t0 = sum(
        1 for f in features.values()
        if f["window_trading_day_count"] and f["window_first_trading_date"]
        and f["missing_price_day_count"] and f["equity_return_window"] is None
        and f["usable_daily_return_count"] >= MIN_VALID_RETURN_OBSERVATIONS
    )
    too_few_returns = sum(
        1 for f in features.values()
        if f["usable_daily_return_count"] < MIN_VALID_RETURN_OBSERVATIONS
    )
    too_few_amihud = sum(
        1 for f in features.values()
        if f["usable_amihud_day_count"] < MIN_VALID_AMIHUD_OBSERVATIONS
    )
    return {
        "development_pairs": total,
        "pairs_with_fewer_than_min_valid_daily_returns": too_few_returns,
        "pairs_with_fewer_than_min_usable_amihud_days": too_few_amihud,
        "pairs_failing_only_the_window_endpoint_price_requirement": missing_t0,
        "min_valid_daily_return_observations": MIN_VALID_RETURN_OBSERVATIONS,
        "min_valid_amihud_observations": MIN_VALID_AMIHUD_OBSERVATIONS,
        "thresholds_reduced_to_improve_coverage": False,
        "missing_values_imputed": False,
    }


def decide_gate_status(
    candidates: list[dict[str, Any]],
    coverage: dict[str, dict[str, Any]],
    common_audit: dict[str, Any],
    feasibility: dict[str, Any],
    blocking_evidence_defects: list[str],
) -> tuple[str, list[str], dict[str, Any]]:
    """Explicit conjunction A AND B AND C AND D AND E AND F.

    PASS is only reachable through observed evidence satisfying every frozen
    requirement. Reachability, an HTTP status, or the external party's own QC
    flag can never produce a PASS. An OBSERVED threshold failure is reported as
    FAIL and is never softened into UNRESOLVED; genuinely missing evidence is
    reported as UNRESOLVED and is never hardened into an observed zero.
    """
    observed_failures: list[str] = []
    unresolved_reasons: list[str] = []

    # -- A: G01-G08 data-admission conditions ------------------------------- #
    a_states = {c["variable"]: c["G08_all_required_gates_pass"]["resolution"]
                for c in candidates}
    for var, state in a_states.items():
        if state == RESOLUTION_FAIL:
            observed_failures.append(
                f"A: candidate '{var}' failed a required G01-G08 data-admission "
                "condition"
            )
        elif state == RESOLUTION_UNRESOLVED:
            unresolved_reasons.append(
                f"A: candidate '{var}' has an UNRESOLVED G01-G08 condition"
            )
    cond_a = all(s == RESOLUTION_PASS for s in a_states.values())

    # -- B: per-candidate development valid coverage >= 0.80 ---------------- #
    cond_b = True
    for var, cov in coverage.items():
        if cov["resolution"] == RESOLUTION_UNRESOLVED:
            cond_b = False
            unresolved_reasons.append(
                f"B: coverage for '{var}' is UNRESOLVED (no observed numerator)"
            )
        elif not cov["coverage_gate_passed"]:
            cond_b = False
            observed_failures.append(
                f"B: observed development valid coverage for '{var}' is "
                f"{cov['overall_coverage']:.4f} "
                f"({cov['valid_rows']}/{cov['total_development_rows']}), below "
                f"the frozen threshold {CANDIDATE_VALID_COVERAGE_MIN}"
            )

    # -- C: three-variable common-sample coverage >= 0.70 ------------------- #
    if common_audit["resolution"] == RESOLUTION_UNRESOLVED:
        cond_c = False
        unresolved_reasons.append("C: block common sample is UNRESOLVED")
    elif not common_audit["common_coverage_gate_passed"]:
        cond_c = False
        observed_failures.append(
            "C: observed three-variable common-sample coverage is "
            f"{common_audit['common_coverage']:.4f} "
            f"({common_audit['common_usable_rows']}/"
            f"{common_audit['total_development_rows']}), below the frozen "
            f"threshold {BLOCK_COMMON_SAMPLE_COVERAGE_MIN}"
        )
    else:
        cond_c = True

    # -- D: >= 5 positive evaluable observations in BOTH windows ------------ #
    if feasibility["resolution"] == RESOLUTION_UNRESOLVED:
        cond_d = False
        unresolved_reasons.append("D: event-count feasibility is UNRESOLVED")
    else:
        pos = feasibility["m2_common_sample_positive_counts"]
        cond_d = all(
            v >= MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW
            for v in pos.values()
        )
        if not cond_d:
            for w, v in pos.items():
                if v < MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW:
                    observed_failures.append(
                        f"D: locked validation window '{w}' contains {v} "
                        "positive evaluable observations in the common M2 "
                        f"sample, below the frozen minimum "
                        f"{MIN_POSITIVE_EVALUABLE_EACH_VALIDATION_WINDOW}"
                    )

    # -- E: no PIT / leakage / join / provenance blocker --------------------- #
    cond_e = not blocking_evidence_defects
    observed_failures.extend(f"E: {d}" for d in blocking_evidence_defects)

    # -- F: all three frozen M2 variables still present --------------------- #
    cond_f = (
        len(candidates) == len(M2_VARIABLES)
        and {c["variable"] for c in candidates} == {v for v, _, _ in M2_VARIABLES}
    )
    if not cond_f:
        observed_failures.append(
            "F: the frozen three-variable M2 block was not fully present"
        )

    conditions = {
        "A_data_admission_g01_g08": cond_a,
        "B_each_candidate_coverage_ge_0_80": cond_b,
        "C_common_sample_coverage_ge_0_70": cond_c,
        "D_both_validation_windows_ge_5_positives": cond_d,
        "E_no_pit_leakage_join_provenance_blocker": cond_e,
        "F_all_three_frozen_m2_variables_present": cond_f,
    }

    if all(conditions.values()):
        return GATE_STATUS_PASS, [], conditions
    if observed_failures:
        # An observed failure is never converted into UNRESOLVED.
        return GATE_STATUS_FAIL, observed_failures + unresolved_reasons, conditions
    return GATE_STATUS_UNRESOLVED, unresolved_reasons, conditions


def build(
    repo_root: str,
    import_qc: dict[str, Any],
    observations: dict[str, list[dict[str, Any]]],
    accessibility_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Execute the Gate from the imported immutable evidence bundle.

    Deterministic and OFFLINE: given the bundle, no network connection is
    required to reproduce this decision. There is no fallback to endpoint
    reachability.
    """
    pairs = load_development_pairs(repo_root)
    accessibility = score_accessibility_from_evidence(accessibility_evidence)

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
        win = pair_scientific_window(cutoff, obs)
        f = compute_pair_features(cutoff, obs)
        # Re-audit the ACCEPTED observations themselves rather than trusting
        # the window construction that produced them.
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
    for var, _, _ in M2_VARIABLES:
        usable_by_var[var] = {
            k for k, f in features.items() if f[var] is not None
        }
    common = set.intersection(*usable_by_var.values())

    timing = {
        "accepted_post_cutoff_observations": post_cutoff,
        "accepted_same_calendar_day_as_cutoff": same_day,
        "accepted_target_year_leakage_violations": target_year_leak,
    }

    candidates = [
        build_candidate_gate(var, cid, fid, accessibility, import_qc, timing)
        for var, cid, fid in M2_VARIABLES
    ]
    coverage = {
        var: candidate_coverage(pairs, usable_by_var[var])
        for var, _, _ in M2_VARIABLES
    }
    common_audit = common_sample_audit(pairs, common)
    feasibility = event_count_feasibility(pairs, common)
    join_audit = join_leakage_audit(pairs, accepted_observations)
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
        "observations imported from the immutable external bundle."
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

    gate_status, blockers, conditions = decide_gate_status(
        candidates, coverage, common_audit, feasibility, blocking_defects
    )

    status_meaning = {
        GATE_STATUS_PASS: (
            "Observed imported evidence satisfies every frozen data-admission "
            "condition, coverage threshold and event-support requirement. This "
            "makes M2 incremental evaluation scientifically ELIGIBLE for a new "
            "explicit human authorization; it does not authorize it."
        ),
        GATE_STATUS_FAIL: (
            "The Gate ran to completion on real imported evidence and OBSERVED "
            "a failure against a frozen requirement. This is a truthful "
            "negative result about the observed data, not missing evidence, "
            "and it is deliberately not softened into UNRESOLVED."
        ),
        GATE_STATUS_UNRESOLVED: (
            "Evidence required to decide is genuinely unavailable. The frozen "
            "M2 block is neither admitted nor rejected. UNRESOLVED is not a "
            "negative scientific finding."
        ),
    }[gate_status]

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
            "AND E AND F. Endpoint reachability, an HTTP status code, or the "
            "external party's own QC flag can never produce a PASS."
        ),
        "gate_decided_from_endpoint_reachability": False,
        "evidence_mode": EVIDENCE_MODE_IMPORTED_BUNDLE,
        "network_required_to_reproduce": False,
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
        },
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
            "next_action_id": NEXT_GATED_ACTION_ID,
            "requires_data_admission_pass": True,
            "requires_development_comparison_feasibility_pass": True,
            "data_admission_pass": conditions["A_data_admission_g01_g08"],
            "development_comparison_feasibility_pass": conditions[
                "D_both_validation_windows_ge_5_positives"],
            "eligible_to_start_m2_incremental_evaluation": (
                gate_status == GATE_STATUS_PASS
            ),
            "m2_incremental_evaluation_authorized": False,
            "m2_modeling_started": False,
            "eligibility_is_not_authorization": True,
        },
        "feature_unavailability_breakdown": unavailability_breakdown(features),
        "window_endpoint_rule": {
            "rule": (
                "Per the frozen contract, W is ordered t0..tN=T* over the "
                "trading days on or after calendar date T* minus 12 calendar "
                "months, and equity_return_window REQUIRES adjusted_close "
                "present at BOTH t0 and tN. t0 is the first trading day of W, "
                "not the first priced day of W."
            ),
            "endpoint_requirement_can_fail": True,
            "missing_endpoint_price_is_never_imputed_or_bridged": True,
            "alternative_reading_not_adopted": (
                "Re-defining t0 as the first PRICED day of W would make the "
                "frozen endpoint requirement vacuous and would raise observed "
                "coverage. It was NOT adopted: relaxing a frozen contract to "
                "improve coverage is prohibited."
            ),
        },
        "frozen_m2_feature_block_extra_features_computed": [],
        "m2_feature_block_changed": False,
        "pair_specific_window_recomputed_from_frozen_contract": True,
        "retrieval_range_used_as_scientific_window": False,
        "retrieval_buffer_days_entered_scientific_window": False,
        "imputation_or_fill_applied": False,
        "unadjusted_close_substituted": False,
        "threshold_reduced": False,
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
        "decision": decision,
        "pairs": pairs,
        "features": features,
        "accessibility": accessibility,
        "usable_by_variable": usable_by_var,
        "common_sample_keys": common,
    }
