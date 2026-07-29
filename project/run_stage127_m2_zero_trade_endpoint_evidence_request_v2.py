"""Build and validate the Stage127 zero-trade/low-return evidence-request
package v2.

DIAGNOSTIC / RETRIEVAL-REQUEST ONLY. Does not query TSETMC, does not decide
trading-day or identity semantics, and does not touch the canonical Gate.

Usage:
    python project/run_stage127_m2_zero_trade_endpoint_evidence_request_v2.py \
        --bundle PATH
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_equity_return_root_cause_audit as rca  # noqa: E402
from src import stage127_m2_external_delivery_import as imp  # noqa: E402
from src import stage127_m2_market_data_gate as gate  # noqa: E402
from src import stage127_m2_zero_trade_endpoint_evidence_request as v1  # noqa: E402
from src import stage127_m2_zero_trade_endpoint_evidence_request_v2 as v2  # noqa: E402

EXTERNAL_DIR_REL = (
    "project/stage127/external_retrieval/zero_trade_endpoint_evidence_request_v2"
)
_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


class PackageValidationError(Exception):
    pass


def _csv(columns: tuple[str, ...], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_all(repo_root: str, bundle_path: str) -> tuple[dict[str, bytes], dict]:
    occurrences, audit = v1.build_endpoint_occurrences(repo_root, bundle_path)
    main_rows = rca.build_audit_rows(audit)
    upper_bound_rows = rca.build_low_return_upper_bound_rows(audit, main_rows)
    range_requests = v2.build_low_return_range_requests(audit, upper_bound_rows)
    unique_rows, mapping_rows = v2.build_unique_requests_v2(
        occurrences, range_requests)

    input_files = {
        "input/endpoint_occurrence_requests.csv": _csv(
            v2.ENDPOINT_OCCURRENCE_COLUMNS, occurrences),
        "input/low_return_range_requests.csv": _csv(
            v2.LOW_RETURN_RANGE_COLUMNS, range_requests)
        if range_requests else _csv(v2.LOW_RETURN_RANGE_COLUMNS, []),
        "input/low_return_semantics_upper_bound_audit.csv": _csv(
            v2.LOW_RETURN_UPPER_BOUND_COLUMNS, upper_bound_rows),
        "input/unique_evidence_requests.csv": _csv(
            v2.UNIQUE_REQUEST_V2_COLUMNS, unique_rows),
        "input/pair_mapping.csv": _csv(
            v2.PAIR_MAPPING_V2_COLUMNS, mapping_rows),
    }
    template_files = {
        "templates/endpoint_calendar_evidence.csv": _csv(
            v2.TEMPLATE_CALENDAR_COLUMNS, []),
        "templates/endpoint_state_evidence.csv": _csv(
            v2.TEMPLATE_STATE_COLUMNS, []),
        "templates/endpoint_trade_evidence.csv": _csv(
            v2.TEMPLATE_TRADE_COLUMNS, []),
        "templates/historical_identity_evidence.csv": _csv(
            v2.TEMPLATE_IDENTITY_V2_COLUMNS, []),
        "templates/raw_evidence_manifest.csv": _csv(
            v2.RAW_EVIDENCE_MANIFEST_COLUMNS, []),
        "templates/raw_artifact_request_mapping.csv": _csv(
            v2.RAW_ARTIFACT_REQUEST_MAPPING_COLUMNS, []),
    }

    files: dict[str, str] = dict(input_files)
    files.update(template_files)

    hashes = {
        name: sha256_bytes(text.encode("utf-8"))
        for name, text in sorted(files.items())
    }
    readme = v2.build_readme(occurrences, range_requests, unique_rows, upper_bound_rows)
    hashes["README.md"] = sha256_bytes(readme.encode("utf-8"))

    manifest = v2.build_manifest(
        occurrences, range_requests, unique_rows, upper_bound_rows, hashes)
    manifest_text = gate.json_dumps(manifest)

    files["README.md"] = readme
    files["manifest.json"] = manifest_text

    context = {
        "occurrences": occurrences,
        "range_requests": range_requests,
        "upper_bound_rows": upper_bound_rows,
        "unique_rows": unique_rows,
        "mapping_rows": mapping_rows,
        "manifest": manifest,
    }
    return {name: text.encode("utf-8") for name, text in files.items()}, context


def write_zip(out_path: str, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=_ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])


def validate_package(files: dict[str, bytes], context: dict) -> list[str]:
    """Deterministic package validation. Returns [] if every check passes."""
    issues: list[str] = []

    occurrences = context["occurrences"]
    range_requests = context["range_requests"]
    upper_bound_rows = context["upper_bound_rows"]
    unique_rows = context["unique_rows"]
    mapping_rows = context["mapping_rows"]
    manifest = context["manifest"]

    # -- all currently pending endpoint occurrences represented -------------- #
    occ_ids = {o["request_id"] for o in occurrences}
    mapped_occ_ids = {
        m["reference_id"] for m in mapping_rows
        if m["reference_type"] == v2.REF_TYPE_ENDPOINT_OCCURRENCE
    }
    if occ_ids != mapped_occ_ids:
        issues.append(
            "endpoint occurrences not fully represented in pair_mapping: "
            f"missing={occ_ids - mapped_occ_ids}, extra={mapped_occ_ids - occ_ids}"
        )

    # -- all POTENTIALLY_RECOVERABLE_PENDING <126 pairs represented ---------- #
    pending_low_return = {
        (u["ticker"], u["target_year"]) for u in upper_bound_rows
        if u["classification"] == rca.CAT_PENDING_LOW_RETURN_SEMANTICS
    }
    range_keys = {(r["ticker"], r["target_year"]) for r in range_requests}
    if pending_low_return != range_keys:
        issues.append(
            "pending low-return pairs not fully represented in "
            f"low_return_range_requests: missing={pending_low_return - range_keys}, "
            f"extra={range_keys - pending_low_return}"
        )
    guaranteed = {
        (u["ticker"], u["target_year"]) for u in upper_bound_rows
        if u["classification"] == rca.CAT_GUARANTEED_LT126
    }
    if guaranteed & range_keys:
        issues.append(
            "GUARANTEED_LT126 pairs must not receive a range request: "
            f"{guaranteed & range_keys}"
        )

    # -- every unique request maps back to >=1 development pair ------------- #
    unique_ids = {u["unique_request_id"] for u in unique_rows}
    mapped_unique_ids = {m["unique_request_id"] for m in mapping_rows}
    if not unique_ids <= mapped_unique_ids:
        issues.append(
            "unique requests with no pair mapping: "
            f"{unique_ids - mapped_unique_ids}"
        )
    ref_ids_by_unique: dict[str, set[str]] = {}
    for m in mapping_rows:
        ref_ids_by_unique.setdefault(m["unique_request_id"], set()).add(
            m["reference_id"])
    for uid, refs in ref_ids_by_unique.items():
        if not refs:
            issues.append(f"unique request {uid} maps to zero pairs")

    # -- duplicate InsCode/date/evidence_reason requests removed ------------- #
    point_keys = [
        (u["InsCode"], u["endpoint_date"])
        for u in unique_rows if u["request_type"] == v2.REQUEST_TYPE_POINT
    ]
    if len(point_keys) != len(set(point_keys)):
        issues.append("duplicate POINT_DATE (InsCode, date) requests found")
    range_dedup_keys = [
        (u["InsCode"], u["range_start_date"], u["range_end_date"])
        for u in unique_rows if u["request_type"] == v2.REQUEST_TYPE_RANGE
    ]
    if len(range_dedup_keys) != len(set(range_dedup_keys)):
        issues.append("duplicate RANGE (InsCode, start, end) requests found")

    # -- no final-test pair/date; target years only 1393-1399 --------------- #
    years = {int(o["target_year"]) for o in occurrences} | {
        int(r["target_year"]) for r in range_requests
    }
    if years - set(gate.DEVELOPMENT_TARGET_YEARS):
        issues.append(
            f"non-development target years present: "
            f"{years - set(gate.DEVELOPMENT_TARGET_YEARS)}"
        )
    if set(gate.FINAL_TEST_TARGET_YEARS) & years:
        issues.append("final-test target years present in the package")
    all_dates = [o["endpoint_date"] for o in occurrences] + [
        d for r in range_requests
        for d in (r["range_start_date"], r["range_end_date"]) if d
    ]
    firewall_min = imp.FINAL_TEST_FIREWALL_MIN_EXCLUDED_DATE
    if any(d >= firewall_min for d in all_dates if d):
        issues.append("a request date is at or beyond the final-test firewall")

    # -- no scientific output or classification in the request package ------ #
    # Templates must be delivered EMPTY (headers only): the package must not
    # ship a pre-filled scientific conclusion for the retriever to rubber-stamp.
    for name, data in files.items():
        if not name.startswith("templates/"):
            continue
        text = data.decode("utf-8")
        body_lines = [l for l in text.splitlines() if l.strip()][1:]
        if body_lines:
            issues.append(f"template {name} is not empty (headers only expected)")
    if manifest.get("external_modeling_authorized") is not False:
        issues.append("manifest must state external_modeling_authorized=false")
    if manifest.get("external_classification_decision_authorized") is not False:
        issues.append(
            "manifest must state external_classification_decision_authorized=false")
    if manifest.get("external_trading_day_semantics_decision_authorized") is not False:
        issues.append(
            "manifest must state "
            "external_trading_day_semantics_decision_authorized=false")

    # -- no identity join; no model/feature execution ------------------------ #
    if manifest.get("identity_join_authorized") is not False:
        issues.append("manifest must state identity_join_authorized=false")

    # -- manifest hashes match package files ---------------------------------- #
    declared = manifest.get("package_files_sha256", {})
    for name, data in files.items():
        if name == "manifest.json":
            continue
        expected = declared.get(name)
        actual = sha256_bytes(data)
        if expected != actual:
            issues.append(
                f"manifest hash mismatch for {name}: declared={expected} "
                f"actual={actual}"
            )

    # -- raw provenance schema can represent >1 raw artifact per request ----- #
    if "unique_request_id" not in v2.RAW_EVIDENCE_MANIFEST_COLUMNS:
        issues.append("raw evidence manifest schema missing unique_request_id")
    if len(v2.RAW_EVIDENCE_MANIFEST_COLUMNS) == len(v1.TEMPLATE_MANIFEST_COLUMNS) and (
        v2.RAW_EVIDENCE_MANIFEST_COLUMNS == v1.TEMPLATE_MANIFEST_COLUMNS
    ):
        issues.append(
            "raw evidence manifest schema is unchanged from the lossy v1 schema"
        )

    # -- identity schema can represent >1 historical identity per ticker ----- #
    if "candidate_historical_InsCode" not in v2.TEMPLATE_IDENTITY_V2_COLUMNS:
        issues.append("identity schema missing candidate_historical_InsCode")
    if any(
        col in v2.TEMPLATE_IDENTITY_V2_COLUMNS
        for col in ("classification",)
    ):
        issues.append(
            "identity schema still carries a market-day classification field"
        )

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    args = ap.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = gate.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, EXTERNAL_DIR_REL)
    os.makedirs(out_dir, exist_ok=True)

    files, context = build_all(repo_root, args.bundle)

    issues = validate_package(files, context)
    if issues:
        print("PACKAGE VALIDATION FAILED:")
        for i in issues:
            print(f"  - {i}")
        return 1

    for name, data in files.items():
        path = os.path.join(out_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    zip_path = os.path.join(out_dir, v2.ZIP_NAME)
    write_zip(zip_path, files)
    zip_bytes = open(zip_path, "rb").read()

    manifest = context["manifest"]
    print("Zero-trade / low-return evidence-request package v2 built and "
          "VALIDATED.")
    print(f"  file: {v2.ZIP_NAME}")
    print(f"  size: {len(zip_bytes)} bytes")
    print(f"  sha256: {sha256_bytes(zip_bytes)}")
    print(f"  endpoint occurrences: {manifest['endpoint_occurrence_count']} "
          f"(t0={manifest['endpoint_occurrence_count_t0']}, "
          f"tN={manifest['endpoint_occurrence_count_tN']})")
    print(f"  low-return range requests (pending only): "
          f"{manifest['low_return_range_request_count']}")
    print(f"  low-return pairs guaranteed (no evidence needed): "
          f"{manifest['low_return_pairs_guaranteed_no_evidence_needed']}")
    print(f"  low-return pairs pending: "
          f"{manifest['low_return_pairs_pending_evidence']}")
    print(f"  unique requests: {manifest['unique_request_count']} "
          f"(point={manifest['unique_request_count_point']}, "
          f"range={manifest['unique_request_count_range']}, "
          f"both={manifest['unique_request_count_reason_both']})")
    print(f"  affected tickers: {manifest['affected_ticker_count']}")
    print(f"  development target years: {manifest['development_target_years']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
