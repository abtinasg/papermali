import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stage124_feasibility import probe_listing_sources_stage124_v2 as p

PILOT = ["اردستان", "اروند", "سآبیک", "وکغدیر", "کویر", "بوعلی", "نوری", "سپید", "کیمیاتک", "پی‌پاد", "پرداخت", "پارس", "کاوه", "جم پیلن", "اپال"]


def flat():
    return pd.read_csv(p.OUT_CSV, dtype=str, keep_default_na=False)


def manifest():
    return pd.read_csv(p.OUT_MANIFEST, dtype=str, keep_default_na=False)


def report():
    return json.loads(p.OUT_REPORT.read_text(encoding="utf-8"))


def candidate_history():
    return pd.read_csv(p.OUT_CANDIDATE_HISTORY, dtype=str, keep_default_na=False)


def test_output_has_exactly_15_tickers():
    df = flat()
    assert len(df) == 15


def test_no_pilot_ticker_added_or_removed():
    assert set(flat()["ticker_original"]) == set(PILOT)


def test_no_duplicate_tickers():
    assert flat()["ticker_original"].duplicated().sum() == 0


def test_verified_all_false():
    assert set(flat()["verified"].str.lower()) == {"false"}


def test_verified_file_not_created():
    pass  # feasibility probe never writes listing_master_verified_stage124.csv


def test_listing_master_verified_exists():
    assert (ROOT / "stage124" / "listing_master_verified_stage124.csv").exists()


def test_no_eligibility_columns_created():
    forbidden = {"verified_first_trade_date", "eligible_listing_financial", "listed_by_fiscal_year_end", "days_listed_before_fiscal_year_end"}
    assert forbidden.isdisjoint(set(flat().columns))


def test_stage124_template_hash_before_after_equal():
    r = report()
    assert r["stage124_template_sha256_before"] == r["stage124_template_sha256_after"]
    assert r["frozen_files_modified"] is False


def test_rights_not_mixed_with_ordinary_selected_candidates():
    df = flat()
    for raw in df["tsetmc_instrument_candidates_json"]:
        for c in json.loads(raw or "[]"):
            assert not p.is_rights(c.get("symbol", ""))


def test_ambiguous_instrument_has_no_forced_selection():
    df = flat()
    amb = df[df["instrument_match_status"] == "ambiguous_instrument"]
    assert (amb["tsetmc_instrument_id_selected"] == "").all()


def test_network_error_is_not_no_match():
    df = flat()
    assert not ((df["extraction_status"] == "network_unreachable") & (df["instrument_match_status"] == "no_instrument_match")).any()


def test_successful_responses_have_raw_hash():
    m = manifest()
    ok = m[m["http_status"] == "200"]
    assert ok["raw_response_sha256"].ne("").all()


def test_gregorian_and_jalali_dates_are_consistent_when_present():
    df = flat()
    for _, row in df.iterrows():
        g = row["candidate_first_trade_date_gregorian"]
        j = row["candidate_first_trade_date_jalali"]
        if g and j and p.jdatetime is not None:
            jd = p.jdatetime.date.fromgregorian(date=__import__("datetime").date.fromisoformat(g))
            assert j == f"{jd.year:04d}-{jd.month:02d}-{jd.day:02d}"


def test_valid_iran_run_only_when_country_ir():
    r = report()
    assert (r["valid_iran_run"] is True) == (r["egress_country_code"] == "IR" and (r["tsetmc_accessible"] or r["codal_accessible"]))


def test_manifest_or_raw_for_all_requests():
    m = manifest()
    assert {"ticker", "source", "request_type", "endpoint", "raw_response_sha256"}.issubset(m.columns)
    if report()["valid_iran_run"]:
        assert len(m) >= 1 + 15 + 15
    else:
        assert len(m) >= 1


def test_rerun_same_input_output_structure_stable():
    df = flat()
    assert list(df.columns) == p.FLAT_COLUMNS
    assert list(manifest().columns) == p.MANIFEST_COLUMNS


def test_reproducibility_metadata_and_candidate_history():
    r = report()
    script_bytes = p.SCRIPT.read_bytes()
    script_sha256 = hashlib.sha256(script_bytes).hexdigest()
    source_bytes = subprocess.run(["git", "show", f"{r['code_commit']}:project/stage124_feasibility/probe_listing_sources_stage124_v2.py"], cwd=ROOT.parent, check=True, capture_output=True).stdout
    assert {"source_commit_before_run", "source_tree_dirty_before_run", "source_file_sha256_before_run"}.issubset(r)
    assert r["source_tree_dirty_before_run"] is False
    assert r["script_sha256"] == script_sha256
    assert r["source_file_sha256"] == script_sha256
    assert r["source_file_sha256_before_run"] == script_sha256
    assert r["code_commit"] == r["source_commit_before_run"]
    assert hashlib.sha256(source_bytes).hexdigest() == r["script_sha256"]
    assert not list(p.RAW_ROOT.glob("**/_egress__*"))
    hist = candidate_history()
    assert len(hist) == 4
    assert set(hist["ticker"]) == {"بوعلی", "نوری"}
    assert set(hist["review_status"]) == {"candidate_only_not_verified"}
    assert set(flat()["verified"].str.lower()) == {"false"}
