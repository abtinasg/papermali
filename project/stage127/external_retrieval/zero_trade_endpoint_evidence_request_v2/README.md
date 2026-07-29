# TSETMC zero-trade & low-return semantics — evidence request (v2)

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
| `input/endpoint_occurrence_requests.csv` | One row per **occurrence** — 523 rows (270 missing-`t0`, 253 missing-`T*`). |
| `input/low_return_range_requests.csv` | One row per **PENDING** low-return pair — 27 rows. Pairs already proven `GUARANTEED_LT126_EVEN_IF_ALL_ZERO_TRADE_ROWS_EXCLUDED` are NOT included here; nothing further is needed for them. |
| `input/low_return_semantics_upper_bound_audit.csv` | All 90 `<126`-return development pairs, with the ceiling computation and classification, for context. |
| `input/unique_evidence_requests.csv` | The full deduplicated request universe — 454 rows (427 `POINT_DATE`, 27 `RANGE`, 36 tagged `BOTH`). **Retrieve by this file.** |
| `input/pair_mapping.csv` | Maps each `unique_request_id` back to every pair/occurrence it answers (`reference_type` distinguishes an endpoint occurrence from a low-return pair). |

Scale: **454 unique requests** (427 point, 27
range), covering **103 tickers**, development target years
**1393, 1394, 1395, 1396, 1397, 1398, 1399** only.

Of the 90 `<126`-return pairs: **63** are already mathematically
`GUARANTEED` to stay under 126 no matter how this evidence resolves (no
further evidence needed), and **27** are `PENDING` — only these
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
one of: `CALENDAR`, `STATE`, `TRADE_HISTORY`, `DAILY_CLOSING`, `INSTRUMENT_HISTORY`, `INSTRUMENT_IDENTITY`. Then use
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
1393, 1394, 1395, 1396, 1397, 1398, 1399). It does **not** contain, reference,
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
