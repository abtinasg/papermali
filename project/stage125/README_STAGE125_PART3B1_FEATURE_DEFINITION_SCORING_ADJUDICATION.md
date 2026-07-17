# Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock

**Status:** decision locked (contracts / synthetic validation only).

User-approved selections:

| decision_id | selected_answer |
|---|---|
| m2_feature_definitions | M2-A_modified |
| m3_feature_definitions | M3-C |
| m4_feature_definitions | M4-A |
| rubric_score_mapping_0_5 | R-A |
| cbi_endpoint_provenance | CBI-A |
| available_at_and_cutoff_rules | CUT-A |

## Locked scope

- Schema/formula contracts for M2/M3/M4
- M2 market window ends strictly before pair cutoff
  (`market_observation_date < pair_cutoff_date`); equal-to-cutoff trading days
  are rejected
- Operational rubric mapping (candidate-level scores; pair coverage via G09–G12)
- CUT-A retention of Part 2 pair cutoff
  (`feature_available_at <= pair_cutoff` unchanged)
- Synthetic validators only

## Still prohibited

- Network extraction / real values
- Real accessibility scoring application
- Part 3B.2 / Stage126 / modeling
- Merging any PR without explicit user approval

`part3b_completed=false`. Part 3B remains an active/incomplete accessibility
feasibility probe until candidate/pair evidence and scoring are separately
authorized.
