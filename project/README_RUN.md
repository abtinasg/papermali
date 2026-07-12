# Financial Distress Prediction — Current Run Guide (Stage122 → Stage123 → Stage124)

This project is at the **data-freeze** phase. The current, authoritative pipeline is the
Stage122 → Stage123 → Stage124 sequence. **No model is run yet** — no Logistic
Regression, Random Forest, XGBoost, Optuna, SHAP, SMOTE, calibration, article/report
generation, or macro/market merge.

**Stage124 status:** Gate B is **completed and frozen**. The verified listing master
(`listing_master_verified_stage124.csv`, 130 tickers from the official TSE API) is
canonical, and four Gate B sample designs have been produced in
`project/stage124/gate_b_final/`. Tests are **local results** (no GitHub Actions
configured): 58 focused tests in `test_stage124_gate_b_execution.py`, 736 passed,
1 skipped in the full suite. **Modeling remains prohibited** until
`stage125-modeling-readiness` is approved.

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

# 3) Stage124 — listing-master verification + Gate B eligibility execution
python run_stage124.py               # writes stage124/  (exits non-zero if QC fails)

# 4) Unit tests (Stage123, Stage124, Gate B readiness + execution)
python -m pytest tests/ -q
```

`run_stage122.py` must run **before** `run_stage123.py`, and `run_stage123.py` before
`run_stage124.py`: each stage consumes the previous stage's frozen output (the bulky
panels are gitignored, so a fresh clone regenerates them in order). Stage123 aligns
Stage121 raw and the Stage122 base by `row_key`; Stage124 derives its 130-ticker template
from the frozen Stage123 panel — both are independent of input row order.

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

## Guardrails still enforced (Stage123 + Stage124 Gate B)

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
- Stage124 Gate B is completed and frozen; modeling remains prohibited until
  `stage125-modeling-readiness` is approved.
