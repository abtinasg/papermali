"""Tests for the repository-driven AI Handoff Package.

Two groups:

* Real-repo checks (read-only): the committed handoff state validates, the
  machine-readable state agrees with git, links resolve, markers are off, and the
  change allowlist holds.
* Semantic-drift tests: build a self-contained synthetic git repository in a temp
  dir, generate a valid handoff, then mutate it and assert the validator's
  behaviour. The real project history is never touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

import update_ai_handoff as gen          # noqa: E402
import validate_ai_handoff as val        # noqa: E402

REAL_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(root: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", root, *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _state(root: str) -> dict:
    return json.load(open(os.path.join(root, "project/docs/ai/handoff_state.json"), encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Real-repo, read-only checks
# --------------------------------------------------------------------------- #

def test_real_repo_validates():
    assert val.run_check(REAL_ROOT) == 0


def test_state_matches_git():
    state = _state(REAL_ROOT)
    head = gen.head_commit(REAL_ROOT)
    gfc = state["generated_from_commit"]
    assert gfc == head or gen.is_ancestor(REAL_ROOT, gfc, head)
    assert state["last_stage_commit"] == gen.last_stage_commit(REAL_ROOT)


def test_real_repo_last_stage_commit_is_a_real_content_commit():
    # last_stage_commit is PATH-BASED / SEMANTIC: it must resolve to the most
    # recent commit that introduces real (non-Handoff-only, non-artifact-only,
    # non-maintenance-only) content, regardless of that commit's message
    # wording. This test does NOT hard-code a specific SHA (a hard-coded
    # expectation here would itself be message-wording-adjacent and would need
    # editing on every future real commit) — instead it independently
    # recomputes the expectation via the same path-based rule and cross-checks
    # it against the git history walk.
    got = gen.last_stage_commit(REAL_ROOT)
    files = gen._introduced_files(REAL_ROOT, got)
    assert gen._is_stage_relevant(files), (
        f"last_stage_commit {got} must introduce at least one real "
        "(non-Handoff-only, non-artifact-only, non-maintenance-only) file"
    )
    # Every commit strictly newer than `got` must NOT be stage-relevant,
    # otherwise `got` would not be the LATEST qualifying commit.
    # Content-preserving two-parent merges (tree == second parent) are skipped
    # by last_stage_commit and must be skipped here for the same reason.
    newer = gen._git(REAL_ROOT, "rev-list", f"{got}..HEAD").splitlines()
    for sha in newer:
        if gen._is_content_preserving_merge(REAL_ROOT, sha):
            continue
        newer_files = gen._introduced_files(REAL_ROOT, sha)
        assert not gen._is_stage_relevant(newer_files), (
            f"commit {sha} is newer than last_stage_commit {got} but is "
            f"ALSO stage-relevant (files={newer_files}) — last_stage_commit "
            "should have resolved to it instead"
        )


def test_qc_counts_match_report():
    state = _state(REAL_ROOT)
    qc = json.load(open(os.path.join(REAL_ROOT, state["selected_qc_path"]), encoding="utf-8"))
    assert state["qc_assertions"] == qc["assertion_count"]
    assert state["qc_failed"] == qc["failed_count"]
    assert state["qc_all_pass"] == qc["all_pass"]
    assert qc["failed_count"] == 0 and qc["all_pass"] is True


def test_markers_are_off():
    # Gate B has been executed (Stage124 finalization): gate_b_started is True.
    # Stage126 M1 is human-authorized and development-fold modeling has started,
    # so modeling_started is now True. It never implies final-test access.
    state = _state(REAL_ROOT)
    assert state["modeling_started"] is True
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["gate_b_started"] is True
    assert state["verified_master_created"] is True


def test_frozen_stages_present():
    for mf in gen.FROZEN_MANIFESTS:
        assert os.path.isfile(os.path.join(REAL_ROOT, mf)), mf


def test_internal_links_resolve():
    errors: list[str] = []
    val._check_links(REAL_ROOT, errors)
    assert errors == [], errors


def test_no_forbidden_phrases():
    errors: list[str] = []
    val._check_forbidden_phrases(REAL_ROOT, errors)
    assert errors == [], errors


def test_roadmap_ordering():
    errors: list[str] = []
    val._check_roadmap(REAL_ROOT, errors)
    assert errors == [], errors


def test_generator_is_idempotent():
    outputs = gen.generate(REAL_ROOT)
    fresh = json.loads(outputs["project/docs/ai/handoff_state.json"])
    assert fresh["state_fingerprint"] == _state(REAL_ROOT)["state_fingerprint"]


@pytest.mark.skipif(
    os.environ.get("ENFORCE_HANDOFF_CHANGE_ALLOWLIST") != "1",
    reason="Change allowlist is only enforced on Handoff-maintenance branches",
)
def test_change_allowlist_real_repo():
    try:
        gen._git(REAL_ROOT, "rev-parse", "origin/main")
    except gen.HandoffError:
        pytest.skip("origin/main not available")
    assert val.run_check_changes(REAL_ROOT, "origin/main", include_wt=True) == 0


# --------------------------------------------------------------------------- #
# Allowlist path matching (no prefix attacks) — pure unit
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path,ok", [
    ("AGENTS.md", True),
    ("CLAUDE.md", True),
    ("project/docs/ai/CURRENT_STATE.md", True),
    ("project/docs/ai/sub/x.md", True),
    ("project/scripts/update_ai_handoff.py", True),
    # Stage125 Part 1 (maintenance task) allowlisted paths
    ("project/stage125/data_dictionary_stage125.csv", True),
    ("project/stage125/sub/x.json", True),
    ("project/src/stage125_part1_data_contract.py", True),
    ("project/run_stage125_part1.py", True),
    ("project/tests/test_stage125_part1_data_contract.py", True),
    # Stage125 Part 2 allowlisted paths
    ("project/src/stage125_part2_prediction_time_contract.py", True),
    ("project/run_stage125_part2.py", True),
    ("project/tests/test_stage125_part2_prediction_time_contract.py", True),
    ("project/stage125/prediction_time_contract_stage125_part2.json", True),
    ("project/stage125/metadata_and_hashes_stage125_part2.json", True),
    # Stage125 Part 3A allowlisted paths
    ("project/src/stage125_part3a_pilot_protocol.py", True),
    ("project/run_stage125_part3a.py", True),
    ("project/tests/test_stage125_part3a_pilot_protocol.py", True),
    ("project/stage125/part3_candidate_inventory_stage125.csv", True),
    ("project/stage125/metadata_and_hashes_stage125_part3a.json", True),
    # Stage125 Part 3A.1 allowlisted paths
    ("project/src/stage125_part3a_decision_lock.py", True),
    ("project/run_stage125_part3a_decision_lock.py", True),
    ("project/tests/test_stage125_part3a_decision_lock.py", True),
    ("project/stage125/part3a_decision_lock_stage125.json", True),
    ("project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json", True),
    # Stage124 modeling-guardrail fix — narrowest exact-file allowance
    ("project/src/stage124_gate_b_execution.py", True),
    ("project/tests/test_stage124_gate_b_execution.py", True),
    ("project/stage124/stage124_batch02_gate_b_qc_report.json", True),
    ("project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json", True),
    # prefix attacks must be rejected
    ("AGENTS.md.evil", False),
    ("project/scripts/update_ai_handoff.py.bak", False),
    ("project/docs/ai-evil/x.md", False),
    ("project/docs/aimalicious", False),
    ("project/src/secret.py", False),
    # Stage125 similar-but-unauthorized prefixes must be rejected
    ("project/stage125", False),
    ("project/stage1250/evil.csv", False),
    ("project/stage125_evil/x.csv", False),
    ("project/src/stage125_part1_data_contract.py.bak", False),
    ("project/run_stage125_part1.py.evil", False),
    ("project/src/stage125_part2_data_contract.py", False),
    ("project/tests/test_stage125_part2_data_contract.py", False),
    ("project/src/stage125_part2_prediction_time_contract.py.bak", False),
    ("project/run_stage125_part2.py.evil", False),
    ("project/src/stage125_part3a_pilot_protocol.py.bak", False),
    ("project/run_stage125_part3a.py.evil", False),
    ("project/src/stage125_part3a_data_contract.py", False),
    ("project/tests/test_stage125_part3a_data_contract.py", False),
    # Stage125 Part 3A.1 similar-but-unauthorized prefixes must be rejected
    ("project/src/stage125_part3a_decision_lock.py.bak", False),
    ("project/run_stage125_part3a_decision_lock.py.evil", False),
    ("project/src/stage125_part3a1_decision_lock.py", False),
    # Stage124 similar-but-unauthorized paths must be rejected
    ("project/src/stage124_gate_b_execution.py.bak", False),
    ("project/tests/test_stage124_gate_b_execution.py.evil", False),
    ("project/stage124/stage124_batch02_gate_b_qc_report.json.bak", False),
    ("project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json.bak", False),
    ("project/stage124/other_file.json", False),
    ("project/src/stage124_gate_b_readiness.py", False),
    ("project/stage124/gate_b_final/modeling_main_rule_a_eligible.csv", False),
])
def test_allowlist_prefix_attack(path, ok):
    assert gen.path_allowlisted(path) is ok


# --------------------------------------------------------------------------- #
# Handoff-only classification (independent of change allowlist) — pure unit
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path,ok", [
    # Handoff-maintenance paths ARE handoff-only.
    ("AGENTS.md", True),
    ("CLAUDE.md", True),
    ("project/docs/ai/CURRENT_STATE.md", True),
    ("project/docs/ai/sub/x.md", True),
    ("project/scripts/update_ai_handoff.py", True),
    ("project/scripts/validate_ai_handoff.py", True),
    ("project/tests/test_ai_handoff.py", True),
    # Stage125 Part 1 code is change-allowlisted but MUST NOT be handoff-only.
    ("project/stage125/data_dictionary_stage125.csv", False),
    ("project/src/stage125_part1_data_contract.py", False),
    ("project/run_stage125_part1.py", False),
    ("project/tests/test_stage125_part1_data_contract.py", False),
    # Stage125 Part 2 code is change-allowlisted but MUST NOT be handoff-only.
    ("project/src/stage125_part2_prediction_time_contract.py", False),
    ("project/run_stage125_part2.py", False),
    ("project/tests/test_stage125_part2_prediction_time_contract.py", False),
    ("project/stage125/prediction_time_contract_stage125_part2.json", False),
    # Stage125 Part 3A code is change-allowlisted but MUST NOT be handoff-only.
    ("project/src/stage125_part3a_pilot_protocol.py", False),
    ("project/run_stage125_part3a.py", False),
    ("project/tests/test_stage125_part3a_pilot_protocol.py", False),
    ("project/stage125/part3_candidate_inventory_stage125.csv", False),
    # Stage125 Part 3A.1 code is change-allowlisted but MUST NOT be handoff-only.
    ("project/src/stage125_part3a_decision_lock.py", False),
    ("project/run_stage125_part3a_decision_lock.py", False),
    ("project/tests/test_stage125_part3a_decision_lock.py", False),
    ("project/stage125/part3a_decision_lock_stage125.json", False),
    # prefix attacks must be rejected
    ("AGENTS.md.evil", False),
    ("project/scripts/update_ai_handoff.py.bak", False),
    ("project/docs/ai-evil/x.md", False),
    ("project/docs/aimalicious", False),
    ("project/src/secret.py", False),
])
def test_handoff_only_classification(path, ok):
    assert gen.path_handoff_only(path) is ok


def test_handoff_only_disjoint_from_stage125_code():
    # Change allowlist accepts Stage125 Part 1 code; handoff-only does not.
    for p in (
        "project/src/stage125_part1_data_contract.py",
        "project/run_stage125_part1.py",
        "project/tests/test_stage125_part1_data_contract.py",
        "project/stage125/data_dictionary_stage125.csv",
    ):
        assert gen.path_allowlisted(p) is True
        assert gen.path_handoff_only(p) is False


# --------------------------------------------------------------------------- #
# Generated-artifact-only classification (independent of path_allowlisted AND
# path_handoff_only) — pure unit
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path,ok", [
    # Known generated QC-report / metadata_and_hashes outputs ARE artifact-only.
    ("project/stage124/stage124_batch02_gate_b_qc_report.json", True),
    ("project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json", True),
    ("project/stage125/metadata_and_hashes_stage125_part2.json", True),
    ("project/stage125/stage125_part2_prediction_time_contract_qc_report.json", True),
    ("project/stage125/metadata_and_hashes_stage125_part3a.json", True),
    ("project/stage125/stage125_part3a_pilot_protocol_qc_report.json", True),
    ("project/stage125/README_STAGE125_PART3A_PILOT_PROTOCOL.md", True),
    ("project/stage125/accessibility_scoring_rubric_stage125_part3a.json", True),
    ("project/stage125/part3_candidate_inventory_stage125.csv", True),
    ("project/stage125/part3_gate_decision_protocol_stage125.csv", True),
    ("project/stage125/part3_pilot_sampling_options_stage125.csv", True),
    ("project/stage125/part3_sampling_frame_by_target_year_stage125.csv", True),
    ("project/stage125/part3_sampling_frame_summary_stage125.json", True),
    ("project/stage125/part3_source_evidence_manifest_schema_stage125.json", True),
    # Stage125 Part 3A.1 generated decision-lock artifacts
    ("project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json", True),
    ("project/stage125/stage125_part3a_decision_lock_qc_report.json", True),
    ("project/stage125/README_STAGE125_PART3A_DECISION_LOCK.md", True),
    ("project/stage125/part3a_decision_lock_stage125.json", True),
    ("project/stage125/part3a_approved_gate_thresholds_stage125.csv", True),
    ("project/stage125/part3a_selected_pilot_pairs_stage125.csv", True),
    ("project/stage122/metadata_and_hashes_stage122.json", True),
    ("project/stage123/stage123_qc_report.json", True),
    # Real research/contract deliverables under the SAME directories are NOT
    # artifact-only, even though they sit next to generated bookkeeping files.
    ("project/stage125/prediction_time_contract_stage125_part2.json", False),
    ("project/stage125/data_dictionary_stage125.csv", False),
    ("project/stage124/listing_master_verified_stage124.csv", False),
    ("project/stage124/gate_b_final/modeling_main_rule_a_eligible.csv", False),
    # Handoff-only / source / test paths are NOT artifact-only.
    ("project/docs/ai/CURRENT_STATE.md", False),
    ("project/scripts/update_ai_handoff.py", False),
    ("project/tests/test_ai_handoff.py", False),
    ("project/src/stage124_gate_b_execution.py", False),
    ("project/tests/test_stage124_gate_b_execution.py", False),
    ("AGENTS.md", False),
    # prefix / suffix attacks must be rejected
    ("project/stage124/stage124_batch02_gate_b_qc_report.json.bak", False),
    ("project/stage125/metadata_and_hashes_stage125_part2.json.evil", False),
    ("project/stage125/metadata_and_hashes_stage125_part3a.json.evil", False),
    ("project/stage125/part3_candidate_inventory_stage125.csv.evil", False),
    ("project/stage125/sub/part3_candidate_inventory_stage125.csv", False),
    ("project/stage125/part3a_decision_lock_stage125.json.bak", False),
    ("project/stage125/part3a_selected_pilot_pairs_stage125.csv.evil", False),
    ("project/stage125/sub/part3a_decision_lock_stage125.json", False),
    ("project/stage125/sub/metadata_and_hashes_stage125_part2.json", False),
])
def test_artifact_only_classification(path, ok):
    assert gen.path_artifact_only(path) is ok


def test_artifact_only_independent_of_allowlist_and_handoff_only():
    # A file can be change-allowlisted (Stage125 dir) without being
    # artifact-only, and an artifact-only file is never handoff-only.
    contract_path = "project/stage125/prediction_time_contract_stage125_part2.json"
    assert gen.path_allowlisted(contract_path) is True
    assert gen.path_artifact_only(contract_path) is False

    for p in gen.ARTIFACT_ONLY_FILES:
        assert gen.path_handoff_only(p) is False


# --------------------------------------------------------------------------- #
# Dependency-contract maintenance-only classification (independent of
# path_allowlisted, path_handoff_only, and path_artifact_only) — pure unit
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path,ok", [
    ("project/environment.yml", True),
    ("project/requirements.txt", True),
    ("project/tests/test_dependency_contract.py", True),
    # prefix / suffix attacks must be rejected
    ("project/environment.yml.bak", False),
    ("project/requirements.txt.evil", False),
    ("project/tests/test_dependency_contract.py.bak", False),
    ("project/tests/sub/test_dependency_contract.py", False),
    # real research / Handoff / artifact paths are NOT maintenance-only
    ("project/src/stage125_part3a_decision_lock.py", False),
    ("project/docs/ai/CURRENT_STATE.md", False),
    ("project/stage125/stage125_part3a_decision_lock_qc_report.json", False),
])
def test_maintenance_only_classification(path, ok):
    assert gen.path_maintenance_only(path) is ok


def test_maintenance_only_disjoint_from_handoff_and_artifact():
    for p in gen.MAINTENANCE_ONLY_FILES:
        assert gen.path_handoff_only(p) is False
        assert gen.path_artifact_only(p) is False


def test_dependency_contract_full_commit_is_skipped(synth):
    before = gen.last_stage_commit(synth)
    for rel in gen.MAINTENANCE_ONLY_FILES:
        _write(synth, rel, "pinned\n")
    sha = _commit(synth, "Stage125: dependency contract refresh")
    assert gen.last_stage_commit(synth) == before
    assert gen.last_stage_commit(synth) != sha


def test_single_maintenance_file_commit_is_skipped(synth):
    before = gen.last_stage_commit(synth)
    _write(synth, "project/requirements.txt", "jdatetime==6.0.1\n")
    sha = _commit(synth, "fix(deps): pin jdatetime")
    assert gen.last_stage_commit(synth) == before
    assert gen.last_stage_commit(synth) != sha


def test_mixed_maintenance_and_stage_source_commit_advances(synth):
    before = gen.last_stage_commit(synth)
    _write(synth, "project/environment.yml", "python=3.13.5\n")
    _write(synth, "project/src/stage125_part3a_decision_lock.py", "GUARD = 2\n")
    sha = _commit(synth, "fix(part3a1): runtime pin plus guard update")
    got = gen.last_stage_commit(synth)
    assert got == sha
    assert got != before


# --------------------------------------------------------------------------- #
# Synthetic repo for semantic-drift tests
# --------------------------------------------------------------------------- #

STAGE = "stage9_batch1_part0"          # digit-bearing -> Stage9 / Batch1


def _commit(root: str, subject: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "-C", root, "add", "-A"], check=True, env=env,
                   capture_output=True, text=True)
    subprocess.run(["git", "-C", root, "commit", "-m", subject], check=True, env=env,
                   capture_output=True, text=True)
    return _git(root, "rev-parse", "HEAD")


def _write(root: str, rel: str, content: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


@pytest.fixture
def synth(tmp_path, monkeypatch):
    """A synthetic repo with a valid, committed handoff package."""
    root = str(tmp_path / "repo")
    os.makedirs(root)
    _git(root, "init")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")

    src = "STAGE_SRC = 1\n"
    test = "def test_ok():\n    assert True\n"
    _write(root, f"project/src/{STAGE}.py", src)
    _write(root, f"project/tests/test_{STAGE}.py", test)

    # Frozen manifests + tracked data files (frozen) + a regenerable log file.
    for s in ("stage122", "stage123"):
        data = f"frozen {s}\n"
        _write(root, f"project/{s}/data_{s}.csv", data)
    log = "log line\n"
    _write(root, "project/stage123/log_stage123.txt", log)
    _write(root, "project/stage122/metadata_and_hashes_stage122.json", json.dumps(
        {"stage": "stage122", "output_files_sha256": {"data_stage122.csv": _sha("frozen stage122\n")}}))
    _write(root, "project/stage123/metadata_and_hashes_stage123.json", json.dumps(
        {"stage": "stage123", "output_files_sha256": {
            "data_stage123.csv": _sha("frozen stage123\n"),
            "log_stage123.txt": _sha(log)}}))

    _write(root, "project/docs/ai/ROADMAP.md",
           "---\n"
           "roadmap_version: 1\n"
           f"active_research_workstream_id: {STAGE}\n"
           f"last_completed_research_action_id: stage9-a-1\n"
           f"next_research_action_id: stage9-a-2\n"
           "active_maintenance_task_id: handoff\n"
           "---\n\n"
           "## Research actions\n\n"
           "1. `stage9-a-1` done\n"
           "2. `stage9-a-2` next\n")

    monkeypatch.setattr(gen, "FROZEN_MANIFESTS", (
        "project/stage122/metadata_and_hashes_stage122.json",
        "project/stage123/metadata_and_hashes_stage123.json",
    ))
    # log_stage123.txt is tracked & in the manifest, but classified regenerable.
    monkeypatch.setattr(gen, "NON_FROZEN_TRACKED", {"project/stage123/log_stage123.txt"})

    sha1 = _commit(root, f"Stage1 Part initial: {STAGE} code")

    _write(root, f"project/qc/{STAGE}_qc_report.json", json.dumps({
        "stage": STAGE,
        "generated_at": "2026-01-01T00:00:00Z",
        "source_commit": sha1,
        "source_file_sha256": _sha(src),
        "test_file_sha256": _sha(test),
        "ticker_count": 2,
        "tickers": ["AAA", "BBB"],
        "all_pass": True,
        "assertion_count": 3,
        "failed_count": 0,
    }))
    _commit(root, f"Stage1 Part artifacts: {STAGE} QC")

    outputs = gen.generate(root)
    for rel, content in outputs.items():
        _write(root, rel, content)
    _commit(root, "handoff: generate package")

    assert val.run_check(root) == 0  # baseline must be valid
    return root


# ---- the 7 plan scenarios -------------------------------------------------- #

def test_scenario1_handoff_only_commit_ok(synth):
    _write(synth, "AGENTS.md", "pointer tweak\n")
    _commit(synth, "handoff: tweak AGENTS pointer")
    assert val.run_check(synth) == 0


def test_scenario2_stage_source_change_fails(synth):
    _write(synth, f"project/src/{STAGE}.py", "STAGE_SRC = 999\n")
    _commit(synth, "Stage1 Part: tamper source")
    assert val.run_check(synth) == 1


def test_scenario3_qc_test_file_change_fails(synth):
    _write(synth, f"project/tests/test_{STAGE}.py", "def test_ok():\n    assert 1 == 1\n")
    _commit(synth, "Stage1 Part: tamper test")
    assert val.run_check(synth) == 1


def test_scenario4_frozen_asset_change_fails(synth):
    _write(synth, "project/stage122/data_stage122.csv", "TAMPERED\n")
    _commit(synth, "Stage1 Part: tamper frozen asset")
    assert val.run_check(synth) == 1


def test_scenario5_roadmap_id_change_without_regen_fails(synth):
    text = open(os.path.join(synth, "project/docs/ai/ROADMAP.md"), encoding="utf-8").read()
    text = text.replace("stage9-a-2", "stage9-a-3")
    text = text.replace("2. `stage9-a-3` next", "2. `stage9-a-2` mid\n3. `stage9-a-3` next")
    _write(synth, "project/docs/ai/ROADMAP.md", text)
    _commit(synth, "handoff: bump roadmap next id (no regen)")
    assert val.run_check(synth) == 1


def test_scenario6_new_stage_commit_fails(synth):
    _write(synth, "project/qc/extra_note.txt", "more research\n")
    _commit(synth, "Stage2 Part new: extra research output")
    assert val.run_check(synth) == 1


def test_scenario7_timestamp_only_change_keeps_fingerprint(synth):
    fp_before = _state(synth)["state_fingerprint"]
    outputs = gen.generate(synth)
    fresh = json.loads(outputs["project/docs/ai/handoff_state.json"])
    assert fresh["state_fingerprint"] == fp_before
    assert fresh["generated_at_utc"] is not None
    assert val.run_check(synth) == 0


# ---- hardening tests (item 8) --------------------------------------------- #

def test_frozen_mismatch_is_fatal(synth):
    # Uncommitted tamper of a FROZEN (non-regenerable) file -> generation fatal.
    _write(synth, "project/stage122/data_stage122.csv", "TAMPERED\n")
    with pytest.raises(gen.HandoffError):
        gen.semantic_state(synth)
    assert val.run_check(synth) == 1


def test_regenerable_mismatch_not_fatal(synth):
    # Uncommitted tamper of the regenerable log file -> still valid.
    _write(synth, "project/stage123/log_stage123.txt", "different timing line\n")
    gen.semantic_state(synth)            # must not raise
    assert val.run_check(synth) == 0


def test_merge_commit_with_research_file_fails(synth):
    base = _git(synth, "rev-parse", "--abbrev-ref", "HEAD")
    _git(synth, "checkout", "-b", "side")
    _write(synth, "project/src/new_research.py", "RESEARCH = 1\n")
    _commit(synth, "research: add new module")
    _git(synth, "checkout", base)
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", synth, "merge", "--no-ff", "-m", "Merge research", "side"],
                   check=True, env=env, capture_output=True, text=True)
    # The merge introduces a non-Handoff file -> commit-anchor check fails.
    assert val.run_check(synth) == 1


# ---- transparent GitHub-style HEAD merge (real two-parent commits) --------- #

def _set_state_field(root: str, key: str, value) -> None:
    path = os.path.join(root, "project/docs/ai/handoff_state.json")
    state = json.load(open(path, encoding="utf-8"))
    state[key] = value
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def _merge_no_ff(root: str, branch: str, message: str = "Merge branch") -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(
        ["git", "-C", root, "merge", "--no-ff", "-m", message, branch],
        check=True, env=env, capture_output=True, text=True,
    )
    return _git(root, "rev-parse", "HEAD")


def _github_style_merge_onto_base(root: str, base_sha: str, pr_branch: str = "pr-head") -> str:
    """Create a real two-parent merge: first=base_sha, second=current tip, tree=tip."""
    tip = _git(root, "rev-parse", "HEAD")
    _git(root, "branch", pr_branch, tip)
    _git(root, "checkout", "-B", "main", base_sha)
    return _merge_no_ff(root, pr_branch, f"Merge branch '{pr_branch}'")


def _pr_merge_base(root: str) -> str:
    """GitHub-like main tip: first parent of the tip handoff commit.

    Using the pre-handoff parent (not the repo root) keeps ``last_stage_commit``
    stable across a transparent merge, matching real PR merges onto main.
    """
    return _git(root, "rev-parse", "HEAD^")


def test_transparent_head_merge_accepted(synth):
    # Transparent HEAD merge: two parents, tree identical to second parent,
    # generated_from_commit ancestor of second parent, baseline ancestor of
    # first parent => accepted (ordinary non-Handoff rejection still intact).
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    merge_sha = _github_style_merge_onto_base(synth, base_sha)
    # baseline_commit is volatile; set on disk after merge (survives checkout).
    _set_state_field(synth, "baseline_commit", base_sha)
    head = _git(synth, "rev-parse", "HEAD")
    assert merge_sha == head
    parents = val._commit_parents(synth, merge_sha)
    assert len(parents) == 2
    assert val._commit_tree(synth, merge_sha) == val._commit_tree(synth, parents[1])
    assert gen.is_ancestor(synth, gfc, parents[1])
    assert gen.is_ancestor(synth, base_sha, parents[0])
    assert not gen._git(synth, "diff", "--name-only", parents[1], merge_sha).strip()
    assert val._is_transparent_head_merge(
        synth, merge_sha, head, gfc, base_sha
    ) is True
    assert val.run_check(synth) == 0


def test_merge_with_manual_resolution_tree_diff_rejected(synth):
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    merge_sha = _github_style_merge_onto_base(synth, base_sha)
    _set_state_field(synth, "baseline_commit", base_sha)
    # Manual resolution / tree drift vs second parent, keeping a two-parent HEAD.
    parents = val._commit_parents(synth, merge_sha)
    _write(synth, "project/docs/ai/OPEN_TASKS.md", "manual merge resolution\n")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "-C", synth, "add", "-A"], check=True, env=env,
                   capture_output=True, text=True)
    tree = _git(synth, "write-tree")
    new_merge = subprocess.run(
        ["git", "-C", synth, "commit-tree", tree, "-p", parents[0], "-p", parents[1],
         "-m", "Merge with manual resolution"],
        check=True, capture_output=True, text=True, env=env,
    ).stdout.strip()
    _git(synth, "reset", "--hard", new_merge)
    _set_state_field(synth, "baseline_commit", base_sha)
    head = _git(synth, "rev-parse", "HEAD")
    assert val._commit_tree(synth, head) != val._commit_tree(synth, parents[1])
    assert val._is_transparent_head_merge(
        synth, head, head, gfc, base_sha
    ) is False
    assert val.run_check(synth) == 1
    errors: list[str] = []
    val._check_commit_anchors(synth, _state(synth), errors)
    assert any("non-transparent merge" in e for e in errors), errors


def test_transparent_looking_merge_not_head_rejected(synth):
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    merge_sha = _github_style_merge_onto_base(synth, base_sha)
    _set_state_field(synth, "baseline_commit", base_sha)
    assert val.run_check(synth) == 0
    # A further Handoff-only commit makes the prior merge no longer HEAD.
    _write(synth, "AGENTS.md", "post-merge pointer\n")
    _commit(synth, "handoff: post-merge pointer")
    _set_state_field(synth, "baseline_commit", base_sha)
    head = _git(synth, "rev-parse", "HEAD")
    assert merge_sha != head
    assert val._is_transparent_head_merge(
        synth, merge_sha, head, gfc, base_sha
    ) is False
    assert val.run_check(synth) == 1
    errors: list[str] = []
    val._check_commit_anchors(synth, _state(synth), errors)
    assert any("non-transparent merge" in e for e in errors), errors


def test_merge_gfc_not_in_second_parent_ancestry_rejected(synth):
    # Build a real two-parent merge whose second parent is an orphan commit
    # that does not contain generated_from_commit in its ancestry.
    tip = _git(synth, "rev-parse", "HEAD")
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    blob = subprocess.run(
        ["git", "-C", synth, "hash-object", "-w", "--stdin"],
        input="orphan\n", check=True, capture_output=True, text=True,
    ).stdout.strip()
    orphan_tree = subprocess.run(
        ["git", "-C", synth, "mktree"],
        input=f"100644 blob {blob}\tunrelated.txt\n",
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    unrelated = subprocess.run(
        ["git", "-C", synth, "commit-tree", orphan_tree, "-m", "orphan: unrelated tip"],
        check=True, capture_output=True, text=True, env=env,
    ).stdout.strip()
    merge_sha = subprocess.run(
        ["git", "-C", synth, "commit-tree", orphan_tree,
         "-p", base_sha, "-p", unrelated, "-m", "Merge unrelated orphan"],
        check=True, capture_output=True, text=True, env=env,
    ).stdout.strip()
    _git(synth, "reset", "--hard", merge_sha)
    # Restore a readable handoff_state on disk from the pre-merge tip (volatile
    # gfc overridden below); keep baseline valid for first parent.
    subprocess.run(
        ["git", "-C", synth, "checkout", tip, "--", "project/docs/ai/handoff_state.json"],
        check=True, capture_output=True, text=True,
    )
    # Use first parent as gfc so the ancestry-of-HEAD gate passes, but
    # second-parent ancestry fails.
    _set_state_field(synth, "generated_from_commit", base_sha)
    _set_state_field(synth, "baseline_commit", base_sha)
    head = _git(synth, "rev-parse", "HEAD")
    parents = val._commit_parents(synth, head)
    assert parents == [base_sha, unrelated]
    assert gen.is_ancestor(synth, base_sha, head)
    assert not gen.is_ancestor(synth, base_sha, unrelated)
    assert not gen.is_ancestor(synth, gfc, unrelated)
    assert val._is_transparent_head_merge(
        synth, head, head, base_sha, base_sha
    ) is False
    errors: list[str] = []
    val._check_commit_anchors(synth, _state(synth), errors)
    assert any("non-transparent merge" in e for e in errors), errors
    assert val.run_check(synth) == 1


def test_merge_baseline_not_in_first_parent_ancestry_rejected(synth):
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    merge_sha = _github_style_merge_onto_base(synth, base_sha)
    # Baseline points at the second parent (PR tip), not an ancestor of first.
    parents = val._commit_parents(synth, merge_sha)
    bad_baseline = parents[1]
    _set_state_field(synth, "baseline_commit", bad_baseline)
    assert not gen.is_ancestor(synth, bad_baseline, parents[0])
    head = _git(synth, "rev-parse", "HEAD")
    assert val._is_transparent_head_merge(
        synth, merge_sha, head, gfc, bad_baseline
    ) is False
    assert val.run_check(synth) == 1
    errors: list[str] = []
    val._check_commit_anchors(synth, _state(synth), errors)
    assert any("non-transparent merge" in e for e in errors), errors


def test_multiple_merge_commits_after_gfc_rejected(synth):
    gfc = _state(synth)["generated_from_commit"]
    base_sha = _pr_merge_base(synth)
    # First merge onto base.
    _github_style_merge_onto_base(synth, base_sha, pr_branch="pr-a")
    _set_state_field(synth, "baseline_commit", base_sha)
    assert val.run_check(synth) == 0
    # Second merge: create another side branch tip and merge again.
    _git(synth, "checkout", "-b", "pr-b")
    _write(synth, "AGENTS.md", "second pr tip\n")
    _commit(synth, "handoff: second pr tip")
    _git(synth, "checkout", "main")
    _merge_no_ff(synth, "pr-b", "Merge branch 'pr-b'")
    _set_state_field(synth, "baseline_commit", base_sha)
    # gfc still the original handoff tip; two merges exist in (gfc, HEAD].
    head = _git(synth, "rev-parse", "HEAD")
    between = gen._git(synth, "rev-list", f"{gfc}..{head}").splitlines()
    merge_count = sum(1 for sha in between if len(val._commit_parents(synth, sha)) >= 2)
    assert merge_count >= 2
    assert val.run_check(synth) == 1


def test_ordinary_non_handoff_after_gfc_still_rejected(synth):
    # Ordinary non-Handoff detection must remain intact beside merge handling.
    _write(synth, "project/src/extra_module.py", "X = 1\n")
    _commit(synth, "research: ordinary non-handoff after gfc")
    assert val.run_check(synth) == 1
    errors: list[str] = []
    val._check_commit_anchors(synth, _state(synth), errors)
    assert any("non-Handoff commit" in e for e in errors), errors


def test_handoff_only_after_gfc_still_accepted(synth):
    _write(synth, "AGENTS.md", "pointer still handoff-only\n")
    _commit(synth, "handoff: ordinary handoff-only after gfc")
    assert val.run_check(synth) == 0


@pytest.mark.parametrize("field,value", [
    ("current_stage", "Stage999"),
    ("current_batch", "Batch99"),
    ("tickers", ["ZZZ"]),
])
def test_tampered_record_field_fails(synth, field, value):
    path = os.path.join(synth, "project/docs/ai/handoff_state.json")
    state = json.load(open(path, encoding="utf-8"))
    state[field] = value
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, sort_keys=True)
    assert val.run_check(synth) == 1


def test_docs_ai_commit_stays_handoff_only(synth):
    # A commit touching only project/docs/ai/ is handoff-only -> skipped, so
    # last_stage_commit does not advance to it and the package stays valid.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/docs/ai/OPEN_TASKS.md", "note tweak\n")
    _commit(synth, "handoff: tweak open tasks")
    assert gen.last_stage_commit(synth) == before
    assert val.run_check(synth) == 0


def test_stage125_part1_code_commit_advances_stage(synth):
    # A Stage125-Part1-style code commit is change-allowlisted but NOT
    # handoff-only, so last_stage_commit MUST recognise it.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/src/stage125_part1_data_contract.py", "CONTRACT = 1\n")
    sha = _commit(synth, "Stage125 Part1: implement data contract")
    assert gen.path_allowlisted("project/src/stage125_part1_data_contract.py") is True
    got = gen.last_stage_commit(synth)
    assert got == sha
    assert got != before


def test_real_content_commit_advances_regardless_of_missing_stage_wording(synth):
    # PATH-BASED / SEMANTIC recognition: a commit that introduces a real
    # (non-Handoff-only, non-artifact-only) file MUST advance last_stage_commit
    # even when its message contains NO "Stage"/"Part" wording at all.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/stage125/data_dictionary_stage125.csv", "col\n")
    sha = _commit(synth, "artifact: refresh generated data dictionary")
    got = gen.last_stage_commit(synth)
    assert got == sha
    assert got != before


# ---- BLOCKER 1: artifact-only classification must not depend on wording ---- #

def test_generated_artifact_only_commit_with_stage_wording_is_skipped(synth):
    # Reproduces the real-repo bug: a commit that ONLY regenerates a known
    # generated QC/metadata artifact must be skipped even though its message
    # contains "Stage125 Part 2" (or any Stage/Part wording).
    before = gen.last_stage_commit(synth)
    _write(synth, "project/stage125/metadata_and_hashes_stage125_part2.json",
           json.dumps({"stage": "stage125_part2", "output_files_sha256": {}}))
    sha = _commit(
        synth,
        "artifacts(stage125-part2): regenerate QC/metadata after Stage125 Part 2 hash change",
    )
    got = gen.last_stage_commit(synth)
    assert got == before
    assert got != sha


def test_generated_artifact_only_commit_without_stage_wording_is_also_skipped(synth):
    # The artifact-only classification must be equally wording-INDEPENDENT in
    # the other direction: a purely generated artifact commit stays skipped
    # even when its message has NO Stage/Part wording at all.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/stage125/metadata_and_hashes_stage125_part2.json",
           json.dumps({"stage": "stage125_part2", "output_files_sha256": {}}))
    sha = _commit(synth, "chore: bump generated hash manifest")
    got = gen.last_stage_commit(synth)
    assert got == before
    assert got != sha


# ---- BLOCKER A: last_stage_commit must be PATH-BASED, not wording-based --- #

def test_code_and_test_commit_advances_with_no_stage_wording_in_message(synth):
    # Requirement: a commit changing real source + test files must be
    # recognised as stage-relevant even when its message is a plain
    # conventional-commit subject with NO "Stage"/"Part" anywhere.
    _write(synth, "project/src/stage124_gate_b_execution.py", "GUARDRAIL = 1\n")
    _write(synth, "project/tests/test_stage124_gate_b_execution.py",
           "def test_guardrail():\n    assert True\n")
    sha = _commit(synth, "fix(qc-scan): recursive nested-artifact detection")
    assert gen.last_stage_commit(synth) == sha


def test_stage124_code_test_commit_advances_last_stage_commit(synth):
    # The same real code/test change also advances last_stage_commit when its
    # message DOES happen to mention "Stage124" — wording must be irrelevant
    # either way.
    _write(synth, "project/src/stage124_gate_b_execution.py", "GUARDRAIL = 1\n")
    _write(synth, "project/tests/test_stage124_gate_b_execution.py",
           "def test_guardrail():\n    assert True\n")
    sha = _commit(
        synth,
        "fix(stage124): modeling-guardrail - contract dir is not a modeling artifact",
    )
    assert gen.last_stage_commit(synth) == sha


@pytest.mark.parametrize("subject", [
    "fix(stage124): guardrail fix plus regenerated QC artifact (Stage124 Part)",
    "fix(qc-scan): guardrail fix plus regenerated QC artifact",
])
def test_mixed_source_and_artifact_commit_advances(synth, subject):
    # A commit that introduces BOTH a real code file AND a generated artifact
    # file must NOT be misclassified as artifact-only; it must still advance
    # last_stage_commit — regardless of whether the message mentions
    # "Stage"/"Part" or not.
    _write(synth, "project/src/stage124_gate_b_execution.py", "GUARDRAIL = 2\n")
    _write(synth, "project/stage124/stage124_batch02_gate_b_qc_report.json",
           json.dumps({"stage": "stage124_gate_b_execution"}))
    sha = _commit(synth, subject)
    assert gen.last_stage_commit(synth) == sha


@pytest.mark.parametrize("subject", [
    "handoff: Stage125 Part 2 open-tasks tweak",
    "handoff: tweak open tasks",
])
def test_handoff_only_commits_remain_skipped_alongside_artifact_only(synth, subject):
    # Handoff-only classification must keep working regardless of message
    # wording, both after the artifact-only classification was added and
    # after last_stage_commit became fully path-based.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/docs/ai/OPEN_TASKS.md", "note tweak\n")
    _commit(synth, subject)
    assert gen.last_stage_commit(synth) == before


def test_is_stage_relevant_unit():
    # Direct unit coverage of the classification primitive itself.
    assert gen._is_stage_relevant(["project/src/stage124_gate_b_execution.py"]) is True
    assert gen._is_stage_relevant(
        ["project/tests/test_stage124_gate_b_execution.py"]) is True
    assert gen._is_stage_relevant(["project/docs/ai/OPEN_TASKS.md"]) is False
    assert gen._is_stage_relevant(
        ["project/stage124/stage124_batch02_gate_b_qc_report.json"]) is False
    assert gen._is_stage_relevant([]) is False
    # Mixed: one real file is enough to qualify.
    assert gen._is_stage_relevant([
        "project/docs/ai/OPEN_TASKS.md",
        "project/src/stage124_gate_b_execution.py",
    ]) is True
    assert gen._is_stage_relevant([
        "project/docs/ai/OPEN_TASKS.md",
        "project/stage124/stage124_batch02_gate_b_qc_report.json",
    ]) is False


def test_change_allowlist_blocks_non_handoff(synth):
    base = _git(synth, "rev-parse", "HEAD")
    _write(synth, f"project/src/{STAGE}.py", "STAGE_SRC = 2\n")
    _commit(synth, "Stage1 Part: source edit")
    assert val.run_check_changes(synth, base, include_wt=True) == 1


# ---- correction-commit fixes --------------------------------------------- #

def test_atomic_write_rollback_restores_all(synth, monkeypatch):
    import glob
    files = list(gen.AUTO_FILES)
    originals = {f: open(os.path.join(synth, f), encoding="utf-8").read() for f in files}
    outputs = {f: f"NEW CONTENT for {f}\n" for f in files}

    real_replace = os.replace

    def flaky(src, dst, *a, **k):
        # Fail exactly on the risky tmp->target move of the 2nd auto file,
        # AFTER its backup has already been created.
        if str(dst).endswith(files[1]) and str(src).endswith(".handoff_tmp"):
            raise OSError("boom")
        return real_replace(src, dst, *a, **k)

    monkeypatch.setattr(gen.os, "replace", flaky)
    with pytest.raises(OSError):
        gen._atomic_write(synth, outputs)
    monkeypatch.undo()

    # Every original is intact (including the one whose replace failed).
    for f in files:
        assert open(os.path.join(synth, f), encoding="utf-8").read() == originals[f]
    # No stray backup/temp files left behind.
    d = os.path.join(synth, "project/docs/ai")
    assert glob.glob(os.path.join(d, "*.handoff_bak")) == []
    assert glob.glob(os.path.join(d, "*.handoff_tmp")) == []


def _add_manifest_entry(root: str, rel_file: str, content: str) -> None:
    _write(root, rel_file, content)
    manifest = os.path.join(root, "project/stage122/metadata_and_hashes_stage122.json")
    data = json.load(open(manifest, encoding="utf-8"))
    data["output_files_sha256"][os.path.basename(rel_file)] = _sha(content)
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def test_untracked_not_ignored_frozen_is_fatal(synth):
    # Untracked, NOT gitignored, NOT classified -> fatal even if content matches.
    _add_manifest_entry(synth, "project/stage122/extra_frozen.csv", "x\n")
    with pytest.raises(gen.HandoffError):
        gen.semantic_state(synth)


def test_untracked_but_ignored_is_regenerable(synth):
    _write(synth, ".gitignore", "project/stage122/ignored_out.csv\n")
    _add_manifest_entry(synth, "project/stage122/ignored_out.csv", "y\n")
    # Proven gitignored -> regenerable -> must NOT raise.
    gen.semantic_state(synth)


# ---- Stage125 Part 3A artifact-only + last_stage_commit regression -------- #

@pytest.mark.parametrize("path", [
    "project/stage125/README_STAGE125_PART3A_PILOT_PROTOCOL.md",
    "project/stage125/accessibility_scoring_rubric_stage125_part3a.json",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3_gate_decision_protocol_stage125.csv",
    "project/stage125/part3_pilot_sampling_options_stage125.csv",
    "project/stage125/part3_sampling_frame_by_target_year_stage125.csv",
    "project/stage125/part3_sampling_frame_summary_stage125.json",
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json",
])
def test_stage125_part3a_generated_files_are_artifact_only(path):
    assert gen.path_artifact_only(path) is True
    assert gen.path_handoff_only(path) is False


@pytest.mark.parametrize("path", [
    "project/stage125/part3_candidate_inventory_stage125.csv.bak",
    "project/stage125/part3_candidate_inventory_stage125.csv.evil",
    "project/stage125/sub/part3_pilot_sampling_options_stage125.csv",
    "project/stage125/part3_gate_decision_protocol_stage125.csv~",
])
def test_stage125_part3a_artifact_prefix_suffix_attacks_rejected(path):
    assert gen.path_artifact_only(path) is False


def test_stage125_part3a_full_artifact_commit_is_skipped(synth):
    before = gen.last_stage_commit(synth)
    for rel in (
        "project/stage125/part3_candidate_inventory_stage125.csv",
        "project/stage125/part3_pilot_sampling_options_stage125.csv",
        "project/stage125/stage125_part3a_pilot_protocol_qc_report.json",
        "project/stage125/metadata_and_hashes_stage125_part3a.json",
    ):
        _write(synth, rel, "generated\n")
    sha = _commit(synth, "artifacts: freeze Stage125 Part3A pilot protocol")
    assert gen.last_stage_commit(synth) == before
    assert gen.last_stage_commit(synth) != sha


def test_stage125_part3a_mixed_code_and_artifact_commit_advances(synth):
    before = gen.last_stage_commit(synth)
    _write(synth, "project/src/stage125_part3a_pilot_protocol.py", "GUARD = 1\n")
    _write(synth, "project/stage125/metadata_and_hashes_stage125_part3a.json",
           json.dumps({"stage": "stage125_part3a"}))
    sha = _commit(synth, "fix(part3a): guard update plus regenerated metadata")
    got = gen.last_stage_commit(synth)
    assert got == sha
    assert got != before


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_real_repo_dependency_maintenance_merge_is_excluded():
    # Regression: dependency-only maintenance merges (e.g. PR #33) must not
    # advance the research-stage anchor. This test pins the historical
    # dependency merge as excluded; it does NOT freeze the latest stage SHA.
    dep_merge = "167be6c68264cb04722da26f7fbbf527d67e1230"
    head = gen.head_commit(REAL_ROOT)
    assert gen.is_ancestor(REAL_ROOT, dep_merge, head)

    dep_files = gen._introduced_files(REAL_ROOT, dep_merge)
    assert dep_files
    assert set(dep_files) == set(gen.MAINTENANCE_ONLY_FILES)
    assert gen._is_maintenance_only(dep_files)
    assert all(gen.path_maintenance_only(p) for p in dep_files)
    assert not gen._is_stage_relevant(dep_files)

    assert gen.last_stage_commit(REAL_ROOT) != dep_merge


# ---- Stage125 Part 3A.1 artifact-only + last_stage_commit regression -------- #

@pytest.mark.parametrize("path", [
    "project/stage125/README_STAGE125_PART3A_DECISION_LOCK.md",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
])
def test_stage125_part3a1_generated_files_are_artifact_only(path):
    assert gen.path_artifact_only(path) is True
    assert gen.path_handoff_only(path) is False


@pytest.mark.parametrize("path", [
    "project/stage125/part3a_decision_lock_stage125.json.bak",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv.evil",
    "project/stage125/sub/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv~",
])
def test_stage125_part3a1_artifact_prefix_suffix_attacks_rejected(path):
    assert gen.path_artifact_only(path) is False


def test_stage125_part3a1_full_artifact_commit_is_skipped(synth):
    before = gen.last_stage_commit(synth)
    for rel in (
        "project/stage125/stage125_part3a_decision_lock_qc_report.json",
        "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json",
        "project/stage125/part3a_decision_lock_stage125.json",
        "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
        "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
        "project/stage125/README_STAGE125_PART3A_DECISION_LOCK.md",
    ):
        _write(synth, rel, "generated\n")
    sha = _commit(synth, "artifacts: Stage125 Part3A.1 decision lock")
    got = gen.last_stage_commit(synth)
    assert got == before
    assert got != sha


def test_stage125_part3a1_mixed_code_and_artifact_commit_advances(synth):
    before = gen.last_stage_commit(synth)
    _write(synth, "project/src/stage125_part3a_decision_lock.py", "GUARD = 1\n")
    _write(synth, "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json",
           json.dumps({"stage": "stage125_part3a_decision_lock"}))
    sha = _commit(synth, "fix(part3a1): guard update plus regenerated metadata")
    got = gen.last_stage_commit(synth)
    assert got == sha
    assert got != before


# ---- Part 3A.1 handoff workflow markers (Blocker 1) ------------------------ #

def test_extract_qc_workflow_markers_decision_lock_scope():
    qc = {
        "stage": "stage125_part3a_decision_lock",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got == {
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b_started": False,
    }


def test_extract_qc_workflow_markers_part3a_scope_without_decision_lock():
    qc = {
        "stage": "stage125_part3a_pilot_protocol",
        "part3a_protocol_locked": True,
        "part3b_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got == {
        "part3a_protocol_locked": True,
        "part3b_started": False,
    }
    assert "part3a_decision_locked" not in got


def test_extract_qc_workflow_markers_fail_closed_when_field_missing():
    qc = {
        "stage": "stage125_part3a_decision_lock",
        "part3a_protocol_locked": True,
        "part3b_started": False,
    }
    with pytest.raises(gen.HandoffError, match="part3a_decision_locked"):
        gen.extract_qc_workflow_markers(qc)


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_real_repo_handoff_part3b_workflow_markers():
    state = _state(REAL_ROOT)
    assert state["current_stage"] == "Stage126"
    # The newest completed robustness micro-part supplies the selected QC; the
    # research-action pointers deliberately stay on the Stage126 M1 action.
    assert state["selected_qc_scope"] == (
        "stage126_m1_robustness_part2_listing_rule_b"
    )
    assert state["last_completed_micro_part"] == (
        "stage126-m1-robustness-part2-listing-rule-b"
    )
    assert state["next_research_action_id"] == (
        "stage126-m1-financial-baseline"
    )
    assert state["active_workstream"] == "stage126_m1_financial_baseline"
    # Stage126 M1 is human-authorized and started; development-fold modeling
    # occurred, while the final test remains fully locked.
    assert state["stage125_completed"] is True
    assert state["stage126_m1_entry_ready"] is True
    assert state["stage126_authorized"] is True
    assert state["stage126_started"] is True
    assert state["development_modeling_authorized"] is True
    assert state["modeling_authorized"] is True
    assert state["modeling_started"] is True
    assert state["m1_primary_development_tuning_completed"] is True
    # Robustness Parts 1 and 2 have executed; the overall set is incomplete.
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is False
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["final_test_predictor_values_inspected"] is False
    assert state["final_test_target_values_inspected"] is False
    assert state["final_test_evaluation_performed"] is False
    assert state["m2_data_collected"] is False
    assert state["m3_data_collected"] is False
    assert state["m4_data_collected"] is False
    # Repository-wide temporal-availability invariants carried from Stage125.
    assert state["financial_data_researcher_verified_frozen"] is True
    assert state["broad_codal_capture_stopped"] is True
    assert state["active_availability_method"] == "fixed_regulatory_lag"
    assert state["active_availability_lag_months"] == 4
    assert state["four_month_regulatory_lag_locked"] is True
    assert state["six_month_lag_superseded"] is True
    assert state["historical_six_month_decision_retained"] is True
    assert state["row_level_publish_datetime_collection_required"] is False
    assert state["part3b_completed"] is False
    assert state["part3c_leakage_safe_finalization_completed"] is True
    assert state["part4_statistical_analysis_plan_locked"] is True


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_real_repo_roadmap_stage126_status_consistency():
    roadmap = open(
        os.path.join(REAL_ROOT, "project/docs/ai/ROADMAP.md"), encoding="utf-8",
    ).read()
    fm = gen.read_roadmap(REAL_ROOT)
    assert fm["active_research_workstream_id"] == (
        "stage126-m1-financial-baseline"
    )
    assert fm["last_completed_research_action_id"] == (
        "stage125-part5-readiness-closure"
    )
    assert fm["next_research_action_id"] == (
        "stage126-m1-financial-baseline"
    )
    # Isolate the Stage126 research-action row (item 18).
    match = re.search(
        r"18\.\s*`stage126-m1-financial-baseline`\s*—\s*([^\n]+)",
        roadmap,
    )
    assert match is not None, "Stage126 research-action row missing"
    stage126_row = match.group(1)
    stage126_row_l = stage126_row.lower()
    assert "human-authorized and started" in stage126_row_l
    # Stale unauthorized/future wording must not describe the Stage126 action.
    for banned in (
        "**future**",
        "blocked pending authorization",
        "blocked pending explicit human authorization",
        "a next-action pointer is not authorization",
    ):
        assert banned.lower() not in stage126_row_l, (
            f"Stage126 ROADMAP body still contains stale phrase {banned!r}"
        )
    # Whole-action "not started" (historical wording), not "robustness not started".
    assert re.search(r"(?<!robustness )\*\*not started\*\*", stage126_row_l) is None
    assert re.search(
        r";\s*\*\*not started\*\*", stage126_row_l,
    ) is None
    assert "future; blocked pending" not in stage126_row_l
    assert stage126_row_l.strip().startswith("**future**") is False


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_real_repo_open_tasks_stage126_markers_match_handoff():
    open_tasks = open(
        os.path.join(REAL_ROOT, "project/docs/ai/OPEN_TASKS.md"),
        encoding="utf-8",
    ).read()
    state = _state(REAL_ROOT)
    assert "## Active research workstream: `stage126-m1-financial-baseline`" in (
        open_tasks
    )
    assert "Stage126 M1 human-authorized = true" in open_tasks
    assert "Stage126 started = true" in open_tasks
    assert "development modeling authorized = true" in open_tasks
    assert "modeling started = true" in open_tasks
    assert "primary development tuning completed = true" in open_tasks
    # Derived from the Handoff rather than pinned, so the OPEN_TASKS marker
    # block cannot silently drift away from the real state as micro-parts
    # complete. Robustness has started (Parts 1 and 2) but is not complete.
    assert "M1 robustness started = {}".format(
        str(state["m1_robustness_started"]).lower()
    ) in open_tasks
    assert "M1 robustness completed = {}".format(
        str(state["m1_robustness_completed"]).lower()
    ) in open_tasks
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is False
    assert "final test unlocked = false" in open_tasks
    assert "M2/M3/M4 data collected = false" in open_tasks
    assert "historical state at Stage125 closure time" in open_tasks
    # Current markers section must agree with Handoff; historical false
    # Stage126 markers must not be presented as current.
    current_section = open_tasks.split("### Current Stage126 markers")[1].split(
        "**Still prohibited"
    )[0]
    assert "`stage126_authorized=true`" in current_section
    assert "`stage126_started=true`" in current_section
    assert "`modeling_authorized=true`" in current_section
    assert "`modeling_started=true`" in current_section
    assert "`stage126_authorized=false`" not in current_section
    assert "`stage126_started=false`" not in current_section
    assert state["stage126_authorized"] is True
    assert state["stage126_started"] is True
    assert state["modeling_authorized"] is True
    assert state["modeling_started"] is True
    assert state["m1_primary_development_tuning_completed"] is True
    assert state["active_availability_method"] == "fixed_regulatory_lag"
    assert state["active_availability_lag_months"] == 4
    # Active OPEN_TASKS must not describe current Stage126 as unauthorized.
    active_header = open_tasks.split("### Historical markers")[0]
    assert "future; not authorized" not in active_header.lower()
    assert "blocked pending explicit human authorization" not in (
        active_header.lower()
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("active_availability_method", "fixed_conservative_lag"),
        ("active_availability_lag_months", 6),
        ("four_month_regulatory_lag_locked", False),
        ("six_month_lag_superseded", False),
        ("financial_data_researcher_verified_frozen", False),
        ("broad_codal_capture_stopped", False),
        ("row_level_publish_datetime_collection_required", True),
        ("part3b_completed", True),
    ],
)
@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_stage126_temporal_availability_mutation_fails_closed(
    monkeypatch, field, value,
):
    state = _state(REAL_ROOT)
    assert field in state, f"expected carried invariant {field} in handoff_state"
    state = dict(state)
    state[field] = value
    monkeypatch.setattr(val, "_load_state", lambda _root: state)
    assert val.run_check(REAL_ROOT) == 1


@pytest.mark.parametrize(
    "field",
    [
        "active_availability_method",
        "active_availability_lag_months",
        "four_month_regulatory_lag_locked",
        "six_month_lag_superseded",
        "financial_data_researcher_verified_frozen",
        "broad_codal_capture_stopped",
        "row_level_publish_datetime_collection_required",
        "part3b_completed",
        "historical_six_month_decision_retained",
        "part3c_leakage_safe_finalization_completed",
        "part4_statistical_analysis_plan_locked",
        "stage125_completed",
    ],
)
@pytest.mark.skipif(
    not os.path.isdir(os.path.join(REAL_ROOT, ".git")),
    reason="real-repo test requires git checkout",
)
def test_stage126_temporal_availability_missing_fails_closed(monkeypatch, field):
    state = dict(_state(REAL_ROOT))
    assert field in state
    del state[field]
    monkeypatch.setattr(val, "_load_state", lambda _root: state)
    assert val.run_check(REAL_ROOT) == 1


def test_derive_stage125_temporal_availability_invariants_real_repo():
    if not os.path.isdir(os.path.join(REAL_ROOT, ".git")):
        pytest.skip("real-repo test requires git checkout")
    got = gen.derive_stage125_temporal_availability_invariants(REAL_ROOT)
    assert got == {
        "financial_data_researcher_verified_frozen": True,
        "broad_codal_capture_stopped": True,
        "active_availability_method": "fixed_regulatory_lag",
        "active_availability_lag_months": 4,
        "four_month_regulatory_lag_locked": True,
        "six_month_lag_superseded": True,
        "historical_six_month_decision_retained": True,
        "row_level_publish_datetime_collection_required": False,
        "part3b_completed": False,
        "part3c_leakage_safe_finalization_completed": True,
        "part4_statistical_analysis_plan_locked": True,
        "stage125_completed": True,
    }


# ---- Stage125 Part 3B.0 artifact-only + workflow markers ------------------- #

@pytest.mark.parametrize("path", [
    "project/stage125/README_STAGE125_PART3B0_EVIDENCE_READINESS.md",
    "project/stage125/part3b0_evidence_capture_contract_stage125.json",
    "project/stage125/part3b0_evidence_manifest_template_stage125.csv",
    "project/stage125/part3b0_gate_result_template_stage125.csv",
    "project/stage125/part3b0_immutable_cache_contract_stage125.json",
    "project/stage125/part3b0_network_denial_contract_stage125.json",
])
def test_stage125_part3b0_generated_files_are_artifact_only(path):
    assert gen.path_artifact_only(path) is True
    assert gen.path_handoff_only(path) is False


@pytest.mark.parametrize("path", [
    "project/stage125/README_STAGE125_PART3B_EVIDENCE_CAPTURE.md",
    "project/stage125/README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md",
    "project/stage125/part3b_authorization_stage125.json",
    "project/stage125/part3b_capture_plan_stage125.csv",
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv",
    "project/stage125/part3b_evidence_manifest_stage125.csv",
    "project/stage125/part3b_cache_handles_stage125.csv",
    "project/stage125/part3b_candidate_evidence_linkage_stage125.csv",
    "project/stage125/part3b_capture_attempt_log_stage125.csv",
    "project/stage125/part3b_capture_network_log_stage125.json",
    "project/stage125/part3b_pair_candidate_assessment_stage125.csv",
    "project/stage125/part3b_accessibility_scores_stage125.csv",
    "project/stage125/part3b_gate_results_stage125.csv",
    "project/stage125/part3b_gate_summary_stage125.json",
    "project/stage125/part3b_unresolved_and_failures_stage125.csv",
    "project/stage125/part3b_decision_requirements_stage125.json",
    "project/stage125/stage125_part3b_evidence_capture_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b.json",
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json",
    "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json",
    "project/stage125/part3b1_m4_feature_definition_contract_stage125.json",
    "project/stage125/part3b1_rubric_operational_mapping_stage125.json",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
    "project/stage125/part3b1_selected_decisions_stage125.csv",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1.json",
    "project/stage125/README_STAGE125_PART3B1A_CUT_A_AVAILABLE_AT_LOCK.md",
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1a.json",
    "project/stage125/README_STAGE125_PART3B1B_CODAL_DOCUMENT_BINDING.md",
    "project/stage125/part3b1b_predictor_document_scope_stage125.csv",
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv",
    "project/stage125/part3b1b_capture_attempt_log_stage125.csv",
    "project/stage125/part3b1b_network_log_stage125.json",
    "project/stage125/part3b1b_unresolved_and_rejections_stage125.csv",
    "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json",
    "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json",
    "project/stage125/stage125_part3b1b_codal_document_binding_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1b.json",
    "project/stage125/README_STAGE125_PART3B1C_DOCUMENT_BINDING_RESOLUTION.md",
    "project/stage125/part3b1c_binding_failure_taxonomy_stage125.csv",
    "project/stage125/part3b1c_identity_normalization_contract_stage125.json",
    "project/stage125/part3b1c_exact_document_evidence_hierarchy_stage125.json",
    "project/stage125/part3b1c_row_resolution_requirements_stage125.csv",
    "project/stage125/part3b1c_proposed_capture_authorization_stage125.json",
    "project/stage125/part3b1c_scale_up_readiness_decision_stage125.json",
    "project/stage125/part3b1c_document_binding_resolution_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1c_document_binding_resolution_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1c.json",
    "project/stage125/README_STAGE125_PART3B1E_CONSERVATIVE_LAG.md",
    "project/stage125/part3b1e_conservative_lag_decision_lock_stage125.json",
    "project/stage125/part3b1e_frozen_financial_data_manifest_stage125.json",
    "project/stage125/stage125_part3b1e_conservative_lag_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1e.json",
    "project/stage125/README_STAGE125_PART3C_LEAKAGE_SAFE_DATASET.md",
    "project/stage125/README_STAGE125_PART3C_FOUR_MONTH_LAG_REVISION.md",
    "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json",
    "project/stage125/part3c_four_month_regulatory_lag_revision_decision_stage125.json",
    "project/stage125/part3c_input_hash_manifest_stage125.json",
    "project/stage125/part3c_column_role_map_stage125.csv",
    "project/stage125/part3c_sample_summary_stage125.csv",
    "project/stage125/part3c_target_year_distribution_stage125.csv",
    "project/stage125/part3c_leakage_audit_stage125.csv",
    "project/stage125/stage125_part3c_leakage_safe_dataset_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3c.json",
    "project/stage125/README_STAGE125_PART4_STATISTICAL_ANALYSIS_PLAN.md",
    "project/stage125/part4_statistical_analysis_plan_stage125.json",
    "project/stage125/part4_feature_sets_stage125.csv",
    "project/stage125/part4_feature_exclusion_decisions_stage125.csv",
    "project/stage125/part4_sample_target_matrix_stage125.csv",
    "project/stage125/part4_temporal_split_contract_stage125.json",
    "project/stage125/part4_temporal_split_manifest_stage125.csv",
    "project/stage125/part4_event_count_gate_stage125.csv",
    "project/stage125/part4_development_feature_coverage_audit_stage125.csv",
    "project/stage125/part4_preprocessing_contract_stage125.json",
    "project/stage125/part4_model_specifications_stage125.json",
    "project/stage125/part4_hyperparameter_budget_stage125.json",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
    "project/stage125/part4_shap_stability_contract_stage125.json",
    "project/stage125/part4_revenue_growth_exclusion_revision_decision_stage125.json",
    "project/stage125/README_STAGE125_PART4_REVENUE_GROWTH_EXCLUSION_REVISION.md",
    "project/stage125/stage125_part4_statistical_analysis_plan_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part4.json",
    "project/stage125/README_STAGE125_PART5_READINESS_CLOSURE.md",
    "project/stage125/part5_readiness_closure_report_stage125.json",
    "project/stage125/part5_keep_drop_decisions_stage125.csv",
    "project/stage125/part5_blocker_register_stage125.csv",
    "project/stage125/part5_stage126_m1_entry_contract_stage125.json",
    "project/stage125/part5_artifact_integrity_manifest_stage125.csv",
    "project/stage125/stage125_part5_readiness_closure_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part5.json",
])
def test_stage125_part3b_generated_files_are_artifact_only(path):
    assert gen.path_artifact_only(path) is True
    assert gen.path_handoff_only(path) is False


def test_extract_qc_workflow_markers_part3b0_scope():
    qc = {
        "stage": "stage125_part3b0_evidence_readiness",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": False,
        "evidence_collected": False,
        "accessibility_scoring_applied": False,
        "network_extraction_performed": False,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["part3b0_readiness"] is True
    assert got["evidence_collected"] is False
    assert got["part3b_started"] is False


def test_extract_qc_workflow_markers_part3b_scope():
    qc = {
        "stage": "stage125_part3b_evidence_capture",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["part3b_started"] is True
    assert got["endpoint_probe_evidence_collected"] is True
    assert got["candidate_value_evidence_collected"] is False
    assert got["part3b_completed"] is False
    assert got["accessibility_scoring_applied"] is False
    assert got["modeling_started"] is False


def test_extract_qc_workflow_markers_part3b1_scope():
    qc = {
        "stage": "stage125_part3b1_decision_lock",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["part3b1_decision_locked"] is True
    assert got["part3b_completed"] is False
    assert got["candidate_value_evidence_collected"] is False
    assert got["modeling_started"] is False


def test_extract_qc_workflow_markers_part3b1a_scope():
    qc = {
        "stage": "stage125_part3b1a_cut_a_available_at_operationalization_lock",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["cut_a_available_at_operationalization_locked"] is True
    assert got["part3b1_decision_locked"] is True
    assert got["predictor_available_at_evidence_collected"] is False
    assert got["pilot_cutoff_provenance_resolved"] is False
    assert got["part3b_completed"] is False
    assert got["modeling_started"] is False


def test_qc_source_test_override_part3b1a():
    src, test = gen._qc_source_test_paths(
        "stage125_part3b1a_cut_a_available_at_operationalization_lock"
    )
    assert src.endswith(
        "stage125_part3b1a_cut_a_available_at_operationalization.py"
    )
    assert test.endswith(
        "test_stage125_part3b1a_cut_a_available_at_operationalization.py"
    )


def test_extract_qc_workflow_markers_part3b1b_scope():
    qc = {
        "stage": "stage125_part3b1b_codal_document_binding_mini_pilot",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["predictor_document_binding_mini_pilot_completed"] is True
    assert got["predictor_document_binding_evidence_collected"] is True
    assert got["predictor_available_at_evidence_collected"] is False
    assert got["part3b_completed"] is False
    assert got["modeling_started"] is False


def test_qc_source_test_override_part3b1b():
    src, test = gen._qc_source_test_paths(
        "stage125_part3b1b_codal_document_binding_mini_pilot"
    )
    assert src.endswith("stage125_part3b1b_codal_document_binding.py")
    assert test.endswith("test_stage125_part3b1b_codal_document_binding.py")


def test_extract_qc_workflow_markers_part3b1e_scope():
    qc = {
        "stage": "stage125_part3b1e_conservative_six_month_lag_decision_lock",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "document_binding_resolution_decision_locked": True,
        "conservative_six_month_lag_decision_locked": True,
        "broad_codal_capture_stopped": True,
        "financial_data_researcher_verified_frozen": True,
        "conservative_availability_lag_locked": True,
        "conservative_lag_months": 6,
        "row_level_publish_datetime_collection_required": False,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["conservative_six_month_lag_decision_locked"] is True
    assert got["broad_codal_capture_stopped"] is True
    assert got["financial_data_researcher_verified_frozen"] is True
    assert got["conservative_availability_lag_locked"] is True
    assert got["conservative_lag_months"] == 6
    assert got["row_level_publish_datetime_collection_required"] is False
    assert got["modeling_started"] is False


def test_qc_source_test_override_part3b1e():
    src, test = gen._qc_source_test_paths(
        "stage125_part3b1e_conservative_six_month_lag_decision_lock"
    )
    assert src.endswith("stage125_part3b1e_conservative_lag_decision.py")
    assert test.endswith(
        "test_stage125_part3b1e_conservative_lag_decision.py"
    )


def test_extract_qc_workflow_markers_part3c_scope():
    qc = {
        "stage": "stage125_part3c_leakage_safe_dataset_finalization",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "document_binding_resolution_decision_locked": True,
        "conservative_six_month_lag_decision_locked": True,
        "broad_codal_capture_stopped": True,
        "financial_data_researcher_verified_frozen": True,
        "conservative_availability_lag_locked": True,
        "row_level_publish_datetime_collection_required": False,
        "active_availability_method": "fixed_regulatory_lag",
        "active_availability_lag_months": 4,
        "four_month_regulatory_lag_locked": True,
        "six_month_lag_superseded": True,
        "historical_six_month_decision_retained": True,
        "historical_six_month_decision_active": False,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": True,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "part3c_leakage_safe_finalization_completed": True,
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["part3c_leakage_safe_finalization_completed"] is True
    assert got["pair_level_evidence_collected"] is True
    assert got["modeling_started"] is False
    assert got["active_availability_lag_months"] == 4
    assert got["four_month_regulatory_lag_locked"] is True
    assert got["six_month_lag_superseded"] is True


def test_qc_source_test_override_part3c():
    src, test = gen._qc_source_test_paths(
        "stage125_part3c_leakage_safe_dataset_finalization"
    )
    assert src.endswith(
        "stage125_part3c_leakage_safe_dataset_finalization.py"
    )
    assert test.endswith(
        "test_stage125_part3c_leakage_safe_dataset_finalization.py"
    )


def test_extract_qc_workflow_markers_part4_scope():
    qc = {
        "stage": "stage125_part4_statistical_analysis_plan",
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "document_binding_resolution_decision_locked": True,
        "conservative_six_month_lag_decision_locked": True,
        "broad_codal_capture_stopped": True,
        "financial_data_researcher_verified_frozen": True,
        "conservative_availability_lag_locked": True,
        "row_level_publish_datetime_collection_required": False,
        "active_availability_method": "fixed_regulatory_lag",
        "active_availability_lag_months": 4,
        "four_month_regulatory_lag_locked": True,
        "six_month_lag_superseded": True,
        "historical_six_month_decision_retained": True,
        "historical_six_month_decision_active": False,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": True,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "part3c_leakage_safe_finalization_completed": True,
        "part4_statistical_analysis_plan_locked": True,
        "contract_version": "stage125_part4_sap_v2",
        "network_extraction_performed": True,
        "modeling_started": False,
    }
    got = gen.extract_qc_workflow_markers(qc)
    assert got["part4_statistical_analysis_plan_locked"] is True
    assert got["part3c_leakage_safe_finalization_completed"] is True
    assert got["modeling_started"] is False
    assert got["active_availability_lag_months"] == 4
    assert got["contract_version"] == "stage125_part4_sap_v2"


def test_qc_source_test_override_part4():
    src, test = gen._qc_source_test_paths(
        "stage125_part4_statistical_analysis_plan"
    )
    assert src.endswith("stage125_part4_statistical_analysis_plan.py")
    assert test.endswith(
        "test_stage125_part4_statistical_analysis_plan.py"
    )


def test_stage125_part3b0_full_artifact_commit_is_skipped(synth):
    before = gen.last_stage_commit(synth)
    for rel in (
        "project/stage125/stage125_part3b0_evidence_readiness_qc_report.json",
        "project/stage125/metadata_and_hashes_stage125_part3b0.json",
        "project/stage125/part3b0_evidence_capture_contract_stage125.json",
        "project/stage125/README_STAGE125_PART3B0_EVIDENCE_READINESS.md",
    ):
        _write(synth, rel, "generated\n")
    sha = _commit(synth, "artifacts: Stage125 Part3B.0 readiness")
    got = gen.last_stage_commit(synth)
    assert got == before
    assert got != sha


# --------------------------------------------------------------------------- #
# Entry-document consistency tests (Stage126 current state)
# --------------------------------------------------------------------------- #

def test_readme_run_current_state_contains_stage126_authorized():
    """README_RUN current state must contain Stage126 authorized and started."""
    readme_path = os.path.join(REAL_ROOT, "project", "README_RUN.md")
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    assert "Stage126 M1 is human-authorized and started" in content, (
        "README_RUN must state Stage126 M1 is human-authorized and started"
    )


def test_readme_run_does_not_claim_no_model_has_run():
    """README_RUN must not claim no model has run (Stage126 M1 tuning completed)."""
    readme_path = os.path.join(REAL_ROOT, "project", "README_RUN.md")
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    # The stale phrase "No model is run yet" must not appear
    assert "No model is run yet" not in content, (
        "README_RUN must not claim 'No model is run yet'"
    )


def test_readme_run_does_not_globally_prohibit_all_modeling():
    """README_RUN must not globally prohibit all modeling (Stage126 M1 is authorized)."""
    readme_path = os.path.join(REAL_ROOT, "project", "README_RUN.md")
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()
    # The stale phrase "Modeling remains prohibited" without qualification must not appear
    # Allow it only in historical context (e.g., "through Stage125")
    lines = content.split("\n")
    for line in lines:
        if "Modeling remains prohibited" in line and "Stage125" not in line:
            assert False, (
                f"README_RUN line contains unqualified 'Modeling remains prohibited': {line}"
            )


def test_handoff_package_current_state_contains_modeling_started_true():
    """HANDOFF_PACKAGE current state must reflect modeling_started=true."""
    state = _state(REAL_ROOT)
    assert state["modeling_started"] is True, (
        "handoff_state.json must have modeling_started=true"
    )


def test_handoff_package_current_state_contains_primary_m1_tuning_completed():
    """HANDOFF_PACKAGE current state must mention primary M1 development tuning completed."""
    package_path = os.path.join(REAL_ROOT, "project", "docs", "ai", "HANDOFF_PACKAGE.md")
    with open(package_path, encoding="utf-8") as f:
        content = f.read()
    assert "Primary M1 development-fold tuning is completed" in content, (
        "HANDOFF_PACKAGE must state primary M1 development tuning is completed"
    )


def test_handoff_package_does_not_describe_stage126_as_future():
    """HANDOFF_PACKAGE must not describe current Stage126 as future, unauthorized or not started."""
    package_path = os.path.join(REAL_ROOT, "project", "docs", "ai", "HANDOFF_PACKAGE.md")
    with open(package_path, encoding="utf-8") as f:
        content = f.read()
    # These stale phrases must not appear in current-state descriptions
    stale_phrases = [
        "no model trained yet",
        "future / blocked pending explicit human authorization",
        "modeling remains prohibited until Stage126",
    ]
    for phrase in stale_phrases:
        # Allow in historical quoted sections (e.g., in "Historical Stage125" labels)
        # Check if phrase appears outside of historical context
        if phrase in content:
            # Simple heuristic: if the phrase appears, ensure it's in a historical context
            # by checking for nearby historical markers
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if phrase in line:
                    # Check surrounding lines for historical context markers
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 3)
                    context = "\n".join(lines[context_start:context_end])
                    if "Historical" not in context and "historical" not in context:
                        assert False, (
                            f"HANDOFF_PACKAGE contains stale phrase '{phrase}' outside historical context: {line}"
                        )
    # "not started" is allowed when referring to specific sub-components (e.g., "M1 robustness is not started")
    # but not when describing Stage126 overall as not started
    if "not started" in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "not started" in line:
                # Check if this line describes Stage126 overall as not started
                # Allow it if it's about specific sub-components
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 3)
                context = "\n".join(lines[context_start:context_end])
                # Reject if it says Stage126 is not started without qualifying sub-component
                if "Stage126" in context and ("robustness" not in context and "M2" not in context and "M3" not in context and "M4" not in context):
                    assert False, (
                        f"HANDOFF_PACKAGE describes Stage126 overall as 'not started': {line}"
                    )


def test_decisions_current_stage126_guardrails_contain_authorized_and_started():
    """DECISIONS current Stage126 guardrails must contain authorized and started."""
    decisions_path = os.path.join(REAL_ROOT, "project", "docs", "ai", "DECISIONS.md")
    with open(decisions_path, encoding="utf-8") as f:
        content = f.read()
    # Check the Current Stage126 M1 guardrails section
    assert "Stage126 M1 is human-authorized and started" in content, (
        "DECISIONS must state Stage126 M1 is human-authorized and started"
    )


def test_decisions_current_stage126_guardrails_contain_final_test_locked():
    """DECISIONS current Stage126 guardrails must contain final test locked."""
    decisions_path = os.path.join(REAL_ROOT, "project", "docs", "ai", "DECISIONS.md")
    with open(decisions_path, encoding="utf-8") as f:
        content = f.read()
    assert "final test remains locked" in content, (
        "DECISIONS must state final test remains locked"
    )


def test_decisions_does_not_label_current_phase_as_no_model_data_freeze():
    """DECISIONS must not label the current phase as a no-model data-freeze phase."""
    decisions_path = os.path.join(REAL_ROOT, "project", "docs", "ai", "DECISIONS.md")
    with open(decisions_path, encoding="utf-8") as f:
        content = f.read()
    # The section title "Phase guardrails (current data-freeze phase)" is stale
    # It should now be "Phase guardrails" with subsections
    assert "Phase guardrails (current data-freeze phase)" not in content, (
        "DECISIONS must not label current phase as 'current data-freeze phase'"
    )


# --------------------------------------------------------------------------- #
# Section-aware entry-document consistency tests (final entry-doc correction)
# --------------------------------------------------------------------------- #

def _read_doc(*parts: str) -> str:
    """Read a repository text file relative to REAL_ROOT."""
    with open(os.path.join(REAL_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text: str) -> str:
    """Collapse all runs of whitespace to single spaces so that phrase checks
    are robust to markdown hard line-wrapping."""
    return " ".join(text.split())


def _md_section(content: str, heading_substring: str) -> str:
    """Return the body of the first level-1/level-2 markdown section whose
    heading line contains ``heading_substring``.

    The section runs from its heading up to (but excluding) the next level-1 or
    level-2 heading (``#`` or ``##``); deeper ``###`` headings stay inside.
    Raises AssertionError if the heading is not found.
    """
    lines = content.split("\n")
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{1,2} ", line) and heading_substring in line:
            start = i
            break
    assert start is not None, (
        f"heading containing {heading_substring!r} not found"
    )
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^#{1,2} ", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def test_readme_run_has_no_stale_modeling_readiness_redesign():
    """README_RUN must not contain the stale stage125-modeling-readiness redesign."""
    content = _read_doc("project", "README_RUN.md")
    assert "modeling pipeline will be redesigned separately under" \
        not in _flat(content), (
        "README_RUN must not say the modeling pipeline will be redesigned separately"
    )
    assert "stage125-modeling-readiness" not in content, (
        "README_RUN must not reference stage125-modeling-readiness"
    )


def test_readme_run_stage_output_table_has_stage125_and_stage126_rows():
    """README_RUN stage-output table must include Stage125 and Stage126 rows."""
    section = _md_section(_read_doc("project", "README_RUN.md"),
                          "What each stage produces")
    assert "| Stage125 |" in section, (
        "README_RUN stage-output table must include a | Stage125 | row"
    )
    assert "| Stage126 |" in section, (
        "README_RUN stage-output table must include a | Stage126 | row"
    )
    # Stage126 must not be implied complete.
    assert "no full-development refit" in _flat(section), (
        "README_RUN Stage126 row must state no full-development refit"
    )


def test_decisions_pipeline_section_has_no_stale_redesign_statement():
    """DECISIONS Pipeline section must not contain the stale redesign statement."""
    section = _flat(_md_section(_read_doc("project", "docs", "ai", "DECISIONS.md"),
                               "Pipeline order & target"))
    assert "current modeling pipeline will be redesigned after the Stage123 freeze" \
        not in section, (
        "DECISIONS Pipeline section must not say the modeling pipeline will be "
        "redesigned after the Stage123 freeze"
    )


def test_decisions_pipeline_section_distinguishes_the_two_pipelines():
    """DECISIONS Pipeline section must distinguish the two named pipelines."""
    section = _flat(_md_section(_read_doc("project", "docs", "ai", "DECISIONS.md"),
                               "Pipeline order & target"))
    assert "Frozen data-preparation pipeline" in section, (
        "DECISIONS Pipeline section must name the frozen data-preparation pipeline"
    )
    assert "Research-design and modeling sequence" in section, (
        "DECISIONS Pipeline section must name the research-design and modeling "
        "sequence"
    )


def test_handoff_package_final_goal_has_no_later_models_phrase():
    """HANDOFF_PACKAGE Final goal must not contain the stale (later) models phrase."""
    section = _flat(_md_section(
        _read_doc("project", "docs", "ai", "HANDOFF_PACKAGE.md"), "Final goal"))
    assert "(later) distress-prediction models" not in section, (
        "HANDOFF_PACKAGE Final goal must not say '(later) distress-prediction models'"
    )


def test_handoff_package_done_section_lists_stage125_and_stage126_milestones():
    """HANDOFF_PACKAGE Done section must list Part 5 closure and Stage126 tuning."""
    section = _flat(_md_section(
        _read_doc("project", "docs", "ai", "HANDOFF_PACKAGE.md"), "Done"))
    assert "Stage125 Part 5 readiness closure" in section, (
        "HANDOFF_PACKAGE Done section must include Stage125 Part 5 readiness closure"
    )
    assert "Stage126 primary development-fold tuning" in section, (
        "HANDOFF_PACKAGE Done section must include Stage126 primary "
        "development-fold tuning"
    )


def test_handoff_package_next_step_requires_explicit_human_decision():
    """HANDOFF_PACKAGE Next step must require a separate explicit human decision."""
    section = _flat(_md_section(
        _read_doc("project", "docs", "ai", "HANDOFF_PACKAGE.md"), "Next step"))
    assert "separate explicit human micro-part decision" in section, (
        "HANDOFF_PACKAGE Next step must require a separate explicit human "
        "micro-part decision"
    )
    assert "M1 robustness" in section, (
        "HANDOFF_PACKAGE Next step must reference M1 robustness"
    )


# --------------------------------------------------------------------------- #
# Stage126 M1 robustness Part 0 decision-lock Handoff integration
# --------------------------------------------------------------------------- #

def test_handoff_state_carries_robustness_decision_markers():
    """handoff_state.json must carry the robustness-decision markers.

    After Part 1 execution the decision lock remains in force and there is still
    no standing execution authorization; `m1_robustness_started` is now True and
    the next category has advanced to Part 2 (which remains unauthorized).
    """
    state = _state(REAL_ROOT)
    assert state["m1_robustness_decision_locked"] is True
    assert state["m1_robustness_execution_authorized"] is False
    assert state["m1_robustness_completed"] is False
    assert state["m1_robustness_packaging_policy"] == "one_category_per_micro_part_pr"
    assert state["m1_robustness_started"] is True
    # Parts 1 and 2 are complete, so the next registered category is Part 3.
    assert state["m1_robustness_next_category_id"] == (
        "expanded_rule_a_company_scope_robustness"
    )


def test_robustness_decision_lock_does_not_advance_research_pointers():
    """Robustness micro-parts must not advance the research action pointers."""
    state = _state(REAL_ROOT)
    assert state["next_research_action_id"] == "stage126-m1-financial-baseline"
    assert state["active_workstream"] == "stage126_m1_financial_baseline"
    # The micro-part pointer tracks the newest completed robustness micro-part;
    # the research-action chain deliberately stays on Stage126 M1.
    assert state["last_completed_micro_part"] == \
        "stage126-m1-robustness-part2-listing-rule-b"


def test_robustness_decision_lock_preserves_primary_and_final_test_state():
    """Decision lock must not change primary or final-test state."""
    state = _state(REAL_ROOT)
    assert state["current_stage"] == "Stage126"
    assert state["m1_primary_development_tuning_completed"] is True
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["final_test_evaluation_performed"] is False


def test_robustness_decision_markers_derive_from_record():
    """Generator derivation must match the tracked decision + Part 1 records."""
    markers = gen.derive_m1_robustness_decision_markers(REAL_ROOT)
    assert markers["m1_robustness_decision_locked"] is True
    assert markers["m1_robustness_execution_authorized"] is False
    # Parts 1 and 2 are complete, so the next registered category is Part 3.
    assert markers["m1_robustness_next_category_id"] == (
        "expanded_rule_a_company_scope_robustness"
    )
    assert markers["m1_robustness_part1_completed"] is True
    assert markers["m1_robustness_part2_completed"] is True


# --------------------------------------------------------------------------- #
# Fail-closed Handoff derivation for the Part 0 decision record
# --------------------------------------------------------------------------- #

_ROBUSTNESS_RECORD_REL = (
    "project/stage126/stage126_m1_robustness_part0_decision_record.json"
)


def _valid_robustness_record() -> dict:
    with open(os.path.join(REAL_ROOT, _ROBUSTNESS_RECORD_REL), encoding="utf-8") as f:
        return json.load(f)


def _write_record_to(tmp, record) -> str:
    d = os.path.join(tmp, "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_ROBUSTNESS_RECORD_REL)),
              "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    return tmp


def test_derive_markers_positive_from_valid_synthetic(tmp_path):
    root = _write_record_to(str(tmp_path), _valid_robustness_record())
    markers = gen.derive_m1_robustness_decision_markers(root)
    assert markers == {
        "m1_robustness_decision_locked": True,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m1_robustness_next_category_id": "m1_target_proximity_six_feature_set",
        "m1_robustness_packaging_policy": "one_category_per_micro_part_pr",
    }


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(contract_id="WRONG"),
    lambda r: r.update(contract_version="WRONG"),
    lambda r: r.update(decision_id="WRONG"),
    lambda r: r.update(decision_locked=False),
    lambda r: r.update(execution_authorized=True),
    lambda r: r.update(m1_robustness_started=True),
    lambda r: r.update(m1_robustness_completed=True),
    lambda r: r.update(part0_authorizes_part1=True),
    lambda r: r.update(each_part_requires_separate_human_authorization=False),
    lambda r: r.update(packaging_policy="WRONG"),
    lambda r: r.__setitem__("execution_order", r["execution_order"][1:]),  # missing
    lambda r: r.__setitem__(
        "execution_order", r["execution_order"] + ["extra_category"]),  # extra
    lambda r: r.__setitem__(
        "execution_order", list(reversed(r["execution_order"]))),  # reordered
    lambda r: r.update(human_decision_text="tampered text"),
    lambda r: r.update(human_decision_text_sha256="0" * 64),
], ids=[
    "wrong_contract_id", "wrong_contract_version", "wrong_decision_id",
    "decision_locked_false", "execution_authorized_true",
    "m1_robustness_started_true", "m1_robustness_completed_true",
    "part0_authorizes_part1_true", "each_part_requires_auth_false",
    "wrong_packaging_policy", "missing_category", "extra_category",
    "reordered_category", "wrong_decision_text", "wrong_decision_hash",
])
def test_derive_markers_fail_closed(tmp_path, mutate):
    record = _valid_robustness_record()
    mutate(record)
    root = _write_record_to(str(tmp_path), record)
    with pytest.raises(gen.HandoffError):
        gen.derive_m1_robustness_decision_markers(root)


def test_derive_markers_absent_record_returns_empty(tmp_path):
    # No decision record => empty markers (pre-Part-0 repository states).
    assert gen.derive_m1_robustness_decision_markers(str(tmp_path)) == {}


# --------------------------------------------------------------------------- #
# Stage126 M1 robustness Part 1 Handoff integration
# --------------------------------------------------------------------------- #

_PART1_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part1_human_authorization_record.json"
)
_PART1_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part1_completion_lock.json"
)
_PART1_ORDER = [
    "m1_target_proximity_six_feature_set",
    "main_rule_b_listing_robustness",
    "expanded_rule_a_company_scope_robustness",
    "expanded_rule_b_combined_robustness",
    "persistent_loss_robustness_target",
    "smote_training_fold_only_robustness",
]


def _valid_part1_auth() -> dict:
    with open(os.path.join(REAL_ROOT, _PART1_AUTH_REL), encoding="utf-8") as f:
        return json.load(f)


def _valid_part1_lock() -> dict:
    with open(os.path.join(REAL_ROOT, _PART1_LOCK_REL), encoding="utf-8") as f:
        return json.load(f)


def _write_part1(tmp, auth, lock) -> str:
    d = os.path.join(tmp, "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_PART1_AUTH_REL)),
              "w", encoding="utf-8") as f:
        json.dump(auth, f, ensure_ascii=False)
    with open(os.path.join(d, os.path.basename(_PART1_LOCK_REL)),
              "w", encoding="utf-8") as f:
        json.dump(lock, f, ensure_ascii=False)
    return tmp


def test_handoff_state_carries_part1_markers():
    """Part 1 markers are RETAINED (not replaced) after Part 2 completed."""
    state = _state(REAL_ROOT)
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is False
    assert state["m1_robustness_part1_human_authorized"] is True
    assert state["m1_robustness_part1_completed"] is True
    assert state["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
    ]
    assert state["m1_robustness_next_category_id"] == (
        "expanded_rule_a_company_scope_robustness"
    )
    assert state["m1_robustness_execution_authorized"] is False


def test_handoff_state_carries_part2_markers():
    state = _state(REAL_ROOT)
    assert state["m1_robustness_part2_human_authorized"] is True
    assert state["m1_robustness_part2_completed"] is True
    assert state["m1_robustness_part3_authorized"] is False
    assert state["m1_robustness_execution_authorized"] is False
    assert state["m1_robustness_completed"] is False
    assert state["contract_version"] == (
        "stage126_m1_robustness_part2_listing_rule_b_v1"
    )


def test_handoff_state_carries_part2_sample_robustness_markers():
    """The Part 2 comparison markers are derived fail-closed, never invented."""
    state = _state(REAL_ROOT)
    cmp_ = json.load(open(os.path.join(
        REAL_ROOT,
        "project/stage126/stage126_m1_robustness_part2_primary_comparison.json",
    ), encoding="utf-8"))
    assert state["m1_robustness_part2_sample_sensitivity_reported"] is True
    assert state["m1_robustness_part2_observed_ordering"] == \
        cmp_["part2_observed_sensitivity_ordering"]
    assert state["m1_robustness_part2_ordering_differs_from_primary"] == \
        cmp_["observed_ordering_differs_from_primary"]
    assert state["m1_primary_claim_ordering_preserved"] is True
    # The Part 1 instability markers are retained unchanged.
    assert state["m1_robustness_part1_ordering_instability_reported"] is True
    assert state["m1_robustness_part1_observed_ordering"] == [
        "xgboost", "random_forest", "regularized_logistic_regression",
    ]


def test_part2_markers_absent_returns_empty(tmp_path):
    assert gen.derive_m1_robustness_part2_markers(
        str(tmp_path), _PART1_ORDER,
    ) == {}


def test_part2_half_present_fails_closed(tmp_path):
    d = os.path.join(str(tmp_path), "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(
        d, "stage126_m1_robustness_part2_completion_lock.json",
    ), "w", encoding="utf-8") as f:
        json.dump({"category_id": "main_rule_b_listing_robustness"}, f)
    with pytest.raises(gen.HandoffError):
        gen.derive_m1_robustness_part2_markers(str(tmp_path), _PART1_ORDER)


def test_part1_preserves_primary_and_final_test_state():
    state = _state(REAL_ROOT)
    assert state["m1_primary_development_tuning_completed"] is True
    assert state["full_development_refit_performed"] is False
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["final_test_predictor_values_inspected"] is False
    assert state["final_test_target_values_inspected"] is False
    assert state["final_test_evaluation_performed"] is False
    assert state["m2_data_collected"] is False
    assert state["m3_data_collected"] is False
    assert state["m4_data_collected"] is False


def test_part1_selected_qc_and_micro_part():
    """After Part 2 the NEWEST completed micro-part supplies the selected QC."""
    state = _state(REAL_ROOT)
    assert state["last_completed_micro_part"] == \
        "stage126-m1-robustness-part2-listing-rule-b"
    assert state["selected_qc_scope"] == \
        "stage126_m1_robustness_part2_listing_rule_b"
    assert state["selected_qc_path"] == \
        "project/stage126/stage126_m1_robustness_part2_qc_report.json"


def test_part1_does_not_advance_research_pointers():
    state = _state(REAL_ROOT)
    assert state["next_research_action_id"] == "stage126-m1-financial-baseline"
    assert state["active_workstream"] == "stage126_m1_financial_baseline"
    assert state["current_stage"] == "Stage126"


def test_part1_markers_positive_from_synthetic(tmp_path):
    root = _write_part1(str(tmp_path), _valid_part1_auth(), _valid_part1_lock())
    m = gen.derive_m1_robustness_part1_markers(root, _PART1_ORDER)
    assert m["m1_robustness_started"] is True
    assert m["m1_robustness_part1_completed"] is True
    assert m["m1_robustness_part2_authorized"] is False
    assert m["m1_robustness_execution_authorized"] is False
    assert m["m1_robustness_next_category_id"] == "main_rule_b_listing_robustness"


def test_part1_markers_absent_returns_empty(tmp_path):
    assert gen.derive_m1_robustness_part1_markers(str(tmp_path), _PART1_ORDER) == {}


def test_part1_half_present_fails_closed(tmp_path):
    d = os.path.join(str(tmp_path), "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_PART1_AUTH_REL)),
              "w", encoding="utf-8") as f:
        json.dump(_valid_part1_auth(), f, ensure_ascii=False)
    with pytest.raises(gen.HandoffError):
        gen.derive_m1_robustness_part1_markers(str(tmp_path), _PART1_ORDER)


@pytest.mark.parametrize("mutate_auth", [
    lambda a: a.update(authorization_id="WRONG"),
    lambda a: a.update(authorized_category_id="WRONG"),
    lambda a: a.update(part1_execution_authorized=False),
    lambda a: a.update(part2_execution_authorized=True),
    lambda a: a.update(final_test_access_authorized=True),
    lambda a: a.update(human_authorization_text="tampered"),
    lambda a: a.update(human_authorization_text_sha256="0" * 64),
], ids=[
    "wrong_auth_id", "wrong_category", "part1_not_authorized",
    "part2_authorized", "final_test_authorized", "tampered_text", "wrong_hash",
])
def test_part1_auth_fail_closed(tmp_path, mutate_auth):
    auth = _valid_part1_auth()
    mutate_auth(auth)
    root = _write_part1(str(tmp_path), auth, _valid_part1_lock())
    with pytest.raises(gen.HandoffError):
        gen.derive_m1_robustness_part1_markers(root, _PART1_ORDER)


@pytest.mark.parametrize("mutate_lock", [
    lambda l: l.update(category_id="WRONG"),
    lambda l: l.update(part1_execution_completed=False),
    lambda l: l.update(authorization_consumed=False),
    lambda l: l.update(no_retuning=False),
    lambda l: l.update(m1_robustness_started=False),
    lambda l: l.update(m1_robustness_completed=True),
    lambda l: l.update(part2_execution_authorized=True),
    lambda l: l.update(full_development_refit_performed=True),
    lambda l: l.update(final_test_unlocked=True),
    lambda l: l.update(final_test_evaluation_performed=True),
    lambda l: l.update(smote_executed=True),
    lambda l: l.update(smotenc_executed=True),
    lambda l: l.update(shap_executed=True),
    lambda l: l.update(completed_category_ids=[]),
    lambda l: l.update(next_category_id="WRONG"),
], ids=[
    "wrong_category", "not_completed", "auth_not_consumed", "retuning",
    "not_started", "all_completed", "part2_authorized", "full_refit",
    "final_test_unlocked", "final_test_evaluated", "smote", "smotenc", "shap",
    "empty_completed_ids", "wrong_next_category",
])
def test_part1_lock_fail_closed(tmp_path, mutate_lock):
    lock = _valid_part1_lock()
    mutate_lock(lock)
    root = _write_part1(str(tmp_path), _valid_part1_auth(), lock)
    with pytest.raises(gen.HandoffError):
        gen.derive_m1_robustness_part1_markers(root, _PART1_ORDER)


# --------------------------------------------------------------------------- #
# Frozen Part 5 successor-compatibility markers
# --------------------------------------------------------------------------- #

_PART5_COMPAT_REL = (
    "project/stage126/"
    "stage126_m1_robustness_part1_part5_successor_compatibility.json"
)
_PART1_QC_REL = "project/stage126/stage126_m1_robustness_part1_qc_report.json"


def _valid_compat() -> dict:
    with open(os.path.join(REAL_ROOT, _PART5_COMPAT_REL), encoding="utf-8") as f:
        return json.load(f)


def _valid_part1_qc() -> dict:
    with open(os.path.join(REAL_ROOT, _PART1_QC_REL), encoding="utf-8") as f:
        return json.load(f)


def test_handoff_state_carries_part5_compatibility_markers():
    state = _state(REAL_ROOT)
    assert state["stage125_part5_frozen_artifacts_verified"] is True
    assert state["stage125_part5_live_successor_check_applicable"] is False
    assert state["stage125_part5_successor_compatibility_status"] == (
        "expected_historical_contract_boundary_after_part1"
    )


def test_part5_compatibility_markers_absent_without_artifacts(tmp_path):
    assert gen.derive_part5_successor_compatibility_markers(str(tmp_path)) == {}


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(contract_id="WRONG"),
    lambda c: c.update(contract_version="WRONG"),
    lambda c: c.update(part1_category_id="WRONG"),
    lambda c: c.update(stage125_part5_artifacts_modified=True),
    lambda c: c.update(stage125_part5_source_modified=True),
    lambda c: c.update(stage125_part5_historical_closure_remains_valid=False),
    lambda c: c.update(
        stage125_part5_live_handoff_check_applicable_after_part1=True),
    lambda c: c.update(part1_scientific_execution_valid=False),
    lambda c: c.update(part2_execution_authorized=True),
    lambda c: c.update(full_development_refit_performed=True),
    lambda c: c.update(final_test_access_authorized=True),
    lambda c: c.update(final_test_evaluation_performed=True),
    lambda c: c.update(expected_live_mismatch_fields=["only_one_field"]),
], ids=[
    "wrong_contract_id", "wrong_contract_version", "wrong_category",
    "artifacts_modified", "source_modified", "closure_invalid",
    "check_applicable", "execution_invalid", "part2_authorized",
    "full_refit", "final_test_access", "final_test_evaluated",
    "wrong_mismatch_fields",
])
def test_part5_compatibility_fail_closed(tmp_path, mutate):
    compat = _valid_compat()
    mutate(compat)
    d = os.path.join(str(tmp_path), "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_PART5_COMPAT_REL)),
              "w", encoding="utf-8") as f:
        json.dump(compat, f, ensure_ascii=False)
    with open(os.path.join(d, os.path.basename(_PART1_QC_REL)),
              "w", encoding="utf-8") as f:
        json.dump(_valid_part1_qc(), f, ensure_ascii=False)
    with pytest.raises(gen.HandoffError):
        gen.derive_part5_successor_compatibility_markers(str(tmp_path))


def test_current_state_labels_micro_part_not_research_action():
    """CURRENT_STATE must not label a micro-part as a completed research action."""
    text = _read_doc("project", "docs", "ai", "CURRENT_STATE.md")
    assert "- **Last completed micro-part:** " \
        "`stage126-m1-robustness-part2-listing-rule-b`" in text
    assert "Last completed research action" not in text, (
        "a robustness micro-part must never be labelled a research action"
    )
    assert "- **Next research action:** `stage126-m1-financial-baseline`" in text


# --------------------------------------------------------------------------- #
# Part 1 observed-ordering instability markers
# --------------------------------------------------------------------------- #

_COMPARISON_REL = (
    "project/stage126/stage126_m1_robustness_part1_primary_comparison.json"
)


def _valid_comparison() -> dict:
    with open(os.path.join(REAL_ROOT, _COMPARISON_REL), encoding="utf-8") as f:
        return json.load(f)


def _write_comparison(tmp, cmp_) -> str:
    d = os.path.join(tmp, "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_COMPARISON_REL)),
              "w", encoding="utf-8") as f:
        json.dump(cmp_, f, ensure_ascii=False)
    return tmp


def test_handoff_state_carries_ordering_instability_markers():
    state = _state(REAL_ROOT)
    assert state["m1_robustness_part1_ordering_instability_reported"] is True
    assert state["m1_robustness_part1_observed_ordering"] == [
        "xgboost", "random_forest", "regularized_logistic_regression",
    ]
    assert state["m1_primary_claim_ordering_preserved"] is True


def test_ordering_markers_absent_without_comparison(tmp_path):
    assert gen.derive_part1_ordering_instability_markers(str(tmp_path)) == {}


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(contract_version="WRONG"),
    lambda c: c.update(comparison_scope="WRONG"),
    lambda c: c.update(comparison_metric="WRONG"),
    lambda c: c.update(observed_ordering_differs_from_primary=False),
    lambda c: c.update(ordering_instability_reported_to_human_supervisor=False),
    lambda c: c.update(primary_ordering_for_confirmatory_claims_changed=True),
    lambda c: c.update(selected_configurations_changed=True),
    lambda c: c.update(paper_winner_selected=True),
    lambda c: c.update(automatic_scientific_action_triggered=True),
    lambda c: c.update(part1_observed_sensitivity_ordering=["random_forest"]),
], ids=[
    "wrong_version", "wrong_scope", "wrong_metric", "no_difference",
    "not_reported", "primary_ordering_changed", "configs_changed",
    "winner_selected", "auto_action", "wrong_observed_ordering",
])
def test_ordering_markers_fail_closed(tmp_path, mutate):
    cmp_ = _valid_comparison()
    mutate(cmp_)
    root = _write_comparison(str(tmp_path), cmp_)
    with pytest.raises(gen.HandoffError):
        gen.derive_part1_ordering_instability_markers(root)


def test_part5_compatibility_requires_part1_qc_all_pass(tmp_path):
    qc = _valid_part1_qc()
    qc["all_pass"] = False
    d = os.path.join(str(tmp_path), "project", "stage126")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, os.path.basename(_PART5_COMPAT_REL)),
              "w", encoding="utf-8") as f:
        json.dump(_valid_compat(), f, ensure_ascii=False)
    with open(os.path.join(d, os.path.basename(_PART1_QC_REL)),
              "w", encoding="utf-8") as f:
        json.dump(qc, f, ensure_ascii=False)
    with pytest.raises(gen.HandoffError):
        gen.derive_part5_successor_compatibility_markers(str(tmp_path))
