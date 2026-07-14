"""Tests for Stage125 Part 3A — Accessibility & Pilot Protocol Lock.

All tests are read-only: they never modify the canonical repository files.
The canonical-repository-unchanged fixture (session-scoped, autouse) in
``test_canonical_repository_immutable.py`` guards against any accidental write.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3a_pilot_protocol as part3a  # noqa: E402

ALL_ROWS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_all_rows_stage124_gate_b.csv"
PAIRS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_one_year_ahead_stage124_gate_b.csv"
OUTPUT_DIR = ROOT / "stage125"


def _build():
    return part3a.build_all(REPO_ROOT, ALL_ROWS_PATH, PAIRS_PATH)


def _check_files(result):
    files = result["files"]
    for name, content in files.items():
        disk = OUTPUT_DIR / name
        assert disk.is_file(), f"missing output: {name}"
        on_disk = disk.read_text(encoding="utf-8")
        assert on_disk == content, f"drift in {name}"


def _read_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


# --------------------------------------------------------------------------- #
# Input verification
# --------------------------------------------------------------------------- #

def test_input_files_exist():
    assert ALL_ROWS_PATH.is_file()
    assert PAIRS_PATH.is_file()


def test_input_sha256_verified():
    import hashlib
    sha_all = hashlib.sha256(ALL_ROWS_PATH.read_bytes()).hexdigest()
    sha_pairs = hashlib.sha256(PAIRS_PATH.read_bytes()).hexdigest()
    assert sha_all == part3a.EXPECTED_INPUT_ALL_ROWS_SHA256
    assert sha_pairs == part3a.EXPECTED_INPUT_PAIRS_SHA256


def test_load_inputs_returns_correct_data():
    df_all, df_pairs, sha_all, sha_pairs = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    assert len(df_all) == 1331
    assert len(df_pairs) == 1200
    assert sha_all == part3a.EXPECTED_INPUT_ALL_ROWS_SHA256
    assert sha_pairs == part3a.EXPECTED_INPUT_PAIRS_SHA256


def test_load_inputs_fail_closed_on_missing():
    with pytest.raises(part3a.QCFail):
        part3a.load_inputs(None, PAIRS_PATH)
    with pytest.raises(part3a.QCFail):
        part3a.load_inputs(ALL_ROWS_PATH, None)


def test_invariants_match():
    result = _build()
    counts = result["counts"]
    errs = part3a.check_invariants(counts)
    assert errs == [], "; ".join(errs)


def test_baseline_commit_is_ancestor():
    part3a.verify_baseline_commit(str(REPO_ROOT))


# --------------------------------------------------------------------------- #
# Candidate inventory
# --------------------------------------------------------------------------- #

def test_registered_candidate_count_exactly_10():
    rows = part3a.build_candidate_inventory_rows()
    registered = [r for r in rows if r["candidate_scope_status"] == "registered_candidate"]
    assert len(registered) == 10


def test_registered_block_counts():
    rows = part3a.build_candidate_inventory_rows()
    registered = [r for r in rows if r["candidate_scope_status"] == "registered_candidate"]
    assert sum(1 for r in registered if r["block"] == "M2") == 3
    assert sum(1 for r in registered if r["block"] == "M3") == 3
    assert sum(1 for r in registered if r["block"] == "M4") == 4
    assert not any(r["block"] == "M5" for r in registered)


def test_registered_variable_names():
    rows = part3a.build_candidate_inventory_rows()
    registered = [r for r in rows if r["candidate_scope_status"] == "registered_candidate"]
    names = {r["variable_name"] for r in registered}
    expected = {
        "equity_return_window", "realized_volatility", "amihud_illiquidity",
        "cpi_inflation", "fx_change_official", "policy_financing_rate",
        "audit_opinion_type", "going_concern_flag", "audit_lag_days", "board_size",
    }
    assert names == expected


def test_src_m3_sci_macro_registry_only():
    rows = part3a.build_candidate_inventory_rows()
    sci = [r for r in rows if r["source_id"] == "src_m3_sci_macro"]
    assert len(sci) == 1
    assert sci[0]["registry_status"] == "registry_only_not_registered"
    assert sci[0]["candidate_scope_status"] == "registry_only_not_registered"
    assert sci[0]["variable_name"] == ""


def test_no_evidence_scores_assigned():
    rows = part3a.build_candidate_inventory_rows()
    registered = [r for r in rows if r["candidate_scope_status"] == "registered_candidate"]
    for r in registered:
        assert r["accessibility_score"] == ""
        assert r["evidence_status"] == "unresolved"
        assert r["decision_status"] == "pending_part3b_evidence"
        assert "pass" not in r["decision_status"].lower()
        assert "admit" not in r["decision_status"].lower()


def test_research_design_only_not_registered():
    rows = part3a.build_candidate_inventory_rows()
    rd = [r for r in rows
          if r["candidate_scope_status"] == "research_design_only_not_registered"]
    assert len(rd) >= 1
    assert all(r["dictionary_status"] == "not_registered" for r in rd)


def test_out_of_scope_locked_present():
    rows = part3a.build_candidate_inventory_rows()
    oos = [r for r in rows if r["candidate_scope_status"] == "out_of_scope_locked"]
    assert any(r["variable_name"] == "persian_text_modeling" for r in oos)


# --------------------------------------------------------------------------- #
# Accessibility rubric
# --------------------------------------------------------------------------- #

def test_accessibility_rubric_pending_approval():
    rubric = part3a.build_accessibility_rubric()
    assert rubric["approval_status"] == "pending_user_approval"
    assert rubric["applied_to_sources"] is False
    assert rubric["label"] == "proposed, not yet applied"


def test_accessibility_rubric_scoring_rules():
    rubric = part3a.build_accessibility_rubric()
    rules = rubric["scoring_rules"]
    assert rules["missing_evidence"] == "null_or_unresolved_never_zero"
    assert rules["score_below_3"] == "hard_drop"
    assert rules["score_equals_3"] == "pilot_permission_only_not_automatic_admission"
    assert rules["score_4_or_5"] == "must_still_pass_every_other_gate"


def test_accessibility_rubric_score_definitions_proposed():
    rubric = part3a.build_accessibility_rubric()
    for score in ("0", "1", "2", "3", "4", "5"):
        assert rubric["score_definitions"][score]["label"] == "proposed, not yet applied"


# --------------------------------------------------------------------------- #
# Gate protocol
# --------------------------------------------------------------------------- #

def test_gate_protocol_locked_and_pending():
    rows = part3a.build_gate_protocol_rows()
    locked = [r for r in rows if r["lock_status"] == "locked"]
    pending = [r for r in rows if r["approval_status"] == "pending_user_approval"]
    assert len(locked) == 8
    assert len(pending) == 6
    assert all(r["threshold_value"] == "" for r in pending)


def test_gate_protocol_coverage_and_event_gates_pending():
    rows = part3a.build_gate_protocol_rows()
    names = {r["gate_name"] for r in rows}
    assert "minimum_company_year_coverage" in names
    assert "minimum_common_sample_coverage" in names
    assert "minimum_positive_event_count_per_fold" in names
    assert "minimum_negative_event_count_per_fold" in names
    assert "final_pilot_sample_size" in names
    assert "final_pilot_sampling_allocation" in names


def test_gate_protocol_accessibility_locked():
    rows = part3a.build_gate_protocol_rows()
    g01 = next(r for r in rows if r["gate_id"] == "G01")
    assert g01["lock_status"] == "locked"
    assert "accessibility" in g01["gate_name"]


# --------------------------------------------------------------------------- #
# Sampling frame
# --------------------------------------------------------------------------- #

def test_sampling_summary_counts():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    counts = part3a.compute_invariants(df_all, df_pairs)
    summary = part3a.build_sampling_summary(df_all, df_pairs, counts)
    assert summary["total_company_year_rows"] == 1331
    assert summary["total_pairs"] == 1200
    assert summary["unique_tickers"] == 130
    assert summary["rule_a_primary_sample"]["pairs"] == 1013
    assert summary["rule_a_primary_sample"]["positive"] == 81
    assert summary["rule_b_listing_robustness_sample"]["pairs"] == 994
    assert summary["rule_b_listing_robustness_sample"]["positive"] == 80


def test_sampling_by_year_has_10_target_years():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part3a.build_sampling_by_year_rows(df_all, df_pairs)
    assert len(rows) == 10
    assert sum(int(r["total_pairs"]) for r in rows) == 1200


def test_pilot_sampling_options_pending_approval():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    options = part3a.build_pilot_sampling_options(df_all, df_pairs)
    assert len(options) == 3
    for opt in options:
        assert opt["status"] == "pending_user_approval"
        assert int(opt["proposed_sample_size"]) > 0


def test_pilot_sampling_deterministic():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    a = part3a.build_pilot_sampling_options(df_all, df_pairs)
    b = part3a.build_pilot_sampling_options(df_all, df_pairs)
    assert a == b


# --------------------------------------------------------------------------- #
# Evidence schema
# --------------------------------------------------------------------------- #

def test_evidence_manifest_schema_fields():
    schema = part3a.build_evidence_manifest_schema()
    field_names = [f["name"] for f in schema["required_fields"]]
    assert "evidence_id" in field_names
    assert "candidate_id" in field_names
    assert "source_url" in field_names
    assert "snapshot_sha256" in field_names
    assert schema["null_rules"]["unknown_fields_must_be_null"] is True


# --------------------------------------------------------------------------- #
# Full build + QC
# --------------------------------------------------------------------------- #

def test_build_all_passes_qc():
    result = _build()
    qc = result["qc"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["modeling_started"] is False
    assert qc["part3a_protocol_locked"] is True
    assert qc["part3b_started"] is False
    assert qc["network_extraction_performed"] is False
    assert qc["eligibility_impact"] == "none_protocol_only"
    assert qc["baseline_commit"] == part3a.EXPECTED_BASELINE_COMMIT


def test_qc_assertion_count_at_least_25():
    result = _build()
    assert result["qc"]["assertion_count"] >= 25


def test_frozen_assets_unchanged():
    before = part3a.frozen_asset_hashes(REPO_ROOT)
    result = _build()
    after = part3a.frozen_asset_hashes(REPO_ROOT)
    assert before == after
    assert len(before) > 0


def test_content_deterministic():
    r1 = _build()
    r2 = _build()
    for name in part3a.CONTENT_FILES:
        assert r1["files"][name] == r2["files"][name]


def test_on_disk_matches_computed():
    result = _build()
    _check_files(result)


def test_runner_check_mode():
    import subprocess
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_stage125_part3a.py"), "--check"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr


def test_no_modeling_artifact_created():
    result = _build()
    for name in result["files"]:
        assert "model" not in name.lower() or "modeling" in name.lower()
    assert result["qc"]["modeling_started"] is False


def test_inventory_csv_structure_in_build():
    result = _build()
    rows = _read_csv(result["files"][part3a.F_CANDIDATE_INVENTORY])
    assert len(rows) > 10
    registered = [r for r in rows if r["candidate_scope_status"] == "registered_candidate"]
    assert len(registered) == 10
