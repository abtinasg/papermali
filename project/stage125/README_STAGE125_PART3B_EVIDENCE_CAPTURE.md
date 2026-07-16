# Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot

## Scope

Authorized Part 3B pilot on the locked 80-pair event-enriched sample and the
exact 10 registered M2–M4 candidates (800 pair-candidate assessments).

## Modes

- `--plan` — deterministic capture plan + endpoint registry (no network)
- `--capture` — approved read-only HTTPS GET/HEAD only
- `--write` — derive manifests/scores/gates/QC from cached evidence (no network)
- `--check` — offline validation (no network)

## Scientific honesty

- Feature-definition gaps are recorded; values are not invented.
- Missing evidence yields null accessibility scores (never 0 by absence).
- Prediction cutoffs come only from the frozen Part 2 audit (currently
  unresolvable pending `available_at`).
- Part 3B outcomes are pilot accessibility outcomes only — not Stage126 admission.

## Network policy

Default-deny `NetworkSentinel` remains installed. Capture uses a scoped
read-only permit that restores default-deny after exit/exception.

## Part 3B.0 history

Part 3B.0 readiness artifacts remain a frozen historical baseline. Live Part 3B
state is owned by this runner.
