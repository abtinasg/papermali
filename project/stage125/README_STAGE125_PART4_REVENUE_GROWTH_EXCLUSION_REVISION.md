# Stage125 Part 4 — Revenue-Growth Exclusion Revision

**Status:** active human-supervisor methodological correction.
**Decision date:** 2026-07-19
**Contract:** `stage125_part4_sap_v2`

## Decision

`revenue_growth_period_adjusted` is **rejected** from admitted M1 primary
features because raw Fold 1 training coverage fails the locked minimum
fold-training coverage threshold:

```text
148 / 245 = 0.6040816327  <  0.75
```

Overall development coverage passes (`565 / 666 = 0.8483483483` ≥ 0.80), but
that is not sufficient for M1 admission.

## Explicit non-authorizations

- No coverage-denominator exception.
- No first-observation exclusion from the fold denominator.
- Missing first observations remain missing observations.
- Imputation later in a training pipeline does **not** retroactively change
  feature-admission coverage.

## Retention

- Retained in frozen Part 3C datasets.
- Retained in the development coverage audit as
  `rejected_m1_primary_coverage_gate_failed`.
- Removed from `M1_PRIMARY_FEATURE_ORDER`,
  `M1_TARGET_PROXIMITY_ROBUSTNESS`, and all nested M2–M4 modeling surfaces.

## Immutable scientific state

Financial values, targets, sample membership, temporal folds, final-test years,
and Part 3C hashes are unchanged.
