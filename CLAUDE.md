<!-- BEGIN AI-HANDOFF-POINTER (managed; idempotent section) -->
# CLAUDE — start here

This repository uses a **repository-driven AI Handoff Package**. Before doing any
work, read these (in `project/docs/ai/`):

1. [`project/docs/ai/HANDOFF_PACKAGE.md`](project/docs/ai/HANDOFF_PACKAGE.md) — index
2. [`project/docs/ai/CURRENT_STATE.md`](project/docs/ai/CURRENT_STATE.md) — auto-generated snapshot
3. [`project/docs/ai/OPEN_TASKS.md`](project/docs/ai/OPEN_TASKS.md) — what to do next
4. [`project/docs/ai/handoff_state.json`](project/docs/ai/handoff_state.json) — machine-readable state

## Rules

- Do **not** edit the auto-generated files (`CURRENT_STATE.md`, `FROZEN_ASSETS.md`,
  `handoff_state.json`) by hand — regenerate them instead.
- Do **not** modify any file listed as frozen in
  [`project/docs/ai/FROZEN_ASSETS.md`](project/docs/ai/FROZEN_ASSETS.md) without
  explicit approval.
- Before acting, check repository state (`git status`, `git rev-parse HEAD`); if in
  doubt run `python project/scripts/validate_ai_handoff.py --check`.

## Updating the Handoff Package

When the user says "Handoff Package را آپدیت کن" / "update the Handoff Package":

```bash
python project/scripts/update_ai_handoff.py --from-repository --write
python project/scripts/validate_ai_handoff.py --check
```

The full project state lives in `project/docs/ai/`; this file is only a pointer.
<!-- END AI-HANDOFF-POINTER -->
