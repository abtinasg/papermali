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
* official-metadata unavailability: no official CBI data or documentation artifact is committed in this repository, so the prospective definition lock could not be completed from official sources in this execution
* the access-probe capture metadata is not independently verifiable (raw response bytes unavailable, no headers or stderr logs captured), so it cannot supply G02/G03/G04 evidence
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

## What this code actually implements

`implementation_scope` = **`PHASE_A_TERMINAL_UNRESOLVED_SNAPSHOT`**.

This repository code is **not** a complete executable PASS/FAIL data Gate.
`phase_b_implementation_present` = **false**. What executed here was:

* official-source discovery,
* a **metadata-only** prospective definition-lock attempt,
* recording of the UNRESOLVED decision.

What did **not** execute: value-level retrieval, coverage, join, event-count
and temporal-support assessment. Those outputs are null. Implementing and
running Phase B would require official metadata **and a new explicit
authorization after human review**.

## Official evidence — downgraded, not independently verifiable

**`access_probe_evidence_status` = `UNVERIFIED_CAPTURE_METADATA_ONLY`.**

Only one thing about the access attempt is independently verifiable from
committed data: all 11 probes targeted official
`cbi.ir` hosts, which can be checked against the committed URL list. No
unofficial source, aggregator, mirror, news article, SCI series or free-market
FX rate was used, and the CAPTCHA was never solved or bypassed.

Everything else is **programmer-reported capture metadata, raw bytes
unavailable for independent audit**:

* `access_probe_raw_bytes_available` = **false** — the response bodies from the
  capture session were not retained;
* `response_headers_captured` = **false**, `stderr_logs_captured` = **false**;
* the recorded SHA-256 values, byte lengths, status codes, and the
  WAF / CAPTCHA / byte-reproducibility classifications **cannot be
  re-derived** from committed bytes.

Accordingly this package does **not** assert that the responses were definitely
CAPTCHA pages, that they definitely contained no macro series, that every
responding URL definitely returned "Request Rejected", or that
non-reproducibility is proven. Those remain programmer-reported observations
only, and **none of them is used as G02, G03 or G04 evidence**.

## Why the Gate is UNRESOLVED

Three distinct causes, deliberately not conflated:

1. **Frozen-contract incompleteness** — the frozen contracts alone do not
   uniquely determine the operational series for any candidate.
2. **Official-metadata unavailability** — no independently verifiable official
   CBI documentation or data artifact is committed, so the prospective lock
   could not be completed from official sources in this execution.
3. **No value-level execution** — coverage, join, event counts and temporal
   support were never assessed.

It is **not** established that the Gate could not have passed with official
access. Official source documentation could potentially have completed the
prospective definition lock. A new human-selected contract is one possible
future route; an authorized, reproducible official CBI documentation and data
package is another.

The candidate ambiguity classes recorded in the lock are **unverified**
(`ambiguity_classes_verified_against_official_documentation` = false). They are
derived from what the incomplete frozen contract leaves open and must not be
read as verified facts about CBI series.

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
