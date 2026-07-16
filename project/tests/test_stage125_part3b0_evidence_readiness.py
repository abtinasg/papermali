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


def _synthetic_valid_record(
    *,
    snapshot_rel: str | None = None,
    snapshot_bytes: bytes | None = None,
    snapshot_sha256: str | None = None,
) -> dict:
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
        payload = b"synthetic-snapshot-bytes" if snapshot_bytes is None else snapshot_bytes
        rec["local_snapshot_path"] = snapshot_rel
        rec["snapshot_sha256"] = (
            snapshot_sha256
            if snapshot_sha256 is not None
            else p3b0.sha256_bytes(payload)
        )
        rec["_snapshot_bytes"] = payload  # test helper only; stripped before validate
    return rec


def _write_snapshot(tmp_path: Path, rec: dict) -> dict:
    """Materialize snapshot bytes for a fixture record and drop helper key."""
    out = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
    rel = out.get("local_snapshot_path")
    if rel:
        payload = rec.get("_snapshot_bytes", b"synthetic-snapshot-bytes")
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return out


def _frozen_pilot(policy=None):
    policy = policy or _policy()
    return (
        set(policy.frozen_pilot_keys),
        set(policy.frozen_pilot_key_labels),
        set(policy.frozen_pilot_key_years),
    )


def _seal_gate_input(schema_and_maps, tmp_path, **gate_kwargs):
    rec = _write_snapshot(tmp_path, _synthetic_valid_record())
    evidence = p3b0.validate_and_seal_synthetic_evidence(
        rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
    )
    return p3b0.build_validated_gate_input(
        evidence,
        prediction_cutoff=gate_kwargs.pop(
            "prediction_cutoff", "2026-01-01T00:00:00Z",
        ),
        **gate_kwargs,
    )

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
    assert len(policy.frozen_pilot_keys) == 80
    assert p3b0.SHA256_RE.match(policy.source_pilot_pairs_sha256)


# --------------------------------------------------------------------------- #
# Evidence schema validator
# --------------------------------------------------------------------------- #

def test_schema_valid_synthetic_record(schema_and_maps, tmp_path):
    rec = _write_snapshot(tmp_path, _synthetic_valid_record(snapshot_rel="snap.bin"))
    p3b0.validate_evidence_record_synthetic(
        rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
    )


def test_snapshot_correct_bytes_and_hash_pass(schema_and_maps, tmp_path):
    payload = b"exact-bytes-ok"
    rec = _write_snapshot(
        tmp_path,
        _synthetic_valid_record(snapshot_rel="ok.bin", snapshot_bytes=payload),
    )
    p3b0.validate_evidence_record_synthetic(
        rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
    )


def test_snapshot_wrong_hash_fails(schema_and_maps, tmp_path):
    rec = _write_snapshot(
        tmp_path,
        _synthetic_valid_record(
            snapshot_rel="bad.bin",
            snapshot_bytes=b"bytes",
            snapshot_sha256="a" * 64,
        ),
    )
    with pytest.raises(p3b0.EvidenceValidationError, match="does not match"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_snapshot_nonexistent_fails(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record(snapshot_rel="missing.bin")
    rec = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
    with pytest.raises(p3b0.EvidenceValidationError, match="missing|unreadable"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_snapshot_mutated_after_record_creation_fails(schema_and_maps, tmp_path):
    rec = _write_snapshot(
        tmp_path,
        _synthetic_valid_record(snapshot_rel="mut.bin", snapshot_bytes=b"original"),
    )
    (tmp_path / "mut.bin").write_bytes(b"mutated-after-hash")
    with pytest.raises(p3b0.EvidenceValidationError, match="does not match"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_snapshot_symlink_rejected(schema_and_maps, tmp_path):
    real = tmp_path / "real.bin"
    real.write_bytes(b"payload")
    link = tmp_path / "link.bin"
    link.symlink_to(real)
    rec = _synthetic_valid_record(
        snapshot_rel="link.bin",
        snapshot_bytes=b"payload",
    )
    rec = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
    with pytest.raises(p3b0.EvidenceValidationError, match="symlink"):
        p3b0.validate_evidence_record_synthetic(
            rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
        )


def test_snapshot_intermediate_dir_symlink_rejected(schema_and_maps, tmp_path):
    real_dir = tmp_path / "realdir"
    real_dir.mkdir()
    (real_dir / "snap.bin").write_bytes(b"payload")
    link_dir = tmp_path / "linkdir"
    link_dir.symlink_to(real_dir, target_is_directory=True)
    rec = _synthetic_valid_record(
        snapshot_rel="linkdir/snap.bin",
        snapshot_bytes=b"payload",
    )
    rec = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
    with pytest.raises(p3b0.EvidenceValidationError, match="symlink"):
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
    rec = _write_snapshot(tmp_path, _synthetic_valid_record(snapshot_rel="snap.bin"))
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


def test_wrong_hash_with_b_x_bytes_no_longer_passes(schema_and_maps, tmp_path):
    """Regression: writing b'x' while supplying 'a'*64 must fail closed."""
    (tmp_path / "snap.bin").write_bytes(b"x")
    rec = _synthetic_valid_record(snapshot_rel="snap.bin")
    rec = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
    rec["snapshot_sha256"] = "a" * 64
    with pytest.raises(p3b0.EvidenceValidationError, match="does not match"):
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


def test_omission_of_nullable_field_fails(schema_and_maps):
    rec = _synthetic_valid_record()
    rec.pop("source_title")
    with pytest.raises(p3b0.EvidenceValidationError, match="omission not allowed"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_explicit_null_nullable_field_passes(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["source_title"] = None
    p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_exact_22_field_manifest_record_passes(schema_and_maps):
    schema = schema_and_maps["schema"]
    fields = p3b0.evidence_header_from_schema(schema)
    assert len(fields) == 22
    rec = _synthetic_valid_record()
    assert set(rec) == set(fields)
    p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_invalid_calendar_enum(schema_and_maps):
    rec = _synthetic_valid_record()
    rec["calendar"] = "mayan"
    with pytest.raises(p3b0.EvidenceValidationError, match="invalid calendar"):
        p3b0.validate_evidence_record_synthetic(rec, **schema_and_maps)


def test_snapshot_outside_tmp_rejected(schema_and_maps, tmp_path):
    rec = _synthetic_valid_record(
        snapshot_rel=str(REPO_ROOT / "project/stage125/x.bin"),
    )
    rec = {k: v for k, v in rec.items() if k != "_snapshot_bytes"}
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


def test_g01_score_4_with_other_gate_failing(schema_and_maps, tmp_path):
    gate_input = _seal_gate_input(
        schema_and_maps,
        tmp_path,
        accessibility_score=4,
        authoritative_source=False,
        reproducible_retrieval=True,
        quality_controls_met=True,
        prediction_cutoff="2026-01-01T00:00:00Z",
    )
    statuses = p3b0.evaluate_candidate_gates(gate_input)
    assert statuses["G01"] == p3b0.GATE_PASS
    assert statuses["G02"] == p3b0.GATE_FAIL
    assert statuses["G08"] == p3b0.GATE_FAIL


def test_evaluate_candidate_gates_rejects_raw_dict():
    with pytest.raises((TypeError, p3b0.QCFail)):
        p3b0.evaluate_candidate_gates({  # type: ignore[arg-type]
            "evidence_captured": True,
            "no_future_leakage": True,
            "authoritative_source": "false",
        })


def test_truthiness_coercion_rejected(schema_and_maps, tmp_path):
    rec = _write_snapshot(tmp_path, _synthetic_valid_record())
    evidence = p3b0.validate_and_seal_synthetic_evidence(
        rec, allowed_snapshot_root=tmp_path, **schema_and_maps,
    )
    with pytest.raises(p3b0.QCFail, match="bool"):
        p3b0.build_validated_gate_input(
            evidence,
            prediction_cutoff="2026-01-01T00:00:00Z",
            authoritative_source="false",  # type: ignore[arg-type]
        )
    assert p3b0.evaluate_g02("false") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g03("false") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g05("false") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g07("false") == p3b0.GATE_FAIL
    assert p3b0.evaluate_score_without_evidence(3, "false") == p3b0.GATE_FAIL


def test_g07_derived_from_cutoff_not_caller_bool(schema_and_maps, tmp_path):
    # available_at=2025-12-31, cutoff earlier => leakage FAIL even if a caller
    # would have claimed no_future_leakage=True.
    gate_input = _seal_gate_input(
        schema_and_maps,
        tmp_path,
        accessibility_score=4,
        authoritative_source=True,
        reproducible_retrieval=True,
        quality_controls_met=True,
        prediction_cutoff="2025-01-01T00:00:00Z",
    )
    statuses = p3b0.evaluate_candidate_gates(gate_input)
    assert statuses["G07"] == p3b0.GATE_FAIL
    # Same evidence with later cutoff passes G07.
    gate_ok = _seal_gate_input(
        schema_and_maps,
        tmp_path,
        accessibility_score=4,
        authoritative_source=True,
        reproducible_retrieval=True,
        quality_controls_met=True,
        prediction_cutoff="2026-01-01T00:00:00Z",
    )
    assert p3b0.evaluate_candidate_gates(gate_ok)["G07"] == p3b0.GATE_PASS


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


def test_g04_g06_malformed_dates_fail():
    assert p3b0.evaluate_g04("not-a-date", None) == p3b0.GATE_FAIL
    assert p3b0.evaluate_g04(None, "not-a-date") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g04("2026-99-99T00:00:00Z", None) == p3b0.GATE_FAIL
    assert p3b0.evaluate_g06("not-a-date") == p3b0.GATE_FAIL
    assert p3b0.evaluate_g06("2026-01-01T00:00:00Z") == p3b0.GATE_PASS
    assert p3b0.evaluate_g04(
        "2026-01-01T00:00:00Z", "2026-01-02T00:00:00+00:00",
    ) == p3b0.GATE_PASS


def test_future_target_year_leakage_fails():
    assert p3b0.evaluate_g07(False) == p3b0.GATE_FAIL
    assert p3b0.evaluate_g07_from_cutoff(
        "2026-06-01T00:00:00Z", "2026-01-01T00:00:00Z",
    ) == p3b0.GATE_FAIL


def test_forged_weakened_locked_policy_rejected():
    real = _policy()
    forged = p3b0.LockedGatePolicy(
        g09_threshold=0.1,
        g10_threshold=0.0,
        g11_minimum=0,
        g12_minimum=0,
        g13_expected=79,
        g14_option_id=real.g14_option_id,
        target_years=real.target_years,
        source_thresholds_sha256=real.source_thresholds_sha256,
        source_decision_lock_sha256=real.source_decision_lock_sha256,
        frozen_pilot_keys=real.frozen_pilot_keys,
        frozen_pilot_key_labels=real.frozen_pilot_key_labels,
        frozen_pilot_key_years=real.frozen_pilot_key_years,
        source_pilot_pairs_sha256=real.source_pilot_pairs_sha256,
        _seal=real._seal,
    )
    pilot, _, _ = _frozen_pilot(real)
    usable = {c["candidate_id"]: pilot for c in part3a.REGISTERED_CANDIDATES}
    with pytest.raises(p3b0.QCFail, match="LockedGatePolicy"):
        p3b0.evaluate_g09(usable, pilot, forged)
    with pytest.raises(p3b0.QCFail, match="LockedGatePolicy"):
        p3b0.require_sealed_gate_policy(forged)


def test_g09_caller_cannot_weaken_threshold():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    usable = set(list(sorted(pilot))[:8])  # 0.10 coverage
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL
    with pytest.raises(TypeError):
        p3b0.evaluate_g09(statuses, pilot, threshold=0.1)  # type: ignore[call-arg]


def test_g09_just_below_threshold_fails_all_ten_candidates():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    usable = set(list(sorted(pilot))[:63])  # 63/80 < 0.80
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert len(statuses) == 10
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL


def test_g09_exactly_at_threshold_passes():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    usable = set(list(sorted(pilot))[:64])
    statuses = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_PASS


def test_g09_single_candidate_below_fails_while_others_pass():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    keys = list(sorted(pilot))
    full = set(keys[:64])
    weak = set(keys[:63])
    statuses = {
        c["candidate_id"]: full for c in part3a.REGISTERED_CANDIDATES
    }
    victim = part3a.REGISTERED_CANDIDATES[0]["candidate_id"]
    statuses[victim] = weak
    assert p3b0.evaluate_g09(statuses, pilot, policy) == p3b0.GATE_FAIL


def test_g09_rejects_arbitrary_eighty_keys():
    policy = _policy()
    pilot = {f"k{i}" for i in range(80)}
    usable = {c["candidate_id"]: pilot for c in part3a.REGISTERED_CANDIDATES}
    with pytest.raises(p3b0.QCFail, match="pilot key identity"):
        p3b0.evaluate_g09(usable, pilot, policy)


def test_g09_rejects_one_replaced_key():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    mutated = set(pilot)
    victim = next(iter(mutated))
    mutated.remove(victim)
    mutated.add("REPLACED|0000")
    usable = {c["candidate_id"]: mutated for c in part3a.REGISTERED_CANDIDATES}
    with pytest.raises(p3b0.QCFail, match="pilot key identity"):
        p3b0.evaluate_g09(usable, mutated, policy)


def test_g09_rejects_duplicate_keys_list():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    dup = list(pilot) + [next(iter(pilot))]
    usable = {c["candidate_id"]: pilot for c in part3a.REGISTERED_CANDIDATES}
    with pytest.raises(p3b0.QCFail, match="duplicate"):
        p3b0.evaluate_g09(usable, dup, policy)


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
    pilot, _, _ = _frozen_pilot(policy)
    keys = list(sorted(pilot))
    usable_map = _full_block_usable_map(pilot, keys[:56])  # all blocks at 0.70
    for key in keys[55:56]:
        for cand in p3b0.BLOCK_CANDIDATES["M2"]:
            usable_map[key][cand] = False
    assert p3b0.evaluate_g10(usable_map, pilot, policy) == p3b0.GATE_FAIL


def test_g10_exactly_at_threshold_passes():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    usable_map = _full_block_usable_map(pilot, list(sorted(pilot))[:56])
    assert p3b0.evaluate_g10(usable_map, pilot, policy) == p3b0.GATE_PASS


def test_g10_rejects_string_usable_flag():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    key = next(iter(pilot))
    usable_map = {
        key: {p3b0.BLOCK_CANDIDATES["M2"][0]: "false"},  # type: ignore[dict-item]
    }
    with pytest.raises(p3b0.QCFail, match="exact bool"):
        p3b0.evaluate_g10(usable_map, pilot, policy)


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


def test_g11_rejects_float_count():
    policy = _policy()
    data = {
        b: {y: 3.0 for y in policy.target_years}  # type: ignore[dict-item]
        for b in p3b0.BLOCK_CANDIDATES
    }
    with pytest.raises(p3b0.QCFail, match="exact int"):
        p3b0.evaluate_g11(data, policy)


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
    pilot, _, _ = _frozen_pilot(policy)
    with pytest.raises(p3b0.QCFail, match="pilot key identity"):
        p3b0.evaluate_g13(set(list(pilot)[:79]), policy)


def test_g13_80_pairs_passes():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    assert p3b0.evaluate_g13(pilot, policy) == p3b0.GATE_PASS


def test_g13_81_pairs_fails():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    with pytest.raises(p3b0.QCFail, match="pilot key identity"):
        p3b0.evaluate_g13(set(pilot) | {"EXTRA|0000"}, policy)


def test_g13_caller_cannot_weaken_expected():
    policy = _policy()
    pilot, _, _ = _frozen_pilot(policy)
    with pytest.raises(TypeError):
        p3b0.evaluate_g13(set(list(pilot)[:79]), expected=79)  # type: ignore[call-arg]
    with pytest.raises(p3b0.QCFail, match="pilot key identity"):
        p3b0.evaluate_g13({f"k{i}" for i in range(80)}, policy)


def test_g14_altered_allocation_fails():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
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
        pilot_keys=pilot,
        key_labels=labels,
        key_years=years,
    ) == p3b0.GATE_FAIL


def test_g14_post_evidence_substitution_fails():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=True,
        policy=policy,
        pilot_keys=pilot,
        key_labels=labels,
        key_years=years,
    ) == p3b0.GATE_FAIL


def test_g14_locked_allocation_passes():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    assert p3b0.evaluate_g14(
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=False,
        policy=policy,
        pilot_keys=pilot,
        key_labels=labels,
        key_years=years,
    ) == p3b0.GATE_PASS


def test_g14_rejects_float_positive_count():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    with pytest.raises(p3b0.QCFail, match="exact int"):
        p3b0.evaluate_g14(
            option_id=lock.APPROVED_PILOT_OPTION,
            positive=39.0,  # type: ignore[arg-type]
            negative=41,
            unknown=0,
            year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
            post_evidence_substitution=False,
            policy=policy,
            pilot_keys=pilot,
            key_labels=labels,
            key_years=years,
        )


def test_g14_rejects_changed_class_labels():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    mutated = set()
    for key, label in labels:
        mutated.add((key, "positive" if label == "negative" else "negative"))
    with pytest.raises(p3b0.QCFail, match="label identity"):
        p3b0.evaluate_g14(
            option_id=lock.APPROVED_PILOT_OPTION,
            positive=39,
            negative=41,
            unknown=0,
            year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
            post_evidence_substitution=False,
            policy=policy,
            pilot_keys=pilot,
            key_labels=mutated,
            key_years=years,
        )


def test_g14_rejects_changed_target_years():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    mutated = {(k, "1393" if y != "1393" else "1402") for k, y in years}
    with pytest.raises(p3b0.QCFail, match="year identity"):
        p3b0.evaluate_g14(
            option_id=lock.APPROVED_PILOT_OPTION,
            positive=39,
            negative=41,
            unknown=0,
            year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
            post_evidence_substitution=False,
            policy=policy,
            pilot_keys=pilot,
            key_labels=labels,
            key_years=mutated,
        )


def test_composite_pilot_gate_evaluation_frozen_identity():
    policy = _policy()
    pilot, labels, years = _frozen_pilot(policy)
    keys = list(sorted(pilot))
    usable = set(keys[:64])
    usable_by_candidate = {
        c["candidate_id"]: usable for c in part3a.REGISTERED_CANDIDATES
    }
    usable_map = _full_block_usable_map(pilot, keys[:56])
    pos = {b: {y: 3 for y in policy.target_years} for b in p3b0.BLOCK_CANDIDATES}
    neg = {b: {y: 3 for y in policy.target_years} for b in p3b0.BLOCK_CANDIDATES}
    statuses = p3b0.evaluate_pilot_gates_synthetic(
        policy=policy,
        usable_by_candidate=usable_by_candidate,
        usable_by_pair_block=usable_map,
        usable_positive_by_block_year=pos,
        usable_negative_by_block_year=neg,
        pilot_keys=pilot,
        key_labels=labels,
        key_years=years,
        option_id=lock.APPROVED_PILOT_OPTION,
        positive=39,
        negative=41,
        unknown=0,
        year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
        post_evidence_substitution=False,
    )
    assert statuses["G09"] == p3b0.GATE_PASS
    assert statuses["G10"] == p3b0.GATE_PASS
    assert statuses["G11"] == p3b0.GATE_PASS
    assert statuses["G12"] == p3b0.GATE_PASS
    assert statuses["G13"] == p3b0.GATE_PASS
    assert statuses["G14"] == p3b0.GATE_PASS


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
    assert cache.get(r1.payload_sha256, r1.metadata_sha256) == data
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
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_metadata_and_local_seal_tampering_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    tampered = {"content_sha256": result.payload_sha256, "note": "evil"}
    meta_bytes = json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode()
    (entry / cache._META_NAME).write_bytes(meta_bytes)
    (entry / cache._META_HASH_NAME).write_text(
        p3b0.sha256_bytes(meta_bytes) + "\n", encoding="utf-8",
    )
    # Local seal matches tampered bytes, but original returned handle must fail.
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_wrong_expected_metadata_hash_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get(result.payload_sha256, "c" * 64)


def test_cache_original_handle_detects_every_mutation(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._PAYLOAD_NAME).write_bytes(b"mutated-payload")
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get(result.payload_sha256, result.metadata_sha256)
    # restore payload, mutate metadata only
    (entry / cache._PAYLOAD_NAME).write_bytes(b"payload")
    meta_path = entry / cache._META_NAME
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["note"] = "mutated"
    meta_path.write_text(json.dumps(meta, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_payload_tampering_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._PAYLOAD_NAME).write_bytes(b"tampered")
    with pytest.raises(p3b0.ImmutableCacheError, match="payload hash"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_payload_without_metadata_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._META_NAME).unlink()
    (entry / cache._META_HASH_NAME).unlink()
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_metadata_without_payload_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / cache._PAYLOAD_NAME).unlink()
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_duplicate_metadata_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    (entry / "metadata.json.bak").write_bytes((entry / cache._META_NAME).read_bytes())
    with pytest.raises(p3b0.ImmutableCacheError, match="exactly"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_malformed_metadata_json_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    entry = cache._entry_dir(result.payload_sha256)
    bad = b"{not-json"
    (entry / cache._META_NAME).write_bytes(bad)
    (entry / cache._META_HASH_NAME).write_text(
        p3b0.sha256_bytes(bad) + "\n", encoding="utf-8",
    )
    with pytest.raises(p3b0.ImmutableCacheError, match="malformed metadata JSON|metadata hash"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_orphan_staging_detected_with_real_name(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    parent = cache._entry_dir(result.payload_sha256).parent
    orphan = parent / f".staging-{result.payload_sha256[:16]}-{'a' * 32}"
    orphan.mkdir()
    (orphan / cache._PAYLOAD_NAME).write_bytes(b"partial")
    with pytest.raises(p3b0.ImmutableCacheError, match="orphan/partial staging"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_symlink_root_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink"):
        p3b0.ImmutableCache(link)


def test_cache_intermediate_shard_symlink_inside_root_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    entry = cache._entry_dir(result.payload_sha256)
    shard = entry.parent
    # Replace shard directory with symlink to another dir inside root.
    alt = tmp_path / "altshard"
    alt.mkdir()
    shutil = __import__("shutil")
    shutil.rmtree(shard)
    shard.symlink_to(alt, target_is_directory=True)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_intermediate_symlink_outside_root_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    cache = p3b0.ImmutableCache(cache_root)
    data = b"payload"
    content_hash = p3b0.sha256_bytes(data)
    shard = cache_root / content_hash[:2]
    shard.symlink_to(outside, target_is_directory=True)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink"):
        cache.put(data, {"note": "x"})


def test_cache_final_entry_file_symlink_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    entry = cache._entry_dir(result.payload_sha256)
    payload = entry / cache._PAYLOAD_NAME
    real = entry / "real.bin"
    real.write_bytes(b"payload")
    payload.unlink()
    payload.symlink_to(real)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink|exactly|failed to open"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_symlink_introduced_after_init_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    entry = cache._entry_dir(result.payload_sha256)
    meta = entry / cache._META_NAME
    backup = entry / "meta.bak"
    backup.write_bytes(meta.read_bytes())
    meta.unlink()
    meta.symlink_to(backup)
    with pytest.raises(p3b0.ImmutableCacheError, match="symlink|exactly|failed to open"):
        cache.get(result.payload_sha256, result.metadata_sha256)


def test_cache_injected_failure_leaves_no_partial(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="injected failure"):
        cache.put(b"payload", {"note": "x"}, _inject_failure="before_commit")
    assert cache.entry_count() == 0
    for p in tmp_path.rglob("payload.bin"):
        pytest.fail(f"partial payload left behind: {p}")


def test_cache_path_traversal_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="invalid content hash"):
        cache._entry_dir("../escape")


def test_cache_unknown_hash_fail_closed(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    with pytest.raises(p3b0.ImmutableCacheError, match="unknown hash|expected metadata"):
        cache.get("b" * 64, "c" * 64)


def test_immutable_cache_contract_states_enforced_guarantees_only():
    contract = p3b0.build_immutable_cache_contract()
    assert contract["overwrite_support"] is False
    assert contract["put_returns_payload_and_metadata_sha256"] is True
    assert contract["external_expected_metadata_sha256_required_on_get"] is True
    assert contract["external_cache_handle_required_for_secure_get"] is True
    assert contract["real_cache_handles_created_in_part3b0"] is False
    assert "tautological_meta_hash_check" not in contract


def test_cache_handle_serialize_restart_load_get(tmp_path):
    cache_a = p3b0.ImmutableCache(tmp_path / "a")
    result = cache_a.put(b"persist-me", {"note": "synthetic"})
    handle = p3b0.cache_handle_from_put_result("synth_cache_001", result)
    serialized = p3b0.serialize_cache_handle(handle)
    # Simulate process restart with a new cache object on the same root bytes.
    cache_b = p3b0.ImmutableCache(tmp_path / "a")
    loaded = p3b0.load_cache_handle(serialized)
    assert cache_b.get_by_handle(loaded) == b"persist-me"


def test_cache_handle_altered_payload_hash_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    handle = p3b0.cache_handle_from_put_result("synth_cache_001", result)
    bad = p3b0.CacheHandle(
        evidence_id=handle.evidence_id,
        payload_sha256="b" * 64,
        metadata_sha256=handle.metadata_sha256,
        cache_contract_version=handle.cache_contract_version,
        schema_version=handle.schema_version,
    )
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get_by_handle(bad)


def test_cache_handle_altered_metadata_hash_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    handle = p3b0.cache_handle_from_put_result("synth_cache_001", result)
    bad = p3b0.CacheHandle(
        evidence_id=handle.evidence_id,
        payload_sha256=handle.payload_sha256,
        metadata_sha256="c" * 64,
        cache_contract_version=handle.cache_contract_version,
        schema_version=handle.schema_version,
    )
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get_by_handle(bad)


def test_cache_handle_altered_serialization_fails(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "x"})
    handle = p3b0.cache_handle_from_put_result("synth_cache_001", result)
    serialized = p3b0.serialize_cache_handle(handle)
    tampered = serialized.replace(handle.metadata_sha256, "d" * 64)
    with pytest.raises(p3b0.ImmutableCacheError):
        loaded = p3b0.load_cache_handle(tampered)
        cache.get_by_handle(loaded)


def test_cache_local_dual_tamper_still_fails_with_handle(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    handle = p3b0.cache_handle_from_put_result("synth_cache_001", result)
    entry = cache._entry_dir(result.payload_sha256)
    tampered = {"content_sha256": result.payload_sha256, "note": "evil"}
    meta_bytes = json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode()
    (entry / cache._META_NAME).write_bytes(meta_bytes)
    (entry / cache._META_HASH_NAME).write_text(
        p3b0.sha256_bytes(meta_bytes) + "\n", encoding="utf-8",
    )
    with pytest.raises(p3b0.ImmutableCacheError, match="metadata hash"):
        cache.get_by_handle(handle)


def test_cache_cannot_read_securely_without_persisted_handle(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path)
    result = cache.put(b"payload", {"note": "orig"})
    # Knowing only the payload hash is insufficient without external metadata seal.
    with pytest.raises(p3b0.ImmutableCacheError, match="expected metadata|metadata"):
        cache.get(result.payload_sha256, "")
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get_by_handle("not-a-handle")  # type: ignore[arg-type]


def test_cache_handle_template_header_only_zero_rows():
    text = p3b0.build_cache_handle_template_csv()
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows == []
    assert "evidence_id" in text.splitlines()[0]
    assert "metadata_sha256" in text.splitlines()[0]


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


def test_subprocess_default_deny_no_child_process_launched():
    launched: list[tuple] = []

    def _boom_run(*args, **kwargs):
        launched.append(("run", args, kwargs))
        raise AssertionError("child process launched")

    class _BoomPopen:
        def __init__(self, *args, **kwargs):
            launched.append(("popen", args, kwargs))
            raise AssertionError("child process launched")

    cases = [
        (["bash", "-c", "echo hi"], {}),
        (["python", "-c", "print(1)"], {}),
        (["/usr/bin/curl", "http://example.invalid/"], {}),
        ([], {"args": ["wget", "http://example.invalid/"]}),
        (["echo hi"], {"shell": True}),
        ("echo hi", {}),
        (["git", "-C", str(REPO_ROOT), "-c", "alias.x=!touch /tmp/x", "x"], {}),
        (["git", "-C", str(REPO_ROOT), "log", "--ext-diff"], {}),
        (["git", "-C", str(REPO_ROOT), "show", "--textconv", "HEAD"], {}),
        (["/usr/bin/git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], {}),
    ]
    with p3b0.network_sentinel() as sentinel:
        saved_run = sentinel._orig_subprocess_run
        saved_popen = sentinel._orig_subprocess_popen
        sentinel._orig_subprocess_run = _boom_run  # type: ignore[method-assign]
        sentinel._orig_subprocess_popen = _BoomPopen  # type: ignore[assignment]
        try:
            for args, kwargs in cases:
                with pytest.raises(p3b0.NetworkBlockedError):
                    if isinstance(args, str):
                        subprocess.run(args, **kwargs)
                    elif args:
                        subprocess.run(args, **kwargs)
                    else:
                        subprocess.run(**kwargs)
                with pytest.raises(p3b0.NetworkBlockedError):
                    if isinstance(args, str):
                        subprocess.Popen(args, **kwargs)
                    elif args:
                        subprocess.Popen(args, **kwargs)
                    else:
                        subprocess.Popen(**kwargs)
            assert launched == []
            assert sentinel.calls_attempted >= len(cases)
        finally:
            # Restore originals before context exit so sentinel.restore() is clean.
            sentinel._orig_subprocess_run = saved_run
            sentinel._orig_subprocess_popen = saved_popen


def test_os_system_popen_spawn_denied_no_child_process():
    launched: list[str] = []

    def _boom_system(*args, **kwargs):
        launched.append("system")
        raise AssertionError("os.system launched")

    def _boom_popen(*args, **kwargs):
        launched.append("popen")
        raise AssertionError("os.popen launched")

    def _make_boom_spawn(name: str):
        def _boom(*args, **kwargs):
            launched.append(name)
            raise AssertionError(f"os.{name} launched")
        return _boom

    with p3b0.network_sentinel() as sentinel:
        saved_system = sentinel._orig_os_system
        saved_popen = sentinel._orig_os_popen
        saved_spawns = dict(sentinel._orig_os_spawns)
        sentinel._orig_os_system = _boom_system  # type: ignore[method-assign]
        sentinel._orig_os_popen = _boom_popen  # type: ignore[method-assign]
        for name in list(sentinel._orig_os_spawns):
            sentinel._orig_os_spawns[name] = _make_boom_spawn(name)
        try:
            with pytest.raises(p3b0.NetworkBlockedError):
                os.system("echo blocked")
            with pytest.raises(p3b0.NetworkBlockedError):
                os.popen("echo blocked")
            for name in saved_spawns:
                fn = getattr(os, name)
                with pytest.raises(p3b0.NetworkBlockedError):
                    if name.endswith("l") or name.endswith("le") or name.endswith("lp") or name.endswith("lpe"):
                        # spawnl family: mode, file, *args
                        if "e" in name[-2:]:
                            fn(os.P_WAIT, "/bin/echo", "echo", "hi", {"PATH": "/bin"})
                        else:
                            fn(os.P_WAIT, "/bin/echo", "echo", "hi")
                    else:
                        # spawnv family
                        if name.endswith("e"):
                            fn(os.P_WAIT, "/bin/echo", ["echo", "hi"], {"PATH": "/bin"})
                        else:
                            fn(os.P_WAIT, "/bin/echo", ["echo", "hi"])
            assert launched == []
            assert sentinel.calls_attempted >= 2 + len(saved_spawns)
        finally:
            sentinel._orig_os_system = saved_system
            sentinel._orig_os_popen = saved_popen
            sentinel._orig_os_spawns = saved_spawns


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


def test_content_aware_qc_detects_innocuous_filenames(tmp_path):
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    (stage / "notes.csv").write_text(
        "accessibility_score,decision_status\n4,admitted\n",
        encoding="utf-8",
    )
    (stage / "results.json").write_text(
        json.dumps([{"evidence_id": "ev1", "accessibility_score": 5}]),
        encoding="utf-8",
    )
    assert p3b0.count_accessibility_scores(tmp_path) >= 2
    assert p3b0.count_candidate_decisions(tmp_path) >= 1
    scan = p3b0.scan_for_part3b_capture_start(tmp_path)
    assert scan["no_part3b"] is False
    joined = "\n".join(scan["hits"])
    assert "notes.csv" in joined
    assert "results.json" in joined


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
    handle = result["files"][p3b0.F_CACHE_HANDLE_TEMPLATE]
    assert len(list(csv.DictReader(io.StringIO(evidence)))) == 0
    assert len(list(csv.DictReader(io.StringIO(gate)))) == 0
    assert len(list(csv.DictReader(io.StringIO(handle)))) == 0
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
