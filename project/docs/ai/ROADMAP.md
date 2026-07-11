---
roadmap_version: 1
active_research_workstream_id: stage124-gate-b-readiness
qc_scope: stage124-batch02-part03
last_completed_research_action_id: stage124-official-api-finalize
next_research_action_id: stage124-gate-b-readiness
active_maintenance_task_id: repository-driven-ai-handoff
---

# ROADMAP

The front matter above is the **machine-readable** roadmap pointer. The action IDs
must also appear in the body below. The validator checks that:

- every front-matter ID exists in the **Research actions** list,
- `next_research_action_id` comes strictly after `last_completed_research_action_id`,
- the roadmap does not contradict the repository-derived `last_stage_commit`,
- a maintenance task ID never advances the research stage.

> Research work and maintenance work are tracked separately. A Handoff/documentation
> commit advances `active_maintenance_task_id`, never the research action IDs.

## Research actions (ordered)

1. `stage124-batch02-part03-1a-5` — reviewed-evidence engine
2. `stage124-batch02-part03-1a-5-1` — partial-date manual review + precision compatibility
3. `stage124-batch02-part03-1a-5-2` — cross-record evidence aggregation, deterministic canonical
4. `stage124-batch02-part03-1a-5-3` — unified decision engine, full research↔provenance QC
5. `stage124-batch02-part03-1b-0` — Research-Intake Readiness, baseline unlock, auditable intake scaffold ✅
6. `stage124-batch02-part03-1b-1` — manual source discovery, snapshot capture, and reviewed-evidence intake for the 10 Part 3 tickers — **superseded / cancelled by official TSE API** (not completed)
7. `stage124-official-api-finalize` — Finalized verified master for 130 tickers using official TSETMC first-observed-trade dates; merged through PR #15, merge commit 22c2d0c ✅
8. `stage124-gate-b-readiness` — Gate B readiness / eligibility rebuild planning ⬅️ **next**

## Maintenance tasks

- `repository-driven-ai-handoff` — repository-derived Handoff Package (generator + validator + tests)

## Notes on ordering

`*-1b-0` prepared and hardened the intake path without adding research findings.
`*-1b-1` was superseded / cancelled by official TSE API (not completed): the
canonical listing dates for all 130 tickers were obtained from the official
TSETMC API. The verified master (`listing_master_verified_stage124.csv`) stores
dates in `first_public_trading_date_jalali` and `first_public_trading_date_gregorian`
with `date_semantics=first_observed_trading_date_from_official_tse_api`, making the
manual Human-in-the-Loop research path obsolete. The HIL dashboard and manual
intake runner have been retired.
`stage124-official-api-finalize` completed the verified master for 130 tickers and
was merged through PR #15 (merge commit 22c2d0c).
`stage124-gate-b-readiness` is planning only — Gate B execution and modeling remain
out of scope in the current PR.
