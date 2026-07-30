# Stage128 — M2 D2 Boundary-Month Equity-Return Design Freeze

## Governance/provenance consistency closure (latest commits)

This PR was continued for a governance-only closure. **No scientific content changed** — D2 formula, Gregorian convention, the 539/666 historical feasibility record, the 126-return floor, `W`, `t0`, `T*`, daily-return adjacency, realized volatility, Amihud, the eligibility contract and the final-test firewall are all untouched; no Gate execution, no model, no prediction, no target or final-test access.

1. **Current state now reflects the human decision already made.** A completed Stage128 D2 freeze IS the human decision the terminal Stage127 FAIL result was waiting for, so once the freeze is recognized, `stage127_m2_market_data_gate_terminal_result_pending_human_review` and `stage127_m2_semantics_human_decision_required` are both `false`, while `stage127_m2_market_data_gate_status` remains `FAIL_M2_DATA_GATE` and the history is preserved (`stage127_m2_human_review_originally_required = true`, `stage127_m2_human_review_resolved_by_action_id = stage128-m2-boundary-month-return-design-freeze`). `CURRENT_STATE.md` renders Stage127 as **HISTORICAL — COMPLETED AND RESOLVED** and adds an explicit Stage128 D2 design-freeze section; ROADMAP item 21, the current-transition note and `OPEN_TASKS.md` are updated to match.
2. **QC claims are literally true** — see the Test plan below.
3. **Authorization provenance is exact** — see Authorization provenance below.
4. **Feasibility provenance no longer overclaims** — see Feasibility provenance below.
5. **The current-state validator fails closed on the contradiction**, with tests covering it (`stage128_freeze_closes_stage127_pending_human_review`, `stage127_human_review_history_not_erased`, `stage127_historical_d0_gate_status_preserved`, `current_state_renders_stage128_section_after_freeze`, `current_state_does_not_call_stage127_the_current_action_after_freeze`).

## Live current-state labels (latest commit)

`current_stage` and `active_workstream` claim to describe the CURRENT live research state, so they no longer name the completed Stage126 M1 baseline once the Stage128 D2 freeze is recognized. `current_stage = Stage128` and `active_workstream = stage128_m2_d2_boundary_month_equity_return` — a stable, machine-readable workstream label **derived from** the frozen action `stage128-m2-boundary-month-return-design-freeze`. It is **not** a new scientific action, authorizes nothing, and never substitutes for a research-action id: `last_completed_research_action_id` and `next_research_action_id` are unchanged. `stage126-m1-financial-baseline` is retained as history (ROADMAP items 1-20, OPEN_TASKS historical section) and `qc_scope` still points at the last completed micro-part's QC scope. The generator fails closed if the ROADMAP workstream pointer is stale, and the current-state validator fails if `stage128_m2_d2_design_freeze_completed = true` while `current_stage == Stage126` or `active_workstream == stage126_m1_financial_baseline`.

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
- `project/stage128/` — the machine-readable governance package: `stage128_m2_d2_design_freeze.json`, `stage128_m2_d2_human_authorization_record.json` (verbatim authorizing utterance + SHA256), `stage128_m2_d2_design_freeze_qc_report.json` (43/43 REQUIRED freeze-package assertions PASS — `all_pass` means the required package assertions, including the no-new-regressions-vs-base check; it does **not** claim the relevant suite had zero failures), `metadata_and_hashes_stage128_m2_d2_design_freeze.json`, `stage128_m2_d2_feasibility_provenance.json` and `d0_reproduction_and_prelock_feasibility_archival_record.py` (labeled `D0_REPRODUCTION_PLUS_ARCHIVAL_RECORD_OF_PRELOCK_EXTERNAL_FEASIBILITY_EVIDENCE`), and `stage128_m2_d0_reproduction_audit_table.csv` (target-free, 666 rows).
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

D0 (269/666) is **independently and exactly reproduced in-repository** from the already-committed, target-free `stage127_m2_development_features.csv`. D1/D2 (Gregorian, 539/666)/D3/the Jalali diagnostic require raw per-day price data that was **never committed to this repository** (only the external bundle's SHA256 is referenced); these four are ARCHIVED as **externally supplied historical feasibility evidence** only, explicitly flagged `d1_d2_d3_jalali_independently_reproduced_in_repository = false` — no synthetic data was fabricated to manufacture a fake reproduction.

Recorded separately in `stage128_m2_d2_feasibility_provenance.json`:

- `historical_counts_transmitted_by_human = true` — the human authorization text is the **transmission channel** for those counts, not the scientific source of truth (`externally_supplied_evidence_is_scientific_source_of_truth = false`).
- `external_market_bundle_sha256 = d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec`; `raw_bundle_present_in_repository = false`.
- `prelock_D2_count_independently_verified_in_repository = false`.
- `canonical_confirmation_deferred_to = stage128-m2-d2-gate-rerun` — which remains **unauthorized**.
- `original_prelock_feasibility_script_not_preserved = true` — the original pre-lock scratchpad feasibility script/output are not preserved and cannot be hashed; no substitute provenance is manufactured.

## Authorization provenance

`stage128_m2_d2_human_authorization_record.json` records the **ORIGINAL Stage128 D2 scientific authorization** (`authorization_class = ORIGINAL_SCIENTIFIC_AUTHORIZATION`) — the human-supervisor message beginning "I explicitly authorize the following scientific research action ONLY:" and authorizing `stage128-m2-boundary-month-equity-return-design-freeze`. It is **not** the later PR #69 governance-package continuation instruction: those later instructions requested repository-governance work only and created **no** new scientific decision (`later_pr69_governance_continuation_created_new_scientific_decision = false`).

One unrelated trailing sentence belonging to the earlier PR #68 merge context ("The next scientific action — Gregorian D2 design amendment/freeze — is separate and is NOT authorized by this merge.") was removed from the recorded verbatim text, and `human_source_utterance_sha256` plus every dependent hash were recomputed. Corrected `human_source_utterance_sha256`: `dd462fa29ef3ec494bf0f76a725f958ae94a52651ed4f84411d962af9d4504a6`.

## Test plan

Focused Stage128 (function library + freeze-package consistency):

```bash
PYTHONPATH=project python -m pytest project/tests/test_stage128_m2_d2_boundary_month_equity_return.py project/tests/test_stage128_m2_d2_design_freeze_package.py -q
```

Result on the final head: **56 passed**.

Relevant suite (Stage127 Gate primitives, external-delivery/import controls, trading-day semantics, Stage128, Handoff/current-state, allowlist/change-guard):

```bash
PYTHONPATH=project python -m pytest project/tests/test_ai_handoff.py project/tests/test_stage126_current_state_validator.py project/tests/test_stage128_m2_d2_boundary_month_equity_return.py project/tests/test_stage128_m2_d2_design_freeze_package.py project/tests/test_stage127_m2_market_data_gate.py project/tests/test_stage127_m2_external_delivery_import.py project/tests/test_stage127_m2_zero_trade_semantics_import.py project/tests/test_stage127_m2_external_retrieval_request.py -q
```

Two environments are reported, because the result differs and neither is hidden:

- **Originally reported environment** (the gitignored, untracked Stage125 input `project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv` is **absent**): **765 passed, 8 failed, 26 skipped** — `relevant_suite_all_pass = false`. All 8 failures are the identical pre-existing `FileNotFoundError` for that missing input, present identically in a clean checkout of the PR base commit (`b25804ab764258c846b391f4823f089552c855e3`) — an environment/untracked-asset limitation, not a regression. `relevant_suite_new_failures_vs_base = 0`, `relevant_suite_new_errors_vs_base = 0`, `relevant_suite_regression_check_pass = true`.
- **Final-head environment** (that input **present**): **813 passed, 0 failed, 1 skipped** — literally all-pass.

The QC report no longer carries the untruthful `relevant_suite_tests_pass` assertion. It now carries `relevant_suite_regression_check_pass` plus an explicit `test_evidence` block recording both environments, and `all_pass_semantics` states that `all_pass` means all REQUIRED freeze-package assertions passed (including no new regressions vs base) — **not** that the entire relevant suite had zero failures.

Full-suite base-vs-head comparison (`--junitxml`, same machine/environment, identical working directory with gitignored inputs present, run on the FINAL head):

- base `b25804ab764258c846b391f4823f089552c855e3` = **2916 passed / 2 failed / 0 errored / 1 skipped / 14 deselected**
- head = **2977 passed / 2 failed / 0 errored / 1 skipped / 14 deselected**
- `new_failure_nodeids = 0`, `new_error_nodeids = 0`, `resolved_failure_nodeids = 0`

The 2 base failures are pre-existing and identical on both sides: `test_stage125_part5_readiness_closure.py::test_run_canonical_check_zero_scientific_drift` and `test_stage126_m1_robustness_closure.py::test_on_disk_artifacts_match_fresh_build`.

## Research pointers

target values accessed = 0; model fits = 0; predictions = 0; final-test access = 0; canonical Gate executions = 0; canonical Gate changed = NO; M2 admitted = NO.

`last_completed_research_action_id` / `next_research_action_id` are updated to represent the state **if and only if this PR is merged** (`stage128-m2-boundary-month-return-design-freeze` / `stage128-m2-d2-gate-rerun`); `stage128-m2-d2-gate-rerun` is a pointer only, **not** an authorization (`stage128_m2_d2_gate_rerun_authorized = false`). Until merge, the live `main` pointer is unaffected.
