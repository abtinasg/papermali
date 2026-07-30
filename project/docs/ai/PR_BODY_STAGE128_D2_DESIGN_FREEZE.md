# Stage128 — M2 D2 Boundary-Month Equity-Return Design Freeze

## Merge status

- Branch: `stage128-m2-boundary-month-return-design-freeze`
- Base: `main` @ `b25804ab764258c846b391f4823f089552c855e3`
- **This PR must NOT be merged as part of this task.** It requires a later, separate, explicit merge authorization.
- `m2_modeling_started`: unchanged (false). No canonical Gate execution. No M2 admission.

## Purpose

Formalize, document, test and freeze the D2 amendment to the M2 equity-return construct (`BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN`, Gregorian calendar convention) as the new prospective PRIMARY M2 equity-return specification, per the explicit authorization scope in [`STAGE128_M2_D2_DESIGN_FREEZE.md`](STAGE128_M2_D2_DESIGN_FREEZE.md), then upgrade the package into a complete, reproducible, repository-governed scientific design-freeze package per the continuation authorization recorded in [`project/stage128/stage128_m2_d2_human_authorization_record.json`](../../stage128/stage128_m2_d2_human_authorization_record.json).

This is a **design-freeze / contract PR only**. It adds:

- [`project/src/stage128_m2_d2_boundary_month_equity_return.py`](../../src/stage128_m2_d2_boundary_month_equity_return.py) — pure-function D2 endpoint-selection and return-construction logic, built on top of the unchanged, frozen `pair_scientific_window` / `daily_simple_returns` from `project/src/stage127_m2_market_data_gate.py`. It does not touch `realized_volatility` or `amihud_illiquidity`.
- [`project/tests/test_stage128_m2_d2_boundary_month_equity_return.py`](../../tests/test_stage128_m2_d2_boundary_month_equity_return.py) and [`project/tests/test_stage128_m2_d2_design_freeze_package.py`](../../tests/test_stage128_m2_d2_design_freeze_package.py) — development-side/synthetic fixtures and package-consistency checks only.
- [`STAGE128_M2_D2_DESIGN_FREEZE.md`](STAGE128_M2_D2_DESIGN_FREEZE.md) — the human-readable contract (authorization scope, D2 formula, Gregorian lock rationale, D0/D1/D3 historical/diagnostic status, feasibility provenance, endpoint validity semantics, failure taxonomy, temporal-availability limitation, and the post-lock eligibility-audit contract).
- `project/stage128/` — the machine-readable governance package: `stage128_m2_d2_design_freeze.json`, `stage128_m2_d2_human_authorization_record.json` (verbatim authorizing utterance + SHA256), `stage128_m2_d2_design_freeze_qc_report.json` (42/42 assertions PASS), `metadata_and_hashes_stage128_m2_d2_design_freeze.json`, `stage128_m2_d2_feasibility_provenance.json` and `reproduce_prelock_predictor_only_feasibility.py` (labeled `REPRODUCTION_OF_PRELOCK_PREDICTOR_ONLY_FEASIBILITY`), and `stage128_m2_d0_reproduction_audit_table.csv` (target-free, 666 rows).
- Allowlist update in `project/scripts/update_ai_handoff.py`: `project/stage128/` added to `ALLOWLIST_DIRS`; the two Stage128 `project/src/`/`project/tests/` files added by exact path to `ALLOWLIST_FILES` (no broad `project/src/`/`project/tests/` allowance).
- A new `derive_stage128_m2_d2_design_freeze_markers` recognizer in `update_ai_handoff.py`, and a matching `stage128_m2_d2_design_freeze_completed` recognizer in `project/src/stage126_current_state_validator.py`, both narrow and fail-closed (mirroring the existing Stage126 retained-design-freeze pattern): they advance the research pointer ONLY when the freeze artifact is present and internally consistent, never authorize the Gate re-run, and never touch the historical Stage127 D0 markers.
- Governance-surface updates: `ROADMAP.md` (new items 22-23, front-matter pointers updated to represent the state *if this PR is merged*, with an explicit not-yet-live note), `OPEN_TASKS.md`, `DECISIONS.md`.
- Regenerated `project/docs/ai/handoff_state.json` / `CURRENT_STATE.md` via the canonical generator, reflecting the Stage128 state.

No frozen Stage125/Stage127 scientific artifact is modified; the historical `FAIL_M2_DATA_GATE` D0 record is preserved byte-for-byte throughout.

## Explicit non-claims

- Canonical M2 Gate: **not** rerun. Gate result unchanged (`FAIL_M2_DATA_GATE`, historical/D0).
- M2 incremental evaluation: **not** performed.
- Model fitting / prediction generation / hyperparameter tuning / feature discovery / target-based design comparison: **none**.
- Final-test access: **none**.
- M3 / M4: **not** started.
- Winner selection: **none**.
- D2-vs-D3 design selection: **not** reopened. Gregorian D2: **unchanged**.
- `stage128-m2-d2-gate-rerun` (or equivalent): **not** authorized by this PR — it is identified as a research-pointer value only (`stage128_m2_d2_gate_rerun_authorized = false` throughout).

## Feasibility provenance (honest limitation)

D0 (269/666) is **independently and exactly reproduced in-repository** from the already-committed, target-free `stage127_m2_development_features.csv`. D1/D2 (Gregorian, 539/666)/D3/the Jalali diagnostic require raw per-day price data that was **never committed to this repository** (only the external bundle's SHA256 is referenced); these four are recorded as externally-supplied historical evidence only, explicitly flagged `d1_d2_d3_jalali_independently_reproduced_in_repository = false` — no synthetic data was fabricated to manufacture a fake reproduction.

## Test plan

Focused Stage128 (function library + freeze-package consistency):

```bash
PYTHONPATH=project python -m pytest project/tests/test_stage128_m2_d2_boundary_month_equity_return.py project/tests/test_stage128_m2_d2_design_freeze_package.py -q
```

Result: **46 passed**.

Relevant suite (Stage127 Gate primitives, external-delivery/import controls, trading-day semantics, Stage128, Handoff/current-state, allowlist/change-guard):

```bash
PYTHONPATH=project python -m pytest project/tests/test_ai_handoff.py project/tests/test_stage126_current_state_validator.py project/tests/test_stage128_m2_d2_boundary_month_equity_return.py project/tests/test_stage128_m2_d2_design_freeze_package.py project/tests/test_stage127_m2_market_data_gate.py project/tests/test_stage127_m2_external_delivery_import.py project/tests/test_stage127_m2_zero_trade_semantics_import.py project/tests/test_stage127_m2_external_retrieval_request.py -q
```

Result: **765 passed, 8 failed, 26 skipped**. All 8 failures are the identical pre-existing `FileNotFoundError` for a gitignored, untracked input (`project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv`), confirmed present in an identical clean checkout of the PR base commit (`b25804ab764258c846b391f4823f089552c855e3`) — an environment/untracked-asset limitation, not a regression from this change.

Full-suite base-vs-head comparison (`--junitxml`, same machine/environment): base `b25804ab764258c846b391f4823f089552c855e3` = 2529 passed / 289 failed / 75 errored / 26 skipped; head (this branch) = see final response. `new_failure_nodeids` / `new_error_nodeids` after fixing the pointer-transition regression tests (`test_ai_handoff.py`, `test_stage126_current_state_validator.py`) that legitimately needed updating for the new research pointer = **0**.

## Research pointers

target values accessed = 0; model fits = 0; predictions = 0; final-test access = 0; canonical Gate executions = 0; canonical Gate changed = NO; M2 admitted = NO.

`last_completed_research_action_id` / `next_research_action_id` are updated to represent the state **if and only if this PR is merged** (`stage128-m2-boundary-month-return-design-freeze` / `stage128-m2-d2-gate-rerun`); `stage128-m2-d2-gate-rerun` is a pointer only, **not** an authorization (`stage128_m2_d2_gate_rerun_authorized = false`). Until merge, the live `main` pointer is unaffected.
