# Stage125 Part 3A.1 — User-Approved Pilot Decision Lock

## Scope

Part 3A.1 records **user-approved decisions** on top of the frozen Part 3A protocol. It performs:
- **No** modeling, **no** evidence collection, **no** network access.
- **No** changes to frozen Part 3A protocol files or Stage122–Stage124 assets.
- **No** accessibility scores applied to sources.
- Part 3B (evidence capture) is **not** started.

## Rubric approval

- Version `stage125_part3a_v1` approved for Part 3B evidence pilot.
- `rubric_approval_status=approved_for_part3b_evidence_pilot`
- `applied_to_sources=false` (frozen rubric file unchanged)
- Score 0–2 = hard drop; score 3 = pilot permission only; scores 4–5 must still pass all other Gates.
- Missing evidence = null/unresolved, never zero.

## Pilot selection

- Selected option: `pilot_option_event_enriched`
- Sample size: 80 (39 positive / 41 negative / 0 unknown)
- `population_representative=false`, `modeling_sample=false`
- `eligibility_impact=none_protocol_only`
- Compact and extended options remain `not_selected`.
- Selection is deterministic, without replacement, Rule A eligible only, before evidence, from frozen identifiers.
- **No post-evidence substitution** — failed pairs are fail/unresolved, not replaced.

### Allocation by target year

- 1393: 4 positive / 4 negative
- 1394: 4 positive / 4 negative
- 1395: 4 positive / 4 negative
- 1396: 4 positive / 4 negative
- 1397: 4 positive / 4 negative
- 1398: 4 positive / 4 negative
- 1399: 4 positive / 4 negative
- 1400: 4 positive / 4 negative
- 1401: 4 positive / 4 negative
- 1402: 3 positive / 5 negative

- Unique tickers: 26
- Unique known industries: 10
- Industry present pairs: 53
- Industry missing pairs: 27
- Legacy nonempty industry label count (includes unknown sentinel): 11
- Unknown sentinel `نامشخص در فایل ارسالی` is **not** a known industry.

## Approved G09–G14 thresholds

Pilot-only coverage/event thresholds (not final modeling thresholds). See `part3a_approved_gate_thresholds_stage125.csv`.

## Guardrails

- `part3a_protocol_locked=true`
- `part3a_decision_locked=true`
- `part3b_started=false`
- `modeling_started=false`
- Candidate decisions remain unresolved pending Part 3B evidence.
