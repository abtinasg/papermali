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
import shutil
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


# --------------------------------------------------------------------------- #
# Real-repo, read-only checks
# --------------------------------------------------------------------------- #

def test_real_repo_validates():
    assert val.run_check(REAL_ROOT) == 0


def test_state_matches_git():
    state = json.load(
        open(os.path.join(REAL_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8")
    )
    head = gen.head_commit(REAL_ROOT)
    gfc = state["generated_from_commit"]
    assert gfc == head or gen.is_ancestor(REAL_ROOT, gfc, head)
    assert state["last_stage_commit"] == gen.last_stage_commit(REAL_ROOT)


def test_qc_counts_match_report():
    state = json.load(
        open(os.path.join(REAL_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8")
    )
    qc = json.load(open(os.path.join(REAL_ROOT, state["selected_qc_path"]), encoding="utf-8"))
    assert state["qc_assertions"] == qc["assertion_count"]
    assert state["qc_failed"] == qc["failed_count"]
    assert state["qc_all_pass"] == qc["all_pass"]
    assert qc["failed_count"] == 0 and qc["all_pass"] is True


def test_markers_are_off():
    state = json.load(
        open(os.path.join(REAL_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8")
    )
    assert state["modeling_started"] is False
    assert state["gate_b_started"] is False
    assert state["verified_master_created"] is False


def test_frozen_stages_present():
    for mf in gen.FROZEN_MANIFESTS:
        assert os.path.isfile(os.path.join(REAL_ROOT, mf)), mf


def test_internal_links_resolve():
    errors: list[str] = []
    gen_root = REAL_ROOT
    val._check_links(gen_root, errors)
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
    # Re-generating must not change the semantic fingerprint.
    outputs = gen.generate(REAL_ROOT)
    fresh = json.loads(outputs["project/docs/ai/handoff_state.json"])
    on_disk = json.load(
        open(os.path.join(REAL_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8")
    )
    assert fresh["state_fingerprint"] == on_disk["state_fingerprint"]


def test_change_allowlist_real_repo():
    # origin/main must resolve for this check; skip cleanly if offline/no remote.
    try:
        gen._git(REAL_ROOT, "rev-parse", "origin/main")
    except gen.HandoffError:
        pytest.skip("origin/main not available")
    assert val.run_check_changes(REAL_ROOT, "origin/main", include_wt=True) == 0


# --------------------------------------------------------------------------- #
# Synthetic repo for semantic-drift tests
# --------------------------------------------------------------------------- #

STAGE = "stagex"


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

    # Frozen manifests + their tracked data files.
    for s in ("stage122", "stage123"):
        data = f"frozen {s}\n"
        _write(root, f"project/{s}/data_{s}.csv", data)
        _write(root, f"project/{s}/metadata_and_hashes_{s}.json", json.dumps(
            {"stage": s, "output_files_sha256": {f"data_{s}.csv": _sha(data)}}, indent=2
        ))

    # Roadmap (human input).
    _write(root, "project/docs/ai/ROADMAP.md",
           "---\n"
           "roadmap_version: 1\n"
           f"active_research_workstream_id: {STAGE}\n"
           f"last_completed_research_action_id: {STAGE}-a-1\n"
           f"next_research_action_id: {STAGE}-a-2\n"
           "active_maintenance_task_id: handoff\n"
           "---\n\n"
           "## Research actions\n\n"
           f"1. `{STAGE}-a-1` done\n"
           f"2. `{STAGE}-a-2` next\n")
    os.makedirs(os.path.join(root, "project/docs/ai"), exist_ok=True)

    # Point the generator's frozen-manifest list at the synthetic manifests.
    monkeypatch.setattr(gen, "FROZEN_MANIFESTS", (
        "project/stage122/metadata_and_hashes_stage122.json",
        "project/stage123/metadata_and_hashes_stage123.json",
    ))

    sha1 = _commit(root, f"Stage1 Part initial: {STAGE} code")

    # QC report referencing the code commit, with matching fingerprints.
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
    }, indent=2))
    _commit(root, f"Stage1 Part artifacts: {STAGE} QC")

    # Generate + commit the handoff (handoff-only commit).
    outputs = gen.generate(root)
    for rel, content in outputs.items():
        _write(root, rel, content)
    _commit(root, "handoff: generate package")

    assert val.run_check(root) == 0  # baseline must be valid
    return root


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
    text = text.replace(f"{STAGE}-a-2", f"{STAGE}-a-3")
    text = text.replace(f"2. `{STAGE}-a-3` next", f"2. `{STAGE}-a-2` mid\n3. `{STAGE}-a-3` next")
    _write(synth, "project/docs/ai/ROADMAP.md", text)
    _commit(synth, "handoff: bump roadmap next id (no regen)")
    assert val.run_check(synth) == 1


def test_scenario6_new_stage_commit_fails(synth):
    _write(synth, "project/qc/extra_note.txt", "more research\n")
    _commit(synth, "Stage2 Part new: extra research output")
    assert val.run_check(synth) == 1


def test_scenario7_timestamp_only_change_keeps_fingerprint(synth):
    state_path = os.path.join(synth, "project/docs/ai/handoff_state.json")
    state = json.load(open(state_path, encoding="utf-8"))
    fp_before = state["state_fingerprint"]
    # Regenerate (new timestamp) — semantic fingerprint must be unchanged.
    outputs = gen.generate(synth)
    fresh = json.loads(outputs["project/docs/ai/handoff_state.json"])
    assert fresh["state_fingerprint"] == fp_before
    assert fresh["generated_at_utc"] is not None
    assert val.run_check(synth) == 0


def test_changes_allowlist_blocks_non_handoff(synth):
    base = _git(synth, "rev-parse", "HEAD")
    _write(synth, f"project/src/{STAGE}.py", "STAGE_SRC = 2\n")
    _commit(synth, "Stage1 Part: source edit")
    # The new commit touches a non-allowlisted path -> allowlist check fails.
    assert val.run_check_changes(synth, base, include_wt=True) == 1
