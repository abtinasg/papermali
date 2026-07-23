#!/usr/bin/env python3
"""Historical regression runner for the frozen Stage125 Part 5 successor tests.

Usage:
    python project/run_stage125_part5_historical_successor_tests.py

Stage125 Part 5 is **historical and immutable** and is **not** a live Stage126
successor-state gate. The tests in its frozen test file marked
``live_successor_state`` assert the Handoff successor state as it stood at the
Part 2 reference commit, so they are historical regression tests and are
excluded from the default Stage126 live suite.

This runner verifies them the only way that is meaningful: inside a temporary,
detached, read-only worktree checked out at that reference commit. It is
**historical regression verification only** — it never runs Stage125 Part 5 as
a live current-state gate.

Guarantees:
  * the frozen Part 5 test file hash is verified before anything runs;
  * the real branch, ``main``, the Stage125 tree and the Handoff are never
    modified;
  * gitignored frozen inputs are copied into the temporary worktree read-only,
    and only after their historical expected hashes are verified;
  * the temporary worktree is removed afterwards, including on failure;
  * a nonzero exit code is returned if any historical successor test fails.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

HISTORICAL_MARKER = "live_successor_state"
HISTORICAL_REFERENCE_COMMIT = "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
FROZEN_PART5_TEST_REL = "project/tests/test_stage125_part5_readiness_closure.py"
FROZEN_PART5_TEST_SHA256 = (
    "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71"
)
FROZEN_PART5_SOURCE_REL = "project/src/stage125_part5_readiness_closure.py"
FROZEN_PART5_SOURCE_SHA256 = (
    "cb61ea7c99b53f1988c22f5eac0af66af9cd9e46657a48bf66ccb198d654d41c"
)
FROZEN_PART5_RUNNER_REL = "project/run_stage125_part5.py"
FROZEN_PART5_RUNNER_SHA256 = (
    "ba6bd9e8e155e9cad71299e53806515caa1f95664bfcba0aebd20929f769e037"
)

# The Part 3C outputs are gitignored, so a fresh worktree lacks them. Their
# exact expected hashes are NOT hard-coded here: they are read from the frozen,
# TRACKED Stage125 contract below, which the worktree already contains.
PART3C_SUMMARY_REL = "project/stage125/part3c_sample_summary_stage125.csv"
PART3C_SUMMARY_SHA256 = (
    "c203ed3f31a796b769d96e586d45b9b14ab1f73a74bffdfbfcf2d975f2e512bc"
)


def required_ignored_inputs(repo_root: Path) -> dict[str, str]:
    """Frozen Part 3C inputs and their expected hashes, from the frozen contract.

    Reading the expectations from the tracked Stage125 summary (itself
    hash-pinned) keeps this runner honest: a drifted input cannot be smuggled
    in by editing a constant here.
    """
    import csv
    summary = repo_root / PART3C_SUMMARY_REL
    if not summary.is_file():
        raise HistoricalRunError(f"missing frozen contract: {PART3C_SUMMARY_REL}")
    got = _sha(summary)
    if got != PART3C_SUMMARY_SHA256:
        raise HistoricalRunError(
            f"frozen Part 3C summary changed: {got} != {PART3C_SUMMARY_SHA256}"
        )
    required: dict[str, str] = {}
    with summary.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            for path_key, hash_key in (
                ("audited_output_file", "audited_output_sha256"),
                ("analysis_ready_output_file", "analysis_ready_output_sha256"),
            ):
                rel, digest = row.get(path_key, ""), row.get(hash_key, "")
                if rel and digest:
                    required[rel] = digest
    if not required:
        raise HistoricalRunError("frozen Part 3C summary lists no inputs")
    return required


class HistoricalRunError(RuntimeError):
    """Fail-closed historical verification error."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd or REPO_ROOT), *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise HistoricalRunError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def verify_frozen_part5(repo_root: Path) -> dict[str, str]:
    """The frozen Part 5 surfaces must be byte-identical before anything runs."""
    observed: dict[str, str] = {}
    for rel, expected in (
        (FROZEN_PART5_TEST_REL, FROZEN_PART5_TEST_SHA256),
        (FROZEN_PART5_SOURCE_REL, FROZEN_PART5_SOURCE_SHA256),
        (FROZEN_PART5_RUNNER_REL, FROZEN_PART5_RUNNER_SHA256),
    ):
        path = repo_root / rel
        if not path.is_file():
            raise HistoricalRunError(f"missing frozen Part 5 path: {rel}")
        got = _sha(path)
        if got != expected:
            raise HistoricalRunError(
                f"frozen Part 5 path changed: {rel} {got} != {expected}"
            )
        observed[rel] = got
    return observed


def _make_read_only(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def copy_required_ignored_inputs(worktree: Path) -> list[str]:
    """Copy gitignored frozen inputs read-only, after verifying their hashes."""
    copied: list[str] = []
    for rel, expected in sorted(required_ignored_inputs(REPO_ROOT).items()):
        src = REPO_ROOT / rel
        if not src.is_file():
            raise HistoricalRunError(f"required frozen input missing: {rel}")
        got = _sha(src)
        if got != expected:
            raise HistoricalRunError(
                f"frozen input hash mismatch before copy: {rel} {got} != {expected}"
            )
        dst = worktree / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if _sha(dst) != expected:
            raise HistoricalRunError(f"copied frozen input differs: {rel}")
        _make_read_only(dst)
        copied.append(rel)
    return copied


def _remove_worktree(worktree: Path) -> None:
    """Always remove the temporary worktree, including after a failure."""
    if worktree.exists():
        for path in worktree.rglob("*"):
            if path.is_file():
                try:
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
                except OSError:
                    pass
    try:
        _git("worktree", "remove", "--force", str(worktree))
    except HistoricalRunError:
        shutil.rmtree(worktree, ignore_errors=True)
    try:
        _git("worktree", "prune")
    except HistoricalRunError:
        pass


def run_historical_successor_tests() -> int:
    print("=" * 70)
    print("Stage125 Part 5 — historical successor-test regression run")
    print("=" * 70)
    print("Stage125 Part 5 is historical and immutable. This is NOT a live "
          "Stage126 current-state gate.")

    observed = verify_frozen_part5(REPO_ROOT)
    print(f"Frozen Part 5 test  : {observed[FROZEN_PART5_TEST_REL]}")
    print(f"Frozen Part 5 source: {observed[FROZEN_PART5_SOURCE_REL]}")
    print(f"Frozen Part 5 runner: {observed[FROZEN_PART5_RUNNER_REL]}")
    print(f"Historical reference commit: {HISTORICAL_REFERENCE_COMMIT}")

    before_head = _git("rev-parse", "HEAD")
    before_status = _git("status", "--porcelain")

    tmp_parent = Path(tempfile.mkdtemp(prefix="stage125-part5-historical-"))
    worktree = tmp_parent / "worktree"
    returncode = 1
    try:
        _git("worktree", "add", "-q", "--detach", str(worktree),
             HISTORICAL_REFERENCE_COMMIT)
        copied = copy_required_ignored_inputs(worktree)
        print(f"Copied {len(copied)} gitignored frozen input(s) read-only into "
              f"the temporary worktree.")

        # Verify the worktree really is at the reference commit and that the
        # frozen Part 5 surfaces there are the same bytes.
        wt_head = _git("rev-parse", "HEAD", cwd=worktree)
        if wt_head != HISTORICAL_REFERENCE_COMMIT:
            raise HistoricalRunError(
                f"temporary worktree HEAD {wt_head} != "
                f"{HISTORICAL_REFERENCE_COMMIT}"
            )
        verify_frozen_part5(worktree)

        print("Running the historical successor tests "
              f"(-m {HISTORICAL_MARKER}) inside the temporary worktree...")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest",
             "-o", "addopts=",
             FROZEN_PART5_TEST_REL,
             "-m", HISTORICAL_MARKER,
             "-q"],
            cwd=str(worktree), text=True,
            env={**os.environ, "PYTHONPATH": "project"},
        )
        returncode = proc.returncode
    finally:
        _remove_worktree(worktree)
        shutil.rmtree(tmp_parent, ignore_errors=True)

    # The real branch must be untouched.
    after_head = _git("rev-parse", "HEAD")
    after_status = _git("status", "--porcelain")
    if after_head != before_head or after_status != before_status:
        raise HistoricalRunError(
            "the working branch changed during the historical run (fail-closed)"
        )
    verify_frozen_part5(REPO_ROOT)

    if returncode == 0:
        print("Historical successor tests PASSED at the reference commit.")
    else:
        print("Historical successor tests FAILED at the reference commit.",
              file=sys.stderr)
    return returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        return run_historical_successor_tests()
    except HistoricalRunError as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
