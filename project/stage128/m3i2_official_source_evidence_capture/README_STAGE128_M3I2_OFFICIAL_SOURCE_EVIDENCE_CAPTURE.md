# Stage128 — M3I-2 official-source evidence capture

**Action id:** `stage128-m3i2-official-source-evidence-capture`
**Action type:** `official_source_evidence_capture_only_no_join_no_feature_no_coverage_no_gate_no_modeling`
**Baseline:** `main` @ `cf23771a383bf9ad8f7ff2855c216c9a240647ff`
**Evidence status:** `UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE`
**Result code:** `M3I2_OFFICIAL_SOURCE_EVIDENCE_CAPTURE_UNRESOLVED_READY_FOR_INDEPENDENT_AUDIT`

```text
OFFICIAL-SOURCE EVIDENCE CAPTURE ONLY
NETWORK ACCESS LIMITED TO OFFICIAL WORLD BANK / IMF SOURCES
RAW BYTES RETAINED AND HASHED
NO COMPANY-PANEL MACRO JOIN
NO FEATURE MATERIALIZATION
NO COVERAGE
NO DATA GATE
NO MODELING
NO M3I-vs-M2
NO M4
FINAL TEST LOCKED
NO MERGE AUTHORIZATION
```

## What this action is

An evidence-acquisition action. It captures, hashes and packages **official**
World Bank WDI and IMF material for the already-merged M3I-2 contract and the
contingent M3I-3 financing shell. It answers exactly one question: *is there an
independently auditable, raw-byte-backed official-source evidence package?*

It does **not** answer whether M3I-2 meets coverage thresholds, whether it
improves prediction, whether it should be admitted, or what the final model is.
An evidence status of `EVIDENCE_COMPLETE_FOR_SEPARATE_M3I2_DATA_GATE_REVIEW` would mean only that a **separate,
separately authorized** Data Gate may be *considered* after human review.

## The merged contract is read-only

`project/stage128/m3_intl_macro_contract_lock/**` is byte-identical to `cf23771a383bf9ad8f7ff2855c216c9a240647ff`. Candidate
ids, source ids, indicator codes, transformations, observation-year rules,
vintage rules, missing-value rules, Data Gate thresholds, multiplicity families,
the financing shell's null fields and the final-test controls are all unchanged.

Locked candidates, restated for the reader (not redefined here):

1. `cand_m3i_cpi_inflation_annual` → `intl_cpi_inflation_annual`, `FP.CPI.TOTL.ZG`,
   transformation `identity`.
2. `cand_m3i_fx_change_official_annual` → `intl_fx_change_official_annual`,
   `PA.NUS.FCRF`, transformation `100 * ln(E_y / E_(y-1))` — **not
   evaluated in this action**.

## Development-cutoff input firewall

Cutoffs come from one uniquely bound source:

* path `project/stage128/stage128_m2_d2_development_features.csv`
* git blob `89c4b2c30906dcf1fc1f5baf112d7e4586c5f5be`
* SHA-256 `068519065fc4c36594a892b14c9242471a088e7b33484fbd5453b12391af2583`
* cutoff field `pair_cutoff_date`
* columns read: `ticker`, `fiscal_year_t`, `target_year`, `pair_cutoff_date`, `in_three_variable_common_sample`

No target, financial, market or macro feature column was read, no final-test
directory was searched, and only development target years
1393–1399 are in
scope. Unique development cutoffs:
**37** over
539 development pairs — an
**input-integrity count, not coverage**.

**Known limitation.** `pair_cutoff_date` is a date with no
verified intraday `available_at` timestamp: Stage125 Part3B1A locked the Cut-A
operationalization but recorded zero real `available_at` assignments. Edition
selection therefore uses `00:00:00Z` of the cutoff date — the
earliest possible instant, which can only **exclude** an edition, never admit
one.

## Official sources

Discovery roots, captured before anything was downloaded from them:

* https://datatopics.worldbank.org/world-development-indicators/wdi-archives.html
* https://databank.worldbank.org/databases/archives
* https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FP.CPI.TOTL.ZG
* https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.FCRF
* https://data.imf.org/en/datasets/IMF.STA%3AMFS_IR

Only official `worldbank.org` / `imf.org` hosts may terminate a request, HTTPS
only, with a descriptive User-Agent, a finite timeout, at most 3 attempts per
request and deterministic backoff. A redirect that leaves an official host is a
hard stop. Mirrors, aggregators, FRED/ALFRED, DBnomics, Kaggle, GitHub copies
and unofficial Iranian FX sources are forbidden, and a search-result snippet is
never evidence.

## Evidence status

**`UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE`**

* official requests attempted: 21
* official responses retained: 21
  (successful: 21)
* raw bytes retained: 1066295643 bytes across
  21 objects
* WDI editions discovered: 110
* editions with a **verified** release date:
  **0** — unverified filename
  date tokens: 110
* required (servable) editions: **0** —
  archive editions actually captured and held:
  16
* cutoffs without a verified pre-cutoff vintage:
  **37** of
  37
  (539 of 539
  development pairs)
* locked-series rows extracted: 1878
* semantic compatibility — CPI PASS 16 /
  UNRESOLVED 0 / FAIL_INTEGRITY
  0; **FX** PASS
  0 / UNRESOLVED
  16 / FAIL_INTEGRITY
  0
* capture invocations: 2
* IMF catalog entries: 0
* financing metadata decision: `NO_EXACT_CANDIDATE_IDENTIFIED_UNRESOLVED_METADATA_LOCK`

Unresolved evidence is **never** converted into zero coverage or into an
observed failure. Missing proof is `UNRESOLVED`, not `FAIL`.

## Why nothing has a verified release date

The official archive listing publishes a table of `Year | Month(s)` and a
hyperlink per edition. The date inside a filename such as
`WDI_excel_2017_09_19.zip` is recorded as an **`edition_date_token`** — and
that is all it is. The retained listing bytes contain **no** occurrence of
"release", "released", "publish", "published", "last updated" or "revision",
and no retained archive states an edition-level release date either. So no
retained official bytes describe that token as a release, publication or update
date.

Under the locked rule, that means `release_date_verified = false`,
`derived_release_available_at_utc = null` and
`release_available_at_derivation_status =
UNRESOLVED_FILENAME_DATE_TOKEN_NOT_VERIFIED_AS_RELEASE_DATE` for every edition. Retrieval time,
`Last-Modified`, ZIP member timestamps and workbook properties are explicitly
not accepted as substitutes.

An edition with no verified `available_at` can never be a pre-cutoff vintage,
so **every** development cutoff is unresolved. The archives themselves are
still held and still extracted — being unable to date an edition is not the
same as not having it.

## Why every FX row is UNRESOLVED

The archived `PA.NUS.FCRF` metadata gives a generic construct
("Official exchange rate (LCU per US$, period average)", `Periodicity: Annual`,
`Unit of measure` empty) and a generic methodology note about exchange-rate
arrangements. Section 4 permits an archived title to support the construct and
the **unit label** — but not the three continuity facts a log change depends
on:

1. which currency unit the local-currency figures are denominated in;
2. the local-currency valuation definition for that vintage;
3. that no redenomination or currency-unit break falls across the pair.

The archived metadata names no currency, no denomination and no unit break, and
silence is not proof of absence. All three therefore stay unverified and every
FX row is `UNRESOLVED`. Continuity is **not** inferred from smooth values, and
the current metadata page — which states it was updated on a 2026 date — is not
used as proof about historical editions.

CPI rows remain `PASS` where the archived title, annual periodicity, percent
rate and calendar-year columns are each evidenced; the provenance of the unit
claim now travels in the committed CSV as `unit_evidence_source`.

## Forbidden execution counters — all zero

company macro joins, feature materializations, coverage calculations, Data Gate
executions, model fits, predictions, predictive metrics, Holm calculations,
final-test rows read.

QC: **74 assertions, 0 failed**,
all_pass = **True**.

## State after this action

* `m3i2_contract_status` = `PROSPECTIVELY_LOCKED_NO_DATA`
* `m3i2_data_gate_executed` = **false**, `m3i2_block_admitted` = **false**,
  `m3i2_modeling_started` = **false**
* `m3i3_admitted` = **false**, lock `UNRESOLVED_METADATA_LOCK`
* M3-CBI `UNRESOLVED_M3_DATA_GATE`, admitted **false**
* `m4_authorized` = **false**, `m4_started` = **false**
* `final_test_locked` = **true**
* `merge_authorized` = **false**

Next pointer (informational only): `stage128-m3i2-official-source-evidence-review` with
`next_research_action_authorized` = **false**. **An evidence-capture completion
does not by itself authorize the Data Gate.**
