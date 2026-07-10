# DECISIONS — firm, non-negotiable

These are stable project decisions. Change them only deliberately (and note it in
`CHANGELOG.md`). They are **inputs** to the handoff state, not generated.

## Data integrity

- **No value is guessed.** If a source value is not found, it stays **Missing**.
- **Every date/number is documented to a source** (`source_file`, `source_url`,
  SHA-256 hashes).
- Admission-only dates are **not** treated as public-entry dates.

## Pipeline order & target

- Authoritative pipeline: **Stage122 → Stage123 → Stage124**. Each stage consumes the
  previous stage's frozen output.
- Primary target: **`FD_target_main`** (composite operational distress), frozen in
  Stage122, plus two robustness targets.
- `run_all.py` is the **legacy Stage121 baseline only**; it is not run for the current
  target. The current modeling pipeline will be redesigned after the Stage123 freeze.

## Freeze & read-only guarantees

- Stage122 / Stage123 / targets / financials / ratios / statement-scope are
  **read-only**. Their SHA-256 are checked before and after every run; a mismatch
  aborts.
- Frozen assets are tracked via the existing `metadata_and_hashes_stage12{2,3}.json`
  manifests (see `FROZEN_ASSETS.md`).

## Phase guardrails (current data-freeze phase)

- **No** model / tuning / SHAP / SMOTE / calibration / report in this phase.
- Stage124 produces review templates; nothing is promoted to
  `verified_user_confirmed` outside an explicit user-confirmation step.
- Gate B execution and Part 2 modeling are not yet in scope; the next step is
  Gate B readiness / eligibility rebuild planning only.

## Verified listing master (Stage124)

- `listing_master_verified_stage124.csv` **exists** and contains exactly **130
  unique tickers**. It is the canonical source for first-trading-date information.
- The date column is `first_observed_trading_date_from_official_tse_api` with
  status `verified_tse_api_first_observed_trade`. These dates are **first observed
  trading dates** from the official TSETMC API — they are **not** necessarily IPO,
  admission, or listing dates.
- The Human-in-the-Loop (HIL) dashboard and manual intake runner have been
  **retired**. The manual research path for the 10 Part 3 tickers
  (`stage124-batch02-part03-1b-1`) is **superseded** by the official TSE API.

## Ranking & evidence (Stage124 Batch02)

- Tiered **lexicographic** ranking (A–E), not a weighted score.
- Four separate event-type date columns (admission / listing / first-public-offering
  / first-public-trading); they are never conflated.
- `ready_for_user_review` is `false` unless the evidence standard is met.

## Engineering / git

- Two-commit workflow: **code-commit → artifact-commit → merge-commit**. QC reports
  reference the **code** commit (e.g. `076388…`), while `main` points at the merge
  (e.g. `fec87cc…`).
- Bulky outputs (models, figures, workbooks, panels) are gitignored; only source and
  small QC/metadata/audit files are committed.
