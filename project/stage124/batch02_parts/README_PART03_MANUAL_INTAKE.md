# Stage124 Batch02 Part 3.1B.0 — Manual Evidence Intake

This package adds a **no-network, auditable** path for importing manually captured
source snapshots into the Part 3 source registry and provenance table.

## Scope

- Exact ticker scope remains the 10 Part 3 tickers.
- No Stage122/Stage123/frozen financial or target file is changed.
- No eligibility, Gate B, verified master, model, tuning, SHAP, SMOTE, calibration,
  or report is produced.
- A successful manual import is retrieval only. Evidence is accepted only after the
  existing reviewed-evidence engine recomputes all derived fields.

## Files

- `part03_manual_evidence_intake_template.csv` — header-only intake template.
- `part03_manual_evidence_intake_audit.csv` — header-only audit schema.
- `project/src/stage124_batch02_part03_manual_intake.py` — validator/import engine.
- `project/run_stage124_batch02_part03_manual_intake.py` — dry-run/apply runner.

## Snapshot location

Every snapshot must already exist under:

`project/stage124/batch02_parts/snapshots_part03/manual/`

The intake stores the path relative to `project/`, for example:

`stage124/batch02_parts/snapshots_part03/manual/khomehr_source_3.html`

Absolute paths, `..`, path escape, missing files, and hash mismatches are rejected.
The SHA-256 is recomputed locally and never trusted from the CSV.

## Retrieval semantics

The importer records `retrieval_status=manual_snapshot_imported`. This status is
registered as a successful retrieval only inside the manual-intake integration path.
It is never mislabeled as `fetched_ok` or `reused_existing_snapshot`.

Pending review rows cannot carry event/date/ordinary-share findings and therefore
cannot become evidence. Reviewed rows may support an event only when the existing
Part 3 engine validates snapshot/hash, domain authority, document specificity,
date precision, ordinary-share explicitness, and source sufficiency.

## Commands

Dry-run, with no writes:

```bash
python project/run_stage124_batch02_part03_manual_intake.py
```

Apply a populated, validated intake:

```bash
python project/run_stage124_batch02_part03_manual_intake.py \
  --intake project/stage124/batch02_parts/part03_manual_evidence_intake_template.csv \
  --apply
```

`--apply` is refused for a header-only file. Successful apply writes the registry,
provenance, audit, and apply manifest as one rollback-protected package. The runner
performs no network request.

## Current state

The committed intake and audit CSVs are intentionally header-only. No source URL,
date, event, or evidence has been added in Part 3.1B.0.
