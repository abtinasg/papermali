# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage124-batch02-part03`

Manual public-entry-date research for the current **10 tickers** (still
`pending_manual_research`):

| # | Ticker |
|---|--------|
| 1 | خمهر |
| 2 | خنصیر |
| 3 | خوساز |
| 4 | خچرخش |
| 5 | خکمک |
| 6 | دروز |
| 7 | دسبحا |
| 8 | دیران |
| 9 | رانفور |
| 10 | رمپنا |

### Next action — `stage124-batch02-part03-1b-1`

**Execute the actual manual research and populate the dedicated intake safely.**
For each discovered source, record only source-backed facts. Store a snapshot under
the approved Part 3 snapshot directory, recompute SHA-256, and keep event/date and
ordinary-share findings empty unless they are explicit in the stored source.

The intake runner must first pass in dry-run mode. Registry changes require the
explicit `--apply` flag. No canonical listing date is accepted merely because a
source was discovered or a snapshot was stored; the existing reviewed-evidence
engine remains the decision authority.

## Completed immediately before this task

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
  The committed intake is header-only; no URL, snapshot, event, or date was added.

## Not in scope yet (do NOT start)

- ❌ Gate B execution
- ❌ `listing_master_verified_stage124.csv` (verified master)
- ❌ Modeling, tuning, SHAP, SMOTE, calibration, or article reporting

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
