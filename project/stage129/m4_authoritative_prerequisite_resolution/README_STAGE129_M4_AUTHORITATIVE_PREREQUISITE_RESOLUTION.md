# Stage129 — M4 authoritative prerequisite resolution (DOCUMENTARY RESEARCH ONLY)

This package records a bounded attempt to resolve the **three unresolved
prerequisites** that the locked Stage129 M4 contract
([`stage129_m4_data_gate_contract.json`](../m4_governance_data_gate_contract/stage129_m4_data_gate_contract.json))
records as `CONTRACT_ISSUE_UNRESOLVED`, and which currently make the M4
Data Gate non-executable for **every** candidate.

It is documentary research. It retrieves **zero** M4 candidate observations,
calculates **zero** coverage, executes **zero** Gates, fits **zero** models and
reads **zero** Final Test rows. It authorizes nothing downstream.

## Overall outcome

> **`DOCUMENTARY_RESEARCH_BLOCKED`** — 0 of 3 prerequisites resolved.

| # | Prerequisite | Verdict |
| --- | --- | --- |
| A | `codal_to_parent_company_identity_resolution` | `BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION` |
| B | `audit_opinion_type_taxonomy` | `BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION` |
| C | `audit_lag_days_calendar_conversion` | `BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION` |

All three questions terminate at authoritative sources that could not be
reached from this execution environment. Real research was performed and real
findings were obtained (below), but **no prerequisite was closed**, so the
contract state is unchanged: `m4_data_gate_executable = false`,
`m4_candidates_the_gate_may_execute_for = []`.

## The access limitation, stated precisely

Every Iranian host consulted resolves to an address inside `198.18.0.0/15` —
the RFC 2544 benchmarking range — which means DNS is intercepted by the
execution sandbox. Reachability therefore reflects a **sandbox proxy
allowlist**, not public availability of these sites.

| Host | Resolved IP | Result |
| --- | --- | --- |
| `www.codal.ir` | `198.18.0.35` | connection timed out |
| `www.tsetmc.com` | `198.18.0.37` | connection timed out |
| `audit.org.ir` | `198.18.0.31` | connection timed out (all variants, incl. the standards path) |
| `www.seo.ir` | — | connection timed out |
| `www.iacpa.ir` | `198.18.0.39` | **HTTP 200 — reachable** |
| `www.ifac.org` | `198.18.0.40` | **HTTP 200 — reachable** |
| `github.com` | `198.18.0.41` | **HTTP 200 — reachable** (control) |

Because control hosts return 200, the failures are **host-specific, not a loss
of network egress**.

> **This is an access limitation of this environment. It is explicitly NOT a
> finding that CODAL, the Audit Organization or TSETMC lack the documentation
> in question.** Absence of evidence is not evidence of absence.

## A — CODAL → parent-company identity

**Question.** Is there an authoritative, deterministic, auditable mapping from
a CODAL issuer/disclosure identity to the frozen parent-side key `ticker`
(with `fiscal_year_t`)?

**Result.** Not established. The three authoritative routes — CODAL's own
public metadata, TSETMC issuer records, and the Securities and Exchange
Organization — were all unreachable. No identifier field name was confirmed,
so none of the required specification could be written: no normalization rules,
no Unicode / Persian–Arabic character policy, no ZWNJ (نیم‌فاصله) or whitespace
policy, no ticker-change policy, no collision policy, and no verifiable
one-to-one guarantee.

No fuzzy matching, name matching, manual best-guess matching or
outcome-informed matching was performed, and no fallback mapping was
substituted — all four are forbidden by the frozen contract and none was used.

This prerequisite blocks **all four** candidates, because every M4 candidate
value is CODAL-sourced.

## B — `audit_opinion_type` taxonomy

**Question.** What is the exact authoritative allowed-category taxonomy for the
structured `audit_opinion_type` field?

**What was obtained.** ISA 705 (Revised) was read as primary text during the
original authorized documentary session. Its bytes were hashed at that time
(observed SHA-256 `3517bbe5…`, observed 173,296 bytes, 25 pages) but are **not
in repository custody** — see [Documentary custody](#documentary-custody)
below. Paragraph 2 states verbatim:

> "This ISA establishes three types of modified opinions, namely, a qualified
> opinion, an adverse opinion, and a disclaimer of opinion."

Effective for audits of financial statements for periods ending on or after
15 December 2016. With ISA 700 (Revised)'s unmodified opinion, that is a
four-category structure.

**Why that is still not enough.** The frozen Stage125 definition requires the
label to be *an explicit structured field/value on the official CODAL report,
never inferred from free text*. ISA 705 is authoritative for the international
standard but establishes **none** of the following:

- that the Iranian Audit Organization adopted this taxonomy verbatim — its
  codified-standards portal (`audit.org.ir`) was unreachable;
- that CODAL exposes a **structured** audit-opinion field at all;
- the exact machine-readable category identifiers CODAL would use;
- the Persian-term → category mapping as CODAL encodes it.

IACPA (`iacpa.ir`) *was* reachable, but publishes no taxonomy itself — it links
out to `audit.org.ir`, which is unreachable. So both named authoritative routes
in the frozen contract remain unopened.

The provisional four Persian categories recorded in the Stage129 contract
therefore remain **unverified and unfrozen**. No taxonomy was derived from
observed report frequencies or keywords.

## C — `audit_lag_days` calendar conversion

**Question.** Is there an authoritative deterministic convention for
`audit_lag_days = audit_report_date − fiscal_year_end`, including each field's
documented calendar and format, plus an authoritative Jalali/Gregorian
conversion rule if conversion is required?

**Result.** Not established. CODAL's date-field format documentation was
unreachable, so neither field's calendar nor format is documented here, and it
is not even established that both dates use the same calendar. Inclusive vs.
exclusive day-count convention is likewise undocumented.

**Two substantive secondary findings were obtained, and both cut against
freezing a rule now:**

1. **Available supporting evidence describes the official Iranian civil
   calendar as astronomically determined** — the year beginning at the midnight
   nearest the vernal equinox observed at the Iranian reference meridian —
   **rather than governed by a closed-form arithmetic rule** such as the
   repository library's fixed 33-year cycle. So no arithmetic library can be
   *assumed* to reproduce the official civil calendar without being checked
   against officially published dates.

   > **Qualification.** This rests on **secondary** reference material, not on
   > an Iranian legal or standards text — that text was not retrieved. It is
   > enough to show the library approximation cannot simply be assumed correct,
   > and therefore to keep this prerequisite blocked. It is **not** offered as
   > independently resolved authoritative evidence, and it establishes no
   > specific divergence in any specific year.

2. **The repository's pinned library is an approximation with no standards
   authority.** `jdatetime==6.0.1` implements:

   ```python
   def isleap(self) -> bool:
       """check if year is leap year
       algortim is based on http://en.wikipedia.org/wiki/Leap_year"""
       return self.year % 33 in (1, 5, 9, 13, 17, 22, 26, 30)
   ```

   That is a fixed **33-year arithmetic cycle**, and the only authority its own
   source cites is **Wikipedia**. A round-trip check over 7,304 consecutive
   Jalali dates (1385-01-01 … 1404-12-28) produced 0 mismatches — but that
   establishes only that the library is *internally invertible under its own
   approximation*. It is **not** offered as validation against the official
   calendar, and it is not an authoritative source.

The Stage128 `jalali_fiscal_year_t_plus_621` rule remains forbidden here: it is
a year-level macro-data mapping, not a day-level date conversion.

## Documentary custody

**This package places zero documentary objects into repository custody.**

One document — ISA 705 (Revised) — was downloaded and locally hashed inside the
original authorized documentary session. Its bytes are **deliberately not
committed**, because the document's own notice states verbatim:

> "Copyright © January 2015 by the IFAC®. All rights reserved. Written
> permission from IFAC® is required to reproduce, store or transmit, or to make
> other similar uses of, this document, except as permitted by law. Contact
> permissions@ifac.org." (ISBN 978-1-60815-205-6)

This repository is **public**, so committing the PDF would reproduce, store and
transmit it publicly. No such written permission exists. The document was
therefore **not** re-downloaded, **not** reconstructed, and **not** substituted
with a different copy.

Consequently:

- `documentary_documents_in_repository_custody = 0`
- every byte count and SHA-256 in this package is **historical execution
  metadata** observed at retrieval time — **none of them hashes a file
  committed by this action**;
- the package hash manifest covers only this package's own JSON/README
  artifacts, and never claimed otherwise;
- **independent byte-level reproduction of ISA 705 requires a separately
  authorized future retrieval.** The recorded hash cannot be verified against
  anything inside this repository.

Where byte count, media type or hash was not captured during the original
session (for example the IACPA page, read through a summarising fetch layer),
the field is recorded as `null` with an explicit capture note. Nothing was
estimated, reconstructed or fabricated, and no source was contacted again
during this correction.

## What this action did NOT do

Zero successful CODAL requests, zero CODAL filings retrieved, zero M4 candidate
observations read, zero company rows loaded, zero audit-opinion / going-concern
/ audit-date / board-size values read, zero coverage calculations, zero Gate
executions, zero block admissions, zero model fits, zero predictions, zero Holm
calculations, zero Final Test rows read. See
[`stage129_m4_prerequisite_resolution_execution_audit.json`](stage129_m4_prerequisite_resolution_execution_audit.json).

Network access **was** performed, but strictly documentary: reachability probes
and standards-document fetches. No company-year record was ever requested.

## Scientific state after this action (unchanged)

`m4_contract_complete=false`, `m4_contract_fully_executable=false`,
`m4_data_gate_executable=false`, `m4_data_gate_authorized=false`,
`m4_candidates_the_gate_may_execute_for=[]`, retrieval not started,
observations read `=0`, coverage not calculated, Gate not executed, block not
admitted, modeling not started, incremental evaluation not authorized, Final
Test locked with `rows_read=0`, no paper winner, no final model, no
full-development refit. Candidate identities
(`audit_opinion_type`, `going_concern_flag`, `audit_lag_days`, `board_size`),
all four thresholds, and the confirmatory Holm family
(`M2_minus_M1`, `M3_CBI_minus_M2`, `M4_minus_M3_CBI`) are unchanged and the
Holm family is unexecuted. M3-CBI stays `UNRESOLVED_M3_DATA_GATE`; M3-LAG-WDI
stays `SUPPLEMENTARY_EXPLORATORY_ONLY`.

The Stage129 pointer `stage129-m4-governance-data-gate` remains
`authorized = false`. **A pointer is never an authorization.**

## What would actually unblock this

Each item below needs its own separate human authorization; none is started
here.

1. **Network access** to `codal.ir`, `audit.org.ir` and `tsetmc.com` from an
   environment permitted to reach them — this is the single gating constraint
   for all three prerequisites.
2. **A** — an authoritative CODAL issuer-identifier schema, then a separately
   audited deterministic identity-mapping artifact with its own uniqueness and
   ambiguity audit.
3. **B** — the Iranian Audit Organization codified standard text and/or a CODAL
   structured-field schema giving exact category identifiers.
4. **C** — CODAL date-field format documentation, plus a conversion rule
   validated against officially published Iranian calendar dates rather than
   assumed from a library.

## Files

- `stage129_m4_prerequisite_resolution_decision.json` — the three verdicts,
  the overall outcome, and the exact unchanged post-action contract state.
- `stage129_m4_prerequisite_resolution_source_evidence.json` — per-source
  manifest: authority, URL, timestamp, resolved IP, status, bytes, SHA-256,
  what each source establishes and what it does **not** establish.
- `stage129_m4_prerequisite_resolution_execution_audit.json` — all execution
  counters.
- `stage129_m4_prerequisite_resolution_governance_boundary.json` — explicit
  non-authorization / non-drift assertions.
- `metadata_and_hashes_stage129_m4_authoritative_prerequisite_resolution.json`
  — hash manifest for this package.
- Tests: `project/tests/test_stage129_m4_authoritative_prerequisite_resolution.py`.
