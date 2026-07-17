# Stage125 Part 3B.1B — CODAL Predictor-Document Binding Mini-Pilot

**Status:** controlled mini-pilot for exactly five locked predictor rows.

## Scope

Document metadata / provenance capture only. No financial-value extraction,
accessibility scoring, Gate application, Stage126, or modeling.

## Locked rows

Five predictor rows verified against the frozen Part 3A pilot CSV (full fields)
and pinned Stage121 modeling / OCF manifest canonical sources:

- ثنوسا|1392 (B2) — historical authorized CODAL Decision capture (tracked receipt)
- بوعلی|1399 / بوعلی|1400 (B1) — read-only Stage124 feasibility search caches
- اردستان|1401 (B3) — subsidiary-title rejection path
- اپال|1401 (B1) — incomplete pagination without canonical LetterSerial

## Provenance

- Historical authorized capture requests performed: 1
- Current `--check` network requests attempted: 0
- Tracked receipt: `part3b1b_thanusa_capture_receipt_stage125.json`
- Local raw HTML under `raw_cache_part3b1b/` is optional / gitignored

## Binding statuses

`BOUND` / `UNRESOLVED` / `REJECTED` via Part 3B.1A exact-document binding.

`available_at` is assigned only when `binding_status=BOUND` using CUT-A
`PublishDateTime` → Asia/Tehran → UTC rules. `SentDateTime` is never availability.

## Research pointers (unchanged)

- `last_completed_research_action_id=stage125-part3a-decision-lock`
- `next_research_action_id=stage125-part3b-evidence-capture`
