# Addendum E — Stage126+ Q1/Q2 Methods and Governance Update

**Date:** 2026-07-26

**Parent contract:** [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md)

**Status:** forward-looking addendum. The historical Stage125 decisions remain unchanged. This addendum governs Stage126+ after merge.

## E1. What this addendum changes

This addendum does **not** change the frozen scientific design already established in Stage125:

- primary Rule A sample;
- primary `FD_target_main_t_plus_1` target;
- M1 primary nine-feature order;
- M1 registered robustness set;
- temporal folds and final-test years;
- model families;
- primary PR-AUC metric;
- point-in-time leakage controls;
- M2–M4 nested-block concept;
- final-test lock.

It changes two things only:

1. it raises the explicit reporting/evaluation standard to a Q1/Q2-grade prediction-study level; and
2. it replaces over-engineered repository governance with the proportional control model in [`STAGE126_Q1Q2_LEAN_GOVERNANCE.md`](STAGE126_Q1Q2_LEAN_GOVERNANCE.md).

## E2. Q1/Q2 methodological review outcome

The original design already had the core elements expected in a strong prediction study: point-in-time predictor timing, temporal development/evaluation separation, a pre-specified primary metric, a locked final test, calibration, paired block comparison, bootstrap uncertainty, multiplicity control, limited model families, negative-result reporting and explainability stability.

The review identified the following items that must be made explicit in the final workflow:

### A. Uncertainty is mandatory

The blueprint previously listed **"no CI"** as a reviewer risk. This is no longer acceptable as an unresolved design gap.

For final manuscript results:

- primary performance estimates must carry 95% uncertainty intervals where estimable;
- M2–M4 value-add comparisons must use paired ticker-cluster bootstrap deltas on matched observations;
- the number/fraction of valid bootstrap resamples must be reported when a metric is undefined in event-poor resamples;
- unstable uncertainty must lead to a descriptive interpretation, not a superiority claim.

### B. Calibration must be reported honestly

At minimum:

- Brier score;
- calibration curve;
- calibration intercept and slope when estimable.

With low event counts, calibration slope/intercept may be too unstable. In that case, report the failure/instability explicitly and retain Brier + calibration plot. Do not manufacture a precise calibration claim.

### C. Final-test semantics must be precise

The 1400–1402 holdout is a **locked temporal evaluation set**. It is not an external validation dataset because it comes from the same underlying market/universe and study pipeline.

The paper must not use "external validation" for this holdout.

### D. Final-test event count limits inference

The primary final test contains roughly 12 positive events. Therefore:

- the final test cannot select a winner;
- final-test results cannot trigger retuning, feature changes or threshold optimization;
- event-poor subgroup/industry analyses are descriptive only;
- Article-141-only final-test evidence remains descriptive;
- wide/unstable uncertainty must be shown rather than hidden.

### E. Common-sample paired comparisons are required

Incremental claims are valid only when the compared blocks are evaluated on a common eligible sample with paired predictions, or when sample differences are explicitly reported and the claim is limited accordingly.

M2–M4 must report:

- rows/companies/events entering the common sample;
- attrition from the parent block;
- paired metric deltas;
- uncertainty of those deltas;
- whether the data Gate materially changes the event composition.

### F. Development and evaluation decisions remain separate

All of the following must be decided from development evidence before final-test access:

- admitted feature blocks;
- preprocessing;
- selected hyperparameters;
- retained model/design;
- comparison family;
- uncertainty procedure;
- calibration reporting method;
- claim hierarchy.

The final test estimates performance of the frozen design; it does not participate in design selection.

### G. Reproducibility must be paper-facing

The final reproducibility package must identify:

- source/provenance rules;
- point-in-time availability assumptions;
- target/sample/split contracts;
- exact admitted predictors;
- missing-data and preprocessing rules;
- exact model configurations;
- runtime/software versions;
- canonical prediction and metric artifacts;
- deviations from the SAP;
- code revision used for canonical execution.

Repository engineering hashes that do not affect scientific reproducibility are not manuscript claims.

## E3. Reporting benchmark

As a high methodological benchmark, the project adopts the general prediction-study principles of transparent reporting and explicit separation of model development from performance evaluation reflected in:

- Collins GS et al. **TRIPOD+AI statement**. BMJ. 2024;385:e078378. doi:10.1136/bmj-2023-078378.
- Moons KGM et al. **PROBAST+AI**. BMJ. 2025;388:e082505. doi:10.1136/bmj-2024-082505.

These references are used as cross-domain methodological benchmarks only. The paper remains a finance/accounting prediction study and must follow the target journal's own author instructions and disciplinary conventions.

## E4. Stage126+ governance supersession

For Stage126+ engineering mechanics, the following historical Part 0 change-control language is superseded where it conflicts with the lean-governance addendum:

- a change to an operational test file is **not** itself a research-design change;
- a change to QC formatting/assertion inventory is **not** itself a research-design change;
- a Handoff refresh is **not** a research action;
- an operational metadata/hash update is **not** a scientific re-analysis unless it changes or redefines scientific provenance/results;
- earlier Parts must not validate the current workflow state of later Parts.

The following remain research-design changes and still require explicit versioned scientific authorization:

- target, universe, eligibility, cutoff or temporal split;
- frozen feature/block definition;
- model-family set;
- tuning budget after modeling starts;
- selected configuration after freeze;
- primary metric/inferential plan;
- full-development refit;
- final-test unlock/evaluation;
- any scientific change after final-test inspection.

## E5. Reviewer-facing risk register after this update

The remaining major risks are substantive rather than repository-mechanical:

1. **Operational target vs legal distress definition** — mitigate with precise target construction, robustness targets and no legal-equivalence claim.
2. **Small positive-event count** — mitigate with conservative model complexity, temporal design, uncertainty reporting and limited claims.
3. **Four-month assumed availability lag** — label explicitly as a regulatory/methodological assumption and test sensitivity where pre-specified.
4. **Temporal overfitting** — small model family, finite tuning budget, temporal folds, locked final evaluation.
5. **Low macro degrees of freedom** — small theory-driven M3 only; Gate may legitimately fail.
6. **Generalizability** — no external-validation claim; discuss TSE/time-period limits explicitly.
7. **Incremental-block sample attrition** — paired common-sample reporting and event-count disclosure.
8. **Calibration instability** — Brier/curve always; slope/intercept only when estimable.
9. **Multiplicity / researcher degrees of freedom** — pre-specified comparison family, Holm only where planned, no post-hoc feature/model search.
10. **Explainability overclaim** — descriptive/stability-focused SHAP or coefficients, no causal interpretation.

The former repository-engineering risk "repeated pipeline corrections" should be documented as project process history if relevant, but it must not be allowed to generate new scientific degrees of freedom or an endless maintenance loop.

## E6. Completion criterion

The paper is ready for final manuscript assembly only after:

- all retained blocks have passed their data Gates;
- development evidence and uncertainty are complete;
- the retained design is frozen;
- full-development refit is completed without final-test access;
- the locked temporal final evaluation is run once;
- post-test interpretation changes no model decision;
- explainability/stability outputs are descriptive and frozen;
- every table/figure/claim traces to scientific output;
- limitations, negative results and deviations from the SAP are explicit;
- the final Q1/Q2 reporting checklist is completed.
