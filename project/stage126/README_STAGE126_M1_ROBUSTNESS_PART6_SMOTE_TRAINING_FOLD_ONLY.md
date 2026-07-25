# Stage126 M1 — Robustness Part 6: SMOTE Training-Fold-Only

**Part 6 only. Explicitly human-authorized. Development folds only. This is the SIXTH AND FINAL registered M1 robustness category. Only the imbalance strategy changed (class weighting -> training-fold-only SMOTENC). No retuning occurred. No full-development refit occurred. No final-test predictor or target values were accessed, preprocessed or resampled. No final-test evaluation occurred. No calibration, threshold optimization, bootstrap, Holm correction, p-values or winner selection. No SHAP. Completing Part 6 completes all six registered M1 robustness categories but does NOT itself authorize a full-development refit or final-test access — those remain a separate, later human decision. Primary results were not replaced and no paper winner was selected.**

Part 6 is **development-only imbalance-strategy robustness evidence**.

## Specification

- Category: `smote_training_fold_only_robustness` (changed dimension: `imbalance_strategy`)
- Scientific role: `imbalance_strategy_robustness`
- Micro-part: `stage126-m1-robustness-part6-smote-training-fold-only`
- Sample: `main_rule_a_primary` (unchanged)
- Target: `FD_target_main_t_plus_1` (unchanged)
- Feature set: `M1_PRIMARY_FEATURE_ORDER` — 9 base features, 18 model-matrix columns (9 transformed features followed by their 9 missingness indicators, categorical for SMOTENC)
- Imbalance policy: `SMOTE_family_training_fold_only_robustness` (**changed**; primary is `primary_class_weighting`); class weighting disabled
- Sampler: `imblearn.over_sampling.SMOTENC`, `random_state=20260725`, `k_neighbors=min(5, training_minority_count - 1)`
- Model seeds: 20260719, 20260720, 20260721, 20260722, 20260723; Logistic deterministic seed 20260719 (unchanged)
- Model fits: 22; predictions: 22; SMOTENC calls: 6; tuning searches: 0

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

## Sample counts (unchanged from primary)

- Analysis-ready: **1012 rows**, 119 companies, 80 positive, 932 negative, 0 missing target
- Development: **666 rows** (68 positive, 598 negative)
- Fold roles: fold1_train 245, fold1_validation 205, fold2_train 450, fold2_validation 216
- Final-test identities (counted via the frozen split contract only): **346**

## SMOTENC resampling audit (training folds only)

| model family | fold | k_neighbors | orig pos/neg | resampled pos/neg | synthetic rows | validation before/after |
|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_train | 5 | 33/212 | 212/212 | 179 | 205/205 |
| `regularized_logistic_regression` | fold2_train | 5 | 58/392 | 392/392 | 334 | 216/216 |
| `random_forest` | fold1_train | 5 | 33/212 | 212/212 | 179 | 205/205 |
| `random_forest` | fold2_train | 5 | 58/392 | 392/392 | 334 | 216/216 |
| `xgboost` | fold1_train | 5 | 33/212 | 212/212 | 179 | 205/205 |
| `xgboost` | fold2_train | 5 | 58/392 | 392/392 | 334 | 216/216 |

Validation rows are never resampled (`validation_rows_before` == `validation_rows_after` for every row above); the final test is never approached; every resampled missingness-indicator column remains binary; class weighting is disabled for every fit.

## Development results (imbalance-strategy sensitivity only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 205 | 25 | 22 | 0.47644856089 | 0.874 | 0.165543066349 | 0.44 | 4.1 |
| `regularized_logistic_regression` | fold2_validation | 216 | 10 | 22 | 0.452738208187 | 0.884466019417 | 0.136615170869 | 0.5 | 4.909090909091 |
| `regularized_logistic_regression` | pooled_development_oof | 421 | 35 | 44 | 0.443220732198 | 0.880384900074 | 0.150701200734 | 0.457142857143 | 4.374025974026 |
| `random_forest` | fold1_validation | 205 | 25 | 22 | 0.420109860443 | 0.84 | 0.157466397338 | 0.4 | 3.727272727273 |
| `random_forest` | fold2_validation | 216 | 10 | 22 | 0.343761816548 | 0.877669902913 | 0.121056720199 | 0.4 | 3.927272727273 |
| `random_forest` | pooled_development_oof | 421 | 35 | 44 | 0.370840785189 | 0.859807549963 | 0.138785897903 | 0.4 | 3.827272727273 |
| `xgboost` | fold1_validation | 205 | 25 | 22 | 0.406955224648 | 0.801111111111 | 0.13638613562 | 0.36 | 3.354545454545 |
| `xgboost` | fold2_validation | 216 | 10 | 22 | 0.213360278213 | 0.850970873786 | 0.112107363868 | 0.3 | 2.945454545455 |
| `xgboost` | pooled_development_oof | 421 | 35 | 44 | 0.301969007417 | 0.824204293116 | 0.12392956864 | 0.342857142857 | 3.280519480519 |

## Comparison with the locked primary class-weighted results

| model family | locked primary pooled PR-AUC | Part 6 pooled PR-AUC | absolute | relative | direction |
|---|---|---|---|---|---|
| `regularized_logistic_regression` | 0.445756964048 | 0.443220732198 | -0.00253623185 | -0.568971896023% | declined |
| `random_forest` | 0.40244183002 | 0.370840785189 | -0.031601044831 | -7.852326093793% | declined |
| `xgboost` | 0.356545008162 | 0.301969007417 | -0.054576000745 | -15.306903615434% | declined |

- Primary observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Part 6 observed ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- **Primary ordering preserved: true**
- Largest absolute pooled PR-AUC change: 0.054576000745

**Interpretation (cautious).** Development-only imbalance-strategy robustness. The sample (`main_rule_a_primary`), the primary target (`FD_target_main_t_plus_1`), the nine-feature primary set, the three selected non-weight hyperparameters, the temporal folds and the seeds are all unchanged; ONLY the imbalance strategy changes from primary class weighting to SMOTENC applied strictly inside each training fold, with class weighting disabled. The development identities and the pooled-OOF identity sets are byte-for-byte the primary identity sets. This is secondary evidence reported descriptively and cautiously: it does not replace the primary class-weighted results or the locked primary ordering used for confirmatory interpretation, does not constitute a new confirmatory model comparison and selects no paper winner.

## Final-test lock

- Final-test identities counted via the frozen split contract: **346**
- Final-test predictor rows loaded: **0**
- Final-test target rows loaded: **0**
- Final-test preprocessing calls: **0**
- Final-test sampler calls: **0**
- Final-test predictions generated: **0**
- Final-test metrics computed: **0**
- Final-test evaluations: **0**
- Full-development refits: **0**
- Frozen final-test aggregate positive events (via the frozen gate only; no row-level target inspected): primary **12**

## Validation architecture

Current Stage126 state is validated by the independent Stage126 current-state validator, which recognizes this Part 6 package generically, plus one explicit, narrowly-scoped exception in `discover_part()`: the completion-lock field `smotenc_executed` is permitted (and required) to be `True` only for category `smote_training_fold_only_robustness` — every other forbidden-operation field, and this field for every other category, remains unconditionally `False`. **Stage125 Part 5 remains historical and immutable** and is not a live gate. Parts 1-5 remain closed packages and were not regenerated.

## Next

**All six registered M1 robustness categories are now complete.** `m1_robustness_completed = true`. There is no seventh registered category. This does **not** authorize a full-development refit or final-test access — either requires its own separate, later, explicit human authorization and decision. The final test remains locked and untouched.
