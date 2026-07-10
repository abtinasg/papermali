from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import stage124_part03_csv_import as csv_import  # noqa: E402
from src.stage124_batch02_part03 import PART03_TICKERS  # noqa: E402
from src.stage124_batch02_v2 import read_csv  # noqa: E402


def _template_partial_master() -> pd.DataFrame:
    rows = []
    for ticker in PART03_TICKERS:
        rows.append(
            {
                "ticker": ticker,
                "company_name": f"شرکت {ticker}",
                "ticker_aliases": "",
                "market": "",
                "earliest_fiscal_year_in_dataset": "1392",
                "latest_fiscal_year_in_dataset": "1402",
                "current_prelisting_proxy_row_count": "0",
                "has_prelisting_proxy_rows": "0",
                "current_first_eligible_year_proxy": "1392",
                "admission_date_jalali": "",
                "listing_date_jalali": "",
                "ipo_date_jalali": "",
                "first_public_trading_date_jalali": "",
                "first_public_trading_date_gregorian": "",
                "source_1_type": "",
                "source_1_title": "",
                "source_1_url": "",
                "source_2_type": "",
                "source_2_title": "",
                "source_2_url": "",
                "verification_status": "pending",
                "conflict_status": "",
                "notes": "",
            }
        )
    rows.append(
        {
            "ticker": "فولاد",
            "company_name": "شرکت فولاد مبارکه",
            "ticker_aliases": "",
            "market": "",
            "earliest_fiscal_year_in_dataset": "1392",
            "latest_fiscal_year_in_dataset": "1402",
            "current_prelisting_proxy_row_count": "0",
            "has_prelisting_proxy_rows": "0",
            "current_first_eligible_year_proxy": "1392",
            "admission_date_jalali": "",
            "listing_date_jalali": "",
            "ipo_date_jalali": "",
            "first_public_trading_date_jalali": "",
            "first_public_trading_date_gregorian": "",
            "source_1_type": "",
            "source_1_title": "",
            "source_1_url": "",
            "source_2_type": "",
            "source_2_title": "",
            "source_2_url": "",
            "verification_status": "pending",
            "conflict_status": "",
            "notes": "keep me untouched",
        }
    )
    return pd.DataFrame(rows)


def _write_partial_master(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _template_partial_master().to_csv(
        path, index=False, encoding="utf-8-sig"
    )


def _trusted_rows() -> list[dict]:
    rows = []
    for index, ticker in enumerate(PART03_TICKERS, start=1):
        rows.append(
            {
                "ticker": ticker,
                "company_name": f"شرکت {ticker}",
                "public_entry_date_jalali": f"1400-01-{index:02d}",
                "source_title": "بورس تهران",
                "source_type": "official_tse_csv_import",
                "source_url": "https://www.tse.ir/",
                "notes": "Imported from official exchange CSV.",
            }
        )
    return rows


def _write_input(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_canonicalize_accepts_alias_columns(tmp_path):
    input_path = tmp_path / "trusted.csv"
    _write_input(
        input_path,
        [
            {
                "نماد": "خمهر",
                "نام شرکت": "شرکت خمهر",
                "تاریخ ورود به بورس": "1400/01/01",
            }
        ],
    )
    raw = pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    canonical = csv_import.canonicalize_input(raw)
    assert list(canonical.columns) == csv_import.CANONICAL_COLUMNS
    assert canonical.iloc[0]["ticker"] == "خمهر"
    assert canonical.iloc[0]["public_entry_date_jalali"] == "1400/01/01"


def test_partial_scope_accepts_symbol_and_first_trade_columns(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    _write_partial_master(partial_master)
    input_path = tmp_path / "trusted.csv"
    rows = [
        {
            "symbol": "خنصیر",
            "first_trade_date_jalali": "1383/12/15",
            "first_trade_date_gregorian": "2005-03-05",
        },
        {
            "symbol": "خوساز",
            "first_trade_date_jalali": "1380/01/18",
            "first_trade_date_gregorian": "2001-04-07",
        },
        {
            "symbol": "فولاد",
            "first_trade_date_jalali": "1380/01/01",
            "first_trade_date_gregorian": "2001-03-21",
        },
    ]
    _write_input(input_path, rows)
    raw = pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    canonical = csv_import.canonicalize_input(raw)

    report = csv_import.validate_input(
        canonical,
        partial_master_path=partial_master,
        scope_tickers=["خنصیر", "خوساز"],
        allow_partial_scope=True,
    )
    assert report["ticker_count"] == 2
    assert report["ignored_out_of_scope_tickers"] == ["فولاد"]


def test_validate_rejects_partial_scope(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    _write_partial_master(partial_master)
    input_path = tmp_path / "trusted.csv"
    _write_input(input_path, _trusted_rows()[:-1])

    canonical = csv_import.canonicalize_input(
        pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    )

    with pytest.raises(csv_import.ImportErrorCSV, match="exactly 10 in-scope rows"):
        csv_import.validate_input(canonical, partial_master_path=partial_master)


def test_validate_rejects_duplicate_ticker(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    _write_partial_master(partial_master)
    rows = _trusted_rows()
    rows[-1]["ticker"] = rows[0]["ticker"]
    input_path = tmp_path / "trusted.csv"
    _write_input(input_path, rows)

    canonical = csv_import.canonicalize_input(
        pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    )

    with pytest.raises(csv_import.ImportErrorCSV, match="duplicate tickers"):
        csv_import.validate_input(canonical, partial_master_path=partial_master)


def test_validate_rejects_bad_jalali_date(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    _write_partial_master(partial_master)
    rows = _trusted_rows()
    rows[0]["public_entry_date_jalali"] = "1400-13-01"
    input_path = tmp_path / "trusted.csv"
    _write_input(input_path, rows)

    canonical = csv_import.canonicalize_input(
        pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    )

    with pytest.raises(csv_import.ImportErrorCSV, match="invalid exact Jalali"):
        csv_import.validate_input(canonical, partial_master_path=partial_master)


def test_apply_updates_only_part03_rows(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    report_path = tmp_path / "report.json"
    input_path = tmp_path / "trusted.csv"
    _write_partial_master(partial_master)
    _write_input(input_path, _trusted_rows())

    report = csv_import.run_import(
        input_path=input_path,
        partial_master_path=partial_master,
        report_path=report_path,
        apply=True,
    )

    assert report["status"] == "import_applied"
    updated = read_csv(partial_master).set_index("ticker")
    untouched = updated.loc["فولاد"]
    assert untouched["verification_status"] == "pending"
    assert untouched["notes"] == "keep me untouched"

    for index, ticker in enumerate(PART03_TICKERS, start=1):
        row = updated.loc[ticker]
        expected_j = f"1400-01-{index:02d}"
        assert row["first_public_trading_date_jalali"] == expected_j
        assert row["listing_date_jalali"] == ""
        assert row["ipo_date_jalali"] == ""
        assert row["verification_status"] == csv_import.VERIFICATION_STATUS
        assert row["conflict_status"] == csv_import.CONFLICT_STATUS
        assert row["source_1_title"] == "بورس تهران"

    assert report_path.exists()


def test_dry_run_leaves_partial_master_unchanged(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    report_path = tmp_path / "report.json"
    input_path = tmp_path / "trusted.csv"
    _write_partial_master(partial_master)
    before = partial_master.read_bytes()
    _write_input(input_path, _trusted_rows())

    report = csv_import.run_import(
        input_path=input_path,
        partial_master_path=partial_master,
        report_path=report_path,
        apply=False,
    )

    assert report["status"] == "validated_dry_run"
    assert partial_master.read_bytes() == before
    assert not report_path.exists()


def test_all_listing_master_skips_bad_status_and_imports_ok_rows(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    report_path = tmp_path / "report.json"
    input_path = tmp_path / "trusted.csv"
    _write_partial_master(partial_master)
    rows = [
        {
            "symbol": "خنصیر",
            "first_trade_date_jalali": "1383/12/15",
            "first_trade_date_gregorian": "2005-03-05",
            "status": "ok",
        },
        {
            "symbol": "خوساز",
            "first_trade_date_jalali": "1380/01/18",
            "first_trade_date_gregorian": "2001-04-07",
            "status": "ok",
        },
        {
            "symbol": "فولاد",
            "first_trade_date_jalali": "1380/01/01",
            "first_trade_date_gregorian": "2001-03-21",
            "status": "ok",
        },
        {
            "symbol": "بوعلی",
            "status": "ambiguous",
        },
        {
            "symbol": "UNKNOWN",
            "first_trade_date_jalali": "1380/01/01",
            "status": "ok",
        },
    ]
    _write_input(input_path, rows)

    report = csv_import.run_import(
        input_path=input_path,
        partial_master_path=partial_master,
        report_path=report_path,
        apply=True,
        all_listing_master=True,
    )

    assert report["scope_mode"] == "listing_master"
    assert report["row_count"] == 3
    assert report["skipped_bad_status"] == [
        {"ticker": "بوعلی", "import_status": "ambiguous", "row": 5}
    ]
    assert report["skipped_not_in_master"] == [{"ticker": "UNKNOWN", "row": 6}]

    updated = read_csv(partial_master).set_index("ticker")
    assert updated.loc["خنصیر", "verification_status"] == csv_import.VERIFICATION_STATUS
    assert updated.loc["فولاد", "verification_status"] == csv_import.VERIFICATION_STATUS
    assert updated.loc["خمهر", "verification_status"] == "pending"


def test_apply_partial_scope_updates_only_requested_subset(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    report_path = tmp_path / "report.json"
    input_path = tmp_path / "trusted.csv"
    _write_partial_master(partial_master)
    rows = [
        {
            "symbol": "خنصیر",
            "first_trade_date_jalali": "1383/12/15",
            "first_trade_date_gregorian": "2005-03-05",
            "note": "This is first observed trading date.",
        },
        {
            "symbol": "خوساز",
            "first_trade_date_jalali": "1380/01/18",
            "first_trade_date_gregorian": "2001-04-07",
            "note": "This is first observed trading date.",
        },
        {
            "symbol": "فولاد",
            "first_trade_date_jalali": "1380/01/01",
            "first_trade_date_gregorian": "2001-03-21",
        },
    ]
    _write_input(input_path, rows)

    report = csv_import.run_import(
        input_path=input_path,
        partial_master_path=partial_master,
        report_path=report_path,
        apply=True,
        scope_tickers=["خنصیر", "خوساز"],
        allow_partial_scope=True,
    )

    updated = read_csv(partial_master).set_index("ticker")
    assert updated.loc["خنصیر", "verification_status"] == csv_import.VERIFICATION_STATUS
    assert updated.loc["خوساز", "verification_status"] == csv_import.VERIFICATION_STATUS
    assert updated.loc["خمهر", "verification_status"] == "pending"
    assert report["ignored_out_of_scope_tickers"] == ["فولاد"]


def test_all_listing_master_matches_zwnj_ticker_in_partial_master(tmp_path):
    partial_master = tmp_path / "listing_master_partial_verified_stage124.csv"
    report_path = tmp_path / "report.json"
    input_path = tmp_path / "trusted.csv"
    _write_partial_master(partial_master)
    partial = read_csv(partial_master)
    partial.loc[partial["ticker"] == "فولاد", "ticker"] = "پی\u200cپاد"
    partial.loc[partial["ticker"] == "پی\u200cپاد", "company_name"] = "پرداخت الکترونیک پاسارگاد"
    partial.to_csv(partial_master, index=False, encoding="utf-8-sig")
    _write_input(
        input_path,
        [
            {
                "symbol": "پی پاد",
                "first_trade_date_jalali": "1402/01/16",
                "first_trade_date_gregorian": "2023-04-05",
                "status": "ok",
            }
        ],
    )

    csv_import.run_import(
        input_path=input_path,
        partial_master_path=partial_master,
        report_path=report_path,
        apply=True,
        all_listing_master=True,
    )

    updated = read_csv(partial_master).set_index("ticker", drop=False)
    row = updated.loc[updated["ticker"].str.replace("\u200c", " ", regex=False) == "پی پاد"].iloc[0]
    assert row["verification_status"] == csv_import.VERIFICATION_STATUS
    assert row["first_public_trading_date_jalali"] == "1402-01-16"
