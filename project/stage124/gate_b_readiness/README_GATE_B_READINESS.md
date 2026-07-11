# Gate B Readiness — Dry-Run Eligibility Rule Comparison

## Overview

This package contains a **dry-run comparison** of three candidate Gate B
eligibility rules. **No rule has been finalized.** The next action is
`stage124-gate-b-rule-approval` — the user and scientific reviewer must
approve the final rule from the comparison report.

## Date Semantics

All listing master dates have `date_semantics = first_observed_trading_date_from_official_tse_api`.

**These dates are the first observed trading dates from the official TSETMC API. They are NOT IPO dates, admission dates, or listing dates.**

## Input Files

| File | SHA-256 | Status |
|---|---|---|
| `modeling_all_rows_stage123.csv` | `28b9f9d418561718...` | ✅ match |
| `modeling_one_year_ahead_stage123.csv` | `e3d3063e840d61a3...` | ✅ match |
| `stage123_workbook.xlsx` | `3e47d871086f81f0...` | ❌ mismatch |

## Schema Validation

- Overall: ✅ PASS

- ✅ all_rows_count: 1331/1331
- ✅ all_rows_required_columns: all present
- ✅ row_key_unique: duplicates=0
- ✅ unique_tickers: 130/130
- ✅ listing_master_unique_tickers: 130/130
- ✅ all_tickers_matched: all matched
- ✅ no_duplicate_listing_tickers: duplicates=0
- ✅ listing_master_required_columns: all present
- ✅ no_missing_trading_dates: missing=0

## Data Quality Summary

- OK rows: 1321
- Missing fiscal_year_end: 4
- Non-12-month period: 6
- Unmatched ticker: 0

## Rule Comparison

### Rule A — first_observed_trading_date <= fiscal_year_end (end-of-year rule)

| Metric | Value |
|---|---|
| Total company-year rows | 1331 |
| Eligible rows | 1230 |
| Pre-listing rows | 97 |
| Unresolved rows | 4 |
| Affected tickers | 23 |
| Total pairs | 1200 |
| Eligible pairs | 1013 |
| Positive pairs | 81 |
| Negative pairs | 932 |
| Target missing pairs | 0 |
| Change vs Stage123 | -72 |



### Rule B — first_observed_trading_date <= fiscal_year_start (start-of-year strict rule)

| Metric | Value |
|---|---|
| Total company-year rows | 1331 |
| Eligible rows | 1202 |
| Pre-listing rows | 119 |
| Unresolved rows | 10 |
| Affected tickers | 27 |
| Total pairs | 1200 |
| Eligible pairs | 994 |
| Positive pairs | 80 |
| Negative pairs | 914 |
| Target missing pairs | 0 |
| Change vs Stage123 | -91 |



### Rule C — first_observed_trading_year < fiscal_year (year-level conservative rule)

| Metric | Value |
|---|---|
| Total company-year rows | 1331 |
| Eligible rows | 1205 |
| Pre-listing rows | 116 |
| Unresolved rows | 10 |
| Affected tickers | 26 |
| Total pairs | 1200 |
| Eligible pairs | 995 |
| Positive pairs | 80 |
| Negative pairs | 915 |
| Target missing pairs | 0 |
| Change vs Stage123 | -90 |



### Stage123 Baseline

| Metric | Value |
|---|---|
| Eligible pairs | 1085 |
| Positive pairs | 86 |
| Negative pairs | 999 |
| Target missing pairs | 0 |

## Row Differences Between Rules

- Rule A vs Rule B: **29** rows differ
- Rule A vs Rule C: **26** rows differ
- Rule B vs Rule C: **3** rows differ

## Scientific Controls

- No missing value was zeroed.
- No date or year was guessed.
- No row was dropped.
- `fiscal_year_start` is computed only for 12-month periods with valid `fiscal_year_end`.
- Listing master dates are **first observed trading dates** from the official TSETMC API.
- They are **NOT** IPO dates, admission dates, or listing dates.

## Output Files

- `gate_b_rule_comparison_summary.json` — full comparison summary
- `gate_b_company_year_audit.csv` — per-row audit with all rule eligibility
- `gate_b_pair_impact_summary.csv` — per-rule pair statistics
- `gate_b_unmatched_or_ambiguous_rows.csv` — rows with data quality issues
- `gate_b_rule_disagreement_rows.csv` — rows where rules disagree (A/B/C comparison)
- `gate_b_readiness_qc_report.json` — QC report
- `metadata_and_hashes_gate_b_readiness.json` — hashes and metadata
- `README_GATE_B_READINESS.md` — this file

## Next Action

`stage124-gate-b-rule-approval` — User and scientific reviewer must approve
the final Gate B rule from the comparison report.
