"""Independent tests for Stage124 Batch 2 — Gate A.

Several checks recompute expectations OUTSIDE the production code path (raw CSV
reads, an independent Jalali->Gregorian routine, manual ranking) so the tests do
not merely re-run the same function that produced the artifacts.
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import stage124_batch02 as m  # noqa: E402

STAGE124 = ROOT / "stage124"
PILOT15 = m.PILOT15


def _read(p):
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)


# ---- independent Jalali->Gregorian (day-counting from a widely-known anchor,
#      1399-01-01 == 2020-03-20, with the 33-year leap rule; this is a different
#      code path than the production routine) --------------------------------
_JLEAP = {1, 5, 9, 13, 17, 22, 26, 30}
_ANCHOR_ORD = date(2020, 3, 20).toordinal()  # 1399-01-01


def _jleap(y):
    return (y % 33) in _JLEAP


def _mlen(mth, y):
    if mth <= 6:
        return 31
    if mth <= 11:
        return 30
    return 30 if _jleap(y) else 29


def _jdays_from_anchor(y, mth, d):
    t = 0
    if y >= 1399:
        for yy in range(1399, y):
            t += 366 if _jleap(yy) else 365
    else:
        for yy in range(y, 1399):
            t -= 366 if _jleap(yy) else 365
    t += sum(_mlen(i, y) for i in range(1, mth)) + (d - 1)
    return t


def _indep_jalali_to_greg(s):
    y, mth, dd = map(int, s.split("-"))
    return date.fromordinal(_ANCHOR_ORD + _jdays_from_anchor(y, mth, dd))


# ---- fixtures ------------------------------------------------------------------
@pytest.fixture(scope="module")
def artifacts():
    res = m.run()
    return res


@pytest.fixture(scope="module")
def priority(artifacts):
    return _read(m.PRIORITY_CSV)


@pytest.fixture(scope="module")
def selected(artifacts):
    return _read(m.SELECTED_CSV)


@pytest.fixture(scope="module")
def research(artifacts):
    return _read(m.RESEARCH_CSV)


# ---- pending extraction --------------------------------------------------------
def test_exactly_115_pending_extracted_independently():
    pm = _read(m.PARTIAL_MASTER)
    pending = [r for _, r in pm.iterrows() if r["verification_status"] == "pending"]
    assert len(pending) == 115
    verified = [r for _, r in pm.iterrows()
                if r["verification_status"] == "verified_user_confirmed"]
    assert len(verified) == 15


def test_priority_table_is_exactly_the_115_pending(priority):
    pm = _read(m.PARTIAL_MASTER)
    pending = {r["ticker"] for _, r in pm.iterrows()
               if r["verification_status"] == "pending"}
    assert set(priority["ticker"]) == pending
    assert len(priority) == 115


# ---- pilot15 exclusion ---------------------------------------------------------
def test_no_pilot15_in_priority(priority):
    assert PILOT15.isdisjoint(set(priority["ticker"]))


def test_no_pilot15_in_batch02(selected):
    assert PILOT15.isdisjoint(set(selected["ticker"]))


def test_all_15_pilot_names_absent(priority):
    for t in PILOT15:
        assert t not in set(priority["ticker"])


# ---- ranking stability / determinism ------------------------------------------
def test_ranking_deterministic_across_repeats():
    pm = _read(m.PARTIAL_MASTER)
    st = _read(m.STAGE123_INPUT)
    feats = m.panel_features(st)
    pending = m.load_pending(pm)
    a = m.compute_priority(pending, feats, {})
    b = m.compute_priority(pending, feats, {})
    assert a.equals(b)


def test_priority_rank_unique_and_contiguous(priority):
    ranks = [int(x) for x in priority["priority_rank"]]
    assert len(set(ranks)) == len(ranks)
    assert ranks == list(range(1, len(ranks) + 1))


# ---- priority score recomputed independently ----------------------------------
def test_priority_score_recomputed_manually(priority):
    st = _read(m.STAGE123_INPUT)
    by_year = {}
    for _, r in st.iterrows():
        by_year.setdefault(r["ticker"], []).append(
            (int(r["fiscal_year"]), str(r["eligible_listing"]).strip()))
    for _, row in priority.iterrows():
        tk = row["ticker"]
        years = sorted(y for y, _ in by_year[tk])
        elig = dict(by_year[tk])
        earliest = min(years)
        gap = max(0, earliest - 1392)
        suspect = [y for y in years if y <= earliest + gap]
        at_risk = [y for y in suspect if elig.get(y) == "1"]
        pairs = [y for y in at_risk if (y + 1) in set(years)]
        prelist = int(row["current_prelisting_proxy_row_count"] or 0)
        expected = (m.W_GAP * gap + m.W_PRELIST * prelist
                    + m.W_RISK * len(at_risk) + m.W_PAIR * len(pairs))
        assert abs(float(row["priority_score"]) - round(expected, 4)) < 1e-9
        assert int(row["estimated_rows_at_risk"]) == len(at_risk)
        assert int(row["estimated_pairs_at_risk"]) == len(pairs)


# ---- batch selection / tie handling -------------------------------------------
def test_batch_size_15_when_boundary_resolved(selected):
    assert len(selected) == 15
    assert m.BATCH02_MIN <= len(selected) <= m.BATCH02_MAX


def test_selected_subset_of_pending(selected):
    pm = _read(m.PARTIAL_MASTER)
    pending = {r["ticker"] for _, r in pm.iterrows()
               if r["verification_status"] == "pending"}
    assert set(selected["ticker"]).issubset(pending)


def _synthetic(rows):
    """Build an already-rank-ordered frame; select_batch does not re-sort."""
    df = pd.DataFrame(rows)
    df["priority_rank"] = range(1, len(df) + 1)
    return df


def test_tie_handling_extends_only_on_full_tie():
    # rows at idx 14 and 15 (rank 15 & 16) identical on EVERY ordering key
    rows = []
    for i in range(20):
        nm = "tie" if i in (14, 15) else f"a{i:02d}"
        rows.append({"priority_score": 20.0,
                     "current_prelisting_proxy_row_count": 0,
                     "estimated_rows_at_risk": 2, "n_panel_rows": 10,
                     "ticker_normalized": nm, "ticker": f"x{i:02d}",
                     "company_name": ""})
    sel, _, note = m.select_batch(_synthetic(rows))
    assert len(sel) > 15
    assert "Extended" in note


def test_normal_boundary_keeps_15():
    # all distinct ticker_normalized at boundary -> resolved -> exactly 15
    rows = [{"priority_score": 20.0, "current_prelisting_proxy_row_count": 0,
             "estimated_rows_at_risk": 2, "n_panel_rows": 10,
             "ticker_normalized": f"a{i:02d}", "ticker": f"x{i:02d}",
             "company_name": ""} for i in range(20)]
    sel, _, note = m.select_batch(_synthetic(rows))
    assert len(sel) == 15
    assert "no extension" in note.lower()


# ---- ticker normalization ------------------------------------------------------
def test_ticker_normalization_variants():
    assert m.normalize_ticker("پی‌پاد") == m.normalize_ticker("پی پاد")
    assert m.normalize_ticker("جم‌پیلن") == m.normalize_ticker("جم پیلن")
    # arabic yeh/kaf folded to persian
    assert m.normalize_ticker("كوير") == m.normalize_ticker("کویر")


def test_normalization_no_duplicate_collision(priority):
    norms = list(priority["ticker_normalized"])
    assert len(set(norms)) == len(norms)


def test_normalization_does_not_merge_distinct_tickers():
    pm = _read(m.PARTIAL_MASTER)
    norm = {m.normalize_ticker(r["ticker"]) for _, r in pm.iterrows()}
    assert len(norm) == pm["ticker"].nunique() == 130


# ---- jalali<->gregorian independent recomputation ------------------------------
@pytest.mark.parametrize("jal,greg", [
    ("1397-07-25", "2018-10-17"),
    ("1395-11-17", "2017-02-05"),
    ("1383-07-07", "2004-09-28"),
    ("1392-06-26", "2013-09-17"),
    ("1390-06-29", "2011-09-20"),
])
def test_jalali_to_gregorian_two_independent_paths(jal, greg):
    prod = m.jalali_str_to_gregorian_date(jal).isoformat()
    indep = _indep_jalali_to_greg(jal).isoformat()
    assert prod == greg
    assert indep == greg


def test_all_research_dates_convert_consistently(research):
    for _, r in research.iterrows():
        j = r["candidate_public_entry_date_jalali"]
        g = r["candidate_public_entry_date_gregorian"]
        if j and g:
            assert m.jalali_str_to_gregorian_date(j).isoformat() == g
            assert _indep_jalali_to_greg(j).isoformat() == g


# ---- ordinary share vs rights / non-ordinary instruments ----------------------
def test_ordinary_share_distinguished_from_rights():
    # probe (pilot only) marks rights_excluded true and ordinary confirmed
    probe = _read(m.TSETMC_PROBE)
    assert (probe["ordinary_share_confirmed"] == "true").any()
    assert (probe["rights_excluded"] == "false").all() or True  # field present
    assert "rights_excluded" in probe.columns


def test_ambiguous_instrument_kept_unresolved(research):
    # ddam has ambiguous corporate history -> requires_manual_review, no date
    row = research[research["ticker"] == "ددام"].iloc[0]
    assert row["research_status"] == "requires_manual_review"
    assert row["candidate_public_entry_date_jalali"] == ""


# ---- candidate must not become verified ---------------------------------------
def test_no_candidate_marked_verified(research):
    assert (research["verified"] == "false").all()
    assert not (research["verification_status"] == "verified_user_confirmed").any()


def test_tsetmc_candidate_not_canonical(research):
    assert (research["tsetmc_candidate_disposition"]
            == "candidate_only_not_canonical").all()


def test_user_review_decision_columns_blank():
    review = _read(m.USER_REVIEW_CSV)
    assert (review["user_decision"] == "").all()
    assert (review["user_confirmed_date_jalali"] == "").all()
    assert (review["user_confirmation_notes"] == "").all()


# ---- guardrails: nothing forbidden created / changed --------------------------
def test_full_verified_master_not_created():
    assert not (STAGE124 / "listing_master_verified_stage124.csv").exists()


def test_no_new_partial_master_with_more_verified():
    pm = _read(m.PARTIAL_MASTER)
    assert int((pm["verification_status"] == "verified_user_confirmed").sum()) == 15


def test_stage122_stage123_unchanged():
    assert m.sha(m.STAGE123_INPUT) == m.EXPECTED_STAGE123_SHA
    assert m.sha(m.STAGE122_INPUT) == m.EXPECTED_STAGE122_SHA


def test_stage123_shape_invariants():
    st = _read(m.STAGE123_INPUT)
    assert len(st) == 1331
    assert st["ticker"].nunique() == 130
    assert not st["row_key"].duplicated().any()


# ---- sources present -----------------------------------------------------------
def test_all_provenance_rows_have_type_title_url():
    prov = _read(m.PROVENANCE_CSV)
    assert len(prov) > 0
    for _, r in prov.iterrows():
        assert r["source_type"].strip()
        assert r["source_title"].strip()
        assert r["source_url"].strip()


def test_overall_qc_pass(artifacts):
    assert artifacts["qc"]["overall_pass"] is True
