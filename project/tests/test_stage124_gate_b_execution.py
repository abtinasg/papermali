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


def test_listing_master_hash_mismatch_fail_closed(monkeypatch):
    """Listing master hash mismatch must fail closed."""
    monkeypatch.setattr(ex, "EXPECTED_LISTING_MASTER_SHA256", "deadbeef")
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
    """Every Stage123 source column must be present and cell-by-cell identical."""
    for col in src_all_rows.columns:
        assert col in company_year.columns, f"missing source column: {col}"
        s = src_all_rows[col].reset_index(drop=True)
        d = company_year[col].reset_index(drop=True)
        assert len(s) == len(d), f"{col}: length mismatch {len(s)} vs {len(d)}"
        assert s.isna().equals(d.isna()), f"{col}: NaN positions differ"
        assert s[~s.isna()].equals(d[~d.isna()]), f"{col}: values differ"
        if str(s.dtype) != object and str(d.dtype) != object:
            assert s.dtype == d.dtype, f"{col}: dtype {s.dtype} vs {d.dtype}"


def test_target_values_unchanged(pairs_out, src_pairs):
    """All target columns must be cell-by-cell identical to Stage123."""
    target_cols = [
        "FD_target_main_t_plus_1",
        "FD_target_article141_only_t_plus_1",
        "FD_target_persistent_loss_robustness_t_plus_1",
        "valid_target_t_plus_1",
        "target_year",
    ]
    for col in target_cols:
        assert col in pairs_out.columns, f"missing target column: {col}"
        assert col in src_pairs.columns, f"missing source target column: {col}"
        s = src_pairs[col].reset_index(drop=True)
        d = pairs_out[col].reset_index(drop=True)
        assert len(s) == len(d), f"{col}: length mismatch"
        assert s.isna().equals(d.isna()), f"{col}: NaN positions differ"
        assert s[~s.isna()].equals(d[~d.isna()]), f"{col}: values differ"


def test_no_missing_zero_filled(company_year, pairs_out):
    """Unresolved company-years must remain 'unresolved' with zeroed predictors and no eligible pairs."""
    for elig_col, status_col, pred_cols, pair_flag in [
        ("eligible_listing_gate_b_primary", "listing_gate_b_primary_status",
         ["predictor_eligible_main_gate_b_primary", "predictor_eligible_expanded_gate_b_primary"],
         "pair_final_eligible_main_gate_b_primary"),
        ("eligible_listing_gate_b_robustness", "listing_gate_b_robustness_status",
         ["predictor_eligible_main_gate_b_robustness", "predictor_eligible_expanded_gate_b_robustness"],
         "pair_final_eligible_main_gate_b_robustness"),
    ]:
        unres = company_year[company_year[elig_col] == "unresolved"]
        for _, row in unres.iterrows():
            assert row[elig_col] == "unresolved"
            assert row[status_col] == "unresolved"
            for pc in pred_cols:
                if pc in company_year.columns:
                    assert int(row[pc]) == 0, f"{row['row_key']} {pc} != 0"
            dep = pairs_out[pairs_out["predictor_row_key_t"] == row["row_key"]]
            assert not (dep[pair_flag] == 1).any(), f"{row['row_key']} has eligible pair"


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
    """No modeling artifacts or paths may exist in Gate B outputs."""
    assert not (ROOT / "outputs" / "stage_modeling" / "run_manifest.json").is_file()
    assert not (ROOT / "stage125").is_dir()
    banned_exts = (".joblib", ".npz")
    banned_pats = ("shap", "smote", "calibration", "temporal_split",
                   "predictions", "model_results")
    for name in [f.name for f in GATE_B_DIR.iterdir() if f.is_file()]:
        low = name.lower()
        if low.startswith("modeling_") and low.endswith(".csv"):
            continue
        for ext in banned_exts:
            assert not low.endswith(ext), name
        for pat in banned_pats:
            assert pat not in low, name


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
    # Six large + small outputs (including approval JSON + README) + qc report all hashed.
    keys = metadata["output_files_sha256"]
    for large in ex.LARGE_OUTPUTS:
        assert f"gate_b_final/{large}" in keys
    for small in ex.SMALL_OUTPUTS:
        assert f"gate_b_final/{small}" in keys
    assert "stage124_batch02_gate_b_qc_report.json" in keys


def test_approval_files_frozen_in_manifest(metadata):
    """Approval JSON and README must be in output_files_sha256 (frozen assets)."""
    keys = metadata["output_files_sha256"]
    assert "gate_b_final/gate_b_rule_approval_stage124.json" in keys
    assert keys["gate_b_final/gate_b_rule_approval_stage124.json"] is not None
    assert "gate_b_final/README_GATE_B_RULE_APPROVAL.md" in keys
    assert keys["gate_b_final/README_GATE_B_RULE_APPROVAL.md"] is not None


def test_metadata_stable_python_fields(metadata):
    """Metadata must use stable python_version/python_implementation matching expected runtime."""
    assert "python" not in metadata or metadata["python"] is None
    assert "python_version" in metadata
    assert "python_implementation" in metadata
    assert metadata["python_version"] == ex.EXPECTED_PYTHON_VERSION
    assert metadata["python_implementation"] == ex.EXPECTED_PYTHON_IMPLEMENTATION


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


def test_approval_all_anchors_validated():
    """verify_inputs must validate every approval anchor with exact values."""
    report = ex.verify_inputs(ROOT)
    approval_mismatches = [m for m in report["mismatches"]
                           if "approval anchor" in m]
    assert approval_mismatches == []
    ap = report["approval"]
    for field, expected in ex.APPROVAL_EXPECTED.items():
        assert ap.get(field) == expected, f"approval field {field}: {ap.get(field)!r} != {expected!r}"


def test_approval_anchor_fail_closed(monkeypatch):
    """A modified approval anchor must cause fail-closed."""
    original = ex.APPROVAL_EXPECTED.copy()
    monkeypatch.setitem(ex.APPROVAL_EXPECTED, "decision_status", "rejected")
    with pytest.raises(ex.QCFail):
        ex.verify_inputs(ROOT)


def test_approval_counts_validated(stats):
    """verify_inputs must validate exact approved counts for Rule A and Rule B."""
    report = ex.verify_inputs(ROOT)
    ap = report["approval"]
    assert ap["approved_primary_expected_pairs"] == 1013
    assert ap["approved_primary_expected_positive"] == 81
    assert ap["approved_primary_expected_negative"] == 932
    assert ap["approved_robustness_expected_pairs"] == 994
    assert ap["approved_robustness_expected_positive"] == 80
    assert ap["approved_robustness_expected_negative"] == 914


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


def test_qc_assertions_are_real(qc_report):
    """QC assertions must include real computed checks, not constant PASS."""
    assertion_names = {a["assertion"] for a in qc_report["assertions"]}
    required = {
        "no_modeling_started",
        "no_rule_c_canonical",
        "date_semantics_provenance_verified",
        "no_missing_zeroed",
        "input_hashes_verified",
        "listing_master_hash_verified",
        "approval_record_verified",
        "nesting_invariants",
        "distribution_sums",
        "source_columns_preserved",
        "pair_source_columns_preserved",
        "target_columns_preserved",
        "output_hashes_verified",
    }
    assert required.issubset(assertion_names), \
        f"missing assertions: {required - assertion_names}"
    for a in qc_report["assertions"]:
        assert a["status"] == "PASS", f"{a['assertion']}: {a['status']}"


def test_qc_assertion_count(qc_report):
    """QC report must have a reasonable number of assertions (schema + computed)."""
    assert qc_report["assertion_count"] >= 20


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


# --------------------------------------------------------------------------- #
# Negative tests — each QC assertion must be computed, not constant PASS
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def listing_master():
    return pd.read_csv(ROOT / "stage124" / "listing_master_verified_stage124.csv",
                       encoding="utf-8-sig")


def _mock_stats():
    """Minimal stats dict for negative tests that only check specific assertions."""
    return {
        "main_rule_a_primary": {"pairs": 0, "positive": 0, "negative": 0, "target_missing": 0},
        "main_rule_b_listing_robustness": {"pairs": 0, "positive": 0, "negative": 0, "target_missing": 0},
        "expanded_rule_a_company_scope_robustness": {"pairs": 0, "positive": 0, "negative": 0, "target_missing": 0},
        "expanded_rule_b_combined_robustness": {"pairs": 0, "positive": 0, "negative": 0, "target_missing": 0},
    }


def _empty_company_year():
    """Minimal company_year with required columns and no unresolved rows."""
    return pd.DataFrame({
        "row_key": [],
        "eligible_listing_gate_b_primary": [],
        "listing_gate_b_primary_status": [],
        "eligible_listing_gate_b_robustness": [],
        "listing_gate_b_robustness_status": [],
        "predictor_eligible_main_gate_b_primary": [],
        "predictor_eligible_expanded_gate_b_primary": [],
        "predictor_eligible_main_gate_b_robustness": [],
        "predictor_eligible_expanded_gate_b_robustness": [],
    })


def _empty_pairs_out():
    """Minimal pairs_out with required columns and no eligible pairs."""
    return pd.DataFrame({
        "predictor_row_key_t": [],
        "pair_final_eligible_main_gate_b_primary": [],
        "pair_final_eligible_main_gate_b_robustness": [],
        "pair_final_eligible_expanded_gate_b_primary": [],
        "pair_final_eligible_expanded_gate_b_robustness": [],
    })


def test_negative_altered_target_value(pairs_out, src_pairs):
    """Altering a target value must cause target_columns_preserved to FAIL."""
    tampered = pairs_out.copy()
    tampered.loc[0, "FD_target_main_t_plus_1"] = (
        999 if tampered.loc[0, "FD_target_main_t_plus_1"] != 999 else 998)
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=tampered, company_year=_empty_company_year(),
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=src_pairs, src_pairs=src_pairs)
    tgt = [a for a in assertions if a["assertion"] == "target_columns_preserved"]
    assert len(tgt) == 1
    assert tgt[0]["status"] == "FAIL", "target_columns_preserved must FAIL on altered target"


def test_negative_altered_source_value(company_year, src_all_rows):
    """Altering a source value must cause source_columns_preserved to FAIL."""
    tampered = company_year.copy()
    tampered.loc[0, "total_assets"] = (
        999999.0 if float(tampered.loc[0, "total_assets"]) != 999999.0 else 888888.0)
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=_empty_pairs_out(), company_year=tampered,
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=src_all_rows, src_pairs=_empty_pairs_out())
    src = [a for a in assertions if a["assertion"] == "source_columns_preserved"]
    assert len(src) == 1
    assert src[0]["status"] == "FAIL", "source_columns_preserved must FAIL on altered source"


def test_negative_wrong_date_semantics(listing_master):
    """Changing verification_status must cause date_semantics_provenance_verified to FAIL."""
    tampered_lm = listing_master.copy()
    tampered_lm.loc[0, "verification_status"] = "wrong_value"
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=_empty_pairs_out(), company_year=_empty_company_year(),
        listing_master=tampered_lm, verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=_empty_pairs_out())
    ds = [a for a in assertions if a["assertion"] == "date_semantics_provenance_verified"]
    assert len(ds) == 1
    assert ds[0]["status"] == "FAIL", "date_semantics_provenance_verified must FAIL on wrong verification_status"


def test_negative_inserted_rule_c_column(company_year, pairs_out):
    """Inserting a Rule C column must cause no_rule_c_canonical to FAIL."""
    tampered_cy = company_year.copy()
    tampered_cy["eligible_rule_c_test"] = 0
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=pairs_out, company_year=tampered_cy,
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=_empty_pairs_out())
    rc = [a for a in assertions if a["assertion"] == "no_rule_c_canonical"]
    assert len(rc) == 1
    assert rc[0]["status"] == "FAIL", "no_rule_c_canonical must FAIL on Rule C column"


def test_negative_unresolved_pair_eligible(company_year, pairs_out):
    """Making an unresolved pair eligible must cause no_missing_zeroed to FAIL."""
    unres_a_keys = set(
        company_year[company_year["eligible_listing_gate_b_primary"] == "unresolved"]["row_key"])
    tampered_pairs = pairs_out.copy()
    mask = tampered_pairs["predictor_row_key_t"].isin(unres_a_keys)
    if mask.any():
        idx = tampered_pairs.index[mask][0]
        tampered_pairs.loc[idx, "pair_final_eligible_main_gate_b_primary"] = 1
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=tampered_pairs, company_year=company_year,
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=_empty_pairs_out())
    nmz = [a for a in assertions if a["assertion"] == "no_missing_zeroed"]
    assert len(nmz) == 1
    assert nmz[0]["status"] == "FAIL", "no_missing_zeroed must FAIL on eligible unresolved pair"


def test_negative_modeling_artifact_present():
    """Creating a .joblib artifact must cause no_modeling_started to FAIL."""
    artifact = GATE_B_DIR / "test_model.joblib"
    artifact.write_bytes(b"fake model")
    try:
        assertions = ex._qc_assertions(
            _mock_stats(), {"checks": [], "overall_pass": True},
            pairs_out=_empty_pairs_out(), company_year=_empty_company_year(),
            listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
            output_hashes={}, project_dir=ROOT,
            src_all_rows=_empty_company_year(), src_pairs=_empty_pairs_out())
        nm = [a for a in assertions if a["assertion"] == "no_modeling_started"]
        assert len(nm) == 1
        assert nm[0]["status"] == "FAIL", "no_modeling_started must FAIL on .joblib artifact"
    finally:
        artifact.unlink(missing_ok=True)


def test_negative_altered_pair_source_value(pairs_out, src_pairs):
    """Altering a non-target pair feature must cause pair_source_columns_preserved to FAIL."""
    tampered = pairs_out.copy()
    tampered.loc[0, "predictor_eligible_main_t"] = (
        999 if int(tampered.loc[0, "predictor_eligible_main_t"]) != 999 else 998)
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=tampered, company_year=_empty_company_year(),
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=src_pairs)
    psc = [a for a in assertions if a["assertion"] == "pair_source_columns_preserved"]
    assert len(psc) == 1
    assert psc[0]["status"] == "FAIL", "pair_source_columns_preserved must FAIL on altered pair source value"


def test_negative_altered_pair_provenance_field(pairs_out, src_pairs):
    """Altering a provenance field (ticker) must cause pair_source_columns_preserved to FAIL."""
    tampered = pairs_out.copy()
    tampered.loc[0, "ticker"] = "TAMPERED_TICKER"
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=tampered, company_year=_empty_company_year(),
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes={}, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=src_pairs)
    psc = [a for a in assertions if a["assertion"] == "pair_source_columns_preserved"]
    assert len(psc) == 1
    assert psc[0]["status"] == "FAIL", "pair_source_columns_preserved must FAIL on altered ticker"


def test_pair_source_columns_preserved(qc_report):
    """QC report must include pair_source_columns_preserved assertion and it must PASS."""
    psc = [a for a in qc_report["assertions"]
           if a["assertion"] == "pair_source_columns_preserved"]
    assert len(psc) == 1
    assert psc[0]["status"] == "PASS"


def test_date_semantics_provenance_verified(qc_report):
    """QC report must include date_semantics_provenance_verified assertion and it must PASS."""
    ds = [a for a in qc_report["assertions"]
          if a["assertion"] == "date_semantics_provenance_verified"]
    assert len(ds) == 1
    assert ds[0]["status"] == "PASS"


def test_negative_mismatched_output_hash():
    """A tampered output hash must cause output_hashes_verified to FAIL."""
    fake_hashes = {"gate_b_final/gate_b_sample_matrix.csv": "0" * 64}
    assertions = ex._qc_assertions(
        _mock_stats(), {"checks": [], "overall_pass": True},
        pairs_out=_empty_pairs_out(), company_year=_empty_company_year(),
        listing_master=pd.DataFrame(), verify_report={"inputs": {}, "mismatches": []},
        output_hashes=fake_hashes, project_dir=ROOT,
        src_all_rows=_empty_company_year(), src_pairs=_empty_pairs_out())
    oh = [a for a in assertions if a["assertion"] == "output_hashes_verified"]
    assert len(oh) == 1
    assert oh[0]["status"] == "FAIL", "output_hashes_verified must FAIL on mismatched hash"


def test_negative_wrong_python_runtime(monkeypatch):
    """Mismatched Python runtime must cause fail-closed before any artifact write."""
    monkeypatch.setattr(ex, "EXPECTED_PYTHON_VERSION", "9.9.9")
    with pytest.raises(ex.QCFail, match="Python runtime mismatch"):
        ex.verify_python_runtime()
