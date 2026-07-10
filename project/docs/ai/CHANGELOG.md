# CHANGELOG

Human-maintained, newest first. Record decisions and milestones (not every commit —
`git log` already has those).

## 2026-07-10

- **Retired the Human-in-the-Loop (HIL) and manual listing-date research path.**
  The HIL Streamlit dashboard (`stage124_part03_hil_panel.py`), the manual intake
  runner (`run_stage124_batch02_part03_manual_intake.py`), their tests, and the
  `streamlit` dependency have been removed. The `part03_manual_intake_input.csv`
  template and the HIL panel README were also deleted.
- **`stage124-batch02-part03-1b-1` superseded** — cancelled by the official TSETMC
  API. The verified master (`listing_master_verified_stage124.csv`) now contains
  130 unique tickers with `first_observed_trading_date_from_official_tse_api`
  (status `verified_tse_api_first_observed_trade`). These dates are first observed
  trading dates, not necessarily IPO, admission, or listing dates.
- **Next action** is `stage124-gate-b-readiness` (Gate B readiness / eligibility
  rebuild planning). Gate B execution and modeling are not in scope.
- Removed the old DECISIONS rule "No `listing_master_verified_stage124.csv`" —
  the verified master now exists and is canonical.
- Historical Part 3 artifacts (worklist, QC report, provenance, snapshots) are
  retained for scientific reproducibility; they are not deleted.

## 2026-06-28

- **Created the repository-driven AI Handoff Package** (`docs/ai/`, `scripts/`,
  `tests/test_ai_handoff.py`, root `AGENTS.md`/`CLAUDE.md`) on branch
  `docs/ai-handoff-package` off `origin/main` (`fec87cc`). Maintenance task
  `repository-driven-ai-handoff`.
- Recorded the project baseline at this point: Stage122 & Stage123 frozen;
  Stage124 Batch02 Part 3.1A.5.3 completed (QC: 467 assertions, 0 failed, code commit
  `076388…`); next research action `stage124-batch02-part03-1b-0`.

## Earlier (summary from git history)

- Stage124 Batch02 Part 3.1A.* — research/evidence/decision engine for 10 tickers.
- Stage124 Batch02 Part 2.1A/2.1B — offline finalizer, sealed package.
- Stage124 Batch02 Gate A V1 → V2 — tiered ranking, TSETMC probe, review template.
- Stage124 Pilot15 — user-confirmed public-entry dates.
- Stage124 Part 1 — listing-master review template.
- Stage123 — statement-scope correction + eligibility/panel rebuild (frozen).
- Stage122 — composite distress target + eligibility + pairs (frozen).
- Stage121 — legacy baseline (kept for reference only).
