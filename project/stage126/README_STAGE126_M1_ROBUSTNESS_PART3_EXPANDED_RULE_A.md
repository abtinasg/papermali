# Stage126 M1 — Robustness Part 3: Expanded Rule A Company Scope

**Part 3 only. Explicitly human-authorized. Development folds only. Only the company-scope sample changed. No retuning occurred. No full-development refit occurred. No final-test predictor or target values were accessed. No final-test evaluation occurred. No calibration, threshold optimization, bootstrap, Holm correction, p-values, SMOTE, SMOTENC or SHAP was executed. Part 4 is not authorized and not started. Primary results were not replaced and no paper winner was selected. Stage125 Part 5 remains historical and immutable.**

Part 3 is **development-only sample-sensitivity evidence**.

## Specification

- Category: `expanded_rule_a_company_scope_robustness` (changed dimension: `sample`)
- Scientific role: `expanded_company_scope_sample_robustness`
- Micro-part: `stage126-m1-robustness-part3-expanded-rule-a`
- Sample: `expanded_rule_a_company_scope_robustness` (**changed**; primary is `main_rule_a_primary`)
- Input: `project/stage125/part3c_outputs/analysis_ready_expanded_rule_a_stage125.csv` (`fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9`)
- Target: `FD_target_main_t_plus_1` (unchanged)
- Feature set: `M1_PRIMARY_FEATURE_ORDER` — 9 base features, 18 model-matrix columns (9 transformed features followed by their 9 missingness indicators)
- Imbalance policy: `primary_class_weighting` (unchanged)
- Folds: Fold 1 train 1393-1395 / val 1396-1397; Fold 2 train 1393-1397 / val 1398-1399 (unchanged)
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

- Analysis-ready: **1056 rows**, 124 companies, 80 positive, 976 negative, 0 missing target
- Development: **695 rows** (68 positive, 627 negative)
- Fold roles: fold1_train 254, fold1_validation 215, fold2_train 469, fold2_validation 226
- Final-test identities (counted via the frozen split contract only): **361**

## Sample delta versus the primary Rule A sample (row identities only)

| scope | primary Rule A | expanded Rule A | difference |
|---|---|---|---|
| analysis-ready rows | 1012 | 1056 | +44 |
| companies | 119 | 124 | +5 |
| positive | 80 | 80 | 0 |
| negative | 932 | 976 | +44 |
| development rows | 666 | 695 | +29 |
| OOF identities | 421 | 441 | +20 |
| final-test identities | 346 | 361 | +15 |

Expanded Rule A is a **strict superset** of primary Rule A (44 expanded-only rows, 0 primary-only rows). **Every added development row is negative**, and all 20 added OOF identities carry target 0. Final-test rows contribute identities and counts only — no row-level final-test value was read. Detail: `stage126_m1_robustness_part3_sample_delta.csv`.

## Development results (sample sensitivity only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 215 | 25 | 22 | 0.482882859298 | 0.886736842105 | 0.164611340418 | 0.44 | 4.3 |
| `regularized_logistic_regression` | fold2_validation | 226 | 10 | 24 | 0.439030534252 | 0.886111111111 | 0.134537932505 | 0.6 | 5.65 |
| `regularized_logistic_regression` | pooled_development_oof | 441 | 35 | 46 | 0.442885909854 | 0.888036593948 | 0.149199571284 | 0.485714285714 | 4.65652173913 |
| `random_forest` | fold1_validation | 215 | 25 | 22 | 0.485108975954 | 0.846315789474 | 0.14263049027 | 0.36 | 3.518181818182 |
| `random_forest` | fold2_validation | 226 | 10 | 24 | 0.349613806241 | 0.896296296296 | 0.1108327154 | 0.5 | 4.708333333333 |
| `random_forest` | pooled_development_oof | 441 | 35 | 46 | 0.39070232845 | 0.869669247009 | 0.126335031946 | 0.4 | 3.834782608696 |
| `xgboost` | fold1_validation | 215 | 25 | 22 | 0.45078284734 | 0.834526315789 | 0.1067728694 | 0.4 | 3.909090909091 |
| `xgboost` | fold2_validation | 226 | 10 | 24 | 0.34133480622 | 0.876388888889 | 0.092841796739 | 0.5 | 4.708333333333 |
| `xgboost` | pooled_development_oof | 441 | 35 | 46 | 0.35656070755 | 0.848135116115 | 0.099633589533 | 0.428571428571 | 4.108695652174 |

## Comparison with the locked primary Rule A results

| model family | locked primary pooled PR-AUC | Part 3 pooled PR-AUC | absolute | relative | direction |
|---|---|---|---|---|---|
| `regularized_logistic_regression` | 0.445756964048 | 0.442885909854 | -0.002871054194 | -0.644085101426% | declined |
| `random_forest` | 0.40244183002 | 0.39070232845 | -0.01173950157 | -2.917067932381% | declined |
| `xgboost` | 0.356545008162 | 0.35656070755 | 1.5699388e-05 | 0.004403199495% | improved |

- Primary observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Part 3 observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- **Primary ordering preserved: true**
- Largest absolute pooled PR-AUC change: 0.01173950157

**Interpretation (cautious).** Development-only sample sensitivity. The expanded company scope adds negative-only development rows (29 development rows, of which 20 enter the pooled OOF surface, all with target 0), so pooled PR-AUC shifts here mainly reflect a slightly lower event rate rather than a change in discrimination. The comparison is reported descriptively and cautiously: it does not replace the primary results, does not alter the locked primary ordering used for confirmatory interpretation, does not constitute a new confirmatory model comparison and selects no paper winner.

## Descriptive comparison with Part 2 (separated; no additional claim)

| model family | Part 2 pooled PR-AUC | Part 3 pooled PR-AUC | Part 3 − Part 2 |
|---|---|---|---|
| `regularized_logistic_regression` | 0.447170385532 | 0.442885909854 | -0.004284475678 |
| `random_forest` | 0.401263142511 | 0.39070232845 | -0.010560814061 |
| `xgboost` | 0.34195953388 | 0.35656070755 | 0.01460117367 |

Separated descriptive context only. Part 2 (listing Rule B) and Part 3 (expanded company scope) probe DIFFERENT sample dimensions; no preferred robustness sample is selected and no additional claim is made.

## Final-test lock

- Final-test identities counted via the frozen split contract: **361**
- Final-test predictor rows loaded: **0**
- Final-test target rows loaded: **0**
- Final-test predictions generated: **0**
- Final-test metrics computed: **0**
- Final-test evaluations: **0**
- Full-development refits: **0**

## Validation architecture

Current Stage126 state is validated by the independent Stage126 current-state validator, which recognized this Part 3 package generically with **no validator source change**. **Stage125 Part 5 remains historical and immutable** and is not a live gate; no Part 3 Part 5 compatibility artifact exists. Part 1 and Part 2 remain closed packages and were not regenerated.

## Next

The next registered category is `expanded_rule_b_combined_robustness` (Part 4). **Part 4 is not authorized and not started** — it requires its own separate explicit human authorization. Parts 4-6 remain outstanding, so the overall M1 robustness program is **not** complete. The final test remains locked and untouched.
