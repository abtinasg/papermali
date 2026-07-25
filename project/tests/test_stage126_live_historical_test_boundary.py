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

# Stage126+ Q1/Q2 Lean Governance adds a second, disjoint historical-marker
# class: five pre-terminal successor assertions inside the CLOSED Part 1/Part 2
# robustness test files (see project/docs/ai/STAGE126_Q1Q2_LEAN_GOVERNANCE.md
# section 10 and pytest.ini). Unlike the frozen Part 5 file, Part 1/Part 2
# remain live, mutable test files: only the five named nodes are excluded, by
# marker only, and every other test in those two files stays in the live gate.
TERMINAL_MARKER = "stage126_terminal_successor_state"
TERMINAL_MARKED_NODE_IDS = (
    "project/tests/test_stage126_m1_robustness_part1_target_proximity.py"
    "::test_expected_mismatch_matches_the_real_frozen_validator",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py"
    "::test_expected_mismatch_matches_the_real_frozen_validator",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py"
    "::test_direct_handoff_validation_helper_is_exact",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py"
    "::test_deterministic_repeated_build_output",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py"
    "::test_check_mode_is_clean",
)
TERMINAL_MARKED_FILES = (
    "project/tests/test_stage126_m1_robustness_part1_target_proximity.py",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py",
)

LIVE_MARKER_EXPRESSION = (
    "not live_successor_state and not stage126_terminal_successor_state"
)
PYTEST_INI_REL = "pytest.ini"

# Test files whose contents must remain fully inside the live gate.
LIVE_GATE_FILES = (
    "test_stage126_m1_robustness_part3_expanded_rule_a.py",
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
    assert "--deselect" not in addopts
    assert not any(f.split("::")[0] in addopts for f in TERMINAL_MARKED_FILES)
    markers = parser.get("pytest", "markers")
    assert HISTORICAL_MARKER in markers
    assert TERMINAL_MARKER in markers


def test_frozen_part5_file_still_contributes_tests_to_the_live_suite():
    """Only the marked nodes are deselected — the rest of the file still runs."""
    live = _collected_node_ids()
    part5_live = [n for n in live if n.startswith(FROZEN_PART5_TEST_REL)]
    assert len(part5_live) > 100, len(part5_live)
    marked = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    assert not (set(part5_live) & marked)


def test_deselected_set_is_exactly_the_marked_set():
    """Restricted to the `live_successor_state` class: the frozen Part 5 file
    is the ONLY file it ever excludes from (the disjoint
    `stage126_terminal_successor_state` class is proven separately)."""
    live_successor_marked = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    every_in_frozen_file = {
        n for n in _collected_node_ids("-m", "")
        if n.startswith(FROZEN_PART5_TEST_REL)
    }
    live_in_frozen_file = {
        n for n in _collected_node_ids() if n.startswith(FROZEN_PART5_TEST_REL)
    }
    assert every_in_frozen_file - live_in_frozen_file == live_successor_marked
    assert all(
        n.split("::")[0] == FROZEN_PART5_TEST_REL for n in live_successor_marked
    )


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
    assert record["terminal_historical_marker"] == TERMINAL_MARKER
    assert record["terminal_historical_successor_tests_are_live_gate"] is False
    assert record["whole_part1_or_part2_test_file_excluded"] is False
    assert sorted(record["terminal_historical_marked_node_ids"]) == sorted(
        TERMINAL_MARKED_NODE_IDS
    )
    assert sorted(record["historical_marked_node_ids"]) == _collected_node_ids(
        "-m", HISTORICAL_MARKER
    )


# --------------------------------------------------------------------------- #
# 10. Stage126+ Q1/Q2 Lean Governance — the SECOND historical marker class
#
# Exactly the five named Part 1/Part 2 pre-terminal successor assertions are
# excluded, by marker only, from the default live gate. Unlike the frozen
# Part 5 file, Part 1/Part 2 remain live, mutable files: every other test in
# them stays collected and runnable.
# --------------------------------------------------------------------------- #

def test_terminal_marker_selects_exactly_the_five_named_nodes():
    marked = set(_collected_node_ids("-m", TERMINAL_MARKER))
    assert marked == set(TERMINAL_MARKED_NODE_IDS), marked


def test_terminal_marker_appears_only_in_the_two_named_part_files():
    offenders: list[str] = []
    for rel in _tracked_files():
        if not rel.endswith(".py") or rel in TERMINAL_MARKED_FILES:
            continue
        text = (REAL_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        if f"pytest.mark.{TERMINAL_MARKER}" in text:
            offenders.append(rel)
    assert offenders == [], offenders


def test_no_whole_part1_or_part2_test_file_is_excluded():
    """Only the five named nodes are deselected — every other Part1/Part2
    test remains live."""
    live = set(_collected_node_ids())
    every = set(_collected_node_ids("-m", ""))
    marked_terminal = set(_collected_node_ids("-m", TERMINAL_MARKER))
    for rel in TERMINAL_MARKED_FILES:
        file_every = {n for n in every if n.startswith(rel)}
        file_live = {n for n in live if n.startswith(rel)}
        file_marked = {n for n in marked_terminal if n.startswith(rel)}
        assert file_every, rel
        assert file_every - file_live == file_marked, rel
        # The file still contributes non-marked tests to the live gate.
        assert file_live, rel


def test_terminal_and_live_successor_marker_classes_are_disjoint():
    live_successor = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    terminal_successor = set(_collected_node_ids("-m", TERMINAL_MARKER))
    assert not (live_successor & terminal_successor)


def test_deselected_set_equals_union_of_both_historical_marker_classes():
    live = set(_collected_node_ids())
    every = set(_collected_node_ids("-m", ""))
    live_successor = set(_collected_node_ids("-m", HISTORICAL_MARKER))
    terminal_successor = set(_collected_node_ids("-m", TERMINAL_MARKER))
    assert every - live == live_successor | terminal_successor


def test_no_current_scientific_or_gate_test_carries_the_terminal_marker():
    """No current-state-validator, final-test-lock or leakage test is ever
    excluded via the terminal-successor marker."""
    marked = set(_collected_node_ids("-m", TERMINAL_MARKER))
    for node in marked:
        assert "current_state_validator" not in node, node
        assert "final_test" not in node.lower() or node in TERMINAL_MARKED_NODE_IDS
        assert "leakage" not in node, node


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
