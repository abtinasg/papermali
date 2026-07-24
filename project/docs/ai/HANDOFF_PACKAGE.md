# 📦 HANDOFF PACKAGE — Financial Distress Prediction (Iran)

> Living index for `abtinasg/papermali`. New agents: read this, then
> [`CURRENT_STATE.md`](CURRENT_STATE.md) and [`OPEN_TASKS.md`](OPEN_TASKS.md).
> The machine-readable snapshot is [`handoff_state.json`](handoff_state.json).
> Repository-driven: the auto files are generated from git + QC. See
> [`README.md`](README.md) for the auto/human split.

## 1. Project intro

Research project (journal paper) predicting **financial distress** of companies
listed on the Tehran Stock Exchange. Python pipeline, config-driven, reproducible,
with independent QC at every stage.

## 2. Final goal

A defensible, fully source-documented dataset and a reproducible, leakage-safe
distress-prediction modeling pipeline, with final-test results and article claims
produced only after their separate authorization — where **every value is traceable
to a source** and nothing is guessed.

## 3. Current state

See [`CURRENT_STATE.md`](CURRENT_STATE.md) (auto-generated). Stage126 M1 is human-authorized and started. Primary M1 development-fold tuning is completed on PR #52. M1 robustness Parts 1–4 are completed on the development folds (Part 4 `expanded_rule_b_combined_robustness` was explicitly authorized and is completed; that authorization was consumed and is not a standing authorization). Parts 5–6 remain outstanding and Part 5 is not authorized. No full-development refit has occurred. The final test remains locked and untouched. M2/M3/M4 data were not collected.

## 4. Firm decisions

See [`DECISIONS.md`](DECISIONS.md).

## 5. Non-negotiable rules

- Nothing is guessed. If a source value is not found, it stays **Missing**.
- Every date/number must be documented to a source (`source_file`, `source_url`,
  hashes).
- Stage122 / Stage123 / targets / financials / ratios / statement-scope are
  **read-only**; their hashes are checked before and after every run.
- **Current Stage126 M1 prohibitions:** final-test access or evaluation; full-development refit; M1 robustness without the next explicit micro-part decision; SMOTE robustness; target-proximity robustness; Rule B / expanded-sample robustness; persistent-loss robustness; M2/M3/M4 data collection or modeling; SHAP; network extraction.
- Bulky outputs are gitignored; only source + small QC/metadata/audit files are
  committed.
- Two-commit workflow: **code-commit → artifact-commit → merge-commit**. QC points at
  the *code* commit, not the merge.

### 5.1 Research vs maintenance pointers (Handoff semantics)

Do not confuse QC selection with the research-action chain:

- `last_completed_micro_part` in `handoff_state.json` is a **legacy JSON field
  name**; its value is copied from
  `ROADMAP.md` → `last_completed_research_action_id` (research chain only).
- `next_research_action_id` likewise shows only the research chain.
- `selected_qc_scope` may point at a **newer maintenance-task QC** (for example
  Part 3B.1A CUT-A available-at operationalization lock) while those research
  IDs stay unchanged.
- Part 3B.1 completion is signaled by `part3b1_decision_locked=true`; Part 3B.1A
  adds `cut_a_available_at_operationalization_locked=true`. Neither must advance
  `last_completed_research_action_id` / `next_research_action_id`.
- Handoff / documentation commits also never advance the research stage
  (`active_maintenance_task_id` vs `active_research_workstream_id`).

## 6. Reference files

- Run guide: [`../../README_RUN.md`](../../README_RUN.md)
- Legacy Stage121 baseline: [`../../README_STAGE121_LEGACY.md`](../../README_STAGE121_LEGACY.md)
- Config: [`../../config.yaml`](../../config.yaml)
- Gate B execution source/test/QC: `src/stage124_gate_b_execution.py`,
  `tests/test_stage124_gate_b_execution.py`,
  `stage124/stage124_batch02_gate_b_qc_report.json`
- Frozen-asset report: [`FROZEN_ASSETS.md`](FROZEN_ASSETS.md)
- Stage125 research contract: [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md)
- Stage125 Part 1 data-contract source/test/QC: `src/stage125_part1_data_contract.py`,
  `run_stage125_part1.py`, `tests/test_stage125_part1_data_contract.py`,
  `stage125/stage125_part1_data_contract_qc_report.json` (contracts + read-only
  M1 provenance-gap audit; no modeling, no extraction)
- Stage125 Part 2 prediction-time-contract source/test/QC: `src/stage125_part2_prediction_time_contract.py`,
  `run_stage125_part2.py`, `tests/test_stage125_part2_prediction_time_contract.py`,
  `stage125/stage125_part2_prediction_time_contract_qc_report.json` (prediction-time
  & leakage contract; per-pair cutoff/feature/leakage audit; no modeling, no extraction)
- Stage125 Part 3A pilot-protocol source/test/QC: `src/stage125_part3a_pilot_protocol.py`,
  `run_stage125_part3a.py`, `tests/test_stage125_part3a_pilot_protocol.py`,
  `stage125/stage125_part3a_pilot_protocol_qc_report.json` (accessibility rubric,
  gate protocol, candidate inventory freeze, sampling frame; no evidence, no extraction)
- Stage125 Part 3A.1 decision-lock source/test/QC: `src/stage125_part3a_decision_lock.py`,
  `run_stage125_part3a_decision_lock.py`, `tests/test_stage125_part3a_decision_lock.py`,
  `stage125/stage125_part3a_decision_lock_qc_report.json` (approved rubric, G09–G14
  thresholds, locked pilot selection; no evidence, no extraction)
- Stage125 Part 3B.0 evidence-readiness source/test/QC: `src/stage125_part3b0_evidence_readiness.py`,
  `run_stage125_part3b0.py`, `tests/test_stage125_part3b0_evidence_readiness.py`,
  `stage125/stage125_part3b0_evidence_readiness_qc_report.json` (schema validator,
  immutable cache contract, network sentinel, Gate engine scaffolding; frozen
  historical baseline after Part 3B authorization)
- Stage125 Part 3B evidence-capture source/test/QC: `src/stage125_part3b_evidence_capture.py`,
  `run_stage125_part3b.py`, `tests/test_stage125_part3b_evidence_capture.py`,
  `stage125/stage125_part3b_evidence_capture_qc_report.json` (authorized Part 3B
  endpoint/source-origin feasibility probe; 800 pair-candidate assessments;
  scores null; no candidate-value or pair-level value extraction; no real
  accessibility scoring; no modeling)
- Stage125 Part 3B.1 decision-lock source/test/QC: `src/stage125_part3b1_decision_lock.py`,
  `run_stage125_part3b1.py`, `tests/test_stage125_part3b1_decision_lock.py`,
  `stage125/stage125_part3b1_decision_lock_qc_report.json` (feature/scoring/cutoff
  adjudication contracts + synthetic validation only; no network; no real
  extraction/scoring; no modeling). Adjudicated outputs are versioned as
  `part3b1_adjudicated_decision_requirements_stage125.json` and
  `README_STAGE125_PART3B1_DECISION_LOCK.md` (historical Part 3B proposed
  requirements README remains frozen).
- Stage125 Part 3B.1E conservative-lag decision-lock source/test/QC:
  `src/stage125_part3b1e_conservative_lag_decision.py`,
  `run_stage125_part3b1e.py`,
  `tests/test_stage125_part3b1e_conservative_lag_decision.py`,
  `stage125/stage125_part3b1e_conservative_lag_qc_report.json` (fixed
  six-month lag; researcher-verified financials frozen; no broad CODAL
  capture; assumed availability field only; no Stage126 / modeling).
- Stage125 Part 4 statistical analysis plan source/test/QC:
  `src/stage125_part4_statistical_analysis_plan.py`,
  `run_stage125_part4.py`,
  `tests/test_stage125_part4_statistical_analysis_plan.py`,
  `stage125/stage125_part4_statistical_analysis_plan_qc_report.json` (active
  contract `stage125_part4_sap_v2`; M1=9 admitted; revenue-growth audit-only
  rejection; temporal splits; coverage/event gates; no modeling)
- Stage125 Part 5 readiness closure source/test/QC:
  `src/stage125_part5_readiness_closure.py`,
  `run_stage125_part5.py`,
  `tests/test_stage125_part5_readiness_closure.py`,
  `stage125/stage125_part5_readiness_closure_qc_report.json` (Gate 125.0;
  keep/drop/defer; Stage126 M1 entry contract readiness-only; no modeling).
  The entry-contract flags `stage126_authorized=false` / `modeling_authorized=false`
  describe the **historical Stage125 closure-state artifact** at closure time; they
  are not the current authorization state (Stage126 M1 is now human-authorized and
  started). The frozen artifact itself is unchanged.
- Stage125 Part 3C leakage-safe dataset finalization source/test/QC:
  `src/stage125_part3c_leakage_safe_dataset_finalization.py`,
  `run_stage125_part3c.py`,
  `tests/test_stage125_part3c_leakage_safe_dataset_finalization.py`,
  `stage125/stage125_part3c_leakage_safe_dataset_qc_report.json` (four
  Gate B designs; audited pair + timing-eligible analysis-ready surfaces;
  active four-Jalali-month regulatory lag; six-month methodology superseded;
  bulky outputs gitignored/hashed; no feature approval / modeling / Stage126).
- Stage126 M1 primary development-fold tuning source/test/QC:
  `src/stage126_m1_primary_development_tuning.py`,
  `run_stage126_m1_primary_development_tuning.py`,
  `tests/test_stage126_m1_primary_development_tuning.py`,
  `stage126/stage126_m1_primary_development_tuning_qc_report.json`
  (human-authorized M1 development-fold tuning; final test locked; no robustness).
- Stage126 authorization transition guard source/test/QC:
  `src/stage126_authorization_transition_guard.py`,
  `tests/test_stage126_authorization_transition_guard.py`,
  `stage126/stage126_m1_final_test_lock_guard.json`,
  `stage126/stage126_m1_primary_development_lock.json`.
- Stage126 M1 robustness Part 0 decision-lock source/test/QC:
  `src/stage126_m1_robustness_part0_decision_lock.py`,
  `run_stage126_m1_robustness_part0_decision_lock.py`,
  `tests/test_stage126_m1_robustness_part0_decision_lock.py`,
  `stage126/stage126_m1_robustness_part0_decision_record.json`,
  `stage126/stage126_m1_robustness_part0_decision_lock_qc_report.json`
  (additive robustness execution contract; **decision lock only — no robustness
  execution**; primary artifacts byte-identical; final test locked).
- Stage126 M1 robustness Part 1 (target-proximity) source/test/QC:
  `src/stage126_m1_robustness_part1_target_proximity.py`,
  `run_stage126_m1_robustness_part1_target_proximity.py`,
  `tests/test_stage126_m1_robustness_part1_target_proximity.py`,
  `stage126/stage126_m1_robustness_part1_human_authorization_record.json`,
  `stage126/stage126_m1_robustness_part1_oof_predictions.csv`,
  `stage126/stage126_m1_robustness_part1_metrics.csv`,
  `stage126/stage126_m1_robustness_part1_completion_lock.json`,
  `stage126/stage126_m1_robustness_part1_qc_report.json`
- Stage126 M1 robustness Part 3 (expanded Rule A company scope) source/test/QC:
  `src/stage126_m1_robustness_part3_expanded_rule_a.py`,
  `run_stage126_m1_robustness_part3_expanded_rule_a.py`,
  `tests/test_stage126_m1_robustness_part3_expanded_rule_a.py`,
  `stage126/stage126_m1_robustness_part3_human_authorization_record.json`,
  `stage126/stage126_m1_robustness_part3_sample_delta.csv`,
  `stage126/stage126_m1_robustness_part3_oof_predictions.csv`,
  `stage126/stage126_m1_robustness_part3_metrics.csv`,
  `stage126/stage126_m1_robustness_part3_primary_comparison.json`,
  `stage126/stage126_m1_robustness_part3_completion_lock.json`,
  `stage126/stage126_m1_robustness_part3_qc_report.json`
- Stage126 M1 robustness Part 2 (listing Rule B sample) source/test/QC:
  `src/stage126_m1_robustness_part2_listing_rule_b.py`,
  `run_stage126_m1_robustness_part2_listing_rule_b.py`,
  `tests/test_stage126_m1_robustness_part2_listing_rule_b.py`,
  `stage126/stage126_m1_robustness_part2_human_authorization_record.json`,
  `stage126/stage126_m1_robustness_part2_sample_delta.csv`,
  `stage126/stage126_m1_robustness_part2_oof_predictions.csv`,
  `stage126/stage126_m1_robustness_part2_metrics.csv`,
  `stage126/stage126_m1_robustness_part2_primary_comparison.json`,
  `stage126/stage126_m1_robustness_part2_completion_lock.json`,
  `stage126/stage126_m1_robustness_part2_qc_report.json`
  (**explicitly human-authorized and completed on development folds only; only
  the feature set changed; no retuning; no full-development refit; final test
  locked; sensitivity analysis only; Part 2 not authorized**).
- Stage126 M1 robustness Part 4 (expanded Rule B combined sample) source/test/QC:
  `src/stage126_m1_robustness_part4_expanded_rule_b.py`,
  `run_stage126_m1_robustness_part4_expanded_rule_b.py`,
  `tests/test_stage126_m1_robustness_part4_expanded_rule_b.py`,
  `stage126/stage126_m1_robustness_part4_human_authorization_record.json`,
  `stage126/stage126_m1_robustness_part4_sample_delta.csv`,
  `stage126/stage126_m1_robustness_part4_oof_predictions.csv`,
  `stage126/stage126_m1_robustness_part4_metrics.csv`,
  `stage126/stage126_m1_robustness_part4_primary_comparison.json`,
  `stage126/stage126_m1_robustness_part4_completion_lock.json`,
  `stage126/stage126_m1_robustness_part4_qc_report.json`
  (**explicitly human-authorized and completed on development folds only; only
  the combined sample changed; no retuning; no full-development refit; final
  test locked; development-only sample sensitivity; Part 5 not authorized**).

## 7. Done

See [`CHANGELOG.md`](CHANGELOG.md) and `git log`. High level: Stage121 (legacy) →
Stage122 freeze → Stage123 freeze → Stage124 Part1 template → Pilot15 confirmed →
Batch02 Gate A V1→V2 → Batch02 Part 2 sealed → Part 3.1A.* research engine →
official API verified master → Gate B readiness → rule approval → Gate B execution →
Stage125 Part 3C leakage-safe finalization → Stage125 Part 4 SAP lock →
Stage125 Part 5 readiness closure → Stage126 M1 human authorization →
Stage126 primary development-fold tuning completed on PR #52.

## 8. Open tasks

See [`OPEN_TASKS.md`](OPEN_TASKS.md).

## 9. Known issues / traps

- `project/outputs/04_models/` holds **legacy Stage121** model artifacts
  (`best_hyperparameters.json`, `final_thresholds.json`) from `run_all.py`. These do
  **not** mean modeling has started for the current target — they are historical
  artifacts only.
- `run_all.py` is the old Stage121 baseline only; do not run it for the current
  target.

## 10. Next step

See `next_research_action_id` in [`ROADMAP.md`](ROADMAP.md) and
[`handoff_state.json`](handoff_state.json). Stage126 M1 is human-authorized and started;
primary M1 development-fold tuning is completed on PR #52.

The next scientific action is **not automatically authorized**. A separate explicit
human micro-part decision is required before any M1 robustness execution. M1
robustness, full-development refit and final-test access remain unstarted and
unauthorized. The final test remains locked and untouched; M2/M3/M4 data were not
collected.

The robustness Part 0 decision lock
(`stage126_m1_robustness_execution_contract_v1`) records the execution contract
for the six robustness categories (one category per micro-part PR). **Part 1
(`m1_target_proximity_six_feature_set`) was explicitly human-authorized and is
now completed** on the development folds — only the feature set changed, no
retuning, no full-development refit, and the final test remains locked and
untouched. Part 1 is **sensitivity-analysis evidence only**.

**Part 2 (`main_rule_b_listing_robustness`) was explicitly human-authorized and
is now completed** on the development folds — **only the sample changed** (the
listing-timing Rule B sample: 993 rows, 117 companies, 655 development rows,
1239 OOF rows), no retuning, no full-development refit, and the final test
remains locked and untouched (338 identities counted, never parsed). Part 2 is
**sensitivity-analysis evidence only**. Rule B keys are a strict subset of Rule
A keys (19 Rule A-only rows, 0 Rule B-only rows). All seven Part 1 scientific
artifacts remain byte-identical.

**Part 3 (`expanded_rule_a_company_scope_robustness`) was explicitly
human-authorized and is now completed** on the development folds — **only the
company-scope sample changed** (1056 analysis-ready rows, 124 companies, 695
development rows, 1323 OOF rows), no retuning, no full-development refit, and
the final test remains locked (361 identities counted only via the frozen split
contract). Expanded Rule A is a **strict superset** of primary Rule A: 44
expanded-only rows, 0 primary-only, +5 companies, +0 positive, +44 negative; all
20 added OOF identities carry target 0. Pooled PR-AUC: Logistic 0.442886
(−0.64%), RF 0.390702 (−2.92%), XGBoost 0.356561 (+0.00%) — **the locked primary
ordering Logistic > RF > XGBoost is preserved**, and because the additions are
negative-only the expanded scope does **not** materially change interpretation.
Part 3 is development-only sample-sensitivity evidence: primary results were not
replaced, the primary ordering lock is unchanged and no paper winner was
selected. All Part 1 and Part 2 artifacts, the primary Stage126 artifacts and
Stage125 remain byte-identical, and the independent current-state validator
advanced generically with no source change.

**Part 4 (`expanded_rule_b_combined_robustness`) was explicitly human-authorized
and is now completed** on the development folds — **only the combined Rule B
sample changed** (1035 analysis-ready rows, 122 companies, 682 development rows,
1296 OOF rows), no retuning, no full-development refit, and the final test
remains locked (353 identities counted only via the frozen split contract).
Part 4 is a **strict superset** of Part 2 (42 Part4-only rows, 0 Part2-only) and
a **strict subset** of Part 3 (21 Part3-only rows, 0 Part4-only), and neither a
subset nor a superset of the locked primary sample. The corrected interpretation
distinguishes the **development-fold and pooled-OOF identity differences (all
target-0)** from the **frozen full-sample aggregate level, where Part 4 has one
fewer positive event than both Part 3 and the locked primary sample** (−1 each);
the corresponding **frozen final-test aggregate positive counts are 12 (primary)
/ 12 (Part 3) / 11 (Part 4)**, read only from the frozen event-count gate with
**no row-level final-test target accessed**. Pooled PR-AUC: Logistic 0.444984
(−0.17%), RF 0.396419 (−1.50%), XGBoost 0.355211 (−0.37%) — **the locked primary
ordering Logistic > RF > XGBoost is preserved**, so the combined sample does
**not** materially change the development-only interpretation. Primary results
were **not** replaced and **no paper winner** was selected. The Part 4
authorization was **consumed** and is **not** a standing authorization
(`m1_robustness_execution_authorized=false`). The Part 4 metadata runtime
provenance was corrected to the canonical environment (Python 3.13.5 /
jdatetime 6.0.1); no scientific artifact, metric or OOF prediction changed.
**Part 5 (`persistent_loss_robustness_target`) is not authorized and not
started**; each future Part requires its own separate explicit human
authorization. Parts 5–6 remain outstanding, so M1 robustness is not complete.
Stage125 Part 5 remains historical and immutable. All Part 1, Part 2 and Part 3
artifacts, the primary Stage126 artifacts and Stage125 remain byte-identical,
and the independent current-state validator advanced generically with no source
change.

**Observed ordering sensitivity (reported; primary claims unchanged).** Primary
pooled PR-AUC ordering: **Logistic > RF > XGBoost**. Part 1 observed pooled
PR-AUC ordering: **XGBoost > RF > Logistic**. **All three pooled PR-AUC values
declined.** The observed Part 1 sensitivity ordering differs from the primary
development ordering; this does not change the locked primary ordering used for
confirmatory interpretation, does not replace the primary results, and does not
select a paper winner. Development-only sensitivity finding, recorded in
`stage126/stage126_m1_robustness_part1_primary_comparison.json` and reported to
the human supervisor. No selected configuration changed and no automatic
scientific action was triggered.

**Part 2 observed ordering (reported; primary claims unchanged).** Pooled
development-OOF PR-AUC: Logistic 0.447170 (+0.32%), RF 0.401263 (−0.29%),
XGBoost 0.341960 (−4.09%). The **observed Part 2 ordering (Logistic > RF >
XGBoost) matches the primary development ordering** — unlike Part 1's, which
differed. It remains sensitivity evidence only: no primary result was replaced,
the locked confirmatory ordering is unchanged, no selected configuration
changed, and no paper winner was selected. Recorded in
`stage126/stage126_m1_robustness_part2_primary_comparison.json`. The Part 1
ordering-instability markers are retained unchanged.

**Validation architecture (locked 2026-07-23).** Stage125 Part 5 is a **frozen
historical closure**. It is **no longer responsible for validating live Stage126
successor state**. The **independent Stage126 current-state validator**
(`stage126_current_state_validator_v1`,
`project/run_stage126_current_state_validator.py --check`) is the **sole
current-state validation surface**; it never imports, executes or calls into
Part 5. Future robustness parts must **not** regenerate previous-part
verification artifacts unless a genuine scientific error **and** a separate
explicit human authorization exist. Handoff markers:
`validation_architecture=stage126_current_state_validator_v1`,
`stage125_part5_mode=historical_immutable`,
`stage125_part5_live_gate_active=false`,
`stage125_part5_future_regeneration_allowed=false`,
`prior_robustness_verification_artifact_regeneration_allowed=false`,
`prior_part_reopening_requires_scientific_error=true`,
`prior_part_reopening_requires_explicit_human_authorization=true`.
Live sequence: the Stage126 current-state validator, the newest micro-part
runner `--check`, the Handoff validator and the full test suite —
`run_stage125_part5.py --check` is **not** a routine gate.

**Live versus historical tests.** The frozen Stage125 Part 5 file contains
historical tests explicitly marked `live_successor_state`. Those tests remain
byte-identical and are verified against the frozen Part 2 successor reference
commit `6412b45c4adc6584a5567c7c96e0932f68f31e8a` by
`project/run_stage125_part5_historical_successor_tests.py`. **They are not part
of the current Stage126 live gate.** The default repository suite excludes only
that historical marker (`not live_successor_state`, configured in `pytest.ini`);
**all non-historical tests remain active**, including the rest of the frozen
Part 5 file. The Stage126 current-state validator remains the sole current-state
validation surface. Recorded in
`stage126/stage126_live_vs_historical_test_boundary.json`; Handoff markers
`stage125_part5_historical_successor_tests_in_live_gate=false` and
`stage126_live_test_suite_marker_expression="not live_successor_state"`.

The validator derives current state generically: the completed prefix is
`execution_order[:n]` over discovered per-part packages, the next category is
`execution_order[n]`, and the last completed micro-part comes from the newest
completion lock. Closed parts — scientific **and** verification-only artifacts,
plus their source, runner and tests — are pinned in
`stage126/stage126_closed_part_registry.json`; byte drift in any of them fails
validation. **Two QC roles are reported separately:**
`current_state_validation_*` (the independent validator) and
`last_completed_micro_part_qc_*` (the newest completed scientific part).

**Frozen Part 5 live-successor boundary (historical provenance only).** Stage125 Part 5 remains a frozen,
valid historical closure (source, runner and all `project/stage125/` artifacts
byte-identical). Its embedded live-Handoff successor check ends at the earlier
primary-development state. The full frozen Part 5 runner exits 1 first with the inherited `readiness_surface_disagreement` during a live-successor rebuild. Separately, direct `validate_actual_handoff` returns exactly the documented five-field historical successor mismatch (`m1_robustness_started`, `selected_qc_scope`, `selected_qc_path`, `contract_version`, `last_completed_micro_part`) with no forbidden fields. Neither behaviour was introduced by Part 2, and no Stage125 scientific artifact changed.

The **committed** frozen closure report still records `all_gate_pass=true`,
`stage125_gate_125_0=PASS` and `stage126_m1_entry_ready=true`; the failed gate
exists only inside the runner's transient live rebuild. This is an **expected
inherited historical-validator boundary**, recorded in
`stage126/stage126_m1_robustness_part1_part5_successor_compatibility.json` and
`stage126/stage126_m1_robustness_part2_part5_successor_compatibility.json`,
asserted in the Part 1 and Part 2 QC reports and explicitly tested — not a
scientific failure and not Stage125 drift. Current Stage126 successor state is
validated by the Part 0 integrity controls, the Part 1 and Part 2 QC reports,
the Part 2 completion lock and this Handoff validator.

**Successor-test provenance (three generations).** The Part 2 compatibility
record separates the Stage125 historical test hash `0a117c19…` (still pinned by
the frozen Part 5 metadata), the Part 1 completion-time hash `62cd1593…`
(history — never presented as current) and the recomputed Part 2 current hash.
Refreshing the Part 1 QC report, metadata manifest and Part 5 compatibility
record to carry the current hash is verification-only maintenance: every Part 1
scientific artifact stayed byte-identical.

## 11. Recent change history

See [`CHANGELOG.md`](CHANGELOG.md).
