# Stage125 Part 3B.0 — Evidence Capture Readiness

## Scope

Part 3B.0 is **infrastructure/readiness only**. It performs:
- **No** modeling, **no** real evidence capture, **no** network access.
- **No** real accessibility scores or candidate admission decisions.
- **No** changes to frozen Stage122–Stage125 Part 3A.1 scientific assets.
- Part 3B evidence capture (`stage125-part3b-evidence-capture`) is **not started**.

## Deliverables

- Evidence capture contract JSON (schema + null rules).
- Header-only evidence manifest template CSV (zero data rows).
- Header-only gate-result template CSV (zero data rows).
- Immutable raw-cache contract JSON (tested in pytest temp dirs only).
- Header-only cache-handle template CSV (external trust-anchor contract).
- Default-deny network/child-process sentinel contract JSON.

## Guardrails

- `part3b0_readiness=true`
- `part3b_started=false`
- `evidence_collected=false`
- `accessibility_scoring_applied=false`
- `network_extraction_performed=false`
- `modeling_started=false`
- `part3a_protocol_locked=true`
- `part3a_decision_locked=true`
- Snapshot bytes verified against `snapshot_sha256` (no symlink follow).
- Gate inputs are sealed/typed; G07 derived from available_at vs cutoff.
- G09–G14 bound to exact frozen pilot key identity (80/39/41).

## Next research action

Remains `stage125-part3b-evidence-capture` (pointer only; not started).

