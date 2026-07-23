# Stage126 M1 — Robustness Part 2: Listing Rule B Sample

**Part 2 only. Explicitly human-authorized. Development folds only. Only the sample changed. No retuning occurred. No full-development refit occurred. No final-test predictor or target values were inspected. No final-test evaluation occurred. No SMOTE, SMOTENC or SHAP was executed. Part 3 is not authorized and not started. Primary Stage126 artifacts and Part 1 scientific artifacts remain byte-identical.**

Part 2 is **sensitivity-analysis evidence only**. The observed Part 2 sensitivity ordering **matches** the primary development ordering. Either way, Part 2 does **not** replace the primary results and does **not** select a paper winner.

## Specification

- Category: `main_rule_b_listing_robustness` (changed dimension: `sample`)
- Scientific role: `listing_timing_sample_robustness`
- Sample: `main_rule_b_listing_robustness` (**changed**; primary is `main_rule_a_primary`)
- Input: `project/stage125/part3c_outputs/analysis_ready_main_rule_b_stage125.csv` (`5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480`)
- Target: `FD_target_main_t_plus_1` (unchanged)
- Feature set: `M1_PRIMARY_FEATURE_ORDER` — 9 base features, 18 transformed columns (9 imputed continuous + 9 missingness indicators) (unchanged)
- Imbalance policy: `primary_class_weighting` (unchanged)
- Folds: Fold 1 train 1393-1395 / val 1396-1397; Fold 2 train 1393-1397 / val 1398-1399 (unchanged)
- Model seeds: 20260719, 20260720, 20260721, 20260722, 20260723; Logistic deterministic seed 20260719 (unchanged)
- Model fits: 22; predictions: 22; tuning searches: 0

## Nine-feature primary order (unchanged)

| # | feature | source column | transformation |
|---|---|---|---|
| 1 | `log_total_assets` | `total_assets` | ln(total_assets) if total_assets > 0 else missing |
| 2 | `leverage_ratio` | `leverage_ratio` | frozen_part3c_value |
| 3 | `current_ratio` | `current_ratio` | frozen_part3c_value |
| 4 | `roa_period_adjusted` | `roa_period_adjusted` | frozen_part3c_value |
| 5 | `ocf_to_assets_period_adjusted` | `ocf_to_assets_period_adjusted` | frozen_part3c_value |
| 6 | `asset_turnover_period_adjusted` | `asset_turnover_period_adjusted` | frozen_part3c_value |
| 7 | `operating_margin_period_adjusted` | `operating_margin_period_adjusted` | frozen_part3c_value |
| 8 | `financial_expense_to_assets_period_adjusted` | `financial_expense_to_assets_period_adjusted` | frozen_part3c_value_source_sign_preserved |
| 9 | `accumulated_loss_to_capital_ratio` | `accumulated_loss_to_capital_ratio` | frozen_part3c_value |

`revenue_growth_period_adjusted` remains audit-only and prohibited.

## Rule A versus Rule B sample delta (row identities only)

| scope | Rule A | Rule B | difference |
|---|---|---|---|
| analysis-ready rows | 1012 | 993 | -19 |
| companies | 119 | 117 | -2 |
| positive | 80 | 79 | -1 |
| negative | 932 | 914 | -18 |
| development rows | 666 | 655 | -11 |
| OOF validation rows | 421 | 413 | -8 |
| final-test identities | 346 | 338 | -8 |

Rule B keys are a **strict subset** of Rule A keys (19 Rule A-only rows, 0 Rule B-only rows). The audit compares **row identities only**; aggregate final-test counts are read from the frozen `project/stage125/part4_event_count_gate_stage125.csv`, never from row-level final-test values. Full detail: `stage126_m1_robustness_part2_sample_delta.csv`.

## Development results (sensitivity analysis only)

| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | Recall@10% | Lift@10% |
|---|---|---|---|---|---|---|---|---|---|
| `regularized_logistic_regression` | fold1_validation | 202 | 25 | 22 | 0.48417493284 | 0.878870056497 | 0.168477385195 | 0.44 | 4.04 |
| `regularized_logistic_regression` | fold2_validation | 211 | 10 | 22 | 0.441409584567 | 0.880099502488 | 0.139575999318 | 0.5 | 4.795454545455 |
| `regularized_logistic_regression` | pooled_development_oof | 413 | 35 | 44 | 0.447170385532 | 0.880650037793 | 0.153711786115 | 0.457142857143 | 4.290909090909 |
| `random_forest` | fold1_validation | 202 | 25 | 22 | 0.495077161461 | 0.838192090395 | 0.145455804647 | 0.4 | 3.672727272727 |
| `random_forest` | fold2_validation | 211 | 10 | 22 | 0.353027669548 | 0.886069651741 | 0.115006123076 | 0.5 | 4.795454545455 |
| `random_forest` | pooled_development_oof | 413 | 35 | 44 | 0.401263142511 | 0.861300075586 | 0.12989918767 | 0.428571428571 | 4.022727272727 |
| `xgboost` | fold1_validation | 202 | 25 | 22 | 0.433891505429 | 0.822824858757 | 0.11207095862 | 0.4 | 3.672727272727 |
| `xgboost` | fold2_validation | 211 | 10 | 22 | 0.33918445804 | 0.863184079602 | 0.097540065641 | 0.5 | 4.795454545455 |
| `xgboost` | pooled_development_oof | 413 | 35 | 44 | 0.34195953388 | 0.836734693878 | 0.10464718521 | 0.428571428571 | 4.022727272727 |

## Observed sample sensitivity vs the primary run (reported)

- Primary pooled PR-AUC ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Part 2 observed pooled PR-AUC ordering: `regularized_logistic_regression` > `random_forest` > `xgboost`
- Observed ordering differs from primary: **false**

| model family | primary pooled PR-AUC | Part 2 pooled PR-AUC | absolute change | relative change | direction |
|---|---|---|---|---|---|
| `regularized_logistic_regression` | 0.445756964048 | 0.447170385532 | 0.001413421484 | 0.317083432901% | improved |
| `random_forest` | 0.40244183002 | 0.401263142511 | -0.001178687509 | -0.292883945225% | declined |
| `xgboost` | 0.356545008162 | 0.34195953388 | -0.014585474282 | -4.090780672316% | declined |

This is a **development-only sensitivity finding** produced by changing the sample and nothing else. It does **not** replace the primary results, does **not** change the locked primary ordering used for confirmatory interpretation, and does **not** select a paper winner. It is reported to the human supervisor and triggered no automatic scientific action: selected configurations are unchanged, no refit was authorized, and the final test remains locked. Full detail: `stage126_m1_robustness_part2_primary_comparison.json`.

## Final-test lock

- Final-test identities seen but never parsed: **338**
- Final-test predictor rows loaded: **0**
- Final-test target rows loaded: **0**
- Final-test evaluations: **0**
- Full-development refits: **0**

## Frozen Stage125 Part 5 live-successor boundary (expected)

**Stage125 Part 5 remains a frozen, valid historical closure** — its source, its runner and every `project/stage125/` artifact are byte-identical. Part 5's *embedded live-Handoff successor check* terminates at the earlier Stage126 primary-development state and predates robustness execution. After a truthful Part 2 completion it reports exactly these five mismatching fields:

- `m1_robustness_started`
- `selected_qc_scope`
- `selected_qc_path`
- `contract_version`
- `last_completed_micro_part`

`run_stage125_part5.py --check` consequently exits 1 **by design**. This is an **expected historical-contract boundary**, not a scientific failure and not Stage125 drift. It is recorded in `stage126_m1_robustness_part2_part5_successor_compatibility.json`, asserted in the Part 2 QC, and explicitly tested.

The successor-aware Part 5 **test file** has three recorded generations: the Stage125 historical hash pinned by the frozen Part 5 metadata (`0a117c1916ad845653e148d951a49a2c0375d13b7de23019e50ae891aee1b437`), the Part 1 completion-time hash (`62cd1593e7bfafdeb1aa1c728f3fb9c22aadf50d3031e2cec964d267e752b189`), and the recomputed Part 2 current hash. All three are recorded separately in `stage126_m1_robustness_part2_part5_successor_compatibility.json`; the Part 1 hash is history, never the current hash. Replaying the frozen Part 5 build would differ in exactly two self-describing bookkeeping files — `metadata_and_hashes_stage125_part5.json`, `stage125_part5_readiness_closure_qc_report.json` — while **every Part 5 scientific artifact stays byte-identical**.

## Next

The next registered category is `expanded_rule_a_company_scope_robustness` (Part 3). **Part 3 is not authorized and not started** — it requires its own separate explicit human authorization. Parts 3-6 remain outstanding, so the overall M1 robustness program is **not** complete. The final test remains locked and untouched.
