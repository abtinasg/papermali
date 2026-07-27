"""Tests for the Stage127 external TSETMC retrieval-request package.

Fail-closed: every assertion protects either the frozen development scope, the
final-test firewall, or the external programmer's inability to make a
scientific decision. No model is fit and no market data is retrieved here.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, timedelta

import pytest

from src import stage127_m2_external_retrieval_request as ext
from src import stage127_m2_market_data_gate as gate

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(REAL_ROOT)
EXT_DIR = os.path.join(REAL_ROOT, "stage127", "external_retrieval")

#: Jalali 1400-01-01 == 2021-03-21 Gregorian: the first day of the locked
#: final-test period. Nothing in this package may reach it.
FINAL_TEST_PERIOD_START = date(2021, 3, 21)

EXPECTED_PAIRS = 666
EXPECTED_TICKERS = 110


def _read_csv(name: str) -> list[dict[str, str]]:
    with open(os.path.join(EXT_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _headers(name: str) -> list[str]:
    with open(os.path.join(EXT_DIR, name), encoding="utf-8") as f:
        return next(csv.reader(f))


@pytest.fixture(scope="module")
def requests_rows():
    return _read_csv(ext.REQUEST_CSV)


@pytest.fixture(scope="module")
def ranges_rows():
    return _read_csv(ext.TICKER_RANGES_CSV)


@pytest.fixture(scope="module")
def manifest():
    with open(os.path.join(EXT_DIR, ext.REQUEST_MANIFEST_JSON), encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Scope: exactly the frozen 666 development pairs
# --------------------------------------------------------------------------- #

def test_exactly_666_unique_development_pair_requests(requests_rows):
    assert len(requests_rows) == EXPECTED_PAIRS
    keys = {(r["ticker"], r["fiscal_year_t"]) for r in requests_rows}
    assert len(keys) == EXPECTED_PAIRS


def test_no_duplicate_request_ids(requests_rows):
    ids = [r["request_id"] for r in requests_rows]
    assert len(ids) == len(set(ids))


def test_only_development_target_years(requests_rows):
    years = {int(r["target_year"]) for r in requests_rows}
    assert years == set(gate.DEVELOPMENT_TARGET_YEARS)


def test_zero_final_test_target_year_pairs(requests_rows):
    for r in requests_rows:
        assert int(r["target_year"]) not in gate.FINAL_TEST_TARGET_YEARS


def test_every_request_belongs_to_the_frozen_development_set(requests_rows):
    pairs = gate.load_development_pairs(REPO_ROOT)
    frozen = {(p["ticker"], p["fiscal_year_t"]) for p in pairs}
    requested = {(r["ticker"], r["fiscal_year_t"]) for r in requests_rows}
    assert requested == frozen


def test_ticker_count_matches_frozen_development_set(requests_rows):
    assert len({r["ticker"] for r in requests_rows}) == EXPECTED_TICKERS


# --------------------------------------------------------------------------- #
# Point-in-time correctness
# --------------------------------------------------------------------------- #

def test_all_pair_cutoff_dates_present(requests_rows):
    for r in requests_rows:
        assert r["pair_cutoff_date"].strip()
        date.fromisoformat(r["pair_cutoff_date"])


def test_requested_end_is_strictly_before_pair_cutoff(requests_rows):
    for r in requests_rows:
        assert date.fromisoformat(r["requested_end_date"]) < date.fromisoformat(
            r["pair_cutoff_date"]), r["request_id"]


def test_requested_range_contains_the_full_12_month_window(requests_rows):
    for r in requests_rows:
        start = date.fromisoformat(r["requested_start_date"])
        end = date.fromisoformat(r["requested_end_date"])
        assert start < end
        # The retrieval superset must contain the true 12-calendar-month window.
        assert start <= gate.minus_calendar_months(end, 12)


def test_retrieval_buffer_is_documented_as_superset_only(manifest):
    assert manifest["retrieval_buffer_days"] == ext.RETRIEVAL_BUFFER_DAYS
    assert manifest["retrieval_buffer_is_superset_only"] is True
    assert manifest["retrieval_buffer_does_not_alter_scientific_window"] is True
    assert manifest["shared_window_calendar_months"] == 12


def test_window_rule_states_strictly_before_cutoff(requests_rows):
    for r in requests_rows:
        assert r["window_rule"] == ext.WINDOW_RULE
    assert "strictly_before_pair_cutoff" in ext.WINDOW_RULE


# --------------------------------------------------------------------------- #
# Final-test firewall — no final-test period may appear anywhere
# --------------------------------------------------------------------------- #

def test_no_requested_date_reaches_the_final_test_period(requests_rows):
    for r in requests_rows:
        assert date.fromisoformat(r["requested_end_date"]) < FINAL_TEST_PERIOD_START
        assert date.fromisoformat(r["requested_start_date"]) < FINAL_TEST_PERIOD_START


def test_no_ticker_range_reaches_the_final_test_period(ranges_rows):
    for r in ranges_rows:
        assert date.fromisoformat(r["requested_end_date"]) < FINAL_TEST_PERIOD_START


def test_manifest_declares_final_test_excluded(manifest):
    assert manifest["final_test_target_years_excluded"] == [1400, 1401, 1402]
    assert manifest["final_test_pairs_included"] == 0
    assert manifest["final_test_row_level_data_included"] is False
    assert manifest["final_test_access_authorized"] is False


def test_package_carries_no_target_or_predictor_values(requests_rows):
    """The external party must receive identifiers and dates only."""
    leaky = {
        gate.PRIMARY_TARGET, "FD_target_main", "total_assets", "leverage_ratio",
        "roa_period_adjusted", "target", "label",
    }
    assert not (set(requests_rows[0].keys()) & leaky)
    assert set(requests_rows[0].keys()) == set(ext.REQUEST_COLUMNS)


# --------------------------------------------------------------------------- #
# Ticker ranges: derived only from pair requests, never broadened
# --------------------------------------------------------------------------- #

def test_ticker_ranges_derive_only_from_pair_requests(requests_rows, ranges_rows):
    req_tickers = {r["ticker"] for r in requests_rows}
    rng_tickers = {r["ticker"] for r in ranges_rows}
    assert rng_tickers == req_tickers


def test_no_range_exceeds_the_union_of_its_pair_ranges(requests_rows, ranges_rows):
    """Each merged range must be covered by contiguous/overlapping pair ranges.

    A merged interval is legitimate only if the pair intervals inside it chain
    together with no gap. Any range extending beyond that union would be an
    unjustified broadening of scientific scope.
    """
    by_ticker: dict[str, list[tuple[date, date]]] = {}
    for r in requests_rows:
        by_ticker.setdefault(r["ticker"], []).append((
            date.fromisoformat(r["requested_start_date"]),
            date.fromisoformat(r["requested_end_date"]),
        ))

    for rng in ranges_rows:
        rs = date.fromisoformat(rng["requested_start_date"])
        re_ = date.fromisoformat(rng["requested_end_date"])
        intervals = sorted(
            iv for iv in by_ticker[rng["ticker"]] if iv[0] >= rs and iv[1] <= re_
        )
        assert intervals, rng["range_id"]
        # Endpoints must come from real pair requests, never invented.
        assert intervals[0][0] == rs
        assert max(e for _, e in intervals) == re_
        # The chain must be gap-free: only contiguous/overlapping merges.
        reach = intervals[0][1]
        for s, e in intervals[1:]:
            assert s <= reach, (
                f"{rng['range_id']} merges across a real gap at {s}"
            )
            reach = max(reach, e)


def test_every_pair_request_is_covered_by_exactly_one_range(requests_rows, ranges_rows):
    for r in requests_rows:
        s = date.fromisoformat(r["requested_start_date"])
        e = date.fromisoformat(r["requested_end_date"])
        covering = [
            g for g in ranges_rows
            if g["ticker"] == r["ticker"]
            and date.fromisoformat(g["requested_start_date"]) <= s
            and date.fromisoformat(g["requested_end_date"]) >= e
        ]
        assert len(covering) == 1, r["request_id"]


def test_covered_pair_counts_sum_to_the_request_count(requests_rows, ranges_rows):
    assert sum(int(r["covered_pair_count"]) for r in ranges_rows) == len(requests_rows)


def test_disjoint_intervals_are_not_merged():
    """A real gap must produce two ranges, never one spanning span."""
    reqs = [
        {"ticker": "X", "requested_start_date": "2013-01-01",
         "requested_end_date": "2013-06-01"},
        {"ticker": "X", "requested_start_date": "2019-01-01",
         "requested_end_date": "2019-06-01"},
    ]
    ranges = ext.merge_ticker_ranges(reqs)
    assert len(ranges) == 2
    assert ranges[0]["requested_end_date"] == "2013-06-01"
    assert ranges[1]["requested_start_date"] == "2019-01-01"


def test_overlapping_intervals_are_merged():
    reqs = [
        {"ticker": "X", "requested_start_date": "2013-01-01",
         "requested_end_date": "2014-01-01"},
        {"ticker": "X", "requested_start_date": "2013-06-01",
         "requested_end_date": "2014-06-01"},
    ]
    ranges = ext.merge_ticker_ranges(reqs)
    assert len(ranges) == 1
    assert ranges[0]["requested_start_date"] == "2013-01-01"
    assert ranges[0]["requested_end_date"] == "2014-06-01"
    assert ranges[0]["covered_pair_count"] == 2


# --------------------------------------------------------------------------- #
# Source discipline
# --------------------------------------------------------------------------- #

def test_source_id_is_exactly_tsetmc(requests_rows, ranges_rows, manifest):
    assert {r["source_id"] for r in requests_rows} == {"src_m2_tsetmc_market"}
    assert {r["source_id"] for r in ranges_rows} == {"src_m2_tsetmc_market"}
    assert manifest["source_id"] == "src_m2_tsetmc_market"
    assert manifest["substitute_sources_authorized"] is False


def test_required_fields_are_the_frozen_ones(requests_rows):
    assert {r["required_price_field"] for r in requests_rows} == {"adjusted_close"}
    assert {r["required_value_field"] for r in requests_rows} == {"traded_value_rial"}


# --------------------------------------------------------------------------- #
# Return schemas
# --------------------------------------------------------------------------- #

def test_daily_template_headers_exact():
    assert _headers(ext.DAILY_TEMPLATE_CSV) == list(ext.DAILY_TEMPLATE_COLUMNS)


def test_mapping_template_headers_exact():
    assert _headers(ext.MAPPING_TEMPLATE_CSV) == list(ext.MAPPING_TEMPLATE_COLUMNS)


def test_manifest_template_headers_exact():
    assert _headers(ext.MANIFEST_TEMPLATE_CSV) == list(ext.MANIFEST_TEMPLATE_COLUMNS)


@pytest.mark.parametrize("name", [
    ext.DAILY_TEMPLATE_CSV, ext.MAPPING_TEMPLATE_CSV, ext.MANIFEST_TEMPLATE_CSV,
])
def test_templates_contain_no_synthetic_example_rows(name):
    assert _read_csv(name) == []


def test_allowed_status_vocabularies_are_documented():
    readme = open(os.path.join(EXT_DIR, ext.EXTERNAL_README), encoding="utf-8").read()
    for status in ext.ALLOWED_MAPPING_STATUS:
        assert status in readme
    for status in ext.ALLOWED_RETRIEVAL_STATUS:
        assert status in readme


# --------------------------------------------------------------------------- #
# Manifest consistency
# --------------------------------------------------------------------------- #

def test_manifest_counts_match_the_request_files(manifest, requests_rows, ranges_rows):
    assert manifest["pair_count"] == len(requests_rows) == EXPECTED_PAIRS
    assert manifest["ticker_count"] == len(
        {r["ticker"] for r in requests_rows}) == EXPECTED_TICKERS
    assert manifest["ticker_range_count"] == len(ranges_rows)
    assert manifest["date_min"] == min(
        r["requested_start_date"] for r in requests_rows)
    assert manifest["date_max"] == max(
        r["requested_end_date"] for r in requests_rows)


def test_manifest_scope_and_role_fields(manifest):
    assert manifest["request_scope"] == "development_only"
    assert manifest["sample"] == "main_rule_a_primary"
    assert manifest["target"] == "FD_target_main_t_plus_1"
    assert manifest["development_target_years"] == [
        1393, 1394, 1395, 1396, 1397, 1398, 1399]
    assert manifest["external_programmer_role"] == (
        "raw_authoritative_data_retrieval_only")
    assert manifest["external_feature_engineering_authorized"] is False
    assert manifest["external_modeling_authorized"] is False
    assert manifest["imputation_authorized"] is False
    assert manifest["ticker_mapping_guessing_authorized"] is False


def test_manifest_lists_the_three_downstream_variables(manifest):
    assert manifest["downstream_m2_variables"] == [
        "equity_return_window", "realized_volatility", "amihud_illiquidity"]
    assert manifest["downstream_m2_variables_computed_by"] == (
        "papermali_after_ingestion")


def test_manifest_pins_every_package_file(manifest):
    pinned = manifest["package_files_sha256"]
    for name in ext.PACKAGE_FILES:
        if name == ext.REQUEST_MANIFEST_JSON:
            continue  # cannot hash itself
        assert name in pinned, name
        text = open(os.path.join(EXT_DIR, name), encoding="utf-8").read()
        assert pinned[name] == gate.sha256_text(text), name


def test_manifest_does_not_resolve_the_gate(manifest):
    assert manifest["gate_status_unchanged"] == "UNRESOLVED_M2_DATA_GATE"
    assert manifest["m2_data_collected"] is False


# --------------------------------------------------------------------------- #
# README completeness for a reader who knows nothing about the project
# --------------------------------------------------------------------------- #

def test_readme_states_the_critical_prohibitions():
    readme = open(os.path.join(EXT_DIR, ext.EXTERNAL_README), encoding="utf-8").read()
    lower = readme.lower()
    for term in ("yahoo", "kaggle", "mirror"):
        assert term in lower
    for term in ("impute", "interpolate", "forward-fill", "backward-fill"):
        assert term in lower
    assert "ADJUSTED_CLOSE_UNRESOLVED" in readme
    assert "UNRESOLVED" in readme
    assert "sha256" in lower
    assert "pilot" in lower


def test_readme_forbids_computing_the_three_m2_features():
    readme = open(os.path.join(EXT_DIR, ext.EXTERNAL_README), encoding="utf-8").read()
    for var, _, _ in gate.M2_VARIABLES:
        assert var in readme
    assert "do not compute" in readme.lower()


def test_readme_requires_code_delivery_and_raw_responses():
    readme = open(os.path.join(EXT_DIR, ext.EXTERNAL_README), encoding="utf-8").read()
    lower = readme.lower()
    assert "extraction scripts" in lower or "extraction code" in lower
    assert "raw response" in lower


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def test_generation_is_deterministic():
    a = ext.build_all(REPO_ROOT)
    b = ext.build_all(REPO_ROOT)
    assert a == b


def test_on_disk_package_matches_a_fresh_build():
    fresh = ext.build_all(REPO_ROOT)
    for name, text in fresh.items():
        on_disk = open(os.path.join(EXT_DIR, name), encoding="utf-8").read()
        assert on_disk == text, name


def test_request_rows_are_deterministically_ordered(requests_rows):
    keys = [
        (r["ticker"], int(r["fiscal_year_t"]), int(r["target_year"]))
        for r in requests_rows
    ]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------- #
# Fail-closed behaviour
# --------------------------------------------------------------------------- #

def test_build_fails_closed_on_a_final_test_pair(monkeypatch):
    poisoned = [{
        "ticker": "X", "fiscal_year_t": "1399", "target_year": 1400,
        "predictor_row_key_t": "X|1399", "folds": ["fold1_train"],
        "pair_cutoff_date": "2021-05-01", "target": "0",
    }]
    monkeypatch.setattr(gate, "load_development_pairs", lambda _root: poisoned)
    with pytest.raises(gate.GateFail):
        ext.build_pair_requests(REPO_ROOT)


def test_build_fails_closed_on_a_missing_cutoff(monkeypatch):
    poisoned = [{
        "ticker": "X", "fiscal_year_t": "1396", "target_year": 1397,
        "predictor_row_key_t": "X|1396", "folds": ["fold1_train"],
        "pair_cutoff_date": "", "target": "0",
    }]
    monkeypatch.setattr(gate, "load_development_pairs", lambda _root: poisoned)
    with pytest.raises(gate.GateFail):
        ext.build_pair_requests(REPO_ROOT)


# --------------------------------------------------------------------------- #
# ZIP contains only what the external programmer needs
# --------------------------------------------------------------------------- #

def test_zip_contains_exactly_the_package_files():
    import zipfile
    zip_path = os.path.join(EXT_DIR, ext.ZIP_NAME)
    assert os.path.isfile(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        assert sorted(zf.namelist()) == sorted(ext.PACKAGE_FILES)


def test_zip_carries_no_internal_repository_file():
    import zipfile
    with zipfile.ZipFile(os.path.join(EXT_DIR, ext.ZIP_NAME)) as zf:
        for name in zf.namelist():
            assert not name.startswith("project/")
            assert "stage125" not in name
            assert "stage126" not in name
            assert "analysis_ready" not in name
