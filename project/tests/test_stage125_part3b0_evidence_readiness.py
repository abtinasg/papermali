"""Tests for Stage125 Part 3B.0 — Evidence Capture Readiness.

All repository-mutating cache tests use pytest temporary directories only.
"""
from __future__ import annotations

import csv
import io
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3a_decision_lock as lock  # noqa: E402
from src import stage125_part3a_pilot_protocol as part3a  # noqa: E402
from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402


def _build():
    return p3b0.build_all(REPO_ROOT)


def _synthetic_valid_record() -> dict:
    return {
        "evidence_id": "ev_synth_001",
        "candidate_id": "cand_m2_equity_return_window",
        "source_id": "src_m2_tsetmc_market",
        "source_owner": "TSETMC",
        "source_url": "https://example.invalid/synthetic-only",
        "source_title": "Synthetic fixture",
        "source_identifier": "SYNTH-001",
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
        "published_at": "2025-12-31T00:00:00Z",
        "available_at": "2025-12-31T00:00:00Z",
        "raw_date_text": "1404/10/11",
        "calendar": "jalali",
        "timezone": "Asia/Tehran",
        "access_method": "synthetic_fixture",
        "authentication_required": False,
        "response_status_evidence": "synthetic",
        "local_snapshot_path": "synthetic/snap.bin",
        "snapshot_sha256": "a" * 64,
        "revision_status": "initial",
        "license_or_usage_notes": "synthetic test only",
        "reviewer_status": "synthetic",
        "failure_reason": "",
    }


@pytest.fixture
def schema_and_maps():
    schema = p3b0.load_frozen_evidence_schema(REPO_ROOT)
    return {
        "schema": schema,
        "candidate_source_map": p3b0.load_candidate_source_map(REPO_ROOT),
        "source_registry": p3b0.load_source_registry(REPO_ROOT),
    }


# --------------------------------------------------------------------------- #
# Baseline / frozen inputs
# --------------------------------------------------------------------------- #

def test_baseline_commit_ancestry_chain():
    p3b0.verify_baseline_commit(str(REPO_ROOT))


def test_frozen_input_hashes_verified():
    hashes = p3b0.verify_frozen_input_hashes(REPO_ROOT)
    assert len(hashes) == len(p3b0.FROZEN_INPUT_PATHS)


def test_build_all_qc_passes():
    result = _build()
    assert result["qc"]["all_pass"] is True
    assert result["qc"]["failed_count"] == 0


# --------------------------------------------------------------------------- #
# Evidence schema validator
# --------------------------------------------------------------------------- #

def test_schema_valid_synthetic_record(schema_and_maps):
    p3b0.validate_evidence_record_synthetic(
        _synthetic_valid_record(), **schema_and_maps,
    )


def test_missing_required_identifier(schema_and_maps):
    rec = _synthetic_valid_record()
    rec.pop("evidence_id")
    with pytest.raises(p3b0.EvidenceValidationError, match="missing non-nullable"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_wrong_type(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["authentication_required"] = "yes"
    with pytest.raises(p3b0.EvidenceValidationError, match="wrong type"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_unknown_candidate(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["candidate_id"] = "cand_unknown"
    with pytest.raises(p3b0.EvidenceValidationError, match="unknown candidate_id"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_unknown_source(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["source_id"] = "src_unknown"
    with pytest.raises(p3b0.EvidenceValidationError, match="unknown source_id"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_invalid_candidate_source_mapping(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["source_id"] = "src_m3_cbi_macro"
    with pytest.raises(p3b0.EvidenceValidationError, match="mapping mismatch"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_out_of_scope_candidate(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["candidate_id"] = "oos_order_book"
    rec["source_id"] = "src_m2_tsetmc_market"
    with pytest.raises(p3b0.EvidenceValidationError, match="out-of-scope"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_malformed_sha256(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["snapshot_sha256"] = "not-a-hash"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid SHA-256"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_invalid_datetime(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["published_at"] = "not-a-date"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid datetime"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_guessed_marker_rejected(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["raw_date_text"] = "inferred from memory"
    with pytest.raises(p3b0.EvidenceValidationError, match="guessed/inferred"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_real_evidence_prohibited_in_part3b0(schema_and_maps):
    with pytest.raises(p3b0.EvidenceValidationError, match="prohibited"):
        p3b0.validate_evidence_record(
            _synthetic_valid_record(), allow_real_evidence=False, **schema_and_maps,
        )


def test_unknown_field_rejected(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["extra_field"] = "x"
    with pytest.raises(p3b0.EvidenceValidationError, match="unknown fields"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


# --------------------------------------------------------------------------- #
# Gate engine (synthetic in-memory only)
# --------------------------------------------------------------------------- #

def test_g01_score_without_evidence_fails():
    assert p3b0.evaluate_score_without_evidence(3, False) == p3b0.GATE_FAIL


def test_g01_score_below_3_fails():
    assert p3b0.evaluate_g01(2) == p3b0.GATE_FAIL


def test_g01_score_equal_3_passes():
    assert p3b0.evaluate_g01(3) == p3b0.GATE_PASS


def test_g01_missing_score_unresolved():
    assert p3b0.evaluate_g01(None) == p3b0.GATE_UNRESOLVED


def test_g01_score_4_with_other_gate_failing():
    ctx = {
        "accessibility_score": 4,
        "evidence_captured": True,
        "authoritative_source": False,
        "reproducible_retrieval": True,
        "published_at": "2025-01-01T00:00:00Z",
        "available_at": "2025-01-01T00:00:00Z",
        "quality_controls_met": True,
        "no_future_leakage": True,
    }
    statuses = p3b0.evaluate_candidate_gates(ctx)
    assert statuses["G01"] == p3b0.GATE_PASS
    assert statuses["G02"] == p3b0.GATE_FAIL
    assert statuses["G08"] == p3b0.GATE_FAIL


def test_missing_availability_time_unresolved():
    assert p3b0.evaluate_g06(None) == p3b0.GATE_UNRESOLVED


def test_future_target_year_leakage_fails():
    assert p3b0.evaluate_g07(False) == p3b0.GATE_FAIL


def test_g09_just_below_threshold_fails():
    pilot = {f"k{i}" for i in range(80)}
    usable = {f"k{i}" for i in range(63)}
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert p3b0.evaluate_g09(statuses, pilot, threshold=0.80) == p3b0.GATE_FAIL


def test_g09_exactly_at_threshold_passes():
    pilot = {f"k{i}" for i in range(80)}
    usable = {f"k{i}" for i in range(64)}
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert p3b0.evaluate_g09(statuses, pilot, threshold=0.80) == p3b0.GATE_PASS


def test_g10_just_below_threshold_fails():
    pilot = {f"k{i}" for i in range(80)}
    usable_map = {key: {c: True for c in p3b0.BLOCK_CANDIDATES["M2"]}
                  for key in list(pilot)[:55]}
    assert p3b0.evaluate_g10(usable_map, pilot, threshold=0.70) == p3b0.GATE_FAIL


def test_g10_exactly_at_threshold_passes():
    pilot = {f"k{i}" for i in range(80)}
    usable_keys = list(pilot)[:56]
    usable_map = {
        key: {
            cand: True
            for block in p3b0.BLOCK_CANDIDATES.values()
            for cand in block
        }
        for key in usable_keys
    }
    assert p3b0.evaluate_g10(usable_map, pilot, threshold=0.70) == p3b0.GATE_PASS


def test_g11_count_2_fails():
    data = {"M2": {"1393": 2}, "M3": {"1393": 3}, "M4": {"1393": 3}}
    assert p3b0.evaluate_g11(data, minimum=3) == p3b0.GATE_FAIL


def test_g11_count_3_passes():
    data = {b: {str(y): 3 for y in range(1393, 1403)} for b in p3b0.BLOCK_CANDIDATES}
    assert p3b0.evaluate_g11(data, minimum=3) == p3b0.GATE_PASS


def test_g12_count_2_fails():
    data = {"M2": {"1393": 2}, "M3": {"1393": 3}, "M4": {"1393": 3}}
    assert p3b0.evaluate_g12(data, minimum=3) == p3b0.GATE_FAIL


def test_g12_count_3_passes():
    data = {b: {str(y): 3 for y in range(1393, 1403)} for b in p3b0.BLOCK_CANDIDATES}
    assert p3b0.evaluate_g12(data, minimum=3) == p3b0.GATE_PASS


def test_g13_79_pairs_fails():
    assert p3b0.evaluate_g13({f"k{i}" for i in range(79)}) == p3b0.GATE_FAIL


def test_g13_80_pairs_passes():
    assert p3b0.evaluate_g13({f"k{i}" for i in range(80)}) == p3b0.GATE_PASS


def test_g13_81_pairs_fails():
    assert p3b0.evaluate_g13({f"k{i}" for i in range(81)}) == p3b0.GATE_FAIL


def test_g14_altered_allocation_fails():
    bad_year = dict(lock.EXPECTED_YEAR_ALLOCATION)
    bad_year["1402"] = {"positive": 4, "negative": 4, "unknown": 0}
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=bad_year,
        post_evidence_substitution=False,
    ) == p3b0.GATE_FAIL


def test_g14_post_evidence_substitution_fails():
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=True,
    ) == p3b0.GATE_FAIL


def test_g14_locked_allocation_passes():
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=False,
    ) == p3b0.GATE_PASS


# --------------------------------------------------------------------------- #
# Immutable cache (temp dirs only)
# --------------------------------------------------------------------------- #

def test_cache_write_once_and_identical_no_op(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    data = b"synthetic payload"
    h1 = cache.put(data, {"note": "synthetic"})
    h2 = cache.put(data, {"note": "synthetic"})
    assert h1 == h2
    assert cache.get(h1) == data
    assert cache.entry_count() == 1


def test_cache_overwrite_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    data = b"first"
    h = cache.put(data)
    payload_path = cache._payload_path(h)
    payload_path.write_bytes(b"tampered")
    with pytest.raises(p3b0.ImmutableCacheError, match="collision"):
        cache.put(data)


def test_cache_path_traversal_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="invalid content hash"):
        cache._payload_path("../escape")


def test_cache_unknown_hash_fail_closed(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="unknown hash"):
        cache.get("b" * 64)


# --------------------------------------------------------------------------- #
# Network sentinel
# --------------------------------------------------------------------------- #

def test_network_attempt_blocked_before_connection():
    with p3b0.network_sentinel() as sentinel:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(p3b0.NetworkBlockedError):
                sock.connect(("127.0.0.1", 9))
        finally:
            sock.close()
        assert sentinel.calls_attempted == 1


def test_guard_network_sentinel_zero_calls():
    result = _build()
    assert result["guard_evidence"]["network_calls_attempted"] == 0
    assert result["guard_evidence"]["no_network_calls"] is True


# --------------------------------------------------------------------------- #
# Runner / templates
# --------------------------------------------------------------------------- #

def test_templates_header_only_zero_rows():
    result = _build()
    evidence = result["files"][p3b0.F_EVIDENCE_TEMPLATE]
    gate = result["files"][p3b0.F_GATE_TEMPLATE]
    assert len(list(csv.DictReader(io.StringIO(evidence)))) == 0
    assert len(list(csv.DictReader(io.StringIO(gate)))) == 0
    assert evidence.splitlines()[0] == ",".join(p3b0._EVIDENCE_HEADER)


def test_runner_check_mode_no_writes(tmp_path):
    out = tmp_path / "stage125"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    write_proc = subprocess.run(
        [sys.executable, str(ROOT / "run_stage125_part3b0.py"),
         "--output-dir", str(out), "--write"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert write_proc.returncode == 0, write_proc.stderr
    mtime_before = {
        p.name: p.stat().st_mtime for p in out.iterdir() if p.is_file()
    }
    check_proc = subprocess.run(
        [sys.executable, str(ROOT / "run_stage125_part3b0.py"),
         "--output-dir", str(out), "--check"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert check_proc.returncode == 0, check_proc.stderr
    for name, before in mtime_before.items():
        assert out / name
        assert (out / name).stat().st_mtime == before


def test_runner_idempotency(tmp_path):
    out = tmp_path / "stage125"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "run_stage125_part3b0.py"),
             "--output-dir", str(out), "--write"],
            capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, proc.stderr
    hashes = {
        p.name: p3b0.sha256_file(p)
        for p in sorted(out.iterdir()) if p.is_file()
    }
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_stage125_part3b0.py"),
         "--output-dir", str(out), "--write"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    hashes2 = {
        p.name: p3b0.sha256_file(p)
        for p in sorted(out.iterdir()) if p.is_file()
    }
    assert hashes == hashes2


def test_qc_assertions_evidence_backed():
    result = _build()
    names = {a["assertion"]: a for a in result["qc"]["assertions"]}
    for key in (
        "part3b0_readiness_true",
        "part3b_started_false",
        "evidence_collected_false",
        "real_evidence_record_count_zero",
        "network_calls_attempted_zero",
    ):
        assert names[key]["status"] == "PASS"
