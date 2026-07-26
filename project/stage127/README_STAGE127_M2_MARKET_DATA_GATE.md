# Stage127 — M2 Market-Data Admission Gate

**Gate status: `UNRESOLVED_M2_DATA_GATE`**

Development-only point-in-time data admission gate for the frozen three-variable M2 market block. This Gate answers only whether the frozen M2 variables can be obtained with correct timing, quality, coverage, joins and event support. It does **not** answer whether M2 improves prediction. No model was fit, no prediction was generated, and no final-test row was read.

## Frozen M2 block (unchanged)

| variable | candidate_id |
|---|---|
| `equity_return_window` | `cand_m2_equity_return_window` |
| `realized_volatility` | `cand_m2_realized_volatility` |
| `amihud_illiquidity` | `cand_m2_amihud_illiquidity` |

Source: `src_m2_tsetmc_market` (TSETMC market data). Formula contract option `M2-A_modified`; shared 12-calendar-month window ending on the last eligible trading day **strictly before** each pair's cutoff; adjusted close only; >=126 usable observations; no imputation, scaling, extrapolation, annualization or threshold reduction.

## Why UNRESOLVED

- No probe reached the authoritative TSETMC source from this execution environment, so no candidate_endpoint_evidence could be captured and no accessibility score could be assigned.
- Zero market observations were retrieved, so candidate coverage, block common coverage and event-count feasibility could not be evaluated against the frozen thresholds.
- The corporate-action-adjusted closing price field required by the frozen contract could not be verified as obtainable; unadjusted close was not substituted.

`UNRESOLVED` is deliberately **not** `FAIL`. The frozen R-A mapping requires `missing_evidence = null_or_unresolved_never_zero`: no probe reached the authoritative source, so no property of the source was observed. Scoring 0-2 (a hard drop) would assert an unobserved property and wrongly close the M2 path. No M2 variable was dropped and the frozen three-variable block was not redefined.

## Development scope (real, computed)

- Development pairs: **666** (sample `main_rule_a_primary`, target `FD_target_main_t_plus_1`, target years 1393-1399)
- Coverage denominator: 666 rows; candidate threshold 0.8, block common threshold 0.7
- Numerators are UNRESOLVED (no observation retrieved), which is distinct from an observed zero.

## Final-test firewall

`final_test_locked=true`; unlocked / access_authorized / predictor_values_inspected / target_values_inspected / evaluation_performed all `false`. Final-test target years 1400-1402 were excluded structurally before any value was read, and final-test coverage was not used for admission.

## Next action

Not eligible to start `stage127-m2-incremental-evaluation`: that requires BOTH data admission and development comparison feasibility to pass, and both are UNRESOLVED. This Gate result requires human review.

## Files

- `stage127_m2_candidate_accessibility.csv`
- `stage127_m2_candidate_coverage_audit.csv`
- `stage127_m2_common_sample_audit.csv`
- `stage127_m2_development_features.csv`
- `stage127_m2_gate_qc_report.json`
- `stage127_m2_join_leakage_audit.json`
- `stage127_m2_market_data_gate_decision.json`
- `stage127_m2_market_data_gate_human_authorization_record.json`
- `stage127_m2_source_manifest.json`
