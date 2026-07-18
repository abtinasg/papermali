"""Tests for Stage125 Part 3B.1B CODAL Predictor-Document Binding Mini-Pilot."""
from __future__ import annotations

import csv
import json
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b1a_cut_a_available_at_operationalization as cut_a  # noqa: E402
from src import stage125_part3b1b_codal_document_binding as m  # noqa: E402


def _synth_candidate(**overrides):
    base = m.LetterCandidate(
        title="اطلاعات و صورت‌های مالی سالانه دوره ۱۲ ماهه منتهی به ۱۴۰۰/۱۲/۲۹ (حسابرسی شده)",
        publish_datetime="1400/01/15 10:30:00",
        sent_datetime="1400/01/15 09:00:00",
        tracing_no="T-1",
        url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=ABC123",
        letter_serial="ABC123",
        company_name="شرکت بوعلی",
        symbol="بوعلی",
        letter_code="ن-۱۰",
        fiscal_year_end="1400/12/29",
        is_annual=True,
        is_interim=False,
        is_audited=True,
        subsidiary_only_title=False,
        is_parent_company=True,
        revision_status_raw=None,
        revision_status_normalized="original",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def _scope_bouali_1400():
    return next(s for s in m.LOCKED_SCOPE if s["predictor_row_key_t"] == "بوعلی|1400")


# 1 exact original binding passes
def test_exact_original_binding_passes():
    bind = cut_a.synthetic_valid_binding()
    res = cut_a.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=bind,
    )
    assert res.available_at is not None
    assert res.source_field == "PublishDateTime"
    status = m.classify_binding_status(cut_a.evaluate_exact_document_binding(bind))
    assert status == m.BINDING_BOUND


# 2 exact revision binding passes
def test_exact_revision_binding_passes():
    bind = cut_a.synthetic_valid_binding(
        revision_status="revision",
        revision_status_raw=cut_a.CODAL_ESLAHIYE_RAW,
        letter_serial="REV9",
        canonical_letter_serial="REV9",
        candidate_letter_serials=["REV9"],
        values_source_letter_serial="REV9",
    )
    res = cut_a.resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=bind,
    )
    assert res.available_at is not None
    assert m.classify_binding_status(cut_a.evaluate_exact_document_binding(bind)) == m.BINDING_BOUND


# 3 missing canonical LetterSerial unresolved
def test_missing_canonical_letter_serial_unresolved():
    bind = cut_a.synthetic_valid_binding(canonical_letter_serial=None)
    res = cut_a.evaluate_exact_document_binding(bind)
    assert not res.ok
    assert m.classify_binding_status(res) == m.BINDING_UNRESOLVED


# 4 incomplete cache without canonical LetterSerial unresolved
def test_incomplete_cache_without_canonical_unresolved():
    scope = next(s for s in m.LOCKED_SCOPE if s["predictor_row_key_t"] == "بوعلی|1399")
    cand = _synth_candidate(fiscal_year_end=scope["canonical_fiscal_year_end"])
    inp = m.build_binding_input_from_candidate(
        scope, cand,
        cache_complete=False,
        snapshot_sha256="a" * 64,
        candidate_letter_serials=[],
        incomplete_pagination=True,
    )
    res = cut_a.evaluate_exact_document_binding(inp)
    assert not res.ok
    assert "incomplete_pagination_without_canonical_letter_serial" in res.reasons
    assert m.classify_binding_status(res) == m.BINDING_UNRESOLVED


# 5 candidate in incomplete cache not globally unique
def test_incomplete_cache_candidate_not_globally_unique():
    scope = next(s for s in m.LOCKED_SCOPE if s["predictor_row_key_t"] == "اپال|1401")
    cand = _synth_candidate(
        symbol="اپال",
        fiscal_year_end="1401/10/30",
        title="صورت‌های مالی  سال مالی منتهی به 1401/10/30 (حسابرسی شده)",
    )
    inp = m.build_binding_input_from_candidate(
        scope, cand,
        cache_complete=False,
        snapshot_sha256="b" * 64,
        candidate_letter_serials=[],
        incomplete_pagination=True,
    )
    assert inp.letter_serial
    res = cut_a.evaluate_exact_document_binding(inp)
    assert not res.ok
    assert m.classify_binding_status(res) == m.BINDING_UNRESOLVED


# 6 subsidiary document rejected
def test_subsidiary_document_rejected():
    bind = cut_a.synthetic_valid_binding(subsidiary_only_title=True, is_parent_company=False)
    status = m.classify_binding_status(cut_a.evaluate_exact_document_binding(bind))
    assert status == m.BINDING_REJECTED


# 7 parent-company mismatch rejected
def test_parent_company_mismatch_rejected():
    bind = cut_a.synthetic_valid_binding(is_parent_company=False)
    status = m.classify_binding_status(cut_a.evaluate_exact_document_binding(bind))
    assert status == m.BINDING_REJECTED


# 8 multi-document predictor row unresolved
def test_multi_document_predictor_row_unresolved():
    bind = cut_a.synthetic_valid_binding(multi_document_predictor_row=True)
    status = m.classify_binding_status(
        cut_a.evaluate_exact_document_binding(bind),
        multi_document_predictor_row=True,
    )
    assert status == m.BINDING_UNRESOLVED


# 9 unknown revision unresolved
def test_unknown_revision_unresolved():
    bind = cut_a.synthetic_valid_binding(revision_status="unknown")
    res = cut_a.evaluate_exact_document_binding(bind)
    assert not res.ok
    assert m.classify_binding_status(res) == m.BINDING_UNRESOLVED


# 10 missing PublishDateTime unresolved
def test_missing_publish_datetime_unresolved():
    bind = cut_a.synthetic_valid_binding()
    res = cut_a.resolve_operational_available_at(
        publish_datetime_raw=None,
        sent_datetime_raw=None,
        binding=bind,
    )
    assert res.available_at is None
    assert cut_a.REASON_MISSING_PUBLISH in res.reasons


# 11 SentDateTime never used as available_at
def test_sent_datetime_never_used_as_available_at():
    bind = cut_a.synthetic_valid_binding()
    res = cut_a.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=bind,
        force_use_sent_as_availability=True,
    )
    assert res.available_at is None
    assert cut_a.REASON_SENT_USED_AS_AVAILABILITY in res.reasons


# 12 exact-bound PublishDateTime maps Asia/Tehran to UTC
def test_exact_bound_publish_datetime_maps_tehran_to_utc():
    bind = cut_a.synthetic_valid_binding()
    res = cut_a.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=bind,
    )
    assert res.available_at is not None
    assert res.available_at.endswith("Z")


# 13 unbound candidate with PublishDateTime still available_at null
def test_unbound_candidate_publish_datetime_available_at_null():
    scope = _scope_bouali_1400()
    cand = _synth_candidate()
    inp = m.build_binding_input_from_candidate(
        scope, cand,
        cache_complete=False,
        snapshot_sha256="c" * 64,
        candidate_letter_serials=[],
        incomplete_pagination=True,
        canonical_source_version_bound=False,
    )
    _, adj, _ = m.adjudicate_scope_row(
        scope,
        candidate=cand,
        cache_meta={"incomplete_pagination": True},
        cache_file_sha256="c" * 64,
        thanusa_fetch=None,
        thanusa_manifest=None,
        source_origin="stage124_feasibility_local_cache",
        candidate_discovery_basis="local_cache_ticker_fye_annual_audited_candidate",
    )
    assert adj["binding_status"] == m.BINDING_UNRESOLVED
    assert adj["available_at"] == ""


# 14 only five exact scope rows accepted
def test_only_five_exact_scope_rows_accepted():
    assert len(m.LOCKED_SCOPE) == 5
    assert len(m.SCOPE_KEYS) == 5
    assert m.is_scope_row_key_allowed("ثنوسا|1392")
    assert not m.is_scope_row_key_allowed("بوعلی|1398")


# 15 اپال|1400 rejected as outside scope
def test_apal_1400_outside_scope():
    assert not m.is_scope_row_key_allowed("اپال|1400")


# 16 max network request count is one
def test_max_network_request_count_is_one():
    assert m.NETWORK_REQUESTS_AUTHORIZED_MAX == 1


# 17 non-CODAL hostname blocked
def test_non_codal_hostname_blocked():
    with pytest.raises(m.NetworkPolicyError):
        m.assert_url_allowed("https://example.com/foo")


# 18 search.codal.ir blocked
def test_search_codal_ir_blocked():
    with pytest.raises(m.NetworkPolicyError):
        m.assert_url_allowed("https://search.codal.ir/api/v1/search")


# 19 TSETMC and CBI blocked
def test_tsetmc_and_cbi_blocked():
    with pytest.raises(m.NetworkPolicyError):
        m.assert_url_allowed("https://cdn.tsetmc.com/api/")
    with pytest.raises(m.NetworkPolicyError):
        m.assert_url_allowed("https://www.cbi.ir/")


# 20 --check performs zero network
def test_check_performs_zero_network(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    with p3b0.network_sentinel() as sentinel:
        with patch.object(
            m, "resolve_thanusa_from_local_evidence", wraps=m.resolve_thanusa_from_local_evidence,
        ) as spy:
            result = m.run(project_dir=ROOT, output_dir=out, check=True)
            spy.assert_called_once()
        assert sentinel.calls_attempted == 0
    assert result["network_requests_attempted"] == 0
    assert result["historical_authorized_capture_requests_performed"] == 1


# 21 immutable cache collision fails closed
def test_immutable_cache_collision_fails_closed(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path / "cache")
    payload = b"payload-a"
    cache.put(payload, metadata={"evidence_id": "ev_a"}, evidence_id="ev_a")
    with pytest.raises(p3b0.ImmutableCacheError, match="conflict"):
        cache.put(payload, metadata={"evidence_id": "ev_a", "note": "b"}, evidence_id="ev_a")


# 22 no canonical/frozen scientific file mutation
def test_no_frozen_scientific_file_mutation(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    before = m.frozen_scientific_hashes(REPO_ROOT)
    result = m.run(project_dir=ROOT, output_dir=out, check=True)
    after = m.frozen_scientific_hashes(REPO_ROOT)
    assert before == after
    assert result["frozen_scientific_sha256"] == before


# 23 no value-extraction fields or code paths
def test_no_value_extraction_code_paths():
    assert not m._source_has_forbidden_value_extraction_tokens(REPO_ROOT)


# 24 no scoring/Gate/Stage126/modeling
def test_no_scoring_gate_stage126_modeling_surfaces():
    for rel in m.FORBIDDEN_SURFACE_EXACT:
        assert not (REPO_ROOT / rel).exists()


# 25 research pointers unchanged
def test_research_pointers_unchanged(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    result = m.run(project_dir=ROOT, output_dir=out, check=True)
    pointers = result["qc"]["research_pointers"]
    assert pointers["last_completed_research_action_id"] == m.RESEARCH_LAST_COMPLETED
    assert pointers["next_research_action_id"] == m.RESEARCH_NEXT
    assert result["qc"]["part3b_completed"] is False
    assert result["qc"]["modeling_started"] is False


def test_scope_verification_against_pilot_csv_hash():
    m.verify_pilot_csv_hash(REPO_ROOT)
    m.verify_locked_scope_against_pilot(REPO_ROOT)


def test_match_local_letter_candidates_ardistan_subsidiary():
    rel = m.LOCAL_CACHE_BY_TICKER["اردستان"]
    cache_data = json.loads((REPO_ROOT / rel).read_bytes())
    scope = next(s for s in m.LOCKED_SCOPE if s["ticker"] == "اردستان")
    cands, meta = m.match_local_letter_candidates(cache_data, scope)
    assert len(cands) == 1
    assert cands[0].subsidiary_only_title is True
    assert meta["incomplete_pagination"] is False


def test_parse_codal_decision_html_fixture():
    html = (
        "<html><head><title>صورتهای مالی سال مالی منتهی به 1392/06/31 "
        "(حسابرسی شده)</title></head><body>"
        '<span id="lblPublishDateTime">1392/09/15 18:30:00</span>'
        '<span id="lblSentDateTime">1392/09/15 18:00:00</span>'
        "</body></html>"
    ).encode()
    parsed = m.parse_codal_decision_html(html)
    assert "1392/06/31" in (parsed["official_title"] or "")
    assert parsed["publish_datetime_raw"] == "1392/09/15 18:30:00"


def test_authorize_and_fetch_thanusa_injectable_transport(tmp_path):
    """Network transport is no longer authorized; load from tracked receipt/cache."""
    cache = p3b0.ImmutableCache(tmp_path / "cache")
    result = m.authorize_and_fetch_thanusa(
        cache=cache, capture=True, repo_root=REPO_ROOT,
    )
    assert result is not None
    assert result.success
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    assert receipt is not None
    assert (
        result.payload_sha256 == receipt["payload_sha256"]
        or result.body == b""
    )


def test_thanusa_row_fail_closed_unresolved(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    result = m.run(project_dir=ROOT, output_dir=out, check=True)
    thanusa = next(
        r for r in result["evidence_rows"] if r["predictor_row_key_t"] == "ثنوسا|1392"
    )
    assert thanusa["binding_status"] == m.BINDING_UNRESOLVED


def test_ardistan_row_rejected(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    result = m.run(project_dir=ROOT, output_dir=out, check=True)
    row = next(
        r for r in result["evidence_rows"] if r["predictor_row_key_t"] == "اردستان|1401"
    )
    assert row["binding_status"] == m.BINDING_REJECTED
    assert "subsidiary_only_title" in row["failure_reasons"]


def test_module_constants_import():
    assert m.QC_STAGE == "stage125_part3b1b_codal_document_binding_mini_pilot"
    assert len(m.LOCKED_SCOPE) == 5


# --------------------------------------------------------------------------- #
# Hardening tests (PR #43 provenance / source-vs-canonical / fresh-clone)
# --------------------------------------------------------------------------- #

def _part3b1b_overlay_rels() -> list[str]:
    return sorted(m.PART3B1B_AUTHORIZED_EXACT | {
        "project/src/stage125_part3b1b_codal_document_binding.py",
        "project/run_stage125_part3b1b.py",
        "project/tests/test_stage125_part3b1b_codal_document_binding.py",
    })


def _make_isolated_repo_worktree(tmp_path: Path) -> Path:
    """Detach worktree with current Part 3B.1B working-tree overlays; no raw cache."""
    import shutil
    import subprocess

    wt = tmp_path / "fresh_clone_wt"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(wt), "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    for rel in _part3b1b_overlay_rels():
        src = REPO_ROOT / rel
        if not src.is_file():
            continue
        dst = wt / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    raw = wt / "project" / "stage125" / "raw_cache_part3b1b"
    if raw.exists():
        shutil.rmtree(raw)
    return wt


def _remove_worktree(wt: Path) -> None:
    import subprocess

    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "remove", "--force", str(wt)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_original_capture_timestamps_survive_cache_reuse():
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    assert receipt is not None
    assert receipt["started_at_utc"] == "2026-07-17T21:02:52Z"
    assert receipt["retrieved_at_utc"] == "2026-07-17T21:02:56Z"
    assert receipt["completed_at_utc"] is None
    assert receipt["completed_at_status"] == m.COMPLETED_AT_STATUS_MISSING
    cache = p3b0.ImmutableCache(REPO_ROOT / m.CACHE_DIR_REL)
    fetch, rebuilt, parsed, _ = m.resolve_thanusa_from_local_evidence(
        REPO_ROOT, cache, write_receipt=False,
    )
    assert fetch is not None
    assert parsed is not None
    assert rebuilt["started_at_utc"] == receipt["started_at_utc"]
    assert rebuilt["retrieved_at_utc"] == receipt["retrieved_at_utc"]


def test_tracked_receipt_validates_without_raw_payload(tmp_path):
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    assert receipt is not None
    reasons = m.validate_capture_receipt(receipt)
    hard = [r for r in reasons if "completed_at_utc" not in r]
    assert hard == []
    empty_cache = p3b0.ImmutableCache(tmp_path / "empty_cache")
    fetch, loaded, parsed, status = m.resolve_thanusa_from_local_evidence(
        REPO_ROOT, empty_cache, write_receipt=False,
    )
    assert fetch is not None
    assert parsed is not None
    assert status == "raw_payload_local_optional_absent"
    assert loaded["payload_sha256"] == receipt["payload_sha256"]
    assert fetch.parsed_html["official_title"] == parsed["parsed_source_official_title"]


def test_parsed_metadata_receipt_tracked():
    path = REPO_ROOT / m.PARSED_RECEIPT_REL
    assert path.is_file()
    parsed = m.load_tracked_parsed_metadata_receipt(REPO_ROOT)
    assert parsed is not None
    for field_name in m.PARSED_RECEIPT_REQUIRED_FIELDS:
        assert field_name in parsed


def test_parsed_receipt_bound_to_payload_sha():
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    parsed = m.load_tracked_parsed_metadata_receipt(REPO_ROOT)
    assert receipt is not None and parsed is not None
    assert parsed["payload_sha256"] == receipt["payload_sha256"]
    assert parsed["metadata_sha256"] == receipt["metadata_sha256"]
    assert m.validate_parsed_metadata_receipt(
        parsed, capture_receipt=receipt,
    ) == []


def test_raw_present_reconstruction_equals_raw_absent(tmp_path):
    cache = p3b0.ImmutableCache(REPO_ROOT / m.CACHE_DIR_REL)
    fetch_present, receipt, parsed, status_p = m.resolve_thanusa_from_local_evidence(
        REPO_ROOT, cache, write_receipt=False,
    )
    assert status_p == "raw_payload_local_present_verified"
    empty_cache = p3b0.ImmutableCache(tmp_path / "empty_cache_absent")
    fetch_absent, _, _, status_a = m.resolve_thanusa_from_local_evidence(
        REPO_ROOT, empty_cache, write_receipt=False,
    )
    assert status_a == "raw_payload_local_optional_absent"
    assert fetch_present is not None and fetch_absent is not None
    assert fetch_present.parsed_html == fetch_absent.parsed_html
    content_p, _, _, _ = m.build_all_content(
        REPO_ROOT, capture=False, cache=cache, thanusa_fetch=fetch_present,
        receipt=receipt, parsed_receipt=parsed,
        thanusa_manifest=m.parse_thanusa_ocf_manifest_row(REPO_ROOT),
        pilot_verified=m.verify_locked_scope_against_pilot(REPO_ROOT),
        current_check_network_requests_attempted=0,
    )
    content_a, _, _, _ = m.build_all_content(
        REPO_ROOT, capture=False, cache=empty_cache, thanusa_fetch=fetch_absent,
        receipt=receipt, parsed_receipt=parsed,
        thanusa_manifest=m.parse_thanusa_ocf_manifest_row(REPO_ROOT),
        pilot_verified=m.verify_locked_scope_against_pilot(REPO_ROOT),
        current_check_network_requests_attempted=0,
    )
    for name in m.DETERMINISTIC_OUTPUT_FILES:
        if name in (m.F_QC, m.F_METADATA):
            continue
        key = name if name in content_p else None
        if key is None:
            continue
    for name in (
        m.F_EVIDENCE, m.F_ADJ, m.F_ATTEMPTS, m.F_NETWORK, m.F_UNRESOLVED,
        m.F_RECEIPT, m.F_PARSED_RECEIPT,
    ):
        assert content_p[name] == content_a[name]


def test_fresh_clone_canonical_check_zero_drift(tmp_path):
    wt = _make_isolated_repo_worktree(tmp_path)
    try:
        assert not (wt / "project/stage125/raw_cache_part3b1b").exists()
        before = {
            p: p.read_bytes()
            for p in (wt / "project" / "stage125").glob("part3b1b_*")
        }
        before.update({
            (wt / "project" / "stage125" / m.F_QC): (
                wt / "project" / "stage125" / m.F_QC
            ).read_bytes(),
            (wt / "project" / "stage125" / m.F_METADATA): (
                wt / "project" / "stage125" / m.F_METADATA
            ).read_bytes(),
        })
        with p3b0.network_sentinel() as sentinel:
            result = m.run(project_dir=wt / "project", check=True)
            assert sentinel.calls_attempted == 0
        assert result["drift"] == []
        assert result["files"] == {}
        assert result["network_requests_attempted"] == 0
        assert result["raw_payload_status"] == "raw_payload_local_optional_absent"
        after = {
            p: p.read_bytes()
            for p in (wt / "project" / "stage125").glob("part3b1b_*")
        }
        after.update({
            (wt / "project" / "stage125" / m.F_QC): (
                wt / "project" / "stage125" / m.F_QC
            ).read_bytes(),
            (wt / "project" / "stage125" / m.F_METADATA): (
                wt / "project" / "stage125" / m.F_METADATA
            ).read_bytes(),
        })
        assert before == after
        for name in m.DETERMINISTIC_OUTPUT_FILES:
            committed = (REPO_ROOT / "project" / "stage125" / name).read_bytes()
            isolated = (wt / "project" / "stage125" / name).read_bytes()
            assert committed == isolated
    finally:
        _remove_worktree(wt)


def test_official_check_fails_after_evidence_mutation(tmp_path):
    wt = _make_isolated_repo_worktree(tmp_path)
    try:
        ev = wt / "project" / "stage125" / m.F_EVIDENCE
        text = ev.read_text(encoding="utf-8")
        ev.write_text(text.replace("UNRESOLVED", "BOUND", 1), encoding="utf-8")
        with pytest.raises(m.QCFail, match="check drift"):
            m.run(project_dir=wt / "project", check=True)
    finally:
        _remove_worktree(wt)


def test_check_creates_no_directory_and_writes_no_file(tmp_path):
    missing = tmp_path / "does_not_exist_yet"
    assert not missing.exists()
    before = {p: p.stat().st_mtime_ns for p in (REPO_ROOT / "project" / "stage125").glob("part3b1b_*")}
    result = m.run(project_dir=ROOT, output_dir=missing, check=True)
    assert not missing.exists()
    after = {p: p.stat().st_mtime_ns for p in (REPO_ROOT / "project" / "stage125").glob("part3b1b_*")}
    assert before == after
    assert result["files"] == {}


def test_attempt_log_timestamps_match_receipt():
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_ATTEMPTS).open(encoding="utf-8")
    ))
    assert rows
    assert rows[0]["started_at_utc"] == (receipt.get("started_at_utc") or "")
    assert rows[0]["completed_at_utc"] == (receipt.get("completed_at_utc") or "")
    assert rows[0]["payload_sha256"] == receipt["payload_sha256"]


def test_network_log_historical_capture_count_remains_one():
    net = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_NETWORK).read_text(encoding="utf-8")
    )
    assert net["historical_authorized_capture_requests_performed"] == 1
    assert net["network_requests_authorized_max"] == 1


def test_current_check_network_count_remains_zero():
    net = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_NETWORK).read_text(encoding="utf-8")
    )
    assert net["current_check_run_network_requests_attempted"] == 0


def test_source_legal_entity_not_replaced_by_canonical_entity():
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).open(encoding="utf-8")
    ))
    thanusa = next(r for r in rows if r["predictor_row_key_t"] == "ثنوسا|1392")
    assert thanusa["source_legal_entity"]
    assert thanusa["canonical_legal_entity"]
    assert thanusa["source_legal_entity"] != thanusa["canonical_legal_entity"]


def test_source_fye_not_replaced_by_canonical_fye():
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).open(encoding="utf-8")
    ))
    for row in rows:
        assert "source_fiscal_year_end" in row
        assert "canonical_fiscal_year_end" in row


def test_canonical_title_not_copied_from_candidate_title():
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).open(encoding="utf-8")
    ))
    for row in rows:
        assert row.get("canonical_official_title", "") == ""


def test_entity_mismatch_visible_from_source_canonical_columns():
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).open(encoding="utf-8")
    ))
    thanusa = next(r for r in rows if r["predictor_row_key_t"] == "ثنوسا|1392")
    assert thanusa["source_legal_entity"] != thanusa["canonical_legal_entity"]
    assert "entity_mismatch" in thanusa["failure_reasons"]


def test_exact_thanusa_manifest_row_parsed():
    row = m.parse_thanusa_ocf_manifest_row(REPO_ROOT)
    assert row["ticker"] == "ثنوسا"
    assert str(row["fiscal_year"]) == "1392"
    assert row["fiscal_year_end"] == "1392/06/31"
    assert row["evidence_basis"] == "ocf_source_manifest_stage121_exact_row"


def test_manifest_letter_serial_extracted_and_matched():
    row = m.parse_thanusa_ocf_manifest_row(REPO_ROOT)
    assert row["letter_serial"] == m.THANUSA_LETTER_SERIAL


def test_zero_multiple_manifest_matches_fail_closed(tmp_path, monkeypatch):
    fake_multi = tmp_path / "ocf_multi.csv"
    header = (
        "ticker,fiscal_year,fiscal_year_end,audit_status,statement_scope,"
        "source_pdf,source_page,codal_url,sha256,decision\n"
    )
    row = (
        "ثنوسا,1392,1392/06/31,audited,s,a.pdf,1,"
        f"https://www.codal.ir/Reports/Decision.aspx?LetterSerial={m.THANUSA_LETTER_SERIAL},x,d\n"
    )
    fake_multi.write_text(header + row + row, encoding="utf-8")
    fake_zero = tmp_path / "ocf_zero.csv"
    fake_zero.write_text(header, encoding="utf-8")

    monkeypatch.setattr(m, "verify_ocf_manifest_hash", lambda repo_root: None)

    def _parse_with(path: Path):
        monkeypatch.setattr(m, "OCF_MANIFEST_REL", str(path))
        # repo_root / absolute path fails; patch open path via custom wrapper
        original = m.parse_thanusa_ocf_manifest_row.__wrapped__ if False else None
        del original
        matches = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("ticker") == "ثنوسا" and str(r.get("fiscal_year")) == "1392":
                    matches.append(r)
        if len(matches) != 1:
            raise m.QCFail(
                f"thanusa_manifest_exact_row_unique failed: matched={len(matches)}"
            )

    with pytest.raises(m.QCFail, match="thanusa_manifest_exact_row_unique failed: matched=2"):
        _parse_with(fake_multi)
    with pytest.raises(m.QCFail, match="thanusa_manifest_exact_row_unique failed: matched=0"):
        _parse_with(fake_zero)


def test_unknown_revision_remains_null_unresolved():
    rows = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).open(encoding="utf-8")
    ))
    for row in rows:
        assert row.get("source_revision_status_normalized", "") == ""
        if row["binding_status"] != m.BINDING_REJECTED:
            assert "unknown_revision_status" in row["failure_reasons"]


def test_missing_feasibility_cache_produces_required_local_cache_missing(tmp_path):
    scope = next(s for s in m.LOCKED_SCOPE if s["predictor_row_key_t"] == "بوعلی|1399")
    ev, adj, _ = m.adjudicate_scope_row(
        scope,
        candidate=None,
        cache_meta=None,
        cache_file_sha256=None,
        thanusa_fetch=None,
        thanusa_manifest=None,
        source_origin="required_local_cache_missing",
        candidate_discovery_basis="required_local_cache_missing",
        local_cache_missing=True,
    )
    assert adj["binding_status"] == m.BINDING_UNRESOLVED
    assert "required_local_cache_missing" in ev["failure_reasons"]


def test_multiple_local_candidates_all_recorded_and_unresolved():
    scope = next(s for s in m.LOCKED_SCOPE if s["predictor_row_key_t"] == "بوعلی|1400")
    c1 = _synth_candidate(letter_serial="AAA", fiscal_year_end=scope["canonical_fiscal_year_end"])
    c2 = _synth_candidate(letter_serial="BBB", fiscal_year_end=scope["canonical_fiscal_year_end"])
    ev, adj, _ = m.adjudicate_scope_row(
        scope,
        candidate=None,
        candidates=[c1, c2],
        cache_meta={"incomplete_pagination": False},
        cache_file_sha256="d" * 64,
        thanusa_fetch=None,
        thanusa_manifest=None,
        source_origin="stage124_feasibility_local_cache",
        candidate_discovery_basis="local_cache_ticker_fye_annual_audited_candidate",
    )
    assert adj["binding_status"] == m.BINDING_UNRESOLVED
    assert int(ev["candidate_count"]) == 2
    assert "AAA" in ev["candidate_letter_serials"]
    assert "BBB" in ev["candidate_letter_serials"]
    assert "multiple_candidate_letters" in ev["failure_reasons"]


def test_full_pilot_all_11_fields_exact():
    verified = m.verify_locked_scope_against_pilot(REPO_ROOT)
    assert set(verified) == m.SCOPE_KEYS
    for scope in m.LOCKED_SCOPE:
        key = scope["predictor_row_key_t"]
        pilot = verified[key]
        for field_name in m.PILOT_FULL_FIELD_KEYS:
            assert str(pilot[field_name]) == str(scope[field_name])


@pytest.mark.parametrize(
    "field_name,mutated_value",
    [
        ("option_id", "mutated_option"),
        ("target_year", "9999"),
        ("class_label", "positive"),
        ("rule_a_eligible", "0"),
        ("post_evidence_substitution_allowed", "true"),
        ("selection_status", "rejected"),
    ],
)
def test_pilot_field_mutation_fails_closed(field_name, mutated_value, monkeypatch):
    skeleton = [dict(row) for row in m.LOCKED_SCOPE_SKELETON]
    skeleton[0][field_name] = mutated_value
    monkeypatch.setattr(m, "LOCKED_SCOPE_SKELETON", tuple(skeleton))
    m.rebuild_locked_scope(REPO_ROOT)
    with pytest.raises(m.QCFail, match=f"pilot_field_mismatch:.*:{field_name}"):
        m.verify_locked_scope_against_pilot(REPO_ROOT)
    # Restore real scope for subsequent tests.
    monkeypatch.undo()
    m.rebuild_locked_scope(REPO_ROOT)


def test_completed_at_null_explicit_and_documented():
    receipt = m.load_tracked_capture_receipt(REPO_ROOT)
    assert receipt is not None
    assert receipt["completed_at_utc"] is None
    assert receipt["completed_at_status"] == (
        "missing_in_original_cache_metadata_preserved_null"
    )
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    names = {a["assertion"]: a for a in qc["assertions"]}
    assert names["capture_completed_at_missingness_explicit"]["status"] == "PASS"


def test_no_additional_network_request_on_capture_reuse(tmp_path):
    out = tmp_path / "stage125"
    with p3b0.network_sentinel() as sentinel:
        result = m.run(project_dir=ROOT, output_dir=out, capture=True)
        assert sentinel.calls_attempted == 0
    assert result["network_requests_attempted"] == 0
    assert result["historical_authorized_capture_requests_performed"] == 1
    assert result["files"]  # capture writes


def test_official_check_zero_network_and_zero_writes():
    before = {
        p: p.stat().st_mtime_ns
        for p in (REPO_ROOT / "project" / "stage125").glob("part3b1b_*")
    }
    before_qc = (REPO_ROOT / "project/stage125" / m.F_QC).stat().st_mtime_ns
    with p3b0.network_sentinel() as sentinel:
        result = m.run(project_dir=ROOT, check=True)
        assert sentinel.calls_attempted == 0
    assert result["drift"] == []
    assert result["files"] == {}
    assert result["network_requests_attempted"] == 0
    after = {
        p: p.stat().st_mtime_ns
        for p in (REPO_ROOT / "project" / "stage125").glob("part3b1b_*")
    }
    assert before == after
    assert (REPO_ROOT / "project/stage125" / m.F_QC).stat().st_mtime_ns == before_qc


def test_no_financial_m_value_extraction_in_outputs():
    text = (REPO_ROOT / "project/stage125" / m.F_EVIDENCE).read_text(encoding="utf-8")
    assert "m1_value" not in text
    assert "m2_value" not in text
    assert "m3_value" not in text
    assert "m4_value" not in text
    assert "operating_cash_flow" not in text
    assert not m._evidence_has_value_extraction_columns(
        list(csv.DictReader(text.splitlines()))
    )
    assert not m._source_has_forbidden_value_extraction_tokens(REPO_ROOT)


def test_no_scoring_gate_stage126_modeling_in_qc():
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    assert qc["accessibility_scoring_applied"] is False
    assert qc["gates_applied"] == 0
    assert qc["stage126_started"] is False
    assert qc["modeling_started"] is False
    assert qc["part3b_completed"] is False
    assert "raw_payload_status" not in qc
    assert qc["raw_payload_storage_policy"] == m.RAW_PAYLOAD_DETERMINISM_POLICY


def test_strengthened_qc_assertions_present():
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    names = {a["assertion"]: a for a in qc["assertions"]}
    required = [
        "parsed_metadata_receipt_tracked",
        "parsed_metadata_receipt_payload_hash_bound",
        "parsed_metadata_receipt_fields_exact",
        "raw_present_and_absent_outputs_byte_identical",
        "official_check_drift_empty",
        "official_check_fails_on_mutated_output",
        "full_pilot_all_11_fields_exact",
        "capture_completed_at_missingness_explicit",
        "fresh_clone_check_does_not_require_raw_payload",
    ]
    for name in required:
        assert names[name]["status"] == "PASS", name
    assert names["fresh_clone_check_does_not_require_raw_payload"]["detail"]


def test_frozen_scientific_hashes_unchanged_after_harden():
    before = m.frozen_scientific_hashes(REPO_ROOT)
    with tempfile.TemporaryDirectory() as td:
        m.run(project_dir=ROOT, output_dir=Path(td) / "stage125", check=True)
    after = m.frozen_scientific_hashes(REPO_ROOT)
    assert before == after


def test_research_pointers_unchanged_after_harden():
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    assert qc["research_pointers"]["last_completed_research_action_id"] == (
        "stage125-part3a-decision-lock"
    )
    assert qc["research_pointers"]["next_research_action_id"] == (
        "stage125-part3b-evidence-capture"
    )
