"""Stage127 — external TSETMC retrieval-request package (development-only).

Generates a deterministic, self-contained request package that an external
programmer can execute WITHOUT understanding the papermali project and WITHOUT
making any scientific decision. The external party retrieves raw authoritative
TSETMC data only; every M2 feature is computed later inside this repository.

Everything is derived from canonical repository artifacts. No ticker or date
range is hand-typed. Final-test pairs (target years 1400-1402) are excluded
structurally and can never enter the package.

This module retrieves nothing and fits nothing.
"""
from __future__ import annotations

import io
import csv
import os
from datetime import date
from typing import Any

from src import stage127_m2_market_data_gate as gate

EXTERNAL_DIR_REL = "project/stage127/external_retrieval"

REQUEST_CSV = "stage127_m2_external_retrieval_request.csv"
TICKER_RANGES_CSV = "stage127_m2_external_retrieval_ticker_ranges.csv"
DAILY_TEMPLATE_CSV = "stage127_m2_external_return_daily_template.csv"
MAPPING_TEMPLATE_CSV = "stage127_m2_external_return_mapping_template.csv"
MANIFEST_TEMPLATE_CSV = "stage127_m2_external_return_manifest_template.csv"
REQUEST_MANIFEST_JSON = "stage127_m2_external_retrieval_request_manifest.json"
EXTERNAL_README = "README_STAGE127_M2_EXTERNAL_TSETMC_RETRIEVAL.md"

PACKAGE_FILES: tuple[str, ...] = (
    REQUEST_CSV,
    TICKER_RANGES_CSV,
    DAILY_TEMPLATE_CSV,
    MAPPING_TEMPLATE_CSV,
    MANIFEST_TEMPLATE_CSV,
    REQUEST_MANIFEST_JSON,
    EXTERNAL_README,
)

ZIP_NAME = "stage127_m2_external_tsetmc_retrieval_package.zip"

REQUEST_COLUMNS: tuple[str, ...] = (
    "request_id",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "predictor_row_key_t",
    "pair_cutoff_date",
    "requested_start_date",
    "requested_end_date",
    "source_id",
    "required_price_field",
    "required_value_field",
    "window_rule",
)

TICKER_RANGE_COLUMNS: tuple[str, ...] = (
    "range_id",
    "ticker",
    "requested_start_date",
    "requested_end_date",
    "covered_pair_count",
    "source_id",
)

DAILY_TEMPLATE_COLUMNS: tuple[str, ...] = (
    "requested_ticker", "ticker", "company_name", "tsetmc_instrument_id",
    "isin", "trading_date", "adjusted_close", "adjusted_close_status",
    "raw_close", "last_price", "open", "high", "low", "traded_value_rial",
    "raw_traded_value", "raw_traded_value_unit", "volume", "trade_count",
    "source_endpoint", "retrieved_at_utc", "raw_response_file",
    "raw_response_sha256",
)

MAPPING_TEMPLATE_COLUMNS: tuple[str, ...] = (
    "requested_ticker", "matched_ticker", "company_name",
    "tsetmc_instrument_id", "isin", "mapping_status", "mapping_evidence",
    "mapping_note",
)

#: RANGE-level, not ticker-level. A ticker with two disjoint authorized ranges
#: (e.g. `شکلر`) must produce two manifest rows, each with its own retrieval
#: status, so a partial failure in one range cannot be masked by success in the
#: other. ``range_id`` is therefore the leading key.
MANIFEST_TEMPLATE_COLUMNS: tuple[str, ...] = (
    "range_id", "requested_ticker", "tsetmc_instrument_id",
    "requested_start_date", "requested_end_date", "first_returned_date",
    "last_returned_date", "rows_retrieved", "retrieval_status",
    "source_endpoint", "retrieved_at_utc", "raw_response_file",
    "raw_response_sha256", "notes",
)

ALLOWED_MAPPING_STATUS: tuple[str, ...] = ("MATCHED", "UNRESOLVED")
ALLOWED_RETRIEVAL_STATUS: tuple[str, ...] = (
    "SUCCESS", "PARTIAL", "FAILED", "UNRESOLVED_MAPPING",
)

WINDOW_RULE = (
    "shared_12_calendar_month_window_ending_on_last_eligible_trading_day_"
    "strictly_before_pair_cutoff_date"
)

#: Retrieval superset only. The scientific window remains exactly the frozen
#: 12 calendar months; these extra days exist solely so the true window --
#: whose endpoint is a TRADING day that cannot be known without the market
#: calendar -- is always fully contained in what the external party returns.
RETRIEVAL_BUFFER_DAYS = 30


def _csv_text(columns: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_pair_requests(repo_root: str) -> list[dict[str, Any]]:
    """One request row per frozen DEVELOPMENT pair, deterministically ordered.

    ``gate.load_development_pairs`` filters final-test rows by ``dataset_split``
    before reading any value, so no final-test pair can reach this package.
    """
    pairs = gate.load_development_pairs(repo_root)

    ordered = sorted(
        pairs, key=lambda p: (p["ticker"], int(p["fiscal_year_t"]), p["target_year"])
    )
    rows: list[dict[str, Any]] = []
    for i, p in enumerate(ordered, start=1):
        if p["target_year"] in gate.FINAL_TEST_TARGET_YEARS:
            raise gate.GateFail(
                f"final-test target_year {p['target_year']} reached the request"
            )
        if not p["pair_cutoff_date"]:
            raise gate.GateFail(f"missing pair cutoff for {p['ticker']}")
        start, end = gate.required_window(p["pair_cutoff_date"])
        if date.fromisoformat(end) >= date.fromisoformat(p["pair_cutoff_date"]):
            raise gate.GateFail("requested_end_date must be < pair_cutoff_date")
        rows.append({
            "request_id": f"REQ{i:04d}",
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "predictor_row_key_t": p["predictor_row_key_t"],
            "pair_cutoff_date": p["pair_cutoff_date"],
            "requested_start_date": start,
            "requested_end_date": end,
            "source_id": gate.M2_PRIMARY_SOURCE_ID,
            "required_price_field": gate.PRICE_FIELD,
            "required_value_field": gate.VOLUME_FIELD,
            "window_rule": WINDOW_RULE,
        })
    return rows


def merge_ticker_ranges(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge overlapping/adjacent per-pair ranges per ticker, deterministically.

    Only genuinely overlapping or contiguous intervals are merged. Disjoint
    intervals separated by a real gap stay separate, so the plan never requests
    a span the pair-level requests do not already permit and never silently
    turns bounded requests into one long history.
    """
    by_ticker: dict[str, list[tuple[date, date]]] = {}
    for r in requests:
        by_ticker.setdefault(r["ticker"], []).append((
            date.fromisoformat(r["requested_start_date"]),
            date.fromisoformat(r["requested_end_date"]),
        ))

    out: list[dict[str, Any]] = []
    counter = 0
    for ticker in sorted(by_ticker):
        intervals = sorted(by_ticker[ticker])
        merged: list[list[date]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                # Overlapping or touching -> extend, never shrink.
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        for start, end in merged:
            counter += 1
            covered = sum(
                1 for s, e in intervals if s >= start and e <= end
            )
            out.append({
                "range_id": f"RNG{counter:04d}",
                "ticker": ticker,
                "requested_start_date": start.isoformat(),
                "requested_end_date": end.isoformat(),
                "covered_pair_count": covered,
                "source_id": gate.M2_PRIMARY_SOURCE_ID,
            })
    return out


def build_request_manifest(
    repo_root: str,
    requests: list[dict[str, Any]],
    ranges: list[dict[str, Any]],
    file_hashes: dict[str, str],
) -> dict[str, Any]:
    starts = [r["requested_start_date"] for r in requests]
    ends = [r["requested_end_date"] for r in requests]
    return {
        "request_scope": "development_only",
        "source_id": gate.M2_PRIMARY_SOURCE_ID,
        "source_family": gate.M2_SOURCE_FAMILY,
        "authoritative_source_only": True,
        "sample": gate.PRIMARY_SAMPLE,
        "target": gate.PRIMARY_TARGET,
        "development_target_years": list(gate.DEVELOPMENT_TARGET_YEARS),
        "final_test_target_years_excluded": list(gate.FINAL_TEST_TARGET_YEARS),
        "final_test_pairs_included": 0,
        "final_test_row_level_data_included": False,
        "pair_count": len(requests),
        "ticker_count": len({r["ticker"] for r in requests}),
        "ticker_range_count": len(ranges),
        "date_min": min(starts),
        "date_max": max(ends),
        "required_price_field": gate.PRICE_FIELD,
        "required_value_field": gate.VOLUME_FIELD,
        "window_rule": WINDOW_RULE,
        "shared_window_calendar_months": gate.SHARED_WINDOW_CALENDAR_MONTHS,
        "retrieval_buffer_days": RETRIEVAL_BUFFER_DAYS,
        "retrieval_buffer_is_superset_only": True,
        "retrieval_buffer_does_not_alter_scientific_window": True,
        "downstream_m2_variables": [v for v, _, _ in gate.M2_VARIABLES],
        "downstream_m2_variables_computed_by": "papermali_after_ingestion",
        "external_programmer_role": "raw_authoritative_data_retrieval_only",
        "external_feature_engineering_authorized": False,
        "external_modeling_authorized": False,
        "final_test_access_authorized": False,
        "imputation_authorized": False,
        "ticker_mapping_guessing_authorized": False,
        "substitute_sources_authorized": False,
        "gate_status_unchanged": "UNRESOLVED_M2_DATA_GATE",
        "m2_data_collected": False,
        "package_files_sha256": file_hashes,
        "canonical_sources_sha256": {
            rel: gate.sha256_file(os.path.join(repo_root, rel))
            for rel in gate.CANONICAL_SOURCES
        },
    }


def tickers_with_multiple_ranges(ranges: list[dict[str, Any]]) -> list[str]:
    """Tickers whose authorized retrieval is split across disjoint ranges.

    Derived from the generated plan, never hardcoded, so the README example
    stays correct if the frozen development set ever changes.
    """
    counts: dict[str, int] = {}
    for r in ranges:
        counts[r["ticker"]] = counts.get(r["ticker"], 0) + 1
    return sorted(t for t, n in counts.items() if n > 1)


def build_external_readme(
    manifest: dict[str, Any], ranges: list[dict[str, Any]],
) -> str:
    multi = tickers_with_multiple_ranges(ranges)
    gap_count = len(multi)
    listed = ", ".join(f"`{t}`" for t in multi)
    if gap_count == 1:
        gap_sentence = (
            f"One ticker ({listed}) has **two** authorized ranges rather than "
            "one, so the manifest has one more row than there are tickers."
        )
        gap_note = (
            f"**{listed}** has **two separate authorized ranges** and must "
            "therefore appear as **two distinct manifest rows**."
        )
    elif gap_count > 1:
        gap_sentence = (
            f"{gap_count} tickers ({listed}) have more than one authorized "
            "range, so the manifest has more rows than there are tickers."
        )
        gap_note = (
            "These tickers have **more than one authorized range** and must "
            f"appear as one manifest row per range: {listed}."
        )
    else:
        gap_sentence = "Each ticker has exactly one authorized range."
        gap_note = (
            "Every ticker here has exactly one authorized range, so each "
            "appears once."
        )
    return f"""# TSETMC historical daily data — retrieval request

You do **not** need to know anything about the project this request comes from.
This document is self-contained. Please read it fully before starting.

## What we need

Official **raw historical daily trading data from TSETMC** for a list of Iranian
listed companies, each over a specific date range. Nothing more.

**You will not compute any indicator, ratio, or statistic.** Just return the raw
daily rows plus provenance.

## Source — TSETMC only

Use **only** official TSETMC (`tsetmc.com`) data.

**Do not use** Yahoo Finance, Kaggle, unofficial mirrors, scraped aggregator
sites, Telegram channels, broker exports, or any third-party dataset. If TSETMC
cannot provide something, report that — do not substitute another source.

## Input files

| file | meaning |
|---|---|
| `{REQUEST_CSV}` | **The authoritative request.** One row per company-year, with the exact date range needed. |
| `{TICKER_RANGES_CSV}` | **Operational convenience only.** The same ranges merged per ticker so you can make fewer calls. |

Retrieving by `{TICKER_RANGES_CSV}` is enough — it already covers every row of
the authoritative request. Please **do not** widen the ranges, and please do not
download a company's entire history when a bounded range is given.

Scale: **{manifest['pair_count']} requests**, **{manifest['ticker_count']} tickers**,
**{manifest['ticker_range_count']} merged ranges**, dates from
**{manifest['date_min']}** to **{manifest['date_max']}**.

## What to return

Fill these three files (headers are fixed — do not rename, reorder or add
columns). Note the different granularity of each:

| file | one row per |
|---|---|
| `{DAILY_TEMPLATE_CSV}` | ticker × trading day |
| `{MAPPING_TEMPLATE_CSV}` | **requested ticker** ({manifest['ticker_count']} rows) |
| `{MANIFEST_TEMPLATE_CSV}` | **retrieval range / `range_id`** ({manifest['ticker_range_count']} rows) |

{gap_sentence}

### 1. `{DAILY_TEMPLATE_CSV}` — one row per ticker per trading day

Key fields:

- `trading_date` — the trading day (ISO `YYYY-MM-DD`; if you also have the
  Jalali date, put it in notes, not here)
- `adjusted_close` — **corporate-action-adjusted** closing price (see below)
- `adjusted_close_status` — `OK` if genuinely adjusted, or
  `ADJUSTED_CLOSE_UNRESOLVED` if you cannot verify adjustment
- `raw_close`, `last_price`, `open`, `high`, `low` — raw price fields as TSETMC
  gives them
- `traded_value_rial` — total traded **value** for the day **in rial**
- `raw_traded_value` + `raw_traded_value_unit` — the value exactly as returned
  and its unit (e.g. `rial`, `toman`) so we can verify the conversion ourselves
- `volume`, `trade_count` — share volume and number of trades
- `source_endpoint`, `retrieved_at_utc`, `raw_response_file`,
  `raw_response_sha256` — provenance

### 2. `{MAPPING_TEMPLATE_CSV}` — one row per requested ticker

This file **is** per ticker ({manifest['ticker_count']} rows), unlike the
manifest below. A ticker with two retrieval ranges still gets only **one**
mapping row, because it is still one company mapped to one instrument.

How each requested ticker maps to a TSETMC instrument (`tsetmc_instrument_id` /
InsCode, ISIN, official company name), with the evidence you used.

`mapping_status` must be exactly one of: {" or ".join(f"`{s}`" for s in ALLOWED_MAPPING_STATUS)}.

### 3. `{MANIFEST_TEMPLATE_CSV}` — one row per **retrieval range**

**This file is per `range_id`, not per ticker.** Read this carefully — it is the
easiest part of the request to get wrong.

- Take every `range_id` from `{TICKER_RANGES_CSV}` and give it **exactly one**
  row here. There are **{manifest['ticker_range_count']} range_ids** across
  **{manifest['ticker_count']} tickers**, so the finished manifest has
  **{manifest['ticker_range_count']} rows**.
- `range_id` is the first column. Copy it verbatim, along with that range's
  `requested_start_date` and `requested_end_date`.
- **Do not merge two ranges of the same ticker into one row**, even though they
  share a ticker and instrument id.
- {gap_note} Its ranges are separated by a deliberate gap: we do not want the
  data in between, so please do not fill the gap in and please do not stretch
  one range to cover both.
- `retrieval_status` is judged **separately for each range**. One range may be
  `SUCCESS` while another range of the same ticker is `PARTIAL` or `FAILED`.
  That is expected and useful — please do not average or combine them.

Record what you actually retrieved: requested vs returned date span, row count,
and status.

`retrieval_status` must be exactly one of: {", ".join(f"`{s}`" for s in ALLOWED_RETRIEVAL_STATUS)}.

Use `UNRESOLVED_MAPPING` when the ticker could not be mapped to a TSETMC
instrument at all (its mapping row should then also be `UNRESOLVED`).

## Rules that matter most

**1. Never invent data.** Do not impute, interpolate, forward-fill,
backward-fill, or substitute `0` for anything missing. A missing day should
simply be absent, or present with an empty value. An empty cell is a useful,
correct answer; a fabricated one silently corrupts the study.

**2. Never guess a ticker mapping.** Iranian tickers change names and symbols,
and several companies have similar ones. If you are not certain which instrument
a ticker refers to, set `mapping_status = UNRESOLVED` and explain in
`mapping_note`. An honest `UNRESOLVED` is far more valuable than a wrong guess.

**3. Adjusted close must be real.** `adjusted_close` must be adjusted for
corporate actions (capital increases, splits, dividends as TSETMC handles them),
either taken directly from official TSETMC adjusted data or derived from
official TSETMC data by a transformation you describe and we can reproduce.
If you cannot do this verifiably, put the unadjusted price in `raw_close`, leave
`adjusted_close` empty, and set `adjusted_close_status =
ADJUSTED_CLOSE_UNRESOLVED`. **Do not** silently put the unadjusted close in the
`adjusted_close` column — that is the single most damaging thing that could
happen to this dataset.

**4. Traded value must be in rial.** If TSETMC returns toman or another unit,
record the original in `raw_traded_value` with its `raw_traded_value_unit` and
put the rial figure in `traded_value_rial`. Never fabricate volume or value.

**5. Preserve raw responses.** Save the raw API/page responses where practical,
give each a filename in `raw_response_file`, and record its `SHA256` in
`raw_response_sha256`.

**6. Deliver your code.** Please send all extraction scripts you used, so the
retrieval can be reproduced independently.

## Please do NOT compute

Do not compute or return any of the following — they are computed on our side
after ingestion, and receiving them from outside would invalidate the study:

- `equity_return_window`
- `realized_volatility`
- `amihud_illiquidity`

Also please do not extend the requested date ranges "to be helpful."

## Start with a small pilot

**Before running the full extraction**, send a pilot for **2-3 tickers only**:

1. 10-20 normalized daily rows in the `{DAILY_TEMPLATE_CSV}` format
2. the matching mapping rows
3. the matching retrieval manifest rows (one per `range_id` covered)
4. one raw response file
5. a short note on which endpoint(s) and fields you used
6. a short explanation of how you produced `adjusted_close`
7. a short explanation of how you produced `traded_value_rial` (including units)

We will review the schema and confirm before you run the full extraction. This
protects your time: a field-mapping misunderstanding found at pilot stage costs
minutes, but found after the full run costs the entire retrieval.

## Questions

If anything is ambiguous, please ask rather than assume. Returning fewer rows
with honest `UNRESOLVED` statuses is always better than returning complete-looking
data that is wrong.
"""


def build_all(repo_root: str) -> dict[str, str]:
    """Return {filename: text} for the complete external package."""
    requests = build_pair_requests(repo_root)
    ranges = merge_ticker_ranges(requests)

    files: dict[str, str] = {
        REQUEST_CSV: _csv_text(REQUEST_COLUMNS, requests),
        TICKER_RANGES_CSV: _csv_text(TICKER_RANGE_COLUMNS, ranges),
        DAILY_TEMPLATE_CSV: _csv_text(DAILY_TEMPLATE_COLUMNS, []),
        MAPPING_TEMPLATE_CSV: _csv_text(MAPPING_TEMPLATE_COLUMNS, []),
        MANIFEST_TEMPLATE_CSV: _csv_text(MANIFEST_TEMPLATE_COLUMNS, []),
    }

    hashes = {name: gate.sha256_text(text) for name, text in sorted(files.items())}
    manifest = build_request_manifest(repo_root, requests, ranges, hashes)
    readme = build_external_readme(manifest, ranges)
    manifest["package_files_sha256"][EXTERNAL_README] = gate.sha256_text(readme)

    files[EXTERNAL_README] = readme
    files[REQUEST_MANIFEST_JSON] = gate.json_dumps(manifest)
    return files
