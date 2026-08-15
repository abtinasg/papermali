# Stage129 — threshold derivation EXECUTED (development only)

**Action id:** `stage129-threshold-derivation-execution`
**Contracts executed:** `stage129_threshold_derivation_algorithm_contract` (PR #92) and `stage129_predicted_probability_parse_rule_contract` (PR #93)
**Result:** all **30** contractual controls PASS (+1 supplementary check) · exactly **1** threshold selected · `final_test_rows_read = 0`

This is the second attempt. The first, recorded in PR #93, aborted on the
serialization defect. That record is preserved verbatim and is **not** rewritten.

**No Final Test row, predictor, target, prediction or metric was read or
produced.** No model was loaded, fitted or refitted.

## The result

| field | value |
| --- | --- |
| **threshold** | **`0.426878838687`** |
| F2 at threshold | `0.5916030534351145` |
| TP / FP / FN | 31 / 91 / 4 |
| argmax members | **1** — tie-break not needed |
| unique candidates | 421 |
| evaluable rows | 421 of 421 selected |
| positives / negatives | 35 / 386 |

The 35 pooled development-OOF positives match the figure quoted in the frozen
calibration clause, an independent consistency check on the row selection.

`5 × 31 / (5 × 31 + 4 × 4 + 91) = 155 / 262 = 0.5916030534351145`, recomputed
from the recorded confusion counts and equal to the recorded F2.

**This is a development operating point, nothing more.** It is not evidence of
model superiority, not a test statistic, and carries no inference. It exists so
a future, separately authorized evaluation has a threshold to apply.

## Controls: 30 contractual, plus one supplementary check

`TD01`–`TD18` and `PP01`–`PP12` are the **30** contractual controls and all
PASS. The executor additionally recorded one observation about parse scope. It
is **not** a contracted control, so it is carried separately as `SUP01` with a
non-`TD`/`PP` identifier and `classification: SUPPLEMENTARY_QC_CHECK`.

An earlier version of this package reported "31 controls" by counting the
supplementary check among the contractual ones. That was a reporting error and
is corrected here **without repeating the derivation** — the threshold, its F2
and the confusion counts are untouched.

## Exactly one run

The contract permits one execution. There was **no computational dry run** and
**no second run to demonstrate determinism** — the executor refuses to start
without `--write` precisely so a "harmless" dry run cannot happen by reflex.

Artifact correctness was therefore established from the **written bytes and
their hashes**, and by recomputing F2 from the recorded confusion counts, rather
than by repeating the derivation.

## Row selection precedes parsing

Order matters here and the contract fixes it. 1263 rows were read; 421 survived
the `regularized_logistic_regression` / `logistic__C_0.1` filter; all 421 had a
valid target and were evaluable. **Only those 421 probability tokens were
parsed.** The other 842 rows' tokens were never converted to numbers.

Every token was parsed with the PR #93 rule: ASCII-checked, then an anchored
`fullmatch` against

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
post-check re-asserted no member exceeds the selection. Here the argmax set has
a single member, so the tie-break did not bind — but it was executed and proved
rather than assumed.

## Counters — action-specific and cumulative, kept separate

The PR #93 abort record is preserved verbatim; its counters are not rewritten.

| this action | value |
| --- | --- |
| attempts started | 1 |
| attempts succeeded | 1 |
| thresholds selected | 1 |
| probability tokens parsed | 421 |
| fits, refits, `predict_proba`, tuning, recalibration, bootstrap, SHAP, p-values, sensitivity analyses, model re-selections | 0 |
| `final_test_rows_read` | 0 |

| cumulative | value |
| --- | --- |
| **total attempts started** | **2** |
| prior aborted attempts | 1 |
| successful attempts | 1 |
| **total thresholds materialized** | **1** |

## What this does and does not unblock

`PRE02` is now **resolved**: the threshold value exists in a committed artifact.

`PRE01` remains **unresolved** — a new explicit human authorization for Final
Test access. So:

```
PRE01 = UNRESOLVED          PRE02 = RESOLVED
final_test_contract_fully_executable = false
final_test_access_authorized         = false
final_test_execution_authorized      = false
final_test_rows_read                 = 0
final_test_locked                    = true
stage130_started                     = false
```

**The Final Test is not declared executable.** Resolving one of two
prerequisites does not open it, and no partial or threshold-free run is
permitted either.

## The frozen file did not move

`stage126_m1_development_oof_predictions.csv` is byte-identical at
`48a00c88…3326749`, verified before and after the run. No cleaned or normalised
copy was created. The three locked development results are byte-identical.

## متن فارسی

استخراج یک‌باره threshold اجرا شد و **دقیقاً یک عدد** تولید کرد:
**`0.426878838687`** با `F2 = 0.5916030534351145` و شمارش `TP=31`, `FP=91`,
`FN=4`. مجموعه argmax تنها **یک** عضو داشت، پس tie-break نیاز نشد — ولی اجرا و
اثبات شد، نه فرض.

این تلاش **دوم** بود؛ رکورد تلاش اول که با `ABORT_THRESHOLD_DERIVATION` متوقف شد
دست‌نخورده حفظ شده و بازنویسی نشده. شمارنده‌های action-specific و cumulative
جداگانه ثبت شده‌اند: **کل تلاش‌های آغازشده ۲**، تلاش موفق **۱**، threshold
materialize شده **۱**.

**فقط یک اجرا انجام شد**: نه dry run محاسباتی و نه اجرای دوباره برای اثبات
determinism. صحت artifactها از روی بایت‌های نوشته‌شده و hash آن‌ها و بازمحاسبهٔ
F2 از شمارش‌های ثبت‌شده بررسی شد، نه با تکرار derivation.

**ابتدا انتخاب ردیف، سپس parse:** از ۱۲۶۳ ردیف، ۴۲۱ ردیف مدل و پیکربندی منتخب
جدا شد و **فقط همین ۴۲۱ توکن** parse شد؛ توکن‌های ۸۴۲ ردیف خانواده‌های دیگر
هرگز به عدد تبدیل نشدند. parse فقط با regex قفل‌شدهٔ PR #93 و بدون
`eval`/`exec`/`ast.literal_eval`.

**این صرفاً یک operating point توسعه است** و نباید به‌عنوان برتری مدل یا نتیجهٔ
استنباطی گزارش شود.

`PRE02` اکنون **resolved** است، ولی `PRE01` همچنان **unresolved** می‌ماند؛
بنابراین Final Test قابل اجرا اعلام نمی‌شود و
`final_test_access_authorized = false`، `final_test_rows_read = 0` و
`final_test_locked = true` باقی می‌مانند. فایل OOF منجمد byte-identical ماند.

## Files

- `stage129_threshold_value.json` — the threshold, its F2 and confusion counts.
- `stage129_threshold_derivation_provenance_record.json` — contract hashes, input hash, counts, parse regex, runtime.
- `stage129_threshold_derivation_qc_report.json` — the 30 contractual controls, the SUP01 supplementary check, the tie-break proof, action and cumulative counters.
- `metadata_and_hashes_stage129_threshold_derivation_execution.json`.

Executor: `project/src/stage129_threshold_derivation.py`.
Regression tests: `project/tests/test_stage129_threshold_derivation_execution.py`.
