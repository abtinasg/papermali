# Stage124 Batch02 Part 3.1B.1B — Human-in-the-Loop Panel MVP

This directory contains the internal Streamlit panel for researching and
validating sources for the exact 10 Part03 tickers.

## Files

- `project/apps/stage124_part03_hil_panel.py` — Streamlit UI only.
- `project/src/stage124_part03_hil_panel.py` — Core operations, snapshot
  security, audit, validation and bridge invocation.
- `project/tests/test_stage124_part03_hil_panel.py` — Synthetic pytest suite.
- `project/stage124/batch02_parts/part03_hil_panel_audit.jsonl` — Append-only
  audit log created by the panel.
- `project/stage124/batch02_parts/panel_submissions/` — Immutable single-row
  submission CSVs written by the panel.

## Architecture

The panel is deliberately thin. It does **not** re-implement evidence,
canonical date or research status logic. The only bridge used is:

```python
run_stage124_batch02_part03_manual_intake.run_intake
```

- Validation-only calls `run_intake(..., apply=False, write_report=False)`.
- Apply calls `run_intake(..., apply=True)` and persists changes to the Part 3
  outputs under the configured `root` (by default the project directory itself).
- The panel never edits `registry`, `provenance`, `screening`, `summary`,
  `QC` or `manifest` files directly; all mutations are performed by the bridge
  via atomic writes.

> **Caution:** When the panel is run against the real project root,
> `Apply` genuinely mutates `part03_source_registry.csv`, provenance, screening,
> summary, QC and manifest. Use validation-only mode or a dedicated `root` for
> testing.

## Security rules

- Snapshots are stored only under `stage124/batch02_parts/snapshots_part03/<ticker>/`.
- Uploaded filenames are sanitized, extensions are allow-listed, and size is
  capped at 20 MB.
- Absolute paths, `..` and symlinks are rejected.
- SHA-256 is computed from the actual bytes and re-verified from disk.
- HTML snapshots are rendered as text/code or download only; they are never
  executed in the browser.

## Human review modes

| Mode | `content_review_status` | Notes |
|------|---------------------------|-------|
| کشف منبع | empty | Registers the source URL; optional snapshot is kept and attached |
| نیازمند بررسی | `pending_manual_review` | Snapshot allowed, no findings |
| بررسی‌شده | `reviewed` | Requires snapshot, notes, UTC timestamp |
| ردشده | `rejected` | Requires reason, creates no evidence |

`manual_reviewed_at_utc` is generated in the core as UTC; users cannot type it.

## Run the panel

```bash
python -m streamlit run project/apps/stage124_part03_hil_panel.py \
  --server.headless=true \
  --server.port=8501
```

Health check:

```bash
python - <<'PY'
from urllib.request import urlopen
print(urlopen("http://localhost:8501/_stcore/health", timeout=10).read().decode())
PY
```

Expected output: `ok`.

## Tests

```bash
python -m pytest project/tests/test_stage124_part03_hil_panel.py -q
```

Also run the broader Part03 tests before committing:

```bash
python -m pytest \
  project/tests/test_stage124_batch02_part03_manual_intake.py \
  project/tests/test_stage124_batch02_part03.py \
  project/tests/test_ai_handoff.py \
  -q
```

## Scope boundaries

- Do **not** change Stage122 or Stage123 files.
- Do **not** advance the ROADMAP, Gate B, verified master, modeling, SHAP or
  SMOTE work.
