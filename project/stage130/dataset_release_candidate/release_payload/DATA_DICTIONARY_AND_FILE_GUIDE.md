# Data dictionary and file guide

How to read every file in this bundle, and which committed record documents it.

---

## File-by-file

### `data/` — analysis-ready modeling surfaces

All four are leakage-safe: they contain only rows whose predictor was available
under the prespecified four-Jalali-month rule before the outcome fiscal year
end. All four have the same 115 columns.

| File | Role | Pairs | Companies | Positive | Negative |
|---|---|---|---|---|---|
| `analysis_ready_main_rule_a_stage125.csv` | **PRIMARY** | 1,012 | 119 | 80 | 932 |
| `analysis_ready_main_rule_b_stage125.csv` | Robustness — listing rule | 993 | 117 | 79 | 914 |
| `analysis_ready_expanded_rule_a_stage125.csv` | Robustness — company scope | 1,056 | 124 | 80 | 976 |
| `analysis_ready_expanded_rule_b_stage125.csv` | Robustness — combined | 1,035 | 122 | 79 | 956 |

Counts are read from
`documentation/part3c_leakage_safe_dataset_contract_stage125.json` and
`documentation/part3c_sample_summary_stage125.csv`.

### `audit/` — audit surfaces, NOT all model-ready

Same 115 columns; each is a superset of its analysis-ready counterpart,
retaining the pairs the timing rule excludes.

| File | Audited pairs | Analysis-ready counterpart |
|---|---|---|
| `audited_pairs_main_rule_a_stage125.csv` | 1,013 | 1,012 |
| `audited_pairs_main_rule_b_stage125.csv` | 994 | 993 |
| `audited_pairs_expanded_rule_a_stage125.csv` | 1,057 | 1,056 |
| `audited_pairs_expanded_rule_b_stage125.csv` | 1,036 | 1,035 |

The difference in each row of that table is the timing exclusion. Do not fit a
model on these files.

### `documentation/` — the committed project records

| File | What it gives you |
|---|---|
| `data_dictionary_stage125.csv` | Per-variable block, role, data type, unit, temporal reference, source id, provenance status, description |
| `part3c_column_role_map_stage125.csv` | Per-column role and whether it may enter the model feature matrix |
| `part3c_sample_summary_stage125.csv` | Per-design counts and the frozen output digests |
| `part3c_target_year_distribution_stage125.csv` | Pairs / positives / negatives by target year and surface |
| `part3c_leakage_safe_dataset_contract_stage125.json` | The authoritative contract: availability semantics, the four locked designs, expected counts, explicit non-claims |
| `stage125_part3c_leakage_safe_dataset_qc_report.json` | QC report for the finalization that produced the eight frozen files |
| `source_registry_stage125.csv` | Provider, status and recorded provenance gaps per source block |
| `part4_temporal_split_manifest_stage125.csv` | Prespecified temporal split assignment |
| `target_definition_stage122.csv` | The outcome definition, criterion by criterion, with three-valued missing semantics |

---

## The 115 columns

### Start here: `RELEASE_COLUMN_DICTIONARY.csv`

**One row for each of the 115 released columns. No gaps, no duplicates.** This
is the file to open when you want to know what a column is.

| Field | What it gives you |
|---|---|
| `column_name` | The column, exactly as it appears in the CSV header |
| `definition` | What the column is, in a sentence |
| `data_type` | `numeric`, `integer`, `string`, `categorical`, `boolean_0_1`, `boolean_true_false`, `three_valued_1_0_missing`, `date_jalali_iso`, `date_gregorian_iso` |
| `unit` | `million_IRR`, `ratio`, `binary_0_1`, `jalali_year`, a date format, or `not_applicable` |
| `column_role` | The role from the authoritative role map |
| `model_eligibility` | Whether it may ever be a feature — read this before selecting |
| `source_block` | Which panel or construction stage the column comes from |
| `source_provider_or_author_derived` | Provider line item, author-compiled ratio, author-derived rule output, or an assigned key |
| `temporal_reference` | Which period the value describes: predictor year *t*, outcome year *t+1*, a period end, or a constant |
| `missing_value_semantics` | What a missing or empty value means for **this** column |
| `derivation_or_formula` | The committed formula, or the copy rule |
| `authoritative_source_path` | The repository file the facts were transcribed from |
| `authoritative_source_field_or_section` | The row, key or code section inside that file |
| `definition_status` | `committed_dictionary`, `committed_contract`, `committed_target_definition`, or `frozen_generator_code` |
| `limitations` | What this specific column cannot support |

Nothing in it was invented. Every row is anchored to a committed artifact and
the build refuses to ship a row it cannot anchor — an undefined column is
reported by name rather than filled with a plausible sentence.

### How it relates to the two historical artifacts

Three files describe columns, and they are not interchangeable:

| File | What it is | Coverage of the 115 |
|---|---|---|
| `RELEASE_COLUMN_DICTIONARY.csv` | **This release's** dictionary, built for publication | **115 / 115** |
| `documentation/part3c_column_role_map_stage125.csv` | The **authoritative column set and role contract**, committed at Stage125 | 115 / 115 — names and roles only, no definitions |
| `documentation/data_dictionary_stage125.csv` | The historical **Part 1 dictionary over the upstream panel** | 25 / 115 |

The role map stays authoritative for *which* columns exist and *what role* each
has; the release dictionary is gated at build time to match it exactly, so the
two can never drift apart. The Stage125 dictionary ships unedited as history: it
holds 38 entries, 25 of which correspond to released columns, and 13 of which
describe candidate variables that were never materialized (M2 market fields, M3
macro fields, M4 governance fields) or upstream keys renamed when the
company-year pair surface was built. That shortfall is a fact about a committed
historical artifact, and it is published in `release_manifest.json` under
`upstream_dictionary_coverage` rather than quietly corrected.

Every column carries exactly one role:

| Role | Count | Meaning |
|---|---|---|
| `sample_eligibility_audit` | 37 | Why a row is in or out of a given design |
| `predictor_candidate` | 31 | Eligible to be considered as a feature |
| `forbidden_from_model_matrix` | 14 | **Never** a feature — target-derived or otherwise leaking |
| `identifier` | 10 | Keys and labels |
| `timing_assumption` | 10 | The availability-rule fields |
| `provenance_audit` | 5 | Where the row came from |
| `timing_eligibility_audit` | 5 | Timing-rule outcome per row |
| `target` | 3 | Outcome variables |
| **Total** | **115** | |

**The 14 `forbidden_from_model_matrix` columns are the important ones.** They
include the target-derived fields. Using one as a feature produces a model that
predicts the outcome from the outcome. Filter on `model_eligibility` in
`RELEASE_COLUMN_DICTIONARY.csv`, or on `role` in the role map; do not select by
name pattern.

### Key column groups

**Identity and period**
`ticker`, `company_name`, `industry`, `fiscal_year_t`, `target_year`,
`predictor_row_key_t`, `target_row_key_t_plus_1`, `row_key_predictor`,
`sample_design`, `unit`.

**Raw statement line items** (fiscal year *t*, period-adjusted where marked)
`total_assets`, `total_liabilities`, `equity`, `registered_capital`,
`accumulated_loss`, `current_assets`, `current_liabilities`,
`revenue_period_adjusted`, `gross_profit_period_adjusted`,
`operating_profit_period_adjusted`, `net_income_period_adjusted`,
`operating_cash_flow_period_adjusted`, `financial_expense_period_adjusted`.

**Derived ratios**
`leverage_ratio`, `current_ratio`, `equity_ratio`, `roa_period_adjusted`,
`roe_period_adjusted`, `ocf_to_assets_period_adjusted`,
`financial_expense_to_assets_period_adjusted`, the margin family, the growth
family, `asset_turnover_period_adjusted`, `accumulated_loss_to_capital_ratio`,
`debt_to_equity`.

**Outcomes (t+1)**
`FD_target_main_t_plus_1` — the primary outcome.
`FD_target_article141_only_t_plus_1` and
`FD_target_persistent_loss_robustness_t_plus_1` — robustness definitions.
Their un-suffixed counterparts describe year *t* and are
`forbidden_from_model_matrix`.

**Timing assumption — read `README.md` §"availability date"**
`assumed_available_at_regulatory_jalali` / `_gregorian`,
`regulatory_lag_months` (= 4), `availability_method`
(= `fixed_regulatory_lag`), `availability_date_semantics`,
`is_observed_publication_timestamp` (= false),
`fiscal_year_end_t_jalali` / `_gregorian`,
`target_fiscal_year_end_t_plus_1_jalali` / `_gregorian`.

**Timing eligibility**
`assumed_before_target_fiscal_year_end`, `timing_relation_violation`,
`timing_eligible_for_analysis`, `timing_eligible_for_model`,
`timing_exclusion_reason`.

**Provenance**
`source_file` — statement workbook **filename** only (no path, no content).
`source_url` — public CODAL report URL, populated for a small minority of rows.

**Eligibility audit**
The `eligible_*`, `pair_final_eligible_*`, `predictor_eligible_*`,
`*_exclusion_reason_*` families record, per row and per design, exactly which
rule admitted or excluded it.

---

## Dates and calendars

Jalali is the primary calendar. Fields ending `_jalali` are Jalali; fields
ending `_gregorian` are the converted equivalent. Fiscal years are Jalali years
1392–1402. The four-month availability lag is counted in **Jalali** months.

## Missing values

Missing is missing. Unknown outcomes are preserved as unknown and never
converted to a negative. No imputation and no scaling has been applied to the
released values — the contract records `no_imputation_or_scaling` among its
explicit non-claims.

What a blank means differs by column, and that is why every row of
`RELEASE_COLUMN_DICTIONARY.csv` carries its own `missing_value_semantics`. In
the reason-string columns an empty value means *there was no reason to record*,
not *the reason is unknown*; in the outcome and criterion columns a blank is a
genuine three-valued unknown; in the provenance columns it is a recorded gap.
Do not treat the three the same way.

## Verifying what you received

```
sha256sum -c SHA256SUMS.txt
```

`release_manifest.json` additionally records, for each of the **25 payload
files**, its byte size, SHA-256, role, source path within the study repository,
and the reason it is included.

**Two counts, and they are not the same count.** `release_manifest.json`
describes **25 payload files**. The archive contains **27 members**: those 25
plus `release_manifest.json` and `SHA256SUMS.txt`. The last two are integrity
records *about* the payload, so they are not themselves manifest payload files —
the manifest deliberately excludes both, and `SHA256SUMS.txt` covers the payload
and the manifest but never hashes itself. That is why the checksum file carries
**26 lines**, not 27.

## What the released columns are compiled from

Every released value is either a researcher-compiled company
financial-statement field transcribed from a publicly accessible CODAL
disclosure, or a variable or annotation the authors derived from those fields.
**No TSETMC-derived and no World Bank-derived field is included in this
release**; those sources relate only to the wider study. Each row of
`RELEASE_COLUMN_DICTIONARY.csv` states, per column, whether the value came from
a provider line item or was author-derived.
