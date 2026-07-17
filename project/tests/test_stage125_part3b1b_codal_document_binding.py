"""Tests for Stage125 Part 3B.1B CODAL Predictor-Document Binding Mini-Pilot."""
from __future__ import annotations

import json
import socket
import sys
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
        source_origin="stage124_feasibility_local_cache",
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
        with patch.object(m, "authorize_and_fetch_thanusa", wraps=m.authorize_and_fetch_thanusa) as spy:
            result = m.run(project_dir=ROOT, output_dir=out, check=True)
            spy.assert_called_once()
            assert spy.call_args.kwargs.get("capture") is False
        assert sentinel.calls_attempted == 0
    assert result["network_requests_attempted"] == 0


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
    cache = p3b0.ImmutableCache(tmp_path / "cache")
    html = (
        b"<html><title>test</title>"
        b'<span id="lblPublishDateTime">1392/01/01 12:00:00</span></html>'
    )

    def transport(method, url):
        m.assert_url_allowed(url)
        return html, {
            "request_url": url,
            "redirect_chain": [url],
            "final_url": url,
            "response_status": 200,
            "content_type": "text/html",
            "bytes": len(html),
            "redirect_count": 0,
        }

    result = m.authorize_and_fetch_thanusa(
        cache=cache, capture=True, transport=transport,
    )
    assert result is not None
    assert result.success
    assert result.payload_sha256 == m.sha256_bytes(html)


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
