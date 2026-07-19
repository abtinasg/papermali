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

## Stage125 Part 4 — Statistical Analysis Plan (2026-07-19)

Research action `stage125-part4-statistical-analysis-plan`:

- Active contract: `stage125_part4_sap_v2` (v1 retained in Git history).
- Locks M1 primary ordered features (exactly 9 admitted), M1 coverage-audit
  candidates (10, including rejected `revenue_growth_period_adjusted`), M1
  target-proximity robustness (exactly 6), nested M2–M4 blocks (9/12/15/19),
  four sample designs, target-year temporal folds (development 1393–1399;
  final test 1400–1402), preprocessing with pre-imputation missingness masks,
  allowed model families, finite hyperparameter budget (32/block), seeds,
  PR-AUC primary, Recall@10%/Lift@10%, calibration, paired ticker-cluster
  bootstrap (2000; Holm α=0.05), and SHAP stability contracts.
- Human supervisor rejected `revenue_growth_period_adjusted` from admitted M1:
  raw Fold 1 training coverage `148/245 = 0.6040816327` < 0.75. No
  first-observation denominator exception. Feature retained in frozen data and
  coverage audit as `rejected_m1_primary_coverage_gate_failed`.
- Strict positive/negative/missing target event accounting; final-test event
  threshold is claim eligibility only (not predictor admission). SMOTE
  robustness disables class weighting.
- Primary paper result: `main_rule_a_primary` × `FD_target_main_t_plus_1`.
- Part 3C analysis-ready / audited hashes are pinned; financial values and
  targets remain frozen; رمپنا remains audit-only.
- M3 remains not admitted (no authoritative CBI endpoint). No M2/M3/M4 data
  collected in Part 4.
- Article-141-only final-test event count on the primary sample is below 10
  positives → distributional/descriptive robustness only.
- **Non-claims:** no model fitting; no prediction; no SHAP computation; no
  final-test predictor inspection for admission/tuning; Stage125 incomplete
  until Part 5; Stage126 and modeling unauthorized. Historical next after
  Part 4: `stage125-part5-readiness-closure`.

## Stage125 Part 5 — Readiness Closure (2026-07-19)

Research action `stage125-part5-readiness-closure`:

- Closes Stage125 under Gate 125.0 with outcome
  `READY_FOR_STAGE126_M1_HUMAN_AUTHORIZATION_DECISION`.
- Distinguishes **ready for a future authorization decision** from
  **authorized to execute modeling**.
- Keep/drop/defer vocabulary locked; M1 primary 9 ready; M1 target-proximity
  6 robustness; Revenue Growth audit-only; Article-141 descriptive-only;
  M2 deferred; M3 not admitted; M4 deferred; M5 removed.
- Part 3B expansion superseded/nonblocking (`part3b_completed` remains false).
- Final test 1400–1402 remains locked; four-month lag active; six-month
  historical only.
- Stage126 M1 entry contract recorded with
  `entry_readiness=READY_FOR_HUMAN_AUTHORIZATION_DECISION` and
  `stage126_authorized=false`, `modeling_authorized=false`,
  `final_test_unlocked=false`.
- **Non-claims:** no model fitting; no prediction; no SHAP; no SMOTE
  execution; no final-test predictor inspection; Stage126 not authorized and
  not started. Next pointer `stage126-m1-financial-baseline` is **future /
  blocked pending explicit human authorization / not started**.

## Stage125 Part 3C — Leakage-safe dataset finalization (2026-07-18)

Research action `stage125-part3c-leakage-safe-dataset-finalization`:

- Operationalizes the Part 3B.1E locked six-month **Jalali** calendar lag for
  all four frozen Gate B sample designs. Gate B **audit membership**, targets,
  and positive counts are unchanged on the audited pair surface.
- Predictors join Stage123 on `predictor_row_key_t` → `row_key` (fail-closed
  one-to-one). Targets are **copied** from Gate B pair files (never recomputed).
- Assumed availability uses `assumed_available_at_conservative` only; never
  written as observed `PublishDateTime` / `available_at` / `SentDateTime`.
- Part 3B broad CODAL expansion remains **superseded**. Financial data remain
  researcher-verified and frozen.
- One audited fiscal-year-calendar-shift timing exception is recorded
  (`رمپنا|1396` → `رمپنا|1397`): retained in the **audited pair** surface with
  `timing_relation_exception=true`,
  `assumed_before_target_fiscal_year_end=false`,
  `timing_eligible_for_analysis=false`, `timing_eligible_for_model=false`, and
  exclusion reason
  `assumed_availability_not_before_target_fye_authorized_calendar_shift`;
  **not** timing-safe; **not** eligible for analysis-ready / model matrices.
  Any other timing violation fails closed. No row is silently dropped.
- Full-membership outputs are **audited pair datasets**. Only the filtered
  timing-eligible outputs (`assumed_before_target_fiscal_year_end=true`) are
  **leakage-safe analysis-ready datasets**. Gate B membership preservation
  refers to the audit population, not necessarily the analysis-ready population.
- Feature selection / model fitting / Stage126 remain unauthorized. Stage125
  remains incomplete. Next research action:
  `stage125-part4-statistical-analysis-plan`.

## Stage125 Part 3C — Four-month regulatory lag revision (2026-07-19)

Explicit human-supervisor approval supersedes the active six-month lag for
the modeling path (`stage125-part3c-four-month-regulatory-lag-revision`):

- **Active method:** `fixed_regulatory_lag` with `active_lag_months = 4`
  (Jalali calendar).
  `assumed_available_at_regulatory = fiscal_year_end_t + 4 Jalali months`.
- **Semantics:** methodological regulatory-deadline assumption — **not**
  observed publication time / `PublishDateTime` / `available_at`.
- **Historical six-month decision:** retained (`part3b1e_*` artifacts) but
  `historical_six_month_decision_active=false`.
- **Timing rule (general):**
  `assumed_available_at_regulatory < target_fiscal_year_end_t_plus_1`;
  no ticker-specific authorization. رمپنا 1396→1397 remains audit-only.
- **Features:** Part 3C candidate inventory only; zero fields approved for
  model entry (Part 4 locks features).
- **Non-claims:** Stage126 / modeling unauthorized.

## Stage125 Part 3B.1E — Conservative six-month availability lag (2026-07-18)

Human-supervisor-approved methodological pivot
(`stage125-part3b-conservative-lag-decision-lock` /
`stage125-part3b1e-conservative-six-month-lag-decision-lock`).
**Superseded for the active modeling path** by the 2026-07-19 four-month
regulatory lag revision; retained as historical provenance:

- **Financial data status:** researcher-verified and **frozen**. No
  financial-value re-extraction or revalidation in this stage.
- **Broad CODAL capture:** stopped / not authorized. The five-row CODAL
  metadata pilot did not justify expansion; PR #47 was closed unmerged;
  no 80-row or 130-company CODAL metadata capture is planned.
- **Availability method (historical):** `fixed_conservative_lag` with
  `conservative_lag_months = 6`.
  `assumed_available_at_conservative = fiscal_year_end + 6 calendar months`.
  This was a methodological anti-leakage assumption — **not** an observed
  `PublishDateTime`, CODAL publication date, verified source timestamp, or
  observed `available_at`.
- **Alignment:** predictors from fiscal year **t** may only predict distress
  target **t+1**.
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
