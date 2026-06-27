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

## Manual review ↔ evidence engine wiring (Part 3.1A.2)

The data flow was corrected so research screening is built **only** from the
recomputed provenance:

1. raw retrieval records →
2. `apply_validated_review_overlay()` overlays validated manual-review fields from
   the prior provenance file →
3. all derived evidence fields are recomputed (`normalize_provenance_records()`) →
4. final provenance →
5. `build_research_screening()` derives status from that provenance only →
6. QC + summary.

- **Controlled review preservation.** A prior manual review is kept only when the
  row matches on `(ticker, source_index)` AND the source_url, snapshot_path and
  content_sha256 are unchanged and the on-disk snapshot still hashes to that
  content_sha256. If the URL / snapshot / hash changed, every manual field is
  cleared and `content_review_status=stale_review_invalidated`; a timeout/failed
  record never inherits a review.
- **Derived fields are never trusted from the CSV.** `source_authority_class`,
  `authority_validation_error`, `document_specific`, `contemporaneous_with_event`,
  `independent_source_group`, `evidence_accepted` and `ready_for_user_review` are
  always recomputed; a manual `evidence_accepted=true` is ignored.
- **company_official is fail-closed.** Honoured only when the host is in
  `VERIFIED_COMPANY_OFFICIAL_DOMAINS[ticker]` (boundary-safe). The whitelist is
  empty until a company domain is actually verified in Part 3.1B; one ticker's
  domain is never valid for another.
- **TSETMC is `official_market_data_audit`.** It may corroborate but is never
  qualifying, never single-source ready, never counted in the two-source path,
  and never the sole basis of a canonical date.
- **SENA is market news.** `sena.ir` is `credible_news`: as a single source it
  needs an explicit contemporaneous publication date (≤30 days).
- **Per-class document specificity.** Regulatory needs a stable-id document;
  credible news needs a specific article (not category/tag/search/archive);
  company-official needs a specific news/announcement/PDF on the verified domain
  (not about/investor/profile); aggregators are never qualifying.

## Evidence engine hardening (Part 3.1A.1)

The evidence engine was tightened before any real research:

- **Domain-strict taxonomy.** `classify_source_authority()` is fail-closed and
  uses `urllib.parse` with boundary-safe host matching. The URL's real domain is
  the source of truth; a declared `source_type` that contradicts the domain
  yields `unknown` plus an `authority_validation_error`. `codal_official` is only
  valid on `codal.ir` (or a real subdomain) — `fake-codal.ir`, `codal.ir.example.com`
  and Tacodal can never be official.
- **Discovery vs. document.** `is_document_specific_source()` rejects search /
  list / overview pages (Codal `ReportList.aspx`, symbol-search, Rahavard
  `/asset/`, homepages). Codal evidence is accepted only from a specific document
  with a stable id (LetterSerial / TracingNo / AnnouncementId / attachment / PDF).
- **Real exact-day dates.** `is_valid_exact_jalali_date()` requires a complete,
  in-range, round-trippable `YYYY-MM-DD`; year-only, month-only and invalid
  strings are rejected.
- **Qualifying sources only.** Two-independent readiness counts only qualifying
  authorities (official-regulatory / credible-news / company-official) from two
  different real domains. Aggregator/unknown sources may corroborate but never
  make a record ready — two aggregators or aggregator+unknown never reach ready.
- **Contemporaneous news.** A single credible-news source must carry an explicit
  publication date within 30 days of the event; an official-regulatory document
  needs no contemporaneity but must still be document-specific, reviewed,
  hash-backed, ordinary-share-explicit and exact-day.
- **Computed `evidence_accepted`.** Provenance `evidence_accepted` is always the
  engine's recomputation (manual values are ignored); QC re-checks the match.
- New provenance columns: `authority_validation_error`, `document_specific`,
  `publication_date_jalali`, `publication_date_explicit`,
  `contemporaneous_with_event`. For the 20 current (timeout) records they are
  `false`/empty and `evidence_accepted=false`.

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
