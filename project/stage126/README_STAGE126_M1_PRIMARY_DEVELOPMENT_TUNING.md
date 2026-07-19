# Stage126 M1 — Primary Development-Fold Tuning

**Stage126 M1 is human-authorized.** This deliverable performs primary M1 development-fold tuning only. The final test remains locked. No final-test predictor or target values were inspected. No final-test evaluation occurred. M1 robustness is not executed here.

## Scope

- Sample: `main_rule_a_primary`
- Target: `FD_target_main_t_plus_1`
- Feature set: `M1_PRIMARY_FEATURE_ORDER` (9 features, exact order)
- Model families: regularized_logistic_regression, random_forest, xgboost
- Configurations: 32 (4 logistic + 12 random forest + 16 xgboost)
- Tuning seeds: 20260719, 20260720, 20260721
- Final RF/XGBoost OOF seeds: 20260719, 20260720, 20260721, 20260722, 20260723

## Temporal development folds

- Fold 1: train 1393–1395 (245), validation 1396–1397 (205)
- Fold 2: train 1393–1397 (450), validation 1398–1399 (216)
- Development rows: 666 (68 positive / 598 negative)
- Pooled validation/OOF rows: 421 (35 positive / 386 negative) per family

## Selected configurations

- `regularized_logistic_regression`: `logistic__C_0.1` (mean validation PR-AUC=0.462281478468; pooled OOF PR-AUC=0.445756964048)
- `random_forest`: `rf__depth_3__maxfeat_'sqrt'__leaf_10` (mean validation PR-AUC=0.415840277848; pooled OOF PR-AUC=0.40244183002)
- `xgboost`: `xgboost__lr_0.03__depth_2__mcw_1__lambda_1` (mean validation PR-AUC=0.395176945304; pooled OOF PR-AUC=0.356545008162)

## Locks

- No full-development refit; no final-test application model created.
- No SMOTE, no SHAP, no robustness variants, no M2/M3/M4 data.
- Registered robustness variants remain frozen for a later Stage126 micro-part.
- The final test stays locked until a separate explicit human authorization.
