# Stage129 — Final Test execution (the one-time pass)

This package is the result of the single authorized pass over the held-out
years **۱۴۰۰–۱۴۰۲**. The Final Test firewall, which stood untouched through
every prior action in the programme, is now **spent**. It may never be opened
again.

The result below is reported exactly as computed. It was accepted before it
was seen: the model, the preprocessing statistics, the threshold, the metric
set, the bootstrap parameters and all twenty-one controls were frozen in commit
`dfd5b5d` **before** the pass, and nothing was changed, re-run or re-selected
afterwards.

## What ran

One invocation of the frozen executor, in the locked runtime:

```
/Users/aliehpourdast/anaconda3/bin/python3 project/src/stage129_final_test_execution.py --execute-final-test --write
```

* invocations: **1** — dry runs: **0** — retries: **0**
* executor SHA-256: `d85234ee4c7e2b14dc21084348a059fceb083cf8bcc0ecbf30ee64eef79c56a4`
* runtime: python 3.13.5, numpy 2.4.6, pandas 3.0.3, scikit-learn 1.9.0,
  jdatetime 6.0.1, xgboost 3.3.0 — matched element-wise against the locked
  development runtime by `FT03`.

`--execute-final-test` is the entry-point gate. Without `--write` the executor
self-labels the run a dry run and emits no package; `PRE01` excludes "any
computational dry run", so `--write` is what makes the authorized pass the real
one.

## The result

**Evaluation set:** ۳۴۶ cohort pairs, ۳۴۶ evaluable rows (**۱۲** positive /
**۳۳۴** negative, prevalence `0.03468`) across ۱۱۹ tickers; ۳۴۶ predictions.
Zero development rows entered the evaluation.

| metric | value | 95% cluster-bootstrap interval |
|---|---|---|
| **PR-AUC** (primary) | **0.243879669979** | `[0.053272572767, 0.541675572242]` |
| ROC-AUC | 0.907684630739 | `[0.787834897749, 0.97144045144]` |
| Brier score | 0.071625345916 | `[0.053164118058, 0.092580775647]` |
| Recall@10% | 0.666666666667 | — |
| Lift@10% | 6.407407407407 | — |

The metric set is **closed**: `additional_metrics_computed = 0`. The primary
metric was not changed after seeing results.

The frozen executor computes intervals for the three metrics above only. The
two top-K metrics carry no interval because `K_y = ceil(0.10 * N_y)` is not
stable under a ticker resample that changes `N_y`.

**Read the primary interval honestly.** The contract's own low-positive caveat
applies and is not softened here: with **12** positives the `PR-AUC` interval is
very wide, and its lower bound `0.0533` sits close to the `0.0347` base rate.
This single evaluation does not establish a precise effect size. No inference
is claimed — `holm_executions = 0`, `p_values_computed = 0`,
`inferential_superiority_claim = false`.

**Top-K detail:** `K_y = 12` in each of the three years, 36 rows selected, 8 of
the 12 positives captured, pooled precision among selected `0.2222`.
`K_optimized_after_results = false`.

**At the admitted operating point** `0.426878838687` (development-OOF
F2-maximizing, tie-break `higher_threshold`, read from the attempt-3 artifact
and never derived here): **TP ۸ / FP ۴۳ / TN ۲۹۱ / FN ۴**.

**Uncertainty:** paired company-cluster bootstrap on `ticker`, 2000 replicates,
**1998** valid under the both-classes rule (floor of 1000 satisfied),
percentile-95, seed `20260724`. No parameter was changed after seeing results.

## What did not happen

`model_fits_executed = 0`, `refits_executed = 0`, `tuning_runs = 0`,
`hyperparameter_searches = 0`, `feature_searches = 0`, `threshold_searches = 0`,
`recalibration_executions = 0`, `isotonic_executions = 0`, `shap_executions = 0`,
`holm_executions = 0`, `p_values_computed = 0`, `winner_selections = 0`.

The model was **applied**, never fitted — reconstructed from the pinned
intercept and 18 explicit coefficients of the accepted PR #90 artifact.
Preprocessing statistics came from PR #90 verbatim and were verified
element-wise on the way into the locked `transform()`; nothing was re-estimated
on the Final Test. The missingness indicators are each row's **own**
pre-imputation NaN positions, which `FT08` re-derives from the raw rows rather
than trusting. Probabilities are **raw** — no recalibration of any kind.

The three locked development results were re-hashed before and after the pass
and are byte-identical (`FT14`). No historical artifact, contract or package was
edited.

## Controls

All twenty-one fail-closed controls `FT01`–`FT21` executed real logic and
**PASS**. Each aborts the run with `ABORT_FINAL_TEST [FTxx]` on failure; there
is no continue-on-error path. `FT05` is the mirror image of the refit's `FC03`:
there Final Test years were forbidden in the fit window, here development years
are forbidden in the evaluation window, because evaluating on development rows
would silently report an in-sample result.

## Two recorded interpretations

Both were confirmed by the human supervisor before the pass, and neither edits a
merged or historical artifact. They are recorded in
`stage129_final_test_execution_interpretation_record.json`:

* **INT01** — `uncertainty.bootstrap_execution_authorized_by_this_contract =
  false` in the PR #91 contract artifact scoped the **contract-lock action
  itself**, which executed nothing. It is not a standing prohibition on a later,
  separately authorized execution, so the independent `PRE01` authorization
  permits the full contract including the locked bootstrap. No bootstrap
  parameter was changed.
* **INT02** — `usable_for_final_test = false` on the threshold artifact is the
  **historical state** of the moment `PRE01` was unresolved. It is
  **superseded — not corrected** — by the independent `PRE01` record. The
  historical artifact is left byte-identical.

## What this authorizes

Nothing further. The firewall status is `SPENT_BY_AUTHORIZED_SINGLE_PASS`.

Two different kinds of fact are recorded, and they must not be conflated.
`final_test_rows_read = 346` and `final_test_evaluation_performed = true` are
**events**: the evaluation happened. The **permission** keys are back where
they were, because the one-action `PRE01` authorization was CONSUMED by this
pass — `final_test_access_authorized = false`, `final_test_unlocked = false`,
`final_test_locked = true`. The Final Test is shut again, and nothing here
advertises a standing permission to reopen it.

* second pass authorized — **false** (a second pass is refused outright by
  `FT11` and by the executor's per-root guard, not merely unauthorized)
* `stage130_started = false`, `stage130_authorized = false`
* `merge_authorized = false`, `ready_for_review_authorized = false`

No result in this package may reopen model selection, retune, refit,
recalibrate, add a metric, or rewrite a manuscript claim. The pointer is
`human_authorization_required_for_ready_for_review_and_merge`, authorized =
**false**.

## Package contents

Sealed by `metadata_and_hashes_stage129_final_test_execution.json`, which
records the SHA-256 and byte count of every file below:

| file | SHA-256 | bytes |
|---|---|---|
| `stage129_final_test_metrics.json` | `0b1ea6c086430d6ecc65432c8001cc3b028422e7c1293a9ea2fb6c44d7ef4392` | 2452 |
| `stage129_final_test_predictions.json` | `654c8c50b25d90b6811901708876b542a9ede87598ad58ca1a35a5a5e3dba37b` | 84455 |
| `stage129_final_test_provenance_record.json` | `5b5d4d66ed4ca0770667547752c0436380c8960f0d5296f62bda83b3fa80c551` | 3694 |
| `stage129_final_test_qc_report.json` | `016eaa19149a9247574e13931e9aae4a10fede26316a63f1321a6643c96ad9f5` | 5926 |

The manifest itself hashes to
`0ac59f9bef0fc984b78b3398a8ffe022906a07953db236331c892b8d6b73c4c9` (1310 bytes).

Alongside the sealed package, and deliberately **outside** the manifest:

* `stage129_pre01_human_authorization_record.json` — the independent PRE01
  authorization, merged before the pass
* `stage129_final_test_execution_interpretation_record.json` — INT01 and INT02
* this README

Executor: `project/src/stage129_final_test_execution.py`.
Regression tests: `project/tests/test_stage129_final_test_execution.py`.
