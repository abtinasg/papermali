# Stage128 — M2 D2 Boundary-Month Equity-Return Design Freeze

**Date:** 2026-07-30

**Parent contracts:** [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md), the frozen M2 formula contract (`project/stage125/part3b1_m2_feature_formula_contract_stage125.json`), and the Stage127 Gate outcome (`project/stage127/README_STAGE127_M2_MARKET_DATA_GATE.md`).

**Status:** design-freeze / contract amendment. Historical Stage125/Stage127 records remain unchanged and are preserved byte-for-byte. This document supersedes only the D0 equity-return measurement component for **future** M2 Gate execution. It does not execute a Gate, admit M2, fit a model, or generate a prediction.

## Authorization scope

This freeze is authorized ONLY to formalize, document, test and freeze the D2 equity-return specification below. It is explicitly **not** authorized to: rerun the canonical M2 Gate; perform M2 incremental evaluation; fit a model; generate a prediction; tune hyperparameters or features; run a target-based design comparison; access final-test data; start M3/M4; select a winner; or merge this PR without a later, separate, explicit authorization.

target values accessed = 0. model fits = 0. predictions = 0. final-test access = 0. canonical Gate executions = 0.

## 1. Historical record — D0 (preserved, unchanged)

D0 is the original frozen `equity_return_window` specification: adjusted close required at the **exact** `t0` (first trading day of the shared 12-calendar-month window `W`) and the **exact** `T*` (last eligible trading day strictly before the pair cutoff).

Authoritative TSETMC evidence (Stage127, `project/stage127/`):

| quantity | value | fraction |
|---|---:|---|
| `equity_return_window` coverage (D0) | 269/666 | 0.4039039039 |
| `realized_volatility` coverage | 576/666 | 0.8648648649 |
| `amihud_illiquidity` coverage | 576/666 | 0.8648648649 |
| D0 three-variable common sample | 269/666 | 0.4039039039 |

D0 Gate outcome: **`FAIL_M2_DATA_GATE`** (thresholds: each-candidate coverage ≥ 0.80, common-sample coverage ≥ 0.70; both violated by `equity_return_window`).

The subsequent official-calendar investigation (Stage127 zero-trade/trading-day semantics adjudication) established that this failure was **not a retrieval or database defect**, and that the D0 implementation conformed to the then-frozen contract. D0 remains the historical scientific record and this document does not rewrite it to make D2 appear ex ante.

## 2. Why D2 was considered

D2 was considered only after **predictor-data feasibility** was observed — no M2 model, prediction, PR-AUC, target-based design comparison, or final-test result was inspected before this decision. The correct characterization is:

> prospectively locked after predictor-only feasibility assessment and before outcome/model evaluation

D2 is **not** described as "ex-ante pre-registered," since the possibility of amending the endpoint-selection rule was only raised after the D0 failure was observed.

## 3. D2 frozen formula contract

**Primary paper-facing name:** Boundary-Month As-of Trailing Equity Return. First-use explanatory wording: "an approximately 12-month as-of cumulative equity return" — never described as an exact 12-month return without that qualification.

Implementation: [`project/src/stage128_m2_d2_boundary_month_equity_return.py`](../../src/stage128_m2_d2_boundary_month_equity_return.py).

### Unchanged (retained exactly as frozen in Stage125/Stage127)

- pair-specific `W`: shared 12-calendar-month window;
- `t0`: first trading day of `W`; `T*`: last eligible trading day strictly before the pair cutoff;
- trading-day semantics, including zero-trade `InstrumentCalendar` days remaining in `W`;
- daily-return adjacency (`daily_simple_returns`), unchanged from Stage127;
- `realized_volatility` and `amihud_illiquidity`: same `W`, same formulas, same ≥126 minimum, same PIT constraints, same zero-traded-value treatment, same no-imputation rules. D2 does not change either feature.

### Changed (D2 only reselects the two equity-return endpoints)

**Start boundary.** Identify the Gregorian calendar month containing `t0`. Within `W`, `d_start` = the FIRST trading observation on or after `t0`, within that SAME Gregorian month, with a valid adjusted close. If none exists, `equity_return_d2 = unavailable`.

**End boundary.** Identify the Gregorian calendar month containing `T*`. Within `W`, `d_end` = the LAST trading observation on or before `T*`, within that SAME Gregorian month, with a valid adjusted close. If none exists, `equity_return_d2 = unavailable`.

**Return:**

```
R_D2 = P_adjusted(d_end) / P_adjusted(d_start) - 1
```

No annualization. No rescaling to exactly 365 days. No interpolation, extrapolation, forward fill, backward fill, or other imputation. No raw/unadjusted close substitution. No synthetic adjusted prices. No cross-month fallback and no boundary-tolerance tuning (no 14/21/31-day search) to recover unusable pairs.

### 126-return quality floor (unchanged rule, reused verbatim)

`usable_daily_return_count >= 126`, computed by the EXISTING frozen `daily_simple_returns(W)` logic (same adjacency, missing-price handling, and minimum count as D0). If below 126, D2 is unavailable even when both boundary prices exist.

### M2 primary block after this amendment

1. Boundary-Month As-of Trailing Equity Return (D2)
2. Realized volatility (unchanged)
3. Amihud illiquidity (unchanged)

No fourth primary market feature. `zero_trade_day_ratio_W` remains a descriptive microstructure/eligibility diagnostic only; it is **not** added to primary M2.

## 4. Calendar convention — Gregorian lock

Gregorian boundary-month membership is frozen for D2. Rationale (scientific, not coverage-driven):

- the canonical M2 market-time axis uses Gregorian/ISO dates;
- TSETMC `dEven` and the existing market-data pipeline operate on the Gregorian date axis;
- the frozen 12-calendar-month `W` uses `datetime.date` / Gregorian arithmetic;
- D2 preserves `W`, `t0`, `T*`, daily-return adjacency, realized volatility and Amihud exactly, changing only endpoint selection.

No alternative-calendar search is rerun to choose the primary definition. The pre-lock Jalali diagnostic is recorded transparently and is **not** adopted:

| quantity | value |
|---|---|
| Gregorian D2 usable | 539/666 |
| Jalali-boundary diagnostic usable | 459/666 |
| observations changing usability status | 86/666 |
| pairs usable under both calendars | 456 |
| return-value difference among the 456 dual-usable pairs | 0 |

Interpretation: calendar convention affects eligibility/sample definition, not the measured return where both conventions are eligible. The Jalali-boundary diagnostic materially changed eligibility but did not change return values among dual-usable observations, so it remains a pre-lock diagnostic and is not adopted. Gregorian is chosen for coherence with the frozen market-time axis and `W` construct — **not** because 539/666 clears the Gate; this document does not claim a Gate pass.

## 5. Feasibility provenance — record, do not reselect

Predictor-only feasibility study results (recorded as historical evidence; not reselected or retuned by this document):

| design | usable | coverage |
|---|---:|---:|
| D0 (exact endpoints) | 269/666 | 0.4039039039 |
| D1 (diagnostic upper bound; never a specification) | 576/666 | 0.8648648649 |
| D2 Gregorian (this freeze) | 539/666 | 0.8093093093 |
| D2 three-feature common sample | 539/666 | 0.8093093093 |
| D3 (monthly as-of; NOT adopted) | 555/666 | 0.8333333333 (common 553/666) |

D3 is **not** adopted: it breaks the shared M2 information-window construct, since its return horizon differs from the volatility/Amihud horizon across usable observations and discards recent pre-cutoff information. Larger raw coverage alone is not a reason to include it in primary M2. D1 remains diagnostic only and must never become a scientific specification.

### D2 failure taxonomy (predictor-only feasibility; descriptive, not corrective)

D2 unusable total: 127/666. Observed non-exclusive causes:

| cause | count |
|---|---:|
| `LT126_VALID_RETURNS` | 90 |
| `NO_START_BOUNDARY_PRICE` | 55 |
| `NO_END_BOUNDARY_PRICE` | 17 |

This taxonomy is retained as a descriptive audit only. No extra boundary tolerance, no 14/21/31-day cross-month fallback, and no other tuning is introduced to recover these observations.

### Effective-span diagnostic (historical, not a new rule)

Previously observed effective-span diagnostic across usable D2 pairs: minimum ≈ 342 days, median ≈ 364 days, maximum ≈ 366 days. This is historical predictor-only feasibility evidence, not a new selection rule; no minimum effective-span threshold is added.

### Temporal availability limitation (record, do not equalize)

D2 availability was temporally heterogeneous in the feasibility study:

| fold | usable | coverage |
|---|---:|---|
| `fold1_train` | 173/245 | 0.706122... |
| `fold1_validation` | 159/205 | 0.775610... |
| `fold2_train` | 332/450 | 0.737778... |
| `fold2_validation` | 207/216 | 0.958333... |

This is recorded as a limitation/diagnostic only. No fold-specific Gate threshold is created and D2 is not altered to equalize temporal coverage.

## 6. Post-lock eligibility audit contract (future work, not executed here)

After this design lock, but **before** interpreting any M2 predictive result, a future eligibility audit must compare D2-eligible vs. D2-ineligible observations on predictor-side characteristics, at minimum: prediction cohort/year, industry, firm size, `zero_trade_day_ratio_W`, market activity/traded-value diagnostics, and M1 predictor availability, using standardized mean differences (SMD) where appropriate. An `|SMD| >= 0.10` is a descriptive imbalance flag only, never a pass/fail exclusion rule; no row is removed based on SMD. Any future distress-rate comparison between eligible and ineligible cases may be performed only after this design is locked, and must not retroactively alter the design. This audit is **not** performed as part of this freeze.

## 7. Historical Stage127 reference

`project/stage127/README_STAGE127_M2_MARKET_DATA_GATE.md` and all other historical Stage127 artifacts continue to record, byte-for-byte unchanged, the historical D0 Gate outcome `FAIL_M2_DATA_GATE`. This freeze does not mark the M2 Gate as passed and does not mark M2 admitted for modeling. `project/docs/ai/ROADMAP.md`, `project/docs/ai/OPEN_TASKS.md`, and (via the canonical generator only) `project/docs/ai/handoff_state.json`/`CURRENT_STATE.md` are updated to represent the *resulting* research-pointer state **if and only if this PR is merged** — see §9. Until merge, the live pointers on `main` are unaffected by this PR.

## 8. Next state (explicitly not authorized by this freeze)

This design-freeze PR, once separately audited and explicitly merged, becomes the completed research action for `stage128-m2-boundary-month-return-design-freeze`. It does **not** itself authorize `stage128-m2-d2-gate-rerun` or any equivalent successor — that identification is a pointer only, not an authorization. After this freeze PR is complete, the next action remains a future, separately authorized canonical D2 Gate execution.

## 9. Machine-readable freeze package

The human-readable contract above is mirrored, with additional machine-checkable detail, under [`project/stage128/`](../../stage128/):

- [`stage128_m2_d2_design_freeze.json`](../../stage128/stage128_m2_d2_design_freeze.json) — the full machine-readable freeze record (authorization scope, D2 formula contract, unchanged/changed invariants, endpoint-validity semantics, D0/D1/D3/Jalali status, eligibility-audit contract, and the resulting-if-merged research pointers).
- [`stage128_m2_d2_human_authorization_record.json`](../../stage128/stage128_m2_d2_human_authorization_record.json) — the verbatim authorizing human utterance, its SHA256, and the separately labeled derived (non-verbatim) normalized scope.
- [`stage128_m2_d2_design_freeze_qc_report.json`](../../stage128/stage128_m2_d2_design_freeze_qc_report.json) — internal-consistency assertions for this package (not a Gate re-run).
- [`metadata_and_hashes_stage128_m2_d2_design_freeze.json`](../../stage128/metadata_and_hashes_stage128_m2_d2_design_freeze.json) — SHA256 manifest of every package and referenced source artifact.
- [`stage128_m2_d2_feasibility_provenance.json`](../../stage128/stage128_m2_d2_feasibility_provenance.json) and [`reproduce_prelock_predictor_only_feasibility.py`](../../stage128/reproduce_prelock_predictor_only_feasibility.py) — see §10.

## 10. Feasibility provenance and reproduction — honest limitation

The D0 count (269/666) is **independently and exactly reproduced in this repository** from the already-committed, target-free `project/stage127/stage127_m2_development_features.csv` (666 rows; no distress/target label column) by `reproduce_prelock_predictor_only_feasibility.py`, labeled `REPRODUCTION_OF_PRELOCK_PREDICTOR_ONLY_FEASIBILITY`.

The D1, D2 (Gregorian), D3, and Jalali-boundary-diagnostic counts in §5 require raw **per-day** adjusted-close observations across each pair's 12-calendar-month window. That raw daily data was never committed to this repository — only aggregate per-pair columns and the external-bundle SHA256 provenance (`d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec`) are present. These four counts are therefore recorded as **externally-supplied historical evidence**, explicitly flagged `d1_d2_d3_jalali_independently_reproduced_in_repository = false` in `stage128_m2_d2_feasibility_provenance.json`, and are **not** independently re-derived here. No synthetic daily-price data was fabricated to manufacture an artificial reproduction of these counts.

## 11. Endpoint adjusted-close validity semantics (frozen, disambiguated)

Endpoint eligibility inherits the exact D0 rule (`project/src/stage127_m2_market_data_gate.py: compute_pair_features`): an observation is eligible when `adjusted_close is not None`. A literal `adjusted_close == 0.0` is **not** separately rejected by that rule.

D2 therefore applies:

- **Start boundary (`d_start`, denominator of `R_D2`)**: `adjusted_close is not None` **and** `adjusted_close != 0` — the nonzero guard exists only because `d_start`'s price is the division denominator, mirroring D0's own `p_first != 0` guard.
- **End boundary (`d_end`, numerator of `R_D2`)**: `adjusted_close is not None` only. A literal `0.0` at the end boundary is permitted under the inherited D0 semantics and is **not** silently upgraded to `adjusted_close > 0`.

This does not change the observed 539/666 D2 Gregorian universe recorded in §5.

Required values for this task: target values accessed = 0; model fits = 0; predictions = 0; final-test access = 0; canonical Gate executions = 0; canonical Gate changed = NO; M2 admitted = NO.
