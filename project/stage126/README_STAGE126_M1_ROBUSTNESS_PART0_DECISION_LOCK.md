# Stage126 M1 — Robustness Part 0 Decision Lock

**Decision lock only. No robustness model was executed. No model was fit or predicted. No retuning occurred. No SMOTE or SMOTENC was executed. Primary Stage126 artifacts are byte-identical. The final test remains locked and untouched. Part 1 is not authorized or started.**

This Part 0 records the machine-readable execution contract (`stage126_m1_robustness_execution_contract`, version `stage126_m1_robustness_execution_contract_v1`) for the six registered Stage126 M1 robustness categories. It is an additive operational layer over the frozen Stage125 Part 4 / Part 5 contracts and does not modify any historical contract or primary Stage126 artifact.

## Execution order (binding via this decision record)

| Micro-part | Category | Changed dimension | Sample | Target | Feature set |
|---|---|---|---|---|---|
| Part 1 | `m1_target_proximity_six_feature_set` | feature_set | `main_rule_a_primary` | `FD_target_main_t_plus_1` | `M1_TARGET_PROXIMITY_ROBUSTNESS` |
| Part 2 | `main_rule_b_listing_robustness` | sample | `main_rule_b_listing_robustness` | `FD_target_main_t_plus_1` | `M1_PRIMARY_FEATURE_ORDER` |
| Part 3 | `expanded_rule_a_company_scope_robustness` | sample | `expanded_rule_a_company_scope_robustness` | `FD_target_main_t_plus_1` | `M1_PRIMARY_FEATURE_ORDER` |
| Part 4 | `expanded_rule_b_combined_robustness` | sample | `expanded_rule_b_combined_robustness` | `FD_target_main_t_plus_1` | `M1_PRIMARY_FEATURE_ORDER` |
| Part 5 | `persistent_loss_robustness_target` | target | `main_rule_a_primary` | `FD_target_persistent_loss_robustness_t_plus_1` | `M1_PRIMARY_FEATURE_ORDER` |
| Part 6 | `smote_training_fold_only_robustness` | imbalance_strategy | `main_rule_a_primary` | `FD_target_main_t_plus_1` | `M1_PRIMARY_FEATURE_ORDER` |

## Global rules (locked)

- One factor at a time: each category changes only its registered dimension; all others equal the locked primary specification.
- Model families (all three, every category): `regularized_logistic_regression`, `random_forest`, `xgboost`.
- No retuning (`second_tuning_search=false`); reuse the primary selected configurations; robustness may not replace them.
- Temporal folds: Fold 1 train 1393-1395 / val 1396-1397; Fold 2 train 1393-1397 / val 1398-1399. Only 1393-1399 loaded.
- Metrics: PR-AUC, ROC-AUC, Brier score, Recall@10%, Lift@10% at fold1_validation / fold2_validation / pooled_development_oof; top-K rule `K_y = ceil(0.10 * N_y)`.
- No calibration, no F2 threshold optimization, no paired bootstrap, no Holm correction, no p-values, no winner selection.
- All six categories are sensitivity analyses only; they may not change a selected configuration, the primary model-family ordering, select a final winner, unlock the final test, trigger a refit, or advance M2/M3/M4.

## Packaging

One robustness category per micro-part PR. Each future Part requires a separate explicit human authorization after the preceding PR is reviewed and merged. **Part 0 does not authorize Part 1.**

## SMOTE / SMOTENC missingness-indicator rule (Part 6)

If appended binary missingness-indicator columns are present, operationalize the registered SMOTE robustness with **SMOTENC** and mark all appended missingness-indicator columns as categorical; continuous features remain continuous; missingness indicators must remain binary 0/1 in synthetic observations. If no missingness-indicator columns exist in the fold matrix, standard **SMOTE** may be used. Sampler `random_state=20260725`; `k_neighbors=min(5, training_minority_count - 1)`; applied only inside each training fold; validation and final-test data are never resampled.
