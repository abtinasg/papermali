# Stage129 — Full-Development Refit EXECUTED (development only)

**Action id:** `stage129-full-development-refit-execution`
**Contract executed:** `stage129_full_development_refit_contract` (locked and merged in PR #89)
**Result:** all twelve fail-closed controls PASS · exactly **1** model fitted · `final_test_rows_read = 0`

This is the one-time refit the locked contract described. It fits the selected
model once on the development window and produces the four contracted outputs.
**No Final Test row, predictor, target, prediction or metric was read or
produced.**

## What was fitted

| field | value |
| --- | --- |
| block | `M1` |
| algorithm | `regularized_logistic_regression` |
| configuration | `logistic__C_0.1` |
| hyperparameters | `C=0.1`, `penalty=l2`, `solver=liblinear`, `max_iter=5000`, `class_weight=balanced` |
| fit set | development target years **1393–1399** |
| rows | **666** (68 positive / 598 negative), 110 tickers |
| design matrix | 18 columns — 9 continuous + 9 unstandardized missingness indicators |
| convergence | `n_iter = 6` |

The fit set is the union of the four development fold-roles, **deduplicated** —
666 unique predictor/target pairs, not the 1012-row full sample (which includes
the locked final-test partition) and not the 421-row pooled OOF surface.

## The pipeline was reused, not reimplemented

The refit imports `project/src/stage126_m1_primary_development_tuning.py` — the
same module that produced the locked primary results — and calls its own
`build_development_allowlist`, `load_development_values`, `fit_preprocessor`
and `transform`. Only the **fit set** differs: one 1393–1399 window instead of
two training folds.

That matters for the Final Test firewall too: the loader streams the
analysis-ready CSV and, for any key on the final-test denylist, skips the row
**without parsing a single value**. The firewall is a property of the code path,
not an assertion added afterwards.

## Preprocessing re-estimated on this fit set only

Clipping bounds (1st/99th percentile), medians of the clipped observed values,
and standardization mean/std were all re-estimated on the single 1393–1399 fit
set. **Nothing was carried over from a development fold** — the contract's
central requirement.

FC07 proves the ordering rather than asserting it: it recomputes the bounds and
the median-of-clipped-observed directly from the raw fit set and compares. If
imputation had preceded clipping, the medians would not match and the run would
have aborted.

## The four contracted outputs

| artifact | SHA-256 |
| --- | --- |
| `stage129_full_development_refit_model.json` | `48faab1ef186206508385713fb3b885a88a55bb072fb586d56e63d2777c97690` |
| `stage129_full_development_refit_preprocessing_parameters.json` | `862c65ec37082be1e3e95c29d2bf8873df9105e90cc43ce1ecac4fd8901ba9f6` |
| `stage129_full_development_refit_provenance_record.json` | `4b1aa9a6c85208713f250b5ac3fe71f56c4a8398c3834855926e29a43ad8f07d` |
| `stage129_full_development_refit_qc_report.json` | `e874ee5bdf2510f6c630f170482ca7a13f50ab73c7838550e9412c372c5ee63c` |

The fitted model is serialized as **explicit coefficients, not a pickle**. A
regularized logistic regression is fully determined by its intercept, its 18
coefficients and the preprocessing parameters recorded alongside it, so a JSON
artifact is exactly reproducible, diffable and auditable — and it keeps a binary
blob out of the repository.

## Determinism

`liblinear` + L2 is deterministic, and the frozen budget records
`logistic_regression_deterministic = true`. The call keeps the same shape as the
locked development module by passing `random_state = 20260719`, the first
already-locked final seed — **no new seed was introduced**.

Determinism was confirmed at zero extra cost: the dry run and the writing run
produced **byte-identical** artifact hashes. No second model was fitted to test
it, because FC12 permits exactly one fit.

## Fail-closed controls — all PASS

| control | result |
| --- | --- |
| FC01 input SHA-256 | PASS — 3 pinned inputs match |
| FC02 runtime match | PASS — python 3.13.5, scikit-learn 1.9.0, numpy 2.4.6, pandas 3.0.3, jdatetime 6.0.1, xgboost 3.3.0 |
| FC03 fit window | PASS — years 1393–1399, **zero** Final Test years, 666 rows, 68/598 events |
| FC04 feature matrix | PASS — `M1_PRIMARY_FEATURE_ORDER`, count 9, prohibited feature absent |
| FC05 hyperparameters | PASS — exact |
| FC06 missingness indicators | PASS — unstandardized binary 0/1 |
| FC07 clipping before imputation | PASS — bounds and medians recomputed and matched |
| FC08 no search | PASS — no tuning, grid expansion or early stopping |
| FC09 Final Test untouched | PASS — `final_test_rows_loaded == 0`, no value read |
| FC10 locked results intact | PASS — 4 locked artifacts byte-identical before and after |
| FC11 threshold | PASS — read from the development-OOF rule, not re-derived |
| FC12 exactly one fit | PASS — 1 |

Every control aborts the run on failure; there is no continue-on-error path.

## What was NOT done

No tuning, retuning or model re-selection; no feature or threshold search; no
bootstrap; no recalibration; no SHAP; no prediction generated; **no new
scientific metric, CI or p-value**; no Stage130. The Holm family is untouched
and still `HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE`. The locked primary
development results are byte-identical and are **not** replaced by this refit.

**The Final Test remains locked and unread** (`final_test_locked = true`,
`final_test_rows_read = 0`, `final_test_access_authorized = false`). Applying
this model to the Final Test is a separate step requiring **new explicit human
authorization**.

## متن فارسی

Refit یک‌باره مطابق قرارداد قفل‌شده PR #89 اجرا شد: دقیقاً **یک** مدل
(`M1 / regularized_logistic_regression / logistic__C_0.1`) و فقط روی پنجره
Development سال‌های **۱۳۹۳ تا ۱۳۹۹** با **۶۶۶** ردیف (۶۸ مثبت / ۵۹۸ منفی).

تمام آماره‌های وابسته به آموزش — کران‌های clipping، میانه‌ها و میانگین/انحراف
معیار استانداردسازی — فقط روی همین fit set دوباره برآورد شدند و هیچ آماره‌ای از
foldهای توسعه منتقل نشد.

هر دوازده کنترل `ABORT_REFIT` با موفقیت گذشت. چهار خروجی قراردادشده ساخته و
hash شدند. هیچ tuning، retuning، انتخاب مجدد مدل، feature search، threshold
search، bootstrap، recalibration، SHAP، Stage130 یا نتیجه علمی جدیدی تولید
نشد.

**هیچ ردیف، predictor، target، prediction یا metric مربوط به Final Test
(۱۴۰۰–۱۴۰۲) خوانده یا تولید نشد** و `final_test_rows_read = 0` باقی ماند.
دسترسی به Final Test نیازمند مجوز انسانی جداگانه است.

## Files

- `stage129_full_development_refit_model.json` — intercept and 18 coefficients.
- `stage129_full_development_refit_preprocessing_parameters.json` — fit-set
  clipping bounds, medians, standardization mean/std.
- `stage129_full_development_refit_provenance_record.json` — contract hash,
  input hashes, runtime, fit-set definition, pipeline module hash.
- `stage129_full_development_refit_qc_report.json` — FC01–FC12 results and the
  Final Test counters.
- `stage129_full_development_refit_execution_governance_boundary.json`.
- `metadata_and_hashes_stage129_full_development_refit_execution.json`.

Executor: `project/src/stage129_full_development_refit.py`.
Regression tests: `project/tests/test_stage129_full_development_refit_execution.py`.
