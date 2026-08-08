# Stage128 — Track B step E: the M3-LAG-WDI EXPLORATORY INCREMENTAL EVALUATION

**Action:** `stage128-m3-lag-wdi-exploratory-incremental-evaluation`
**Authorized scope:** `exploratory_incremental_evaluation_only`
**Comparison:** `M3_LAG_WDI_minus_retained_M2` (hypothesis `E1`)
**Family:** `M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY`
**Results label:** `supplementary_exploratory_robustness_only`
**E1 conclusion:** `E1_NULL_NO_DETECTABLE_INCREMENTAL_CONTRIBUTION`

## What this action is

The one authorized execution of the pre-frozen step-E modeling contract. It
materialized the M3-LAG-WDI modeling feature-value table for the first time
(step D deliberately produced row STATUSES only, because feature values are
not invariant to the calendar convention that was unlocked at the time),
refit the retained M2 comparator and the 14-feature M3-LAG-WDI block on the
IDENTICAL development sample, and computed the paired exploratory comparison.

**It made no new scientific design choice.** Every rule it applied — the
calendar mapping, the two features, the complete-case policy, the three model
configurations, the validation windows, the metric definitions, the seed
policy and the bootstrap machinery — was frozen before it ran, and is re-read
from committed bytes at run time so drift fails closed.

## The sample

| Quantity | Value |
| --- | --- |
| Rows | 539 |
| Positives / negatives | 55 / 484 |
| Companies | 108 |
| Event rate | 0.102041 |
| Pooled out-of-fold rows | 366 |
| Pooled out-of-fold positives | 28 |
| Validation positives | fold1 18, fold2 10 |
| Attrition from the step D admitted sample | 0 |
| Final Test rows | 0 |

Both blocks were evaluated on exactly these rows. The retained M2 comparator
was **refit** here, never imported: the previously published M1 666-row
results were not used as the comparator. Because both WDI features are
constructible for all 539 rows, the frozen complete-case rule removed
nothing, so the step-E sample is mechanically the retained-M2 sample — and
the refit M2 reproduces the committed retained-M2 metrics exactly
(45 values compared,
0 mismatches).

## The features

Calendar mapping: `predictor_year_t = jalali_fiscal_year_t + 621` (locked; offset
621, rejected offset 622).

* `intl_cpi_inflation_lag1_wdi` — `FP.CPI.TOTL.ZG`, observation year **t-1**, identity.
* `intl_fx_change_official_lag1_wdi` — `PA.NUS.FCRF`,
  `FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))`, observation years **t-1** and
  **t-2**.

No same-year `t` observation was read (0).
Comparator = **12** features; exploratory block =
**14** features. No third macro feature, no
feature search, no selection, no substitution, no imputation.

Both are NATIONAL annual series, so within a predictor year every company
carries the same value:

| Predictor year | Rows | CPI lag1 | FX change lag1 |
| --- | --- | --- | --- |
| 2013 | 40 | 27.256813 | 13.703843 |
| 2014 | 67 | 36.603036 | 41.370596 |
| 2015 | 66 | 16.606553 | 34.271476 |
| 2016 | 79 | 12.484682 | 11.184168 |
| 2017 | 80 | 7.245425 | 6.354472 |
| 2018 | 100 | 8.044924 | 7.210495 |
| 2019 | 107 | 18.014118 | 20.691586 |

## Result — exploratory, supplementary

Primary metric `pr_auc`, pooled out-of-fold, paired
paired_company_cluster_bootstrap on `ticker`
(2000 replicates, seed 20260724,
percentile intervals at 0.95):

| Family | retained M2 | M3-LAG-WDI | delta | 95% CI | Direction |
| --- | --- | --- | --- | --- | --- |
| `regularized_logistic_regression` | 0.486028 | 0.486890 | +0.000862 | [-0.028237, +0.032186] | `approximately_null_interval_includes_zero` |
| `random_forest` | 0.348246 | 0.345526 | -0.002720 | [-0.029157, +0.011924] | `approximately_null_interval_includes_zero` |
| `xgboost` | 0.374564 | 0.377313 | +0.002749 | [-0.007437, +0.014554] | `approximately_null_interval_includes_zero` |

Adding the two lagged WDI macro features to the retained M2 block produced no detectable change in out-of-fold DISCRIMINATION on the identical 539-row development sample. In every one of the three frozen model families the paired pr_auc difference is small and its 95% paired company-cluster bootstrap interval includes zero. This conclusion is about the PRIMARY metric. It is not a claim that nothing moved anywhere: regularized_logistic_regression brier_score -0.004600 [-0.006147, -0.003066] favouring M3_LAG_WDI; random_forest brier_score -0.001375 [-0.002229, -0.000566] favouring M3_LAG_WDI. Brier score measures CALIBRATION, not ranking, so a better Brier alongside an unchanged PR-AUC is the coherent reading that the macro features shift the probability LEVEL within a year without improving the company-level ORDERING inside it — which is exactly what year-constant features would be expected to do, and is not evidence of incremental discriminative value. It remains exploratory and supplementary, and it is not a confirmatory claim.

### Secondary metrics — reported, not hidden behind the primary null

The conclusion above is about the **primary** metric. Every secondary metric
whose paired interval excludes zero is enumerated here so it cannot vanish
behind a primary-metric null:

| Family | Metric | Delta | 95% CI | Direction | Favours |
| --- | --- | --- | --- | --- | --- |
| `regularized_logistic_regression` | `brier_score` | -0.004600 | [-0.006147, -0.003066] | lower is better | M3_LAG_WDI |
| `random_forest` | `brier_score` | -0.001375 | [-0.002229, -0.000566] | lower is better | M3_LAG_WDI |

### The four mandated registers

1. **Predictive result.** On the identical post-complete-case development sample of 539 rows (55 positives, 108 companies; 366 pooled out-of-fold rows carrying 28 positives), the 14-feature M3-LAG-WDI block was compared against the refit 12-feature retained M2 block. Paired pr_auc differences by family: regularized_logistic_regression +0.000862, random_forest -0.002720, xgboost +0.002749.
2. **Exploratory interpretation.** This result belongs to the supplementary exploratory family `M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY` and is labelled `supplementary_exploratory_robustness_only`. It is not a confirmatory test, it was not inserted into the confirmatory Holm family, and it neither supports nor retires any confirmatory conclusion. The block's frozen role as a `supplementary_exploratory_robustness_block` is unchanged by it.
3. **Statistical uncertainty.** Uncertainty is quantified by the frozen paired paired_company_cluster_bootstrap on `ticker` with 2000 replicates at seed 20260724, percentile intervals at 0.95, with the same resampled companies and rows used for both blocks in every replicate and no model refit inside the bootstrap. With 28 pooled out-of-fold positives the intervals are wide relative to the observed differences; an interval that includes zero is evidence of an undetectably small effect at this event count, not proof that the effect is exactly zero.
4. **Limitations.** Below — none of them resolved by this action.

## Limitations that survive this result

- **point_in_time_wdi_availability_unproven** — The retained WDI values are the CURRENT/REVISED series. WDI `lastupdated` is a revision marker, not evidence of what was published at any past date, so historical point-in-time availability remains UNPROVEN.
- **lagging_does_not_create_point_in_time_data** — The one-year lag is a conservative temporal-separation design only. Lagging a revised series does not convert it into point-in-time data, and the locked +621 calendar mapping does not either.
- **fx_degenerate_2021_2024** — The FX log-ratio is defined but identically ZERO for predictor years 2021-2024, because the official rate is pegged at 42000 across the 2019-2023 observations. Under the locked mapping the development sample spans predictor years 2013-2019, so 0 of 539 rows are zero-change here — the degeneracy binds any extension of the block, not this evaluation.
- **fx_missing_2024_2025** — PA.NUS.FCRF carries no value for observation years 2024-2025, capping the jointly constructible predictor-year ceiling at 2024. This does not bind the development sample but caps any future extension of the block.
- **exploratory_role_is_frozen** — The block's role is frozen as `supplementary_exploratory_robustness_block`. It is not confirmatory M3, not a replacement for or repair of M3-CBI, not a replacement for M3I-2, not historical-vintage or real-time WDI, not part of the confirmatory Holm family, and not independently capable of selecting the paper winner.
- **macro_features_are_year_level_not_company_level** — Both features are NATIONAL annual series, so within a predictor year every company carries the same value: across the 539 rows they take only 7 and 7 distinct values respectively, one per predictor year 2013-2019. Because the temporal folds make training and validation years DISJOINT by construction, every value the block sees in a validation window is one it never saw in training. The block can therefore shift or rescale predictions within a validation year but cannot contribute company-level discrimination inside it, which is what the ranking metrics measure. This is a structural property of the design, not an artefact of the observed result, and it constrains the interpretation of E1 in either direction.
- **two_validation_windows_few_positives** — The paired comparison rests on 366 pooled out-of-fold rows carrying 28 positives across two temporal windows. Interval width, not point estimates, is the honest summary at this event count.

## Where this action stopped

Final Test rows read: `0` · new World Bank requests: `0` · step C reruns:
`0` · step D / Gate reruns: `0` · calendar-lock reruns: `0` · retuning or
grid searches: `0` · SHAP executions: `0` · confirmatory Holm executions:
`0` · paper-winner selections: `0`.

The step-E authorization is **consumed** and is not reusable. No next action
is authorized: PR #79 stays a Draft, the Final Test stays locked, M4 stays
unauthorized, and the confirmatory conclusions are exactly what they were
before this ran.
