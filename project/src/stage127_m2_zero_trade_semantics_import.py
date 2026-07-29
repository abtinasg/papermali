"""Stage127 — independent import of the zero-trade semantics evidence delivery.

The external delivery ``stage127_m2_zero_trade_semantics_full_delivery_v3.zip``
is treated as IMMUTABLE SOURCE EVIDENCE. This module never edits it and never
repairs it: it opens the ZIP, verifies its identity, and then re-derives every
claim the external party made directly from the raw artifacts inside it.

The delivered ``full_qc_report.json`` is COMPARED AGAINST, never trusted. Every
number recorded on the papermali side is recomputed here and every check fails
closed.

Nothing in this module decides trading-day semantics, joins a historical
identity, computes a scientific feature, fits a model, or reads a final-test
row. It imports factual evidence only; the semantics adjudication lives in
:mod:`stage127_m2_trading_day_semantics_adjudication`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import zipfile
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Identity of the authorized immutable delivery
# --------------------------------------------------------------------------- #

BUNDLE_FILENAME = "stage127_m2_zero_trade_semantics_full_delivery_v3.zip"
BUNDLE_SHA256 = (
    "5e05c3ad52d582236cc9c0bbea69dae520a02385921f3dd03792e6f65c917317"
)
BUNDLE_SIZE_BYTES = 1_955_293

ROOT = "full_delivery_v3"

#: SHA256 of the evidence-request package v2 generated earlier on PR #66. The
#: delivery is only admissible if it answered EXACTLY that request universe.
CANONICAL_REQUEST_SHA256 = (
    "cad5b6f9e97c8d11df65730773061b809b6494c4b7f5dcf9108694b9f6203c45"
)
CANONICAL_REQUEST_REL = (
    "project/stage127/external_retrieval/zero_trade_endpoint_evidence_request_v2/"
    "stage127_m2_zero_trade_endpoint_evidence_request_v2.zip"
)
CANONICAL_UNIQUE_REQUESTS_REL = "input/unique_evidence_requests.csv"
CANONICAL_OCCURRENCES_REL = "input/endpoint_occurrence_requests.csv"

FILLED = f"{ROOT}/filled"
AUDITS = f"{ROOT}/audits"

MANIFEST_REL = f"{FILLED}/raw_evidence_manifest.csv"
REQUEST_MAPPING_REL = f"{FILLED}/raw_artifact_request_mapping.csv"
ROLE_MAPPING_REL = f"{FILLED}/artifact_evidence_role_mapping.csv"
CALENDAR_EVIDENCE_REL = f"{FILLED}/endpoint_calendar_evidence.csv"
STATE_EVIDENCE_REL = f"{FILLED}/endpoint_state_evidence.csv"
TRADE_EVIDENCE_REL = f"{FILLED}/endpoint_trade_evidence.csv"
IDENTITY_EVIDENCE_REL = f"{FILLED}/historical_identity_evidence.csv"
CAL_VS_DAILY_REL = f"{AUDITS}/calendar_vs_daily_date_set_audit.csv"
TRADE_AUDIT_REL = f"{AUDITS}/trade_history_semantics_audit.csv"
IDENTITY_AUDIT_REL = f"{AUDITS}/identity_identifier_semantics_audit.csv"
EXTERNAL_QC_REL = f"{ROOT}/full_qc_report.json"

REQUIRED_BUNDLE_MEMBERS: tuple[str, ...] = (
    EXTERNAL_QC_REL,
    MANIFEST_REL,
    REQUEST_MAPPING_REL,
    ROLE_MAPPING_REL,
    CALENDAR_EVIDENCE_REL,
    STATE_EVIDENCE_REL,
    TRADE_EVIDENCE_REL,
    IDENTITY_EVIDENCE_REL,
    CAL_VS_DAILY_REL,
    TRADE_AUDIT_REL,
    IDENTITY_AUDIT_REL,
)

RAW_PREFIX = f"{ROOT}/raw_bounded/"

#: The delivery must NOT carry the external programmer's full-history escrow.
FORBIDDEN_PREFIXES: tuple[str, ...] = (f"{ROOT}/raw_full_escrow/",)

# --------------------------------------------------------------------------- #
# Development-only firewall
# --------------------------------------------------------------------------- #

#: No imported observation may touch the locked final-test period.
FINAL_TEST_FIREWALL_DEVEN = 20210101

# --------------------------------------------------------------------------- #
# Exact official TSETMC endpoints, declared independently of the delivery
# --------------------------------------------------------------------------- #

_INS = r"\d{6,}"
_DATE = r"\d{8}"
_HOST = r"https://cdn\.tsetmc\.com/api"

#: evidence_type -> the exact endpoint shapes admissible for it. A generic or
#: unrecognised endpoint fails the import closed.
ALLOWED_ENDPOINTS: dict[str, tuple[str, ...]] = {
    "INSTRUMENT_IDENTITY": (
        rf"^{_HOST}/Instrument/GetInstrumentIdentity/{_INS}$",
    ),
    "INSTRUMENT_HISTORY": (
        rf"^{_HOST}/Instrument/GetInstrumentHistory/{_INS}/{_DATE}$",
    ),
    "DAILY_CLOSING": (
        rf"^{_HOST}/ClosingPrice/GetClosingPriceDailyList/{_INS}/0$",
        rf"^{_HOST}/ClosingPrice/GetClosingPriceDaily/{_INS}/{_DATE}$",
    ),
    "CALENDAR": (
        rf"^{_HOST}/ClosingPrice/GetInstrumentCalendar/{_INS}$",
    ),
    "STATE": (
        rf"^{_HOST}/MarketData/GetInstrumentState/{_INS}/{_DATE}$",
    ),
    "TRADE_HISTORY": (
        rf"^{_HOST}/Trade/GetTradeHistory/{_INS}/{_DATE}/true$",
        rf"^{_HOST}/Trade/GetTradeHistory/{_INS}/{_DATE}/false$",
    ),
}

#: The grouped/ungrouped TradeHistory role is decided by the ENDPOINT, never by
#: the filename: a delivered basename may be generic, the endpoint may not be.
TRADE_ROLE_BY_ENDPOINT_SUFFIX = {"true": "TRADE_HISTORY_GROUPED",
                                 "false": "TRADE_HISTORY_UNGROUPED"}

#: A zero-byte raw artifact is admissible ONLY under these statuses. A zero-byte
#: SUCCESS or CACHED artifact is an unproven claim and fails the import.
ZERO_BYTE_ALLOWED_STATUS = ("UNRESOLVED", "HTTP_500")

VALID_RETRIEVAL_STATUS = ("SUCCESS", "CACHED", "UNRESOLVED", "HTTP_500")


class EvidenceImportError(Exception):
    """Raised whenever the delivery fails an independent papermali-side check."""


def _fail(message: str) -> None:
    raise EvidenceImportError(message)


# --------------------------------------------------------------------------- #
# Hashing / IO helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_bytes(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def csv_text(fieldnames: Iterable[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fieldnames), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


# --------------------------------------------------------------------------- #
# Step 0 — bundle identity (fails closed BEFORE anything is read)
# --------------------------------------------------------------------------- #

def verify_bundle_identity(bundle_path: str) -> dict[str, Any]:
    """Verify size and SHA256 of the delivery before opening it as evidence."""
    if not os.path.isfile(bundle_path):
        _fail(f"external delivery not found: {bundle_path}")
    size = os.path.getsize(bundle_path)
    if size != BUNDLE_SIZE_BYTES:
        _fail(
            f"external delivery size mismatch: expected {BUNDLE_SIZE_BYTES} "
            f"bytes, found {size}"
        )
    digest = sha256_file(bundle_path)
    if digest != BUNDLE_SHA256:
        _fail(
            f"external delivery SHA256 mismatch: expected {BUNDLE_SHA256}, "
            f"computed {digest}"
        )
    return {
        "bundle_filename": BUNDLE_FILENAME,
        "bundle_size_bytes": size,
        "bundle_sha256": digest,
        "bundle_size_verified": True,
        "bundle_sha256_verified": True,
        "bundle_treated_as_immutable_source_evidence": True,
        "bundle_edited_in_place": False,
        "bundle_stored_outside_repository": True,
    }


# --------------------------------------------------------------------------- #
# Step 1 — the canonical request universe, read from the repository, not the ZIP
# --------------------------------------------------------------------------- #

def load_canonical_requests(repo_root: str) -> dict[str, Any]:
    """Load the request universe from the repo-side v2 package.

    The delivery is only admissible if it answered exactly this universe, so the
    universe is read from the SHA-verified request package that PR #66 itself
    produced — never from the delivery.
    """
    path = os.path.join(repo_root, CANONICAL_REQUEST_REL)
    if not os.path.isfile(path):
        _fail(f"canonical request package missing: {CANONICAL_REQUEST_REL}")
    digest = sha256_file(path)
    if digest != CANONICAL_REQUEST_SHA256:
        _fail(
            "canonical request package SHA256 mismatch: expected "
            f"{CANONICAL_REQUEST_SHA256}, computed {digest}"
        )
    with zipfile.ZipFile(path) as zf:
        unique = read_csv_bytes(zf.read(CANONICAL_UNIQUE_REQUESTS_REL))
        occurrences = read_csv_bytes(zf.read(CANONICAL_OCCURRENCES_REL))
    by_id = {r["unique_request_id"]: r for r in unique}
    if len(by_id) != len(unique):
        _fail("canonical request package contains duplicate unique_request_id")
    return {
        "canonical_request_sha256": digest,
        "unique_requests": unique,
        "unique_requests_by_id": by_id,
        "occurrences": occurrences,
        "point_ids": {r["unique_request_id"] for r in unique
                      if r["request_type"] == "POINT_DATE"},
        "range_ids": {r["unique_request_id"] for r in unique
                      if r["request_type"] == "RANGE"},
        "tickers": {r["ticker"] for r in unique},
    }


# --------------------------------------------------------------------------- #
# Step 2 — structural admission of the ZIP
# --------------------------------------------------------------------------- #

def open_delivery(bundle_path: str) -> zipfile.ZipFile:
    zf = zipfile.ZipFile(bundle_path)
    names = set(zf.namelist())
    for forbidden in FORBIDDEN_PREFIXES:
        offenders = [n for n in names if n.startswith(forbidden)]
        if offenders:
            _fail(
                f"delivery carries forbidden escrow content under {forbidden}: "
                f"{len(offenders)} member(s)"
            )
    missing = [m for m in REQUIRED_BUNDLE_MEMBERS if m not in names]
    if missing:
        _fail(f"delivery is missing required members: {sorted(missing)}")
    return zf


# --------------------------------------------------------------------------- #
# Step 3 — raw artifact universe and per-artifact SHA256
# --------------------------------------------------------------------------- #

def validate_raw_universe(
    zf: zipfile.ZipFile, manifest: list[dict[str, str]],
) -> dict[str, Any]:
    """Re-hash every raw artifact and reconcile it against the manifest.

    Fails closed on: a manifest row without a file, a file without a manifest
    row, a duplicate artifact id, a duplicate raw path, or ANY SHA256 mismatch.
    """
    raw_members = {
        n for n in zf.namelist()
        if n.startswith(RAW_PREFIX) and not n.endswith("/")
    }
    ids = [r["evidence_artifact_id"] for r in manifest]
    if len(set(ids)) != len(ids):
        _fail("raw_evidence_manifest contains duplicate evidence_artifact_id")
    paths = [r["raw_response_file"] for r in manifest]
    if len(set(paths)) != len(paths):
        _fail("raw_evidence_manifest contains duplicate raw_response_file")

    declared = {f"{ROOT}/{p}" for p in paths}
    orphan_files = raw_members - declared
    if orphan_files:
        _fail(
            f"{len(orphan_files)} raw artifact(s) exist in the ZIP with no "
            f"manifest row, e.g. {sorted(orphan_files)[:3]}"
        )
    missing_files = declared - raw_members
    if missing_files:
        _fail(
            f"{len(missing_files)} manifest row(s) reference a raw artifact "
            f"absent from the ZIP, e.g. {sorted(missing_files)[:3]}"
        )

    verified = 0
    mismatches: list[str] = []
    zero_byte: list[dict[str, str]] = []
    sizes: dict[str, int] = {}
    for row in manifest:
        member = f"{ROOT}/{row['raw_response_file']}"
        payload = zf.read(member)
        sizes[row["evidence_artifact_id"]] = len(payload)
        digest = sha256_bytes(payload)
        if digest != row["raw_response_sha256"]:
            mismatches.append(row["evidence_artifact_id"])
        else:
            verified += 1
        if not payload:
            zero_byte.append(row)
    if mismatches:
        _fail(
            f"{len(mismatches)} raw artifact SHA256 mismatch(es), e.g. "
            f"{mismatches[:3]}"
        )

    bad_status = sorted({
        r["retrieval_status"] for r in manifest
        if r["retrieval_status"] not in VALID_RETRIEVAL_STATUS
    })
    if bad_status:
        _fail(f"unrecognised retrieval_status value(s): {bad_status}")

    bad_bounded = [r["evidence_artifact_id"] for r in manifest
                   if r["bounded_response"].strip().lower() != "true"]
    if bad_bounded:
        _fail(
            f"{len(bad_bounded)} manifest row(s) are not marked bounded_response"
        )

    return {
        "raw_artifact_count": len(raw_members),
        "manifest_rows": len(manifest),
        "unique_raw_response_file_count": len(set(paths)),
        "unique_evidence_artifact_id_count": len(set(ids)),
        "sha256_recomputed_count": len(manifest),
        "sha256_verified_count": verified,
        "sha256_mismatch_count": len(mismatches),
        "zero_byte_rows": zero_byte,
        "artifact_sizes": sizes,
    }


def validate_endpoints(manifest: list[dict[str, str]]) -> dict[str, Any]:
    """Every source_endpoint must be an exact official TSETMC API path."""
    counts: dict[str, int] = {}
    offenders: list[str] = []
    for row in manifest:
        etype, endpoint = row["evidence_type"], row["source_endpoint"]
        patterns = ALLOWED_ENDPOINTS.get(etype)
        if patterns is None:
            _fail(f"unrecognised evidence_type: {etype!r}")
        if not any(re.match(p, endpoint) for p in patterns):
            offenders.append(f"{row['evidence_artifact_id']}:{endpoint}")
        counts[etype] = counts.get(etype, 0) + 1
    if offenders:
        _fail(
            f"{len(offenders)} artifact(s) carry a non-exact or generic "
            f"endpoint, e.g. {offenders[:3]}"
        )
    return {
        "evidence_type_counts": dict(sorted(counts.items())),
        "exact_endpoint_verified_count": len(manifest),
        "generic_endpoint_count": 0,
    }


def validate_mappings(
    manifest: list[dict[str, str]],
    request_mapping: list[dict[str, str]],
    role_mapping: list[dict[str, str]],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile artifact -> request and artifact -> evidence-role mappings."""
    artifact_ids = {r["evidence_artifact_id"] for r in manifest}
    by_id = {r["evidence_artifact_id"]: r for r in manifest}

    mapped = {r["evidence_artifact_id"] for r in request_mapping}
    if mapped != artifact_ids:
        _fail(
            "raw_artifact_request_mapping does not cover the artifact universe "
            f"exactly (missing={len(artifact_ids - mapped)}, "
            f"unknown={len(mapped - artifact_ids)})"
        )
    if len(request_mapping) != len(mapped):
        _fail("raw_artifact_request_mapping contains duplicate artifact rows")

    known = canonical["point_ids"] | canonical["range_ids"]
    unknown_request = sorted({
        r["unique_request_id"] for r in request_mapping
        if r["unique_request_id"] and r["unique_request_id"] not in known
    })
    if unknown_request:
        _fail(
            "raw_artifact_request_mapping references request ids outside the "
            f"canonical universe: {unknown_request[:3]}"
        )

    roled = {r["evidence_artifact_id"] for r in role_mapping}
    unmapped = artifact_ids - roled
    if unmapped:
        _fail(f"{len(unmapped)} artifact(s) carry no evidence role")
    unknown_roled = roled - artifact_ids
    if unknown_roled:
        _fail(f"{len(unknown_roled)} role row(s) reference an unknown artifact")

    role_counts: dict[str, int] = {}
    for row in role_mapping:
        role_counts[row["evidence_role"]] = role_counts.get(
            row["evidence_role"], 0) + 1
    if "TRADE_HISTORY" in role_counts:
        _fail("generic TRADE_HISTORY role present; grouping must be explicit")

    # The grouped/ungrouped role must agree with the endpoint, not the filename.
    roles_by_artifact: dict[str, set[str]] = {}
    for row in role_mapping:
        roles_by_artifact.setdefault(
            row["evidence_artifact_id"], set()).add(row["evidence_role"])
    trade_mismatch: list[str] = []
    generic_basenames = 0
    for aid, row in by_id.items():
        if row["evidence_type"] != "TRADE_HISTORY":
            continue
        expected = TRADE_ROLE_BY_ENDPOINT_SUFFIX[row["source_endpoint"].rsplit("/", 1)[1]]
        if expected not in roles_by_artifact.get(aid, set()):
            trade_mismatch.append(aid)
        base = os.path.basename(row["raw_response_file"])
        if "grouped" not in base and "ungrouped" not in base:
            generic_basenames += 1
    if trade_mismatch:
        _fail(
            f"{len(trade_mismatch)} TradeHistory artifact(s) carry a role that "
            f"contradicts their endpoint, e.g. {trade_mismatch[:3]}"
        )

    return {
        "request_mapping_rows": len(request_mapping),
        "role_mapping_rows": len(role_mapping),
        "unmapped_artifact_count": 0,
        "artifacts_without_role_count": 0,
        "generic_trade_history_role_count": 0,
        "role_counts": dict(sorted(role_counts.items())),
        "trade_history_role_derived_from_endpoint": True,
        "trade_history_generic_basename_count": generic_basenames,
    }


# --------------------------------------------------------------------------- #
# Step 4 — evidence-area validation
# --------------------------------------------------------------------------- #

def validate_point_calendar(
    calendar_rows: list[dict[str, str]], canonical: dict[str, Any],
) -> dict[str, Any]:
    """Every POINT_DATE endpoint date must be an InstrumentCalendar member.

    Membership is only accepted when the evidence endpoint is the official
    ``ClosingPrice/GetInstrumentCalendar`` endpoint.
    """
    by_id = {r["unique_request_id"]: r for r in calendar_rows}
    if len(by_id) != len(calendar_rows):
        _fail("endpoint_calendar_evidence contains duplicate request rows")
    missing = canonical["point_ids"] - set(by_id)
    if missing:
        _fail(f"{len(missing)} POINT_DATE request(s) carry no calendar evidence")

    present = absent = unresolved = 0
    bad_endpoint: list[str] = []
    for rid in sorted(canonical["point_ids"]):
        row = by_id[rid]
        endpoint = row["calendar_evidence_endpoint"]
        if not re.match(
            rf"^{_HOST}/ClosingPrice/GetInstrumentCalendar/{_INS}$", endpoint
        ):
            bad_endpoint.append(rid)
        flag = row["in_instrument_trading_calendar"].strip().lower()
        if flag == "true":
            present += 1
        elif flag == "false":
            absent += 1
        else:
            unresolved += 1
    if bad_endpoint:
        _fail(
            "calendar evidence for POINT_DATE requests must come from "
            f"ClosingPrice/GetInstrumentCalendar; offenders: {bad_endpoint[:3]}"
        )
    if present != len(canonical["point_ids"]) or absent or unresolved:
        _fail(
            "POINT_DATE calendar membership is not exact: "
            f"present={present}, absent={absent}, unresolved={unresolved}, "
            f"requested={len(canonical['point_ids'])}"
        )
    return {
        "point_date_requests": len(canonical["point_ids"]),
        "point_present_in_official_instrument_calendar": present,
        "point_absent_from_official_instrument_calendar": absent,
        "point_calendar_unresolved": unresolved,
        "calendar_evidence_endpoint_exact": True,
    }


def validate_range_calendar_vs_daily(
    rows: list[dict[str, str]], canonical: dict[str, Any],
) -> dict[str, Any]:
    """For every RANGE request compare the calendar and daily-list date sets."""
    by_id = {r["unique_request_id"]: r for r in rows}
    if set(by_id) != canonical["range_ids"]:
        _fail(
            "calendar_vs_daily_date_set_audit does not cover the RANGE request "
            f"universe exactly (rows={len(by_id)}, "
            f"ranges={len(canonical['range_ids'])})"
        )
    equal = 0
    differing: list[str] = []
    for rid, row in sorted(by_id.items()):
        same = row["date_sets_equal"].strip().lower() == "true"
        cal_n = int(row["calendar_date_count"])
        day_n = int(row["daily_date_count"])
        miss = int(row["missing_in_daily_count"])
        extra = int(row["extra_in_daily_count"])
        # Re-derive the equality claim from the counts rather than trusting it.
        derived = cal_n == day_n and miss == 0 and extra == 0
        if same != derived:
            _fail(
                f"{rid}: date_sets_equal={same} contradicts the delivered "
                f"counts (calendar={cal_n}, daily={day_n}, missing={miss}, "
                f"extra={extra})"
            )
        if derived:
            equal += 1
        else:
            differing.append(rid)
    return {
        "range_requests": len(canonical["range_ids"]),
        "calendar_vs_daily_date_sets_equal": equal,
        "calendar_vs_daily_date_sets_differing": len(differing),
        "differing_range_request_ids": differing,
    }


def validate_state(
    manifest: list[dict[str, str]], state_rows: list[dict[str, str]],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    """Count STATE evidence and keep the literal state codes UNINTERPRETED."""
    artifacts = [r for r in manifest if r["evidence_type"] == "STATE"]
    by_request: dict[str, int] = {}
    for row in artifacts:
        by_request[row["unique_request_id"]] = (
            by_request.get(row["unique_request_id"], 0) + 1)
    point = sum(n for rid, n in by_request.items() if rid in canonical["point_ids"])
    rng = sum(n for rid, n in by_request.items() if rid in canonical["range_ids"])
    # A RANGE row carries one literal code per sampled STATE artifact, so the
    # code counts are per artifact and must sum to the STATE artifact universe.
    codes: dict[str, int] = {}
    for row in state_rows:
        found = _STATE_CODE_RE.findall(row["instrument_state"])
        for code in found or ["UNRESOLVED"]:
            key = f"'{code}'" if code != "UNRESOLVED" else code
            codes[key] = codes.get(key, 0) + 1
    if sum(codes.values()) != len(artifacts):
        _fail(
            f"literal state codes ({sum(codes.values())}) do not account for "
            f"the STATE artifact universe ({len(artifacts)})"
        )
    return {
        "state_artifacts_point": point,
        "state_artifacts_range": rng,
        "state_artifacts_total": len(artifacts),
        "state_request_rows": len(state_rows),
        "literal_state_code_counts": dict(sorted(codes.items())),
        "state_meaning_resolved_count": 0,
        "state_meaning_unresolved_count": len(artifacts),
        "state_code_semantics": "UNRESOLVED_NO_FROZEN_AUTHORITATIVE_MAPPING",
        "third_party_state_definition_used": False,
    }


def validate_trade(
    manifest: list[dict[str, str]], trade_audit: list[dict[str, str]],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    """Count grouped/ungrouped TradeHistory evidence from the endpoints."""
    artifacts = [r for r in manifest if r["evidence_type"] == "TRADE_HISTORY"]
    grouped = [r for r in artifacts if r["source_endpoint"].endswith("/true")]
    ungrouped = [r for r in artifacts if r["source_endpoint"].endswith("/false")]
    point_grouped = sum(
        1 for r in grouped if r["unique_request_id"] in canonical["point_ids"])
    range_grouped = sum(
        1 for r in grouped if r["unique_request_id"] in canonical["range_ids"])
    range_ungrouped = sum(
        1 for r in ungrouped if r["unique_request_id"] in canonical["range_ids"])
    # The audit records a literal field comparison per row; a row whose observed
    # property states an inequality is a daily-vs-ungrouped mismatch.
    mismatch = [r for r in trade_audit if "!=" in r["observed_pilot_property"]]
    return {
        "trade_history_artifacts_total": len(artifacts),
        "trade_history_grouped_total": len(grouped),
        "trade_history_ungrouped_total": len(ungrouped),
        "trade_history_point_grouped": point_grouped,
        "trade_history_range_grouped": range_grouped,
        "trade_history_range_ungrouped": range_ungrouped,
        "trade_audit_rows": len(trade_audit),
        "daily_vs_ungrouped_mismatch_rows": len(mismatch),
        "daily_vs_ungrouped_mismatch_request_ids": [
            r["unique_request_id"] for r in mismatch],
    }


def validate_identity(
    identity_rows: list[dict[str, str]], audit_rows: list[dict[str, str]],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    """Preserve historical-identity uncertainty explicitly.

    A ticker whose predecessor was not demonstrated stays UNRESOLVED. Absence of
    a demonstrated predecessor is never recorded as proof that none exists, and
    ``insCode == "0"`` is never accepted as a predecessor.
    """
    tickers = {r["ticker"] for r in audit_rows}
    if tickers != canonical["tickers"]:
        _fail(
            "identity audit does not cover the affected ticker universe exactly "
            f"(audit={len(tickers)}, requested={len(canonical['tickers'])})"
        )
    statuses: dict[str, int] = {}
    for row in identity_rows:
        statuses[row["evidence_status"]] = statuses.get(row["evidence_status"], 0) + 1

    # Identifier equality is a per-ticker statement about the CURRENT snapshot;
    # the historical probe rows are separate evidence and are not counted here.
    current = [r for r in audit_rows
               if r["evidence_status"] == "current_identity_snapshot"]
    if len({r["ticker"] for r in current}) != len(current):
        _fail("identity audit carries more than one current snapshot per ticker")
    isin_eq_instrument = sum(
        1 for r in current
        if r["same_request_ISIN_as_instrumentID"].strip().lower() == "true")
    isin_eq_cisin = sum(
        1 for r in current
        if r["same_request_ISIN_as_cIsin"].strip().lower() == "true")

    zero_used = [
        r for r in identity_rows
        if str(r.get("candidate_historical_InsCode", "")).strip() == "0"
    ]
    if zero_used:
        _fail(
            f"{len(zero_used)} identity row(s) use insCode='0' as a predecessor"
        )
    claimed = [
        r for r in identity_rows
        if r.get("evidence_status") == "CANDIDATE_FOUND"
    ]
    return {
        "tickers_checked": len(tickers),
        "identity_evidence_rows": len(identity_rows),
        "identity_audit_rows": len(audit_rows),
        "current_identity_snapshot_rows": len(current),
        "historical_probe_rows": len(audit_rows) - len(current),
        "evidence_status_counts": dict(sorted(statuses.items())),
        "unresolved_count": statuses.get("UNRESOLVED", 0),
        "none_found_count": statuses.get("NONE_FOUND", 0),
        "candidate_found_count": len(claimed),
        "request_ISIN_equals_raw_instrumentID": isin_eq_instrument,
        "request_ISIN_equals_raw_cIsin": isin_eq_cisin,
        "ins_code_zero_used_as_predecessor": False,
        "histories_concatenated": False,
        "identity_uncertainty_preserved": True,
        "absence_of_predecessor_treated_as_proof_of_none": False,
    }


def validate_zero_byte(
    zero_byte_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """A zero-byte artifact may never be presented as a successful retrieval."""
    counts: dict[str, int] = {}
    types: dict[str, int] = {}
    for row in zero_byte_rows:
        counts[row["retrieval_status"]] = counts.get(row["retrieval_status"], 0) + 1
        types[row["evidence_type"]] = types.get(row["evidence_type"], 0) + 1
    offenders = [
        r["evidence_artifact_id"] for r in zero_byte_rows
        if r["retrieval_status"] not in ZERO_BYTE_ALLOWED_STATUS
    ]
    if offenders:
        _fail(
            f"{len(offenders)} zero-byte artifact(s) claim a successful "
            f"retrieval status, e.g. {offenders[:3]}"
        )
    return {
        "zero_byte_artifact_count": len(zero_byte_rows),
        "zero_byte_status_counts": dict(sorted(counts.items())),
        "zero_byte_evidence_type_counts": dict(sorted(types.items())),
        "zero_byte_success_or_cached_count": 0,
        "zero_byte_semantics": (
            "UNRESOLVED means retrieval was not demonstrated; HTTP_500 is a "
            "trusted observed upstream failure. Neither is evidence of absence."
        ),
    }


_STATE_CODE_RE = re.compile(r"state_code='(..)'")

_DEVEN_RE = re.compile(rb'"dEven"\s*:\s*(\d+)')


def validate_firewall(zf: zipfile.ZipFile, manifest: list[dict[str, str]]) -> dict[str, Any]:
    """Structurally prove no imported observation touches the final-test period.

    ``dEven`` values are scanned out of the raw payloads themselves, not out of
    the delivered summaries.
    """
    max_deven = 0
    offenders: list[str] = []
    scanned = 0
    for row in manifest:
        payload = zf.read(f"{ROOT}/{row['raw_response_file']}")
        if not payload:
            continue
        scanned += 1
        for match in _DEVEN_RE.finditer(payload):
            value = int(match.group(1))
            if value <= 0:
                continue  # a null/sentinel date carries no observation
            max_deven = max(max_deven, value)
            if value >= FINAL_TEST_FIREWALL_DEVEN:
                offenders.append(f"{row['evidence_artifact_id']}:{value}")
    if offenders:
        _fail(
            f"{len(offenders)} raw observation(s) breach the development-only "
            f"firewall dEven < {FINAL_TEST_FIREWALL_DEVEN}, e.g. {offenders[:3]}"
        )
    return {
        "artifacts_scanned_for_dEven": scanned,
        "maximum_bounded_dEven": max_deven,
        "dEven_at_or_after_final_test_boundary_count": 0,
        "final_test_firewall_boundary_dEven": FINAL_TEST_FIREWALL_DEVEN,
        "final_test_rows_accessed": False,
    }


# --------------------------------------------------------------------------- #
# Step 5 — full independent import
# --------------------------------------------------------------------------- #

def import_delivery(repo_root: str, bundle_path: str) -> dict[str, Any]:
    """Run every independent check and return the papermali-side QC result."""
    provenance = verify_bundle_identity(bundle_path)
    canonical = load_canonical_requests(repo_root)

    with open_delivery(bundle_path) as zf:
        manifest = read_csv_bytes(zf.read(MANIFEST_REL))
        request_mapping = read_csv_bytes(zf.read(REQUEST_MAPPING_REL))
        role_mapping = read_csv_bytes(zf.read(ROLE_MAPPING_REL))
        calendar_rows = read_csv_bytes(zf.read(CALENDAR_EVIDENCE_REL))
        state_rows = read_csv_bytes(zf.read(STATE_EVIDENCE_REL))
        trade_rows = read_csv_bytes(zf.read(TRADE_EVIDENCE_REL))
        identity_rows = read_csv_bytes(zf.read(IDENTITY_EVIDENCE_REL))
        cal_vs_daily = read_csv_bytes(zf.read(CAL_VS_DAILY_REL))
        trade_audit = read_csv_bytes(zf.read(TRADE_AUDIT_REL))
        identity_audit = read_csv_bytes(zf.read(IDENTITY_AUDIT_REL))
        external_qc = json.loads(zf.read(EXTERNAL_QC_REL).decode("utf-8"))

        raw = validate_raw_universe(zf, manifest)
        endpoints = validate_endpoints(manifest)
        mappings = validate_mappings(
            manifest, request_mapping, role_mapping, canonical)
        point_cal = validate_point_calendar(calendar_rows, canonical)
        range_cal = validate_range_calendar_vs_daily(cal_vs_daily, canonical)
        state = validate_state(manifest, state_rows, canonical)
        trade = validate_trade(manifest, trade_audit, canonical)
        identity = validate_identity(identity_rows, identity_audit, canonical)
        zero_byte = validate_zero_byte(raw.pop("zero_byte_rows"))
        firewall = validate_firewall(zf, manifest)

    raw.pop("artifact_sizes", None)
    requests_block = {
        "canonical_unique_requests": len(canonical["unique_requests"]),
        "canonical_point_date_requests": len(canonical["point_ids"]),
        "canonical_range_requests": len(canonical["range_ids"]),
        "canonical_endpoint_occurrences": len(canonical["occurrences"]),
        "canonical_affected_tickers": len(canonical["tickers"]),
        "delivery_answered_canonical_universe_exactly": True,
        "canonical_request_sha256": canonical["canonical_request_sha256"],
    }

    result = {
        "provenance": provenance,
        "requests": requests_block,
        "raw": raw,
        "endpoints": endpoints,
        "mappings": mappings,
        "calendar_point": point_cal,
        "calendar_range_vs_daily": range_cal,
        "state": state,
        "trade": trade,
        "identity": identity,
        "zero_byte": zero_byte,
        "firewall": firewall,
        "external_qc_report_trusted": False,
        "external_qc_report_compared": True,
        "scientific_actions": {
            "trading_day_semantics_decided_here": False,
            "identity_join_performed": False,
            "feature_engineering_performed": False,
            "model_fits": 0,
            "predictions_generated": 0,
            "final_test_access": 0,
            "canonical_gate_modified": False,
        },
        "validator_pass": True,
    }
    result["external_qc_comparison"] = compare_against_external_qc(
        result, external_qc)
    return result


# --------------------------------------------------------------------------- #
# Step 6 — compare (never defer to) the external QC report
# --------------------------------------------------------------------------- #

#: papermali-derived value -> the external claim it must agree with.
_QC_COMPARISONS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("requests_total", ("requests", "canonical_unique_requests"),
     ("requests", "total")),
    ("requests_point_date", ("requests", "canonical_point_date_requests"),
     ("requests", "POINT_DATE")),
    ("requests_range", ("requests", "canonical_range_requests"),
     ("requests", "RANGE")),
    ("affected_tickers", ("requests", "canonical_affected_tickers"),
     ("requests", "affected_tickers")),
    ("raw_artifact_count", ("raw", "raw_artifact_count"),
     ("raw", "raw_artifact_count")),
    ("manifest_rows", ("raw", "manifest_rows"), ("raw", "manifest_rows")),
    ("unique_raw_files", ("raw", "unique_raw_response_file_count"),
     ("raw", "unique_raw_response_file_count")),
    ("sha256_verified", ("raw", "sha256_verified_count"),
     ("raw", "SHA256_verified")),
    ("point_calendar_present",
     ("calendar_point", "point_present_in_official_instrument_calendar"),
     ("calendar", "POINT_present")),
    ("point_calendar_absent",
     ("calendar_point", "point_absent_from_official_instrument_calendar"),
     ("calendar", "POINT_absent")),
    ("calendar_vs_daily_equal",
     ("calendar_range_vs_daily", "calendar_vs_daily_date_sets_equal"),
     ("calendar", "calendar_vs_daily_equal")),
    ("state_point", ("state", "state_artifacts_point"), ("state", "POINT")),
    ("state_range", ("state", "state_artifacts_range"), ("state", "RANGE")),
    ("state_total", ("state", "state_artifacts_total"), ("state", "TOTAL")),
    ("state_literal_code_counts", ("state", "literal_state_code_counts"),
     ("state", "literal_code_counts")),
    ("state_meaning_unresolved", ("state", "state_meaning_unresolved_count"),
     ("state", "state_meaning_unresolved_count")),
    ("identity_unresolved", ("identity", "unresolved_count"),
     ("identity", "UNRESOLVED")),
    ("identity_none_found", ("identity", "none_found_count"),
     ("identity", "NONE_FOUND")),
    ("trade_point_grouped", ("trade", "trade_history_point_grouped"),
     ("trade", "POINT_grouped")),
    ("trade_range_grouped", ("trade", "trade_history_range_grouped"),
     ("trade", "RANGE_grouped")),
    ("trade_range_ungrouped", ("trade", "trade_history_range_ungrouped"),
     ("trade", "RANGE_ungrouped")),
    ("trade_artifacts_total", ("trade", "trade_history_artifacts_total"),
     ("trade", "TradeHistory_artifacts_total")),
    ("trade_audit_rows", ("trade", "trade_audit_rows"),
     ("trade", "trade_audit_rows")),
    ("daily_vs_ungrouped_mismatch",
     ("trade", "daily_vs_ungrouped_mismatch_rows"),
     ("trade", "daily_vs_ungrouped_mismatch")),
    ("identity_tickers", ("identity", "tickers_checked"),
     ("identity", "tickers_checked")),
    ("identity_candidate_found", ("identity", "candidate_found_count"),
     ("identity", "CANDIDATE_FOUND")),
    ("identity_isin_eq_instrumentID",
     ("identity", "request_ISIN_equals_raw_instrumentID"),
     ("identity", "request_ISIN_vs_instrumentID_matches")),
    ("identity_isin_eq_cIsin", ("identity", "request_ISIN_equals_raw_cIsin"),
     ("identity", "request_ISIN_vs_cIsin_matches")),
    ("zero_byte_total", ("zero_byte", "zero_byte_artifact_count"),
     ("empty_raw", "zero_byte_artifacts")),
    ("zero_byte_success_or_cached",
     ("zero_byte", "zero_byte_success_or_cached_count"),
     ("empty_raw", "SUCCESS_CACHED_empty_without_trusted_provenance")),
    ("maximum_bounded_dEven", ("firewall", "maximum_bounded_dEven"),
     ("firewall", "maximum_bounded_dEven")),
    ("final_period_observations",
     ("firewall", "dEven_at_or_after_final_test_boundary_count"),
     ("firewall", "dEven_gte_20210101_count")),
    ("request_mapping_rows", ("mappings", "request_mapping_rows"),
     ("roles", "request_mapping_rows")),
    ("role_mapping_rows", ("mappings", "role_mapping_rows"),
     ("roles", "role_mapping_rows")),
    ("unmapped_artifacts", ("mappings", "unmapped_artifact_count"),
     ("roles", "unmapped_artifact_count")),
)


def _dig(obj: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    return obj


def compare_against_external_qc(
    derived: dict[str, Any], external_qc: dict[str, Any],
) -> dict[str, Any]:
    """Compare papermali-derived counts against the external claims.

    The external report is EVIDENCE, not authority: a disagreement is recorded
    and fails the import closed rather than being silently repaired.
    """
    rows: list[dict[str, Any]] = []
    disagreements: list[str] = []
    for name, own_path, ext_path in _QC_COMPARISONS:
        own = _dig(derived, own_path)
        ext = _dig(external_qc, ext_path)
        agree = own == ext
        if not agree:
            disagreements.append(f"{name}: papermali={own!r} external={ext!r}")
        rows.append({
            "comparison": name,
            "papermali_derived_value": own,
            "external_claimed_value": ext,
            "agree": agree,
        })
    if disagreements:
        _fail(
            "papermali-derived evidence disagrees with the external QC report: "
            + "; ".join(disagreements)
        )
    return {
        "comparisons": rows,
        "comparison_count": len(rows),
        "disagreement_count": 0,
        "external_report_treated_as_authority": False,
        "external_bundle_silently_repaired": False,
    }


# --------------------------------------------------------------------------- #
# Step 7 — papermali-side derived evidence artifacts
# --------------------------------------------------------------------------- #

#: Factual columns only. Nothing in these rows is a scientific inclusion
#: decision: interpretation is kept strictly separate from evidence.
POINT_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "ticker",
    "InsCode",
    "endpoint_date",
    "endpoint_occurrence_count",
    "official_calendar_member",
    "calendar_evidence_endpoint",
    "daily_row_present",
    "daily_closing_evidence_endpoint",
    "zTotTran",
    "qTotTran5J",
    "qTotCap",
    "raw_close",
    "zero_trade",
    "trade_history_records",
    "trade_history_empty",
    "trade_evidence_endpoint",
    "literal_state_code",
    "state_meaning",
    "state_evidence_endpoint",
    "adjusted_close_availability",
    "scientific_inclusion_decision",
)

RANGE_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "unique_request_id",
    "ticker",
    "InsCode",
    "range_start_date",
    "range_end_date",
    "calendar_row_count",
    "daily_row_count",
    "calendar_vs_daily_date_sets_equal",
    "missing_in_daily_count",
    "extra_in_daily_count",
    "zero_trade_row_count",
    "positive_trade_row_count",
    "state_sample_artifact_count",
    "literal_state_codes_sampled",
    "trade_diagnostic_rows",
    "daily_vs_ungrouped_mismatch_rows",
    "scientific_inclusion_decision",
)

IDENTITY_EVIDENCE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "request_InsCode",
    "request_ISIN",
    "current_raw_instrumentID",
    "current_raw_cIsin",
    "request_ISIN_equals_instrumentID",
    "request_ISIN_equals_cIsin",
    "historical_probe_count",
    "candidate_historical_InsCode",
    "evidence_status",
    "histories_concatenated",
    "ins_code_zero_used_as_predecessor",
)

#: The literal evidence carries no scientific verdict; the verdict is recorded
#: only in the adjudication artifact.
NO_DECISION = "NOT_A_SCIENTIFIC_DECISION_SEE_ADJUDICATION_ARTIFACT"

_ZERO_TRADE_RE = re.compile(r"zero_trade_rows=(\d+)")
_POSITIVE_TRADE_RE = re.compile(r"positive_trade_rows=(\d+)")


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_point_evidence_rows(
    canonical: dict[str, Any],
    calendar_rows: list[dict[str, str]],
    state_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
    manifest: list[dict[str, str]],
    occurrences: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """One factual row per unique POINT_DATE request."""
    cal = {r["unique_request_id"]: r for r in calendar_rows}
    state = {r["unique_request_id"]: r for r in state_rows}
    trade = {r["unique_request_id"]: r for r in trade_rows}
    daily_endpoint: dict[str, str] = {}
    for row in manifest:
        if row["evidence_type"] == "DAILY_CLOSING" and "GetClosingPriceDaily/" in row["source_endpoint"]:
            daily_endpoint[row["unique_request_id"]] = row["source_endpoint"]
    adjusted: dict[tuple[str, str], str] = {
        (o["ticker"], o["endpoint_date"]): o["adjusted_close_status"]
        for o in occurrences
    }

    rows: list[dict[str, Any]] = []
    for req in canonical["unique_requests"]:
        rid = req["unique_request_id"]
        if rid not in canonical["point_ids"]:
            continue
        c, s, t = cal[rid], state[rid], trade[rid]
        codes = _STATE_CODE_RE.findall(s["instrument_state"])
        records = _num(t["trade_count_daily"])
        z = _num(req["zTotTran"])
        rows.append({
            "unique_request_id": rid,
            "ticker": req["ticker"],
            "InsCode": req["InsCode"],
            "endpoint_date": req["endpoint_date"],
            "endpoint_occurrence_count": req["occurrence_count"],
            "official_calendar_member": c["in_instrument_trading_calendar"],
            "calendar_evidence_endpoint": c["calendar_evidence_endpoint"],
            "daily_row_present": bool(daily_endpoint.get(rid)),
            "daily_closing_evidence_endpoint": daily_endpoint.get(rid, ""),
            "zTotTran": req["zTotTran"],
            "qTotTran5J": req["qTotTran5J"],
            "qTotCap": req["qTotCap"],
            "raw_close": req["raw_close"],
            "zero_trade": z == 0 if z is not None else "",
            "trade_history_records": t["trade_count_daily"],
            "trade_history_empty": records == 0 if records is not None else "",
            "trade_evidence_endpoint": t["trade_evidence_endpoint"],
            "literal_state_code": codes[0] if codes else "UNRESOLVED",
            "state_meaning": "UNRESOLVED",
            "state_evidence_endpoint": s["state_evidence_endpoint"],
            "adjusted_close_availability": adjusted.get(
                (req["ticker"], req["endpoint_date"]), "UNRESOLVED"),
            "scientific_inclusion_decision": NO_DECISION,
        })
    return rows


def build_range_evidence_rows(
    canonical: dict[str, Any],
    cal_vs_daily: list[dict[str, str]],
    state_rows: list[dict[str, str]],
    trade_audit: list[dict[str, str]],
    manifest: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """One factual row per low-return RANGE request."""
    cvd = {r["unique_request_id"]: r for r in cal_vs_daily}
    state = {r["unique_request_id"]: r for r in state_rows}
    state_artifacts: dict[str, int] = {}
    for row in manifest:
        if row["evidence_type"] == "STATE":
            state_artifacts[row["unique_request_id"]] = (
                state_artifacts.get(row["unique_request_id"], 0) + 1)
    audit_by_request: dict[str, list[dict[str, str]]] = {}
    for row in trade_audit:
        audit_by_request.setdefault(row["unique_request_id"], []).append(row)

    rows: list[dict[str, Any]] = []
    for req in canonical["unique_requests"]:
        rid = req["unique_request_id"]
        if rid not in canonical["range_ids"]:
            continue
        d = cvd[rid]
        note = d.get("notes", "") or ""
        zero = _ZERO_TRADE_RE.search(note)
        positive = _POSITIVE_TRADE_RE.search(note)
        audit = audit_by_request.get(rid, [])
        zero_rows = int(zero.group(1)) if zero else ""
        if zero_rows == "":
            # Derive from the delivered trade diagnostics when the note is silent.
            zero_rows = sum(1 for a in audit if _num(a["daily_zTotTran"]) == 0)
            pos_rows = sum(1 for a in audit if (_num(a["daily_zTotTran"]) or 0) > 0)
        else:
            pos_rows = int(positive.group(1)) if positive else ""
        rows.append({
            "unique_request_id": rid,
            "ticker": req["ticker"],
            "InsCode": req["InsCode"],
            "range_start_date": req["range_start_date"],
            "range_end_date": req["range_end_date"],
            "calendar_row_count": d["calendar_date_count"],
            "daily_row_count": d["daily_date_count"],
            "calendar_vs_daily_date_sets_equal": d["date_sets_equal"],
            "missing_in_daily_count": d["missing_in_daily_count"],
            "extra_in_daily_count": d["extra_in_daily_count"],
            "zero_trade_row_count": zero_rows,
            "positive_trade_row_count": pos_rows,
            "state_sample_artifact_count": state_artifacts.get(rid, 0),
            "literal_state_codes_sampled": ";".join(sorted(set(
                _STATE_CODE_RE.findall(state[rid]["instrument_state"])))),
            "trade_diagnostic_rows": len(audit),
            "daily_vs_ungrouped_mismatch_rows": sum(
                1 for a in audit if "!=" in a["observed_pilot_property"]),
            "scientific_inclusion_decision": NO_DECISION,
        })
    return rows


def build_identity_evidence_rows(
    identity_rows: list[dict[str, str]], audit_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """One row per affected ticker, preserving identity uncertainty."""
    current = {r["ticker"]: r for r in audit_rows
               if r["evidence_status"] == "current_identity_snapshot"}
    probes: dict[str, int] = {}
    for row in audit_rows:
        if row["evidence_status"] == "historical_snapshot":
            probes[row["ticker"]] = probes.get(row["ticker"], 0) + 1

    rows: list[dict[str, Any]] = []
    for row in sorted(identity_rows, key=lambda r: r["ticker"]):
        cur = current.get(row["ticker"], {})
        rows.append({
            "ticker": row["ticker"],
            "request_InsCode": row["request_InsCode"],
            "request_ISIN": row["request_ISIN"],
            "current_raw_instrumentID": row["current_raw_instrumentID"],
            "current_raw_cIsin": row["current_raw_cIsin"],
            "request_ISIN_equals_instrumentID": cur.get(
                "same_request_ISIN_as_instrumentID", ""),
            "request_ISIN_equals_cIsin": cur.get(
                "same_request_ISIN_as_cIsin", ""),
            "historical_probe_count": probes.get(row["ticker"], 0),
            "candidate_historical_InsCode": row["candidate_historical_InsCode"],
            "evidence_status": row["evidence_status"],
            "histories_concatenated": False,
            "ins_code_zero_used_as_predecessor": False,
        })
    return rows


def build_derived_evidence(repo_root: str, bundle_path: str) -> dict[str, Any]:
    """Import the delivery and build every papermali-side derived artifact."""
    qc = import_delivery(repo_root, bundle_path)
    canonical = load_canonical_requests(repo_root)
    with open_delivery(bundle_path) as zf:
        manifest = read_csv_bytes(zf.read(MANIFEST_REL))
        calendar_rows = read_csv_bytes(zf.read(CALENDAR_EVIDENCE_REL))
        state_rows = read_csv_bytes(zf.read(STATE_EVIDENCE_REL))
        trade_rows = read_csv_bytes(zf.read(TRADE_EVIDENCE_REL))
        identity_rows = read_csv_bytes(zf.read(IDENTITY_EVIDENCE_REL))
        cal_vs_daily = read_csv_bytes(zf.read(CAL_VS_DAILY_REL))
        trade_audit = read_csv_bytes(zf.read(TRADE_AUDIT_REL))
        identity_audit = read_csv_bytes(zf.read(IDENTITY_AUDIT_REL))

    point = build_point_evidence_rows(
        canonical, calendar_rows, state_rows, trade_rows, manifest,
        canonical["occurrences"])
    ranges = build_range_evidence_rows(
        canonical, cal_vs_daily, state_rows, trade_audit, manifest)
    identity = build_identity_evidence_rows(identity_rows, identity_audit)

    if len(point) != len(canonical["point_ids"]):
        _fail("derived POINT evidence does not cover every POINT_DATE request")
    if len(ranges) != len(canonical["range_ids"]):
        _fail("derived RANGE evidence does not cover every RANGE request")
    if len(identity) != len(canonical["tickers"]):
        _fail("derived identity evidence does not cover every affected ticker")

    occurrences_covered = sum(
        int(r["endpoint_occurrence_count"]) for r in point)
    return {
        "qc": qc,
        "point_rows": point,
        "range_rows": ranges,
        "identity_rows": identity,
        "point_endpoint_occurrences_covered": occurrences_covered,
    }
