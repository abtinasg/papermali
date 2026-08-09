# Stage128 — Track B step D: the M3-LAG-WDI EXPLORATORY DATA GATE

**Action:** `stage128-m3-lag-wdi-exploratory-data-gate`
**Authorized scope:** `data_gate_only`
**Formal verdict:** `PASS_M3_LAG_WDI_DATA_GATE`

## What this action is

The one authorized execution of the PRE-EXISTING, locked M3-LAG-WDI Data
Gate. It computed, for every row of the retained-M2 development common
sample, whether the two contract-locked lagged WDI features are
constructible, compared coverage to the inherited thresholds, and recorded
the formal data-admission verdict. **A Gate PASS is DATA ADMISSION ONLY** —
it is not modeling authorization, not an information-content claim about the
FX feature, not point-in-time vintage proof, and not a Final Test unlock.

Payload identity was proven on the raw bytes before decoding, against the
committed retrieval manifest anchored to the immutable Zenodo record
`10.5281/zenodo.21844636`. No World Bank request was made; the retained
evidence was not modified.

## Coverage under the locked thresholds

| Quantity | Numerator | Denominator | Value | Threshold | Met |
| --- | --- | --- | --- | --- | --- |
| CPI candidate coverage | 539 | 539 | 1.0000 | >= 0.8 | yes |
| FX candidate coverage | 539 | 539 | 1.0000 | >= 0.8 | yes |
| Block common-sample coverage | 539 | 539 | 1.0000 | >= 0.7 | yes |

| Validation window | Target years | Window positives | Positive evaluable | Floor | Met |
| --- | --- | --- | --- | --- | --- |
| `fold1_validation` | 1396-1397 | 18 | 18 | >= 5 | yes |
| `fold2_validation` | 1398-1399 | 10 | 10 | >= 5 | yes |

## The unlocked calendar mapping — why the verdict is still well-defined

The locked contract indexes the features by a GREGORIAN predictor year but
does not lock the Jalali-to-Gregorian mapping for the development rows. This
Gate refused to invent it: every row's constructibility status was computed
under BOTH admissible conventions (`jalali + 621` and `jalali + 622`), and
the statuses are identical under both
(`status_invariant_across_calendar_conventions =
True`), so the coverage
numbers and the verdict do not depend on the missing convention. Feature
VALUES do differ between the conventions, which is why this package contains
row STATUSES only and no authoritative feature-value table. **The mapping
must be locked by a human before any modeling table may be built.**

## The step C findings — preserved, not laundered

The formal verdict above is a COVERAGE statement under the locked rules. It
must never be read as erasing the step C material findings, which are
distinguished explicitly in the decision record (syntactic coverage vs.
thresholds vs. information content):

- the formal Gate PASS is a coverage statement only; it does not make the FX feature informative: step C's finding stands that the FX log-ratio is defined but identically ZERO for predictor years 2021-2024 (outside the development sample, which ends at predictor year 2020 at the latest under either calendar convention)
- PA.NUS.FCRF carries no value for observation years 2024-2025, so the jointly constructible predictor-year ceiling remains 2024; this does not bind the 539-row development sample but caps any future extension of the block
- the WDI `lastupdated` value is a revision marker, not point-in-time availability proof; no historical-vintage or point-in-time claim is made and the one-year lag does not create one
- the locked contract does not fix the Jalali-to-Gregorian mapping for predictor_year_t; the Gate verdict is invariant to the two admissible conventions, but feature VALUES are not, so the mapping must be human-locked before any modeling feature table is built

The development rows land on Gregorian predictor years
2013–2019
(begin-year convention) or
2014–2020
(end-year convention), so the FX zero-change window 2021–2024 and the
2024–2025 `PA.NUS.FCRF` nulls lie OUTSIDE the development sample under either
convention (0 development rows carry a
zero-change FX feature). They remain real limitations of the block's recent
end and of any future use beyond the development window.

## Where this action stopped

Model fits: `0` · Final Test rows read: `0` · new World Bank requests: `0` ·
feature-value tables materialized: `0`.

A Gate `PASS_M3_LAG_WDI_DATA_GATE` authorizes nothing further. Step E
(`stage128-m3-lag-wdi-exploratory-incremental-evaluation`) remains
`authorized = False` and requires its own new
explicit human authorization, which must also resolve the calendar-mapping
lock recorded above.
