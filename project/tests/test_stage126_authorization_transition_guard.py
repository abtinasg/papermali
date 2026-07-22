"""Fail-closed tests for the shared Stage126 authorization transition guard."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from src import stage126_authorization_transition_guard as guard

REPO_ROOT = Path(__file__).resolve().parents[2]


def _valid() -> dict:
    return guard.build_authorization_record()


def test_valid_record_passes_and_recomputes_sha():
    rec = _valid()
    out = guard.validate_authorization_record(rec)
    assert out is rec
    recomputed = guard.recompute_authorization_text_sha256(
        rec["authorization_text_fa"]
    )
    assert recomputed == guard.AUTHORIZATION_TEXT_SHA256
    assert recomputed == rec["authorization_text_sha256"]
    assert (
        hashlib.sha256(rec["authorization_text_fa"].encode("utf-8")).hexdigest()
        == guard.AUTHORIZATION_TEXT_SHA256
    )


def test_on_disk_record_loads_via_shared_validator():
    loaded = guard.load_authorization_record(REPO_ROOT)
    assert loaded["authorization_id"] == guard.AUTHORIZATION_ID
    assert guard.stage126_m1_development_authorized(REPO_ROOT) is True


def test_correct_hash_field_plus_mutated_persian_text_fails():
    rec = _valid()
    rec["authorization_text_fa"] = rec["authorization_text_fa"] + " "
    # Keep the hash field equal to the approved SHA — classic weak-check bypass.
    rec["authorization_text_sha256"] = guard.AUTHORIZATION_TEXT_SHA256
    with pytest.raises(guard.AuthorizationError):
        guard.validate_authorization_record(rec)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorization_id", "wrong_id"),
        ("authorizing_role", "not_the_data_owner"),
        ("research_action_id", "stage126-unauthorized"),
        ("authorization_date", "2099-01-01"),
        ("stage126_authorized", False),
        ("development_modeling_authorized", False),
        ("final_test_unlocked", True),
        ("final_test_access_authorized", True),
        ("final_test_evaluation_authorized", True),
        ("contract_change_authorized", True),
        ("m2_m3_m4_authorized", True),
        ("authorization_text_sha256", "0" * 64),
    ],
)
def test_required_field_mutation_fails(field, value):
    rec = _valid()
    rec[field] = value
    with pytest.raises(guard.AuthorizationError):
        guard.validate_authorization_record(rec)


def test_missing_required_field_fails():
    rec = _valid()
    del rec["research_action_id"]
    with pytest.raises(guard.AuthorizationError, match="missing required fields"):
        guard.validate_authorization_record(rec)


def test_malformed_json_fails(tmp_path):
    root = tmp_path
    path = root / guard.AUTHORIZATION_RECORD_REL
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(guard.AuthorizationError, match="malformed"):
        guard.load_authorization_record(root)
    assert guard.stage126_m1_development_authorized(root) is False


def test_missing_record_fails(tmp_path):
    with pytest.raises(guard.AuthorizationError, match="missing authorization"):
        guard.load_authorization_record(tmp_path)
    assert guard.stage126_m1_development_authorized(tmp_path) is False


def test_part4_and_part5_delegate_to_shared_guard():
    from src import stage125_part4_statistical_analysis_plan as part4
    from src import stage125_part5_readiness_closure as part5

    assert part4.stage126_m1_development_authorized(REPO_ROOT) is True
    assert part5.stage126_m1_development_authorized(REPO_ROOT) is True
    assert part4.STAGE126_M1_AUTHORIZATION_TEXT_SHA256 == (
        guard.AUTHORIZATION_TEXT_SHA256
    )
    assert part5.STAGE126_M1_AUTHORIZATION_TEXT_SHA256 == (
        guard.AUTHORIZATION_TEXT_SHA256
    )


def test_hash_field_trusted_alone_is_insufficient(tmp_path):
    """A record with the correct hash field but wrong text must never authorize."""
    rec = _valid()
    rec["authorization_text_fa"] = "مرحوم متن جعلی"
    rec["authorization_text_sha256"] = guard.AUTHORIZATION_TEXT_SHA256
    path = tmp_path / guard.AUTHORIZATION_RECORD_REL
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    assert guard.stage126_m1_development_authorized(tmp_path) is False
