"""Stage127 — external evidence-request package for zero-trade endpoint dates.

Builds a deterministic, self-contained request package asking the
already-used Iranian TSETMC retriever for AUTHORITATIVE evidence on what a
``qTotCap=0, zTotTran=0`` ClosingPriceDailyList row actually represents for a
given InsCode/date: a genuine trading day with zero executions, a suspension,
a non-tradable instrument state, or a calendar artifact.

This module does not decide that question and does not touch the canonical
Gate. It generates the REQUEST only, from the existing diagnostic artifacts
(the equity_return_window root-cause audit), for the 391 pairs whose
classification is `ZERO_TRADE_ENDPOINT_REQUIRES_TRADING_DAY_SEMANTICS_
ADJUDICATION` plus their raw endpoint occurrences, historical-identity
evidence for the affected tickers, and reference context for the 90
<126-return pairs.

Development-only, TSETMC-only, firewalled exactly like the prior external
TSETMC retrieval-request package: target years 1400-1402 can never enter this
package because it is built entirely from the frozen 666 development pairs.
"""
from __future__ import annotations

import csv
import io
import os
from typing import Any

from . import stage127_m2_equity_return_root_cause_audit as rca
from . import stage127_m2_external_delivery_import as imp
from . import stage127_m2_market_data_gate as gate

PACKAGE_NAME = "stage127_m2_zero_trade_endpoint_evidence_request"
ZIP_NAME = f"{PACKAGE_NAME}.zip"

PENDING_ADJUDICATION_LABEL = rca.CAT_ZERO_TRADE_ENDPOINT

ENDPOINT_OCCURRENCE_COLUMNS: tuple[str, ...] = (
    "request_id",
    "predictor_row_key_t",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "endpoint_type",
    "endpoint_date",
    "pair_cutoff_date",
    "current_InsCode",
    "current_ISIN",
    "source_range_id",
    "qTotCap",
    "qTotTran5J",
    "zTotTran",
    "raw_close",
    "adjusted_close_status",
)

UNIQUE_REQUEST_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "InsCode",
    "ISIN",
    "ticker",
    "endpoint_date",
    "occurrence_count",
    "qTotCap",
    "qTotTran5J",
    "zTotTran",
    "raw_close",
)

PAIR_MAPPING_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "request_id",
)

LOW_RETURN_CONTEXT_COLUMNS: tuple[str, ...] = (
    "ticker",
    "fiscal_year_t",
    "target_year",
    "current_InsCode",
    "current_ISIN",
    "window_observation_count",
    "missing_adjusted_price_days",
    "zero_trade_days",
    "valid_return_count",
    "authorized_range_start",
    "authorized_range_end",
    "range_is_partial_source",
)

TEMPLATE_CALENDAR_COLUMNS: tuple[str, ...] = (
    "unique_request_id", "InsCode", "endpoint_date",
    "in_instrument_trading_calendar", "calendar_evidence_endpoint",
    "calendar_evidence_note",
)
TEMPLATE_STATE_COLUMNS: tuple[str, ...] = (
    "unique_request_id", "InsCode", "endpoint_date",
    "instrument_state", "state_evidence_endpoint", "state_evidence_note",
)
TEMPLATE_TRADE_COLUMNS: tuple[str, ...] = (
    "unique_request_id", "InsCode", "endpoint_date",
    "trade_occurred", "trade_count", "traded_volume", "traded_value",
    "trade_evidence_endpoint", "trade_evidence_note",
)
TEMPLATE_IDENTITY_COLUMNS: tuple[str, ...] = (
    "ticker", "current_InsCode", "current_ISIN",
    "historical_InsCode_found", "historical_ISIN_found",
    "identity_change_date", "predecessor_identity_evidence_endpoint",
    "predecessor_identity_note",
    "classification",
)
TEMPLATE_MANIFEST_COLUMNS: tuple[str, ...] = (
    "unique_request_id", "InsCode", "endpoint_date",
    "retrieval_status", "retrieved_at_utc",
    "raw_response_file", "raw_response_sha256", "notes",
)

ALLOWED_CLASSIFICATIONS: tuple[str, ...] = (
    "A_MARKET_OPEN_INSTRUMENT_ELIGIBLE_ZERO_TRADES",
    "B_INSTRUMENT_SUSPENDED_OR_PROHIBITED",
    "C_CALENDAR_ARTIFACT_NOT_A_TRADING_DAY",
    "D_LEGITIMATE_TRADING_DAY_ZERO_EXECUTIONS",
    "E_OTHER_TSETMC_STATE",
    "POTENTIAL_TSETMC_HISTORY_FRAGMENTATION",
    "UNRESOLVED",
)


def _csv_text(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_endpoint_occurrences(
    repo_root: str, bundle_path: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (occurrence_rows, {predictor_row_key: pair}) for pending pairs.

    Every occurrence corresponds to exactly one row in the existing
    ``tN``/``t0`` detail audits whose root cause is the pending-adjudication
    label. Final-test pairs cannot appear: ``audit.pairs`` comes from
    ``gate.load_development_pairs``, which filters by ``dataset_split`` before
    any value is read.
    """
    audit = rca.RootCauseAudit(repo_root, bundle_path)
    main_rows = rca.build_audit_rows(audit)
    pairs_by_key = {
        (p["ticker"], p["fiscal_year_t"]): p for p in audit.pairs
    }

    occurrences: list[dict[str, Any]] = []
    counter = 0
    for r in main_rows:
        ticker = r["ticker"]
        fiscal_year_t = r["fiscal_year_t"]
        pair = pairs_by_key[(ticker, fiscal_year_t)]
        mapping_row = audit.mapping[ticker]

        for endpoint_type, date_key, status_key, ev_prefix in (
            ("tN", "t_star", "t_star_adjusted_close_status", "t_star"),
            ("t0", "t0_trading_date", "t0_adjusted_close_status", "t0"),
        ):
            endpoint_date = r[date_key]
            if not endpoint_date:
                continue
            if r[f"{ev_prefix}_adjusted_close_present"]:
                continue  # only missing endpoints are requested
            counter += 1
            occurrences.append({
                "request_id": f"REQ{counter:04d}",
                "predictor_row_key_t": pair["predictor_row_key_t"],
                "ticker": ticker,
                "fiscal_year_t": fiscal_year_t,
                "target_year": r["target_year"],
                "endpoint_type": endpoint_type,
                "endpoint_date": endpoint_date,
                "pair_cutoff_date": r["pair_cutoff_date"],
                "current_InsCode": mapping_row["tsetmc_instrument_id"],
                "current_ISIN": mapping_row["isin"],
                "source_range_id": r[f"{ev_prefix}_source_range_id"],
                "qTotCap": r[f"{ev_prefix}_qTotCap"],
                "qTotTran5J": r[f"{ev_prefix}_qTotTran5J"],
                "zTotTran": r[f"{ev_prefix}_zTotTran"],
                "raw_close": r[f"{ev_prefix}_raw_close"],
                "adjusted_close_status": r[status_key],
            })
    return occurrences, audit


def build_unique_requests(
    occurrences: list[dict[str, Any]], audit: rca.RootCauseAudit,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate by (InsCode, endpoint_date); keep the request_id mapping."""
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for o in occurrences:
        key = (o["current_InsCode"], o["endpoint_date"])
        by_key.setdefault(key, []).append(o)

    unique_rows: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    for i, (key, occs) in enumerate(sorted(by_key.items()), start=1):
        ins_code, endpoint_date = key
        first = occs[0]
        uid = f"UNQ{i:04d}"
        unique_rows.append({
            "unique_request_id": uid,
            "InsCode": ins_code,
            "ISIN": first["current_ISIN"],
            "ticker": first["ticker"],
            "endpoint_date": endpoint_date,
            "occurrence_count": len(occs),
            "qTotCap": first["qTotCap"],
            "qTotTran5J": first["qTotTran5J"],
            "zTotTran": first["zTotTran"],
            "raw_close": first["raw_close"],
        })
        for o in occs:
            mapping_rows.append({
                "unique_request_id": uid,
                "request_id": o["request_id"],
            })
    return unique_rows, mapping_rows


def build_low_return_context(
    repo_root: str, audit: rca.RootCauseAudit,
) -> list[dict[str, Any]]:
    main_rows = rca.build_audit_rows(audit)
    rows: list[dict[str, Any]] = []
    for r in main_rows:
        if r["usable_daily_return_count"] == "":
            continue
        if int(r["usable_daily_return_count"]) >= gate.MIN_VALID_RETURN_OBSERVATIONS:
            continue
        mapping_row = audit.mapping[r["ticker"]]
        rows.append({
            "ticker": r["ticker"],
            "fiscal_year_t": r["fiscal_year_t"],
            "target_year": r["target_year"],
            "current_InsCode": mapping_row["tsetmc_instrument_id"],
            "current_ISIN": mapping_row["isin"],
            "window_observation_count": r["window_trading_day_count"],
            "missing_adjusted_price_days": r["missing_price_day_count"],
            "zero_trade_days": r["zero_traded_value_day_count"],
            "valid_return_count": r["usable_daily_return_count"],
            "authorized_range_start": r["authorized_range_start"],
            "authorized_range_end": r["authorized_range_end"],
            "range_is_partial_source": r["range_is_partial_source"],
        })
    return rows


def tickers_with_pending_endpoints(occurrences: list[dict[str, Any]]) -> list[str]:
    return sorted({o["ticker"] for o in occurrences})


def build_readme(
    occurrences: list[dict[str, Any]],
    unique_rows: list[dict[str, Any]],
    low_return_rows: list[dict[str, Any]],
) -> str:
    tickers = tickers_with_pending_endpoints(occurrences)
    n_t0 = sum(1 for o in occurrences if o["endpoint_type"] == "t0")
    n_tN = sum(1 for o in occurrences if o["endpoint_type"] == "tN")
    target_years = sorted({o["target_year"] for o in occurrences})
    return f"""# TSETMC zero-trade endpoint semantics — evidence request

You do **not** need to know anything about the project this request comes
from. Please read this document fully before starting.

## What we need

For a specific list of **(instrument, calendar date)** pairs where our records
show `qTotCap = 0` and `zTotTran = 0` on TSETMC's own `ClosingPriceDailyList`
response, we need **authoritative TSETMC evidence** establishing what that date
actually represents for the instrument:

1. Was the date part of the instrument's trading calendar?
2. What was the instrument's state on that date (normal / suspended /
   prohibited / other)?
3. Did any trade actually occur (trade count, volume, value)?
4. Does the official adjusted-price history include or omit the date, and why?

**You will not compute or infer anything.** Report exactly what the
authoritative TSETMC endpoints return, with provenance, and mark anything you
cannot determine as `UNRESOLVED` rather than guessing.

## Source — TSETMC only

Use **only** official TSETMC (`tsetmc.com`) endpoints. Candidate surfaces
(use whichever official endpoints actually answer each question — do not
guess a URL that does not exist):

- `ClosingPrice/GetInstrumentCalendar/{{InsCode}}` (trading calendar)
- `MarketData/GetInstrumentState/{{InsCode}}/{{DEven}}` (instrument state)
- `Trade/GetTradeHistory/{{InsCode}}/{{DEven}}/...` (executed trades)
- `ClosingPrice/GetClosingPriceDaily/{{InsCode}}/{{DEven}}` (daily closing
  record)
- `Instrument/GetInstrumentHistory/{{InsCode}}/{{DEven}}` (instrument history)
- `Instrument/GetInstrumentIdentity/{{InsCode}}` (identity/ISIN history)

**Do not use** Yahoo Finance, Kaggle, unofficial mirrors, or any third-party
dataset. If TSETMC cannot answer a question, report `UNRESOLVED` — do not
substitute another source.

## Input files

| file | meaning |
|---|---|
| `input/endpoint_occurrence_requests.csv` | One row per **occurrence** — {len(occurrences)} rows ({n_t0} missing-`t0`, {n_tN} missing-`T*`). |
| `input/unique_endpoint_requests.csv` | The same evidence, deduplicated by (InsCode, date) — {len(unique_rows)} rows. **Retrieve by this file** so you never fetch the same date twice. |
| `input/pair_mapping.csv` | Maps each `unique_request_id` back to every `request_id` (pair) it answers. Do not lose this mapping. |
| `input/low_return_reference_context.csv` | {len(low_return_rows)} additional development pairs with fewer than 126 valid daily returns, included for context only (diagnostic, not a request for new endpoints beyond what is already listed above). |

Scale: **{len(unique_rows)} unique instrument/date requests**, covering
**{len(tickers)} tickers**, development target years **{', '.join(str(y) for y in target_years)}** only.

## What to return

Fill these templates (headers are fixed — do not rename, reorder, or add
columns):

| file | one row per |
|---|---|
| `templates/endpoint_calendar_evidence.csv` | `unique_request_id` |
| `templates/endpoint_state_evidence.csv` | `unique_request_id` |
| `templates/endpoint_trade_evidence.csv` | `unique_request_id` |
| `templates/historical_identity_evidence.csv` | ticker (one row per requested ticker) |
| `templates/retrieval_manifest.csv` | `unique_request_id` (provenance) |

### `historical_identity_evidence.csv` — read this carefully

For each requested ticker, check whether TSETMC shows a **historical**
instrument identity (a different InsCode or ISIN) that represents the **same
economic listed security** at an earlier date than our current mapping's
history begins. Do **not** merge or concatenate any history yourself. Just
report what you find:

- `historical_InsCode_found` / `historical_ISIN_found` — leave empty if none
  found;
- `classification` must be exactly one of:
  {", ".join(f"`{c}`" for c in ALLOWED_CLASSIFICATIONS)};
- if you find a plausible predecessor identity, set `classification =
  POTENTIAL_TSETMC_HISTORY_FRAGMENTATION` and describe the evidence in
  `predecessor_identity_note` — **do not** decide or imply that the histories
  should be joined. That decision is made separately, by us, after review.

## Rules that matter most

**1. Never invent data.** If TSETMC's calendar, state, or trade-history
endpoints do not resolve a date, set the field to `UNRESOLVED`. An honest
`UNRESOLVED` is far more valuable than a guess.

**2. Never guess an instrument's history.** See the identity-evidence rule
above.

**3. Preserve raw responses.** Save the raw API/page responses where
practical, and record file + SHA256 in `retrieval_manifest.csv`.

**4. Deliver your code.** Please send all scripts you used, so the retrieval
can be reproduced independently.

## Firewall

This package contains **only** development-year pairs (target years
{', '.join(str(y) for y in target_years)}). It does **not** contain, reference,
or request evidence for target years 1400, 1401, or 1402, and no final-test
predictor or target value is included anywhere in this package.

## Please do NOT compute

Do not classify, aggregate, or draw conclusions across dates. Just report the
authoritative TSETMC evidence, per date, with provenance.
"""


def build_manifest(
    occurrences: list[dict[str, Any]],
    unique_rows: list[dict[str, Any]],
    low_return_rows: list[dict[str, Any]],
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    tickers = tickers_with_pending_endpoints(occurrences)
    target_years = sorted({o["target_year"] for o in occurrences})
    return {
        "package_name": PACKAGE_NAME,
        "purpose": (
            "Request authoritative TSETMC evidence to adjudicate whether "
            "qTotCap=0/zTotTran=0 ClosingPriceDailyList endpoint dates are "
            "genuine trading days, suspensions, non-tradable states, or "
            "calendar artifacts. Diagnostic only; does not alter the "
            "canonical Stage127 Gate."
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
        "unique_endpoint_request_count": len(unique_rows),
        "affected_ticker_count": len(tickers),
        "affected_tickers": tickers,
        "low_return_reference_pair_count": len(low_return_rows),
        "source_id": gate.M2_PRIMARY_SOURCE_ID,
        "authoritative_source_only": True,
        "substitute_sources_authorized": False,
        "external_feature_engineering_authorized": False,
        "external_modeling_authorized": False,
        "external_classification_decision_authorized": False,
        "identity_join_authorized": False,
        "final_test_access_authorized": False,
        "imputation_authorized": False,
        "package_files_sha256": file_hashes,
    }
