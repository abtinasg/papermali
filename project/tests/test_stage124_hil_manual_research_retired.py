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

REQUIRED_FILE_ROLES = {
    "bulk_first_trade_export",
    "ambiguous_resolved_export",
    "final_pair_export",
    "provenance_manifest",
    "verified_listing_master",
    "first_trade_conflict_audit",
    "import_manifest",
}


def test_official_api_metadata_hashes_match_files():
    """Verify every file in metadata_and_hashes.json has a matching SHA-256."""
    assert MANIFEST_PATH.is_file(), "metadata_and_hashes.json missing"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    files = manifest.get("files", [])
    assert len(files) > 0, "metadata_and_hashes.json has empty 'files' list"

    seen_roles: set[str] = set()
    for entry in files:
        rel_path = entry["relative_path"]
        file_path = ROOT / rel_path
        assert file_path.is_file(), f"Missing file listed in manifest: {rel_path}"
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual == entry["sha256"], (
            f"SHA-256 mismatch for {rel_path}: "
            f"expected {entry['sha256']}, got {actual}"
        )
        seen_roles.add(entry["file_role"])

    missing_roles = REQUIRED_FILE_ROLES - seen_roles
    assert not missing_roles, (
        f"metadata_and_hashes.json missing required file_role(s): {missing_roles}"
    )


# ---- 6. Stage122 and Stage123 frozen-asset hashes verified -------------------

STAGE_MANIFESTS = {
    "stage122": ROOT / "stage122" / "metadata_and_hashes_stage122.json",
    "stage123": ROOT / "stage123" / "metadata_and_hashes_stage123.json",
}

# Files classified as non-frozen (regenerable) — their hash may differ.
NON_FROZEN_TRACKED = {
    "project/stage123/stage123_unit_test_output.txt",
}


@pytest.mark.parametrize("stage_name", list(STAGE_MANIFESTS))
def test_stage_frozen_asset_hashes_match(stage_name: str):
    """Verify SHA-256 of every frozen tracked file matches its manifest."""
    manifest_path = STAGE_MANIFESTS[stage_name]
    assert manifest_path.is_file(), f"Manifest missing: {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = manifest.get("output_files_sha256", {})
    assert len(outputs) > 0, f"{manifest_path.name} has empty output_files_sha256"

    stage_dir = stage_name  # e.g. "stage122"
    for fname, expected_sha in outputs.items():
        file_rel = f"project/{stage_dir}/{fname}"
        file_path = REPO_ROOT / file_rel

        # Skip non-frozen (regenerable) files.
        if file_rel in NON_FROZEN_TRACKED:
            continue

        # Skip gitignored files (regenerable, not hash-verified).
        ignore_check = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", "--", file_rel],
            capture_output=True,
        )
        if ignore_check.returncode == 0:
            continue

        assert file_path.is_file(), f"Missing frozen asset: {file_rel}"
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual == expected_sha, (
            f"SHA-256 mismatch for {file_rel}: "
            f"expected {expected_sha}, got {actual}"
        )
