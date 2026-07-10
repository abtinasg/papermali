from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import stage124_official_api_finalize as finalize  # noqa: E402
from src.stage124_batch02_v2 import jalali_str_to_gregorian_date, normalize_ticker, read_csv  # noqa: E402
from src.stage124_part03_csv_import import VERIFICATION_STATUS  # noqa: E402

JALALI_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@pytest.fixture(scope="module")
def verified_df():
    return read_csv(finalize.VERIFIED_MASTER)


@pytest.fixture(scope="module")
def template_df():
    return read_csv(finalize.TEMPLATE)


def test_exactly_130_unique_tickers(verified_df):
    assert len(verified_df) == 130
    assert verified_df["ticker"].nunique() == 130
    assert not verified_df["ticker"].duplicated().any()


def test_no_empty_first_public_trading_dates(verified_df):
    assert (verified_df["first_public_trading_date_jalali"].str.len() > 0).all()
    assert (verified_df["first_public_trading_date_gregorian"].str.len() > 0).all()


def test_jalali_dates_use_yyyy_mm_dd(verified_df):
    for value in verified_df["first_public_trading_date_jalali"]:
        assert JALALI_RE.match(value), value


def test_gregorian_conversion_matches_jalali(verified_df):
    for _, row in verified_df.iterrows():
        expected = jalali_str_to_gregorian_date(row["first_public_trading_date_jalali"]).isoformat()
        assert row["first_public_trading_date_gregorian"] == expected


def test_template_tickers_fully_covered_without_extra(verified_df, template_df):
    verified_tickers = [normalize_ticker(v) for v in verified_df["ticker"]]
    template_tickers = [normalize_ticker(v) for v in template_df["ticker"]]
    assert set(verified_tickers) == set(template_tickers)
    assert verified_tickers == template_tickers


def test_verification_status_allowed(verified_df):
    allowed = finalize.ALLOWED_VERIFICATION_STATUSES
    assert allowed == {VERIFICATION_STATUS}
    assert set(verified_df["verification_status"]) == allowed


def test_first_trade_dates_only_in_first_public_columns(verified_df):
    assert (verified_df["listing_date_jalali"].str.len() == 0).all()
    assert (verified_df["admission_date_jalali"].str.len() == 0).all()
    assert (verified_df["ipo_date_jalali"].str.len() == 0).all()


def test_official_api_manifest_hashes_match_files():
    manifest = json.loads(finalize.MANIFEST.read_text(encoding="utf-8"))
    for batch in manifest["raw_batches"]:
        path = ROOT / batch["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == batch["sha256"], batch["path"]


def test_official_api_raw_batches_exist():
    for spec in finalize.RAW_BATCH_SPECS:
        path = finalize.OFFICIAL_API_DIR / spec["repo_name"]
        assert path.is_file(), spec["repo_name"]


def test_finalize_runs_on_fresh_clone_without_downloads(tmp_path):
    api_dir = tmp_path / "official_api"
    api_dir.mkdir()
    for spec in finalize.RAW_BATCH_SPECS:
        shutil.copy2(finalize.OFFICIAL_API_DIR / spec["repo_name"], api_dir / spec["repo_name"])

    template_path = tmp_path / "listing_master_template_stage124.csv"
    verified_path = tmp_path / "listing_master_verified_stage124.csv"
    shutil.copy2(finalize.TEMPLATE, template_path)

    report = finalize.run_finalize(
        official_api_dir=api_dir,
        template_path=template_path,
        verified_master_path=verified_path,
        write_sidecar_metadata=False,
    )
    assert report["row_count"] == 130
    assert verified_path.is_file()
    out = read_csv(verified_path)
    assert len(out) == 130
    assert (out["verification_status"] == VERIFICATION_STATUS).all()


def test_cli_runs_without_downloads_dependency(tmp_path):
    api_dir = tmp_path / "official_api"
    api_dir.mkdir()
    for spec in finalize.RAW_BATCH_SPECS:
        shutil.copy2(finalize.OFFICIAL_API_DIR / spec["repo_name"], api_dir / spec["repo_name"])
    template_path = tmp_path / "listing_master_template_stage124.csv"
    verified_path = tmp_path / "listing_master_verified_stage124.csv"
    shutil.copy2(finalize.TEMPLATE, template_path)

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "run_stage124_official_api_finalize.py"),
            "--official-api-dir",
            str(api_dir),
            "--template",
            str(template_path),
        "--verified-master",
        str(verified_path),
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
    check=False,
    env={**os.environ, "PYTHONPATH": str(ROOT)},
)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert verified_path.is_file()


def test_validate_verified_master_rejects_bad_status(template_df, verified_df):
    bad = verified_df.copy()
    bad.loc[0, "verification_status"] = "pending"
    with pytest.raises(finalize.FinalizeError, match="invalid verification_status"):
        finalize.validate_verified_master(bad, template_df)
