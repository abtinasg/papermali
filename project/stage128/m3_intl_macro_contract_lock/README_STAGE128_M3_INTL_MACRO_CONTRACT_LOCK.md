# Stage128 — M3I-2 prospective contract lock

**Action id:** `stage128-m3i2-prospective-contract-lock`
**Contract type:** `prospective_contract_lock_only_no_data_no_gate_no_modeling`
**Contract status:** `PROSPECTIVELY_LOCKED_NO_DATA`
**Stacked on:** PR #73 head `e6db63fb7d105f0d3a39db101c9e364161c367e9`
(branch `stage128-m3-macro-data-gate`), which is **not merged**.

```text
CONTRACT LOCK ONLY
NO DATA RETRIEVAL
NO DATA GATE
NO MODELING
NO M3I-vs-M2
NO M4
FINAL TEST LOCKED
NO MERGE AUTHORIZATION
```

## What this action is

A **prospective** source / definition / statistical contract lock for the
supplementary international-macro block **M3I-2**, plus a **contingent and
unresolved** M3I-3 financing shell. Everything here is metadata. No macro
observation was retrieved, no value was normalized or joined, no coverage was
computed, no Gate was executed, no model was fit and no comparison was run.

## Relationship to M3-CBI — supplementary, not a replacement

The frozen CBI block is preserved exactly:

```text
M3-CBI: cpi_inflation, fx_change_official, policy_financing_rate
source: src_m3_cbi_macro
status: UNRESOLVED_M3_DATA_GATE
```

M3I-2 is **not** a substitution, correction or continuation of M3-CBI. It is a
distinct supplementary family, and **no M3I block may ever be presented as
confirmatory M3**.

## M3I-2 — prospectively locked

1. `intl_cpi_inflation_annual` — `src_m3i_wdi_imf_ifs_cpi`, indicator `FP.CPI.TOTL.ZG`,
   annual, percent, transformation `identity`.
2. `intl_fx_change_official_annual` — `src_m3i_wdi_imf_ifs_fx`, indicator
   `PA.NUS.FCRF`, annual, LCU per US dollar, transformation
   `100 * ln(E_y / E_(y-1))` over two consecutive annual observations from
   the **same vintage**, fail-closed to null on any missing, non-positive,
   non-consecutive or cross-vintage input.

`PA.NUS.ATLS`, free-market/unofficial rates, aggregators, crypto-implied rates
and manual regime splices are forbidden, as is any alternative indicator or
transformation chosen **after** coverage or model inspection.

## M3I-3 — contingent and unresolved

`intl_financing_rate` exists only as a contract shell against
`src_m3i_imf_mfs_interest_rate` / `IMF.STA:MFS_IR`. Every operational metadata field
is `null`, `candidate_selection_status` = `UNRESOLVED_METADATA_LOCK`, and
`admitted` = **false**. Deposit rates, deposit-rate ceilings, real rates,
spreads, repo/reverse-repo volumes, standing-facility amounts and any
relabelled policy rate are forbidden proxies.

**Stop rule.** If no exact IMF series later passes metadata and coverage review, M3I-3 remains unavailable. M3I-2 is not invalidated. No fourth variable and no substitute proxy may be introduced.

## Data Gate contract — inherited, not redesigned, not executed

Thresholds are the existing frozen ones (candidate coverage
0.8, block common sample
0.7, ≥5
positives per locked validation window, development-only over the retained-M2
development common sample: 539 rows,
55 positive, 484 negative,
108 companies).

In this action every observed value is `null` and the Gate result is
`NOT_EXECUTED`. **Zero is never used in place of
unresolved/not-executed.**

M3I-2 passes only if **both** candidates pass; a reduced one-variable M3I-1
cannot pass; financing may be considered only after M3I-2 passes, its metadata
lock is completed prospectively and it independently passes the same candidate
Gate — and financing failure never invalidates a passing M3I-2.

## Multiplicity — a separate supplementary family

The original confirmatory Holm family stays exactly
`M2_minus_M1`, `M3_CBI_minus_M2`, `M4_minus_M3_CBI`
(`original_confirmatory_family_complete` = false,
`M3I_inserted_into_original_family` = false).

The supplementary family is `S1 = M3I_2_minus_retained_M2` and
`S2 = M3I_3_minus_M3I_2`; neither exists yet. All future M3I results are
labelled supplementary/robustness, and no confirmatory superiority claim is
permitted.

## Execution audit

All zero: network requests, data files downloaded, macro observations read,
company rows loaded, final-test rows loaded, model fits, predictions,
predictive metrics, coverage calculations, Holm calculations.

QC: **46 assertions, 0 failed**,
all_pass = **True**.

## State

* `m3i2_contract_lock_executed` = **true**, status
  `PROSPECTIVELY_LOCKED_NO_DATA`
* `m3i2_retrieval_started` = **false**, `m3i2_data_gate_executed` = **false**
* `m3i2_block_admitted` = **false**,
  `m3i2_incremental_evaluation_authorized` = **false**
* `m3i2_modeling_started` = **false**
* `m3i3_financing_lock` = `UNRESOLVED_METADATA_LOCK`, `m3i3_admitted` =
  **false**
* `m4_authorized` = **false**, `m4_started` = **false**,
  `final_test_locked` = **true**
* `merge_authorized` = **false**

Next pointer (informational only): `stage128-m3i2-official-source-evidence-capture` with
`next_action_authorized` = **false**. Data collection has **not** started.
