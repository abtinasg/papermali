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

JALALI_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@pytest.fixture()
def isolated_official_api_tree(tmp_path):
    api_dir = tmp_path / "official_api"
    api_dir.mkdir()
    for spec in finalize.RAW_BATCH_SPECS:
        shutil.copy2(finalize.OFFICIAL_API_DIR / spec["repo_name"], api_dir / spec["repo_name"])
    template_path = tmp_path / "listing_master_template_stage124.csv"
    verified_path = tmp_path / "listing_master_verified_stage124.csv"
    shutil.copy2(finalize.TEMPLATE, template_path)
    return {
        "api_dir": api_dir,
        "template_path": template_path,
        "verified_path": verified_path,
    }


def _run_finalize(tree: dict) -> pd.DataFrame:
    report = finalize.run_finalize(
        official_api_dir=tree["api_dir"],
        template_path=tree["template_path"],
        verified_master_path=tree["verified_path"],
        write_sidecar_metadata=False,
    )
    assert report["row_count"] == 130
    return read_csv(tree["verified_path"])


def test_exactly_130_unique_tickers(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert len(verified) == 130
    assert verified["ticker"].nunique() == 130
    assert not verified["ticker"].duplicated().any()


def test_no_empty_first_public_trading_dates(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert (verified["first_public_trading_date_jalali"].str.len() > 0).all()
    assert (verified["first_public_trading_date_gregorian"].str.len() > 0).all()


def test_jalali_dates_use_yyyy_mm_dd(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    for value in verified["first_public_trading_date_jalali"]:
        assert JALALI_RE.match(value), value


def test_gregorian_conversion_matches_jalali(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    for _, row in verified.iterrows():
        expected = jalali_str_to_gregorian_date(row["first_public_trading_date_jalali"]).isoformat()
        assert row["first_public_trading_date_gregorian"] == expected


def test_template_tickers_fully_covered_without_extra(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    template = read_csv(isolated_official_api_tree["template_path"])
    verified_tickers = [normalize_ticker(v) for v in verified["ticker"]]
    template_tickers = [normalize_ticker(v) for v in template["ticker"]]
    assert set(verified_tickers) == set(template_tickers)
    assert verified_tickers == template_tickers


def test_verification_status_allowed(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert finalize.ALLOWED_VERIFICATION_STATUSES == {finalize.VERIFICATION_STATUS}
    assert set(verified["verification_status"]) == {finalize.VERIFICATION_STATUS}


def test_first_trade_dates_only_in_first_public_columns(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert (verified["listing_date_jalali"].str.len() == 0).all()
    assert (verified["admission_date_jalali"].str.len() == 0).all()
    assert (verified["ipo_date_jalali"].str.len() == 0).all()


def test_source_urls_populated(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert (verified["source_1_url"].str.len() > 0).all()
    assert verified["source_1_url"].str.startswith("https://").all()


def test_conflict_status_not_auto_resolved(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert not (verified["conflict_status"] == "resolved_tse_csv_imported").any()
    hk = verified.loc[verified["ticker"] == "حکشتی", "conflict_status"].iloc[0]
    assert hk == finalize.CONFLICT_UNRESOLVED


def test_hkeshti_conflict_documented(isolated_official_api_tree):
    _run_finalize(isolated_official_api_tree)
    audit = finalize.build_conflict_audit(
        {
            item["ticker"]: item
            for item in (
                finalize._normalize_api_row(row)
                for _, row in finalize.load_official_api_batches(
                    official_api_dir=isolated_official_api_tree["api_dir"]
                )[1].iterrows()
            )
        }
    )
    hk = audit[audit["ticker"] == "حکشتی"]
    assert not hk.empty
    assert {"1387-02-28", "1387-02-29"}.issubset(
        set(hk["previous_date"]).union(set(hk["api_observed_date"]))
    )


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


def test_finalize_runs_on_fresh_clone_without_downloads(isolated_official_api_tree):
    verified = _run_finalize(isolated_official_api_tree)
    assert len(verified) == 130


def test_cli_runs_without_downloads_dependency(isolated_official_api_tree):
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "run_stage124_official_api_finalize.py"),
            "--official-api-dir",
            str(isolated_official_api_tree["api_dir"]),
            "--template",
            str(isolated_official_api_tree["template_path"]),
            "--verified-master",
            str(isolated_official_api_tree["verified_path"]),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert isolated_official_api_tree["verified_path"].is_file()


def test_validate_verified_master_rejects_bad_status(isolated_official_api_tree):
    template = read_csv(isolated_official_api_tree["template_path"])
    verified = _run_finalize(isolated_official_api_tree)
    bad = verified.copy()
    bad.loc[0, "verification_status"] = "pending"
    with pytest.raises(finalize.FinalizeError, match="invalid verification_status"):
        finalize.validate_verified_master(bad, template)
