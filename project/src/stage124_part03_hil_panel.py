"""Stage124 Batch02 Part 3.1B.1B — Human-in-the-Loop Panel core.

All file operations, snapshot security, audit logging, validation and bridge
invocation live in this module. The Streamlit app is a thin UI over these helpers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

# Project root is the parent of this file's directory (project/src -> project).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import run_stage124_batch02_part03_manual_intake as intake_bridge  # noqa: E402
from src.stage124_batch02_part03 import (  # noqa: E402
    PART03_TICKERS,
    PROVENANCE_COLUMNS,
    ROOT,
    SOURCE_REGISTRY_PATH,
    read_csv,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PANEL_SUBMISSIONS_DIR = ROOT / "stage124" / "batch02_parts" / "panel_submissions"
PANEL_AUDIT_PATH = ROOT / "stage124" / "batch02_parts" / "part03_hil_panel_audit.jsonl"
SNAPSHOT_ROOT = ROOT / "stage124" / "batch02_parts" / "snapshots_part03"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".html",
    ".htm",
    ".txt",
    ".json",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

_REVIEW_MODE_TO_STATUS = {
    "discovery": "",
    "pending_manual_review": "pending_manual_review",
    "reviewed": "reviewed",
    "rejected": "rejected",
}

_INTAKE_COLUMNS = intake_bridge.INTAKE_COLUMNS
ALLOWED_SOURCE_TYPES = intake_bridge.ALLOWED_SOURCE_TYPES
ALLOWED_EVENT_CANDIDATES = intake_bridge.ALLOWED_EVENT_CANDIDATES

_ALLOWED_BASENAME = re.compile(r"[^\w\-.\s]")
_SNAPSHOT_ROOT_REL = PurePosixPath("stage124/batch02_parts/snapshots_part03")


class PanelError(RuntimeError):
    """Fail-closed panel error."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _canonical_url(value: str) -> str:
    """Normalize a URL to scheme://host/path (no fragment, standard ports)."""
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _row_sha256(row: dict) -> str:
    """Stable hash of the intake row for immutable submission filenames."""
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _ensure_safe_dir(path: Path) -> None:
    """Create directory and verify it is not a symlink."""
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PanelError("snapshot directory is a symlink")


def _confine_snapshot_path(root: Path, snapshot_path: str) -> Path:
    """Return the absolute path for a snapshot path only if it is safely
    confined under the allowed snapshot root."""
    raw = _s(snapshot_path).replace("\\", "/")
    if not raw:
        raise PanelError("snapshot_path is empty")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise PanelError("snapshot_path must be a safe relative path")
    prefix = _SNAPSHOT_ROOT_REL.parts
    if tuple(rel.parts[: len(prefix)]) != prefix:
        raise PanelError(f"snapshot_path must be under {_SNAPSHOT_ROOT_REL.as_posix()}/")

    root_resolved = Path(root).resolve()
    allowed_root = (root_resolved / Path(*prefix)).resolve()
    unresolved = root_resolved / Path(*rel.parts)
    if unresolved.is_symlink():
        raise PanelError("snapshot symlinks are forbidden")
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise PanelError("snapshot_path escapes the snapshot root") from exc
    return candidate


# ---------------------------------------------------------------------------
# Filename / upload security
# ---------------------------------------------------------------------------
def sanitize_filename(filename: str) -> str:
    r"""Return a collision-safe, shell-safe filename preserving the extension.

    - Strips path separators, null bytes and control characters.
    - Replaces spaces with underscores.
    - Removes characters outside [A-Za-z0-9\-_.\s] and Persian/Arabic word chars.
    - Collapses multiple underscores.
    - Guarantees no leading dots, no .., no absolute paths.
    """
    name = _s(filename)
    if not name:
        raise PanelError("filename is empty")
    # Normalize separators
    name = name.replace("\\", "/")
    # Take only the basename
    name = name.split("/")[-1].split("\x00")[-1]
    # Replace spaces and dangerous characters
    name = _ALLOWED_BASENAME.sub("", name)
    name = name.replace(" ", "_")
    # Collapse repeated underscores
    name = re.sub(r"_+", "_", name)
    # Remove leading dots to avoid hidden files / path traversal by extension
    name = name.lstrip(".")
    if not name or name in {"", ".", ".."}:
        raise PanelError("filename is empty after sanitization")
    return name


def validate_upload(filename: str, content: bytes) -> None:
    """Validate an uploaded file before it is stored.

    Raises PanelError on any security or size violation.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise PanelError("content must be bytes")
    safe = sanitize_filename(filename)
    if len(content) > MAX_UPLOAD_BYTES:
        raise PanelError(
            f"upload size {len(content)} exceeds limit {MAX_UPLOAD_BYTES}"
        )
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise PanelError(f"upload extension {ext!r} is not allowed")
    # Reject absolute-looking paths and traversal
    if Path(filename).is_absolute() or "/" in filename or "\\" in filename:
        raise PanelError("absolute filename rejected")
    if ".." in Path(filename).parts:
        raise PanelError("path traversal rejected")


# ---------------------------------------------------------------------------
# Snapshot storage
# ---------------------------------------------------------------------------
def store_snapshot(
    *,
    root: Path,
    ticker: str,
    filename: str,
    content: bytes,
) -> dict:
    """Store an uploaded snapshot under the confined snapshot root.

    Returns a dict with:
      - snapshot_path: relative to ``root`` (e.g. stage124/.../ticker/...)
      - content_sha256: SHA-256 of the actual bytes
      - size_bytes
      - stored_filename
    """
    if _s(ticker) not in PART03_TICKERS:
        raise PanelError(f"ticker {ticker!r} out of Part 3 scope")
    validate_upload(filename, content)
    safe_name = sanitize_filename(filename)
    content_sha256 = _sha256_bytes(content)
    sha12 = content_sha256[:12]
    timestamp = _utc_timestamp_for_filename()
    stored_name = f"{timestamp}_{sha12}_{safe_name}"

    snap_dir = Path(root).resolve() / _SNAPSHOT_ROOT_REL / ticker
    _ensure_safe_dir(snap_dir)
    target = snap_dir / stored_name
    if target.is_symlink():
        raise PanelError("snapshot target is a symlink")
    # Collision safety: on the very rare chance of collision, append a counter.
    if target.exists():
        for counter in range(1, 1000):
            candidate = snap_dir / f"{timestamp}_{sha12}_{counter}_{safe_name}"
            if not candidate.exists():
                target = candidate
                break
        else:
            raise PanelError("could not create a collision-safe filename")
    target.write_bytes(content)
    # Re-verify confinement and hash from disk
    stored_abs = _confine_snapshot_path(root, target.relative_to(Path(root).resolve()).as_posix())
    disk_hash = _sha256_bytes(stored_abs.read_bytes())
    if disk_hash != content_sha256:
        raise PanelError("stored snapshot hash does not match uploaded bytes")
    rel_path = target.relative_to(Path(root).resolve()).as_posix()
    return {
        "snapshot_path": rel_path,
        "content_sha256": content_sha256,
        "size_bytes": len(content),
        "stored_filename": stored_name,
    }


# ---------------------------------------------------------------------------
# Intake row builder
# ---------------------------------------------------------------------------
def build_intake_row(
    *,
    ticker: str,
    source_type: str,
    source_url: str,
    source_title: str,
    review_mode: str,
    event_type: str = "",
    candidate_date_jalali: str = "",
    date_precision: str = "unknown",
    ordinary_share_explicit: str = "unknown",
    snapshot_path: str = "",
    content_sha256: str = "",
    publication_date_jalali: str = "",
    actor: str,
    discovery_notes: str = "",
    reviewer_notes: str = "",
) -> dict:
    """Build an intake row dict matching the bridge schema.

    ``review_mode`` is one of: discovery, pending_manual_review, reviewed,
    rejected. The Core generates ``manual_reviewed_at_utc`` in UTC for reviewed
    rows; the caller must not provide a manual timestamp.
    """
    if not _s(actor):
        raise PanelError("actor is required")
    if review_mode not in _REVIEW_MODE_TO_STATUS:
        raise PanelError(f"invalid review_mode {review_mode!r}")
    status = _REVIEW_MODE_TO_STATUS[review_mode]
    if review_mode == "reviewed":
        manual_reviewed_at_utc = _utc_now()
        if not reviewer_notes:
            raise PanelError("reviewed mode requires reviewer_notes")
        if not snapshot_path or not content_sha256:
            raise PanelError("reviewed mode requires snapshot_path and content_sha256")
    elif review_mode == "pending_manual_review":
        manual_reviewed_at_utc = ""
        if event_type:
            raise PanelError("pending_manual_review must not have event_type")
        if candidate_date_jalali:
            raise PanelError("pending_manual_review must not have candidate_date_jalali")
        if ordinary_share_explicit.lower() in {"true", "false"}:
            raise PanelError("pending_manual_review must not have ordinary_share_explicit")
        if reviewer_notes:
            raise PanelError("pending_manual_review must not have reviewer_notes")
    elif review_mode == "discovery":
        manual_reviewed_at_utc = ""
        event_type = ""
        candidate_date_jalali = ""
        ordinary_share_explicit = "unknown"
        reviewer_notes = ""
        snapshot_path = ""
        content_sha256 = ""
    else:  # rejected
        manual_reviewed_at_utc = ""
        if not reviewer_notes:
            raise PanelError("rejected mode requires a rejection reason")

    row = {
        "ticker": _s(ticker),
        "source_type": _s(source_type),
        "source_url": _s(source_url),
        "source_title": _s(source_title),
        "event_type_candidate": _s(event_type),
        "candidate_date_jalali": _s(candidate_date_jalali),
        "date_precision": _s(date_precision) or "unknown",
        "ordinary_share_explicit": _s(ordinary_share_explicit) or "unknown",
        "snapshot_path": _s(snapshot_path),
        "content_sha256": _s(content_sha256).lower(),
        "publication_date_jalali": _s(publication_date_jalali),
        "added_by": _s(actor),
        "discovery_notes": _s(discovery_notes),
        "content_review_status": status,
        "reviewer_notes": _s(reviewer_notes),
        "manual_reviewed_at_utc": manual_reviewed_at_utc,
    }
    return {k: row[k] for k in _INTAKE_COLUMNS}


# ---------------------------------------------------------------------------
# Submission CSV helpers
# ---------------------------------------------------------------------------
def _write_submission_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{c: _s(row.get(c, "")) for c in _INTAKE_COLUMNS}])
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def _submission_path(root: Path, ticker: str, row: dict) -> Path:
    ts = _utc_timestamp_for_filename()
    return (
        Path(root).resolve()
        / "stage124"
        / "batch02_parts"
        / "panel_submissions"
        / f"{ts}_{_s(ticker)}_{_row_sha256(row)}.csv"
    )


# ---------------------------------------------------------------------------
# Duplicate provenance guard
# ---------------------------------------------------------------------------
def _load_existing_provenance(root: Path) -> pd.DataFrame | None:
    prov_path = Path(root).resolve() / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv"
    if not prov_path.exists():
        return None
    try:
        return read_csv(prov_path)
    except Exception:
        return None


def _duplicate_provenance_exists(row: dict, root: Path) -> bool:
    """Return True if a provenance row already exists for the same
    (ticker, canonical source_url, source_index, content_sha256)."""
    prov = _load_existing_provenance(root)
    if prov is None or prov.empty:
        return False
    ticker = _s(row.get("ticker"))
    url = _canonical_url(_s(row.get("source_url")))
    sha256 = _s(row.get("content_sha256")).lower()
    # We also need source_index. Load registry to resolve the index.
    registry = _load_registry(root)
    source_index = ""
    if registry is not None and not registry.empty:
        matches = registry[
            (registry["ticker"].astype(str).str.strip() == ticker)
            & (registry["source_url"].astype(str).str.strip() == _s(row.get("source_url")))
        ]
        if not matches.empty:
            source_index = str(matches.iloc[0].get("source_index", "")).strip()

    for _, pr in prov.iterrows():
        pr_ticker = str(pr.get("ticker", "")).strip()
        pr_url = _canonical_url(str(pr.get("source_url", "")))
        pr_index = str(pr.get("source_index", "")).strip()
        pr_sha = str(pr.get("content_sha256", "")).strip().lower()
        if pr_ticker == ticker and pr_url == url:
            if pr_index == source_index or pr_sha == sha256:
                return True
    return False


# ---------------------------------------------------------------------------
# Registry helper
# ---------------------------------------------------------------------------
def _load_registry(root: Path) -> pd.DataFrame | None:
    registry_path = Path(root).resolve() / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    if not registry_path.exists():
        return None
    try:
        return read_csv(registry_path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_submission(
    *,
    row: dict,
    root: Path,
) -> dict:
    """Run a dry-run validation of a single-row submission via the bridge.

    Returns a dict with keys:
      - valid (bool)
      - bridge_status (str)
      - report (dict | None)
      - errors (list[str])
    """
    root = Path(root).resolve()
    registry_path = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    report_path = root / "stage124" / "batch02_parts" / "part03_manual_intake_report.json"
    with tempfile.TemporaryDirectory() as tmp:
        intake_path = Path(tmp) / "panel_submission.csv"
        _write_submission_csv(intake_path, row)
        try:
            report = intake_bridge.run_intake(
                intake_path=intake_path,
                registry_path=registry_path,
                report_path=report_path,
                root=root,
                apply=False,
                write_report=False,
            )
            return {
                "valid": True,
                "bridge_status": report.get("status", "unknown"),
                "report": report,
                "errors": [],
            }
        except Exception as exc:
            return {
                "valid": False,
                "bridge_status": "validation_failed",
                "report": None,
                "errors": [str(exc)],
            }


# ---------------------------------------------------------------------------
# Apply / reject
# ---------------------------------------------------------------------------
def apply_submission(
    *,
    row: dict,
    root: Path,
    actor: str,
    action: str,
) -> dict:
    """Apply or reject a validated submission and append an audit event.

    ``action`` must be one of: validate, apply, reject.

    Returns a dict with at least:
      - action
      - valid (bool)
      - applied (bool)
      - rejected (bool)
      - bridge_status (str)
      - report (dict | None)
      - errors (list[str])
      - submission_path (str | "")
      - audit_event (dict | None)
    """
    if action not in {"validate", "apply", "reject"}:
        raise PanelError(f"invalid action {action!r}")
    root = Path(root).resolve()
    if not _s(actor):
        raise PanelError("actor is required")

    if action == "validate":
        result = validate_submission(row=row, root=root)
        audit_event = _append_audit_event(
            root=root,
            actor=actor,
            action="validate",
            row=row,
            result=result,
            submission_path="",
        )
        result.update({
            "action": "validate",
            "applied": False,
            "rejected": False,
            "audit_event": audit_event,
        })
        return result

    if action == "reject":
        submission_path = _submission_path(root, row.get("ticker", ""), row)
        _write_submission_csv(submission_path, row)
        result = {
            "valid": True,
            "bridge_status": "rejected",
            "report": None,
            "errors": [],
            "submission_path": str(submission_path),
            "action": "reject",
            "applied": False,
            "rejected": True,
        }
        audit_event = _append_audit_event(
            root=root,
            actor=actor,
            action="reject",
            row=row,
            result=result,
            submission_path=str(submission_path),
        )
        result["audit_event"] = audit_event
        return result

    # action == "apply"
    if _duplicate_provenance_exists(row, root):
        error = "این منبع قبلاً وارد provenance شده است و Apply مجدد مجاز نیست."
        result = {
            "valid": False,
            "bridge_status": "duplicate_blocked",
            "report": None,
            "errors": [error],
            "submission_path": "",
            "action": "apply",
            "applied": False,
            "rejected": False,
        }
        audit_event = _append_audit_event(
            root=root,
            actor=actor,
            action="apply",
            row=row,
            result=result,
            submission_path="",
        )
        result["audit_event"] = audit_event
        return result

    submission_path = _submission_path(root, row.get("ticker", ""), row)
    _write_submission_csv(submission_path, row)
    registry_path = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    report_path = root / "stage124" / "batch02_parts" / "part03_manual_intake_report.json"
    try:
        report = intake_bridge.run_intake(
            intake_path=submission_path,
            registry_path=registry_path,
            report_path=report_path,
            root=root,
            apply=True,
        )
        result = {
            "valid": True,
            "bridge_status": report.get("status", "applied"),
            "report": report,
            "errors": [],
            "submission_path": str(submission_path),
            "action": "apply",
            "applied": True,
            "rejected": False,
        }
    except Exception as exc:
        result = {
            "valid": False,
            "bridge_status": "apply_failed",
            "report": None,
            "errors": [str(exc)],
            "submission_path": str(submission_path),
            "action": "apply",
            "applied": False,
            "rejected": False,
        }

    audit_event = _append_audit_event(
        root=root,
        actor=actor,
        action="apply",
        row=row,
        result=result,
        submission_path=str(submission_path),
    )
    result["audit_event"] = audit_event
    return result


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
def _append_audit_event(
    *,
    root: Path,
    actor: str,
    action: str,
    row: dict,
    result: dict,
    submission_path: str,
) -> dict:
    """Append a single audit event to the JSONL audit log atomically."""
    audit_path = Path(root).resolve() / "stage124" / "batch02_parts" / "part03_hil_panel_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_id": uuid.uuid4().hex,
        "created_at_utc": _utc_now(),
        "actor": _s(actor),
        "action": action,
        "ticker": _s(row.get("ticker", "")),
        "source_url": _s(row.get("source_url", "")),
        "review_mode": _s(row.get("content_review_status", "")),
        "row_sha256": _row_sha256(row),
        "submission_path": submission_path,
        "snapshot_path": _s(row.get("snapshot_path", "")),
        "content_sha256": _s(row.get("content_sha256", "")).lower(),
        "bridge_status": result.get("bridge_status", ""),
        "bridge_report": result.get("report") or {},
        "error": "; ".join(result.get("errors", [])),
    }
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    temp = audit_path.with_name(audit_path.name + ".tmp")
    if audit_path.exists():
        existing = audit_path.read_bytes()
        temp.write_bytes(existing + line.encode("utf-8"))
    else:
        temp.write_bytes(line.encode("utf-8"))
    os.replace(temp, audit_path)
    return event


# ---------------------------------------------------------------------------
# Dashboard data loading
# ---------------------------------------------------------------------------
def _safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return read_csv(path)
    except Exception:
        return None


def _safe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_dashboard_data(root: Path) -> dict:
    """Load all Part 3 outputs read-only for the dashboard.

    Missing files do not crash the panel; an empty DataFrame or empty dict is
    returned instead.
    """
    root = Path(root).resolve()
    part03_dir = root / "stage124" / "batch02_parts"

    registry = _safe_read_csv(part03_dir / "part03_source_registry.csv")
    provenance = _safe_read_csv(part03_dir / "part03_source_provenance_10tickers.csv")
    screening = _safe_read_csv(part03_dir / "part03_research_screening_10tickers.csv")
    summary = _safe_read_json(part03_dir / "part03_research_summary.json")
    qc = _safe_read_json(part03_dir / "part03_qc_report.json")
    manifest = _safe_read_json(part03_dir / "part03_manual_intake_apply_manifest.json")
    audit = read_audit_events(root, limit=100)

    # Build metrics that mirror the UI cards
    if screening is not None and not screening.empty:
        metrics = {
            "ticker_count": len(screening),
            "ready_count": int(
                (screening["ready_for_user_review"].astype(str).str.strip().str.lower() == "true").sum()
            ),
            "requires_review_count": int(
                (screening["evidence_status"].astype(str).str.strip() == "requires_manual_review").sum()
            ),
            "conflict_count": int(
                (screening["conflict_flag"].astype(str).str.strip().str.lower() == "true").sum()
            ),
            "network_blocked_count": int(
                (screening["network_blocked"].astype(str).str.strip().str.lower() == "true").sum()
            ),
        }
    else:
        metrics = {
            "ticker_count": len(PART03_TICKERS),
            "ready_count": 0,
            "requires_review_count": 0,
            "conflict_count": 0,
            "network_blocked_count": 0,
        }

    return {
        "registry": registry,
        "provenance": provenance,
        "screening": screening,
        "summary": summary or {},
        "qc_report": qc or {},
        "manifest": manifest or {},
        "audit_events": audit,
        "metrics": metrics,
    }


def read_audit_events(root: Path, limit: int = 100) -> list[dict]:
    """Return the most recent ``limit`` audit events (newest first)."""
    audit_path = Path(root).resolve() / "stage124" / "batch02_parts" / "part03_hil_panel_audit.jsonl"
    if not audit_path.exists():
        return []
    events: list[dict] = []
    try:
        with audit_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return events[-limit:][::-1]
