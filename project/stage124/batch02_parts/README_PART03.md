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

## Research status vs. evidence (Part 3.1A correction)

A failed fetch (`timeout` / `connection_error` / `fetch_error`) means the
research could **not be completed** because of network limits — it is **not**
the same as "no reliable evidence". The two are now strictly separated:

- `research_status=research_blocked_network` + `evidence_status=requires_manual_review`
  when every source attempt failed on the network (no fetch succeeded). The
  ticker also carries `network_blocked=true` and `research_completion_status=blocked_network`.
- `evidence_status=no_reliable_evidence` is permitted **only** after sources were
  actually fetched **and** reviewed, yet none carried first-public-entry evidence.
  A timeout/connection error can never produce `no_reliable_evidence`.

A successful fetch is **not** evidence by itself. Page content must be reviewed
(`content_review_status=reviewed`) before any event/date is supported.

## Fetch / evidence separation (provenance)

Each provenance record now records the review layer separately from the fetch:
`content_review_status`, `source_authority_class`, `ordinary_share_explicit`,
`event_type_supported`, `exact_date_explicit`, `reviewed_date_jalali`,
`independent_source_group`, and `evidence_accepted`. A record is `evidence_accepted`
only when it is fetched, reviewed, snapshot+SHA-256 valid, supports a canonical
exact-day event, and states the instrument is an ordinary share.

## Canonical rule and safe `ready_for_user_review`

A `proposed_canonical_public_entry_date_jalali` may only be set when there is an
**exact-day** event of type `first_public_offering` or `first_public_trading`,
the ordinary-share nature is **explicitly** confirmed, and the event is backed by
reviewed evidence with a recorded snapshot and valid SHA-256. `ready_for_user_review=true`
is produced by an independent, testable decision (`decide_ready_for_user_review`)
that additionally requires either **one official / credible-news source** or
**two independent sources from different domains**. A single aggregator, two
sources sharing one domain, or a generic Codal search page can never reach
`ready=true`. `ordinary_share_confirmed` is never derived merely from the presence
of an event/date. Admission, listing, registration, conversion-to-public, market
transfer, symbol changes, rights offerings, or the oldest TSETMC record are
**never** canonical on their own. No date is guessed; conflicts force `ready=false`.

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
fabricated, and no new network request was made. Consequently every ticker is
screened as `research_status=research_blocked_network`,
`evidence_status=requires_manual_review`, `network_blocked=true`,
`date_precision=unknown`, `ordinary_share_confirmed=unknown`, with an empty
canonical date and `ready_for_user_review=false`. `fetched_source_count`,
`reviewed_source_count`, and `evidence_source_count` are all `0`, and the ready
count is `0`. No ticker is `no_reliable_evidence`. None of the 10 tickers exist
in the frozen V2 TSETMC audit, so each TSETMC row is `not_in_historical_v2_audit`.
The QC report (`part03_qc_report.json`) is fully self-computed and fail-closed.

## Manual research worklist (Part 3.1B)

`part03_manual_research_worklist.csv` holds exactly 10 rows in Part 3 order, with
pre-filled Farsi search queries (company + عرضه اولیه / نخستین روز معامله /
پذیرش بورس / درج نماد / امیدنامه) and **empty** discovered-source/date fields. No
URL or date is guessed; these are filled during the manual/browser research step.

## Files

- `part03_tickers.csv`
- `part03_research_screening_10tickers.csv`
- `part03_source_provenance_10tickers.csv`
- `part03_tsetmc_audit_10tickers.csv`
- `part03_manual_research_worklist.csv`
- `part03_qc_report.json`
- `part03_summary.json`
- `snapshots_part03/` (successful snapshots only; empty when all fetches fail)

The final hash manifest and the Part 3 finalizer are intentionally **not**
produced here; that step runs after these screening results are reviewed.
