# TSETMC historical daily data — retrieval request

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
| `stage127_m2_external_retrieval_request.csv` | **The authoritative request.** One row per company-year, with the exact date range needed. |
| `stage127_m2_external_retrieval_ticker_ranges.csv` | **Operational convenience only.** The same ranges merged per ticker so you can make fewer calls. |

Retrieving by `stage127_m2_external_retrieval_ticker_ranges.csv` is enough — it already covers every row of
the authoritative request. Please **do not** widen the ranges, and please do not
download a company's entire history when a bounded range is given.

Scale: **666 requests**, **110 tickers**,
**111 merged ranges**, dates from
**2012-09-21** to **2020-07-18**.

## What to return

Fill these three files (headers are fixed — do not rename, reorder or add
columns):

### 1. `stage127_m2_external_return_daily_template.csv` — one row per ticker per trading day

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

### 2. `stage127_m2_external_return_mapping_template.csv` — one row per requested ticker

How each requested ticker maps to a TSETMC instrument (`tsetmc_instrument_id` /
InsCode, ISIN, official company name), with the evidence you used.

`mapping_status` must be exactly one of: `MATCHED` or `UNRESOLVED`.

### 3. `stage127_m2_external_return_manifest_template.csv` — one row per requested ticker

What you actually retrieved: requested vs returned date span, row count, and
status.

`retrieval_status` must be exactly one of: `SUCCESS`, `PARTIAL`, `FAILED`, `UNRESOLVED_MAPPING`.

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

1. 10-20 normalized daily rows in the `stage127_m2_external_return_daily_template.csv` format
2. the matching mapping rows
3. the matching retrieval manifest rows
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
