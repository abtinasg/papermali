"""Minimal unit tests for Stage123 (run: pytest -q tests/test_stage123.py).

Pure-function tests use small synthetic frames; a few integration tests read the
Stage123 outputs produced by run_stage123.py (the session fixture builds them once).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import utils, stage123 as s123  # noqa: E402
from src import stage122 as s122  # noqa: E402


@pytest.fixture(scope="session")
def built():
    cfg = utils.load_config()
    res = s123.build_full(cfg)
    out = res["out"]
    return {
        "cfg": cfg, "out": out, "qc": res["qc"],
        "mar": pd.read_csv(out / "modeling_all_rows_stage123.csv", dtype=str,
                           encoding="utf-8-sig", keep_default_na=False),
        "pairs": pd.read_csv(out / "modeling_one_year_ahead_stage123.csv", dtype=str,
                             encoding="utf-8-sig", keep_default_na=False),
        "ea": pd.read_csv(out / "eligibility_audit_stage123.csv", dtype=str,
                          encoding="utf-8-sig", keep_default_na=False),
        "raw": s122.load_all_rows(cfg),
    }


def _s(vals):
    return pd.Series([np.nan if v is None else float(v) for v in vals])


# 1 ----------------------------------------------------------------------
def test_nonblocking_article141_only():
    # article141 all-missing must NOT block a definite 0 from the 3 quant criteria
    art = _s([None, None, None])
    acc = _s([0, 1, 0]); neg = _s([0, 0, 0]); ocf = _s([0, 0, 0])
    res = s123.aggregate_fd_target(art, acc, neg, ocf)
    assert res.tolist() == [0.0, 1.0, 0.0]


# 2 ----------------------------------------------------------------------
def test_quantitative_criterion_all_missing_fails():
    art = _s([None, None]); acc = _s([None, None])  # all-missing quant
    neg = _s([0, 1]); ocf = _s([0, 0])
    with pytest.raises(s123.QCFail):
        s123.aggregate_fd_target(art, acc, neg, ocf)


# 3 ----------------------------------------------------------------------
def test_target_missing_not_zero_roundtrip(tmp_path):
    s = pd.Series([1.0, 0.0, np.nan])
    df = pd.DataFrame({"FD_target_main": s122._csvnum(s)})
    p = tmp_path / "t.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    back = pd.read_csv(p, dtype=str, keep_default_na=False)
    assert back["FD_target_main"].tolist() == ["1", "0", ""]  # missing stays empty


# 4 ----------------------------------------------------------------------
def test_predictor_eligibility_independent_of_target_t():
    df = pd.DataFrame({
        "ticker": ["AAA"], "fiscal_year": ["1395"], "total_assets": ["100"],
        "total_liabilities": ["40"], "equity": ["60"],
        "ocf_resolution_status": ["observed_or_verified"],
        "statement_scope_status": ["separate"], "non_12_month_period_flag": ["0"],
        "source_file": ["f.pdf"], "unit": ["میلیون ریال"]})
    main_target = pd.Series([np.nan])  # target MISSING at year t
    el = s123.compute_eligibility123(df, main_target, pd.Series([False]))
    assert el["eligible_target"].iloc[0] == 0          # target is missing
    assert el["predictor_eligible_main"].iloc[0] == 1  # but predictor still eligible


# 5 ----------------------------------------------------------------------
def test_exact_one_year_pairing():
    df = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"], "fiscal_year": ["1392", "1393", "1395"],
        "row_key": ["AAA|1392", "AAA|1393", "AAA|1395"]})
    name = pd.Series(["A", "A", "A"])
    main = pd.Series([0.0, 1.0, 0.0]); a = pd.Series([0.0, 0.0, 0.0])
    el = pd.DataFrame({"predictor_eligible_main": [1, 1, 1],
                       "predictor_eligible_expanded": [1, 1, 1],
                       "model_exclusion_reason_main": ["", "", ""],
                       "model_exclusion_reason_expanded": ["", "", ""]})
    pairs = s123.build_pairs123(df, main, a, a, el, name)
    # only 1392->1393 (1393->1394 missing, 1395 has no 1394 predecessor) => 1 pair
    assert len(pairs) == 1
    assert pairs.iloc[0]["fiscal_year_t"] == 1392
    assert pairs.iloc[0]["target_year"] == 1393


# 6 ----------------------------------------------------------------------
def test_no_duplicate_pairs(built):
    p = built["pairs"]
    assert int(p.duplicated(["ticker", "fiscal_year_t"]).sum()) == 0


# 7 ----------------------------------------------------------------------
def test_statement_scope_user_confirmation(built):
    mar = built["mar"]
    # no consolidated/unknown remains in the analytical canonical status
    assert int(mar["statement_scope_status"].isin(s123.CONSOLIDATED_SCOPES).sum()) == 0
    corr = pd.read_csv(built["out"] / "statement_scope_correction_audit_stage123.csv",
                       dtype=str, keep_default_na=False)
    assert (corr["corrected_statement_scope"] == s123.CORRECTED_SCOPE).all()


# 8 ----------------------------------------------------------------------
def test_source_provenance_unchanged(built):
    mar = built["mar"].set_index("row_key")
    raw = built["raw"].set_index("row_key")
    assert (mar.loc[raw.index, "source_file"] == raw["source_file"]).all()
    assert (mar.loc[raw.index, "source_url"] == raw["source_url"]).all()


# 9 ----------------------------------------------------------------------
def test_manual_company_mapping_main_and_expanded(built):
    ea = built["ea"]
    for t, m in s123.COMPANY_SAMPLE_MAPPING.items():
        sub = ea[ea["ticker"] == t]
        assert len(sub) > 0
        assert (sub["eligible_company_main"] == str(m["main"])).all()
        assert (sub["eligible_company_expanded"] == str(m["expanded"])).all()
    # a non-listed ticker defaults to fully eligible on company grounds
    others = ea[~ea["ticker"].isin(s123.COMPANY_SAMPLE_MAPPING)]
    assert (others["eligible_company_main"] == "1").all()


# 10 ---------------------------------------------------------------------
def test_no_future_columns_in_predictor_manifest():
    universe = [c for c, _ in s123.ALLOWED_T_PREDICTORS + s123.NEAR_TARGET_PREDICTORS]
    prohibited = {c for c, _ in s123.PROHIBITED_LEAKAGE}
    assert not any(c.endswith("_t_plus_1") for c in universe)
    assert not (set(universe) & prohibited)


# bonus: overall independent QC must pass
def test_independent_qc_overall_pass(built):
    assert built["qc"]["overall_pass"] is True
