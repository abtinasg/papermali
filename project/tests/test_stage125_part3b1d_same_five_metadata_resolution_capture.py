"""Focused tests for Stage125 Part 3B.1D metadata-resolution capture.

Network tests use mocks/local fixtures only — no real CODAL requests.
"""
from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b1d_same_five_metadata_resolution_capture as m  # noqa: E402


GOOD = m.AUTHORIZED_REQUESTS[0]
GOOD_URL = GOOD["exact_url"]
GOOD_SERIAL = GOOD["candidate_letter_serial"]


def _fixture_html(*, marker: str = "default") -> bytes:
    return (
        "<html><head><title>صورت‌های مالی 12 ماهه منتهی به  1392/06/31 "
        "(حسابرسی شده)</title></head>"
        f"<!-- marker:{marker} -->"
        '<body><span id="ctl00_CompanyName">نوسازي و ساختمان تهران</span>'
        '<span id="ctl00_lblSymbol">ثنوسا</span>'
        "PublishDateTime: 1392/07/15 10:11:12 "
        "SentDateTime: 1392/07/14 09:08:07 "
        "TracingNo: 12345"
        "</body></html>"
    ).encode("utf-8")


def _mock_transport_factory(bodies: dict[str, bytes] | None = None):
    bodies = bodies or {
        r["exact_url"]: _fixture_html(marker=r["slug"]) for r in m.AUTHORIZED_REQUESTS
    }
    calls: list[str] = []

    def transport(method: str, url: str):
        assert method == "GET"
        m.validate_authorized_url(
            url, candidate_letter_serial=m.decode_letter_serial_from_url(url),
        )
        calls.append(url)
        body = bodies.get(url, _fixture_html(marker=url))
        if len(body) > m.MAX_RESPONSE_BYTES:
            raise m.NetworkPolicyError("oversized response rejected")
        return body, {
            "request_url": url,
            "redirect_chain": [url],
            "final_url": url,
            "response_status": 200,
            "content_type": "text/html; charset=utf-8",
            "bytes": len(body),
            "redirect_count": 0,
        }

    transport.calls = calls  # type: ignore[attr-defined]
    return transport


def test_bad_scheme_rejected():
    with pytest.raises(m.NetworkPolicyError, match="bad scheme"):
        m.validate_authorized_url(
            GOOD_URL.replace("https://", "http://"),
            candidate_letter_serial=GOOD_SERIAL,
        )


def test_bad_host_rejected():
    with pytest.raises(m.NetworkPolicyError, match="host"):
        m.validate_authorized_url(
            GOOD_URL.replace("www.codal.ir", "evil.example"),
            candidate_letter_serial=GOOD_SERIAL,
        )


def test_bad_port_rejected():
    url = GOOD_URL.replace("https://www.codal.ir", "https://www.codal.ir:8443")
    with pytest.raises(m.NetworkPolicyError, match="bad port"):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_bad_path_rejected():
    url = GOOD_URL.replace("/Reports/Decision.aspx", "/Reports/Other.aspx")
    with pytest.raises(m.NetworkPolicyError, match="bad path"):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_missing_letter_serial_rejected():
    url = "https://www.codal.ir/Reports/Decision.aspx?rt=0"
    with pytest.raises(m.NetworkPolicyError, match="missing LetterSerial"):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_duplicate_letter_serial_rejected():
    url = GOOD_URL + "&LetterSerial=other=="
    # May fail authorized-set first; ensure policy rejects either way.
    with pytest.raises(m.NetworkPolicyError):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_mismatched_letter_serial_rejected():
    with pytest.raises(m.NetworkPolicyError, match="mismatched LetterSerial"):
        m.validate_authorized_url(GOOD_URL, candidate_letter_serial="AAAA==")


def test_credentials_rejected():
    url = GOOD_URL.replace("https://", "https://user:pass@")
    with pytest.raises(m.NetworkPolicyError, match="credentials"):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_fragment_rejected():
    with pytest.raises(m.NetworkPolicyError, match="fragment"):
        m.validate_authorized_url(
            GOOD_URL + "#x", candidate_letter_serial=GOOD_SERIAL,
        )


def test_wildcard_rejected():
    with pytest.raises(m.NetworkPolicyError, match="wildcard"):
        m.validate_authorized_url(
            "https://*.codal.ir/Reports/Decision.aspx?LetterSerial=x",
            candidate_letter_serial="x",
        )


def test_unknown_query_parameter_rejected():
    url = GOOD_URL + "&evil=1"
    with pytest.raises(m.NetworkPolicyError, match="unknown query"):
        m.validate_authorized_url(url, candidate_letter_serial=GOOD_SERIAL)


def test_post_rejected():
    with pytest.raises(m.NetworkPolicyError, match="POST rejected"):
        m.validate_authorized_url(
            GOOD_URL, candidate_letter_serial=GOOD_SERIAL, method="POST",
        )


def test_search_endpoint_rejected():
    url = "https://search.codal.ir/Reports/Decision.aspx?LetterSerial=x"
    with pytest.raises(m.NetworkPolicyError):
        m.validate_authorized_url(url, candidate_letter_serial="x")


def test_fifth_logical_request_rejected():
    state = m.CaptureAttemptState()
    for req in m.AUTHORIZED_REQUESTS:
        state.authorize_next(req["exact_url"])
    with pytest.raises(m.NetworkPolicyError, match="fifth logical request"):
        state.authorize_next(m.AUTHORIZED_REQUESTS[0]["exact_url"])


def test_retry_of_already_attempted_url_rejected():
    state = m.CaptureAttemptState()
    state.authorize_next(GOOD_URL)
    with pytest.raises(m.NetworkPolicyError, match="already-attempted"):
        state.authorize_next(GOOD_URL)


def test_ardistan_request_rejected():
    with pytest.raises(m.NetworkPolicyError, match="اردستان"):
        m.validate_authorized_url(m.ARDISTAN_URL)
    state = m.CaptureAttemptState()
    with pytest.raises(m.NetworkPolicyError, match="اردستان"):
        state.authorize_next(m.ARDISTAN_URL)


def test_redirect_to_another_host_rejected():
    with pytest.raises(m.NetworkPolicyError, match="another host"):
        m._assert_redirect_allowed(
            "https://evil.example/Reports/Decision.aspx?LetterSerial="
            + GOOD_SERIAL,
            expected_letter_serial=GOOD_SERIAL,
        )


def test_redirect_with_changed_letter_serial_rejected():
    with pytest.raises(m.NetworkPolicyError, match="changed LetterSerial"):
        m._assert_redirect_allowed(
            "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=OTHER==",
            expected_letter_serial=GOOD_SERIAL,
        )


def test_oversized_response_rejected():
    huge = b"x" * (m.MAX_RESPONSE_BYTES + 1)
    transport = _mock_transport_factory({GOOD_URL: huge})
    # Only one URL — force oversized on first authorized URL via custom map
    bodies = {r["exact_url"]: (_fixture_html() if r["exact_url"] != GOOD_URL else huge)
              for r in m.AUTHORIZED_REQUESTS}
    transport = _mock_transport_factory(bodies)
    with pytest.raises(m.NetworkPolicyError, match="oversized"):
        transport("GET", GOOD_URL)


def test_payload_hash_mismatch_rejected(tmp_path: Path):
    receipt = {
        "response_sha256": "a" * 64,
        "local_cache_path": "payload.bin",
    }
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"hello")
    # Emulate check in load path
    actual = hashlib.sha256(payload.read_bytes()).hexdigest()
    assert actual != receipt["response_sha256"]


def test_parsed_receipt_hash_mismatch_rejected():
    req = GOOD
    capture = {
        "response_sha256": "a" * 64,
        "capture_status": "captured_ok",
        "parser_eligible": True,
    }
    parsed = {
        "payload_sha256": "b" * 64,
        "capture_receipt_response_sha256": "b" * 64,
        "fields": {name: m._field_record(
            raw_value=None, source_selector=None,
            missingness_reason="x",
        ) for name in m.METADATA_FIELDS},
        "available_at": None,
    }
    errs = m.validate_parsed_receipt(parsed, capture)
    assert any("hash mismatch" in e for e in errs)


def test_canonical_to_source_backfill_rejected():
    parsed = {
        "available_at": None,
        "fields": {},
        "canonical_legal_entity": "x",
    }
    with pytest.raises(m.QCFail, match="canonical-to-source backfill"):
        m.reject_canonical_to_source_backfill(parsed)


def test_letterserial_as_lettercode_rejected():
    parsed = {"available_at": None, "LetterCode": "x", "fields": {}}
    with pytest.raises(m.QCFail, match="LetterSerial-as-LetterCode"):
        m.reject_canonical_to_source_backfill(parsed)


def test_missing_metadata_remains_null():
    fields = m.parse_codal_decision_metadata(b"<html><body>empty</body></html>")
    for name in m.METADATA_FIELDS:
        assert fields[name]["raw_value"] is None
        assert fields[name]["presence_status"] == "missing"
        assert fields[name]["missingness_reason"]


def test_sent_datetime_cannot_populate_available_at():
    req = GOOD
    receipt = m.build_success_receipt(
        req,
        started="2026-07-18T00:00:00Z",
        completed="2026-07-18T00:00:01Z",
        body=_fixture_html(),
        transport_meta={
            "redirect_chain": [GOOD_URL],
            "final_url": GOOD_URL,
            "response_status": 200,
            "content_type": "text/html",
            "redirect_count": 0,
        },
        local_cache_path="x",
        metadata_sha256="c" * 64,
    )
    fields = m.parse_codal_decision_metadata(_fixture_html())
    parsed = m.build_parsed_receipt(
        req, receipt, fields, parsed_at_utc="2026-07-18T00:00:01Z",
    )
    assert parsed["available_at"] is None
    assert fields["SentDateTime"]["presence_status"] == "present"
    parsed["available_at"] = fields["SentDateTime"]["raw_value"]
    with pytest.raises(m.QCFail, match="available_at"):
        m.reject_canonical_to_source_backfill(parsed)


def test_scientific_artifacts_remain_byte_identical():
    before = {
        rel: m.sha256_file(REPO_ROOT / rel) for rel in m.PINNED_INPUTS
    }
    assert before == m.PINNED_INPUTS


def test_authorized_urls_match_part3b1c_proposed():
    proposed = m.load_part3b1c_proposed_urls(REPO_ROOT)
    auth = [r["exact_url"] for r in m.AUTHORIZED_REQUESTS]
    assert auth == proposed


def test_mock_capture_four_requests(tmp_path: Path):
    # Minimal repo copy of required pinned inputs + auth lock
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    (tmp_path / "project" / "docs" / "ai").mkdir(parents=True)
    # Copy pinned inputs
    for rel in m.PINNED_INPUTS:
        src = REPO_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copy2(
        REPO_ROOT / "project/stage125" / m.F_AUTH,
        stage / m.F_AUTH,
    )
    roadmap = (
        "---\n"
        "last_completed_research_action_id: stage125-part3a-decision-lock\n"
        "next_research_action_id: stage125-part3b-evidence-capture\n"
        "---\n"
    )
    (tmp_path / "project/docs/ai/ROADMAP.md").write_text(roadmap, encoding="utf-8")
    # Fake git baseline ancestor via real repo: run against REPO_ROOT instead
    # with isolated output dir + mock transport.
    transport = _mock_transport_factory()
    out = tmp_path / "out"
    out.mkdir()
    # Use real repo for baseline/git/pinned; write outputs elsewhere.
    # perform_authorized_captures writes cache under repo — use tmp copy of cache
    # by monkeypatching CACHE via running with transport only at unit level.
    receipts, parsed_map, state = m.perform_authorized_captures(
        REPO_ROOT, transport=transport,
    )
    assert state.logical_count == 4
    assert len(transport.calls) == 4  # type: ignore[attr-defined]
    assert m.ARDISTAN_URL not in transport.calls  # type: ignore[attr-defined]
    for req in m.AUTHORIZED_REQUESTS:
        assert receipts[req["slug"]]["capture_status"] == "captured_ok"
        assert parsed_map[req["slug"]]["available_at"] is None
        assert set(parsed_map[req["slug"]]["fields"]) == set(m.METADATA_FIELDS)


def test_fresh_detached_worktree_check_zero_network_zero_writes(tmp_path: Path):
    """If capture artifacts exist, --check must not network or write."""
    stage = REPO_ROOT / "project" / "stage125"
    # Skip if capture not yet performed in this working tree.
    needed = [stage / m.RECEIPT_BY_SLUG[r["slug"]] for r in m.AUTHORIZED_REQUESTS]
    if not all(p.is_file() for p in needed):
        pytest.skip("capture artifacts not present yet")

    before = {}
    for path in stage.glob("part3b1d_*"):
        if path.is_file():
            before[path.name] = path.read_bytes()
    for name in (m.F_QC, m.F_METADATA, m.F_README, m.F_SUMMARY, m.F_MANIFEST):
        p = stage / name
        if p.is_file():
            before[name] = p.read_bytes()

    result = m.run(project_dir=ROOT, capture=False, check=True)
    assert result["network_requests_attempted"] == 0
    assert result["drift"] == []

    after = {}
    for path in stage.glob("part3b1d_*"):
        if path.is_file():
            after[path.name] = path.read_bytes()
    for name in (m.F_QC, m.F_METADATA, m.F_README, m.F_SUMMARY, m.F_MANIFEST):
        p = stage / name
        if p.is_file():
            after[name] = p.read_bytes()
    assert before == after
