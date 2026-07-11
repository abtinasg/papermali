"""Independent tests for Stage124 Gate B Readiness dry-run.

Run: pytest -q tests/test_stage124_gate_b_readiness.py

These tests verify:
  1. Stage122/Stage123/listing master are not modified by the readiness script.
  2. Input file hashes match Stage123 metadata (CSV files, fail-closed).
  3. Schema and key validations pass (1331 rows, 130 tickers, unique row_key).
  4. Rule determinism: same inputs -> same outputs.
  5. No modeling started, no Gate B finalized, no canonical dataset produced.
  6. fiscal_year_start computation correctness (leap year, non-leap, non-12m).
  7. Date semantics declared correctly.
  8. No rows dropped, no missing values zeroed.
  9. Output files exist and have expected columns.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage124_gate_b_readiness as gate_b  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def run_result():
    """Run the full Gate B readiness dry-run once for the session."""
    return gate_b.run(ROOT)


@pytest.fixture(scope="session")
def audit_df():
    return pd.read_csv(
        ROOT / "stage124" / "gate_b_readiness" / "gate_b_company_year_audit.csv",
        encoding="utf-8-sig",
    )


@pytest.fixture(scope="session")
def summary_json():
    with open(ROOT / "stage124" / "gate_b_readiness" / "gate_b_rule_comparison_summary.json",
              encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def qc_report():
    with open(ROOT / "stage124" / "gate_b_readiness" / "gate_b_readiness_qc_report.json",
              encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1. No changes to Stage122/123 or listing master
# --------------------------------------------------------------------------- #

CANONICAL_PREFIXES = (
    "project/stage124/listing_master_verified_stage124.csv",
    "project/stage123/",
    "project/stage122/",
    "project/src/stage122.py",
    "project/src/stage123.py",
)


def _tracked_canonical_shas() -> dict[str, str]:
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", *CANONICAL_PREFIXES],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    out = {}
    for rel in listed:
        p = REPO_ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_stage122_123_listing_master_unchanged():
    """Stage122/123 source and listing master must not be modified."""
    # This test runs after the session fixture (run_result) has executed.
    # We verify by checking git status for modifications to canonical files.
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    modified = [l[3:].strip() for l in result.stdout.splitlines()
                if l.startswith((" M", "M ", " D", "D "))]
    for path in modified:
        for prefix in CANONICAL_PREFIXES:
            if path.startswith(prefix):
                pytest.fail(f"Canonical file modified: {path}")


# --------------------------------------------------------------------------- #
# 2. Input file hashes match Stage123 metadata
# --------------------------------------------------------------------------- #

def test_csv_hashes_match_metadata(run_result):
    hash_report = run_result["hash_report"]
    csv_files = [
        f for f, info in hash_report["files"].items()
        if info.get("fail_closed")
    ]
    for fname in csv_files:
        assert hash_report["files"][fname]["match"], \
            f"{fname} hash mismatch"


def test_csv_hash_verification_passes(run_result):
    assert run_result["hash_report"]["all_match"]


# --------------------------------------------------------------------------- #
# 3. Schema and key validation
# --------------------------------------------------------------------------- #

def test_schema_validation_passes(run_result):
    assert run_result["schema_report"]["overall_pass"]


def test_row_count_1331(audit_df):
    assert len(audit_df) == 1331


def test_row_key_unique(audit_df):
    assert audit_df["row_key"].nunique() == len(audit_df)


def test_130_tickers(audit_df):
    assert audit_df["ticker"].nunique() == 130


# --------------------------------------------------------------------------- #
# 4. Rule determinism
# --------------------------------------------------------------------------- #

def test_rule_determinism():
    """Running the computation twice produces identical audit DataFrames."""
    all_rows = pd.read_csv(
        ROOT / "stage123" / "modeling_all_rows_stage123.csv",
        encoding="utf-8-sig",
    )
    listing_master = pd.read_csv(
        ROOT / "stage124" / "listing_master_verified_stage124.csv",
        encoding="utf-8-sig",
    )
    audit1, _ = gate_b.compute_rules(all_rows, listing_master)
    audit2, _ = gate_b.compute_rules(all_rows, listing_master)
    pd.testing.assert_frame_equal(audit1, audit2)


# --------------------------------------------------------------------------- #
# 5. No modeling / Gate B / canonical dataset
# --------------------------------------------------------------------------- #

def test_no_modeling_started():
    assert not (ROOT / "outputs" / "stage_modeling" / "run_manifest.json").is_file()


def test_no_gate_b_finalized():
    assert not (ROOT / "stage124" / "stage124_batch02_gate_b_qc_report.json").is_file()
    assert not (ROOT / "stage124" / "metadata_and_hashes_stage124_batch02_gate_b.json").is_file()


def test_no_new_canonical_dataset():
    """No new canonical modeling CSV should exist from this dry-run."""
    out_dir = ROOT / "stage124" / "gate_b_readiness"
    if out_dir.is_dir():
        files = [f.name for f in out_dir.iterdir() if f.is_file()]
        for f in files:
            assert "modeling_all_rows" not in f
            assert "modeling_one_year_ahead" not in f


# --------------------------------------------------------------------------- #
# 6. fiscal_year_start computation
# --------------------------------------------------------------------------- #

def test_fy_start_standard_month():
    """fy_end = 1396/10/30 -> fy_start = 1395/11/01"""
    import jdatetime
    result = gate_b.compute_fiscal_year_start("1396/10/30", 0)
    assert result is not None
    assert result.year == 1395
    assert result.month == 11
    assert result.day == 1


def test_fy_start_leap_year_esfand_30():
    """fy_end = 1399/12/30 (leap year) -> fy_start = 1399/01/01"""
    import jdatetime
    result = gate_b.compute_fiscal_year_start("1399/12/30", 0)
    assert result is not None
    assert result.year == 1399
    assert result.month == 1
    assert result.day == 1


def test_fy_start_non_leap_year_esfand_29():
    """fy_end = 1392/12/29 (non-leap) -> fy_start = 1392/01/01"""
    import jdatetime
    result = gate_b.compute_fiscal_year_start("1392/12/29", 0)
    assert result is not None
    assert result.year == 1392
    assert result.month == 1
    assert result.day == 1


def test_fy_start_non_12_month_returns_none():
    assert gate_b.compute_fiscal_year_start("1396/10/30", 1) is None


def test_fy_start_missing_returns_none():
    assert gate_b.compute_fiscal_year_start("", 0) is None
    assert gate_b.compute_fiscal_year_start(None, 0) is None


# --------------------------------------------------------------------------- #
# 7. Date semantics declared
# --------------------------------------------------------------------------- #

def test_date_semantics_in_summary(summary_json):
    assert summary_json["date_semantics"] == \
        "first_observed_trading_date_from_official_tse_api"


def test_date_semantics_in_audit(audit_df):
    assert (audit_df["date_semantics"] ==
            "first_observed_trading_date_from_official_tse_api").all()


def test_date_semantics_note_present(summary_json):
    assert "NOT IPO" in summary_json["date_semantics_note"]


# --------------------------------------------------------------------------- #
# 8. No rows dropped, no missing zeroed
# --------------------------------------------------------------------------- #

def test_no_rows_dropped(audit_df):
    all_rows = pd.read_csv(
        ROOT / "stage123" / "modeling_all_rows_stage123.csv",
        encoding="utf-8-sig",
    )
    assert len(audit_df) == len(all_rows)


def test_no_missing_zeroed(audit_df):
    """No row should have data_quality_status indicating zero-filling."""
    # data_quality_status should only contain: ok, missing_fiscal_year_end,
    # non_12_month_period, unmatched_ticker
    valid_statuses = {"ok", "missing_fiscal_year_end", "non_12_month_period",
                      "unmatched_ticker", "missing_fiscal_year_end | non_12_month_period"}
    for s in audit_df["data_quality_status"].unique():
        parts = set(s.split(" | "))
        for p in parts:
            assert p in {"ok", "missing_fiscal_year_end", "non_12_month_period",
                         "unmatched_ticker"}, f"Unexpected status component: {p}"


# --------------------------------------------------------------------------- #
# 9. Output file existence and columns
# --------------------------------------------------------------------------- #

EXPECTED_OUTPUTS = [
    "gate_b_rule_comparison_summary.json",
    "gate_b_company_year_audit.csv",
    "gate_b_pair_impact_summary.csv",
    "gate_b_unmatched_or_ambiguous_rows.csv",
    "gate_b_readiness_qc_report.json",
    "metadata_and_hashes_gate_b_readiness.json",
    "README_GATE_B_READINESS.md",
]


def test_output_files_exist():
    out_dir = ROOT / "stage124" / "gate_b_readiness"
    for fname in EXPECTED_OUTPUTS:
        assert (out_dir / fname).is_file(), f"Missing output: {fname}"


def test_audit_csv_columns(audit_df):
    expected = {
        "row_key", "ticker", "fiscal_year", "fiscal_year_end",
        "first_public_trading_date_jalali", "first_public_trading_date_gregorian",
        "date_semantics", "eligible_rule_a", "eligible_rule_b", "eligible_rule_c",
        "exclusion_reason_rule_a", "exclusion_reason_rule_b",
        "exclusion_reason_rule_c", "data_quality_status",
    }
    assert expected.issubset(set(audit_df.columns))


def test_qc_report_all_pass(qc_report):
    assert qc_report["all_pass"] is True
    assert qc_report["failed_count"] == 0


def test_qc_report_has_required_fields(qc_report):
    required = ("stage", "source_commit", "source_file_sha256",
                "test_file_sha256", "tickers", "all_pass",
                "assertion_count", "failed_count")
    for k in required:
        assert k in qc_report, f"Missing QC field: {k}"


def test_summary_has_three_rules(summary_json):
    for rule in ("rule_a", "rule_b", "rule_c"):
        assert rule in summary_json["rules"]
        assert "eligible_pairs" in summary_json["rules"][rule]
        assert "description" in summary_json["rules"][rule]


def test_summary_has_stage123_baseline(summary_json):
    assert "stage123_baseline" in summary_json
    assert summary_json["stage123_baseline"]["eligible_pairs"] == 1085


def test_summary_has_row_differences(summary_json):
    for pair in ("a_and_b", "a_and_c", "b_and_c"):
        key = f"rows_differing_between_{pair}"
        assert key in summary_json
        assert "count" in summary_json[key]


def test_warning_no_rule_finalized(summary_json):
    assert "No rule has been finalized" in summary_json["warning"]


def test_next_action_is_rule_approval(summary_json):
    assert summary_json["next_action"] == "stage124-gate-b-rule-approval"


# --------------------------------------------------------------------------- #
# 10. Rule consistency checks
# --------------------------------------------------------------------------- #

def test_rule_b_stricter_than_rule_a(audit_df):
    """Rule B (fy_start) should be at least as strict as Rule A (fy_end)."""
    for i in audit_df.index:
        a = audit_df.at[i, "eligible_rule_a"]
        b = audit_df.at[i, "eligible_rule_b"]
        # If Rule B says eligible (1), Rule A should also be eligible (1)
        if b == 1:
            assert a == 1, \
                f"Rule B eligible but Rule A not: {audit_df.at[i, 'row_key']}"


def test_rule_c_similar_to_rule_b(audit_df):
    """Rule C (year-level) should be close to Rule B (start-of-year)."""
    # Rule C and Rule B should agree on most rows
    differ = sum(
        1 for i in audit_df.index
        if audit_df.at[i, "eligible_rule_b"] != audit_df.at[i, "eligible_rule_c"]
    )
    assert differ < 20, f"Too many differences between Rule B and C: {differ}"


def test_unresolved_only_for_valid_reasons(audit_df):
    """Unresolved rows should only be due to missing fy_end or non-12-month."""
    for rule in ("eligible_rule_b", "eligible_rule_c"):
        rule_short = rule.replace("eligible_", "")
        unresolved = audit_df[audit_df[rule] == "unresolved"]
        for i in unresolved.index:
            reason = audit_df.at[i, f"exclusion_reason_{rule_short}"]
            assert reason in ("fiscal_year_start_unresolved",
                              "trading_date_missing",
                              "year_extraction_failed"), \
                f"Unexpected unresolved reason: {reason}"
