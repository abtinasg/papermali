# Financial Distress Prediction — Stage121 — Run Guide

Reproducible pipeline comparing **Logistic Regression, Random Forest, XGBoost** for
**one-year-ahead** financial-distress prediction (Tehran Stock Exchange firms), with
explainability, leakage control, and imbalance reporting.

## 1. Setup (clean environment)

```bash
cd project
python3.13 -m venv .venv          # Python 3.13 recommended (3.14 lacks some wheels)
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run everything (one command)

```bash
python run_all.py                 # uses config.yaml; writes everything under outputs/
```

All paths and choices live in `config.yaml` — nothing is hard-coded. The original
handoff files under `raw_handoff/` are read-only inputs and are never overwritten.

## 3. Output map

| Folder | Contents |
|---|---|
| `outputs/01_data_audit` | schema, duplicates, class distribution, target-shift audit, missingness, outliers, `data_audit_report.xlsx` |
| `outputs/02_modeling_data` | `modeling_one_year_ahead_final.csv`, `split_manifest.csv`, feature lists, preprocessing config |
| `outputs/04_models` | fitted joblib pipelines, best hyperparameters, final thresholds, calibrators |
| `outputs/05_predictions` | `test_predictions_all_models.csv` (row-level) |
| `outputs/06_metrics` | CV by fold/summary, test metrics, bootstrap CIs, threshold + calibration + seed-stability + robustness, `model_comparison_table.xlsx` |
| `outputs/07_explainability` | LR coefficients/odds, tree importances, SHAP global importance + values + plots |
| `outputs/08_figures` | all figures as PNG (300 dpi) + PDF |
| `outputs/03_code` | self-contained copy of the runnable code + `analysis_display.ipynb` |
| `outputs/09_report` | technical report (**md + pdf + docx**), Persian article drafts (**md + docx, RTL**), numbered `article_tables.xlsx`, `tables_index_fa.csv`, `figure_index_fa.csv` |
| `outputs/10_reproducibility` | env info, frozen requirements, seeds, run log, file hashes, final config |

> Report formats: the **technical report** is generated as Markdown, PDF (via
> `xhtml2pdf`, no system deps) and DOCX. The **Persian** article method/results drafts
> are delivered as Markdown and as RTL **DOCX** (Word renders Persian shaping/RTL
> correctly); a Persian PDF is intentionally not auto-generated because faithful Arabic
> shaping in PDF needs extra fonts — open the DOCX and export to PDF from Word if needed.

## 4. Split rationale (important, approved revision)

The distress label is non-zero **only in target years 1393–1398**. The brief's original
test window (1401–1402) therefore had a single positive, and two of the three proposed
validation folds had zero positives — making PR-AUC and the held-out evaluation
uncomputable. With written approval the temporal boundary was moved earlier:

- **dev** = target years 1393–1396 (27 positives) — expanding-window CV inside it
- **test** = target years 1397–1398 (9 positives), used exactly once
- target years ≥ 1399 (zero positives, after the test window) are excluded from
  one-year-ahead modeling and documented in `01_data_audit/target_shift_audit.csv`.

The split is still strictly forward-in-time. The test set is small (9 positives), so
test metrics / bootstrap CIs are wide; validation PR-AUC is the primary selection signal.

## 5. Key guardrails honored

- No financial missing value is zero-filled; median imputation + missing indicators,
  fit on the train fold only.
- No imputation/scaling/winsorization/SMOTE/threshold/calibration before the split.
- `ticker`/company name and the year-*t* target are never used as features.
- Cost-sensitive learning is the main imbalance method; SMOTE only in robustness.
- SHAP is computed only on the untouched test set with the final models.
- `config.yaml` controls run switches (`run:`), search spaces, seeds, and CV design.
