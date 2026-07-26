# Stage126 — M1 Retained Design Freeze

## Purpose

This package records the **decision-freeze-only** milestone
`stage126-m1-retained-design-freeze`. It performs **no model execution, no
hyperparameter tuning, and no new data collection**. It packages evidence that
was already produced and merged in Parts 0-6 of the Stage126 M1 robustness
program (`project/stage126/stage126_m1_robustness_part0..6_*`) and the
subsequent robustness closure (PR #64), into a single frozen design-lock
artifact: `stage126_m1_retained_design_freeze.json`.

## Retained design (frozen by this package)

- **Sample:** `main_rule_a_primary`
- **Target:** `FD_target_main_t_plus_1`
- **Feature set (`M1_PRIMARY_FEATURE_ORDER`, 9 features, exact order):**
  `log_total_assets`, `leverage_ratio`, `current_ratio`,
  `roa_period_adjusted`, `ocf_to_assets_period_adjusted`,
  `asset_turnover_period_adjusted`, `operating_margin_period_adjusted`,
  `financial_expense_to_assets_period_adjusted`,
  `accumulated_loss_to_capital_ratio`
- **Preprocessing:** training-fold-only 1st/99th percentile clipping, median
  imputation, unstandardized missingness indicators, Logistic-only
  standardization of imputed continuous predictors (frozen at
  `project/stage125/part4_preprocessing_contract_stage125.json`).
- **Imbalance strategy:** Logistic `class_weight=balanced`, RF
  `class_weight=balanced_subsample`, XGBoost `scale_pos_weight` = train-fold
  negative/positive ratio. SMOTENC (Part 6) remains robustness-only and is
  **not** retained.
- **Retained model families and exact frozen configurations** (verified
  byte-for-byte against `stage126_m1_selected_configurations.json`):
  - `logistic__C_0.1` — C=0.1, l2, liblinear, max_iter=5000
  - `rf__depth_3__maxfeat_'sqrt'__leaf_10` — bootstrap=true, max_depth=3,
    max_features=sqrt, min_samples_leaf=10, n_estimators=500
  - `xgboost__lr_0.03__depth_2__mcw_1__lambda_1` — learning_rate=0.03,
    max_depth=2, min_child_weight=1, reg_lambda=1, n_estimators=300,
    subsample=0.8, colsample_bytree=0.8, gamma=0,
    objective=binary:logistic, eval_metric=aucpr, tree_method=hist,
    early_stopping=false, n_jobs=1
- **Temporal folds:** Fold1 train 1393-1395 / val 1396-1397; Fold2 train
  1393-1397 / val 1398-1399; locked final test 1400-1402; 4-Jalali-month
  availability lag.
- **Metrics:** PR-AUC primary; ROC-AUC, Brier, Recall@10%, Lift@10%
  secondary; `K_y = ceil(0.10 * N_y)`.
- **Calibration reporting procedure** and **uncertainty procedure**
  (paired company-cluster bootstrap, cluster=ticker, 2000 replicates, seed
  20260724) and **multiplicity plan** (Holm, alpha=0.05) are recorded as
  frozen *procedures for future reporting* — none are executed by this
  package.

## Rationale (evidence citations)

- **Feature set:** Part 1 is the sole robustness category where the primary
  ordering is not preserved and all families decline
  (`project/stage126/stage126_m1_robustness_part1_primary_comparison.json`).
- **Sample:** Parts 2-4 preserve the primary ordering under sample
  redefinition (`..._part2/3/4_primary_comparison.json`).
- **Target:** Part 5's PR-AUC gain co-occurs with a target and positive-count
  change and is not a same-outcome gain
  (`project/stage126/stage126_m1_robustness_part5_primary_comparison.json`).
- **Imbalance:** Part 6 (training-fold-only SMOTENC) preserves ordering but
  all families decline versus primary class weighting
  (`project/stage126/stage126_m1_robustness_part6_primary_comparison.json`,
  `..._part6_resampling_audit.csv`).
- **Model families:** primary ordering preserved in 5 of 6 categories
  (`project/stage126/stage126_m1_robustness_closure_synthesis_record.json`).

## Explicit non-authorizations

This freeze does **not**:
- select a paper winner or a final model,
- perform a full development refit,
- unlock, access, or evaluate on the final test set,
- start M2 (`stage127-m2-market-data-gate`), M3, or M4,
- execute calibration, bootstrap, Holm correction, or SHAP.

All final-test firewall flags remain locked
(`final_test_locked=true`, `final_test_unlocked=false`,
`final_test_access_authorized=false`,
`final_test_predictor_values_inspected=false`,
`final_test_target_values_inspected=false`,
`final_test_evaluation_performed=false`,
`full_development_refit_performed=false`).

`last_completed_research_action_id = stage126-m1-retained-design-freeze`;
`next_research_action_id = stage127-m2-market-data-gate` (not started).

## Files

- `stage126_m1_retained_design_freeze.json` — the frozen design package.
- `stage126_m1_retained_design_freeze_human_authorization_record.json` —
  scoped human authorization record (does not extend to M2 or later work).
- `metadata_and_hashes_stage126_m1_retained_design_freeze.json` — SHA-256
  hashes of the artifacts in this package.
- `project/tests/test_stage126_m1_retained_design_freeze.py` — structural and
  guard-flag tests.
