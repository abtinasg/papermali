# Stage128 — canonical M2 data-admission Gate RE-RUN (Gregorian D2)

**Action:** `stage128-m2-d2-gate-rerun` — one authorized execution, consumed.

**Gate result: `PASS_FOR_M2_INCREMENTAL_EVALUATION`**

Re-run on real imported evidence under the frozen Gregorian D2 equity-return specification, every frozen data-admission condition, coverage threshold and event-support requirement is satisfied. This is DATA ADMISSION only: it makes M2 incremental evaluation scientifically ELIGIBLE for a new explicit human authorization; it does not authorize it, and it says nothing about whether M2 improves prediction.

## What this Gate re-ran, and what it did not

This is the SAME canonical M2 data-admission Gate that Stage127 executed, with exactly one difference: the equity-return slot of the frozen three-variable M2 block is measured under the already-frozen Stage128 D2 specification `BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN` (GREGORIAN calendar convention), frozen by `stage128-m2-boundary-month-return-design-freeze`.

No new design decision was made here. D0/D1/D2/D3 selection was not reopened, Gregorian was not re-compared against Jalali, no threshold was changed, no boundary tolerance was searched, and the Gate outcome was not used to redesign D2. `W`, `t0`, `T*`, the trading-day sequence, daily-return adjacency, realized volatility, Amihud and both 126 floors are the unchanged frozen Stage127 primitives, called directly.

The historical Stage127 D0 Gate result (`FAIL_M2_DATA_GATE`) is preserved unchanged in its own Stage127 artifacts; nothing here rewrites it.

## Evidence

- Bundle: `stage127_m2_tsetmc_full_delivery.zip`
- SHA256: `d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec` (independently verified before execution)
- Normalized daily observations: 163230
- Instrument mappings: 110 — retrieval ranges: 111 — restricted raw files: 222
- The same immutable bundle as the historical Gate. No fresher dataset, no widened period, no replaced PARTIAL range, no backfill, no substitute source, and no reachability-based evidence.

## Conditions A–F (each reported separately)

- **A — G01–G08 source/data-quality admission:** True
- **B — each candidate coverage ≥ 0.8:** True
  - `equity_return_window`: 539/666 = 0.8093 vs 0.8 → True
  - `realized_volatility`: 576/666 = 0.8649 vs 0.8 → True
  - `amihud_illiquidity`: 576/666 = 0.8649 vs 0.8 → True
- **C — three-variable common-sample coverage ≥ 0.7:** True (539/666 = 0.8093)
- **D — ≥ 5 positive evaluable observations in BOTH locked validation windows:** True
  - `fold1_validation`: positives 18, negatives 141 (threshold 5 positives)
  - `fold2_validation`: positives 10, negatives 197 (threshold 5 positives)
- **E — no PIT/leakage/join/provenance blocker:** True
- **F — all three frozen M2 variables present:** True

## D2 diagnostics (descriptive only — never tuning inputs)

- D2 unusable: 127/666
- `LT126_VALID_RETURNS`: 90
- `NO_START_BOUNDARY_PRICE`: 55
- `NO_END_BOUNDARY_PRICE`: 17
- `ZERO_START_BOUNDARY_PRICE`: 0
- Causes are non-exclusive and do not sum to the unusable total.

## Pre-lock cross-check (AFTER canonical reconstruction)

The pre-lock predictor-only reference was 539/666. The canonical re-run observed 539 (difference +0). The reference was NOT an input to this Gate and was never hard-coded as its outcome; a discrepancy triggers provenance investigation, never a design search.

## What this result does NOT authorize

The Gate PASSED **data admission only**. It does not say that M2 improves prediction, and it authorizes nothing further.

`stage127-m2-incremental-evaluation` is identified as a POINTER only. It requires a new, explicit human authorization (`m2_incremental_evaluation_authorized = false`). No model was fit, no prediction generated, no winner selected, and the final test remains locked.

The post-lock eligibility audit frozen by the design-freeze contract remains REQUIRED before any M2 predictive result is interpreted. It was not executed here and is not a condition of this Gate.

## How development target labels were used (literal statement)

Development target labels **were** read by this Gate, through the unchanged frozen Stage127 machinery. They were used for exactly three limited descriptive / event-support audits:

1. condition-D positive evaluable event counts in the two locked validation windows;
2. target-stratified descriptive candidate coverage (`positive_row_coverage` / `negative_row_coverage`);
3. the descriptive positive/negative composition of the three-variable common sample (55 positive / 484 negative of 539).

Nothing else. Explicitly: no predictive performance metric, no model fit, no prediction, no target-based design selection, no target-based feature selection, no threshold tuning, no target value written into the pair-level predictor artifact (`stage128_m2_d2_development_features.csv` carries no target column), and no final-test target or predictor access. The machine readable form is `development_target_label_use.declared_uses` in the decision JSON (`declared_uses_are_exhaustive = True`).

## Counters

development target labels accessed for the three declared descriptive/event-support audits above = YES; target values used for any predictive, design, feature-selection or tuning purpose = NONE; model fits = 0; predictions = 0; final-test access = 0; canonical Gate executions in this action = 1 (the authorized re-run); historical D0 Gate changed = NO; M2 admitted for modeling = DATA ADMISSION ONLY.
