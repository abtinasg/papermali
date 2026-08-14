# Stage129 — Full-Development Refit contract lock (audit only)

**Action id:** `stage129-full-development-refit-contract-lock`
**Status:** `PROSPECTIVELY_LOCKED_NOT_EXECUTED`
**Type:** audit of the pre-locked contracts + a prospective refit contract. **No fit, no execution, no Final Test.**

This package answers one question: *if the full-development refit of the selected
model were authorized, exactly what would it be allowed to do?* Every term below
is **extracted** from an already-frozen artifact — nothing is invented here
(`no_term_invented_by_this_action = true`), and each term carries the file and
key it came from.

## The model this contract is for

| field | value | source |
| --- | --- | --- |
| block | `M1` | selection decision |
| algorithm | `regularized_logistic_regression` | selection decision |
| configuration | `logistic__C_0.1` | retained design freeze |
| hyperparameters | `C=0.1`, `penalty=l2`, `solver=liblinear`, `max_iter=5000` | retained design freeze |
| class weight | `balanced` | model specifications |

Retuning, hyperparameter search and grid expansion are all **unauthorized**.

## Authorized development data

- Sample `main_rule_a_primary`, target `FD_target_main_t_plus_1`.
- `analysis_ready_main_rule_a_stage125.csv`, SHA-256 pinned to
  `4d04d7d2…d64f` (and the audited-pairs file alongside it).
- **Fit target years `1393–1399`** — taken directly from the frozen
  preprocessing contract's own `final_development_refit.fit_years`.
- Split variable `target_year`; random split and shuffle both unauthorized.

## The one substantive thing this audit had to resolve

The frozen preprocessing contract sets
`fit_scope = each_temporal_training_fold_separately`. That is a **development**
statement — it describes the two-fold cross-validation, where every
training-derived statistic is estimated inside each fold.

A full-development refit has no folds. So the contract records the fit scope
explicitly as **the single 1393–1399 development window**, with every
training-derived statistic — clipping bounds, medians, standardization mean/std
— re-estimated on that one fit set, and **no statistic carried over from any
fold**. This is not a new rule: it is the same
`final_development_refit.fit_years` block of the frozen contract, applied
consistently. It is called out here because reusing fold-level statistics would
be the easiest way to silently break the pipeline.

## Preprocessing and missing handling

The eight-step continuous pipeline is reproduced verbatim from the frozen
contract. The parts that matter most, and the order they must happen in:

1. capture the **original pre-imputation missingness mask** — never infer it
   from the imputed matrix;
2. estimate 1st/99th percentile clipping bounds on **observed fit-set values
   only**, *before* median imputation;
3. apply clipping, then estimate the fit-set median on the clipped observed
   values, then impute;
4. append missingness indicators from the original mask, **unstandardized
   binary 0/1**;
5. standardize the imputed continuous features (logistic only) using fit-set
   mean/std.

Target states are exact: `1` positive, `0` negative, anything else missing, and
**missing is never counted as negative**.

## Threshold

Rule `development_OOF_F2_maximizing_threshold`, tie-break `higher_threshold`.

This is a **development-OOF quantity**. The contract records explicitly that it
is *not* re-derived from the refit model's own in-sample predictions and is
never optimized on the Final Test.

## Seeds and determinism

The frozen budget records `logistic_regression_deterministic = true`, and the
five-seed probability-averaging rule is scoped to random forest and XGBoost
(`final_rf_xgb_probability`). **The selected logistic configuration therefore
needs no fit seed and no seed averaging.** The locked seeds and the bootstrap
seed `20260724` are recorded for reference only; introducing any new seed is
unauthorized.

## Environment

Must match the locked development runtime **exactly**:

```
python 3.13.5 · scikit-learn 1.9.0 · numpy 2.4.6 · pandas 3.0.3 · jdatetime 6.0.1 · xgboost 3.3.0
```

Mismatch ⇒ `FAIL_CLOSED_DO_NOT_REFIT`. (XGBoost is pinned because it is part of
the locked environment, not because this model uses it.)

## Calibration

Primary probabilities stay **raw and uncalibrated**. Isotonic is unauthorized.
Platt is optional, secondary, and may only ever be fit on pooled development OOF
predictions. The frozen skip rule (`skip_recalibration_if_oof_positives_lt: 20`)
does **not** trigger: the selected model has **35** pooled development-OOF
positives, quoted from the committed metrics artifact. Executing recalibration
is still not authorized by this contract.

## Expected outputs — none of which exists yet

A future, separately authorized execution is expected to produce: the fitted
model artifact, its fit-set preprocessing parameters, a provenance record
(input hashes, runtime versions, row/event counts, fit-set definition) and a QC
report covering every fail-closed control. **All four are `exists_now: false`.**

Forbidden outputs include any Final Test prediction or metric, any new
hyperparameter-search result, any recalibrated *primary* probability, and any
new development metric that would replace the locked primary results — which
this refit explicitly does **not** replace.

## Fail-closed controls (FC01–FC12)

Every one aborts the refit on failure. In short: input hashes match; runtime
matches; fit set contains **zero** rows with `target_year` in 1400–1402; feature
matrix equals `M1_PRIMARY_FEATURE_ORDER` exactly in order, count 9;
hyperparameters exact; mask captured before imputation; clipping before
imputation; no search/expansion/early-stopping; **`final_test_rows_loaded == 0`**;
locked primary results byte-identical before and after; threshold read from the
development-OOF rule; and **exactly one model fitted**.

## Final Test boundary

Final Test target years `1400–1402` stay **locked, unread and unauthorized**
(`final_test_rows_read = 0`). The refit may not read, predict on, or evaluate
against them. The frozen contract's `apply_once_to_locked_final_test` is
acknowledged as a **future, separately authorized step** — recording it here is
not permission to take it. The expected final-test counts (346 / 12 / 334) are
quoted as frozen metadata from the temporal split contract; no row-level access
occurred.

## متن فارسی

این بسته فقط **ممیزی و قفل‌کردن قرارداد** Full-Development Refit برای مدل منتخب
`M1 / regularized_logistic_regression / logistic__C_0.1` است. تمام بندهای
قرارداد از artifactهای ازپیش‌قفل‌شده **استخراج** شده‌اند و هیچ بندی در این مرحله
ساخته نشده است؛ برای هر بند مسیر فایل و کلید مرجع ثبت شده است.

داده مجاز، پنجره برازش `۱۳۹۳–۱۳۹۹`، ویژگی‌ها، ترتیب هشت‌مرحله‌ای preprocessing،
مدیریت missing، threshold مبتنی بر OOF توسعه، seed و نسخه محیط، خروجی‌های
مورد انتظار، دوازده کنترل fail-closed و مرزهای Final Test همگی ثبت شده‌اند.

**هیچ برازشی انجام نشده است.** اجرای واقعی refit، انتخاب مجدد مدل، Stage130 و
دسترسی به Final Test هیچ‌کدام با این قرارداد مجاز نمی‌شوند و نیازمند **مجوز
انسانی جداگانه** هستند. Final Test همچنان قفل و خوانده‌نشده است
(`final_test_rows_read = 0`).

## What this contract does NOT authorize

Executing the refit; fitting or predicting with any model; tuning, retuning or
re-selecting the model or configuration; feature or threshold search; bootstrap;
calibration; SHAP; any new metric, CI or p-value; row-level scientific data
reads for analysis; Final Test access or unlock; Stage130. Every counter in the
governance boundary is `0`, including `full_development_refits_executed`.

`refit_execution_requires_new_explicit_human_authorization = true`. The pointer
is `human_authorization_required_for_full_development_refit_execution` with
`authorized = false` — a pointer is never an authorization.

## Files

- `stage129_full_development_refit_contract.json` — the contract itself.
- `stage129_full_development_refit_source_provenance.json` — SHA-256 of all 12
  artifacts every term was extracted from.
- `stage129_full_development_refit_governance_boundary.json` — what stays shut.
- `metadata_and_hashes_stage129_full_development_refit_contract_lock.json`.

Regression tests:
`project/tests/test_stage129_full_development_refit_contract_lock.py`.
