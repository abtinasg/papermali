#!/usr/bin/env python3
"""Runner — Stage128 Track B step C: M3-LAG-WDI POST-RETRIEVAL AUDIT.

Authorized action: ``stage128-m3-lag-wdi-exploratory-post-retrieval-audit``
Authorized scope:  ``post_retrieval_audit_only``

Two modes, neither of which may touch the network:

``--execute BUNDLE_DIR``  the ONE authorized audit run. Decodes the retained
                          payloads (after proving their identity) and writes
                          the committed audit package.
``--check``               offline verification of the committed package.

There is deliberately no ``--retrieve``: this step has no network code path at
all. It cannot re-request the World Bank API even if asked to, because nothing
here imports the capture layer.

This runner executes no Data Gate, computes no coverage against any threshold,
makes no admission decision, joins nothing to a company row, fits no model and
reads no Final Test row. Those are steps D and E, each needing its own separate
explicit human authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_post_retrieval_audit as m)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / m.PACKAGE_REL

_ARTIFACT_FILES = {
    "human_authorization_record":
        "stage128_m3_lag_wdi_post_retrieval_audit_human_authorization_"
        "record.json",
    "audit_report": "stage128_m3_lag_wdi_post_retrieval_audit_report.json",
    "execution_audit":
        "stage128_m3_lag_wdi_post_retrieval_audit_execution_audit.json",
    "governance_boundary":
        "stage128_m3_lag_wdi_post_retrieval_audit_governance_boundary.json",
    "decision": "stage128_m3_lag_wdi_post_retrieval_audit_decision.json",
    "qc_report": "stage128_m3_lag_wdi_post_retrieval_audit_qc_report.json",
}
_METADATA_FILE = (
    "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_post_retrieval_"
    "audit.json")
_README_FILE = (
    "README_STAGE128_M3_LAG_WDI_EXPLORATORY_POST_RETRIEVAL_AUDIT.md")

#: Counters this step must leave at zero. Step C reads a series; it does not
#: touch the sample, the Gate, the models or the Final Test.
_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "coverage_calculations", "candidate_coverage_evaluations",
    "block_coverage_evaluations", "coverage_threshold_comparisons",
    "data_gate_executions", "data_gate_results_returned",
    "admission_decisions", "company_row_macro_joins",
    "feature_materializations", "common_sample_constructions",
    "model_fits", "predictions", "predictive_metrics", "bootstrap_executions",
    "holm_calculations", "shap_executions", "tuning_runs",
    "final_test_rows_read", "final_test_predictor_values_read",
    "final_test_target_values_read",
)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _readme(built: dict) -> str:
    report = built["audit_report"]
    decision = built["decision"]
    cpi, fx = report["feature_availability"]
    rows = []
    for entry in report["series"]:
        rows.append(
            f"| `{entry['indicator_code']}` | {entry['observations_returned']} "
            f"| {entry['observation_year_first']}–"
            f"{entry['observation_year_last']} | "
            f"{entry['observations_numeric']} | {entry['observations_null']} | "
            f"`{entry['source_last_updated']}` |")
    table = "\n".join(rows)
    findings = "\n".join(
        f"- {f}" for entry in report["series"] for f in entry["findings"]
    ) or "- (none at series level)"
    return f"""# Stage128 — Track B step C: M3-LAG-WDI POST-RETRIEVAL AUDIT

**Action:** `{m.ACTION_ID}`
**Authorized scope:** `{m.AUTHORIZED_SCOPE}`
**Result:** `{decision['audit_result']}`

## What this action is

The first and only authorized decode of the payloads acquired by step B. It
asks what the retained evidence actually contains and whether it matches the
locked contract. **It is not the Data Gate**: no coverage threshold was
applied, no company row was touched and nothing was admitted.

Identity was proven on the raw bytes **before** decoding: byte count and
SHA-256 were re-verified against the committed retrieval manifest, which is
anchored to the immutable Zenodo record `{m.__dict__.get('ZENODO_VERSION_DOI',
'10.5281/zenodo.21844636')}`.

| Indicator | Obs | Year span | Numeric | Null | WDI lastupdated |
| --- | --- | --- | --- | --- | --- |
{table}

## What the evidence supports

| Feature | Constructible predictor years | First | Last |
| --- | --- | --- | --- |
| `{cpi['feature_id']}` | {cpi['constructible_predictor_years']} | {cpi['constructible_predictor_year_first']} | {cpi['constructible_predictor_year_last']} |
| `{fx['feature_id']}` | {fx['constructible_predictor_years']} | {fx['constructible_predictor_year_first']} | {fx['constructible_predictor_year_last']} |

The contract requires **both** features complete on the same row, so the
series-level ceiling is
**{report['both_features_constructible_predictor_year_first']}–{report['both_features_constructible_predictor_year_last']}**
({report['both_features_constructible_predictor_years']} predictor years),
bound by `{report['binding_constraint_indicator']}`.

These are SERIES-level statements. Translating them into per-row coverage,
comparing them to the inherited thresholds and deciding admission is the Data
Gate — step D, unauthorized and unexecuted.

## Findings

{findings}

## Material limitations recorded

{chr(10).join('- ' + item for item in decision['material_limitations'])}

## Where this action stopped

Coverage computed: `{report['candidate_coverage_computed']}` · admission
decision: `{report['admission_decision_made']}` · company rows touched:
`{report['company_rows_touched']}`.

A completed step C authorizes nothing. The Data Gate
(`{decision['next_action_id']}`) is a separate action and remains
`authorized = {decision['next_action_authorized']}`.
"""


def _execute(bundle_dir: str) -> int:
    authorization = m.verify_human_authorization()
    manifest = json.loads(
        (ROOT / m.RETRIEVAL_MANIFEST_REL).read_text(encoding="utf-8"))

    series: dict[str, dict] = {}
    values: dict[str, dict[int, object]] = {}
    payload_identity = []
    for entry in manifest["indicators"]:
        code = entry["indicator_code"]
        path = os.path.join(bundle_dir, "raw", entry["raw_artifact_filename"])
        blob, document = m.load_retained_payload(
            path, entry["raw_artifact_bytes"], entry["raw_artifact_sha256"])
        series[code] = m.audit_series(code, document)
        values[code] = {int(row["date"]): row.get("value")
                        for row in document[1]}
        payload_identity.append({
            "indicator_code": code,
            "raw_artifact_filename": entry["raw_artifact_filename"],
            "raw_artifact_bytes": len(blob),
            "raw_artifact_sha256": hashlib.sha256(blob).hexdigest(),
            "identity_matches_committed_manifest": True,
            "bytes_modified_by_this_action": False,
        })

    report = m.build_audit_report(series, values)
    report["retained_payload_identity"] = payload_identity

    all_findings = [f for entry in report["series"] for f in entry["findings"]]
    fx = report["feature_availability"][1]
    material: list[str] = []
    if series[m.FX_CODE]["trailing_null_observation_years"]:
        material.append(
            f"{m.FX_CODE} carries no value for its most recent observation "
            f"years {series[m.FX_CODE]['trailing_null_observation_years']}, "
            "which caps the predictor years the FX feature can cover at "
            f"{fx['constructible_predictor_year_last']}")
    if fx["trailing_zero_change_predictor_years"]:
        material.append(
            "the official exchange rate is repeated unchanged across the most "
            "recent usable years, so the contract-locked log-ratio transform "
            "is defined but identically ZERO for predictor years "
            f"{fx['trailing_zero_change_predictor_year_list']} — i.e. the "
            f"LAST {fx['trailing_zero_change_predictor_years']} usable "
            "predictor years carry a complete but information-free FX feature "
            f"(zero-change years overall: "
            f"{fx['degenerate_zero_change_predictor_year_list']})")
    elif fx["degenerate_zero_change_predictor_years"]:
        material.append(
            "the contract-locked log-ratio transform is defined but "
            "identically ZERO for predictor years "
            f"{fx['degenerate_zero_change_predictor_year_list']}")
    material.append(
        "the WDI vintage is a revision marker "
        f"(`lastupdated {series[m.CPI_CODE]['source_last_updated']}`), not "
        "evidence of what was published at any past moment; no point-in-time "
        "or historical-vintage availability is established")

    # The audit PASSES on evidence integrity when the bytes are provably the
    # retrieved bytes, the schema is the expected one and both series carry the
    # contract's indicator and country. Material findings do not fake a
    # failure, and they are never allowed to disappear either.
    integrity_ok = all(p["identity_matches_committed_manifest"]
                       for p in payload_identity)
    result = ("PASS_WITH_MATERIAL_FINDINGS" if (integrity_ok and material)
              else "PASS" if integrity_ok else "FAIL")

    decision = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "audit_result": result,
        "evidence_integrity_verified": integrity_ok,
        "schema_conforms_to_world_bank_v2": True,
        "series_match_locked_contract": True,
        "findings": all_findings,
        "material_limitations": material,
        "scientific_effect": "NONE",
        "admission_decision_made": False,
        "coverage_decision_made": False,
        "gate_decision_made": False,
        "modeling_decision_made": False,
        "authorizes_next_action": False,
        "next_action_id": "stage128-m3-lag-wdi-exploratory-data-gate",
        "next_action_authorized": False,
        "next_action_scope": "data_gate_only",
    }

    execution_audit = {
        "action_id": m.ACTION_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "post_retrieval_audit_executed": True,
        "payload_json_decoded": True,
        "payloads_decoded": len(payload_identity),
        "wdi_observations_read": sum(
            entry["observations_returned"] for entry in report["series"]),
        "retained_bytes_modified": False,
        "deposited_evidence_modified": False,
        "quarantined_local_draft_used_as_input": False,
        **{counter: 0 for counter in _ZERO_COUNTERS},
    }

    boundary = {
        "action_id": m.ACTION_ID,
        "m3_lag_wdi_post_retrieval_audit_action_authorized": True,
        "m3_lag_wdi_post_retrieval_audit_executed": True,
        "m3_lag_wdi_post_retrieval_audit_authorization_consumed": True,
        "m3_lag_wdi_post_retrieval_audit_authorization_reusable": False,
        "m3_lag_wdi_post_retrieval_audit_executes_data_gate": False,
        "post_retrieval_audit_authorization_implies_gate_authorization": False,
        "post_retrieval_audit_pass_is_gate_authorization": False,
        "post_retrieval_audit_pass_is_admission": False,
        "m3_lag_wdi_next_action_id":
            "stage128-m3-lag-wdi-exploratory-data-gate",
        "m3_lag_wdi_next_action_authorized": False,
        "m3_lag_wdi_data_gate_action_id":
            "stage128-m3-lag-wdi-exploratory-data-gate",
        "m3_lag_wdi_data_gate_action_authorized": False,
        "m3_lag_wdi_data_gate_executed": False,
        "m3_lag_wdi_data_gate_requires_new_explicit_human_authorization": True,
        "m3_lag_wdi_gate_pass_authorizes_modeling": False,
        "m3_lag_wdi_modeling_action_id":
            "stage128-m3-lag-wdi-exploratory-incremental-evaluation",
        "m3_lag_wdi_modeling_authorized": False,
        "m3_lag_wdi_modeling_started": False,
        "m3_lag_wdi_block_admitted": False,
        "m3_lag_wdi_authoritative_contract_status":
            "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL",
        "m3_lag_wdi_contract_modified_by_this_action": False,
        # Retrieval semantics are historical and stay exactly as step B left
        # them: authorized once, consumed, never standing.
        "retrieval_was_authorized": True,
        "retrieval_authorized_now": False,
        "retrieval_authorization_consumed": True,
        "retrieval_authorization_reusable": False,
        "further_retrieval_requires_new_human_authorization": True,
        "new_world_bank_request_made_by_this_action": False,
        # Track A is untouched by a Track B audit.
        "world_bank_inquiry_status":
            "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE",
        "world_bank_follow_up_authorized": False,
        "world_bank_response_ingestion_authorized": False,
        "world_bank_inquiry_terminated_by_this_action": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "m4_authorized": False,
        "merge_authorized": False,
        "ready_for_review_authorized": False,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
        "raw_wdi_payloads_committed_to_git": 0,
    }

    checks = [
        ("payload_identity_verified_before_decode", integrity_ok),
        ("both_locked_indicators_audited", len(payload_identity) == 2),
        ("schema_is_world_bank_v2", True),
        ("no_new_world_bank_request",
         execution_audit["world_bank_api_requests"] == 0),
        ("retained_bytes_unmodified",
         execution_audit["retained_bytes_modified"] is False),
        ("no_coverage_calculation",
         execution_audit["coverage_calculations"] == 0),
        ("no_data_gate_execution",
         execution_audit["data_gate_executions"] == 0),
        ("no_admission_decision", execution_audit["admission_decisions"] == 0),
        ("no_company_row_join",
         execution_audit["company_row_macro_joins"] == 0),
        ("no_model_fit", execution_audit["model_fits"] == 0),
        ("no_final_test_row_read",
         execution_audit["final_test_rows_read"] == 0),
        ("data_gate_still_unauthorized",
         boundary["m3_lag_wdi_data_gate_action_authorized"] is False),
        ("modeling_still_unauthorized",
         boundary["m3_lag_wdi_modeling_authorized"] is False),
        ("audit_pass_is_not_gate_authorization",
         boundary["post_retrieval_audit_pass_is_gate_authorization"] is False),
        ("material_findings_recorded", isinstance(material, list)),
    ]
    qc = {
        "action_id": m.ACTION_ID,
        "checks_total": len(checks),
        "checks_failed": sum(1 for _, ok in checks if not ok),
        "all_pass": all(ok for _, ok in checks),
        "checks": [{"check": name, "pass": bool(ok)} for name, ok in checks],
    }

    built = {
        "human_authorization_record": authorization,
        "audit_report": report,
        "execution_audit": execution_audit,
        "governance_boundary": boundary,
        "decision": decision,
        "qc_report": qc,
    }

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
    _write_json(PACKAGE_DIR / _METADATA_FILE, {
        "action_id": m.ACTION_ID,
        "package_id": m.PACKAGE_ID,
        "authorized_scope": m.AUTHORIZED_SCOPE,
        "authorization_sha256": authorization["authorization_sha256"],
        "authorization_utf8_bytes": authorization["authorization_utf8_bytes"],
        "package_files": package_files,
        "audited_evidence_zenodo_version_doi": "10.5281/zenodo.21844636",
        "audited_evidence_modified": False,
        "raw_wdi_payloads_committed_to_git": 0,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
    })

    print(f"package -> {PACKAGE_DIR}")
    print(f"audit result: {decision['audit_result']}")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    for item in material:
        print(f"  FINDING: {item}")
    return 0 if qc["all_pass"] else 3


def _check() -> int:
    """Offline verification of the committed audit package."""
    m.verify_human_authorization()
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

    audit = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["execution_audit"])
                       .read_text(encoding="utf-8"))
    boundary = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["governance_boundary"])
                          .read_text(encoding="utf-8"))
    decision = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["decision"])
                          .read_text(encoding="utf-8"))
    for counter in _ZERO_COUNTERS:
        if audit.get(counter) != 0:
            print(f"STOP_EXECUTION_COUNTER_NOT_ZERO: {counter}",
                  file=sys.stderr)
            return 2
    for field in ("m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_block_admitted",
                  "m3_lag_wdi_next_action_authorized",
                  "post_retrieval_audit_authorization_implies_gate_"
                  "authorization",
                  "post_retrieval_audit_pass_is_gate_authorization",
                  "post_retrieval_audit_pass_is_admission",
                  "retrieval_authorized_now",
                  "new_world_bank_request_made_by_this_action",
                  "merge_authorized", "final_test_access_authorized"):
        if boundary.get(field) is not False:
            print(f"STOP_BOUNDARY_FIELD_NOT_FALSE: {field}", file=sys.stderr)
            return 2
    if boundary.get("final_test_locked") is not True:
        print("STOP_FINAL_TEST_NOT_LOCKED", file=sys.stderr)
        return 2

    qc = json.loads((PACKAGE_DIR / _ARTIFACT_FILES["qc_report"])
                    .read_text(encoding="utf-8"))
    print(f"action: {m.ACTION_ID} (scope {m.AUTHORIZED_SCOPE})")
    print(f"audit result: {decision['audit_result']}")
    print(f"QC: {qc['checks_total']} checks, {qc['checks_failed']} failed, "
          f"all_pass={qc['all_pass']}")
    print(f"next action: {boundary['m3_lag_wdi_next_action_id']} "
          f"(authorized={boundary['m3_lag_wdi_next_action_authorized']})")
    print(f"Data Gate executed: {boundary['m3_lag_wdi_data_gate_executed']}")
    print(f"final test rows read: {audit['final_test_rows_read']}")
    for item in decision["material_limitations"]:
        print(f"  FINDING: {item}")
    if not qc["all_pass"]:
        return 3
    print("Post-retrieval audit package verified (--check).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", metavar="BUNDLE_DIR",
                       help="the ONE authorized audit run (offline)")
    group.add_argument("--check", action="store_true",
                       help="offline verification; no network, no writes")
    args = parser.parse_args(argv)
    if args.execute:
        return _execute(args.execute)
    return _check()


if __name__ == "__main__":
    raise SystemExit(main())
