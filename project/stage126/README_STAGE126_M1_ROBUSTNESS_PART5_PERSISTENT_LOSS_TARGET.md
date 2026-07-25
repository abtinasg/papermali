# Stage126 M1 — Robustness Part 5: Persistent-Loss Robustness Target

**Part 5 only. Explicitly human-authorized. Development folds only. Only the target changed (to `FD_target_persistent_loss_robustness_t_plus_1`). No retuning occurred. No full-development refit occurred. No final-test predictor or target values were accessed. No final-test evaluation occurred. No calibration, threshold optimization, bootstrap, Holm correction, p-values, SMOTE, SMOTENC or SHAP was executed. Part 6 is not authorized and not started. Primary target and primary results were not replaced and no paper winner was selected.**

Part 5 is **development-only secondary target-robustness evidence**.

## Specification

- Category: `persistent_loss_robustness_target` (changed dimension: `target`)
- Scientific role: `secondary_target_robustness`
- Micro-part: `stage126-m1-robustness-part5-persistent-loss-target`
- Sample: `main_rule_a_primary` (**unchanged**; same as primary)
- Input: `project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv` (`4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e`)
- Primary target: `FD_target_main_t_plus_1` (reference, unchanged)
- Part 5 target: `FD_target_persistent_loss_robustness_t_plus_1` (**changed**)
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

## Sample and event counts (persistent-loss target)

- Analysis-ready: **1012 rows**, 119 companies, 100 positive, 912 negative, 0 missing target
- Development: **666 rows** (85 positive, 581 negative)
- Fold roles: fold1_train 245/42/203, fold1_validation 205/30/175, fold2_train 450/72/378, fold2_validation 216/13/203
- Final-test identities (counted via the frozen split contract only): **346**

## Development-only target transitions (primary → persistent-loss)

| primary target | persistent-loss target | rows |
|---|---|---|
| 0 | 0 | 581 |
| 0 | 1 | 17 |
| 1 | 0 | 0 |
| 1 | 1 | 68 |

Development primary-target positives: **68**; persistent-loss positives: **85** (net +17). These reconcile against the frozen development aggregates. The sample identities and pooled-OOF identity sets are byte-for-byte the primary identity sets; only target values differ.

## Development results (secondary target sensitivity only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 205 | 30 | 22 | 0.566356251832 | 0.901523809524 | 0.158424669534 | 0.466666666667 | 4.348484848485 |
| `regularized_logistic_regression` | fold2_validation | 216 | 13 | 22 | 0.437048983982 | 0.899962106859 | 0.128315581178 | 0.538461538462 | 5.286713286713 |
| `regularized_logistic_regression` | pooled_development_oof | 421 | 43 | 44 | 0.508760611404 | 0.902977728559 | 0.14297677622 | 0.488372093023 | 4.672832980973 |
| `random_forest` | fold1_validation | 205 | 30 | 22 | 0.601020440117 | 0.872952380952 | 0.14141641571 | 0.4 | 3.727272727273 |
| `random_forest` | fold2_validation | 216 | 13 | 22 | 0.3999153089 | 0.898825312618 | 0.112223938434 | 0.538461538462 | 5.286713286713 |
| `random_forest` | pooled_development_oof | 421 | 43 | 44 | 0.500501101034 | 0.886981666051 | 0.126438802666 | 0.441860465116 | 4.227801268499 |
| `xgboost` | fold1_validation | 205 | 30 | 22 | 0.518477799111 | 0.876 | 0.111092848521 | 0.5 | 4.659090909091 |
| `xgboost` | fold2_validation | 216 | 13 | 22 | 0.34306398848 | 0.880636604775 | 0.099357745948 | 0.538461538462 | 5.286713286713 |
| `xgboost` | pooled_development_oof | 421 | 43 | 44 | 0.441491570406 | 0.880829334318 | 0.105071988294 | 0.511627906977 | 4.895348837209 |

## Comparison with the locked primary results (primary target)

| model family | locked primary pooled PR-AUC | Part 5 pooled PR-AUC | absolute | relative | direction |
|---|---|---|---|---|---|
| `regularized_logistic_regression` | 0.445756964048 | 0.508760611404 | 0.063003647356 | 14.134080325712% | improved |
| `random_forest` | 0.40244183002 | 0.500501101034 | 0.098059271014 | 24.366073230789% | improved |
| `xgboost` | 0.356545008162 | 0.441491570406 | 0.084946562244 | 23.824919799579% | improved |

- Primary observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Part 5 observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- **Primary ordering preserved: true**
- Largest absolute pooled PR-AUC change: 0.098059271014

**Interpretation (cautious).** Development-only secondary target robustness. The sample (`main_rule_a_primary`), the nine-feature primary set, the three selected configurations, the temporal folds, the imbalance policy and the seeds are all unchanged; ONLY the modeling target changes to `FD_target_persistent_loss_robustness_t_plus_1`. The development identities and the pooled-OOF identity sets are byte-for-byte the primary identity sets; only target values differ. The persistent-loss target has more development positives than the primary target (85 vs 68); the target-transition counts are reported and reconciled against the frozen development aggregates. This is secondary evidence reported descriptively and cautiously: it does not replace the primary target, the primary results or the locked primary ordering used for confirmatory interpretation, does not constitute a new confirmatory model comparison and selects no paper winner.

## Final-test lock (aggregate counts only)

- Final-test identities counted via the frozen split contract: **346**
- Frozen final-test aggregate (from the event-count gate only; no row-level target inspected): primary target **12 positive / 334 negative**; persistent-loss target **15 positive / 331 negative**
- Final-test predictor rows loaded: **0**
- Final-test target rows loaded: **0**
- Final-test predictions generated: **0**
- Final-test metrics computed: **0**
- Final-test evaluations: **0**
- Final-test row identities inspected together with target values: **false**
- Full-development refits: **0**

## Next

The next registered category is `smote_training_fold_only_robustness` (Part 6). **Part 6 is not authorized and not started** — it requires its own separate explicit human authorization. Part 6 remains outstanding, so the overall M1 robustness program is **not** complete. The final test remains locked and untouched.
