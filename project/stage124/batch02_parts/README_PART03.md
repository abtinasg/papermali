# Stage124 Batch 2 — Part 3: Research Screening (next 10 tickers)

This package contains the **research screening only** for the next 10 tickers in
Batch 2. It does **not** change eligibility or ranking, does **not** build a
verified master, does **not** run Gate B, and does **not** run any modelling.

## Scope (exact, ordered)

| # | Ticker | Company |
|---|--------|---------|
| 1 | خمهر | مهرکام پارس |
| 2 | خنصیر | مهندسی نصیر ماشین |
| 3 | خوساز | محورسازان ایران خودرو |
| 4 | خچرخش | چرخشگر |
| 5 | خکمک | کمک فنر ایندامین |
| 6 | دروز | روز دارو |
| 7 | دسبحا | گروه دارویی سبحان |
| 8 | دیران | ایران دارو |
| 9 | رانفور | خدمات انفورماتیک |
| 10 | رمپنا | گروه مپنا |

No Part 2 or Pilot15 ticker is re-researched.

## Canonical rule

A `proposed_canonical_public_entry_date_jalali` may only be set when there is an
**exact-day** event of type `first_public_offering` or `first_public_trading`,
the ordinary-share nature is confirmed, and the event is backed by **fetched**
evidence with a recorded snapshot and SHA-256. Admission, listing, registration,
conversion-to-public, market transfer, symbol changes, rights offerings, or the
oldest TSETMC record are **never** canonical on their own. No date is guessed.

## TSETMC

No live TSETMC probe is performed in Part 3. Historical TSETMC results are read
**only** from the frozen V2 audit
`project/stage124/listing_batch02_tsetmc_conflict_audit_v2.csv`. Each TSETMC
audit row records `probe_source=historical_v2_audit` and
`network_request_performed=false`. A `network_unreachable` historical status is
preserved and never converted to "no candidate". Any historical TSETMC date is
audit evidence only and never automatically canonical.

## Source fetching

Up to 3 source URLs per ticker were attempted, **sequentially**, with
`timeout=5s` and `retry=0`. Only the genuine `codal.ir` domain is tagged
`codal_official`; Tacodal / Databours and similar aggregators are tagged
`market_information_aggregator`. A failed fetch records the real failure reason
and **never** fabricates a snapshot or hash. Successful snapshots (if any) are
stored only under `snapshots_part03/`, with relative paths.

## Result of this run

All 20 source-fetch attempts returned `timeout` (the upstream Iranian sources
were unreachable from the run environment). No snapshot and no hash were
fabricated. Consequently every ticker is screened as `no_reliable_evidence`,
`date_precision=unknown`, with an empty canonical date and
`ready_for_user_review=false`. None of the 10 tickers exist in the frozen V2
TSETMC audit, so each TSETMC row is `not_in_historical_v2_audit`. The QC report
(`part03_qc_report.json`) is fully self-computed and fail-closed.

## Files

- `part03_tickers.csv`
- `part03_research_screening_10tickers.csv`
- `part03_source_provenance_10tickers.csv`
- `part03_tsetmc_audit_10tickers.csv`
- `part03_qc_report.json`
- `part03_summary.json`
- `snapshots_part03/` (successful snapshots only; empty when all fetches fail)

The final hash manifest and the Part 3 finalizer are intentionally **not**
produced here; that step runs after these screening results are reviewed.
