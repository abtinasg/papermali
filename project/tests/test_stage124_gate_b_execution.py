"""Independent tests for Stage124 Gate B execution.

Run: pytest -q project/tests/test_stage124_gate_b_execution.py

These tests recompute expectations from the authoritative inputs; they do not
hardcode outputs or weaken assertions.
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

from src import stage124_gate_b_execution as ex  # noqa: E402
from src import stage124_gate_b_readiness as rb  # noqa: E402

GATE_B_DIR = ROOT / "stage124" / "gate_b_final"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def run_result():
    return ex.run(ROOT)


@pytest.fixture(scope="session")
def company_year(run_result):
    return run_result["company_year"]


@pytest.fixture(scope="session")
def pairs_out(run_result):
    return run_result["pairs_out"]


@pytest.fixture(scope="session")
def stats(run_result):
    return run_result["stats"]


@pytest.fixture(scope="session")
def qc_report(run_result):
    with open(ROOT / "stage124" / "stage124_batch02_gate_b_qc_report.json",
              encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def metadata(run_result):
    with open(ROOT / "stage124" / "metadata_and_hashes_stage124_batch02_gate_b.json",
              encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def src_all_rows():
    return pd.read_csv(ROOT / "stage123" / "modeling_all_rows_stage123.csv",
                       encoding="utf-8-sig")


@pytest.fixture(scope="session")
def src_pairs():
    return pd.read_csv(ROOT / "stage123" / "modeling_one_year_ahead_stage123.csv",
                       encoding="utf-8-sig")


# --------------------------------------------------------------------------- #
# 1. Input SHA-256 fail-closed behavior
# --------------------------------------------------------------------------- #

def test_input_hashes_pass(run_result):
    assert run_result["verify_report"]["mismatches"] == []


def test_input_hash_fail_closed(monkeypatch):
    monkeypatch.setitem(ex.EXPECTED_INPUT_SHA256,
                        "modeling_all_rows_stage123.csv", "deadbeef")
    with pytest.raises(ex.QCFail):
        ex.verify_inputs(ROOT)


# --------------------------------------------------------------------------- #
# 2. Listing master schema and 130 ticker match
# --------------------------------------------------------------------------- #

def test_listing_master_130_tickers():
    lm = pd.read_csv(ROOT / "stage124" / "listing_master_verified_stage124.csv",
                     encoding="utf-8-sig")
    assert lm["ticker"].nunique() == 130
    assert lm["ticker"].duplicated().sum() == 0
    assert lm["first_public_trading_date_jalali"].isna().sum() == 0


def test_all_tickers_matched(company_year):
    assert company_year["ticker"].nunique() == 130


# --------------------------------------------------------------------------- #
# 3-4. Rule A / Rule B exact-date computation (checked against the definition)
# --------------------------------------------------------------------------- #

def test_rule_a_exact_date(company_year):
    lm = pd.read_csv(ROOT / "stage124" / "listing_master_verified_stage124.csv",
                     encoding="utf-8-sig")
    tdate = lm.set_index("ticker")["first_public_trading_date_jalali"].to_dict()
    checked = 0
    for _, r in company_year.iterrows():
        val = r["eligible_listing_gate_b_primary"]
        if val == "unresolved":
            continue
        ftd = rb.parse_jalali_date(str(tdate[r["ticker"]]))
        fye = rb.parse_jalali_date(str(r["fiscal_year_end"]))
        if ftd is None or fye is None:
            continue
        expected = 1 if ftd <= fye else 0
        assert int(val) == expected, r["row_key"]
        checked += 1
    assert checked > 1000


def test_rule_b_exact_date(company_year):
    lm = pd.read_csv(ROOT / "stage124" / "listing_master_verified_stage124.csv",
                     encoding="utf-8-sig")
    tdate = lm.set_index("ticker")["first_public_trading_date_jalali"].to_dict()
    checked = 0
    for _, r in company_year.iterrows():
        val = r["eligible_listing_gate_b_robustness"]
        if val == "unresolved":
            continue
        fys = rb.parse_jalali_date(str(r["fiscal_year_start_gate_b"]))
        ftd = rb.parse_jalali_date(str(tdate[r["ticker"]]))
        assert fys is not None and ftd is not None
        expected = 1 if ftd <= fys else 0
        assert int(val) == expected, r["row_key"]
        checked += 1
    assert checked > 1000


# --------------------------------------------------------------------------- #
# 5. Jalali Esfand leap-year handling
# --------------------------------------------------------------------------- #

def test_fy_start_leap_esfand_30():
    result = rb.compute_fiscal_year_start("1399/12/30", 0)
    assert (result.year, result.month, result.day) == (1399, 1, 1)


def test_fy_start_non_leap_esfand_29():
    result = rb.compute_fiscal_year_start("1392/12/29", 0)
    assert (result.year, result.month, result.day) == (1392, 1, 1)


def test_fy_start_mid_year_month():
    result = rb.compute_fiscal_year_start("1396/10/30", 0)
    assert (result.year, result.month, result.day) == (1395, 11, 1)


# --------------------------------------------------------------------------- #
# 6-7. Unresolved handling
# --------------------------------------------------------------------------- #

def test_non_12_month_unresolved():
    assert rb.compute_fiscal_year_start("1396/10/30", 1) is None


def test_missing_fy_end_unresolved():
    assert rb.compute_fiscal_year_start("", 0) is None
    assert rb.compute_fiscal_year_start(None, 0) is None


def test_unresolved_rows_preserved(company_year):
    n_unres_b = int((company_year["eligible_listing_gate_b_robustness"] == "unresolved").sum())
    assert n_unres_b == 10
    n_unres_a = int((company_year["eligible_listing_gate_b_primary"] == "unresolved").sum())
    assert n_unres_a == 4


def test_unresolved_rows_csv_complete(company_year):
    df = pd.read_csv(GATE_B_DIR / "gate_b_unresolved_rows.csv", encoding="utf-8-sig")
    mask = ((company_year["eligible_listing_gate_b_primary"] == "unresolved")
            | (company_year["eligible_listing_gate_b_robustness"] == "unresolved"))
    assert len(df) == int(mask.sum())


# --------------------------------------------------------------------------- #
# 8-9. Main counts
# --------------------------------------------------------------------------- #

def test_main_rule_a_counts(stats):
    s = stats["main_rule_a_primary"]
    assert (s["pairs"], s["positive"], s["negative"], s["target_missing"]) == (1013, 81, 932, 0)


def test_main_rule_b_counts(stats):
    s = stats["main_rule_b_listing_robustness"]
    assert (s["pairs"], s["positive"], s["negative"], s["target_missing"]) == (994, 80, 914, 0)


# --------------------------------------------------------------------------- #
# 10. Target-year distribution sums
# --------------------------------------------------------------------------- #

def test_target_year_distribution_sums(stats):
    dist = pd.read_csv(GATE_B_DIR / "gate_b_distribution_by_target_year.csv",
                       encoding="utf-8-sig")
    assert set(dist["target_year"]) == set(range(1393, 1403))
    for design, s in stats.items():
        sub = dist[dist["sample_design"] == design]
        assert sub["n"].sum() == s["pairs"], design
        assert sub["positive"].sum() == s["positive"], design
        assert sub["negative"].sum() == s["negative"], design


# --------------------------------------------------------------------------- #
# 11. Four-design nesting invariants
# --------------------------------------------------------------------------- #

def test_nesting_invariants(pairs_out):
    def subset(a, b):
        return bool((~((pairs_out[a] == 1) & (pairs_out[b] != 1))).all())
    assert subset("pair_final_eligible_main_gate_b_robustness",
                  "pair_final_eligible_main_gate_b_primary")
    assert subset("pair_final_eligible_expanded_gate_b_robustness",
                  "pair_final_eligible_expanded_gate_b_primary")
    assert subset("pair_final_eligible_main_gate_b_primary",
                  "pair_final_eligible_expanded_gate_b_primary")
    assert subset("pair_final_eligible_main_gate_b_robustness",
                  "pair_final_eligible_expanded_gate_b_robustness")


# --------------------------------------------------------------------------- #
# 12-13. All rows / pairs preserved
# --------------------------------------------------------------------------- #

def test_all_rows_preserved(company_year, src_all_rows):
    assert len(company_year) == 1331 == len(src_all_rows)
    assert company_year["row_key"].nunique() == 1331


def test_all_pairs_preserved(pairs_out, src_pairs):
    assert len(pairs_out) == 1200 == len(src_pairs)
    assert pairs_out["predictor_row_key_t"].nunique() == 1200


def test_full_canonical_outputs_row_counts():
    cy = pd.read_csv(GATE_B_DIR / "modeling_all_rows_stage124_gate_b.csv",
                     encoding="utf-8-sig")
    pr = pd.read_csv(GATE_B_DIR / "modeling_one_year_ahead_stage124_gate_b.csv",
                     encoding="utf-8-sig")
    assert len(cy) == 1331
    assert len(pr) == 1200


# --------------------------------------------------------------------------- #
# 14-16. Immutability of upstream assets
# --------------------------------------------------------------------------- #

# Specific upstream assets Gate B execution consumes but must never write.
IMMUTABLE_FILES = (
    ROOT / "stage123" / "modeling_all_rows_stage123.csv",
    ROOT / "stage123" / "modeling_one_year_ahead_stage123.csv",
    ROOT / "stage124" / "listing_master_verified_stage124.csv",
    ROOT / "src" / "stage122.py",
    ROOT / "src" / "stage123.py",
    ROOT / "stage124" / "gate_b_readiness" / "gate_b_rule_comparison_summary.json",
    ROOT / "stage124" / "gate_b_readiness" / "metadata_and_hashes_gate_b_readiness.json",
)


def test_upstream_assets_unchanged():
    """Executing Gate B must not modify any upstream/input asset it reads."""
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in IMMUTABLE_FILES if p.is_file()}
    assert len(before) >= 5, "expected upstream assets to exist"
    ex.run(ROOT)
    for p, h in before.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == h, f"modified: {p}"


# --------------------------------------------------------------------------- #
# 17-19. No source/target/feature values changed; no missing zero-filled
# --------------------------------------------------------------------------- #

def test_source_columns_preserved(company_year, src_all_rows):
    for col in src_all_rows.columns:
        assert col in company_year.columns
        pd.testing.assert_series_equal(
            company_year[col].reset_index(drop=True),
            src_all_rows[col].reset_index(drop=True),
            check_names=False)


def test_target_values_unchanged(pairs_out, src_pairs):
    for col in ("FD_target_main_t_plus_1", "FD_target_article141_only_t_plus_1",
                "FD_target_persistent_loss_robustness_t_plus_1"):
        pd.testing.assert_series_equal(
            pairs_out[col].reset_index(drop=True),
            src_pairs[col].reset_index(drop=True), check_names=False)


def test_no_missing_zero_filled(company_year):
    # Unresolved listing must remain the string 'unresolved', never 0.
    unresolved = company_year[company_year["listing_gate_b_robustness_status"] == "unresolved"]
    assert (unresolved["eligible_listing_gate_b_robustness"] == "unresolved").all()


# --------------------------------------------------------------------------- #
# 20. Rule C absent from final canonical eligibility columns
# --------------------------------------------------------------------------- #

def test_rule_c_absent(company_year, pairs_out):
    for df in (company_year, pairs_out):
        for col in df.columns:
            low = col.lower()
            if "eligible" in low or "predictor" in low or "listing" in low:
                assert "rule_c" not in low and "_c_" not in low, col


def test_rule_c_absent_in_canonical_files():
    cy = pd.read_csv(GATE_B_DIR / "modeling_all_rows_stage124_gate_b.csv",
                     encoding="utf-8-sig", nrows=1)
    for col in cy.columns:
        assert "rule_c" not in col.lower()


# --------------------------------------------------------------------------- #
# 21. No modeling / temporal-split / SHAP / SMOTE / calibration artifacts
# --------------------------------------------------------------------------- #

def test_no_modeling_artifacts():
    assert not (ROOT / "outputs" / "stage_modeling" / "run_manifest.json").is_file()
    for name in [f.name for f in GATE_B_DIR.iterdir() if f.is_file()]:
        low = name.lower()
        for banned in ("shap", "smote", "calibrat", "temporal_split", "model_", ".joblib"):
            assert banned not in low, name


# --------------------------------------------------------------------------- #
# 22-23. Metadata hashes match; self-hash absent
# --------------------------------------------------------------------------- #

def test_metadata_output_hashes_match(metadata):
    base = ROOT / "stage124"
    for key, expected in metadata["output_files_sha256"].items():
        fpath = base / key
        assert fpath.is_file(), key
        assert ex.sha256_file(fpath) == expected, key


def test_metadata_self_hash_absent(metadata):
    assert "metadata_and_hashes_stage124_batch02_gate_b.json" not in \
        metadata["output_files_sha256"]
    for key in metadata["output_files_sha256"]:
        assert "metadata_and_hashes_stage124_batch02_gate_b" not in key


def test_metadata_has_all_inputs(metadata):
    assert set(metadata["input_files_sha256"]) == {
        "modeling_all_rows_stage123.csv", "modeling_one_year_ahead_stage123.csv"}
    assert metadata["listing_master_sha256"]
    assert metadata["readiness_summary_sha256"]
    assert metadata["rule_approval_sha256"]
    # Six large + four small + qc report all hashed.
    keys = metadata["output_files_sha256"]
    for large in ex.LARGE_OUTPUTS:
        assert f"gate_b_final/{large}" in keys
    for small in ex.SMALL_OUTPUTS:
        assert f"gate_b_final/{small}" in keys
    assert "stage124_batch02_gate_b_qc_report.json" in keys


def test_no_workbook_hash(metadata):
    blob = json.dumps(metadata)
    assert "workbook" not in blob.lower()
    assert ".xlsx" not in blob.lower()


# --------------------------------------------------------------------------- #
# 24-25. Determinism and baseline == run1 == run2
# --------------------------------------------------------------------------- #

TRACKED_OUTPUTS = [
    ("gate_b_final", "gate_b_sample_matrix.csv"),
    ("gate_b_final", "gate_b_distribution_by_target_year.csv"),
    ("gate_b_final", "gate_b_pair_change_vs_stage123.csv"),
    ("gate_b_final", "gate_b_unresolved_rows.csv"),
    ("gate_b_final", "README_STAGE124_GATE_B_EXECUTION.md"),
    (".", "stage124_batch02_gate_b_qc_report.json"),
    (".", "metadata_and_hashes_stage124_batch02_gate_b.json"),
]


def _tracked_hashes():
    out = {}
    for sub, name in TRACKED_OUTPUTS:
        p = (ROOT / "stage124" / name) if sub == "." else (ROOT / "stage124" / sub / name)
        if p.is_file():
            out[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_full_run_determinism():
    h0 = _tracked_hashes()
    ex.run(ROOT)
    h1 = _tracked_hashes()
    ex.run(ROOT)
    h2 = _tracked_hashes()
    for name in h0:
        assert h0[name] == h1[name], f"{name}: baseline != run1"
        assert h1[name] == h2[name], f"{name}: run1 != run2"


# --------------------------------------------------------------------------- #
# 26-27. Handoff markers
# --------------------------------------------------------------------------- #

def test_gate_b_started_true(qc_report, metadata):
    assert qc_report["gate_b_started"] is True
    assert metadata["gate_b_started"] is True


def test_modeling_started_false(qc_report, metadata):
    assert qc_report["modeling_started"] is False
    assert metadata["modeling_started"] is False


# --------------------------------------------------------------------------- #
# 28. Approval record matches executed rules
# --------------------------------------------------------------------------- #

def test_approval_matches_execution(stats):
    with open(GATE_B_DIR / "gate_b_rule_approval_stage124.json", encoding="utf-8") as f:
        ap = json.load(f)
    assert ap["decision_status"] == "approved"
    assert ap["modeling_authorized"] is False
    assert ap["approved_primary_expected_pairs"] == stats["main_rule_a_primary"]["pairs"]
    assert ap["approved_primary_expected_positive"] == stats["main_rule_a_primary"]["positive"]
    assert ap["approved_robustness_expected_pairs"] == stats["main_rule_b_listing_robustness"]["pairs"]
    assert ap["approved_robustness_expected_positive"] == stats["main_rule_b_listing_robustness"]["positive"]


# --------------------------------------------------------------------------- #
# 29. QC source commit points to actual code/test commit
# --------------------------------------------------------------------------- #

def test_qc_source_commit_valid(qc_report):
    src = ROOT / "src" / "stage124_gate_b_execution.py"
    test = ROOT / "tests" / "test_stage124_gate_b_execution.py"
    assert qc_report["source_file_sha256"] == ex.sha256_file(src)
    assert qc_report["test_file_sha256"] == ex.sha256_file(test)
    commit = qc_report["source_commit"]
    head = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    anc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", commit, head])
    assert commit == head or anc.returncode == 0


def test_qc_all_pass(qc_report):
    assert qc_report["all_pass"] is True
    assert qc_report["failed_count"] == 0


# --------------------------------------------------------------------------- #
# 30. Filtered datasets exactly match their corresponding pair flags
# --------------------------------------------------------------------------- #

def test_filtered_views_match_flags(pairs_out):
    mapping = {
        "modeling_main_rule_a_eligible.csv": "pair_final_eligible_main_gate_b_primary",
        "modeling_main_rule_b_eligible.csv": "pair_final_eligible_main_gate_b_robustness",
        "modeling_expanded_rule_a_eligible.csv": "pair_final_eligible_expanded_gate_b_primary",
        "modeling_expanded_rule_b_eligible.csv": "pair_final_eligible_expanded_gate_b_robustness",
    }
    for fname, flag in mapping.items():
        df = pd.read_csv(GATE_B_DIR / fname, encoding="utf-8-sig")
        expected = int((pairs_out[flag] == 1).sum())
        assert len(df) == expected, fname
        assert (df[flag] == 1).all(), fname
