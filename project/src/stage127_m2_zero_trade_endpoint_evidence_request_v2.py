"""Stage127 — external evidence-request package v2.

Supersedes ``stage127_m2_zero_trade_endpoint_evidence_request`` (v1). v1 is
retained as historical record and MUST NOT be sent externally: it does not
cover the low-return sequence semantics question and its provenance/identity
schemas are too lossy (see the two blockers this module fixes).

v2 adds:
  * range-level low-return-sequence-semantics requests for the pairs whose
    <126-return outcome is only PENDING (not GUARANTEED) under the zero-trade
    upper-bound audit -- one bounded calendar-range request per pending pair,
    never one request per zero-trade date;
  * an explicit ``evidence_reason`` on every unique request
    (ENDPOINT_SEMANTICS / LOW_RETURN_SEQUENCE_SEMANTICS / BOTH);
  * a raw-evidence manifest whose unit is one row per actual retrieved raw
    artifact (an endpoint request may need several: calendar, state, trade
    history, ...), with a companion mapping table so one raw artifact can
    answer many requests without duplicating bytes;
  * a historical-identity schema with one row per identity CANDIDATE
    (including an explicit NONE_FOUND row when nothing is found), with all
    market-day/trading-day semantics removed from that template -- the
    external retriever reports literal TSETMC values only and never decides
    trading-day semantics, historical-identity joins, or Gate outcomes.

This module builds the REQUEST only. It does not query TSETMC, does not
decide any open question, and does not touch the canonical Gate.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from . import stage127_m2_equity_return_root_cause_audit as rca
from . import stage127_m2_external_delivery_import as imp
from . import stage127_m2_market_data_gate as gate
from . import stage127_m2_zero_trade_endpoint_evidence_request as v1

PACKAGE_NAME = "stage127_m2_zero_trade_endpoint_evidence_request_v2"
ZIP_NAME = f"{PACKAGE_NAME}.zip"

REASON_ENDPOINT = "ENDPOINT_SEMANTICS"
REASON_LOW_RETURN = "LOW_RETURN_SEQUENCE_SEMANTICS"
REASON_BOTH = "BOTH"

REQUEST_TYPE_POINT = "POINT_DATE"
REQUEST_TYPE_RANGE = "RANGE"

ENDPOINT_OCCURRENCE_COLUMNS = v1.ENDPOINT_OCCURRENCE_COLUMNS

LOW_RETURN_RANGE_COLUMNS: tuple[str, ...] = (
    "range_request_id",
    "predictor_row_key_t",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "current_InsCode",
    "current_ISIN",
    "range_start_date",
    "range_end_date",
    "window_observation_count",
    "zero_trade_day_count",
    "priced_observation_count",
    "current_valid_return_count",
    "max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading",
    "evidence_reason",
)

UNIQUE_REQUEST_V2_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "request_type",
    "InsCode",
    "ISIN",
    "ticker",
    "endpoint_date",
    "range_start_date",
    "range_end_date",
    "occurrence_count",
    "evidence_reason",
    "qTotCap",
    "qTotTran5J",
    "zTotTran",
    "raw_close",
)

PAIR_MAPPING_V2_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "reference_type",
    "reference_id",
)
REF_TYPE_ENDPOINT_OCCURRENCE = "ENDPOINT_OCCURRENCE"
REF_TYPE_LOW_RETURN_PAIR = "LOW_RETURN_PAIR"

LOW_RETURN_UPPER_BOUND_COLUMNS: tuple[str, ...] = (
    "ticker", "fiscal_year_t", "target_year", "window_observation_count",
    "zero_trade_day_count", "priced_observation_count",
    "current_valid_return_count",
    "max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading",
    "current_endpoint_requirements_pass", "classification",
)

# -- templates ---------------------------------------------------------- #

TEMPLATE_CALENDAR_COLUMNS = v1.TEMPLATE_CALENDAR_COLUMNS
TEMPLATE_STATE_COLUMNS = v1.TEMPLATE_STATE_COLUMNS
TEMPLATE_TRADE_COLUMNS = v1.TEMPLATE_TRADE_COLUMNS

#: Blocker 2: one row per actual retrieved raw artifact, never one row per
#: unique_request_id -- a single request may need several evidence surfaces.
RAW_EVIDENCE_MANIFEST_COLUMNS: tuple[str, ...] = (
    "evidence_artifact_id",
    "unique_request_id",
    "ticker",
    "InsCode",
    "endpoint_date",
    "evidence_type",
    "source_endpoint",
    "retrieval_status",
    "retrieved_at_utc",
    "raw_response_file",
    "raw_response_sha256",
    "parent_full_response_sha256",
    "bounded_response",
    "notes",
)
ALLOWED_EVIDENCE_TYPES: tuple[str, ...] = (
    "CALENDAR", "STATE", "TRADE_HISTORY", "DAILY_CLOSING",
    "INSTRUMENT_HISTORY", "INSTRUMENT_IDENTITY",
)

#: One raw artifact can support more than one unique_request_id (e.g. a single
#: calendar-range response answers every date inside it). This table is the
#: many-to-many link; RAW_EVIDENCE_MANIFEST_COLUMNS stays one row per artifact.
RAW_ARTIFACT_REQUEST_MAPPING_COLUMNS: tuple[str, ...] = (
    "evidence_artifact_id",
    "unique_request_id",
)

#: Blocker 2 (identity): one row per CANDIDATE historical identity. No
#: market-day/trading-day classification field -- that adjudication is a
#: downstream papermali decision, never the external retriever's.
TEMPLATE_IDENTITY_V2_COLUMNS: tuple[str, ...] = (
    "identity_evidence_id",
    "ticker",
    "current_InsCode",
    "current_ISIN",
    "candidate_historical_InsCode",
    "candidate_historical_ISIN",
    "candidate_valid_from",
    "candidate_valid_to",
    "source_endpoint",
    "raw_response_file",
    "raw_response_sha256",
    "evidence_status",
    "notes",
)
ALLOWED_IDENTITY_EVIDENCE_STATUS: tuple[str, ...] = (
    "CANDIDATE_FOUND", "NONE_FOUND", "UNRESOLVED",
)


def _csv_text(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_low_return_range_requests(
    audit: rca.RootCauseAudit,
    upper_bound_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One bounded range request per PENDING low-return pair.

    Deliberately range-level, never one row per zero-trade date: a single
    bounded instrument-calendar/state request over
    ``[window_start, window_end]`` lets the retriever answer every date in
    the window in one response. GUARANTEED pairs are excluded -- their
    outcome does not depend on this evidence.
    """
    pending = [
        u for u in upper_bound_rows
        if u["classification"] == rca.CAT_PENDING_LOW_RETURN_SEMANTICS
    ]
    pairs_by_key = {(p["ticker"], p["fiscal_year_t"]): p for p in audit.pairs}

    rows: list[dict[str, Any]] = []
    for i, u in enumerate(sorted(
        pending, key=lambda x: (x["target_year"], x["ticker"])
    ), start=1):
        ticker = u["ticker"]
        pair = pairs_by_key[(ticker, u["fiscal_year_t"])]
        cutoff = pair["pair_cutoff_date"]
        obs = audit.observations.get(ticker, [])
        win = gate.pair_scientific_window(cutoff, obs)
        window = win.get("window", [])
        mapping_row = audit.mapping[ticker]

        rows.append({
            "range_request_id": f"LRQ{i:04d}",
            "predictor_row_key_t": pair["predictor_row_key_t"],
            "ticker": ticker,
            "fiscal_year_t": u["fiscal_year_t"],
            "target_year": u["target_year"],
            "current_InsCode": mapping_row["tsetmc_instrument_id"],
            "current_ISIN": mapping_row["isin"],
            "range_start_date": window[0]["trading_date"] if window else "",
            "range_end_date": window[-1]["trading_date"] if window else "",
            "window_observation_count": u["window_observation_count"],
            "zero_trade_day_count": u["zero_trade_day_count"],
            "priced_observation_count": u["priced_observation_count"],
            "current_valid_return_count": u["current_valid_return_count"],
            "max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading": (
                u["max_possible_valid_returns_if_all_zero_trade_rows_are_non_trading"]
            ),
            "evidence_reason": REASON_LOW_RETURN,
        })
    return rows


def build_unique_requests_v2(
    occurrences: list[dict[str, Any]],
    range_requests: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicated request universe: POINT_DATE (endpoints) + RANGE (low-return).

    Point requests are deduplicated by (InsCode, date) exactly as in v1.
    Range requests are deduplicated by (InsCode, start, end) exactly -- no
    fuzzy interval merging, so the mapping stays simple and deterministic. A
    point request whose date falls inside a range request for the SAME
    InsCode is tagged ``evidence_reason=BOTH``, since the range response would
    already answer it.
    """
    point_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for o in occurrences:
        point_by_key.setdefault(
            (o["current_InsCode"], o["endpoint_date"]), []).append(o)

    range_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in range_requests:
        range_by_key.setdefault(
            (r["current_InsCode"], r["range_start_date"], r["range_end_date"]),
            [],
        ).append(r)

    unique_rows: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    uid_counter = 0

    # Range requests first so point-request overlap detection can consult them.
    ranges_by_inscode: dict[str, list[tuple[str, str]]] = {}
    for (ins_code, start, end) in range_by_key:
        ranges_by_inscode.setdefault(ins_code, []).append((start, end))

    for key in sorted(range_by_key):
        ins_code, start, end = key
        reqs = range_by_key[key]
        uid_counter += 1
        uid = f"UNQ{uid_counter:04d}"
        first = reqs[0]
        unique_rows.append({
            "unique_request_id": uid,
            "request_type": REQUEST_TYPE_RANGE,
            "InsCode": ins_code,
            "ISIN": first["current_ISIN"],
            "ticker": first["ticker"],
            "endpoint_date": "",
            "range_start_date": start,
            "range_end_date": end,
            "occurrence_count": len(reqs),
            "evidence_reason": REASON_LOW_RETURN,
            "qTotCap": "", "qTotTran5J": "", "zTotTran": "", "raw_close": "",
        })
        for r in reqs:
            mapping_rows.append({
                "unique_request_id": uid,
                "reference_type": REF_TYPE_LOW_RETURN_PAIR,
                "reference_id": r["predictor_row_key_t"],
            })

    for key in sorted(point_by_key):
        ins_code, endpoint_date = key
        occs = point_by_key[key]
        first = occs[0]
        overlaps_a_range = any(
            start <= endpoint_date <= end
            for start, end in ranges_by_inscode.get(ins_code, [])
        )
        uid_counter += 1
        uid = f"UNQ{uid_counter:04d}"
        unique_rows.append({
            "unique_request_id": uid,
            "request_type": REQUEST_TYPE_POINT,
            "InsCode": ins_code,
            "ISIN": first["current_ISIN"],
            "ticker": first["ticker"],
            "endpoint_date": endpoint_date,
            "range_start_date": "",
            "range_end_date": "",
            "occurrence_count": len(occs),
            "evidence_reason": REASON_BOTH if overlaps_a_range else REASON_ENDPOINT,
            "qTotCap": first["qTotCap"],
            "qTotTran5J": first["qTotTran5J"],
            "zTotTran": first["zTotTran"],
            "raw_close": first["raw_close"],
        })
        for o in occs:
            mapping_rows.append({
                "unique_request_id": uid,
                "reference_type": REF_TYPE_ENDPOINT_OCCURRENCE,
                "reference_id": o["request_id"],
            })

    return unique_rows, mapping_rows


def tickers_with_any_request(
    occurrences: list[dict[str, Any]], range_requests: list[dict[str, Any]],
) -> list[str]:
    return sorted({o["ticker"] for o in occurrences}
                  | {r["ticker"] for r in range_requests})


def build_readme(
    occurrences: list[dict[str, Any]],
    range_requests: list[dict[str, Any]],
    unique_rows: list[dict[str, Any]],
    upper_bound_rows: list[dict[str, Any]],
) -> str:
    tickers = tickers_with_any_request(occurrences, range_requests)
    n_t0 = sum(1 for o in occurrences if o["endpoint_type"] == "t0")
    n_tN = sum(1 for o in occurrences if o["endpoint_type"] == "tN")
    n_point = sum(1 for u in unique_rows if u["request_type"] == REQUEST_TYPE_POINT)
    n_range = sum(1 for u in unique_rows if u["request_type"] == REQUEST_TYPE_RANGE)
    n_both = sum(1 for u in unique_rows if u["evidence_reason"] == REASON_BOTH)
    target_years = sorted({o["target_year"] for o in occurrences}
                          | {r["target_year"] for r in range_requests})
    n_guaranteed = sum(
        1 for u in upper_bound_rows
        if u["classification"] == rca.CAT_GUARANTEED_LT126)
    n_pending_lr = sum(
        1 for u in upper_bound_rows
        if u["classification"] == rca.CAT_PENDING_LOW_RETURN_SEMANTICS)

    return f"""# TSETMC zero-trade & low-return semantics — evidence request (v2)

You do **not** need to know anything about the project this request comes
from. Please read this document fully before starting. **This v2 package
supersedes any earlier version you may have received — please use this one.**

## What we need

For a specific list of TSETMC **(instrument, date)** and **(instrument,
date-range)** requests, we need **authoritative TSETMC evidence** —
never your judgment or inference — about:

1. whether specific dates belong to the instrument's trading calendar;
2. the instrument's state on those dates (normal / suspended / prohibited /
   other);
3. whether trades actually occurred (count, volume, value);
4. whether the official adjusted-price history includes or omits those
   dates, and why;
5. whether TSETMC shows any **historical predecessor instrument identity**
   for the requested tickers.

**You will not compute, classify, or decide anything.** Report exactly what
the authoritative TSETMC endpoints return, with provenance. Mark anything you
cannot determine as `UNRESOLVED` rather than guessing.

## Source — TSETMC only

Use **only** official TSETMC (`tsetmc.com`) endpoints — calendar, instrument
state, trade history, closing price, instrument history, and instrument
identity surfaces, whichever actually answer each question. **Do not use**
Yahoo Finance, Kaggle, unofficial mirrors, or any third-party dataset.

## Two kinds of request — read this carefully

| request_type | meaning |
|---|---|
| `POINT_DATE` | one specific instrument/date, from an endpoint (`t0`/`T*`) that our records show as zero-trade |
| `RANGE` | one bounded date interval for an instrument, covering an entire scientific window where several zero-trade days break our valid-return count |

**Please do not fetch `RANGE` requests one date at a time.** If TSETMC's
calendar/state endpoint can return the whole interval in one response, use
that — it answers every date in the range at once and avoids thousands of
duplicate single-date requests.

`evidence_reason` tells you why each request exists:

- `ENDPOINT_SEMANTICS` — a `t0`/`T*` scientific-window endpoint;
- `LOW_RETURN_SEQUENCE_SEMANTICS` — part of a range needed to determine how
  many valid returns a window can have;
- `BOTH` — an endpoint date that also falls inside a requested range.

## Input files

| file | meaning |
|---|---|
| `input/endpoint_occurrence_requests.csv` | One row per **occurrence** — {len(occurrences)} rows ({n_t0} missing-`t0`, {n_tN} missing-`T*`). |
| `input/low_return_range_requests.csv` | One row per **PENDING** low-return pair — {len(range_requests)} rows. Pairs already proven `GUARANTEED_LT126_EVEN_IF_ALL_ZERO_TRADE_ROWS_EXCLUDED` are NOT included here; nothing further is needed for them. |
| `input/low_return_semantics_upper_bound_audit.csv` | All 90 `<126`-return development pairs, with the ceiling computation and classification, for context. |
| `input/unique_evidence_requests.csv` | The full deduplicated request universe — {len(unique_rows)} rows ({n_point} `POINT_DATE`, {n_range} `RANGE`, {n_both} tagged `BOTH`). **Retrieve by this file.** |
| `input/pair_mapping.csv` | Maps each `unique_request_id` back to every pair/occurrence it answers (`reference_type` distinguishes an endpoint occurrence from a low-return pair). |

Scale: **{len(unique_rows)} unique requests** ({n_point} point, {n_range}
range), covering **{len(tickers)} tickers**, development target years
**{', '.join(str(y) for y in target_years)}** only.

Of the 90 `<126`-return pairs: **{n_guaranteed}** are already mathematically
`GUARANTEED` to stay under 126 no matter how this evidence resolves (no
further evidence needed), and **{n_pending_lr}** are `PENDING` — only these
are represented in `low_return_range_requests.csv`.

## What to return

Fill these templates (headers are fixed — do not rename, reorder, or add
columns):

| file | one row per |
|---|---|
| `templates/endpoint_calendar_evidence.csv` | `unique_request_id` |
| `templates/endpoint_state_evidence.csv` | `unique_request_id` |
| `templates/endpoint_trade_evidence.csv` | `unique_request_id` |
| `templates/historical_identity_evidence.csv` | one row per identity **candidate** (see below) |
| `templates/raw_evidence_manifest.csv` | one row per **actual raw artifact you retrieved** |
| `templates/raw_artifact_request_mapping.csv` | one row per (artifact, request) it answers |

### `historical_identity_evidence.csv` — one row per CANDIDATE, not per ticker

A ticker may have **zero, one, or several** candidate historical identities.
For EVERY requested ticker, return **at least one row**:

- if you find no historical predecessor identity, return exactly **one** row
  with `evidence_status = NONE_FOUND` and the candidate columns empty;
- if you find one or more plausible predecessor identities (different InsCode
  or ISIN representing what may be the same economic security at an earlier
  date), return **one row per candidate** with `evidence_status =
  CANDIDATE_FOUND` and the evidence in `notes`;
- use `evidence_status = UNRESOLVED` if TSETMC's identity history could not be
  checked.

**Do not decide** whether any candidate should be merged with the current
identity. That decision is made separately, by us, after review. **Do not**
report any market-day/trading-day classification here — this file is about
instrument identity only.

### `raw_evidence_manifest.csv` + `raw_artifact_request_mapping.csv`

One `unique_request_id` may need SEVERAL raw artifacts (e.g. a calendar
response AND a state response). List every actual raw artifact you retrieved
in `raw_evidence_manifest.csv` — one row each, with `evidence_type` exactly
one of: {", ".join(f"`{t}`" for t in ALLOWED_EVIDENCE_TYPES)}. Then use
`raw_artifact_request_mapping.csv` to record every `unique_request_id` a given
artifact answers (a single `RANGE` calendar response, for example, typically
answers many requests at once — list it once in the manifest and map it to
every request it covers, rather than duplicating the raw bytes).

## Rules that matter most

**1. Never invent data.** Unresolvable fields are `UNRESOLVED`, never guessed.

**2. Never decide trading-day semantics.** Report the literal TSETMC
calendar/state/trade values. Whether a zero-trade date counts as a "trading
day" under our frozen scientific contract is decided inside papermali, not by
you.

**3. Never decide an identity join.** See above.

**4. Preserve raw responses and provenance**, per artifact, in
`raw_evidence_manifest.csv`.

**5. Deliver your code.** Please send all scripts you used.

## Firewall

This package contains **only** development-year pairs (target years
{', '.join(str(y) for y in target_years)}). It does **not** contain, reference,
or request evidence for target years 1400, 1401, or 1402, and no final-test
predictor or target value is included anywhere in this package.

## What you must NOT decide

You may report literal TSETMC values and status strings. You must **not**
decide:

- whether a zero-trade date counts as a trading day under our frozen
  contract;
- whether a historical identity should be joined;
- whether a pair becomes usable, or a feature value should be computed;
- whether M2 passes or fails.

Those decisions remain inside papermali after your evidence returns.
"""


def build_manifest(
    occurrences: list[dict[str, Any]],
    range_requests: list[dict[str, Any]],
    unique_rows: list[dict[str, Any]],
    upper_bound_rows: list[dict[str, Any]],
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    tickers = tickers_with_any_request(occurrences, range_requests)
    target_years = sorted({o["target_year"] for o in occurrences}
                          | {r["target_year"] for r in range_requests})
    return {
        "package_name": PACKAGE_NAME,
        "supersedes": v1.PACKAGE_NAME,
        "v1_must_not_be_sent_externally": True,
        "purpose": (
            "Request authoritative TSETMC evidence to adjudicate (a) whether "
            "qTotCap=0/zTotTran=0 ClosingPriceDailyList endpoint dates are "
            "genuine trading days, and (b) whether excluding such dates from "
            "the trading-day sequence would raise a pending pair's valid "
            "daily-return count to >=126. Diagnostic/retrieval-request only; "
            "does not alter the canonical Stage127 Gate."
        ),
        "canonical_gate_status_unchanged": "FAIL_M2_DATA_GATE",
        "request_scope": "development_only",
        "development_target_years": target_years,
        "final_test_target_years_excluded": list(gate.FINAL_TEST_TARGET_YEARS),
        "final_test_pairs_included": 0,
        "final_test_row_level_data_included": False,
        "endpoint_occurrence_count": len(occurrences),
        "endpoint_occurrence_count_t0": sum(
            1 for o in occurrences if o["endpoint_type"] == "t0"),
        "endpoint_occurrence_count_tN": sum(
            1 for o in occurrences if o["endpoint_type"] == "tN"),
        "low_return_range_request_count": len(range_requests),
        "low_return_pairs_guaranteed_no_evidence_needed": sum(
            1 for u in upper_bound_rows
            if u["classification"] == rca.CAT_GUARANTEED_LT126),
        "low_return_pairs_pending_evidence": sum(
            1 for u in upper_bound_rows
            if u["classification"] == rca.CAT_PENDING_LOW_RETURN_SEMANTICS),
        "unique_request_count": len(unique_rows),
        "unique_request_count_point": sum(
            1 for u in unique_rows if u["request_type"] == REQUEST_TYPE_POINT),
        "unique_request_count_range": sum(
            1 for u in unique_rows if u["request_type"] == REQUEST_TYPE_RANGE),
        "unique_request_count_reason_both": sum(
            1 for u in unique_rows if u["evidence_reason"] == REASON_BOTH),
        "affected_ticker_count": len(tickers),
        "affected_tickers": tickers,
        "source_id": gate.M2_PRIMARY_SOURCE_ID,
        "authoritative_source_only": True,
        "substitute_sources_authorized": False,
        "external_feature_engineering_authorized": False,
        "external_modeling_authorized": False,
        "external_classification_decision_authorized": False,
        "external_trading_day_semantics_decision_authorized": False,
        "identity_join_authorized": False,
        "final_test_access_authorized": False,
        "imputation_authorized": False,
        "raw_evidence_schema_supports_multiple_artifacts_per_request": True,
        "identity_schema_supports_multiple_candidates_per_ticker": True,
        "package_files_sha256": file_hashes,
    }
