# Stage127 — M2 Market-Data Admission Gate

**Gate status: `FAIL_M2_DATA_GATE`**

Development-only point-in-time data admission gate for the frozen three-variable M2 market block, decided **offline from imported authoritative TSETMC evidence**. This Gate answers only whether the frozen M2 variables can be obtained with correct timing, quality, coverage, joins and event support. It does **not** answer whether M2 improves prediction. No model was fit, no prediction was generated, and no final-test row was read.

## Evidence

- Bundle: `stage127_m2_tsetmc_full_delivery.zip`
- SHA256: `d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec`
- Size: 13,464,145 bytes
- Instrument mappings: **110**; retrieval ranges: **111** (105 SUCCESS / 6 PARTIAL / 0 FAILED)
- Normalized daily rows: **163,230** (2012-09-22 … 2020-07-18)
- Restricted raw evidence files: **222**, all SHA256-verified
- The external QC flag was **not** trusted: every count, the raw → normalized field mapping (all rows), and the adjusted-close exact-date join were independently recomputed in this repository.
- The Gate is reproducible **without a network connection** once the bundle is present. Endpoint reachability plays no part in the decision and can never produce a PASS.

## Frozen M2 block (unchanged)

| variable | candidate_id | usable pairs | coverage |
|---|---|---:|---:|
| `equity_return_window` | `cand_m2_equity_return_window` | 400/666 | 0.6006 |
| `realized_volatility` | `cand_m2_realized_volatility` | 581/666 | 0.8724 |
| `amihud_illiquidity` | `cand_m2_amihud_illiquidity` | 581/666 | 0.8724 |

Source: `src_m2_tsetmc_market` (TSETMC market data). Formula contract option `M2-A_modified`; shared 12-calendar-month window ending on the last eligible trading day **strictly before** each pair's cutoff; adjusted close only; >=126 usable observations; no imputation, scaling, extrapolation, annualization or threshold reduction. The 111 external ranges are retrieval supersets and were **not** used as scientific windows; every window W was recomputed per pair from the frozen contract.

## Gate decision conditions

| condition | met |
|---|---|
| `A_data_admission_g01_g08` | yes |
| `B_each_candidate_coverage_ge_0_80` | no |
| `C_common_sample_coverage_ge_0_70` | no |
| `D_both_validation_windows_ge_5_positives` | yes |
| `E_no_pit_leakage_join_provenance_blocker` | yes |
| `F_all_three_frozen_m2_variables_present` | yes |

- Three-variable common sample: **400/666** = 0.6006 (threshold 0.7)
- Positive evaluable observations in the locked validation windows (common M2 sample): `fold1_validation` = 18, `fold2_validation` = 7; negatives: `fold1_validation` = 107, `fold2_validation` = 157

## Why `FAIL_M2_DATA_GATE`

- B: observed development valid coverage for 'equity_return_window' is 0.6006 (400/666), below the frozen threshold 0.8
- C: observed three-variable common-sample coverage is 0.6006 (400/666), below the frozen threshold 0.7

This is an **observed** result computed from real imported evidence against the frozen thresholds. It is deliberately not softened into `UNRESOLVED`, and no threshold was reduced, no value imputed, and no M2 variable dropped. The frozen three-variable block was not redefined; redefining it would require a separate explicit human decision.

## Final-test firewall

`final_test_locked=true`; unlocked / access_authorized / predictor_values_inspected / target_values_inspected / evaluation_performed all `false`. Final-test target years 1400-1402 were excluded structurally before any value was read, final-test coverage was not used for admission, and every imported observation date was independently checked against the firewall (latest imported observation: 2020-07-18).

## Next action

Not eligible to start `stage127-m2-incremental-evaluation`. M2 was not automatically redesigned and M3 was not started; this result requires human review.

## Files

- `stage127_m2_candidate_accessibility.csv`
- `stage127_m2_candidate_coverage_audit.csv`
- `stage127_m2_common_sample_audit.csv`
- `stage127_m2_development_features.csv`
- `stage127_m2_event_count_feasibility.csv`
- `stage127_m2_external_delivery_import_qc.json`
- `stage127_m2_external_delivery_provenance.json`
- `stage127_m2_gate_qc_report.json`
- `stage127_m2_join_leakage_audit.json`
- `stage127_m2_market_data_gate_decision.json`
- `stage127_m2_market_data_gate_human_authorization_record.json`
- `stage127_m2_source_manifest.json`
