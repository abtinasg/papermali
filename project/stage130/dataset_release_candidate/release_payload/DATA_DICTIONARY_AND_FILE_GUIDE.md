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

`part3c_column_role_map_stage125.csv` is authoritative: it names all 115
released columns and gives each exactly one role.

**`data_dictionary_stage125.csv` does not cover all of them, and the release
says so rather than implying otherwise.** It is a Part 1 variable dictionary
written over the *upstream source panel* and its candidate variable blocks, so:

* it holds 38 entries;
* **25** of the 115 released columns appear in it;
* **90** released columns do not;
* 13 of its entries are candidate variables that were never materialized (M2
  market fields, M3 macro fields, M4 governance fields) or upstream keys that
  were renamed when the company-year pair surface was built.

So: use the **role map** to decide what a column is and whether it may be a
feature; use the **dictionary** for the richer prose description of the source
variables it does cover. The gap is recorded in `release_manifest.json` under
`column_documentation_coverage`.

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
predicts the outcome from the outcome. Check the role map before selecting
features; do not select by name pattern.

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

## Verifying what you received

```
sha256sum -c SHA256SUMS.txt
```

`release_manifest.json` additionally records, for every payload file, its byte
size, SHA-256, role, source path within the study repository, and the reason it
is included.
