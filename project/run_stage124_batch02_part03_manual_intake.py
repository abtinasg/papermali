#!/usr/bin/env python3
"""Stage124 Batch 2 -- Part 3.1B.1A: Manual Intake to Provenance Bridge.

This step bridges the manual-research intake file to the provenance pipeline for
the exact 10 Part 3 tickers.  It is deliberately *separate* from
``src.stage124_batch02_part03.run()`` and **non-destructive** in dry-run mode.

Safety properties
-----------------
* no network requests;
* dry-run by default -- changes are persisted only with ``--apply``;
* exact input schema and fail-closed row validation;
* snapshot paths must be safe relative paths confined beneath
  ``stage124/batch02_parts/snapshots_part03/``;
* snapshot SHA-256 is recomputed from the stored file;
* Stage122/Stage123 and sealed Part 3 outputs are never written;
* all outputs are built in memory, validated, then written atomically via
  temp files and ``os.replace``; any failure rolls back ALL files.

On ``--apply`` the following outputs are (re)computed and written atomically:

* ``part03_source_registry.csv``
* ``part03_source_provenance_10tickers.csv``
* ``part03_research_screening_10tickers.csv``
* ``part03_research_summary.json``
* ``part03_qc_report.json``
* ``part03_manual_intake_report.json``
* ``part03_manual_intake_apply_manifest.json``

Human-in-the-Loop rules
------------------------
``content_review_status=pending_manual_review``  rows must NOT carry
``event_type_candidate``, ``candidate_date_jalali``,
``ordinary_share_explicit`` = true/false, ``reviewer_notes``, or
``manual_reviewed_at_utc``.

To register a finding the row must have:
``content_review_status=reviewed``, non-empty ``reviewer_notes``, a valid
``manual_reviewed_at_utc``, a valid ``snapshot_path``, and a ``content_sha256``
that matches the file on disk.

Usage:
    python project/run_stage124_batch02_part03_manual_intake.py [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from src.stage124_batch02_part03 import (  # noqa: E402
    FETCHED_STATUSES,
    PART03_DIR,
    PART03_TICKERS,
    PROVENANCE_COLUMNS,
    ROOT,
    SOURCE_REGISTRY_COLUMNS,
    SOURCE_REGISTRY_PATH,
    build_seed_registry_df,
    build_research_screening,
    build_source_provenance,
    build_tickers_df,
    classify_source_authority_with_validation,
    git_head,
    is_document_specific_source,
    is_valid_exact_jalali_date,
    load_company_names,
    load_historical_tsetmc,
    load_source_registry,
    normalize_provenance_records,
    read_csv,
    register_discovered_sources,
    registrable_domain,
    run_part03_qc,
    sha,
    validate_source_registry,
    validate_worklist_date_precision,
    write_csv,
    _is_sha256,
    _utc_now,
    _worklist_url_ok,
)

# ---------------------------------------------------------------------------
# Intake schema
# ---------------------------------------------------------------------------
INTAKE_COLUMNS = [
    "ticker",
    "source_type",
    "source_url",
    "source_title",
    "event_type_candidate",
    "candidate_date_jalali",
    "date_precision",
    "ordinary_share_explicit",
    "snapshot_path",
    "content_sha256",
    "publication_date_jalali",
    "added_by",
    "discovery_notes",
    "content_review_status",
    "reviewer_notes",
    "manual_reviewed_at_utc",
]

ALLOWED_SOURCE_TYPES = {
    "codal_official",
    "regulatory_official",
    "news_agency",
    "credible_news",
    "official_market_news",
    "market_data",
    "official_market_data_audit",
    "market_information_aggregator",
    "aggregator",
    "company_official",
}
ALLOWED_EVENT_CANDIDATES = {
    "",
    "first_public_offering",
    "first_public_trading",
    "admission",
    "listing",
    "public_company_conversion",
    "unresolved",
}
ALLOWED_ORDINARY = {"", "true", "false", "unknown"}
ALLOWED_REVIEW_STATUSES = {"", "pending_manual_review", "reviewed", "rejected"}
SNAPSHOT_ROOT_REL = PurePosixPath(
    "stage124/batch02_parts/snapshots_part03"
)

# New retrieval status for manual snapshots
MANUAL_SNAPSHOT_IMPORTED = "manual_snapshot_imported"

DEFAULT_INTAKE_PATH = PART03_DIR / "part03_manual_intake_input.csv"
DEFAULT_REPORT_PATH = PART03_DIR / "part03_manual_intake_report.json"


class IntakeError(RuntimeError):
    """Fail-closed intake validation error."""


def empty_template() -> pd.DataFrame:
    return pd.DataFrame(columns=INTAKE_COLUMNS)


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _canonical_url(value: str) -> str:
    parts = urlsplit(_s(value))
    host = (parts.hostname or "").lower()
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not host:
        return ""
    netloc = host
    if parts.port and not (
        (scheme == "http" and parts.port == 80)
        or (scheme == "https" and parts.port == 443)
    ):
        netloc = f"{host}:{parts.port}"
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _is_valid_utc_timestamp(value: str) -> bool:
    """Validate a UTC timestamp string (ISO 8601)."""
    s = _s(value)
    if not s:
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def load_intake(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise IntakeError(
            f"intake file not found: {path}; the tracked template must exist"
        )
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if list(df.columns) != INTAKE_COLUMNS:
        missing = [c for c in INTAKE_COLUMNS if c not in df.columns]
        extra = [c for c in df.columns if c not in INTAKE_COLUMNS]
        raise IntakeError(
            "intake schema mismatch; exact ordered columns required; "
            f"missing={missing}, extra={extra}"
        )
    non_empty = df.apply(lambda row: any(_s(v) for v in row), axis=1)
    out = df.loc[non_empty, INTAKE_COLUMNS].copy().reset_index(drop=True)
    for col in INTAKE_COLUMNS:
        out[col] = out[col].map(_s)
    return out


def _resolve_snapshot(root: Path, value: str) -> tuple[Path | None, str]:
    """Resolve and confine a snapshot path beneath the allowed root.

    Security: only relative paths, exactly under snapshots_part03/,
    no ``..``, no absolute paths, no symlinks, resolve + confinement."""
    raw = _s(value).replace("\\", "/")
    if not raw:
        return None, "snapshot_path is empty"
    try:
        rel = PurePosixPath(raw)
    except Exception:
        return None, "snapshot_path is invalid"
    if rel.is_absolute() or ".." in rel.parts:
        return None, "snapshot_path must be a safe relative path"
    prefix = SNAPSHOT_ROOT_REL.parts
    if tuple(rel.parts[: len(prefix)]) != prefix:
        return None, f"snapshot_path must be under {SNAPSHOT_ROOT_REL.as_posix()}/"

    root_resolved = Path(root).resolve()
    allowed_root = (root_resolved / Path(*prefix)).resolve()
    # Check symlink BEFORE resolve (resolve follows symlinks)
    unresolved = root_resolved / Path(*rel.parts)
    if unresolved.is_symlink():
        return None, "snapshot symlinks are forbidden"
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        return None, "snapshot_path escapes the snapshot root"
    if not candidate.exists() or not candidate.is_file():
        return None, f"snapshot file not found: {raw}"
    return candidate, ""


def _is_discovery_only(row: dict) -> bool:
    """A discovery-only row has no snapshot, no date, no event,
    and ordinary_share_explicit=unknown."""
    snapshot = _s(row.get("snapshot_path"))
    event = _s(row.get("event_type_candidate"))
    date = _s(row.get("candidate_date_jalali"))
    ordinary = _s(row.get("ordinary_share_explicit")).lower()
    return (
        not snapshot
        and not event
        and not date
        and ordinary in {"", "unknown"}
    )


def validate_intake_row(row: dict, row_number: int, root: Path) -> list[str]:
    errors: list[str] = []
    prefix = f"row {row_number}"

    ticker = _s(row.get("ticker"))
    if ticker not in PART03_TICKERS:
        errors.append(f"{prefix}: ticker {ticker!r} out of Part 3 scope")

    source_type = _s(row.get("source_type"))
    if source_type not in ALLOWED_SOURCE_TYPES:
        errors.append(f"{prefix}: invalid source_type {source_type!r}")

    source_url = _s(row.get("source_url"))
    if not source_url:
        errors.append(f"{prefix}: source_url is required")
    elif not _worklist_url_ok(source_url) or not _canonical_url(source_url):
        errors.append(f"{prefix}: invalid source_url {source_url!r}")

    if not _s(row.get("source_title")):
        errors.append(f"{prefix}: source_title is required")
    if not _s(row.get("added_by")):
        errors.append(f"{prefix}: added_by is required")

    event = _s(row.get("event_type_candidate"))
    if event not in ALLOWED_EVENT_CANDIDATES:
        errors.append(f"{prefix}: invalid event_type_candidate {event!r}")

    ordinary = _s(row.get("ordinary_share_explicit")).lower()
    if ordinary not in ALLOWED_ORDINARY:
        errors.append(f"{prefix}: invalid ordinary_share_explicit {ordinary!r}")

    date = _s(row.get("candidate_date_jalali"))
    precision = _s(row.get("date_precision")) or "unknown"
    if not validate_worklist_date_precision(date, precision):
        errors.append(
            f"{prefix}: candidate_date_jalali {date!r} disagrees with "
            f"date_precision {precision!r}"
        )
    actual_events = ALLOWED_EVENT_CANDIDATES - {"", "unresolved"}
    if date and event not in actual_events:
        errors.append(f"{prefix}: candidate date requires a specific event type")
    if event in actual_events and not date:
        errors.append(f"{prefix}: event candidate requires candidate_date_jalali")
    if event == "unresolved" and date:
        errors.append(f"{prefix}: unresolved event cannot carry a candidate date")

    publication_date = _s(row.get("publication_date_jalali"))
    if publication_date and not is_valid_exact_jalali_date(publication_date):
        errors.append(
            f"{prefix}: publication_date_jalali must be an exact valid Jalali day"
        )

    # --- Human-in-the-Loop review status rules ---
    review_status = _s(row.get("content_review_status"))
    if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
        errors.append(f"{prefix}: invalid content_review_status {review_status!r}")

    reviewer_notes = _s(row.get("reviewer_notes"))
    reviewed_at = _s(row.get("manual_reviewed_at_utc"))

    if review_status == "pending_manual_review":
        # pending_manual_review must NOT carry finding fields
        if event:
            errors.append(
                f"{prefix}: pending_manual_review must not have event_type_candidate"
            )
        if date:
            errors.append(
                f"{prefix}: pending_manual_review must not have candidate_date_jalali"
            )
        if ordinary in {"true", "false"}:
            errors.append(
                f"{prefix}: pending_manual_review must not have "
                f"ordinary_share_explicit={ordinary}"
            )
        if reviewer_notes:
            errors.append(
                f"{prefix}: pending_manual_review must not have reviewer_notes"
            )
        if reviewed_at:
            errors.append(
                f"{prefix}: pending_manual_review must not have manual_reviewed_at_utc"
            )

    if review_status == "reviewed":
        if not reviewer_notes:
            errors.append(f"{prefix}: reviewed status requires reviewer_notes")
        if not reviewed_at:
            errors.append(
                f"{prefix}: reviewed status requires manual_reviewed_at_utc"
            )
        elif not _is_valid_utc_timestamp(reviewed_at):
            errors.append(
                f"{prefix}: manual_reviewed_at_utc must be a valid UTC timestamp"
            )

    # --- Snapshot / hash validation ---
    snapshot = _s(row.get("snapshot_path"))
    content_hash = _s(row.get("content_sha256")).lower()
    evidence_fields_present = bool(
        event
        or date
        or publication_date
        or ordinary in {"true", "false"}
    )
    if evidence_fields_present and not (snapshot and content_hash):
        errors.append(
            f"{prefix}: event/date/ordinary-share findings require snapshot_path "
            "and content_sha256"
        )
    # A reviewed row that carries evidence findings must have a snapshot
    if review_status == "reviewed" and evidence_fields_present:
        if not snapshot or not content_hash:
            errors.append(
                f"{prefix}: reviewed finding requires snapshot_path and content_sha256"
            )
    if snapshot or content_hash:
        if not (snapshot and content_hash):
            errors.append(
                f"{prefix}: snapshot_path and content_sha256 must be provided together"
            )
        else:
            candidate, path_error = _resolve_snapshot(root, snapshot)
            if path_error:
                errors.append(f"{prefix}: {path_error}")
            if not _is_sha256(content_hash):
                errors.append(f"{prefix}: invalid content_sha256")
            elif candidate is not None and sha(candidate) != content_hash:
                errors.append(
                    f"{prefix}: snapshot SHA-256 does not match content_sha256"
                )
    return errors


def validate_findings(findings: pd.DataFrame, root: Path) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for position, (_, row) in enumerate(findings.iterrows(), start=2):
        data = row.to_dict()
        errors.extend(validate_intake_row(data, position, root))
        key = (_s(data.get("ticker")), _canonical_url(data.get("source_url", "")))
        if key[1]:
            if key in seen:
                errors.append(
                    f"row {position}: duplicate normalized source_url for ticker"
                )
            seen.add(key)
    return errors


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return ("\ufeff" + df.to_csv(index=False, lineterminator="\n")).encode("utf-8")


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write(outputs: dict[Path, bytes]) -> None:
    """Write all outputs atomically with temp files and os.replace.

    On any failure, ALL files are rolled back to their prior state."""
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    created: list[Path] = []
    for target, payload in outputs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".intake_tmp")
        temp.write_bytes(payload)
        temps[target] = temp
    try:
        for target in outputs:
            if target.exists():
                backup = target.with_name(target.name + ".intake_bak")
                os.replace(target, backup)
                backups[target] = backup
            os.replace(temps[target], target)
            if target not in backups:
                created.append(target)
    except Exception:
        for target, backup in backups.items():
            if target.exists():
                target.unlink()
            if backup.exists():
                os.replace(backup, target)
        for target in created:
            if target.exists():
                target.unlink()
        for temp in temps.values():
            if temp.exists():
                temp.unlink()
        raise
    else:
        for backup in backups.values():
            if backup.exists():
                backup.unlink()


def _build_provenance_record(
    row: dict,
    source_index: str,
    root: Path,
) -> dict:
    """Build a provenance record for a reviewed manual intake row.

    All derived fields (source_authority_class, document_specific,
    evidence_accepted, etc.) are left empty here and will be recomputed
    by normalize_provenance_records from the engine."""
    snapshot = _s(row.get("snapshot_path"))
    content_hash = _s(row.get("content_sha256")).lower()
    snap_abs = root / snapshot if snapshot else None
    size = str(snap_abs.stat().st_size) if snap_abs and snap_abs.exists() else ""
    rec = {c: "" for c in PROVENANCE_COLUMNS}
    rec.update({
        "ticker": _s(row.get("ticker")),
        "source_index": source_index,
        "source_type": _s(row.get("source_type")),
        "source_title": _s(row.get("source_title")),
        "source_url": _s(row.get("source_url")),
        "publication_date": "",
        "retrieved_at_utc": _s(row.get("manual_reviewed_at_utc")) or _utc_now(),
        "http_status": "",
        "retrieval_status": MANUAL_SNAPSHOT_IMPORTED,
        "final_url": _s(row.get("source_url")),
        "content_type": "",
        "response_size_bytes": size,
        "snapshot_path": snapshot,
        "content_sha256": content_hash,
        "extraction_notes": "Manual snapshot imported via intake bridge.",
        "exact_text_or_event_summary": "",
        "supported_event_type": "",
        "supported_date_jalali": "",
        "content_review_status": _s(row.get("content_review_status")),
        "ordinary_share_explicit": _s(row.get("ordinary_share_explicit")).lower(),
        "event_type_supported": _s(row.get("event_type_candidate")),
        "exact_date_explicit": (
            "true"
            if _s(row.get("date_precision")) == "exact_day"
            and _s(row.get("candidate_date_jalali"))
            else "false"
        ),
        "reviewed_date_jalali": _s(row.get("candidate_date_jalali")),
        "publication_date_jalali": _s(row.get("publication_date_jalali")),
        "publication_date_explicit": (
            "true" if _s(row.get("publication_date_jalali")) else "false"
        ),
        "reviewer_notes": _s(row.get("reviewer_notes")),
        "manual_reviewed_at_utc": _s(row.get("manual_reviewed_at_utc")),
        # Derived fields -- will be recomputed by normalize_provenance_records
        "source_authority_class": "",
        "authority_validation_error": "",
        "document_specific": "",
        "contemporaneous_with_event": "",
        "independent_source_group": "",
        "evidence_accepted": "",
        "reviewed_event_type": "",
        "reviewed_date_precision": "",
        "reviewed_evidence_valid": "",
        "evidence_role": "",
    })
    return rec


def _recompute_engine_outputs(
    registry_df: pd.DataFrame,
    provenance_by_ticker: dict,
    root: Path,
) -> dict:
    """Recompute all engine-derived outputs from the updated provenance.

    Returns a dict with DataFrames/dicts for screening, summary, and QC."""
    company_names = {}
    try:
        company_names = load_company_names()
    except Exception:
        pass
    tickers_df = build_tickers_df(company_names)

    tsetmc = {}
    try:
        tsetmc = load_historical_tsetmc()
    except Exception:
        for tk in PART03_TICKERS:
            tsetmc[tk] = {
                "instrument_match_status": "not_in_historical_v2_audit",
                "tsetmc_candidate_date_jalali": "",
                "tsetmc_candidate_date_gregorian": "",
                "selected_inscode": "",
                "candidate_disposition": "not_in_historical_v2_audit",
                "source_file_path": "",
                "source_file_sha256": "",
                "probe_source": "historical_v2_audit",
                "network_request_performed": "false",
            }

    research_df = build_research_screening(company_names, provenance_by_ticker, tsetmc)
    provenance_df = build_source_provenance(provenance_by_ticker, root)

    from src.stage124_batch02_part03 import build_tsetmc_audit
    tsetmc_df = build_tsetmc_audit(tsetmc)

    # Build a summary dict from the research screening (matches engine run())
    summary = {
        "stage": "stage124_batch02_part03",
        "generated_at": _utc_now(),
        "source_commit": git_head(),
        "ticker_count": 10,
        "tickers": PART03_TICKERS,
        "exact_day_canonical": {},
        "research_blocked_network_tickers": [],
        "requires_manual_review_tickers": [],
        "no_reliable_evidence_tickers": [],
        "ready_for_user_review_tickers": [],
        "conflict_tickers": [],
        "counts": {
            "ready_count": 0,
            "network_blocked_count": 0,
            "total_attempted_sources": 0,
            "total_fetched_sources": 0,
            "total_reviewed_sources": 0,
            "total_evidence_sources": 0,
        },
        "per_ticker_status": {},
        "tsetmc_historical": {},
        "fetch_results": {},
    }
    for _, r in research_df.iterrows():
        tk = r["ticker"]
        es = r["evidence_status"]
        cand = str(r["proposed_canonical_public_entry_date_jalali"]).strip()
        ready = str(r["ready_for_user_review"]).strip().lower()
        if cand:
            summary["exact_day_canonical"][tk] = cand
        if str(r["research_status"]).strip() == "research_blocked_network":
            summary["research_blocked_network_tickers"].append(tk)
        if es == "requires_manual_review":
            summary["requires_manual_review_tickers"].append(tk)
        if es == "no_reliable_evidence":
            summary["no_reliable_evidence_tickers"].append(tk)
        if ready == "true":
            summary["ready_for_user_review_tickers"].append(tk)
        if str(r["conflict_flag"]).strip().lower() == "true":
            summary["conflict_tickers"].append(tk)
        if str(r.get("network_blocked", "")).strip().lower() == "true":
            summary["counts"]["network_blocked_count"] += 1
        summary["counts"]["total_attempted_sources"] += int(
            r.get("attempted_source_count", 0) or 0
        )
        summary["counts"]["total_fetched_sources"] += int(
            r.get("fetched_source_count", 0) or 0
        )
        summary["counts"]["total_reviewed_sources"] += int(
            r.get("reviewed_source_count", 0) or 0
        )
        summary["counts"]["total_evidence_sources"] += int(
            r.get("evidence_source_count", 0) or 0
        )
        summary["per_ticker_status"][tk] = {
            "evidence_status": es,
            "research_status": str(r["research_status"]),
            "research_completion_status": str(
                r.get("research_completion_status", "")
            ),
            "network_blocked": str(r.get("network_blocked", "")),
            "ordinary_share_confirmed": str(
                r.get("ordinary_share_confirmed", "")
            ),
            "ready_for_user_review": ready,
            "recommended_next_step": str(r.get("recommended_next_step", "")),
        }
    summary["counts"]["ready_count"] = len(
        summary["ready_for_user_review_tickers"]
    )
    for tk, ts in tsetmc.items():
        summary["tsetmc_historical"][tk] = {
            "instrument_match_status": ts["instrument_match_status"],
            "historical_candidate_date": ts["tsetmc_candidate_date_jalali"],
            "candidate_disposition": ts["candidate_disposition"],
            "network_request_performed": ts["network_request_performed"],
        }
    for tk in PART03_TICKERS:
        summary["fetch_results"][tk] = [
            {
                "source_index": rec.get("source_index", ""),
                "source_url": rec.get("source_url", ""),
                "retrieval_status": rec.get("retrieval_status", ""),
                "http_status": str(rec.get("http_status", "")),
                "snapshot_path": rec.get("snapshot_path", ""),
                "content_sha256": rec.get("content_sha256", ""),
            }
            for rec in provenance_by_ticker.get(tk, [])
        ]

    # QC: build with safe empty frozen/part02 dicts (intake never touches those)
    frozen_before = {}
    frozen_after = {}
    part02_before = {}
    part02_after = {}
    qc = run_part03_qc(
        tickers_df, research_df, provenance_df, tsetmc_df,
        frozen_before, frozen_after, part02_before, part02_after,
        registry_df=registry_df,
    )

    src_file = Path(__file__).resolve().parent / "src" / "stage124_batch02_part03.py"
    test_file = root / "tests" / "test_stage124_batch02_part03.py"
    qc_report = {
        "stage": "stage124_batch02_part03",
        "generated_at": _utc_now(),
        "source_commit": git_head(),
        "source_file_sha256": sha(src_file) if src_file.exists() else "",
        "test_file_sha256": sha(test_file) if test_file.exists() else "",
        "ticker_count": 10,
        "tickers": PART03_TICKERS,
        "all_pass": qc["all_pass"],
        "assertion_count": len(qc["assertions"]),
        "failed_count": sum(1 for a in qc["assertions"] if not a["passed"]),
        "assertions": qc["assertions"],
    }

    return {
        "research_df": research_df,
        "provenance_df": provenance_df,
        "summary": summary,
        "qc_report": qc_report,
    }


def run_intake(
    intake_path: Path | None = None,
    registry_path: Path | None = None,
    report_path: Path | None = None,
    root: Path | None = None,
    *,
    apply: bool = False,
    write_report: bool = False,
) -> dict:
    intake_path = Path(intake_path) if intake_path else DEFAULT_INTAKE_PATH
    registry_path = Path(registry_path) if registry_path else SOURCE_REGISTRY_PATH
    report_path = Path(report_path) if report_path else DEFAULT_REPORT_PATH
    root = Path(root) if root else ROOT

    findings = load_intake(intake_path)
    errors = validate_findings(findings, root)
    if errors:
        raise IntakeError("intake validation failed:\n  - " + "\n  - ".join(errors))

    registry_df = (
        load_source_registry(registry_path)
        if registry_path.exists()
        else build_seed_registry_df()
    )
    ok, registry_errors = validate_source_registry(registry_df)
    if not ok:
        raise IntakeError(f"invalid source registry: {registry_errors[:5]}")

    registry_before = len(registry_df)
    proposed_registry = registry_df.copy()
    per_ticker: dict[str, int] = {}
    snapshots_verified: list[str] = []

    # Classify findings
    finding_rows: list[dict] = []
    discovery_only_rows: list[dict] = []
    for _, row in findings.iterrows():
        data = row.to_dict()
        if _is_discovery_only(data):
            discovery_only_rows.append(data)
        else:
            finding_rows.append(data)

    if not findings.empty:
        additions = pd.DataFrame(
            [
                {
                    "ticker": _s(row["ticker"]),
                    "source_type": _s(row["source_type"]),
                    "source_title": _s(row["source_title"]),
                    "source_url": _s(row["source_url"]),
                    "added_at_utc": "",
                    "added_by": _s(row["added_by"]),
                    "discovery_notes": _s(row["discovery_notes"]),
                }
                for _, row in findings.iterrows()
            ]
        )
        try:
            proposed_registry = register_discovered_sources(registry_df, additions)
        except ValueError as exc:
            raise IntakeError(str(exc)) from exc
        for _, row in findings.iterrows():
            ticker = _s(row["ticker"])
            per_ticker[ticker] = per_ticker.get(ticker, 0) + 1
            if _s(row["snapshot_path"]):
                snapshots_verified.append(_s(row["snapshot_path"]))

    proposed_count = len(proposed_registry) - registry_before

    # Determine source_index for each intake row from the proposed registry
    def _get_source_index(ticker: str, url: str) -> str:
        """Get the source_index from the proposed registry for this ticker+url."""
        for _, r in proposed_registry.iterrows():
            if (str(r["ticker"]).strip() == ticker
                    and str(r["source_url"]).strip() == url):
                return str(r["source_index"]).strip()
        return ""

    # Build provenance records for sources with snapshots (reviewed findings)
    provenance_created = 0
    new_provenance_records: list[dict] = []
    for data in finding_rows:
        snapshot = _s(data.get("snapshot_path"))
        review_status = _s(data.get("content_review_status"))
        # Only reviewed rows with snapshots produce provenance
        if snapshot and review_status == "reviewed":
            tk = _s(data.get("ticker"))
            url = _s(data.get("source_url"))
            si = _get_source_index(tk, url)
            rec = _build_provenance_record(data, si, root)
            new_provenance_records.append(rec)
            provenance_created += 1

    if findings.empty:
        status = "ready_no_findings"
    elif apply:
        status = "findings_registered"
    else:
        status = "findings_validated_dry_run"

    report = {
        "stage": "stage124_batch02_part03_manual_intake",
        "part": "3.1B.1A",
        "status": status,
        "source_commit": git_head(),
        "network_request_performed": False,
        "apply_requested": bool(apply),
        "scope_tickers": list(PART03_TICKERS),
        "intake_file": str(intake_path),
        "intake_sha256": sha(intake_path),
        "findings_count": int(len(findings)),
        "sources_proposed": int(proposed_count),
        "sources_registered": int(proposed_count if apply else 0),
        "provenance_created": int(provenance_created if apply else 0),
        "registry_rows_before": int(registry_before),
        "registry_rows_after": int(
            len(proposed_registry) if apply else registry_before
        ),
        "per_ticker_proposed": per_ticker,
        "snapshots_verified": snapshots_verified,
        "discovery_only_count": int(len(discovery_only_rows)),
    }

    if apply and findings.empty:
        raise IntakeError("--apply refused because the intake has no findings")

    # --- Apply mode: build ALL outputs in memory, validate, then write atomically
    if apply:
        # Compute paths relative to root (not hardcoded PART03_DIR)
        part03_dir = root / "stage124" / "batch02_parts"
        # Load existing provenance (if any)
        provenance_path = part03_dir / "part03_source_provenance_10tickers.csv"
        existing_prov_records: list[dict] = []
        if provenance_path.exists():
            try:
                ep = read_csv(provenance_path)
                for _, pr in ep.iterrows():
                    existing_prov_records.append(
                        {c: str(pr.get(c, "")) for c in PROVENANCE_COLUMNS}
                    )
            except Exception:
                pass

        # Merge: add new provenance records, normalise all via engine
        all_prov = existing_prov_records + new_provenance_records
        normalized = normalize_provenance_records(all_prov, root)
        provenance_by_ticker: dict[str, list] = {tk: [] for tk in PART03_TICKERS}
        for rec in normalized:
            tk = str(rec.get("ticker", "")).strip()
            if tk in provenance_by_ticker:
                provenance_by_ticker[tk].append(rec)

        # Recompute all engine outputs (screening, summary, QC)
        engine_out = _recompute_engine_outputs(
            proposed_registry, provenance_by_ticker, root
        )

        # Validate: source with snapshot must have exactly one provenance row
        for data in finding_rows:
            snapshot = _s(data.get("snapshot_path"))
            if snapshot and _s(data.get("content_review_status")) == "reviewed":
                tk = _s(data.get("ticker"))
                url = _s(data.get("source_url"))
                si = _get_source_index(tk, url)
                matching = [
                    r for r in provenance_by_ticker.get(tk, [])
                    if str(r.get("source_index", "")).strip() == si
                ]
                if len(matching) != 1:
                    raise IntakeError(
                        f"source ({tk}, index={si}) must have exactly 1 "
                        f"provenance row, got {len(matching)}"
                    )

        # Build all outputs as bytes in memory
        research_path = part03_dir / "part03_research_screening_10tickers.csv"
        summary_path = part03_dir / "part03_research_summary.json"
        qc_path = part03_dir / "part03_qc_report.json"
        manifest_path = part03_dir / "part03_manual_intake_apply_manifest.json"

        manifest = {
            "generated_at": _utc_now(),
            "source_commit": git_head(),
            "apply_requested": True,
            "findings_count": int(len(findings)),
            "provenance_created": provenance_created,
            "discovery_only_count": int(len(discovery_only_rows)),
            "registry_rows_before": int(registry_before),
            "registry_rows_after": int(len(proposed_registry)),
            "outputs_written": [
                str(registry_path),
                str(provenance_path),
                str(research_path),
                str(summary_path),
                str(qc_path),
                str(report_path),
                str(manifest_path),
            ],
        }

        outputs: dict[Path, bytes] = {
            registry_path: _csv_bytes(
                proposed_registry[SOURCE_REGISTRY_COLUMNS]
            ),
            provenance_path: _csv_bytes(engine_out["provenance_df"]),
            research_path: _csv_bytes(engine_out["research_df"]),
            summary_path: _json_bytes(engine_out["summary"]),
            qc_path: _json_bytes(engine_out["qc_report"]),
            report_path: _json_bytes(report),
            manifest_path: _json_bytes(manifest),
        }

        _atomic_write(outputs)
    elif write_report:
        outputs = {report_path: _json_bytes(report)}
        _atomic_write(outputs)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, default=DEFAULT_INTAKE_PATH)
    parser.add_argument("--registry", type=Path, default=SOURCE_REGISTRY_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="persist validated source additions; default is dry-run",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="write a report during dry-run; --apply always writes one",
    )
    args = parser.parse_args(argv)

    try:
        report = run_intake(
            intake_path=args.intake,
            registry_path=args.registry,
            report_path=args.report,
            root=args.root,
            apply=args.apply,
            write_report=args.write_report,
        )
    except IntakeError as exc:
        print(f"INTAKE FAILED: {exc}", file=sys.stderr)
        return 1

    print("Part 3.1B.1A manual intake:")
    print(f"  status              : {report['status']}")
    print(f"  findings            : {report['findings_count']}")
    print(f"  sources proposed    : {report['sources_proposed']}")
    print(f"  sources registered  : {report['sources_registered']}")
    print(f"  provenance created  : {report['provenance_created']}")
    print(f"  network performed   : {report['network_request_performed']}")
    if not args.apply:
        print("  mode                : DRY RUN (no registry changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
