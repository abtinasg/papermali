# PR #43 — Stage125 Part 3B.1B CODAL document-binding mini-pilot

## Summary

Controlled five-row CODAL predictor-document binding mini-pilot (maintenance).
Document metadata / provenance only.

Verified scientific result (unchanged by this harden pass):

- Scope: `ثنوسا|1392`, `بوعلی|1399`, `بوعلی|1400`, `اردستان|1401`, `اپال|1401`
- `BOUND = 0`
- `UNRESOLVED = 4`
- `REJECTED = 1`
- `available_at` non-null = `0`

Provenance harden (this pass):

- Tracked parsed-metadata receipt
  `part3b1b_thanusa_parsed_metadata_receipt_stage125.json` bound to payload SHA
- Fresh-clone reconstruction does not require gitignored raw HTML
- Raw-present and raw-absent deterministic outputs are byte-identical
- Official `--check` performs zero writes / zero network and fails on canonical drift
- All 11 pilot fields verified by exact equality
- `completed_at_utc = null` preserved with explicit missingness status

## Explicit non-claims

- No additional CODAL / TSETMC / CBI / search-engine network
- No financial-value / M1–M4 extraction
- No accessibility scoring
- No Gate application
- No cutoff-audit mutation
- No Part 3B.2 / Stage126 / modeling
- Does not complete Part 3B research action
- Does not modify PR #3

## Research pointers (unchanged)

- `last_completed_research_action_id = stage125-part3a-decision-lock`
- `next_research_action_id = stage125-part3b-evidence-capture`

## Test plan

- [x] `python project/run_stage125_part3b1b.py --check`
- [x] Focused Part 3B.1B tests
- [x] Part 3B.1A tests
- [x] AI Handoff tests
- [x] Full `project/tests` suite
- [x] `validate_ai_handoff.py --check`
