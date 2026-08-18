# Stage130 Phase 1 — manuscript claim freeze

Every claim below is pinned to a committed artifact and an exact committed
value. Wording outside this file is not frozen and is not authorized.

**PR-AUC is the primary metric.** ROC-AUC, Brier score, Recall@10% and
Lift@10% are secondary. The metric set was closed before the Final Test was
opened and no metric was added afterwards.

No confirmatory inference and no superiority test was conducted:
`p_values_computed = 0`, `holm_executions = 0`,
`inferential_superiority_claim = false`. The Holm family is incomplete and its
final adjustment is deferred. No claim of superiority over any model, block or
comparator is permitted anywhere in the manuscript.

---

## C1 — Primary predictive performance

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`
* **Committed value:** PR-AUC = `0.243879669979`,
  95% cluster-bootstrap interval `[0.053272572767, 0.541675572242]`
* **Final Test prevalence (reported separately):** `0.03468208092485549`
* **Permissible wording:** "On the held-out Final Test the model achieved a
  PR-AUC of 0.243879669979 (95% cluster-bootstrap CI
  0.053272572767–0.541675572242). The Final Test
  prevalence was 0.03468208092485549."
* **Prohibited overclaim:** stating or computing any ratio of PR-AUC to
  prevalence, including "approximately 7x prevalence" or any equivalent
  multiple. The two quantities are reported separately and are never combined.
  No claim of accuracy, reliability or readiness for deployment.
* **Mandatory accompanying limitation:** the interval is wide and its lower
  bound lies close to the prevalence, so this single evaluation does not
  establish a precise effect size.

## C2 — Discrimination

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`
* **Committed value:** ROC-AUC = `0.907684630739`, 95% CI
  `[0.787834897749, 0.97144045144]`
* **Permissible wording:** "ROC-AUC was 0.907684630739 (95% CI
  0.787834897749–0.97144045144)." Report the
  number only.
* **Prohibited overclaim:** the words "strong", "excellent", "high",
  "outstanding" or any synonym applied to ROC-AUC; any use of ROC-AUC as
  evidence of superiority; leading the abstract with ROC-AUC in place of the
  primary metric.
* **Mandatory accompanying limitation:** under severe class imbalance,
  ROC-AUC is less informative about positive-class retrieval and must be
  interpreted alongside the pre-specified primary PR-AUC.

## C3 — Brier score

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`
* **Committed value:** Brier = `0.071625345916`, 95% CI
  `[0.053164118058, 0.092580775647]`
* **Permissible wording:** "The observed Brier score on raw, unrecalibrated
  predicted probabilities was 0.071625345916."
* **Prohibited overclaim:** any statement that calibration was assessed,
  evaluated or established; any claim that the model "is well calibrated";
  any calibration slope, intercept, curve or reliability statement.
  `recalibration_executions = 0` and `isotonic_executions = 0`.
* **Mandatory accompanying limitation:** calibration was **not** fully
  assessed. A single Brier score at a low event rate is not a calibration
  assessment.

## C4 — Threshold-based operating performance

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`, threshold from `project/stage129/threshold_derivation_attempt3/stage129_threshold_value_attempt3.json`
* **Committed value:** threshold `0.426878838687`; TP `8`,
  FP `43`, TN `291`, FN `4`
* **Permissible wording:** "At the pre-specified operating threshold
  0.426878838687, derived from pooled development out-of-fold
  predictions only, the confusion counts were TP 8, FP 43,
  TN 291, FN 4."
* **Prohibited overclaim:** describing the threshold as optimal, tuned or
  selected on the Final Test; deriving any new threshold.
* **Mandatory accompanying limitation:** the threshold was fixed before Final
  Test access and was not re-derived afterwards.

## C5 — Top-10% screening

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`
* **Committed values:** Recall@10% = `0.666666666667`,
  Lift@10% = `6.407407407407`; `K_y = ceil(0.10 * N_y)`;
  36 rows selected; 8 of
  12 positives captured
* **Permissible wording:** report both as **point estimates**, explicitly
  noting that no confidence interval is available for either.
* **Prohibited overclaim:** attaching any interval, standard error or
  significance statement to these two metrics; computing one now.
* **Mandatory accompanying limitation:** per-year capture counts rest on very
  few events and support no stability claim in either direction.

## C6 — Robustness and temporal design

* **Source:** `project/stage126/stage126_m1_robustness_closure_synthesis_record.json`, `project/stage125/part4_temporal_split_contract_stage125.json`
* **Permissible wording:** six pre-registered robustness categories provide
  **sensitivity evidence only**; validation was strictly forward-chaining with
  no shuffling and no random split.
* **Committed value:** the primary ordering is preserved in Parts
  2, 3, 4, 5 and 6; Part 1 is the sole reversal. Derived from
  `part_summaries[*].primary_ordering_preserved` in the locked source, which is
  the only per-part flag covering every registered category.
* **Prohibited overclaim:** presenting robustness as model selection, as proof
  of generalization, or as a superiority argument.
* **Mandatory accompanying limitation:** the primary ordering was preserved in
  Parts 2, 3, 4, 5 and 6 and not in Part 1; no winner was selected
  on this evidence.

## C7 — Explainability

* **Source:** `project/stage129/full_development_refit_execution/stage129_full_development_refit_model.json`, `project/stage129/full_development_refit_execution/stage129_full_development_refit_preprocessing_parameters.json`
* **Committed values:** intercept plus 18 coefficients
* **Permissible wording:** "regularized conditional associations"; odds ratios
  per 1-SD increase for standardized continuous features and for
  indicator = 1 versus 0 for the binary missingness indicators.
* **Prohibited overclaim:** causal language; variable-importance ranking;
  significance marks; confidence intervals or p-values on any coefficient;
  reordering terms by magnitude.
* **Mandatory accompanying limitation:** coefficients are penalized (L2,
  C = 0.1) and conditional on the remaining terms. Six of the nine
  missingness-indicator coefficients are exactly zero in the locked model;
  three are non-zero. This pattern is reported descriptively and does not
  establish statistical significance or a general claim that missingness is
  informative.

## C8 — Sample size and precision

* **Source:** `project/stage129/final_test_execution/stage129_final_test_metrics.json`, `project/stage129/final_test_execution/stage129_final_test_provenance_record.json`
* **Committed values:** 346 evaluable rows,
  **12 positive** and 334 negative observations,
  119 unique tickers; development fit set 666 rows
  with 68 positives
* **Permissible wording:** "Only 12 positive observations were
  present in the Final Test." This must appear explicitly in the Results and
  the Limitations.
* **Prohibited overclaim:** any precision, stability or generalization claim
  that the event count cannot support.

## C9 — Reproducibility and auditability

* **Source:** `project/stage129/final_test_execution/stage129_final_test_qc_report.json`, `project/stage129/final_test_execution/metadata_and_hashes_stage129_final_test_execution.json`, `project/stage129/final_test_execution/stage129_final_test_provenance_record.json`
* **Committed values:** 21 fail-closed controls FT01-FT21 all PASS; one pass;
  `model_fits_executed = 0`;
  `final_test_rows_read = 346`
* **Permissible wording:** the executor was frozen and hashed before Final Test
  access; the Final Test was opened exactly once; artifacts are SHA-256 pinned.
* **Prohibited overclaim:** describing this as external or independent
  validation.

## C10 — Outcome definition (DEFINITIONAL, not inferential)

This section states what is predicted. Every rule below is copied verbatim from
the committed target-definition table; **no value here is estimated, tuned,
derived or inferred**, and none of it is a result.

* **Source:** `project/stage122/target_definition_stage122.csv`
* **Committed rules:**
  * `fd_accumulated_loss` — 1 if accumulated_loss/registered_capital >= 0.5; 0 if < 0.5; missing if registered_capital <=0/missing OR accumulated_loss missing.
  * `fd_negative_equity` — 1 if equity<0; 0 if equity>=0; missing if equity missing.
  * `fd_ocf_high_leverage` — 1 if OCF<0 AND liabilities/assets>0.70; definite 0 if OCF>=0 OR leverage<=0.70; missing otherwise (three-valued).
  * `fd_article141_direct` — 1 if direct Article-141 inclusion verified from a controlled source; 0 if non-inclusion verified; else missing. Stage121 has NO such source -> missing for ALL rows.
  * `FD_target_main` — modified three-valued OR with non-blocking unavailable direct Article-141 evidence. 1 if any criterion definitely 1; 0 if all evaluable quantitative criteria definitely 0; missing otherwise. NOT an Article-141 target.
* **Permissible wording:** the primary outcome is a composite **operational**
  indicator aggregated by a modified three-valued OR, in which unknown evidence
  is recorded as unknown and never as healthy.
* **Prohibited overclaim:** describing `FD_target_main` as an Article-141
  target, as legal insolvency, or as a bankruptcy filing; restating any
  threshold in a different form; treating the unobserved direct Article-141
  criterion as though it had been evaluated.
* **Mandatory accompanying limitation:** direct Article-141 evidence is
  unobserved for every row in this panel, so the composite rests on the
  remaining quantitative criteria alone.

## C11 — Development performance and the observed ordering

* **Source:** `project/stage126/stage126_m1_development_metrics.csv`
* **Committed values (pooled development out-of-fold PR-AUC):**
  `regularized_logistic_regression` = `0.445756964048`,
  `random_forest` = `0.40244183002`,
  `xgboost` = `0.356545008162`
* **Permissible wording:** report these as **observed development out-of-fold
  values** that make the stated ordering auditable. Per-fold values for all
  three families are displayed in the development-performance table.
* **Prohibited overclaim:** any paired difference, ratio, delta, average,
  re-rounding, significance statement or superiority inference computed from
  these values; presenting them as Final Test performance; presenting the
  ordering as a model-selection result.
* **Mandatory accompanying limitation:** these are development values under the
  locked folds, not held-out performance, and no uncertainty interval,
  multiplicity adjustment or comparative test accompanies them.

## C12 — Data construction and QC (DESCRIPTIVE/PROVENANCE, not a result)

This section states how the analysis table was built and what the committed
checks found. **It is descriptive provenance evidence, not a new scientific
result**: no value here is estimated, tuned, derived or inferred, and none of
it is a performance quantity.

* **Sources:** `project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/qc_report_stage121.json`, `project/stage122/stage122_qc_report.json`,
  `project/stage125/README_STAGE125_PART1_DATA_CONTRACT.md`, `project/stage125/part4_statistical_analysis_plan_stage125.json`
* **Displayed by:** `manuscript_results_tables/table_9_data_construction_and_qc.csv`
* **Committed values (upstream source panel):**
  1331 firm-year rows,
  130 companies, Jalali fiscal years
  1392-1402;
  1331 unique row keys,
  0 duplicate keys,
  0 missing keys; accounting identity checked
  on 1312 evaluable rows with 1311
  exact matches,
  1 match
  within the recorded tolerance of 1 million IRR and
  0 failures; the
  7 recorded ratio families recalculated with 0 mismatches.
* **Committed values (Stage122 target QC):** 98 positive,
  1205 negative and 28 unknown target states;
  `no_missing_target_converted_to_zero =
  true`;
  `rows_preserved =
  true`
  (1331 rows in, 1331 rows out); source-file
  provenance present for 1303 rows and absent for 28.
* **Committed values (prespecified analysis plan):**
  `active_availability_lag_months = 4`,
  `active_availability_method = fixed_regulatory_lag`,
  `row_level_publish_datetime_collection_required =
  false`.
* **Permissible wording:** report these as committed checks and their exact
  results, each with its scope named. Structural keys were complete and
  nonduplicated; the accounting identity reconciled; the recorded ratio
  recalculations produced no mismatch; unknown target evidence was preserved
  as unknown.
* **Prohibited overclaim:** any unqualified statement that this is a
  "high-quality dataset"; any claim of complete row-level provenance, of all
  observations being fully traceable, or of verified point-in-time filing
  dates; describing the panel as an open dataset or an open benchmark;
  presenting any figure in this section as a scientific result; collapsing the
  upstream panel, the eligible pairs, the development fit set and the Final
  Test cohort into one cohort.
* **Mandatory accompanying limitation:** provenance is file-level and covers
  1303 of 1331 rows, leaving
  28 without a recorded source file; row-level publication
  timestamps were never collected, so the four-month availability rule is a
  prespecified proxy rather than an observed filing date; and the company
  panel is restricted-access, not openly redistributable.

---

## Standing prohibitions for the manuscript

1. No second Final Test pass, and no re-reading of Final Test rows.
2. No new metric, interval, replicate, p-value, subgroup or per-year
   performance value.
3. No calibration curve, decision curve or net-benefit quantity.
4. No refit, recalibration, tuning, model reselection or SHAP.
5. No causal claim from a predictive model.
6. No statement that the full repository test suite passes.
