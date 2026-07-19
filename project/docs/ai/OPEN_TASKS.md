# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage125-research-design-readiness`

Authoritative research pointers live in `ROADMAP.md` front matter:
`last_completed_research_action_id=stage125-part4-statistical-analysis-plan`,
`next_research_action_id=stage125-part5-readiness-closure`.
Part 3B.1 / 3B.1A / 3B.1B / 3B.1C remain historical **maintenance** locks;
Part 3B.1E is the decision-lock surface for the conservative-lag research
action; Part 3C is the operationalization / leakage-safe dataset surface;
Part 4 is the statistical analysis plan lock (no modeling).

### Completed — `stage124-gate-b-rule-approval`

**Approved.** The user/data owner explicitly approved the final Gate B listing
rules (supported by the readiness comparison; no external reviewer claimed):

- **Rule A (primary):** `first_observed_trading_date <= fiscal_year_end`
- **Rule B (listing-timing robustness):** `first_observed_trading_date <= fiscal_year_start`
- **Rule C rejected:** `first_observed_trading_year < fiscal_year`

Record: `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json` and
`README_GATE_B_RULE_APPROVAL.md`.

### Completed — `stage124-gate-b-execution`

**Gate B executed.** The approved rules were applied to the frozen Stage123 data
and the verified listing master (1331 company-year rows, 1200 t→t+1 pairs, 130
tickers). Four sample designs:

- **main_rule_a_primary** — 1013 eligible (81 pos / 932 neg)
- **main_rule_b_listing_robustness** — 994 eligible (80 pos / 914 neg)
- **expanded_rule_a_company_scope_robustness** — 1057 eligible (81 pos / 976 neg)
- **expanded_rule_b_combined_robustness** — 1036 eligible (80 pos / 956 neg)

Unresolved listing rows: Rule A = 4, Rule B = 10 (preserved explicitly, never
zero-filled). Outputs in `project/stage124/gate_b_final/` (large canonical +
filtered CSVs gitignored/hashed; small audit CSVs, QC, metadata, README tracked).
58 focused tests (`project/tests/test_stage124_gate_b_execution.py`); 736 passed,
1 skipped in the full suite (local results — no GitHub Actions configured).
**No modeling started.**

### Completed research action — `stage125-part3b-conservative-lag-decision-lock`

Human supervisor approved a **fixed conservative six-calendar-month**
availability lag. Deliverables / QC surface:
`stage125-part3b1e-conservative-six-month-lag-decision-lock`. Researcher-verified
financial data are **frozen** (no re-extraction). Broad CODAL metadata and
financial-statement capture are **stopped**. PR #47 was closed **unmerged**
(superseded; branch retained). Assumed availability uses
`assumed_available_at_conservative = fiscal_year_end + 6 calendar months` and
must never be written as observed `PublishDateTime` / `available_at`. Predictors
from year **t** may only predict distress target **t+1**. Stage125 remains
**incomplete**; Stage126 and modeling remain unstarted.

### Completed research action — `stage125-part3c-leakage-safe-dataset-finalization`

Audited pair datasets and timing-eligible leakage-safe analysis-ready
datasets finalized for all four locked Gate B sample designs under the
**active four-Jalali-calendar-month regulatory lag** (human-approved
revision; six-month active methodology superseded; Part 3B.1E six-month
decision retained as historical provenance). Full Gate B membership is
preserved on the audited surface; analysis-ready outputs include only rows
where `assumed_available_at_regulatory < target_fiscal_year_end_t_plus_1`
(general rule; `رمپنا|1396` → `رمپنا|1397` remains audit-only). Financial
values and targets remain frozen copies. Assumed availability uses
`assumed_available_at_regulatory` only (not observed `PublishDateTime` /
`available_at`). Part 3C does **not** approve model features — candidates
remain pending Part 4. Bulky outputs are gitignored and hashed. **Do not**
start Stage126 or modeling. **Do not** resume broad CODAL capture or
row-level PublishDateTime collection.

### Completed research action — `stage125-part4-statistical-analysis-plan`

Statistical analysis plan locked for all four analysis-ready samples under
the active four-month regulatory lag. Primary paper result uses
`main_rule_a_primary` × `FD_target_main_t_plus_1`. M1 primary feature order
(10), M1 target-proximity robustness (7), nested M2–M4 blocks, temporal folds
(development 1393–1399; final test 1400–1402), preprocessing, model families,
finite hyperparameter budget (32 configs/block), seeds, PR-AUC primary,
Recall@10%/Lift@10%, calibration, paired ticker-cluster bootstrap, Holm, and
SHAP stability contracts are frozen. Part 3C hashes pinned. **No** model
fitting, **no** final-test predictor inspection, **no** M2/M3/M4 data
collection, **no** Stage126. Article-141-only final test (1 positive on
primary sample) is distributional/descriptive robustness only.

### Next / active research action — `stage125-part5-readiness-closure`

Stage125 closure / readiness report; record keep/drop decisions; full
validator + tests. **No** Stage126. **No** modeling.

Historical Part 3B / 3B.1x notes (retained): origin probes and five-row
document-binding evidence remain as frozen scientific history; they do **not**
authorize expansion. 80-row scale-up is cancelled.

Current markers (must stay true until separately authorized otherwise):

- `broad_codal_capture_stopped=true`
- `financial_data_researcher_verified_frozen=true`
- `active_availability_method=fixed_regulatory_lag`
- `active_availability_lag_months=4`
- `four_month_regulatory_lag_locked=true`
- `six_month_lag_superseded=true`
- `historical_six_month_decision_retained=true`
- `row_level_publish_datetime_collection_required=false`
- `conservative_six_month_lag_decision_locked=true` (historical Part 3B.1E)
- `part3b_started=true`; `endpoint_probe_evidence_collected=true`
- `part3b1_decision_locked=true`
- `cut_a_available_at_operationalization_locked=true` (historical observed-PublishDateTime contract; collection not authorized for modeling path)
- `predictor_document_binding_mini_pilot_completed=true`
- `predictor_document_binding_evidence_collected=true`
- `document_binding_resolution_decision_locked=true`
- `predictor_available_at_evidence_collected=false`
- `pilot_cutoff_provenance_resolved=false`
- `candidate_value_evidence_collected=false`
- `pair_level_evidence_collected=true` (Part 3C leakage-safe pair construction)
- `data_value_extraction_performed=false`
- `accessibility_scoring_applied=false`
- `part3b_completed=false`
- `part3c_leakage_safe_finalization_completed=true`
- `part4_statistical_analysis_plan_locked=true`
- `modeling_started=false`

**Still prohibited without explicit user authorization:** expanded CODAL/TSETMC/CBI
network for value extraction, row-level PublishDateTime collection, real
observed available_at assignment, 80-row / 130-company CODAL scale-up,
Part 3B.2, Stage126, or modeling.

**Part 0 (done — documentation lock):** baseline after PR #20 confirmed;
research contract recorded in human docs; Handoff regenerated by the generator;
validator + tests green; PR opened. **PR #21 is now MERGED** (`main` merge commit
`d39e770ff49729a2f0b1b0262c0b1aa5ae41b0c4`). Part 0 is CLOSED.

**Part 1 (completed and merged):** Data Dictionary & Provenance Contract. Contracts / read-only-audit only; tracked as maintenance task
`stage125-part1-data-contract` (advances no research action). Deliverables in
`project/stage125/`: M1–M4 data dictionary, identifier/time contract, source
registry (M1–M4 only, no M5), provenance manifest schema, data-admission-gate
template, immutable raw/cache policy, and a read-only M1 provenance-gap audit
(rows 1331; source_file missing 28; source_url missing 1316; fiscal_year_end
missing 4; company_name missing 7; industry missing 29; audit_status_unknown
316). Empty `source_url` is a provenance gap only — no eligibility change, no row
drop, no gap filled, no value guessed.

**Part 2 (completed and merged):** Prediction-time & Leakage Contract. Contract / read-only-audit only; tracked as maintenance task
`stage125-part2-prediction-time-contract` (advances no research action).
Deliverables in `project/stage125/`: prediction-time contract (cutoff based on
verified `available_at`; revision policy; deterministic tie-breaking); feature
availability contract (M1–M4 temporal gating; no target-year features); leakage
checklist (8 machine-testable fail-closed checks LC01–LC08); per-pair
cutoff/feature/leakage audit CSVs preserving all 1200 pairs; cutoff summary.
Missing `fiscal_year_end` (4 predictor, 4 target; 5 pairs either missing, 3 both
missing) is never filled or guessed — those pairs have
`temporal_status=unresolvable`. `eligibility_impact=none_contract_audit_only` for
every pair. No pair is dropped. `modeling_started` remains `false`;
`part2_started=true` (contract only, not modeling); no network extraction.

**PR #27 post-merge Handoff refresh — MERGED** (`main` merge commit
`c6cbb6b7a7dc4dfe7ca3fa6ea0bcf34d7f0612c0`). Part 1 and Part 2 are CLOSED.

**Part 3A (completed and merged):** Accessibility, Coverage & Event Pilot
Protocol Lock. Protocol / inventory freeze only; tracked as maintenance task
`stage125-part3a-pilot-protocol-lock` (advances no research action).
PR #29 **MERGED** (`main` @ `4e15cb7…`). Locks the 10 registered M2–M4
candidates, proposed accessibility rubric (not yet applied), gate decision
protocol (8 locked Gates + 6 pending thresholds), sampling frame from frozen
Gate B data, pilot-size options for later approval, and Part 3B evidence
manifest schema. **No** evidence collection, **no** network access, **no**
accessibility scores assigned, **no** candidate admitted.
`part3a_protocol_locked=true`; `modeling_started` remains `false`;
`part3b_started=false`. Part 3A protocol assets are **frozen**.

**Part 3A.1 (completed and merged):** User-Approved Pilot Decision Lock.
Decision record only; tracked as maintenance task
`stage125-part3a1-decision-lock` (advances no research action). PR #34
Handoff refresh **MERGED** (`main` @ `75abf3f…`). Records user-approved rubric
version `stage125_part3a_v1` (approved but not applied), G09–G14 pilot-only
thresholds, and locked `pilot_option_event_enriched` selection (80 pairs:
39 positive / 41 negative; 26 tickers; 10 known industries; 53 industry-present
pairs; 27 industry-missing pairs).
**No** evidence collection, **no** network access, **no** accessibility scores
applied, **no** candidate admitted/rejected. `part3a_decision_locked=true`;
`part3b_started=false`; `modeling_started=false`.

**Part 3B.0 (completed — frozen historical baseline):** Evidence Capture
Readiness. Infrastructure/readiness only. After Part 3B authorization, its
`--check` verifies historical deliverables byte-identically and does not rewrite
zero-evidence QC history. `part3b0_readiness=true`.

**Part 3B detail (same active/incomplete probe as above):** 800 assessments
derived from origin probes; scores null; G13/G14 PASS; G09–G12 FAIL;
`network_extraction_performed=true` (historical probe contact only).

**Part 3B.1 detail (maintenance Decision Lock):** user-approved selections
M2-A modified / M3-C+CBI-A / M4-A / R-A / CUT-A locked as schema/formula contracts
with synthetic validation only. Adjudication in versioned
`part3b1_adjudicated_decision_requirements_stage125.json` +
`README_STAGE125_PART3B1_DECISION_LOCK.md` (historical Part 3B proposed-requirements
README remains frozen). Does **not** move
`last_completed_research_action_id` or `next_research_action_id`. Not Stage126
admission.

**Modeling remains prohibited** (no modeling, tuning, SHAP, SMOTE, calibration,
temporal splitting, feature selection, or article result generation) through all of
Stage125; it begins only when Stage126 (M1 Financial Baseline) is explicitly
approved.

## Historical — `stage124-gate-b-readiness`

### Superseded — `stage124-batch02-part03-1b-1`

**Cancelled by official TSE API (not completed).** The canonical listing dates
for all 130 tickers were obtained from the official TSETMC API and are stored in
`project/stage124/listing_master_verified_stage124.csv` with
date_semantics=`first_observed_trading_date_from_official_tse_api`, in columns
`first_public_trading_date_jalali` and `first_public_trading_date_gregorian`,
with status `verified_tse_api_first_observed_trade`.

The manual Human-in-the-Loop research path (HIL dashboard, manual intake runner)
has been **retired**. The 10 Part 3 tickers no longer require manual source
discovery or dashboard confirmation.

### Completed — `stage124-gate-b-readiness`

**Gate B readiness dry-run completed.** Three eligibility rules (A/B/C) were
compared as a dry-run:

- **Rule A**: `first_observed_trading_date <= fiscal_year_end` — 1013 eligible pairs (81 pos / 932 neg)
- **Rule B**: `first_observed_trading_date <= fiscal_year_start` — 994 eligible pairs (80 pos / 914 neg)
- **Rule C**: `first_observed_trading_year < fiscal_year` — 995 eligible pairs (80 pos / 915 neg)
- **Stage123 baseline**: 1085 eligible pairs (86 pos / 999 neg)

Output files in `project/stage124/gate_b_readiness/`:
- `gate_b_rule_comparison_summary.json` — full comparison
- `gate_b_company_year_audit.csv` — per-row audit (1331 rows)
- `gate_b_pair_impact_summary.csv` — per-rule pair statistics
- `gate_b_unmatched_or_ambiguous_rows.csv` — data quality issues
- `gate_b_readiness_qc_report.json` — QC report (all pass)
- `metadata_and_hashes_gate_b_readiness.json` — hashes and metadata
- `README_GATE_B_READINESS.md` — human-readable summary

45 focused tests added in `project/tests/test_stage124_gate_b_readiness.py`.

The rule was subsequently finalized under `stage124-gate-b-rule-approval` and
applied under `stage124-gate-b-execution` (see the active workstream above).

## Completed

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
- ✅ `stage124-official-api-finalize` — Finalized verified master for 130 tickers
  using official TSETMC first-observed-trade dates; merged through PR #15, merge
  commit 22c2d0c.
- ✅ `stage124-gate-b-readiness` — Dry-run comparison of three eligibility rules
  (A/B/C) with per-rule impact reports and 45 focused tests.
- ✅ `stage124-gate-b-rule-approval` — Rule A approved as primary, Rule B as
  listing-timing robustness; Rule C rejected.
- ✅ `stage124-gate-b-execution` — Approved rules applied; four sample designs,
  canonical + filtered outputs, 58 focused tests. No modeling started.
- ✅ Verified master: `listing_master_verified_stage124.csv` — 130 unique tickers,
  dates in `first_public_trading_date_jalali` / `first_public_trading_date_gregorian`
  with date_semantics=`first_observed_trading_date_from_official_tse_api`
  (not necessarily IPO, admission, or listing dates).
- ⚠️ `stage124-batch02-part03-1b-1` — superseded / cancelled by official TSE API
  (not completed).

## Not in scope yet (do NOT start)

- ❌ Modeling, tuning, SHAP, SMOTE, calibration, temporal splitting, feature
  selection, or article reporting (blocked; begins only when Stage126 is approved)
- ❌ Persian text / text modeling (M5) — removed from the paper and roadmap
- ❌ Any data or analysis depending on accessibility < 3
- ❌ Data extraction, model runs, or target/sample changes during Stage125 Part 0

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
