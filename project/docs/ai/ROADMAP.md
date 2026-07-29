---
roadmap_version: 2
active_research_workstream_id: stage126-m1-financial-baseline
qc_scope: stage126-m1-financial-baseline
last_completed_research_action_id: stage126-m1-retained-design-freeze
next_research_action_id: stage127-m2-market-data-gate
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
19. `stage126-m1-robustness-closure` — **COMPLETE.** Verified all six pre-registered M1 robustness analyses (Parts 1-6), synthesized sensitivity evidence from already-committed artifacts (zero model fits/predictions/resampling/final-test access), and closed the robustness set. No retuning, no final-test access, no automatic winner selection. No retained design selected or frozen.
20. `stage126-m1-retained-design-freeze` — **COMPLETE.** Froze the exact retained M1 design using development evidence only: sample/target/features/preprocessing/configuration/metric definitions/uncertainty plan (PR #65). No model fit, no retuning, no final-test access, no winner selection, no M2 start. Final test remains locked.
21. `stage127-m2-market-data-gate` — **EXECUTED AND RESOLVED FROM IMPORTED AUTHORITATIVE EVIDENCE; terminal observed result `FAIL_M2_DATA_GATE`.** The point-in-time accessibility/coverage/join/quality/event-count Gate for the frozen three-variable M2 market block was executed development-only (666 pairs, target years 1393-1399). No modeling was performed and no final-test row was read. Human authorization for this Gate already existed; the Gate was first executed with no data available and returned UNRESOLVED, authoritative TSETMC evidence was then obtained externally under the same Gate scope, and the Gate was re-executed offline from that immutable bundle (SHA256 `d8456b50…c6c6ec`; 110 mappings, 111 ranges, 105 SUCCESS / 6 PARTIAL, 163,230 normalized daily rows, 222 SHA256-verified raw files, all independently revalidated in this repository). The shared-window end rule is applied LITERALLY: T* is the last eligible trading day with verified available_at strictly before the pair cutoff, chosen independently of whether adjusted_close is present, so the frozen `Require P_t0 and P_tN present` endpoint condition can genuinely fail. G01-G08 all PASS (accessibility 5, derived from the frozen R-A mapping) and both locked validation windows clear the >=5-positive rule (11 / 5), but the OBSERVED development coverage of `equity_return_window` is 0.4039 (269/666, threshold 0.80) and the three-variable common-sample coverage is 0.4039 (269/666, threshold 0.70). `realized_volatility` and `amihud_illiquidity` both reach 0.8649 (576/666). This is an observed threshold failure, deliberately **not** softened into UNRESOLVED. No threshold was reduced, no value imputed, no unadjusted close substituted, no T* chosen to improve coverage, and the frozen three-variable block was not redefined or reduced. M2 market evidence IS collected and independently validated; that is recorded separately from block admission, which did not occur. **Awaiting human review.**
22. `stage127-m2-incremental-evaluation` — **BLOCKED; not authorized and not started.** Requires BOTH a passing M2 data admission and passing development comparison feasibility. Source/data-quality admission (G01-G08) and comparison feasibility both PASS on the observed evidence, but the Gate as a whole is `FAIL_M2_DATA_GATE` on the frozen coverage conditions, so this action is not eligible. Even a Gate PASS would only make it scientifically eligible for a NEW explicit human authorization — it would not authorize it. Conditional on that: evaluate M2 vs M1 on the paired M2 common sample with the frozen temporal design and pre-specified metrics/uncertainty. No post-hoc feature search.
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

The current canonical state on this branch has completed M1 robustness Parts 1–6, the synthesis-only `stage126-m1-robustness-closure` action, and the `stage126-m1-retained-design-freeze` action (PR #65). The legacy closed-part/test/QC/Handoff mechanics are engineering debt discovered at the terminal M1 transition; they are not evidence that the M1 scientific results are invalid.

The current scientific action is `stage127-m2-market-data-gate`. Its human authorization already exists and Stage127 work has started: the Gate has been executed twice under that same authorization — first as UNRESOLVED with no data available, then re-executed and resolved from the imported authoritative TSETMC evidence bundle, returning a terminal, resolved `FAIL_M2_DATA_GATE`. M2 market data HAS been collected and independently validated — recorded separately from block admission — but it does not meet the frozen admission thresholds. `stage127-m2-incremental-evaluation` remains unauthorized and unstarted, no model has been fit, and no retained-design change has occurred. The maintenance boundary may continue to be simplified under the lean-governance rules so long as scientific artifacts and the final-test firewall remain unchanged.

No M2/M3/M4 action, full-development refit, final-test access/evaluation, SHAP execution, winner/final-model selection, or new tuning is authorized merely by this roadmap update.
