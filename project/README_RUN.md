# Financial Distress Prediction — Current Run Guide (Stage122 → Stage123 → Stage124 → Stage125 → Stage126)

**Stage125 is completed. Stage126 M1 is human-authorized and started. Primary M1 development-fold tuning is completed on PR #52. The robustness Part 0 decision lock records the robustness execution contract. Robustness Part 1 (`m1_target_proximity_six_feature_set`) was explicitly human-authorized and is completed on the development folds — only the feature set changed, no retuning, sensitivity analysis only. The observed Part 1 pooled PR-AUC ordering (XGBoost > RF > Logistic) differs from the primary ordering (Logistic > RF > XGBoost) and all three pooled values declined; this development-only sensitivity finding is reported but does not change the locked primary ordering used for confirmatory interpretation, does not replace the primary results and selects no paper winner. Robustness Part 2 (`main_rule_b_listing_robustness`) was explicitly human-authorized and is completed on the development folds — only the sample changed (the listing-timing Rule B sample), no retuning, sensitivity analysis only. The observed Part 2 pooled PR-AUC ordering (Logistic > RF > XGBoost) matches the primary ordering; it remains sensitivity evidence only and does not replace the primary results or select a paper winner. All seven Part 1 scientific artifacts remain byte-identical. Part 3 (`expanded_rule_a_company_scope_robustness`) is not authorized and not started. No full-development refit has been performed. The final test remains locked and untouched. M2/M3/M4 data collection or modeling has not started.**

The historical Stage122 → Stage123 → Stage124 sequence is frozen. Stage124 Gate B is **completed and frozen**. The verified listing master
(`listing_master_verified_stage124.csv`, 130 tickers from the official TSE API) is
canonical, and four Gate B sample designs have been produced in
`project/stage124/gate_b_final/`. Tests are **local results** (no GitHub Actions
configured): 58 focused tests in `test_stage124_gate_b_execution.py`, 736 passed,
1 skipped in the full suite.

## Correct run order

```bash
cd project
python3.13 -m venv ../.venv          # if not created yet
source ../.venv/bin/activate
pip install -r requirements.txt

# 1) Stage122 — freeze the composite operational distress target + eligibility + pairs
python run_stage122.py               # writes stage122/  (target is frozen here)

# 2) Stage123 — statement-scope correction + eligibility/panel rebuild on the
#    APPROVED Stage122 output (main vs expanded company sets). Independent QC.
python run_stage123.py               # writes stage123/  (exits non-zero if QC fails)

# 3a) Stage124 Part 1 — build the 130-ticker review template
python run_stage124.py

# 3b) Finalize the verified master from committed official TSE API batches
python run_stage124_official_api_finalize.py

# 3c) Reproduce the historical Gate B readiness comparison
python run_stage124_gate_b_readiness.py

# 3d) Execute the already-approved final Gate B rules
python run_stage124_gate_b_execution.py

# 4) Stage125 Part 3C / Part 4 / Part 5 (offline contracts; no modeling)
python run_stage125_part3c.py --check
python run_stage125_part4.py --check
python run_stage125_part5.py --check   # readiness closure / Gate 125.0

# 5) Stage126 M1 primary development-fold tuning (human-authorized; --check only)
python run_stage126_m1_primary_development_tuning.py --check

# 6) Stage126 M1 robustness Part 0 decision lock (decision contract only; --check)
python run_stage126_m1_robustness_part0_decision_lock.py --check

# 7) Stage126 M1 robustness Part 1 target-proximity (development-only; --check)
python run_stage126_m1_robustness_part1_target_proximity.py --check

# 8) Stage126 M1 robustness Part 2 listing Rule B sample (development-only; --check)
python run_stage126_m1_robustness_part2_listing_rule_b.py --check

# NOTE: after Part 1 (and unchanged after Part 2), `run_stage125_part5.py --check`
# exits 1 BY DESIGN on exactly the same five documented fields. Part 5
# is a frozen historical Stage125 closure whose embedded live-Handoff successor
# check ends at the earlier primary-development state; it reports exactly five
# expected mismatching fields. See
# stage126/stage126_m1_robustness_part1_part5_successor_compatibility.json.
# This is not a scientific failure and not Stage125 drift.

# 8) AI Handoff validation
python scripts/validate_ai_handoff.py --check

# 9) Full test suite
python -m pytest tests/ -q
```

`run_stage122.py` must run **before** `run_stage123.py`, and `run_stage123.py` before
the Stage124 runners: each stage consumes the previous stage's frozen output (the bulky
panels are gitignored, so a fresh clone regenerates them in order). Stage123 aligns
Stage121 raw and the Stage122 base by `row_key`; Stage124 derives its 130-ticker template
from the frozen Stage123 panel — both are independent of input row order.

- `run_stage124.py` only builds the template.
- `run_stage124_official_api_finalize.py` builds the verified master from committed
  official files.
- `run_stage124_gate_b_readiness.py` reproduces the historical rule comparison.
- `run_stage124_gate_b_execution.py` executes the already-approved Rule A and Rule B.
- `run_stage125_part5.py` is Stage125 readiness closure only (Gate 125.0); it does
  **not** authorize or start Stage126 / modeling.
- None of them perform modeling.
- The meaning of dates remains
  `first_observed_trading_date_from_official_tse_api`;
  no IPO/admission/listing date is introduced.

## What each stage produces

| Stage | Folder | Key outputs |
|---|---|---|
| Stage122 | `stage122/` | `FD_target_main` (composite operational distress target) + 2 robustness targets, target audit/definition/distribution, eligibility, t→t+1 pairs, QC, change log, metadata, workbook |
| Stage123 | `stage123/` | statement-scope correction audit, `modeling_all_rows_stage123.csv`, `modeling_one_year_ahead_stage123.csv`, eligibility audit, company mapping, listing review, leakage manifest (3 classes), independent QC report, change log, metadata+hashes, workbook |
| Stage124 | `stage124/` | `listing_master_verified_stage124.csv` (130 tickers, dates from official TSE API), Gate B outputs in `gate_b_final/` (four sample designs, canonical + filtered CSVs, QC report, metadata), `metadata_and_hashes_stage124_batch02_gate_b.json` |
| Stage125 | `stage125/` | Part 3C leakage-safe analysis-ready datasets (four Gate B designs), Part 4 locked statistical analysis plan (`stage125_part4_sap_v2`), Part 5 readiness closure (Gate 125.0) with the Stage126 M1 entry contract; **no modeling within Stage125** |
| Stage126 | `stage126/` | Human-authorized M1 development-fold tuning: three locked model families (regularized Logistic Regression, Random Forest, XGBoost), selected configurations, development OOF predictions and metrics, final-test lock guard; robustness Part 0 decision lock; robustness Part 1 target-proximity and Part 2 listing-Rule-B development-fold results (sensitivity analysis only); **no full-development refit, no final-test evaluation, Part 3 not authorized** |

## `run_all.py` is the OLD Stage121 baseline

`run_all.py` trains LR/RF/XGBoost on the **earlier Stage121** target
(`distressed_target_reviewed`) using `build_dataset.py` (the old candidate selection and
time split). It is kept only as the historical baseline and is **documented in
[`README_STAGE121_LEGACY.md`](README_STAGE121_LEGACY.md)**. `run_all.py` remains the
legacy Stage121 pipeline and must not be used for the current target. The current
authorized modeling path is the Stage126 M1 primary development-fold tuning pipeline.

## Guardrails still enforced (Stage123 + Stage124 Gate B + Stage126 M1)

- No financial value, ratio, or target changed by the statement-scope correction; raw
  provenance (`source_file`, `source_url`, hashes) is untouched — the prior scope label
  lives only in the immutable correction audit.
- Target aggregation: only `fd_article141_direct` is non-blocking; any all-missing
  quantitative criterion makes QC FAIL.
- `predictor_eligible_*` excludes the year-t target; pair eligibility =
  `predictor_eligible_t AND valid_target_(t+1)`.
- Independent QC re-reads outputs from disk and checks them against the raw data; on
  failure the QC report is saved and the runner exits non-zero with no metadata file.
- Bulky outputs (models, figures, workbooks, panels) are gitignored; only source and
  small QC/metadata/audit files are committed.
- Stage124 Gate B is completed and frozen.
- **Current Stage126 M1 prohibitions:** final-test access or evaluation; full-development refit; M1 robustness without the next explicit micro-part decision; SMOTE robustness; target-proximity robustness; Rule B / expanded-sample robustness; persistent-loss robustness; M2/M3/M4 data collection or modeling; SHAP; network extraction.
