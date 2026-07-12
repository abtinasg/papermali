---
roadmap_version: 1
active_research_workstream_id: stage124-gate-b-execution
qc_scope: stage124-gate-b-execution
last_completed_research_action_id: stage124-gate-b-execution
next_research_action_id: stage125-modeling-readiness
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
8. `stage124-gate-b-readiness` — Gate B readiness dry-run: three eligibility rules (A/B/C) compared, per-rule impact report generated, 45 focused tests added ✅
9. `stage124-gate-b-rule-approval` — User/data owner approved Rule A (primary) and Rule B (listing-timing robustness); Rule C rejected ✅
10. `stage124-gate-b-execution` — Executed the approved Gate B rules; four sample designs, canonical + filtered outputs, 58 focused tests (736 passed, 1 skipped, local results — no GitHub Actions) ✅
11. `stage125-modeling-readiness` — Post-Gate-B modeling readiness; modeling remains prohibited until approved ⬅️ **next**

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
`stage124-gate-b-readiness` completed the dry-run comparison of three eligibility
rules (A/B/C) with per-rule impact reports and 45 focused tests. Gate B execution
and modeling were out of scope at that point.
`stage124-gate-b-rule-approval` recorded explicit user/data-owner approval of
Rule A (primary, `first_observed_trading_date <= fiscal_year_end`) and Rule B
(listing-timing robustness, `first_observed_trading_date <= fiscal_year_start`);
Rule C (`first_observed_trading_year < fiscal_year`) was rejected.
`stage124-gate-b-execution` applied the approved rules to the frozen Stage123
data and verified listing master, producing four sample designs (main Rule A =
1013 pairs / 81 pos / 932 neg; main Rule B = 994 / 80 / 914) with canonical and
filtered outputs and 58 focused tests (736 passed, 1 skipped, local results). **No modeling was started.**
`stage125-modeling-readiness` is the next action — modeling remains prohibited
until post-Gate-B modeling readiness is approved.
