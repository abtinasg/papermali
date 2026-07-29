"""Build the Stage127 zero-trade endpoint semantics evidence-request package.

DIAGNOSTIC / RETRIEVAL-REQUEST ONLY. Does not query TSETMC, does not decide
trading-day semantics, and does not touch the canonical Gate.

Usage:
    python project/run_stage127_m2_zero_trade_endpoint_evidence_request.py \
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

from src import stage127_m2_market_data_gate as gate  # noqa: E402
from src import stage127_m2_zero_trade_endpoint_evidence_request as req  # noqa: E402

EXTERNAL_DIR_REL = (
    "project/stage127/external_retrieval/zero_trade_endpoint_evidence_request"
)


def _csv(columns: tuple[str, ...], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_all(repo_root: str, bundle_path: str) -> dict[str, bytes]:
    occurrences, audit = req.build_endpoint_occurrences(repo_root, bundle_path)
    unique_rows, mapping_rows = req.build_unique_requests(occurrences, audit)
    low_return_rows = req.build_low_return_context(repo_root, audit)

    input_files = {
        "input/endpoint_occurrence_requests.csv": _csv(
            req.ENDPOINT_OCCURRENCE_COLUMNS, occurrences),
        "input/unique_endpoint_requests.csv": _csv(
            req.UNIQUE_REQUEST_COLUMNS, unique_rows),
        "input/pair_mapping.csv": _csv(req.PAIR_MAPPING_COLUMNS, mapping_rows),
        "input/low_return_reference_context.csv": _csv(
            req.LOW_RETURN_CONTEXT_COLUMNS, low_return_rows),
    }
    template_files = {
        "templates/endpoint_calendar_evidence.csv": _csv(
            req.TEMPLATE_CALENDAR_COLUMNS, []),
        "templates/endpoint_state_evidence.csv": _csv(
            req.TEMPLATE_STATE_COLUMNS, []),
        "templates/endpoint_trade_evidence.csv": _csv(
            req.TEMPLATE_TRADE_COLUMNS, []),
        "templates/historical_identity_evidence.csv": _csv(
            req.TEMPLATE_IDENTITY_COLUMNS, []),
        "templates/retrieval_manifest.csv": _csv(
            req.TEMPLATE_MANIFEST_COLUMNS, []),
    }

    files: dict[str, str] = dict(input_files)
    files.update(template_files)

    hashes = {
        name: sha256_bytes(text.encode("utf-8"))
        for name, text in sorted(files.items())
    }
    readme = req.build_readme(occurrences, unique_rows, low_return_rows)
    hashes["README.md"] = sha256_bytes(readme.encode("utf-8"))

    manifest = req.build_manifest(occurrences, unique_rows, low_return_rows, hashes)
    manifest_text = gate.json_dumps(manifest)

    files["README.md"] = readme
    files["manifest.json"] = manifest_text

    return {name: text.encode("utf-8") for name, text in files.items()}


#: Fixed timestamp so the built ZIP is byte-identical across reruns.
_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def write_zip(out_path: str, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=_ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    args = ap.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = gate.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, EXTERNAL_DIR_REL)
    os.makedirs(out_dir, exist_ok=True)

    files = build_all(repo_root, args.bundle)
    for name, data in files.items():
        path = os.path.join(out_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    zip_path = os.path.join(out_dir, req.ZIP_NAME)
    write_zip(zip_path, files)

    zip_bytes = open(zip_path, "rb").read()
    manifest = json.loads(files["manifest.json"].decode("utf-8"))

    print("Zero-trade endpoint evidence-request package built.")
    print(f"  file: {req.ZIP_NAME}")
    print(f"  size: {len(zip_bytes)} bytes")
    print(f"  sha256: {sha256_bytes(zip_bytes)}")
    print(f"  endpoint occurrences: {manifest['endpoint_occurrence_count']} "
          f"(t0={manifest['endpoint_occurrence_count_t0']}, "
          f"tN={manifest['endpoint_occurrence_count_tN']})")
    print(f"  unique InsCode/date requests: {manifest['unique_endpoint_request_count']}")
    print(f"  affected tickers: {manifest['affected_ticker_count']}")
    print(f"  development target years: {manifest['development_target_years']}")
    print(f"  low-return reference pairs: {manifest['low_return_reference_pair_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
