from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src import stage124_batch02_part03 as p3
from src import stage124_batch02_part03_manual_intake as mi


def _base_registry_and_provenance():
    registry = p3.build_seed_registry_df()
    records = []
    for _, r in registry.iterrows():
        rec = {c: "" for c in p3.PROVENANCE_COLUMNS}
        rec.update({
            "ticker": r["ticker"],
            "source_index": r["source_index"],
            "source_type": r["source_type"],
            "source_title": r["source_title"],
            "source_url": r["source_url"],
            "retrieved_at_utc": "2026-06-27T00:00:00Z",
            "retrieval_status": "timeout",
            "final_url": r["source_url"],
            "content_review_status": "not_available_due_to_fetch_failure",
            "ordinary_share_explicit": "unknown",
            "exact_date_explicit": "false",
            "publication_date_explicit": "false",
        })
        records.append(rec)
    provenance = pd.DataFrame(
        p3.normalize_provenance_records(records, p3.ROOT),
        columns=p3.PROVENANCE_COLUMNS,
    )
    return registry, provenance


def _snapshot(tmp_path: Path, name: str = "evidence.html"):
    rel = Path("stage124/batch02_parts/snapshots_part03/manual") / name
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = b"<html><body>ordinary share first public trading evidence</body></html>"
    path.write_bytes(body)
    return rel.as_posix(), hashlib.sha256(body).hexdigest()


def _row(tmp_path: Path, **overrides):
    snap, digest = _snapshot(tmp_path)
    row = {c: "" for c in mi.INTAKE_COLUMNS}
    row.update({
        "ticker": "خمهر",
        "source_url": "https://www.isna.ir/news/14000102/example",
        "source_type": "credible_news",
        "source_title": "Contemporaneous article",
        "snapshot_path": snap,
        "supplied_snapshot_sha256": digest,
        "captured_at_utc": "2026-06-29T12:00:00Z",
        "final_url": "https://www.isna.ir/news/14000102/example",
        "http_status": "200",
        "content_type": "text/html; charset=utf-8",
        "content_review_status": "reviewed",
        "event_type_supported": "first_public_trading",
        "reviewed_date_jalali": "1400-01-01",
        "exact_date_explicit": "true",
        "ordinary_share_explicit": "true",
        "publication_date_jalali": "1400-01-02",
        "publication_date_explicit": "true",
        "exact_text_or_event_summary": "Article explicitly reports first public trading of ordinary shares.",
        "reviewer_notes": "Manually reviewed against stored snapshot.",
        "manual_reviewed_at_utc": "2026-06-29T12:05:00Z",
        "added_by": "researcher",
        "discovery_notes": "Manual browser discovery.",
    })
    row.update(overrides)
    return row


def _df(tmp_path: Path, **overrides):
    return pd.DataFrame([_row(tmp_path, **overrides)], columns=mi.INTAKE_COLUMNS)


def test_manual_status_is_registered_as_fetched():
    assert mi.MANUAL_RETRIEVAL_STATUS in p3.FETCHED_STATUSES


def test_exact_template_schema():
    assert len(mi.INTAKE_COLUMNS) == len(set(mi.INTAKE_COLUMNS))
    assert not (set(mi.INTAKE_COLUMNS) & mi.DERIVED_FORBIDDEN)


def test_valid_reviewed_intake_passes(tmp_path):
    ok, errors, normalized = mi.validate_manual_evidence_intake(_df(tmp_path), tmp_path)
    assert ok, errors
    assert normalized.loc[0, "ticker"] == "خمهر"


def test_wrong_hash_fails(tmp_path):
    ok, errors, _ = mi.validate_manual_evidence_intake(
        _df(tmp_path, supplied_snapshot_sha256="0" * 64), tmp_path
    )
    assert not ok
    assert any("does not match" in e for e in errors)


def test_path_traversal_fails(tmp_path):
    df = _df(tmp_path, snapshot_path="stage124/batch02_parts/snapshots_part03/manual/../../x")
    ok, errors, _ = mi.validate_manual_evidence_intake(df, tmp_path)
    assert not ok
    assert any("safe relative" in e or "escapes" in e for e in errors)


def test_snapshot_outside_manual_root_fails(tmp_path):
    outside = tmp_path / "outside.html"
    outside.write_text("x", encoding="utf-8")
    df = _df(tmp_path, snapshot_path="outside.html",
             supplied_snapshot_sha256=hashlib.sha256(b"x").hexdigest())
    ok, errors, _ = mi.validate_manual_evidence_intake(df, tmp_path)
    assert not ok
    assert any("must be under" in e for e in errors)


def test_extra_derived_column_fails(tmp_path):
    df = _df(tmp_path)
    df["evidence_accepted"] = "true"
    ok, errors, _ = mi.validate_manual_evidence_intake(df, tmp_path)
    assert not ok
    assert any("unexpected columns" in e for e in errors)
    assert any("derived columns" in e for e in errors)


def test_out_of_scope_ticker_fails(tmp_path):
    ok, errors, _ = mi.validate_manual_evidence_intake(_df(tmp_path, ticker="فملی"), tmp_path)
    assert not ok
    assert any("out of Part 3 scope" in e for e in errors)


def test_duplicate_normalized_url_fails(tmp_path):
    first = _row(tmp_path)
    second = _row(tmp_path, source_url=first["source_url"] + "/")
    df = pd.DataFrame([first, second], columns=mi.INTAKE_COLUMNS)
    ok, errors, _ = mi.validate_manual_evidence_intake(df, tmp_path)
    assert not ok
    assert any("duplicate normalized" in e for e in errors)


def test_pending_review_cannot_carry_findings(tmp_path):
    df = _df(tmp_path, content_review_status="pending_manual_review")
    ok, errors, _ = mi.validate_manual_evidence_intake(df, tmp_path)
    assert not ok
    assert any("pending review row" in e for e in errors)


def test_valid_pending_review_has_no_evidence(tmp_path):
    df = _df(
        tmp_path,
        content_review_status="pending_manual_review",
        event_type_supported="",
        reviewed_date_jalali="",
        exact_date_explicit="false",
        ordinary_share_explicit="unknown",
        publication_date_jalali="",
        publication_date_explicit="false",
        exact_text_or_event_summary="",
        reviewer_notes="",
        manual_reviewed_at_utc="",
    )
    registry, provenance = _base_registry_and_provenance()
    new_registry, new_prov, audit = mi.ingest_manual_evidence_intake(
        registry, provenance, df, tmp_path
    )
    rec = new_prov[(new_prov["ticker"] == "خمهر") & (new_prov["source_index"] == "3")].iloc[0]
    assert rec["retrieval_status"] == "manual_snapshot_imported"
    assert rec["evidence_accepted"] == "false"
    assert rec["reviewed_evidence_valid"] == "false"
    assert len(audit) == 1
    assert len(new_registry) == 21


def test_new_source_gets_index_three_and_manual_origin(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    new_registry, new_prov, audit = mi.ingest_manual_evidence_intake(
        registry, provenance, _df(tmp_path), tmp_path
    )
    row = new_registry[(new_registry["ticker"] == "خمهر")
                       & (new_registry["source_index"] == "3")].iloc[0]
    assert row["source_origin"] == "manual_discovery"
    assert row["discovery_status"] == "manual_snapshot_captured"
    assert row["active"] == "true"
    assert audit.iloc[0]["registry_action"] == "new_source_registered"
    assert ((new_prov["ticker"] == "خمهر") & (new_prov["source_index"] == "3")).sum() == 1


def test_reviewed_credible_news_can_be_accepted(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    _, new_prov, _ = mi.ingest_manual_evidence_intake(
        registry, provenance, _df(tmp_path), tmp_path
    )
    rec = new_prov[(new_prov["ticker"] == "خمهر") & (new_prov["source_index"] == "3")].iloc[0]
    assert rec["retrieval_status"] == "manual_snapshot_imported"
    assert rec["content_sha256"] == _row(tmp_path)["supplied_snapshot_sha256"]
    assert rec["reviewed_evidence_valid"] == "true"
    assert rec["evidence_accepted"] == "true"


def test_existing_url_preserves_source_index(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    seed = registry[(registry["ticker"] == "خمهر") & (registry["source_index"] == "1")].iloc[0]
    df = _df(
        tmp_path,
        source_url=seed["source_url"],
        final_url=seed["source_url"],
        source_type=seed["source_type"],
        source_title=seed["source_title"],
        event_type_supported="",
        reviewed_date_jalali="",
        exact_date_explicit="false",
        ordinary_share_explicit="unknown",
        publication_date_jalali="",
        publication_date_explicit="false",
        exact_text_or_event_summary="",
    )
    new_registry, new_prov, audit = mi.ingest_manual_evidence_intake(
        registry, provenance, df, tmp_path
    )
    assert len(new_registry) == len(registry)
    assert audit.iloc[0]["source_index"] == "1"
    assert audit.iloc[0]["registry_action"] == "existing_url_reused"
    assert ((new_prov["ticker"] == "خمهر") & (new_prov["source_index"] == "1")).sum() == 1


def test_existing_url_type_mismatch_fails(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    seed = registry[(registry["ticker"] == "خمهر") & (registry["source_index"] == "1")].iloc[0]
    df = _df(tmp_path, source_url=seed["source_url"], final_url=seed["source_url"],
             source_type="credible_news")
    with pytest.raises(ValueError, match="source_type mismatch"):
        mi.ingest_manual_evidence_intake(registry, provenance, df, tmp_path)


def test_inputs_are_not_mutated(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    intake = _df(tmp_path)
    r0 = registry.copy(deep=True)
    p0 = provenance.copy(deep=True)
    i0 = intake.copy(deep=True)
    mi.ingest_manual_evidence_intake(registry, provenance, intake, tmp_path)
    pd.testing.assert_frame_equal(registry, r0)
    pd.testing.assert_frame_equal(provenance, p0)
    pd.testing.assert_frame_equal(intake, i0)


def test_active_registry_and_provenance_are_one_to_one(tmp_path):
    registry, provenance = _base_registry_and_provenance()
    new_registry, new_prov, _ = mi.ingest_manual_evidence_intake(
        registry, provenance, _df(tmp_path), tmp_path
    )
    active = {(r["ticker"], str(r["source_index"])) for _, r in new_registry.iterrows()
              if r["active"] == "true"}
    prov = {(r["ticker"], str(r["source_index"])) for _, r in new_prov.iterrows()}
    assert active == prov
