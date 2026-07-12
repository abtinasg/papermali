# CHANGELOG

Human-maintained, newest first. Record decisions and milestones (not every commit —
`git log` already has those).

## 2026-07-12

- **`stage124-gate-b-rule-approval` completed** — The user/data owner explicitly
  approved the final Gate B listing-eligibility rules, supported by the completed
  Gate B readiness comparison (no external reviewer approval claimed):
  - **Rule A (primary)**: `first_observed_trading_date <= fiscal_year_end`
    — main sample 1013 eligible pairs (81 pos / 932 neg).
  - **Rule B (listing-timing robustness)**:
    `first_observed_trading_date <= fiscal_year_start` — main sample 994 eligible
    pairs (80 pos / 914 neg).
  - **Rule C rejected**: `first_observed_trading_year < fiscal_year` — coarse
    year-level approximation, no advantage over exact-date Rule B; retained only
    as a documented rejected readiness candidate.
  - Approval record: `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json`
    and `README_GATE_B_RULE_APPROVAL.md`.
- **`stage124-gate-b-execution` completed** — Applied the approved rules to the
  frozen Stage123 data (1331 company-year rows, 1200 pairs, 130 tickers). Four
  sample designs:
  - `main_rule_a_primary` = 1013 (81 pos / 932 neg)
  - `main_rule_b_listing_robustness` = 994 (80 pos / 914 neg)
  - `expanded_rule_a_company_scope_robustness` = 1057 (81 pos / 976 neg)
  - `expanded_rule_b_combined_robustness` = 1036 (80 pos / 956 neg)
  - Unresolved listing rows: Rule A = 4, Rule B = 10 (preserved, never
    zero-filled). Outputs in `project/stage124/gate_b_final/`; module
    `project/src/stage124_gate_b_execution.py`; 38 focused tests (717 full-suite).
- Gate B **executed** (`gate_b_started = true`); **modeling remains prohibited**
  until `stage125-modeling-readiness` is approved.

## 2026-07-11

- **`stage124-gate-b-readiness` completed** — Dry-run comparison of three Gate B
  eligibility rules (A/B/C) against the verified master and Stage123 modeling data.
  Rule A: `first_observed_trading_date <= fiscal_year_end` (1013 eligible pairs).
  Rule B: `first_observed_trading_date <= fiscal_year_start` (994 eligible pairs).
  Rule C: `first_observed_trading_year < fiscal_year` (995 eligible pairs).
  Stage123 baseline: 1085 eligible pairs. No rule finalized.
- **Output files** in `project/stage124/gate_b_readiness/`: comparison summary JSON,
  per-row audit CSV, pair impact summary CSV, unmatched/ambiguous rows CSV, QC report
  (all pass), metadata/hashes, and README.
- **45 focused tests** in `project/tests/test_stage124_gate_b_readiness.py`
  covering hash verification, schema validation, rule determinism, fiscal_year_start
  computation (leap year Esfand 30 fix), date semantics, no-rows-dropped, and output
  integrity.
- **`fiscal_year_start` computation fix**: for Jalali leap-year Esfand 30 dates
  (e.g. 1399/12/30), the naive "fy_end - 1 year + 1 day" fails because the previous
  year's Esfand has only 29 days. Fixed to use month-based logic: month 12 →
  `jdatetime.date(fy_end.year, 1, 1)`, otherwise `jdatetime.date(fy_end.year - 1,
  fy_end.month + 1, 1)`.
- **Workbook hash note**: `stage123_workbook.xlsx` hash differs from Stage123 metadata
  (gitignored, regenerable, not used in analysis). CSV files verified successfully.
- Updated ROADMAP: `last_completed_research_action_id` → `stage124-gate-b-readiness`,
  `next_research_action_id` → `stage124-gate-b-rule-approval`.
- **Next action** is `stage124-gate-b-rule-approval` — user and scientific reviewer
  must approve the final Gate B rule from the comparison report.

## 2026-07-10

- **Retired the Human-in-the-Loop (HIL) and manual listing-date research path.**
  The HIL Streamlit dashboard (`stage124_part03_hil_panel.py`), the manual intake
  runner (`run_stage124_batch02_part03_manual_intake.py`), their tests, and the
  `streamlit` dependency have been removed. The `part03_manual_intake_input.csv`
  template and the HIL panel README were also deleted.
- **`stage124-batch02-part03-1b-1` superseded** — cancelled by the official TSETMC
  API (not completed). The verified master (`listing_master_verified_stage124.csv`)
  now contains 130 unique tickers with dates in `first_public_trading_date_jalali`
  and `first_public_trading_date_gregorian`
  (date_semantics=`first_observed_trading_date_from_official_tse_api`,
  status `verified_tse_api_first_observed_trade`). These dates are first observed
  trading dates, not necessarily IPO, admission, or listing dates.
- **`stage124-official-api-finalize` completed** — Finalized verified master for
  130 tickers using official TSETMC first-observed-trade dates; merged through PR
  #15, merge commit 22c2d0c.
- **Next action** is `stage124-gate-b-readiness` (Gate B readiness / eligibility
  rebuild planning). Gate B execution and modeling are not in scope.
- Updated ROADMAP front matter: `active_research_workstream_id` changed to
  `stage124-gate-b-readiness` (Part 3 is no longer the active path);
  `last_completed_research_action_id` changed to `stage124-official-api-finalize`;
  `qc_scope: stage124-batch02-part03` added so the generator can still locate the
  Part 3 QC report.
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
