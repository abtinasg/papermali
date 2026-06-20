# Technical Modeling Report — Financial Distress Prediction (Stage121)
Models compared on an identical feature set: **Logistic Regression, Random Forest, XGBoost**. Main metric: **PR-AUC**. Forecast horizon: **one year ahead** (firm info at year *t* → distress at *t+1*).
## 1. Data & target
- One-year-ahead rows built: **983**, positives **37** (3.76%).
- Only dropped predictors: {'predictor_last_year_no_next_panel_row': 128, 'next_year_gap_no_row': 0, 'next_target_invalid': 0}.
- Target `distressed_target_reviewed` was never modified; year-*t* label is excluded from features.
## 2. Temporal split (approved revision)
Distress events exist only in target years 1393–1398, so the brief's original test window (1401–1402) contained a single positive and two validation folds with zero positives. With written approval the boundary was moved earlier:
- **dev**: n=300, positives=27
- **test**: n=200, positives=9
- Rows with target_year ≥ 1399 (zero positives, after the test window) are excluded from one-year-ahead modeling and documented.
## 3. Pipeline
- All preprocessing (median impute + missing indicators, RobustScaler for LR, one-hot industry) is fit on the training fold only — no leakage.
- Imbalance handled by cost-sensitive learning (class_weight / scale_pos_weight); SMOTE only in robustness.
- Hyperparameters tuned with Optuna on expanding-window folds; selection metric = mean validation PR-AUC. Thresholds chosen on validation only.
## 4. Cross-validation (validation folds)
| model         |   fold |   n_val |   pos_val |   pr_auc |   roc_auc |   brier |
|:--------------|-------:|--------:|----------:|---------:|----------:|--------:|
| logistic      |      1 |      78 |         5 |    0.154 |     0.63  |   0.217 |
| logistic      |      2 |      84 |         6 |    0.484 |     0.821 |   0.159 |
| logistic      |      3 |      97 |        10 |    0.524 |     0.822 |   0.14  |
| random_forest |      1 |      78 |         5 |    0.105 |     0.633 |   0.177 |
| random_forest |      2 |      84 |         6 |    0.603 |     0.818 |   0.113 |
| random_forest |      3 |      97 |        10 |    0.7   |     0.916 |   0.081 |
| xgboost       |      1 |      78 |         5 |    0.274 |     0.777 |   0.216 |
| xgboost       |      2 |      84 |         6 |    0.71  |     0.829 |   0.073 |
| xgboost       |      3 |      97 |        10 |    0.79  |     0.922 |   0.093 |
## 5. Test results (optimal threshold, primary = F1)
| model         |   pr_auc |   roc_auc |   recall |   precision |    f1 |    f2 |   specificity |   balanced_accuracy |   mcc |   brier |   log_loss |   tp |   fp |   tn |   fn |
|:--------------|---------:|----------:|---------:|------------:|------:|------:|--------------:|--------------------:|------:|--------:|-----------:|-----:|-----:|-----:|-----:|
| logistic      |    0.263 |     0.777 |    0.444 |       0.267 | 0.333 | 0.392 |         0.942 |               0.693 | 0.304 |   0.129 |      0.605 |    4 |   11 |  180 |    5 |
| random_forest |    0.608 |     0.866 |    0.667 |       0.429 | 0.522 | 0.6   |         0.958 |               0.812 | 0.508 |   0.072 |      0.272 |    6 |    8 |  183 |    3 |
| xgboost       |    0.628 |     0.873 |    0.778 |       0.438 | 0.56  | 0.673 |         0.953 |               0.865 | 0.558 |   0.048 |      0.181 |    7 |    9 |  182 |    2 |
## 6. Test 95% cluster-bootstrap CIs (by ticker)
| metric            |   point |   ci_low |   ci_high |   n_boot_valid | model         |
|:------------------|--------:|---------:|----------:|---------------:|:--------------|
| pr_auc            |   0.263 |    0.103 |     0.577 |            999 | logistic      |
| roc_auc           |   0.777 |    0.591 |     0.959 |            999 | logistic      |
| brier             |   0.129 |    0.103 |     0.155 |            999 | logistic      |
| precision         |   0.267 |    0.071 |     0.5   |            999 | logistic      |
| recall            |   0.444 |    0.111 |     0.833 |            999 | logistic      |
| f1                |   0.333 |    0.091 |     0.545 |            999 | logistic      |
| f2                |   0.392 |    0.106 |     0.656 |            999 | logistic      |
| specificity       |   0.942 |    0.91  |     0.97  |            999 | logistic      |
| balanced_accuracy |   0.693 |    0.529 |     0.891 |            999 | logistic      |
| mcc               |   0.304 |    0.043 |     0.544 |            999 | logistic      |
| pr_auc            |   0.608 |    0.213 |     0.89  |            999 | random_forest |
| roc_auc           |   0.866 |    0.582 |     0.993 |            999 | random_forest |
| brier             |   0.072 |    0.053 |     0.091 |            999 | random_forest |
| precision         |   0.429 |    0.153 |     0.692 |            999 | random_forest |
| recall            |   0.667 |    0.286 |     1     |            999 | random_forest |
| f1                |   0.522 |    0.222 |     0.741 |            999 | random_forest |
| f2                |   0.6   |    0.263 |     0.833 |            999 | random_forest |
| specificity       |   0.958 |    0.927 |     0.984 |            999 | random_forest |
| balanced_accuracy |   0.812 |    0.629 |     0.982 |            999 | random_forest |
| mcc               |   0.508 |    0.2   |     0.744 |            999 | random_forest |
| pr_auc            |   0.628 |    0.238 |     0.957 |            999 | xgboost       |
| roc_auc           |   0.873 |    0.6   |     0.997 |            999 | xgboost       |
| brier             |   0.048 |    0.027 |     0.074 |            999 | xgboost       |
| precision         |   0.438 |    0.166 |     0.706 |            999 | xgboost       |
| recall            |   0.778 |    0.333 |     1     |            999 | xgboost       |
| f1                |   0.56  |    0.23  |     0.774 |            999 | xgboost       |
| f2                |   0.673 |    0.294 |     0.878 |            999 | xgboost       |
| specificity       |   0.953 |    0.916 |     0.984 |            999 | xgboost       |
| balanced_accuracy |   0.865 |    0.653 |     0.985 |            999 | xgboost       |
| mcc               |   0.558 |    0.218 |     0.773 |            999 | xgboost       |
## 7. Seed stability (RF & XGBoost, 30 seeds)
| model         |   ('pr_auc', 'mean') |   ('pr_auc', 'std') |   ('recall', 'mean') |   ('recall', 'std') |   ('f1', 'mean') |   ('f1', 'std') |   ('balanced_accuracy', 'mean') |   ('balanced_accuracy', 'std') |   ('brier', 'mean') |   ('brier', 'std') |
|:--------------|---------------------:|--------------------:|---------------------:|--------------------:|-----------------:|----------------:|--------------------------------:|-------------------------------:|--------------------:|-------------------:|
| random_forest |                0.635 |               0.021 |                0.667 |                   0 |            0.543 |           0.013 |                           0.815 |                          0.001 |               0.071 |              0.001 |
| xgboost       |                0.6   |               0.028 |                0.778 |                   0 |            0.541 |           0.019 |                           0.863 |                          0.002 |               0.05  |              0.001 |
## 8. Calibration (Brier on test)
| model         | method       |   brier_test |
|:--------------|:-------------|-------------:|
| logistic      | uncalibrated |        0.129 |
| logistic      | platt        |        0.04  |
| logistic      | isotonic     |        0.056 |
| random_forest | uncalibrated |        0.072 |
| random_forest | platt        |        0.037 |
| random_forest | isotonic     |        0.031 |
| xgboost       | uncalibrated |        0.048 |
| xgboost       | platt        |        0.03  |
| xgboost       | isotonic     |        0.045 |
## 9. Robustness (separate from main result)
| variant                  | model    |   cv_mean_pr_auc |   test_pr_auc |   test_recall |   test_f1 |
|:-------------------------|:---------|-----------------:|--------------:|--------------:|----------:|
| A_main                   | logistic |            0.387 |         0.263 |         0.444 |     0.333 |
| B_extended               | logistic |            0.536 |         0.393 |         0.778 |     0.412 |
| A_winsorized             | logistic |            0.355 |         0.264 |         0.333 |     0.316 |
| A_smote                  | logistic |            0.366 |         0.265 |         0.444 |     0.32  |
| B_drop_near_definition   | logistic |            0.348 |         0.377 |         0.667 |     0.387 |
| same_year_classification | logistic |            0.48  |         0.277 |         0.556 |     0.5   |
| A_main                   | xgboost  |            0.501 |         0.628 |         0.667 |     0.571 |
| B_extended               | xgboost  |            0.47  |         0.582 |         0.889 |     0.4   |
| A_winsorized             | xgboost  |            0.487 |         0.636 |         0.667 |     0.571 |
| A_smote                  | xgboost  |            0.387 |         0.495 |         0.889 |     0.485 |
| B_drop_near_definition   | xgboost  |            0.412 |         0.684 |         0.667 |     0.6   |
| same_year_classification | xgboost  |            0.658 |         0.564 |         0.667 |     0.462 |
## 10. Documented data limitations (brief)
- 39 missing `operating_cash_flow` (1 source_unavailable_codal, 38 deferred); 145 unresolved `gross_profit`; 13 incomplete provenance; 99 unreviewed abnormal financial changes. None were zero-filled.
## 11. Caveats
- Only 9 positives in the test window → test metrics and bootstrap CIs are wide; PR-AUC on validation folds is the more stable selection signal.
