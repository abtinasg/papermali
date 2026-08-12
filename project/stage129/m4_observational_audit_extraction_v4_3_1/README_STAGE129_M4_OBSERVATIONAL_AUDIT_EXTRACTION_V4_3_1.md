# Stage129 — M4 observational audit-field extraction (V4.3.1), custody package

**Action id:** `stage129-m4-observational-audit-extraction-v4-3-1-custody`
**Action type:** evidence custody only — zero Gate execution, zero feature
materialization, zero modeling, zero Final Test access.

> ## Package status
>
> ```
> OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT
> ```
>
> This package is **not** an M4 input. It does not resolve any of the three
> prerequisites recorded as `CONTRACT_ISSUE_UNRESOLVED` by
> `stage129-m4-governance-data-gate-contract-lock`, and it does not make the M4
> Data Gate executable for any candidate.

---

## 1. Purpose

A local archive of Iranian statutory financial-statement workbooks (fiscal years
۱۳۹۲–۱۴۰۲) was scanned to observe, per `ticker|fiscal_year`, three fields of the
independent auditor's report: fiscal year end, auditor opinion category, and
auditor report date.

This package preserves the **result and its evidence** in repository custody so a
supervisor can audit it. It is a recording action, not a scientific advance.

### What this package explicitly does NOT claim

| Claim | Status |
|---|---|
| The `audit_opinion_type` taxonomy is resolved | **No** — still `CONTRACT_ISSUE_UNRESOLVED` |
| Free-text extraction is the Stage125 *structured field* | **No** — see §6 |
| `audit_opinion_type` is admitted to M4 | **No** |
| `audit_lag_days` is now computable | **No** — never computed; no such column exists |
| `going_concern_flag` was derived | **No** — never derived from text |
| The CODAL identity prerequisite is resolved | **No** |
| The M4 contract is complete or executable | **No** |
| The M4 Data Gate is open or was executed | **No** |

All Stage129 M4 governance markers are unchanged by this action:
`m4_contract_complete=false`, `m4_contract_fully_executable=false`,
`m4_data_gate_executable=false`, `m4_data_gate_authorized=false`,
`m4_candidates_the_gate_may_execute_for=[]`, Final Test locked with
`rows_read=0`.

---

## 2. Canonical population

| Item | Value |
|---|---|
| File | `project/stage124/gate_b_final/modeling_all_rows_stage124_gate_b.csv` |
| SHA-256 | `f6b6bc41cbe757d19d4397ffc5898629d0fca8ab0480351f75040a71d7ce7376` |
| Rows | **1331** |
| Tickers | **130** |
| Primary key | `ticker\|fiscal_year` (unique) |
| Hash scope | committed repository artifact |

The canonical population was opened **read-only**. It was not rewritten,
re-derived or filtered by this action.

---

## 3. Source archive identity and custody

| Item | Value |
|---|---|
| Logical name | `اکسل های صورت مالی کل زیپ ۱۳۹۲-۱۴۰۲.zip` |
| Location | `LOCAL_SOURCE_ARCHIVE_NOT_REPOSITORY_RETAINED` |
| SHA-256 | `f33ee950ffdd7042f6fe60f411e2d81b8cbe38b51ec84d30c2e224de1a1c6bb2` |
| Bytes | 34,909,380 |
| Integrity | `unzip -t` clean |
| Nested ZIPs | 128 |
| Payload files | 1628 (792 OLE2, 836 HTML-mislabeled) |
| Hash scope | **observed external local source** |

> **The raw archive is NOT in repository custody.** Neither the 34.9 MB archive
> nor any of the 1628 raw payloads is committed. Only fingerprints are retained:
> per-payload SHA-256 values live in `archive_file_inventory.csv`.
>
> Consequently this package is **verifiable but not re-derivable** from the
> repository alone. Re-running `scripts/` reproduces the committed artefacts only
> if the same archive — matching the SHA-256 above — is supplied locally. **No
> byte-for-byte reproducibility claim about the raw source is made here.**

Every hash in this package is labelled by scope, either
`observed_external_local_source_not_repository_retained` or
`committed_repository_artifact`, in
`metadata_and_hashes_stage129_m4_observational_audit_extraction_v4_3_1.json`.

---

## 4. Coverage of the 1331 canonical rows

| Coverage status | Rows |
|---|---|
| `MATCHED_SEPARATE_VALID` | **828** |
| `MATCHED_SEPARATE_CORRECTION_SELECTED` (valid اصلاحیه) | **74** |
| `MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED` | **1** |
| `ONLY_CONSOLIDATED_AVAILABLE` | **368** |
| `NO_ARCHIVE_MATCH` | **60** |
| **Total** | **1331** |

No consolidated statement was ever used as a separate statement, and no
unaudited payload was used.

## 5. Extraction outcome

| Field | Rows |
|---|---|
| `fiscal_year_end` | **889** |
| Verified `auditor_opinion_type` | **444** |
| — مشروط (qualified) | **224** |
| — مقبول (unqualified) | **220** |
| — عدم اظهارنظر (disclaimer) | **0 in canonical** |
| — مردود (adverse) | **0** |
| `auditor_report_date` | **446** |
| Field-level missing | **2214** |

Reconciliation: `828 + 74 + 1 + 368 + 60 = 1331`, and
`1331 × 3 − (889 + 444 + 446) = 2214`.

Extraction status: 444 `EXTRACTED_FULL`, 445 `EXTRACTED_PARTIAL`,
14 `UNVERIFIED` (a source exists but no field was provable),
428 `NO_VALID_SEPARATE_SOURCE`.

### Where the data actually lives

All **836** HTML-mislabeled payloads contain **no auditor report at all** — they
are newer CODAL statement-only exports. Every opinion and report date comes from
the **792** OLE2 payloads, in each of which a single auditor-report block was
located and recorded with an explicit `sheet` / `start` / `end` range.

---

## 6. The 65 structured-field payloads — and why they change nothing

65 payloads use an older layout that records the opinion as a genuine
**structured field** with a closed vocabulary (`موضوع گزارش:` / `مخاطب گزارش:` /
`نظر حسابرس :`), yielding 46 `مشروط` and 19 `تعدیل نشده(مقبول)`.

**Every one of these 65 files is fiscal year ۱۳۸۰–۱۳۹۰, entirely outside the
canonical ۱۳۹۲–۱۴۰۲ window.** Their contribution to the 1331 rows is **zero**,
and all 444 canonical opinions are free-text derived (`…|HEADING_CELL`), not
structured-field derived. This is asserted by a regression test.

This matters for the Stage129 contract: the frozen Stage125 definition of
`audit_opinion_type` requires *an explicit structured field, not free-text
inference*. The structured field that would satisfy that definition **exists in
this archive only for years the study does not use**. That is recorded here as an
observation. It is **not** a resolution of the taxonomy prerequisite, and it does
not admit anything to M4.

---

## 7. Corrections and the named regression cases

### 7.1 `فنورد|1400` — an اصلاحیه that destroyed data

The correction payload is 2,908 bytes and contains no `<table>` at all (0 content
cells). The previous run (V4.3) selected it purely because it was labelled
اصلاحیه, and lost the original's data.

V4.3.1 gates correction selection on a **proven-substantive payload**. This one
fails the gate, so the healthy original is retained:
`CORRECTION_PAYLOAD_INVALID_OR_NON_SUBSTANTIVE_ORIGINAL_RETAINED`, recovering
`fiscal_year_end = 1400/12/29`. This is the single row in that coverage status.

### 7.2 `سخوز|1392` — an اصلاحیه that defers the opinion

The correction is substantive (55,808 bytes, 547 cells) and **is** selected, but
every paragraph of its auditor block is a referral:
«گزارش حسابرس و بازرس قانونی به پیوست ارائه شده است».

Its opinion is therefore recorded as `UNVERIFIED` with reason
`REFERRAL_TO_ATTACHMENT`. The original's `مشروط` is **deliberately not carried
over** — no value is ever merged across two documents, so every field of a row
has exactly one source. The non-transferred value is disclosed in
`correction_selection_audit_v4_3_1.csv`.

### 7.3 `خوساز|1396` and six false disclaimers

CODAL forms sometimes leave a template label `مبانی عدم اظهارنظر` ("basis for
disclaimer") inside a report whose **actual** opinion heading is
`اظهار نظر مشروط`. V4.3 ranked candidates by a fixed category weight
(`عدم اظهارنظر = 3 > مشروط = 2`) and let the template label win.

Ten payloads across the archive carry such a label. In **nine** it is purely a
template artefact and the real heading is `اظهار نظر مشروط`, corroborated by a
fair-presentation-with-exception paragraph.

**All six rows V4.3 reported as `عدم اظهارنظر` were wrong; all six are `مشروط`.**

The V4.3.1 rule is: **the paragraph decides the category, the heading only
corroborates**, and a `مبانی …` label is never accepted as an opinion.

### 7.4 The only genuine disclaimer is outside the canonical population

`بکاب|1392` is the one payload with a non-basis `عدم اظهار نظر` heading and a
real disclaimer conclusion («…اظهارنظر نسبت به صورتهای مالی یاد شده در بالا،
امکانپذیر نیست»). **بکاب's canonical rows begin at ۱۳۹۳**, so this row is not in
the 1331. That is why the canonical disclaimer count is 0 — an absence of
eligible rows, not a loss of data. Its full evidence is preserved in
`pilot_evidence/13_disclaimer_in_archive_outside_canonical_بکاب__1392.txt`.

---

## 8. Limitations

1. **Not repository-reproducible.** The source archive is external; see §3.
2. **Free-text, not structured field.** The 444 canonical opinions are read from
   report prose. They do not satisfy the frozen Stage125 structured-field
   definition (§6).
3. **Taxonomy still unresolved.** The four observed labels are the categories the
   documents use. They are **not** an authoritative taxonomy and were not derived
   from one; empirical category discovery remains forbidden.
4. **Calendar unresolved.** Dates are validated for syntax and hard bounds only
   (`all_dates_pass_syntactic_jalali_bounds`). No calendar-validity claim is
   made; 29 vs 30 Esfand in leap years is untouched. No `audit_lag_days`.
5. **Identity unresolved.** Rows are joined on the archive filename's ticker and
   fiscal year against the canonical key. This is **not** the audited CODAL-to-
   parent identity mapping the Gate requires.
6. **Coverage is low by design of the source.** 368 rows have only consolidated
   statements and 60 have no archive match; 887 rows have no verifiable opinion.
7. **14 rows** have a selected source but no provable field at all.
8. **Point-in-time availability is unaddressed.** A report's internal date is not
   its availability date; the Stage125 `available_at` rule is untouched here.

---

## 9. Reproduction and verification

```bash
# verify the committed package against its own manifest
python - <<'PY'
import json,hashlib,os
P='project/stage129/m4_observational_audit_extraction_v4_3_1'
m=json.load(open(os.path.join(P,'metadata_and_hashes_stage129_m4_observational_audit_extraction_v4_3_1.json')))
bad=[f for f,v in m['package_files'].items()
     if hashlib.sha256(open(os.path.join(P,f),'rb').read()).hexdigest()!=v['sha256']]
print('mismatches:',bad)
PY
```

```bash
python -m pytest project/tests/test_stage129_m4_observational_audit_extraction_v4_3_1.py -q
```

`scripts/` contains the full extraction pipeline and `tests/` the semantic
negative-control tests (they assert the extractor *refuses* referral stubs,
negated phrases, another firm's quoted report, boilerplate, out-of-block dates
and heading/paragraph contradictions). Re-running `scripts/` end-to-end
additionally requires the external archive.

---

## 10. Next action

**`human_scientific_decision_required`** — a supervisor must decide whether an
observational, free-text, non-structured extraction has any role in this study.

This package **is not** an authorization to run the M4 Data Gate, to admit
`audit_opinion_type`, to compute `audit_lag_days`, or to start modeling. A
pointer is never an authorization.
