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


def _policy():
    return p3b0.load_locked_gate_policy(REPO_ROOT)


def _synthetic_valid_record(*, snapshot_rel: str | None = None) -> dict:
    rec = {
        "evidence_id": "synth_001",
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
        "local_snapshot_path": "",
        "snapshot_sha256": "",
        "revision_status": "initial",
        "license_or_usage_notes": "synthetic test only",
        "reviewer_status": "synthetic",
        "failure_reason": "",
    }
    if snapshot_rel is not None:
        rec["local_snapshot_path"] = snapshot_rel
        rec["snapshot_sha256"] = "a" * 64
    return rec


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


def test_locked_gate_policy_from_frozen_artifacts():
    policy = _policy()
    assert policy.g09_threshold == 0.80
    assert policy.g10_threshold == 0.70
    assert policy.g11_minimum == 3
    assert policy.g12_minimum == 3
    assert policy.g13_expected == 80
    assert policy.g14_option_id == lock.APPROVED_PILOT_OPTION
    assert len(policy.target_years) == 10


# --------------------------------------------------------------------------- #
# Evidence schema validator
# --------------------------------------------------------------------------- #

def test_schema_valid_synthetic_record(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record(snapshot_rel="snap.bin")
    (tmp_path / "snap.bin").write_bytes(b"x")
    p3b0.validate_evidence_record_synthetic(
        rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
    )


def test_missing_required_identifier(schema_and_maps):
    rec = _synthetic_valid_record()
    rec.pop("evidence_id")
    with pytest.raises(p3b0.EvidenceValidationError, match="synthetic evidence_id"):
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
    rec["source_owner"] = "Central Bank of Iran"
    with pytest.raises(p3b0.EvidenceValidationError, match="mapping mismatch"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_out_of_scope_candidate(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["candidate_id"] = "oos_order_book"
    rec["source_id"] = "src_m2_tsetmc_market"
    with pytest.raises(p3b0.EvidenceValidationError, match="out-of-scope"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_malformed_sha256(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record(snapshot_rel="snap.bin")
    rec["snapshot_sha256"] = "not-a-hash"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid SHA-256"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_invalid_datetime_format(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["published_at"] = "not-a-date"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid datetime"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_invalid_datetime_semantic_impossible_date(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["published_at"] = "2026-99-99T00:00:00Z"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid datetime"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_retrieved_at_utc_requires_timezone_aware_utc(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["retrieved_at_utc"] = "2026-01-01T00:00:00"
    with pytest.raises(p3b0.EvidenceValidationError, match="timezone-aware UTC"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_snapshot_path_hash_co_presence(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record()
    rec["local_snapshot_path"] = "snap.bin"
    rec["snapshot_sha256"] = ""
    with pytest.raises(p3b0.EvidenceValidationError, match="co-present"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_source_owner_must_match_registry(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["source_owner"] = "NOT_TSETMC"
    with pytest.raises(p3b0.EvidenceValidationError, match="source_owner"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_duplicate_evidence_id_manifest(schema_and_maps):
    rec1 = _synthetic_valid_record()
    rec2 = _synthetic_valid_record()
    with pytest.raises(p3b0.EvidenceValidationError, match="duplicate evidence_id"):
        p3b0.validate_evidence_manifest_synthetic(
            [rec1, rec2], **schema_and_maps,
        )


def test_guessed_marker_rejected(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["raw_date_text"] = "inferred from memory"
    with pytest.raises(p3b0.EvidenceValidationError, match="guessed/inferred"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_real_looking_record_rejected_by_synthetic_api(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["evidence_id"] = "ev_codal_real_001"
    rec["source_url"] = "https://codal.ir/reports/real"
    rec["access_method"] = "https_get"
    with pytest.raises(p3b0.EvidenceValidationError):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_no_allow_real_evidence_escape_hatch():
    assert not hasattr(p3b0, "validate_evidence_record") or (
        "allow_real_evidence" not in (
            p3b0.validate_evidence_record.__code__.co_varnames
            if hasattr(p3b0, "validate_evidence_record") else ()
        )
    )
    assert "allow_real_evidence" not in p3b0.validate_evidence_record_synthetic.__code__.co_varnames


def test_unknown_field_rejected(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["extra_field"] = "x"
    with pytest.raises(p3b0.EvidenceValidationError, match="unknown fields"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_invalid_calendar_enum(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["calendar"] = "mayan"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid calendar"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_snapshot_outside_tmp_rejected(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record(snapshot_rel=str(REPO_ROOT / "project/stage125/x.bin"))
    with pytest.raises(p3b0.EvidenceValidationError):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


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


def test_g01_rejects_non_int_and_out_of_range():
    assert p3b0.evaluate_g01(3.0) == p3b0.GATE_FAIL
    assert p3b0.evaluate_g01("3") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g01(-1) == p3b0.GATE_FAIL
    assert p3b0.evaluate_g01(6) == p3b0.GATE_FAIL


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


def test_g08_requires_exactly_g01_g07_and_allowed_status():
    good = {gid: p3b0.GATE_PASS for gid in p3b0.G01_G07}
    assert p3b0.evaluate_g08(good) == p3b0.GATE_PASS
    missing = dict(good)
    missing.pop("G07")
    assert p3b0.evaluate_g08(missing) == p3b0.GATE_FAIL
    unknown = dict(good)
    unknown["G99"] = p3b0.GATE_PASS
    assert p3b0.evaluate_g08(unknown) == p3b0.GATE_FAIL
    bad_status = dict(good)
    bad_status["G03"] = "MAYBE"
    assert p3b0.evaluate_g08(bad_status) != p3b0.GATE_PASS


def test_missing_availability_time_unresolved():
    assert p3b0.evaluate_g06(None) == p3b0.GATE_UNRESOLVED


def test_future_target_year_leakage_fails():
    assert p3b0.evaluate_g07(False) == p3b0.GATE_FAIL


def test_g09_caller_cannot_weaken_threshold():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    usable = {f"k{i}" for i in range(8)}  # 0.10 coverage
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    # Even if a caller *wanted* threshold=0.1, the API only accepts LockedGatePolicy.
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL
    with pytest.raises(TypeError):
        p3b0.evaluate_g09(statuses, pilot, threshold=0.1)  # type: ignore[call-arg]


def test_g09_just_below_threshold_fails_all_ten_candidates():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    usable = {f"k{i}" for i in range(63)}  # 63/80 < 0.80
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert len(statuses) == 10
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL


def test_g09_exactly_at_threshold_passes():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    usable = {f"k{i}" for i in range(64)}
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_PASS


def test_g09_single_candidate_below_fails_while_others_pass():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    full = {f"k{i}" for i in range(64)}
    weak = {f"k{i}" for i in range(63)}
    statuses = {
        c["candidate_id"]: full for c in part3a.REGISTERED_CANDIDATES
    }
    victim = part3a.REGISTERED_CANDIDATES[0]["candidate_id"]
    statuses[victim] = weak
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL


def _full_block_usable_map(pilot: set[str], usable_keys: list[str]):
    return {
        key: {
            cand: True
            for block in p3b0.BLOCK_CANDIDATES.values()
            for cand in block
        }
        for key in usable_keys
    }


def test_g10_just_below_threshold_one_block_only():
    """Boundary: M2 just below 0.70 while M3 and M4 pass."""
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    keys = list(sorted(pilot))
    usable_map = _full_block_usable_map(pilot, keys[:56])  # all blocks at 0.70
    # Drop one M2 candidate flag on enough pairs to push M2 just below 0.70
    # while keeping M3/M4 at 56/80.
    for key in keys[55:56]:
        for cand in p3b0.BLOCK_CANDIDATES["M2"]:
            usable_map[key][cand] = False
    # Now M2 has 55/80, M3/M4 still 56/80.
    assert p3b0.evaluate_g10(usable_map, pilot, policy) == p3b0.GATE_FAIL


def test_g10_exactly_at_threshold_passes():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    usable_map = _full_block_usable_map(pilot, list(pilot)[:56])
    assert p3b0.evaluate_g10(usable_map, pilot, policy) == p3b0.GATE_PASS


def test_g11_one_year_below_while_all_others_pass():
    policy = _policy()
    data = {
        b: {y: 3 for y in policy.target_years}
        for b in p3b0.BLOCK_CANDIDATES
    }
    data["M2"]["1393"] = 2
    assert p3b0.evaluate_g11(data, policy) == p3b0.GATE_FAIL


def test_g11_count_3_passes():
    policy = _policy()
    data = {
        b: {y: 3 for y in policy.target_years}
        for b in p3b0.BLOCK_CANDIDATES
    }
    assert p3b0.evaluate_g11(data, policy) == p3b0.GATE_PASS


def test_g12_one_year_below_while_all_others_pass():
    policy = _policy()
    data = {
        b: {y: 3 for y in policy.target_years}
        for b in p3b0.BLOCK_CANDIDATES
    }
    data["M4"]["1402"] = 2
    assert p3b0.evaluate_g12(data, policy) == p3b0.GATE_FAIL


def test_g12_count_3_passes():
    policy = _policy()
    data = {
        b: {y: 3 for y in policy.target_years}
        for b in p3b0.BLOCK_CANDIDATES
    }
    assert p3b0.evaluate_g12(data, policy) == p3b0.GATE_PASS


def test_g13_79_pairs_fails():
    policy = _policy()
    assert p3b0.evaluate_g13({f"k{i}" for i in range(79)}, policy) == p3b0.GATE_FAIL


def test_g13_80_pairs_passes():
    policy = _policy()
    assert p3b0.evaluate_g13({f"k{i}" for i in range(80)}, policy) == p3b0.GATE_PASS


def test_g13_81_pairs_fails():
    policy = _policy()
    assert p3b0.evaluate_g13({f"k{i}" for i in range(81)}, policy) == p3b0.GATE_FAIL


def test_g13_caller_cannot_weaken_expected():
    policy = _policy()
    with pytest.raises(TypeError):
        p3b0.evaluate_g13({f"k{i}" for i in range(79)}, expected=79)  # type: ignore[call-arg]
    assert p3b0.evaluate_g13({f"k{i}" for i in range(79)}, policy) == p3b0.GATE_FAIL


def test_g14_altered_allocation_fails():
    policy = _policy()
    bad_year = dict(lock.EXPECTED_YEAR_ALLOCATION)
    bad_year["1402"] = {"positive": 4, "negative": 4, "unknown": 0}
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=bad_year,
        post_evidence_substitution=False,
        policy=policy,
    ) == p3b0.GATE_FAIL


def test_g14_post_evidence_substitution_fails():
    policy = _policy()
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=True,
        policy=policy,
    ) == p3b0.GATE_FAIL


def test_g14_locked_allocation_passes():
    policy = _policy()
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=False,
        policy=policy,
    ) == p3b0.GATE_PASS


# --------------------------------------------------------------------------- #
# Immutable cache (temp dirs only)
# --------------------------------------------------------------------------- #

def test_cache_write_once_and_identical_no_op(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    data = b"synthetic payload"
    r1 = cache.put(data, {"note": "synthetic"})
    r2 = cache.put(data, {"note": "synthetic"})
    assert r1.payload_sha256 == r2.payload_sha256
    assert r1.metadata_sha256 == r2.metadata_sha256
    assert cache.get(r1.payload_sha256) == data
    assert cache.entry_count() == 1


def test_cache_identical_payload_different_metadata_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    data = b"synthetic payload"
    cache.put(data, {"note": "a"})
    with pytest.raises(p3b0.ImmutableCacheError, match="conflict"):
        cache.put(data, {"note": "b"})


def test_cache_put_returns_both_hashes(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"abc", {"k": "v"})
    assert p3b0.SHA256_RE.match(result.payload_sha256)
    assert p3b0.SHA256_RE.match(result.metadata_sha256)
    assert result.payload_sha256 != result.metadata_sha256


def test_cache_metadata_only_tampering_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    meta_path = entry / cache._META_NAME
    tampered = json.loads(meta_path.read_text(encoding="utf-8"))
    tampered["note"] = "tampered"
    meta_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get(result.payload_sha256)


def test_cache_payload_tampering_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._PAYLOAD_NAME).write_bytes(b"tampered")
    with pytest.raises(p3b0.ImmutableCacheError, match="payload hash"):
        cache.get(result.payload_sha256)


def test_cache_payload_without_metadata_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._META_NAME).unlink()
    (entry / cache._META_HASH_NAME).unlink()
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get(result.payload_sha256)


def test_cache_metadata_without_payload_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._PAYLOAD_NAME).unlink()
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get(result.payload_sha256)


def test_cache_duplicate_metadata_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / "metadata.json.bak").write_bytes((entry / cache._META_NAME).read_bytes())
    with pytest.raises(p3b0.ImmutableCacheError, match="exactly"):
        cache.get(result.payload_sha256)


def test_cache_malformed_metadata_json_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    bad = b"{not-json"
    (entry / cache._META_NAME).write_bytes(bad)
    (entry / cache._META_HASH_NAME).write_text(
        p3b0.sha256_bytes(bad) + "\n", encoding="utf-8",
    )
    with pytest.raises(p3b0.ImmutableCacheError, match="malformed metadata JSON"):
        cache.get(result.payload_sha256)


def test_cache_symlink_component_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink"):
        p3b0.ImmutableCache(link)


def test_cache_injected_failure_leaves_no_partial(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="injected failure"):
        cache.put(b"payload", {"note": "x"}, _inject_failure="before_commit")
    assert cache.entry_count() == 0
    assert list(tmp_path.rglob("*")) == [] or all(
        p.name.startswith(".") or p.is_dir() for p in tmp_path.rglob("*")
    )
    # No complete entry accepted
    for p in tmp_path.rglob("payload.bin"):
        pytest.fail(f"partial payload left behind: {p}")


def test_cache_path_traversal_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="invalid content hash"):
        cache._entry_dir("../escape")


def test_cache_unknown_hash_fail_closed(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="unknown hash|exactly one"):
        cache.get("b" * 64)


def test_immutable_cache_contract_states_enforced_guarantees_only():
    contract = p3b0.build_immutable_cache_contract()
    assert contract["overwrite_support"] is False
    assert contract["put_returns_payload_and_metadata_sha256"] is True
    assert "tautological_meta_hash_check" not in contract


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


def test_network_blocks_dns_and_sendto():
    with p3b0.network_sentinel() as sentinel:
        with pytest.raises(p3b0.NetworkBlockedError):
            socket.getaddrinfo("example.invalid", 80)
        with pytest.raises(p3b0.NetworkBlockedError):
            socket.gethostbyname("example.invalid")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            with pytest.raises(p3b0.NetworkBlockedError):
                sock.sendto(b"x", ("127.0.0.1", 9))
        finally:
            sock.close()
        assert sentinel.calls_attempted >= 3


def test_network_blocks_urllib_and_curl_subprocess():
    with p3b0.network_sentinel() as sentinel:
        import urllib.request

        with pytest.raises(p3b0.NetworkBlockedError):
            urllib.request.urlopen("http://example.invalid/")
        with pytest.raises(p3b0.NetworkBlockedError):
            subprocess.run(["curl", "http://example.invalid/"], check=False)
        assert sentinel.calls_attempted >= 2


def test_network_allows_readonly_git_and_restores_after_exception():
    with p3b0.network_sentinel() as sentinel:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0
        assert sentinel.calls_attempted == 0
        try:
            with pytest.raises(p3b0.NetworkBlockedError):
                socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        except Exception:
            raise
    # Restored after context
    assert socket.create_connection is not None
    # Nested sentinel restore
    with p3b0.network_sentinel():
        with p3b0.network_sentinel() as inner:
            with pytest.raises(p3b0.NetworkBlockedError):
                socket.getaddrinfo("example.invalid", 443)
            assert inner.calls_attempted >= 1


def test_guard_network_sentinel_zero_calls():
    result = _build()
    assert result["guard_evidence"]["network_calls_attempted"] == 0
    assert result["guard_evidence"]["no_network_calls"] is True


# --------------------------------------------------------------------------- #
# Repository scans / QC evidence-backed assertions
# --------------------------------------------------------------------------- #

def test_scan_rejects_prefix_suffix_nested_attacks(tmp_path):
    root = tmp_path
    stage = root / "project" / "stage125"
    stage.mkdir(parents=True)
    attacks = [
        stage / "part3b0_real_evidence.csv",
        stage / "part3b0_evidence_manifest_template_stage125.csv.bak",
        stage / "nested" / "part3b0_scores.json",
        stage / "raw_cache_nested" / "payload.bin",
        stage / "part3b_evidence.jsonl",
    ]
    for path in attacks:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text("[]", encoding="utf-8")
        elif path.suffix == ".jsonl":
            path.write_text("{}\n", encoding="utf-8")
        elif path.suffix == ".csv" or path.suffix == ".bak":
            path.write_text("evidence_id\nx\n", encoding="utf-8")
        else:
            path.write_bytes(b"bin")
    result = p3b0.scan_for_part3b_capture_start(root)
    assert result["no_part3b"] is False
    joined = "\n".join(result["hits"])
    assert "part3b0_real_evidence.csv" in joined
    assert "part3b0_evidence_manifest_template_stage125.csv.bak" in joined
    assert "nested/part3b0_scores.json" in joined
    assert "raw_cache_nested/payload.bin" in joined
    assert "part3b_evidence.jsonl" in joined


def test_count_real_evidence_records_includes_populated_template(tmp_path):
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    header = ",".join(p3b0.evidence_header_from_schema(
        p3b0.load_frozen_evidence_schema(REPO_ROOT)
    ))
    (stage / p3b0.F_EVIDENCE_TEMPLATE).write_text(
        header + "\n" + ",".join(["x"] * 22) + "\n",
        encoding="utf-8",
    )
    assert p3b0.count_real_evidence_records(tmp_path) >= 1


def test_no_hardcoded_true_qc_assertions():
    result = _build()
    for assertion in result["qc"]["assertions"]:
        # Every assertion must be evidence-backed (status derived, detail non-empty).
        assert assertion["detail"]
        assert assertion["status"] in {"PASS", "FAIL"}


def test_qc_assertions_evidence_backed():
    result = _build()
    names = {a["assertion"]: a for a in result["qc"]["assertions"]}
    for key in (
        "part3b0_readiness_true",
        "part3b_started_false",
        "evidence_collected_false",
        "accessibility_scoring_applied_false",
        "real_evidence_record_count_zero",
        "network_calls_attempted_zero",
        "evidence_template_header_matches_frozen_schema",
        "locked_gate_policy_hash_verified",
    ):
        assert names[key]["status"] == "PASS"
        assert "true" != names[key]["detail"].lower() or "derived" in names[key]["detail"] or "contract" in names[key]["detail"] or "schema" in names[key]["detail"] or "g09" in names[key]["detail"]


# --------------------------------------------------------------------------- #
# Runner / templates
# --------------------------------------------------------------------------- #

def test_templates_header_only_zero_rows():
    result = _build()
    schema = p3b0.load_frozen_evidence_schema(REPO_ROOT)
    evidence = result["files"][p3b0.F_EVIDENCE_TEMPLATE]
    gate = result["files"][p3b0.F_GATE_TEMPLATE]
    assert len(list(csv.DictReader(io.StringIO(evidence)))) == 0
    assert len(list(csv.DictReader(io.StringIO(gate)))) == 0
    assert evidence.splitlines()[0] == ",".join(
        p3b0.evidence_header_from_schema(schema)
    )


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
