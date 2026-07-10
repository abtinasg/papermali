import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import utils, stage124_pilot15 as s124p  # noqa: E402


def input_df():
    return s124p.load_user_input()


def test_input_exactly_15_tickers():
    df = input_df()
    assert len(df) == 15
    assert df["ticker"].nunique() == 15


def test_input_ticker_set_exact():
    assert set(input_df()["ticker"]) == s124p.PILOT_TICKERS


def test_no_duplicate_tickers():
    assert not input_df()["ticker"].duplicated().any()


def test_all_jalali_dates_parse():
    for d in input_df()["confirmed_public_entry_date_jalali"]:
        assert s124p.jalali_str_to_gregorian_date(d)


def test_gregorian_conversions_exact():
    df = input_df()
    for _, r in df.iterrows():
        assert s124p.jalali_str_to_gregorian_date(r["confirmed_public_entry_date_jalali"]).isoformat() == r["confirmed_public_entry_date_gregorian"]


def test_all_verified_user_confirmed():
    df = input_df()
    assert (df["verification_status"] == s124p.VERIFICATION_STATUS).all()
    assert (df["verified"] == "true").all()


def test_partial_master_130_rows_if_present():
    if not s124p.PARTIAL_MASTER.exists():
        return
    df = pd.read_csv(s124p.PARTIAL_MASTER, dtype=str, keep_default_na=False)
    assert len(df) == 130
    assert df["ticker"].nunique() == 130


def test_only_15_rows_leave_pending_if_present():
    if not s124p.PARTIAL_MASTER.exists():
        return
    df = pd.read_csv(s124p.PARTIAL_MASTER, dtype=str, keep_default_na=False)
    assert (df["verification_status"] == s124p.VERIFICATION_STATUS).sum() == 15
    assert (df["verification_status"] == "pending").sum() == 115


def test_nonpilot_rows_match_template_if_present():
    if not s124p.PARTIAL_MASTER.exists():
        return
    tmpl = pd.read_csv(s124p.TEMPLATE, dtype=str, keep_default_na=False).set_index("ticker")
    part = pd.read_csv(s124p.PARTIAL_MASTER, dtype=str, keep_default_na=False).set_index("ticker")
    for tk in set(tmpl.index) - s124p.PILOT_TICKERS:
        assert tmpl.loc[tk].equals(part.loc[tk])


def test_tsetmc_not_canonical_if_present():
    if not s124p.PARTIAL_MASTER.exists():
        return
    inp = input_df()
    part = pd.read_csv(s124p.PARTIAL_MASTER, dtype=str, keep_default_na=False)
    assert not any(part["ipo_date_jalali"].isin(inp["tsetmc_candidate_date_jalali"]))


def test_buali_nouri_ambiguous_if_present():
    if not s124p.CONFLICT_AUDIT.exists():
        return
    c = pd.read_csv(s124p.CONFLICT_AUDIT, dtype=str, keep_default_na=False)
    assert set(c.loc[c["tsetmc_candidate_status"] == "ambiguous_instrument", "ticker"]) == {"بوعلی", "نوری"}


def test_eligibility_exact_fiscal_year_end_if_present():
    if not s124p.ELIGIBILITY_AUDIT.exists():
        return
    a = pd.read_csv(s124p.ELIGIBILITY_AUDIT, dtype=str, keep_default_na=False)
    assert "fiscal_year_end" in a.columns
    assert (a["listing_eligibility_status_verified"].str.len() > 0).all()


def test_arvand_prelisting_if_present():
    if not s124p.ELIGIBILITY_AUDIT.exists():
        return
    a = pd.read_csv(s124p.ELIGIBILITY_AUDIT, dtype=str, keep_default_na=False)
    assert (a.loc[a["ticker"] == "اروند", "eligible_listing_financial_verified"] == "0").all()


def test_stage122_stage123_unchanged_in_qc_if_present():
    if not s124p.QC_REPORT.exists():
        return
    qc = utils.load_config() or {}
    report = pd.read_json(s124p.QC_REPORT, typ="series")
    assertions = report["assertions"]
    if assertions.get("overall_pass"):
        assert assertions["stage122_files_unchanged"]
        assert assertions["stage123_file_hash_unchanged"]


def test_no_target_or_financial_changes_if_present():
    if not s124p.QC_REPORT.exists():
        return
    report = pd.read_json(s124p.QC_REPORT, typ="series")
    assertions = report["assertions"]
    if assertions.get("overall_pass"):
        assert assertions["targets_unchanged"]
        assert assertions["financial_values_unchanged"]


def test_no_listing_master_verified_created():
    assert not s124p.FULL_VERIFIED_FORBIDDEN.exists()


def test_outputs_have_hashes_and_provenance_if_metadata_present():
    if not s124p.METADATA.exists():
        return
    meta = pd.read_json(s124p.METADATA, typ="series")
    assert meta["input_user_confirmed_sha256"]
    assert meta["source_file_sha256"]
    assert meta["output_file_hashes"]
