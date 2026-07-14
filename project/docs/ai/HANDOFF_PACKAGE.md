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
[`handoff_state.json`](handoff_state.json). Currently:
**stage125-research-design-readiness** — Stage125 is a Research Design & Data
Readiness stage that performs **no** modeling. The frozen research contract
(M1–M4 blocks, M5 removed, accessibility Gates) is in
[`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md). Modeling remains
prohibited until Stage126 (M1 Financial Baseline) is explicitly approved.

## 11. Recent change history

See [`CHANGELOG.md`](CHANGELOG.md).
