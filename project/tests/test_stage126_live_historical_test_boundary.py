"""Fail-closed proof that the live/historical test boundary is narrow.

Stage125 Part 5 is historical and immutable and is not a live Stage126
successor-state gate. The tests inside its frozen test file that carry the
``live_successor_state`` marker assert the Handoff successor state as it stood
at the Part 2 reference commit, so they are historical regression tests.

The default suite excludes ONLY that marker. These tests prove the exclusion is
narrow: it never removes a whole file, never targets a node ID, never
introduces a skip/xfail/collection hook, and never touches a current
scientific, current-state-validator, Handoff, final-test-lock or leakage test.
"""
from __future__ import annotations

import ast
import configparser
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REAL_ROOT = Path(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
TESTS_DIR = REAL_ROOT / "project" / "tests"

HISTORICAL_MARKER = "live_successor_state"
FROZEN_PART5_TEST_REL = "project/tests/test_stage125_part5_readiness_closure.py"
FROZEN_PART5_TEST_SHA256 = (
    "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71"
)
HISTORICAL_REFERENCE_COMMIT = "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
LIVE_MARKER_EXPRESSION = "not live_successor_state"
PYTEST_INI_REL = "pytest.ini"

# Test files whose contents must remain fully inside the live gate.
LIVE_GATE_FILES = (
    "test_stage126_m1_robustness_part3_expanded_rule_a.py",
    "test_stage126_m1_robustness_part2_listing_rule_b.py",
    "test_stage126_m1_robustness_part1_target_proximity.py",
    "test_stage126_m1_robustness_part0_decision_lock.py",
    "test_stage126_current_state_validator.py",
    "test_stage126_m1_primary_development_tuning.py",
    "test_ai_handoff.py",
    "test_stage126_live_historical_test_boundary.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pytest(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(cwd or REAL_ROOT), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "project"},
    )


def _collected_node_ids(*args: str) -> list[str]:
    proc = _pytest("project/tests", "-q", "--no-header", "--collect-only", *args)
    return sorted(
        line.strip() for line in proc.stdout.splitlines() if "::" in line
    )


# --------------------------------------------------------------------------- #
# 1. The marker exists ONLY in the frozen Part 5 test file
# --------------------------------------------------------------------------- #

def test_marker_appears_only_in_the_frozen_part5_test_file():
    offenders: list[str] = []
    for rel in _tracked_files():
        if not rel.endswith(".py"):
            continue
        if rel in (FROZEN_PART5_TEST_REL,
                   "project/tests/test_stage126_live_historical_test_boundary.py"):
            continue
        text = (REAL_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        if f"pytest.mark.{HISTORICAL_MARKER}" in text:
            offenders.append(rel)
    assert offenders == [], offenders


def test_every_marked_node_comes_from_the_frozen_part5_file():
    marked = _collected_node_ids("-m", HISTORICAL_MARKER)
    assert marked, "the historical marker selects nothing"
    for node in marked:
        assert node.split("::")[0] == FROZEN_PART5_TEST_REL, node


def test_marker_is_declared_on_functions_inside_the_frozen_file_only():
    """Structural check: the decorators live in the frozen file's own AST."""
    tree = ast.parse((REAL_ROOT / FROZEN_PART5_TEST_REL).read_text(encoding="utf-8"))
    marked = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            attr = dec.attr if isinstance(dec, ast.Attribute) else ""
            if attr == HISTORICAL_MARKER:
                marked.append(node.name)
    assert len(marked) >= 1
    assert sorted(marked) == sorted(
        n.split("::")[-1] for n in _collected_node_ids("-m", HISTORICAL_MARKER)
    )


# --------------------------------------------------------------------------- #
# 2. The frozen Part 5 test file is byte-identical
# --------------------------------------------------------------------------- #

def test_frozen_part5_test_file_hash_is_exact():
    assert _sha(REAL_ROOT / FROZEN_PART5_TEST_REL) == FROZEN_PART5_TEST_SHA256


def test_frozen_part5_paths_unchanged_versus_the_reference_commit():
    for rel in (FROZEN_PART5_TEST_REL,
                "project/src/stage125_part5_readiness_closure.py",
                "project/run_stage125_part5.py"):
        head = subprocess.run(
            ["git", "-C", str(REAL_ROOT), "rev-parse", f"HEAD:{rel}"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        ref = subprocess.run(
            ["git", "-C", str(REAL_ROOT), "rev-parse",
             f"{HISTORICAL_REFERENCE_COMMIT}:{rel}"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert head == ref, rel
    changed = subprocess.run(
        ["git", "-C", str(REAL_ROOT), "diff", "--name-only",
         HISTORICAL_REFERENCE_COMMIT, "HEAD", "--", "project/stage125/"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert changed == "", changed


# --------------------------------------------------------------------------- #
# 3. The configuration excludes the MARKER, not the file
# --------------------------------------------------------------------------- #

def test_pytest_config_excludes_only_the_marker():
    parser = configparser.ConfigParser()
    parser.read(REAL_ROOT / PYTEST_INI_REL, encoding="utf-8")
    assert parser.has_section("pytest")
    addopts = parser.get("pytest", "addopts")
    assert LIVE_MARKER_EXPRESSION in addopts
    # Never a file-level or node-level exclusion.
    assert "--ignore" not in addopts
    assert "--deselect" not in addopts
    assert "-k" not in addopts.split()
    assert FROZEN_PART5_TEST_REL not in addopts
    markers = parser.get("pytest", "markers")
    assert HISTORICAL_MARKER in markers


def test_frozen_part5_file_still_contributes_tests_to_the_live_suite():
    """Only the marked nodes are deselected — the rest of the file still runs."""
    live = _collected_node_ids()
    part5_live = [n for n in live if n.startswith(FROZEN_PART5_TEST_REL)]
    assert len(part5_live) > 100, len(part5_live)
    marked = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    assert not (set(part5_live) & marked)


def test_deselected_set_is_exactly_the_marked_set():
    live = set(_collected_node_ids())
    every = set(_collected_node_ids("-m", ""))
    marked = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    assert every - live == marked
    assert all(n.split("::")[0] == FROZEN_PART5_TEST_REL for n in (every - live))


# --------------------------------------------------------------------------- #
# 4-7. Current live tests are neither marked nor excluded
# --------------------------------------------------------------------------- #

def test_live_gate_files_are_fully_collected():
    live = _collected_node_ids()
    for name in LIVE_GATE_FILES:
        rel = f"project/tests/{name}"
        if not (REAL_ROOT / rel).is_file():
            continue
        selected = [n for n in live if n.startswith(rel)]
        assert selected, rel
        every = [
            n for n in _collected_node_ids("-m", "") if n.startswith(rel)
        ]
        assert sorted(selected) == sorted(every), rel


def test_final_test_lock_and_leakage_tests_remain_live():
    live = "\n".join(_collected_node_ids())
    for needle in ("final_test", "leakage", "poison"):
        assert needle in live, needle
    # Named Part 3 guards specifically.
    for node in (
        "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py"
        "::test_final_test_counters_zero_and_identities_only",
        "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py"
        "::test_poison_final_test_values_are_never_parsed",
        "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py"
        "::test_no_validation_leakage_and_no_final_test_year_in_oof",
    ):
        assert node in live, node


# --------------------------------------------------------------------------- #
# 8. No skip / xfail / collection hook / node-ID suppression was introduced
# --------------------------------------------------------------------------- #

def test_no_skip_or_xfail_was_added_for_the_historical_tests():
    text = (REAL_ROOT / FROZEN_PART5_TEST_REL).read_text(encoding="utf-8")
    for banned in ("pytest.mark.skip", "pytest.mark.xfail", "pytest.skip(",
                   "pytest.xfail("):
        assert banned not in text, banned


def _tracked_files() -> list[str]:
    """Repository-tracked files only — third-party virtualenv code is not ours."""
    return sorted(
        line for line in subprocess.run(
            ["git", "-C", str(REAL_ROOT), "ls-files"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines() if line.strip()
    )


def test_no_conftest_collection_hook_suppresses_tests():
    conftests = [r for r in _tracked_files()
                 if r.endswith("conftest.py")]
    for rel in conftests:
        text = (REAL_ROOT / rel).read_text(encoding="utf-8")
        for banned in ("pytest_collection_modifyitems", "pytest_ignore_collect",
                       "pytest_collectstart", "collect_ignore"):
            assert banned not in text, (rel, banned)


def test_config_contains_no_node_id_specific_suppression():
    text = (REAL_ROOT / PYTEST_INI_REL).read_text(encoding="utf-8")
    assert "test_live_handoff_reports_completed_part2_successor_state" not in text
    assert "::" not in text
    assert not re.search(r"^\s*(collect_ignore|norecursedirs)\s*=", text,
                         flags=re.MULTILINE)


# --------------------------------------------------------------------------- #
# 9. The boundary is generic across all already-marked historical tests
# --------------------------------------------------------------------------- #

def test_boundary_applies_to_every_marked_test_without_editing_sources():
    """All marked tests are excluded by the SAME expression, not one by one."""
    marked = _collected_node_ids("-m", HISTORICAL_MARKER)
    live = set(_collected_node_ids())
    assert len(marked) >= 9, len(marked)
    for node in marked:
        assert node not in live, node
    # The frozen file was not edited to achieve this.
    assert _sha(REAL_ROOT / FROZEN_PART5_TEST_REL) == FROZEN_PART5_TEST_SHA256


def test_boundary_record_matches_the_configuration():
    import json
    record = json.loads(
        (REAL_ROOT / "project/stage126"
         / "stage126_live_vs_historical_test_boundary.json").read_text(
            encoding="utf-8")
    )
    assert record["contract_id"] == "stage126_live_vs_historical_test_boundary"
    assert record["stage125_part5_mode"] == "historical_immutable"
    assert record["historical_marker"] == HISTORICAL_MARKER
    assert record["historical_test_file"] == FROZEN_PART5_TEST_REL
    assert record["historical_test_file_sha256"] == FROZEN_PART5_TEST_SHA256
    assert record["historical_reference_commit"] == HISTORICAL_REFERENCE_COMMIT
    assert record["historical_successor_tests_are_live_gate"] is False
    assert record["stage126_live_suite_marker_expression"] == (
        LIVE_MARKER_EXPRESSION
    )
    assert record["current_state_validator_remains_live_gate"] is True
    assert record["part3_scientific_artifacts_changed"] is False
    assert record["part4_authorized"] is False
    assert record["final_test_unlocked"] is False
    assert sorted(record["historical_marked_node_ids"]) == _collected_node_ids(
        "-m", HISTORICAL_MARKER
    )


def test_historical_runner_exists_and_is_read_only():
    runner = REAL_ROOT / "project/run_stage125_part5_historical_successor_tests.py"
    assert runner.is_file()
    text = runner.read_text(encoding="utf-8")
    assert FROZEN_PART5_TEST_SHA256 in text
    assert HISTORICAL_REFERENCE_COMMIT in text
    assert "worktree" in text
    # It must never write into the real branch or Stage125.
    for banned in ("git add", "git commit", "git push", "--write"):
        assert banned not in text, banned
