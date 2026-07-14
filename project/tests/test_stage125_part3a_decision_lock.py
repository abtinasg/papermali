"""Tests for Stage125 Part 3A.1 — User-Approved Pilot Decision Lock.

All tests are read-only: they never modify the canonical repository files.
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

from src import stage125_part3a_decision_lock as lock  # noqa: E402
from src import stage125_part3a_pilot_protocol as part3a  # noqa: E402

ALL_ROWS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_all_rows_stage124_gate_b.csv"
PAIRS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_one_year_ahead_stage124_gate_b.csv"
OUTPUT_DIR = ROOT / "stage125"


def _build():
    return lock.build_all(REPO_ROOT, ALL_ROWS_PATH, PAIRS_PATH)


def _read_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


# --------------------------------------------------------------------------- #
# Input verification
# --------------------------------------------------------------------------- #

def test_input_files_exist():
    assert ALL_ROWS_PATH.is_file()
    assert PAIRS_PATH.is_file()


def test_baseline_commit_exact():
    lock.verify_baseline_commit(str(REPO_ROOT))


def test_part3a_frozen_files_intact():
    hashes = lock.part3a_frozen_hashes(REPO_ROOT)
    assert len(hashes) >= 9


# --------------------------------------------------------------------------- #
# Rubric approval
# --------------------------------------------------------------------------- #

def test_rubric_approved_not_applied():
    approval = lock.build_rubric_approval_record(REPO_ROOT)
    assert approval["rubric_version"] == "stage125_part3a_v1"
    assert approval["rubric_approval_status"] == (
        "approved_for_part3b_evidence_pilot"
    )
    assert approval["applied_to_sources"] is False
    assert approval["frozen_rubric_scoring_rules_match"] is True


def test_frozen_rubric_file_unchanged():
    rubric = lock.load_frozen_rubric(REPO_ROOT)
    assert rubric["approval_status"] == "pending_user_approval"
    assert rubric["applied_to_sources"] is False


# --------------------------------------------------------------------------- #
# Gate thresholds
# --------------------------------------------------------------------------- #

def test_gate_thresholds_g09_g14():
    rows = lock.build_gate_threshold_rows()
    assert len(rows) == 6
    gids = {r["gate_id"] for r in rows}
    assert gids == {"G09", "G10", "G11", "G12", "G13", "G14"}
    g09 = next(r for r in rows if r["gate_id"] == "G09")
    assert g09["threshold_value"] == "0.80"
    assert g09["unit"] == "proportion"
    g13 = next(r for r in rows if r["gate_id"] == "G13")
    assert g13["threshold_value"] == "80"
    g14 = next(r for r in rows if r["gate_id"] == "G14")
    assert g14["threshold_value"] == "pilot_option_event_enriched"


def test_gate_thresholds_pilot_scope_only():
    rows = lock.build_gate_threshold_rows()
    for r in rows:
        assert "pilot_only" in r["scope"]
        assert "not_final_modeling" in r["scope"]


# --------------------------------------------------------------------------- #
# Pilot selection
# --------------------------------------------------------------------------- #

def test_pilot_selection_eighty_pairs():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    selected, ya = lock.select_approved_pilot_pairs(df_all, df_pairs)
    assert len(selected) == 80
    assert sum(1 for s in selected if s["class"] == "positive") == 39
    assert sum(1 for s in selected if s["class"] == "negative") == 41
    assert sum(1 for s in selected if s["class"] == "unknown") == 0
    assert len({s["ticker"] for s in selected}) == 26
    summary = lock.summarize_industry_counts([s["industry"] for s in selected])
    assert summary["unique_known_industries"] == 10
    assert summary["industry_present_pairs"] == 53
    assert summary["industry_missing_pairs"] == 27
    assert summary["legacy_nonempty_industry_label_count"] == 11
    for ty, expected in lock.EXPECTED_YEAR_ALLOCATION.items():
        assert ya[ty] == expected


def test_pilot_selection_rule_a_eligible():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    merged = part3a._merge_pairs_targets(df_all, df_pairs)
    ra_keys = set(
        merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"][
            "predictor_row_key_t"
        ]
    )
    selected, _ = lock.select_approved_pilot_pairs(df_all, df_pairs)
    keys = [s["predictor_row_key_t"] for s in selected]
    assert len(keys) == len(set(keys))
    assert all(k in ra_keys for k in keys)


def test_pilot_selection_deterministic():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    a, ya1 = lock.select_approved_pilot_pairs(df_all, df_pairs)
    b, ya2 = lock.select_approved_pilot_pairs(df_all, df_pairs)
    assert a == b
    assert ya1 == ya2


def test_not_selected_options():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    selected, ya = lock.select_approved_pilot_pairs(df_all, df_pairs)
    record = lock.build_pilot_selection_record(selected, ya)
    assert record["selected_option"] == "pilot_option_event_enriched"
    assert record["not_selected_options"] == [
        "pilot_option_compact", "pilot_option_extended",
    ]
    assert record["modeling_sample"] is False
    assert record["population_representative"] is False


# --------------------------------------------------------------------------- #
# Full build + QC
# --------------------------------------------------------------------------- #

def test_build_all_passes_qc():
    result = _build()
    qc = result["qc"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["part3a_decision_locked"] is True
    assert qc["part3b_started"] is False
    assert qc["evidence_collected"] is False
    assert qc["modeling_started"] is False
    assert qc["network_extraction_performed"] is False


def test_qc_assertion_count_at_least_20():
    result = _build()
    assert result["qc"]["assertion_count"] >= 20


def test_frozen_assets_unchanged():
    before = lock.frozen_asset_hashes(REPO_ROOT)
    _build()
    after = lock.frozen_asset_hashes(REPO_ROOT)
    assert before == after


def test_part3a_frozen_unchanged_during_build():
    before = lock.part3a_frozen_hashes(REPO_ROOT)
    _build()
    after = lock.part3a_frozen_hashes(REPO_ROOT)
    assert before == after


def test_content_deterministic():
    r1 = _build()
    r2 = _build()
    for name in lock.CONTENT_FILES:
        assert r1["files"][name] == r2["files"][name]


def test_decision_json_required_fields():
    result = _build()
    data = json.loads(result["files"][lock.F_DECISION])
    assert data["part3a_protocol_locked"] is True
    assert data["part3a_decision_locked"] is True
    assert data["part3b_started"] is False
    assert data["evidence_collected"] is False
    assert data["modeling_started"] is False
    assert data["network_extraction_performed"] is False
    assert data["eligibility_impact"] == "none_protocol_only"
    assert "approved_gate_thresholds_g09_g14" in data


def test_selected_pairs_csv_structure():
    result = _build()
    rows = _read_csv(result["files"][lock.F_SELECTED_PAIRS])
    assert len(rows) == 80
    assert all(r["post_evidence_substitution_allowed"] == "false" for r in rows)
    assert all(r["option_id"] == "pilot_option_event_enriched" for r in rows)
    assert "industry_present" in rows[0]
    assert "industry_missing_reason" in rows[0]
    summary = lock.summarize_industry_counts([r["industry"] for r in rows])
    assert summary["unique_known_industries"] == 10
    assert summary["industry_present_pairs"] == 53
    assert summary["industry_missing_pairs"] == 27


def test_industry_blank_and_unknown_sentinel_never_known():
    assert lock.is_industry_missing("") is True
    assert lock.is_industry_missing("   ") is True
    assert lock.is_industry_missing(lock.INDUSTRY_UNKNOWN_SENTINEL) is True
    assert lock.industry_missing_reason("") == "blank_or_whitespace"
    assert lock.industry_missing_reason(
        lock.INDUSTRY_UNKNOWN_SENTINEL,
    ) == "unknown_sentinel"
    summary = lock.summarize_industry_counts([
        "", "  ", lock.INDUSTRY_UNKNOWN_SENTINEL, "خودرو و ساخت قطعات",
    ])
    assert summary["unique_known_industries"] == 1
    assert summary["industry_present_pairs"] == 1
    assert summary["industry_missing_pairs"] == 3
    assert lock.INDUSTRY_UNKNOWN_SENTINEL not in summary["known_industries"]


def test_pilot_selection_industry_json_fields():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    selected, ya = lock.select_approved_pilot_pairs(df_all, df_pairs)
    record = lock.build_pilot_selection_record(selected, ya)
    assert record["unique_known_industries"] == 10
    assert record["industry_present_pairs"] == 53
    assert record["industry_missing_pairs"] == 27
    assert record["legacy_nonempty_industry_label_count"] == 11
    assert "unique_industries" not in record
    assert lock.INDUSTRY_UNKNOWN_SENTINEL not in record["known_industries"]


def test_runner_check_mode():
    import subprocess
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_stage125_part3a_decision_lock.py"),
         "--check"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr


# --------------------------------------------------------------------------- #
# Evidence-based guardrails + negative tests
# --------------------------------------------------------------------------- #

def test_guard_network_sentinel_zero_calls():
    result = _build()
    assert result["guard_evidence"]["network_calls_attempted"] == 0


def test_guard_part3b_scan_clean():
    evidence = part3a.scan_for_part3b_artifacts(REPO_ROOT)
    assert evidence["no_part3b"] is True


def test_negative_part3b_runner_detected(tmp_path):
    src = tmp_path / "project" / "src"
    src.mkdir(parents=True)
    (src / "stage125_part3b_evidence.py").write_text("x\n")
    evidence = part3a.scan_for_part3b_artifacts(tmp_path)
    assert evidence["no_part3b"] is False


def test_negative_network_call_blocked():
    import socket as _socket
    with part3a.network_sentinel() as sentinel:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            with pytest.raises(OSError):
                sock.connect(("127.0.0.1", 9))
        finally:
            sock.close()
        assert sentinel.calls_attempted == 1


def test_negative_eligibility_mismatch_detected():
    df_all, df_pairs, _, _ = part3a.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    tampered = df_pairs.copy()
    idx = tampered.index[
        tampered["pair_final_eligible_main_gate_b_primary"] == "1"
    ][0]
    tampered.loc[idx, "pair_final_eligible_main_gate_b_primary"] = "0"
    evidence = part3a.run_guardrails(ROOT, REPO_ROOT, df_all, tampered, 0)
    assert evidence["eligibility_unchanged"] is False


def test_negative_modeling_artifact_detected(tmp_path):
    bad = tmp_path / "stage125" / "nested"
    bad.mkdir(parents=True)
    (bad / "model.joblib").write_bytes(b"fake")
    evidence = part3a.scan_for_modeling_artifacts(tmp_path)
    assert evidence["no_modeling"] is False


def test_negative_wrong_baseline_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        lock, "EXPECTED_BASELINE_COMMIT", "0" * 40, raising=False,
    )
    with pytest.raises(lock.QCFail, match="origin/main"):
        lock.verify_baseline_commit(str(REPO_ROOT))


def test_negative_part3a_frozen_tamper_detected(tmp_path):
    """Tampering a Part 3A frozen file must fail part3a_frozen_hashes."""
    import shutil
    fake_root = tmp_path / "fake_repo"
    dst = fake_root / "project" / "stage125"
    shutil.copytree(REPO_ROOT / "project" / "stage125", dst)
    (dst / part3a.F_ACCESSIBILITY_RUBRIC).write_text(
        '{"tampered": true}\n', encoding="utf-8",
    )
    with pytest.raises(lock.QCFail, match="hash mismatch"):
        lock.part3a_frozen_hashes(fake_root)


def test_qc_guard_assertions_evidence_backed():
    result = _build()
    names = {a["assertion"]: a for a in result["qc"]["assertions"]}
    for key in (
        "no_part3b_artifacts", "no_network_extraction", "no_modeling_artifacts",
        "eligibility_unchanged", "part3a_frozen_files_unchanged",
        "no_candidate_admitted_or_rejected",
    ):
        assert names[key]["status"] == "PASS", names[key]["detail"]
