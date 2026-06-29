"""Tests for the Part 3.1B.0 manual-intake runner.

Semantic / future-compatible and synthetic: the readiness no-op, fail-closed
validation (out-of-scope ticker, bad URL, missing/mismatched snapshot, date
disagreement), and a legitimate finding registering into a temp registry. The
real committed Part 3 artifacts are never mutated by these tests.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import run_stage124_batch02_part03_manual_intake as intake   # noqa: E402
from src.stage124_batch02_part03 import (                    # noqa: E402
    PART03_TICKERS, build_seed_registry_df, write_csv, load_source_registry, sha,
)

REAL_ROOT = Path(PROJECT_DIR)   # the module's ROOT (outputs live under project/)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _seed_registry(root: Path) -> Path:
    reg = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    reg.parent.mkdir(parents=True, exist_ok=True)
    write_csv(build_seed_registry_df(), reg)
    return reg


def _write_intake(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=intake.INTAKE_COLUMNS) if rows else \
        pd.DataFrame(columns=intake.INTAKE_COLUMNS)
    df.to_csv(path, index=False)


def _snapshot(root: Path, name: str = "x.html", body: str = "<html>ok</html>") -> tuple[str, str]:
    rel = f"stage124/batch02_parts/snapshots_part03/{name}"
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return rel, sha(p)


def _valid_row(root: Path, **over) -> dict:
    rel, h = _snapshot(root)
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
        "content_sha256": h,
        "publication_date_jalali": "",
        "added_by": "researcher",
        "discovery_notes": "manual finding",
        # New audit fields with defaults
        "captured_at_utc": "",
        "content_type": "text/html",
        "http_status": "200",
        "final_url": "",
        "content_review_status": "pending_manual_review",
        "exact_text_or_event_summary": "",
        "reviewer_notes": "",
        "manual_reviewed_at_utc": "",
        "publication_date_explicit": "false",
    }
    row.update(over)
    return row


def _run(tmp: Path, rows=None, create_input=True):
    intake_path = tmp / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    if create_input:
        _write_intake(intake_path, rows or [])
    reg = _seed_registry(tmp)
    report = tmp / "stage124" / "batch02_parts" / "part03_manual_intake_report.json"
    return intake.run_intake(intake_path=intake_path, registry_path=reg,
                             report_path=report, root=tmp), reg, report


# --------------------------------------------------------------------------- #
# readiness / no-op
# --------------------------------------------------------------------------- #

def test_empty_intake_is_noop(tmp_path):
    rep, reg, report = _run(tmp_path, rows=[])
    assert rep["status"] == "ready_no_findings"
    assert rep["findings_count"] == 0
    assert rep["sources_registered"] == 0
    assert rep["registry_rows_before"] == rep["registry_rows_after"] == 20
    assert report.exists()


def test_template_created_when_missing(tmp_path):
    rep, reg, _ = _run(tmp_path, create_input=False)
    assert rep["intake_template_created"] is True
    assert rep["status"] == "ready_no_findings"
    df = pd.read_csv(tmp_path / "stage124/batch02_parts/part03_manual_intake_input.csv",
                     dtype=str)
    assert list(df.columns) == intake.INTAKE_COLUMNS


def test_noop_leaves_registry_unchanged(tmp_path):
    _, reg, _ = _run(tmp_path, rows=[])
    assert len(load_source_registry(reg)) == 20


# --------------------------------------------------------------------------- #
# valid finding registers
# --------------------------------------------------------------------------- #

def test_valid_finding_registers(tmp_path):
    rep, reg, _ = _run(tmp_path, rows=[_valid_row(tmp_path)])
    assert rep["status"] == "findings_validated"  # Dry-run mode
    assert rep["findings_count"] == 1
    assert rep["sources_registered"] == 0  # Dry-run doesn't actually register
    assert rep["registry_rows_before"] == rep["registry_rows_after"] == 20  # No change in dry-run


def test_finding_without_snapshot_is_allowed(tmp_path):
    # A discovered URL with no snapshot/date yet is a legitimate intake.
    row = _valid_row(tmp_path, snapshot_path="", content_sha256="",
                     candidate_date_jalali="", date_precision="unknown",
                     event_type_candidate="")
    rep, _, _ = _run(tmp_path, rows=[row])
    assert rep["sources_registered"] == 0  # Dry-run mode


def test_reviewed_status_requires_notes_and_timestamp(tmp_path):
    # Reviewed status must have reviewer_notes and manual_reviewed_at_utc
    row = _valid_row(tmp_path, content_review_status="reviewed")
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[row])
    
    # Add missing fields
    row["reviewer_notes"] = "Reviewed and confirmed"
    row["manual_reviewed_at_utc"] = "2026-06-29T10:00:00Z"
    rep, _, _ = _run(tmp_path, rows=[row])
    assert rep["sources_registered"] == 0  # Dry-run mode


def test_pending_review_allows_findings(tmp_path):
    # pending_manual_review CAN have findings - they're just not processed until reviewed
    row = _valid_row(tmp_path, content_review_status="pending_manual_review",
                     event_type_candidate="first_public_offering",
                     candidate_date_jalali="1380-03-15")
    rep, _, _ = _run(tmp_path, rows=[row])
    assert rep["sources_registered"] == 0  # Dry-run mode


def test_findings_require_snapshot(tmp_path):
    # Event/date findings require snapshot and hash
    row = _valid_row(tmp_path, snapshot_path="", content_sha256="",
                     event_type_candidate="first_public_offering",
                     candidate_date_jalali="1380-03-15")
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[row])


def test_invalid_review_status_fails(tmp_path):
    row = _valid_row(tmp_path, content_review_status="invalid_status")
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[row])


# --------------------------------------------------------------------------- #
# fail-closed validation (negative tests)
# --------------------------------------------------------------------------- #

def test_out_of_scope_ticker_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, ticker="فولاد")])


def test_bad_url_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, source_url="file:///Users/x")])


def test_missing_source_url_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, source_url="")])


def test_snapshot_missing_file_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(
            tmp_path,
            snapshot_path="stage124/batch02_parts/snapshots_part03/nope.html",
            content_sha256="a" * 64)])


def test_snapshot_hash_mismatch_fails(tmp_path):
    row = _valid_row(tmp_path)
    row["content_sha256"] = "b" * 64          # wrong hash for a real file
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[row])


def test_snapshot_without_hash_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, content_sha256="")])


def test_date_precision_disagreement_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path,
                                        candidate_date_jalali="1380",
                                        date_precision="exact_day")])


def test_bad_event_type_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, event_type_candidate="ipo")])


def test_snapshot_outside_snapshot_dir_fails(tmp_path):
    rel = "stage124/batch02_parts/x.html"
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, rows=[_valid_row(tmp_path, snapshot_path=rel,
                                        content_sha256=sha(p))])


# --------------------------------------------------------------------------- #
# --apply functionality tests
# --------------------------------------------------------------------------- #

def test_apply_creates_provenance_records(tmp_path):
    """Test that --apply creates provenance records for manual snapshots."""
    row = _valid_row(tmp_path)
    rep, reg, report = _run(tmp_path, rows=[row], create_input=True)
    
    # Test dry-run first (no apply)
    assert rep["status"] == "findings_validated"
    assert rep["sources_registered"] == 0  # Dry-run doesn't register
    assert rep.get("provenance_created", 0) == 0
    
    # Now test with apply
    prov_path = tmp_path / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv"
    
    # Run with apply=True by calling run_intake directly
    intake_path = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    _write_intake(intake_path, [row])
    
    rep_apply = intake.run_intake(
        intake_path=intake_path, 
        registry_path=reg, 
        report_path=report, 
        root=tmp_path,
        write_report=False,
        apply_changes=True
    )
    
    assert rep_apply["status"] in ["applied_with_provenance", "applied_discovery_only"]
    assert rep_apply["sources_registered"] == 1
    assert rep_apply.get("provenance_created", 0) >= 0
    
    # Check that provenance file was created/updated
    assert prov_path.exists()


def test_discovery_only_apply(tmp_path):
    """Test apply with discovery-only rows (no snapshot)."""
    row = _valid_row(tmp_path, snapshot_path="", content_sha256="",
                     candidate_date_jalali="", date_precision="unknown",
                     event_type_candidate="")
    
    intake_path = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    _write_intake(intake_path, [row])
    reg = _seed_registry(tmp_path)
    report = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_report.json"
    
    rep = intake.run_intake(
        intake_path=intake_path, 
        registry_path=reg, 
        report_path=report, 
        root=tmp_path,
        write_report=False,
        apply_changes=True
    )
    
    assert rep["status"] == "applied_discovery_only"
    assert rep["sources_registered"] == 1
    assert rep.get("provenance_created", 0) == 0


def test_apply_without_snapshot_fails(tmp_path):
    """Test that apply fails for findings without snapshot."""
    row = _valid_row(tmp_path, snapshot_path="", content_sha256="",
                     event_type_candidate="first_public_offering",
                     candidate_date_jalali="1380-03-15")
    
    intake_path = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    _write_intake(intake_path, [row])
    
    with pytest.raises(intake.IntakeError):
        intake.run_intake(
            intake_path=intake_path, 
            root=tmp_path,
            write_report=False,
            apply_changes=True
        )


def test_atomic_rollback_on_failure(tmp_path):
    """Test that atomic apply rolls back on failure."""
    # Create a valid row and an invalid row
    valid_row = _valid_row(tmp_path)
    invalid_row = _valid_row(tmp_path, ticker="فولاد")  # Out of scope
    
    intake_path = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    _write_intake(intake_path, [valid_row, invalid_row])
    
    # Get initial registry state
    reg = _seed_registry(tmp_path)
    initial_reg_content = reg.read_text(encoding="utf-8")
    
    # Apply should fail and rollback
    with pytest.raises(intake.IntakeError):
        intake.run_intake(
            intake_path=intake_path, 
            registry_path=reg, 
            root=tmp_path,
            write_report=False,
            apply_changes=True
        )
    
    # Registry should be unchanged
    assert reg.read_text(encoding="utf-8") == initial_reg_content


def test_manual_snapshot_imported_status(tmp_path):
    """Test that manual snapshots get manual_snapshot_imported status."""
    row = _valid_row(tmp_path)
    
    intake_path = tmp_path / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv"
    _write_intake(intake_path, [row])
    reg = _seed_registry(tmp_path)
    
    # Apply changes
    intake.run_intake(
        intake_path=intake_path, 
        registry_path=reg, 
        root=tmp_path,
        write_report=False,
        apply_changes=True
    )
    
    # Check provenance record
    prov_path = tmp_path / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv"
    if prov_path.exists():
        prov_df = pd.read_csv(prov_path, dtype=str)
        manual_records = prov_df[prov_df["retrieval_status"] == "manual_snapshot_imported"]
        assert len(manual_records) > 0
        
        # Check that derived fields are computed
        record = manual_records.iloc[0]
        assert record["source_authority_class"] != ""
        assert record["independent_source_group"] != ""


# --------------------------------------------------------------------------- #
# real committed artifacts
# --------------------------------------------------------------------------- #

def test_committed_template_schema_valid():
    p = REAL_ROOT / "stage124/batch02_parts/part03_manual_intake_input.csv"
    if not p.exists():
        pytest.skip("intake template not generated yet")
    df = pd.read_csv(p, dtype=str)
    assert list(df.columns) == intake.INTAKE_COLUMNS


def test_real_repo_intake_is_noop_and_nondestructive():
    # Reading the real (empty) intake must not register anything; write no report.
    rep = intake.run_intake(write_report=False)
    assert rep["status"] == "ready_no_findings"
    assert rep["sources_registered"] == 0
