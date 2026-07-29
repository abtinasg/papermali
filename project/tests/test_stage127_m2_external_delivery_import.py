"""Tests for the Stage127 external TSETMC delivery import / revalidation layer.

Every test below runs against a DETERMINISTIC SYNTHETIC FIXTURE bundle built in
a temp directory. The fixture exists only to prove that the import and Gate
logic fails closed; its numbers are fabricated and are never scientific results.
No model is fit, no prediction is produced, and no final-test row is read.
"""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import zipfile

import pytest

from src import stage127_m2_external_delivery_import as imp
from src import stage127_m2_market_data_gate as g

FIXTURE_DISCLAIMER = (
    "SYNTHETIC FIXTURE DATA — not a scientific result and never reported as one"
)

TICKERS = ("AAA", "BBB")
RANGES = {
    "RNG0001": ("AAA", "2016-01-01", "2016-12-31"),
    "RNG0002": ("BBB", "2016-01-01", "2016-12-31"),
}
INS = {"AAA": "1000000000000001", "BBB": "1000000000000002"}
ISIN = {"AAA": "IRO1AAAA0001", "BBB": "IRO1BBBB0001"}

DAILY_URL_T = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins}/0"
)
ADJ_URL_T = "https://members.tsetmc.com/tsev2/chart/data/Financial.aspx?i={ins}&t=ph&a=1"


# --------------------------------------------------------------------------- #
# Deterministic synthetic bundle
# --------------------------------------------------------------------------- #

def _dates(n: int) -> list[str]:
    """n synthetic 'trading days' inside 2016, deterministic and gap-free."""
    from datetime import date, timedelta
    out: list[str] = []
    d = date(2016, 1, 4)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _csv(columns: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_fixture(
    *,
    days: int = 200,
    drop_range: str | None = None,
    extra_range: bool = False,
    tamper_raw: bool = False,
    break_field_mapping: bool = False,
    break_adjusted_join: bool = False,
    out_of_range_raw_date: bool = False,
    future_date: bool = False,
    duplicate_key: bool = False,
    adjusted_missing_days: set[int] | None = None,
    zero_value_days: set[int] | None = None,
) -> dict[str, bytes]:
    """Return {member_name: bytes} for a synthetic delivery ZIP."""
    adjusted_missing_days = adjusted_missing_days or set()
    zero_value_days = zero_value_days or set()
    dates = _dates(days)

    request_rows = [
        {
            "range_id": rid, "ticker": t,
            "requested_start_date": lo, "requested_end_date": hi,
            "covered_pair_count": 1, "source_id": g.M2_PRIMARY_SOURCE_ID,
        }
        for rid, (t, lo, hi) in RANGES.items()
    ]
    request_csv = _csv(
        ["range_id", "ticker", "requested_start_date", "requested_end_date",
         "covered_pair_count", "source_id"], request_rows)

    members: dict[str, bytes] = {
        f"{imp.ROOT}/README.md": b"# synthetic fixture\n",
        imp.BUNDLE_REQUEST_REL: request_csv.encode("utf-8"),
    }

    mapping_rows = []
    manifest_rows = []
    provenance_rows = []
    raw_sha_rows = []
    daily_rows = []

    for t in TICKERS:
        mapping_rows.append({
            "requested_ticker": t, "matched_ticker": t,
            "company_name": f"{t} Co", "tsetmc_instrument_id": INS[t],
            "isin": ISIN[t], "mapping_status": "MATCHED",
            "mapping_evidence": FIXTURE_DISCLAIMER, "mapping_note": "",
        })

    for rid, (t, lo, hi) in RANGES.items():
        if drop_range == rid:
            continue
        ins = INS[t]
        daily_url = DAILY_URL_T.format(ins=ins)
        adj_url = ADJ_URL_T.format(ins=ins)

        records = []
        adj_parts = []
        for i, d in enumerate(dates):
            price = 1000.0 + i
            value = 0.0 if i in zero_value_days else 1_000_000.0 + i
            volume = 0.0 if i in zero_value_days else 500.0 + i
            deven = int(d.replace("-", ""))
            if out_of_range_raw_date and i == 0:
                deven = 20150102
            records.append({
                "insCode": ins, "dEven": deven,
                "pClosing": price, "pDrCotVal": price - 1,
                "priceFirst": price - 2, "priceMax": price + 5,
                "priceMin": price - 5, "qTotCap": value,
                "qTotTran5J": volume, "zTotTran": 10.0 + i,
            })
            if i not in adjusted_missing_days:
                pc = price if not (break_adjusted_join and i == 5) else price + 777
                adj_parts.append(
                    f"{deven},{price + 5:.0f},{price - 5:.0f},{price - 2:.0f},"
                    f"{price - 1:.0f},{volume:.0f},{pc:.0f}"
                )

        daily_blob = json.dumps({"closingPriceDaily": records}).encode("utf-8")
        adj_blob = ";".join(adj_parts).encode("utf-8")
        if tamper_raw and rid == "RNG0001":
            daily_blob += b" "

        daily_rel = f"raw_restricted/{rid}/{imp.RAW_DAILY_BASENAME}"
        adj_rel = f"raw_restricted/{rid}/{imp.RAW_ADJUSTED_BASENAME}"
        members[f"{imp.ROOT}/{daily_rel}"] = daily_blob
        members[f"{imp.ROOT}/{adj_rel}"] = adj_blob

        daily_sha = imp.sha256_bytes(daily_blob)
        adj_sha = imp.sha256_bytes(adj_blob)
        if tamper_raw and rid == "RNG0001":
            daily_sha = "0" * 64  # manifest no longer describes the bytes

        for rel, sha, blob in (
            (daily_rel, daily_sha, daily_blob), (adj_rel, adj_sha, adj_blob),
        ):
            raw_sha_rows.append(
                {"file": rel, "sha256": sha, "size_bytes": len(blob)})
            provenance_rows.append({
                "range_id": rid, "ticker": t, "InsCode": ins,
                "restricted_raw_file": rel, "restricted_raw_sha256": sha,
                "full_source_file": f"raw_full_escrow/{ins}/full.json",
                "full_source_sha256": "f" * 64,
                "source_endpoint": daily_url if rel == daily_rel else adj_url,
                "requested_start_date": lo, "requested_end_date": hi,
            })

        manifest_rows.append({
            "range_id": rid, "requested_ticker": t,
            "tsetmc_instrument_id": ins,
            "requested_start_date": lo, "requested_end_date": hi,
            "first_returned_date": dates[0], "last_returned_date": dates[-1],
            "rows_retrieved": len(records), "retrieval_status": "SUCCESS",
            "source_endpoint": f"{daily_url} ; {adj_url}",
            "retrieved_at_utc": "2026-07-27T00:00:00Z",
            "raw_response_file": f"{daily_rel} ; {adj_rel}",
            "raw_response_sha256": f"{daily_sha} ; {adj_sha}",
            "notes": FIXTURE_DISCLAIMER,
        })

        for i, d in enumerate(dates):
            price = 1000.0 + i
            value = 0.0 if i in zero_value_days else 1_000_000.0 + i
            volume = 0.0 if i in zero_value_days else 500.0 + i
            has_adj = i not in adjusted_missing_days
            # Under break_adjusted_join the RAW pc was shifted; the normalized
            # row keeps the unshifted value, so the exact-date join must fail.
            pc = price
            trading_date = d
            if future_date and i == 0:
                trading_date = "2021-05-05"
            row = {
                "requested_ticker": t, "ticker": t, "company_name": f"{t} Co",
                "tsetmc_instrument_id": ins, "isin": ISIN[t],
                "trading_date": trading_date,
                "adjusted_close": f"{pc}" if has_adj else "",
                "adjusted_close_status": (
                    imp.ADJUSTED_STATUS_OK if has_adj
                    else imp.ADJUSTED_STATUS_UNRESOLVED),
                "raw_close": price,
                "last_price": price - 1 if not break_field_mapping else price + 99,
                "open": price - 2, "high": price + 5, "low": price - 5,
                "traded_value_rial": value, "raw_traded_value": value,
                "raw_traded_value_unit": "rial", "volume": volume,
                "trade_count": 10.0 + i,
                "source_endpoint": f"{daily_url} ; adjusted_close from {adj_url}",
                "retrieved_at_utc": "2026-07-27T00:00:00Z",
                "raw_response_file": f"{daily_rel} ; {adj_rel}",
                "raw_response_sha256": f"{daily_sha} ; {adj_sha}",
            }
            daily_rows.append(row)
            if duplicate_key and i == 3:
                daily_rows.append(dict(row))

    if extra_range:
        manifest_rows.append(dict(manifest_rows[0], range_id="RNG9999"))

    daily_cols = list(daily_rows[0].keys())
    members[f"{imp.ROOT}/output/stage127_m2_external_return_daily.csv"] = _csv(
        daily_cols, daily_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/stage127_m2_external_return_mapping.csv"] = _csv(
        list(mapping_rows[0].keys()), mapping_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/stage127_m2_external_return_manifest.csv"] = _csv(
        list(manifest_rows[0].keys()), manifest_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/full_retrieval_status_audit.csv"] = _csv(
        list(manifest_rows[0].keys()), manifest_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/raw_sha256_manifest.csv"] = _csv(
        ["file", "sha256", "size_bytes"], raw_sha_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/restricted_raw_provenance_manifest.csv"] = _csv(
        list(provenance_rows[0].keys()), provenance_rows).encode("utf-8")
    members[f"{imp.ROOT}/output/full_extraction_qc_report.json"] = json.dumps(
        {"source": "TSETMC", "qc_passed": True,
         "note": FIXTURE_DISCLAIMER}).encode("utf-8")
    return members


def write_zip(tmp_path, members: dict[str, bytes], name="fixture.zip") -> str:
    path = os.path.join(str(tmp_path), name)
    with zipfile.ZipFile(path, "w") as zf:
        for member, blob in members.items():
            zf.writestr(member, blob)
    return path


def open_fixture(tmp_path, members: dict[str, bytes]) -> imp.ExternalDelivery:
    path = write_zip(tmp_path, members)
    return imp.ExternalDelivery(
        path,
        expected_sha256=imp.sha256_file(path),
        expected_size=os.path.getsize(path),
    )


def canonical_rows(members: dict[str, bytes]) -> list[dict[str, str]]:
    text = members[imp.BUNDLE_REQUEST_REL].decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _request_sha(members: dict[str, bytes]) -> str:
    return imp.sha256_bytes(members[imp.BUNDLE_REQUEST_REL])


def validate(tmp_path, **kwargs):
    members = build_fixture(**kwargs)
    with open_fixture(tmp_path, members) as d:
        return imp.validate_delivery(
            d, canonical_rows(members),
            expected_request_sha256=_request_sha(members),
            strict_expected_counts=False)


# --------------------------------------------------------------------------- #
# A / B — bundle and canonical-request identity
# --------------------------------------------------------------------------- #

def test_A_wrong_zip_sha256_is_a_hard_fail(tmp_path):
    path = write_zip(tmp_path, build_fixture())
    with pytest.raises(imp.ImportFail, match="SHA256 mismatch"):
        imp.ExternalDelivery(
            path, expected_sha256="0" * 64,
            expected_size=os.path.getsize(path))


def test_A_wrong_zip_size_is_a_hard_fail(tmp_path):
    path = write_zip(tmp_path, build_fixture())
    with pytest.raises(imp.ImportFail, match="size mismatch"):
        imp.ExternalDelivery(
            path, expected_sha256=imp.sha256_file(path), expected_size=1)


def test_B_wrong_canonical_request_sha_is_a_hard_fail(tmp_path):
    members = build_fixture()
    with open_fixture(tmp_path, members) as d:
        rows = canonical_rows(members)
        with pytest.raises(imp.ImportFail, match="does not match the canonical"):
            imp.verify_delivered_request_matches_canonical(d, rows)


def test_B_repository_canonical_request_sha_is_pinned():
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    rows = imp.load_canonical_ranges(root)
    assert len(rows) == imp.EXPECTED_RANGES
    assert len({r["ticker"] for r in rows}) == imp.EXPECTED_TICKERS


def test_delivery_must_not_contain_full_history_escrow(tmp_path):
    members = build_fixture()
    members[f"{imp.ROOT}/raw_full_escrow/x/full.json"] = b"{}"
    path = write_zip(tmp_path, members)
    with pytest.raises(imp.ImportFail, match="raw_full_escrow"):
        imp.ExternalDelivery(
            path, expected_sha256=imp.sha256_file(path),
            expected_size=os.path.getsize(path))


# --------------------------------------------------------------------------- #
# C / D / E — range universe and raw integrity
# --------------------------------------------------------------------------- #

def test_C_missing_range_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="missing range_id"):
        validate(tmp_path, drop_range="RNG0002")


def test_D_extra_range_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="extra range_id"):
        validate(tmp_path, extra_range=True)


def test_E_tampered_restricted_raw_sha_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="restricted raw SHA256 mismatch"):
        validate(tmp_path, tamper_raw=True)


def test_F_raw_to_normalized_mismatch_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="field mapping mismatch"):
        validate(tmp_path, break_field_mapping=True)


def test_G_adjusted_pc_date_mismatch_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="exact-date validation failure"):
        validate(tmp_path, break_adjusted_join=True)


def test_H_out_of_range_raw_date_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="outside the authorized range"):
        validate(tmp_path, out_of_range_raw_date=True)


def test_I_future_or_final_test_date_injection_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="firewall violation"):
        validate(tmp_path, future_date=True)


def test_J_duplicate_normalized_key_is_a_hard_fail(tmp_path):
    with pytest.raises(imp.ImportFail, match="duplicate normalized key"):
        validate(tmp_path, duplicate_key=True)


def test_clean_fixture_validates(tmp_path):
    qc, obs, mapping, manifest = validate(tmp_path)
    assert qc["independent_validation_passed"]
    assert qc["raw_to_normalized_field_mismatches"] == 0
    assert qc["adjusted_close_exact_date_mismatches"] == 0
    assert qc["external_qc_report_trusted"] is False
    assert set(obs) == set(TICKERS)


def test_external_qc_flag_is_never_trusted(tmp_path):
    """A delivered ``qc_passed: true`` cannot rescue tampered evidence."""
    members = build_fixture(tamper_raw=True)
    delivered = json.loads(
        members[f"{imp.ROOT}/output/full_extraction_qc_report.json"])
    assert delivered["qc_passed"] is True
    with open_fixture(tmp_path, members) as d:
        with pytest.raises(imp.ImportFail):
            imp.validate_delivery(
                d, canonical_rows(members),
                expected_request_sha256=_request_sha(members),
                strict_expected_counts=False)


def test_non_tsetmc_endpoint_is_rejected(tmp_path):
    members = build_fixture()
    key = f"{imp.ROOT}/output/stage127_m2_external_return_manifest.csv"
    members[key] = members[key].replace(
        b"cdn.tsetmc.com", b"query1.finance.yahoo.com")
    with open_fixture(tmp_path, members) as d:
        with pytest.raises(imp.ImportFail, match="non-TSETMC endpoint"):
            imp.validate_delivery(
                d, canonical_rows(members),
                expected_request_sha256=_request_sha(members),
                strict_expected_counts=False)


# --------------------------------------------------------------------------- #
# K / L / M / N — frozen feature rules on observed evidence
# --------------------------------------------------------------------------- #

def _obs(n: int, *, missing: set[int] = frozenset(),
         zero_value: set[int] = frozenset()) -> list[dict]:
    dates = _dates(n)
    return [
        {
            "trading_date": d, "range_id": "RNG0001",
            "adjusted_close": None if i in missing else 1000.0 + i,
            "adjusted_close_status": (
                imp.ADJUSTED_STATUS_UNRESOLVED if i in missing
                else imp.ADJUSTED_STATUS_OK),
            "traded_value_rial": 0.0 if i in zero_value else 1_000_000.0,
        }
        for i, d in enumerate(dates)
    ]


CUTOFF = "2017-06-01"


def test_K_missing_adjusted_price_stays_unavailable_never_raw_close():
    obs = _obs(200, missing={10})
    f = g.compute_pair_features(CUTOFF, obs)
    assert f["missing_price_day_count"] == 1
    # The missing day is excluded, never filled with the raw close: the two
    # returns that would have used it simply do not exist.
    assert f["usable_daily_return_count"] == 199 - 2


def test_K_missing_price_is_never_bridged():
    """A gap is not closed by pretending the neighbours are consecutive."""
    obs = _obs(60, missing={30})
    f = g.compute_pair_features(CUTOFF, obs)
    assert f["usable_daily_return_count"] == 59 - 2


def test_L_zero_traded_value_day_is_excluded_from_amihud():
    obs = _obs(200, zero_value={20, 21, 22})
    f = g.compute_pair_features(CUTOFF, obs)
    assert f["zero_traded_value_day_count"] == 3
    assert f["usable_amihud_day_count"] == f["usable_daily_return_count"] - 3


def test_M_fewer_than_126_returns_makes_features_unavailable():
    f = g.compute_pair_features(CUTOFF, _obs(100))
    assert f["usable_daily_return_count"] == 99
    assert f["equity_return_window"] is None
    assert f["realized_volatility"] is None


def test_N_fewer_than_126_amihud_days_makes_amihud_unavailable():
    obs = _obs(200, zero_value=set(range(0, 120)))
    f = g.compute_pair_features(CUTOFF, obs)
    assert f["usable_amihud_day_count"] < g.MIN_VALID_AMIHUD_OBSERVATIONS
    assert f["amihud_illiquidity"] is None
    assert f["realized_volatility"] is not None


def test_window_endpoint_price_is_required():
    obs = _obs(200, missing={0})
    f = g.compute_pair_features(CUTOFF, obs)
    assert f["equity_return_window"] is None
    assert f["realized_volatility"] is not None


def test_features_are_computed_and_not_annualized():
    f = g.compute_pair_features(CUTOFF, _obs(200))
    assert f["equity_return_window"] == pytest.approx(1199 / 1000 - 1)
    assert 0 < f["realized_volatility"] < 0.01  # daily, never annualized
    assert f["amihud_illiquidity"] > 0


def test_same_calendar_day_as_cutoff_is_rejected():
    obs = _obs(200)
    cutoff = obs[-1]["trading_date"]
    f = g.compute_pair_features(cutoff, obs)
    assert f["window_last_trading_date"] < cutoff
    assert f["same_calendar_day_as_cutoff_rejected"] == 1


def test_window_is_twelve_calendar_months_not_the_retrieval_range():
    obs = _obs(600)  # far longer than 12 months
    f = g.compute_pair_features("2019-01-01", obs)
    assert f["window_start_calendar_date"] == g.minus_calendar_months(
        __import__("datetime").date.fromisoformat(f["t_star"]), 12).isoformat()
    assert f["window_trading_day_count"] < 300


# --------------------------------------------------------------------------- #
# O–U — Gate conjunction logic
# --------------------------------------------------------------------------- #

def _gate_inputs(*, cov=0.95, common=0.95, pos=(9, 9), g08=g.RESOLUTION_PASS):
    candidates = [
        {
            "variable": v,
            "G08_all_required_gates_pass": {"resolution": g08},
        }
        for v, _, _ in g.M2_VARIABLES
    ]
    coverage = {
        v: {
            "resolution": g.RESOLUTION_PASS,
            "overall_coverage": cov,
            "valid_rows": int(cov * 666),
            "total_development_rows": 666,
            "coverage_gate_passed": cov >= g.CANDIDATE_VALID_COVERAGE_MIN,
        }
        for v, _, _ in g.M2_VARIABLES
    }
    common_audit = {
        "resolution": g.RESOLUTION_PASS,
        "common_coverage": common,
        "common_usable_rows": int(common * 666),
        "total_development_rows": 666,
        "common_coverage_gate_passed": (
            common >= g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN),
    }
    feasibility = {
        "resolution": g.RESOLUTION_PASS,
        "m2_common_sample_positive_counts": {
            "fold1_validation": pos[0], "fold2_validation": pos[1]},
    }
    return candidates, coverage, common_audit, feasibility


def test_R_all_conditions_met_yields_pass():
    status, blockers, cond = g.decide_gate_status(*_gate_inputs(), [])
    assert status == g.GATE_STATUS_PASS
    assert blockers == []
    assert all(cond.values())


def test_O_candidate_coverage_below_threshold_cannot_pass():
    status, blockers, cond = g.decide_gate_status(*_gate_inputs(cov=0.79), [])
    assert status == g.GATE_STATUS_FAIL
    assert cond["B_each_candidate_coverage_ge_0_80"] is False
    assert any("coverage" in b for b in blockers)


def test_P_common_coverage_below_threshold_cannot_pass():
    status, _b, cond = g.decide_gate_status(*_gate_inputs(common=0.69), [])
    assert status == g.GATE_STATUS_FAIL
    assert cond["C_common_sample_coverage_ge_0_70"] is False


def test_Q_one_validation_window_below_five_positives_cannot_pass():
    status, _b, cond = g.decide_gate_status(*_gate_inputs(pos=(9, 4)), [])
    assert status == g.GATE_STATUS_FAIL
    assert cond["D_both_validation_windows_ge_5_positives"] is False


def test_S_missing_evidence_yields_unresolved():
    candidates, coverage, common_audit, feasibility = _gate_inputs(
        g08=g.RESOLUTION_UNRESOLVED)
    for c in coverage.values():
        c["resolution"] = g.RESOLUTION_UNRESOLVED
        c["coverage_gate_passed"] = None
    common_audit["resolution"] = g.RESOLUTION_UNRESOLVED
    feasibility["resolution"] = g.RESOLUTION_UNRESOLVED
    status, blockers, _c = g.decide_gate_status(
        candidates, coverage, common_audit, feasibility, [])
    assert status == g.GATE_STATUS_UNRESOLVED
    assert blockers


def test_T_observed_threshold_failure_is_fail_not_unresolved():
    """An observed failure is never softened into UNRESOLVED."""
    status, blockers, _c = g.decide_gate_status(*_gate_inputs(cov=0.10), [])
    assert status == g.GATE_STATUS_FAIL
    assert status != g.GATE_STATUS_UNRESOLVED
    assert any("observed" in b for b in blockers)


def test_E_condition_blocks_on_leakage_or_provenance_defect():
    status, blockers, cond = g.decide_gate_status(
        *_gate_inputs(), ["adjusted-close exact-date join mismatch"])
    assert status == g.GATE_STATUS_FAIL
    assert cond["E_no_pit_leakage_join_provenance_blocker"] is False
    assert any("join mismatch" in b for b in blockers)


def test_F_condition_requires_all_three_frozen_variables():
    candidates, coverage, common_audit, feasibility = _gate_inputs()
    status, _b, cond = g.decide_gate_status(
        candidates[:2], coverage, common_audit, feasibility, [])
    assert status == g.GATE_STATUS_FAIL
    assert cond["F_all_three_frozen_m2_variables_present"] is False


def test_U_reachability_alone_with_zero_usable_evidence_never_passes():
    """An endpoint responding proves nothing and cannot produce a PASS."""
    evidence = {
        "candidate_level_endpoint_evidence": False,
        "authoritative_source": True,
        "documented_api_or_portal": True,
        "reproducible_retrieval_with_provenance": False,
        "machine_readable_or_reliably_structured": True,
    }
    acc = g.score_accessibility_from_evidence(evidence)
    assert acc["accessibility_score"] is None
    assert acc["resolution"] == g.RESOLUTION_UNRESOLVED

    candidates, coverage, common_audit, feasibility = _gate_inputs(
        g08=g.RESOLUTION_UNRESOLVED)
    for c in coverage.values():
        c["resolution"] = g.RESOLUTION_UNRESOLVED
        c["coverage_gate_passed"] = None
    common_audit["resolution"] = g.RESOLUTION_UNRESOLVED
    feasibility["resolution"] = g.RESOLUTION_UNRESOLVED
    status, _b, _c = g.decide_gate_status(
        candidates, coverage, common_audit, feasibility, [])
    assert status != g.GATE_STATUS_PASS


def test_accessibility_is_never_scored_zero_to_two():
    for evidence in (
        {},
        {"candidate_level_endpoint_evidence": True},
        {"candidate_level_endpoint_evidence": True,
         "documented_api_or_portal": True,
         "reproducible_retrieval_with_provenance": True,
         "authoritative_source": True,
         "machine_readable_or_reliably_structured": True},
    ):
        score = g.score_accessibility_from_evidence(evidence)["accessibility_score"]
        assert score in (None, 3, 4, 5)


# --------------------------------------------------------------------------- #
# V / W — firewall and no-modeling guarantees
# --------------------------------------------------------------------------- #

def test_V_no_final_test_predictor_or_target_access():
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))), "src", "stage127_m2_external_delivery_import.py")
    text = open(src, encoding="utf-8").read()
    assert "final_test" not in text.replace(
        "FINAL_TEST_FIREWALL_MIN_EXCLUDED_DATE", "").replace(
        "final_test_firewall_min_excluded_date", "").replace(
        "final_test_period_observations_imported", "").replace(
        "final-test", "")


def test_V_firewall_rejects_a_bundle_reaching_the_locked_period(tmp_path):
    with pytest.raises(imp.ImportFail, match="firewall violation"):
        validate(tmp_path, future_date=True)


def test_W_no_estimator_fit_or_predict_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in (
        "src/stage127_m2_external_delivery_import.py",
        "src/stage127_m2_market_data_gate.py",
        "run_stage127_m2_market_data_gate.py",
    ):
        text = open(os.path.join(root, rel), encoding="utf-8").read()
        for banned in (
            "sklearn", "xgboost", "lightgbm", "LogisticRegression",
            "RandomForest", ".fit(", ".predict(", "predict_proba",
        ):
            assert banned not in text, f"{rel} references {banned}"


def test_fixture_results_are_labelled_as_fixture_data():
    members = build_fixture()
    mapping = members[
        f"{imp.ROOT}/output/stage127_m2_external_return_mapping.csv"
    ].decode("utf-8")
    assert FIXTURE_DISCLAIMER in mapping


def test_import_is_deterministic(tmp_path):
    a = validate(tmp_path)[0]
    b = validate(tmp_path)[0]
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(
        b, sort_keys=True, default=str)


# --------------------------------------------------------------------------- #
# Frozen shared-window end rule (T*) — the literal contract, never relaxed
# --------------------------------------------------------------------------- #

def _stage127(name: str) -> dict:
    return json.load(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "stage127", name), encoding="utf-8"))


def test_tstar_is_the_last_eligible_trading_day_even_when_unpriced():
    """T* follows `shared_window.end_rule`, not "the last priced day"."""
    obs = _obs(200, missing={199})           # last eligible day has no price
    win = g.pair_scientific_window(CUTOFF, obs)
    assert win["t_star"] == obs[-1]["trading_date"]
    assert win["t_star"] != obs[-2]["trading_date"]


def test_tstar_is_never_moved_backwards_to_find_a_priced_day():
    """A long unpriced tail must not drag T* back to the last priced day."""
    obs = _obs(200, missing=set(range(180, 200)))
    win = g.pair_scientific_window(CUTOFF, obs)
    assert win["t_star"] == obs[-1]["trading_date"]


def test_missing_tN_price_makes_equity_unavailable_but_not_volatility():
    """The frozen `Require P_tN present` condition must be able to fail."""
    f = g.compute_pair_features(CUTOFF, _obs(200, missing={199}))
    assert f["missing_tN_adjusted_close"] is True
    assert f["missing_t0_adjusted_close"] is False
    assert f["equity_return_window"] is None
    assert f["realized_volatility"] is not None
    assert f["amihud_illiquidity"] is not None


def test_t0_and_tN_endpoint_failures_are_not_collapsed():
    only_t0 = g.compute_pair_features(CUTOFF, _obs(200, missing={0}))
    only_tN = g.compute_pair_features(CUTOFF, _obs(200, missing={199}))
    both = g.compute_pair_features(CUTOFF, _obs(200, missing={0, 199}))

    assert (only_t0["missing_t0_adjusted_close"],
            only_t0["missing_tN_adjusted_close"]) == (True, False)
    assert (only_tN["missing_t0_adjusted_close"],
            only_tN["missing_tN_adjusted_close"]) == (False, True)
    assert (both["missing_t0_adjusted_close"],
            both["missing_tN_adjusted_close"]) == (True, True)
    for f in (only_t0, only_tN, both):
        assert f["equity_return_window"] is None
        assert f["fewer_than_126_valid_returns"] is False


def test_tstar_endpoint_requirement_is_capable_of_failing_on_real_evidence():
    """Regression guard against the retired last-priced-day reading.

    Under that reading `missing_tN_adjusted_close` was structurally always
    False. The frozen rule must leave it genuinely observable.
    """
    b = _stage127("stage127_m2_market_data_gate_decision.json")[
        "feature_unavailability_breakdown"]
    assert b["missing_tN_adjusted_close"] > 0
    assert b["causes_are_not_mutually_exclusive"] is True
    assert b["tstar_chosen_to_improve_coverage"] is False


def test_tstar_semantics_audit_is_internally_consistent():
    s = _stage127("stage127_m2_tstar_semantics_audit_summary.json")
    assert s["development_pairs"] == g.EXPECTED_DEV_PAIRS
    assert s["same_tstar_count"] + s["different_tstar_count"] == s[
        "development_pairs"]
    # T* differs from the last-priced day exactly when the literal T* is
    # unpriced, so the two counts must agree.
    assert s["literal_tstar_missing_adjusted_close_count"] == s[
        "different_tstar_count"]
    assert s["tstar_moved_backwards_to_find_a_priced_day"] is False
    assert s["endpoint_price_requirement_evaluated_after_window_definition"]


def test_admission_terminology_cannot_be_read_as_modeling_admission():
    d = _stage127("stage127_m2_market_data_gate_decision.json")
    for cand in d["candidates"]:
        if "ADMITTED" in cand["admission_decision"]:
            assert "G01_G08" in cand["admission_decision"]
        assert cand["admission_scope"] == (
            "source_and_data_quality_gates_G01_G08_only")
        cov = d["candidate_coverage"][cand["variable"]]
        assert cand["candidate_modeling_path_coverage_pass"] == cov[
            "coverage_gate_passed"]
        # A candidate failing the frozen coverage threshold must never read as
        # admitted into the M2 modeling path.
        if not cov["coverage_gate_passed"]:
            assert cand["admitted_into_m2_modeling_path"] is False
