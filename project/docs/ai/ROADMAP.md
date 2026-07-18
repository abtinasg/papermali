---
roadmap_version: 1
active_research_workstream_id: stage125-research-design-readiness
qc_scope: stage125-part3b1d-same-five-metadata-resolution-capture
last_completed_research_action_id: stage125-part3a-decision-lock
next_research_action_id: stage125-part3b-evidence-capture
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
11. `stage125-research-design-readiness` — Stage125 Research Design & Data Readiness (Parts 0–3A.1); **no modeling** in this stage — modeling remains prohibited until Stage126 is approved ✅
12. `stage125-part3a-decision-lock` — Part 3A.1 user-approved pilot decision lock (rubric approval, G09–G14 thresholds, locked 80-pair event-enriched selection); decision record only, **no evidence collection** ✅
13. `stage125-part3b-evidence-capture` — Part 3B accessibility feasibility probe (**active / incomplete**; source-origin probes done; Part 3B.1 Decision Lock recorded; candidate/pair value extraction and real scoring still prohibited; not Stage126 admission) ⬅️ **next / active**

## Maintenance tasks

- `repository-driven-ai-handoff` — repository-derived Handoff Package (generator + validator + tests)
- `stage125-part0-research-design-lock` — record the frozen Stage125 research contract in human docs (see [`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md)); documentation-only, advances no research action
- `stage125-part1-data-contract` — Stage125 Part 1 data dictionary & provenance contract (data dictionary M1–M4, identifier/time contract, source registry, provenance manifest schema, data-admission-gate template, immutable raw/cache policy, read-only M1 provenance-gap audit); contracts/audit only, **no modeling, no extraction, no Part 2**; advances no research action
- `stage125-part2-prediction-time-contract` — Stage125 Part 2 prediction-time & leakage contract (prediction cutoff rules, feature availability M1–M4, revision policy, tie-breaking, anti-leakage checklist with 8 machine-testable checks, per-pair cutoff/feature/leakage audit preserving all 1200 pairs); contract/audit only, **no modeling, no extraction, no eligibility changes**; advances no research action ✅
- `stage125-part3a-pilot-protocol-lock` — Stage125 Part 3A accessibility & pilot protocol lock (candidate inventory freeze, proposed accessibility rubric, gate decision protocol, sampling frame summary, pilot-size options, Part 3B evidence schema); protocol only, **no evidence collection, no network access, no modeling**; advances no research action ✅
- `stage125-part3a1-decision-lock` — Stage125 Part 3A.1 user-approved pilot decision lock (rubric approval record, G09–G14 pilot thresholds, locked event-enriched pilot pair selection); decision record only, **no evidence collection, no network access, no modeling**; advances no research action ✅
- `stage125-part3b0-evidence-readiness` — Stage125 Part 3B.0 evidence capture readiness (schema validator, immutable cache contract, default-deny network sentinel, pure Gate engine scaffolding, header-only templates); infrastructure/readiness only; frozen historical baseline after Part 3B authorization; advances no research action ✅
- `stage125-part3b1-decision-lock` — Stage125 Part 3B.1 feature-definition & scoring adjudication lock (M2-A modified, M3-C+CBI-A, M4-A, R-A, CUT-A); schema/formula contracts + synthetic validation only; **no network, no real extraction, no real scoring, no modeling**; advances no research action ✅
- `stage125-part3b1a-cut-a-available-at-operationalization-lock` — Stage125 Part 3B.1A CUT-A available-at operationalization lock (`PublishDateTime` for exact version-bound CODAL documents; `SentDateTime` audit-only); schema/pure parsers/synthetic validation only; **no network, no real available_at assignment, no cutoff resolution, no extraction, no scoring, no modeling**; advances no research action ✅
- `stage125-part3b1b-codal-document-binding-mini-pilot` — Stage125 Part 3B.1B controlled CODAL predictor-document binding mini-pilot (exactly five locked rows; document metadata/provenance only; at most one authorized `www.codal.ir` GET); **no financial-value extraction, no accessibility scoring, no Gate application, no cutoff audit mutation, no Part 3B.2 / Stage126 / modeling**; advances no research action
- `stage125-part3b1c-document-binding-resolution-decision-lock` — Stage125 Part 3B.1C offline document-binding failure adjudication, normalization/source hierarchy lock, and future capture authorization proposal only; **no network, no new capture, no evidence mutation, no available_at assignment, no extraction/scoring/Gates, no 80-row scale-up, no Part 3B.2 / Stage126 / modeling**; advances no research action
- `stage125-part3b1d-same-five-metadata-resolution-capture` — Stage125 Part 3B.1D controlled same-five metadata-resolution capture (exactly four authorized `www.codal.ir` Decision.aspx GETs; اردستان zero requests; metadata provenance only; raw payloads gitignored); **no binding-status mutation, no available_at assignment, no financial-value extraction, no accessibility scoring, no Gate application, no 80-row scale-up, no Part 3B.2 / Stage126 / modeling**; advances no research action

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
`stage125-research-design-readiness` completed Parts 0–3A.1 under Stage125 (no
modeling). `stage125-part3a-decision-lock` recorded the approved rubric,
G09–G14 pilot thresholds, and locked 80-pair event-enriched selection
(39 positive / 41 negative; 26 tickers; 10 known industries; 53 industry-present
pairs; 27 industry-missing pairs). `stage125-part3b-evidence-capture` is
**active / incomplete** (origin probes only). `stage125-part3b1-decision-lock`
records approved feature/scoring/cutoff adjudication contracts without authorizing
real extraction or scoring. `stage125-part3b1a-cut-a-available-at-operationalization-lock`
operationalizes CUT-A `available_at` as `PublishDateTime` of an exact
version-bound CODAL letter without assigning real timestamps or resolving pilot
cutoffs. `stage125-part3b1b-codal-document-binding-mini-pilot` captures
document-metadata binding evidence for five locked rows only and does not
complete Part 3B or resolve the 80-row pilot cutoff. See
[`STAGE125_RESEARCH_DESIGN.md`](STAGE125_RESEARCH_DESIGN.md). Modeling remains
prohibited until Stage126 (M1 Financial Baseline) is explicitly approved.
