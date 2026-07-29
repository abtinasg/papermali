"""Tests for the Stage127 zero-trade semantics evidence import and adjudication.

Every test below runs against a DETERMINISTIC SYNTHETIC FIXTURE delivery built
in a temp directory. The fixture exists only to prove that the import fails
closed and that the adjudication reasons from the frozen contract; its numbers
are fabricated and are never scientific results.

No model is fit, no prediction is produced, no final-test row is read, and the
canonical Gate is never modified.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import zipfile

import pytest

from src import stage127_m2_trading_day_semantics_adjudication as adj
from src import stage127_m2_zero_trade_semantics_import as imp

FIXTURE_DISCLAIMER = (
    "SYNTHETIC FIXTURE DATA — not a scientific result and never reported as one"
)

ROOT = imp.ROOT
HOST = "https://cdn.tsetmc.com/api"

TICKERS = ("AAA", "BBB")
INS = {"AAA": "1000000000000001", "BBB": "1000000000000002"}
ISIN = {"AAA": "IRO1AAAA0001", "BBB": "IRO1BBBB0001"}

#: Two POINT_DATE requests and one RANGE request, well inside the development
#: period so the final-test firewall is satisfied by construction.
POINT_REQUESTS = (
    {"unique_request_id": "UNQ0001", "ticker": "AAA", "endpoint_date": "2016-07-18"},
    {"unique_request_id": "UNQ0002", "ticker": "BBB", "endpoint_date": "2017-08-21"},
)
RANGE_REQUEST = {
    "unique_request_id": "UNQ0003",
    "ticker": "AAA",
    "range_start_date": "2016-01-01",
    "range_end_date": "2016-12-31",
}


def _csv(columns: tuple[str, ...], rows: list[dict]) -> str:
    return imp.csv_text(columns, rows)


def _deven(iso: str) -> str:
    return iso.replace("-", "")


# --------------------------------------------------------------------------- #
# Deterministic synthetic request package and delivery
# --------------------------------------------------------------------------- #

UNIQUE_REQUEST_COLUMNS = (
    "unique_request_id", "request_type", "InsCode", "ISIN", "ticker",
    "endpoint_date", "range_start_date", "range_end_date", "occurrence_count",
    "evidence_reason", "qTotCap", "qTotTran5J", "zTotTran", "raw_close",
)
OCCURRENCE_COLUMNS = (
    "request_id", "ticker", "endpoint_type", "endpoint_date",
    "adjusted_close_status",
)


def build_request_package(path: str) -> str:
    """Build the synthetic canonical evidence-request package."""
    unique = []
    for req in POINT_REQUESTS:
        unique.append({
            "unique_request_id": req["unique_request_id"],
            "request_type": "POINT_DATE",
            "InsCode": INS[req["ticker"]],
            "ISIN": ISIN[req["ticker"]],
            "ticker": req["ticker"],
            "endpoint_date": req["endpoint_date"],
            "range_start_date": "",
            "range_end_date": "",
            "occurrence_count": "1",
            "evidence_reason": "ZERO_TRADE_ENDPOINT",
            "qTotCap": "0.0", "qTotTran5J": "0.0", "zTotTran": "0.0",
            "raw_close": "1000.0",
        })
    unique.append({
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "request_type": "RANGE",
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "ISIN": ISIN[RANGE_REQUEST["ticker"]],
        "ticker": RANGE_REQUEST["ticker"],
        "endpoint_date": "",
        "range_start_date": RANGE_REQUEST["range_start_date"],
        "range_end_date": RANGE_REQUEST["range_end_date"],
        "occurrence_count": "1",
        "evidence_reason": "LOW_RETURN_SEQUENCE_SEMANTICS",
        "qTotCap": "", "qTotTran5J": "", "zTotTran": "", "raw_close": "",
    })
    occurrences = [
        {
            "request_id": f"REQ{i:04d}",
            "ticker": req["ticker"],
            "endpoint_type": "t0",
            "endpoint_date": req["endpoint_date"],
            "adjusted_close_status": "ADJUSTED_CLOSE_UNRESOLVED",
        }
        for i, req in enumerate(POINT_REQUESTS, start=1)
    ]
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(imp.CANONICAL_UNIQUE_REQUESTS_REL,
                    _csv(UNIQUE_REQUEST_COLUMNS, unique))
        zf.writestr(imp.CANONICAL_OCCURRENCES_REL,
                    _csv(OCCURRENCE_COLUMNS, occurrences))
        zf.writestr("README.md", FIXTURE_DISCLAIMER)
    return path


class _Artifact:
    def __init__(self, aid, request_id, ticker, date, etype, endpoint, rel,
                 payload, roles, status="CACHED"):
        self.aid = aid
        self.request_id = request_id
        self.ticker = ticker
        self.date = date
        self.etype = etype
        self.endpoint = endpoint
        self.rel = rel
        self.payload = payload
        self.roles = roles
        self.status = status


def _artifacts() -> list[_Artifact]:
    out: list[_Artifact] = []
    n = 0

    def add(**kwargs):
        nonlocal n
        n += 1
        out.append(_Artifact(aid=f"ART{n:04d}", **kwargs))

    for req in POINT_REQUESTS:
        rid, tic, day = req["unique_request_id"], req["ticker"], req["endpoint_date"]
        ins, dev = INS[tic], _deven(day)
        add(request_id=rid, ticker=tic, date=day, etype="CALENDAR",
            endpoint=f"{HOST}/ClosingPrice/GetInstrumentCalendar/{ins}",
            rel=f"raw_bounded/{rid}_ICAL/instrument_calendar_bounded.json",
            payload=json.dumps({"instrumentCalendar": [
                {"dEven": int(dev), "pClosing": 1000.0, "qTotTran5J": 0.0}]}
            ).encode(),
            roles=["INSTRUMENT_CALENDAR"])
        add(request_id=rid, ticker=tic, date=day, etype="DAILY_CLOSING",
            endpoint=f"{HOST}/ClosingPrice/GetClosingPriceDaily/{ins}/{dev}",
            rel=f"raw_bounded/{rid}_DC/closing_price_daily_{dev}.json",
            payload=json.dumps({"closingPriceDaily": {
                "insCode": ins, "dEven": int(dev), "pClosing": 1000.0,
                "zTotTran": 0.0, "qTotTran5J": 0.0, "qTotCap": 0.0}}).encode(),
            roles=["DAILY_CLOSING"])
        add(request_id=rid, ticker=tic, date=day, etype="DAILY_CLOSING",
            endpoint=f"{HOST}/ClosingPrice/GetClosingPriceDailyList/{ins}/0",
            rel=f"raw_bounded/{rid}_DLP/closing_price_daily_point.json",
            payload=json.dumps({"closingPriceDaily": [
                {"insCode": ins, "dEven": int(dev), "pClosing": 1000.0,
                 "zTotTran": 0.0}]}).encode(),
            roles=["DAILY_ROW_PRESENCE"])
        add(request_id=rid, ticker=tic, date=day, etype="STATE",
            endpoint=f"{HOST}/MarketData/GetInstrumentState/{ins}/{dev}",
            rel=f"raw_bounded/{rid}_ST/instrument_state_{dev}.json",
            payload=json.dumps({"instrumentState": [
                {"insCode": ins, "cEtaval": "A ", "dEven": 0, "hEven": 1}]}
            ).encode(),
            roles=["STATE"])
        add(request_id=rid, ticker=tic, date=day, etype="TRADE_HISTORY",
            endpoint=f"{HOST}/Trade/GetTradeHistory/{ins}/{dev}/true",
            rel=f"raw_bounded/{rid}_TRG_{dev}/trade_history_{dev}_grouped.json",
            payload=json.dumps({"tradeHistory": []}).encode(),
            roles=["TRADE_HISTORY_GROUPED"])

    rid = RANGE_REQUEST["unique_request_id"]
    tic = RANGE_REQUEST["ticker"]
    ins = INS[tic]
    sample_days = ("2016-03-15", "2016-09-20")
    add(request_id=rid, ticker=tic, date="", etype="CALENDAR",
        endpoint=f"{HOST}/ClosingPrice/GetInstrumentCalendar/{ins}",
        rel=f"raw_bounded/{rid}_ICAL/instrument_calendar_bounded.json",
        payload=json.dumps({"instrumentCalendar": [
            {"dEven": int(_deven(d)), "pClosing": 1000.0} for d in sample_days]}
        ).encode(),
        roles=["INSTRUMENT_CALENDAR"])
    add(request_id=rid, ticker=tic, date="", etype="DAILY_CLOSING",
        endpoint=f"{HOST}/ClosingPrice/GetClosingPriceDailyList/{ins}/0",
        rel=f"raw_bounded/{rid}_BDL/closing_price_daily_bounded.json",
        payload=json.dumps({"closingPriceDaily": [
            {"insCode": ins, "dEven": int(_deven(d)), "pClosing": 1000.0,
             "zTotTran": 0.0 if i == 0 else 5.0} for i, d in enumerate(sample_days)]}
        ).encode(),
        roles=["DAILY_CLOSING", "DAILY_ROW_PRESENCE", "ZERO_TRADE_FIELDS"])
    for i, day in enumerate(sample_days):
        dev = _deven(day)
        add(request_id=rid, ticker=tic, date=day, etype="STATE",
            endpoint=f"{HOST}/MarketData/GetInstrumentState/{ins}/{dev}",
            rel=f"raw_bounded/{rid}_ST/instrument_state_{dev}.json",
            payload=json.dumps({"instrumentState": [
                {"insCode": ins, "cEtaval": "A " if i == 0 else "IS"}]}).encode(),
            roles=["STATE"])
    dev = _deven(sample_days[0])
    add(request_id=rid, ticker=tic, date=sample_days[0], etype="TRADE_HISTORY",
        endpoint=f"{HOST}/Trade/GetTradeHistory/{ins}/{dev}/true",
        rel=f"raw_bounded/{rid}_TRG_{dev}/trade_history_{dev}_grouped.json",
        payload=json.dumps({"tradeHistory": []}).encode(),
        roles=["TRADE_HISTORY_GROUPED"])
    add(request_id=rid, ticker=tic, date=sample_days[0], etype="TRADE_HISTORY",
        endpoint=f"{HOST}/Trade/GetTradeHistory/{ins}/{dev}/false",
        rel=f"raw_bounded/{rid}_TRU_{dev}/trade_history_{dev}_ungrouped.json",
        payload=json.dumps({"tradeHistory": []}).encode(),
        roles=["TRADE_HISTORY_UNGROUPED"])

    for tic in TICKERS:
        add(request_id=POINT_REQUESTS[0]["unique_request_id"], ticker=tic,
            date="", etype="INSTRUMENT_IDENTITY",
            endpoint=f"{HOST}/Instrument/GetInstrumentIdentity/{INS[tic]}",
            rel=f"raw_bounded/ID_{tic}/instrument_identity.json",
            payload=json.dumps({"instrumentIdentity": {
                "instrumentID": ISIN[tic], "cIsin": "IRO1OTHER001"}}).encode(),
            roles=["INSTRUMENT_IDENTITY"])

    # A zero-byte INSTRUMENT_HISTORY whose retrieval was NOT demonstrated.
    add(request_id=POINT_REQUESTS[0]["unique_request_id"], ticker="AAA",
        date="", etype="INSTRUMENT_HISTORY",
        endpoint=f"{HOST}/Instrument/GetInstrumentHistory/{INS['AAA']}/20180101",
        rel="raw_bounded/ID_AAA_HIST_20180101/instrument_history_20180101.json",
        payload=b"", roles=["INSTRUMENT_HISTORY"], status="UNRESOLVED")
    return out


MANIFEST_COLUMNS = (
    "evidence_artifact_id", "unique_request_id", "ticker", "InsCode",
    "endpoint_date", "evidence_type", "source_endpoint", "retrieval_status",
    "retrieved_at_utc", "raw_response_file", "raw_response_sha256",
    "parent_full_response_sha256", "bounded_response", "notes",
)


def build_delivery(path: str, mutate=None) -> str:
    """Build the synthetic v3-shaped delivery ZIP."""
    arts = _artifacts()
    manifest = [{
        "evidence_artifact_id": a.aid,
        "unique_request_id": a.request_id,
        "ticker": a.ticker,
        "InsCode": INS.get(a.ticker, ""),
        "endpoint_date": a.date,
        "evidence_type": a.etype,
        "source_endpoint": a.endpoint,
        "retrieval_status": a.status,
        "retrieved_at_utc": "2026-07-28T00:00:00Z",
        "raw_response_file": a.rel,
        "raw_response_sha256": hashlib.sha256(a.payload).hexdigest(),
        "parent_full_response_sha256": "",
        "bounded_response": "true",
        "notes": FIXTURE_DISCLAIMER,
    } for a in arts]

    calendar = [{
        "unique_request_id": r["unique_request_id"],
        "InsCode": INS[r["ticker"]],
        "endpoint_date": r["endpoint_date"],
        "in_instrument_trading_calendar": "true",
        "calendar_evidence_endpoint":
            f"{HOST}/ClosingPrice/GetInstrumentCalendar/{INS[r['ticker']]}",
        "calendar_evidence_note": "calendar_response_contains_endpoint_date=true",
    } for r in POINT_REQUESTS]
    calendar.append({
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "endpoint_date": "",
        "in_instrument_trading_calendar": "bounded_calendar_rows=2",
        "calendar_evidence_endpoint":
            f"{HOST}/ClosingPrice/GetInstrumentCalendar/"
            f"{INS[RANGE_REQUEST['ticker']]}",
        "calendar_evidence_note": FIXTURE_DISCLAIMER,
    })

    state = [{
        "unique_request_id": r["unique_request_id"],
        "InsCode": INS[r["ticker"]],
        "endpoint_date": r["endpoint_date"],
        "instrument_state": "state_code='A '; state_meaning=UNRESOLVED",
        "state_evidence_endpoint":
            f"{HOST}/MarketData/GetInstrumentState/{INS[r['ticker']]}/"
            f"{_deven(r['endpoint_date'])}",
        "state_evidence_note": FIXTURE_DISCLAIMER,
    } for r in POINT_REQUESTS]
    state.append({
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "endpoint_date": "",
        "instrument_state": (
            "state_code='A '; state_meaning=UNRESOLVED | "
            "state_code='IS'; state_meaning=UNRESOLVED"
        ),
        "state_evidence_endpoint":
            f"{HOST}/MarketData/GetInstrumentState/"
            f"{INS[RANGE_REQUEST['ticker']]}/20160315",
        "state_evidence_note": FIXTURE_DISCLAIMER,
    })

    trade = [{
        "unique_request_id": r["unique_request_id"],
        "InsCode": INS[r["ticker"]],
        "endpoint_date": r["endpoint_date"],
        "trade_occurred": "no",
        "trade_count_daily": "0.0",
        "traded_volume_daily": "0.0",
        "traded_value_daily": "0.0",
        "trade_evidence_endpoint":
            f"{HOST}/Trade/GetTradeHistory/{INS[r['ticker']]}/"
            f"{_deven(r['endpoint_date'])}/true",
        "trade_evidence_note": "grouped_tradeHistory_records=0",
    } for r in POINT_REQUESTS]
    trade.append({
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "endpoint_date": "2016-03-15",
        "trade_occurred": "no",
        "trade_count_daily": "0.0",
        "traded_volume_daily": "0.0",
        "traded_value_daily": "0.0",
        "trade_evidence_endpoint":
            f"{HOST}/Trade/GetTradeHistory/{INS[RANGE_REQUEST['ticker']]}/"
            f"20160315/true",
        "trade_evidence_note": FIXTURE_DISCLAIMER,
    })

    identity = [{
        "identity_evidence_id": f"IDE{i:04d}",
        "ticker": tic,
        "request_InsCode": INS[tic],
        "request_ISIN": ISIN[tic],
        "current_raw_instrumentID": ISIN[tic],
        "current_raw_cIsin": "IRO1OTHER001",
        "candidate_historical_InsCode": "",
        "candidate_historical_ISIN": "",
        "candidate_historical_instrumentID": "",
        "candidate_valid_from": "",
        "candidate_valid_to": "",
        "source_endpoint": f"{HOST}/Instrument/GetInstrumentIdentity/{INS[tic]}",
        "raw_response_file": f"raw_bounded/ID_{tic}/instrument_identity.json",
        "raw_response_sha256": "",
        "evidence_status": "UNRESOLVED",
        "notes": FIXTURE_DISCLAIMER,
    } for i, tic in enumerate(TICKERS, start=1)]

    identity_audit = []
    for tic in TICKERS:
        identity_audit.append({
            "ticker": tic, "request_InsCode": INS[tic], "request_ISIN": ISIN[tic],
            "raw_current_instrumentID": ISIN[tic],
            "raw_current_cIsin": "IRO1OTHER001",
            "same_request_ISIN_as_instrumentID": "true",
            "same_request_ISIN_as_cIsin": "false",
            "historical_probe_date": "",
            "raw_historical_instrumentID": "", "raw_historical_cIsin": "",
            "raw_historical_insCode": "",
            "evidence_status": "current_identity_snapshot",
        })
        identity_audit.append({
            "ticker": tic, "request_InsCode": INS[tic], "request_ISIN": ISIN[tic],
            "raw_current_instrumentID": ISIN[tic],
            "raw_current_cIsin": "IRO1OTHER001",
            "same_request_ISIN_as_instrumentID": "true",
            "same_request_ISIN_as_cIsin": "false",
            "historical_probe_date": "2018-01-01",
            "raw_historical_instrumentID": "", "raw_historical_cIsin": "",
            "raw_historical_insCode": "",
            "evidence_status": "historical_snapshot",
        })

    cal_vs_daily = [{
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "range_start_date": RANGE_REQUEST["range_start_date"],
        "range_end_date": RANGE_REQUEST["range_end_date"],
        "calendar_date_count": "2",
        "daily_date_count": "2",
        "date_sets_equal": "true",
        "missing_in_daily_count": "0",
        "extra_in_daily_count": "0",
        "notes": "zero_trade_rows=1; positive_trade_rows=1",
    }]

    trade_audit = [{
        "unique_request_id": RANGE_REQUEST["unique_request_id"],
        "ticker": RANGE_REQUEST["ticker"],
        "InsCode": INS[RANGE_REQUEST["ticker"]],
        "endpoint_date": "2016-03-15",
        "daily_zTotTran": "0.0", "daily_qTotTran5J": "0.0", "daily_qTotCap": "0.0",
        "grouped_tradeHistory_record_count": "0", "grouped_nTran_values": "",
        "grouped_max_nTran": "", "ungrouped_tradeHistory_record_count": "0",
        "qTranCap_present_in_response": "false",
        "len_grouped_used_as_trade_count": "false",
        "observed_pilot_property":
            "OBSERVED: ungrouped_record_count_equals_daily_zTotTran",
        "notes": FIXTURE_DISCLAIMER,
    }]

    role_rows = [{"evidence_artifact_id": a.aid, "evidence_role": role}
                 for a in arts for role in a.roles]
    request_rows = [{"evidence_artifact_id": a.aid,
                     "unique_request_id": a.request_id} for a in arts]

    max_deven = max(
        int(_deven(r["endpoint_date"])) for r in POINT_REQUESTS)
    max_deven = max(max_deven, 20160920)
    external_qc = {
        "requests": {"total": 3, "POINT_DATE": 2, "RANGE": 1,
                     "affected_tickers": 2},
        "calendar": {"POINT_present": 2, "POINT_absent": 0,
                     "calendar_vs_daily_equal": 1},
        "state": {"POINT": 2, "RANGE": 2, "TOTAL": 4,
                  "literal_code_counts": {"'A '": 3, "'IS'": 1},
                  "state_meaning_unresolved_count": 4},
        "trade": {"POINT_grouped": 2, "RANGE_grouped": 1, "RANGE_ungrouped": 1,
                  "TradeHistory_artifacts_total": 4, "trade_audit_rows": 1,
                  "daily_vs_ungrouped_mismatch": 0},
        "identity": {"tickers_checked": 2, "CANDIDATE_FOUND": 0,
                     "NONE_FOUND": 0, "UNRESOLVED": 2,
                     "request_ISIN_vs_instrumentID_matches": 2,
                     "request_ISIN_vs_cIsin_matches": 0},
        "raw": {"raw_artifact_count": len(arts), "manifest_rows": len(arts),
                "unique_raw_response_file_count": len(arts),
                "SHA256_verified": len(arts)},
        "empty_raw": {"zero_byte_artifacts": 1,
                      "SUCCESS_CACHED_empty_without_trusted_provenance": 0},
        "firewall": {"maximum_bounded_dEven": max_deven,
                     "dEven_gte_20210101_count": 0},
        "roles": {"request_mapping_rows": len(request_rows),
                  "role_mapping_rows": len(role_rows),
                  "unmapped_artifact_count": 0},
    }

    members: dict[str, object] = {
        imp.EXTERNAL_QC_REL: json.dumps(external_qc),
        imp.MANIFEST_REL: _csv(MANIFEST_COLUMNS, manifest),
        imp.REQUEST_MAPPING_REL: _csv(
            ("evidence_artifact_id", "unique_request_id"), request_rows),
        imp.ROLE_MAPPING_REL: _csv(
            ("evidence_artifact_id", "evidence_role"), role_rows),
        imp.CALENDAR_EVIDENCE_REL: _csv(tuple(calendar[0]), calendar),
        imp.STATE_EVIDENCE_REL: _csv(tuple(state[0]), state),
        imp.TRADE_EVIDENCE_REL: _csv(tuple(trade[0]), trade),
        imp.IDENTITY_EVIDENCE_REL: _csv(tuple(identity[0]), identity),
        imp.CAL_VS_DAILY_REL: _csv(tuple(cal_vs_daily[0]), cal_vs_daily),
        imp.TRADE_AUDIT_REL: _csv(tuple(trade_audit[0]), trade_audit),
        imp.IDENTITY_AUDIT_REL: _csv(tuple(identity_audit[0]), identity_audit),
        f"{ROOT}/README.md": FIXTURE_DISCLAIMER,
    }
    raw = {f"{ROOT}/{a.rel}": a.payload for a in arts}
    if mutate is not None:
        mutate(members, raw)

    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
        for name, payload in raw.items():
            zf.writestr(name, payload)
    return path


@pytest.fixture()
def fixture_env(tmp_path, monkeypatch):
    """Point the importer at the synthetic request package and delivery."""
    repo_root = tmp_path / "repo"
    (repo_root / os.path.dirname(imp.CANONICAL_REQUEST_REL)).mkdir(
        parents=True, exist_ok=True)
    request_path = str(repo_root / imp.CANONICAL_REQUEST_REL)
    build_request_package(request_path)
    monkeypatch.setattr(
        imp, "CANONICAL_REQUEST_SHA256", imp.sha256_file(request_path))

    def make(mutate=None, name="delivery.zip"):
        path = str(tmp_path / name)
        build_delivery(path, mutate=mutate)
        monkeypatch.setattr(imp, "BUNDLE_SIZE_BYTES", os.path.getsize(path))
        monkeypatch.setattr(imp, "BUNDLE_SHA256", imp.sha256_file(path))
        return path

    return str(repo_root), make


# --------------------------------------------------------------------------- #
# The fixture itself must import cleanly, otherwise no failure test means much
# --------------------------------------------------------------------------- #

def test_synthetic_delivery_imports_cleanly(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    assert qc["validator_pass"] is True
    assert qc["external_qc_comparison"]["disagreement_count"] == 0
    assert qc["external_qc_report_trusted"] is False


# --------------------------------------------------------------------------- #
# Fail-closed: bundle identity
# --------------------------------------------------------------------------- #

def test_external_zip_hash_failure_closes_import(fixture_env, monkeypatch):
    repo_root, make = fixture_env
    path = make()
    monkeypatch.setattr(imp, "BUNDLE_SHA256", "0" * 64)
    with pytest.raises(imp.EvidenceImportError, match="SHA256 mismatch"):
        imp.import_delivery(repo_root, path)


def test_external_zip_size_failure_closes_import(fixture_env, monkeypatch):
    repo_root, make = fixture_env
    path = make()
    monkeypatch.setattr(imp, "BUNDLE_SIZE_BYTES", 1)
    with pytest.raises(imp.EvidenceImportError, match="size mismatch"):
        imp.import_delivery(repo_root, path)


def test_missing_bundle_closes_import(fixture_env):
    repo_root, _make = fixture_env
    with pytest.raises(imp.EvidenceImportError, match="not found"):
        imp.import_delivery(repo_root, "/nonexistent/delivery.zip")


def test_canonical_request_hash_failure_closes_import(fixture_env, monkeypatch):
    repo_root, make = fixture_env
    path = make()
    monkeypatch.setattr(imp, "CANONICAL_REQUEST_SHA256", "1" * 64)
    with pytest.raises(imp.EvidenceImportError, match="canonical request"):
        imp.import_delivery(repo_root, path)


# --------------------------------------------------------------------------- #
# Fail-closed: raw artifact universe
# --------------------------------------------------------------------------- #

def test_raw_hash_mismatch_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        key = sorted(raw)[0]
        raw[key] = raw[key] + b" tampered"

    with pytest.raises(imp.EvidenceImportError, match="SHA256 mismatch"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_raw_artifact_without_manifest_row_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        raw[f"{ROOT}/raw_bounded/GHOST/ghost.json"] = b"{}"

    with pytest.raises(imp.EvidenceImportError, match="no\\s+manifest row"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_generic_endpoint_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        text = members[imp.MANIFEST_REL]
        members[imp.MANIFEST_REL] = text.replace(
            f"{HOST}/ClosingPrice/GetInstrumentCalendar/{INS['AAA']}",
            "https://cdn.tsetmc.com/api/ClosingPrice", 1)

    with pytest.raises(imp.EvidenceImportError, match="generic endpoint|non-exact"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_escrow_content_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        members[f"{ROOT}/raw_full_escrow/full.json"] = "{}"

    with pytest.raises(imp.EvidenceImportError, match="forbidden escrow"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_unmapped_artifact_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        lines = members[imp.ROLE_MAPPING_REL].splitlines(keepends=True)
        members[imp.ROLE_MAPPING_REL] = "".join(lines[:-1])

    with pytest.raises(imp.EvidenceImportError, match="no evidence role"):
        imp.import_delivery(repo_root, make(mutate=mutate))


# --------------------------------------------------------------------------- #
# Evidence-area semantics
# --------------------------------------------------------------------------- #

def test_point_calendar_evidence_exactness(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    cal = qc["calendar_point"]
    assert cal["point_date_requests"] == len(POINT_REQUESTS)
    assert cal["point_present_in_official_instrument_calendar"] == len(POINT_REQUESTS)
    assert cal["point_absent_from_official_instrument_calendar"] == 0
    assert cal["point_calendar_unresolved"] == 0
    assert cal["calendar_evidence_endpoint_exact"] is True


def test_point_calendar_absence_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        members[imp.CALENDAR_EVIDENCE_REL] = members[
            imp.CALENDAR_EVIDENCE_REL].replace(
                "true,https", "false,https", 1)

    with pytest.raises(imp.EvidenceImportError, match="membership is not exact"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_point_calendar_from_wrong_endpoint_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        members[imp.CALENDAR_EVIDENCE_REL] = members[
            imp.CALENDAR_EVIDENCE_REL].replace(
                f"{HOST}/ClosingPrice/GetInstrumentCalendar/{INS['AAA']},",
                f"{HOST}/ClosingPrice/GetClosingPriceDailyList/{INS['AAA']}/0,",
                1)

    with pytest.raises(imp.EvidenceImportError, match="GetInstrumentCalendar"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_range_calendar_vs_daily_set_comparison(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    rng = qc["calendar_range_vs_daily"]
    assert rng["range_requests"] == 1
    assert rng["calendar_vs_daily_date_sets_equal"] == 1
    assert rng["calendar_vs_daily_date_sets_differing"] == 0


def test_range_equality_claim_contradicting_counts_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        # Claim equality while reporting a date missing from the daily list.
        members[imp.CAL_VS_DAILY_REL] = members[imp.CAL_VS_DAILY_REL].replace(
            "2,2,true,0,0", "3,2,true,1,0", 1)

    with pytest.raises(imp.EvidenceImportError, match="contradicts the delivered"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_zero_byte_unresolved_handling(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    zb = qc["zero_byte"]
    assert zb["zero_byte_artifact_count"] == 1
    assert zb["zero_byte_status_counts"] == {"UNRESOLVED": 1}
    assert zb["zero_byte_success_or_cached_count"] == 0


def test_zero_byte_claiming_success_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        members[imp.MANIFEST_REL] = members[imp.MANIFEST_REL].replace(
            "UNRESOLVED", "SUCCESS", 1)

    with pytest.raises(imp.EvidenceImportError,
                       match="claim a successful"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_identity_unresolved_handling(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    ident = qc["identity"]
    assert ident["tickers_checked"] == len(TICKERS)
    assert ident["unresolved_count"] == len(TICKERS)
    assert ident["candidate_found_count"] == 0
    assert ident["none_found_count"] == 0
    assert ident["ins_code_zero_used_as_predecessor"] is False
    assert ident["histories_concatenated"] is False
    assert ident["absence_of_predecessor_treated_as_proof_of_none"] is False


def test_ins_code_zero_predecessor_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        members[imp.IDENTITY_EVIDENCE_REL] = members[
            imp.IDENTITY_EVIDENCE_REL].replace(
                "IRO1OTHER001,,,", "IRO1OTHER001,0,,", 1)

    with pytest.raises(imp.EvidenceImportError, match="insCode='0'"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_state_codes_stay_literal_and_unresolved(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    state = qc["state"]
    assert state["state_meaning_resolved_count"] == 0
    assert state["state_meaning_unresolved_count"] == state["state_artifacts_total"]
    assert state["third_party_state_definition_used"] is False
    assert state["state_code_semantics"].startswith("UNRESOLVED")


def test_no_final_period_evidence(fixture_env):
    repo_root, make = fixture_env
    qc = imp.import_delivery(repo_root, make())
    fw = qc["firewall"]
    assert fw["dEven_at_or_after_final_test_boundary_count"] == 0
    assert fw["maximum_bounded_dEven"] < imp.FINAL_TEST_FIREWALL_DEVEN
    assert fw["final_test_rows_accessed"] is False


def test_final_period_observation_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        key = [k for k in raw if k.endswith("closing_price_daily_point.json")][0]
        raw[key] = raw[key].replace(b'"dEven": 20160718', b'"dEven": 20210715')
        # keep the manifest hash honest so the FIREWALL is what fails
        import csv as _csv_mod
        rows = imp.read_csv_bytes(members[imp.MANIFEST_REL].encode())
        for row in rows:
            if row["raw_response_file"] in key:
                row["raw_response_sha256"] = hashlib.sha256(raw[key]).hexdigest()
        members[imp.MANIFEST_REL] = _csv(MANIFEST_COLUMNS, rows)

    with pytest.raises(imp.EvidenceImportError, match="firewall"):
        imp.import_delivery(repo_root, make(mutate=mutate))


def test_external_qc_disagreement_closes_import(fixture_env):
    repo_root, make = fixture_env

    def mutate(members, raw):
        qc = json.loads(members[imp.EXTERNAL_QC_REL])
        qc["calendar"]["POINT_present"] = 999
        members[imp.EXTERNAL_QC_REL] = json.dumps(qc)

    with pytest.raises(imp.EvidenceImportError, match="disagrees with the external"):
        imp.import_delivery(repo_root, make(mutate=mutate))


# --------------------------------------------------------------------------- #
# Derived evidence keeps facts and interpretation separate
# --------------------------------------------------------------------------- #

def test_derived_evidence_carries_no_scientific_decision(fixture_env):
    repo_root, make = fixture_env
    derived = imp.build_derived_evidence(repo_root, make())
    assert len(derived["point_rows"]) == len(POINT_REQUESTS)
    assert len(derived["range_rows"]) == 1
    assert len(derived["identity_rows"]) == len(TICKERS)
    for row in derived["point_rows"] + derived["range_rows"]:
        assert row["scientific_inclusion_decision"] == imp.NO_DECISION
    for row in derived["point_rows"]:
        assert row["official_calendar_member"] == "true"
        assert row["state_meaning"] == "UNRESOLVED"


# --------------------------------------------------------------------------- #
# Adjudication: contract -> evidence -> implementation
# --------------------------------------------------------------------------- #

def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def test_contract_trace_covers_every_question():
    trace = adj.build_contract_trace(_repo_root())
    assert {q["question_id"] for q in trace["questions"]} == set("ABCDEFG")
    assert trace["frozen_sources_modified_by_this_task"] is False
    assert trace["inference_beyond_frozen_text_performed"] is False
    for source in trace["frozen_sources"]:
        assert source["present"] is True
        assert len(source["sha256"]) == 64


def test_contract_trace_statements_are_traceable():
    trace = adj.build_contract_trace(_repo_root())
    allowed = {adj.EXPLICIT, adj.DERIVED, adj.AMBIGUOUS, adj.NOT_SPECIFIED}
    for st in trace["statements"]:
        assert st["implication_strength"] in allowed
        assert st["source_file"]
        assert st["semantic_implication"]


def test_frozen_contract_requires_zero_trade_day_to_remain_a_trading_day():
    trace = adj.build_contract_trace(_repo_root())
    by_id = {q["question_id"]: q for q in trace["questions"]}
    assert by_id["B"]["answer"] == "NO"
    assert by_id["C"]["answer"] == "NO"
    assert by_id["C"]["implication_strength"] in (adj.EXPLICIT, adj.DERIVED)


def test_adjudication_outcome_is_derived_only_from_the_trace():
    trace = adj.build_contract_trace(_repo_root())
    result = adj.adjudicate(trace)
    assert result["adjudication_outcome"] == adj.OUTCOME_A
    assert result["current_implementation_conformant"] == "YES"
    # A is genuinely unsettled by the frozen text and must be reported as such,
    # but it is not a GOVERNING question, so it cannot force outcome C.
    assert result["questions_not_unambiguously_answered"] == ["A"]
    assert result["governing_questions_not_unambiguously_answered"] == []
    assert result["nonoperative_ambiguities"] == ["A"]
    assert result["interpretation_chosen_to_obtain_PASS"] is False


def test_ambiguous_governing_question_forces_human_decision():
    """If any governing question were ambiguous, outcome C must be selected."""
    trace = copy.deepcopy(adj.build_contract_trace(_repo_root()))
    for q in trace["questions"]:
        if q["question_id"] == "C":
            q["implication_strength"] = adj.AMBIGUOUS
    result = adj.adjudicate(trace)
    assert result["adjudication_outcome"] == adj.OUTCOME_C
    assert result["current_implementation_conformant"] == "UNRESOLVED"
    assert result["canonical_gate_changed"] is False
    assert "C" in result["governing_questions_not_unambiguously_answered"]
    assert "C" in result["questions_not_unambiguously_answered"]
    assert "C" not in result["nonoperative_ambiguities"]


def test_no_canonical_gate_change_during_adjudication():
    trace = adj.build_contract_trace(_repo_root())
    result = adj.adjudicate(trace)
    assert result["canonical_gate_changed"] is False
    assert result["canonical_gate_status"] == "FAIL_M2_DATA_GATE"
    assert result["t0_changed"] is False
    assert result["t_star_changed"] is False
    assert result["thresholds_changed"] is False
    assert result["features_changed"] is False
    assert result["frozen_stage125_contract_modified"] is False
    assert result["equity_return_window_dropped"] is False


def test_no_model_invocation_in_the_adjudication_modules():
    """No model, prediction or final-test access may appear in these modules."""
    banned = (
        "sklearn", "xgboost", "lightgbm", "LogisticRegression", "fit(",
        "predict(", "roc_auc", "average_precision", "final_test_features",
    )
    for module in (imp, adj):
        source = open(module.__file__, encoding="utf-8").read()
        for token in banned:
            assert token not in source, f"{module.__name__} references {token}"


def test_counterfactual_readings_are_labelled_non_canonical():
    """Reading 2 must never be presented as a canonical or supported result."""
    assert adj.COUNTERFACTUAL_LABEL == "DIAGNOSTIC_COUNTERFACTUAL_NOT_CANONICAL_RESULT"
    assert set(adj.READINGS) == {adj.READING_1, adj.READING_2}
    assert adj.READINGS[adj.READING_1]({"traded_value_rial": 0}) is True
    assert adj.READINGS[adj.READING_2]({"traded_value_rial": 0}) is False
    assert adj.READINGS[adj.READING_2]({"traded_value_rial": 5}) is True


def test_published_counterfactual_artifact_does_not_replace_canonical():
    """The written artifact must keep the canonical Gate and coverage intact."""
    path = os.path.join(
        _repo_root(), "project/stage127",
        "stage127_m2_trading_day_semantics_counterfactuals.json")
    if not os.path.isfile(path):
        pytest.skip("counterfactual artifact not built in this checkout")
    data = json.load(open(path, encoding="utf-8"))
    assert data["label"] == adj.COUNTERFACTUAL_LABEL
    assert data["reading_2_supported_by_frozen_contract"] is False
    assert data["canonical_outputs_modified"] is False
    assert data["canonical_gate_status_unchanged"] == "FAIL_M2_DATA_GATE"
    assert data["canonical_coverage_unchanged"][
        "equity_return_window"]["usable"] == 269
    for reading in data.get("readings", {}).values():
        assert reading["model_fits"] == 0
        assert reading["predictions_generated"] == 0
        assert reading["final_test_access"] == 0
        assert reading["threshold_weakened"] is False


# --------------------------------------------------------------------------- #
# Post-adjudication internal consistency of the repository surfaces
# --------------------------------------------------------------------------- #

CANONICAL_COVERAGE_USABLE = {
    "equity_return_window": 269,
    "realized_volatility": 576,
    "amihud_illiquidity": 576,
}
CANONICAL_COMMON_SAMPLE = 269
CANONICAL_DEVELOPMENT_PAIRS = 666

#: Wording that must NOT survive anywhere in the adjudicated surfaces: the
#: external evidence is complete and the semantics question is closed.
STALE_PENDING_PHRASES = (
    "still pending",
    "remain pending",
    "remains pending",
    "not yet proven",
    "deferred to authoritative",
    "deferred to future external",
    "pending external TSETMC adjudication",
    "awaiting external",
)


def _load(rel: str):
    path = os.path.join(_repo_root(), rel)
    if not os.path.isfile(path):
        pytest.skip(f"{rel} not built in this checkout")
    return json.load(open(path, encoding="utf-8"))


def _root_cause_summary():
    return _load(
        "project/stage127/stage127_m2_equity_return_root_cause_summary.json")


def test_root_cause_pending_semantics_count_is_zero_after_adjudication():
    rc = _root_cause_summary()
    assert rc["pending_external_tsetmc_adjudication_count"] == 0
    assert rc["pending_breakdown"]["pending_endpoint_semantics"] == 0
    assert rc["pending_breakdown"]["pending_low_return_sequence_semantics"] == 0
    assert rc["unresolved_root_cause_count"] == 0
    assert rc["recoverable_due_to_proven_data_capture_defect"] == 0
    assert rc["external_evidence_still_awaited"] is False
    assert rc["semantics_adjudication_completed"] is True
    assert rc["adjudication_outcome"] == adj.OUTCOME_A


def test_root_cause_unavailable_pairs_fully_accounted_as_frozen_missingness():
    rc = _root_cause_summary()
    unavailable = rc["equity_return_unavailable_current"]
    assert rc["nonrecoverable_under_current_frozen_contract"] == unavailable
    breakdown = rc["nonrecoverable_breakdown"]
    endpoint = breakdown[
        "zero_trade_or_missing_adjusted_endpoint_under_frozen_sequence"]
    low_return = breakdown[
        "fewer_than_126_valid_returns_only_under_frozen_sequence"]
    assert endpoint + low_return + breakdown[
        "other_proven_nonrecoverable_categories"] == unavailable
    # Nothing is left in a limbo state between recoverable and nonrecoverable.
    assert (rc["recoverable_due_to_proven_data_capture_defect"]
            + rc["nonrecoverable_under_current_frozen_contract"]
            + rc["pending_external_tsetmc_adjudication_count"]
            + rc["unresolved_root_cause_count"]) == unavailable


def test_historical_zero_trade_label_is_marked_resolved():
    rc = _root_cause_summary()
    status = rc["zero_trade_endpoint_label_status"]
    assert status["label_historical"] is True
    assert status["adjudication_status"] == (
        "RESOLVED_BY_FROZEN_CONTRACT_ADJUDICATION")
    assert status["current_semantic_status"] == "TRUE_FROZEN_CONTRACT_MISSINGNESS"
    assert "stage127_m2_trading_day_semantics_adjudication.json" in (
        status["semantics_adjudicated_in"])


def test_no_stale_pending_prose_in_adjudicated_artifacts():
    """No adjudicated surface may still claim the question is open."""
    for rel in (
        "project/stage127/stage127_m2_equity_return_root_cause_summary.json",
        "project/stage127/stage127_m2_trading_day_semantics_adjudication.json",
        "project/stage127/stage127_m2_trading_day_semantics_contract_trace.json",
    ):
        path = os.path.join(_repo_root(), rel)
        if not os.path.isfile(path):
            pytest.skip(f"{rel} not built in this checkout")
        text = open(path, encoding="utf-8").read()
        for phrase in STALE_PENDING_PHRASES:
            assert phrase.lower() not in text.lower(), (
                f"{rel} still contains stale pending prose: {phrase!r}")


def test_question_A_is_not_specified_but_nonoperative():
    trace = adj.build_contract_trace(_repo_root())
    question_a = {q["question_id"]: q for q in trace["questions"]}["A"]
    assert question_a["implication_strength"] == adj.NOT_SPECIFIED
    result = adj.adjudicate(trace)
    assert "A" in result["questions_not_unambiguously_answered"]
    assert "A" in result["nonoperative_ambiguities"]
    assert "A" not in result["governing_questions_not_unambiguously_answered"]
    assert result["question_A_gap_is_operative"] is False
    assert result["question_A_implication_strength"] == adj.NOT_SPECIFIED
    assert result["adjudication_outcome"] == adj.OUTCOME_A


def test_part4_coverage_thresholds_not_represented_as_pending():
    """The modeling-path coverage thresholds are frozen by the Part 4 SAP."""
    trace = adj.build_contract_trace(_repo_root())
    # The historical Part 3 G10 statement must not be traced as semantics.
    assert not any(
        s["statement_id"].startswith("S14") for s in trace["statements"])
    for statement in trace["statements"]:
        assert "pending_user_approval" not in statement["verbatim"]
    provenance = trace["coverage_threshold_provenance"]
    assert provenance[
        "modeling_path_common_sample_threshold_currently_unfrozen"] is False
    frozen = provenance["frozen_modeling_path_thresholds"]
    assert frozen["candidate_valid_coverage_min"] == 0.8
    assert frozen["block_common_sample_coverage_min"] == 0.7
    assert frozen["replaces_pilot_G09_G14_for_modeling_path"] is True

    # …and the claim must match the frozen SAP itself, not just our summary.
    sap = _load(adj.ANALYSIS_PLAN_REL)["candidate_data_admission"]
    assert sap["candidate_valid_coverage_min"] == frozen[
        "candidate_valid_coverage_min"]
    assert sap["block_common_sample_coverage_min"] == frozen[
        "block_common_sample_coverage_min"]
    assert sap["replaces_pilot_G09_G14_for_modeling_path"] is True


def test_handoff_state_exposes_completed_adjudication():
    state = _load("project/docs/ai/handoff_state.json")
    assert state["stage127_m2_zero_trade_semantics_evidence_validated"] is True
    assert state["stage127_m2_zero_trade_semantics_bundle_sha256"] == (
        imp.BUNDLE_SHA256)
    assert state[
        "stage127_m2_trading_day_semantics_adjudication_completed"] is True
    assert state[
        "stage127_m2_trading_day_semantics_adjudication_outcome"] == adj.OUTCOME_A
    assert state["stage127_m2_current_implementation_conformant"] is True
    assert state["stage127_m2_semantics_pending_count"] == 0
    assert state["stage127_m2_semantics_canonical_gate_changed"] is False
    assert state["stage127_m2_semantics_model_fits"] == 0
    assert state["stage127_m2_semantics_final_test_access"] == 0


def test_handoff_state_keeps_m2_unauthorized():
    state = _load("project/docs/ai/handoff_state.json")
    assert state["stage127_m2_market_data_gate_status"] == "FAIL_M2_DATA_GATE"
    assert state["stage127_m2_block_admitted_for_modeling"] is False
    assert state["m2_incremental_evaluation_authorized"] is False
    assert state["m2_modeling_started"] is False


def test_current_state_carries_the_semantics_subsection():
    path = os.path.join(_repo_root(), "project/docs/ai/CURRENT_STATE.md")
    if not os.path.isfile(path):
        pytest.skip("CURRENT_STATE.md not present")
    text = open(path, encoding="utf-8").read()
    for needle in (
        "semantics adjudication",
        adj.OUTCOME_A,
        "427 / 427",
        "27 / 27",
        "FAIL_M2_DATA_GATE",
        "Human decision still required",
    ):
        assert needle in text, f"CURRENT_STATE.md missing: {needle!r}"


def test_canonical_gate_and_coverage_unchanged_across_surfaces():
    """The repair must not have moved a single canonical number."""
    decision = _load(
        "project/stage127/stage127_m2_market_data_gate_decision.json")
    assert decision["gate_status"] == "FAIL_M2_DATA_GATE"
    assert decision["modeling_performed"] is False
    assert decision["model_fit_calls"] == 0
    assert decision["prediction_calls"] == 0

    counterfactuals = _load(
        "project/stage127/"
        "stage127_m2_trading_day_semantics_counterfactuals.json")
    canonical = counterfactuals["canonical_coverage_unchanged"]
    for variable, usable in CANONICAL_COVERAGE_USABLE.items():
        assert canonical[variable]["usable"] == usable
        assert canonical[variable]["total"] == CANONICAL_DEVELOPMENT_PAIRS
    assert canonical["three_variable_common_sample"]["usable"] == (
        CANONICAL_COMMON_SAMPLE)
    assert counterfactuals["canonical_gate_status_unchanged"] == (
        "FAIL_M2_DATA_GATE")

    reading_1 = counterfactuals["readings"][adj.READING_1]
    assert reading_1["equity_return_window_usable"] == CANONICAL_COVERAGE_USABLE[
        "equity_return_window"]
    assert reading_1["three_variable_common_sample"] == CANONICAL_COMMON_SAMPLE
    assert counterfactuals["reading_1_reproduces_canonical_coverage"] is True

    rc = _root_cause_summary()
    assert rc["equity_return_usable_current"] == CANONICAL_COVERAGE_USABLE[
        "equity_return_window"]
    assert rc["development_pairs"] == CANONICAL_DEVELOPMENT_PAIRS
    assert rc["canonical_gate_status_unchanged"] == "FAIL_M2_DATA_GATE"


def test_no_model_or_final_test_access_anywhere_in_the_semantics_surfaces():
    for rel in (
        "project/stage127/stage127_m2_trading_day_semantics_adjudication.json",
        "project/stage127/"
        "stage127_m2_trading_day_semantics_counterfactuals.json",
        "project/stage127/stage127_m2_zero_trade_semantics_import_qc.json",
    ):
        data = _load(rel)
        flat = json.dumps(data)
        assert '"model_fits": 0' in flat or "model_fits" not in flat
        assert '"final_test_access": 0' in flat or "final_test_access" not in flat
    adjudication = _load(
        "project/stage127/stage127_m2_trading_day_semantics_adjudication.json")
    assert adjudication["model_fits"] == 0
    assert adjudication["predictions_generated"] == 0
    assert adjudication["final_test_access"] == 0
    assert adjudication["canonical_gate_changed"] is False
