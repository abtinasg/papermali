"""Tests for the hardened Part 3.1B.0 manual-intake runner.

The real committed Part 3 artifacts are read-only. Mutation tests use a temporary
repository-like directory and synthetic registry/intake/snapshot files.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import run_stage124_batch02_part03_manual_intake as intake  # noqa: E402
from src.stage124_batch02_part03 import (  # noqa: E402
    PART03_TICKERS,
    build_seed_registry_df,
    load_source_registry,
    sha,
    write_csv,
)

REAL_ROOT = Path(PROJECT_DIR)


def _seed_registry(root: Path) -> Path:
    path = root / "stage124/batch02_parts/part03_source_registry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(build_seed_registry_df(), path)
    return path


def _write_intake(path: Path, rows: list[dict], *, extra_column: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=intake.INTAKE_COLUMNS)
    if extra_column:
        df["unexpected"] = "x"
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _snapshot(
    root: Path,
    name: str = "manual/x.html",
    body: bytes = b"<html>ordinary-share offering evidence</html>",
) -> tuple[str, str]:
    rel = Path("stage124/batch02_parts/snapshots_part03") / name
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return rel.as_posix(), hashlib.sha256(body).hexdigest()


def _valid_row(root: Path, **overrides) -> dict:
    rel, digest = _snapshot(root)
    row = {
        "ticker": PART03_TICKERS[0],
        "source_type": "codal_official",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=abc",
        "source_title": "Codal decision",
        "event_type_candidate": "first_public_offering",
        "candidate_date_jalali": "1380-03-15",
        "date_precision": "exact_day",
        "ordinary_share_explicit": "true",
        "snapshot_path": rel,
        "content_sha256": digest,
        "publication_date_jalali": "",
        "added_by": "researcher",
        "discovery_notes": "manual finding",
    }
    row.update(overrides)
    return row


def _paths(tmp_path: Path):
    intake_path = tmp_path / "stage124/batch02_parts/part03_manual_intake_input.csv"
    registry_path = _seed_registry(tmp_path)
    report_path = tmp_path / "stage124/batch02_parts/part03_manual_intake_report.json"
    return intake_path, registry_path, report_path


def _run(
    tmp_path: Path,
    rows: list[dict],
    *,
    apply: bool = False,
    write_report: bool = False,
):
    intake_path, registry_path, report_path = _paths(tmp_path)
    _write_intake(intake_path, rows)
    report = intake.run_intake(
        intake_path=intake_path,
        registry_path=registry_path,
        report_path=report_path,
        root=tmp_path,
        apply=apply,
        write_report=write_report,
    )
    return report, registry_path, report_path


# --------------------------------------------------------------------------- #
# baseline / dry-run semantics
# --------------------------------------------------------------------------- #


def test_empty_intake_is_true_noop(tmp_path):
    report, registry, report_path = _run(tmp_path, [])
    assert report["status"] == "ready_no_findings"
    assert report["findings_count"] == 0
    assert report["sources_proposed"] == 0
    assert report["sources_registered"] == 0
    assert report["network_request_performed"] is False
    assert len(load_source_registry(registry)) == 20
    assert not report_path.exists()


def test_missing_tracked_template_fails(tmp_path):
    _, registry, report_path = _paths(tmp_path)
    missing = tmp_path / "stage124/batch02_parts/missing.csv"
    with pytest.raises(intake.IntakeError, match="intake file not found"):
        intake.run_intake(
            intake_path=missing,
            registry_path=registry,
            report_path=report_path,
            root=tmp_path,
        )


def test_valid_finding_dry_run_does_not_mutate_registry(tmp_path):
    report, registry, report_path = _run(tmp_path, [_valid_row(tmp_path)])
    assert report["status"] == "findings_validated_dry_run"
    assert report["sources_proposed"] == 1
    assert report["sources_registered"] == 0
    assert report["registry_rows_before"] == report["registry_rows_after"] == 20
    assert len(load_source_registry(registry)) == 20
    assert not report_path.exists()


def test_apply_valid_finding_registers_and_writes_report(tmp_path):
    report, registry, report_path = _run(
        tmp_path, [_valid_row(tmp_path)], apply=True
    )
    assert report["status"] == "findings_registered"
    assert report["sources_registered"] == 1
    assert report["registry_rows_after"] == 21
    assert report_path.exists()
    df = load_source_registry(registry)
    added = df[df["source_origin"] == "manual_discovery"]
    assert len(added) == 1
    assert added.iloc[0]["source_index"] == "3"


def test_apply_empty_intake_is_refused(tmp_path):
    with pytest.raises(intake.IntakeError, match="no findings"):
        _run(tmp_path, [], apply=True)


def test_explicit_dry_run_report_is_allowed(tmp_path):
    report, registry, report_path = _run(
        tmp_path, [_valid_row(tmp_path)], write_report=True
    )
    assert report["sources_registered"] == 0
    assert len(load_source_registry(registry)) == 20
    assert report_path.exists()


def test_discovery_only_row_without_snapshot_is_allowed(tmp_path):
    row = _valid_row(
        tmp_path,
        event_type_candidate="",
        candidate_date_jalali="",
        date_precision="unknown",
        ordinary_share_explicit="unknown",
        snapshot_path="",
        content_sha256="",
        publication_date_jalali="",
    )
    report, registry, _ = _run(tmp_path, [row])
    assert report["sources_proposed"] == 1
    assert len(load_source_registry(registry)) == 20


# --------------------------------------------------------------------------- #
# schema and row validation
# --------------------------------------------------------------------------- #


def test_extra_column_fails(tmp_path):
    intake_path, registry, report = _paths(tmp_path)
    _write_intake(intake_path, [_valid_row(tmp_path)], extra_column=True)
    with pytest.raises(intake.IntakeError, match="schema mismatch"):
        intake.run_intake(
            intake_path=intake_path,
            registry_path=registry,
            report_path=report,
            root=tmp_path,
        )


@pytest.mark.parametrize("source_type", ["", "official", "random_blog"])
def test_invalid_source_type_fails(tmp_path, source_type):
    with pytest.raises(intake.IntakeError, match="source_type"):
        _run(tmp_path, [_valid_row(tmp_path, source_type=source_type)])


def test_missing_title_or_added_by_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, [_valid_row(tmp_path, source_title="", added_by="")])


def test_out_of_scope_ticker_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="out of Part 3 scope"):
        _run(tmp_path, [_valid_row(tmp_path, ticker="فولاد")])


def test_bad_url_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="source_url"):
        _run(tmp_path, [_valid_row(tmp_path, source_url="file:///Users/x")])


def test_duplicate_normalized_url_fails(tmp_path):
    first = _valid_row(tmp_path)
    second = _valid_row(
        tmp_path,
        source_url=first["source_url"] + "/",
        source_title="duplicate URL",
    )
    with pytest.raises(intake.IntakeError, match="duplicate normalized"):
        _run(tmp_path, [first, second])


def test_date_precision_disagreement_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="disagrees"):
        _run(
            tmp_path,
            [_valid_row(tmp_path, candidate_date_jalali="1380", date_precision="exact_day")],
        )


def test_event_requires_date(tmp_path):
    with pytest.raises(intake.IntakeError, match="requires candidate_date"):
        _run(
            tmp_path,
            [_valid_row(tmp_path, candidate_date_jalali="", date_precision="unknown")],
        )


def test_date_requires_specific_event(tmp_path):
    with pytest.raises(intake.IntakeError, match="specific event"):
        _run(tmp_path, [_valid_row(tmp_path, event_type_candidate="unresolved")])


def test_bad_publication_date_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="publication_date_jalali"):
        _run(tmp_path, [_valid_row(tmp_path, publication_date_jalali="1400-13-01")])


def test_evidence_fields_require_snapshot(tmp_path):
    with pytest.raises(intake.IntakeError, match="require snapshot_path"):
        _run(
            tmp_path,
            [_valid_row(tmp_path, snapshot_path="", content_sha256="")],
        )


# --------------------------------------------------------------------------- #
# snapshot confinement and integrity
# --------------------------------------------------------------------------- #


def test_missing_snapshot_file_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="file not found"):
        _run(
            tmp_path,
            [
                _valid_row(
                    tmp_path,
                    snapshot_path=(
                        "stage124/batch02_parts/snapshots_part03/manual/nope.html"
                    ),
                    content_sha256="a" * 64,
                )
            ],
        )


def test_snapshot_hash_mismatch_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="does not match"):
        _run(tmp_path, [_valid_row(tmp_path, content_sha256="b" * 64)])


def test_absolute_snapshot_path_fails(tmp_path):
    outside = tmp_path / "stage124/batch02_parts/snapshots_part03/absolute.html"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="safe relative"):
        _run(
            tmp_path,
            [
                _valid_row(
                    tmp_path,
                    snapshot_path=str(outside.resolve()),
                    content_sha256=sha(outside),
                )
            ],
        )


def test_path_traversal_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="safe relative"):
        _run(
            tmp_path,
            [
                _valid_row(
                    tmp_path,
                    snapshot_path=(
                        "stage124/batch02_parts/snapshots_part03/manual/../../x.html"
                    ),
                )
            ],
        )


def test_snapshot_outside_exact_prefix_fails(tmp_path):
    outside = tmp_path / "stage124/batch02_parts/x_snapshots_part03/y.html"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="must be under"):
        _run(
            tmp_path,
            [
                _valid_row(
                    tmp_path,
                    snapshot_path="stage124/batch02_parts/x_snapshots_part03/y.html",
                    content_sha256=sha(outside),
                )
            ],
        )


# --------------------------------------------------------------------------- #
# committed real template
# --------------------------------------------------------------------------- #


def test_committed_template_schema_valid():
    path = REAL_ROOT / "stage124/batch02_parts/part03_manual_intake_input.csv"
    assert path.is_file()
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    assert list(df.columns) == intake.INTAKE_COLUMNS


def test_real_repo_intake_is_noop_and_nondestructive():
    report = intake.run_intake(write_report=False, apply=False)
    assert report["status"] == "ready_no_findings"
    assert report["sources_registered"] == 0
    assert report["network_request_performed"] is False
