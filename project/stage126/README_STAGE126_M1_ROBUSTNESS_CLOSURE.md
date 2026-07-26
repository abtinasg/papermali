# Stage126 M1 — Robustness Closure

**Synthesis-only closure. Zero model fits, zero predictions, zero resampling, zero hyperparameter search, zero calibration/bootstrap/Holm/p-values/SHAP/threshold-optimization/winner-selection, and zero final-test access. This closure reads only already-committed Part 1-6 artifacts and produces derived evidence artifacts.**

## Purpose

This closure verifies and synthesizes the six pre-registered Stage126 M1 robustness categories (Parts 1-6, all already completed and committed) into a single evidence table and synthesis record. It does **not** select a retained design, does **not** freeze anything, and does **not** authorize `stage126-m1-retained-design-freeze` — that is a separate future action requiring its own explicit human authorization.

## Inputs (read-only)

- Locked primary pooled development-OOF PR-AUC (`project/stage126/stage126_m1_development_metrics.csv`): random_forest=0.402441830020, regularized_logistic_regression=0.445756964048, xgboost=0.356545008162
- `project/stage126/stage126_closed_part_registry.json` (six closed parts).
- Each Part 1-6 `_primary_comparison.json`, `_metrics.csv`, `_completion_lock.json`, `_execution_manifest.json` and `_human_authorization_record.json`.

## Six-category synthesis summary

| Part | Category | Changed dimension | Ordering preserved |
|---|---|---|---|
| 1 | `m1_target_proximity_six_feature_set` | feature_set | see synthesis record |
| 2 | `main_rule_b_listing_robustness` | sample | see synthesis record |
| 3 | `expanded_rule_a_company_scope_robustness` | sample | see synthesis record |
| 4 | `expanded_rule_b_combined_robustness` | sample | see synthesis record |
| 5 | `persistent_loss_robustness_target` | target | see synthesis record |
| 6 | `smote_training_fold_only_robustness` | imbalance_strategy | see synthesis record |

## Interpretation (A-E)

- **A. Model-family ordering:** primary ordering (logistic > random forest > xgboost) preserved in Parts 2,3,4,5,6. Part 1 is the exception (all families declined; different ordering) — reported as feature-set sensitivity, not a change to the locked primary ordering.
- **B. Sample-definition sensitivity (Parts 2-4):** ordering generally preserved, small PR-AUC changes — evidence of comparative stability to listing/company-scope sample redefinition, subject to existing event-rate/identity-composition cautions. No preferred robustness sample is selected.
- **C. Target sensitivity (Part 5):** PR-AUC increases for all three families, but the target changed and positive count increased (85 vs 68) — secondary-target sensitivity evidence only, not a same-outcome performance gain.
- **D. Imbalance-strategy sensitivity (Part 6):** ordering preserved but all three PR-AUC values decline under training-fold-only SMOTENC vs the locked primary class-weighted result. Class weighting is not frozen by this closure.
- **E. Overall:** evidence does not justify changing the primary result, selecting a winner, retuning, opening the final test, or auto-freezing a retained design.

## Limitations

- All robustness analyses are development-only (temporal folds 1393-1399); the locked final-test years (1400-1402) are never accessed by this closure or by Parts 1-6.
- Some sensitivity comparisons involve small absolute positive counts; interpretation is deliberately conservative.

## No final test / no selection

This closure never reads final-test predictor or target row values. It selects no paper winner and freezes no retained design.

## Next action

`stage126-m1-retained-design-freeze` — freeze the exact retained M1 design using development evidence only. This requires a **separate, future, explicit human authorization** and is not started, selected or authorized by this closure.
