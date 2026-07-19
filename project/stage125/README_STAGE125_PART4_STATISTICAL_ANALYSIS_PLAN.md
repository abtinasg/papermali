# Stage125 Part 4 — Statistical Analysis Plan

**Status:** Locked research-design / contract surface only.
**Contract version:** `stage125_part4_sap_v2` (v1 retained in Git history).
**Research action:** `stage125-part4-statistical-analysis-plan`
**Next:** `stage125-part5-readiness-closure`

## Scope

Part 4 locks the statistical analysis plan for future Stage126 modeling:

- primary sample `main_rule_a_primary` (1012 / 119 / 80 / 932)
- primary target `FD_target_main_t_plus_1`
- M1 primary ordered feature set (exactly 9 admitted)
- M1 coverage-audit candidates (exactly 10, including rejected revenue growth)
- M1 target-proximity robustness set (exactly 6)
- nested M2–M4 blocks (9 / 12 / 15 / 19; conditional; no data collected here)
- target-year temporal folds and locked final test 1400–1402
- strict positive / negative / missing target event accounting
- preprocessing with pre-imputation missingness masks
- model families, finite hyperparameter budget, seeds
- SMOTE robustness disables class weighting (no combined oversampling+weights)
- PR-AUC primary; Recall@10% / Lift@10%; calibration; paired ticker-cluster bootstrap; Holm
- SHAP stability contract (no SHAP computation in Part 4)

## Development-comparison feasibility is a target-level conjunction

Development-comparison feasibility is decided per `sample_design × target` as a
conjunction across **both** locked temporal validation windows:

```text
development_comparison_feasibility_met
  iff fold1_validation_positive >= 5 AND fold2_validation_positive >= 5
else development_comparison_not_supported
```

The aggregate `development` event-count row reports this conjunction result; it
is never an independent label derived from the aggregate development positive
count. The `fold1_train`, `fold2_train`, and `all` rows carry the neutral label
`event_count_only_not_an_independent_claim_gate` and are never claim gates. The
generic `eligible_for_comparative_claims` label is removed.

Consequences (all four sample designs):

- `FD_target_article141_only_t_plus_1` has `fold1_validation_positive = 17` but
  `fold2_validation_positive = 3`, so development comparison is **unsupported**,
  and with `final_test_positive ∈ {0, 1}` its final-test analysis is
  **descriptive-only** (no comparative or inferential claim).
- `FD_target_main_t_plus_1` and
  `FD_target_persistent_loss_robustness_t_plus_1` remain development-supported
  and final-test claim-eligible.

## v2 methodological correction

Human supervisor rejected `revenue_growth_period_adjusted` from admitted M1
because raw Fold 1 training coverage `148/245 = 0.6040816327` is below the
locked 0.75 threshold. The unauthorized first-observation denominator exception
is removed. The feature remains in frozen Part 3C data and in the coverage
audit as `rejected_m1_primary_coverage_gate_failed`.

## Explicit non-claims

- No model was fitted (`model_fit_calls = 0`).
- No prediction was generated (`prediction_calls = 0`).
- No SHAP value was calculated.
- Final-test predictor values were not used for admission, tuning, or selection.
- Final-test event thresholds control claim eligibility only, not feature admission.
- Stage126 remains unauthorized and unstarted.
- Modeling remains unstarted.
- M3 remains unavailable pending an authoritative CBI source.
- No M2/M3/M4 values were collected.
- Active availability lag remains four Jalali calendar months.
- Financial data and targets remain frozen.
- `رمپنا|1396 → رمپنا|1397` remains audit-only.
- Part 3C outputs remain unchanged (SHA-256 pinned).

## Runners

```bash
python project/run_stage125_part4.py --build
python project/run_stage125_part4.py --check
```

`--build` is offline and deterministic. `--check` performs zero writes.
