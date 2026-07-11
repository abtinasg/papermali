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
phase, Stage122 & Stage123 frozen, Stage124 verified master with 130 tickers
from official TSE API; **no model trained yet**.

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
- Latest Part 3 source/test/QC: `src/stage124_batch02_part03.py`,
  `tests/test_stage124_batch02_part03.py`,
  `stage124/batch02_parts/part03_qc_report.json`
- Frozen-asset report: [`FROZEN_ASSETS.md`](FROZEN_ASSETS.md)

## 7. Done

See [`CHANGELOG.md`](CHANGELOG.md) and `git log`. High level: Stage121 (legacy) →
Stage122 freeze → Stage123 freeze → Stage124 Part1 template → Pilot15 confirmed →
Batch02 Gate A V1→V2 → Batch02 Part 2 sealed → Part 3.1A.* research engine.

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
[`handoff_state.json`](handoff_state.json). Currently: **stage124-gate-b-readiness**
(Gate B readiness / eligibility rebuild planning).

## 11. Recent change history

See [`CHANGELOG.md`](CHANGELOG.md).
