# Stage128 — M2 D2 Boundary-Month Equity-Return Design Freeze

## Merge status

- Branch: `stage128-m2-boundary-month-return-design-freeze`
- Base: `main` @ `b25804ab764258c846b391f4823f089552c855e3`
- **This PR must NOT be merged as part of this task.** It requires a later, separate, explicit merge authorization.
- `m2_modeling_started`: unchanged (false). No canonical Gate execution. No M2 admission.

## Purpose

Formalize, document, test and freeze the D2 amendment to the M2 equity-return construct (`BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN`, Gregorian calendar convention) as the new prospective PRIMARY M2 equity-return specification, per the explicit authorization scope in [`STAGE128_M2_D2_DESIGN_FREEZE.md`](STAGE128_M2_D2_DESIGN_FREEZE.md).

This is a **design-freeze / contract PR only**. It adds:

- [`project/src/stage128_m2_d2_boundary_month_equity_return.py`](../../src/stage128_m2_d2_boundary_month_equity_return.py) — pure-function D2 endpoint-selection and return-construction logic, built on top of the unchanged, frozen `pair_scientific_window` / `daily_simple_returns` from `project/src/stage127_m2_market_data_gate.py`. It does not touch `realized_volatility` or `amihud_illiquidity`.
- [`project/tests/test_stage128_m2_d2_boundary_month_equity_return.py`](../../tests/test_stage128_m2_d2_boundary_month_equity_return.py) — development-side/synthetic fixtures only.
- [`STAGE128_M2_D2_DESIGN_FREEZE.md`](STAGE128_M2_D2_DESIGN_FREEZE.md) — the full contract: authorization scope, D2 formula, Gregorian lock rationale, D0/D1/D3 historical/diagnostic status, feasibility provenance, failure taxonomy, temporal-availability limitation, and the post-lock eligibility-audit contract.

No frozen Stage125/Stage127 file is modified. No handoff pointer file (`CURRENT_STATE.md`, `handoff_state.json`) is modified — the historical `FAIL_M2_DATA_GATE` D0 record and `next_research_action_id = stage127-m2-market-data-gate` remain exactly as merged in PR #68.

## Explicit non-claims

- Canonical M2 Gate: **not** rerun. Gate result unchanged (`FAIL_M2_DATA_GATE`, historical/D0).
- M2 incremental evaluation: **not** performed.
- Model fitting / prediction generation / hyperparameter tuning / feature discovery / target-based design comparison: **none**.
- Final-test access: **none**.
- M3 / M4: **not** started.
- Winner selection: **none**.
- `stage128-m2-d2-gate-rerun` (or equivalent): **not** authorized by this PR.

## Test plan

Focused:

```bash
PYTHONPATH=project python -m pytest project/tests/test_stage128_m2_d2_boundary_month_equity_return.py -q
```

Result: **14 passed**.

Full relevant suite:

```bash
PYTHONPATH=project python -m pytest project/tests -q
```

Result: **2543 passed, 289 failed, 26 skipped, 14 deselected, 75 errors** in this local environment. All new Stage128 tests are within the passing set; none of the failing/erroring tests belong to this change (they are pre-existing, environment-scoped failures — e.g. `test_stage124_gate_b_readiness.py`, `test_stage126_m1_primary_development_tuning.py` — present on `main` before this branch and unrelated to `stage127_m2_*` / `stage128_m2_*` modules).

## Research pointers

target values accessed = 0; model fits = 0; predictions = 0; final-test access = 0; canonical Gate executions = 0; canonical Gate changed = NO; M2 admitted = NO.

Next authorized action after this freeze PR is separately audited and explicitly merged: none automatically. A future, separately authorized canonical D2 Gate execution is the next possible scientific action — not authorized here.
