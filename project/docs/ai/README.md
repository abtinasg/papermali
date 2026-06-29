# `docs/ai/` — Repository-driven AI Handoff Package

This folder is a **living document** that lets any new chat / AI agent continue the
project from its exact current state, without a giant re-priming prompt. It is
**repository-driven**: the machine-checkable state is *generated from git + QC*, not
hand-typed, and a validator fails if the docs drift from the repository.

## Files

| File | Owner | Overwritten by generator? |
|---|---|---|
| `HANDOFF_PACKAGE.md` | 👤 human (index) | No — bootstrap only |
| `CURRENT_STATE.md` | 🤖 auto | **Yes** — regenerated every run |
| `FROZEN_ASSETS.md` | 🤖 auto | **Yes** — regenerated every run |
| `handoff_state.json` | 🤖 auto | **Yes** — regenerated every run |
| `ROADMAP.md` | 👤 human | No — bootstrap only (input to state) |
| `DECISIONS.md` | 👤 human | No — bootstrap only |
| `OPEN_TASKS.md` | 👤 human | No — bootstrap only |
| `CHANGELOG.md` | 👤 human | No — append by hand |

**🤖 auto** files are *outputs* of `scripts/update_ai_handoff.py`. Never edit them by
hand — your edits will be overwritten and will not change the project's real state.

**👤 human** files are *inputs*. `ROADMAP.md` front matter (the action IDs) feeds the
generated state, so editing it is how you advance the recorded roadmap. The generator
will only create human files if they are missing (bootstrap); it never overwrites them.

## How to read (new agent, start here)

1. Read `HANDOFF_PACKAGE.md` (the index).
2. Read `CURRENT_STATE.md` and `OPEN_TASKS.md`.
3. For a machine-readable snapshot, read `handoff_state.json`.
4. Do **not** modify any file listed as frozen in `FROZEN_ASSETS.md` without explicit
   approval.

## How to update (end of a work session)

From the repository root (`papermali/`):

```bash
python project/scripts/update_ai_handoff.py --from-repository --write   # regenerate 🤖 files
python project/scripts/validate_ai_handoff.py --check                   # must exit 0
```

When the user says *"Handoff Package را آپدیت کن" / "update the Handoff Package"*,
run the two commands above (and append a `CHANGELOG.md` line by hand if a decision
changed).

## Design invariants

- A tracked file cannot store the SHA of the commit that contains it, so we never
  require `head_commit == HEAD`. We anchor on `generated_from_commit` (an ancestor of
  HEAD) plus a semantic `state_fingerprint`. The validator also requires every commit
  between `generated_from_commit` and HEAD — **merge commits included** — to be
  Handoff-only.
- The validator compares the **full** non-volatile semantic projection of
  `handoff_state.json` against a freshly computed state, so any tampered field
  (`current_stage`, `current_batch`, `tickers`, counts, commits, markers, fingerprint)
  is caught — not just a hand-picked subset.
- Handoff/documentation commits never advance the **research** stage (separate
  `active_maintenance_task_id` vs `active_research_workstream_id`).
- QC freshness is checked by source/test **fingerprint**, not by `qc_source_commit ==
  HEAD` (the project uses a code → artifact → merge two-commit workflow).
- A **frozen** asset that is missing, mismatched, or untracked is **fatal**. A file is
  exempt only when it is explicitly classified in `NON_FROZEN_TRACKED` (e.g. a pytest
  log with a non-deterministic timing line) or is **proven gitignored** via
  `git check-ignore`. An untracked, non-ignored, unclassified manifest file is fatal —
  it is not really frozen.
- The change allowlist distinguishes **directories** (prefix match, must end in `/`)
  from **files** (exact match only) — no `foo.py.bak`-style prefix bypass.
- Regeneration is **package-atomic**: all auto files are written to temp siblings, the
  originals are moved aside, and on any error everything is rolled back, so the package
  is never left half-updated.
