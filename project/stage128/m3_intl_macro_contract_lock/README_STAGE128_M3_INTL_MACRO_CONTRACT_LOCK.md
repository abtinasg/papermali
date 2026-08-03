# Stage128 — M3I-2 prospective contract lock

**Action id:** `stage128-m3i2-prospective-contract-lock`
**Contract type:** `prospective_contract_lock_only_no_data_no_gate_no_modeling`
**Contract status:** `PROSPECTIVELY_LOCKED_NO_DATA`
**Scientific provenance baseline:** PR #73
head `e6db63fb7d105f0d3a39db101c9e364161c367e9` (branch
`stage128-m3-macro-data-gate`). Every protected scientific hash is
verified against that commit, permanently.
**Live PR topology:** PR #73 **was merged** by merge commit
`b94f73fab99b5c3bc5c55ea7c14736f2bddb516a`. PR #74 was subsequently
**retargeted to `main`** (base `b94f73fab99b5c3bc5c55ea7c14736f2bddb516a`, the
current main) and **remains a Draft**. The branch was **not rebased**: a
retarget moves the PR base, it does not move the audited baseline. **No merge
authorization has been issued for PR #74.**

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

## Which observation year, inside the selected vintage

Choosing a pre-cutoff archive **vintage** does not say which annual
**observation** that vintage contributes. Both candidates therefore carry an
exact, operationally unique selection rule.

An annual period ends on **December 31 of the labelled Gregorian observation year**, and only a period
that has *finished* strictly before the pair cutoff is eligible
(`completed_annual_period_required` = true,
`current_or_future_incomplete_calendar_year_allowed` = false). Among eligible
years the **maximum** is taken
(`selected_observation_tie_breaker` = `maximum_observation_year`) — never
the first or earliest. A fiscal-year label may never be used as a direct WDI
year lookup, and if no eligible observation exists the value is **null**
(`no_eligible_observation_policy` = `null`). No alternative indicator may be
tried instead.

* CPI — Within the selected pre-cutoff WDI archive vintage, choose the maximum Gregorian observation year y for which FP.CPI.TOTL.ZG[y] is non-missing and December 31 of y is strictly earlier than the pair prediction cutoff.
* FX — Within the selected pre-cutoff WDI archive vintage, choose the maximum Gregorian observation year y such that E_y and E_(y-1) are both non-missing, positive, consecutive annual observations, December 31 of y is strictly earlier than the pair prediction cutoff, and both observations have the same verified currency denomination and valuation definition.

## Historical-vintage semantic and currency compatibility

The WDI archive warns that one indicator code may have carried a different base
year or local-currency valuation in earlier releases, and that **current**
metadata can be displayed alongside **archived** data. An archived vintage is
therefore not self-describing:
`historical_archive_metadata_assumed_identical_to_current` = **false**, and
`semantic_compatibility_evidence_required_before_value_use` = **true**.

Before any value from a selected edition may be used, a later evidence-capture
action must verify, per edition: archive edition identifier, release date and, if available, release time, Iran economy identity, indicator code, series title or archived label compatible with the locked title, frequency = annual, unit compatible with the locked unit, calendar-year observation semantics, raw archive artifact SHA-256.

For CPI: FP.CPI.TOTL.ZG must remain an annual CPI inflation-RATE series in percent in the selected archive vintage. An index-level, GDP-deflator or otherwise differently defined inflation series is a semantic mismatch.

For FX, `E_y` and `E_(y-1)` must additionally share one currency denomination
and one local-currency valuation convention, with no redenomination or
unit break across the pair.

Any mismatch — semantic, unit or redenomination — is
`null_and_invalid_for_coverage`, an unverified vintage never counts towards
candidate coverage, and **no alternative series or source may be tried after a
mismatch or after coverage inspection**.

In this action: `NOT_EXECUTED` — zero archive
editions downloaded, zero observation years selected, zero compatibility
verifications performed.

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

QC: **71 assertions, 0 failed**,
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

## Topology, before and after the predecessor merge

The base rule is **state-dependent**, not unconditional. While
PR #73 was open the base had to be
`stage128-m3-macro-data-gate` and `may_target_main` was false. Now
that PR #73 is merged, the base must be
`main`, `pr_is_stacked_on_open_predecessor` is false and
`may_target_main` is true — while `live_pr_is_draft` = true,
`live_pr_merged` = false and `merge_authorized` = false hold in **both**
states. The pre-merge values are retained under
`historical_pre_merge_topology` (marked `superseded`, `describes_current_state`
= false); nothing was deleted.

This alignment is **governance only**. No candidate identity, transformation,
threshold, Holm family, missing-value rule or point-in-time rule changed, and
the two audited scientific corrections — maximum eligible completed Gregorian
observation-year selection, and historical-vintage semantic / currency
compatibility — are intact.

Next pointer (informational only): `stage128-m3i2-official-source-evidence-capture` with
`next_action_authorized` = **false**. Data collection has **not** started.
