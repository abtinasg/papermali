# Stage126 — Legacy Validation Boundary Adaptation (maintenance record)

**Status:** Tier B infrastructure maintenance under Stage126+ Q1/Q2 Lean
Research Governance. No new scientific analysis, no research decision.

**Base:** `origin/main` at `41c67a73fff5d96349763ec6c866799c5f2f9a01`
(governance reset PR #61 already merged).

## Why the old architecture caused recursive operational hash coupling

The pre-Lean-Governance validator (`stage126_current_state_validator_v1`)
treated three registry buckets per closed micro-part as equally immutable:
`scientific_artifacts_sha256`, `verification_artifacts_sha256` (QC report,
metadata manifest, README, Part 5 compatibility record) and
`code_artifacts_sha256` (test/source/runner files). Because each bucket
self-pinned the others (a test-file edit changed `test_file_sha256`, which
changed the QC report that recorded it, which changed the metadata manifest
that recorded *that*, which changed the registry that recorded all three),
any ordinary test/QC/metadata edit on an already-closed Part required a
one-time "authorized hash migration" table before the live validator would
accept it — a transitive `test hash -> QC hash -> metadata hash -> registry
hash -> Handoff hash` chain, explicitly prohibited by
[`STAGE126_Q1Q2_LEAN_GOVERNANCE.md`](STAGE126_Q1Q2_LEAN_GOVERNANCE.md) section 4.

## What is now classified scientific vs operational

| Surface | Classification | Enforcement |
|---|---|---|
| `scientific_artifacts_sha256` (per closed part) | Scientific | Live gate — fails closed on any drift |
| Completion-lock / authorization / category-identity fields | Scientific | Live gate — fails closed on any drift |
| `code_artifacts_sha256`, `verification_artifacts_sha256` | Operational | Historical provenance only — informational, never fails the live gate |
| pytest markers / test-collection config | Operational | Git-versioned, mutable |
| QC report formatting, metadata bookkeeping | Operational | Git-versioned, mutable |
| Handoff files / generated current-state prose | Operational | Regenerated in this PR; its own hash is not a lock |

## Validation responsibilities that remain hard

`project/src/stage126_current_state_validator.py` (now
`stage126_current_state_validator_v2_lean`) still fails closed on:

- scientific artifact hash drift for any closed Part (`verify_registry_immutability`);
- completion-lock / authorization / category-identity drift for any closed Part;
- Part 0 execution-order / category-skip violations (`completed_prefix`);
- the final-test lock guard and primary development lock (`verify_final_test_lock`)
  — all `FINAL_TEST_LOCK_FIELDS` must remain `False`;
- unauthorized next-category execution (`verify_no_unauthorized_execution`);
- Handoff architecture-field and current-state-pointer drift (`verify_handoff`);
- Stage125 Part 5 remaining historical/immutable and never imported/executed.

## What was retired

- The old validator raised on `code_artifacts_sha256` / `verification_artifacts_sha256`
  drift for a closed Part. `verify_registry_immutability` now separates
  `SCIENTIFIC_GATE_BUCKETS` (fatal) from `INFORMATIONAL_ONLY_BUCKETS`
  (reported, never fatal).
- No one-time hash-migration table was introduced. The five pre-terminal
  successor tests inside the closed Part 1/Part 2 files
  (`test_expected_mismatch_matches_the_real_frozen_validator` in each, plus
  `test_direct_handoff_validation_helper_is_exact`,
  `test_deterministic_repeated_build_output` and `test_check_mode_is_clean`
  in Part 2) are marked `stage126_terminal_successor_state` and excluded from
  the default live gate by marker expression only — no `--ignore`,
  `--deselect`, node-ID suppression, `-k`, `skip`, `xfail` or collection hook.
  No executable historical-worktree runner was built for them: Git history
  and the frozen scientific outputs already reachable at each Part's closing
  commit are sufficient provenance (per governance section 8).
- `pytest.ini`'s `addopts` now excludes
  `not live_successor_state and not stage126_terminal_successor_state` —
  strictly additive to the existing `live_successor_state` boundary.

## Scientific artifact immutability — confirmed

Every `scientific_artifacts_sha256` entry and every completion/authorization/
category-identity field in `project/stage126/stage126_closed_part_registry.json`
is byte-identical between this branch and `origin/main`
(`41c67a73fff5d96349763ec6c866799c5f2f9a01`). No target, sample, fold,
feature, configuration, OOF prediction or metric file was regenerated or
touched.

## Final-test lock — confirmed unchanged

All `FINAL_TEST_LOCK_FIELDS` (`final_test_unlocked`,
`final_test_access_authorized`, `final_test_predictor_values_inspected`,
`final_test_target_values_inspected`, `final_test_evaluation_performed`)
remain `False` in both the final-test lock guard and the primary development
lock. No final-test predictor or target value was inspected during this task.

## No research action advanced

This PR performs no model fitting, retuning, full-development refit, or
final-test access. Part 6 (`smote_training_fold_only_robustness`) was not
started, built, or authorized. The preserved local branch
`stage126-m1-robustness-part6-smote-training-fold-only` (HEAD
`0546381e5f91528e146e2a8c63280eec6201fcaa`) was not pushed, rewritten,
rebased, or modified.
