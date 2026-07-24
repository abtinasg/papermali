# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage126-m1-financial-baseline`

Authoritative research pointers live in `ROADMAP.md` front matter:
`last_completed_research_action_id=stage125-part5-readiness-closure`,
`next_research_action_id=stage126-m1-financial-baseline`
(active; human-authorized and started; primary M1 development-fold tuning
completed on PR #52; research action not yet completed).
Part 3B.1 / 3B.1A / 3B.1B / 3B.1C remain historical **maintenance** locks;
Part 3B.1E is the decision-lock surface for the conservative-lag research
action; Part 3C is the operationalization / leakage-safe dataset surface;
Part 4 is the statistical analysis plan lock (no modeling);
Part 5 is the Stage125 readiness closure (Gate 125.0; Stage126 entry contract
as readiness-only at closure time).

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
the active four-month regulatory lag. Active contract:
`stage125_part4_sap_v2`. Primary paper result uses
`main_rule_a_primary` × `FD_target_main_t_plus_1`. M1 primary feature order
(9 admitted), M1 coverage-audit candidates (10; `revenue_growth_period_adjusted`
rejected at Fold 1 train coverage `148/245 = 0.6040816327`), M1
target-proximity robustness (6), nested M2–M4 blocks (9/12/15/19), temporal
folds (development 1393–1399; final test 1400–1402), strict
positive/negative/missing event accounting, pre-imputation missingness-mask
preprocessing, SMOTE without class weighting, model families, finite
hyperparameter budget (32 configs/block), seeds, PR-AUC primary,
Recall@10%/Lift@10%, calibration, paired ticker-cluster bootstrap, Holm, and
SHAP stability contracts are frozen. Part 3C hashes pinned. **No** model
fitting, **no** final-test predictor inspection, **no** M2/M3/M4 data
collection, **no** Stage126. Article-141-only final test (1 positive on
primary sample) is distributional/descriptive robustness only.

### Completed research action — `stage125-part5-readiness-closure`

Stage125 readiness closure / Gate 125.0. Keep/drop/defer decisions recorded;
blocker register classified; Stage126 M1 entry contract written as
**readiness for a future authorization decision only** at Stage125 closure
time (historical state at Stage125 closure time: Stage126 unauthorized;
modeling unstarted; final test locked). Part 3C and Part 4 hashes unchanged.
**No** model fitting, predictions, SHAP, SMOTE, or final-test predictor
inspection in Part 5 itself.

### Active — `stage126-m1-financial-baseline`

Stage126 M1 human-authorized = true
Stage126 started = true
development modeling authorized = true
modeling started = true
primary development tuning completed = true

M1 robustness started = true
M1 robustness completed = false
full-development refit performed = false

final test unlocked = false
final-test access authorized = false
final-test predictor values inspected = false
final-test target values inspected = false
final-test evaluation performed = false

M2/M3/M4 data collected = false

Primary M1 development-fold tuning is completed on PR #52. The Stage126
research action is **not yet completed** (robustness / full-development
refit / final test remain out of scope until separately authorized).

**Robustness Part 0 decision lock (maintenance; 2026-07-22):** the additive
robustness execution contract (`stage126_m1_robustness_execution_contract_v1`)
is locked — six categories in binding order, one factor at a time, all three
model families, no retuning (reuse primary selected configurations), two locked
development folds, fixed metric list, SMOTE/SMOTENC training-fold-only rules, and
one-category-per-micro-part packaging. This is a **decision lock only**: it
authorizes **no** robustness execution and **Part 1 is not started**. Handoff
markers: `m1_robustness_decision_locked=true`,
`m1_robustness_execution_authorized=false`,
`m1_robustness_started=false`,
`m1_robustness_next_category_id=m1_target_proximity_six_feature_set`,
`m1_robustness_packaging_policy=one_category_per_micro_part_pr`. Each future Part
requires a separate explicit human authorization; primary Stage126 artifacts are
byte-identical and the final test remains locked.

**Robustness Part 1 — COMPLETED (2026-07-22):** `m1_target_proximity_six_feature_set`
was explicitly human-authorized and executed on the development folds only.
**Only the feature set changed** (six-feature `M1_TARGET_PROXIMITY_ROBUSTNESS`,
12 transformed columns); sample, target, folds, selected configurations,
imbalance policy, seeds and metrics were held fixed. **No retuning** (0 tuning
searches; exactly 22 fits / 22 predictions), **no full-development refit**, and
the **final test remains locked and untouched** (0 predictor rows, 0 target
rows, 0 evaluations). No SMOTE/SMOTENC/SHAP/calibration/bootstrap/Holm; zero
network. Outputs: 1263 OOF rows (421 per family) and 9 metric rows. **Part 1 is
sensitivity-analysis evidence only** and did not replace the primary results or
select a paper winner. Handoff markers: `m1_robustness_started=true`,
`m1_robustness_part1_completed=true`,
`m1_robustness_completed_category_ids=["m1_target_proximity_six_feature_set"]`,
`m1_robustness_next_category_id=main_rule_b_listing_robustness`,
`m1_robustness_part2_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Observed ordering sensitivity (reported; primary claims unchanged):** primary
pooled PR-AUC ordering is **Logistic > RF > XGBoost**; the Part 1 observed pooled
PR-AUC ordering is **XGBoost > RF > Logistic**, and **all three pooled PR-AUC
values declined**. The observed Part 1 sensitivity ordering differs from the
primary development ordering. This is a **development-only sensitivity finding**
— it does not change the locked primary ordering used for confirmatory
interpretation, does not replace the primary results, does not change selected
configurations and selects no paper winner. It is recorded in
`stage126_m1_robustness_part1_primary_comparison.json` and reported to the human
supervisor; no automatic scientific action was triggered. Handoff markers:
`m1_robustness_part1_ordering_instability_reported=true`,
`m1_primary_claim_ordering_preserved=true`.

**Successor-test-hash divergence (explicit and bounded):** the successor-aware
Part 5 test file intentionally differs from the hash pinned in the frozen Part 5
metadata; both hashes are recorded. Replaying the frozen Part 5 build against it
differs in **exactly two** self-describing bookkeeping files
(`stage125_part5_readiness_closure_qc_report.json`,
`metadata_and_hashes_stage125_part5.json`) while **every Part 5 scientific
artifact remains byte-identical**. Authorized successor-test evolution — not a
Stage125 scientific-artifact mutation.

**Validation-architecture boundary lock (2026-07-23; decision SHA-256
`8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1`):** Stage125
Part 5 is a **frozen historical closure** and is **no longer responsible for
validating live Stage126 successor state**. The **independent Stage126
current-state validator** is the **sole current-state validation surface**:

```bash
python project/run_stage126_current_state_validator.py --check
python project/run_stage126_m1_robustness_part2_listing_rule_b.py --check
python project/scripts/validate_ai_handoff.py --check
PYTHONPATH=project python -m pytest project/tests -q
```

Current state is derived **generically** — completed prefix
`execution_order[:n]`, next category `execution_order[n]`, last micro-part from
the newest completion lock — so a future Part 3 advances state by adding only
its own package. Closed Part 1 and Part 2 packages (scientific **and**
verification-only artifacts, plus source/runner/tests) are pinned in
`stage126_closed_part_registry.json` and fail validation on byte drift. The
Handoff reports current-state validation and the newest scientific micro-part QC
as two separate, explicit roles.

`run_stage125_part5.py --check` is **not** a routine gate, and previous
robustness runners are not current-state gates — previous scientific artifacts
are protected by immutable hashes. Future robustness parts must **not**
regenerate previous-part verification artifacts unless a genuine scientific
error **and** a separate explicit human authorization exist; reopening a
completed part is forbidden by default. This decision authorized no merge, no
Part 3, no refit, no final-test access and no new scientific execution.

**Frozen Part 5 live-successor boundary (historical provenance only; not a
failure):** Stage125
Part 5 remains a **frozen, valid historical closure** — no Stage125 artifact or
source was modified. Its embedded live-Handoff successor check terminates at the
earlier primary-development state. The full frozen Part 5 runner exits 1 first with the inherited `readiness_surface_disagreement` during a live-successor rebuild. Separately, direct `validate_actual_handoff` returns exactly the documented five-field historical successor mismatch (`m1_robustness_started`, `selected_qc_scope`, `selected_qc_path`, `contract_version`, `last_completed_micro_part`) with no forbidden fields. Neither behaviour was introduced by Part 2, and no Stage125 scientific artifact changed.
The **committed** frozen closure report still records `all_gate_pass=true`,
`stage125_gate_125_0=PASS` and `stage126_m1_entry_ready=true`; the failed gate
exists only inside the runner's transient live rebuild. This is an expected
inherited historical-validator boundary, explicitly recorded in
`stage126_m1_robustness_part1_part5_successor_compatibility.json` and
`stage126_m1_robustness_part2_part5_successor_compatibility.json`, asserted in
the Part 1 and Part 2 QC reports and covered by dedicated fail-closed tests
that run the real runner (no stub). It is **not** a scientific
failure, **not** Stage125 drift, and **not** a Part 1 blocker. Part 1 successor
state is validated by the Part 0 integrity controls, the Part 1 QC, the Part 1
completion lock and the AI Handoff validator. Handoff markers:
`stage125_part5_frozen_artifacts_verified=true`,
`stage125_part5_live_successor_check_applicable=false`,
`stage125_part5_successor_compatibility_status=expected_historical_contract_boundary_after_completed_robustness_micro_part`
(generic: the boundary is a property of having completed ANY robustness
micro-part, not of Part 1 specifically).

**Robustness Part 2 — COMPLETED (2026-07-23):** `main_rule_b_listing_robustness`
was explicitly human-authorized and executed on the development folds only.
**Only the sample changed** — from `main_rule_a_primary` to the listing-timing
robustness sample `main_rule_b_listing_robustness`
(`analysis_ready_main_rule_b_stage125.csv`, SHA-256 `5492cf24…`). The target
(`FD_target_main_t_plus_1`), the nine-feature `M1_PRIMARY_FEATURE_ORDER` set (18
transformed columns), the three primary selected configurations, the two locked
folds, the imbalance policy, the seeds and the metric contract were held fixed.
**No retuning** (0 tuning searches; exactly 22 fits / 22 predictions), **no
full-development refit**, and the **final test remained locked and untouched**
(338 identities counted but never parsed; 0 predictor rows, 0 target rows, 0
evaluations). No SMOTE/SMOTENC/SHAP/calibration/bootstrap/Holm; zero network.
Counts: 993 Rule B rows (117 companies, 79/914), 655 development rows (68/587),
fold roles 242 / 202 / 444 / 211, 1239 OOF rows (413 per family), 9 metric rows.
Handoff markers: `m1_robustness_part2_human_authorized=true`,
`m1_robustness_part2_completed=true`,
`m1_robustness_completed_category_ids=["m1_target_proximity_six_feature_set",
"main_rule_b_listing_robustness"]`,
`m1_robustness_next_category_id=expanded_rule_a_company_scope_robustness`,
`m1_robustness_part3_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Rule A vs Rule B sample delta (row identities only):** Rule B keys are a
**strict subset** of Rule A keys — 19 Rule A-only rows, 0 Rule B-only rows. Net:
−19 rows, −2 companies, −1 positive, −18 negative; −11 development rows (0
positive); −8 OOF validation rows (0 positive); −8 final-test identities.
Aggregate final-test counts were read only from the frozen
`part4_event_count_gate_stage125.csv`, never from row-level final-test values.
Recorded in `stage126_m1_robustness_part2_sample_delta.csv`.

**Part 2 observed ordering (reported; primary claims unchanged):** pooled
development-OOF PR-AUC — Logistic 0.447170 (+0.32%), RF 0.401263 (−0.29%),
XGBoost 0.341960 (−4.09%). The **observed Part 2 ordering (Logistic > RF >
XGBoost) matches the primary development ordering**, unlike Part 1's. This
remains **sensitivity evidence only**: it does not replace the primary results,
does not alter the locked primary confirmatory ordering, does not change
selected configurations and selects no paper winner. Recorded in
`stage126_m1_robustness_part2_primary_comparison.json`; handoff markers
`m1_robustness_part2_sample_sensitivity_reported=true`,
`m1_robustness_part2_ordering_differs_from_primary=false`,
`m1_primary_claim_ordering_preserved=true`. The Part 1 ordering-instability
markers are retained unchanged.

**Part 1 preservation:** all seven Part 1 scientific artifacts (authorization
record, feature manifest, execution manifest, OOF predictions, metrics,
completion lock, primary comparison) are byte-identical after Part 2. Only three
**verification-only** Part 1 files were refreshed — the QC report, the metadata
manifest and the Part 5 compatibility record — because they embed the current
successor-test-file hash. No Part 1 model was retuned; no Part 1 probability or
metric changed.

**Successor-test hash history after Part 2 (three generations):** the Stage125
historical hash `0a117c19…` still pinned by the frozen Part 5 metadata, the Part
1 completion-time hash `62cd1593…` (**history — never the current hash**), and
the recomputed Part 2 current hash. All three are recorded separately in
`stage126_m1_robustness_part2_part5_successor_compatibility.json`.

**Robustness Part 3 — COMPLETED (2026-07-23):**
`expanded_rule_a_company_scope_robustness` was explicitly human-authorized
(423-byte text, SHA-256 `f1230aa0…`) and executed on the development folds only,
from base `main` `6412b45c`. **Only the company-scope sample changed**
(`analysis_ready_expanded_rule_a_stage125.csv`, SHA-256 `fbe9b29c…`). Target,
nine-feature order, preprocessing, missingness-indicator logic, selected
configurations, folds, seeds, metrics and class weighting all unchanged.
**No retuning** (0 searches; 22 fits / 22 predictions), **no full-development
refit**, and the **final test remained locked** (361 identities counted only via
the frozen split contract; 0 predictor rows, 0 target rows, 0 predictions, 0
metrics). No calibration, threshold optimization, bootstrap, Holm, p-values,
winner selection, SMOTE/SMOTENC or SHAP. Counts: 1056 rows / 124 companies /
80 pos / 976 neg; development 695 (68 / 627); folds 254 / 215 / 469 / 226;
1323 OOF rows (441 per family); 9 metric rows. Handoff markers:
`m1_robustness_part3_human_authorized=true`,
`m1_robustness_part3_completed=true`,
`m1_robustness_completed_category_ids=[part1, part2, part3]`,
`m1_robustness_next_category_id=expanded_rule_b_combined_robustness`,
`m1_robustness_part4_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Part 3 sample delta (row identities only):** Expanded Rule A is a **strict
superset** of primary Rule A — 44 expanded-only rows, 0 primary-only rows, +5
companies, +0 positive, +44 negative; +29 development rows (all negative); folds
+9 / +10 / +19 / +10; 20 added OOF identities, **all target 0**; +15 final-test
identities.

**Part 3 results (development-only sample sensitivity):** pooled PR-AUC —
Logistic 0.442886 (−0.64%), RF 0.390702 (−2.92%), XGBoost 0.356561 (+0.00%).
**The locked primary ordering Logistic > RF > XGBoost is preserved**; the largest
absolute change is 0.0117. Because the additions are negative-only, the expanded
company scope does **not** materially change interpretation. Primary results were
not replaced, the primary ordering lock is unchanged and no paper winner was
selected. A separated descriptive Part 2 comparison is recorded without
multiplying claims or selecting a preferred robustness sample.

**Live-versus-historical test boundary (2026-07-23):** the frozen Stage125
Part 5 file contains historical tests explicitly marked `live_successor_state`.
Those tests remain **byte-identical** and are verified against the frozen Part 2
successor reference commit `6412b45c4adc6584a5567c7c96e0932f68f31e8a` by
`project/run_stage125_part5_historical_successor_tests.py`. **They are not part
of the current Stage126 live gate.** The default suite

```bash
PYTHONPATH=project python -m pytest project/tests -q
```

excludes only that historical marker (2472 selected / 9 deselected of 2481
collected; 2471 passed, 1 skipped, 9 deselected, 0 failed); **all
non-historical tests remain active**, including the rest of the frozen Part 5
file. Exclusion is by marker expression only — no file ignore, node ID, skip,
xfail or collection hook — and that narrowness is proven by
`test_stage126_live_historical_test_boundary.py`. The Stage126 current-state
validator remains the sole current-state validation surface. This is a
consistent application of the existing validation-architecture boundary lock,
**not** a scientific-error exception; Stage125 Part 5 was neither reopened nor
re-pinned.

**Robustness Part 4 — COMPLETED (2026-07-24):**
`expanded_rule_b_combined_robustness` was explicitly human-authorized
(418-byte text, SHA-256 `e40852d9…`) and executed on the development folds
only, from base `main` `853a8def…`. **Only the combined Rule B sample
changed** (`analysis_ready_expanded_rule_b_stage125.csv`, SHA-256
`2e61a282…`). Target, nine-feature order, preprocessing, missingness-indicator
logic, selected configurations, folds, seeds, metrics and class weighting all
unchanged. **No retuning** (0 searches; 22 fits / 22 predictions), **no
full-development refit**, and the **final test remained locked** (353
identities counted only via the frozen split contract; 0 predictor rows, 0
target rows, 0 predictions, 0 metrics). No calibration, threshold
optimization, bootstrap, Holm, p-values, winner selection, SMOTE/SMOTENC or
SHAP. Counts: 1035 rows / 122 companies / 79 pos / 956 neg; development 682
(68 / 614); folds 250 / 211 / 461 / 221; 1296 OOF rows (432 per family); 9
metric rows. Handoff markers: `m1_robustness_part4_human_authorized=true`,
`m1_robustness_part4_completed=true`,
`m1_robustness_completed_category_ids=[part1, part2, part3, part4]`,
`m1_robustness_next_category_id=persistent_loss_robustness_target`,
`m1_robustness_part5_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Part 4 sample delta (row identities only, three independent comparisons):**
versus Part 2 (main Rule B) — Part 4 is a **strict superset**: 42 Part4-only
rows, 0 Part2-only rows, +5 companies, +0 positive, +42 negative; +27
development rows (all negative); 19 added OOF identities (all target 0); +15
final-test identities. Versus Part 3 (expanded Rule A) — Part 4 is a **strict
subset**: 21 Part3-only rows, 0 Part4-only rows, −2 companies, −1 positive,
−20 negative; −13 development rows (all negative); 9 removed OOF identities;
−8 final-test identities. Versus the locked primary Rule A sample — **neither**
a subset nor a superset: 42 Part4-only rows, 19 primary-only rows, net +23
rows, +3 companies, −1 positive, +24 negative; development net +16 (27
Part4-only / 11 primary-only, all differences negative); OOF net +11 (19 / 8);
final-test net +7 (15 / 8).

**Part 4 results (development-only sample sensitivity):** pooled PR-AUC —
Logistic 0.444984 (−0.17%), RF 0.396419 (−1.50%), XGBoost 0.355211 (−0.37%).
**The locked primary ordering Logistic > RF > XGBoost is preserved.**
Development-fold and pooled-OOF identity differences versus primary, Part 2
and Part 3 are all target-0; at the frozen full-sample aggregate level,
however, Part 4 has one fewer positive event than Part 3 and primary
(frozen final-test positive counts 11 (Part 4) vs 12 (Part 3) vs 12
(primary), no row-level final-test target accessed). Because the pooled
development-OOF ordering is preserved and the PR-AUC changes remain small,
the combined sample does **not** materially change interpretation. Primary
results were not replaced, the primary ordering lock is unchanged and no
paper winner was selected. Separated descriptive Part 2 and Part 3 comparisons
are recorded without multiplying claims or selecting a preferred robustness
sample.

**Next — Part 5 (`persistent_loss_robustness_target`) is NOT authorized
and NOT started.** It requires its own separate explicit human authorization;
the consumed Part 4 authorization is not a standing authorization. Parts 1–4
are completed. Parts 5–6 remain outstanding, so M1 robustness is not complete.

Historical Part 3B / 3B.1x notes (retained): origin probes and five-row
document-binding evidence remain as frozen scientific history; they do **not**
authorize expansion. 80-row scale-up is cancelled. Part 3B expansion disposition
is `superseded_not_required_for_stage125_closure` (`part3b_completed=false`).

### Historical markers — Stage125 Part 5 closure
(historical state at Stage125 closure time; not the current repository state)

At Stage125 closure the Handoff markers were:

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
- `stage125_part5_readiness_closure_completed=true`
- `stage125_completed=true`
- `stage126_m1_entry_ready=true`
- `stage126_authorized=false` (historical state at Stage125 closure time)
- `stage126_started=false` (historical state at Stage125 closure time)
- `modeling_authorized=false` (historical state at Stage125 closure time)
- `modeling_started=false` (historical state at Stage125 closure time)
- `final_test_unlocked=false`

### Current Stage126 markers (must match Handoff)

- `broad_codal_capture_stopped=true`
- `financial_data_researcher_verified_frozen=true`
- `active_availability_method=fixed_regulatory_lag`
- `active_availability_lag_months=4`
- `four_month_regulatory_lag_locked=true`
- `six_month_lag_superseded=true`
- `historical_six_month_decision_retained=true`
- `row_level_publish_datetime_collection_required=false`
- `part3b_completed=false`
- `part3c_leakage_safe_finalization_completed=true`
- `part4_statistical_analysis_plan_locked=true`
- `stage125_completed=true`
- `stage126_m1_entry_ready=true`
- `stage126_authorized=true`
- `stage126_started=true`
- `development_modeling_authorized=true`
- `modeling_authorized=true`
- `modeling_started=true`
- `m1_primary_development_tuning_completed=true`
- `m1_robustness_started=false`
- `m1_robustness_completed=false`
- `final_test_unlocked=false`
- `final_test_access_authorized=false`
- `final_test_predictor_values_inspected=false`
- `final_test_target_values_inspected=false`
- `final_test_evaluation_performed=false`
- `m2_data_collected=false`
- `m3_data_collected=false`
- `m4_data_collected=false`

**Still prohibited without the next explicit micro-part decision / authorization:**

- final-test access or evaluation
- full-development refit
- M1 robustness execution without the next explicit micro-part decision
- SMOTE robustness
- target-proximity robustness
- Rule B / expanded-sample robustness
- persistent-loss robustness
- M2/M3/M4 data collection or modeling
- SHAP
- network extraction
- expanded CODAL/TSETMC/CBI network for value extraction
- row-level PublishDateTime collection
- real observed available_at assignment
- 80-row / 130-company CODAL scale-up
- Part 3B.2

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

**Modeling authorization (Stage125 historical):** modeling remained prohibited
through all of Stage125; it began only when Stage126 (M1 Financial Baseline)
was explicitly human-authorized. Stage126 M1 primary development-fold tuning
is now authorized and started; remaining prohibitions are listed under the
active Stage126 section above.

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

- ❌ Final-test access or evaluation; full-development refit; M1 robustness
  without the next explicit micro-part decision; SMOTE / target-proximity /
  Rule B / expanded-sample / persistent-loss robustness; M2/M3/M4 data
  collection or modeling; SHAP; network extraction
- ❌ Persian text / text modeling (M5) — removed from the paper and roadmap
- ❌ Any data or analysis depending on accessibility < 3
- ❌ Data extraction, model runs, or target/sample changes during Stage125 Part 0

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
