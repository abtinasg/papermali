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
- Stage124 Gate B is **completed and frozen**: four sample designs produced,
  canonical + filtered outputs verified, 58 focused tests (736 passed, 1 skipped,
  local results — no GitHub Actions configured).
- **Modeling remains prohibited.** Stage125 is a **Research Design & Data
  Readiness** stage that performs **no** modeling; modeling begins only when
  Stage126 (M1 Financial Baseline) is explicitly approved. See
  [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md).

## Verified listing master (Stage124)

- `listing_master_verified_stage124.csv` **exists** and contains exactly **130
  unique tickers**. It is the canonical source for first-trading-date information.
- The date columns are `first_public_trading_date_jalali` and
  `first_public_trading_date_gregorian`, with
  `date_semantics=first_observed_trading_date_from_official_tse_api` and status
  `verified_tse_api_first_observed_trade`. These dates are **first observed
  trading dates** from the official TSETMC API — they are **not** necessarily IPO,
  admission, or listing dates.
- The Human-in-the-Loop (HIL) dashboard and manual intake runner have been
  **retired**. The manual research path for the 10 Part 3 tickers
  (`stage124-batch02-part03-1b-1`) is **superseded** by the official TSE API.

## Gate B eligibility rules (Stage124 Batch02) — approved

- **Rule A is the approved PRIMARY Gate B listing rule** for the main
  financial-statement sample: `first_observed_trading_date <= fiscal_year_end`.
- **Rule B is the approved listing-timing ROBUSTNESS rule**:
  `first_observed_trading_date <= fiscal_year_start`. Rule B must **not** replace
  Rule A in the primary sample and must **not** be treated as a future
  market-data / minimum trading-history / market-lookback rule.
- **Rule C is REJECTED** as the final rule (`first_observed_trading_year <
  fiscal_year`): a coarse year-level approximation with no methodological
  advantage over the exact-date Rule B. Rule C may remain documented only as a
  rejected readiness candidate and must never be a final canonical eligibility
  flag.
- Approval basis: **explicit user/data-owner confirmation** supported by the
  completed Gate B readiness comparison (no external reviewer approval claimed).
  Recorded in `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json`.
- Gate B **execution is completed and frozen**. **Modeling remains prohibited**
  through all of Stage125 (Research Design & Data Readiness); it begins only when
  Stage126 (M1 Financial Baseline) is explicitly approved.

## Stage125 research design (locked 2026-07-13)

The research contract for the paper is frozen in
[`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md). Firm points:

- **Incremental nested blocks:** M1 Financial → M2 Market → M3 Parsimonious Macro →
  M4 Structured Audit/Governance, compared on the same common sample, same temporal
  split, and paired predictions.
- **M5 (Persian text / text modeling) is removed** from the paper and roadmap
  (no TF-IDF, embeddings, or heavy language models).
- **All data and analyses depending on accessibility < 3 are removed.**
- **accessibility = 3 is NOT an automatic pass** — it only admits a variable to the
  coverage/quality pilot. A variable enters the main analysis only if it also passes
  provenance, `published_at`/`available_at`, coverage, and event-count Gates.
- **Allowed core models:** regularized Logistic Regression, Random Forest, XGBoost.
  Class weighting is the primary imbalance method; SMOTE is train-fold robustness only.
- **Primary metric (locked before running): PR-AUC**; operational `Recall@K` /
  `Lift@K`; calibration via Brier/curve; ROC-AUC complementary only; temporal splits;
  single locked final test.
- Full out-of-scope list (order-book/bid–ask, non-reproducible free-market FX,
  director biography/network/interlocking, social/news/ESG unstructured sources,
  large searched macro sets, multiple post-hoc regime definitions, real cost-matrix/
  DCA, algorithm inflation) is recorded in `STAGE125_RESEARCH_DESIGN.md` §5.
- Any change to target, universe, eligibility, cutoff, primary metric, or the locked
  test requires an explicit research decision and a new version of that contract.
- **Stage122–Stage124 files are not rewritten or redefined during Stage125.**

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
