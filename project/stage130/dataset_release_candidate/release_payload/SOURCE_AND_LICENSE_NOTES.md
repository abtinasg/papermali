# Source use and redistribution audit

This file records, provider by provider, what was used, what is included here,
and what is known about the terms. It is a factual audit. Where a term could
not be verified, this file says so rather than guessing, and no legal
conclusion is drawn that the evidence does not support.

**Audit date: 2026-08-21.**

---

## Overall disposition: NOT_READY_FOR_PUBLICATION

The blocker is CODAL. The panel's financial-statement values are compiled from
CODAL filings, and the authors were **unable to verify CODAL's published terms
of use from the audit environment** (see below). Until a primary CODAL terms
page is retrieved and read, the redistribution question for the compiled
factual fields is **genuinely unresolved**, not resolved-in-favour.

Two further facts weigh on the same question and are recorded here rather than
smoothed over:

1. The study manuscript, as approved, states that the company-level source data
   are *"researcher-verified and frozen; redistribution is governed by the terms
   under which they were obtained"*, and describes the underlying company panel
   as **not openly redistributable**.
2. The authors' stated intent is to publish this analysis-ready dataset openly.

Those two positions are in tension. Publishing this bundle would require
resolving that tension deliberately — by verifying CODAL's terms, and by
updating the manuscript's data-availability statement in a separate authorized
action. Neither has happened. Nothing was quietly removed from the payload and
no frozen value was altered to make the conflict go away.

---

## Provider matrix

### 1. CODAL — Comprehensive Database of All Listed Companies

| Field | Value |
|---|---|
| Canonical public source URL | `https://www.codal.ir/` |
| Operator | Securities and Exchange Organization of Iran (CODAL disclosure system) |
| Type of information used | Annual company financial-statement line items (assets, liabilities, equity, capital, accumulated loss, revenue, profit, operating cash flow, financial expense) and audit-status labels, for listed non-financial companies, fiscal years 1392–1402 |
| Original provider file included in this candidate? | **No.** No PDF, no XLS/XLSX filing, no HTML report, no API payload |
| Only researcher-compiled factual fields included? | **Yes.** Numeric line items keyed to company and fiscal year, plus researcher-derived ratios, flags and eligibility annotations |
| Publicly stated license or terms | **NOT VERIFIED** |
| Date and URL of terms checked | 2026-08-21 — `https://www.codal.ir/` and `https://www.codal.ir/Rules.aspx` were both requested and **did not respond** from the audit environment (connection timeout, no HTTP status). No CODAL terms page was retrieved, so none was read |
| Residual uncertainty | **HIGH.** The terms are unread, not permissive-by-default. Separately, the extent to which factual financial-statement line items attract protectable rights under Iranian law is not something this audit is competent to decide |
| Release disposition | **BLOCKS PUBLICATION.** Prepared and documented; not publishable until a primary CODAL terms page is retrieved and assessed |

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
| Publicly stated license or terms | **NOT VERIFIED** |
| Date and URL of terms checked | 2026-08-21 — `https://www.tsetmc.com/`, `https://old.tsetmc.com/` and `https://tsetmc.ir/` were requested and **did not respond** from the audit environment (connection timeout) |
| Residual uncertainty | **Not material to this release.** The terms are unverified, but no TSETMC value is distributed here |
| Release disposition | **Does not block.** No TSETMC content to redistribute |

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
| Publicly stated license or terms | **Creative Commons Attribution 4.0 International (CC BY 4.0)**, the World Bank's stated default for datasets it produces and distributes as open data — permitting copying, modification and distribution in any format for any purpose including commercial use, subject to attribution and indication of changes |
| Date and URL of terms checked | 2026-08-21 — `https://datacatalog.worldbank.org/public-licenses`, retrieved successfully (HTTP 200) and read |
| Residual uncertainty | **LOW.** The licence is published and was read directly. It is nonetheless not exercised here, since no World Bank value is distributed |
| Release disposition | **Does not block.** No World Bank content to redistribute |

The raw World Bank retrieval evidence for the supplementary analysis was
deposited separately and openly; it is not part of this bundle and does not
contain the company panel.

---

## Why "not verified" is not the same as "not permitted"

CODAL and TSETMC were unreachable from the audit environment — a network
condition, not a refusal and not evidence about their terms. This audit records
what it could and could not establish. It does not infer permission from
silence, and it does not infer prohibition from a timeout. It marks the
question open, which is what it is.

Resolving it requires retrieving a primary CODAL terms page from an environment
that can reach it, and recording the finding here with the same fields.

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
