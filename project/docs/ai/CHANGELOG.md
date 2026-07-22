# CHANGELOG

Human-maintained, newest first. Record decisions and milestones (not every commit —
`git log` already has those).

## 2026-07-22 — Stage126 M1 Robustness Part 1 (target-proximity six-feature set)

- **Part 1 was explicitly human-authorized and completed on the development
  folds.** Executed the registered robustness category
  `m1_target_proximity_six_feature_set` under the merged Part 0 execution
  contract. **Only the feature set changed** (the six-feature
  `M1_TARGET_PROXIMITY_ROBUSTNESS` set, 12 transformed columns after appending
  the six missingness indicators); the sample (`main_rule_a_primary`), target
  (`FD_target_main_t_plus_1`), the two locked temporal folds, the three primary
  selected configurations, the class-weighting imbalance policy, the seeds and
  the metric contract were all held fixed. **No retuning occurred**
  (`tuning_search_calls=0`; the frozen selected configurations were reused
  verbatim): 22 model fits and 22 predictions exactly. **No full-development
  refit occurred.** Development-only: 666 rows, 421 pooled OOF rows per family
  (1263 total), 9 metric rows. **The final test remains locked and untouched**
  (zero predictor/target rows loaded, zero evaluations); no SMOTE, SMOTENC,
  SHAP, calibration, bootstrap or Holm procedure ran; zero network requests.
  **Part 1 is sensitivity-analysis evidence only** — it does not replace the
  primary results, does not re-rank the primary model families and selects no
  paper winner. Primary Stage126 artifacts and the frozen Stage125 contracts
  remain byte-identical. **Part 2 (`main_rule_b_listing_robustness`) is not
  authorized and not started**; it requires its own separate explicit human
  authorization. Research action pointers are unchanged (Stage126 M1 remains
  the active incomplete research action).

## 2026-07-22 — Stage126 M1 Robustness Part 0 Decision Lock

- **Robustness execution decisions locked (decision lock only; no execution).**
  Added the additive Stage126 M1 robustness execution contract
  (`stage126_m1_robustness_execution_contract`, version
  `stage126_m1_robustness_execution_contract_v1`) recording the byte-for-byte
  human decision text (SHA-256
  `79f98e4c6dc81e6362ad90b138997c0d0bc3c8bad5d471ea65615ffc49627a5b`), the six
  registered robustness categories in binding execution order (one factor at a
  time), all-three model families, no-retuning (reuse the primary selected
  configurations), the two locked development folds, the metric list, the
  SMOTE/SMOTENC training-fold-only rules, and the one-category-per-micro-part
  packaging policy. **Robustness execution is NOT authorized; Part 1 is not
  started.** No model was fit, predicted, retuned or refitted; no SMOTE/SMOTENC
  or SHAP ran; the final test remains locked and untouched; the primary Stage126
  artifacts are byte-identical; no historical Stage125 contract was modified.
  Handoff now carries `m1_robustness_decision_locked=true`,
  `m1_robustness_execution_authorized=false`,
  `m1_robustness_next_category_id=m1_target_proximity_six_feature_set`. Research
  action pointers are unchanged (Stage126 M1 remains the active incomplete
  research action).
- **Frozen Stage125 byte-integrity and fail-closed Handoff validation hardened;
  no scientific decision changed and no execution occurred.** The nine consumed
  Stage125 contracts are individually SHA-256 pinned to their exact frozen bytes;
  the complete tracked `project/stage125/` tree is verified unchanged (committed,
  staged, unstaged, untracked); the Part 4 preprocessing sequence is incorporated
  by reference and validated for exact equality; and the Handoff generator now
  rejects any internally inconsistent Part 0 decision record (identity, flags,
  full execution order, and recomputed human-decision-text hash).
  Integrity-critical Git command failures and invalid repository/base states now
  fail closed rather than being interpreted as empty diffs.

## 2026-07-22

- **Repository-entry-document consistency correction (documentation only).** Updated
  `README_RUN.md`, `HANDOFF_PACKAGE.md`, and `DECISIONS.md` to accurately reflect
  the current Stage126 M1 state: Stage126 M1 is human-authorized and started;
  primary M1 development-fold tuning is completed on PR #52; M1 robustness is not
  started; no full-development refit has occurred; the final test remains locked
  and untouched; M2/M3/M4 data were not collected. This is a repository-state
  documentation correction only and does not represent a new scientific decision.
  Historical Stage125 statements remain explicitly historical. No model was
  refitted and no Stage126 scientific output changed.

## 2026-07-19

- **Stage125 Part 5 / research action
  `stage125-part5-readiness-closure` — Readiness Closure.** Offline Gate 125.0
  closure: keep/drop/defer register, blocker register, Stage126 M1 entry
  contract (readiness only), integrity manifest. Stage125 completed for
  closure; Stage126 M1 entry ready for a **future authorization decision**
  only (`stage126_authorized=false`, `modeling_authorized=false`, final test
  locked). Part 3C and Part 4 hashes unchanged. Zero network / fit / predict /
  SHAP. Research pointers advance to
  `last_completed_research_action_id=stage125-part5-readiness-closure`,
  `next_research_action_id=stage126-m1-financial-baseline` (future; blocked
  pending explicit human authorization; not started).

- **Stage125 Part 4 v2 correction — revenue-growth exclusion revision.**
  Human supervisor rejected `revenue_growth_period_adjusted` from admitted M1
  (raw Fold 1 training coverage `148/245 = 0.6040816327` < 0.75). Removed the
  unauthorized first-observation denominator exception. Active contract
  `stage125_part4_sap_v2` (v1 retained in Git). M1 primary now 9 features;
  target-proximity 6; nested 9/12/15/19; exclusions 23. Added strict
  positive/negative/missing event accounting, pre-imputation missingness-mask
  preprocessing, SMOTE-without-class-weighting, and separation of final-test
  claim eligibility from predictor admission. **No** modeling; **no** Stage126.

- **Stage125 Part 4 / research action
  `stage125-part4-statistical-analysis-plan` — Statistical Analysis Plan lock.**
  Locks M1–M4 feature order, four sample designs, target-year temporal folds,
  preprocessing, model families, finite tuning budget, PR-AUC primary,
  Recall@10%/Lift@10%, calibration, paired ticker-cluster bootstrap, Holm, and
  SHAP stability contracts. Part 3C hashes pinned. **No** model fitting; **no**
  final-test predictor inspection; **no** Stage126. Research pointers advance
  to `last_completed_research_action_id=stage125-part4-statistical-analysis-plan`,
  `next_research_action_id=stage125-part5-readiness-closure`. Stage125 remains
  incomplete.

## 2026-07-18

- **Stage125 Part 3C correction — audited vs analysis-ready split.** The
  authorized `رمپنا|1396` → `رمپنا|1397` timing exception remains visible in
  the complete audited pair surface with explicit ineligibility flags, but is
  excluded from leakage-safe analysis-ready / model-eligible datasets. Full
  membership files are described as audited pair datasets; only
  timing-eligible (`assumed_before_target_fiscal_year_end=true`) files are
  leakage-safe analysis-ready. Fail-closed reconciliation of audit vs
  analysis-ready counts; no silent drops; no financial/target mutation.

- **Stage125 Part 3C / research action
  `stage125-part3c-leakage-safe-dataset-finalization` — Leakage-safe dataset
  finalization.** Operationalizes the locked six-month Jalali lag for all four
  frozen Gate B designs; financial values and targets unchanged; assumed
  availability is methodological only (not observed PublishDateTime). Bulky
  pair CSVs remain gitignored and hashed. Research pointers advance to
  `last_completed_research_action_id=stage125-part3c-leakage-safe-dataset-finalization`,
  `next_research_action_id=stage125-part4-statistical-analysis-plan`. Stage125
  remains incomplete; **no** feature selection / modeling / Stage126.

- **Stage125 Part 3B.1E / research action
  `stage125-part3b-conservative-lag-decision-lock` — Conservative six-month
  availability-lag methodology lock.** Human supervisor approved a fixed
  conservative six-calendar-month availability lag; researcher-verified
  financial data are frozen; broad CODAL metadata / financial-statement
  extraction is stopped. PR #47 closed **unmerged** (superseded; branch
  retained as audit trail). Assumed availability uses field
  `assumed_available_at_conservative` only (never observed `PublishDateTime` /
  `available_at`). Predictors from fiscal year t may only predict distress
  target t+1. Markers: `broad_codal_capture_stopped=true`,
  `financial_data_researcher_verified_frozen=true`,
  `conservative_availability_lag_locked=true`, `conservative_lag_months=6`,
  `row_level_publish_datetime_collection_required=false`. Stage125 remains
  incomplete; **no** Stage126 / modeling.

- **Stage125 Part 3B.1C — Document Binding Resolution Decision Lock
  (maintenance).** Tracked as
  `stage125-part3b1c-document-binding-resolution-decision-lock`. Offline
  failure taxonomy, mechanical identity-normalization contract, exact-document
  evidence hierarchy, row-level resolution requirements, proposed (not
  authorized) capture manifest, and `scale_up_to_80_rows_authorized=false`.
  **No** network, **no** new capture, **no** Part 3B.1B evidence mutation,
  **no** available_at / extraction / scoring / Gates / Part 3B.2 / Stage126 /
  modeling. Research pointers unchanged.

- **Stage125 Part 3B.1B — tracked parsed-metadata receipt + fresh-clone
  determinism (PR #43 harden, maintenance).** Adds
  `part3b1b_thanusa_parsed_metadata_receipt_stage125.json` bound to the
  historical payload SHA so source-observed ثنوسا fields reconstruct without
  gitignored raw HTML. Official `--check` enforces canonical drift outside
  `--capture` (zero writes / zero network). Exact 11-field pilot equality;
  `completed_at_utc=null` preserved with explicit
  `completed_at_status=missing_in_original_cache_metadata_preserved_null`.
  Scientific result unchanged: BOUND=0, UNRESOLVED=4, REJECTED=1,
  `available_at` non-null=0. Research pointers unchanged.

## 2026-07-17

- **Stage125 Part 3B.1B — Controlled CODAL Predictor-Document Binding
  Mini-Pilot (maintenance).** Tracked as
  `stage125-part3b1b-codal-document-binding-mini-pilot` (advances **no**
  research action). Baseline: `origin/main` @
  `4d7a48288543c971f43337e9a5d9a70ccfed2610`. Five locked rows only
  (`ثنوسا|1392`, `بوعلی|1399`, `بوعلی|1400`, `اردستان|1401`, `اپال|1401`);
  document metadata/provenance capture with at most one authorized
  `www.codal.ir` Decision.aspx GET. **No** financial-value extraction, **no**
  accessibility scoring, **no** Gate application, **no** cutoff audit mutation,
  **no** Part 3B.2 / Stage126 / modeling. Markers
  `predictor_document_binding_mini_pilot_completed=true`,
  `predictor_document_binding_evidence_collected=true`,
  `predictor_available_at_evidence_collected=false`. Research pointers remain
  `last_completed_research_action_id=stage125-part3a-decision-lock`,
  `next_research_action_id=stage125-part3b-evidence-capture`.

- **Stage125 Part 3B.1A hardening (PR #41, maintenance).** Normalized
  `revision_status` aligned to frozen provenance enum
  (`original`/`revision`/`restatement`; `correction` removed as normalized
  status). Exact values-source LetterSerial / TracingNo / title binding is
  structural and authoritative. Asia/Tehran gap vs fold classification uses UTC
  round-trips (nonexistent ≠ ambiguous). Canonical runtime
  `Python 3.13.5` + `jdatetime==6.0.1`. Still **no** network, real assignment,
  cutoff recovery, extraction, scoring, Part 3B.2, Stage126, or modeling.
  Research pointers unchanged.

- **Stage125 Part 3B.1A — CUT-A Available-at Operationalization Lock
  (maintenance).** Tracked as
  `stage125-part3b1a-cut-a-available-at-operationalization-lock` (advances **no**
  research action). Baseline: `origin/main` @
  `3a54a79c935f27e311679e8582e4c46330590a43`. Locks operational `available_at` =
  `PublishDateTime` of an exact version-bound CODAL letter; `SentDateTime`
  audit-only; exact-document binding + revision + `Asia/Tehran` normalization
  fail-closed. Schema/pure parsers/synthetic validation only. **No** network,
  **no** real `available_at` assignment, **no** cutoff resolution, **no**
  extraction/scoring, **no** Part 3B.2 / Stage126 / modeling. Marker
  `cut_a_available_at_operationalization_locked=true`. Research pointers remain
  `last_completed_research_action_id=stage125-part3a-decision-lock`,
  `next_research_action_id=stage125-part3b-evidence-capture`.

## 2026-07-15

- **Stage125 Part 3B.0 — Evidence Capture Readiness (authorized/active).**
  Infrastructure/readiness only; tracked as maintenance task
  `stage125-part3b0-evidence-readiness` (advances **no** research action).
  Baseline: `origin/main` @ `75abf3f6d92e514df568e1d6912ccc47cdffc933`.
  New code/tests: `project/src/stage125_part3b0_evidence_readiness.py`,
  `project/run_stage125_part3b0.py`,
  `project/tests/test_stage125_part3b0_evidence_readiness.py`. Readiness
  contracts/templates in `project/stage125/` (header-only CSVs; zero real
  evidence rows). **No** network calls, **no** real evidence, **no**
  accessibility scores, **no** modeling. `part3b0_readiness=true`;
  `part3b_started=false`; next research action remains
  `stage125-part3b-evidence-capture` (pointer only).

- **Stage125 Part 3A.1 blocker fixes (PR #30, additive).** Industry accounting
  corrected: 10 known industries, 53 industry-present pairs, 27 industry-missing
  pairs; unknown sentinel `نامشخص در فایل ارسالی` is not a known industry.
  Handoff generator now propagates `part3a_protocol_locked`,
  `part3a_decision_locked`, and `part3b_started` from the selected QC scope
  (fail-closed). ROADMAP pointers:
  `last_completed_research_action_id=stage125-part3a-decision-lock`,
  `next_research_action_id=stage125-part3b-evidence-capture` (pointer only; Part
  3B not started).

- **Stage125 Part 3A.1 — User-Approved Pilot Decision Lock.** Authorized and
  active as a decision-record task tracked by
  `active_maintenance_task_id = stage125-part3a1-decision-lock`
  (advances **no** research action). Baseline: PR #29 MERGED, `main` @
  `4e15cb7bdec07bfc007e6abe854c877ffd2ac1cc`. Part 3A protocol merged and
  frozen. New code/tests:
  `project/src/stage125_part3a_decision_lock.py`,
  `project/run_stage125_part3a_decision_lock.py`,
  `project/tests/test_stage125_part3a_decision_lock.py`. Deliverables in
  `project/stage125/`: decision lock JSON (rubric approved but not applied;
  locked `pilot_option_event_enriched`; G09–G14 pilot thresholds); approved
  gate thresholds CSV; selected pilot pairs CSV (80 pairs). Pilot is
  event-enriched and non-population-representative; **not** the modeling sample.
  **No** evidence collection, **no** network access, **no** accessibility
  scores applied, **no** candidate admitted/rejected. `part3a_decision_locked=true`;
  `part3b_started=false`; `modeling_started` remains `false`.

## 2026-07-14

- **Stage125 Part 3A — Accessibility & Pilot Protocol Lock — COMPLETED and
  MERGED.** PR #29 merged (`main` @ `4e15cb7…`). Protocol assets frozen.
  `project/src/stage125_part3a_pilot_protocol.py`,
  `project/run_stage125_part3a.py`,
  `project/tests/test_stage125_part3a_pilot_protocol.py`. Deliverables in
  `project/stage125/`: 10 registered M2–M4 candidate inventory freeze;
  proposed accessibility rubric (`pending_user_approval`, not applied);
  gate decision protocol (8 locked Gates + 6 pending thresholds); sampling
  frame summary and by-target-year CSV; three pilot-size options
  (`pending_user_approval`); Part 3B evidence manifest schema. **No**
  evidence collection, **no** network access, **no** accessibility scores,
  **no** candidate admitted. `part3a_protocol_locked=true`;
  `part3b_started=false`; `modeling_started` remains `false`.
- **Stage125 Part 2 — Prediction-time & Leakage Contract — COMPLETED and
  MERGED.** PR #27 post-merge Handoff refresh merged (`main` @
  `c6cbb6b7a7dc4dfe7ca3fa6ea0bcf34d7f0612c0`). Part 2 tracked by
  `stage125-part2-prediction-time-contract` (advances **no** research action).
  `project/src/stage125_part2_prediction_time_contract.py`,
  `project/run_stage125_part2.py`,
  `project/tests/test_stage125_part2_prediction_time_contract.py`. Deliverables
  in `project/stage125/`: prediction-time contract (cutoff based on verified
  `available_at`; revision policy; deterministic tie-breaking); feature
  availability contract (M1–M4 temporal gating; no target-year features);
  leakage checklist (8 machine-testable fail-cailed checks LC01–LC08); per-pair
  cutoff/feature/leakage audit CSVs preserving all 1200 pairs; cutoff summary.
  Missing `fiscal_year_end` (4 predictor, 4 target; 5 pairs either missing, 3
  both missing) is never filled or guessed — those pairs have
  `temporal_status=unresolvable`. `eligibility_impact=none_contract_audit_only`
  for every pair. No pair is dropped. `metadata_and_hashes_stage125_part2.json`
  added to the frozen-manifest workflow. **No modeling, no network extraction;
  `modeling_started` remains `false`; `part2_started=true` (contract only, not
  modeling); Stage122–Stage125 Part 1 assets unchanged.**

## 2026-07-13

- **Stage125 Part 1 — Data Dictionary & Provenance Contract.** PR #21 (Part 0)
  is **MERGED** (`main` merge commit `d39e770ff49729a2f0b1b0262c0b1aa5ae41b0c4`),
  so Part 0 is closed. Part 1 is authorized and executed (in review) as a
  contracts / read-only-audit task tracked by
  `active_maintenance_task_id = stage125-part1-data-contract` (advances **no**
  research action; `last_completed_research_action_id` stays
  `stage124-gate-b-execution`). New code/tests:
  `project/src/stage125_part1_data_contract.py`,
  `project/run_stage125_part1.py`,
  `project/tests/test_stage125_part1_data_contract.py`. Deliverables in
  `project/stage125/`: M1–M4 data dictionary, identifier/time contract, source
  registry (M1–M4 only, **no M5**), provenance manifest schema,
  data-admission-gate template (accessibility ≥ 3 = pilot gate only), and a
  read-only M1 provenance-gap audit (rows 1331; source_file missing 28;
  source_url missing 1316; fiscal_year_end missing 4; company_name missing 7;
  industry missing 29; audit_status_unknown 316). Empty `source_url` is recorded
  as a provenance gap only — **no** eligibility change, **no** row drop, **no**
  gap filled, **no** value guessed. `metadata_and_hashes_stage125_part1.json`
  added to the frozen-manifest workflow. **No modeling, no network extraction,
  Part 2 not started; `modeling_started` remains `false`; Stage122–Stage124
  assets unchanged.**
- **Stage125 Part 0 — Research Design Decision Lock.** Confirmed the live baseline
  (PR #20 MERGED, `main` merge commit `873e538c90645d0fa7c52ddf2bbe79081f310c84`,
  Stage124 Gate B frozen, Stage125/new modeling not started) and froze the research
  contract in the new human doc
  [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md):
  - Incremental nested blocks **M1 Financial → M2 Market → M3 Parsimonious Macro →
    M4 Structured Audit/Governance**, compared on the same common sample / temporal
    split with paired predictions.
  - **M5 (Persian text / text modeling) removed** from the paper and roadmap.
  - **All data/analyses depending on accessibility < 3 removed.**
  - **accessibility = 3 is a pilot gate only** — a variable enters the main analysis
    only if it also passes provenance, `published_at`/`available_at`, coverage, and
    event-count Gates.
  - Full out-of-scope list recorded (order-book/bid–ask, non-reproducible free-market
    FX, director biography/network/interlocking, social/news/ESG unstructured sources,
    large searched macro sets, multiple post-hoc regime definitions, real cost-matrix/
    DCA, algorithm inflation).
- **ROADMAP updated:** `next_research_action_id` →
  `stage125-research-design-readiness` (Stage125 = Research Design & Data Readiness,
  **no modeling**); `active_maintenance_task_id` → `stage125-part0-research-design-lock`.
- Documentation-only; **no** data extraction, model runs, or target/sample changes.
  **Modeling remains prohibited** until Stage126 (M1 Financial Baseline) is approved.
  Stage122–Stage124 files are untouched.

## 2026-07-12

- **PR #19 merged** — Stage124 post-merge Gate B audit and handoff refresh.
  Merge commit `9758ba5f9745e2274e800d901b3516a70815dc50`. Added
  `pair_source_columns_preserved` QC assertion (24 total, 0 failed), renamed
  `date_semantics_declared` to `date_semantics_provenance_verified`, refreshed
  Handoff. Stage124 Gate B is fully closed. Modeling remains prohibited.
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
    `project/src/stage124_gate_b_execution.py`; 46 focused tests (724 passed, 1 skipped).
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
