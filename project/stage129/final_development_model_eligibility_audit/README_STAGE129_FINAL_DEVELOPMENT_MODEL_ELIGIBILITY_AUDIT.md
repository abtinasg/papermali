# Stage129 — final development model eligibility audit

**Action id:** `stage129-final-development-model-eligibility-audit`
**Type:** read-only audit over committed, frozen artifacts. No execution, no selection.

The question this audit answers is **not** "which model is best". It is: *do the
already-frozen rules and already-committed results determine the final block and
the final algorithm uniquely, or is a separate human decision still required?*

## Verdicts

| audit | verdict |
| --- | --- |
| block | **`FINAL_BLOCK_REQUIRES_HUMAN_DECISION`** |
| algorithm | **`FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION`** |
| Holm reporting | **`HOLM_FINAL_REPORTING_REQUIRES_SEPARATE_HUMAN_OR_METHODS_DECISION`** |

`audit_determined_candidate = null` for both. Nothing is selected.

Both verdicts rest on an **absence** of a rule, not a conflict between rules —
which is why neither is `CONTRACT_CONFLICT_...`. And because six candidates are
eligible, neither is `NO_*_CURRENTLY_ELIGIBLE_UNDER_FROZEN_RULES` either.

## Which blocks are still eligible

M1 and M2 only. M3-CBI and M4 were both discontinued **before admission and
before any modeling**, so neither ever produced a model to be eligible.

## Why "M2 retained" is not "M2 selected"

This is the distinction the audit was most at risk of collapsing, and the frozen
record settles it explicitly. `project/stage128/m2_retained_block_human_decision/stage128_m2_retained_block_human_decision.json`
lists under `m2_retention_does_not_imply`:

> `predictive_improvement`, `statistical_significance`, `paper_winner_selection`,
> **`final_model_selection`**, `full_development_refit_authorization`, …

and gives the basis as
`preregistered_nested_confirmatory_architecture_preservation_not_observed_predictive_superiority`,
with `decision_is_a_retained_block_decision_not_a_superiority_decision = true`
and `m2_role = intermediate_confirmatory_block`.

M2 was retained to preserve the nested architecture and to remain the comparator
for `M3−M2`. That is a structural role, not a selection.

## Why the absence of M2 superiority does not force M1

It would be convenient to reason "M2 showed no superiority, therefore M1 wins".
**No frozen rule says that.** The contracts are silent on which block is final
when superiority is absent. Applying that reasoning would be inference, not
rule-following, so the audit records the ambiguity and selects nothing.

The committed M2 evidence, quoted and never recomputed — paired cluster-bootstrap
percentile-95 CIs on the 366-row common sample:

| family | PR-AUC Δ (M2−M1) | 95% CI | excludes 0 |
| --- | --- | --- | --- |
| logistic | +0.008530 | [−0.021177, +0.035282] | no |
| random forest | −0.007313 | [−0.049132, +0.031850] | no |
| xgboost | +0.018802 | [−0.026163, +0.072971] | no |

No PR-AUC interval excludes zero, and the point-estimate signs disagree
(`families_agree_on_point_estimate_sign = false`). Brier intervals *do* exclude
zero for all three, but in **conflicting directions** — random forest worse,
logistic and xgboost better. A secondary metric that disagrees with the primary
metric cannot break a tie that no frozen rule authorizes breaking.

## Why no unique algorithm follows

Four independent reasons, any one of which is sufficient:

1. **No selection rule exists.** The metrics/uncertainty contract fixes
   `primary_metric = PR-AUC` for *reporting*. Its only winner-related clause is a
   *prohibition* (`do_not_select_winner_on_calibrated_final_test = true`). Its
   only `tie_break` is `thresholded_secondary.tie_break = higher_threshold` — a
   rule for choosing a **threshold**, not a model.
2. **All three families are retained, not narrowed.**
   `stage126_m1_retained_design_freeze.json#retained_model_families` freezes
   *three* configurations and sets `final_model_selected = false`. A selected
   configuration *per algorithm* is not a selected final algorithm.
3. **The ordering is unstable.** See below.
4. **The one prespecified ranking mechanism was never run.**
   `confirmatory_family_1 = [Logistic_vs_RF, Logistic_vs_XGBoost, RF_vs_XGBoost]`
   under Holm was never executed, so no adjusted inferential ranking exists.

And the frozen record contains an explicit prohibition on doing it anyway —
`stage126_m1_robustness_closure_synthesis_record.json`:

> This evidence does NOT justify changing the primary result, **selecting a
> winning model family**, retuning any configuration, opening the final test, or
> automatically freezing a retained design.

## Robustness ordering — reported, never used to cherry-pick

Locked primary pooled development-OOF ordering:
**logistic (0.4458) > random forest (0.4024) > xgboost (0.3565)**.

| part | role | ordering |
| --- | --- | --- |
| 1 | target-proximity six-feature | **xgboost > RF > logistic — fully reversed** |
| 2 | listing Rule B sample | preserved |
| 3 | expanded company scope | preserved |
| 4 | combined sample | preserved |
| 5 | persistent-loss target | preserved pooled, **top two inverted within fold 1** (RF 0.6010 > logistic 0.5664) |
| 6 | SMOTENC imbalance | preserved |

Five of six preserve the primary ordering; Part 1 reverses it outright, and Part
5 conceals a per-fold inversion. **No candidate is excluded on these grounds and
no robustness part is promoted to primary** — the instability is reported because
it is evidence about determinability, and using it to drop a candidate would be
exactly the outcome-driven selection the contracts forbid.

## Holm family — reconciled, not executed

| member | status | p-value |
| --- | --- | --- |
| `M2_minus_M1` | `EVALUATED_NO_SUPERIORITY_ESTABLISHED` | `null` |
| `M3_CBI_minus_M2` | `NOT_EXECUTED_M3_CBI_DISCONTINUED` | `null` |
| `M4_minus_M3_CBI` | `NOT_EXECUTED_M4_DISCONTINUED` | `null` |

All three members survive; none is removed, renamed or substituted; the family is
not shrunk post hoc; `holm_family_complete` stays `false`. **No p-value exists for
`M2_minus_M1`** — the committed evidence is bootstrap confidence intervals, and
this audit creates none.

The frozen multiplicity contract fixes membership, correction and alpha but is
**silent on how to close or report a family two of whose three prespecified
members were never executed**. Hence the Holm reporting verdict above. The
Stage129 M4 reporting decision settled how the M4 comparison is *presented*, not
how the family is *closed*.

## Terminology the audit keeps separate

`M2 retained` ≠ `M2 final block selected` · `M2 evaluated` ≠ `M2 superiority
established` · `best point estimate` ≠ `paper winner` · `retained design` ≠
`final model` · `selected configuration per algorithm` ≠ `selected final
algorithm` · `eligible candidate` ≠ `authorized refit` · `development winner` ≠
`Final Test result`.

## A note on surface incomparability

M1 pooled-OOF PR-AUC comes from the **1263-row** primary development lock. M2
values come from the **366-row** paired common sample, whose own M1 arm reads
differently (logistic 0.477497, RF 0.355559, xgboost 0.355762). The two surfaces
are not interchangeable, and this audit does not compare across them.

## What this audit did NOT do

No fit, predict, `predict_proba` or `decision_function`; no tuning, feature
search or threshold search; no bootstrap or resampling; no new metric, CI or
p-value; no calibration or SHAP; no row-level scientific data read; no historical
artifact modified; no paper winner or final model selected; no full-development
refit; no Stage130; no Final Test predictor or target read. Every counter in the
governance boundary is `0`.

M1, M2, M3-CBI, M4 and M3-LAG-WDI all keep their existing dispositions. Final
Test stays locked with `rows_read = 0`. `next_research_action_authorized` stays
`false`, and the audit pointer is `human_decision_required` — a pointer is never
an authorization.

## Files

- `stage129_final_model_eligibility_audit_verdict.json` — the three verdicts,
  their rule citations and the questions answered.
- `stage129_final_model_eligibility_matrix.json` — the 6-candidate machine-readable
  eligibility matrix.
- `stage129_robustness_ordering_record.json` — all six locked robustness orderings.
- `stage129_final_model_eligibility_audit_governance_boundary.json` — what stays shut.
- `metadata_and_hashes_stage129_final_development_model_eligibility_audit.json`.

Regression tests:
`project/tests/test_stage129_final_development_model_eligibility_audit.py`.
