# Stage125 Part 3A — Accessibility & Pilot Protocol Lock

## Scope

Part 3A locks the pilot protocol **before** any source-accessibility or coverage evidence is collected. It performs:
- **No** modeling, **no** data extraction, **no** network access.
- **No** changes to eligibility, targets, samples, or frozen assets.
- **No** candidate admitted, passed, or scored from evidence.
- Part 3B (evidence capture) is **not** started.

## Registered candidate inventory (exactly 10)

**M2 (3):** equity_return_window, realized_volatility, amihud_illiquidity

**M3 (3):** cpi_inflation, fx_change_official, policy_financing_rate

**M4 (4):** audit_opinion_type, going_concern_flag, audit_lag_days, board_size

`src_m3_sci_macro` is registry-only (not a registered variable). Broader research-design narrative items are marked `research_design_only_not_registered`. M5 and Persian-text modeling remain `out_of_scope_locked`.

## Inputs (read-only, SHA-256 verified)

- `modeling_all_rows_stage124_gate_b.csv` — 1331 rows
- `modeling_one_year_ahead_stage124_gate_b.csv` — 1200 pairs, 130 tickers

## Accessibility rubric

- Proposed 0–5 scale; `approval_status=pending_user_approval`.
- `applied_to_sources=false` in Part 3A.
- Missing evidence → null/unresolved, never zero.
- Score < 3 → hard drop; score = 3 → pilot permission only.
- Scores 4–5 must still pass every other Gate.

## Gate protocol

Eight Gates are locked (accessibility ≥ 3, authoritative source, reproducibility, published/available_at, extraction error control, missing availability, no future info, all-must-pass). Six thresholds (coverage, event counts, pilot size/allocation) remain `pending_user_approval` — no numeric values invented.

## Sampling frame

Derived from frozen Gate B data only. Rule A primary = 1013 eligible (81 pos / 932 neg). Rule B robustness = 994 eligible (80 pos / 914 neg). Three event-enriched accessibility/coverage pilot options (`pilot_option_compact`, `pilot_option_event_enriched`, `pilot_option_extended`) provided for later human approval; none executed in Part 3A. All options share `sampling_purpose=event_enriched_accessibility_coverage_pilot`, `population_representative=false`, `modeling_sample=false`, `eligibility_impact=none_protocol_only`. They deliberately oversample positive distress events relative to Rule A prevalence (~8%) and must not be used to estimate population class prevalence or report model performance.

## Guardrails

- `modeling_started` remains `false`.
- `part3a_protocol_locked` = `true`; `part3b_started` = `false`.
- `eligibility_impact` = `none_protocol_only`.
- Stage122–Stage125 Part 1/Part 2 frozen assets unchanged.
