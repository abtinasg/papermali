---
roadmap_version: 1
active_research_workstream_id: stage124-batch02-part03
last_completed_research_action_id: stage124-batch02-part03-1a-5-3
next_research_action_id: stage124-batch02-part03-1b-0
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
4. `stage124-batch02-part03-1a-5-3` — unified decision engine, full research↔provenance QC ✅ **last completed**
5. `stage124-batch02-part03-1b-0` — **Research-Intake Readiness, baseline unlock, auditable manual snapshot import** ⬅️ **next**

## Maintenance tasks

- `repository-driven-ai-handoff` — this AI Handoff Package (in progress)

## Notes on ordering

`*-1b-0` follows `*-1a-5-3`: the `1a.*` line finishes the evidence/decision engine;
`1b.0` opens the research-intake phase. Modeling, Gate B, and the verified listing
master are all **after** the manual research is complete — they are not in scope yet.
