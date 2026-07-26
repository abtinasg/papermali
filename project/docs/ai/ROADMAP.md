---
roadmap_version: 2
active_research_workstream_id: stage126-m1-financial-baseline
qc_scope: stage126-m1-financial-baseline
last_completed_research_action_id: stage126-m1-financial-baseline
next_research_action_id: stage126-m1-robustness-closure
active_maintenance_task_id: repository-driven-ai-handoff
---

# ROADMAP

The front matter above is the **machine-readable** roadmap pointer. Research work and maintenance work remain separate: maintenance never advances a research action.

From 2026-07-26 onward, Stage126+ follows [`STAGE126_Q1Q2_LEAN_GOVERNANCE.md`](STAGE126_Q1Q2_LEAN_GOVERNANCE.md). Scientific contracts/results/final-test controls remain hard-locked; tests, QC formatting, metadata, Handoff and repository bookkeeping are operational surfaces tracked by Git rather than recursively frozen scientific artifacts.

## Research actions (ordered)

1. `stage124-batch02-part03-1a-5` — reviewed-evidence engine
2. `stage124-batch02-part03-1a-5-1` — partial-date manual review + precision compatibility
3. `stage124-batch02-part03-1a-5-2` — cross-record evidence aggregation, deterministic canonical
4. `stage124-batch02-part03-1a-5-3` — unified decision engine, full research↔provenance QC
5. `stage124-batch02-part03-1b-0` — Research-Intake Readiness, baseline unlock, auditable intake scaffold ✅
6. `stage124-batch02-part03-1b-1` — manual source discovery, snapshot capture, and reviewed-evidence intake for the 10 Part 3 tickers — **superseded / cancelled by official TSE API** (not completed)
7. `stage124-official-api-finalize` — Finalized verified master for 130 tickers using official TSETMC first-observed-trade dates ✅
8. `stage124-gate-b-readiness` — Gate B readiness dry-run: three eligibility rules compared ✅
9. `stage124-gate-b-rule-approval` — Rule A primary + Rule B listing-timing robustness approved; Rule C rejected ✅
10. `stage124-gate-b-execution` — approved Gate B rules executed; four sample designs produced ✅
11. `stage125-research-design-readiness` — Stage125 Research Design & Data Readiness; no modeling ✅
12. `stage125-part3a-decision-lock` — accessibility/pilot decision lock ✅
13. `stage125-part3b-evidence-capture` — historical origin probes; broad expansion superseded
14. `stage125-part3b-conservative-lag-decision-lock` — conservative-lag decision history ✅
15. `stage125-part3c-leakage-safe-dataset-finalization` — active four-Jalali-month point-in-time finalization ✅
16. `stage125-part4-statistical-analysis-plan` — M1–M4 SAP, temporal CV, metrics, tuning budget, uncertainty plan ✅
17. `stage125-part5-readiness-closure` — Stage125 Gate 125.0 / Stage126 M1 readiness closure ✅
18. `stage126-m1-financial-baseline` — **COMPLETE.** Primary M1 development tuning is complete. All six registered robustness categories (Parts 1–6, including Part 6 `smote_training_fold_only_robustness`) are complete on `main`. No full-development refit; final test locked; M2/M3/M4 not started.
19. `stage126-m1-robustness-closure` — **ACTIVE.** Verify all six pre-registered M1 robustness analyses, synthesize sensitivity evidence, and close the robustness set. **No retuning, no final-test access, no automatic winner selection.**
20. `stage126-m1-retained-design-freeze` — freeze the exact retained M1 design using development evidence only: sample/target/features/preprocessing/configuration/metric definitions/uncertainty plan. This is the precondition for later refit; final test remains locked.
21. `stage127-m2-market-data-gate` — point-in-time accessibility/coverage/join/quality/event-count Gate for the pre-specified market block. **No modeling in the Gate.** A failed Gate is a reportable negative result and closes the M2 modeling path.
22. `stage127-m2-incremental-evaluation` — **conditional on Gate pass.** Evaluate M2 vs M1 on the paired M2 common sample with the frozen temporal design and pre-specified metrics/uncertainty. No post-hoc feature search.
23. `stage128-m3-macro-data-gate` — Gate the small theory-driven macro block for authoritative source, release timing, coverage and low temporal degrees of freedom. **No modeling in the Gate.**
24. `stage128-m3-incremental-evaluation` — **conditional on Gate pass.** Evaluate M3 vs M2 on the paired M3 common sample. Keep the macro set parsimonious; no searched macro universe.
25. `stage129-m4-governance-data-gate` — Gate each structured audit/governance predictor individually for definition, point-in-time availability, coverage and join quality. **No text modeling.**
26. `stage129-m4-incremental-evaluation` — **conditional on Gate pass.** Evaluate M4 vs M3 on the paired M4 common sample using only admitted structured variables.
27. `stage130-pre-final-design-and-claim-freeze` — choose the retained block/design using development evidence only; freeze exact preprocessing/configurations, comparison family, manuscript claim hierarchy, bootstrap/Holm plan and final-test reporting rules. **No final-test inspection.**
28. `stage131-full-development-refit` — refit the already-frozen retained design on the complete development period only. No tuning, feature changes or final-test access.
29. `stage132-locked-final-temporal-evaluation` — one evaluation on target years 1400–1402 after all design decisions are frozen. Report discrimination, calibration, screening value and uncertainty. **No retuning or model changes after inspection.**
30. `stage133-explainability-and-stability` — descriptive SHAP/coefficient and performance stability analysis for the retained design; no causal interpretation and no model modification.
31. `stage134-manuscript-reproducibility-and-claim-audit` — generate manuscript tables/figures, reproducibility manifest, SAP-deviation log, limitations/negative-results section, and final Q1/Q2 reporting/risk-of-bias checklist before submission.

## Maintenance tasks

- `repository-driven-ai-handoff` — repository-derived Handoff package. Operational aid only; it does not advance research.
- `stage126-q1q2-lean-governance-reset` — adopt the Stage126+ lean governance standard: scientific locks remain strict, operational test/QC/Handoff/hash coupling is simplified, one live current-state authority is used, and future acceptance gates are proportional to scientific risk.
- `stage126-legacy-validation-boundary-adaptation` — after the lean-governance decision is merged, simplify the legacy M1 live/historical validation mechanics so stale operational assertions cannot block a truthful Part 6 terminal state. **Must not alter Parts 1–5 scientific outputs, M1 primary results, final-test lock, target/sample/split or selected configurations.**
- Historical Stage125 maintenance/decision-lock tasks remain in Git history and their artifacts; they do not define the Stage126+ engineering workflow.

## Stage126+ scientific quality requirements

The roadmap requires the following before a result enters the manuscript:

- explicit sample formation and positive/negative/unknown accounting;
- point-in-time `t -> t+1` predictor timing and leakage control;
- pre-specified temporal development folds and one locked temporal final evaluation;
- common-sample paired comparisons for nested M1→M4 value-add analyses;
- PR-AUC primary; ROC-AUC complementary; Brier, calibration, Recall@10% and Lift@10%;
- 95% uncertainty intervals where estimable and paired ticker-cluster bootstrap deltas for pre-specified block comparisons;
- transparent reporting when low event counts make calibration/inference unstable;
- Holm correction only for the pre-specified inferential family in the SAP;
- no final-test model selection, winner selection, retuning, feature changes or threshold hunting;
- explanation stability checks rather than a single SHAP plot;
- explicit limitations, negative results and generalizability constraints;
- traceability of every manuscript number to a scientific artifact/table-generation output/citable source.

The 1400–1402 holdout is a **locked temporal evaluation set**, not external validation. With approximately 12 primary-target positives, final-test claims remain deliberately conservative.

## Notes on the current transition

The current canonical state on `main` has completed M1 robustness Parts 1–5 and has not completed Part 6. The legacy closed-part/test/QC/Handoff mechanics are an engineering debt discovered at the terminal M1 transition; they are not evidence that the M1 scientific results are invalid.

The next scientific work remains `stage126-m1-financial-baseline`. Before Part 6 is finalized, the maintenance boundary may be simplified under the lean-governance rules so long as scientific artifacts and the final-test firewall remain unchanged.

No M2/M3/M4 action, full-development refit, final-test access/evaluation, SHAP execution or new tuning is authorized merely by this roadmap update.
