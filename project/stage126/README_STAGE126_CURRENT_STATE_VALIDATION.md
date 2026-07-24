# Stage126 — Current-State Validation

**Stage125 Part 5 is a frozen historical closure. It is no longer responsible for validating live Stage126 successor state. The independent Stage126 current-state validator is the sole current-state validation surface.**

Future robustness parts must **not** regenerate previous-part verification artifacts unless a genuine scientific error and a separate explicit human authorization exist.

## Decision

- Decision: `stage126-validation-architecture-boundary-lock` (`stage126_validation_architecture_boundary_v1`)
- Human decision text SHA-256: `8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1`
- Authorizes: the boundary lock, this validator, the Stage125 Part 5 freeze, and the documentation/test changes this boundary requires.
- Does **not** authorize: merge, Part 3 execution, full-development refit, final-test access, final-test evaluation, or any new scientific execution.

## Live verification sequence

```bash
python project/run_stage126_current_state_validator.py --check
python project/run_stage126_m1_robustness_part2_listing_rule_b.py --check
python project/scripts/validate_ai_handoff.py --check
PYTHONPATH=project python -m pytest project/tests -q
```

`run_stage125_part5.py --check` is **not** part of this sequence. It is a historical closure runner; its known behaviour (exit 1, first failure `readiness_surface_disagreement`, and a separate five-field direct handoff mismatch) is retained as **historical provenance only** and is no longer a required live gate. Previous robustness runners are also not current-state gates — previous scientific artifacts are protected by immutable hashes recorded here.

## Frozen historical surfaces

- `project/src/stage125_part5_readiness_closure.py` — `cb61ea7c99b53f1988c22f5eac0af66af9cd9e46657a48bf66ccb198d654d41c`
- `project/run_stage125_part5.py` — `ba6bd9e8e155e9cad71299e53806515caa1f95664bfcba0aebd20929f769e037`
- `project/tests/test_stage125_part5_readiness_closure.py` — `0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71`
- `project/stage125/**` — every tracked file pinned in `stage126_historical_boundary_manifest.json`

## Current state

| field | value |
|---|---|
| completed parts | 4 |
| completed categories | `m1_target_proximity_six_feature_set`, `main_rule_b_listing_robustness`, `expanded_rule_a_company_scope_robustness`, `expanded_rule_b_combined_robustness` |
| next category | `persistent_loss_robustness_target` |
| next category authorized | false |
| M1 robustness completed | false |
| full-development refit performed | false |
| final test unlocked | false |
| last completed micro-part | `stage126-m1-robustness-part4-expanded-rule-b` |
| active workstream | `stage126_m1_financial_baseline` |
| next research action | `stage126-m1-financial-baseline` |

## Adding a future part

Parts are discovered generically from the Part 0 registered execution order by naming convention. A future Part 3 advances current state by adding only its own implementation, tests, artifacts and completion lock, plus a refreshed validation report, Handoff and human documentation. **No Part 1, Part 2 or Stage125 Part 5 file may change.**

## Exception policy

- Reopening a completed part: **forbidden** by default.
- A genuine scientific error exception requires all of: `documented_scientific_error`, `impact_assessment`, `explicit_new_human_authorization`, `separate_corrective_PR`.
- **Not** scientific errors: new Handoff timestamp, new branch SHA, new current test hash, new completed robustness part, documentation wording drift, historical validator successor mismatch.
- **May** qualify: incorrect target construction, leakage, incorrect feature computation, wrong sample membership, wrong fold assignment, incorrect probability or metric computation, unauthorized final-test access.
- This validator never reopens a previous part automatically.
