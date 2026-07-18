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

A defensible, fully source-documented dataset and (later) distress-prediction models
for the paper, where **every value is traceable to a source** and nothing is guessed.

## 3. Current state

See [`CURRENT_STATE.md`](CURRENT_STATE.md) (auto-generated). In one line: data-freeze
phase, Stage122 & Stage123 frozen, Stage124 Gate B completed and frozen (verified
master with 130 tickers, four sample designs); **no model trained yet**.

## 4. Firm decisions

See [`DECISIONS.md`](DECISIONS.md).

## 5. Non-negotiable rules

- Nothing is guessed. If a source value is not found, it stays **Missing**.
- Every date/number must be documented to a source (`source_file`, `source_url`,
  hashes).
- Stage122 / Stage123 / targets / financials / ratios / statement-scope are
  **read-only**; their hashes are checked before and after every run.
- In this phase: **no** model / tuning / SHAP / SMOTE / calibration / report.
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
- Stage125 Part 3C leakage-safe dataset finalization source/test/QC:
  `src/stage125_part3c_leakage_safe_dataset_finalization.py`,
  `run_stage125_part3c.py`,
  `tests/test_stage125_part3c_leakage_safe_dataset_finalization.py`,
  `stage125/stage125_part3c_leakage_safe_dataset_qc_report.json` (four
  Gate B designs; audited pair + timing-eligible analysis-ready surfaces;
  Jalali six-month lag operationalized; bulky outputs gitignored/hashed;
  no feature selection / modeling / Stage126).

## 7. Done

See [`CHANGELOG.md`](CHANGELOG.md) and `git log`. High level: Stage121 (legacy) →
Stage122 freeze → Stage123 freeze → Stage124 Part1 template → Pilot15 confirmed →
Batch02 Gate A V1→V2 → Batch02 Part 2 sealed → Part 3.1A.* research engine →
official API verified master → Gate B readiness → rule approval → Gate B execution.

## 8. Open tasks

See [`OPEN_TASKS.md`](OPEN_TASKS.md).

## 9. Known issues / traps

- `project/outputs/04_models/` holds **legacy Stage121** model artifacts
  (`best_hyperparameters.json`, `final_thresholds.json`) from `run_all.py`. These do
  **not** mean modeling has started for the current target — `modeling_started`
  stays `false`.
- `run_all.py` is the old Stage121 baseline only; do not run it for the current
  target.

## 10. Next step

See `next_research_action_id` in [`ROADMAP.md`](ROADMAP.md) and
[`handoff_state.json`](handoff_state.json). Currently the research pointer is
**`stage125-part4-statistical-analysis-plan`** after Part 3C leakage-safe
dataset finalization
(`last_completed_research_action_id=stage125-part3c-leakage-safe-dataset-finalization`).
Broad CODAL capture is stopped; researcher-verified financial data are frozen;
assumed availability uses `assumed_available_at_conservative` only. Stage125
performs **no** modeling; the frozen research contract (M1–M4 blocks, M5
removed, accessibility Gates) is in
[`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md). Modeling remains
prohibited until Stage126 (M1 Financial Baseline) is explicitly approved.

## 11. Recent change history

See [`CHANGELOG.md`](CHANGELOG.md).
