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

## Reviewed-evidence engine (Part 3.1A.5)

The reviewed-evidence engine evaluates each *reviewed* provenance record and
assigns a derived `reviewed_event_type`, `reviewed_date_precision`,
`reviewed_evidence_valid` and `evidence_role`. It accepts the canonical events
(`first_public_offering` / `first_public_trading`) as well as the non-canonical
entry events `admission`, `listing` and `public_company_conversion`
(`conversion_to_public` is mapped onto `public_company_conversion`). A successful
fetch is never evidence; only a reviewed, snapshot-and-hash-valid,
domain-consistent, document-specific record can support an event/date.

## Partial-date, conversion, conflict, derived fields (Part 3.1A.5.1)

- **Partial offering/trading** (`year_only` / `month_only`): the canonical date
  and canonical event type stay empty, `evidence_status=requires_manual_review`,
  `research_status=research_completed_partial_public_entry_date`, and the
  candidate date is recorded only in the matching offering/trading column.
- **`public_company_conversion`**: canonical date/event empty,
  `evidence_status=requires_manual_review`,
  `research_status=research_completed_noncanonical_entry_evidence`, never ready.
- **Same-event conflict**: two *incompatible* dates for the **same** event
  (offering↔offering, trading↔trading, admission↔admission, listing↔listing,
  conversion↔conversion) raise a conflict. A `jalali_dates_compatible` helper
  defines precision compatibility (exact `1380-03-15` is compatible with month
  `1380-03` and year `1380`; a different month/year or two different exact days
  conflict).
- **Admission + listing**: both candidate columns are preserved; the row is
  treated as listing-only pending first-public-trade evidence.
- The four reviewed-evidence fields are **fully derived** every run (removed from
  the review overlay; added to `DERIVED_NEVER_TRUSTED`). Records in a real
  conflict take `evidence_role=conflicting_evidence`. Provenance and research are
  built from one finalized record set.

## Cross-record aggregation & canonical selection (Part 3.1A.5.2)

- **Offering and trading are different events.** A different offering and trading
  date is **not** a conflict; `_conflict_group_for_event` gives every event its
  own conflict group, so a conflict can only arise within the same event.
- **Deterministic canonical selection** (`decide_canonical_public_entry_candidate`):
  all valid exact-day public-entry candidates are collected; the **earliest**
  exact date is the only one that may become canonical (tie-breaker:
  `first_public_offering` before `first_public_trading`). The earliest candidate
  becomes `candidate_supported` / ready **only** if its own event+date has a
  qualifying source (one official-regulatory document, one contemporaneous
  credible-news / company-official document, or two qualifying independent
  domains; aggregators alone never qualify). A later, better-sourced candidate
  can never override an earlier, unresolved one.
- **Exact candidate with an insufficient source** is not `no_reliable_evidence`;
  it gets the new status
  `research_completed_exact_public_entry_needs_corroboration`
  (`research_completion_status=completed_exact_candidate_needs_corroboration`,
  `evidence_status=requires_manual_review`, `ready=false`,
  `recommended_next_step=find_qualifying_corroboration`).
- **Earlier partial blocks a later exact** (`partial_candidate_blocks_exact`): a
  partial interval is expanded (`year_only` → whole year, `month_only` → whole
  month); if it could yield a date earlier than the exact candidate it blocks
  canonicalisation (status stays partial, `find_exact_public_entry_day`). A
  partial that *contains* or is entirely after the exact candidate does not block.
- **All candidate columns are built first** (admission / listing / offering /
  trading) via `select_best_compatible_candidate` (precision exact > month >
  year, tie-break lowest `source_index` then URL) before the dominant status is
  chosen, so no candidate is dropped by an early return.
- A single, idempotent `finalize_reviewed_evidence_set` feeds both the production
  pipeline and QC; QC compares the stored `evidence_role` against the finalized
  (conflict-aware) role, not a single-record evaluation. `no_reliable_evidence`
  is permitted only when no valid entry evidence of any kind exists.

Recommended next-step strings are fixed: partial → `find_exact_public_entry_day`;
exact-needs-corroboration → `find_qualifying_corroboration`;
admission/listing/conversion → `find_first_public_offering_or_trading`;
conflict → `resolve_conflicting_evidence`; ready → `recommend_user_review`.

The QC report is regenerated from the current engine with the network
hard-blocked; the 20 timeout provenance rows and 10 `research_blocked_network`
research rows are unchanged in research content (only the QC report's and
summary's `generated_at` / `source_commit` move).

## Unified decision engine & reproducible QC (Part 3.1A.5.3)

The final pre-research gate removes every remaining dual path and makes QC a
faithful mirror of the production engine.

- **Central status enums.** `ALLOWED_RESEARCH_STATUSES` and
  `ALLOWED_EVIDENCE_STATUSES` are exported from the module; production QC and the
  tests import them — no set is redefined locally. The corroboration status
  `research_completed_exact_public_entry_needs_corroboration` is included, so the
  real-output enum tests are forward-compatible.
- **One decision engine.** `decide_ready_for_user_review` is now a thin wrapper
  over `finalize_reviewed_evidence_set` / `decide_canonical_public_entry_candidate`
  and maps to the legacy keys. The QC `ready` path validates **only** the
  canonical decision (`ready`, `canonical_date`, `canonical_event`, earliest
  candidate, no partial blocker, no conflict). No QC or test keeps the old
  "different events = conflict" semantics.
- **Single finalizer in provenance.** `normalize_provenance_records` calls the
  finalizer and copies back the conflict-aware `evidence_role`; the standalone
  `_mark_conflicting_evidence_roles` is gone. `finalize_reviewed_evidence_set`
  writes the final `evidence_role` into schema-compatible `finalized_records`
  (the private `_final_evidence_role` mirror is never written to CSV).
- **Admission/listing coexistence.** The old `no_canonical_from_admission`
  assertion is replaced by `canonical_not_derived_from_noncanonical_event`: a
  canonical date is valid only when it equals the canonical engine's exact-day
  offering/trading decision, so admission/listing/conversion may coexist with a
  valid canonical without being rejected — but never produce one themselves.
- **Full research↔provenance recompute.** QC now compares every important
  derived field (candidate/canonical event & date, precision,
  ordinary_share_confirmed, evidence/research/completion status, network_blocked,
  all four source counts, ready, conflict flag/dates/reason, recommended next
  step, and the four candidate columns) against `_derive_screening_status`. The
  Gregorian canonical is recomputed independently: empty when the Jalali
  canonical is empty, otherwise the exact conversion.
- **Status-specific semantics** are asserted for every completed status, and
  **`no_reliable_evidence`** is permitted only when the finalizer shows no
  conflict, no exact candidate and no entry-event candidate of any kind.
- **Reproducible artifacts.** The QC report and summary record
  `source_file_sha256` and `test_file_sha256`, and the package is sealed with a
  two-commit workflow: a code commit (source/tests/README), then an artifact
  commit whose `source_commit` pins to the code commit's SHA on a clean tree.

## Forward-compatible real-output tests (Part 3.1A.4.2)

The real-output tests were refactored from baseline-locking assertions (which
would break as soon as Part 3.1B adds a source or a fetch succeeds) to
semantic-invariant assertions that remain valid as the data evolves:

- **Provenance invariants** (`test_o18_real_provenance_retrieval_evidence_invariants`,
  `test_r20b_real_retrieval_evidence_invariants`): failed fetches have no
  snapshot/hash; fetched sources have a valid SHA-256; reviewed sources are
  fetched; `evidence_accepted` always matches the engine's recomputation.
- **Registry ↔ provenance integrity** (`test_r20_real_provenance_registry_integrity`):
  every provenance row is in the registry; active registry rows are one-to-one
  with provenance; inactive rows are not in provenance.
- **Research semantic validity** (`test_o19_real_research_rows_semantically_valid`,
  `test_real_output_research_semantics_valid`): `research_status` and
  `evidence_status` are in allowed enums; network-blocked tickers have zero
  counts and are not ready; ready tickers have `exact_day` precision, a valid
  canonical date, and no conflict; conflict tickers are not ready.
- **Research counts match provenance** (`test_r20c_real_research_counts_match_provenance`):
  per-ticker `fetched_source_count`, `reviewed_source_count`,
  `evidence_source_count`, and `attempted_source_count` in the research CSV
  match the actual counts in the provenance CSV.
- **Summary matches outputs** (`test_r20d_real_summary_matches_current_outputs`):
  `ready_count`, `network_blocked_count`, `total_attempted_sources`,
  `total_fetched_sources`, `total_reviewed_sources`, and
  `total_evidence_sources` in the summary JSON match the current CSVs.
- **Worklist semantic validity** (`test_real_worklist_semantically_valid`):
  10 unique tickers in order; non-empty URLs are http(s) with real hosts;
  `candidate_date_jalali` agrees with `date_precision`; enums are valid and
  non-empty.
- **Synthetic fixtures**: `test_synthetic_all_timeout_fixture_blocked` verifies
  the all-timeout semantics independently of the committed CSV;
  `test_prov_valid_third_source_passes`, `test_prov_valid_fetched_source_passes`,
  `test_research_valid_candidate_supported_passes`, and
  `test_research_valid_conflict_passes` verify that legitimate Part 3.1B findings
  pass through the pipeline.
- **Negative tests**: `test_failed_fetch_fabricated_snapshot_fails`,
  `test_accepted_evidence_inconsistent_fails`,
  `test_active_registry_missing_in_provenance_fails`,
  `test_provenance_outside_registry_fails`,
  `test_research_count_inconsistent_fails`, and
  `test_summary_count_inconsistent_fails` verify that QC catches each class of
  data corruption.

The removed tests (`test_o18_current_timeout_records_unchanged`,
`test_o19_current_research_rows_unchanged`,
`test_real_output_all_blocked_network`,
`test_real_worklist_ten_rows_and_empty_fields`,
`test_r20_current_outputs_unchanged_character`,
`test_f18_current_outputs_unchanged`,
`test_g18_current_outputs_unchanged`) locked on the current all-timeout
baseline (20 rows, all `research_blocked_network`, empty worklist). The new
tests enforce the same invariants without assuming a specific baseline.

## Candidate-date ↔ precision agreement (Part 3.1A.4.1)

A small semantic tightening of the worklist QC:

- `validate_worklist_date_precision(candidate_date_jalali, date_precision)`
  enforces agreement: empty date ⇒ `unknown`; non-empty date ⇒ not `unknown`;
  `year_only`⇒`YYYY` (1200–1500); `month_only`⇒`YYYY-MM`; `exact_day`⇒`YYYY-MM-DD`
  (real convertible Jalali). New assertions `worklist_date_precision_enum_valid`
  and `worklist_date_precision_matches_candidate`.
- `ordinary_share_explicit` and `manual_review_status` are now required non-empty
  and must be valid enum values. The current template (unknown / unknown /
  pending_manual_research / empty date) still passes unchanged.

## Forward-compatible registry & worklist QC (Part 3.1A.4)

The QC was relaxed where it would have wrongly blocked legitimate Part 3.1B
findings, without weakening integrity:

- **Registry QC is no longer locked to 20 rows.** `registry_exactly_20_seed_rows`
  / `registry_two_seed_sources_each` are replaced by seed-preservation checks:
  `registry_seed_20_preserved`, `registry_seed_keys_preserved` (10 tickers ×
  index {1,2}), `registry_seed_content_unchanged` (type/title/url/source_origin),
  `registry_minimum_two_seed_sources_each`, and
  `registry_additional_sources_allowed` (manual_discovery rows at index ≥ 3). The
  registry may grow; `(ticker, source_index)` stays unique, per-ticker URLs stay
  unique, and `active_registry_matches_provenance` /
  `inactive_registry_not_in_provenance` keep active rows one-to-one with
  provenance.
- **Worklist QC is now semantic, not "must be empty".** Empty findings are still
  fine, but non-empty values must be well-formed: `worklist_exact_ticker_scope`,
  `worklist_no_duplicates`, `worklist_discovered_urls_valid` (empty or http(s)
  with a real host and no local path), `worklist_candidate_date_valid` (empty or
  valid Jalali year / month / exact-day), `worklist_event_candidate_valid`,
  `worklist_ordinary_share_value_valid`, `worklist_manual_status_valid`. A
  discovered URL in the worklist is a candidate only and never auto-enters the
  registry.

## Persistent source registry & worklist preservation (Part 3.1A.3)

- **Source registry is the source of truth.** `part03_source_registry.csv`
  (schema: ticker, source_index, source_type, source_title, source_url,
  source_origin, active, discovery_status, added_at_utc, added_by,
  discovery_notes) drives retrieval. It is seeded once with exactly the 20 current
  sources (`source_origin=seed_part03`, `active=true`,
  `discovery_status=network_blocked`). `fetch_sources()` reads it via
  `load_source_registry()` / `validate_source_registry()` /
  `registry_to_research_sources()`; `run()` no longer depends on the hardcoded
  `RESEARCH_SOURCES` (kept only for seeding/migration). A new Part 3.1B URL is
  added at the next `source_index` and flows into the pipeline with no code change;
  inactive rows are skipped. Validation is fail-closed (only the 10 tickers,
  unique `(ticker, source_index)`, positive index, non-empty url/type, no
  duplicate url per ticker, `active∈{true,false}`).
- **Explicit discovery registration.** `register_discovered_sources(registry_df,
  additions_df)` assigns the next index per ticker, rejects duplicate URLs and
  out-of-scope tickers, tags `source_origin=manual_discovery`, fetches nothing and
  does not overwrite the file. Worklist URLs never auto-enter the registry.
- **Worklist persistence.** `merge_existing_worklist_with_current_status()`
  preserves all manual columns (discovered_source_*_url, first_public_event_candidate,
  candidate_date_jalali, date_precision, ordinary_share_explicit, conflict_notes,
  manual_review_status, reviewer_notes) and refreshes only company_name /
  current_research_status / network_blocked. Matching is by ticker; an added,
  removed or duplicated ticker is fail-closed.
- **Review audit fields.** `reviewer_notes` and `manual_reviewed_at_utc` are added
  to the provenance schema; they are preserved only via a validated overlay,
  cleared on a stale review, never inherited by timeouts, and never auto-filled.
  Research primary/secondary are taken from the recomputed provenance by ascending
  `source_index`, not from any hardcoded list.

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
