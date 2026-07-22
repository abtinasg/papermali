# Financial Distress Prediction — Current Run Guide (Stage122 → Stage123 → Stage124 → Stage125 → Stage126)

**Stage125 is completed. Stage126 M1 is human-authorized and started. Primary M1 development-fold tuning is completed on PR #52. M1 robustness is not started. No full-development refit has been performed. The final test remains locked and untouched. M2/M3/M4 data collection or modeling has not started.**

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

# 6) AI Handoff validation
python scripts/validate_ai_handoff.py --check

# 7) Full test suite
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

## `run_all.py` is the OLD Stage121 baseline

`run_all.py` trains LR/RF/XGBoost on the **earlier Stage121** target
(`distressed_target_reviewed`) using `build_dataset.py` (the old candidate selection and
time split). It is kept only as the historical baseline and is **documented in
[`README_STAGE121_LEGACY.md`](README_STAGE121_LEGACY.md)**. Do **not** run it for the
current target — the modeling pipeline will be redesigned separately under
`stage125-modeling-readiness`.

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
