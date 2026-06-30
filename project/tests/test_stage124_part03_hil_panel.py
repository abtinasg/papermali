"""Tests for Stage124 Batch02 Part 3.1B.1B — Human-in-the-Loop Panel MVP.

All tests are synthetic and use temporary directories. No real URLs, dates or
Part 3 ticker data are used beyond the ticker symbol strings themselves.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import run_stage124_batch02_part03_manual_intake as intake  # noqa: E402
import src.stage124_part03_hil_panel as panel  # noqa: E402
from src.stage124_batch02_part03 import (  # noqa: E402
    PART03_TICKERS,
    PROVENANCE_COLUMNS,
    ROOT,
    build_seed_registry_df,
    read_csv,
    write_csv,
)

_REAL_ROOT = ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_registry(root: Path) -> Path:
    path = root / "stage124" / "batch02_parts" / "part03_source_registry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(build_seed_registry_df(), path)
    return path


def _snapshot(
    root: Path,
    ticker: str = PART03_TICKERS[0],
    name: str = "manual.html",
    body: bytes = b"<html>ordinary-share offering evidence</html>",
) -> tuple[str, str]:
    rel = Path("stage124/batch02_parts/snapshots_part03") / ticker / name
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return rel.as_posix(), hashlib.sha256(body).hexdigest()


def _reviewed_row(
    root: Path,
    ticker: str = PART03_TICKERS[0],
    source_url: str = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=TEST",
    **overrides,
) -> dict:
    rel, digest = _snapshot(root, ticker)
    row = panel.build_intake_row(
        ticker=ticker,
        source_type="codal_official",
        source_url=source_url,
        source_title="Codal decision",
        review_mode="reviewed",
        event_type="first_public_offering",
        candidate_date_jalali="1380-03-15",
        date_precision="exact_day",
        ordinary_share_explicit="true",
        snapshot_path=rel,
        content_sha256=digest,
        actor="researcher",
        discovery_notes="manual finding",
        reviewer_notes="Reviewed and confirmed as ordinary-share offering",
    )
    row.update(overrides)
    return row


def _pending_row(
    root: Path,
    ticker: str = PART03_TICKERS[0],
    source_url: str = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=PEND",
) -> dict:
    rel, digest = _snapshot(root, ticker)
    return panel.build_intake_row(
        ticker=ticker,
        source_type="codal_official",
        source_url=source_url,
        source_title="Codal pending",
        review_mode="pending_manual_review",
        snapshot_path=rel,
        content_sha256=digest,
        actor="researcher",
        discovery_notes="pending review",
    )


def _discovery_row(
    root: Path,
    ticker: str = PART03_TICKERS[0],
    source_url: str = "https://www.codal.ir/ReportList.aspx?search&Symbol=TEST",
) -> dict:
    return panel.build_intake_row(
        ticker=ticker,
        source_type="codal_official",
        source_url=source_url,
        source_title="Codal search page",
        review_mode="discovery",
        actor="researcher",
        discovery_notes="discovery only",
    )


def _rejected_row(
    root: Path,
    ticker: str = PART03_TICKERS[0],
    source_url: str = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=REJ",
) -> dict:
    return panel.build_intake_row(
        ticker=ticker,
        source_type="codal_official",
        source_url=source_url,
        source_title="Codal rejected",
        review_mode="rejected",
        actor="researcher",
        discovery_notes="rejected source",
        reviewer_notes="URL not reachable and content unverifiable",
    )


def _sha_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha(directory: Path) -> dict[str, str]:
    out = {}
    if not directory.exists():
        return out
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            out[p.relative_to(directory).as_posix()] = _sha_file(p)
    return out


# ---------------------------------------------------------------------------
# Filename / upload security
# ---------------------------------------------------------------------------
def test_sanitize_filename():
    assert panel.sanitize_filename("file.pdf") == "file.pdf"
    assert panel.sanitize_filename("my file.pdf") == "my_file.pdf"
    assert panel.sanitize_filename("../../etc/passwd") == "passwd"
    assert panel.sanitize_filename("a<b>c:d|e*f?g.pdf") == "abcdefg.pdf"


def test_validate_upload_absolute_filename_rejected():
    with pytest.raises(panel.PanelError):
        panel.validate_upload("/etc/passwd.txt", b"content")


def test_validate_upload_path_traversal_rejected():
    with pytest.raises(panel.PanelError):
        panel.validate_upload("../etc/passwd.txt", b"content")


def test_validate_upload_unsupported_extension_rejected():
    with pytest.raises(panel.PanelError):
        panel.validate_upload("file.exe", b"content")


def test_validate_upload_oversized_rejected():
    with pytest.raises(panel.PanelError):
        panel.validate_upload("file.txt", b"x" * (panel.MAX_UPLOAD_BYTES + 1))


def test_store_snapshot_under_correct_root_and_sha_matches_bytes(tmp_path):
    _seed_registry(tmp_path)
    body = b"<html>test content</html>"
    result = panel.store_snapshot(
        root=tmp_path,
        ticker=PART03_TICKERS[0],
        filename="evidence.html",
        content=body,
    )
    rel = result["snapshot_path"]
    abs_path = tmp_path / rel
    assert abs_path.exists()
    assert abs_path.is_relative_to(tmp_path / "stage124" / "batch02_parts" / "snapshots_part03")
    assert hashlib.sha256(abs_path.read_bytes()).hexdigest() == result["content_sha256"]
    assert result["content_sha256"] == hashlib.sha256(body).hexdigest()


def test_store_snapshot_rejects_symlink_directory(tmp_path):
    _seed_registry(tmp_path)
    # Use a valid ticker so the ticker-scope check does not mask the symlink test.
    real_dir = tmp_path / "stage124" / "batch02_parts" / "snapshots_part03" / (PART03_TICKERS[0] + "_real")
    real_dir.mkdir(parents=True)
    link_dir = tmp_path / "stage124" / "batch02_parts" / "snapshots_part03" / PART03_TICKERS[0]
    link_dir.symlink_to(real_dir)
    with pytest.raises(panel.PanelError):
        panel.store_snapshot(
            root=tmp_path,
            ticker=PART03_TICKERS[0],
            filename="x.html",
            content=b"x",
        )


def test_store_snapshot_rejects_symlink_file(tmp_path):
    _seed_registry(tmp_path)
    body = b"x"
    digest = hashlib.sha256(body).hexdigest()
    sha12 = digest[:12]
    fixed_timestamp = "20260101T000000Z"
    real = tmp_path / "stage124" / "batch02_parts" / "snapshots_part03" / PART03_TICKERS[0] / "real.html"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(body)
    stored_name = f"{fixed_timestamp}_{sha12}_link.html"
    link = real.parent / stored_name
    link.symlink_to(real)
    with patch.object(panel, "_utc_timestamp_for_filename", return_value=fixed_timestamp):
        with pytest.raises(panel.PanelError):
            panel.store_snapshot(
                root=tmp_path,
                ticker=PART03_TICKERS[0],
                filename="link.html",
                content=body,
            )


# ---------------------------------------------------------------------------
# Intake row schema
# ---------------------------------------------------------------------------
def test_build_intake_row_exact_intake_columns_schema(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    row = _reviewed_row(tmp_path)
    assert list(row.keys()) == intake.INTAKE_COLUMNS


def test_build_intake_row_pending_with_event_rejected(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="pending_manual_review",
            event_type="first_public_offering",
            snapshot_path=rel,
            content_sha256=digest,
            actor="a",
        )


def test_build_intake_row_pending_with_date_rejected(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="pending_manual_review",
            candidate_date_jalali="1380-03-15",
            snapshot_path=rel,
            content_sha256=digest,
            actor="a",
        )


def test_build_intake_row_pending_with_ordinary_true_rejected(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="pending_manual_review",
            ordinary_share_explicit="true",
            snapshot_path=rel,
            content_sha256=digest,
            actor="a",
        )


def test_build_intake_row_reviewed_without_snapshot_rejected(tmp_path):
    _seed_registry(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="reviewed",
            event_type="first_public_offering",
            candidate_date_jalali="1380-03-15",
            actor="a",
            reviewer_notes="notes",
        )


def test_build_intake_row_reviewed_without_notes_rejected(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="reviewed",
            event_type="first_public_offering",
            candidate_date_jalali="1380-03-15",
            snapshot_path=rel,
            content_sha256=digest,
            actor="a",
            reviewer_notes="",
        )


def test_build_intake_row_reviewed_without_actor_rejected(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    with pytest.raises(panel.PanelError):
        panel.build_intake_row(
            ticker=PART03_TICKERS[0],
            source_type="codal_official",
            source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=X",
            source_title="t",
            review_mode="reviewed",
            event_type="first_public_offering",
            candidate_date_jalali="1380-03-15",
            snapshot_path=rel,
            content_sha256=digest,
            actor="",
            reviewer_notes="notes",
        )


def test_build_intake_row_reviewed_timestamp_generated_in_utc(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    ts = row["manual_reviewed_at_utc"]
    assert ts
    assert ts.endswith("Z")
    assert "T" in ts


# ---------------------------------------------------------------------------
# Validation-only / Apply via the bridge
# ---------------------------------------------------------------------------
def test_validate_submission_does_not_mutate_canonical_outputs(tmp_path):
    _seed_registry(tmp_path)
    # Seed canonical outputs with stable content
    part03_dir = tmp_path / "stage124" / "batch02_parts"
    (part03_dir / "part03_research_screening_10tickers.csv").write_text(
        "ticker,company_name\n", encoding="utf-8"
    )
    (part03_dir / "part03_source_provenance_10tickers.csv").write_text(
        ",".join(PROVENANCE_COLUMNS) + "\n", encoding="utf-8"
    )
    (part03_dir / "part03_research_summary.json").write_text("{}", encoding="utf-8")
    (part03_dir / "part03_qc_report.json").write_text("{}", encoding="utf-8")
    (part03_dir / "part03_manual_intake_apply_manifest.json").write_text("{}", encoding="utf-8")

    # Snapshot must exist before the baseline so it is not counted as a mutation.
    row = _reviewed_row(tmp_path)
    before = {str(p.relative_to(tmp_path)): _sha_file(p) for p in part03_dir.rglob("*") if p.is_file()}
    result = panel.validate_submission(row=row, root=tmp_path)
    assert result["valid"] is True
    after = {str(p.relative_to(tmp_path)): _sha_file(p) for p in part03_dir.rglob("*") if p.is_file()}
    assert before == after


def test_apply_submission_uses_existing_bridge(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert result["valid"] is True
    assert result["applied"] is True
    assert result["report"]["status"] == "findings_registered"


def test_apply_submission_creates_exactly_one_provenance_row(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    prov = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv")
    assert len(prov[prov["ticker"] == row["ticker"]]) == 1


def test_apply_submission_recomputes_screening(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    screening = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_research_screening_10tickers.csv")
    tk_row = screening[screening["ticker"] == row["ticker"]].iloc[0]
    assert int(tk_row["attempted_source_count"]) >= 1
    assert int(tk_row["fetched_source_count"]) >= 1
    assert int(tk_row["reviewed_source_count"]) >= 1


def test_apply_submission_duplicate_provenance_blocked(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    first = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert first["applied"] is True
    second = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert second["applied"] is False
    assert second["bridge_status"] == "duplicate_blocked"
    assert "این منبع قبلاً وارد provenance شده است" in second["errors"][0]


def test_discovery_row_preserves_optional_snapshot(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    row = panel.build_intake_row(
        ticker=PART03_TICKERS[0],
        source_type="codal_official",
        source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=DISC",
        source_title="Codal discovery",
        review_mode="discovery",
        snapshot_path=rel,
        content_sha256=digest,
        actor="researcher",
        discovery_notes="discovery with snapshot",
    )
    assert row["snapshot_path"] == rel
    assert row["content_sha256"] == digest


def test_discovery_submission_with_snapshot_attaches_to_source(tmp_path):
    _seed_registry(tmp_path)
    rel, digest = _snapshot(tmp_path)
    row = panel.build_intake_row(
        ticker=PART03_TICKERS[0],
        source_type="codal_official",
        source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=DISC",
        source_title="Codal discovery",
        review_mode="discovery",
        snapshot_path=rel,
        content_sha256=digest,
        actor="researcher",
        discovery_notes="discovery with snapshot",
    )
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert result["valid"] is True
    registry = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_source_registry.csv")
    assert any(str(r["source_url"]).strip() == row["source_url"] for _, r in registry.iterrows())
    # No provenance row because discovery is not a reviewed finding.
    prov = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv")
    assert prov.empty or not any(
        str(r["source_url"]).strip() == row["source_url"] for _, r in prov.iterrows()
    )


def test_discovery_registers_source_without_provenance(tmp_path):
    _seed_registry(tmp_path)
    row = _discovery_row(tmp_path)
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert result["applied"] is True
    registry = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_source_registry.csv")
    assert any(str(r["source_url"]).strip() == row["source_url"] for _, r in registry.iterrows())
    prov = read_csv(tmp_path / "stage124" / "batch02_parts" / "part03_source_provenance_10tickers.csv")
    assert prov.empty or not any(
        str(r["source_url"]).strip() == row["source_url"] for _, r in prov.iterrows()
    )


def test_rejected_source_produces_no_accepted_evidence(tmp_path):
    _seed_registry(tmp_path)
    row = _rejected_row(tmp_path)
    before = _tree_sha(tmp_path / "stage124" / "batch02_parts")
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="reject")
    assert result["rejected"] is True
    after = _tree_sha(tmp_path / "stage124" / "batch02_parts")
    # Only the submission and audit files may be added; canonical CSVs unchanged.
    canonical = {
        "part03_source_registry.csv",
        "part03_source_provenance_10tickers.csv",
        "part03_research_screening_10tickers.csv",
        "part03_research_summary.json",
        "part03_qc_report.json",
        "part03_manual_intake_apply_manifest.json",
    }
    for name in canonical:
        if name in before and name in after:
            assert before[name] == after[name], f"{name} mutated by reject"


def test_reject_submission_validates_invalid_row(tmp_path):
    _seed_registry(tmp_path)
    row = _rejected_row(tmp_path)
    row["source_url"] = "not-a-valid-url"
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="reject")
    assert result["valid"] is False
    assert result["rejected"] is False
    assert result["action"] == "reject"
    events = panel.read_audit_events(tmp_path)
    assert events
    assert events[0]["action"] == "reject"
    assert events[0]["error"]


def test_submission_filename_is_unique(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    path1 = panel._submission_path(tmp_path, row["ticker"], row)
    path2 = panel._submission_path(tmp_path, row["ticker"], row)
    assert path1 != path2


def test_submission_csv_refuses_overwrite(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    path = panel._submission_path(tmp_path, row["ticker"], row)
    panel._write_submission_csv(path, row)
    with pytest.raises(panel.PanelError):
        panel._write_submission_csv(path, row)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
def test_validate_action_records_audit_event(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="validate")
    assert result["valid"] is True
    assert result["action"] == "validate"
    events = panel.read_audit_events(tmp_path)
    assert events
    assert events[0]["action"] == "validate"
    assert events[0]["actor"] == "researcher"


def test_audit_success_event_written(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    events = panel.read_audit_events(tmp_path)
    assert events
    assert events[0]["action"] == "apply"
    assert events[0]["actor"] == "researcher"
    assert events[0]["ticker"] == row["ticker"]
    assert events[0]["bridge_status"] == "findings_registered"


def test_audit_failure_event_written(tmp_path):
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    # Corrupt the snapshot so SHA mismatch triggers a failure
    row["content_sha256"] = "0" * 64
    result = panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    assert result["applied"] is False
    events = panel.read_audit_events(tmp_path)
    assert events
    assert events[0]["action"] == "apply"
    assert events[0]["error"]


def test_audit_jsonl_remains_valid(tmp_path):
    _seed_registry(tmp_path)
    panel.apply_submission(row=_reviewed_row(tmp_path), root=tmp_path, actor="a", action="apply")
    panel.apply_submission(row=_reviewed_row(tmp_path, source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=OTHER"), root=tmp_path, actor="a", action="apply")
    panel.apply_submission(row=_discovery_row(tmp_path), root=tmp_path, actor="a", action="reject")
    audit_path = tmp_path / "stage124" / "batch02_parts" / "part03_hil_panel_audit.jsonl"
    assert audit_path.exists()
    with audit_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            assert line.strip()
            json.loads(line)


# ---------------------------------------------------------------------------
# Stage122 / Stage123 unchanged
# ---------------------------------------------------------------------------
def test_stage122_and_stage123_unchanged_after_panel_apply(tmp_path):
    stage122_before = _tree_sha(_REAL_ROOT / "stage122")
    stage123_before = _tree_sha(_REAL_ROOT / "stage123")
    _seed_registry(tmp_path)
    row = _reviewed_row(tmp_path)
    panel.apply_submission(row=row, root=tmp_path, actor="researcher", action="apply")
    stage122_after = _tree_sha(_REAL_ROOT / "stage122")
    stage123_after = _tree_sha(_REAL_ROOT / "stage123")
    assert stage122_before == stage122_after
    assert stage123_before == stage123_after


# ---------------------------------------------------------------------------
# Dashboard loading
# ---------------------------------------------------------------------------
def test_dashboard_loads_when_outputs_are_missing(tmp_path):
    data = panel.load_dashboard_data(tmp_path)
    assert data["metrics"]["ticker_count"] == len(PART03_TICKERS)
    assert data["screening"] is None or data["screening"].empty
    assert data["audit_events"] == []


def test_dashboard_loads_all_10_tickers_when_outputs_exist(tmp_path):
    _seed_registry(tmp_path)
    # Use the real project outputs as a read-only fixture for the dashboard
    part03_dir = _REAL_ROOT / "stage124" / "batch02_parts"
    if (part03_dir / "part03_research_screening_10tickers.csv").exists():
        shutil.copy(part03_dir / "part03_research_screening_10tickers.csv", tmp_path / "stage124" / "batch02_parts" / "part03_research_screening_10tickers.csv")
    data = panel.load_dashboard_data(tmp_path)
    screening = data["screening"]
    if screening is not None and not screening.empty:
        assert set(screening["ticker"].tolist()) == set(PART03_TICKERS)
    else:
        pytest.skip("real screening output not available")


# ---------------------------------------------------------------------------
# Streamlit app smoke test
# ---------------------------------------------------------------------------
def test_streamlit_app_import_smoke():
    import apps.stage124_part03_hil_panel as app_module  # noqa: F401
    assert hasattr(app_module, "st")


def test_snapshot_upload_key_includes_ticker():
    import apps.stage124_part03_hil_panel as app

    class Uploaded:
        name = "x.html"

        def getvalue(self):
            return b"body"

    assert app._snapshot_upload_key("خمهر", Uploaded()) == (
        "خمهر",
        "x.html",
        hashlib.sha256(b"body").hexdigest(),
    )


def test_clear_snapshot_state_removes_only_snapshot_keys():
    import apps.stage124_part03_hil_panel as app
    from unittest.mock import patch

    fake_st = type(
        "FakeSt",
        (),
        {
            "session_state": {
                "snapshot_path": "x",
                "content_sha256": "y",
                "snapshot_size": 1,
                "snapshot_stored": "z",
                "_last_upload_key": "k",
                "other": "keep",
            }
        },
    )()
    with patch.object(app, "st", fake_st):
        app._clear_snapshot_state()
    assert fake_st.session_state == {"other": "keep"}


def test_store_snapshot_same_content_different_tickers_creates_two_files(tmp_path):
    _seed_registry(tmp_path)
    body = b"<html>same</html>"
    result1 = panel.store_snapshot(
        root=tmp_path, ticker=PART03_TICKERS[0], filename="same.html", content=body
    )
    result2 = panel.store_snapshot(
        root=tmp_path, ticker=PART03_TICKERS[1], filename="same.html", content=body
    )
    assert result1["snapshot_path"] != result2["snapshot_path"]
    assert (tmp_path / result1["snapshot_path"]).exists()
    assert (tmp_path / result2["snapshot_path"]).exists()
