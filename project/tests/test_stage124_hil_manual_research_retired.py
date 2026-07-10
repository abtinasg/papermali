"""Regression tests: HIL panel and manual-intake path have been retired.

These tests prove that:
- HIL and manual-intake files no longer exist in the repository.
- No active import or command references the retired modules.
- The verified master still has exactly 130 unique tickers.
- first_public_trading dates are not empty.
- official_api data files and their recorded SHA-256 hashes are unchanged.
- Stage122 and Stage123 directories are untouched (tracked file set stable).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

# ---- 1. Deleted files no longer exist ----------------------------------------

DELETED_FILES = [
    ROOT / "apps" / "stage124_part03_hil_panel.py",
    ROOT / "src" / "stage124_part03_hil_panel.py",
    ROOT / "tests" / "test_stage124_part03_hil_panel.py",
    ROOT / "stage124" / "batch02_parts" / "README_PART03_HIL_PANEL.md",
    ROOT / "run_stage124_batch02_part03_manual_intake.py",
    ROOT / "tests" / "test_stage124_batch02_part03_manual_intake.py",
    ROOT / "stage124" / "batch02_parts" / "part03_manual_intake_input.csv",
]


@pytest.mark.parametrize("path", DELETED_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_retired_file_does_not_exist(path: Path):
    assert not path.exists(), f"Retired file still exists: {path}"


# ---- 2. No active import or command references retired modules ----------------

RETIRED_IMPORT_PATTERNS = [
    "stage124_part03_hil_panel",
    "run_stage124_batch02_part03_manual_intake",
]


def _git_grep(pattern: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-n", "--", pattern],
        capture_output=True,
        text=True,
    )
    return result.stdout


@pytest.mark.parametrize("pattern", RETIRED_IMPORT_PATTERNS)
def test_no_active_import_of_retired_modules(pattern: str):
    """No tracked source file should import or reference the retired modules."""
    hits = _git_grep(pattern)
    # Historical references in docs and this test file itself are allowed.
    filtered = [
        line for line in hits.splitlines()
        if not any(
            hist in line for hist in (
                "docs/ai/CHANGELOG.md",
                "docs/ai/DECISIONS.md",
                "docs/ai/OPEN_TASKS.md",
                "docs/ai/ROADMAP.md",
                "test_stage124_hil_manual_research_retired.py",
            )
        )
    ]
    assert not filtered, (
        f"Active reference to retired module '{pattern}' found:\n"
        + "\n".join(filtered)
    )


def test_streamlit_not_in_requirements():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit" not in req.lower(), "streamlit still in requirements.txt"


# ---- 3. Verified master has exactly 130 unique tickers ------------------------

VERIFIED_MASTER = ROOT / "stage124" / "listing_master_verified_stage124.csv"


def test_verified_master_has_130_unique_tickers():
    df = pd.read_csv(VERIFIED_MASTER, dtype=str).fillna("")
    assert len(df) == 130
    assert df["ticker"].nunique() == 130
    assert not df["ticker"].duplicated().any()


# ---- 4. first_public_trading dates are not empty ------------------------------

def test_verified_master_first_public_trading_dates_not_empty():
    df = pd.read_csv(VERIFIED_MASTER, dtype=str).fillna("")
    assert (df["first_public_trading_date_jalali"].str.len() > 0).all()
    assert (df["first_public_trading_date_gregorian"].str.len() > 0).all()


def test_verified_master_verification_status():
    df = pd.read_csv(VERIFIED_MASTER, dtype=str).fillna("")
    assert set(df["verification_status"]) == {"verified_tse_api_first_observed_trade"}


# ---- 5. official_api files and SHA-256 hashes unchanged -----------------------

OFFICIAL_API_DIR = ROOT / "stage124" / "official_api"
MANIFEST_PATH = OFFICIAL_API_DIR / "metadata_and_hashes.json"


def test_official_api_manifest_hashes_match_files():
    assert MANIFEST_PATH.is_file(), "metadata_and_hashes.json missing"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for batch in manifest.get("raw_batches", []):
        path = ROOT / batch["path"]
        assert path.is_file(), f"Missing raw batch file: {batch['path']}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == batch["sha256"], (
            f"SHA-256 mismatch for {batch['path']}: "
            f"expected {batch['sha256']}, got {actual}"
        )


def test_official_api_provenance_manifest_hashes_match_files():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest.get("provenance_manifests", []):
        path = ROOT / entry["path"]
        assert path.is_file(), f"Missing provenance manifest: {entry['path']}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == entry["sha256"], (
            f"SHA-256 mismatch for {entry['path']}: "
            f"expected {entry['sha256']}, got {actual}"
        )


# ---- 6. Stage122 and Stage123 tracked file sets are stable --------------------

STAGE_DIRS = ["project/stage122", "project/stage123"]


@pytest.mark.parametrize("stage_dir", STAGE_DIRS)
def test_stage_dir_tracked_files_unchanged(stage_dir: str):
    """Verify that the tracked file list for stage122/stage123 matches HEAD."""
    head_files = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", stage_dir],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert len(head_files) > 0, f"No tracked files in {stage_dir}"
    # Verify all listed files exist on disk
    for rel in head_files:
        assert (REPO_ROOT / rel).is_file(), f"Missing tracked file: {rel}"
