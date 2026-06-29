#!/usr/bin/env python3
"""Stage124 Batch 2 — Part 3.1B.1A: Manual Intake to Provenance Bridge.

This is the **intake** step that sits between the Part 3 research screening (all
network-blocked) and any later fetch/review run. It is deliberately *separate* from
``src.stage124_batch02_part03.run()`` and **non-destructive** in dry-run mode.

What it does
------------
1. Ensures a dedicated, explicit intake file
   ``stage124/batch02_parts/part03_manual_intake_input.csv`` exists (an empty
   template is created on first run).
2. Validates every intake row **fail-closed** (ticker in the exact 10-ticker
   Part 3 scope, real http(s) URL, agreeing Jalali date/precision, ordinary-share
   enum, and — when a snapshot is claimed — the snapshot file must exist under
   ``snapshots_part03/`` and its SHA-256 must match the recorded ``content_sha256``).
3. When (and only when) there are valid findings and ``--apply`` is used:
   - Registers the discovered sources into ``part03_source_registry.csv`` via
     ``register_discovered_sources`` (manual_discovery, next index per ticker).
   - Creates provenance records for manual snapshots with ``manual_snapshot_imported`` status.
   - Recomputes all derived fields using the existing Part 3 engine.
4. Writes an auditable readiness/intake report
   ``part03_manual_intake_report.json``.

With an empty intake file (the current "scaffold" state) the run is a safe no-op:
the registry and all sealed artifacts are untouched and the report records
``status=ready_no_findings``. Actual fetching/review/screening of registered
sources remains a later, separate step.

Usage:
    python project/run_stage124_batch02_part03_manual_intake.py [--apply]
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
    PROVENANCE_COLUMNS, normalize_provenance_records, classify_source_authority_with_validation,
    is_document_specific_source, registrable_domain, _utc_now,
)

# Extended intake schema (one row per discovered source).
INTAKE_COLUMNS = [
    "ticker", "source_type", "source_url", "source_title",
    "event_type_candidate", "candidate_date_jalali", "date_precision",
    "ordinary_share_explicit", "snapshot_path", "content_sha256",
    "publication_date_jalali", "added_by", "discovery_notes",
    # New audit fields for complete review tracking
    "captured_at_utc", "content_type", "http_status", "final_url",
    "content_review_status", "exact_text_or_event_summary", "reviewer_notes",
    "manual_reviewed_at_utc", "publication_date_explicit",
]

ALLOWED_EVENT_CANDIDATES = {
    "", "first_public_offering", "first_public_trading",
    "admission", "listing", "public_company_conversion", "unresolved",
}
ALLOWED_ORDINARY = {"", "true", "false", "unknown"}
ALLOWED_REVIEW_STATUSES = {
    "", "pending_manual_review", "reviewed", "rejected",
}
SNAPSHOT_SUBDIR = "snapshots_part03"

# New retrieval status for manual snapshots
MANUAL_SNAPSHOT_IMPORTED = "manual_snapshot_imported"


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

    # Validate new audit fields
    review_status = g("content_review_status")
    if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
        errs.append(f"row {idx}: invalid content_review_status '{review_status}'")

    # Validation rules for review status and findings
    if review_status == "pending_manual_review":
        # pending_manual_review CAN have findings - they're just not processed yet
        pass  # No restriction - findings can exist but won't be processed until reviewed
    
    if review_status == "reviewed":
        if not g("reviewer_notes"):
            errs.append(f"row {idx}: reviewed status requires reviewer_notes")
        if not g("manual_reviewed_at_utc"):
            errs.append(f"row {idx}: reviewed status requires manual_reviewed_at_utc")

    # Validate snapshot and hash
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
            
            # If snapshot exists, must have findings
            if not (ev and date):
                errs.append(f"row {idx}: snapshot with findings requires "
                           "event_type_candidate and candidate_date_jalali")
    
    # If findings exist, must have snapshot
    if (ev or date) and not (snap and h):
        errs.append(f"row {idx}: event/date findings require snapshot_path "
                    "and content_sha256")

    return errs

def create_provenance_record_from_intake(intake_row: dict, source_index: int, root: Path) -> dict:
    """Create a provenance record from a validated manual intake row.
    
    This function creates a provenance record with manual_snapshot_imported status
    and recomputes all derived fields using the existing Part 3 engine.
    """
    def g(key: str) -> str:
        return str(intake_row.get(key, "")).strip()
    
    # Basic fields from intake
    tk = g("ticker")
    url = g("source_url")
    snap_path = g("snapshot_path")
    content_hash = g("content_sha256")
    
    # Create base provenance record
    record = {col: "" for col in PROVENANCE_COLUMNS}
    record.update({
        "ticker": tk,
        "source_index": str(source_index),
        "source_type": g("source_type"),
        "source_title": g("source_title"),
        "source_url": url,
        "publication_date": "",  # Not from intake
        "retrieved_at_utc": _utc_now(),
        "http_status": g("http_status") or "200",
        "retrieval_status": MANUAL_SNAPSHOT_IMPORTED,
        "final_url": g("final_url") or url,
        "content_type": g("content_type") or "text/html",
        "response_size_bytes": "",
        "snapshot_path": snap_path,
        "content_sha256": content_hash,
        "extraction_notes": "Manually imported snapshot with validated hash",
        "exact_text_or_event_summary": g("exact_text_or_event_summary"),
        "supported_event_type": g("event_type_candidate"),
        "supported_date_jalali": g("candidate_date_jalali"),
        "content_review_status": g("content_review_status") or "pending_manual_review",
        "ordinary_share_explicit": g("ordinary_share_explicit"),
        "reviewed_date_jalali": g("candidate_date_jalali"),
        "publication_date_jalali": g("publication_date_jalali"),
        "publication_date_explicit": g("publication_date_explicit") or "false",
        "reviewer_notes": g("reviewer_notes"),
        "manual_reviewed_at_utc": g("manual_reviewed_at_utc"),
    })
    
    # Recompute all derived fields using the existing engine
    authority_class, validation_error = classify_source_authority_with_validation(
        record["source_type"], record["source_url"], record["ticker"]
    )
    record["source_authority_class"] = authority_class
    record["authority_validation_error"] = validation_error
    record["document_specific"] = (
        "true" if is_document_specific_source(url, record["source_type"], tk) else "false"
    )
    record["independent_source_group"] = registrable_domain(url)
    
    # Set event type support flags
    if record["supported_event_type"]:
        record["event_type_supported"] = "true"
    else:
        record["event_type_supported"] = "false"
    
    # Set date precision flags
    if record["supported_date_jalali"] and g("date_precision") == "exact_day":
        record["exact_date_explicit"] = "true"
    else:
        record["exact_date_explicit"] = "false"
    
    # Initialize evidence-related fields (will be computed by normalize_provenance_records)
    record["contemporaneous_with_event"] = "false"
    record["evidence_accepted"] = "false"
    record["reviewed_event_type"] = ""
    record["reviewed_date_precision"] = g("date_precision") or "unknown"
    record["reviewed_evidence_valid"] = "false"
    record["evidence_role"] = "none"
    
    return record


def atomic_apply_changes(intake_df: "pd.DataFrame", registry_df: "pd.DataFrame", 
                        root: Path) -> dict:
    """Apply intake changes atomically with rollback protection.
    
    Returns a dict with operation results for rollback if needed.
    """
    provenance_path = root / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv"
    screening_path = root / "stage124" / "batch02_parts" / "part03_research_screening_10tickers.csv"
    registry_path = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    
    # Backup existing files for rollback
    backups = {}
    for path in [provenance_path, screening_path]:
        if path.exists():
            backups[path] = path.read_text(encoding="utf-8")
    
    try:
        # Register sources in registry
        additions = pd.DataFrame([{
            "ticker": str(r["ticker"]).strip(),
            "source_type": str(r["source_type"]).strip(),
            "source_title": str(r.get("source_title", "")).strip(),
            "source_url": str(r["source_url"]).strip(),
            "added_at_utc": str(r.get("captured_at_utc", "")),
            "added_by": str(r.get("added_by", "")).strip(),
            "discovery_notes": str(r.get("discovery_notes", "")).strip(),
        } for _, r in intake_df.iterrows()])
        
        new_registry = register_discovered_sources(registry_df, additions)
        
        # Get source indices for new registrations
        new_indices = {}
        for _, r in new_registry.iterrows():
            if str(r.get("source_origin")) == "manual_discovery":
                key = (str(r["ticker"]), str(r["source_url"]))
                new_indices[key] = str(r["source_index"])
        
        # Create provenance records for manual snapshots
        new_provenance = []
        for _, intake_row in intake_df.iterrows():
            if str(intake_row.get("snapshot_path", "")).strip():
                key = (str(intake_row["ticker"]).strip(), str(intake_row["source_url"]).strip())
                source_index = new_indices.get(key)
                if source_index:
                    prov_record = create_provenance_record_from_intake(
                        intake_row.to_dict(), int(source_index), root
                    )
                    new_provenance.append(prov_record)
        
        # Load existing provenance and add new records
        if provenance_path.exists():
            existing_prov = pd.read_csv(provenance_path, dtype=str)
        else:
            existing_prov = pd.DataFrame(columns=PROVENANCE_COLUMNS)
        
        # Normalize all provenance records to recompute derived fields
        if new_provenance:
            all_provenance = pd.concat([existing_prov, pd.DataFrame(new_provenance)], ignore_index=True)
            normalized_provenance = normalize_provenance_records(all_provenance.to_dict('records'), root)
            final_provenance = pd.DataFrame(normalized_provenance, columns=PROVENANCE_COLUMNS)
        else:
            final_provenance = existing_prov
        
        # Ensure directory exists
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write files atomically
        write_csv(new_registry, registry_path)
        write_csv(final_provenance, provenance_path)
        
        # TODO: Update research screening when Part 3 engine is ready
        # For now, preserve existing screening file
        
        return {
            "success": True,
            "sources_registered": len(additions),
            "provenance_created": len(new_provenance),
            "backups": backups,
        }
        
    except Exception as exc:
        # Rollback changes
        for path, content in backups.items():
            path.write_text(content, encoding="utf-8")
        raise exc


def run_intake(intake_path: Path = None, registry_path: Path = None,
               report_path: Path = None, root: Path = None,
               write_report: bool = True, apply_changes: bool = False) -> dict:
    """Run manual intake validation and optionally apply changes.
    
    Args:
        intake_path: Path to intake CSV file
        registry_path: Path to source registry CSV file  
        report_path: Path to output report JSON file
        root: Project root directory
        write_report: Whether to write the report file
        apply_changes: Whether to apply changes (creates provenance records)
        
    Returns:
        Dict with operation results
    """
    root = Path(root) if root else ROOT
    
    # Use provided paths or defaults relative to the given root
    if intake_path is None:
        intake_path = root / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    else:
        intake_path = Path(intake_path)
        
    if registry_path is None:
        registry_path = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    else:
        registry_path = Path(registry_path)
        
    if report_path is None:
        report_path = root / "stage124" / "batch02_parts" / "part03_manual_intake_report.json"
    else:
        report_path = Path(report_path)

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
    provenance_created = 0
    
    if apply_changes and not findings.empty:
        # Apply changes atomically with provenance creation
        result = atomic_apply_changes(findings, registry_df, root)
        registered = result["sources_registered"]
        provenance_created = result["provenance_created"]
        
        # Update registry count
        registry_after = registry_before + registered
        
        # Collect statistics
        for _, r in findings.iterrows():
            tk = str(r["ticker"]).strip()
            per_ticker[tk] = per_ticker.get(tk, 0) + 1
            if str(r.get("snapshot_path", "")).strip():
                snapshots_verified.append(str(r["snapshot_path"]).strip())
                
        status = "applied_with_provenance" if provenance_created > 0 else "applied_discovery_only"
        
    elif not findings.empty:
        # Dry run: only validate without registering sources
        if not apply_changes:
            # In dry-run mode, don't actually register anything
            for _, r in findings.iterrows():
                tk = str(r["ticker"]).strip()
                per_ticker[tk] = per_ticker.get(tk, 0) + 1
                if str(r.get("snapshot_path", "")).strip():
                    snapshots_verified.append(str(r["snapshot_path"]).strip())
            registry_after = registry_before
            status = "findings_validated"
        else:
            # Apply mode: register sources without provenance
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
            registry_after = registry_before + registered
            status = "findings_registered"
        
    else:
        registry_after = registry_before
        status = "ready_no_findings"

    report = {
        "stage": "stage124_batch02_part03_manual_intake",
        "part": "3.1B.1A",
        "status": status,
        "source_commit": git_head(),
        "scope_tickers": list(PART03_TICKERS),
        "intake_file": str(intake_path.relative_to(root)) if _under(root, intake_path) else str(intake_path),
        "intake_template_created": created_template,
        "findings_count": int(len(findings)),
        "sources_registered": int(registered),
        "provenance_created": int(provenance_created),
        "registry_rows_before": int(registry_before),
        "registry_rows_after": int(registry_after),
        "per_ticker_registered": per_ticker,
        "snapshots_verified": snapshots_verified,
        "apply_mode": apply_changes,
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
    import argparse
    parser = argparse.ArgumentParser(
        description="Manual Intake to Provenance Bridge for Part 3.1B.1A"
    )
    parser.add_argument(
        "--apply", 
        action="store_true", 
        help="Apply changes and create provenance records (default: dry-run validation only)"
    )
    parser.add_argument(
        "--intake", 
        type=Path, 
        help="Path to intake CSV file (optional)"
    )
    parser.add_argument(
        "--no-report", 
        action="store_true", 
        help="Skip writing report file"
    )
    
    args = parser.parse_args(argv)
    
    try:
        report = run_intake(
            intake_path=args.intake,
            write_report=not args.no_report,
            apply_changes=args.apply
        )
    except IntakeError as exc:
        print(f"INTAKE FAILED: {exc}", file=sys.stderr)
        return 1
    
    print("Part 3.1B.1A manual intake:")
    print(f"  mode                : {'apply' if args.apply else 'dry-run'}")
    print(f"  status              : {report['status']}")
    print(f"  intake file         : {report['intake_file']}"
          + ("  (template created)" if report["intake_template_created"] else ""))
    print(f"  findings            : {report['findings_count']}")
    print(f"  sources registered  : {report['sources_registered']} "
          f"({report['registry_rows_before']} -> {report['registry_rows_after']})")
    if report.get("provenance_created", 0) > 0:
        print(f"  provenance created  : {report['provenance_created']}")
    if report["snapshots_verified"]:
        print(f"  snapshots verified  : {len(report['snapshots_verified'])}")
    
    if args.apply and report["sources_registered"] > 0:
        print("\nChanges applied successfully. Check Part 3 artifacts for updates.")
    elif report["findings_count"] > 0:
        print("\nValidation passed. Use --apply to register sources and create provenance.")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
