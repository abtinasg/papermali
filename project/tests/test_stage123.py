"""Minimal unit tests for Stage123 (run: pytest -q tests/test_stage123.py).

Pure-function tests use small synthetic frames; a few integration tests read the
Stage123 outputs produced by run_stage123.py (the session fixture builds them once).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import utils, stage123 as s123  # noqa: E402
from src import stage122 as s122  # noqa: E402


_TRACKED_FILES = (
    ROOT / "stage123" / "metadata_and_hashes_stage123.json",
    ROOT / "stage123" / "statement_scope_correction_audit_stage123.csv",
)


@pytest.fixture(scope="session")
def built():
    cfg = utils.load_config()
    _backups = {p: p.read_bytes() if p.is_file() else None for p in _TRACKED_FILES}
    try:
        res = s123.build_full(cfg)
        out = res["out"]
        data = {
            "cfg": cfg, "out": out, "qc": res["qc"],
            "mar": pd.read_csv(out / "modeling_all_rows_stage123.csv", dtype=str,
                               encoding="utf-8-sig", keep_default_na=False),
            "pairs": pd.read_csv(out / "modeling_one_year_ahead_stage123.csv", dtype=str,
                                 encoding="utf-8-sig", keep_default_na=False),
            "ea": pd.read_csv(out / "eligibility_audit_stage123.csv", dtype=str,
                              encoding="utf-8-sig", keep_default_na=False),
            "corr": pd.read_csv(out / "statement_scope_correction_audit_stage123.csv",
                                dtype=str, keep_default_na=False),
            "raw": s122.load_all_rows(cfg),
        }
    finally:
        # Restore the tracked files IMMEDIATELY here (setup-time, via
        # try/finally) rather than deferring to session teardown (the old
        # code restored only after the LAST test using `built` returned).
        # Session-scoped fixtures live for the whole pytest process, so a
        # deferred restore left these tracked files mutated on disk for the
        # entire session — observable by any OTHER test module that reads
        # them fresh in the meantime (e.g. Stage125 Part 2's
        # frozen_asset_hashes(), which snapshots this file's actual on-disk
        # SHA-256). Everything the tests below need is already captured in
        # `data` above (read from disk before this restore runs), so no test
        # depends on the mutated, not-yet-restored content.
        for p, backup in _backups.items():
            if backup is not None:
                p.write_bytes(backup)
    yield data


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
    # Read from the in-memory snapshot (captured before the tracked-file
    # restore), NOT re-read from disk — by the time this test runs, the
    # tracked audit CSV on disk has already been restored to its committed
    # content (see the `built` fixture).
    corr = built["corr"]
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


# 11 ---------------------------------------------------------------------
def test_row_order_independence(built):
    # aligning the Stage122 base to raw is invariant to the base's row order
    cfg, raw = built["cfg"], built["raw"]
    base = s123.load_stage122_base(cfg)
    shuffled = base.sample(frac=1.0, random_state=7).reset_index(drop=True)
    a1 = s123.align_base_to_raw(raw, base)
    a2 = s123.align_base_to_raw(raw, shuffled)
    assert (a1["row_key"].values == raw["row_key"].values).all()
    assert a1.equals(a2)  # result identical regardless of input row order


# 12 ---------------------------------------------------------------------
def test_align_rowkey_mismatch_fails():
    raw = pd.DataFrame({"row_key": ["a", "b"], "ticker": ["x", "y"],
                        "fiscal_year": ["1392", "1393"]})
    base_missing = pd.DataFrame({"row_key": ["a", "c"]})
    with pytest.raises(s123.QCFail):
        s123.align_base_to_raw(raw, base_missing)
    base_dup = pd.DataFrame({"row_key": ["a", "a", "b"]})
    with pytest.raises(s123.QCFail):
        s123.align_base_to_raw(raw, base_dup)


# ---- Stage123 timestamp determinism + pytest session-isolation fix ------ #
#
# Regression coverage for a real bug: `built`'s tracked-file restore was
# deferred to session teardown, so any OTHER test module running later in the
# SAME pytest session (e.g. Stage125 Part 2's frozen-asset snapshot) could
# observe `statement_scope_correction_audit_stage123.csv` mid-rebuild, with a
# wall-clock `timestamp` value that never matched the committed content. Fixed
# by (a) anchoring the timestamp to the last commit touching Stage123's own
# code instead of wall-clock time, and (b) restoring the tracked files
# immediately (try/finally) rather than deferring to session teardown.

def test_deterministic_timestamp_stable_within_same_commit():
    # Core determinism guarantee: two calls with no intervening commit must
    # agree, unlike time.strftime(...)/datetime.now(), which never would.
    ts1 = s123._deterministic_timestamp()
    ts2 = s123._deterministic_timestamp()
    assert ts1 == ts2
    assert ts1 != ""


def test_build_full_is_deterministic_across_repeated_runs():
    # Two consecutive build_full() calls at the SAME commit must produce a
    # byte-identical statement_scope_correction_audit_stage123.csv and an
    # identical metadata `datetime` field. This is the actual regression
    # test for the bug: before the fix, `timestamp`/`datetime` were
    # wall-clock-based and differed on every call, so this assertion would
    # have failed.
    cfg = utils.load_config()
    corr_path = ROOT / "stage123" / "statement_scope_correction_audit_stage123.csv"
    meta_path = ROOT / "stage123" / "metadata_and_hashes_stage123.json"
    backups = {p: p.read_bytes() if p.is_file() else None
              for p in (corr_path, meta_path)}
    try:
        s123.build_full(cfg)
        first_corr = corr_path.read_bytes()
        first_datetime = json.loads(meta_path.read_text(encoding="utf-8"))["datetime"]

        s123.build_full(cfg)
        second_corr = corr_path.read_bytes()
        second_datetime = json.loads(meta_path.read_text(encoding="utf-8"))["datetime"]

        assert first_corr == second_corr, (
            "statement_scope_correction_audit_stage123.csv must be "
            "byte-identical across repeated build_full() runs at the same "
            "commit (only non-deterministic before this fix)"
        )
        assert first_datetime == second_datetime
    finally:
        for p, data in backups.items():
            if data is not None:
                p.write_bytes(data)


def test_tracked_files_restored_immediately_after_build(built):
    # Proves the restore is NOT deferred to session teardown: by the time
    # this test runs, `built`'s setup has already completed, and the pytest
    # session is still very much in progress (teardown has not happened) —
    # both tracked files on disk must already match the committed HEAD
    # content byte-for-byte. Before the fix, this would only become true
    # after the LAST test using `built` finished (i.e. at session end),
    # meaning any OTHER test module reading these files fresh in between
    # would see the freshly-rebuilt (not-yet-restored) content.
    for p in _TRACKED_FILES:
        rel = p.relative_to(ROOT.parent).as_posix()
        committed = subprocess.run(
            ["git", "show", f"HEAD:{rel}"], cwd=str(ROOT.parent),
            capture_output=True, check=True).stdout
        assert p.read_bytes() == committed, (
            f"{rel} was not restored to its committed content immediately "
            "after the `built` fixture ran"
        )
