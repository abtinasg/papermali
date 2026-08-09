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
import copy
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


def _current_state_text() -> str:
    with open(os.path.join(REAL_ROOT, "project/docs/ai/CURRENT_STATE.md"),
              encoding="utf-8") as fh:
        return fh.read()


def test_current_state_has_no_literal_unicode_escapes():
    """The generator must emit real symbols, never their escape text."""
    text = _current_state_text()
    assert "\\u26d4" not in text
    # no literal \\uXXXX escape survives anywhere in the generated snapshot
    assert re.search(r"\\u[0-9a-fA-F]{4}", text) is None


def test_current_state_retained_block_line_uses_the_actual_symbol():
    assert (
        "- ⛔ **M2 block retained BY THIS ACTION:** false"
        in _current_state_text())


def test_generator_source_has_no_double_escaped_unicode():
    with open(os.path.join(REAL_ROOT, "project/scripts/update_ai_handoff.py"),
              encoding="utf-8") as fh:
        source = fh.read()
    assert "\\\\u26d4" not in source


def test_retained_block_wording_and_semantics_are_unchanged():
    """Fixing the symbol must not change what the snapshot claims."""
    text = _current_state_text()
    for fragment in (
        "it reports OBSERVED development evidence only and selects no winner",
        "The retained-block question was answered separately, by the human "
        "decision reported below",
        "`m2_block_retained=True`",
        "`m2_retained_block_decision_required=False`",
        "**M2 predictive superiority claim supported:** False",
        "**No winner, no final model:** paper_winner_selected=False",
        "final_model_selected=False",
        "full_development_refit_performed=False",
    ):
        assert fragment in text, fragment
    assert "**M3:** authorized=False, started=False" in text
    assert "**M4:** authorized=False, started=False" in text


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
    # `current_stage` is a CURRENT-state field and advanced with the freeze;
    # the Stage126 label survives in the separate micro-part QC role.
    assert state["current_stage"] == "Stage128"
    assert state["selected_qc_scope"].startswith("stage126")
    # The newest completed robustness micro-part supplies the selected QC.
    # Part 6 closes the six-category robustness set, so the research-action
    # pointer legitimately transitions to the closure/synthesis milestone
    # (see STAGE126_Q1Q2_LEAN_GOVERNANCE.md sections 10-11) -- a one-time,
    # truthful state transition, not a per-part advance.
    assert state["selected_qc_scope"] == (
        "stage126_m1_robustness_part6_smote_training_fold_only"
    )
    assert state["last_completed_micro_part"] == (
        "stage126-m1-robustness-part6-smote-training-fold-only"
    )
    # The human retained-block decision
    # (stage128-m2-retained-block-human-decision) has since been RECORDED
    # under its own explicit one-action authorization, so the pointer
    # legitimately advanced once more -- to the M3 macro data Gate. A pointer
    # is not an authorization: M3 stays unauthorized and unstarted. M2 is
    # retained as the INTERMEDIATE confirmatory block, which is a governance
    # decision and establishes no predictive superiority.
    # ...and once more when the supplementary M3I-2 contract was locked, the
    # official-source evidence capture completed and the final official
    # documentary recovery was INITIATED; the pointer now names a human
    # inquiry-submission action that is NOT authorized.
    # The human supervisor has since voluntarily terminated the Track A
    # waiting period early (2026-08-08) and frozen M3-LAG-WDI's final
    # disposition as supplementary/exploratory only; both pointer chains now
    # converge on the same human-decision-required state.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    # The live workstream label advanced with the live state: the Stage128
    # The M3 macro DATA Gate has EXECUTED, so the CURRENT workstream is the
    # M3 Gate. `stage128_m2_d2_boundary_month_equity_return` is now
    # predecessor context and `stage126_m1_financial_baseline` remains correct
    # HISTORY for the completed M1 baseline workstream — neither is current.
    # The supplementary M3I-2 contract lock has since succeeded the M3 Gate
    # as the live workstream; the Gate is now predecessor context.
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert state["active_workstream_predecessor_context"] == (
        "stage128_m3i2_official_source_evidence_capture"
    )
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
    # All six registered robustness categories have executed; the set is complete.
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is True
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
    # The M3 macro data Gate has executed, so the live workstream is the Gate.
    assert fm["active_research_workstream_id"] == (
        "stage128-m3i2-final-official-documentary-recovery")
    assert fm["predecessor_research_workstream_id"] == (
        "stage128-m3i2-official-source-evidence-capture"
    )
    # The workstream label is derived from the frozen action and never
    # substitutes for a research-action id.
    assert fm["last_completed_research_action_id"] == (
        "stage128-m3i2-track-a-waiting-termination-and-m3-disposition"
    )
    assert fm["next_research_action_id"] == "human-decision-required"
    # The Stage128 M2 D2 design freeze completed, and the canonical D2 Gate
    # re-run has since been EXECUTED under its own explicit one-action
    # authorization and PASSED data admission, so both pointers legitimately
    # advanced once more (see STAGE126_Q1Q2_LEAN_GOVERNANCE.md sections 10-11
    # and README_STAGE128_M2_D2_GATE_RERUN.md).
    # `stage127-m2-incremental-evaluation` is a pointer only, NOT an
    # authorization.
    # Isolate the Stage126 M1 research-action row (item 18) — now COMPLETE.
    match = re.search(
        r"18\.\s*`stage126-m1-financial-baseline`\s*—\s*([^\n]+)",
        roadmap,
    )
    assert match is not None, "Stage126 research-action row missing"
    stage126_row = match.group(1)
    stage126_row_l = stage126_row.lower()
    assert "**complete.**" in stage126_row_l
    assert "part 6" in stage126_row_l or "parts 1–6" in stage126_row_l
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

    # Isolate the robustness-closure row (item 19) — now COMPLETE.
    closure_match = re.search(
        r"19\.\s*`stage126-m1-robustness-closure`\s*—\s*([^\n]+)",
        roadmap,
    )
    assert closure_match is not None, "robustness-closure research-action row missing"
    closure_row_l = closure_match.group(1).lower()
    assert "**complete.**" in closure_row_l

    # Isolate the retained-design-freeze row (item 20) — now COMPLETE.
    freeze_match = re.search(
        r"20\.\s*`stage126-m1-retained-design-freeze`\s*—\s*([^\n]+)",
        roadmap,
    )
    assert freeze_match is not None, "retained-design-freeze research-action row missing"
    freeze_row_l = freeze_match.group(1).lower()
    assert "**complete.**" in freeze_row_l

    # Isolate the M2 market-data-gate row (item 21). The row must state the
    # executed status truthfully and must never claim the Gate passed or was
    # completed. The exact status is not pinned here: it is cross-checked
    # against the machine-readable Gate artifact below, so the row can never
    # drift away from the real result and can never be stale.
    gate_match = re.search(
        r"21\.\s*`stage127-m2-market-data-gate`\s*—\s*([^\n]+)",
        roadmap,
    )
    assert gate_match is not None, "M2 market-data-gate research-action row missing"
    gate_row_l = gate_match.group(1).lower()
    assert "executed" in gate_row_l
    assert any(
        status in gate_row_l
        for status in ("unresolved_m2_data_gate", "fail_m2_data_gate")
    ), "the Gate row must state a truthful non-passing status"
    assert "**complete.**" not in gate_row_l
    assert "pass_for_m2_incremental_evaluation" not in gate_row_l

    # The roadmap must agree with the machine-readable Gate status.
    gate_path = os.path.join(
        REAL_ROOT, "project", "stage127",
        "stage127_m2_market_data_gate_decision.json",
    )
    if os.path.isfile(gate_path):
        with open(gate_path, encoding="utf-8") as f:
            gate = json.load(f)
        assert gate["gate_status"].lower() in gate_row_l
        assert gate["modeling_performed"] is False


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
    # OPEN_TASKS names the CURRENT workstream, which advanced with the
    # Stage128 D2 design freeze; the Stage126 M1 baseline is retained below it
    # as an explicitly HISTORICAL (completed) section.
    assert (
        "## Active research workstream: "
        "`stage128-m3i2-final-official-documentary-recovery`" in open_tasks
    )
    assert (
        "### Historical (completed) — `stage126-m1-financial-baseline`"
        in open_tasks
    )
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert "Stage126 M1 human-authorized = true" in open_tasks
    assert "Stage126 started = true" in open_tasks
    assert "development modeling authorized = true" in open_tasks
    assert "modeling started = true" in open_tasks
    assert "primary development tuning completed = true" in open_tasks
    # Derived from the Handoff rather than pinned, so the OPEN_TASKS marker
    # block cannot silently drift away from the real state as micro-parts
    # complete. All six registered robustness categories are now complete.
    assert "M1 robustness started = {}".format(
        str(state["m1_robustness_started"]).lower()
    ) in open_tasks
    assert "M1 robustness completed = {}".format(
        str(state["m1_robustness_completed"]).lower()
    ) in open_tasks
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is True
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
    assert state["m1_robustness_completed"] is True
    assert state["m1_robustness_packaging_policy"] == "one_category_per_micro_part_pr"
    assert state["m1_robustness_started"] is True
    # All six registered categories are complete; there is no next category.
    assert state["m1_robustness_next_category_id"] == ""


def test_robustness_decision_lock_does_not_advance_research_pointers():
    """A per-part completion must not advance the research action pointers.

    The one exception is the terminal all-six-complete transition (see
    STAGE126_Q1Q2_LEAN_GOVERNANCE.md sections 10-11), which real-repo state
    now reflects: Part 6 closed the six-category set, so the pointer
    legitimately advanced to the closure/synthesis milestone.
    """
    state = _state(REAL_ROOT)
    # The human retained-block decision
    # (stage128-m2-retained-block-human-decision) has since been RECORDED
    # under its own explicit one-action authorization, so the pointer
    # legitimately advanced once more -- to the M3 macro data Gate. A pointer
    # is not an authorization: M3 stays unauthorized and unstarted. M2 is
    # retained as the INTERMEDIATE confirmatory block, which is a governance
    # decision and establishes no predictive superiority.
    # ...and once more when the supplementary M3I-2 contract was locked, the
    # official-source evidence capture completed and the final official
    # documentary recovery was INITIATED; the pointer now names a human
    # inquiry-submission action that is NOT authorized.
    # ...and once more when the human supervisor voluntarily terminated the
    # Track A waiting period and froze M3-LAG-WDI's final disposition
    # (2026-08-08); both pointer chains now converge on
    # `human-decision-required`.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    assert state["m2_incremental_evaluation_authorized"] is False
    # The one-action authorization was CONSUMED, which is why the flag above
    # is False. That never erases the executed modeling: the authorized
    # paired M2 evaluation really did fit 44 canonical development models.
    assert state["m2_modeling_started"] is True
    assert state["stage127_m2_incremental_evaluation_primary_model_fits"] == 44
    assert state["m2_block_retained"] is True
    # The live workstream label advanced with the live state: the Stage128
    # The M3 macro DATA Gate has EXECUTED, so the CURRENT workstream is the
    # M3 Gate. `stage128_m2_d2_boundary_month_equity_return` is now
    # predecessor context and `stage126_m1_financial_baseline` remains correct
    # HISTORY for the completed M1 baseline workstream — neither is current.
    # The supplementary M3I-2 contract lock has since succeeded the M3 Gate
    # as the live workstream; the Gate is now predecessor context.
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert state["active_workstream_predecessor_context"] == (
        "stage128_m3i2_official_source_evidence_capture"
    )
    # The micro-part pointer tracks the newest completed robustness micro-part.
    assert state["last_completed_micro_part"] == \
        "stage126-m1-robustness-part6-smote-training-fold-only"


def test_robustness_decision_lock_preserves_primary_and_final_test_state():
    """Decision lock must not change primary or final-test state."""
    state = _state(REAL_ROOT)
    # `current_stage` is a CURRENT-state field and advanced with the freeze;
    # the Stage126 label survives in the separate micro-part QC role.
    assert state["current_stage"] == "Stage128"
    assert state["selected_qc_scope"].startswith("stage126")
    assert state["m1_primary_development_tuning_completed"] is True
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["final_test_evaluation_performed"] is False


def test_robustness_decision_markers_derive_from_record():
    """Generator derivation must match the tracked decision + Part 1 records."""
    markers = gen.derive_m1_robustness_decision_markers(REAL_ROOT)
    assert markers["m1_robustness_decision_locked"] is True
    assert markers["m1_robustness_execution_authorized"] is False
    # All six registered categories are complete; there is no next category.
    assert markers["m1_robustness_next_category_id"] == ""
    assert markers["m1_robustness_part1_completed"] is True
    assert markers["m1_robustness_part2_completed"] is True
    assert markers["m1_robustness_part3_completed"] is True
    assert markers["m1_robustness_part4_completed"] is True
    assert markers["m1_robustness_part5_completed"] is True


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
    """Part 1 markers are RETAINED (not replaced) after later parts completed."""
    state = _state(REAL_ROOT)
    assert state["m1_robustness_started"] is True
    assert state["m1_robustness_completed"] is True
    assert state["m1_robustness_part1_human_authorized"] is True
    assert state["m1_robustness_part1_completed"] is True
    assert state["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert state["m1_robustness_next_category_id"] == ""
    assert state["m1_robustness_execution_authorized"] is False


def test_handoff_state_carries_part2_markers():
    """Part 2 markers are RETAINED (not replaced) after later parts completed."""
    state = _state(REAL_ROOT)
    assert state["m1_robustness_part2_human_authorized"] is True
    assert state["m1_robustness_part2_completed"] is True
    assert state["m1_robustness_execution_authorized"] is False
    assert state["m1_robustness_completed"] is True


def test_handoff_state_carries_part3_markers():
    state = _state(REAL_ROOT)
    assert state["m1_robustness_part3_human_authorized"] is True
    assert state["m1_robustness_part3_completed"] is True
    assert state["m1_robustness_part3_authorized"] is False
    assert state["m1_robustness_part4_authorized"] is False
    assert state["m1_robustness_execution_authorized"] is False
    assert state["m1_robustness_completed"] is True
    assert state["full_development_refit_performed"] is False
    for field in ("final_test_unlocked", "final_test_access_authorized",
                  "final_test_predictor_values_inspected",
                  "final_test_target_values_inspected",
                  "final_test_evaluation_performed"):
        assert state[field] is False, field


def test_handoff_state_carries_part4_markers():
    state = _state(REAL_ROOT)
    assert state["m1_robustness_part4_human_authorized"] is True
    assert state["m1_robustness_part4_completed"] is True
    assert state["m1_robustness_part4_authorized"] is False
    assert state["m1_robustness_part5_authorized"] is False
    assert state["m1_robustness_execution_authorized"] is False
    assert state["m1_robustness_completed"] is True
    assert state["contract_version"] == (
        "stage126_m1_robustness_part6_smote_training_fold_only_v1"
    )
    assert state["full_development_refit_performed"] is False
    for field in ("final_test_unlocked", "final_test_access_authorized",
                  "final_test_predictor_values_inspected",
                  "final_test_target_values_inspected",
                  "final_test_evaluation_performed"):
        assert state[field] is False, field


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
    """The NEWEST completed micro-part supplies the selected QC."""
    state = _state(REAL_ROOT)
    assert state["last_completed_micro_part"] == \
        "stage126-m1-robustness-part6-smote-training-fold-only"
    assert state["selected_qc_scope"] == \
        "stage126_m1_robustness_part6_smote_training_fold_only"
    assert state["selected_qc_path"] == \
        "project/stage126/stage126_m1_robustness_part6_qc_report.json"


def test_part1_does_not_advance_research_pointers():
    """A per-part completion never advances the pointer -- only the
    terminal all-six-complete transition does (see
    STAGE126_Q1Q2_LEAN_GOVERNANCE.md sections 10-11), which real-repo state
    now reflects."""
    state = _state(REAL_ROOT)
    # The human retained-block decision
    # (stage128-m2-retained-block-human-decision) has since been RECORDED
    # under its own explicit one-action authorization, so the pointer
    # legitimately advanced once more -- to the M3 macro data Gate. A pointer
    # is not an authorization: M3 stays unauthorized and unstarted. M2 is
    # retained as the INTERMEDIATE confirmatory block, which is a governance
    # decision and establishes no predictive superiority.
    # ...and once more when the supplementary M3I-2 contract was locked, the
    # official-source evidence capture completed and the final official
    # documentary recovery was INITIATED; the pointer now names a human
    # inquiry-submission action that is NOT authorized.
    # ...and once more when the human supervisor voluntarily terminated the
    # Track A waiting period and froze M3-LAG-WDI's final disposition
    # (2026-08-08); both pointer chains now converge on
    # `human-decision-required`.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    assert state["m2_incremental_evaluation_authorized"] is False
    # The one-action authorization was CONSUMED, which is why the flag above
    # is False. That never erases the executed modeling: the authorized
    # paired M2 evaluation really did fit 44 canonical development models.
    assert state["m2_modeling_started"] is True
    assert state["stage127_m2_incremental_evaluation_primary_model_fits"] == 44
    assert state["m2_block_retained"] is True
    # The live workstream label advanced with the live state: the Stage128
    # The M3 macro DATA Gate has EXECUTED, so the CURRENT workstream is the
    # M3 Gate. `stage128_m2_d2_boundary_month_equity_return` is now
    # predecessor context and `stage126_m1_financial_baseline` remains correct
    # HISTORY for the completed M1 baseline workstream — neither is current.
    # The supplementary M3I-2 contract lock has since succeeded the M3 Gate
    # as the live workstream; the Gate is now predecessor context.
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert state["active_workstream_predecessor_context"] == (
        "stage128_m3i2_official_source_evidence_capture"
    )
    # `current_stage` is a CURRENT-state field and advanced with the freeze;
    # the Stage126 label survives in the separate micro-part QC role.
    assert state["current_stage"] == "Stage128"
    assert state["selected_qc_scope"].startswith("stage126")


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
        "expected_historical_contract_boundary_after_completed_robustness_micro_part"
    )


def test_current_state_qc_is_separate_from_scientific_micro_part_qc():
    """The two QC roles must be distinct, explicit and truthful."""
    state = _state(REAL_ROOT)
    # Current-state validation surface.
    assert state["current_state_validation_scope"] == (
        "stage126_current_state_validator"
    )
    assert state["current_state_validation_path"] == (
        "project/stage126/stage126_current_state_validation_report.json"
    )
    assert state["current_state_validation_metadata_path"] == (
        "project/stage126/metadata_and_hashes_stage126_current_state_validator.json"
    )
    assert state["current_state_validation_failed"] == 0
    assert state["current_state_validation_all_pass"] is True
    meta = json.load(open(os.path.join(
        REAL_ROOT, state["current_state_validation_metadata_path"],
    ), encoding="utf-8"))
    assert state["current_state_validation_assertions"] == meta["assertion_count"]

    # Last completed SCIENTIFIC micro-part QC — a different role.
    assert state["last_completed_micro_part_qc_scope"] == (
        "stage126_m1_robustness_part6_smote_training_fold_only"
    )
    assert state["last_completed_micro_part_qc_path"] == (
        "project/stage126/stage126_m1_robustness_part6_qc_report.json"
    )
    assert state["last_completed_micro_part_qc_assertions"] == 148
    assert state["last_completed_micro_part_qc_failed"] == 0
    qc = json.load(open(os.path.join(
        REAL_ROOT, state["last_completed_micro_part_qc_path"],
    ), encoding="utf-8"))
    assert state["last_completed_micro_part_qc_assertions"] == qc["assertion_count"]

    # The two roles never collapse into one.
    assert state["current_state_validation_scope"] != \
        state["last_completed_micro_part_qc_scope"]
    assert state["current_state_validation_path"] != \
        state["last_completed_micro_part_qc_path"]


def test_current_state_doc_separates_the_two_qc_roles():
    text = _read_doc("project", "docs", "ai", "CURRENT_STATE.md")
    assert "## Current-state validation" in text
    assert "sole current-state validation surface" in text.lower()
    assert "### Last completed scientific micro-part QC" in text
    cs = text.split("## Current-state validation", 1)[1].split(
        "### Last completed scientific micro-part QC", 1
    )[0]
    assert "`stage126_current_state_validator`" in cs
    assert "stage126_current_state_validation_report.json" in cs
    micro = text.split("### Last completed scientific micro-part QC", 1)[1].split(
        "## Workflow markers", 1
    )[0]
    assert "stage126_m1_robustness_part6_qc_report.json" in micro


def test_handoff_carries_live_vs_historical_test_boundary_markers():
    """The historical Part 5 successor tests are recorded as NOT a live gate."""
    state = _state(REAL_ROOT)
    assert state["stage125_part5_historical_successor_tests"] is True
    assert state["stage125_part5_historical_successor_test_marker"] == (
        "live_successor_state"
    )
    assert state["stage125_part5_historical_successor_test_reference_commit"] == (
        "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
    )
    assert state["stage125_part5_historical_successor_tests_in_live_gate"] is False
    assert state["stage126_live_test_suite_marker_expression"] == (
        "not live_successor_state and not stage126_terminal_successor_state"
    )
    # The boundary changes nothing about current state.
    assert state["last_completed_micro_part"] == (
        "stage126-m1-robustness-part6-smote-training-fold-only"
    )
    assert state["m1_robustness_completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert state["last_completed_micro_part_qc_path"] == (
        "project/stage126/stage126_m1_robustness_part6_qc_report.json"
    )
    assert state["current_state_validation_path"] == (
        "project/stage126/stage126_current_state_validation_report.json"
    )
    assert state["m1_robustness_part4_authorized"] is False
    assert state["final_test_unlocked"] is False
    # The human retained-block decision
    # (stage128-m2-retained-block-human-decision) has since been RECORDED
    # under its own explicit one-action authorization, so the pointer
    # legitimately advanced once more -- to the M3 macro data Gate. A pointer
    # is not an authorization: M3 stays unauthorized and unstarted. M2 is
    # retained as the INTERMEDIATE confirmatory block, which is a governance
    # decision and establishes no predictive superiority.
    # ...and once more when the supplementary M3I-2 contract was locked, the
    # official-source evidence capture completed and the final official
    # documentary recovery was INITIATED; the pointer now names a human
    # inquiry-submission action that is NOT authorized.
    # ...and once more when the human supervisor voluntarily terminated the
    # Track A waiting period and froze M3-LAG-WDI's final disposition
    # (2026-08-08); both pointer chains now converge on
    # `human-decision-required`.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    assert state["m2_incremental_evaluation_authorized"] is False
    # The one-action authorization was CONSUMED, which is why the flag above
    # is False. That never erases the executed modeling: the authorized
    # paired M2 evaluation really did fit 44 canonical development models.
    assert state["m2_modeling_started"] is True
    assert state["stage127_m2_incremental_evaluation_primary_model_fits"] == 44
    assert state["m2_block_retained"] is True
    # Stage125 Part 5 stays historical and immutable.
    assert state["stage125_part5_mode"] == "historical_immutable"
    assert state["stage125_part5_live_gate_active"] is False


def test_test_boundary_markers_fail_closed_without_the_record(tmp_path):
    assert gen.derive_live_vs_historical_test_boundary_markers(
        str(tmp_path)
    ) == {}


def test_test_boundary_markers_fail_closed_on_a_tampered_record(tmp_path):
    d = os.path.join(str(tmp_path), "project", "stage126")
    os.makedirs(d, exist_ok=True)
    record = json.load(open(os.path.join(
        REAL_ROOT,
        "project/stage126/stage126_live_vs_historical_test_boundary.json",
    ), encoding="utf-8"))
    record["historical_successor_tests_are_live_gate"] = True
    with open(os.path.join(
        d, "stage126_live_vs_historical_test_boundary.json",
    ), "w", encoding="utf-8") as f:
        json.dump(record, f)
    with pytest.raises(gen.HandoffError):
        gen.derive_live_vs_historical_test_boundary_markers(str(tmp_path))


def test_part5_compatibility_status_is_generic_not_part1_specific():
    """The status must describe a completed micro-part, never Part 1 specifically.

    Naming Part 1 became untrue the moment Part 2 completed; the generic value
    stays truthful for every later micro-part.
    """
    state = _state(REAL_ROOT)
    status = state["stage125_part5_successor_compatibility_status"]
    assert status == (
        "expected_historical_contract_boundary_after_completed_robustness_micro_part"
    )
    assert "part1" not in status
    assert "part2" not in status
    # And the state it describes is the completed Part 6 micro-part.
    assert state["last_completed_micro_part"] == (
        "stage126-m1-robustness-part6-smote-training-fold-only"
    )
    assert state["m1_robustness_part5_completed"] is True
    assert state["m1_robustness_next_category_id"] == ""
    assert state["m1_robustness_part6_authorized"] is False
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["final_test_evaluation_performed"] is False
    # The workstream pointer stays put; the research-action pointer legitimately
    # advanced because Part 6 closed the six-category robustness set.
    # The live workstream label advanced with the live state: the Stage128
    # The M3 macro DATA Gate has EXECUTED, so the CURRENT workstream is the
    # M3 Gate. `stage128_m2_d2_boundary_month_equity_return` is now
    # predecessor context and `stage126_m1_financial_baseline` remains correct
    # HISTORY for the completed M1 baseline workstream — neither is current.
    # The supplementary M3I-2 contract lock has since succeeded the M3 Gate
    # as the live workstream; the Gate is now predecessor context.
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert state["active_workstream_predecessor_context"] == (
        "stage128_m3i2_official_source_evidence_capture"
    )
    # The human retained-block decision
    # (stage128-m2-retained-block-human-decision) has since been RECORDED
    # under its own explicit one-action authorization, so the pointer
    # legitimately advanced once more -- to the M3 macro data Gate. A pointer
    # is not an authorization: M3 stays unauthorized and unstarted. M2 is
    # retained as the INTERMEDIATE confirmatory block, which is a governance
    # decision and establishes no predictive superiority.
    # ...and once more when the supplementary M3I-2 contract was locked, the
    # official-source evidence capture completed and the final official
    # documentary recovery was INITIATED; the pointer now names a human
    # inquiry-submission action that is NOT authorized.
    # ...and once more when the human supervisor voluntarily terminated the
    # Track A waiting period and froze M3-LAG-WDI's final disposition
    # (2026-08-08); both pointer chains now converge on
    # `human-decision-required`.
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    assert state["m2_incremental_evaluation_authorized"] is False
    # The one-action authorization was CONSUMED, which is why the flag above
    # is False. That never erases the executed modeling: the authorized
    # paired M2 evaluation really did fit 44 canonical development models.
    assert state["m2_modeling_started"] is True
    assert state["stage127_m2_incremental_evaluation_primary_model_fits"] == 44
    assert state["m2_block_retained"] is True


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
        "`stage126-m1-robustness-part6-smote-training-fold-only`" in text
    assert "Last completed research action" not in text, (
        "a robustness micro-part must never be labelled a research action"
    )
    assert (
        "- **Next research action:** "
        "`human-decision-required`" in text
    )


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


# --------------------------------------------------------------------------- #
# M3 macro data Gate — canonical state consistency (no contradictions)
# --------------------------------------------------------------------------- #

def _handoff_state() -> dict:
    with open(os.path.join(REAL_ROOT, "project/docs/ai/handoff_state.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def _roadmap_text() -> str:
    with open(os.path.join(REAL_ROOT, "project/docs/ai/ROADMAP.md"),
              encoding="utf-8") as fh:
        return fh.read()


def _open_tasks_text() -> str:
    with open(os.path.join(REAL_ROOT, "project/docs/ai/OPEN_TASKS.md"),
              encoding="utf-8") as fh:
        return fh.read()


def test_active_workstream_identifies_the_m3_macro_gate():
    state = _handoff_state()
    assert state["m3_macro_data_gate_executed"] is True
    # The live label is the supplementary M3I-2 contract lock, which succeeded
    # the CBI M3 Gate; neither older label may be the CURRENT one.
    assert state["active_workstream"] == (
        "stage128_m3i2_final_official_documentary_recovery")
    assert state["active_workstream"] not in (
        "stage128_m2_d2_boundary_month_equity_return",
        "stage128_m3_macro_data_gate")
    assert state["active_workstream_predecessor_context"] == (
        "stage128_m3i2_official_source_evidence_capture")


def test_m3_data_workstream_started_but_modeling_did_not():
    state = _handoff_state()
    assert state["m3_data_workstream_started"] is True
    assert state["m3_modeling_started"] is False
    assert state["m3_incremental_evaluation_authorized"] is False
    assert state["m3_block_admitted_for_incremental_evaluation"] is False
    assert state["m3_macro_data_gate_human_review_required"] is True
    assert state["m3_macro_data_gate_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert state["stage128_m3_macro_data_gate_authorization_consumed"] is True


def test_pointers_are_unchanged_because_the_gate_is_unresolved():
    """The UNRESOLVED CBI Gate never advanced the pointer to its own successor.

    The pointer did advance later, but only because a DIFFERENT, separately
    authorized action — the supplementary M3I-2 contract lock — completed. The
    CBI Gate's own successor was never created.
    """
    state = _handoff_state()
    # The pointer has since advanced once more: the human supervisor
    # voluntarily terminated the Track A waiting period and froze M3-LAG-WDI's
    # final disposition (2026-08-08), which is its own separately recorded
    # decision — not the CBI Gate's successor either.
    assert state["last_completed_research_action_id"] == (
        "stage128-m3i2-track-a-waiting-termination-and-m3-disposition")
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_id"] != (
        "stage128-m3-incremental-evaluation")
    assert state["m3_macro_data_gate_human_review_required"] is True


def test_current_state_does_not_say_the_m3_gate_was_not_executed():
    """The exact contradiction present in the reviewed head must be gone."""
    text = _current_state_text()
    for stale in ("no M3 Gate executed",
                  "no M3 Gate was executed",
                  "M3 Gate not executed",
                  "M3 Gate not started",
                  "M3 Gate not authorized"):
        assert stale not in text, stale


def test_current_state_says_the_m3_gate_was_executed():
    text = _current_state_text()
    assert "M3 macro DATA Gate" in text
    assert "**Executed:** True" in text
    assert "UNRESOLVED_M3_DATA_GATE" in text
    assert ("**Active workstream:** "
            "`stage128_m3i2_final_official_documentary_recovery`") in text


def test_current_state_cannot_both_assert_and_deny_gate_execution():
    text = _current_state_text()
    executed = "**Executed:** True" in text
    denied = "no M3 Gate executed" in text
    assert not (executed and denied)
    assert executed


def test_roadmap_no_longer_labels_the_m3_gate_unauthorized_or_unstarted():
    text = _roadmap_text()
    front = text.split("---")[1]
    assert ("active_research_workstream_id: "
            "stage128-m3i2-final-official-documentary-recovery") in front
    assert ("predecessor_research_workstream_id: "
            "stage128-m3i2-official-source-evidence-capture") in front
    # the stale live-workstream label must not be the ACTIVE one
    assert ("active_research_workstream_id: "
            "stage128-m2-d2-boundary-month-equity-return") not in front
    # item 25 must not still call the Gate a pointer-only, unstarted action
    assert "NEXT POINTER ONLY; NOT authorized and NOT started" not in text
    assert "EXECUTED once as a DATA-ADMISSION GATE ONLY" in text


def test_open_tasks_no_longer_calls_stage127_m2_the_current_action():
    text = _open_tasks_text()
    assert ("The current scientific action is `stage127-m2-incremental-"
            "evaluation`") not in text
    assert ("`stage128-m3i2-prospective-contract-lock` — **COMPLETE**"
            in text)
    assert ("## Active research workstream: "
            "`stage128-m3i2-final-official-documentary-recovery`") in text
    assert ("## Active research workstream: "
            "`stage128-m2-d2-boundary-month-equity-return`") not in text
    # the M2 description is preserved, but explicitly as history
    assert "### Predecessor scientific action (HISTORICAL)" in text


def test_handoff_fields_and_roadmap_front_matter_agree():
    state = _handoff_state()
    front = _roadmap_text().split("---")[1]
    front_map = dict(
        line.split(":", 1) for line in front.strip().splitlines() if ":" in line)
    front_map = {k.strip(): v.strip() for k, v in front_map.items()}
    assert front_map["active_research_workstream_id"].replace("-", "_") == (
        state["active_workstream"])
    assert front_map["last_completed_research_action_id"] == (
        state["last_completed_research_action_id"])
    assert front_map["next_research_action_id"] == (
        state["next_research_action_id"])
    assert front_map["m3_macro_data_gate_status"] == (
        state["m3_macro_data_gate_status"])


def test_access_probe_evidence_downgrade_is_reflected_in_open_tasks():
    text = _open_tasks_text()
    assert "UNVERIFIED_CAPTURE_METADATA_ONLY" in text
    assert "programmer-reported" in text.lower()


# --------------------------------------------------------------------------- #
# Stage128 — supplementary M3I-2 prospective contract lock
# --------------------------------------------------------------------------- #

def test_m3i2_contract_lock_markers_are_recognized():
    state = _handoff_state()
    assert state["stage128_m3i2_contract_lock_executed"] is True
    assert state["stage128_m3i2_contract_status"] == (
        "PROSPECTIVELY_LOCKED_NO_DATA")
    assert state["stage128_m3i2_contract_lock_authorization_consumed"] is True
    assert state["m3i2_retrieval_started"] is False
    assert state["m3i2_data_gate_executed"] is False
    assert state["m3i2_block_admitted"] is False
    assert state["m3i2_incremental_evaluation_authorized"] is False
    assert state["m3i2_modeling_started"] is False
    assert state["m3i3_financing_lock"] == "UNRESOLVED_METADATA_LOCK"
    assert state["m3i3_admitted"] is False
    assert state["m3i_is_supplementary_not_confirmatory_m3"] is True


def test_m3i2_contract_lock_preserves_the_cbi_block_and_the_firewall():
    state = _handoff_state()
    assert state["m3_macro_data_gate_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert state["m3_block_admitted_for_incremental_evaluation"] is False
    assert state["m3_incremental_evaluation_authorized"] is False
    assert state["m3_modeling_started"] is False
    assert state["m4_authorized"] is False and state["m4_started"] is False
    assert state["final_test_locked"] is True
    assert state["next_research_action_authorized"] is False


def test_m3i2_provenance_baseline_is_still_the_pr73_head():
    """The PR #73 merge does not move the audited scientific baseline."""
    state = _handoff_state()
    assert state["stage128_m3i2_baseline_pr_number"] == 73
    assert state["stage128_m3i2_baseline_commit"] == (
        "e6db63fb7d105f0d3a39db101c9e364161c367e9")
    assert state["stage128_m3i2_provenance_baseline_commit"] == (
        "e6db63fb7d105f0d3a39db101c9e364161c367e9")
    assert state["stage128_m3i2_provenance_baseline_commit"] != (
        "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")


def test_m3i2_contract_time_topology_is_the_post_merge_retargeted_state():
    """PR #74 topology is retained ONLY under contract-time field names."""
    state = _handoff_state()
    assert state["stage128_m3i2_predecessor_pr_merged"] is True
    assert state["stage128_m3i2_predecessor_pr_merge_commit"] == (
        "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")
    assert state["stage128_m3i2_contract_time_pr_number"] == 74
    assert state["stage128_m3i2_contract_time_pr_base_branch"] == "main"
    assert state["stage128_m3i2_contract_time_pr_base_commit"] == (
        "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")
    assert state["stage128_m3i2_contract_time_main_commit"] == (
        "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")
    assert state["stage128_m3i2_contract_time_pr_semantics"] == (
        "historical_contract_lock_topology_superseded_by_pr75")
    assert state["stage128_m3i2_pr_is_stacked_on_open_predecessor"] is False
    assert state[
        "stage128_m3i2_retargeted_to_main_after_predecessor_merge_verified"
    ] is True
    assert state["stage128_m3i2_may_target_main"] is True


def test_m3i2_contract_time_pr74_stays_draft_unmerged_and_unauthorized():
    state = _handoff_state()
    assert state["stage128_m3i2_contract_time_pr_is_draft"] is True
    assert state["stage128_m3i2_contract_time_pr_merged"] is False
    assert state["stage128_m3i2_merge_authorized"] is False
    assert state["next_research_action_authorized"] is False


def test_m3i2_marker_derivation_fails_closed_on_a_contradictory_artifact(
    tmp_path,
):
    rel = gen._STAGE128_M3I2_CONTRACT_LOCK_REL
    src = os.path.join(REAL_ROOT, rel)
    payload = json.load(open(src, encoding="utf-8"))
    assert gen.derive_stage128_m3i2_contract_lock_markers(REAL_ROOT)

    for field, bad in (
        ("m3i2_data_gate_executed", True),
        ("m3i2_modeling_started", True),
        ("m3i3_admitted", True),
        ("m3_cbi_contract_changed", True),
        ("merge_authorized", True),
        ("m4_started", True),
        ("final_test_locked", False),
        ("macro_observations_read", 12),
        ("m3_cbi_gate_status", "PASS_FOR_M3_INCREMENTAL_EVALUATION"),
        ("next_action_authorized", True),
    ):
        root = tmp_path / field.replace("/", "_")
        (root / os.path.dirname(rel)).mkdir(parents=True, exist_ok=True)
        broken = dict(payload)
        broken[field] = bad
        (root / rel).write_text(
            json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(gen.HandoffError):
            gen.derive_stage128_m3i2_contract_lock_markers(str(root))


@pytest.mark.parametrize("mutation", [
    # predecessor merged but the base still names the predecessor branch
    {"live_pr_base_branch": "stage128-m3-macro-data-gate"},
    # predecessor unmerged while the base is main
    {"predecessor_pr_merged": False, "live_pr_base_branch": "main"},
    # merged without / with the wrong merge commit
    {"predecessor_pr_merge_commit": None},
    {"predecessor_pr_merge_commit": "0" * 40},
    # live base SHA not equal to current main
    {"live_pr_base_commit": "e6db63fb7d105f0d3a39db101c9e364161c367e9"},
    # provenance baseline replaced by the merge commit
    {"scientific_provenance_baseline_commit":
        "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a"},
    # PR marked ready or merged, or merge authorized
    {"live_pr_is_draft": False},
    {"live_pr_merged": True},
    {"merge_authorized": True},
])
def test_m3i2_topology_mutations_fail_closed(tmp_path, mutation):
    rel = gen._STAGE128_M3I2_CONTRACT_LOCK_REL
    src = os.path.join(REAL_ROOT, rel)
    payload = json.load(open(src, encoding="utf-8"))

    root = tmp_path / "topology"
    (root / os.path.dirname(rel)).mkdir(parents=True, exist_ok=True)
    broken = copy.deepcopy(payload)
    broken["live_topology"].update(mutation)
    (root / rel).write_text(
        json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3i2_contract_lock_markers(str(root))


# --------------------------------------------------------------------------- #
# Stage128 — historical (PR #74) vs LIVE (PR #75) M3I-2 PR topology
# --------------------------------------------------------------------------- #

def test_pr74_is_only_historical_and_never_live():
    """No field and no phrase may present PR #74 as the live PR."""
    state = _handoff_state()
    assert state["stage128_m3i2_contract_time_pr_number"] == 74
    assert state["stage128_m3i2_contract_time_pr_semantics"] == (
        "historical_contract_lock_topology_superseded_by_pr75")
    # every live/current field that carries a PR number must name 75, not 74
    for key, value in state.items():
        if key.startswith("stage128_m3i2_live_"):
            assert value != 74, key
            assert value != "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a", key
    text = _current_state_text()
    for phrase in ("PR #74 is the live", "live PR #74", "current draft PR #74",
                   "PR #74 (the LIVE", "PR #74 (the evidence-capture PR)"):
        assert phrase not in text
    assert "PR #74 is the **historical contract-lock PR**" in text


def test_live_pr_topology_is_the_track_b_pr_on_main():
    # PR #77 has since been merged into `main` and is now the predecessor; the
    # LIVE Draft PR is the Track B M3-LAG-WDI contract-lock PR, on `main` @ the
    # PR #77 merge commit. A MERGED PR is never the live Draft.
    state = _handoff_state()
    # PR #78 (the contract lock) has MERGED, so the live Draft is now the
    # retrieval PR #79, based on #78's merge commit.
    assert state["stage128_m3i2_live_pr_number"] == 79
    assert state["stage128_m3i2_live_pr_base_branch"] == "main"
    assert state["stage128_m3i2_live_pr_base_commit"] == (
        "175e7949e009eeecdd66aedab31ec4b48e9d3c7d")
    assert state["stage128_m3i2_live_main_commit"] == (
        "175e7949e009eeecdd66aedab31ec4b48e9d3c7d")
    assert state["stage128_m3i2_live_pr_is_draft"] is True
    assert state["stage128_m3i2_live_pr_merged"] is False
    assert state["stage128_m3i2_live_pr_ready_for_review_authorized"] is False
    assert state["stage128_m3i2_live_pr_role"] == (
        "m3_lag_wdi_exploratory_data_retrieval_pr")
    # The contract-lock PR is HISTORY now, with its merge commit pinned.
    assert state["stage128_m3_lag_wdi_contract_lock_pr_number"] == 78
    assert state["stage128_m3_lag_wdi_contract_lock_pr_merged"] is True
    assert state["stage128_m3_lag_wdi_contract_lock_pr_merge_commit"] == (
        "175e7949e009eeecdd66aedab31ec4b48e9d3c7d")
    assert state["stage128_m3_lag_wdi_contract_lock_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr79")
    # The human-submission recording PR is HISTORY under its OWN role.
    assert state["stage128_m3i2_human_submission_pr_number"] == 77
    assert state["stage128_m3i2_human_submission_pr_merged"] is True
    assert state["stage128_m3i2_human_submission_pr_merge_commit"] == (
        "93de6bae9344ce893b0261f818abce8a991cf842")
    # #77 was superseded by #78, NOT by whatever Draft is live now.
    assert state["stage128_m3i2_human_submission_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr78")
    # Re-anchoring the LIVE topology onto PR #79 must NOT shift the older
    # documentary-recovery role forward: that is PR #76, permanently.
    assert state["stage128_m3i2_recovery_pr_number"] == 76
    assert state["stage128_m3i2_recovery_pr_merged"] is True
    assert state["stage128_m3i2_recovery_pr_merge_commit"] == (
        "89d8e6ff2d12ec82903cd28aa7ab839eb946b658")
    assert state["stage128_m3i2_recovery_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr77")
    assert state["stage128_m3i2_evidence_capture_pr_number"] == 75
    assert state["stage128_m3i2_evidence_capture_pr_merged"] is True
    assert state["stage128_m3i2_evidence_capture_pr_merge_commit"] == (
        "b3627809dbfde8429d0308bec5d1c8541a161188")


def test_current_state_never_calls_a_merged_pr_the_live_draft():
    text = _current_state_text()
    # Both merged PRs are rendered as history, each under its own role, and
    # neither is re-labelled as the other.
    assert "**HISTORICAL PR roles (pinned, never re-derived):**" in text
    assert ("PR #76 = `final_official_documentary_recovery_initiation_pr`"
            in text)
    assert ("PR #77 = `final_official_inquiry_human_submission_recording_pr`"
            in text)
    assert ("PR #78 = `m3_lag_wdi_exploratory_contract_lock_pr`" in text)
    assert "the LIVE Draft PR is **PR #79**" in text
    # the merged predecessors must never be rendered as the live Draft
    assert "the LIVE Draft PR is **PR #78**" not in text
    assert "**PR #78** (the LIVE Draft PR)" not in text
    assert "**PR #77** (the LIVE Draft PR)" not in text
    assert "**PR #76** (the LIVE Draft PR)" not in text
    assert "**PR #75** (the LIVE Draft PR)" not in text


def test_live_pr_head_is_derived_from_the_repository_head_not_pinned():
    state = _handoff_state()
    # An engineering anchor, labelled as such: it is the repository head at
    # generation time, NOT the instantaneous GitHub PR head.
    assert state["stage128_m3i2_live_pr_head_commit_source"] == (
        "repository_head_at_generation_not_github_pr_head")
    # HEAD-relative, therefore excluded from the semantic projection
    assert "stage128_m3i2_live_pr_head_commit" in gen.VOLATILE_FIELDS
    assert "stage128_m3i2_live_pr_head_commit" not in gen.projection(state)
    # and it must never be pinned to a superseded audited head
    assert state.get("stage128_m3i2_live_pr_head_commit") != (
        state["stage128_m3i2_live_pr_base_commit"])


def test_evidence_capture_and_retrieval_are_recorded_as_completed():
    state = _handoff_state()
    assert state["stage128_m3i2_evidence_capture_executed"] is True
    assert state["stage128_m3i2_official_source_retrieval_completed"] is True


def test_contract_time_retrieval_marker_is_kept_false_with_semantics():
    state = _handoff_state()
    assert state["m3i2_retrieval_started"] is False
    assert state["m3i2_retrieval_started_semantics"] == (
        "contract_lock_time_marker_superseded_by_official_source_evidence"
        "_capture")


def test_topology_correction_admits_nothing():
    """Distinguishing history from live state moves no scientific state."""
    state = _handoff_state()
    assert state["m3i2_data_gate_executed"] is False
    assert state["m3i2_block_admitted"] is False
    assert state["m3i2_modeling_started"] is False
    assert state["m3i2_incremental_evaluation_authorized"] is False
    assert state["stage128_m3i2_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
    assert state["final_test_locked"] is True
    assert state["m4_authorized"] is False and state["m4_started"] is False
    assert state["stage128_m3i2_merge_authorized"] is False


def test_live_pr_topology_derivation_fails_closed(tmp_path):
    decision_rel = gen._STAGE128_M3I2_EVIDENCE_DECISION_REL
    boundary_rel = gen._STAGE128_M3I2_GOVERNANCE_BOUNDARY_REL
    audit_rel = gen._STAGE128_M3I2_INDEPENDENT_AUDIT_REL
    sources = {rel: json.load(open(os.path.join(REAL_ROOT, rel),
                                   encoding="utf-8"))
               for rel in (decision_rel, boundary_rel, audit_rel)}
    assert gen.derive_stage128_m3i2_live_pr_topology_markers(REAL_ROOT)

    def _build(name, mutations=(), drop=()):
        root = tmp_path / name
        for rel, payload in sources.items():
            if rel in drop:
                continue
            body = copy.deepcopy(payload)
            for rel_target, field, value in mutations:
                if rel_target == rel:
                    body[field] = value
            (root / os.path.dirname(rel)).mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(
                json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return str(root)

    # a missing corroborating artifact is fatal, never a silent default
    for rel in (boundary_rel, audit_rel):
        with pytest.raises(gen.HandoffError):
            gen.derive_stage128_m3i2_live_pr_topology_markers(
                _build("drop_" + os.path.basename(rel), drop=(rel,)))

    for name, mutation in (
        # base branch disagreement / non-main base
        ("branch", (boundary_rel, "pr_base_branch", "stage128-m3-macro-data-gate")),
        ("branch_audit", (audit_rel, "audited_pr_base_branch", "dev")),
        # base commit disagreement (e.g. the superseded PR #74 base)
        ("base", (audit_rel, "audited_pr_base_sha",
                  "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")),
        ("base_decision", (decision_rel, "baseline_commit",
                           "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")),
        # the live PR marked ready, merged-authorized, or not a successor
        ("draft", (decision_rel, "pr_is_draft", False)),
        ("merge", (boundary_rel, "merge_authorized", True)),
        ("number", (audit_rel, "pr_number", 74)),
        ("number_type", (audit_rel, "pr_number", "75")),
        # main base claimed while the predecessor PR is not merged
        ("predecessor", (decision_rel, "predecessor_pr_merged", False)),
    ):
        with pytest.raises(gen.HandoffError):
            gen.derive_stage128_m3i2_live_pr_topology_markers(
                _build(name, mutations=(mutation,)))


def test_current_state_renders_the_m3i2_contract_lock_section():
    text = _current_state_text()
    assert "M3I-2 prospective contract lock" in text
    assert "PROSPECTIVELY_LOCKED_NO_DATA" in text
    assert "UNRESOLVED_METADATA_LOCK" in text
    assert "e6db63fb7d105f0d3a39db101c9e364161c367e9" in text
    # exactly one live next-action pointer, and it is not an authorization
    pointers = [ln for ln in text.splitlines()
                if ln.startswith("- **Next research action (pointer only):**")]
    assert len(pointers) == 1
    assert "human-decision-required" in pointers[0]


# --------------------------------------------------------------------------- #
# Stage128 — M3I-2 post-capture independent bundle integrity audit
# --------------------------------------------------------------------------- #

def _audit_record() -> dict:
    with open(os.path.join(REAL_ROOT, gen._STAGE128_M3I2_INDEPENDENT_AUDIT_REL),
              encoding="utf-8") as fh:
        return json.load(fh)


def _audit_root(tmp_path, name: str, payload: dict) -> str:
    """Write ``payload`` as the only audit record under a fresh temp root."""
    rel = gen._STAGE128_M3I2_INDEPENDENT_AUDIT_REL
    root = tmp_path / name
    (root / os.path.dirname(rel)).mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(root)


def test_m3i2_independent_bundle_audit_markers_are_recognized():
    state = _handoff_state()
    assert state["stage128_m3i2_independent_bundle_integrity_audit"] == (
        "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS")
    assert state["stage128_m3i2_independent_bundle_audit_verification_type"] \
        == "external_independent_bundle_integrity_audit"
    assert state["stage128_m3i2_independent_audit_completed"] is True
    assert state["stage128_m3i2_independently_verified_by_auditor"] is True
    assert state["stage128_m3i2_auditor_independent_from_pr_author"] is True
    assert state["stage128_m3i2_auditor_independent_from_bundle_creator"] \
        is True
    assert state["stage128_m3i2_auditor_participated_in_artifact_creation"] \
        is False
    assert state["stage128_m3i2_audited_pr_number"] == 75
    assert state["stage128_m3i2_audited_pr_head_sha"] == (
        "187c628a17f6e429fbf6455412f5f655d2f3602e")
    assert state["stage128_m3i2_audit_primary_members_expected"] == 24
    assert state["stage128_m3i2_audit_primary_members_found"] == 24


def test_the_committed_audit_record_derives_cleanly():
    """The positive case: the real record passes every fail-closed check."""
    markers = gen.derive_stage128_m3i2_independent_bundle_audit_markers(
        REAL_ROOT)
    assert markers["stage128_m3i2_independent_bundle_integrity_audit"] == (
        "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS")
    assert markers["stage128_m3i2_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")


def test_a_missing_audit_record_yields_no_markers(tmp_path):
    """Absence is silent; only a PRESENT-but-wrong record is an error."""
    assert gen.derive_stage128_m3i2_independent_bundle_audit_markers(
        str(tmp_path / "empty")) == {}


#: Every integrity, provenance and firewall claim the audit record makes.
#: A wrong value — and, for booleans, a missing key — must fail closed.
_AUDIT_MUTATIONS = [
    # hash / CRC / ZIP structure
    {"all_part_hashes_match": False},
    {"all_zip_crc_checks_pass": False},
    {"all_zip_structures_valid": False},
    # member counts and uniqueness
    {"primary_members_expected": 23},
    {"primary_members_found": 23},
    {"primary_members_unique": False},
    {"all_member_hashes_match": False},
    {"all_member_sizes_match": False},
    # request / response counts
    {"request_count": 20},
    {"response_count": 20},
    {"successful_response_count": 20},
    {"failed_response_count": 1},
    # invocation and host restrictions
    {"capture_invocations": 3},
    {"third_invocation_present": True},
    {"official_hosts_only": False},
    # original single bundle
    {"original_single_bundle_present": False},
    {"original_single_bundle_directly_rechecked": False},
    {"original_single_bundle_hash_match": False},
    # audited PR / head
    {"pr_number": 74},
    {"audited_pr_head_sha": "0" * 40},
    # audit scope
    {"audit_scope_includes": ["bundle_integrity"]},
    {"audit_scope_includes": [
        "bundle_integrity", "sha256", "zip_crc", "multipart_structure",
        "manifest_consistency", "official_source_restrictions",
        "raw_member_integrity", "coverage"]},
    {"audit_scope_excludes": ["coverage"]},
    {"audit_scope_excludes": [
        "coverage", "data_gate", "modeling", "final_test"]},
    # scientific firewalls — an integrity PASS may never move these
    {"m3i2_admitted": True},
    {"m3i2_evidence_status": "RESOLVED_OFFICIAL_SOURCE_EVIDENCE"},
    {"data_gate_executed": True},
    {"final_test_locked": False},
    {"merge_authorized": True},
    {"m4_authorized": True},
    {"modeling_started": True},
    {"historical_vintage_problem_resolved": True},
    {"data_gate_executions": 1},
    {"model_fits": 1},
    {"network_requests": 1},
    {"coverage_calculations": 1},
    {"final_test_rows_read": 1},
    # independence and audit provenance
    {"independent_audit_completed": False},
    {"independently_verified_by_auditor": False},
    {"auditor_independent_from_pr_author": False},
    {"auditor_independent_from_bundle_creator": False},
    {"auditor_participated_in_artifact_creation": True},
    {"capture_time_manifest_retained_unmodified": False},
    {"capture_time_delivered_to_independent_auditor": True},
    {"capture_time_independently_verified_by_auditor": True},
    {"capture_time_values_superseded_by_this_record": False},
    {"audit_result_relies_on_prior_session_execution_by_auditor": False},
    # taxonomy of the record itself
    {"record_type": "developer_side_check"},
    {"verification_type":
     "developer_side_deterministic_verification_not_independent_audit"},
    {"overall_result": "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_FAIL"},
]


@pytest.mark.parametrize("mutation", _AUDIT_MUTATIONS)
def test_audit_record_mutations_fail_closed(tmp_path, mutation):
    broken = copy.deepcopy(_audit_record())
    broken.update(mutation)
    root = _audit_root(tmp_path, "mutated", broken)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3i2_independent_bundle_audit_markers(root)


@pytest.mark.parametrize("field", sorted(
    {key for mutation in _AUDIT_MUTATIONS for key in mutation}))
def test_a_dropped_audit_field_fails_closed(tmp_path, field):
    """No optimistic defaults: a missing claim is as bad as a false one."""
    broken = copy.deepcopy(_audit_record())
    broken.pop(field)
    root = _audit_root(tmp_path, "dropped", broken)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3i2_independent_bundle_audit_markers(root)


def test_current_state_renders_the_m3i2_evidence_capture_section():
    text = _current_state_text()
    assert "### Stage128 — M3I-2 official-source evidence capture" in text
    assert "21 requests" in text and "21 successful responses" in text
    assert "1,066,295,643" in text
    assert "16 captured and held out of 110 discovered" in text
    assert "verified release dates 0 of 110" in text
    assert "cutoffs 37 of 37" in text
    assert "development pairs 539 of 539" in text
    assert "CPI 16 PASS" in text and "FX 16 UNRESOLVED" in text
    assert "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE" in text
    assert "NOT_EXECUTED" in text


def test_current_state_marks_the_contract_lock_section_as_historical():
    text = _current_state_text()
    assert "M3I-2 prospective contract lock (HISTORICAL, contract-time)" \
        in text
    assert "This section describes CONTRACT-TIME state" in text
    # the stale live-state claims are gone
    assert "Data collection has **not** started" not in text
    assert "Data collection has not started" not in text
    # the live topology belongs to the evidence-capture section, never to the
    # historical contract-lock section
    contract_section = text.split(
        "### Stage128 — M3I-2 prospective contract lock", 1)[1].split(
        "### Stage128 — M3I-2 official-source evidence capture", 1)[0]
    assert "- **Live PR topology:**" not in contract_section
    assert "- **LIVE PR topology:** the LIVE Draft PR is **PR #79**" in text


def test_current_state_does_not_present_pr74_as_the_live_draft():
    text = _current_state_text()
    assert "PR #74 is the **historical contract-lock PR**" in text
    assert "the LIVE Draft PR is **PR #79**" in text
    # no merged PR may ever be presented as the live one
    assert "carried by **PR #75** (the LIVE evidence-capture PR)" not in text
    assert "carried by **PR #76** (the LIVE Draft PR)" not in text
    for line in text.splitlines():
        if "PR #74" in line:
            assert "historical" in line.lower(), line


def test_current_state_audit_section_moves_nothing_scientific():
    text = _current_state_text()
    assert "M3I-2 independent bundle integrity audit (integrity only)" in text
    assert "does **not** resolve the historical-vintage evidence problem" \
        in text


# --------------------------------------------------------------------------- #
# Stage128 — ROADMAP item 25b must agree with the MERGED PR #75 artifacts
#
# Item 25b is prose about a merged, immutable evidence-capture package. Prose
# drifts; the artifacts do not. These tests read the four authoritative
# artifacts of that package and fail closed when the ROADMAP claims anything
# the artifacts do not support — in either direction. They are a documentation
# gate only: they retrieve nothing, admit nothing and never touch a Gate.
# --------------------------------------------------------------------------- #

_M3I2_CAPTURE_DIR = "project/stage128/m3i2_official_source_evidence_capture"
_M3I2_CAPTURE_DECISION_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_official_source_evidence_decision.json")
_M3I2_RELEASE_MANIFEST_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_wdi_archive_release_manifest.csv")
_M3I2_SEMANTIC_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_wdi_vintage_semantic_compatibility.csv")
_M3I2_INTEGRITY_AUDIT_REL = (
    f"{_M3I2_CAPTURE_DIR}/"
    "stage128_m3i2_independent_bundle_integrity_audit_record.json")
_M3I2_CUTOFF_PLAN_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_unique_cutoff_plan.csv")
_M3I2_REQUIRED_EDITIONS_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_required_wdi_editions.csv")
_M3I2_LOCKED_SERIES_REL = (
    f"{_M3I2_CAPTURE_DIR}/stage128_m3i2_wdi_irn_locked_series_extract.csv")

#: Claims that were once in item 25b and are contradicted by the artifacts.
#: They must never come back — not even softened, and not as live fact.
_M3I2_SUPERSEDED_ROADMAP_CLAIMS = (
    "66 carry",
    "66 editions",
    "16 required editions were selected",
    "32/32 semantic",
    "earliest verified archive edition",
    "19 of 37",
    "252 of 539",
)


def _csv_rows(rel: str) -> list[dict]:
    import csv
    with open(os.path.join(REAL_ROOT, rel), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _json_artifact(rel: str) -> dict:
    with open(os.path.join(REAL_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _roadmap_item_25b() -> str:
    """Item 25b only — a claim elsewhere in the ROADMAP is a different claim."""
    text = _roadmap_text()
    start = text.index(
        "25b. `stage128-m3i2-official-source-evidence-capture`")
    end = text.index("\n25c.", start)
    return text[start:end]


def test_m3i2_capture_artifacts_are_the_ones_the_roadmap_is_checked_against():
    """Guard the guard: a renamed or missing artifact must fail, not skip."""
    for rel in (
        _M3I2_CAPTURE_DECISION_REL, _M3I2_RELEASE_MANIFEST_REL,
        _M3I2_SEMANTIC_REL, _M3I2_INTEGRITY_AUDIT_REL,
        _M3I2_CUTOFF_PLAN_REL, _M3I2_REQUIRED_EDITIONS_REL,
        _M3I2_LOCKED_SERIES_REL,
    ):
        assert os.path.isfile(os.path.join(REAL_ROOT, rel)), rel


def test_roadmap_25b_records_the_edition_counts_the_artifacts_support():
    """110 discovered / 16 captured — and ZERO of either verified."""
    editions = _csv_rows(_M3I2_RELEASE_MANIFEST_REL)
    required = _csv_rows(_M3I2_REQUIRED_EDITIONS_REL)
    assert len(editions) == 110
    assert len(required) == 16
    # Not one edition has a verified release date, in either artifact.
    assert sum(
        1 for r in editions if r["release_date_verified"] == "True") == 0
    assert sum(
        1 for r in required if r["release_date_verified"] == "True") == 0
    assert sum(1 for r in editions if r["derived_release_available_at_utc"]) == 0
    assert sum(1 for r in required if r["release_available_at_utc"]) == 0
    # ...and none may serve as a pre-cutoff vintage.
    assert sum(
        1 for r in required
        if r["usable_as_pre_cutoff_vintage"] == "True") == 0

    item = _roadmap_item_25b()
    assert "110 archive editions were discovered" in item
    assert "16 were captured and held" in item
    assert "`release_date_verified` is False for all 110" in item
    assert "editions with a verified `available_at` = 0" in item


def test_roadmap_25b_records_every_cutoff_and_pair_as_unresolved():
    """0 of 37 served; 37 of 37 and 539 of 539 unresolved."""
    plan = _csv_rows(_M3I2_CUTOFF_PLAN_REL)
    assert len(plan) == 37
    assert sum(
        int(r["number_of_development_pairs_sharing_cutoff"]) for r in plan
    ) == 539
    served = [r for r in plan if r["selected_wdi_archive_edition_id"]]
    assert served == []
    assert {r["selection_reason"] for r in plan} == {
        "NO_VERIFIED_PRE_CUTOFF_EDITION"}

    item = _roadmap_item_25b()
    assert "cutoffs with a verified pre-cutoff edition = 0 of 37" in item
    assert "all 37 cutoffs and all 539 development pairs" in item
    assert "are UNRESOLVED" in item
    # unresolved is never the same statement as zero coverage
    assert "never zero coverage" in item


def test_roadmap_25b_records_the_locked_series_row_count():
    assert len(_csv_rows(_M3I2_LOCKED_SERIES_REL)) == 1878
    assert "1,878 locked-series rows" in _roadmap_item_25b()


def test_roadmap_25b_records_cpi_pass_and_fx_unresolved_separately():
    """CPI 16/0/0 and FX 0/16/0 — one resolved indicator is not two."""
    rows = _csv_rows(_M3I2_SEMANTIC_REL)
    assert len(rows) == 32
    tally = {}
    for r in rows:
        tally.setdefault(r["indicator_code"], []).append(r["compatibility_status"])
    cpi = tally["FP.CPI.TOTL.ZG"]
    fx = tally["PA.NUS.FCRF"]
    assert (cpi.count("PASS"), cpi.count("UNRESOLVED"),
            cpi.count("FAIL_INTEGRITY")) == (16, 0, 0)
    assert (fx.count("PASS"), fx.count("UNRESOLVED"),
            fx.count("FAIL_INTEGRITY")) == (0, 16, 0)

    item = _roadmap_item_25b()
    assert "16 CPI PASS / 0 UNRESOLVED / 0 FAIL_INTEGRITY" in item
    assert "0 FX PASS / 16 FX UNRESOLVED / 0 FAIL_INTEGRITY" in item
    # FX must be named as its own open blocker, not folded into the vintage gap
    assert "independent, still-open blocker" in item


def test_roadmap_25b_records_the_unresolved_unadmitted_scientific_state():
    decision = _json_artifact(_M3I2_CAPTURE_DECISION_REL)
    assert decision["m3i2_official_source_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
    assert decision["m3i2_admitted"] is False
    assert decision["data_gate_executions"] == 0
    assert decision["data_gate_passed"] is False

    item = _roadmap_item_25b()
    assert "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE" in item
    assert "The Data Gate is `NOT_EXECUTED`" in item
    assert "`m3i2_admitted` is false" in item


def test_roadmap_25b_keeps_integrity_pass_separate_from_vintage_resolution():
    audit = _json_artifact(_M3I2_INTEGRITY_AUDIT_REL)
    assert audit["overall_result"] == "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS"
    # the audit itself refuses to be read as an evidence resolution
    assert audit["m3i2_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")

    item = _roadmap_item_25b()
    assert "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS" in item
    assert "integrity** result only" in item
    assert "does **not** resolve the historical-vintage problem" in item
    assert "does not create a verified release date" in item


def test_roadmap_25b_denies_that_a_filename_token_is_release_evidence():
    """The 66/44 split is token exactness, never a day-precision release date."""
    editions = _csv_rows(_M3I2_RELEASE_MANIFEST_REL)
    assert sum(
        1 for r in editions
        if r["release_date_explicitly_stated_by_official_source"] == "True"
    ) == 0
    assert {r["release_available_at_derivation_status"] for r in editions} == {
        "UNRESOLVED_FILENAME_DATE_TOKEN_NOT_VERIFIED_AS_RELEASE_DATE"}

    item = _roadmap_item_25b()
    assert "A filename date token is **not** a release date" in item
    assert "was never a day-precision release date" in item


@pytest.mark.parametrize("claim", _M3I2_SUPERSEDED_ROADMAP_CLAIMS)
def test_superseded_m3i2_claims_never_return_to_the_roadmap(claim):
    """Each of these was contradicted by the artifacts and must stay gone."""
    assert claim not in _roadmap_text(), (
        f"superseded M3I-2 evidence-capture claim reintroduced: {claim!r}"
    )


def test_roadmap_front_matter_pins_the_live_recovery_workstream():
    fm = gen.read_roadmap(REAL_ROOT)
    assert fm["active_research_workstream_id"] == (
        "stage128-m3i2-final-official-documentary-recovery")
    assert fm["predecessor_research_workstream_id"] == (
        "stage128-m3i2-official-source-evidence-capture")
    assert fm["last_completed_research_action_id"] == (
        "stage128-m3i2-track-a-waiting-termination-and-m3-disposition")
    assert fm["next_research_action_id"] == "human-decision-required"
    # the front-matter reader hands back the raw scalar; unauthorized either way
    assert fm["next_research_action_authorized"] in (False, "false")


def test_roadmap_marks_the_evidence_capture_paragraph_as_historical():
    """PR #75 is the merged predecessor; PR #76 is the live Draft."""
    text = _roadmap_text()
    para = [ln for ln in text.splitlines()
            if ln.startswith("**Workstream identifier note (HISTORICAL")]
    assert len(para) == 1, "the evidence-capture note must be marked HISTORICAL"
    note = para[0]
    assert "was live at that time" in note
    assert "retained only as historical state" in note
    assert "merged predecessor** (PR #75)" in note
    assert "the live Draft **PR #76**" in note
    # and it may no longer claim to be the current workstream
    assert "names the workstream that is live **now**. That is now " \
        "`stage128-m3i2-official-source-evidence-capture`" not in text


def test_handoff_agrees_the_capture_and_recovery_prs_are_merged():
    # Every predecessor is merged; the live Draft is the retrieval PR. Merged
    # and live are mutually exclusive, in every state field.
    state = _handoff_state()
    assert state["stage128_m3i2_evidence_capture_pr_number"] == 75
    assert state["stage128_m3i2_evidence_capture_pr_merged"] is True
    assert state["stage128_m3i2_recovery_pr_number"] == 76
    assert state["stage128_m3i2_recovery_pr_merged"] is True
    assert state["stage128_m3i2_human_submission_pr_number"] == 77
    assert state["stage128_m3i2_human_submission_pr_merged"] is True
    assert state["stage128_m3_lag_wdi_contract_lock_pr_number"] == 78
    assert state["stage128_m3_lag_wdi_contract_lock_pr_merged"] is True
    assert state["stage128_m3i2_live_pr_number"] == 79
    assert state["stage128_m3i2_live_pr_is_draft"] is True
    assert state["stage128_m3i2_live_pr_merged"] is False
    assert state["stage128_m3i2_merge_authorized"] is False
    # the general invariant: no merged PR number is the live one
    assert state["stage128_m3i2_live_pr_number"] not in {
        state["stage128_m3i2_evidence_capture_pr_number"],
        state["stage128_m3i2_recovery_pr_number"],
        state["stage128_m3i2_human_submission_pr_number"],
        state["stage128_m3_lag_wdi_contract_lock_pr_number"],
    }


# --------------------------------------------------------------------------- #
# Stage128 — the full-suite baseline comparison is a VERIFICATION record
#
# It reports how the test suite behaved on the baseline and on the candidate
# correction head. It must never become a scientific claim, must never claim
# to have tested the commit that carries it, and must be internally consistent
# — a record asserting "no new failures" while listing some is broken, and
# fails closed here rather than being trusted.
# --------------------------------------------------------------------------- #

_M3I2_SUITE_COMPARISON_REL = (
    "project/stage128/m3i2_final_official_documentary_recovery/"
    "stage128_m3i2_full_suite_baseline_comparison.json")


def _suite_comparison() -> dict:
    return _json_artifact(_M3I2_SUITE_COMPARISON_REL)


def _comparison_root(tmp_path, name: str, record: dict) -> str:
    """A minimal root carrying a mutated comparison record."""
    root = tmp_path / name
    pkg = root / "project/stage128/m3i2_final_official_documentary_recovery"
    pkg.mkdir(parents=True)
    for rel in (_M3I2_SUITE_COMPARISON_REL,
                gen._STAGE128_M3I2_RECOVERY_DECISION_REL):
        src = os.path.join(REAL_ROOT, rel)
        with open(src, encoding="utf-8") as fh:
            payload = json.load(fh)
        if rel == _M3I2_SUITE_COMPARISON_REL:
            payload = record
        with open(os.path.join(str(root), rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    return str(root)


def test_suite_comparison_evaluates_the_candidate_not_its_own_commit():
    rec = _suite_comparison()
    assert rec["report_commit_self_reference_avoided"] is True
    assert rec["baseline_sha"] == (
        "b3627809dbfde8429d0308bec5d1c8541a161188")
    # the candidate head is a real commit, and it is NOT the baseline
    assert re.fullmatch(r"[0-9a-f]{40}", rec["candidate_correction_head"])
    assert rec["candidate_correction_head"] != rec["baseline_sha"]


def test_suite_comparison_reports_no_new_failures():
    rec = _suite_comparison()
    base = set(rec["baseline_failure_node_ids"])
    cand = set(rec["candidate_failure_node_ids"])
    assert set(rec["new_failure_node_ids"]) == cand - base
    assert set(rec["preexisting_failure_node_ids"]) == base & cand
    assert set(rec["resolved_failure_node_ids"]) == base - cand
    assert rec["new_failure_node_ids"] == []
    assert rec["new_failures_count"] == 0
    assert rec["comparison_result"] == (
        "PASS_NO_PR_INTRODUCED_FULL_SUITE_FAILURES")


def test_suite_comparison_ran_both_sides_the_same_way():
    rec = _suite_comparison()
    assert rec["python_version"] == "3.13.5"
    assert rec["jdatetime_version"] == "6.0.1"
    for field in ("same_pytest_command", "same_assets",
                  "same_environment_variables",
                  "same_working_directory_semantics"):
        assert rec[field] is True, field
    # a comparison is only meaningful if the suite actually grew or held
    assert rec["candidate_tests_collected"] >= rec["baseline_tests_collected"]


def test_suite_comparison_hides_no_failure_by_deleting_a_test():
    rec = _suite_comparison()
    assert rec["no_test_was_deleted_or_weakened_to_hide_a_failure"] is True
    # every failure carries the evidence needed to check that claim by hand
    for row in rec["failure_details"]:
        assert row["node_id"]
        assert row["exception_class"]
        assert row["first_meaningful_failure_line"]
        assert isinstance(row["present_on_baseline"], bool)
        assert isinstance(row["present_on_candidate"], bool)
    covered = {row["node_id"] for row in rec["failure_details"]}
    assert covered == set(rec["baseline_failure_node_ids"]) | set(
        rec["candidate_failure_node_ids"])


def test_suite_comparison_moves_nothing_scientific():
    rec = _suite_comparison()
    assert rec["m3i2_evidence_status"] == "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"
    assert rec["m3i2_admitted"] is False
    assert rec["m3i2_data_gate_executed"] is False
    assert rec["m3_lag_wdi_authoritative_contract_status"] == "NOT_LOCKED"
    assert rec["final_test_locked"] is True
    assert rec["m4_authorized"] is False
    assert rec["merge_authorized"] is False
    assert rec["inquiry_submission_status"] == "HUMAN_SUBMISSION_REQUIRED"
    assert rec["network_requests_during_verification"] == 0
    assert rec["scientific_effect"] == "NONE_AUTHORITATIVE"


# --------------------------------------------------------------------------- #
# A CONSUMED one-time authorization may never read as a STANDING one
# --------------------------------------------------------------------------- #
#
# The naming contract, established by the step B retrieval markers and stated
# in their own comment, is that ``<prefix>_was_authorized`` holds the
# HISTORICAL fact while ``<prefix>_authorized`` and ``<prefix>_authorized_now``
# hold the STANDING permission. Publishing history in a standing field is how a
# spent one-time authorization comes to read as live permission to act again —
# which is exactly the drift these tests exist to prevent recurring.

def test_no_consumed_track_b_authorization_is_published_as_standing():
    state = _handoff_state()
    for prefix in gen._ONE_TIME_AUTHORIZATION_PREFIXES:
        if state.get(f"{prefix}_authorization_consumed") is not True:
            continue
        assert state[f"{prefix}_authorized"] is False, prefix
        assert state[f"{prefix}_authorized_now"] is False, prefix
        assert state[f"{prefix}_authorization_reusable"] is False, prefix
        # the history must survive the correction, not be erased by it
        assert state[f"{prefix}_was_authorized"] is True, prefix


def test_every_completed_track_b_step_records_history_not_permission():
    """Each executed step keeps its history AND publishes no live permission."""
    state = _handoff_state()
    executed = {
        "stage128_m3_lag_wdi_retrieval":
            state.get("stage128_m3_lag_wdi_data_retrieval_started"),
        "stage128_m3_lag_wdi_post_retrieval_audit":
            state.get("stage128_m3_lag_wdi_post_retrieval_audit_executed"),
        "stage128_m3_lag_wdi_data_gate":
            state.get("stage128_m3_lag_wdi_data_gate_executed"),
    }
    for prefix, ran in executed.items():
        if ran is not True:
            continue
        assert state[f"{prefix}_authorization_consumed"] is True, prefix
        assert state[f"{prefix}_was_authorized"] is True, prefix
        assert state[f"{prefix}_authorized"] is False, prefix
    # and the action sequence agrees: history in was_authorized, never in
    # authorized / authorized_now
    for entry in state["stage128_m3_lag_wdi_action_sequence"]:
        assert entry["authorized"] is False, entry["step"]
        assert entry["authorized_now"] is False, entry["step"]


@pytest.mark.parametrize("leaking_field", [
    "authorized", "authorized_now", "authorization_reusable"])
@pytest.mark.parametrize("prefix", gen._ONE_TIME_AUTHORIZATION_PREFIXES)
def test_the_generator_refuses_a_consumed_authorization_that_stands(
        prefix, leaking_field):
    with pytest.raises(gen.HandoffError):
        gen._assert_no_consumed_authorization_is_standing({
            f"{prefix}_authorization_consumed": True,
            f"{prefix}_was_authorized": True,
            f"{prefix}_{leaking_field}": True,
        })


@pytest.mark.parametrize("prefix", gen._ONE_TIME_AUTHORIZATION_PREFIXES)
def test_the_generator_refuses_a_consumed_authorization_without_history(
        prefix):
    """"Consumed" without a recorded grant would describe an authorization the
    state never admits existed."""
    with pytest.raises(gen.HandoffError):
        gen._assert_no_consumed_authorization_is_standing({
            f"{prefix}_authorization_consumed": True,
            f"{prefix}_was_authorized": False,
            f"{prefix}_authorized": False,
        })


@pytest.mark.parametrize("prefix", gen._ONE_TIME_AUTHORIZATION_PREFIXES)
def test_the_generator_accepts_the_correct_consumed_shape(prefix):
    state = {
        f"{prefix}_authorization_consumed": True,
        f"{prefix}_was_authorized": True,
        f"{prefix}_authorized": False,
        f"{prefix}_authorized_now": False,
        f"{prefix}_authorization_reusable": False,
    }
    assert gen._assert_no_consumed_authorization_is_standing(state) is state


def test_handoff_publishes_the_comparison_as_verification_only():
    state = _handoff_state()
    assert state["full_suite_baseline_comparison_completed"] is True
    assert state["full_suite_new_failures"] == 0
    assert state["full_suite_comparison_is_verification_not_science"] is True
    assert state["full_suite_comparison_self_reference_avoided"] is True
    # and it changed nothing about the scientific state
    assert state["m3i2_block_admitted"] is False
    assert state["m3i2_data_gate_executed"] is False
    assert state["final_test_locked"] is True
    # The comparison record itself still says NOT_LOCKED and always will: it is
    # a frozen verification artifact from before Track B was authorized. The
    # LIVE status has since advanced, under a separate explicit human
    # authorization, to the pre-retrieval contract lock — and the point of this
    # assertion is that the verification record did not move it.
    assert state["stage128_m3_lag_wdi_authoritative_contract_status"] == (
        "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL")
    # Retrieval, the Data Gate and step E each have their own separately
    # authorized actions and may legitimately have advanced, so none of them is
    # pinned here — doing so would encode a MOMENT. What a VERIFICATION record
    # can never move is the STANDING permission, which is False at every point
    # in the sequence: before step E because it had not been granted, and after
    # step E because its single-use grant was consumed.
    assert state["stage128_m3_lag_wdi_modeling_authorized"] is False
    if state["stage128_m3_lag_wdi_modeling_started"] is True:
        assert state["stage128_m3_lag_wdi_modeling_executed"] is True
        assert state[
            "stage128_m3_lag_wdi_modeling_authorization_consumed"] is True
        assert state["stage128_m3_lag_wdi_modeling_authorized_now"] is False


_COMPARISON_MUTATIONS = (
    {"new_failure_node_ids": ["project/tests/test_x.py::test_y"]},
    {"new_failures_count": 3},
    {"report_commit_self_reference_avoided": False},
    {"baseline_sha": "0" * 40},
    {"same_assets": False},
    {"no_test_was_deleted_or_weakened_to_hide_a_failure": False},
    {"final_test_locked": False},
    {"merge_authorized": True},
    {"m3i2_admitted": True},
    {"m3_lag_wdi_authoritative_contract_status": "LOCKED"},
    {"preexisting_failure_node_ids": []},
)


@pytest.mark.parametrize("mutation", _COMPARISON_MUTATIONS)
def test_a_dishonest_comparison_record_fails_closed(tmp_path, mutation):
    broken = copy.deepcopy(_suite_comparison())
    broken.update(mutation)
    root = _comparison_root(tmp_path, "broken", broken)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3i2_full_suite_comparison_markers(root)


def test_the_unmutated_comparison_record_is_accepted(tmp_path):
    """The mutation tests above are only meaningful if the real one passes."""
    root = _comparison_root(tmp_path, "clean", _suite_comparison())
    markers = gen.derive_stage128_m3i2_full_suite_comparison_markers(root)
    assert markers["full_suite_baseline_comparison_completed"] is True
    assert markers["full_suite_new_failures"] == 0


def test_absent_comparison_record_yields_no_markers(tmp_path):
    """Before the record exists the generator must stay silent, not guess."""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert gen.derive_stage128_m3i2_full_suite_comparison_markers(
        str(empty)) == {}


# --------------------------------------------------------------------------- #
# Stage128 — no stale M3I-2 gap claim may survive anywhere in the ROADMAP
#
# Item 25b was corrected against the merged PR #75 artifacts, but a downstream
# pointer (item 25e) still described the older, narrower reading: a "pre-2017
# vintage gap" affecting 19 of 37 cutoffs. The artifacts support no such
# partition — nothing is verified, so everything is unresolved. These guards
# sweep the WHOLE file, because a corrected paragraph is worth nothing while a
# neighbouring one still contradicts it.
# --------------------------------------------------------------------------- #

#: Every phrasing of the superseded partial-gap reading.
_M3I2_SUPERSEDED_GAP_CLAIMS = (
    "unresolved pre-2017 vintage gap",
    "pre-2017 vintage gap",
    "pre-2017",
    "19 unservable cutoffs",
    "19 of 37",
    "252 of 539",
    "earliest verified archive edition",
)


@pytest.mark.parametrize("claim", _M3I2_SUPERSEDED_GAP_CLAIMS)
def test_no_stale_m3i2_gap_claim_survives_anywhere_in_the_roadmap(claim):
    assert claim not in _roadmap_text(), (
        f"superseded M3I-2 vintage-gap claim present in ROADMAP: {claim!r}"
    )


def test_roadmap_states_the_authoritative_unresolved_totals():
    """Nothing verified means everything unresolved — no middle partition."""
    text = _roadmap_text()
    assert "cutoffs with a verified pre-cutoff edition = 0 of 37" in text
    assert "all 37 cutoffs and all 539 development pairs" in text
    assert "0 of 37 cutoffs has a verified pre-cutoff edition" in text
    assert "all 37 cutoffs and all 539 development pairs remain unresolved" \
        in text
    assert "editions with a verified `available_at` = 0" in text
    assert "`release_date_verified` is False for all 110" in text


def test_item_25e_is_historical_superseded_and_unauthorized():
    text = _roadmap_text()
    item = text[text.index("25e. `stage128-m3i2-official-source-evidence-"
                           "review`"):]
    item = item.split("\n26.", 1)[0]
    assert "HISTORICAL / SUPERSEDED POINTER ONLY" in item
    assert "NOT AUTHORIZED" in item
    assert "NOT the current next action" in item
    assert "retained only as historical state" in item or \
        "retained only as historical roadmap state" in item
    assert "authorizes no review, no Data Gate and no modeling" in item
    # it must hand the live pointer over to the action that really is next
    assert "stage128-m3i2-final-official-inquiry-response-ingestion" in item
    # and the superseded reading must not survive inside the item either
    for claim in _M3I2_SUPERSEDED_GAP_CLAIMS:
        assert claim not in item, claim


def test_the_current_next_pointer_is_human_decision_required_and_unauthorized():
    """Both pointer chains converge on human-decision-required (2026-08-08).

    The Track A waiting period was voluntarily terminated early and
    M3-LAG-WDI's final disposition was frozen as supplementary/exploratory
    only, superseding the earlier `...-response-ingestion` pointer (which
    remains valid roadmap history) and confirming the already-exhausted
    Track B sequence.
    """
    fm = gen.read_roadmap(REAL_ROOT)
    assert fm["next_research_action_id"] == "human-decision-required"
    assert fm["next_research_action_authorized"] in (False, "false")
    state = _handoff_state()
    assert state["next_research_action_id"] == "human-decision-required"
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True


# --------------------------------------------------------------------------- #
# Stage129 — M4 governance Data-Gate contract lock (design only, additive)
# --------------------------------------------------------------------------- #

_STAGE129_M4_REQUIRED_RELS = (
    gen._STAGE129_M4_CONTRACT_REL,
    gen._STAGE129_M4_BOUNDARY_REL,
    gen._STAGE129_M4_AUDIT_REL,
)


def _stage129_m4_root(tmp_path, mutate_rel=None, mutate=None):
    """A fresh temp root carrying real copies of all three Stage129 files.

    ``mutate_rel`` names which of the three companion files to mutate;
    ``mutate`` is applied to that file's loaded JSON dict before writing it
    back. When both are None, the root is an untouched, faithful copy of the
    real committed package (used as the positive-control baseline).
    """
    root = tmp_path
    for rel in _STAGE129_M4_REQUIRED_RELS:
        src = os.path.join(REAL_ROOT, rel)
        payload = json.load(open(src, encoding="utf-8"))
        if rel == mutate_rel and mutate is not None:
            payload = mutate(payload)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, ensure_ascii=False),
                        encoding="utf-8")
    return str(root)


def test_stage129_m4_contract_lock_markers_are_recognized_on_a_faithful_copy(
        tmp_path):
    root = _stage129_m4_root(tmp_path)
    markers = gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
        root)
    assert markers["stage129_m4_contract_lock_executed"] is True
    assert markers["stage129_m4_candidate_set"] == [
        "audit_opinion_type", "going_concern_flag", "audit_lag_days",
        "board_size",
    ]
    assert markers["stage129_m4_audit_opinion_type_taxonomy_status"] == (
        "CONTRACT_ISSUE_UNRESOLVED")
    assert markers["stage129_m4_audit_lag_days_calendar_conversion_status"] \
        == "CONTRACT_ISSUE_UNRESOLVED"
    assert markers["m4_data_retrieval_started"] is False
    assert markers["m4_candidate_observations_read"] == 0
    assert markers["m4_data_gate_executed"] is False
    assert markers["m4_block_admitted"] is False
    assert markers["m4_modeling_started"] is False
    assert markers["m4_incremental_evaluation_authorized"] is False
    assert markers["stage129_m4_next_action_id"] == (
        "stage129-m4-governance-data-gate")
    assert markers["stage129_m4_next_action_authorized"] is False
    assert markers[
        "stage129_m4_next_action_pointer_is_not_authorization"] is True


def test_stage129_m4_markers_are_empty_before_the_package_exists(tmp_path):
    """Missing contract == pre-lock state, not an error (fail-closed only on
    a present-but-corrupt package, never on plain absence)."""
    assert gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
        str(tmp_path)) == {}


def test_stage129_m4_markers_fail_closed_on_a_corrupt_contract(tmp_path):
    rel = gen._STAGE129_M4_CONTRACT_REL
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            str(tmp_path))


def test_stage129_m4_markers_fail_closed_when_companion_files_are_missing(
        tmp_path):
    """The contract alone is not sufficient: the governance boundary and the
    execution audit are required companions, and their absence must fail
    closed rather than silently produce a valid-looking Stage129 state."""
    src = os.path.join(REAL_ROOT, gen._STAGE129_M4_CONTRACT_REL)
    payload = json.load(open(src, encoding="utf-8"))
    dst = tmp_path / gen._STAGE129_M4_CONTRACT_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            str(tmp_path))


@pytest.mark.parametrize("mutation", [
    {"authorizes_retrieval": True},
    {"authorizes_gate_execution": True},
    {"authorizes_modeling": True},
    {"is_the_gate_itself": True},
    {"locked_before_any_value_level_work": False},
])
def test_stage129_m4_contract_authorization_flags_fail_closed(
        tmp_path, mutation):
    def _mutate(payload):
        payload = dict(payload)
        payload.update(mutation)
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_candidate_set_mutation_fails_closed(tmp_path):
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["candidate_set"]["candidates"] = [
            "audit_opinion_type", "going_concern_flag", "audit_lag_days",
            "board_size", "auditor_tenure",
        ]
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_taxonomy_cannot_be_smuggled_in_as_frozen(tmp_path):
    """If a future edit tried to quietly re-freeze the audit-opinion-type
    taxonomy (dropping the CONTRACT_ISSUE_UNRESOLVED status) instead of
    resolving it with an authoritative source, recognition must fail
    closed rather than publish it as gate-ready."""
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_opinion_type"][
            "taxonomy_status"] = "FROZEN"
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_lag_days_cannot_apply_the_plus_621_year_mapping_rule(
        tmp_path):
    """The M3-LAG-WDI +621 rule is a YEAR-MAPPING convention, not a
    date-conversion rule. If a future edit tried to reuse it as a date
    offset for audit_lag_days (dropping the UNRESOLVED status), recognition
    must fail closed."""
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_lag_days"][
            "calendar_conversion_status"] = "RESOLVED"
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)
    # And on the real, committed contract, the +621 rule is explicitly
    # documented as NOT applicable -- no code path may apply that offset to
    # audit_lag_days.
    real_contract = json.load(open(
        os.path.join(REAL_ROOT, gen._STAGE129_M4_CONTRACT_REL),
        encoding="utf-8"))
    convention = real_contract["semantic_definitions"]["audit_lag_days"][
        "calendar_conversion_convention"]
    assert "jalali_fiscal_year_t_plus_621" in convention
    assert "NOT applicable" in convention or "NOT be reused" in convention


def test_stage129_m4_join_keys_frozen_or_unresolved(tmp_path):
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["join_identity_rule"]["required_identifier"] = (
            "some_vague_open_ended_description")
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_threshold_provenance_mutation_fails_closed(tmp_path):
    """A blanket 'all four thresholds from Stage125 Part4' claim for the
    fourth threshold (which actually originates in the Stage128 M3 macro
    Data Gate decision) must not be recognized as valid."""
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["thresholds"]["canonical_sources"][
            "minimum_positive_evaluable_per_locked_validation_fold"][
            "found_in"] = (
                "project/stage125/part4_statistical_analysis_plan_"
                "stage125.json")
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


@pytest.mark.parametrize("field,bad", [
    ("m4_data_retrieval_started", True),
    ("m4_candidate_observations_read", 3),
    ("m4_data_gate_executed", True),
    ("m4_block_admitted", True),
    ("m4_modeling_started", True),
    ("m4_incremental_evaluation_authorized", True),
    ("next_action_authorized", True),
])
def test_stage129_m4_no_retrieval_gate_or_modeling_may_be_claimed(
        tmp_path, field, bad):
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["contract_lock_state"][field] = bad
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_m3_boundary_and_holm_family_mutations_fail_closed(
        tmp_path):
    for field, bad in (
        ("m3_cbi_status_preserved", "PASS_M3_DATA_GATE"),
        ("m3_lag_wdi_disposition_preserved", "CONFIRMATORY"),
        ("confirmatory_holm_family_executed", True),
    ):
        def _mutate(payload, field=field, bad=bad):
            payload = json.loads(json.dumps(payload))
            payload["m3_comparator_boundary"][field] = bad
            return payload
        root = _stage129_m4_root(
            tmp_path / field, mutate_rel=gen._STAGE129_M4_CONTRACT_REL,
            mutate=_mutate)
        with pytest.raises(gen.HandoffError):
            gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
                root)


def test_stage129_m4_final_test_firewall_mutation_fails_closed(tmp_path):
    def _mutate(payload):
        payload = json.loads(json.dumps(payload))
        payload["final_test_firewall"]["final_test_rows_read"] = 1
        return payload
    root = _stage129_m4_root(
        tmp_path, mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)


def test_stage129_m4_boundary_and_audit_mutations_fail_closed(tmp_path):
    def _mutate_boundary(payload):
        payload = dict(payload)
        payload["m4_authorized"] = True
        return payload
    root = _stage129_m4_root(
        tmp_path / "boundary", mutate_rel=gen._STAGE129_M4_BOUNDARY_REL,
        mutate=_mutate_boundary)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root)

    def _mutate_audit(payload):
        payload = dict(payload)
        payload["counters"] = dict(payload["counters"])
        payload["counters"]["m4_candidate_observations_read"] = 12
        return payload
    root2 = _stage129_m4_root(
        tmp_path / "audit", mutate_rel=gen._STAGE129_M4_AUDIT_REL,
        mutate=_mutate_audit)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root2)


def test_stage129_m4_is_recognized_by_the_full_handoff_build():
    """End-to-end: the real, committed repository state carries the locked
    Stage129 contract all the way into the generated handoff record."""
    record = gen.compute_record(REAL_ROOT)
    assert record["stage129_m4_contract_lock_executed"] is True
    assert record["m4_data_retrieval_started"] is False
    assert record["m4_data_gate_executed"] is False
    assert record["m4_block_admitted"] is False
    assert record["m4_modeling_started"] is False
    assert record["m4_incremental_evaluation_authorized"] is False
    assert record["stage129_m4_next_action_id"] == (
        "stage129-m4-governance-data-gate")
    assert record["stage129_m4_next_action_authorized"] is False
    assert record["next_research_action_id"] == "human-decision-required"
    assert record["stage128_m3_lag_wdi_next_action_id"] == (
        "human_decision_required")


def test_current_state_renders_the_stage129_m4_contract_lock_section():
    text = _current_state_text()
    assert "Stage129" in text
    assert "M4 governance Data-Gate contract lock" in text
    assert "PROSPECTIVELY_LOCKED_PRE_RETRIEVAL" in text
    assert "CONTRACT_ISSUE_UNRESOLVED" in text
    assert "stage129-m4-governance-data-gate" in text
    # It must not claim to have advanced either pre-existing live pointer.
    assert "A THIRD, separate pointer" in text


def test_stage129_m4_completion_cannot_be_overstated(tmp_path):
    """Section D must never publish the contract as complete/executable while
    section C holds unresolved prerequisite definitions. Each of these single
    flips is the whole overstatement, so each must fail closed on its own."""
    for field, value in (
        ("m4_contract_complete", True),
        ("m4_contract_fully_executable", True),
        ("m4_data_gate_executable", True),
        ("m4_data_gate_authorized", True),
        ("m4_coverage_calculated", True),
        ("m4_contract_completion_status", "COMPLETE"),
        ("m4_candidate_identity_set_locked", False),
        ("m4_gate_policy_contract_recorded", False),
    ):
        def _mutate(payload, _field=field, _value=value):
            payload = json.loads(json.dumps(payload))
            payload["contract_lock_state"][_field] = _value
            return payload
        root = _stage129_m4_root(
            tmp_path / field.replace("/", "_"),
            mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=_mutate)
        with pytest.raises(gen.HandoffError):
            gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
                root)


def test_stage129_m4_blocked_candidate_cannot_be_quietly_unblocked(tmp_path):
    """Dropping a candidate from the blocked list, or declaring its Gate
    executable, must fail closed while its definition stays unresolved."""
    def _drop_blocked(payload):
        payload = json.loads(json.dumps(payload))
        state = payload["contract_lock_state"]
        state["m4_candidates_blocked_by_unresolved_definitions"] = [
            "audit_lag_days"]
        state["m4_candidates_with_gate_ready_semantic_definitions"] = [
            "audit_opinion_type", "going_concern_flag", "board_size"]
        return payload

    def _gate_executable_for_blocked(payload):
        payload = json.loads(json.dumps(payload))
        payload["contract_lock_state"][
            "unresolved_prerequisite_definitions"][0][
                "gate_may_execute_for_this_candidate"] = True
        return payload

    def _semantic_gate_executable(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_opinion_type"][
            "gate_may_execute_for_this_candidate"] = True
        return payload

    def _admit_categorical_values(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_opinion_type"][
            "modeled_categorical_values_admitted"] = True
        return payload

    def _permit_621_as_date_rule(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_lag_days"][
            "jalali_fiscal_year_t_plus_621_permitted_as_daily_date_conversion"
        ] = True
        return payload

    def _permit_lag_calculation(payload):
        payload = json.loads(json.dumps(payload))
        payload["semantic_definitions"]["audit_lag_days"][
            "value_may_be_calculated"] = True
        return payload

    for index, mutate in enumerate((
            _drop_blocked, _gate_executable_for_blocked,
            _semantic_gate_executable, _admit_categorical_values,
            _permit_621_as_date_rule, _permit_lag_calculation)):
        root = _stage129_m4_root(
            tmp_path / f"case{index}",
            mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=mutate)
        with pytest.raises(gen.HandoffError):
            gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
                root)


def test_stage129_m4_codal_identity_cannot_be_declared_resolved(tmp_path):
    """Prior use of the same parent-side keys against a TSETMC child is not
    evidence of CODAL identity compatibility. Declaring it resolved, or
    re-opening a fallback mapping, must fail closed."""
    def _resolve_identity(payload):
        payload = json.loads(json.dumps(payload))
        payload["join_identity_rule"][
            "codal_to_parent_company_identity_resolution"][
                "status"] = "RESOLVED"
        return payload

    def _allow_join_dimension(payload):
        payload = json.loads(json.dumps(payload))
        payload["join_identity_rule"][
            "codal_to_parent_company_identity_resolution"][
                "gate_may_execute_join_dimension_for_codal_sourced_values"
            ] = True
        return payload

    def _permit_fallback(payload):
        payload = json.loads(json.dumps(payload))
        payload["join_identity_rule"]["required_identifier"][
            "fallback_mapping_permitted"] = True
        return payload

    def _drop_cross_cutting(payload):
        payload = json.loads(json.dumps(payload))
        payload["contract_lock_state"][
            "unresolved_cross_cutting_prerequisites"] = []
        return payload

    def _claim_gate_executable_candidates(payload):
        payload = json.loads(json.dumps(payload))
        payload["contract_lock_state"][
            "m4_candidates_the_gate_may_execute_for"] = [
                "going_concern_flag", "board_size"]
        return payload

    for index, mutate in enumerate((
            _resolve_identity, _allow_join_dimension, _permit_fallback,
            _drop_cross_cutting, _claim_gate_executable_candidates)):
        root = _stage129_m4_root(
            tmp_path / f"identity{index}",
            mutate_rel=gen._STAGE129_M4_CONTRACT_REL, mutate=mutate)
        with pytest.raises(gen.HandoffError):
            gen.derive_stage129_m4_governance_data_gate_contract_lock_markers(
                root)
