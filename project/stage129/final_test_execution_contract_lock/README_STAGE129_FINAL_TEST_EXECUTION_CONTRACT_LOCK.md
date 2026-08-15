# Stage129 — Final Test execution contract, LOCKED (not executed)

**Action id:** `stage129-final-test-execution-contract-lock`
**Status:** `PROSPECTIVELY_LOCKED_NOT_EXECUTED`
**Result:** contract locked · `final_test_rows_read = 0` · **two prerequisites unsatisfied**

This action is a **read-only audit over already-committed artifacts**. It records
what a future, separately authorized Final Test execution would be permitted to
do. **No Final Test row, predictor, target or prediction for target years
۱۴۰۰–۱۴۰۲ was read, loaded or produced.** No model was fitted, no metric
computed, no threshold derived.

Locking a contract is not permission to execute it.

## What the contract accepts — and nothing else

The contract accepts exactly one model and exactly four artifacts. Everything
else fails closed.

| field | value |
| --- | --- |
| block / algorithm | `M1` / `regularized_logistic_regression` |
| configuration | `logistic__C_0.1` |
| hyperparameters | `C=0.1`, `penalty=l2`, `solver=liblinear`, `max_iter=5000`, `class_weight=balanced` |
| selection basis | `HUMAN_DECISION_BASED_ON_PRELOCKED_DEVELOPMENT_EVIDENCE` |
| model source | the merged Full-Development Refit (PR #90) |

The four accepted artifacts are pinned by SHA-256:

| artifact | SHA-256 |
| --- | --- |
| `stage129_full_development_refit_model.json` | `48faab1ef186206508385713fb3b885a88a55bb072fb586d56e63d2777c97690` |
| `stage129_full_development_refit_preprocessing_parameters.json` | `862c65ec37082be1e3e95c29d2bf8873df9105e90cc43ce1ecac4fd8901ba9f6` |
| `stage129_full_development_refit_provenance_record.json` | `4b1aa9a6c85208713f250b5ac3fe71f56c4a8398c3834855926e29a43ad8f07d` |
| `stage129_full_development_refit_qc_report.json` | `e874ee5bdf2510f6c630f170482ca7a13f50ab73c7838550e9412c372c5ee63c` |

`FT01` re-hashes all four. A drifted artifact aborts before any Final Test row
is touched. Random forest and XGBoost are **not accepted as input** — which is a
scope statement about this contract, not a claim that either is statistically
inferior; both keep `NOT_SELECTED_BY_HUMAN_DECISION_ONLY`.

## The model is applied, never refitted

The single most important structural term: **`model_fits_executed = 0`.**

The fitted model already exists as explicit intercept and 18 coefficients. A
Final Test execution reconstructs it from those numbers and performs one forward
pass. It never calls `fit`, never partially updates, and never re-estimates a
preprocessing statistic.

That is why the frozen eight-step pipeline appears here as **six** steps. The
three estimation steps — clipping-bound estimation, median estimation, and the
mean/std half of standardization — are already fixed by the refit and are
removed, not replaced. No step is added and no step is reordered.

The one asymmetry is deliberate and is drawn verbatim from the frozen
preprocessing contract: **the Final Test missingness mask comes from the Final
Test rows' own original pre-imputation positions**, while the imputation *value*
comes from the refit fit set. Reading which of a row's own fields are blank is
not estimating a statistic on the Final Test.

## The threshold gap — the substantive thing this audit had to resolve

The frozen metrics contract fixes the operating-threshold **rule**
(`development_OOF_F2_maximizing_threshold`) and its **tie-break**
(`higher_threshold`). It does not contain the resulting number.

**No committed artifact anywhere in the repository contains that number. It was
never computed.** All 17 pinned sources were searched. The development metrics
CSV has no threshold column; the only other `threshold_value` keys in the
repository belong to unrelated Stage125 data-quality gates.

This contract does **not** compute it. Deriving it would be a new derived
quantity, and no authorization for that exists. Instead the gap is recorded as
an unsatisfied prerequisite `PRE02`, the derivation inputs are pinned for
whoever is later authorized to do it, and `FT10` blocks every thresholded output
until a committed value exists.

One tempting inference is explicitly **blocked**. `Recall@10%` and `Lift@10%`
are **top-K** metrics, defined by `K_y = ceil(0.10 * N_y)`, so they do not need
the F2 threshold. That is a statement about arithmetic, **not a permission**. It
does not license opening the Final Test early to collect whichever metrics
happen to be computable today.

`PRE02` therefore has exactly one resolution: the value is computed and
committed under its own human authorization. A threshold-free run is **not** an
alternative route, and `FT21` aborts any partial, threshold-free or
metric-subset execution. **The Final Test is opened once, after every
prerequisite is resolved — never in stages.**

Deriving the threshold requires **zero** Final Test rows: it is a
development-only OOF computation. It is unauthorized here because it is a new
scientific result, not because it would touch the Final Test. It needs its own
separate human authorization.

## Metrics, uncertainty and inference are locked before any access

The metric set is **closed**: primary `PR-AUC`; secondary `ROC-AUC`,
`Brier_score`, `Recall@10%`, `Lift@10%`. Adding a metric after seeing results,
substituting one, or changing which is primary are all unauthorized.

Bootstrap parameters are locked in advance — `paired_company_cluster_bootstrap`,
clustered on `ticker`, 2000 replicates, minimum 1000 valid, percentile-95
intervals, seed `20260724` — and **executing** the bootstrap is still not
authorized by this contract. The contract also records, without changing any
frozen parameter, that the expected Final Test positive count is **12**, so any
interval computed on it would be wide.

**No inference.** `confirmatory_family_1` was never executed. Evaluating one
model on the Final Test is a reporting act: it produces no p-value, closes no
Holm family, and establishes no superiority. The family may not be shrunk or
redefined post hoc, and Final Test results may never reopen model selection —
`do_not_select_winner_on_calibrated_final_test` is carried through verbatim.

Primary probabilities stay **raw**. Isotonic is unauthorized; Platt is optional,
may only ever be fit on pooled development OOF, and executing it is not
authorized here. The frozen `skip_recalibration_if_oof_positives_lt: 20` rule
does not trigger, because the selected model has **35** pooled development-OOF
positives.

## Twenty-one fail-closed controls — every one `ABORT_FINAL_TEST`

`FT01` accepted artifact hashes · `FT02` model identity · `FT03` runtime match ·
`FT04` input hashes · `FT05` **only target years ۱۴۰۰–۱۴۰۲, zero development
rows** · `FT06` design matrix exact · `FT07` **no preprocessing statistic
re-estimated on Final Test** · `FT08` masks from the rows' own original
positions · `FT09` **`model_fits_executed == 0`** · `FT10` threshold read from a
committed artifact or thresholded outputs not produced · `FT11` **exactly one
pass** · `FT12` no recalibration · `FT13` no re-selection, no winner ·
`FT14` locked development results byte-identical · `FT15` no search of any kind ·
`FT16` missing never counted as negative · `FT17` closed metric set, `K` not
optimized after results · `FT18` no Holm, no p-value · `FT19` bootstrap
parameters unchanged or zero executions · `FT20` writes nothing outside its own
package · `FT21` **every prerequisite resolved first, and no partial,
threshold-free or staged opening**.

Note the direction of `FT05`. In the refit contract, `FC03` required **zero
Final Test years**. Here the window is the mirror image — only ۱۴۰۰–۱۴۰۲, and
zero development rows — because evaluating on development data would silently
report an in-sample result.

## Prerequisites — two unsatisfied

| id | requirement | satisfied |
| --- | --- | --- |
| `PRE01` | a new explicit human authorization for Final Test access exists | **no** |
| `PRE02` | the F2 threshold value exists in a committed artifact, produced by a separately authorized development-only computation | **no** |
| `PRE03` | the four accepted refit artifacts are merged on main and hash to their pinned values | yes |
| `PRE04` | the runtime matches the locked development runtime exactly | yes |

Because two are unresolved, the contract publishes its executability directly
rather than making a reader infer it:

```
final_test_contract_fully_executable = false   (blocked by PRE01, PRE02)
final_test_execution_authorized      = false
final_test_access_authorized         = false
final_test_rows_read                 = 0
```

## What was NOT done

No Final Test execution. No fit, refit or second fit. No prediction, no metric,
no confidence interval, no p-value. No recalibration, no isotonic, no Platt. No
tuning, retuning, model re-selection, feature search or threshold search. No
SHAP. No Holm execution. No threshold materialized. No Stage130 —
`stage130_started = false`. The Holm family is untouched at
`HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE`, and the locked primary
development results are unmodified.

**The Final Test remains locked and unread** (`final_test_locked = true`,
`final_test_rows_read = 0`, `final_test_access_authorized = false`). The pointer
is `human_authorization_required_for_final_test_execution` with
`authorized = false` — a pointer is never an authorization.

## متن فارسی

این اقدام یک **ممیزی read-only روی artifactهای از پیش commit‌شده** است و
قرارداد اجرای یک‌باره Final Test را فقط **قفل** می‌کند. **هیچ ردیف، predictor،
target یا prediction مربوط به سال‌های ۱۴۰۰ تا ۱۴۰۲ خوانده، بارگذاری یا تولید
نشد** و `final_test_rows_read = 0` باقی ماند.

قرارداد فقط مدل انتخاب‌شده `M1 / regularized_logistic_regression /
logistic__C_0.1` و چهار artifact قفل‌شده Full-Development Refit را می‌پذیرد؛ هر
چهار artifact با SHA-256 پین شده‌اند و کنترل `FT01` آن‌ها را دوباره hash می‌کند.

مدل فقط **اعمال** می‌شود و هرگز دوباره fit نمی‌شود: `model_fits_executed = 0`.
تمام آماره‌های پیش‌پردازش از همان fit set قفل‌شده می‌آیند و هیچ آماره‌ای روی
Final Test برآورد نمی‌شود؛ فقط ماسک missing از موقعیت‌های خالیِ خودِ ردیف‌های
Final Test خوانده می‌شود که برآورد آماره نیست.

**شکاف threshold:** قاعده و tie-break قفل‌اند، اما مقدار عددی آن **هرگز محاسبه
نشده** و در هیچ artifactی وجود ندارد. این قرارداد آن را محاسبه نمی‌کند و از
OOF predictions هم استخراج نمی‌کند؛ استخراج آن یک محاسبه علمی Development-only
جداگانه و نیازمند مجوز انسانی مستقل است. این شکاف به‌عنوان پیش‌نیاز حل‌نشده
`PRE02` ثبت شده است.

معیارهای `Recall@10%` و `Lift@10%` بر پایه top-K هستند و از نظر ریاضی به این
مقدار وابسته نیستند، اما **این یک مجوز نیست**: هیچ اجرای جزئی یا threshold-free
روی Final Test مجاز نیست و کنترل `FT21` چنین اجرایی را متوقف می‌کند. Final Test
فقط **یک‌بار** و **پس از حل همه پیش‌نیازها** باز می‌شود و هرگز مرحله‌به‌مرحله
باز نمی‌شود.

تا زمانی که `PRE02` حل نشده است:
`final_test_contract_fully_executable = false`،
`final_test_execution_authorized = false`،
`final_test_access_authorized = false` و `final_test_rows_read = 0`.

معیارها، threshold، خروجی‌ها، شمارنده‌ها و بیست کنترل `ABORT_FINAL_TEST` همگی
**پیش از هر دسترسی** قفل شدند. هیچ fit دوم، recalibration، refit، tuning، Holm،
p-value، انتخاب مجدد مدل، Stage130 یا نتیجه علمی جدیدی تولید نشد. اجرای Final
Test نیازمند مجوز انسانی صریح و جداگانه است.

## Files

- `stage129_final_test_execution_contract.json` — the locked contract.
- `stage129_final_test_execution_governance_boundary.json` — counters and boundary flags.
- `stage129_final_test_execution_source_provenance.json` — 17 pinned sources.
- `metadata_and_hashes_stage129_final_test_execution_contract_lock.json`.

Regression tests: `project/tests/test_stage129_final_test_execution_contract_lock.py`.
