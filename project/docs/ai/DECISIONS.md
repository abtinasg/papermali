# DECISIONS — firm, non-negotiable

These are stable project decisions. Change them only deliberately (and note it in
`CHANGELOG.md`). They are **inputs** to the handoff state, not generated.

## Data integrity

- **No value is guessed.** If a source value is not found, it stays **Missing**.
- **Every date/number is documented to a source** (`source_file`, `source_url`,
  SHA-256 hashes).
- Admission-only dates are **not** treated as public-entry dates.

## Pipeline order & target

- **Frozen data-preparation pipeline:** **Stage122 → Stage123 → Stage124**. Each stage
  consumes the previous stage's frozen output.
- **Research-design and modeling sequence:** **Stage125 → Stage126**.
  - **Stage125** completed the research-design, leakage, SAP and readiness contracts
    (Part 3C leakage-safe finalization, Part 4 statistical analysis plan lock, Part 5
    readiness closure). Stage125 performs no modeling.
  - **Stage126 M1** is the current human-authorized modeling workstream. Primary M1
    development-fold tuning is completed. The Stage126 research action remains
    incomplete.
- Primary target: **`FD_target_main`** (composite operational distress), frozen in
  Stage122, plus two robustness targets.
- `run_all.py` is the **legacy Stage121 baseline only**; it is not run for the current
  target. The current authorized modeling path is the Stage126 M1 primary
  development-fold tuning pipeline.

## Freeze & read-only guarantees

- Stage122 / Stage123 / targets / financials / ratios / statement-scope are
  **read-only**. Their SHA-256 are checked before and after every run; a mismatch
  aborts.
- Frozen assets are tracked via the existing `metadata_and_hashes_stage12{2,3}.json`
  manifests (see `FROZEN_ASSETS.md`).

## Phase guardrails

### Historical Stage125 guardrails (data-freeze phase)

- **No** model / tuning / SHAP / SMOTE / calibration / report in this phase.
- Stage124 Gate B is **completed and frozen**: four sample designs produced,
  canonical + filtered outputs verified, 58 focused tests (736 passed, 1 skipped,
  local results — no GitHub Actions configured).
- **Modeling remains prohibited** through Stage125 (Research Design & Data
  Readiness); modeling begins only when Stage126 (M1 Financial Baseline) is
  explicitly approved. See
  [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md).

### Current Stage126 M1 guardrails

- Stage126 M1 is human-authorized and started.
- Primary M1 development-fold tuning is completed.
- The Stage126 research action is not yet completed.
- M1 robustness is not started.
- No full-development refit has occurred.
- The final test remains locked.
- No M2/M3/M4 data collection or modeling has occurred.
- SHAP, SMOTE robustness and network extraction remain prohibited.

### Stage126 M1 robustness Part 0 — decision lock (2026-07-22)

- The robustness **execution contract is locked** in an additive record
  (`stage126_m1_robustness_execution_contract_v1`); this is a **decision lock
  only** and authorizes **no** robustness execution. Part 1 is not authorized or
  started.
- Six categories, in binding execution order: (1)
  `m1_target_proximity_six_feature_set`, (2) `main_rule_b_listing_robustness`,
  (3) `expanded_rule_a_company_scope_robustness`, (4)
  `expanded_rule_b_combined_robustness`, (5) `persistent_loss_robustness_target`
  (primary Rule A sample only), (6) `smote_training_fold_only_robustness`.
- One factor at a time; all three model families every category; **no retuning**
  (reuse the primary selected configurations, which robustness may not replace);
  the two locked development folds only; metrics limited to PR-AUC, ROC-AUC,
  Brier, Recall@10%, Lift@10%; no calibration/bootstrap/Holm/winner selection.
- SMOTE category uses training-fold-only SMOTE/SMOTENC (SMOTENC when appended
  binary missingness indicators are present, marked categorical), sampler
  `random_state=20260725`, class weighting disabled.
- All six categories are **sensitivity analyses only** — they may not change a
  selected configuration, the primary model-family ordering, select a final
  winner, unlock the final test, trigger a refit, or advance M2/M3/M4.
- **Packaging:** one robustness category per micro-part PR; each future Part
  requires a separate explicit human authorization. Primary Stage126 artifacts
  remain byte-identical; the final test remains locked and untouched.

### Stage126 M1 robustness Part 1 — executed (2026-07-22)

- **Part 1 (`m1_target_proximity_six_feature_set`) was explicitly
  human-authorized and completed on the development folds only.**
- **Only the feature set changed:** the six-feature
  `M1_TARGET_PROXIMITY_ROBUSTNESS` set (12 transformed columns). Sample, target,
  folds, selected configurations, imbalance policy, seeds and metrics unchanged.
- **No retuning** (frozen selected configurations reused; 0 tuning searches;
  exactly 22 fits / 22 predictions). **No full-development refit.**
- **Final test remains locked and untouched**; no SMOTE/SMOTENC, SHAP,
  calibration, bootstrap or Holm; zero network access.
- **Sensitivity analysis only** — Part 1 does not replace the primary results
  and selects no paper winner.
- **Observed ordering sensitivity (reported, not acted upon).** Primary pooled
  PR-AUC ordering: **Logistic > RF > XGBoost**. Part 1 observed pooled PR-AUC
  ordering: **XGBoost > RF > Logistic**. **All three pooled PR-AUC values
  declined** (Logistic −0.127639458886 / −28.63%, RF −0.070307846896 / −17.47%,
  XGBoost −0.017282221021 / −4.85%). The observed Part 1 sensitivity ordering
  differs from the primary development ordering; this does **not** change the
  locked primary ordering used for confirmatory interpretation, does **not**
  replace the primary results, and does **not** select a paper winner. This is a
  development-only sensitivity finding, recorded in
  `stage126_m1_robustness_part1_primary_comparison.json` and reported to the
  human supervisor. No selected configuration changed, no refit was authorized,
  no automatic scientific action was triggered, and the final test stays locked.
- **Part 2 (`main_rule_b_listing_robustness`) is not authorized and not
  started.** The consumed Part 1 authorization confers no standing
  authorization for any later category.

### Stage126 live-versus-historical test-suite boundary (2026-07-23)

- The frozen Stage125 Part 5 file contains historical tests explicitly marked
`live_successor_state`. Those tests remain **byte-identical** and are verified
against the frozen Part 2 successor reference commit
`6412b45c4adc6584a5567c7c96e0932f68f31e8a`. **They are not part of the current
Stage126 live gate.** The default Stage126 repository test suite excludes only
that historical marker — never the file, never a node ID, never a skip or
xfail. **All non-historical tests remain active.** The Stage126 current-state
validator remains the sole current-state validation surface.
- **Governance basis.** This is a consistent application of the existing
  `stage126-validation-architecture-boundary-lock`, **not** a scientific-error
  exception. Stage125 Part 5 was not reopened and its pins were not changed; the
  frozen test file is byte-identical at
  `0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71`.
- **Live gate surfaces:** the Stage126 current-state validator, the current
  Stage126 scientific micro-part tests, the AI Handoff validator, and every
  non-historical repository test.
- **Exclusion mechanism:** marker expression only. No `--ignore`, no
  `--deselect`, no node-ID targeting, no skip/xfail, no collection hook, no
  broad skip pattern. Proven by dedicated fail-closed tests.
- **Historical tests are preserved, not deleted.** They are executed against the
  reference commit by a read-only runner that never modifies the branch,
  `main`, the Stage125 tree or the Handoff.

### Stage126 M1 robustness Part 3 — executed (2026-07-23)

- **Part 3 (`expanded_rule_a_company_scope_robustness`) was explicitly
  human-authorized and completed on the development folds only.** The
  authorization text is 423 UTF-8 bytes and hashes to
  `f1230aa0dac18670695d41d99709cfd4ba5619e96e6f93c2e0678387ab28dab1`; it is
  consumed by this execution and grants no standing authorization, no merge, no
  Part 4, no refit, no final-test access or evaluation, no calibration,
  threshold optimization, bootstrap, Holm correction, p-values or winner
  selection, and no SMOTE/SMOTENC/SHAP/M2/M3/M4.
- **Only the company scope changed:** 1056 analysis-ready rows across 124
  companies (80 positive / 976 negative), 695 development rows (68 / 627), fold
  roles 254 / 215 / 469 / 226. Target, feature definitions and order,
  preprocessing, missingness-indicator logic, selected configurations, model
  families, folds, seeds, metrics and class weighting all unchanged.
- **No retuning** (0 tuning searches; exactly 22 fits / 22 predictions). **No
  full-development refit.** XGBoost class weights recomputed per training fold
  (221/33, 411/58) — never from validation rows and never reused from the
  primary sample.
- **The final test remained locked.** 361 final-test identities were counted
  only through the frozen temporal split contract; zero predictor rows, zero
  target rows, zero predictions and zero metrics.
- **Sample delta:** Expanded Rule A is a strict superset of primary Rule A —
  44 expanded-only rows, 0 primary-only rows, +5 companies, +0 positive, +44
  negative; +29 development rows (all negative); 20 added OOF identities, all
  with target 0; +15 final-test identities.
- **Development-only sample-sensitivity evidence.** Pooled PR-AUC: Logistic
  0.442885909854 (−0.64%), RF 0.390702328450 (−2.92%), XGBoost 0.356560707550
  (+0.00%). **The locked primary ordering Logistic > RF > XGBoost is
  preserved**, the largest absolute change is 0.0117, and because the added
  observations are negative-only the expanded scope does not materially change
  interpretation. Primary results were not replaced, the primary ordering lock
  is unchanged, no paper winner was selected and this is not a new confirmatory
  model comparison. The Part 2 comparison is separated and descriptive only.
- **Part 4 (`expanded_rule_b_combined_robustness`) is not authorized and not
  started.** Parts 4-6 remain outstanding.
- **Nothing closed was touched.** Part 1 and Part 2 packages (scientific and
  verification), the primary Stage126 artifacts and the Stage125 tree are
  byte-identical; Stage125 Part 5 remains historical and immutable and was not
  used as a gate. The independent current-state validator recognized Part 3
  generically with no source change.

### Stage126 M1 robustness Part 4 — executed (2026-07-24)

- **Part 4 (`expanded_rule_b_combined_robustness`) was explicitly
  human-authorized and completed on the development folds only.** The
  authorization text is 418 UTF-8 bytes and hashes to
  `e40852d9e2a78cc6d9b3079379abd0fed8f4921b65bec00ecf58d5aad78fd1b4`; it is
  consumed by this execution and grants no standing authorization, no merge, no
  Part 5, no refit, no final-test access or evaluation, no calibration,
  threshold optimization, bootstrap, Holm correction, p-values or winner
  selection, and no SMOTE/SMOTENC/SHAP/M2/M3/M4.
- **Only the combined Rule B sample changed:** 1035 analysis-ready rows across
  122 companies (79 positive / 956 negative), 682 development rows (68 / 614),
  fold roles 250 / 211 / 461 / 221. Target, feature definitions and order,
  preprocessing, missingness-indicator logic, selected configurations, model
  families, folds, seeds, metrics and class weighting all unchanged.
- **No retuning** (0 tuning searches; exactly 22 fits / 22 predictions). **No
  full-development refit.** XGBoost class weights recomputed per training fold
  (217/33, 403/58) — never from validation rows and never reused from any
  other sample.
- **The final test remained locked.** 353 final-test identities were counted
  only through the frozen temporal split contract; zero predictor rows, zero
  target rows, zero predictions and zero metrics.
- **Three independently recomputed sample-delta comparisons, identities
  only:** versus Part 2 (main Rule B) Part 4 is a strict superset (42
  Part4-only rows, 0 Part2-only, all additions negative); versus Part 3
  (expanded Rule A) Part 4 is a strict subset (21 Part3-only rows, 0
  Part4-only, all removals negative); versus the locked primary sample the
  relationship is neither a subset nor a superset (42 Part4-only, 19
  primary-only, net +23 rows, all differences negative-only).
- **Development-only sample-sensitivity evidence.** Pooled PR-AUC: Logistic
  0.444983882478 (−0.17%), RF 0.396418788419 (−1.50%), XGBoost
  0.355210803326 (−0.37%). **The locked primary ordering
  Logistic > RF > XGBoost is preserved**, and because every identity
  difference versus primary, Part 2 and Part 3 is negative-only the combined
  sample does not materially change interpretation. Primary results were not
  replaced, the primary ordering lock is unchanged, no paper winner was
  selected and this is not a new confirmatory model comparison. The Part 2
  and Part 3 comparisons are separated and descriptive only.
- **Part 5 (`persistent_loss_robustness_target`) is not authorized and not
  started.** Parts 5-6 remain outstanding.
- **Nothing closed was touched.** Parts 1, 2 and 3 packages (scientific and
  verification), the primary Stage126 artifacts and the Stage125 tree are
  byte-identical; Stage125 Part 5 remains historical and immutable and was not
  used as a gate. The independent current-state validator recognized Part 4
  generically with no source change.

### Stage126 current-state validation — generic enforcement (2026-07-23)

- **No hard-coded current state.** The validator derives the completed prefix,
  the next registered category and the last completed micro-part from the Part 0
  execution order, the discovered per-part packages and their completion locks.
  The three expected-state constants no longer exist.
- **Closed parts are protected by a generic registry**
  (`stage126_closed_part_registry.json`), not by per-part constants. It pins
  each closed part's scientific artifacts, verification artifacts and
  source/runner/tests; already-registered hashes may never change.
- **Verification-only artifacts are immutable too**, exactly as the governance
  decision requires — QC reports, metadata manifests, Part 5 compatibility
  records and READMEs all fail validation on byte drift.
- **The Handoff architecture fields are enforced inside the validator**, not
  merely reported.
- **Two QC roles are explicit:** current-state validation versus the newest
  completed scientific micro-part. Neither is described by an ambiguous
  `selected_qc` field alone.
- **A future part changes nothing older.** An end-to-end synthetic Part 5 builds
  and checks through the real validator without modifying validator source or
  any Part 1, Part 2, Part 3, Part 4 or Stage125 file.

### Stage126 validation-architecture boundary lock (2026-07-23)

- **Human governance decision** (SHA-256
  `8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1`),
  recorded verbatim in
  `stage126_validation_architecture_boundary_decision.json`.
- **Stage125 Part 5 is historical and immutable.** It is no longer a live
  successor-state validator for Stage126. Its source, runner, test and the whole
  `project/stage125/**` tree are hash-pinned in
  `stage126_historical_boundary_manifest.json`. Historical materials are neither
  deleted nor rewritten.
- **The independent Stage126 current-state validator is the sole current-state
  validation surface** (`stage126_current_state_validator_v1`). It never
  imports the Part 5 source, never executes its runner and never calls its
  `validate_actual_handoff`; this is proven structurally by AST-based tests
  rather than asserted.
- **Later parts must not regenerate earlier parts' verification artifacts.**
  Part 1 and Part 2 are closed historical micro-part packages. The previous
  coupling — earlier packages embedding the hash of a then-mutable current test
  file — is resolved by freezing and pinning that file.
- **Reopening a completed part is forbidden by default.** An exception requires
  a documented scientific error, an impact assessment, an explicit new human
  authorization and a separate corrective PR. A new Handoff timestamp, branch
  SHA, current test hash, newly completed part, documentation wording drift or
  historical validator successor mismatch are explicitly **not** scientific
  errors. Incorrect target construction, leakage, incorrect feature
  computation, wrong sample membership, wrong fold assignment, incorrect
  probability/metric computation or unauthorized final-test access **may**
  qualify. The validator never reopens a part automatically.
- **Generic future-part design.** Parts are discovered from the Part 0
  registered execution order by naming convention; Part 3 will advance current
  state by adding only its own files.
- **Authorizes nothing else.** No merge, no Part 3 execution, no
  full-development refit, no final-test access or evaluation, no new scientific
  execution. All Part 1 and Part 2 scientific hashes are unchanged.

### Frozen Part 5 runner provenance — corrected wording (2026-07-23)

- **No Stage125 file changed.** `project/src/stage125_part5_readiness_closure.py`,
  `project/run_stage125_part5.py` and every `project/stage125/` artifact are
  byte-identical to base main `f7f7c9ed`.
- **The committed frozen closure report is PASS.** On disk it records
  `all_gate_pass=true`, `stage125_completed=true`, `stage125_gate_125_0=PASS`
  and `stage126_m1_entry_ready=true`. Earlier PR wording that attributed
  `all_gate_pass=false` to the committed artifact was **wrong** and is
  corrected here: that false gate exists only inside the runner's transient
  live rebuild.
- **Two distinct facts, never to be conflated:**
  1. **Full runner** — `run_stage125_part5.py --check` exits **1** and its
     **first** failure is the inherited `readiness_surface_disagreement`. The
     `--check` path rebuilds the closure report live; the `valid_handoff` gate
     fails inside that rebuild, so the rebuilt `all_gate_pass` becomes false and
     the rebuilt readiness flags become not-ready, while the truthful live
     Handoff still reports Stage126 entry readiness. The cross-artifact
     readiness check reports that disagreement first.
  2. **Direct validation** — `validate_actual_handoff(...)` separately returns
     exactly the five documented mismatching fields, with none of the forbidden
     fields present.
- **Both behaviours are inherited.** Both were reproduced identically in a
  read-only detached worktree at base main `f7f7c9ed`
  (`exit_code=1`, first failure `readiness_surface_disagreement`, same five
  direct fields). **Part 2 introduced no new Part 5 failure mode.** The
  gitignored local Part 3C inputs were copied read-only into that temporary
  worktree so the runner could execute; neither branch was modified.
- **Handoff compatibility status made generic.** It now reads
  `expected_historical_contract_boundary_after_completed_robustness_micro_part`
  instead of naming Part 1, which stopped being true once Part 2 completed.
- **No scientific change.** All eight Part 2 scientific artifacts and all seven
  Part 1 scientific artifacts remain byte-identical; no probability, metric,
  row set, sample delta, selected configuration or interpretation changed.

### Stage126 M1 robustness Part 2 — executed (2026-07-23)

- **Part 2 (`main_rule_b_listing_robustness`) was explicitly human-authorized
  and completed on the development folds only.** The authorization text hashes
  to `27935d31a6efcc6116f0d4007424bad5c7b8599faabcb8d39176c569bf172bcb` and is
  consumed by this execution — it grants no standing authorization, no merge,
  no Part 3, no refit, no final-test access, no SMOTE/SMOTENC/SHAP and no
  M2/M3/M4.
- **Only the sample changed:** from `main_rule_a_primary` to the listing-timing
  robustness sample `main_rule_b_listing_robustness`
  (`analysis_ready_main_rule_b_stage125.csv`, SHA-256
  `5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480`). Target,
  the nine-feature `M1_PRIMARY_FEATURE_ORDER` set (18 transformed columns),
  selected configurations, folds, imbalance policy, seeds and metrics unchanged.
- **No retuning** (frozen selected configurations reused; 0 tuning searches;
  exactly 22 fits / 22 predictions). **No full-development refit.**
- **Final test remained locked and untouched**: 338 row identities counted but
  never parsed, 0 predictor rows, 0 target rows, 0 evaluations. Aggregate
  final-test counts were read only from the frozen
  `part4_event_count_gate_stage125.csv`, never from row-level final-test values.
  No SMOTE/SMOTENC, SHAP, calibration, bootstrap or Holm; zero network access.
- **Counts:** 993 Rule B rows (117 companies, 79 pos / 914 neg); 655 development
  rows (68 / 587); fold roles 242 / 202 / 444 / 211; 1239 OOF rows (413 per
  family); 9 metric rows. XGBoost `scale_pos_weight` recomputed per Rule B
  training fold: 209/33 and 386/58.
- **Sample-delta audit (row identities only).** Rule B keys are a **strict
  subset** of Rule A keys: 19 Rule A-only rows, 0 Rule B-only rows. Net −19 rows,
  −2 companies, −1 positive, −18 negative; development −11 rows (0 positive);
  OOF −8 rows (0 positive); final-test identities −8.
- **Sensitivity analysis only** — Part 2 does not replace the primary results
  and selects no paper winner.
- **Observed ordering (reported, not acted upon).** Pooled development-OOF
  PR-AUC: Logistic 0.447170385532 (+0.001413421484 / +0.32%), RF 0.401263142511
  (−0.001178687509 / −0.29%), XGBoost 0.341959533880 (−0.014585474282 /
  −4.09%). The **observed Part 2 ordering (Logistic > RF > XGBoost) matches the
  primary development ordering**, unlike Part 1's, which differed. Recorded in
  `stage126_m1_robustness_part2_primary_comparison.json`. No selected
  configuration changed, no refit was authorized, no automatic scientific action
  was triggered, the locked primary confirmatory ordering is unchanged and the
  final test stays locked.
- **Part 1 preservation.** All seven Part 1 scientific artifacts are
  byte-identical. Only three verification-only Part 1 files (QC report, metadata
  manifest, Part 5 compatibility record) were refreshed because they embed the
  current successor-test-file hash; no Part 1 model was retuned and no Part 1
  probability or metric changed.
- **Part 3 (`expanded_rule_a_company_scope_robustness`) is not authorized and
  not started.** The consumed Part 2 authorization confers no standing
  authorization for any later category. Parts 3–6 remain outstanding, so M1
  robustness is not complete.

### Frozen Part 5 live-successor boundary (2026-07-22)

- **Stage125 Part 5 remains a frozen, valid historical closure.** Neither its
  source, its runner, nor any `project/stage125/` artifact was modified.
- Part 5's *embedded live-Handoff successor check* hard-codes the earlier
  Stage126 **primary-development** state and predates robustness execution. It
  therefore cannot accept a truthful completed-Part-1 Handoff.
- After Part 1 the **direct `validate_actual_handoff`** mismatch is **exactly
  five fields**: `m1_robustness_started`, `selected_qc_scope`,
  `selected_qc_path`, `contract_version`, `last_completed_micro_part`. This is
  an **expected historical-contract boundary**, not a scientific failure, not
  Stage125 drift, and not a Part 1 merge blocker. (See the 2026-07-23 entry
  below: this five-field statement describes the DIRECT validator only — it was
  never a statement about the full runner's first failure.)
- It must never be "fixed" by writing false Handoff markers or by changing
  `project/stage125/**`. It is recorded in
  `stage126_m1_robustness_part1_part5_successor_compatibility.json`, asserted in
  the Part 1 QC, and explicitly tested — historical Part 5 replay tests use a
  monkeypatched historical primary-successor fixture (the real Handoff file is
  never written), and a dedicated live test proves the boundary is exactly those
  five fields with no readiness/final-test/authorization/research-pointer drift.
- **Current Stage126 successor state is validated by:** the Part 0 integrity
  controls, the Part 1 QC, the Part 1 completion lock, and the AI Handoff
  validator.

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
