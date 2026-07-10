"""Unit tests for Stage124 Part 1 (listing-master template).

Run: pytest -q tests/test_stage124.py
Pure-function tests use synthetic frames; integration tests read the real frozen
Stage123 dataset and the produced template.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import utils, stage124 as s124  # noqa: E402


def _synthetic(n_tickers=130, years=(1392, 1393, 1394), prelisting_ticker="AAA0"):
    rows = []
    for i in range(n_tickers):
        tk = f"AAA{i}"
        for y in years:
            el = "0" if (tk == prelisting_ticker and y == years[0]) else "1"
            rows.append({"row_key": f"{tk}|{y}", "ticker": tk,
                         "company_name": f"Co {i}", "fiscal_year": str(y),
                         "eligible_listing": el})
    return pd.DataFrame(rows)


_TRACKED_META = ROOT / "stage124" / "metadata_and_hashes_stage124_part1.json"


@pytest.fixture(scope="session")
def built():
    cfg = utils.load_config()
    _backup = _TRACKED_META.read_bytes() if _TRACKED_META.is_file() else None
    res = s124.build_template(cfg)
    tmpl = pd.read_csv(res["out"] / "listing_master_template_stage124.csv", dtype=str,
                       keep_default_na=False)
    raw = s124.load_stage123_frozen()
    yield {"cfg": cfg, "out": res["out"], "qc": res["qc"], "tmpl": tmpl, "raw": raw}
    if _backup is not None:
        _TRACKED_META.write_bytes(_backup)


# 1 ----------------------------------------------------------------------
def test_template_exactly_130_unique_tickers(built):
    assert built["tmpl"]["ticker"].nunique() == 130
    assert len(built["tmpl"]) == 130


# 2 ----------------------------------------------------------------------
def test_template_matches_stage123_ticker_set(built):
    assert set(built["tmpl"]["ticker"]) == set(built["raw"]["ticker"].unique())


# 3 ----------------------------------------------------------------------
def test_manual_date_and_source_fields_are_blank(built):
    assert (built["tmpl"][s124.MANUAL_BLANK] == "").all().all()


# 4 ----------------------------------------------------------------------
def test_prelisting_proxy_count_and_flag_consistent(built):
    t = built["tmpl"]
    cnt = t["current_prelisting_proxy_row_count"].astype(int)
    flag = t["has_prelisting_proxy_rows"].astype(int)
    assert (flag == (cnt > 0).astype(int)).all()


# 5 ----------------------------------------------------------------------
def test_template_independent_of_input_row_order():
    df = _synthetic()
    a = s124.build_template_df(df)
    b = s124.build_template_df(df.sample(frac=1.0, random_state=11).reset_index(drop=True))
    assert a.equals(b)


# 6 ----------------------------------------------------------------------
def test_duplicate_ticker_fails():
    # a template with a duplicated ticker row must fail QC
    df = _synthetic()
    tmpl = s124.build_template_df(df)
    dupd = pd.concat([tmpl, tmpl.iloc[[0]]], ignore_index=True)
    qc = s124.compute_qc(dupd, set(df["ticker"]), "deadbeef", "x.csv", len(df))
    assert qc["overall_pass"] is False
    assert qc["assertions"]["zero_duplicate_ticker"] is False


# 7 ----------------------------------------------------------------------
def test_missing_or_extra_ticker_fails():
    df = _synthetic()
    tmpl = s124.build_template_df(df)
    ref = set(df["ticker"])
    # missing one ticker
    qc_missing = s124.compute_qc(tmpl.iloc[1:].copy(), ref, "h", "x.csv", len(df))
    assert qc_missing["overall_pass"] is False
    # extra ticker not in reference
    extra = pd.concat([tmpl, tmpl.iloc[[0]].assign(ticker="ZZZ")], ignore_index=True)
    qc_extra = s124.compute_qc(extra, ref, "h", "x.csv", len(df))
    assert qc_extra["overall_pass"] is False


# 8 ----------------------------------------------------------------------
def test_stage123_input_hash_recorded(built):
    expected = utils.sha256_file(s124.stage123_frozen_path())
    assert built["qc"]["stage123_input_sha256"] == expected
    meta = pd.read_json(built["out"] / "metadata_and_hashes_stage124_part1.json",
                        typ="series")
    assert meta["stage123_input_sha256"] == expected


# 9 ----------------------------------------------------------------------
def test_qc_failure_prevents_success_metadata(tmp_path):
    cfg = utils.load_config()
    bad = _synthetic(n_tickers=129)  # != 130 and != frozen set -> QC must fail
    with pytest.raises(s124.QCFail):
        s124.build_template(cfg, out_dir=tmp_path, df=bad)
    assert (tmp_path / "stage124_template_report.json").exists()        # report saved
    assert not (tmp_path / "metadata_and_hashes_stage124_part1.json").exists()  # no meta


# 10 ---------------------------------------------------------------------
def test_stage123_file_not_modified():
    p = s124.stage123_frozen_path()
    before = utils.sha256_file(p)
    cfg = utils.load_config()
    s124.build_template(cfg)
    assert utils.sha256_file(p) == before  # Stage123 input untouched
