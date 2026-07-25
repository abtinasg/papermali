# Stage126+ Q1/Q2 Lean Research Governance

**Status:** authoritative forward-looking governance addendum for Stage126+ after merge.

**Date:** 2026-07-26

**Scope:** this document changes the *engineering and governance mechanics* used to complete the paper. It does **not** change the frozen scientific target, sample definitions, temporal split, M1 feature definitions, selected M1 configurations, existing M1 scientific results, or final-test lock.

## 1. Purpose

The project must remain rigorous enough for a serious Q1/Q2-level academic prediction study without treating ordinary repository maintenance like a banking, aerospace, or safety-critical software certification program.

The governing principle from this point forward is:

> **Scientific decisions and scientific outputs are hard-locked; engineering support files are version-controlled, reviewable, and mutable.**

The goal is reproducible, leakage-safe, pre-specified research with transparent uncertainty and claim control — not transitive hash chains over every test, QC file, README, Handoff, or commit.

This document is a project-specific governance standard. It uses the transparent-reporting principles in TRIPOD+AI (Collins et al., BMJ 2024;385:e078378) and the development/evaluation risk-of-bias separation in PROBAST+AI (Moons et al., BMJ 2025;388:e082505) as a **cross-domain methodological benchmark only**. Those tools were developed for healthcare prediction research and are not claimed to be finance-specific reporting requirements.

## 2. What remains hard-locked

The following are **scientific control surfaces**. A change requires an explicit, versioned research decision before the change is used for new scientific results:

- target definition and target timing;
- study universe and sample eligibility rules;
- prediction cutoff / point-in-time availability logic;
- temporal development folds and locked final-test years;
- admitted predictor definitions and ordered feature sets for a frozen model block;
- model-family set for a frozen comparison;
- tuning budget and search space once the corresponding modeling action starts;
- selected configuration after development selection is closed;
- preprocessing semantics that can affect predictions, including imputation, scaling, missingness indicators and resampling;
- canonical OOF predictions and scientific metric tables from a completed analysis;
- retained-design freeze before full-development refit;
- final-test lock, final-test access authorization, and final-test results;
- any numeric claim used in the paper.

For these surfaces, provenance and hashes remain appropriate.

## 3. What is no longer a scientific lock

The following are **operational / engineering surfaces**. They remain tracked in Git and reviewed, but they are not immutable scientific artifacts and should not create a new research authorization merely because their bytes change:

- unit/integration tests;
- pytest markers and test-collection configuration;
- QC report formatting and assertion inventory;
- metadata files that describe code/test/QC state rather than scientific data/results;
- Handoff files and generated current-state prose;
- README files;
- documentation wording;
- validator implementation details, provided the validator continues to enforce the scientific controls above;
- operational registries whose only role is repository bookkeeping;
- commit SHAs used only as engineering anchors.

Git history is the provenance record for these operational files. They may be corrected or refactored in a maintenance PR without a new scientific decision **unless** the change can alter scientific data, model predictions, metric values, or final-test access.

## 4. No transitive operational hash chain

For new Stage126+ work, do **not** build a transitive chain such as:

`test hash -> QC hash -> metadata hash -> registry hash -> Handoff hash`.

A scientific analysis should instead have a small scientific manifest that pins only the artifacts required to reproduce or audit the scientific result, for example:

- admitted-data manifest / source provenance;
- split manifest;
- exact feature/configuration contract;
- canonical prediction file;
- canonical metric file;
- final scientific lock / analysis manifest;
- software environment / code revision used for canonical execution.

Operational tests and documentation can verify those artifacts, but their own hashes are not recursively promoted into scientific locks.

## 5. One live current-state authority

There must be **one** authoritative live-state surface for the current research stage.

Earlier scientific Parts may verify their own frozen scientific outputs, but they must not assert that the *current project state* still equals the state that existed when that Part was closed.

Therefore:

- historical state is preserved by Git history and frozen scientific artifacts;
- current state is validated by the current-stage validator / current-stage state record;
- a later legitimate state transition must not force regeneration of earlier scientific packages;
- stale historical assertions about current workflow state are maintenance issues, not scientific blockers.

## 6. Human authorization policy

Separate authorization remains mandatory when the proposed action changes research degrees of freedom or exposes the locked final test.

### Explicit research authorization required

- target change;
- universe / eligibility / sample-rule change;
- cutoff or availability-rule change;
- adding/removing predictors from a frozen block;
- changing model families;
- changing the tuning/search budget after modeling starts;
- retuning after the retained configuration is frozen;
- changing the primary metric or inferential comparison plan;
- retained-design selection/freeze;
- full-development refit;
- final-test unlock/access/evaluation;
- any post-final-test model or feature change;
- new scientific analysis not already present in the roadmap/SAP.

### No separate scientific authorization required

- fixing or refactoring tests;
- updating README or documentation;
- Handoff refresh;
- QC/metadata formatting changes;
- validator refactor that preserves scientific gates;
- adding a historical marker to an operational test;
- correcting operational repository bookkeeping;
- infrastructure changes that cannot alter canonical scientific outputs or final-test access.

These maintenance changes still require code review and a green verification gate.

## 7. PR granularity

The default unit is **one meaningful research milestone per PR**, not one file, one assertion, one Handoff refresh, or one minor robustness mechanic per PR.

Recommended pattern:

- data-admission Gate PR (no model fitting);
- conditional modeling/evaluation PR only if the Gate passes;
- one synthesis/closure PR only when a genuine research milestone needs synthesis.

Do not create follow-up Handoff-only PRs merely because an engineering anchor moved, unless the Handoff itself is the deliverable.

Commit count is never an acceptance criterion.

## 8. Verification tiers

### Tier A — docs-only / wording-only

Required:

- document consistency check;
- `git diff --check`;
- no scientific artifact changes.

Full modeling tests are not required.

### Tier B — infrastructure / tests / validator / metadata

Required:

- focused tests for the changed infrastructure;
- current-state/final-test-lock checks;
- repository full test suite when practical;
- proof that scientific artifacts did not change.

Temporary model fits triggered by regression tests are engineering verification, not canonical scientific execution, provided they use development data only and write no canonical scientific result.

### Tier C — scientific execution

Required:

- canonical environment;
- pre-run contract checks;
- point-in-time / leakage checks;
- focused scientific tests;
- canonical output manifest;
- full relevant test suite;
- scientific artifact hashes;
- final-test firewall checks;
- clear development-vs-final-test separation.

## 9. Q1/Q2 scientific quality gate

A research action may feed the manuscript only when the following are satisfied or transparently declared not estimable.

### 9.1 Population, target and timing

- exact sample formation is reported;
- positive / negative / unknown target states remain distinct;
- missing target is never treated as healthy;
- prediction is `t -> t+1` under the locked point-in-time cutoff;
- all predictor availability assumptions are reported;
- the four-Jalali-month lag is described as a methodological/regulatory assumption, not an observed publication timestamp.

### 9.2 Development and evaluation separation

- temporal folds are pre-specified and unchanged;
- all imputation/scaling/resampling is fitted inside training folds only;
- model selection, feature admission and tuning use development data only;
- the final temporal test remains unopened until the retained design is frozen;
- the 1400–1402 holdout is described as a **locked temporal evaluation set**, not external validation.

### 9.3 Common-sample incremental comparisons

For M2–M4, incremental value must be evaluated on the same eligible rows whenever possible:

- M2 vs M1 on the M2 common sample;
- M3 vs M2 on the M3 common sample;
- M4 vs M3 on the M4 common sample.

Report the common-sample attrition and event counts before interpreting a delta.

### 9.4 Performance reporting

At minimum report:

- PR-AUC as the primary discrimination metric;
- ROC-AUC as complementary discrimination;
- Brier score;
- Recall@10% and Lift@10% as screening metrics;
- calibration curve;
- calibration intercept/slope when estimable and stable enough to report.

Do not force calibration slope/intercept when the event count makes them unstable; report the limitation and retain Brier + calibration plot.

### 9.5 Uncertainty and multiplicity

The previous reviewer-risk item **"no CI" is closed as a design gap** by requiring uncertainty reporting in the final paper workflow.

- report 95% uncertainty intervals for primary performance estimates where estimable;
- for pre-specified nested block comparisons, use paired ticker-cluster bootstrap deltas on matched predictions;
- report the number/fraction of valid bootstrap resamples for metrics that can become undefined in event-poor resamples;
- do not convert unstable/poorly estimable intervals into superiority claims;
- use Holm adjustment only for the pre-specified family of inferential comparisons defined in the SAP; do not create a post-hoc multiplicity family after seeing results.

### 9.6 Small-event-count claim control

The final temporal test has a low positive-event count (approximately 12 under the primary target). Therefore:

- no algorithmic winner may be selected from the final test;
- no model/feature/tuning decision may be changed after final-test inspection;
- final-test comparisons with unstable uncertainty are descriptive;
- subgroup/industry claims require adequate event counts; otherwise report only distributions/descriptive patterns;
- Article-141-only final-test evidence remains descriptive because its event count is too small for confirmatory comparison.

### 9.7 Model stability and explainability

- report development-fold / temporal stability of performance;
- report seed stability for stochastic models;
- SHAP/coefficient interpretation is descriptive, not causal;
- explanation stability is assessed across seed/fold/time where feasible;
- do not present one SHAP plot as evidence of a stable mechanism.

### 9.8 Transparency and reproducibility

The reproducibility package must identify:

- data/source provenance and access assumptions;
- sample/target/split contracts;
- exact features and preprocessing;
- model families and selected hyperparameters;
- software/runtime versions;
- code revision used for canonical scientific execution;
- canonical OOF/final prediction outputs and metric definitions;
- deviations from the SAP and their authorization/justification;
- limitations and negative results.

Every manuscript number must trace to a scientific artifact, table-generation output, or citable external source.

## 10. M1 transition rule

Existing M1 primary and completed Parts 1–5 remain scientifically valid and frozen.

The legacy repository mechanics that pinned historical tests/QC/metadata are **not** a scientific reason to reopen or rerun those analyses.

Before Part 6 is finalized, a maintenance implementation may simplify the live/historical validation boundary so that:

- prior scientific outputs remain unchanged;
- old operational test/QC/hash couplings no longer block a truthful terminal state;
- Part 6 can be verified against the scientific contract and current-state/final-test gates;
- no final-test access, retuning or refit is introduced.

Part 6 remains the sixth and final registered M1 robustness sensitivity analysis. Completing it does not itself authorize full-development refit or final-test access.

## 11. Stage126+ research sequence

The research sequence after the current M1 workstream is:

1. finish M1 robustness Part 6 and close the six-part robustness set;
2. synthesize M1 development evidence and freeze the retained M1 design;
3. M2 market-data Gate; if it fails, report the negative Gate result and skip M2 modeling;
4. if M2 passes, evaluate M2 incremental value on a paired common sample;
5. M3 macro-data Gate; if it fails, report and skip M3 modeling;
6. if M3 passes, evaluate M3 incremental value;
7. M4 audit/governance data Gate; if it fails, report and skip M4 modeling;
8. if M4 passes, evaluate M4 incremental value;
9. freeze the final retained design and claim hierarchy before any final-test access;
10. full-development refit of the frozen retained design;
11. one locked temporal final-test evaluation;
12. explanation/performance stability analysis with no model changes;
13. manuscript tables/figures, reproducibility package, claim audit and reporting checklist.

## 12. Anti-loop rule

A maintenance defect may block science only when it can plausibly change:

- data admitted to the analysis;
- target/sample/cutoff/split;
- model input or prediction;
- reported metric/uncertainty;
- scientific provenance required to reproduce a result;
- final-test access or interpretation.

If a defect is limited to operational state, test packaging, Handoff anchoring, documentation, QC formatting or bookkeeping, fix it in the smallest maintenance change and continue. Do not create a new research micro-part.

No recursive maintenance chain is allowed (for example: Handoff refresh -> anchor refresh -> Handoff refresh). Git history is sufficient provenance for ordinary engineering evolution.

## 13. Acceptance standard

This governance is intended to bring the project to a **Q1/Q2-grade methodological standard**, not to guarantee acceptance by any journal. Journal acceptance additionally depends on novelty, writing, fit, reviewer judgment and empirical results.

A manuscript claim is acceptable only if the design is leakage-safe, pre-specified where needed, uncertainty is reported honestly, final-test discipline is preserved, and limitations are explicit.
