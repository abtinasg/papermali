# Stage126 M1 — Robustness Part 4: Expanded Rule B Combined Sample

**Part 4 only. Explicitly human-authorized. Development folds only. Only the combined sample changed. No retuning occurred. No full-development refit occurred. No final-test predictor or target values were accessed. No final-test evaluation occurred. No calibration, threshold optimization, bootstrap, Holm correction, p-values, SMOTE, SMOTENC or SHAP was executed. Part 5 is not authorized and not started. Primary results were not replaced and no paper winner was selected. Stage125 Part 5 remains historical and immutable.**

Part 4 is **development-only sample-sensitivity evidence**.

## Specification

- Category: `expanded_rule_b_combined_robustness` (changed dimension: `sample`)
- Scientific role: `combined_sample_robustness`
- Micro-part: `stage126-m1-robustness-part4-expanded-rule-b`
- Sample: `expanded_rule_b_combined_robustness` (**changed**; primary is `main_rule_a_primary`)
- Input: `project/stage125/part3c_outputs/analysis_ready_expanded_rule_b_stage125.csv` (`2e61a282165ccdaef37bac61a460c83878f2ae633b10535945cc33897d3b4c22`)
- Target: `FD_target_main_t_plus_1` (unchanged)
- Feature set: `M1_PRIMARY_FEATURE_ORDER` — 9 base features, 18 model-matrix columns (9 transformed features followed by their 9 missingness indicators)
- Imbalance policy: `primary_class_weighting` (unchanged)
- Model seeds: 20260719, 20260720, 20260721, 20260722, 20260723; Logistic deterministic seed 20260719 (unchanged)
- Model fits: 22; predictions: 22; tuning searches: 0

## Nine-feature primary order (unchanged)

| # | feature | source column | transformation | indicator column |
|---|---|---|---|---|
| 1 | `log_total_assets` | `total_assets` | ln(total_assets) if total_assets > 0 else missing | 10 |
| 2 | `leverage_ratio` | `leverage_ratio` | frozen_part3c_value | 11 |
| 3 | `current_ratio` | `current_ratio` | frozen_part3c_value | 12 |
| 4 | `roa_period_adjusted` | `roa_period_adjusted` | frozen_part3c_value | 13 |
| 5 | `ocf_to_assets_period_adjusted` | `ocf_to_assets_period_adjusted` | frozen_part3c_value | 14 |
| 6 | `asset_turnover_period_adjusted` | `asset_turnover_period_adjusted` | frozen_part3c_value | 15 |
| 7 | `operating_margin_period_adjusted` | `operating_margin_period_adjusted` | frozen_part3c_value | 16 |
| 8 | `financial_expense_to_assets_period_adjusted` | `financial_expense_to_assets_period_adjusted` | frozen_part3c_value_source_sign_preserved | 17 |
| 9 | `accumulated_loss_to_capital_ratio` | `accumulated_loss_to_capital_ratio` | frozen_part3c_value | 18 |

`revenue_growth_period_adjusted` remains audit-only and prohibited.

## Sample counts

- Analysis-ready: **1035 rows**, 122 companies, 79 positive, 956 negative, 0 missing target
- Development: **682 rows** (68 positive, 614 negative)
- Fold roles: fold1_train 250, fold1_validation 211, fold2_train 461, fold2_validation 221
- Final-test identities (counted via the frozen split contract only): **353**

## Sample delta A — versus Part 2 (main Rule B; Part 4 is a strict superset)

| scope | Part 2 | Part 4 | difference |
|---|---|---|---|
| analysis-ready rows | 993 | 1035 | +42 |
| companies | 117 | 122 | +5 |
| positive | 79 | 79 | 0 |
| negative | 914 | 956 | +42 |
| development rows | 655 | 682 | +27 |
| OOF identities | 413 | 432 | +19 |
| final-test identities | 338 | 353 | +15 |

Part 4 is a **strict superset** of Part 2 (42 Part4-only rows, 0 Part2-only rows); every added row is negative.

## Sample delta B — versus Part 3 (expanded Rule A; Part 4 is a strict subset)

| scope | Part 3 | Part 4 | difference |
|---|---|---|---|
| analysis-ready rows | 1056 | 1035 | -21 |
| companies | 124 | 122 | -2 |
| positive | 80 | 79 | -1 |
| negative | 976 | 956 | -20 |
| development rows | 695 | 682 | -13 |
| OOF identities | 441 | 432 | -9 |
| final-test identities | 361 | 353 | -8 |

Part 4 is a **strict subset** of Part 3 (21 Part3-only rows, 0 Part4-only rows). Development-fold and pooled-OOF removed rows are target-0 (verified by conservation against the frozen development/OOF aggregate counts). At the frozen full-sample aggregate level Part 4 has one fewer positive event than Part 3 (-1); the frozen final-test aggregate count is **11** versus **12**. No row-level final-test target was read — this single-event difference is never attributed to an identified row.

## Sample delta C — versus the locked primary Rule A sample (mixed; neither sub- nor super-set)

| scope | primary | Part 4 | net difference |
|---|---|---|---|
| analysis-ready rows | 1012 | 1035 | +23 |
| companies | 119 | 122 | +3 |
| positive | 80 | 79 | -1 |
| negative | 932 | 956 | +24 |
| development rows | 666 | 682 | +16 |
| OOF identities | 421 | 432 | +11 |
| final-test identities | 346 | 353 | +7 |

Part4-only rows: **42**; primary-only rows: **19**. Development-fold and pooled-OOF identity differences on both sides are target-0 (verified by conservation against the frozen development/OOF aggregate counts). At the frozen full-sample aggregate level Part 4 has one fewer positive event than the locked primary sample (-1); the frozen final-test aggregate count is **11** versus **12**. Final-test rows contribute identities and counts only — no row-level final-test value was read. Detail: `stage126_m1_robustness_part4_sample_delta.csv`.

## Development results (sample sensitivity only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 211 | 25 | 22 | 0.484836747913 | 0.885376344086 | 0.165537628736 | 0.44 | 4.22 |
| `regularized_logistic_regression` | fold2_validation | 221 | 10 | 23 | 0.440046955258 | 0.884834123223 | 0.136352220697 | 0.6 | 5.765217391304 |
| `regularized_logistic_regression` | pooled_development_oof | 432 | 35 | 45 | 0.444983882478 | 0.886290032386 | 0.150607130642 | 0.485714285714 | 4.662857142857 |
| `random_forest` | fold1_validation | 211 | 25 | 22 | 0.476551199691 | 0.846666666667 | 0.142984396525 | 0.36 | 3.452727272727 |
| `random_forest` | fold2_validation | 221 | 10 | 23 | 0.354328690052 | 0.891469194313 | 0.112821954115 | 0.5 | 4.804347826087 |
| `random_forest` | pooled_development_oof | 432 | 35 | 45 | 0.396418788419 | 0.868010075567 | 0.127554072978 | 0.4 | 3.84 |
| `xgboost` | fold1_validation | 211 | 25 | 22 | 0.425343496071 | 0.827096774194 | 0.11008626272 | 0.4 | 3.836363636364 |
| `xgboost` | fold2_validation | 221 | 10 | 23 | 0.31261766606 | 0.875355450237 | 0.093092240017 | 0.5 | 4.804347826087 |
| `xgboost` | pooled_development_oof | 432 | 35 | 45 | 0.355210803326 | 0.843756747031 | 0.101392561291 | 0.428571428571 | 4.114285714286 |

## Comparison with the locked primary Rule A results

| model family | locked primary pooled PR-AUC | Part 4 pooled PR-AUC | absolute | relative | direction |
|---|---|---|---|---|---|
| `regularized_logistic_regression` | 0.445756964048 | 0.444983882478 | -0.00077308157 | -0.173431181642% | declined |
| `random_forest` | 0.40244183002 | 0.396418788419 | -0.006023041601 | -1.49662414583% | declined |
| `xgboost` | 0.356545008162 | 0.355210803326 | -0.001334204836 | -0.374203762627% | declined |

- Primary observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Part 4 observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- **Primary ordering preserved: true**
- Largest absolute pooled PR-AUC change: 0.006023041601

**Interpretation (cautious).** Development-only sample sensitivity. The Rule-B combined sample is a strict subset of the Part 3 expanded scope and a strict superset of the Part 2 listing-Rule-B sample; relative to the locked primary sample it neither contains nor is contained by it. All development-fold and pooled-OOF identity differences relevant to the Part 4 predictive comparison are target-0 observations. At the frozen full-sample aggregate level, however, Part 4 has one fewer positive event than Part 3 and the locked primary sample (-1); the corresponding final-test aggregate count is 11 versus 12 (Part 3) and 12 (primary). No row-level final-test target was accessed. Because the pooled development-OOF ordering is preserved and the PR-AUC changes remain small, the combined sample does not materially change the development-only interpretation. The comparison is reported descriptively and cautiously: it does not replace the primary results, does not alter the locked primary ordering used for confirmatory interpretation, does not constitute a new confirmatory model comparison and selects no paper winner.

## Descriptive comparison with Part 2 (separated; no additional claim)

| model family | Part 2 pooled PR-AUC | Part 4 pooled PR-AUC | Part 4 − Part 2 |
|---|---|---|---|
| `regularized_logistic_regression` | 0.447170385532 | 0.444983882478 | -0.002186503054 |
| `random_forest` | 0.401263142511 | 0.396418788419 | -0.004844354092 |
| `xgboost` | 0.34195953388 | 0.355210803326 | 0.013251269446 |

Separated descriptive context only — effect of expanding company scope under Rule B. Part 2 (main listing Rule B) and Part 4 (combined expanded Rule B) probe RELATED but not identical sample dimensions; no preferred robustness sample is selected and no additional claim is made.

## Descriptive comparison with Part 3 (separated; no additional claim)

| model family | Part 3 pooled PR-AUC | Part 4 pooled PR-AUC | Part 4 − Part 3 |
|---|---|---|---|
| `regularized_logistic_regression` | 0.442885909854 | 0.444983882478 | 0.002097972624 |
| `random_forest` | 0.39070232845 | 0.396418788419 | 0.005716459969 |
| `xgboost` | 0.35656070755 | 0.355210803326 | -0.001349904224 |

Separated descriptive context only — effect of applying Rule B inside the expanded company scope. Part 3 (expanded Rule A) and Part 4 (combined expanded Rule B) probe RELATED but not identical sample dimensions; no preferred robustness sample is selected and no additional claim is made.

## Final-test lock

- Final-test identities counted via the frozen split contract: **353**
- Final-test predictor rows loaded: **0**
- Final-test target rows loaded: **0**
- Final-test predictions generated: **0**
- Final-test metrics computed: **0**
- Final-test evaluations: **0**
- Full-development refits: **0**
- Frozen final-test aggregate positive events (via the frozen gate only; no row-level target inspected): primary **12**, Part 3 **12**, Part 4 **11**

## Validation architecture

Current Stage126 state is validated by the independent Stage126 current-state validator, which recognized this Part 4 package generically with **no validator source change**. **Stage125 Part 5 remains historical and immutable** and is not a live gate; no Part 4 Part 5 compatibility artifact exists. Parts 1, 2 and 3 remain closed packages and were not regenerated.

## Next

The next registered category is `persistent_loss_robustness_target` (Part 5). **Part 5 is not authorized and not started** — it requires its own separate explicit human authorization. Parts 5-6 remain outstanding, so the overall M1 robustness program is **not** complete. The final test remains locked and untouched.
