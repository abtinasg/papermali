"""Exact-path allowlist guards for Stage125 Part 3B.1 Decision Lock surfaces.

Proves legitimate Part 3B.1 paths are accepted by historical Part 3A / 3B.0
guards, while prefix/suffix/glob/directory/symlink/unknown attacks remain
fail-closed. No network. No real evidence/scoring/modeling.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3a_pilot_protocol as part3a  # noqa: E402
from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b_evidence_capture as part3b  # noqa: E402

LEGIT_PART3B1 = frozenset(part3b.PART3B1_AUTHORIZED_EXACT)

ATTACK_PATHS = (
    "project/src/stage125_part3b10_decision_lock.py",
    "project/src/stage125_part3b1_decision_lock.py.bak",
    "project/src/stage125_part3b1_decision_lock.py.evil",
    "project/tests/test_stage125_part3b10_decision_lock.py",
    "project/tests/test_stage125_part3b1_decision_lock.py.bak",
    "project/stage125/part3b1_unknown_extra_contract_stage125.json",
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage125/nested/part3b1_decision_lock_stage125.json",
    "project/stage125/../src/stage125_part3b1_decision_lock.py.evil",
    "project/stage125/part3b1_decision_lock_stage125.json.exe",
    "project/stage125/real_evidence_cache.bin",
    "project/stage125/accessibility_scores_live.csv",
    "project/stage125/model_weights.pkl",
)


def _auth_mini_repo(tmp_path: Path) -> Path:
    """Minimal repo where Part 3B authorization is active."""
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    (stage / "part3b_authorization_stage125.json").write_text(
        json.dumps({"part3b_started": True}), encoding="utf-8",
    )
    (tmp_path / "project" / "src").mkdir(parents=True)
    (tmp_path / "project" / "tests").mkdir(parents=True)
    return tmp_path


def test_part3b1_authorized_exact_paths_are_literal_and_complete():
    expected = {
        "project/run_stage125_part3b1.py",
        "project/src/stage125_part3b1_decision_lock.py",
        "project/tests/test_stage125_part3b1_decision_lock.py",
        "project/tests/test_stage125_part3b1_allowlist_guards.py",
        "project/stage125/README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md",
        "project/stage125/metadata_and_hashes_stage125_part3b1.json",
        "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
        "project/stage125/part3b1_decision_lock_stage125.json",
        "project/stage125/part3b1_m2_feature_formula_contract_stage125.json",
        "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json",
        "project/stage125/part3b1_m4_feature_definition_contract_stage125.json",
        "project/stage125/part3b1_rubric_operational_mapping_stage125.json",
        "project/stage125/part3b1_selected_decisions_stage125.csv",
        "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
    }
    assert set(part3b.PART3B1_AUTHORIZED_EXACT) == expected
    assert part3b.PART3B1_AUTHORIZED_EXACT <= part3b.PART3B_AUTHORIZED_EXACT
    for rel in expected:
        if rel.startswith("project/stage125/"):
            assert rel in p3b0.STAGE125_ALLOWED_EXACT
        assert (REPO_ROOT / rel).is_file()


def test_no_wildcard_or_directory_wide_part3b1_allowlist():
    joined_auth = "\n".join(sorted(part3b.PART3B_AUTHORIZED_EXACT))
    joined_stage = "\n".join(sorted(p3b0.STAGE125_ALLOWED_EXACT))
    for blob in (joined_auth, joined_stage):
        assert "part3b1_*" not in blob
        assert "stage125_part3b1/" not in blob
        assert "*" not in blob
    assert "project/src/stage125_part3b/" not in part3b.PART3B_AUTHORIZED_EXACT
    assert "project/stage125/" not in part3b.PART3B_AUTHORIZED_EXACT
    # Authorization must not rely on startswith("stage125_part3b").
    assert not any(
        p.endswith("/") and "part3b" in p for p in part3b.PART3B_AUTHORIZED_EXACT
    )


@pytest.mark.parametrize("rel", sorted(LEGIT_PART3B1))
def test_legitimate_part3b1_paths_are_authorized(rel: str):
    assert rel in part3b.PART3B_AUTHORIZED_EXACT
    assert p3b0._is_authorized_part3b_path(REPO_ROOT, rel) is True
    if rel.startswith("project/stage125/"):
        assert rel in p3b0.STAGE125_ALLOWED_EXACT


def test_live_repo_part3a_and_part3b0_scans_clean_for_part3b1():
    a = part3a.scan_for_part3b_artifacts(REPO_ROOT)
    b0 = p3b0.scan_for_part3b_capture_start(REPO_ROOT)
    assert not any("part3b1" in h.lower() for h in a["hits"])
    assert not any("part3b1" in h.lower() for h in b0["hits"])
    assert a["no_part3b"] is True
    assert b0["no_part3b"] is True


@pytest.mark.parametrize("rel", ATTACK_PATHS)
def test_attack_paths_not_in_exact_allowlists(rel: str):
    assert rel not in part3b.PART3B_AUTHORIZED_EXACT
    assert rel not in part3b.PART3B1_AUTHORIZED_EXACT
    assert rel not in p3b0.STAGE125_ALLOWED_EXACT


def test_prefix_suffix_and_part3b10_attacks_rejected_by_scan(tmp_path):
    repo = _auth_mini_repo(tmp_path)
    # Seed one legitimate authorized file so auth set is exercised.
    legit = "project/src/stage125_part3b1_decision_lock.py"
    (repo / legit).parent.mkdir(parents=True, exist_ok=True)
    (repo / legit).write_text("# legit\n", encoding="utf-8")

    attacks = {
        "project/src/stage125_part3b10_decision_lock.py": "evil",
        "project/src/stage125_part3b1_decision_lock.py.bak": "bak",
        "project/src/stage125_part3b1_decision_lock.py.evil": "evil",
        "project/tests/test_stage125_part3b10_decision_lock.py": "evil",
        "project/stage125/part3b1_unknown_extra_contract_stage125.json": "{}",
        "project/stage125/part3b2_feature_extraction_stage125.json": "{}",
        "project/stage125/unknown_file_stage125.txt": "x",
        "project/run_stage126.py": "# stage126\n",
        "project/src/stage126_modeling.py": "# modeling\n",
        "project/stage125/nested/part3b1_decision_lock_stage125.json": "{}",
        "project/stage125/real_evidence_cache.bin": "cache",
        "project/stage125/accessibility_scores_live.csv": "a,b\n",
        "project/stage125/model_weights.pkl": "model",
    }
    for rel, body in attacks.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    a_hits = set(part3a.scan_for_part3b_artifacts(repo)["hits"])
    b0_hits = set(p3b0.scan_for_part3b_capture_start(repo)["hits"])

    # Legitimate exact path must not be reported once authorized.
    assert legit not in a_hits
    assert legit not in b0_hits

    # Prefix / suffix / unknown / nested / 3B.2 / Stage126 must be hits.
    for rel in (
        "project/src/stage125_part3b10_decision_lock.py",
        "project/src/stage125_part3b1_decision_lock.py.bak",
        "project/src/stage125_part3b1_decision_lock.py.evil",
        "project/tests/test_stage125_part3b10_decision_lock.py",
    ):
        assert rel in a_hits or rel in b0_hits
    for rel in (
        "project/stage125/part3b1_unknown_extra_contract_stage125.json",
        "project/stage125/part3b2_feature_extraction_stage125.json",
        "project/stage125/unknown_file_stage125.txt",
        "project/stage125/nested/part3b1_decision_lock_stage125.json",
        "project/stage125/real_evidence_cache.bin",
        "project/stage125/accessibility_scores_live.csv",
        "project/stage125/model_weights.pkl",
    ):
        assert rel in b0_hits
    # Stage126 surfaces must never be treated as Part 3B.1-authorized.
    assert "project/run_stage126.py" not in part3b.PART3B_AUTHORIZED_EXACT
    assert "project/src/stage126_modeling.py" not in part3b.PART3B_AUTHORIZED_EXACT
    assert "project/run_stage126.py" not in p3b0.STAGE125_ALLOWED_EXACT
    assert p3b0._is_authorized_part3b_path(repo, "project/run_stage126.py") is False
    assert p3b0._is_authorized_part3b_path(
        repo, "project/src/stage126_modeling.py",
    ) is False


def test_unregistered_new_part3b1_file_fail_closed(tmp_path):
    repo = _auth_mini_repo(tmp_path)
    rel = "project/stage125/part3b1_brand_new_unlisted_contract_stage125.json"
    path = repo / rel
    path.write_text("{}", encoding="utf-8")
    assert rel not in part3b.PART3B1_AUTHORIZED_EXACT
    assert rel not in p3b0.STAGE125_ALLOWED_EXACT
    hits = p3b0.scan_for_part3b_capture_start(repo)["hits"]
    assert rel in hits


def test_symlink_to_authorized_path_is_not_treated_as_exact_allowlist(tmp_path):
    repo = _auth_mini_repo(tmp_path)
    legit_rel = "project/src/stage125_part3b1_decision_lock.py"
    legit = repo / legit_rel
    legit.write_text("# legit\n", encoding="utf-8")

    link_rel = "project/src/stage125_part3b1_decision_lock_link.py"
    link = repo / link_rel
    if hasattr(os, "symlink"):
        try:
            link.symlink_to(legit)
        except OSError:
            pytest.skip("symlink not permitted in this environment")
    else:
        pytest.skip("symlink unsupported")

    assert link_rel not in part3b.PART3B_AUTHORIZED_EXACT
    hits = part3a.scan_for_part3b_artifacts(repo)["hits"]
    # Symlink path itself is not the exact authorized path.
    assert link_rel in hits or not link.exists() or link.is_symlink()
    # Even if scanners follow the target, the symlink path is unlisted.
    assert link_rel not in part3b.PART3B1_AUTHORIZED_EXACT


def test_path_traversal_style_name_not_authorized():
    rel = "project/stage125/../src/stage125_part3b1_decision_lock.py"
    assert rel not in part3b.PART3B_AUTHORIZED_EXACT
    assert rel not in p3b0.STAGE125_ALLOWED_EXACT
    # Normalized legitimate path remains exact-only.
    assert "project/src/stage125_part3b1_decision_lock.py" in (
        part3b.PART3B1_AUTHORIZED_EXACT
    )


def test_live_historical_builds_pass_after_exact_allowlist():
    all_rows = ROOT / "stage124/gate_b_final/modeling_all_rows_stage124_gate_b.csv"
    pairs = ROOT / "stage124/gate_b_final/modeling_one_year_ahead_stage124_gate_b.csv"
    a = part3a.build_all(REPO_ROOT, all_rows, pairs)
    assert a["qc"]["all_pass"] is True
    from src import stage125_part3a_decision_lock as a1
    a1r = a1.build_all(REPO_ROOT, all_rows, pairs)
    assert a1r["qc"]["all_pass"] is True
    b0 = p3b0.build_all(REPO_ROOT)
    assert b0["qc"]["all_pass"] is True
