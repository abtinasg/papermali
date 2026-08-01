# Stage128 — M3 macro data Gate

**Action id:** `stage128-m3-macro-data-gate`
**Gate type:** `macro_data_admission_gate_only_no_predictive_modeling`
**Gate status:** `UNRESOLVED_M3_DATA_GATE`
**Baseline:** `abtinasg/papermali` `main` @ `35aaf4b70e9341704ee38be6f8cf2e2519c70bb2`

## What this Gate answers

Only this:

> Can the exact frozen M3 macro block be obtained from authoritative,
> reproducible and point-in-time-safe sources with sufficient development
> coverage, usable paired sample and temporal support?

It does **not** answer whether M3 improves prediction relative to M2. No
predictive metric was computed, no model was fit, and no M3-versus-M2
comparison was executed.

## The exact frozen block

In frozen order, never reduced, expanded or reordered:

1. `cpi_inflation` (`cand_m3_cpi_inflation`)
2. `fx_change_official` (`cand_m3_fx_change_official`)
3. `policy_financing_rate` (`cand_m3_policy_financing_rate`)

Required source id `src_m3_cbi_macro`, required authority
**Central Bank of Iran**.

## Result: `UNRESOLVED_M3_DATA_GATE`

* cand_m3_cpi_inflation: operational series and transformation not uniquely determined (14 of 20 required lock fields unresolved)
* cand_m3_fx_change_official: operational series and transformation not uniquely determined (14 of 20 required lock fields unresolved)
* cand_m3_policy_financing_rate: operational series and transformation not uniquely determined (14 of 20 required lock fields unresolved)
* no authoritative CBI data artifact was obtained: 6 WAF rejections, 2 CAPTCHA challenges, 3 unreachable hosts across 11 official-host probes
* no reproducible retrieval path: identical repeated requests to the same official URL returned different bytes
* cand_m3_cpi_inflation: G-rules unresolved ['G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07']
* cand_m3_fx_change_official: G-rules unresolved ['G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07']
* cand_m3_policy_financing_rate: G-rules unresolved ['G01', 'G02', 'G03', 'G04', 'G05', 'G06', 'G07']

A candidate that failed or remained unresolved was **not** silently dropped to
let a smaller block pass. No partial block was admitted.

## Phase A — prospective source and definition lock

Lock status: `UNRESOLVED_DEFINITION_LOCK`. The lock was written **before** any
value-level work and is derived from source schema, frozen contracts and
theoretical meaning — never from observed coverage and never from target
outcomes.

Of the 20 required operational fields, the frozen
Stage125 contracts uniquely determine only the candidate identity, variable
name, source id, source owner, frequency and unit. Every field that requires
official CBI series identity, release metadata, revision/vintage policy,
as-of rule or transformation is recorded as `null` and unresolved.

Because the lock is unresolved, `assert_phase_b_permitted` fail-closes and
**Phase B never executed**. That guard is what prevents an opportunistic
definition choice or a sequential search for a series with better coverage.

## Official evidence

Every official CBI URL that responded returned either a WAF 'Request Rejected' page or a JavaScript/CAPTCHA bot-protection challenge; the Time Series Database hosts did not respond at all. No probe returned a macro data series. No two identical requests returned identical bytes, so no reproducible retrieval path exists. The CAPTCHA was never solved or bypassed.

All 11 probes targeted official `cbi.ir` hosts only. No
unofficial source, aggregator, mirror, news article, SCI series or free-market
FX rate was used or consulted as evidence. The CAPTCHA was never solved or
bypassed.

## Parent sample

The M3 Gate denominator is the **retained-M2 development common sample**, not
the 666-row M1 development universe:

* rows **539**, positive **55**,
  negative **484**, companies
  **108**
* derived programmatically from `project/stage128/stage128_m2_d2_development_features.csv` and reconciled against the
  committed PR #71 join audit; membership never altered
* the 666-row universe is reported as reconciliation audit only

## Thresholds

Stage125 Part 4 development thresholds, unchanged: candidate coverage
**0.8**, exact three-variable common sample
**0.7**, minimum positives per locked
validation window **5**. The historical
80-pair Part 3A pilot rules G09–G14 are **not** applied.

Unresolved coverage is recorded as `null`, never as zero.

## Temporal degrees of freedom

Macro observations are shared across many company-year rows. The
539 company-year rows are **not** independent macro
observations and are never reported as such. The independent temporal macro
support is unresolved because no macro observation was retrieved.

## Final-test firewall

Final-test target years ['1400', '1401', '1402'] remain locked:
0 rows loaded, 0 predictor values read, 0 target values read, 0 macro values
materialized, 0 predictions, 0 evaluations.

## State

* `m3_macro_data_gate_authorization_consumed` = **true**
* `m3_macro_data_gate_executed` = **true**, status `UNRESOLVED_M3_DATA_GATE`
* `m3_data_workstream_started` = **true**
* `m3_incremental_evaluation_authorized` = **false**
* `m3_modeling_started` = **false**
* `m4_authorized` = **false**, `m4_started` = **false**
* `final_test_locked` = **true**

The research pointer was **not** advanced to
`stage128-m3-incremental-evaluation`; `m3_macro_data_gate_human_review_required` = **true**.
