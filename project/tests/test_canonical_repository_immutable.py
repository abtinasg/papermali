"""Ensure tmp_path stage tests never mutate tracked canonical repository files."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

CANONICAL_PREFIXES = (
    "project/stage124/",
    "project/stage123/",
    "project/stage122/",
)


def _tracked_canonical_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", *CANONICAL_PREFIXES],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return [REPO_ROOT / rel for rel in listed if rel.strip()]


def _snapshot_canonical_shas() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in _tracked_canonical_files():
        if path.is_file():
            out[str(path.relative_to(REPO_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


@pytest.fixture(scope="session", autouse=True)
def canonical_repository_unchanged_after_tests():
    before = _snapshot_canonical_shas()
    yield
    after = _snapshot_canonical_shas()
    assert before == after, "Tracked canonical repository files changed during pytest session"
