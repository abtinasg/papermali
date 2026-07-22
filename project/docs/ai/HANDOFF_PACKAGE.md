# 📦 HANDOFF PACKAGE — Financial Distress Prediction (Iran)

> Living index for `abtinasg/papermali`. New agents: read this, then
> [`CURRENT_STATE.md`](CURRENT_STATE.md) and [`OPEN_TASKS.md`](OPEN_TASKS.md).
> The machine-readable snapshot is [`handoff_state.json`](handoff_state.json).
> Repository-driven: the auto files are generated from git + QC. See
> [`README.md`](README.md) for the auto/human split.

## 1. Project intro

Research project (journal paper) predicting **financial distress** of companies
listed on the Tehran Stock Exchange. Python pipeline, config-driven, reproducible,
with independent QC at every stage.

## 2. Final goal

A defensible, fully source-documented dataset and a reproducible, leakage-safe
distress-prediction modeling pipeline, with final-test results and article claims
produced only after their separate authorization — where **every value is traceable
to a source** and nothing is guessed.

## 3. Current state

See [`CURRENT_STATE.md`](CURRENT_STATE.md) (auto-generated). Stage126 M1 is human-authorized and started. Primary M1 development-fold tuning is completed on PR #52. M1 robustness is not started. No full-development refit has occurred. The final test remains locked and untouched. M2/M3/M4 data were not collected.

## 4. Firm decisions

See [`DECISIONS.md`](DECISIONS.md).

## 5. Non-negotiable rules

- Nothing is guessed. If a source value is not found, it stays **Missing**.
- Every date/number must be documented to a source (`source_file`, `source_url`,
  hashes).
- Stage122 / Stage123 / targets / financials / ratios / statement-scope are
  **read-only**; their hashes are checked before and after every run.
- **Current Stage126 M1 prohibitions:** final-test access or evaluation; full-development refit; M1 robustness without the next explicit micro-part decision; SMOTE robustness; target-proximity robustness; Rule B / expanded-sample robustness; persistent-loss robustness; M2/M3/M4 data collection or modeling; SHAP; network extraction.
- Bulky outputs are gitignored; only source + small QC/metadata/audit files are
  committed.
- Two-commit workflow: **code-commit → artifact-commit → merge-commit**. QC points at
  the *code* commit, not the merge.

### 5.1 Research vs maintenance pointers (Handoff semantics)

Do not confuse QC selection with the research-action chain:

- `last_completed_micro_part` in `handoff_state.json` is a **legacy JSON field
  name**; its value is copied from
  `ROADMAP.md` → `last_completed_research_action_id` (research chain only).
- `next_research_action_id` likewise shows only the research chain.
- `selected_qc_scope` may point at a **newer maintenance-task QC** (for example
  Part 3B.1A CUT-A available-at operationalization lock) while those research
  IDs stay unchanged.
- Part 3B.1 completion is signaled by `part3b1_decision_locked=true`; Part 3B.1A
  adds `cut_a_available_at_operationalization_locked=true`. Neither must advance
  `last_completed_research_action_id` / `next_research_action_id`.
- Handoff / documentation commits also never advance the research stage
  (`active_maintenance_task_id` vs `active_research_workstream_id`).

## 6. Reference files

- Run guide: [`../../README_RUN.md`](../../README_RUN.md)
- Legacy Stage121 baseline: [`../../README_STAGE121_LEGACY.md`](../../README_STAGE121_LEGACY.md)
- Config: [`../../config.yaml`](../../config.yaml)
- Gate B execution source/test/QC: `src/stage124_gate_b_execution.py`,
  `tests/test_stage124_gate_b_execution.py`,
  `stage124/stage124_batch02_gate_b_qc_report.json`
- Frozen-asset report: [`FROZEN_ASSETS.md`](FROZEN_ASSETS.md)
- Stage125 research contract: [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md)
- Stage125 Part 1 data-contract source/test/QC: `src/stage125_part1_data_contract.py`,
  `run_stage125_part1.py`, `tests/test_stage125_part1_data_contract.py`,
  `stage125/stage125_part1_data_contract_qc_report.json` (contracts + read-only
  M1 provenance-gap audit; no modeling, no extraction)
- Stage125 Part 2 prediction-time-contract source/test/QC: `src/stage125_part2_prediction_time_contract.py`,
  `run_stage125_part2.py`, `tests/test_stage125_part2_prediction_time_contract.py`,
  `stage125/stage125_part2_prediction_time_contract_qc_report.json` (prediction-time
  & leakage contract; per-pair cutoff/feature/leakage audit; no modeling, no extraction)
- Stage125 Part 3A pilot-protocol source/test/QC: `src/stage125_part3a_pilot_protocol.py`,
  `run_stage125_part3a.py`, `tests/test_stage125_part3a_pilot_protocol.py`,
  `stage125/stage125_part3a_pilot_protocol_qc_report.json` (accessibility rubric,
  gate protocol, candidate inventory freeze, sampling frame; no evidence, no extraction)
- Stage125 Part 3A.1 decision-lock source/test/QC: `src/stage125_part3a_decision_lock.py`,
  `run_stage125_part3a_decision_lock.py`, `tests/test_stage125_part3a_decision_lock.py`,
  `stage125/stage125_part3a_decision_lock_qc_report.json` (approved rubric, G09–G14
  thresholds, locked pilot selection; no evidence, no extraction)
- Stage125 Part 3B.0 evidence-readiness source/test/QC: `src/stage125_part3b0_evidence_readiness.py`,
  `run_stage125_part3b0.py`, `tests/test_stage125_part3b0_evidence_readiness.py`,
  `stage125/stage125_part3b0_evidence_readiness_qc_report.json` (schema validator,
  immutable cache contract, network sentinel, Gate engine scaffolding; frozen
  historical baseline after Part 3B authorization)
- Stage125 Part 3B evidence-capture source/test/QC: `src/stage125_part3b_evidence_capture.py`,
  `run_stage125_part3b.py`, `tests/test_stage125_part3b_evidence_capture.py`,
  `stage125/stage125_part3b_evidence_capture_qc_report.json` (authorized Part 3B
  endpoint/source-origin feasibility probe; 800 pair-candidate assessments;
  scores null; no candidate-value or pair-level value extraction; no real
  accessibility scoring; no modeling)
- Stage125 Part 3B.1 decision-lock source/test/QC: `src/stage125_part3b1_decision_lock.py`,
  `run_stage125_part3b1.py`, `tests/test_stage125_part3b1_decision_lock.py`,
  `stage125/stage125_part3b1_decision_lock_qc_report.json` (feature/scoring/cutoff
  adjudication contracts + synthetic validation only; no network; no real
  extraction/scoring; no modeling). Adjudicated outputs are versioned as
  `part3b1_adjudicated_decision_requirements_stage125.json` and
  `README_STAGE125_PART3B1_DECISION_LOCK.md` (historical Part 3B proposed
  requirements README remains frozen).
- Stage125 Part 3B.1E conservative-lag decision-lock source/test/QC:
  `src/stage125_part3b1e_conservative_lag_decision.py`,
  `run_stage125_part3b1e.py`,
  `tests/test_stage125_part3b1e_conservative_lag_decision.py`,
  `stage125/stage125_part3b1e_conservative_lag_qc_report.json` (fixed
  six-month lag; researcher-verified financials frozen; no broad CODAL
  capture; assumed availability field only; no Stage126 / modeling).
- Stage125 Part 4 statistical analysis plan source/test/QC:
  `src/stage125_part4_statistical_analysis_plan.py`,
  `run_stage125_part4.py`,
  `tests/test_stage125_part4_statistical_analysis_plan.py`,
  `stage125/stage125_part4_statistical_analysis_plan_qc_report.json` (active
  contract `stage125_part4_sap_v2`; M1=9 admitted; revenue-growth audit-only
  rejection; temporal splits; coverage/event gates; no modeling)
- Stage125 Part 5 readiness closure source/test/QC:
  `src/stage125_part5_readiness_closure.py`,
  `run_stage125_part5.py`,
  `tests/test_stage125_part5_readiness_closure.py`,
  `stage125/stage125_part5_readiness_closure_qc_report.json` (Gate 125.0;
  keep/drop/defer; Stage126 M1 entry contract readiness-only; no modeling).
  The entry-contract flags `stage126_authorized=false` / `modeling_authorized=false`
  describe the **historical Stage125 closure-state artifact** at closure time; they
  are not the current authorization state (Stage126 M1 is now human-authorized and
  started). The frozen artifact itself is unchanged.
- Stage125 Part 3C leakage-safe dataset finalization source/test/QC:
  `src/stage125_part3c_leakage_safe_dataset_finalization.py`,
  `run_stage125_part3c.py`,
  `tests/test_stage125_part3c_leakage_safe_dataset_finalization.py`,
  `stage125/stage125_part3c_leakage_safe_dataset_qc_report.json` (four
  Gate B designs; audited pair + timing-eligible analysis-ready surfaces;
  active four-Jalali-month regulatory lag; six-month methodology superseded;
  bulky outputs gitignored/hashed; no feature approval / modeling / Stage126).
- Stage126 M1 primary development-fold tuning source/test/QC:
  `src/stage126_m1_primary_development_tuning.py`,
  `run_stage126_m1_primary_development_tuning.py`,
  `tests/test_stage126_m1_primary_development_tuning.py`,
  `stage126/stage126_m1_primary_development_tuning_qc_report.json`
  (human-authorized M1 development-fold tuning; final test locked; no robustness).
- Stage126 authorization transition guard source/test/QC:
  `src/stage126_authorization_transition_guard.py`,
  `tests/test_stage126_authorization_transition_guard.py`,
  `stage126/stage126_m1_final_test_lock_guard.json`,
  `stage126/stage126_m1_primary_development_lock.json`.
- Stage126 M1 robustness Part 0 decision-lock source/test/QC:
  `src/stage126_m1_robustness_part0_decision_lock.py`,
  `run_stage126_m1_robustness_part0_decision_lock.py`,
  `tests/test_stage126_m1_robustness_part0_decision_lock.py`,
  `stage126/stage126_m1_robustness_part0_decision_record.json`,
  `stage126/stage126_m1_robustness_part0_decision_lock_qc_report.json`
  (additive robustness execution contract; **decision lock only — no robustness
  execution; Part 1 not started**; primary artifacts byte-identical; final test
  locked).

## 7. Done

See [`CHANGELOG.md`](CHANGELOG.md) and `git log`. High level: Stage121 (legacy) →
Stage122 freeze → Stage123 freeze → Stage124 Part1 template → Pilot15 confirmed →
Batch02 Gate A V1→V2 → Batch02 Part 2 sealed → Part 3.1A.* research engine →
official API verified master → Gate B readiness → rule approval → Gate B execution →
Stage125 Part 3C leakage-safe finalization → Stage125 Part 4 SAP lock →
Stage125 Part 5 readiness closure → Stage126 M1 human authorization →
Stage126 primary development-fold tuning completed on PR #52.

## 8. Open tasks

See [`OPEN_TASKS.md`](OPEN_TASKS.md).

## 9. Known issues / traps

- `project/outputs/04_models/` holds **legacy Stage121** model artifacts
  (`best_hyperparameters.json`, `final_thresholds.json`) from `run_all.py`. These do
  **not** mean modeling has started for the current target — they are historical
  artifacts only.
- `run_all.py` is the old Stage121 baseline only; do not run it for the current
  target.

## 10. Next step

See `next_research_action_id` in [`ROADMAP.md`](ROADMAP.md) and
[`handoff_state.json`](handoff_state.json). Stage126 M1 is human-authorized and started;
primary M1 development-fold tuning is completed on PR #52.

The next scientific action is **not automatically authorized**. A separate explicit
human micro-part decision is required before any M1 robustness execution. M1
robustness, full-development refit and final-test access remain unstarted and
unauthorized. The final test remains locked and untouched; M2/M3/M4 data were not
collected.

The robustness Part 0 decision lock
(`stage126_m1_robustness_execution_contract_v1`) records the execution contract
for the six robustness categories (one category per micro-part PR, first
`m1_target_proximity_six_feature_set`). It is a **decision lock only**:
`m1_robustness_execution_authorized=false` and **Part 1 is not started**. Each
future Part requires its own separate explicit human authorization.

## 11. Recent change history

See [`CHANGELOG.md`](CHANGELOG.md).
