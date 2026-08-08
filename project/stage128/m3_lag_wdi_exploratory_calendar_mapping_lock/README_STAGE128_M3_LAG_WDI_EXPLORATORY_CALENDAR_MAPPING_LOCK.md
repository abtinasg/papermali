# Stage128 — Track B: the M3-LAG-WDI CALENDAR-MAPPING LOCK

**Action:** `stage128-m3-lag-wdi-exploratory-calendar-mapping-lock`
**Authorized scope:** `calendar_mapping_lock_only`
**Locked rule:** `predictor_year_t = jalali_fiscal_year_t + 621`

## What this action is

Step D returned `PASS_M3_LAG_WDI_DATA_GATE` and exposed a gap in the locked
contract: the macro features are indexed by a **Gregorian** `predictor_year_t`,
the development rows are keyed by a **Jalali** `fiscal_year_t`, and no
committed artifact mapped one onto the other. The Gate verdict is invariant to
the two admissible mappings; the feature **values** are not. This action locks
the mapping — and **only** that.

It fits no model, materializes no feature value, reads no Final Test row, does
not rerun step C or step D, and **does not authorize step E**.

## The decision

`fiscal_year_t` labels **the Jalali year in which the accounting period ENDS**
(539/539 agreement, established by inverting Stage125 Part 3C's
four-Jalali-month regulatory lag over the committed cutoffs). A Jalali year
spans two Gregorian years, so a uniform mapping is either `+621` (the year the
Jalali year **begins**) or `+622` (the year it **ends**).

| | `+621` (locked) | `+622` (rejected) |
| --- | --- | --- |
| Gregorian year semantics | the Gregorian year in which the Jalali year BEGINS | the Gregorian year in which the Jalali year ENDS |
| **Rows whose `t-1` observation year was incomplete at the cutoff** | **0 / 539** | **22 / 539** |
| Affected fiscal years | — | ['1392', '1393', '1394', '1395', '1396', '1397', '1398'] |
| Worst case | — | 131 days **after** the cutoff |
| Margin (min / median) | 234 d / 566 d | -131 d / 201 d |
| Development predictor years | 2013–2019 | 2014–2020 |
| Binding `t-1` observation years | 2012–2018 | 2013–2019 |

`+622` is rejected because, for 22
development rows spread across **every** fiscal-year cohort, it would require a
macro value whose observation period had **not yet ended** at the prediction
cutoff — future information under the frozen
`G07 no_future_or_target_year_information` rule.

## Why the lock is fail-closed, not declarative

The runner **recomputes** this table from committed bytes on both `--execute`
and `--check`, and refuses to write a lock for any offset that admits a single
timing violation. `+622` is therefore **structurally
unlockable** while the committed development sample says what it says — it
cannot be swapped in by editing a constant. Changing the locked mapping
requires a new explicit human scientific decision **and** evidence that
supports it.

The recomputation needs only `fiscal_year_t` and `pair_cutoff_date` plus
integer arithmetic: **no calendar library, no feature value, no outcome label,
no Final Test row**.

## Independence from model performance

The selection used `selection_used_model_performance: false`,
`selection_used_coverage_comparison: false`,
`selection_used_feature_values: false`. No feature value was computed and no
metric was evaluated — only observation-period end dates against cutoff dates.
The justification stands unchanged if `+622` later produced
better predictive numbers; that would be evidence of leakage, not of merit,
since the 22 violating rows are exactly where a
look-ahead advantage would come from.

## What this lock does NOT establish

- point-in-time WDI availability remains UNPROVEN: the retained values are current/latest revised WDI and may contain later revisions, and locking the calendar mapping does not turn revised WDI into point-in-time data
- the one-year lag remains a conservative temporal-separation design only; it does not prove historical publication availability
- the FX feature remains defined but identically ZERO for predictor years 2021-2024 (outside the development sample under the locked mapping, but real for any future extension of the block)
- PA.NUS.FCRF still carries no value for observation years 2024-2025, so the jointly constructible predictor-year ceiling remains 2024

## Where this action stopped

Model fits `0` · feature-value tables materialized `0` · Final Test rows read
`0` · new World Bank requests `0` · Gate reruns `0`.

Step D remains `PASS_M3_LAG_WDI_DATA_GATE` with coverage 539/539/539,
validation positives 18 and 10, 0 exclusions, admitted **DATA ADMISSION ONLY**.
The authoritative pre-retrieval contract is **amended, not edited**: its
historical unlocked state is retained, following the Stage125 Part 3C
superseding pattern.

Step E (`stage128-m3-lag-wdi-exploratory-incremental-evaluation`) remains
`authorized = False` and needs its own separate
explicit human authorization.
