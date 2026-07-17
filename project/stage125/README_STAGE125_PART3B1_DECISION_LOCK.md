# Stage125 Part 3B.1 — Decision Lock

**Status:** decision locked (contracts / synthetic validation only).

This versioned Part 3B.1 adjudication README is independent of the historical
Part 3B proposed-requirements README
(`README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md`), which
remains a frozen Part 3B artifact.

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
- Shared 12-month M2 window ending strictly before pair cutoff
  (`market_observation_date < pair_cutoff_date`)
- M2 minimum-valid-observation lock: 126 daily returns / 126 Amihud days
- Operational rubric mapping (candidate-level scores; pair coverage via G09–G12)
- CUT-A retention of Part 2 pair cutoff with semantic UTC timestamp compare
  (`feature_available_at <= pair_cutoff`)
- Synthetic validators only

## Still prohibited

- Network extraction / real values
- Real accessibility scoring application
- Part 3B.2 / Stage126 / modeling
- Merging any PR without explicit user approval

`part3b_completed=false`. Part 3B remains an active/incomplete accessibility
feasibility probe until candidate/pair evidence and scoring are separately
authorized.
