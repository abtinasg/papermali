# Source use and redistribution notes

This file records, provider by provider, what was used, what is included here,
what an environment check could and could not establish, and what the **human
author has determined**. It keeps those three things apart on purpose. Where a
term could not be verified, this file still says so; a human determination is
recorded as a human determination and never re-described as verification.

**Environment terms check: 2026-08-21. Human author determination: 2026-08-21.**

---

## Disposition: READY_FOR_EXACT_DIGEST_HUMAN_REVIEW

Release candidate **1.0.0-rc.3**. It supersedes 1.0.0-rc.2, which in turn
superseded 1.0.0-rc.1 (marked `NOT_READY_FOR_PUBLICATION`). Both predecessors
are preserved, not deleted.

### What 1.0.0-rc.3 corrected, and what it did not touch

1.0.0-rc.2's Zenodo description named all three study providers together as
the sources of the released values. As a statement about **this release** that
is false, and it contradicted the very matrix below. The superseded wording is
preserved verbatim in the study repository's decision record, so the correction
stays auditable without reproducing a false statement here. rc.3 replaces it
with what the matrix has said throughout:

> The released company-year panel contains researcher-compiled company
> financial-statement fields from publicly accessible CODAL disclosures,
> together with author-derived variables and annotations. **No TSETMC- or
> World Bank-derived field is included in this release**; those sources relate
> only to the wider study.

That correction is about **composition**, not about rights. **No rights record
changed.** No CODAL or TSETMC terms page has been retrieved or read — then, in
rc.2, or since; their stated terms are still `NOT_VERIFIED`; the CODAL row still
carries its rc.1 `BLOCKS_PUBLICATION` as `superseded_release_disposition`; and
the basis of this release is still the human author's determination, never a
verification. Both the builder and the Handoff generator now fail closed on any
recurrence of the superseded three-provider sentence, and on any new sentence
asserting that TSETMC- or World Bank-derived material is in the release.

rc.3 also made the file counts unambiguous: `release_manifest.json` describes
**25 payload files**, while the archive holds **27 members** — those 25 plus
`release_manifest.json` and `SHA256SUMS.txt`.

### The rights position itself

What changed in rc.2 was **not** that anyone verified CODAL's terms. Nobody did, and
§"What was and was not established" below still says so in full. What changed is
that the **human author supplied a source-rights determination** for the data
used in this study, and that determination — not an agent inference, and not a
provider licence anyone read — is what now governs the candidate's status.

The status this candidate carries is `READY_FOR_EXACT_DIGEST_HUMAN_REVIEW`: a
human is being asked to read the exact archive digest and decide. It is **not**
`PUBLISHED`, it is **not** `PUBLIC_RELEASE_AUTHORIZED`, and it authorizes no
Zenodo action of any kind.

---

## The human author's source-rights determination

**Status: `HUMAN_AUTHOR_DETERMINATION_NO_SEPARATE_PERMISSION_REQUIRED`**

Supplied by the human author, verbatim:

> برای تمام داده‌هایی که در این پژوهش استفاده کرده‌ام نیازی به اخذ مجوز جداگانه
> نیست. این داده‌ها به‌صورت رایگان و عمومی در اینترنت در دسترس‌اند.

Operationally, and as it applies to this release:

0. **Scope.** The determination covers all source data used in the wider study.
   What this release actually distributes is narrower: researcher-compiled
   company financial-statement fields from publicly accessible CODAL
   disclosures, plus author-derived variables and annotations. No TSETMC- and
   no World Bank-derived field is in it. The two facts are separate and neither
   implies the other.
1. All source data used in the study were **publicly and freely accessible**.
2. **No purchased, confidential, personal or human-participant data** were used.
3. The human author determines that **public redistribution of the
   researcher-compiled analysis-ready panel and the author-derived variables
   does not require separate provider permission**.
4. **No original provider PDF, filing document, workbook, raw API response or
   raw provider response is redistributed** — none is in this bundle.
5. **CC BY 4.0 applies only to the authors' own** compilation, structure,
   annotations, derived variables and release metadata, to the extent the
   authors hold rights in them. See `LICENSE_DATASET.txt`.
6. This determination was **supplied by the human author and was not
   independently inferred by the agent** that assembled this release.

### What this determination is not

It is **not** a provider licence, **not** an independent verification of any
provider's published terms, and **not** a legal opinion. No CODAL or TSETMC
terms page was retrieved or read at any point in preparing either release
candidate, and none has been read since — through 1.0.0-rc.3 inclusive. This
file does not assert that CODAL's
terms are open, that they were verified, or that they permit redistribution. It
asserts only what the human author determined, and attributes it to them.

A reuser who needs certainty about the underlying provider materials should
consult the provider directly. A reuser who needs the original filings must
obtain them from the provider under the provider's own terms — this release does
not carry them.

---

## What was and was not established by the environment check

This section is **historical and unchanged**. It records what the 2026-08-21
audit could and could not retrieve, and it is retained exactly because the
determination above did not make any of it go away.

| Provider | Terms pages requested | Outcome | Terms independently retrieved | Terms independently verified |
|---|---|---|---|---|
| CODAL | `https://www.codal.ir/`, `https://www.codal.ir/Rules.aspx` | Connection timeout; no HTTP response | **no** | **no** |
| TSETMC | `https://www.tsetmc.com/`, `https://old.tsetmc.com/`, `https://tsetmc.ir/` | Connection timeout; no HTTP response | **no** | **no** |
| World Bank | `https://datacatalog.worldbank.org/public-licenses` | HTTP 200; retrieved and read | **yes** | **yes** |

CODAL and TSETMC were unreachable from the audit environment. That is a network
condition, not a refusal and not evidence about anyone's terms. This release does
not infer permission from a timeout, and it does not infer prohibition from one
either. What it records is: the pages were not retrieved, so they were not read.

---

## Provider matrix

### 1. CODAL — the Iranian listed-company disclosure system

| Field | Value |
|---|---|
| Canonical public source URL | `https://www.codal.ir/` |
| Operator | Securities and Exchange Organization of Iran (CODAL disclosure system) |
| Type of information used | Annual company financial-statement line items (assets, liabilities, equity, capital, accumulated loss, revenue, profit, operating cash flow, financial expense) and audit-status labels, for listed non-financial companies, fiscal years 1392–1402 |
| Original provider file included in this candidate? | **No.** No PDF, no XLS/XLSX filing, no HTML report, no API payload |
| Only researcher-compiled factual fields included? | **Yes.** Numeric line items keyed to company and fiscal year, plus researcher-derived ratios, flags and eligibility annotations |
| Publicly stated licence or terms | **`NOT_VERIFIED`** — no terms page was retrieved, so none was read |
| Terms independently retrieved / verified | **no / no** |
| Human author determination | Publicly and freely accessible; **no separate permission required** for redistributing the researcher-compiled panel and author-derived variables |
| Release disposition | **SUPERSEDED_BY_HUMAN_AUTHOR_DETERMINATION** (previously `BLOCKS_PUBLICATION` in 1.0.0-rc.1) |

Two provenance columns in the payload reference CODAL:

* `source_file` — the **filename** of the statement workbook a row was
  extracted from. Filenames only; no directory component, no local path, and
  no file content. Present for every row of the primary surface.
* `source_url` — a public CODAL report URL. Populated for a small minority of
  rows only (7 of 1,012 on the primary surface). It is a partial convenience
  pointer, not a provenance guarantee.

### 2. TSETMC — Tehran Securities Exchange Technology Management Co.

| Field | Value |
|---|---|
| Canonical public source URL | `https://www.tsetmc.com/` |
| Type of information used in the wider study | Daily market prices, returns and liquidity, evaluated as a candidate predictor block |
| Type of information used **in this release** | **None** |
| Original provider file included in this candidate? | **No** |
| Only researcher-compiled factual fields included? | **Not applicable — no TSETMC-derived field is in this release** |
| Publicly stated licence or terms | **`NOT_VERIFIED`** — no terms page was retrieved, so none was read |
| Terms independently retrieved / verified | **no / no** |
| Human author determination | Covered by the same determination, but **not material**: nothing from TSETMC is distributed |
| Release disposition | **DOES_NOT_BLOCK.** No TSETMC content to redistribute |

Verified two ways: the committed source registry records
`src_m2_tsetmc_market` as `pending_part3` / not collected, and none of the 115
released columns is a market-data field.

### 3. World Bank — World Development Indicators

| Field | Value |
|---|---|
| Canonical public source URL | `https://datacatalog.worldbank.org/public-licenses` |
| Type of information used in the wider study | Country-level macroeconomic indicators, retrieved for a supplementary exploratory analysis |
| Type of information used **in this release** | **None** |
| Original provider file included in this candidate? | **No** |
| Only researcher-compiled factual fields included? | **Not applicable — no World Bank field is in this release** |
| Publicly stated licence or terms | **Creative Commons Attribution 4.0 International (CC BY 4.0)**, the World Bank's stated default for datasets it produces and distributes as open data — permitting copying, modification and distribution in any format for any purpose including commercial use, subject to attribution and indication of changes |
| Terms independently retrieved / verified | **yes / yes** — `https://datacatalog.worldbank.org/public-licenses`, HTTP 200, 2026-08-21, read directly |
| Human author determination | Covered by the same determination, but **not material**: nothing from the World Bank is distributed |
| Release disposition | **DOES_NOT_BLOCK.** No World Bank content to redistribute |

The raw World Bank retrieval evidence for the supplementary analysis was
deposited separately and openly; it is not part of this bundle and does not
contain the company panel.

---

## The standing conflict with the manuscript

The approved study manuscript, as reviewed and byte-pinned, states that the
company-level source data are *"researcher-verified and frozen; redistribution
is governed by the terms under which they were obtained"*, and describes the
underlying company panel as **not openly redistributable**.

That wording is **unchanged**, and this release did not touch the manuscript.
The conflict between it and the authors' intent to publish this panel openly is
recorded here rather than smoothed over. Reconciling it requires a separate,
separately authorized manuscript edit — and that edit may only happen once a
real DOI exists, because until then the manuscript's present description is the
truthful one.

Nothing was removed from the payload and no frozen value was altered at any
point: `columns_removed_to_avoid_the_blocker = 0` and
`frozen_values_altered_to_avoid_the_blocker = 0` in the decision record, for
1.0.0-rc.1, 1.0.0-rc.2 and 1.0.0-rc.3.

---

## What the CC BY 4.0 grant covers

`LICENSE_DATASET.txt` states the scope. In short: the authors licence **their
own** original compilation, selection, arrangement, derived variables,
annotations, quality-control records and release metadata, to the extent they
hold rights in them.

The grant does **not**:

* relicense CODAL, TSETMC or any other third party's source materials;
* represent that the underlying provider content is free of third-party rights;
* redistribute any original source PDF, filing document or raw provider
  response — none is included;
* purport to grant rights the authors do not hold.

A reuser who needs the original filings must obtain them from the provider
under the provider's own terms.
