# Stage125 Part 3B accessibility feasibility probe — active/incomplete

## Status

**Not a completed Part 3B pilot.** `part3b_completed=false`.
`next_research_action_id` remains `stage125-part3b-evidence-capture`.
No Stage126 / modeling advance.

Scoped markers:

- `endpoint_probe_evidence_collected=true` (when origin probes exist)
- `candidate_value_evidence_collected=false`
- `pair_level_evidence_collected=false`
- `data_value_extraction_performed=false`
- `accessibility_scoring_applied=false`
- `part3b_completed=false`

`evidence_collected=true` means **endpoint-probe** evidence only — not 800
pair-level observations.

## Evidence classes

| Class | Meaning |
|---|---|
| `source_origin_probe` | Official origin GET (current TSETMC/CODAL probes) |
| `candidate_endpoint_evidence` | Not collected in this probe |
| `pair_value_evidence` | Not collected in this probe |

## Modes

- `--plan` — deterministic capture plan + endpoint registry (no network)
- `--capture` — approved read-only HTTPS GET/HEAD only (resume preferred)
- `--write` — derive assessments/scores/gates/QC (no network)
- `--check` — **full** offline verification including immutable cache
- `--check-manifest-only` — tracked hashes only; **not** full evidence verification

## Cache portability

Raw payloads live under gitignored `project/stage125/raw_cache_part3b/`.
A fresh checkout without that local cache fails `--check` with
`evidence_cache_unavailable`.

## Part 3B.1 (proposed, not started)

See `README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md`.
Requires explicit user approval before any work.
