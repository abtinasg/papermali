# Financial Distress Prediction — Current Run Guide (Stage122 → Stage123)

This project is at the **data-freeze** phase. The current, authoritative pipeline is the
Stage122 → Stage123 sequence. **No final model is run yet** (no Logistic Regression,
Random Forest, XGBoost, Optuna, SHAP, SMOTE, calibration, or article/report generation).

## Correct run order

```bash
cd project
python3.13 -m venv ../.venv          # if not created yet
source ../.venv/bin/activate
pip install -r requirements.txt

# 1) Stage122 — freeze the composite operational distress target + eligibility + pairs
python run_stage122.py               # writes stage122/  (target is frozen here)

# 2) Stage123 — statement-scope correction + eligibility/panel rebuild on the
#    APPROVED Stage122 output (main vs expanded company sets). Independent QC + tests.
python run_stage123.py               # writes stage123/  (exits non-zero if QC fails)

# 3) Unit tests
python -m pytest tests/test_stage123.py -q
```

`run_stage122.py` must run **before** `run_stage123.py`: Stage123 consumes
`stage122/modeling_all_rows_stage122.csv` (the bulky panel is gitignored, so a fresh
clone regenerates it via step 1). Stage123 aligns Stage121 raw and the Stage122 base by
`row_key`, so results are independent of row order.

## What each stage produces

| Stage | Folder | Key outputs |
|---|---|---|
| Stage122 | `stage122/` | `FD_target_main` (composite operational distress target) + 2 robustness targets, target audit/definition/distribution, eligibility, t→t+1 pairs, QC, change log, metadata, workbook |
| Stage123 | `stage123/` | statement-scope correction audit, `modeling_all_rows_stage123.csv`, `modeling_one_year_ahead_stage123.csv`, eligibility audit, company mapping, listing review, leakage manifest (3 classes), independent QC report, change log, metadata+hashes, workbook |

## `run_all.py` is the OLD Stage121 baseline

`run_all.py` trains LR/RF/XGBoost on the **earlier Stage121** target
(`distressed_target_reviewed`) using `build_dataset.py` (the old candidate selection and
time split). It is kept only as the historical baseline and is **documented in
[`README_STAGE121_LEGACY.md`](README_STAGE121_LEGACY.md)**. Do **not** run it for the
current target — the Stage123 target/split modeling pipeline will be redesigned
separately after the Stage123 freeze is approved.

## Guardrails still enforced (Stage123)

- No model / tuning / SHAP / SMOTE / calibration / report in this phase.
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
