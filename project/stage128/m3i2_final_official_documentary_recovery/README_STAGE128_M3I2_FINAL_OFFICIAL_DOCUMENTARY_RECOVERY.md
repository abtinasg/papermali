# Stage128 — M3I-2 final official documentary recovery (INITIATION ONLY)

**Action id:** `stage128-m3i2-final-official-documentary-recovery-initiation`
**Baseline:** `main @ b3627809dbfde8429d0308bec5d1c8541a161188` (the merge commit of PR #75)
**Predecessor:** PR #75 — `stage128-m3i2-official-source-evidence-capture` (merged)

```
FINAL OFFICIAL DOCUMENTARY RECOVERY INITIATION ONLY
NO REPEAT OF PRIOR ARCHIVE CAPTURE
NO ARCHIVE ZIP REDOWNLOAD
NO COVERAGE
NO DATA GATE
NO FEATURE MATERIALIZATION
NO MODELING
NO FINAL TEST
NO M3-LAG-WDI CONTRACT LOCK
NO MERGE AUTHORIZATION
```

## What this action is

A bounded, final attempt to recover **official documentary evidence** for the
two — and only two — blockers that keep M3I-2 unresolved, plus preparation of
exactly one official inquiry to the World Bank Data Help Desk.

1. **Archive release availability.** Is there an official release calendar,
   version history, edition log or publication-date record for historical WDI
   archive editions, and what exactly does a date token in an archive filename
   mean?
2. **Historical FX semantic continuity.** For `PA.NUS.FCRF` / `IRN`: the
   historical local-currency denomination, the valuation convention, the
   period-average construction, any redenomination or unit break, and whether
   an annual log change over two consecutive observations from one archived
   edition is unit-consistent.

Acquisition of official *documents* is not admission of *data*. This action
cannot and does not move M3I-2 towards PASS.

## Outcome

| item | value |
| --- | --- |
| bounded documentary GET requests | 14 of a maximum of 20 |
| archive ZIP downloads / redownloads | 0 / 0 |
| duplicate requests of prior captured URLs | 0 (blocked by a fail-closed guard) |
| bounded-search outcome | `NO_NEW_DOCUMENTARY_EVIDENCE_IN_BOUNDED_SEARCH` |
| initiation status | `HUMAN_SUBMISSION_REQUIRED` |
| initial inquiries attempted / submitted | 0 / 0 (maximum 1) |
| blocker 1 resolved | **false** |
| blocker 2 resolved | **false** |
| M3I-2 evidence status | `UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE` |

### What the bounded search did find (and why it resolves nothing)

* The official **WDI release notes** exist only from **December 2024** onward
  (`wdi_release_note_toc`). No official release note covers the historical
  editions behind the 37 development cutoffs.
* The official **Data Updates and Errata** page announces dated **database
  updates** for 2010-2024 (`wb_kb_data_updates_and_errata`). These are database
  update announcements, not archive-edition publication records, and several
  announced dates differ from the archive filename tokens. Mapping an
  announcement onto an archive edition would be an assumption, not evidence.
* The complete official Help Desk **article index** contains no article on
  archive release dates and none on Iranian rial denomination or
  redenomination (`wb_helpdesk_all_articles_index`).
* The official indicator page for `PA.NUS.FCRF` / Iran confirms only the series
  title and the IMF IFS source (`wb_data_pa_nus_fcrf_irn`); the **DEC
  conversion factor** article confirms the official rate is the IFS rate on a
  calendar-year basis (`wb_kb_dec_conversion_factor`). Neither states the
  Iranian denomination, valuation convention or any unit break.

Therefore **rule D** applies unchanged for every edition:
`available_at = null`, `release_date_verified = false`.

### Why the inquiry was not submitted by automation

The Data Help Desk exposes no public support form; opening a ticket requires a
signed-in account. Automation must not create an account, sign in, supply a
personal e-mail address or bypass any human-verification step, so the inquiry
is fully prepared and left for a human supervisor. **No ticket id was invented
and no confirmation was fabricated.**

## Locked availability rules (A-E)

| rule | official evidence | `available_at` |
| --- | --- | --- |
| A | exact timestamp with timezone | that timestamp normalized to UTC |
| B | full date `YYYY-MM-DD`, no time | the **next** calendar day, `00:00:00Z` |
| C | month and year only, officially confirmed | the **first day of the next month**, `00:00:00Z` |
| D | only a filename/URL token | `null`, `release_date_verified = false` |
| E | — | an unproven previous-month fallback is **forbidden** |

Never evidence, on their own: filename token, URL token, retrieval timestamp,
HTTP `Last-Modified`, ZIP member timestamp, workbook properties, local file
mtime, workbook year columns, cache date, search-engine snippet.

## Stopping rule (locked prospectively)

* initial inquiry: **maximum 1**;
* waiting period: **10 business days** after a successful submission
  (Monday-Friday only, submission day excluded, public holidays not modeled);
* follow-up: **maximum 1**, only after the waiting period and only under a
  separate explicit human authorization; automatic follow-up is forbidden;
* a response, whenever it arrives, is ingested and adjudicated only in a
  **separate action**;
* if a response is still insufficient after an authorized follow-up, the
  terminal status is `UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY`, after which the
  M3-LAG-WDI-EXPLORATORY path may be *considered* under its own authorization.

Resolving only one blocker never admits M3I-2:
`partial_documentary_recovery_can_admit_m3i2 = false`.

## Superseded local M3-LAG draft

A local, uncommitted draft of the M3-LAG-WDI exploratory contract was partially
materialized before the human supervisor superseded that path. It produced no
data retrieval, Gate, modeling or Final Test access and never became an
authoritative repository contract. It was **quarantined outside the repository
and left untouched** — not deleted, not cleaned, not committed. See
`stage128_m3_lag_partial_local_execution_supersession_record.json`. The
authorization behind that draft is consumed and is **not reusable**.

## Files

| file | role |
| --- | --- |
| `..._contract.json` | the locked bounds of this action |
| `..._human_authorization_record.json` | the one-action authorization (text, bytes, SHA-256) |
| `..._baseline.json` | baseline verification and the read-only carry-over of prior findings |
| `..._search_log.csv` | every documentary GET: URL, purpose, status, hash, bytes |
| `..._evidence_manifest.csv` | per-document evidence assessment (`resolves_blocker` is false throughout) |
| `stage128_m3i2_world_bank_inquiry_request.md` | the exact inquiry body to be submitted |
| `m3i2_world_bank_inquiry_edition_inventory.csv` | attachment 1 — public edition inventory |
| `m3i2_world_bank_inquiry_fx_semantic_questions.md` | attachment 2 — FX semantic questions |
| `..._inquiry_submission_record.json` | submission status, hashes, human-submission instructions |
| `..._governance_boundary.json` | what this action may not touch |
| `stage128_m3_lag_partial_local_execution_supersession_record.json` | the superseded local draft |
| `..._decision.json` | the decision record |
| `..._qc_report.json` | fail-closed QC assertions |
| `metadata_and_hashes_....json` | SHA-256 of every package file |
| `raw_official_documents/` | the retained official bytes, hashed |

Reproduce the derived artifacts with:

```bash
python project/run_stage128_m3i2_final_official_documentary_recovery.py
```
