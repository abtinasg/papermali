#!/usr/bin/env python3
"""Runner — Stage128 Track B: M3-LAG-WDI exploratory data retrieval.

Authorized action: ``stage128-m3-lag-wdi-exploratory-data-retrieval``
Authorized scope:  ``retrieval_only``

Three strictly separated modes:

``--retrieve``              the ONE authorized network session. Delegates every
                            socket to ``stage128_m3_lag_wdi_retrieval_capture_layer``.
``--build-from-bundle DIR`` offline rebuild of every committed artifact from the
                            retained raw bytes.
``--check``                 offline verification of the committed package. No
                            network, no writes.

Only ``--retrieve`` may touch the network, and it is the only path that imports
the capture layer.

This runner never executes the Data Gate, never computes coverage, never joins
a WDI value to a company row, never fits a model and never reads a Final Test
row. Those are steps C/D/E and each needs its own separate human authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m3_lag_wdi_exploratory_data_retrieval as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / m.PACKAGE_REL

_ARTIFACT_FILES = {
    "human_authorization_record":
        "stage128_m3_lag_wdi_retrieval_human_authorization_record.json",
    "source_manifest": "stage128_m3_lag_wdi_retrieval_source_manifest.json",
    "execution_audit": "stage128_m3_lag_wdi_retrieval_execution_audit.json",
    "governance_boundary":
        "stage128_m3_lag_wdi_retrieval_governance_boundary.json",
    "decision": "stage128_m3_lag_wdi_retrieval_decision.json",
    "pr_topology": "stage128_m3_lag_wdi_retrieval_pr_topology.json",
    "qc_report": "stage128_m3_lag_wdi_retrieval_qc_report.json",
}
_METADATA_FILE = (
    "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_data_retrieval.json")
_README_FILE = "README_STAGE128_M3_LAG_WDI_EXPLORATORY_DATA_RETRIEVAL.md"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _retrieve(bundle_dir: str) -> int:
    """Run THE one authorized retrieval session."""
    # Imported HERE so that --check and --build-from-bundle never even load a
    # module that can open a socket.
    from src import stage128_m3_lag_wdi_retrieval_capture_layer as capture

    m.verify_human_authorization()
    verified = m.verify_locked_contract(ROOT)
    print(f"action:   {m.ACTION_ID}")
    print(f"scope:    {m.AUTHORIZED_SCOPE}")
    print(f"baseline: {m.BASELINE_BRANCH} @ {m.BASELINE_COMMIT}")
    print(f"contract: {verified['contract_status']}")
    print(f"country:  {verified['country_code']}")
    print(f"locked indicators: {verified['indicator_codes']}")
    print(f"bundle -> {bundle_dir}")

    session = capture.retrieve_locked_indicators(bundle_dir)
    print(json.dumps({
        "session_closed": session["session_closed"],
        "indicators_requested": session["indicators_requested"],
        "indicators_succeeded": session["indicators_succeeded"],
        "indicators_failed": session["indicators_failed"],
        "http_requests_made": session["http_requests_made"],
        "raw_artifacts_retained": session["raw_artifacts_retained"],
        "raw_bytes_retained": session["raw_bytes_retained"],
    }, ensure_ascii=False, indent=2))
    if not session["session_closed"]:
        print("STOP_RETRIEVAL_SESSION_NOT_CLOSED", file=sys.stderr)
        return 2
    return 0


def _readme(built: dict) -> str:
    manifest = built["source_manifest"]
    audit = built["execution_audit"]
    rows = []
    for entry in manifest["indicators"]:
        rows.append(
            f"| `{entry['indicator_code']}` | {entry['country_code']} | "
            f"{entry['retrieval_result']} | {entry['http_status_code']} | "
            f"{entry['raw_artifact_bytes']} | "
            f"`{(entry['raw_artifact_sha256'] or '')[:16]}…` |")
    table = "\n".join(rows)
    return f"""# Stage128 — Track B: M3-LAG-WDI exploratory DATA RETRIEVAL

**Action:** `{m.ACTION_ID}`
**Authorized scope:** `{m.AUTHORIZED_SCOPE}`
**Baseline:** `{m.BASELINE_BRANCH}` @ `{m.BASELINE_COMMIT}` (the merge commit of
PR #78, the contract lock)

## What this action is

Acquisition of the raw official World Bank WDI source payloads for the **two
indicators frozen by the merged contract**, for **IRN**, and nothing else.

**Acquiring bytes is not admitting data.** This action answers no question
about coverage, about the Data Gate, about admission or about modeling.

| Indicator | Country | Result | HTTP | Bytes | SHA-256 |
| --- | --- | --- | --- | --- | --- |
{table}

Raw payloads are retained **outside the repository**; only their byte counts
and SHA-256 digests are committed
(`raw_payloads_committed_to_git: {manifest['raw_payloads_committed_to_git']}`).

## Where this action stopped

The payload was **never decoded or parsed**
(`payload_json_decoded: {audit['payload_json_decoded']}`,
`wdi_observations_read: {audit['wdi_observations_read']}`). Reading what is
*inside* the retained bytes is the separately authorized post-retrieval audit.

All zero: value inspections, coverage calculations, candidate/block coverage
evaluations, Data Gate executions, admission decisions, company-row joins,
feature materializations, FX transformation calculations, common-sample
constructions, model fits, predictions, predictive metrics, bootstrap
executions, Holm calculations, SHAP executions, tuning runs, **Final Test rows
read**.

## The authorization boundary

The retrieval authorization (125 UTF-8 bytes, SHA-256
`{built['human_authorization_record']['authorization_sha256'][:16]}…`) is
**single-use and is now consumed**. It does not reach:

| Step | Action | Authorized |
| --- | --- | --- |
| C | `{m.NEXT_ACTION_ID}` | **false** |
| D | `{m.DATA_GATE_ACTION_ID}` | **false** — needs a NEW explicit human authorization |
| E | `{m.MODELING_ACTION_ID}` | **false** — only after a Gate PASS, and needs ANOTHER authorization |

A retrieval authorization does **not** authorize the Data Gate. A Data Gate
PASS would be **data admission only** and would **not** authorize modeling. A
pointer is never an authorization.

## Track A is untouched

The World Bank official inquiry remains a parallel ACTIVE track: still
`SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE`, follow-up and
response adjudication both unauthorized. Retrieving Track B data does not
resolve, close or abandon Track A.

## Reproducing

```
python3 project/run_stage128_m3_lag_wdi_exploratory_data_retrieval.py --check
```

`--check` is offline and read-only. `--build-from-bundle DIR` rebuilds every
artifact here from the retained raw bytes. `--retrieve` is the one authorized
network path and is already spent.
"""


def _build(bundle_dir: str) -> int:
    built = m.build_package(ROOT, bundle_dir)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in _ARTIFACT_FILES.items():
        _write_json(PACKAGE_DIR / filename, built[key])
    (PACKAGE_DIR / _README_FILE).write_text(_readme(built), encoding="utf-8")

    package_files = {}
    for filename in sorted(list(_ARTIFACT_FILES.values()) + [_README_FILE]):
        path = PACKAGE_DIR / filename
        package_files[filename] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    inherited = {}
    for rel in (m.CONTRACT_REL, m.CONTRACT_BOUNDARY_REL, m.CONTRACT_GATE_REL):
        path = ROOT / rel
        inherited[rel] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    _write_json(PACKAGE_DIR / _METADATA_FILE, {
        "action_id": m.ACTION_ID,
        "package_id": m.PACKAGE_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "baseline_commit": m.BASELINE_COMMIT,
        "authorization_sha256": m.HUMAN_AUTHORIZATION_SHA256,
        "authorization_utf8_bytes": m.HUMAN_AUTHORIZATION_UTF8_BYTES,
        "package_files": package_files,
        "inherited_inputs": inherited,
        "inherited_inputs_modified_by_this_action": False,
        "raw_wdi_payloads_committed_to_git": 0,
        "wdi_value_files_committed": 0,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
    })
    qc = built["qc_report"]
    print(f"package -> {PACKAGE_DIR}")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    return 0 if qc["all_pass"] else 3


def _check() -> int:
    """Offline verification of the committed package. No network, no writes."""
    m.verify_human_authorization()
    m.verify_locked_contract(ROOT)
    missing = [f for f in list(_ARTIFACT_FILES.values())
               + [_METADATA_FILE, _README_FILE]
               if not (PACKAGE_DIR / f).is_file()]
    if missing:
        print(f"STOP_PACKAGE_INCOMPLETE: {missing}", file=sys.stderr)
        return 2

    metadata = json.loads(
        (PACKAGE_DIR / _METADATA_FILE).read_text(encoding="utf-8"))
    for filename, record in metadata["package_files"].items():
        path = PACKAGE_DIR / filename
        if _sha256_file(path) != record["sha256"]:
            print(f"STOP_PACKAGE_HASH_MISMATCH: {filename}", file=sys.stderr)
            return 2
        if path.stat().st_size != record["bytes"]:
            print(f"STOP_PACKAGE_SIZE_MISMATCH: {filename}", file=sys.stderr)
            return 2

    audit = json.loads(
        (PACKAGE_DIR / _ARTIFACT_FILES["execution_audit"]).read_text(
            encoding="utf-8"))
    boundary = json.loads(
        (PACKAGE_DIR / _ARTIFACT_FILES["governance_boundary"]).read_text(
            encoding="utf-8"))
    # The firewall, re-asserted offline on every --check.
    for field in ("wdi_value_inspections", "wdi_observations_read",
                  "coverage_calculations", "data_gate_executions",
                  "admission_decisions", "company_row_macro_joins",
                  "feature_materializations", "model_fits",
                  "final_test_rows_read", "alternative_indicators_retrieved"):
        if audit.get(field) != 0:
            print(f"STOP_EXECUTION_COUNTER_NOT_ZERO: {field}", file=sys.stderr)
            return 2
    for field in ("m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_modeling_authorized",
                  "retrieval_authorization_implies_gate_authorization",
                  "combined_retrieval_and_gate_action_permitted",
                  "m3_lag_wdi_gate_pass_authorizes_modeling",
                  "merge_authorized"):
        if boundary.get(field) is not False:
            print(f"STOP_BOUNDARY_FIELD_NOT_FALSE: {field}", file=sys.stderr)
            return 2

    qc = json.loads(
        (PACKAGE_DIR / _ARTIFACT_FILES["qc_report"]).read_text(
            encoding="utf-8"))
    print(f"action: {m.ACTION_ID} (scope {m.AUTHORIZED_SCOPE})")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    print(f"next action: {boundary['m3_lag_wdi_next_action_id']} "
          f"(authorized={boundary['m3_lag_wdi_next_action_authorized']})")
    print(f"Data Gate: {boundary['m3_lag_wdi_data_gate_action_id']} "
          f"(authorized={boundary['m3_lag_wdi_data_gate_action_authorized']}, "
          f"executed={boundary['m3_lag_wdi_data_gate_executed']})")
    print(f"final test rows read: {audit['final_test_rows_read']}")
    if not qc["all_pass"]:
        return 3
    print("Retrieval package verified (--check).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--retrieve", action="store_true",
                       help="the ONE authorized network session")
    group.add_argument("--build-from-bundle", metavar="DIR",
                       help="offline rebuild from retained raw bytes")
    group.add_argument("--check", action="store_true",
                       help="offline verification; no network, no writes")
    parser.add_argument("--bundle-dir",
                        help="external bundle directory (with --retrieve)")
    args = parser.parse_args(argv)

    if args.retrieve:
        if not args.bundle_dir:
            parser.error("--retrieve requires --bundle-dir")
        return _retrieve(args.bundle_dir)
    if args.build_from_bundle:
        return _build(args.build_from_bundle)
    return _check()


if __name__ == "__main__":
    raise SystemExit(main())
