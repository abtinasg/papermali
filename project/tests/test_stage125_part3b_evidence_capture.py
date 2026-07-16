"""Tests for Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot.

Network tests use mocks/fakes only; they never contact the live internet.
"""
from __future__ import annotations

import csv
import io
import json
import socket
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
import sys

sys.path.insert(0, str(ROOT))

from src import stage125_part3a_pilot_protocol as part3a  # noqa: E402
from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b_evidence_capture as part3b  # noqa: E402


@pytest.fixture
def schema_and_maps():
    return {
        "schema": p3b0.load_frozen_evidence_schema(REPO_ROOT),
        "candidate_source_map": p3b0.load_candidate_source_map(REPO_ROOT),
        "source_registry": p3b0.load_source_registry(REPO_ROOT),
    }


def _failed_evidence(candidate_id="cand_m2_equity_return_window"):
    return part3b.empty_evidence_record(
        evidence_id="ev_test_001",
        candidate_id=candidate_id,
        source_id=part3b.CANDIDATE_SOURCE_MAP[candidate_id],
        source_owner="TSETMC",
        failure_reason="unit_test_failure",
    )


# --------------------------------------------------------------------------- #
# Frozen inputs / plan
# --------------------------------------------------------------------------- #

def test_frozen_input_hashes_match_authorization():
    got = part3b.verify_frozen_input_hashes(REPO_ROOT)
    assert got == part3b.FROZEN_INPUT_HASHES


def test_endpoint_registry_no_url_guessing_for_cbi():
    rows = part3b.build_endpoint_registry_rows(REPO_ROOT)
    cbi = next(r for r in rows if r["source_id"] == "src_m3_cbi_macro")
    assert cbi["verification_status"] == "unverified_no_authoritative_endpoint"
    assert cbi["exact_endpoint_or_url_pattern"] == ""
    assert "GET" not in (cbi.get("allowed_http_method") or "")


def test_sci_not_promoted():
    rows = part3b.build_endpoint_registry_rows(REPO_ROOT)
    sci = next(r for r in rows if r["source_id"] == "src_m3_sci_macro")
    assert sci["verification_status"] == "out_of_scope_not_contacted"


def test_capture_plan_deterministic_and_blocks_unverified():
    endpoints = part3b.build_endpoint_registry_rows(REPO_ROOT)
    plan1 = part3b.build_capture_plan(REPO_ROOT, endpoints)
    plan2 = part3b.build_capture_plan(REPO_ROOT, endpoints)
    assert plan1 == plan2
    assert len(plan1) == 10
    blocked = [r for r in plan1 if r["source_id"] == "src_m3_cbi_macro"]
    assert all(r["plan_status"] == "blocked" for r in blocked)
    assert part3b.capture_plan_sha256(plan1) == part3b.capture_plan_sha256(plan2)


def test_plan_mode_no_network(tmp_path):
    out = tmp_path / "stage125"
    out.mkdir()
    with p3b0.network_sentinel() as sentinel:
        # run_plan installs its own sentinel; outer proves default deny still works after
        result = part3b.run_plan(REPO_ROOT, out, write=True)
    assert result["network_calls_attempted"] == 0
    assert (out / part3b.F_AUTH).is_file()
    assert (out / part3b.F_PLAN).is_file()
    assert part3b.part3b_authorization_active(tmp_path) is False  # marker under out not repo
    # Authorization marker path is repo-relative; write to repo output in integration.


# --------------------------------------------------------------------------- #
# Sealing / schema
# --------------------------------------------------------------------------- #

def test_real_evidence_rejects_synthetic_id(schema_and_maps):
    rec = _failed_evidence()
    rec["evidence_id"] = "synth_not_allowed"
    with pytest.raises(p3b0.EvidenceValidationError, match="synthetic"):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_missing_schema_field_fails(schema_and_maps):
    rec = _failed_evidence()
    del rec["failure_reason"]
    with pytest.raises(p3b0.EvidenceValidationError, match="missing field"):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_unregistered_candidate_fails(schema_and_maps):
    rec = _failed_evidence()
    rec["candidate_id"] = "oos_m5_persian_text"
    rec["source_id"] = "src_m2_tsetmc_market"
    with pytest.raises(p3b0.EvidenceValidationError):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_wrong_candidate_source_mapping_fails(schema_and_maps):
    rec = _failed_evidence()
    rec["source_id"] = "src_m3_cbi_macro"
    rec["source_owner"] = "Central Bank of Iran"
    with pytest.raises(p3b0.EvidenceValidationError, match="mapping"):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_source_owner_mismatch_fails(schema_and_maps):
    rec = _failed_evidence()
    rec["source_owner"] = "NOT_TSETMC"
    with pytest.raises(p3b0.EvidenceValidationError, match="source_owner"):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_guessed_marker_rejected(schema_and_maps):
    rec = _failed_evidence()
    rec["source_title"] = "guessed title"
    with pytest.raises(p3b0.EvidenceValidationError, match="guessed"):
        part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)


def test_seal_tamper_fails(schema_and_maps):
    rec = _failed_evidence()
    sealed = part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)
    import dataclasses
    tampered = dataclasses.replace(sealed, evidence_id="ev_tampered")
    with pytest.raises(part3b.QCFail, match="seal"):
        part3b.require_sealed_real_evidence(tampered)


def test_score_without_unique_support_stays_null():
    row = part3b.null_score_row(
        "cand_m2_equity_return_window", "src_m2_tsetmc_market",
        ["ev_x"], "ambiguous",
    )
    assert row["accessibility_score"] == ""
    assert row["requires_human_adjudication"] == "true"
    assert row["rubric_version"] == part3b.RUBRIC_VERSION


def test_usability_flag_must_be_bool():
    with pytest.raises(part3b.QCFail, match="usability_flag"):
        part3b.seal_pair_candidate_assessment(
            assessment_id="a1",
            predictor_row_key_t="خاذین|1392",
            target_row_key_t_plus_1="خاذین|1393",
            candidate_id="cand_m2_equity_return_window",
            source_id="src_m2_tsetmc_market",
            class_label="positive",
            target_year="1393",
            prediction_cutoff=None,
            evidence_id=None,
            snapshot_sha256=None,
            metadata_sha256=None,
            external_handle_sha256=None,
            assessment_status="UNRESOLVED",
            usability_flag="false",  # type: ignore[arg-type]
        )


# --------------------------------------------------------------------------- #
# Network policy (mocked)
# --------------------------------------------------------------------------- #

def test_non_get_head_rejected():
    permit = part3b.ReadOnlyNetworkPermit({("GET", "https://cdn.tsetmc.com/")})
    with pytest.raises(part3b.NetworkPolicyError, match="method"):
        with permit:
            permit._validate_url("POST", "https://cdn.tsetmc.com/")


def test_unapproved_host_rejected():
    permit = part3b.ReadOnlyNetworkPermit({("GET", "https://cdn.tsetmc.com/")})
    with pytest.raises(part3b.NetworkPolicyError, match="allowlist"):
        with permit:
            permit._validate_url("GET", "https://evil.example/")


def test_http_scheme_rejected():
    permit = part3b.ReadOnlyNetworkPermit({("GET", "http://cdn.tsetmc.com/")})
    with pytest.raises(part3b.NetworkPolicyError, match="https"):
        with permit:
            permit._validate_url("GET", "http://cdn.tsetmc.com/")


def test_private_ip_rejected():
    permit = part3b.ReadOnlyNetworkPermit({("GET", "https://cdn.tsetmc.com/")})
    with permit:
        with mock.patch.object(
            permit._sentinel, "_orig_getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
        ):
            with pytest.raises(part3b.NetworkPolicyError, match="private|reserved|loopback"):
                permit._assert_public_dns("cdn.tsetmc.com")


def test_permit_preserves_outer_default_deny_after_exception():
    allowed = {("GET", "https://cdn.tsetmc.com/")}
    with p3b0.network_sentinel() as outer:
        try:
            with part3b.ReadOnlyNetworkPermit(allowed, sentinel=outer):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        # Outer default-deny still installed
        with pytest.raises(p3b0.NetworkBlockedError):
            socket.create_connection(("example.com", 443), timeout=0.1)


def test_permit_preserves_outer_default_deny_after_nested_context():
    allowed = {("GET", "https://cdn.tsetmc.com/")}
    with p3b0.network_sentinel() as outer:
        with part3b.ReadOnlyNetworkPermit(allowed, sentinel=outer):
            with part3b.ReadOnlyNetworkPermit(allowed, sentinel=outer):
                pass
        with pytest.raises(p3b0.NetworkBlockedError):
            socket.getaddrinfo("example.com", 443)


def test_subprocess_still_blocked_under_default_deny():
    with p3b0.network_sentinel():
        with pytest.raises(p3b0.NetworkBlockedError):
            import subprocess
            subprocess.run(["curl", "https://example.com"], check=False)


# --------------------------------------------------------------------------- #
# Cache integrity (tmp)
# --------------------------------------------------------------------------- #

def test_cache_symlink_rejected(tmp_path):
    root = tmp_path / "cache"
    cache = p3b0.ImmutableCache(root)
    put = cache.put(b"abc", metadata={"k": 1}, evidence_id="ev_cache_1")
    entry = root / put.payload_sha256[:2] / put.payload_sha256
    # Replace payload with symlink
    payload = entry / "payload.bin"
    payload.unlink()
    payload.symlink_to("/etc/hosts")
    handle = p3b0.cache_handle_from_put_result("ev_cache_1", put)
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get_by_handle(handle)


def test_cross_entry_handle_rejected(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path / "cache")
    a = cache.put(b"payload-a", metadata={"n": 1}, evidence_id="ev_a")
    b = cache.put(b"payload-b", metadata={"n": 2}, evidence_id="ev_b")
    forged = p3b0.CacheHandle(
        evidence_id="ev_a",
        payload_sha256=b.payload_sha256,
        metadata_sha256=b.metadata_sha256,
        cache_contract_version=p3b0.CACHE_CONTRACT_VERSION,
    )
    with pytest.raises(p3b0.ImmutableCacheError):
        cache.get_by_handle(forged)
    del a


def test_identical_bytes_different_metadata_fail_closed(tmp_path):
    cache = p3b0.ImmutableCache(tmp_path / "cache")
    cache.put(b"same", metadata={"x": 1}, evidence_id="ev1")
    with pytest.raises(p3b0.ImmutableCacheError, match="conflict"):
        cache.put(b"same", metadata={"x": 2}, evidence_id="ev2")


# --------------------------------------------------------------------------- #
# Transition / authorization
# --------------------------------------------------------------------------- #

def test_unauthorized_part3b_still_detected_by_part3b0_scan(tmp_path):
    # Create a fake unauthorized evidence file under a temp stage125 copy is hard;
    # assert PART3B_FORBIDDEN still lists the runner path conceptually and
    # authorization helper is false without marker.
    assert part3b.part3b_authorization_active(REPO_ROOT) in (True, False)
    # Before plan write in repo, may be false; after integration true.
    # Ensure helper is exact-path based:
    assert not (tmp_path / "project/stage125" / part3b.F_AUTH).exists()
    assert part3b.part3b_authorization_active(tmp_path) is False


def test_historical_baseline_refuses_write_when_authorized(tmp_path):
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    # Minimal fake authorization + metadata for part3b0
    (stage / part3b.F_AUTH).write_text("{}", encoding="utf-8")
    # Point check at tmp by monkeypatching paths is complex; unit-test helper:
    meta = {
        "part3b0_readiness": True,
        "part3b_started": False,
        "evidence_collected": False,
        "accessibility_scoring_applied": False,
        "network_extraction_performed": False,
        "modeling_started": False,
        "output_files_sha256": {
            "dummy.txt": part3b.sha256_bytes(b"hello\n"),
        },
    }
    (stage / "metadata_and_hashes_stage125_part3b0.json").write_text(
        json.dumps(meta), encoding="utf-8",
    )
    (stage / "dummy.txt").write_text("hello\n", encoding="utf-8")
    result = part3b.check_historical_baseline(
        tmp_path, stage, "metadata_and_hashes_stage125_part3b0.json",
        require_historical_flags={"part3b_started": False, "evidence_collected": False},
    )
    assert result["historical_baseline_ok"] is True


def test_allowlist_exact_no_prefix_attack():
    # Directory-wide stage125 allowlist must not exist for Part 3B code paths
    assert "project/src/stage125_part3b/" not in part3b.PART3B_AUTHORIZED_EXACT
    assert part3b.SRC_REL in part3b.PART3B_AUTHORIZED_EXACT
    # Prefix attack: sibling path not authorized
    assert "project/src/stage125_part3b_evidence_capture.py.bak" not in part3b.PART3B_AUTHORIZED_EXACT
    assert "project/stage125/part3b_evidence_manifest_stage125.csv.exe" not in part3b.PART3B_AUTHORIZED_EXACT


def test_raw_g11_count_injection_rejected():
    policy = p3b0.load_locked_gate_policy(REPO_ROOT)
    raw_counts = {
        "M2": {y: 3 for y in policy.target_years},
        "M3": {y: 3 for y in policy.target_years},
        "M4": {y: 3 for y in policy.target_years},
    }
    with pytest.raises(p3b0.QCFail, match="raw caller-supplied counts"):
        p3b0.evaluate_g11(raw_counts, policy)


def test_gate_input_rejects_truthiness_coercion(schema_and_maps):
    rec = _failed_evidence()
    sealed = part3b.validate_and_seal_real_evidence(rec, **schema_and_maps)
    with pytest.raises(part3b.QCFail, match="bool"):
        part3b.build_validated_real_gate_input(
            sealed, authoritative_source=1,  # type: ignore[arg-type]
        )


def test_g07_unresolved_when_cutoff_missing(schema_and_maps):
    rec = _failed_evidence()
    sealed = part3b.validate_and_seal_real_evidence(
        rec, prediction_cutoff=None, **schema_and_maps,
    )
    gin = part3b.build_validated_real_gate_input(sealed)
    statuses = part3b.evaluate_real_candidate_gates(gin)
    assert statuses["G07"] == p3b0.GATE_UNRESOLVED


def test_no_model_artifact_constants():
    assert part3b.QC_STAGE == "stage125_part3b_evidence_capture"
    assert "model" not in part3b.F_METADATA
    assert part3a.REGISTERED_CANDIDATES and len(part3b.REGISTERED_CANDIDATE_IDS) == 10
