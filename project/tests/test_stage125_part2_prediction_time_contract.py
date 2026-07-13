"""Tests for Stage125 Part 2 — Prediction-time & Leakage Contract.

All tests are read-only: they never modify the canonical repository files.
The canonical-repository-unchanged fixture (session-scoped, autouse) in
``test_canonical_repository_immutable.py`` guards against any accidental write.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part2_prediction_time_contract as part2  # noqa: E402

ALL_ROWS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_all_rows_stage124_gate_b.csv"
PAIRS_PATH = ROOT / "stage124" / "gate_b_final" / "modeling_one_year_ahead_stage124_gate_b.csv"
OUTPUT_DIR = ROOT / "stage125"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _build():
    return part2.build_all(REPO_ROOT, ALL_ROWS_PATH, PAIRS_PATH)


def _check_files(result):
    files = result["files"]
    for name, content in files.items():
        disk = OUTPUT_DIR / name
        assert disk.is_file(), f"missing output: {name}"
        on_disk = disk.read_text(encoding="utf-8")
        assert on_disk == content, f"drift in {name}"


def _read_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


# --------------------------------------------------------------------------- #
# Input verification
# --------------------------------------------------------------------------- #

def test_input_files_exist():
    assert ALL_ROWS_PATH.is_file(), f"missing {ALL_ROWS_PATH}"
    assert PAIRS_PATH.is_file(), f"missing {PAIRS_PATH}"


def test_input_sha256_verified():
    import hashlib
    sha_all = hashlib.sha256(ALL_ROWS_PATH.read_bytes()).hexdigest()
    sha_pairs = hashlib.sha256(PAIRS_PATH.read_bytes()).hexdigest()
    assert sha_all == part2.EXPECTED_INPUT_ALL_ROWS_SHA256
    assert sha_pairs == part2.EXPECTED_INPUT_PAIRS_SHA256


def test_load_inputs_returns_correct_data():
    df_all, df_pairs, sha_all, sha_pairs = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    assert len(df_all) == 1331
    assert len(df_pairs) == 1200
    assert sha_all == part2.EXPECTED_INPUT_ALL_ROWS_SHA256
    assert sha_pairs == part2.EXPECTED_INPUT_PAIRS_SHA256


def test_load_inputs_fail_closed_on_missing():
    with pytest.raises(part2.QCFail):
        part2.load_inputs(None, PAIRS_PATH)
    with pytest.raises(part2.QCFail):
        part2.load_inputs(ALL_ROWS_PATH, None)


def test_load_inputs_fail_closed_on_bad_hash(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("not the right content\n")
    with pytest.raises(part2.QCFail):
        part2.load_inputs(bad, PAIRS_PATH)
    with pytest.raises(part2.QCFail):
        part2.load_inputs(ALL_ROWS_PATH, bad)


# --------------------------------------------------------------------------- #
# Invariants
# --------------------------------------------------------------------------- #

def test_invariants_match():
    result = _build()
    counts = result["counts"]
    errs = part2.check_invariants(counts)
    assert errs == [], "; ".join(errs)


def test_invariants_exact_values():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    counts = part2.compute_invariants(df_all, df_pairs)
    assert counts["all_rows"] == 1331
    assert counts["unique_row_key_all_rows"] == 1331
    assert counts["pairs"] == 1200
    assert counts["unique_predictor_row_key_t"] == 1200
    assert counts["unique_target_row_key_t_plus_1"] == 1200
    assert counts["unique_tickers_pairs"] == 130
    assert counts["target_year_equals_fiscal_year_t_plus_1"] == 1200
    assert counts["predictor_keys_in_all_rows"] == 1200
    assert counts["target_keys_in_all_rows"] == 1200
    assert counts["fiscal_year_end_t_present"] == 1196
    assert counts["fiscal_year_end_t_missing"] == 4
    assert counts["fiscal_year_end_t_plus_1_present"] == 1196
    assert counts["fiscal_year_end_t_plus_1_missing"] == 4
    assert counts["pairs_either_date_missing"] == 5
    assert counts["pairs_both_dates_missing"] == 3
    assert counts["pairs_both_dates_present"] == 1195


# --------------------------------------------------------------------------- #
# Prediction-time contract
# --------------------------------------------------------------------------- #

def test_prediction_time_contract_structure():
    contract = part2.build_prediction_time_contract()
    assert contract["contract_version"] == "stage125_part2_v1"
    assert contract["stage"] == "Stage125"
    assert "prediction_cutoff" in contract
    assert contract["prediction_cutoff"]["cutoff_basis"] == "verified_available_at_timestamp"
    assert "revision_policy" in contract
    assert contract["revision_policy"]["rule"] == "revision_is_new_version_not_overwrite"
    assert "tie_breaking" in contract
    assert contract["tie_breaking"]["rule"] == "earliest_verified_available_at"
    assert contract["eligibility_rules"]["no_eligibility_changed"] is True
    assert contract["eligibility_rules"]["no_pair_dropped"] is True
    assert contract["eligibility_rules"]["eligibility_impact"] == "none_contract_audit_only"


def test_prediction_time_contract_identifiers_not_redefined():
    contract = part2.build_prediction_time_contract()
    assert contract["identifier_rules"]["predictor_row_key_t"]["redefined"] is False
    assert contract["identifier_rules"]["target_row_key_t_plus_1"]["redefined"] is False


def test_prediction_time_contract_calendar_rules():
    contract = part2.build_prediction_time_contract()
    assert contract["calendar_rules"]["jalali_and_gregorian_preserved_separately"] is True
    assert contract["calendar_rules"]["fiscal_year_end_not_inferred_when_missing"] is True


# --------------------------------------------------------------------------- #
# Feature availability contract
# --------------------------------------------------------------------------- #

def test_feature_availability_contract_blocks():
    fc = part2.build_feature_availability_contract()
    assert "M1_financial" in fc["blocks"]
    assert "M2_market" in fc["blocks"]
    assert "M3_macro" in fc["blocks"]
    assert "M4_audit_governance" in fc["blocks"]
    for block_name, block in fc["blocks"].items():
        assert "available_when" in block
        assert "unavailable_when" in block
        assert "target_leakage_rule" in block
        assert "temporal_gating" in block


def test_feature_availability_global_rules():
    fc = part2.build_feature_availability_contract()
    assert fc["global_rules"]["no_feature_from_target_year"] is True
    assert fc["global_rules"]["no_feature_from_future_period"] is True
    assert fc["global_rules"]["no_feature_without_verified_available_at"] is True
    assert fc["global_rules"]["missing_available_at_means_unavailable"] is True
    assert fc["global_rules"]["no_imputation_of_availability"] is True


# --------------------------------------------------------------------------- #
# Leakage checklist
# --------------------------------------------------------------------------- #

def test_leakage_checklist_has_8_checks():
    cl = part2.build_leakage_checklist()
    assert len(cl["checks"]) == 8
    ids = [c["id"] for c in cl["checks"]]
    assert ids == [f"LC0{i}" for i in range(1, 9)]


def test_leakage_checklist_all_machine_testable():
    cl = part2.build_leakage_checklist()
    for c in cl["checks"]:
        assert c["machine_testable"] is True
        assert c["fail_closed"] is True


# --------------------------------------------------------------------------- #
# Cutoff audit
# --------------------------------------------------------------------------- #

def test_cutoff_audit_all_1200_pairs():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    assert len(rows) == 1200


def test_cutoff_audit_no_pair_dropped():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    assert len(rows) == 1200


def test_cutoff_audit_both_dates_present_1195():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    both = sum(1 for r in rows if r["both_dates_present"] == 1)
    assert both == 1195


def test_cutoff_audit_either_missing_5():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    either = sum(1 for r in rows if r["either_date_missing"] == 1)
    assert either == 5


def test_cutoff_audit_both_missing_3():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    both_miss = sum(1 for r in rows if r["both_dates_missing"] == 1)
    assert both_miss == 3


def test_cutoff_audit_unresolvable_5():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    unresolvable = sum(1 for r in rows if r["temporal_status"].startswith("unresolvable"))
    assert unresolvable == 5


def test_cutoff_audit_both_missing_temporal_status():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    both_miss = [r for r in rows if r["both_dates_missing"] == 1]
    assert len(both_miss) == 3
    for r in both_miss:
        assert r["temporal_status"] == "unresolvable_both_dates_missing"


def test_cutoff_audit_one_missing_temporal_status():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    one_miss = [r for r in rows
                if r["temporal_status"] == "unresolvable_one_date_missing"]
    assert len(one_miss) == 2


def test_cutoff_audit_resolvable_1195():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    resolvable = [r for r in rows
                  if r["temporal_status"] == "resolvable_pending_available_at"]
    assert len(resolvable) == 1195


def test_cutoff_audit_no_eligibility_changed():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["eligibility_impact"] == "none_contract_audit_only"


def test_cutoff_audit_missing_fye_not_filled():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    missing_t = [r for r in rows if r["fiscal_year_end_t_present"] == 0]
    for r in missing_t:
        assert r["fiscal_year_end_t"] == ""


def test_cutoff_audit_fye_t1_missing_not_filled():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_cutoff_audit_rows(df_all, df_pairs)
    missing_t1 = [r for r in rows if r["fiscal_year_end_t_plus_1_present"] == 0]
    for r in missing_t1:
        assert r["fiscal_year_end_t_plus_1"] == ""


# --------------------------------------------------------------------------- #
# Cutoff summary
# --------------------------------------------------------------------------- #

def test_cutoff_summary_values():
    result = _build()
    counts = result["counts"]
    summary = part2.build_cutoff_summary(counts)
    assert summary["total_pairs"] == 1200
    assert summary["pairs_both_dates_present"] == 1195
    assert summary["pairs_either_date_missing"] == 5
    assert summary["pairs_both_dates_missing"] == 3
    assert summary["no_pair_dropped"] is True
    assert summary["no_fiscal_year_end_filled_or_guessed"] is True
    assert summary["eligibility_impact"] == "none_contract_audit_only"
    assert summary["temporal_status_breakdown"]["resolvable_pending_available_at"] == 1195
    assert summary["temporal_status_breakdown"]["unresolvable_one_date_missing"] == 2
    assert summary["temporal_status_breakdown"]["unresolvable_both_dates_missing"] == 3


# --------------------------------------------------------------------------- #
# Feature audit
# --------------------------------------------------------------------------- #

def test_feature_audit_all_1200_pairs():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_feature_audit_rows(df_all, df_pairs)
    assert len(rows) == 1200


def test_feature_audit_no_feature_available():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_feature_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["M1_financial_available"] == 0
        assert r["M2_market_available"] == 0
        assert r["M3_macro_available"] == 0
        assert r["M4_audit_governance_available"] == 0
        assert r["any_feature_available"] == 0


def test_feature_audit_no_eligibility_changed():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_feature_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["eligibility_impact"] == "none_contract_audit_only"


# --------------------------------------------------------------------------- #
# Leakage audit
# --------------------------------------------------------------------------- #

def test_leakage_audit_all_1200_pairs():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_leakage_audit_rows(df_all, df_pairs)
    assert len(rows) == 1200


def test_leakage_audit_lc01_through_lc07_pass():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_leakage_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["LC01_no_target_year_feature"] == 1
        assert r["LC02_no_future_period_data"] == 1
        assert r["LC03_no_unverified_available_at"] == 1
        assert r["LC04_no_inferred_cutoff"] == 1
        assert r["LC05_no_revision_used_as_original"] == 1
        assert r["LC06_no_eligibility_changed"] == 1
        assert r["LC07_no_pair_dropped"] == 1


def test_leakage_audit_lc08_only_for_missing_fye():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_leakage_audit_rows(df_all, df_pairs)
    lc08_count = sum(1 for r in rows if r["LC08_missing_fye_not_filled"] == 1)
    assert lc08_count == 4


def test_leakage_audit_no_other_leakage_flags():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_leakage_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["leakage_flag_count"] == 0 or \
            r["leakage_flags"] == "LC08_missing_fye_not_filled"


def test_leakage_audit_no_eligibility_changed():
    df_all, df_pairs, _, _ = part2.load_inputs(ALL_ROWS_PATH, PAIRS_PATH)
    rows = part2.build_leakage_audit_rows(df_all, df_pairs)
    for r in rows:
        assert r["eligibility_impact"] == "none_contract_audit_only"


# --------------------------------------------------------------------------- #
# QC report
# --------------------------------------------------------------------------- #

def test_qc_all_pass():
    result = _build()
    qc = result["qc"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0


def test_qc_assertion_count():
    result = _build()
    qc = result["qc"]
    assert qc["assertion_count"] >= 20


def test_qc_modeling_not_started():
    result = _build()
    qc = result["qc"]
    assert qc["modeling_started"] is False


def test_qc_part2_started():
    result = _build()
    qc = result["qc"]
    assert qc["part2_started"] is True


def test_qc_no_network_extraction():
    result = _build()
    qc = result["qc"]
    assert qc["network_extraction_performed"] is False


def test_qc_frozen_assets_unchanged():
    result = _build()
    qc = result["qc"]
    assert qc["frozen_assets_before"] == qc["frozen_assets_after"]
    assert len(qc["frozen_assets_before"]) > 0


# --------------------------------------------------------------------------- #
# Metadata manifest
# --------------------------------------------------------------------------- #

def test_metadata_structure():
    result = _build()
    files = result["files"]
    meta = json.loads(files[part2.F_METADATA])
    assert meta["stage"] == part2.QC_STAGE
    assert meta["modeling_started"] is False
    assert meta["part2_started"] is True
    assert meta["network_extraction_performed"] is False
    assert part2.F_QC in meta["output_files_sha256"]
    for fname in part2.CONTENT_FILES:
        assert fname in meta["output_files_sha256"]


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def test_determinism():
    r1 = _build()
    r2 = _build()
    assert r1["files"] == r2["files"]


# --------------------------------------------------------------------------- #
# Output file presence
# --------------------------------------------------------------------------- #

def test_all_output_files_present():
    result = _build()
    files = result["files"]
    expected = set(part2.CONTENT_FILES) | {part2.F_QC, part2.F_METADATA}
    assert set(files.keys()) == expected


# --------------------------------------------------------------------------- #
# Runner (--check mode)
# --------------------------------------------------------------------------- #

def test_runner_check_no_drift():
    result = part2.run(project_dir=ROOT, all_rows_path=ALL_ROWS_PATH,
                       pairs_path=PAIRS_PATH, output_dir=OUTPUT_DIR,
                       write=False)
    assert result["drift"] == []


def test_runner_check_reports_drift(tmp_path):
    result = part2.run(project_dir=ROOT, all_rows_path=ALL_ROWS_PATH,
                       pairs_path=PAIRS_PATH, output_dir=tmp_path,
                       write=False)
    assert len(result["drift"]) > 0
