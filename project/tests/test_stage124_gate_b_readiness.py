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
 10. Target-year distribution correctness (sum n == eligible, sum pos == positive, etc.).
 11. Metadata self-hash is NOT present in output_files_sha256.
 12. All SHA-256 in output_files_sha256 match actual files.
 13. Full-run idempotence: two consecutive runs produce byte-identical tracked files.
 14. Disagreement rows CSV exists and has required columns.
 15. Hash report uses explicit fields (authoritative_csv_all_match, etc.).
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


@pytest.fixture(scope="session")
def metadata_json():
    with open(ROOT / "stage124" / "gate_b_readiness" / "metadata_and_hashes_gate_b_readiness.json",
              encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1. No changes to Stage122/123 or listing master
# --------------------------------------------------------------------------- #

CANONICAL_FILES = (
    "project/stage124/listing_master_verified_stage124.csv",
    "project/stage123/modeling_all_rows_stage123.csv",
    "project/stage123/modeling_one_year_ahead_stage123.csv",
    "project/stage122/modeling_all_rows_stage122.csv",
    "project/stage122/modeling_one_year_ahead_stage122.csv",
    "project/src/stage122.py",
    "project/src/stage123.py",
)


def _tracked_canonical_shas() -> dict[str, str]:
    out = {}
    for rel in CANONICAL_FILES:
        p = REPO_ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_stage122_123_listing_master_unchanged():
    """Stage122/123 source and listing master must not be modified."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    modified = [l[3:].strip() for l in result.stdout.splitlines()
                if l.startswith((" M", "M ", " D", "D "))]
    for path in modified:
        if path in CANONICAL_FILES:
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
    assert run_result["hash_report"]["authoritative_csv_all_match"]


def test_hash_report_explicit_fields(run_result):
    """Hash report must use explicit fields, not ambiguous all_match."""
    hr = run_result["hash_report"]
    assert "authoritative_csv_all_match" in hr
    assert hr["authoritative_csv_all_match"] is True
    assert hr["authoritative_csv_verified_count"] == 2
    assert "workbook_match" in hr
    assert hr["workbook_nonblocking"] is True
    assert hr["workbook_used_in_analysis"] is False


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
    "gate_b_rule_disagreement_rows.csv",
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
        "fiscal_year_start",
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


def test_qc_hash_verification_detail(qc_report):
    """QC assertion for hash_verification must not say '3 files verified'."""
    for a in qc_report["assertions"]:
        if a["assertion"] == "hash_verification":
            assert "3 files verified" not in a["detail"]
            assert "authoritative" in a["detail"].lower()
            break
    else:
        pytest.fail("hash_verification assertion not found")


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
# 10. Target-year distribution correctness
# --------------------------------------------------------------------------- #

def test_target_year_distribution_sums(summary_json):
    """For each rule: sum(n by target year) == eligible_pairs,
    sum(pos by target year) == positive_pairs,
    sum(neg by target year) == negative_pairs.
    """
    for rule_name in ("rule_a", "rule_b", "rule_c"):
        rule = summary_json["rules"][rule_name]
        dist = rule["pos_neg_by_target_year_t_plus_1"]
        total_n = sum(v["n"] for v in dist.values())
        total_pos = sum(v["pos"] for v in dist.values())
        total_neg = sum(v["neg"] for v in dist.values())
        assert total_n == rule["eligible_pairs"], \
            f"{rule_name}: sum(n by target year)={total_n} != eligible_pairs={rule['eligible_pairs']}"
        assert total_pos == rule["positive_pairs"], \
            f"{rule_name}: sum(pos by target year)={total_pos} != positive_pairs={rule['positive_pairs']}"
        assert total_neg == rule["negative_pairs"], \
            f"{rule_name}: sum(neg by target year)={total_neg} != negative_pairs={rule['negative_pairs']}"


def test_target_year_range_covered(summary_json):
    """Target year distribution should cover years 1393-1402."""
    for rule_name in ("rule_a", "rule_b", "rule_c"):
        dist = summary_json["rules"][rule_name]["pos_neg_by_target_year_t_plus_1"]
        for y in range(1393, 1403):
            assert str(y) in dist, \
                f"{rule_name}: target year {y} missing from distribution"


def test_predictor_year_distribution_present(summary_json):
    """Each rule should also have pos_neg_by_predictor_year_t."""
    for rule_name in ("rule_a", "rule_b", "rule_c"):
        assert "pos_neg_by_predictor_year_t" in summary_json["rules"][rule_name]


def test_baseline_has_both_distributions(summary_json):
    bl = summary_json["stage123_baseline"]
    assert "pos_neg_by_predictor_year_t" in bl
    assert "pos_neg_by_target_year_t_plus_1" in bl


# --------------------------------------------------------------------------- #
# 11. Metadata self-hash NOT in output_files_sha256
# --------------------------------------------------------------------------- #

def test_metadata_self_hash_absent(metadata_json):
    """metadata_and_hashes_gate_b_readiness.json must NOT be in output_files_sha256."""
    assert "metadata_and_hashes_gate_b_readiness.json" not in \
        metadata_json["output_files_sha256"]


# --------------------------------------------------------------------------- #
# 12. All SHA-256 in output_files_sha256 match actual files
# --------------------------------------------------------------------------- #

def test_output_hashes_match_files(metadata_json):
    """Every file listed in output_files_sha256 must exist and match its hash."""
    out_dir = ROOT / "stage124" / "gate_b_readiness"
    hashes = metadata_json["output_files_sha256"]
    assert len(hashes) > 0, "output_files_sha256 must not be empty"
    for fname, expected_hash in hashes.items():
        assert expected_hash is not None, f"{fname}: hash is None"
        fpath = out_dir / fname
        assert fpath.is_file(), f"{fname}: file not found"
        actual = gate_b.sha256_file(fpath)
        assert actual == expected_hash, \
            f"{fname}: hash mismatch (expected {expected_hash}, got {actual})"


# --------------------------------------------------------------------------- #
# 13. Full-run idempotence
# --------------------------------------------------------------------------- #

def test_full_run_idempotence():
    """Baseline committed outputs == run1 == run2 (byte-identical tracked files)."""
    out_dir = ROOT / "stage124" / "gate_b_readiness"
    tracked_outputs = [
        "gate_b_rule_comparison_summary.json",
        "gate_b_pair_impact_summary.csv",
        "gate_b_unmatched_or_ambiguous_rows.csv",
        "gate_b_rule_disagreement_rows.csv",
        "gate_b_readiness_qc_report.json",
        "metadata_and_hashes_gate_b_readiness.json",
        "README_GATE_B_READINESS.md",
    ]

    # Baseline: committed (on-disk) hashes before any run
    hashes_0 = {}
    for fname in tracked_outputs:
        fpath = out_dir / fname
        if fpath.is_file():
            hashes_0[fname] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    # First run
    gate_b.run(ROOT)
    hashes_1 = {}
    for fname in tracked_outputs:
        fpath = out_dir / fname
        if fpath.is_file():
            hashes_1[fname] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    # Second run
    gate_b.run(ROOT)
    hashes_2 = {}
    for fname in tracked_outputs:
        fpath = out_dir / fname
        if fpath.is_file():
            hashes_2[fname] = hashlib.sha256(fpath.read_bytes()).hexdigest()

    for fname in tracked_outputs:
        assert fname in hashes_0, f"{fname}: missing at baseline"
        assert fname in hashes_1, f"{fname}: missing after run 1"
        assert fname in hashes_2, f"{fname}: missing after run 2"
        assert hashes_0[fname] == hashes_1[fname], \
            f"{fname}: baseline != run1 (idempotence violation)"
        assert hashes_1[fname] == hashes_2[fname], \
            f"{fname}: run1 != run2 (idempotence violation)"


# --------------------------------------------------------------------------- #
# 14. Disagreement rows CSV
# --------------------------------------------------------------------------- #

def test_disagreement_rows_csv_exists():
    path = ROOT / "stage124" / "gate_b_readiness" / "gate_b_rule_disagreement_rows.csv"
    assert path.is_file(), "gate_b_rule_disagreement_rows.csv missing"


def test_disagreement_rows_columns():
    path = ROOT / "stage124" / "gate_b_readiness" / "gate_b_rule_disagreement_rows.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = {
        "row_key", "ticker", "fiscal_year", "fiscal_year_end",
        "fiscal_year_start", "first_public_trading_date_jalali",
        "eligible_rule_a", "eligible_rule_b", "eligible_rule_c",
        "exclusion_reason_rule_a", "exclusion_reason_rule_b",
        "exclusion_reason_rule_c",
        "FD_target_main_t_plus_1",
        "pair_eligible_rule_a", "pair_eligible_rule_b",
        "pair_eligible_rule_c",
    }
    assert required.issubset(set(df.columns)), \
        f"Missing columns: {required - set(df.columns)}"


def test_disagreement_rows_count(summary_json):
    """Disagreement CSV should contain rows where A and B differ."""
    path = ROOT / "stage124" / "gate_b_readiness" / "gate_b_rule_disagreement_rows.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    ab_count = summary_json["rows_differing_between_a_and_b"]["count"]
    assert len(df) >= ab_count, \
        f"Disagreement CSV has {len(df)} rows, expected >= {ab_count} (A/B disagreements)"


# --------------------------------------------------------------------------- #
# 15. Rule consistency checks
# --------------------------------------------------------------------------- #

def test_rule_b_stricter_than_rule_a(audit_df):
    """Rule B (fy_start) should be at least as strict as Rule A (fy_end)."""
    for i in audit_df.index:
        a = audit_df.at[i, "eligible_rule_a"]
        b = audit_df.at[i, "eligible_rule_b"]
        if b == 1:
            assert a == 1, \
                f"Rule B eligible but Rule A not: {audit_df.at[i, 'row_key']}"


def test_rule_c_similar_to_rule_b(audit_df):
    """Rule C (year-level) should be close to Rule B (start-of-year)."""
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
