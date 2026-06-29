#!/usr/bin/env python3
"""Stage124 Batch 2 — Part 3.1B.0: research-intake readiness.

This step prepares and validates a dedicated manual-research intake file for the
exact 10 Part 3 tickers. It is deliberately separate from the sealed Part 3.1A.5.3
screening pipeline.

Safety properties
-----------------
* no network requests;
* dry-run by default — the registry is changed only with ``--apply``;
* exact input schema and fail-closed row validation;
* snapshot paths must be safe relative paths confined beneath
  ``stage124/batch02_parts/snapshots_part03/``;
* snapshot SHA-256 is recomputed from the stored file;
* Stage122/Stage123 and sealed Part 3 outputs are never written;
* registry/report writes are rollback-protected as one package.

The current committed intake is header-only, so the default run is a true no-op.
Actual URLs/snapshots are a later research step.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from src.stage124_batch02_part03 import (  # noqa: E402
    PART03_DIR,
    PART03_TICKERS,
    ROOT,
    SOURCE_REGISTRY_COLUMNS,
    SOURCE_REGISTRY_PATH,
    build_seed_registry_df,
    git_head,
    is_valid_exact_jalali_date,
    load_source_registry,
    register_discovered_sources,
    sha,
    validate_source_registry,
    validate_worklist_date_precision,
    _is_sha256,
    _worklist_url_ok,
)

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
SNAPSHOT_ROOT_REL = PurePosixPath(
    "stage124/batch02_parts/snapshots_part03"
)

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
    candidate = (root_resolved / Path(*rel.parts)).resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        return None, "snapshot_path escapes the snapshot root"
    if not candidate.exists() or not candidate.is_file():
        return None, f"snapshot file not found: {raw}"
    if candidate.is_symlink():
        return None, "snapshot symlinks are forbidden"
    return candidate, ""


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
    if findings.empty:
        status = "ready_no_findings"
    elif apply:
        status = "findings_registered"
    else:
        status = "findings_validated_dry_run"

    report = {
        "stage": "stage124_batch02_part03_manual_intake",
        "part": "3.1B.0",
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
        "registry_rows_before": int(registry_before),
        "registry_rows_after": int(
            len(proposed_registry) if apply else registry_before
        ),
        "per_ticker_proposed": per_ticker,
        "snapshots_verified": snapshots_verified,
    }

    if apply and findings.empty:
        raise IntakeError("--apply refused because the intake has no findings")

    outputs: dict[Path, bytes] = {}
    if apply:
        outputs[registry_path] = _csv_bytes(
            proposed_registry[SOURCE_REGISTRY_COLUMNS]
        )
        outputs[report_path] = _json_bytes(report)
    elif write_report:
        outputs[report_path] = _json_bytes(report)
    if outputs:
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

    print("Part 3.1B.0 manual intake:")
    print(f"  status              : {report['status']}")
    print(f"  findings            : {report['findings_count']}")
    print(f"  sources proposed    : {report['sources_proposed']}")
    print(f"  sources registered  : {report['sources_registered']}")
    print(f"  network performed   : {report['network_request_performed']}")
    if not args.apply:
        print("  mode                : DRY RUN (no registry changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
