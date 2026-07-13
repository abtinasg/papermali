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


def test_qc_counts_match_report():
    state = _state(REAL_ROOT)
    qc = json.load(open(os.path.join(REAL_ROOT, state["selected_qc_path"]), encoding="utf-8"))
    assert state["qc_assertions"] == qc["assertion_count"]
    assert state["qc_failed"] == qc["failed_count"]
    assert state["qc_all_pass"] == qc["all_pass"]
    assert qc["failed_count"] == 0 and qc["all_pass"] is True


def test_markers_are_off():
    # Gate B has been executed (Stage124 finalization): gate_b_started is now
    # True. Modeling has NOT started and must remain False.
    state = _state(REAL_ROOT)
    assert state["modeling_started"] is False
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


def test_artifact_commit_without_stage_does_not_advance(synth):
    # A non-handoff-only commit whose body lacks any Stage/Part marker must not
    # become last_stage_commit.
    before = gen.last_stage_commit(synth)
    _write(synth, "project/stage125/data_dictionary_stage125.csv", "col\n")
    _commit(synth, "artifact: refresh generated data dictionary")
    assert gen.last_stage_commit(synth) == before


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
