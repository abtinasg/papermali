# Stage128 — retain M2 as the intermediate confirmatory block

**Action id:** `stage128-m2-retained-block-human-decision`
**Decision type:** `human_retained_block_decision_only_no_scientific_execution`
**Decision outcome:** `RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK`
**Baseline:** `abtinasg/papermali` `main` @ `bdac807788b377690be0a879765cfe4ac148970d`

## What was decided

M2 is **retained as the intermediate block** of the preregistered nested
confirmatory chain `M1 → M2 → M3 → M4`, and remains the comparator for a future
paired `M3 − M2` evaluation — but only if the M3 data Gate is **separately
authorized** and passes.

This is a **retained-block decision, not a superiority decision.**

## What was NOT decided

Retention does **not** imply predictive improvement, does **not** imply
statistical significance, does **not** select a paper winner, does **not**
select a final model, does **not** authorize a full-development refit, and does
**not** unlock or authorize the final test. M3 and M4 remain unauthorized and
unstarted.

## The evidence, unchanged

The M2 incremental comparison was development-only and completed under its own
one-action authorization (roadmap item 24, PR #71):

* common sample **539 / 666** development rows — 55 positive, 484 negative,
  108 companies;
* parent-to-common-sample attrition **127 / 666** rows — 13 positive, 114
  negative, 53 distinct companies (proportion `0.1906906907`);
* pooled locked-validation OOF **366 rows, 28 positive**;
* post-lock D2 eligibility audit: **53 comparisons, 35** descriptive
  `|SMD| ≥ 0.10` flags — interpretation-limiting only; they changed no sample
  membership, weighting, matching, D2 construction or model specification.

Primary pooled OOF PR-AUC deltas (M2 − M1):

| family | delta | 95% CI |
| --- | --- | --- |
| regularized logistic regression | +0.008530265112 | [−0.021177343686, +0.035281506756] |
| random forest | −0.007313160157 | [−0.049131999282, +0.031850216682] |
| xgboost | +0.018802067544 | [−0.026163341118, +0.072970509355] |

**All three intervals include zero and the point-estimate signs disagree across
model families. The observed M2 evidence is approximately null and does not
support a superiority claim.** Negative or null incremental evidence remains a
reportable scientific result, and it is reported here rather than rewritten.

## Why retain, then

Retention is a **governance/design** decision. It preserves the prospectively
defined nested confirmatory architecture and avoids post-outcome deletion or
redefinition of the `M3 − M2` comparator after the M2 results were observed.
The incomplete Holm family (`M2_minus_M1`, `M3_minus_M2`, `M4_minus_M3`) stays
incomplete and its final adjustment stays deferred.

## Exact retained M2 definition (frozen as already evaluated)

M1 base features, in exact order:

1. `log_total_assets`
1. `leverage_ratio`
1. `current_ratio`
1. `roa_period_adjusted`
1. `ocf_to_assets_period_adjusted`
1. `asset_turnover_period_adjusted`
1. `operating_margin_period_adjusted`
1. `financial_expense_to_assets_period_adjusted`
1. `accumulated_loss_to_capital_ratio`

M2 adds exactly `equity_return_window`, `realized_volatility`,
`amihud_illiquidity`. `equity_return_window` keeps its frozen D2 semantics
`BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN` under the Gregorian
calendar convention. `zero_trade_day_ratio_W` remains **eligibility-audit-only** and
is not an M2 predictor. Nothing else about D2, the boundary-month convention,
`W`, `t0`, `T*`, the trading-day sequence, daily-return adjacency, the 126-return
floors, realized-volatility or Amihud construction, source evidence, coverage
thresholds, the sample rule, preprocessing, model families, selected
configurations, temporal folds, metric definitions, the bootstrap design or the
multiplicity family was reopened.

## No scientific execution

This package was built **only by reading existing committed evidence**: zero
model fits, zero predictions, zero new OOF rows, zero resampling, zero bootstrap
or Holm execution, zero p-values, zero calibration runs, zero SHAP, zero
full-development refits, and zero final-test predictor or target values read.
The builder imports the standard library only; the focused tests assert that it
cannot reach an estimator `.fit()` / `.predict()` / `.predict_proba()` or any
resampling procedure.

## Pointers

* `last_completed_research_action_id` = `stage128-m2-retained-block-human-decision`
* `next_research_action_id` = `stage128-m3-macro-data-gate`
* `next_research_action_pointer_is_not_authorization` = **true**

The M3 Gate is a pointer only. It is not authorized, no macro data was
collected, no M3 variable was created, no M3 Gate was executed and no M3 model
was fit.

## Protected immutability scope

The immutability guarantee covers **every tracked file that existed at baseline
commit `bdac807788b377690be0a879765cfe4ac148970d`** under `project/stage128/m2_incremental_evaluation/`
and `project/stage127/`, plus these individually protected files:

* `project/stage128/stage128_m2_d2_development_features.csv`
* `project/stage126/stage126_m1_retained_design_freeze.json`
* `project/stage126/stage126_m1_selected_configurations.json`
* `project/stage125/part4_metrics_uncertainty_contract_stage125.json`

The path set is enumerated **from the baseline commit itself**, never from the
working tree, and the complete SHA-256 manifest of the baseline bytes is
committed as `protected_files_sha256` in both the decision artifact and the
metadata artifact (`protected_baseline_commit`, `protected_file_count`,
`protected_files_sha256`). Verification requires: every protected path still
present, every protected file byte-identical to baseline, no new tracked file
inside a protected tree, an identical path set, a manifest count equal to the
independently enumerated count, and an empty
`git diff --name-only bdac807788b377690be0a879765cfe4ac148970d..HEAD` over the protected paths — a
**committed-history** comparison, not a working-tree comparison.

Baseline blobs are hashed as **opaque bytes only**. They are never parsed,
decoded or evaluated, so no final-test predictor or target value is read.

The smaller `source_artifacts_sha256` field lists only the artifacts whose
numeric values this decision re-derives. It is **not** the immutability scope.

## Package

* `stage128_m2_retained_block_human_decision.json` — the decision
* `stage128_m2_retained_block_human_authorization_record.json` — the only
  authoritative location of the exact human utterance, with the derived
  normalized scope recorded separately and labelled as derived
* `metadata_and_hashes_stage128_m2_retained_block_human_decision.json`
* `stage128_m2_retained_block_human_decision_qc_report.json`
