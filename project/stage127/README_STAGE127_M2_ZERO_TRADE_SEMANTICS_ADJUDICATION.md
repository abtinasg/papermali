# Stage127 M2 — zero-trade semantics evidence import and frozen-contract adjudication

**Canonical Gate is UNCHANGED by this task: `FAIL_M2_DATA_GATE`.** No model was fitted, no prediction was 
generated, no final-test row was read, and no frozen Stage125 contract was modified.

## 1. External evidence delivery

- filename: `stage127_m2_zero_trade_semantics_full_delivery_v3.zip`
- size: 1,955,293 bytes (verified)
- SHA256: `5e05c3ad52d582236cc9c0bbea69dae520a02385921f3dd03792e6f65c917317` (verified)
- The ZIP is immutable, was never edited, and is NOT committed to this repository.
- The delivered `full_qc_report.json` was COMPARED AGAINST, never trusted:
  35 independent comparisons, 0 disagreements.

## 2. Independent papermali-side validation

- raw bounded artifacts in ZIP: 3590
- manifest rows: 3590
- unique raw files: 3590
- SHA256 recomputed and verified: 3590 / 3590 (mismatches: 0)
- exact official TSETMC endpoints verified: 3590 (generic: 0)
- artifacts with no request mapping: 0; with no evidence role: 0
- zero-byte artifacts: 130 ({'HTTP_500': 5, 'UNRESOLVED': 125}); zero-byte SUCCESS/CACHED: 0
- development-only firewall: maximum bounded dEven = 20200718; observations at or after 20210101: 0

## 3. Official calendar result

- POINT_DATE requests: 427
- present in official `ClosingPrice/GetInstrumentCalendar`: 427
- absent: 0; unresolved: 0
- RANGE requests with InstrumentCalendar date set == ClosingPriceDailyList date set: 27 / 27

The zero-trade endpoint dates are therefore REAL OFFICIAL InstrumentCalendar dates, not retrieval or extraction defects. The 
hypothesis that these rows exist only because extraction included dates outside TSETMC's official calendar is NOT supported.

## 4. Historical identity

- tickers checked: 103
- request_ISIN == raw instrumentID: 103 / 103
- request_ISIN == raw cIsin: 8 / 103
- CANDIDATE_FOUND: 0; NONE_FOUND: 0; UNRESOLVED: 103

Identity uncertainty is preserved explicitly. Histories were NOT concatenated, `insCode="0"` was NOT used as a predecessor, and the 
absence of a demonstrated predecessor is NOT treated as proof that none exists.

## 5. Frozen-contract semantics trace

13 frozen statements were traced ({'DERIVED_UNAMBIGUOUSLY': 6, 'EXPLICIT': 4, 'NOT_SPECIFIED': 3}). Answers:

- **A.** Does 'trading day' explicitly mean an official TSETMC InstrumentCalendar member?  
  → `NO_NOT_EXPLICITLY_DEFINED` (NOT_SPECIFIED)
- **B.** Does 'trading day' explicitly require positive executed trade?  
  → `NO` (DERIVED_UNAMBIGUOUSLY)
- **C.** Does zero trade remove a date from W?  
  → `NO` (DERIVED_UNAMBIGUOUSLY)
- **D.** Does missing_price_rule = exclude_day_from_window_computations mean (1) remove the date from the scientific trading-day sequence, or (2) keep the day in W but exclude its missing price from calculations?  
  → `READING_2_KEEP_DAY_IN_W_EXCLUDE_FROM_CALCULATIONS` (DERIVED_UNAMBIGUOUSLY)
- **E.** For realized volatility, does 'consecutive trading days with both prices present' permit bridging over an intervening calendar member with no price?  
  → `NO_BRIDGING_PERMITTED` (DERIVED_UNAMBIGUOUSLY)
- **F.** Is t0 the first calendar-member trading day of W, or the first positive-trade/priced day?  
  → `FIRST_TRADING_DAY_OF_W_NOT_FIRST_PRICED_OR_TRADED_DAY` (DERIVED_UNAMBIGUOUSLY)
- **G.** Is T* defined independently of adjusted_close availability?  
  → `YES` (DERIVED_UNAMBIGUOUSLY)

The single decisive record is the FROZEN synthetic validation that locked the contract: a window of 248 days containing exactly one 
zero-traded-value day produced 247 usable daily returns (= 248 − 1) and 246 usable Amihud days (= 247 − 1). The zero-trade day was 
therefore retained in the trading-day sequence and still contributed returns; only Amihud excluded it.

## 6. Adjudication outcome

**FROZEN_CONTRACT_UNAMBIGUOUS_CURRENT_IMPLEMENTATION_CONFORMANT**

- current implementation conformant: `YES`
- canonical Gate changed: `False`
- t0 changed: `False`; T* changed: `False`; thresholds changed: `False`

## 7. Diagnostic counterfactuals — NOT canonical results

| reading | equity_return | realized_vol | amihud | common |
| --- | --- | --- | --- | --- |
| `INSTRUMENT_CALENDAR_MEMBERSHIP_READING` | 269 (0.4039) | 576 (0.8649) | 576 (0.8649) | 269 (0.4039) |
| `POSITIVE_EXECUTED_TRADE_DAY_READING` | 609 (0.9144) | 609 (0.9144) | 609 (0.9144) | 609 (0.9144) |

`INSTRUMENT_CALENDAR_MEMBERSHIP_READING` reproduces the canonical coverage exactly, which is what the frozen contract requires.

`POSITIVE_EXECUTED_TRADE_DAY_READING` is a COUNTERFACTUAL ONLY. It is not supported by the frozen contract and is contradicted by 
the frozen synthetic validation. It raises coverage, which is precisely why it may not be adopted on the strength of the Gate 
result it would produce.

## 8. Canonical state (unchanged)

- Gate: `FAIL_M2_DATA_GATE`
- equity_return_window: 269 / 666 = 0.4039
- realized_volatility: 576 / 666 = 0.8649
- amihud_illiquidity: 576 / 666 = 0.8649
- common sample: 269 / 666 = 0.4039

M2 modeling is NOT authorized. M2 has NOT passed.

## 9. Derived evidence artifacts

- `stage127_m2_zero_trade_point_endpoint_evidence.csv` — 427 unique POINT_DATE requests covering 523 endpoint occurrences
- `stage127_m2_zero_trade_range_evidence.csv` — 27 low-return RANGE requests
- `stage127_m2_zero_trade_historical_identity_evidence.csv` — 103 tickers

Factual evidence and scientific interpretation are kept strictly separate: every evidence row carries 
`scientific_inclusion_decision = NOT_A_SCIENTIFIC_DECISION_SEE_ADJUDICATION_ARTIFACT`, and TSETMC state codes remain literal with UNRESOLVED meaning.

