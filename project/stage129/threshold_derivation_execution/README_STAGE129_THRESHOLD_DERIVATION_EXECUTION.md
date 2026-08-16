# Stage129 — threshold derivation COMPUTED, RESULT NOT ADMITTED

**Action id:** `stage129-threshold-derivation-execution`
**Contracts:** `stage129_threshold_derivation_algorithm_contract` (PR #92) and `stage129_predicted_probability_parse_rule_contract` (PR #93)
**Attempt status:** `COMPUTATION_COMPLETED_RESULT_NOT_ADMITTED_PP08_NOT_EXECUTED`
**Result:** **29 of 30** contractual controls PASS · **`PP08` NOT_EXECUTED** · **0 thresholds admitted** · `final_test_rows_read = 0`

> **The computed number below is NOT admitted.** It is retained for audit
> history only. It is **not** canonical, **not** authorized, **not** operational,
> and may **not** be applied to the Final Test. `PRE02` remains **UNRESOLVED**.

This is the second attempt. The first, recorded in PR #93, aborted on the
serialization defect. That record is preserved verbatim and is **not** rewritten.

**No Final Test row, predictor, target, prediction or metric was read or
produced.** No model was loaded, fitted or refitted.

## The computed result — retained for audit, not admitted

| field | value |
| --- | --- |
| computed threshold | `0.426878838687` |
| F2 at that threshold | `0.5916030534351145` |
| TP / FP / FN | 31 / 91 / 4 |
| argmax members | 1 |
| unique candidates | 421 |
| evaluable rows | 421 of 421 selected |
| positives / negatives | 35 / 386 |
| **admission status** | **`COMPUTED_BUT_NOT_ADMITTED_QC_INCOMPLETE`** |
| **thresholds admitted** | **0** |

`5 × 31 / (5 × 31 + 4 × 4 + 91) = 155 / 262 = 0.5916030534351145`, recomputed
from the recorded confusion counts.

These numbers are preserved so the audit trail is complete and nothing is
hidden. **No scientific or operational claim may be built on them.** They are
not a development operating point, not evidence of model superiority, not a test
statistic, and carry no inference. A threshold becomes usable only from a
derivation whose contractual QC is complete.

## Why the result is not admitted

`PP08` requires two things: that conversion yields IEEE-754 binary64, **and**
that `numpy.float64(group) == float(group)` for **every parsed token** in the
locked runtime.

Clause (a) was **performed**. Clause (b) was **not** — the executor never
imported numpy and never compared the two constructors over the 421 tokens. The
entry was nevertheless recorded `PASS`, which was inaccurate. It now reads
`NOT_EXECUTED`, with both clauses stated separately and the original `PASS`
disclosed.

Two things this is *not*:

- It is **not** a conversion nonconformity. The merged parse contract permits
  either constructor — `conversion.equivalent_to_python_float_on_the_captured_group
  = true`, and its `equivalent_note` reads "a conforming implementation may use
  either, and a control re-checks agreement". Using `float()` was allowed; what
  is missing is the re-check the same sentence promises.
- It is **not** repaired by the 14-literal agreement spot-check performed during
  review. Representative literals are not the 421 real tokens the control names.

**No later edit can make `PP08` have run.** The executor was not rewritten to
paper over this, and the QC entry states plainly what the past run actually did.

## Controls: 30 contractual, plus one supplementary check

| outcome | count | ids |
| --- | --- | --- |
| PASS | **29** | all except `PP08` |
| FAIL | **0** | — |
| **NOT_EXECUTED** | **1** | **`PP08`** |

`all_contractual_controls_passed = false`.

`TD01`–`TD18` and `PP01`–`PP12` are the 30 contractual controls. The executor
additionally recorded one observation about parse scope; it is **not** a
contracted control, so it is carried separately as `SUP01` with a non-`TD`/`PP`
identifier and `classification: SUPPLEMENTARY_QC_CHECK`. An earlier version
counted "31 controls" by conflating the two — a reporting error, corrected
without repeating the derivation.

## Exactly one run

The contract permits one execution. There was **no computational dry run** and
**no second run to demonstrate determinism** — the executor refuses to start
without `--write` precisely so a "harmless" dry run cannot happen by reflex.

Verification was therefore from the **written bytes and their hashes**, and by
recomputing F2 from the recorded confusion counts, never by repeating the
derivation.

## Row selection precedes parsing

1263 rows were read; 421 survived the `regularized_logistic_regression` /
`logistic__C_0.1` filter; all 421 had a valid target and were evaluable. **Only
those 421 probability tokens were parsed.** The other 842 rows' tokens were
never converted to numbers.

Every token was ASCII-checked, then matched with an anchored `fullmatch` against

```
^np\.float64\((?P<decimal>[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\)$
```

No `eval`, no `exec`, no `ast.literal_eval`, no general parser. 421 tokens read,
421 parsed — none skipped, defaulted or imputed.

## The sweep and the tie-break

Candidates are exactly the 421 distinct parsed values: no grid, no synthetic
endpoints, no midpoints, no thinning, no rounding or truncation anywhere before
selection. A row is predicted positive when `predicted_probability >= threshold`;
strict `>` is never used. Missing targets are never counted as negative.

F2 uses the binding closed form `5*TP / (5*TP + 4*FN + FP)` on integer counts,
with `F2 = 0` on a zero denominator. `metrics.py::pick_threshold` is neither
imported nor called.

The maximum F2 was computed first, every candidate attaining it was collected
into an **explicit argmax set**, `max()` was taken over that set, and a
post-check re-asserted no member exceeds the selection.

## Counters — action-specific and cumulative, kept separate

The PR #93 abort record is preserved verbatim; its counters are not rewritten.

| this action | value |
| --- | --- |
| attempts started | 1 |
| **computations completed but not admitted** | **1** |
| **attempts succeeded (admitted)** | **0** |
| thresholds computed | 1 |
| **thresholds admitted** | **0** |
| probability tokens parsed | 421 |
| fits, refits, `predict_proba`, tuning, recalibration, bootstrap, SHAP, p-values, sensitivity analyses, model re-selections | 0 |
| `final_test_rows_read` | 0 |

| cumulative | value |
| --- | --- |
| **total attempts started** | **2** |
| aborted attempts | **1** |
| computations completed but not admitted | **1** |
| **admitted derivations** | **0** |
| thresholds computed | 1 |
| **thresholds admitted** | **0** |

`stage129_threshold_value_materialized` is deliberately split: a numeric file
**was** written (1); a governance-admitted threshold **was not** (0).

## What this unblocks — nothing

`PRE02` is **UNRESOLVED**. A committed numeric file is not a resolved
prerequisite when the derivation that produced it has an unexecuted contractual
control.

```
PRE01 = UNRESOLVED          PRE02 = UNRESOLVED
final_test_contract_fully_executable = false
final_test_access_authorized         = false
final_test_execution_authorized      = false
final_test_rows_read                 = 0
final_test_locked                    = true
stage130_started                     = false
```

## The frozen file did not move

`stage126_m1_development_oof_predictions.csv` is byte-identical at
`48a00c88…3326749`, verified before and after the run. No cleaned or normalised
copy was created. The three locked development results are byte-identical.

## متن فارسی

محاسبه تا انتها اجرا شد، اما **نتیجه پذیرفته نشد**. وضعیت تلاش:
`COMPUTATION_COMPLETED_RESULT_NOT_ADMITTED_PP08_NOT_EXECUTED`.

**علت:** کنترل قراردادی `PP08` دو بند دارد — تبدیل به IEEE-754 binary64، و
بررسی برابری `numpy.float64(group) == float(group)` برای **تمام** توکن‌ها. بند
اول انجام شد؛ **بند دوم اجرا نشد** (executor اصلاً numpy را import نکرد). این
مورد ابتدا اشتباهاً `PASS` ثبت شده بود و اکنون `NOT_EXECUTED` است.

این یک **نقص در اجرای کنترل** است، نه نقض تبدیل عددی: قرارداد Merge‌شده صراحتاً
هر دو سازنده را مجاز می‌داند
(`equivalent_to_python_float_on_the_captured_group = true` و توضیح آن: «a
conforming implementation may use either, and a control re-checks agreement»).
بررسی ۱۴ literal نماینده هم جایگزین کنترل الزام‌شده روی ۴۲۱ توکن واقعی نیست، و
**هیچ ویرایش پسینی نمی‌تواند `PP08` را اجراشده جلوه دهد**.

عدد محاسبه‌شدهٔ `0.426878838687` حذف یا پنهان نشده و صرفاً برای **تاریخچهٔ
حسابرسی** نگهداری می‌شود: **canonical، authorized یا operational نیست** و برای
Final Test قابل استفاده نیست. هیچ ادعای علمی یا عملیاتی بر پایهٔ آن مجاز نیست.

شمارنده‌ها: کل تلاش‌های آغازشده **۲** (یک Abort، یک محاسبهٔ کامل ولی
پذیرفته‌نشده)، threshold محاسبه‌شده **۱**، threshold **پذیرفته‌شده صفر**. رکورد
Abort تلاش اول دست‌نخورده است.

`PRE01` و `PRE02` هر دو **unresolved** می‌مانند و تمام قفل‌های Final Test و
Stage130 بسته باقی می‌مانند.

## Files

- `stage129_threshold_value.json` — the computed (not admitted) threshold, its F2 and confusion counts.
- `stage129_threshold_derivation_provenance_record.json` — contract hashes, input hash, counts, parse regex, runtime, and the PP08 conformity note.
- `stage129_threshold_derivation_qc_report.json` — the 30 contractual controls with PP08 as `NOT_EXECUTED`, the `SUP01` supplementary check, the tie-break proof, action and cumulative counters.
- `metadata_and_hashes_stage129_threshold_derivation_execution.json`.

Executor: `project/src/stage129_threshold_derivation.py`.
Regression tests: `project/tests/test_stage129_threshold_derivation_execution.py`.
