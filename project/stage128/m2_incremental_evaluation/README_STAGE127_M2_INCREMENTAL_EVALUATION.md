# Stage127 — paired M2 versus M1 incremental evaluation (frozen Gregorian D2 common sample)

**Action:** `stage127-m2-incremental-evaluation` — one authorized execution, consumed.

**Development-only.** No final-test predictor or target value was read, no final-test model was fit, no configuration was retuned, no feature was searched, no winner was selected and M3/M4 were not started.

## What was compared, and on which rows

Both blocks were REFITTED on exactly the same common-sample training rows and evaluated on exactly the same common-sample validation rows. The original 666-row M1 results are NOT compared against these 539-row M2 results; that comparison would confound sample restriction with model change and is deliberately not made.

- Parent M1 development surface: 666 rows (68 positive, 110 companies)
- M2 three-variable common sample: 539 rows (55 positive, 484 negative, 108 companies)
- Attrition: 127 rows (0.190690690691) — reported, never interpreted as model improvement
- Pooled locked-validation OOF rows: 366 (28 positive)

## Blocks

- **M1** (9 features): `log_total_assets`, `leverage_ratio`, `current_ratio`, `roa_period_adjusted`, `ocf_to_assets_period_adjusted`, `asset_turnover_period_adjusted`, `operating_margin_period_adjusted`, `financial_expense_to_assets_period_adjusted`, `accumulated_loss_to_capital_ratio`
- **M2** (12 features): the nested M1 set plus `equity_return_window`, `realized_volatility`, `amihud_illiquidity`
- `equity_return_window` is measured ONLY by the frozen `BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN` (GREGORIAN) construct, taken from `equity_return_d2`. The historical D0 equity return is NOT an active predictor. `zero_trade_day_ratio_W` appears only in the eligibility audit.

## Post-lock D2 eligibility audit (descriptive only)

- Eligible rows: 539 — ineligible: 127
- Comparisons: 53 across 6 dimensions; 35 carry |SMD| ≥ 0.1
- An SMD flag is descriptive. No row was removed, no weighting or matching was introduced, D2 was not changed, the Gate was not revised and no model design was altered. Flags limit INTERPRETATION and are recorded in the decision limitations.

## Observed paired results (primary metric: PR-AUC)

| family | M1 | M2 | M2−M1 | 95% CI | direction |
| --- | --- | --- | --- | --- | --- |
| `regularized_logistic_regression` | 0.477497460644 | 0.486027725756 | 0.008530265112 | [-0.021177343686, 0.035281506756] | approximately_null_interval_includes_zero |
| `random_forest` | 0.355559464623 | 0.348246304466 | -0.007313160157 | [-0.049131999282, 0.031850216682] | approximately_null_interval_includes_zero |
| `xgboost` | 0.355762083254 | 0.374564150798 | 0.018802067544 | [-0.026163341118, 0.072970509355] | approximately_null_interval_includes_zero |

Secondary metrics (ROC-AUC, Brier, Recall@10%, Lift@10%), fold-level results and the full paired bootstrap are in `stage127_m2_block_model_metrics.csv` and `stage127_m2_paired_bootstrap_delta_summary.json`.

## Multiplicity

- Confirmatory family: `M2_minus_M1`, `M3_minus_M2`, `M4_minus_M3`
- Available here: `M2_minus_M1` only
- `holm_family_complete = False`, `holm_final_adjustment_deferred = True`
- The three-member family is NOT redefined as a single hypothesis, and no one-comparison Holm adjustment is presented as a completed family adjustment.

## Interpretation

This action reports OBSERVED development evidence. It creates no new PASS/FAIL threshold for M2 predictive value, selects no winner, retains and rejects nothing, and makes no causal or superiority claim.

- The comparison is restricted to the 539-row three-variable M2 common sample; 127 parent development rows are absent and the absent rows differ from the retained rows on flagged predictor-side dimensions (see the post-lock eligibility audit).
- Only 28 positive events are available across the two pooled locked validation windows, so all interval estimates are wide and fold-level estimates are unstable.
- The confirmatory multiplicity family is incomplete; no family-level adjusted inference is available in this action.
- Development evidence only. Nothing here is a final-test result and nothing here selects a winner or a retained block.

**A human retained-block decision is required** and is explicitly NOT made here.

## Counters

primary predictive model fits = 44; final-test predictor values read = 0; final-test target values read = 0; final-test predictions = 0; full-development refits = 0; M3 executions = 0; M4 executions = 0; winners selected = 0.
