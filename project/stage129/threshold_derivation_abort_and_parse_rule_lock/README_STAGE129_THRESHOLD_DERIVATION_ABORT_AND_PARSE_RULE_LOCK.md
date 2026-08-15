# Stage129 — aborted derivation recorded, parse rule LOCKED (not executed)

**Action id:** `stage129-threshold-derivation-abort-and-parse-rule-lock`
**Status:** `PROSPECTIVELY_LOCKED_NOT_EXECUTED`
**Result:** one attempt aborted · `threshold_value = null` · **`PRE02` still unresolved**

Two things, kept deliberately separate: an honest record of a derivation that
started and stopped, and a prospective rule for the defect that stopped it.

**Nothing was derived.** No probability or target value was re-read by this
action, no parse was executed against the data, `final_test_rows_read = 0`.

## What happened

The one-time derivation authorized against the merged PR #92 contract was
started from `fbcc48b6`. It passed `TD01`, `TD15`, `TD09`, `TD02`, `TD03`,
`TD16` and `TD12`, then failed while building the candidate set:

```
ValueError: could not convert string to float: 'np.float64(0.513922437119)'
```

Every value in the `predicted_probability` column of the frozen OOF predictions
is stored as a **numpy repr string**, not a number — all 1263 rows, all three
model families. `observed_target`, `target_year` and the aggregation column are
clean; only this one column is affected.

The run was **not** forced through. Stripping the wrapper needs a parse step no
merged contract defines, and `TD07` forbids transforming values before
selection. Inventing that step mid-run would have made the resulting threshold
an artefact of an unpinned implementation choice — the exact failure this whole
contract chain exists to prevent.

**The defect is serialization only. No digits were lost.** Every token matched
an anchored wrapper pattern with a well-formed finite decimal inside, and every
parsed inner value satisfied `float(str(v)) == v`.

## The counters, including the ones that are not zero

A counter that is quietly zero is worse than one that says it does not know. So:

| counter | value |
| --- | --- |
| derivation attempts started | **1** |
| derivation attempts completed | 0 |
| **F2 candidates evaluated** | **0** |
| **thresholds selected or materialized** | **0** |
| model fits / refits / `predict_proba` | 0 |
| `final_test_rows_read` | **0** |

Inside the aborted run:

| counter | value | basis |
| --- | --- | --- |
| CSV rows read into memory | 1263 | `csv.DictReader` materialised every row before filtering |
| filtered rows for the selected model | 421 | the `TD02` check passed |
| `observed_target` values classified | 421 | the `TD12` block completed; it precedes the failing line |
| **evaluable rows determined** | **`UNKNOWN_NOT_ZERO`** | computed in memory, never emitted — the process died before any output |
| probability tokens held as strings | 421 | |
| `float()` attempts on a probability token | **1** | `sorted(key=float)` raised on its first key call |
| **inner values successfully parsed** | **0** | |

And the diagnostic reads that happened *after* the abort, to characterise the
defect for this record — disclosed because a counter must never be falsely zero:

| counter | value |
| --- | --- |
| rows inspected (shape census) | 1263 |
| anchored-regex matches on the selected model | 421 |
| **inner values parsed to float** | **421** |
| distinct inner values observed | 421 |
| F2 candidates evaluated | 0 |
| thresholds selected | 0 |

`evaluable rows` is the only count the evidence cannot prove. It is recorded as
`UNKNOWN_NOT_ZERO` — provably at least 1, because the executor aborts on an
empty evaluable set and did not take that branch — and **no number was guessed**.

## The parse rule, locked prospectively

A token is interpreted as a number **only** if it fullmatches, anchored:

```
^np\.float64\((?P<decimal>[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\)$
```

`[0-9]` is deliberate rather than `\d`. Python's `\d` matches **Unicode**
decimal digits, so `np.float64(۰.۵)` would satisfy a naive pattern and parse to
something unintended. In a repository carrying Persian text that is not
hypothetical. The token must also be ASCII, checked explicitly.

**No `eval`, no `exec`, no `ast.literal_eval`, no general code parser.** The
token merely *resembles* a Python expression; evaluating it would execute
repository data as code. Extraction is by regex only, and `PP06` enforces it.

Rejected — each one aborting, with **no** row-skipping, default, sentinel or
imputation: `NaN`, `Inf` and every non-finite literal; leading, trailing or
internal whitespace; nested or repeated wrappers; any prefix or suffix; a bare
decimal with no wrapper; an empty token; a non-ASCII digit; hexadecimal or
underscore-separated literals; anything else that fails the pattern.

The captured group converts to **IEEE-754 binary64** under the locked runtime's
`numpy.float64` constructor semantics. `PP08` re-checks that
`numpy.float64(group) == float(group)` for every token. The only rounding
permitted is the round-to-nearest-even inherent to binary64; nothing further,
and nothing at all between parsing and selection.

**This is serialization interpretation, not cleaning.** Not rounding, not
imputation, not correction, not normalisation. The underlying numeric content is
unchanged, and parsing is a read.

## The frozen file does not move

`original_file_must_remain_byte_identical = true`, no cleaned copy, no rewritten
replacement, no in-place edit, no cascade.

That constraint is the reason the rule exists. This CSV's SHA-256 is pinned in
**23** committed files — including three merged Stage129 contracts and seven
robustness QC reports. Rewriting it would invalidate every one of them. `PP12`
enforces both halves: the file is byte-identical afterwards, and no normalised
copy exists anywhere in the repository.

## PR #92 is otherwise untouched

The merged algorithm contract stays in force and byte-identical. This rule
inserts a parse step between reading a token and treating it as a number, and
changes nothing else: candidates are the distinct **numeric values** from this
parse, comparison is `>=`, F2 is `5*TP / (5*TP + 4*FN + FP)` at beta 2 with
F2 = 0 on a zero denominator, and the tie-break takes the largest threshold
across the full argmax set. `pick_threshold` stays forbidden.

## This does NOT resolve `PRE02`

```
PRE01 = UNRESOLVED
PRE02 = UNRESOLVED
final_test_contract_fully_executable = false
final_test_access_authorized         = false
final_test_rows_read                 = 0
```

Defining how a token becomes a number is not producing a threshold.

## متن فارسی

دو چیز، عمداً جدا از هم: ثبت صادقانهٔ یک استخراج که آغاز و متوقف شد، و قفل
prospective قاعدهٔ parse برای نقصی که آن را متوقف کرد. **هیچ threshold تولید
نشد**، هیچ probability یا target در این اقدام دوباره خوانده نشد، هیچ parse عملی
روی داده اجرا نشد و `final_test_rows_read = 0` باقی ماند.

**علت توقف:** تمام مقادیر ستون `predicted_probability` به‌صورت repr نام‌پی ذخیره
شده‌اند، نه عدد — هر ۱۲۶۳ ردیف. اجرا به‌زور ادامه داده نشد، چون strip کردن
wrapper نیازمند یک مرحلهٔ parse است که هیچ قرارداد Merge‌شده‌ای تعریف نکرده و
`TD07` دگرگون‌سازی پیش از انتخاب را ممنوع می‌کند. **نقص فقط serialization است و
هیچ رقمی گم نشده.**

**شمارنده‌ها:** یک تلاش آغاز و متوقف شد؛ **هیچ candidate برای F2 ارزیابی نشد**؛
**هیچ threshold انتخاب یا materialize نشد**. در اجرای متوقف‌شده: ۱۲۶۳ ردیف در
حافظه خوانده شد، ۴۲۱ ردیف فیلتر شد، ۴۲۱ مقدار `observed_target` طبقه‌بندی شد،
**۱** تلاش `float()` روی توکن probability انجام شد و **۰** مقدار داخلی با
موفقیت parse شد. تعداد ردیف‌های evaluable قابل اثبات نیست و به‌صورت
`UNKNOWN_NOT_ZERO` ثبت شده — **هیچ عددی حدس زده نشد**. خواندن‌های تشخیصیِ پس از
توقف نیز افشا شده‌اند: ۴۲۱ مقدار داخلی در آن مرحله parse شد، ولی همچنان صفر F2 و
صفر threshold.

**قاعدهٔ parse** فقط با یک regex کامل و anchored، بدون `eval`/`exec`/parser
عمومی، با کلاس رقم `[0-9]` (نه `\d`، که ارقام یونیکد را هم می‌گیرد)، رد
`NaN`/`Inf`/whitespace/wrapper تودرتو/prefix/suffix با `ABORT`، و تبدیل به
IEEE-754 binary64 مطابق سازندهٔ `numpy.float64` در runtime قفل‌شده. این کار
**تفسیر serialization است، نه cleaning، rounding یا imputation**. فایل اصلی
byte-identical می‌ماند و هیچ نسخهٔ تمیزشده‌ای ساخته نمی‌شود.

**`PRE02` همچنان unresolved است** و اجرای استخراج نیازمند مجوز انسانی جداگانه.

## Files

- `stage129_threshold_derivation_abort_record.json` — the aborted attempt and its counters.
- `stage129_predicted_probability_parse_rule_contract.json` — the parse rule and PP01–PP12.
- `stage129_threshold_derivation_abort_and_parse_rule_governance_boundary.json`.
- `stage129_threshold_derivation_abort_and_parse_rule_source_provenance.json` — 5 pinned sources, 8 supplied terms.
- `metadata_and_hashes_stage129_threshold_derivation_abort_and_parse_rule_lock.json`.

Regression tests: `project/tests/test_stage129_threshold_derivation_abort_and_parse_rule_lock.py`.
