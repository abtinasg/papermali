# TSETMC zero-trade endpoint semantics — evidence request

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

- `ClosingPrice/GetInstrumentCalendar/{InsCode}` (trading calendar)
- `MarketData/GetInstrumentState/{InsCode}/{DEven}` (instrument state)
- `Trade/GetTradeHistory/{InsCode}/{DEven}/...` (executed trades)
- `ClosingPrice/GetClosingPriceDaily/{InsCode}/{DEven}` (daily closing
  record)
- `Instrument/GetInstrumentHistory/{InsCode}/{DEven}` (instrument history)
- `Instrument/GetInstrumentIdentity/{InsCode}` (identity/ISIN history)

**Do not use** Yahoo Finance, Kaggle, unofficial mirrors, or any third-party
dataset. If TSETMC cannot answer a question, report `UNRESOLVED` — do not
substitute another source.

## Input files

| file | meaning |
|---|---|
| `input/endpoint_occurrence_requests.csv` | One row per **occurrence** — 523 rows (270 missing-`t0`, 253 missing-`T*`). |
| `input/unique_endpoint_requests.csv` | The same evidence, deduplicated by (InsCode, date) — 427 rows. **Retrieve by this file** so you never fetch the same date twice. |
| `input/pair_mapping.csv` | Maps each `unique_request_id` back to every `request_id` (pair) it answers. Do not lose this mapping. |
| `input/low_return_reference_context.csv` | 90 additional development pairs with fewer than 126 valid daily returns, included for context only (diagnostic, not a request for new endpoints beyond what is already listed above). |

Scale: **427 unique instrument/date requests**, covering
**103 tickers**, development target years **1393, 1394, 1395, 1396, 1397, 1398, 1399** only.

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
  `A_MARKET_OPEN_INSTRUMENT_ELIGIBLE_ZERO_TRADES`, `B_INSTRUMENT_SUSPENDED_OR_PROHIBITED`, `C_CALENDAR_ARTIFACT_NOT_A_TRADING_DAY`, `D_LEGITIMATE_TRADING_DAY_ZERO_EXECUTIONS`, `E_OTHER_TSETMC_STATE`, `POTENTIAL_TSETMC_HISTORY_FRAGMENTATION`, `UNRESOLVED`;
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
1393, 1394, 1395, 1396, 1397, 1398, 1399). It does **not** contain, reference,
or request evidence for target years 1400, 1401, or 1402, and no final-test
predictor or target value is included anywhere in this package.

## Please do NOT compute

Do not classify, aggregate, or draw conclusions across dates. Just report the
authoritative TSETMC evidence, per date, with provenance.
