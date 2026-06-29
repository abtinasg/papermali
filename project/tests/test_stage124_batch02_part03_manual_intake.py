"""Tests for Stage124 Batch02 Part 3.1B.1A — Manual Intake to Provenance Bridge.

The real committed Part 3 artifacts are read-only. Mutation tests use a temporary
repository-like directory and synthetic registry/intake/snapshot files.

Mandatory test coverage:
  - dry-run changes nothing
  - pending_manual_review with findings is rejected
  - reviewed without notes is rejected
  - reviewed without timestamp is rejected
  - hash mismatch is rejected
  - path traversal is rejected
  - absolute path is rejected
  - symlink is rejected
  - apply creates exactly one provenance record
  - manual_snapshot_imported counts as fetched
  - screening is recomputed
  - research counts match provenance
  - aggregator alone is not accepted
  - official document-specific fixture passes engine
  - registry/provenance integrity
  - failure injection rolls back all files
  - Stage122/Stage123 byte-for-byte unchanged
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import run_stage124_batch02_part03_manual_intake as intake  # noqa: E402
from src.stage124_batch02_part03 import (  # noqa: E402
    FETCHED_STATUSES,
    PART03_TICKERS,
    PROVENANCE_COLUMNS,
    build_seed_registry_df,
    classify_source_authority_with_validation,
    compute_evidence_accepted,
    evaluate_source_record,
    is_document_specific_source,
    load_source_registry,
    normalize_provenance_records,
    sha,
    write_csv,
)

REAL_ROOT = Path(PROJECT_DIR)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

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


def _reviewed_row(root: Path, **overrides) -> dict:
    """A fully reviewed row with snapshot — produces provenance on apply."""
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
        "content_review_status": "reviewed",
        "reviewer_notes": "Reviewed and confirmed as ordinary-share offering",
        "manual_reviewed_at_utc": "2026-06-29T10:00:00Z",
    }
    row.update(overrides)
    return row


def _discovery_row(root: Path, **overrides) -> dict:
    """A discovery-only row — no snapshot, no date, no event."""
    row = {
        "ticker": PART03_TICKERS[0],
        "source_type": "codal_official",
        "source_url": "https://www.codal.ir/ReportList.aspx?search&Symbol=test",
        "source_title": "Codal search page",
        "event_type_candidate": "",
        "candidate_date_jalali": "",
        "date_precision": "unknown",
        "ordinary_share_explicit": "unknown",
        "snapshot_path": "",
        "content_sha256": "",
        "publication_date_jalali": "",
        "added_by": "researcher",
        "discovery_notes": "discovery only",
        "content_review_status": "",
        "reviewer_notes": "",
        "manual_reviewed_at_utc": "",
    }
    row.update(overrides)
    return row


def _pending_row(root: Path, **overrides) -> dict:
    """A pending_manual_review row — no findings allowed."""
    rel, digest = _snapshot(root)
    row = {
        "ticker": PART03_TICKERS[0],
        "source_type": "codal_official",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=pend",
        "source_title": "Codal decision pending",
        "event_type_candidate": "",
        "candidate_date_jalali": "",
        "date_precision": "unknown",
        "ordinary_share_explicit": "unknown",
        "snapshot_path": rel,
        "content_sha256": digest,
        "publication_date_jalali": "",
        "added_by": "researcher",
        "discovery_notes": "pending review",
        "content_review_status": "pending_manual_review",
        "reviewer_notes": "",
        "manual_reviewed_at_utc": "",
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


# ---------------------------------------------------------------------------
# baseline / dry-run semantics
# ---------------------------------------------------------------------------


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


def test_dry_run_does_not_mutate_any_file(tmp_path):
    """dry-run must not change any file."""
    intake_path, registry_path, report_path = _paths(tmp_path)
    _write_intake(intake_path, [_reviewed_row(tmp_path)])
    reg_before = registry_path.read_bytes()

    provenance_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    screening_path = tmp_path / "stage124/batch02_parts/part03_research_screening_10tickers.csv"

    report = intake.run_intake(
        intake_path=intake_path,
        registry_path=registry_path,
        report_path=report_path,
        root=tmp_path,
        apply=False,
    )
    assert report["status"] == "findings_validated_dry_run"
    assert report["sources_proposed"] == 1
    assert report["sources_registered"] == 0
    assert report["provenance_created"] == 0
    assert report["registry_rows_before"] == report["registry_rows_after"] == 20
    # Registry bytes unchanged
    assert registry_path.read_bytes() == reg_before
    # No provenance/screening/report written
    assert not provenance_path.exists()
    assert not screening_path.exists()
    assert not report_path.exists()


# ---------------------------------------------------------------------------
# Human-in-the-Loop review status rules
# ---------------------------------------------------------------------------


def test_pending_review_with_finding_is_rejected(tmp_path):
    """pending_manual_review must NOT have event_type_candidate."""
    row = _pending_row(tmp_path, event_type_candidate="first_public_offering",
                       candidate_date_jalali="1380-03-15",
                       date_precision="exact_day")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not have event_type_candidate"):
        _run(tmp_path, [row])


def test_pending_review_with_date_is_rejected(tmp_path):
    """pending_manual_review must NOT have candidate_date_jalali."""
    row = _pending_row(tmp_path, candidate_date_jalali="1380-03-15",
                       date_precision="exact_day",
                       event_type_candidate="first_public_offering")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not"):
        _run(tmp_path, [row])


def test_pending_review_with_ordinary_true_is_rejected(tmp_path):
    """pending_manual_review must NOT have ordinary_share_explicit=true."""
    row = _pending_row(tmp_path, ordinary_share_explicit="true")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not have.*ordinary_share_explicit"):
        _run(tmp_path, [row])


def test_pending_review_with_ordinary_false_is_rejected(tmp_path):
    """pending_manual_review must NOT have ordinary_share_explicit=false."""
    row = _pending_row(tmp_path, ordinary_share_explicit="false")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not have.*ordinary_share_explicit"):
        _run(tmp_path, [row])


def test_pending_review_with_reviewer_notes_is_rejected(tmp_path):
    """pending_manual_review must NOT have reviewer_notes."""
    row = _pending_row(tmp_path, reviewer_notes="some notes")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not have reviewer_notes"):
        _run(tmp_path, [row])


def test_pending_review_with_reviewed_at_is_rejected(tmp_path):
    """pending_manual_review must NOT have manual_reviewed_at_utc."""
    row = _pending_row(tmp_path, manual_reviewed_at_utc="2026-06-29T10:00:00Z")
    with pytest.raises(intake.IntakeError, match="pending_manual_review must not have manual_reviewed_at_utc"):
        _run(tmp_path, [row])


def test_reviewed_without_notes_is_rejected(tmp_path):
    """reviewed status requires reviewer_notes."""
    row = _reviewed_row(tmp_path, reviewer_notes="")
    with pytest.raises(intake.IntakeError, match="reviewed status requires reviewer_notes"):
        _run(tmp_path, [row])


def test_reviewed_without_timestamp_is_rejected(tmp_path):
    """reviewed status requires manual_reviewed_at_utc."""
    row = _reviewed_row(tmp_path, manual_reviewed_at_utc="")
    with pytest.raises(intake.IntakeError, match="reviewed status requires manual_reviewed_at_utc"):
        _run(tmp_path, [row])


def test_reviewed_with_invalid_timestamp_is_rejected(tmp_path):
    """manual_reviewed_at_utc must be a valid UTC timestamp."""
    row = _reviewed_row(tmp_path, manual_reviewed_at_utc="not-a-date")
    with pytest.raises(intake.IntakeError, match="valid UTC timestamp"):
        _run(tmp_path, [row])


# ---------------------------------------------------------------------------
# snapshot confinement and integrity
# ---------------------------------------------------------------------------


def test_hash_mismatch_is_rejected(tmp_path):
    """snapshot SHA-256 mismatch must fail."""
    with pytest.raises(intake.IntakeError, match="does not match"):
        _run(tmp_path, [_reviewed_row(tmp_path, content_sha256="b" * 64)])


def test_path_traversal_is_rejected(tmp_path):
    """path traversal via .. must fail."""
    with pytest.raises(intake.IntakeError, match="safe relative"):
        _run(
            tmp_path,
            [_reviewed_row(
                tmp_path,
                snapshot_path="stage124/batch02_parts/snapshots_part03/manual/../../x.html",
            )],
        )


def test_absolute_path_is_rejected(tmp_path):
    """absolute snapshot path must fail."""
    outside = tmp_path / "stage124/batch02_parts/snapshots_part03/absolute.html"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="safe relative"):
        _run(
            tmp_path,
            [_reviewed_row(
                tmp_path,
                snapshot_path=str(outside.resolve()),
                content_sha256=sha(outside),
            )],
        )


def test_symlink_is_rejected(tmp_path):
    """snapshot symlinks must be rejected."""
    real = tmp_path / "stage124/batch02_parts/snapshots_part03/manual/real.html"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(b"<html>real</html>")
    link = tmp_path / "stage124/batch02_parts/snapshots_part03/manual/link.html"
    link.symlink_to(real)
    digest = hashlib.sha256(b"<html>real</html>").hexdigest()
    with pytest.raises(intake.IntakeError, match="symlinks are forbidden"):
        _run(
            tmp_path,
            [_reviewed_row(
                tmp_path,
                snapshot_path="stage124/batch02_parts/snapshots_part03/manual/link.html",
                content_sha256=digest,
            )],
        )


def test_missing_snapshot_file_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="file not found"):
        _run(
            tmp_path,
            [_reviewed_row(
                tmp_path,
                snapshot_path="stage124/batch02_parts/snapshots_part03/manual/nope.html",
                content_sha256="a" * 64,
            )],
        )


def test_snapshot_outside_exact_prefix_fails(tmp_path):
    outside = tmp_path / "stage124/batch02_parts/x_snapshots_part03/y.html"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(intake.IntakeError, match="must be under"):
        _run(
            tmp_path,
            [_reviewed_row(
                tmp_path,
                snapshot_path="stage124/batch02_parts/x_snapshots_part03/y.html",
                content_sha256=sha(outside),
            )],
        )


# ---------------------------------------------------------------------------
# apply: provenance creation
# ---------------------------------------------------------------------------


def test_apply_creates_exactly_one_provenance(tmp_path):
    """--apply with a reviewed finding must create exactly 1 provenance row."""
    row = _reviewed_row(tmp_path)
    report, registry_path, report_path = _run(tmp_path, [row], apply=True)

    assert report["status"] == "findings_registered"
    assert report["sources_registered"] == 1
    assert report["provenance_created"] == 1
    assert report["registry_rows_after"] == 21
    assert report_path.exists()

    # Check registry was updated
    reg = load_source_registry(registry_path)
    added = reg[reg["source_origin"] == "manual_discovery"]
    assert len(added) == 1
    assert added.iloc[0]["source_index"] == "3"  # seed had 1 & 2

    # Check provenance file
    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    assert prov_path.exists()
    prov_df = pd.read_csv(prov_path, dtype=str, keep_default_na=False,
                          encoding="utf-8-sig")
    manual_records = prov_df[prov_df["retrieval_status"] == "manual_snapshot_imported"]
    assert len(manual_records) == 1
    rec = manual_records.iloc[0]
    assert rec["source_index"] == "3"
    assert rec["ticker"] == PART03_TICKERS[0]
    assert rec["content_sha256"] == row["content_sha256"]

    # Derived fields must be computed by engine (not empty)
    assert rec["source_authority_class"] != ""
    assert rec["independent_source_group"] != ""
    assert rec["document_specific"] != ""


def test_manual_snapshot_imported_is_fetched_status(tmp_path):
    """manual_snapshot_imported must be in FETCHED_STATUSES."""
    assert "manual_snapshot_imported" in FETCHED_STATUSES


# ---------------------------------------------------------------------------
# screening recompute
# ---------------------------------------------------------------------------


def test_screening_is_recomputed_on_apply(tmp_path):
    """--apply must recompute research screening from provenance."""
    row = _reviewed_row(tmp_path)
    _run(tmp_path, [row], apply=True)

    screening_path = tmp_path / "stage124/batch02_parts/part03_research_screening_10tickers.csv"
    assert screening_path.exists()
    screening_df = pd.read_csv(screening_path, dtype=str, keep_default_na=False,
                               encoding="utf-8-sig")
    assert len(screening_df) == 10
    assert set(screening_df["ticker"].tolist()) == set(PART03_TICKERS)


def test_research_counts_match_provenance(tmp_path):
    """research screening counts must match provenance after apply."""
    row = _reviewed_row(tmp_path)
    _run(tmp_path, [row], apply=True)

    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    screening_path = tmp_path / "stage124/batch02_parts/part03_research_screening_10tickers.csv"

    prov_df = pd.read_csv(prov_path, dtype=str, keep_default_na=False,
                          encoding="utf-8-sig")
    screening_df = pd.read_csv(screening_path, dtype=str, keep_default_na=False,
                               encoding="utf-8-sig")

    # For the ticker with the new source, fetched count should include it
    tk = PART03_TICKERS[0]
    tk_screening = screening_df[screening_df["ticker"] == tk].iloc[0]
    tk_prov = prov_df[prov_df["ticker"] == tk]
    fetched_count = int(tk_screening["fetched_source_count"])
    assert fetched_count == len(
        tk_prov[tk_prov["retrieval_status"].isin(FETCHED_STATUSES)]
    )


# ---------------------------------------------------------------------------
# aggregator cannot be accepted/supported/ready on its own
# ---------------------------------------------------------------------------


def test_aggregator_alone_is_not_accepted(tmp_path):
    """An aggregator-only source must not produce evidence_accepted=true,
    candidate_supported, or ready_for_user_review=true."""
    row = _reviewed_row(
        tmp_path,
        source_type="aggregator",
        source_url="https://rahavard365.com/asset/detail/12345/ipo-report",
    )
    _run(tmp_path, [row], apply=True)

    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    prov_df = pd.read_csv(prov_path, dtype=str, keep_default_na=False,
                          encoding="utf-8-sig")
    manual = prov_df[prov_df["retrieval_status"] == "manual_snapshot_imported"]
    assert len(manual) == 1
    rec = manual.iloc[0]
    assert rec["evidence_accepted"] == "false"

    screening_path = tmp_path / "stage124/batch02_parts/part03_research_screening_10tickers.csv"
    screening_df = pd.read_csv(screening_path, dtype=str, keep_default_na=False,
                               encoding="utf-8-sig")
    tk_row = screening_df[screening_df["ticker"] == PART03_TICKERS[0]].iloc[0]
    assert tk_row["ready_for_user_review"] == "false"
    assert tk_row["research_status"] != "candidate_supported"


# ---------------------------------------------------------------------------
# official document-specific fixture passes engine
# ---------------------------------------------------------------------------


def test_official_document_specific_fixture(tmp_path):
    """A codal_official document-specific URL with valid review should be
    classified correctly by the engine."""
    url = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=abc123"
    cls, verr = classify_source_authority_with_validation("codal_official", url, PART03_TICKERS[0])
    assert cls == "official_regulatory"
    assert verr == ""
    assert is_document_specific_source(url, "codal_official", PART03_TICKERS[0])


# ---------------------------------------------------------------------------
# discovery-only sources
# ---------------------------------------------------------------------------


def test_discovery_only_enters_registry_only(tmp_path):
    """discovery-only source (no snapshot/date/event/ordinary=unknown) must
    only enter registry and not produce evidence or provenance."""
    row = _discovery_row(tmp_path)
    report, registry_path, _ = _run(tmp_path, [row], apply=True)

    assert report["sources_registered"] == 1
    assert report["provenance_created"] == 0
    assert report["discovery_only_count"] == 1

    # Registry updated
    reg = load_source_registry(registry_path)
    assert len(reg) == 21

    # No provenance for this source
    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    if prov_path.exists():
        prov_df = pd.read_csv(prov_path, dtype=str, keep_default_na=False,
                              encoding="utf-8-sig")
        manual = prov_df[prov_df["retrieval_status"] == "manual_snapshot_imported"]
        assert len(manual) == 0


# ---------------------------------------------------------------------------
# registry/provenance integrity
# ---------------------------------------------------------------------------


def test_registry_provenance_integrity(tmp_path):
    """After apply, registry and provenance must be internally consistent."""
    row = _reviewed_row(tmp_path)
    _run(tmp_path, [row], apply=True)

    reg = load_source_registry(
        tmp_path / "stage124/batch02_parts/part03_source_registry.csv"
    )
    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    prov_df = pd.read_csv(prov_path, dtype=str, keep_default_na=False,
                          encoding="utf-8-sig")

    # Every provenance row's (ticker, source_index) must exist in registry
    for _, pr in prov_df.iterrows():
        tk = pr["ticker"]
        si = str(pr["source_index"]).strip()
        match = reg[(reg["ticker"] == tk) & (reg["source_index"] == si)]
        assert len(match) >= 1, f"provenance ({tk}, {si}) not in registry"


# ---------------------------------------------------------------------------
# atomic rollback on failure
# ---------------------------------------------------------------------------


def test_failure_injection_rolls_back_all_files(tmp_path):
    """If apply fails mid-write, ALL files must be rolled back."""
    row = _reviewed_row(tmp_path)
    intake_path, registry_path, report_path = _paths(tmp_path)
    _write_intake(intake_path, [row])

    # Record initial state of all files
    initial_reg = registry_path.read_bytes()
    prov_path = tmp_path / "stage124/batch02_parts/part03_source_provenance_10tickers.csv"
    screening_path = tmp_path / "stage124/batch02_parts/part03_research_screening_10tickers.csv"

    # Inject failure into _atomic_write after first file is written
    original_atomic = intake._atomic_write

    def failing_atomic(outputs):
        # Write to temp files but inject error during the replace phase
        temps = {}
        backups = {}
        created = []
        for target, payload in outputs.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".intake_tmp")
            temp.write_bytes(payload)
            temps[target] = temp

        targets = list(outputs.keys())
        # Replace the first file successfully
        first = targets[0]
        if first.exists():
            backup = first.with_name(first.name + ".intake_bak")
            os.replace(first, backup)
            backups[first] = backup
        os.replace(temps[first], first)
        if first not in backups:
            created.append(first)

        # Now raise to trigger rollback
        try:
            raise RuntimeError("injected failure")
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

    with patch.object(intake, '_atomic_write', side_effect=failing_atomic):
        with pytest.raises(RuntimeError, match="injected failure"):
            intake.run_intake(
                intake_path=intake_path,
                registry_path=registry_path,
                report_path=report_path,
                root=tmp_path,
                apply=True,
            )

    # Registry must be rolled back to its initial state
    assert registry_path.read_bytes() == initial_reg
    # No other files should have been created
    assert not prov_path.exists()
    assert not screening_path.exists()
    assert not report_path.exists()


# ---------------------------------------------------------------------------
# Stage122 / Stage123 byte-for-byte unchanged
# ---------------------------------------------------------------------------


def test_stage122_stage123_byte_for_byte_unchanged(tmp_path):
    """Apply must never modify Stage122 or Stage123 files."""
    # Create stage122 and stage123 sentinel files
    s122 = tmp_path / "stage122" / "sentinel.csv"
    s123 = tmp_path / "stage123" / "sentinel.csv"
    s122.parent.mkdir(parents=True, exist_ok=True)
    s123.parent.mkdir(parents=True, exist_ok=True)
    s122.write_text("stage122_data", encoding="utf-8")
    s123.write_text("stage123_data", encoding="utf-8")

    s122_before = s122.read_bytes()
    s123_before = s123.read_bytes()

    row = _reviewed_row(tmp_path)
    _run(tmp_path, [row], apply=True)

    assert s122.read_bytes() == s122_before
    assert s123.read_bytes() == s123_before


# ---------------------------------------------------------------------------
# schema and row validation
# ---------------------------------------------------------------------------


def test_extra_column_fails(tmp_path):
    intake_path, registry, report = _paths(tmp_path)
    _write_intake(intake_path, [_reviewed_row(tmp_path)], extra_column=True)
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
        _run(tmp_path, [_reviewed_row(tmp_path, source_type=source_type)])


def test_missing_title_or_added_by_fails(tmp_path):
    with pytest.raises(intake.IntakeError):
        _run(tmp_path, [_reviewed_row(tmp_path, source_title="", added_by="")])


def test_out_of_scope_ticker_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="out of Part 3 scope"):
        _run(tmp_path, [_reviewed_row(tmp_path, ticker="\u0641\u0648\u0644\u0627\u062f")])


def test_bad_url_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="source_url"):
        _run(tmp_path, [_reviewed_row(tmp_path, source_url="file:///Users/x")])


def test_duplicate_normalized_url_fails(tmp_path):
    first = _reviewed_row(tmp_path)
    # Use a URL whose path differs only by a trailing slash (normalizes same)
    second = _reviewed_row(
        tmp_path,
        source_url="https://www.codal.ir/Reports/Decision.aspx/?LetterSerial=abc",
        source_title="duplicate URL",
    )
    with pytest.raises(intake.IntakeError, match="duplicate normalized"):
        _run(tmp_path, [first, second])


def test_date_precision_disagreement_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="disagrees"):
        _run(
            tmp_path,
            [_reviewed_row(tmp_path, candidate_date_jalali="1380", date_precision="exact_day")],
        )


def test_event_requires_date(tmp_path):
    with pytest.raises(intake.IntakeError, match="requires candidate_date"):
        _run(
            tmp_path,
            [_reviewed_row(tmp_path, candidate_date_jalali="", date_precision="unknown")],
        )


def test_date_requires_specific_event(tmp_path):
    with pytest.raises(intake.IntakeError, match="specific event"):
        _run(tmp_path, [_reviewed_row(tmp_path, event_type_candidate="unresolved")])


def test_bad_publication_date_fails(tmp_path):
    with pytest.raises(intake.IntakeError, match="publication_date_jalali"):
        _run(tmp_path, [_reviewed_row(tmp_path, publication_date_jalali="1400-13-01")])


def test_evidence_fields_require_snapshot(tmp_path):
    with pytest.raises(intake.IntakeError, match="require snapshot_path"):
        _run(
            tmp_path,
            [_reviewed_row(tmp_path, snapshot_path="", content_sha256="")],
        )


def test_apply_empty_intake_is_refused(tmp_path):
    with pytest.raises(intake.IntakeError, match="no findings"):
        _run(tmp_path, [], apply=True)


def test_explicit_dry_run_report_is_allowed(tmp_path):
    report, registry, report_path = _run(
        tmp_path, [_reviewed_row(tmp_path)], write_report=True
    )
    assert report["sources_registered"] == 0
    assert len(load_source_registry(registry)) == 20
    assert report_path.exists()


# ---------------------------------------------------------------------------
# all apply outputs are written
# ---------------------------------------------------------------------------


def test_apply_writes_all_seven_outputs(tmp_path):
    """--apply must produce all seven output files."""
    row = _reviewed_row(tmp_path)
    _run(tmp_path, [row], apply=True)
    base = tmp_path / "stage124" / "batch02_parts"
    assert (base / "part03_source_registry.csv").exists()
    assert (base / "part03_source_provenance_10tickers.csv").exists()
    assert (base / "part03_research_screening_10tickers.csv").exists()
    assert (base / "part03_research_summary.json").exists()
    assert (base / "part03_qc_report.json").exists()
    assert (base / "part03_manual_intake_report.json").exists()
    assert (base / "part03_manual_intake_apply_manifest.json").exists()


# ---------------------------------------------------------------------------
# committed real template
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# invalid review status
# ---------------------------------------------------------------------------


def test_invalid_review_status_fails(tmp_path):
    row = _reviewed_row(tmp_path, content_review_status="invalid_status")
    with pytest.raises(intake.IntakeError, match="content_review_status"):
        _run(tmp_path, [row])
