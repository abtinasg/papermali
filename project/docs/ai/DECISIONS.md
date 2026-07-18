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

## Stage125 Part 3B.1E — Conservative six-month availability lag (2026-07-18)

Human-supervisor-approved methodological pivot
(`stage125-part3b-conservative-lag-decision-lock` /
`stage125-part3b1e-conservative-six-month-lag-decision-lock`):

- **Financial data status:** researcher-verified and **frozen**. No
  financial-value re-extraction or revalidation in this stage.
- **Broad CODAL capture:** stopped / not authorized. The five-row CODAL
  metadata pilot did not justify expansion; PR #47 was closed unmerged;
  no 80-row or 130-company CODAL metadata capture is planned.
- **Availability method:** `fixed_conservative_lag` with
  `conservative_lag_months = 6`.
  `assumed_available_at_conservative = fiscal_year_end + 6 calendar months`.
  This is a methodological anti-leakage assumption — **not** an observed
  `PublishDateTime`, CODAL publication date, verified source timestamp, or
  observed `available_at`. Do not write the assumed date into those fields.
- **Alignment:** predictors from fiscal year **t** may only predict distress
  target **t+1**. A predictor observation may only be used after the six-month
  lag has elapsed.
- **Non-claims:** Stage125 incomplete; Stage126 and modeling remain
  unauthorized. Markers:
  `broad_codal_capture_stopped=true`,
  `financial_data_researcher_verified_frozen=true`,
  `conservative_availability_lag_locked=true`,
  `row_level_publish_datetime_collection_required=false`.

## Stage125 Part 3B.1A — CUT-A Available-at Operationalization (2026-07-17)

Maintenance decision lock only (`stage125-part3b1a-cut-a-available-at-operationalization-lock`).
Historical contract for *observed* CODAL `PublishDateTime` mapping when an
exact document is bound. **Superseded for modeling-path availability** by the
2026-07-18 conservative six-month lag decision (Part 3B.1E): row-level
PublishDateTime collection is no longer authorized. Does **not** by itself
advance research action pointers.

- **Operational `available_at`** for predictor-year financial statements =
  `PublishDateTime` of the exact matched official CODAL `LetterSerial`/version,
  only when the document is exactly bound to the predictor row and the canonical
  source version.
- **`SentDateTime` ≠ `available_at`**: preserved raw for audit/comparison only;
  never cutoff or public availability; even when equal to `PublishDateTime`,
  mapping still uses `PublishDateTime`.
- **Rationale:** `PublishDateTime` is the operational public-release timestamp;
  `SentDateTime` may be publisher-send time; `PublishDateTime` is more
  conservative / leakage-safe. Methodological operationalization — not inference
  from local filenames or cache mtimes.
- **Exact-document binding** and **revision/version** policy are fail-closed
  (each `LetterSerial` is an independent version; multi-document rows stay
  `UNRESOLVED` with
  `multi_document_predictor_row_requires_separate_adjudication`).
- **Normalized `revision_status`** matches the frozen provenance schema only:
  `original` / `revision` / `restatement`. `correction` is not a normalized
  status. CODAL «اصلاحیه» may be retained in `revision_status_raw` and maps to
  `revision` only when that mapping is explicit. Exact
  `values_source_letter_serial == letter_serial == canonical_letter_serial`
  is authoritative for revision/restatement rows (boolean flags cannot bypass).
- **Timezone:** raw Jalali CODAL timestamps normalized via `jdatetime==6.0.1` +
  `zoneinfo.ZoneInfo("Asia/Tehran")` → UTC ISO-8601 using UTC round-trip
  fold=0/fold=1 classification; nonexistent spring-forward ≠ ambiguous;
  no fixed `+03:30` for all years; malformed/nonexistent/ambiguous/naive →
  `available_at=null`.
- **Non-claims:** no network; no real `available_at` assignment; no pilot cutoff
  resolution; no extraction/scoring/Gate admission; no Part 3B.2 / Stage126 /
  modeling. Marker: `cut_a_available_at_operationalization_locked=true`.

## Stage125 Part 0 / Part 1 / Part 2 status (2026-07-14)

> **Historical snapshot (as of 2026-07-14).** Do not treat the bullets below as
> current project status. For live state, use `ROADMAP.md`, `CURRENT_STATE.md`,
> and `OPEN_TASKS.md`. After this date, Part 3B became **active but incomplete**
> (endpoint/source-origin feasibility probe only), and Part 3B.1 was recorded as
> a **maintenance** Decision Lock (`part3b1_decision_locked=true`) without
> advancing research action pointers.

- **Part 0 (Research Design Decision Lock) is CLOSED.** PR #21 is **MERGED**;
  `main` contains merge commit `d39e770ff49729a2f0b1b0262c0b1aa5ae41b0c4`.
- **Part 1 (Data Dictionary & Provenance Contract) is COMPLETED and MERGED.**
  PR #21 merged; tracked as `stage125-part1-data-contract`.
- **Part 2 (Prediction-time & Leakage Contract) is COMPLETED and MERGED.**
  PR #27 post-merge Handoff refresh merged (`main` @ `c6cbb6b7…`); tracked as
  `stage125-part2-prediction-time-contract`.
- **Part 3A (Accessibility & Pilot Protocol Lock) is COMPLETED and MERGED.**
  PR #29 merged (`main` @ `4e15cb7…`); tracked as `stage125-part3a-pilot-protocol-lock`.
  Protocol assets frozen. Locks 10 registered M2–M4 candidates, proposed
  accessibility rubric, gate protocol, sampling frame, pilot options, Part 3B
  evidence schema. **No** evidence collection, **no** network access, **no**
  scores assigned.
- **Part 3A.1 (User-Approved Pilot Decision Lock) is AUTHORIZED and ACTIVE.**
  Tracked as `stage125-part3a1-decision-lock`; advances **no** research action.
  Records user-approved rubric `stage125_part3a_v1` (approved but not applied),
  G09–G14 pilot thresholds, and locked `pilot_option_event_enriched` pilot
  (80 pairs; event-enriched; not population-representative; not modeling
  sample). **No** evidence, **no** network access, **no** scores applied.
- **Part 3B is NOT started.** Evidence capture belongs to Part 3B only.
- **`modeling_started` remains `false`. `part2_started` is `true` (contract only,
  not modeling). `part3a_protocol_locked` is `true`. `part3a_decision_locked` is
  `true` (Part 3A.1). `part3b_started` is `false`. No network extraction was
  performed.** Modeling begins only when Stage126 is approved.

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
