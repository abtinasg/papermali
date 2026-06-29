"""Stage124 Batch02 Part 3.1B.0 — auditable manual snapshot intake.

This module provides a deterministic, no-network path for importing manually
captured source snapshots into the existing Part 3 registry/provenance engine.
It never guesses dates, never trusts derived evidence fields, and never writes
files itself. Callers must validate first and persist the returned DataFrames
atomically.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

from . import stage124_batch02_part03 as p3

MANUAL_RETRIEVAL_STATUS = "manual_snapshot_imported"
p3.FETCHED_STATUSES.add(MANUAL_RETRIEVAL_STATUS)

INTAKE_COLUMNS = [
    "ticker", "source_url", "source_type", "source_title", "snapshot_path",
    "supplied_snapshot_sha256", "captured_at_utc", "final_url", "http_status",
    "content_type", "content_review_status", "event_type_supported",
    "reviewed_date_jalali", "exact_date_explicit", "ordinary_share_explicit",
    "publication_date_jalali", "publication_date_explicit",
    "exact_text_or_event_summary", "reviewer_notes", "manual_reviewed_at_utc",
    "added_by", "discovery_notes",
]

AUDIT_COLUMNS = [
    "intake_row_number", "ticker", "source_url", "source_index",
    "registry_action", "provenance_action", "snapshot_path",
    "computed_snapshot_sha256", "supplied_snapshot_sha256",
    "content_review_status", "event_type_supported", "reviewed_date_jalali",
    "validation_status", "validation_errors", "apply_mode", "applied_at_utc",
]

ALLOWED_SOURCE_TYPES = {
    "codal_official", "regulatory_official", "news_agency", "credible_news",
    "official_market_news", "market_data", "official_market_data_audit",
    "market_information_aggregator", "aggregator", "company_official",
}
ALLOWED_REVIEW_STATUSES = {"pending_manual_review", "reviewed"}
ALLOWED_BOOL = {"true", "false"}
ALLOWED_ORDINARY = {"true", "false", "unknown"}

# These fields are always recomputed by the Part 3 engine and must never appear
# in a manual intake file, even as empty convenience columns.
DERIVED_FORBIDDEN = {
    "retrieval_status", "content_sha256", "response_size_bytes",
    "source_authority_class", "authority_validation_error", "document_specific",
    "contemporaneous_with_event", "independent_source_group", "evidence_accepted",
    "reviewed_event_type", "reviewed_date_precision", "reviewed_evidence_valid",
    "evidence_role", "supported_event_type", "supported_date_jalali",
    "publication_date", "extraction_notes",
}

MANUAL_SNAPSHOT_PREFIX = PurePosixPath(
    "stage124/batch02_parts/snapshots_part03/manual"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _canonical_url(value: str) -> str:
    value = _s(value)
    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not scheme or not host:
        return ""
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _valid_http_url(value: str) -> bool:
    try:
        parts = urlsplit(_s(value))
        return parts.scheme.lower() in {"http", "https"} and bool(parts.hostname)
    except Exception:
        return False


def _valid_utc(value: str) -> bool:
    try:
        datetime.strptime(_s(value), "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def _date_precision(value: str) -> str:
    value = _s(value)
    if not value:
        return "unknown"
    if re.fullmatch(r"(?:12|13|14|15)\d{2}", value):
        return "year_only"
    m = re.fullmatch(r"((?:12|13|14|15)\d{2})-(\d{2})", value)
    if m and 1 <= int(m.group(2)) <= 12:
        return "month_only"
    if p3.is_valid_exact_jalali_date(value):
        return "exact_day"
    return "invalid"


def _snapshot_candidate(snapshot_root: Path, rel_value: str) -> tuple[Path | None, str]:
    rel_text = _s(rel_value).replace("\\", "/")
    try:
        rel = PurePosixPath(rel_text)
    except Exception:
        return None, "invalid snapshot_path"
    if not rel_text or rel.is_absolute() or ".." in rel.parts:
        return None, "snapshot_path must be a safe relative path"
    if tuple(rel.parts[: len(MANUAL_SNAPSHOT_PREFIX.parts)]) != MANUAL_SNAPSHOT_PREFIX.parts:
        return None, f"snapshot_path must be under {MANUAL_SNAPSHOT_PREFIX.as_posix()}/"

    root = Path(snapshot_root).resolve()
    manual_root = (root / Path(*MANUAL_SNAPSHOT_PREFIX.parts)).resolve()
    candidate = (root / Path(*rel.parts)).resolve()
    try:
        candidate.relative_to(manual_root)
    except ValueError:
        return None, "snapshot_path escapes the manual snapshot root"
    if not candidate.exists() or not candidate.is_file():
        return None, "snapshot file does not exist"
    if candidate.is_symlink():
        return None, "snapshot symlinks are forbidden"
    return candidate, ""


def read_intake_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def validate_manual_evidence_intake(
    intake_df: pd.DataFrame,
    snapshot_root: Path = p3.ROOT,
) -> tuple[bool, list[str], pd.DataFrame]:
    """Validate and normalize an intake table without mutating inputs or files."""
    errors: list[str] = []
    if intake_df is None:
        return False, ["intake is None"], pd.DataFrame(columns=INTAKE_COLUMNS)

    actual = list(intake_df.columns)
    missing = [c for c in INTAKE_COLUMNS if c not in actual]
    extras = [c for c in actual if c not in INTAKE_COLUMNS]
    forbidden = sorted(set(actual) & DERIVED_FORBIDDEN)
    if missing:
        errors.append("missing columns: " + ", ".join(missing))
    if extras:
        errors.append("unexpected columns: " + ", ".join(extras))
    if forbidden:
        errors.append("derived columns are forbidden: " + ", ".join(forbidden))
    if missing or extras:
        return False, errors, pd.DataFrame(columns=INTAKE_COLUMNS)

    normalized = intake_df.copy()
    for c in INTAKE_COLUMNS:
        normalized[c] = normalized[c].map(_s)

    if normalized.empty:
        errors.append("intake has no data rows")
        return False, errors, normalized

    seen: set[tuple[str, str]] = set()
    for pos, (_, row) in enumerate(normalized.iterrows(), start=2):
        prefix = f"row {pos}"
        ticker = p3.normalize_ticker(row["ticker"])
        normalized.at[row.name, "ticker"] = ticker
        url = row["source_url"]
        canon = _canonical_url(url)
        if ticker not in p3.PART03_TICKERS:
            errors.append(f"{prefix}: ticker out of Part 3 scope: {ticker!r}")
        if not _valid_http_url(url):
            errors.append(f"{prefix}: source_url must be http(s) with a real host")
        elif (ticker, canon) in seen:
            errors.append(f"{prefix}: duplicate normalized source_url for ticker")
        else:
            seen.add((ticker, canon))
        if row["source_type"] not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}: invalid source_type {row['source_type']!r}")
        if not row["source_title"]:
            errors.append(f"{prefix}: source_title is required")

        final_url = row["final_url"] or url
        normalized.at[row.name, "final_url"] = final_url
        if not _valid_http_url(final_url):
            errors.append(f"{prefix}: final_url must be blank or valid http(s)")

        snap, snap_error = _snapshot_candidate(Path(snapshot_root), row["snapshot_path"])
        if snap_error:
            errors.append(f"{prefix}: {snap_error}")
        supplied = row["supplied_snapshot_sha256"].lower()
        normalized.at[row.name, "supplied_snapshot_sha256"] = supplied
        if not re.fullmatch(r"[0-9a-f]{64}", supplied):
            errors.append(f"{prefix}: supplied_snapshot_sha256 must be 64 lowercase hex")
        elif snap is not None:
            actual_hash = sha256_file(snap)
            if actual_hash != supplied:
                errors.append(f"{prefix}: supplied snapshot SHA-256 does not match file")

        if not _valid_utc(row["captured_at_utc"]):
            errors.append(f"{prefix}: captured_at_utc must be UTC YYYY-MM-DDTHH:MM:SSZ")
        if row["http_status"]:
            if not row["http_status"].isdigit() or not 100 <= int(row["http_status"]) <= 599:
                errors.append(f"{prefix}: http_status must be 100..599 or blank")
        if not row["content_type"]:
            errors.append(f"{prefix}: content_type is required")

        review_status = row["content_review_status"]
        if review_status not in ALLOWED_REVIEW_STATUSES:
            errors.append(f"{prefix}: invalid content_review_status")
        if row["exact_date_explicit"] not in ALLOWED_BOOL:
            errors.append(f"{prefix}: exact_date_explicit must be true/false")
        if row["publication_date_explicit"] not in ALLOWED_BOOL:
            errors.append(f"{prefix}: publication_date_explicit must be true/false")
        if row["ordinary_share_explicit"] not in ALLOWED_ORDINARY:
            errors.append(f"{prefix}: ordinary_share_explicit must be true/false/unknown")

        event = row["event_type_supported"]
        if event and event not in p3.REVIEWED_EVENT_TYPES:
            errors.append(f"{prefix}: invalid event_type_supported {event!r}")
        reviewed_date = row["reviewed_date_jalali"]
        precision = _date_precision(reviewed_date)
        exact_flag = row["exact_date_explicit"] == "true"
        if precision == "invalid":
            errors.append(f"{prefix}: invalid reviewed_date_jalali")
        if event and not reviewed_date:
            errors.append(f"{prefix}: event_type_supported requires reviewed_date_jalali")
        if reviewed_date and not event:
            errors.append(f"{prefix}: reviewed_date_jalali requires event_type_supported")
        if exact_flag != (precision == "exact_day"):
            errors.append(f"{prefix}: exact_date_explicit disagrees with reviewed date precision")

        pub = row["publication_date_jalali"]
        pub_explicit = row["publication_date_explicit"] == "true"
        if pub_explicit != bool(pub):
            errors.append(f"{prefix}: publication_date_explicit disagrees with publication date")
        if pub and not p3.is_valid_exact_jalali_date(pub):
            errors.append(f"{prefix}: publication_date_jalali must be an exact valid Jalali day")

        if review_status == "pending_manual_review":
            pending_fields = {
                "event_type_supported": event,
                "reviewed_date_jalali": reviewed_date,
                "exact_text_or_event_summary": row["exact_text_or_event_summary"],
                "reviewer_notes": row["reviewer_notes"],
                "manual_reviewed_at_utc": row["manual_reviewed_at_utc"],
                "publication_date_jalali": pub,
            }
            if any(pending_fields.values()) or exact_flag or pub_explicit or row["ordinary_share_explicit"] != "unknown":
                errors.append(f"{prefix}: pending review row must not contain review findings")
        else:
            if not _valid_utc(row["manual_reviewed_at_utc"]):
                errors.append(f"{prefix}: reviewed row requires manual_reviewed_at_utc")
            if not row["reviewer_notes"]:
                errors.append(f"{prefix}: reviewed row requires reviewer_notes")
            if event and not row["exact_text_or_event_summary"]:
                errors.append(f"{prefix}: reviewed event evidence requires text/event summary")

        if not row["added_by"]:
            errors.append(f"{prefix}: added_by is required")

    return len(errors) == 0, errors, normalized


def _next_index(registry: pd.DataFrame, ticker: str) -> int:
    vals = []
    for value in registry.loc[registry["ticker"] == ticker, "source_index"].astype(str):
        if value.isdigit():
            vals.append(int(value))
    return max(vals, default=0) + 1


def _base_provenance_record(row: pd.Series, source_index: int, content_hash: str,
                            response_size: int) -> dict:
    rec = {c: "" for c in p3.PROVENANCE_COLUMNS}
    rec.update({
        "ticker": row["ticker"],
        "source_index": str(source_index),
        "source_type": row["source_type"],
        "source_title": row["source_title"],
        "source_url": row["source_url"],
        "retrieved_at_utc": row["captured_at_utc"],
        "http_status": row["http_status"],
        "retrieval_status": MANUAL_RETRIEVAL_STATUS,
        "final_url": row["final_url"] or row["source_url"],
        "content_type": row["content_type"],
        "response_size_bytes": str(response_size),
        "snapshot_path": row["snapshot_path"],
        "content_sha256": content_hash,
        "extraction_notes": "Manual snapshot imported; SHA-256 recomputed locally; no network request performed.",
        "exact_text_or_event_summary": row["exact_text_or_event_summary"],
        "content_review_status": row["content_review_status"],
        "ordinary_share_explicit": row["ordinary_share_explicit"],
        "event_type_supported": row["event_type_supported"],
        "exact_date_explicit": row["exact_date_explicit"],
        "reviewed_date_jalali": row["reviewed_date_jalali"],
        "publication_date_jalali": row["publication_date_jalali"],
        "publication_date_explicit": row["publication_date_explicit"],
        "reviewer_notes": row["reviewer_notes"],
        "manual_reviewed_at_utc": row["manual_reviewed_at_utc"],
    })
    return rec


def ingest_manual_evidence_intake(
    registry_df: pd.DataFrame,
    existing_provenance_df: pd.DataFrame,
    intake_df: pd.DataFrame,
    snapshot_root: Path = p3.ROOT,
    apply_mode: str = "dry_run",
    applied_at_utc: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return updated registry, normalized provenance, and an audit table.

    Validation completes before any copy is changed. Existing ticker+URL records keep
    their source_index. New URLs receive the next per-ticker index (normally >=3).
    No file is written and no network request is performed.
    """
    ok, errors, intake = validate_manual_evidence_intake(intake_df, snapshot_root)
    if not ok:
        raise ValueError("manual intake validation failed: " + " | ".join(errors))

    registry = registry_df.copy(deep=True)
    provenance = existing_provenance_df.copy(deep=True)
    for col in p3.SOURCE_REGISTRY_COLUMNS:
        if col not in registry.columns:
            registry[col] = ""
    registry = registry[p3.SOURCE_REGISTRY_COLUMNS].copy()
    for col in p3.PROVENANCE_COLUMNS:
        if col not in provenance.columns:
            provenance[col] = ""
    provenance = provenance[p3.PROVENANCE_COLUMNS].copy()

    ok_registry, registry_errors = p3.validate_source_registry(registry)
    if not ok_registry:
        raise ValueError("existing source registry is invalid: " + " | ".join(registry_errors))

    by_url: dict[tuple[str, str], int] = {}
    for idx, r in registry.iterrows():
        by_url[(p3.normalize_ticker(r["ticker"]), _canonical_url(r["source_url"]))] = idx

    audit_rows = []
    applied = applied_at_utc or utc_now()
    new_records: list[dict] = []
    replaced_keys: set[tuple[str, str]] = set()

    for intake_pos, (_, row) in enumerate(intake.iterrows(), start=2):
        ticker = row["ticker"]
        key = (ticker, _canonical_url(row["source_url"]))
        reg_idx = by_url.get(key)
        if reg_idx is not None:
            current_type = _s(registry.at[reg_idx, "source_type"])
            if current_type and current_type != row["source_type"]:
                raise ValueError(
                    f"row {intake_pos}: existing URL source_type mismatch: "
                    f"registry={current_type!r}, intake={row['source_type']!r}"
                )
            source_index = int(str(registry.at[reg_idx, "source_index"]))
            registry_action = "existing_url_reused"
            registry.at[reg_idx, "source_title"] = row["source_title"]
            registry.at[reg_idx, "active"] = "true"
            registry.at[reg_idx, "discovery_status"] = "manual_snapshot_captured"
            if not _s(registry.at[reg_idx, "added_at_utc"]):
                registry.at[reg_idx, "added_at_utc"] = row["captured_at_utc"]
            if not _s(registry.at[reg_idx, "added_by"]):
                registry.at[reg_idx, "added_by"] = row["added_by"]
            registry.at[reg_idx, "discovery_notes"] = row["discovery_notes"]
        else:
            source_index = _next_index(registry, ticker)
            if source_index < 3:
                source_index = 3
                while ((registry["ticker"] == ticker)
                       & (registry["source_index"].astype(str) == str(source_index))).any():
                    source_index += 1
            registry = pd.concat([registry, pd.DataFrame([{
                "ticker": ticker,
                "source_index": str(source_index),
                "source_type": row["source_type"],
                "source_title": row["source_title"],
                "source_url": row["source_url"],
                "source_origin": "manual_discovery",
                "active": "true",
                "discovery_status": "manual_snapshot_captured",
                "added_at_utc": row["captured_at_utc"],
                "added_by": row["added_by"],
                "discovery_notes": row["discovery_notes"],
            }], columns=p3.SOURCE_REGISTRY_COLUMNS)], ignore_index=True)
            by_url[key] = registry.index[-1]
            registry_action = "new_source_registered"

        snap, snap_error = _snapshot_candidate(Path(snapshot_root), row["snapshot_path"])
        if snap_error or snap is None:  # defensive; validation already passed
            raise ValueError(f"row {intake_pos}: {snap_error or 'snapshot unavailable'}")
        computed_hash = sha256_file(snap)
        rec = _base_provenance_record(row, source_index, computed_hash, snap.stat().st_size)
        new_records.append(rec)
        replaced_keys.add((ticker, str(source_index)))

        existed = ((provenance["ticker"].map(p3.normalize_ticker) == ticker)
                   & (provenance["source_index"].astype(str) == str(source_index))).any()
        audit_rows.append({
            "intake_row_number": str(intake_pos),
            "ticker": ticker,
            "source_url": row["source_url"],
            "source_index": str(source_index),
            "registry_action": registry_action,
            "provenance_action": "replaced_existing_record" if existed else "added_record",
            "snapshot_path": row["snapshot_path"],
            "computed_snapshot_sha256": computed_hash,
            "supplied_snapshot_sha256": row["supplied_snapshot_sha256"],
            "content_review_status": row["content_review_status"],
            "event_type_supported": row["event_type_supported"],
            "reviewed_date_jalali": row["reviewed_date_jalali"],
            "validation_status": "valid",
            "validation_errors": "",
            "apply_mode": apply_mode,
            "applied_at_utc": applied,
        })

    keep = ~provenance.apply(
        lambda r: (p3.normalize_ticker(r["ticker"]), str(r["source_index"])) in replaced_keys,
        axis=1,
    )
    raw_records = provenance.loc[keep, p3.PROVENANCE_COLUMNS].to_dict("records") + new_records
    normalized_records = p3.normalize_provenance_records(raw_records, Path(snapshot_root))
    updated_provenance = pd.DataFrame(normalized_records, columns=p3.PROVENANCE_COLUMNS)

    ok_registry, registry_errors = p3.validate_source_registry(registry)
    if not ok_registry:
        raise ValueError("updated source registry is invalid: " + " | ".join(registry_errors))

    # Active registry rows must map one-to-one to provenance keys.
    active_keys = {
        (p3.normalize_ticker(r["ticker"]), str(r["source_index"]))
        for _, r in registry.iterrows() if _s(r["active"]).lower() == "true"
    }
    prov_keys = {
        (p3.normalize_ticker(r["ticker"]), str(r["source_index"]))
        for _, r in updated_provenance.iterrows()
    }
    if active_keys != prov_keys:
        missing = sorted(active_keys - prov_keys)
        extra = sorted(prov_keys - active_keys)
        raise ValueError(f"registry/provenance key mismatch; missing={missing}, extra={extra}")

    audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
    return registry.reset_index(drop=True), updated_provenance.reset_index(drop=True), audit
