# Stage129 — threshold derivation, ATTEMPT 3: ADMITTED

**Action id:** `stage129-threshold-derivation-attempt3`
**Base:** `origin/main @ 99c9288d0abc268f926e21ac766cc55db507054c`
**Contracts:** algorithm (PR #92) and parse rule (PR #93)
**Result:** **30 of 30** contractual controls PASS · **`PP08(b)` executed: 421 comparisons, 0 mismatches** · **1 threshold ADMITTED** · `final_test_rows_read = 0`

## The admitted threshold

| field | value |
| --- | --- |
| **threshold** | **`0.426878838687`** |
| F2 at threshold | `0.5916030534351145` |
| TP / FP / FN | 31 / 91 / 4 |
| argmax members | 1 |
| unique candidates | 421 |
| evaluable rows | 421 of 421 selected |
| positives / negatives | 35 / 386 |
| **admission status** | **`ADMITTED`** |

`5 × 31 / (5 × 31 + 4 × 4 + 91) = 155 / 262 = 0.5916030534351145`, recomputed
from the recorded confusion counts.

This is a **development operating point**. It is not evidence of model
superiority, not a test statistic, and carries no inference.

## What attempt 2 got wrong, and what changed

`PP08` has two clauses: conversion to IEEE-754 binary64, **and** a re-check that
`numpy.float64(group) == float(group)` for **every parsed token**. Attempt 2
performed only the first and recorded `PASS` anyway.

Here clause (b) genuinely ran. For each of the 421 tokens the captured decimal
group was converted with **both** constructors and compared:

```
pp08_agreement_comparisons = 421
pp08_agreement_mismatches  = 0
numpy 2.4.6 · python 3.13.5
```

Any mismatch, any non-finite value, any parse failure would have aborted with
`ABORT_THRESHOLD_DERIVATION` and admitted nothing.

## This run stands on its own

The attempt-3 executor is a **new file**,
`project/src/stage129_threshold_derivation_attempt3.py`. The attempt-2 executor
was **not rewritten** — it is historical evidence of a run whose `PP08(b)` never
executed, and editing it would misrepresent that run.

Attempt 2's number was **not read, not used and not assumed**:
`attempt2_value_read_by_this_run = false`,
`attempt2_result_used_as_input_or_shortcut = false`. The sweep recomputed
everything from the pinned input.

The result **agrees** with attempt 2. That agreement is an independent
recomputation arriving at the same answer — it is not the basis for admission.
Admission rests on this run's own complete QC.

## Method, as contracted

1263 rows read; 421 survived the `regularized_logistic_regression` /
`logistic__C_0.1` filter; all 421 evaluable. **Only those 421 probability tokens
were parsed** — the other 842 rows' tokens were never converted to numbers.
Row selection strictly preceded reading any probability or target value.

Candidates are exactly the 421 distinct parsed values — no grid, endpoints,
midpoints, thinning, rounding or truncation. Positive prediction is
`p >= threshold`; strict `>` is never used. Missing targets are never negative.
F2 uses the binding closed form on integer counts. `pick_threshold` is neither
imported nor called.

The maximum F2 was computed first, all candidates attaining it were collected
into an explicit argmax set, `max()` taken over it, and a post-check re-asserted
no member exceeds the selection.

**Exactly one run.** No computational dry run, no determinism re-run — the
executor refuses to start without `--write`.

## Controls

| outcome | count |
| --- | --- |
| PASS | **30** |
| FAIL | 0 |
| NOT_EXECUTED | 0 |

`TD01`–`TD18` and `PP01`–`PP12`. `SUP01` is supplementary and excluded from the
count of 30.

## Counters

| this action | value |
| --- | --- |
| attempts started | 1 |
| attempts succeeded (admitted) | **1** |
| thresholds computed / admitted | 1 / **1** |
| tokens parsed · `PP08(b)` comparisons | 421 · 421 |
| fits, refits, `predict_proba`, tuning, recalibration, bootstrap, SHAP, p-values, sensitivity analyses, model re-selections | 0 |

| cumulative across all three attempts | value |
| --- | --- |
| **total attempts started** | **3** |
| aborted (attempt 1) | **1** |
| computed but not admitted (attempt 2) | **1** |
| **admitted derivations** | **1** |
| thresholds computed / **admitted** | 2 / **1** |

Attempts 1 and 2 are preserved **byte-identical** and pinned by hash in this
run's QC report.

## What this unblocks — `PRE02` only

```
PRE01 = UNRESOLVED          PRE02 = RESOLVED
final_test_contract_fully_executable = false
final_test_access_authorized         = false
final_test_execution_authorized      = false
final_test_rows_read                 = 0
final_test_locked                    = true
stage130_started                     = false
```

`PRE01` — a new explicit human authorization for Final Test access — is
untouched. The admitted threshold carries `usable_for_final_test = false` for
exactly that reason. Resolving one prerequisite does not open the Final Test,
and no partial or threshold-free run is permitted.

## Nothing frozen moved

The OOF CSV is byte-identical at `48a00c88…3326749`, verified before and after,
with no cleaned copy. The three locked development results are byte-identical.
The attempt-1 abort record, the attempt-2 value and QC report, and the attempt-2
executor are all byte-identical — checked before **and** after the run.

## متن فارسی

تلاش سوم اجرا شد و **نتیجه پذیرفته شد**: هر **۳۰** کنترل قراردادی PASS و
**`PP08(b)` واقعاً اجرا شد** — برای هر ۴۲۱ توکن، گروه داخلی با **هر دو** سازندهٔ
`float` و `numpy.float64` تبدیل و مقایسه شد: **۴۲۱ مقایسه، صفر mismatch**.

threshold پذیرفته‌شده: **`0.426878838687`** با `F2 = 0.5916030534351145` و
`TP=31, FP=91, FN=4`.

executor تلاش دوم **بازنویسی نشد** — یک فایل جدید ساخته شد، چون فایل قبلی سند
تاریخی اجرایی است که `PP08(b)` در آن انجام نشده بود. مقدار تلاش دوم **خوانده و
استفاده نشد**؛ همه‌چیز از ورودی پین‌شده بازمحاسبه شد. نتیجه با تلاش دوم یکی
درآمد، ولی این توافق **مبنای پذیرش نیست** — پذیرش بر QC کاملِ همین اجرا استوار
است.

شمارنده‌های تجمعی: **۳ تلاش آغازشده**، **۱ Abort**، **۱ محاسبهٔ
پذیرفته‌نشده**، **۱ derivation پذیرفته‌شده**، **۱ threshold admitted**.
رکوردهای تلاش‌های اول و دوم byte-identical مانده‌اند.

`PRE02` اکنون **RESOLVED** است، ولی `PRE01` همچنان **UNRESOLVED** می‌ماند؛
بنابراین Final Test باز نمی‌شود و `final_test_access_authorized = false`،
`final_test_rows_read = 0`، `final_test_locked = true` و
`stage130_started = false` باقی می‌مانند.

## Files

- `stage129_threshold_value_attempt3.json` — the admitted threshold, F2 and confusion counts.
- `stage129_threshold_derivation_attempt3_provenance_record.json` — contract and input hashes, counts, `PP08(b)` comparison and mismatch counts, runtime.
- `stage129_threshold_derivation_attempt3_qc_report.json` — the 30 contractual controls, `SUP01`, the tie-break proof, action and cumulative counters, and the pinned hashes of attempts 1 and 2.
- `metadata_and_hashes_stage129_threshold_derivation_attempt3.json`.

Executor: `project/src/stage129_threshold_derivation_attempt3.py`.
Regression tests: `project/tests/test_stage129_threshold_derivation_attempt3.py`.
