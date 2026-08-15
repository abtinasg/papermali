# Stage129 — threshold derivation algorithm, LOCKED (not executed)

**Action id:** `stage129-threshold-derivation-algorithm-contract-lock`
**Status:** `PROSPECTIVELY_LOCKED_NOT_EXECUTED`
**Result:** algorithm locked · `threshold_value = null` · **`PRE02` still unresolved**

This action locks *how* the development-OOF F2-maximizing threshold would be
computed. **It computes nothing.** No `predicted_probability` and no
`observed_target` value was read — only the pinned input's SHA-256, byte count
and header row. `final_test_rows_read = 0`.

## Why this contract exists, and why it is not a pure extraction

Its two predecessors could say `every_term_is_extracted_from_a_prelocked_artifact
= true`. **This one cannot, and says so.**

The audit behind the Final Test contract lock found that the frozen record fixes
the threshold **rule** (`development_OOF_F2_maximizing_threshold`) and the
**tie-break** (`higher_threshold`) — and then stops. It never defines the
candidate set, never states whether a probability equal to the threshold
predicts positive, and never gives beta or a formula for "F2". That gap was
recorded as `PRE02` rather than filled quietly.

A human supervisor has now supplied the missing pieces. Six terms are therefore
**decisions, not rules**, and the provenance record lists each one with the
reason it is untraceable. Recording that distinction is the whole point: a later
reader must not mistake a 2026 decision for a frozen 2025 rule.

| supplied term | value |
| --- | --- |
| candidate set | exactly the distinct stored `predicted_probability` values |
| comparison operator | `predicted_probability >= threshold` |
| objective | F2, beta = 2, `5*TP / (5*TP + 4*FN + FP)` |
| degenerate case | F2 = 0 when the denominator is 0 |
| numeric discipline | no rounding or truncation before selection |
| output precision | round-trip exact — `float(str(value)) == value` |

Eight further terms *are* extracted, each with its source key: the rule name,
the tie-break, `never_optimize_on_final_test`, the input surface, the selected
model, target-state semantics, the target years, and the runtime.

## The algorithm

Input is the pooled development-OOF surface, pinned by SHA-256, filtered to
`regularized_logistic_regression` / `logistic__C_0.1` — an expected **421** rows,
quoted from the primary development lock. Nothing else is an authorized input.

Candidates are **exactly** the distinct stored probabilities. No linear grid, no
synthetic `0.0`/`1.0` endpoints, no midpoints between consecutive values, no
thinning. Each candidate is scored by `5*TP / (5*TP + 4*FN + FP)` over evaluable
rows only, with missing targets never counted as negative. The maximum F2 wins;
**among ties the LARGEST threshold wins**, verified against the full argmax set
rather than inferred from scan order.

No model is loaded and none is fitted. The derivation reads stored predictions.

## `project/src/metrics.py::pick_threshold` is explicitly forbidden

It is the only threshold routine in the repository and it may not be used:

- it is referenced by **zero** merged contracts and is **not imported** by the
  locked development pipeline;
- its candidate set is a 200-point linear grid unioned with the observed
  probabilities *and* synthetic `0.0`/`1.0` endpoints — none of which any
  contract fixes, and `grid_points` is a default argument, not a contract term;
- its ascending scan with `v > best_v` keeps the **first** maximizing candidate,
  which is the **lowest** — directly contradicting the locked `higher_threshold`
  tie-break.

Using it would have violated the very rule it appears to implement. `TD09`
turns that into a fail-closed control.

## Eighteen fail-closed controls — every one `ABORT_THRESHOLD_DERIVATION`

`TD01` input hash and byte count · `TD02` row filter and the 421-row count ·
`TD03` **development years only, zero Final Test rows** · `TD04` **candidate set
is exactly the unique stored probabilities** · `TD05` `>=` and never strict `>` ·
`TD06` the closed-form F2 with the zero-denominator convention · `TD07` **no
rounding or truncation before selection** · `TD08` **largest threshold among the
full argmax set** · `TD09` `pick_threshold` neither imported nor called ·
`TD10` exactly one threshold, no sensitivity alternatives · `TD11`
`model_fits_executed == 0`, no `predict_proba` · `TD12` missing never negative ·
`TD13` locked development results byte-identical · `TD14` **round-trip-exact
recorded value** · `TD15` runtime match · `TD16` `final_test_rows_read == 0` ·
`TD17` writes nothing outside its package · `TD18` no recalibration, bootstrap,
SHAP, p-value or re-selection.

## This does NOT resolve `PRE02`

`PRE02` requires the threshold **value** to exist in a committed artifact.
Defining how a number would be produced is not producing it.

```
PRE01 = UNRESOLVED
PRE02 = UNRESOLVED
final_test_contract_fully_executable = false
final_test_access_authorized         = false
final_test_rows_read                 = 0
```

The Final Test contract is unchanged by this action.

## What was NOT done

No threshold derived or materialized (`threshold_value = null`). No probability
value read. No model fit, refit, load or `predict_proba` call. No recalibration,
tuning, model re-selection, bootstrap, SHAP, p-value or confidence interval. No
new scientific result. No Stage130 — `stage130_started = false`. No Final Test
access of any kind.

The pointer is `human_authorization_required_for_threshold_derivation_execution`
with `authorized = false` — a locked algorithm is never an execution permission.

## متن فارسی

این اقدام فقط **الگوریتم** استخراج threshold را قفل می‌کند و **هیچ محاسبه‌ای
انجام نمی‌دهد**. هیچ مقدار `predicted_probability` یا `observed_target` خوانده
نشد؛ تنها SHA-256، حجم و سطر header ورودی پین‌شده خوانده شد و
`final_test_rows_read = 0` باقی ماند.

برخلاف دو قرارداد قبلی، این قرارداد **استخراج محض نیست** و همین را صریح ثبت
می‌کند: رکورد منجمد فقط قاعده و tie-break را داشت و مجموعه candidateها، عملگر
مقایسه و فرمول F2 را تعریف نکرده بود. این شکاف پیش‌تر به‌عنوان `PRE02` گزارش شد
و اکنون **شش ترم** توسط تصمیم انسانی تأمین شده است. این شش ترم در provenance
جداگانه فهرست شده‌اند تا خواننده‌ای در آینده یک تصمیم را با یک قاعدهٔ منجمد
اشتباه نگیرد.

ورودی مجاز فقط pooled Development OOF مربوط به `logistic__C_0.1` است؛ مجموعه
candidateها دقیقاً همان probabilityهای یکتای ذخیره‌شده؛ پیش‌بینی مثبت با
`probability >= threshold`؛ معیار `5TP / (5TP + 4FN + FP)` با قرارداد صفر برای
مخرج صفر؛ بیشترین F2 و در تساوی **بزرگ‌ترین** threshold. هیچ roundingی پیش از
انتخاب مجاز نیست و مقدار نهایی باید round-trip دقیق ثبت شود. تابع
`metrics.py::pick_threshold` صریحاً **غیرمجاز** است، چون با tie-break قفل‌شده
تناقض دارد و در هیچ قرارداد Merge‌شده‌ای پین نشده.

**این اقدام `PRE02` را حل نمی‌کند.** `PRE02` وجود *مقدار* را در یک artifact
کامیت‌شده می‌طلبد و اینجا هیچ مقداری تولید نشد؛ بنابراین `PRE01` و `PRE02` هر دو
حل‌نشده می‌مانند و
`final_test_contract_fully_executable = false` باقی است. اجرای استخراج نیازمند
مجوز انسانی جداگانه است.

## Files

- `stage129_threshold_derivation_algorithm_contract.json` — the locked algorithm and TD01–TD18.
- `stage129_threshold_derivation_algorithm_governance_boundary.json` — counters and boundary flags.
- `stage129_threshold_derivation_algorithm_source_provenance.json` — 9 pinned sources and the 6 human-supplied terms.
- `metadata_and_hashes_stage129_threshold_derivation_algorithm_contract_lock.json`.

Regression tests: `project/tests/test_stage129_threshold_derivation_algorithm_contract_lock.py`.
