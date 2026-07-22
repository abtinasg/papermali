# Stage126 M1 — Robustness Part 1: Target-Proximity Six-Feature Set

**Part 1 only. Explicitly human-authorized. Development folds only. Only the feature set changed. No retuning occurred. No full-development refit occurred. No final-test predictor or target values were inspected. No final-test evaluation occurred. No SMOTE, SMOTENC or SHAP was executed. Part 2 is not authorized or started. Primary Stage126 artifacts remain byte-identical.**

Part 1 is **sensitivity-analysis evidence only**. It does not replace the primary results, does not re-rank the primary model families, and does not select a paper winner.

## Specification

- Category: `m1_target_proximity_six_feature_set` (changed dimension: `feature_set`)
- Sample: `main_rule_a_primary` (unchanged)
- Target: `FD_target_main_t_plus_1` (unchanged)
- Feature set: `M1_TARGET_PROXIMITY_ROBUSTNESS` — 6 base features, 12 transformed columns (6 imputed continuous + 6 missingness indicators)
- Imbalance policy: `primary_class_weighting` (unchanged)
- Folds: Fold 1 train 1393-1395 / val 1396-1397; Fold 2 train 1393-1397 / val 1398-1399 (unchanged)
- Model seeds: 20260719, 20260720, 20260721, 20260722, 20260723; Logistic deterministic seed 20260719
- Model fits: 22; predictions: 22; tuning searches: 0

## Six-feature order (locked)

| # | feature | source column | transformation |
|---|---|---|---|
| 1 | `log_total_assets` | `total_assets` | ln(total_assets) if total_assets > 0 else missing |
| 2 | `current_ratio` | `current_ratio` | frozen_part3c_value |
| 3 | `roa_period_adjusted` | `roa_period_adjusted` | frozen_part3c_value |
| 4 | `asset_turnover_period_adjusted` | `asset_turnover_period_adjusted` | frozen_part3c_value |
| 5 | `operating_margin_period_adjusted` | `operating_margin_period_adjusted` | frozen_part3c_value |
| 6 | `financial_expense_to_assets_period_adjusted` | `financial_expense_to_assets_period_adjusted` | frozen_part3c_value_source_sign_preserved |

Removed relative to the primary nine-feature set (never loaded onto the Part 1 model surface): `leverage_ratio`, `ocf_to_assets_period_adjusted`, `accumulated_loss_to_capital_ratio`; `revenue_growth_period_adjusted` remains audit-only and prohibited.

## Development results (sensitivity analysis only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 205 | 25 | 22 | 0.387997687122 | 0.780444444444 | 0.223421341124 | 0.32 | 2.981818181818 |
| `regularized_logistic_regression` | fold2_validation | 216 | 10 | 22 | 0.296907728348 | 0.860194174757 | 0.151131187775 | 0.6 | 5.890909090909 |
| `regularized_logistic_regression` | pooled_development_oof | 421 | 35 | 44 | 0.318117505162 | 0.824944485566 | 0.18633185627 | 0.4 | 3.827272727273 |
| `random_forest` | fold1_validation | 205 | 25 | 22 | 0.341721273103 | 0.745777777778 | 0.183110242894 | 0.36 | 3.354545454545 |
| `random_forest` | fold2_validation | 216 | 10 | 22 | 0.364411265346 | 0.918932038835 | 0.131760711313 | 0.6 | 5.890909090909 |
| `random_forest` | pooled_development_oof | 421 | 35 | 44 | 0.332133983124 | 0.822945965951 | 0.156764639992 | 0.428571428571 | 4.100649350649 |
| `xgboost` | fold1_validation | 205 | 25 | 22 | 0.404478607992 | 0.753555555556 | 0.140896048461 | 0.28 | 2.609090909091 |
| `xgboost` | fold2_validation | 216 | 10 | 22 | 0.322201924694 | 0.890291262136 | 0.095185246072 | 0.5 | 4.909090909091 |
| `xgboost` | pooled_development_oof | 421 | 35 | 44 | 0.339262787141 | 0.8088823094 | 0.117443475264 | 0.342857142857 | 3.280519480519 |

## Frozen Stage125 Part 5 live-successor boundary (expected)

Part 1 executed successfully on the development folds. **Stage125 Part 5 remains a frozen, valid historical closure** — its source, its runner and every `project/stage125/` artifact are byte-identical.

Part 5's *embedded live-Handoff successor check* terminates at the earlier Stage126 primary-development state and predates robustness execution. After a truthful Part 1 completion it therefore reports exactly these five mismatching fields:

- `m1_robustness_started`
- `selected_qc_scope`
- `selected_qc_path`
- `contract_version`
- `last_completed_micro_part`

`run_stage125_part5.py --check` consequently exits 1 **by design**. This is an **expected historical-contract boundary**, not a scientific failure and not Stage125 drift. It is recorded in `stage126_m1_robustness_part1_part5_successor_compatibility.json`, asserted in the Part 1 QC, and explicitly tested (historical Part 5 replay tests use a monkeypatched historical primary-successor fixture — the real Handoff file is never written — and a dedicated live test proves the boundary is exactly these five fields, with no readiness, final-test, authorization or research-pointer drift).

Part 1 successor state is validated by: `stage126_m1_robustness_part0_decision_lock`, `stage126_m1_robustness_part1_qc`, `stage126_m1_robustness_part1_completion_lock`, `ai_handoff_validator`.

## Next

The next registered category is `main_rule_b_listing_robustness` (Part 2). **Part 2 is not authorized and not started** — it requires its own separate explicit human authorization. The final test remains locked and untouched.
