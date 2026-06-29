#!/usr/bin/env python3
"""Stage124 Batch 2 — Part 3.1B.0: Research-Intake Readiness & auditable manual import.

This is the **intake** step that sits between the Part 3 research screening (all
network-blocked) and any later fetch/review run. It is deliberately *separate* from
``src.stage124_batch02_part03.run()`` and **non-destructive**: it never re-runs the
screening pipeline, never overwrites the sealed Part 3.1A.5.3 artifacts, and never
fabricates a URL, date, snapshot, or hash.

What it does
------------
1. Ensures a dedicated, explicit intake file
   ``stage124/batch02_parts/part03_manual_intake_input.csv`` exists (an empty
   template is created on first run).
2. Validates every intake row **fail-closed** (ticker in the exact 10-ticker
   Part 3 scope, real http(s) URL, agreeing Jalali date/precision, ordinary-share
   enum, and — when a snapshot is claimed — the snapshot file must exist under
   ``snapshots_part03/`` and its SHA-256 must match the recorded ``content_sha256``).
3. When (and only when) there are valid findings, it registers the discovered
   sources into ``part03_source_registry.csv`` via
   ``register_discovered_sources`` (manual_discovery, next index per ticker).
4. Writes an auditable readiness/intake report
   ``part03_manual_intake_report.json``.

With an empty intake file (the current "scaffold" state) the run is a safe no-op:
the registry and all sealed artifacts are untouched and the report records
``status=ready_no_findings``. Actual fetching/review/screening of registered
sources remains a later, separate step.

Usage:
    python project/run_stage124_batch02_part03_manual_intake.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from src.stage124_batch02_part03 import (  # noqa: E402
    PART03_DIR, PART03_TICKERS, ROOT, SOURCE_REGISTRY_PATH,
    build_seed_registry_df, load_source_registry, validate_source_registry,
    register_discovered_sources, validate_worklist_date_precision,
    _worklist_url_ok, _is_sha256, sha, git_head, write_csv,
)

# Explicit intake schema (one row per discovered source).
INTAKE_COLUMNS = [
    "ticker", "source_type", "source_url", "source_title",
    "event_type_candidate", "candidate_date_jalali", "date_precision",
    "ordinary_share_explicit", "snapshot_path", "content_sha256",
    "publication_date_jalali", "added_by", "discovery_notes",
]

ALLOWED_EVENT_CANDIDATES = {
    "", "first_public_offering", "first_public_trading",
    "admission", "listing", "public_company_conversion", "unresolved",
}
ALLOWED_ORDINARY = {"", "true", "false", "unknown"}
SNAPSHOT_SUBDIR = "snapshots_part03"


class IntakeError(RuntimeError):
    """Fail-closed intake validation error."""


DEFAULT_INTAKE_PATH = PART03_DIR / "part03_manual_intake_input.csv"
DEFAULT_REPORT_PATH = PART03_DIR / "part03_manual_intake_report.json"


def empty_template() -> "pd.DataFrame":
    return pd.DataFrame(columns=INTAKE_COLUMNS)


def load_intake(path: Path) -> "pd.DataFrame":
    df = pd.read_csv(path, dtype=str).fillna("")
    for col in INTAKE_COLUMNS:
        if col not in df.columns:
            raise IntakeError(f"intake file missing required column: {col}")
    # Drop fully-blank rows (a template may contain none).
    non_empty = df[INTAKE_COLUMNS].apply(
        lambda r: any(str(v).strip() for v in r), axis=1
    )
    return df[non_empty].reset_index(drop=True)


def validate_intake_row(row: dict, idx: int, root: Path) -> list[str]:
    errs: list[str] = []

    def g(key: str) -> str:
        return str(row.get(key, "")).strip()

    tk = g("ticker")
    if tk not in PART03_TICKERS:
        errs.append(f"row {idx}: ticker '{tk}' out of Part 3 scope")

    url = g("source_url")
    if not url:
        errs.append(f"row {idx}: source_url is required")
    elif not _worklist_url_ok(url):
        errs.append(f"row {idx}: invalid source_url '{url}'")

    if not g("source_type"):
        errs.append(f"row {idx}: source_type is required")

    ev = g("event_type_candidate")
    if ev not in ALLOWED_EVENT_CANDIDATES:
        errs.append(f"row {idx}: invalid event_type_candidate '{ev}'")

    od = g("ordinary_share_explicit").lower()
    if od not in ALLOWED_ORDINARY:
        errs.append(f"row {idx}: invalid ordinary_share_explicit '{od}'")

    date = g("candidate_date_jalali")
    prec = g("date_precision") or "unknown"
    if not validate_worklist_date_precision(date, prec):
        errs.append(f"row {idx}: candidate_date_jalali '{date}' disagrees with "
                    f"date_precision '{prec}'")

    snap = g("snapshot_path")
    h = g("content_sha256")
    if snap or h:
        if not (snap and h):
            errs.append(f"row {idx}: snapshot_path and content_sha256 must be "
                        "provided together")
        else:
            if SNAPSHOT_SUBDIR not in snap.replace("\\", "/"):
                errs.append(f"row {idx}: snapshot must live under {SNAPSHOT_SUBDIR}/")
            if not _is_sha256(h):
                errs.append(f"row {idx}: invalid content_sha256")
            snap_abs = (Path(snap) if Path(snap).is_absolute() else root / snap)
            if not snap_abs.is_file():
                errs.append(f"row {idx}: snapshot file not found: {snap}")
            elif _is_sha256(h) and sha(snap_abs) != h:
                errs.append(f"row {idx}: snapshot SHA-256 does not match "
                            "content_sha256 (no fabricated evidence)")
    return errs


def run_intake(intake_path: Path = None, registry_path: Path = None,
               report_path: Path = None, root: Path = None,
               write_report: bool = True) -> dict:
    intake_path = Path(intake_path) if intake_path else DEFAULT_INTAKE_PATH
    registry_path = Path(registry_path) if registry_path else SOURCE_REGISTRY_PATH
    report_path = Path(report_path) if report_path else DEFAULT_REPORT_PATH
    root = Path(root) if root else ROOT

    intake_path.parent.mkdir(parents=True, exist_ok=True)

    created_template = False
    if not intake_path.exists():
        write_csv(empty_template(), intake_path)
        created_template = True
        findings = empty_template()
    else:
        findings = load_intake(intake_path)

    # Fail-closed validation of every finding.
    errors: list[str] = []
    for i, (_, row) in enumerate(findings.iterrows()):
        errors.extend(validate_intake_row(row.to_dict(), i, root))
    if errors:
        raise IntakeError("intake validation failed:\n  - " + "\n  - ".join(errors))

    # Load + validate the registry (source of truth).
    if registry_path.exists():
        registry_df = load_source_registry(registry_path)
    else:
        registry_df = build_seed_registry_df()
    ok, reg_errors = validate_source_registry(registry_df)
    if not ok:
        raise IntakeError(f"invalid source registry: {reg_errors[:5]}")
    registry_before = len(registry_df)

    registered = 0
    per_ticker: dict[str, int] = {}
    snapshots_verified: list[str] = []
    if not findings.empty:
        additions = pd.DataFrame([{
            "ticker": str(r["ticker"]).strip(),
            "source_type": str(r["source_type"]).strip(),
            "source_title": str(r.get("source_title", "")).strip(),
            "source_url": str(r["source_url"]).strip(),
            "added_at_utc": "",
            "added_by": str(r.get("added_by", "")).strip(),
            "discovery_notes": str(r.get("discovery_notes", "")).strip(),
        } for _, r in findings.iterrows()])
        new_registry = register_discovered_sources(registry_df, additions)
        write_csv(new_registry, registry_path)
        registered = len(new_registry) - registry_before
        for _, r in findings.iterrows():
            tk = str(r["ticker"]).strip()
            per_ticker[tk] = per_ticker.get(tk, 0) + 1
            if str(r.get("snapshot_path", "")).strip():
                snapshots_verified.append(str(r["snapshot_path"]).strip())

    status = "ready_no_findings" if findings.empty else "findings_registered"
    report = {
        "stage": "stage124_batch02_part03_manual_intake",
        "part": "3.1B.0",
        "status": status,
        "source_commit": git_head(),
        "scope_tickers": list(PART03_TICKERS),
        "intake_file": str(intake_path.relative_to(root)) if _under(root, intake_path) else str(intake_path),
        "intake_template_created": created_template,
        "findings_count": int(len(findings)),
        "sources_registered": int(registered),
        "registry_rows_before": int(registry_before),
        "registry_rows_after": int(registry_before + registered),
        "per_ticker_registered": per_ticker,
        "snapshots_verified": snapshots_verified,
    }
    if write_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
    return report


def _under(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    try:
        report = run_intake()
    except IntakeError as exc:
        print(f"INTAKE FAILED: {exc}", file=sys.stderr)
        return 1
    print("Part 3.1B.0 manual intake:")
    print(f"  status              : {report['status']}")
    print(f"  intake file         : {report['intake_file']}"
          + ("  (template created)" if report["intake_template_created"] else ""))
    print(f"  findings            : {report['findings_count']}")
    print(f"  sources registered  : {report['sources_registered']} "
          f"({report['registry_rows_before']} -> {report['registry_rows_after']})")
    if report["snapshots_verified"]:
        print(f"  snapshots verified  : {len(report['snapshots_verified'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
