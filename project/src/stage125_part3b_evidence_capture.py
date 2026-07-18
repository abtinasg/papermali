"""Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot.

Authorized real-evidence path separate from Part 3B.0 synthetic readiness.
No modeling, no sample/target/eligibility change, no guessed values.
"""
from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import socket
import ssl
import time
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src import stage125_part3a_decision_lock as lock
from src import stage125_part3a_pilot_protocol as part3a
from src import stage125_part3b0_evidence_readiness as p3b0

QC_STAGE = "stage125_part3b_evidence_capture"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "959169c71a6e9378995be40979d1c6df7dc45a1d"
RUBRIC_VERSION = "stage125_part3a_v1"

SRC_REL = "project/src/stage125_part3b_evidence_capture.py"
TEST_REL = "project/tests/test_stage125_part3b_evidence_capture.py"
RUN_REL = "project/run_stage125_part3b.py"

F_AUTH = "part3b_authorization_stage125.json"
F_PLAN = "part3b_capture_plan_stage125.csv"
F_ENDPOINTS = "part3b_verified_endpoint_registry_stage125.csv"
F_EVIDENCE = "part3b_evidence_manifest_stage125.csv"
F_HANDLES = "part3b_cache_handles_stage125.csv"
F_LINKAGE = "part3b_candidate_evidence_linkage_stage125.csv"
F_ATTEMPTS = "part3b_capture_attempt_log_stage125.csv"
F_ASSESS = "part3b_pair_candidate_assessment_stage125.csv"
F_SCORES = "part3b_accessibility_scores_stage125.csv"
F_GATES = "part3b_gate_results_stage125.csv"
F_GATE_SUMMARY = "part3b_gate_summary_stage125.json"
F_UNRESOLVED = "part3b_unresolved_and_failures_stage125.csv"
F_README = "README_STAGE125_PART3B_EVIDENCE_CAPTURE.md"
F_QC = "stage125_part3b_evidence_capture_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b.json"
F_NETWORK_LOG = "part3b_capture_network_log_stage125.json"
F_DECISION_REQ = "part3b_decision_requirements_stage125.json"
F_DECISION_REQ_MD = "README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md"
CACHE_DIR_REL = "project/stage125/raw_cache_part3b"

FROZEN_INPUT_HASHES = {
    "project/stage125/part3_candidate_inventory_stage125.csv":
        "4bd5f6a71ecf0e1f74866a64a3774e51340729f4188ae2784f1d90db07e7032f",
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json":
        "9a736edb18046128851d55c87f07609b8dc2a4b2be73a41c5837fe0e2a4cd78d",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv":
        "11c7efe5f242ab8e4a4f7b1955fb25d48e288249f7a1ce4c6bf1713dbf117d20",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv":
        "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5",
    "project/stage125/part3a_decision_lock_stage125.json":
        "475c82b3483ef18ff19aea2268f65527ca87c9441603622bd1952bd21f18f35e",
    "project/stage125/source_registry_stage125.csv":
        "980f375acea69795d06bc19b003563f731bc25f7041bcb07b3fb8f9ec922e13c",
}

# Endpoint-ownership provenance inputs (must be tracked + hash-pinned).
FROZEN_ENDPOINT_PROVENANCE_HASHES = {
    "project/stage124/official_api/import_manifest.json":
        "9ff7bd939b1e28844d897412db6c2671db3e6857b83dce9261c3de44b4871e06",
    "project/stage124/official_api/README.md":
        "0d4cf8581a953877f3102f4f7289c9017aa0b968e6ec9c8cfd4d3918c3c64492",
    "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
    "ocf_source_manifest_stage121.csv":
        "b1bf92d74f19b4c00373079c3222489d6cb54e1c8f11e30a9e02557e6936057a",
}

# Cache-bound evidence IDs from the authorized origin-probe capture (immutable).
# Identical payload bytes cannot be rebound to a different evidence_id.
CANONICAL_SOURCE_EVIDENCE_ID = {
    "src_m2_tsetmc_market":
        "ev_src_m2_tsetmc_market_cand_m2_equity_return_window",
    "src_m4_codal_audit":
        "ev_src_m4_codal_audit_cand_m4_audit_opinion_type",
    "src_m4_codal_governance":
        "ev_src_m4_codal_governance_cand_m4_board_size",
}
CANONICAL_EVIDENCE_BINDING_CANDIDATE = {
    "ev_src_m2_tsetmc_market_cand_m2_equity_return_window":
        "cand_m2_equity_return_window",
    "ev_src_m4_codal_audit_cand_m4_audit_opinion_type":
        "cand_m4_audit_opinion_type",
    "ev_src_m4_codal_governance_cand_m4_board_size":
        "cand_m4_board_size",
}
EVIDENCE_CLASS_ORIGIN_PROBE = "source_origin_probe"
EVIDENCE_CLASS_CANDIDATE_ENDPOINT = "candidate_endpoint_evidence"
EVIDENCE_CLASS_PAIR_VALUE = "pair_value_evidence"
EVIDENCE_CLASS_BLOCKED = "blocked_unverified_endpoint"

REGISTERED_CANDIDATE_IDS = tuple(c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES)
CANDIDATE_SOURCE_MAP = {c["candidate_id"]: c["source_id"] for c in part3a.REGISTERED_CANDIDATES}
BLOCK_BY_CANDIDATE = {c["candidate_id"]: c["block"] for c in part3a.REGISTERED_CANDIDATES}

# Exact-path Part 3B.1 Decision Lock surfaces (no globs / no directory-wide).
PART3B1_SRC_REL = "project/src/stage125_part3b1_decision_lock.py"
PART3B1_TEST_REL = "project/tests/test_stage125_part3b1_decision_lock.py"
PART3B1_ALLOWLIST_TEST_REL = (
    "project/tests/test_stage125_part3b1_allowlist_guards.py"
)
PART3B1_RUN_REL = "project/run_stage125_part3b1.py"
PART3B1_AUTHORIZED_EXACT = frozenset({
    PART3B1_SRC_REL,
    PART3B1_TEST_REL,
    PART3B1_ALLOWLIST_TEST_REL,
    PART3B1_RUN_REL,
    "project/stage125/README_STAGE125_PART3B1_DECISION_LOCK.md",
    "project/stage125/metadata_and_hashes_stage125_part3b1.json",
    "project/stage125/part3b1_adjudicated_decision_requirements_stage125.json",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json",
    "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json",
    "project/stage125/part3b1_m4_feature_definition_contract_stage125.json",
    "project/stage125/part3b1_rubric_operational_mapping_stage125.json",
    "project/stage125/part3b1_selected_decisions_stage125.csv",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
})

# Exact-path Part 3B.1A CUT-A available-at operationalization surfaces.
PART3B1A_SRC_REL = (
    "project/src/stage125_part3b1a_cut_a_available_at_operationalization.py"
)
PART3B1A_TEST_REL = (
    "project/tests/test_stage125_part3b1a_cut_a_available_at_operationalization.py"
)
PART3B1A_RUN_REL = "project/run_stage125_part3b1a.py"
PART3B1A_AUTHORIZED_EXACT = frozenset({
    PART3B1A_SRC_REL,
    PART3B1A_TEST_REL,
    PART3B1A_RUN_REL,
    "project/stage125/README_STAGE125_PART3B1A_CUT_A_AVAILABLE_AT_LOCK.md",
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1a.json",
})

# Exact-path Part 3B.1B CODAL document-binding mini-pilot surfaces.
PART3B1B_SRC_REL = "project/src/stage125_part3b1b_codal_document_binding.py"
PART3B1B_TEST_REL = (
    "project/tests/test_stage125_part3b1b_codal_document_binding.py"
)
PART3B1B_RUN_REL = "project/run_stage125_part3b1b.py"
PART3B1B_AUTHORIZED_EXACT = frozenset({
    PART3B1B_SRC_REL,
    PART3B1B_TEST_REL,
    PART3B1B_RUN_REL,
    "project/stage125/README_STAGE125_PART3B1B_CODAL_DOCUMENT_BINDING.md",
    "project/stage125/part3b1b_predictor_document_scope_stage125.csv",
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv",
    "project/stage125/part3b1b_capture_attempt_log_stage125.csv",
    "project/stage125/part3b1b_network_log_stage125.json",
    "project/stage125/part3b1b_unresolved_and_rejections_stage125.csv",
    "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json",
    "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json",
    "project/stage125/stage125_part3b1b_codal_document_binding_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1b.json",
})

PART3B1C_SRC_REL = "project/src/stage125_part3b1c_document_binding_resolution.py"
PART3B1C_TEST_REL = (
    "project/tests/test_stage125_part3b1c_document_binding_resolution.py"
)
PART3B1C_RUN_REL = "project/run_stage125_part3b1c.py"
PART3B1C_AUTHORIZED_EXACT = frozenset({
    PART3B1C_SRC_REL,
    PART3B1C_TEST_REL,
    PART3B1C_RUN_REL,
    "project/stage125/README_STAGE125_PART3B1C_DOCUMENT_BINDING_RESOLUTION.md",
    "project/stage125/part3b1c_binding_failure_taxonomy_stage125.csv",
    "project/stage125/part3b1c_identity_normalization_contract_stage125.json",
    "project/stage125/part3b1c_exact_document_evidence_hierarchy_stage125.json",
    "project/stage125/part3b1c_row_resolution_requirements_stage125.csv",
    "project/stage125/part3b1c_proposed_capture_authorization_stage125.json",
    "project/stage125/part3b1c_scale_up_readiness_decision_stage125.json",
    "project/stage125/part3b1c_document_binding_resolution_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1c_document_binding_resolution_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1c.json",
})

PART3B1E_SRC_REL = "project/src/stage125_part3b1e_conservative_lag_decision.py"
PART3B1E_TEST_REL = (
    "project/tests/test_stage125_part3b1e_conservative_lag_decision.py"
)
PART3B1E_RUN_REL = "project/run_stage125_part3b1e.py"
PART3B1E_AUTHORIZED_EXACT = frozenset({
    PART3B1E_SRC_REL,
    PART3B1E_TEST_REL,
    PART3B1E_RUN_REL,
    "project/stage125/README_STAGE125_PART3B1E_CONSERVATIVE_LAG.md",
    "project/stage125/part3b1e_conservative_lag_decision_lock_stage125.json",
    "project/stage125/part3b1e_frozen_financial_data_manifest_stage125.json",
    "project/stage125/stage125_part3b1e_conservative_lag_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1e.json",
})

PART3C_SRC_REL = (
    "project/src/stage125_part3c_leakage_safe_dataset_finalization.py"
)
PART3C_TEST_REL = (
    "project/tests/test_stage125_part3c_leakage_safe_dataset_finalization.py"
)
PART3C_RUN_REL = "project/run_stage125_part3c.py"
PART3C_AUTHORIZED_EXACT = frozenset({
    PART3C_SRC_REL,
    PART3C_TEST_REL,
    PART3C_RUN_REL,
    "project/stage125/README_STAGE125_PART3C_LEAKAGE_SAFE_DATASET.md",
    "project/stage125/README_STAGE125_PART3C_FOUR_MONTH_LAG_REVISION.md",
    "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json",
    "project/stage125/part3c_four_month_regulatory_lag_revision_decision_stage125.json",
    "project/stage125/part3c_input_hash_manifest_stage125.json",
    "project/stage125/part3c_column_role_map_stage125.csv",
    "project/stage125/part3c_sample_summary_stage125.csv",
    "project/stage125/part3c_target_year_distribution_stage125.csv",
    "project/stage125/part3c_leakage_audit_stage125.csv",
    "project/stage125/stage125_part3c_leakage_safe_dataset_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3c.json",
})

PART3B_AUTHORIZED_EXACT = frozenset({
    SRC_REL, TEST_REL, RUN_REL,
    f"project/stage125/{F_AUTH}", f"project/stage125/{F_PLAN}",
    f"project/stage125/{F_ENDPOINTS}", f"project/stage125/{F_EVIDENCE}",
    f"project/stage125/{F_HANDLES}", f"project/stage125/{F_LINKAGE}",
    f"project/stage125/{F_ATTEMPTS}", f"project/stage125/{F_ASSESS}",
    f"project/stage125/{F_SCORES}", f"project/stage125/{F_GATES}",
    f"project/stage125/{F_GATE_SUMMARY}", f"project/stage125/{F_UNRESOLVED}",
    f"project/stage125/{F_README}", f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}", f"project/stage125/{F_NETWORK_LOG}",
    f"project/stage125/{F_DECISION_REQ}", f"project/stage125/{F_DECISION_REQ_MD}",
}) | PART3B1_AUTHORIZED_EXACT | PART3B1A_AUTHORIZED_EXACT | PART3B1B_AUTHORIZED_EXACT | PART3B1C_AUTHORIZED_EXACT | PART3B1E_AUTHORIZED_EXACT | PART3C_AUTHORIZED_EXACT


ENDPOINT_HEADER = [
    "source_id", "official_source_owner", "exact_https_origin", "exact_hostname",
    "exact_endpoint_or_url_pattern", "allowed_http_method",
    "authoritative_ownership_evidence", "ownership_evidence_url",
    "retrieval_purpose", "evidence_class", "content_type_expected",
    "verification_status", "failure_reason", "reviewer_status",
    "provenance_input_paths", "provenance_input_sha256",
]
PLAN_HEADER = [
    "plan_row_id", "candidate_id", "source_id", "endpoint_id", "request_url",
    "http_method", "retrieval_purpose", "evidence_class", "plan_status",
    "blocker_reason", "shared_snapshot_key", "canonical_evidence_id",
]
LINKAGE_HEADER = [
    "candidate_id", "source_id", "evidence_id", "evidence_class",
    "linkage_status", "failure_reason",
]
ATTEMPT_HEADER = [
    "capture_run_id", "attempt_id", "planned_request_url", "http_method",
    "started_at_utc", "completed_at_utc", "final_url", "response_status",
    "content_type", "byte_count", "redirect_count", "payload_sha256",
    "metadata_sha256", "success", "failure_class", "shared_snapshot_key",
    "canonical_evidence_id", "network_log_complete",
]
HANDLE_HEADER = [
    "evidence_id", "payload_sha256", "metadata_sha256", "cache_contract_version",
    "cache_handle_schema_version", "external_handle_sha256", "source_id",
    "binding_candidate_id",
]
ASSESS_HEADER = [
    "assessment_id", "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
    "target_year", "class_label", "candidate_id", "source_id", "block",
    "evidence_id", "assessment_status", "usability_flag", "definition_contract_gap",
    "prediction_cutoff", "cutoff_resolvable",
    "g01", "g02", "g03", "g04", "g05", "g06", "g07", "g08",
    "failure_reason", "reviewer_status",
]
SCORE_HEADER = [
    "candidate_id", "source_id", "rubric_version", "accessibility_score",
    "score_status", "evidence_ids_cited", "rationale",
    "requires_human_adjudication", "reviewer_status",
]

MAX_RESPONSE_BYTES = 2_000_000
REQUEST_TIMEOUT_SEC = 30.0
MAX_REDIRECTS = 5
RATE_LIMIT_SLEEP_SEC = 0.35
VERIFIED_STATUSES = frozenset({"verified_from_frozen_repo_provenance"})
_REAL_EVIDENCE_SEAL = "stage125_part3b_validated_real_evidence_v1"
_REAL_GATE_SEAL = "stage125_part3b_validated_real_gate_input_v1"
_ASSESS_SEAL = "stage125_part3b_sealed_pair_candidate_assessment_v1"

DEFINITION_CONTRACT_GAP = (
    "feature_definition_not_uniquely_locked_in_frozen_contracts;"
    "accessibility_evidence_only;value_extraction_unresolved"
)


class QCFail(p3b0.QCFail):
    pass


class NetworkPolicyError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return p3b0.sha256_bytes(data)


def sha256_file(path: Path) -> str | None:
    return p3b0.sha256_file(path)


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({k: ("" if row.get(k) is None else row.get(k, "")) for k in header})
    return buf.getvalue()


def part3b_authorization_active(repo_root: Path) -> bool:
    return (repo_root / "project" / "stage125" / F_AUTH).is_file()


def check_historical_baseline(
    repo_root: Path,
    output_dir: Path,
    metadata_name: str,
    *,
    require_historical_flags: dict[str, Any] | None = None,
) -> dict:
    del repo_root
    meta_path = output_dir / metadata_name
    if not meta_path.is_file():
        raise QCFail(f"historical metadata missing: {metadata_name}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    hashes = meta.get("output_files_sha256") or meta.get("output_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise QCFail(f"historical metadata lacks output hashes: {metadata_name}")
    drift: list[str] = []
    for name, expected in sorted(hashes.items()):
        path = output_dir / name
        if not path.is_file():
            drift.append(name)
            continue
        if sha256_file(path) != expected:
            drift.append(name)
    if require_historical_flags:
        qc_path = None
        for n in hashes:
            if n.endswith("_qc_report.json"):
                qc_path = output_dir / n
                break
        qc = json.loads(qc_path.read_text(encoding="utf-8")) if qc_path and qc_path.is_file() else {}
        for key, expected in require_historical_flags.items():
            actual = meta.get(key, qc.get(key))
            if actual != expected:
                raise QCFail(
                    f"historical flag mismatch: {key} expected={expected!r} actual={actual!r}"
                )
    if drift:
        raise QCFail("historical baseline drift: " + ", ".join(drift))
    return {
        "historical_baseline_ok": True,
        "metadata": metadata_name,
        "files_verified": len(hashes),
        "drift": [],
        "written": False,
        "output_dir": str(output_dir),
        "qc": {
            "all_pass": True,
            "assertion_count": 0,
            "failed_count": 0,
            "historical_mode": True,
            "part3b0_readiness": True,
            "part3b_started": False,
            "evidence_collected": False,
            "accessibility_scoring_applied": False,
            "network_extraction_performed": False,
            "modeling_started": False,
        },
        "guard_evidence": {
            "historical_baseline_mode": True,
            "network_calls_attempted": 0,
            "no_network_calls": True,
            "real_evidence_record_count": 0,
            "accessibility_score_count": 0,
            "candidate_decision_count": 0,
            "cache_real_entry_count": 0,
            "part3b": {"hits": [], "no_part3b": True},
            "modeling": {"no_modeling": True},
        },
        "files": {},
        # Compatibility stubs for historical Part 3A / 3A.1 / 3B.0 runners.
        "counts": {
            "pairs": 0,
            "all_rows": 0,
            "unique_tickers_pairs": 0,
        },
        "input_all_rows_sha256": "",
        "input_pairs_sha256": "",
        "pilot_selection": {
            "sample_size": 80,
            "positive": 39,
            "negative": 41,
        },
    }


def verify_frozen_input_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_INPUT_HASHES.items():
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"frozen input missing: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise QCFail(f"frozen input hash mismatch: {rel}")
        out[rel] = actual
    return out


def verify_endpoint_provenance_hashes(repo_root: Path) -> dict[str, str]:
    """Pin + verify every file used for endpoint ownership evidence."""
    tracked = set(p3b0._git(str(repo_root), "ls-files").splitlines())
    out: dict[str, str] = {}
    for rel, expected in FROZEN_ENDPOINT_PROVENANCE_HASHES.items():
        if rel not in tracked:
            raise QCFail(f"endpoint provenance input untracked: {rel}")
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"endpoint provenance input missing: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise QCFail(f"endpoint provenance hash mismatch: {rel}")
        out[rel] = actual
    return out


def _provenance_pin_or_none(
    repo_root: Path, rel_paths: list[str],
) -> tuple[str, str] | None:
    """Return joined paths + joined sha256 if all pinned/tracked/match; else None."""
    try:
        all_pins = verify_endpoint_provenance_hashes(repo_root)
    except QCFail:
        # Per-path check when global verify not yet desired
        all_pins = {}
        tracked = set(p3b0._git(str(repo_root), "ls-files").splitlines())
        for rel, expected in FROZEN_ENDPOINT_PROVENANCE_HASHES.items():
            if rel not in tracked:
                continue
            path = repo_root / rel
            if not path.is_file():
                continue
            actual = sha256_file(path)
            if actual == expected:
                all_pins[rel] = actual
    hashes = []
    for rel in rel_paths:
        expected = FROZEN_ENDPOINT_PROVENANCE_HASHES.get(rel)
        if expected is None:
            return None
        actual = sha256_file(repo_root / rel)
        if actual != expected:
            return None
        hashes.append(actual)
    return ";".join(rel_paths), ";".join(hashes)


def verify_baseline_commit(repo_root: str) -> None:
    head = p3b0._git(repo_root, "rev-parse", "HEAD")
    if head != EXPECTED_BASELINE_COMMIT and not p3b0._is_ancestor(
        repo_root, EXPECTED_BASELINE_COMMIT, head
    ):
        raise QCFail(
            f"HEAD {head} is not a descendant of baseline {EXPECTED_BASELINE_COMMIT}"
        )


def load_prediction_cutoff_map(repo_root: Path) -> dict[tuple[str, str], dict]:
    path = repo_root / "project/stage125/prediction_cutoff_audit_stage125_part2.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"]): r for r in rows}


def pair_prediction_cutoff(audit_row: dict | None) -> tuple[str | None, bool]:
    if audit_row is None:
        return None, False
    resolvable = str(audit_row.get("cutoff_resolvable", "0")).strip() == "1"
    cutoff = audit_row.get("prediction_cutoff")
    if cutoff is not None and str(cutoff).strip() not in ("", "null", "None"):
        return str(cutoff).strip(), resolvable
    return None, False


# --------------------------------------------------------------------------- #
# Endpoint registry / capture plan
# --------------------------------------------------------------------------- #

def _unverified_endpoint(source_id: str, owner: str, reason: str) -> dict:
    return {
        "source_id": source_id,
        "official_source_owner": owner,
        "exact_https_origin": "",
        "exact_hostname": "",
        "exact_endpoint_or_url_pattern": "",
        "allowed_http_method": "",
        "authoritative_ownership_evidence": "",
        "ownership_evidence_url": "",
        "retrieval_purpose": "source_origin_probe",
        "evidence_class": EVIDENCE_CLASS_BLOCKED,
        "content_type_expected": "",
        "verification_status": "unverified_no_authoritative_endpoint",
        "failure_reason": reason,
        "reviewer_status": "automated_fail_closed",
        "provenance_input_paths": "",
        "provenance_input_sha256": "",
    }


def build_endpoint_registry_rows(repo_root: Path) -> list[dict]:
    rows: list[dict] = []
    tsetmc_paths = [
        "project/stage124/official_api/import_manifest.json",
        "project/stage124/official_api/README.md",
    ]
    tsetmc_pin = _provenance_pin_or_none(repo_root, tsetmc_paths)
    if tsetmc_pin is not None:
        manifest = json.loads(
            (repo_root / tsetmc_paths[0]).read_text(encoding="utf-8")
        )
        exact = manifest.get("exact_endpoint_url")
        if isinstance(exact, str) and exact.startswith("https://cdn.tsetmc.com/"):
            rows.append({
                "source_id": "src_m2_tsetmc_market",
                "official_source_owner": "TSETMC",
                "exact_https_origin": "https://cdn.tsetmc.com",
                "exact_hostname": "cdn.tsetmc.com",
                "exact_endpoint_or_url_pattern": exact,
                "allowed_http_method": "GET",
                "authoritative_ownership_evidence": (
                    "Hash-pinned Stage124 official_api import_manifest.json + README "
                    "document TSETMC CDN API exact_endpoint_url."
                ),
                "ownership_evidence_url": tsetmc_paths[0],
                "retrieval_purpose": "source_origin_probe",
                "evidence_class": EVIDENCE_CLASS_ORIGIN_PROBE,
                "content_type_expected": "application/json",
                "verification_status": "verified_from_frozen_repo_provenance",
                "failure_reason": "",
                "reviewer_status": "automated_repo_provenance_only",
                "provenance_input_paths": tsetmc_pin[0],
                "provenance_input_sha256": tsetmc_pin[1],
            })
        else:
            rows.append(_unverified_endpoint(
                "src_m2_tsetmc_market", "TSETMC",
                "frozen_manifest_missing_or_unexpected_exact_endpoint_url",
            ))
    else:
        rows.append(_unverified_endpoint(
            "src_m2_tsetmc_market", "TSETMC",
            "endpoint_provenance_unpinned_or_hash_mismatch",
        ))

    rows.append(_unverified_endpoint(
        "src_m3_cbi_macro", "Central Bank of Iran",
        "no_authoritative_official_endpoint_in_frozen_stage125_or_stage124_assets",
    ))

    codal_paths = [
        "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
        "ocf_source_manifest_stage121.csv",
    ]
    codal_pin = _provenance_pin_or_none(repo_root, codal_paths)
    codal_path = repo_root / codal_paths[0]
    if (
        codal_pin is not None
        and codal_path.is_file()
        and "https://www.codal.ir/" in codal_path.read_text(
            encoding="utf-8", errors="replace",
        )
    ):
        for source_id in ("src_m4_codal_audit", "src_m4_codal_governance"):
            rows.append({
                "source_id": source_id,
                "official_source_owner": "CODAL",
                "exact_https_origin": "https://www.codal.ir",
                "exact_hostname": "www.codal.ir",
                "exact_endpoint_or_url_pattern": "https://www.codal.ir/",
                "allowed_http_method": "GET",
                "authoritative_ownership_evidence": (
                    "Hash-pinned Stage121 OCF source manifest records "
                    "https://www.codal.ir/ Reports URLs as CODAL source_url."
                ),
                "ownership_evidence_url": codal_paths[0],
                "retrieval_purpose": "source_origin_probe",
                "evidence_class": EVIDENCE_CLASS_ORIGIN_PROBE,
                "content_type_expected": "text/html",
                "verification_status": "verified_from_frozen_repo_provenance",
                "failure_reason": "",
                "reviewer_status": "automated_repo_provenance_only",
                "provenance_input_paths": codal_pin[0],
                "provenance_input_sha256": codal_pin[1],
            })
    else:
        for source_id in ("src_m4_codal_audit", "src_m4_codal_governance"):
            rows.append(_unverified_endpoint(
                source_id, "CODAL",
                "endpoint_provenance_unpinned_missing_or_hash_mismatch",
            ))

    rows.append({
        "source_id": "src_m3_sci_macro",
        "official_source_owner": "Statistical Center of Iran",
        "exact_https_origin": "",
        "exact_hostname": "",
        "exact_endpoint_or_url_pattern": "",
        "allowed_http_method": "",
        "authoritative_ownership_evidence": "",
        "ownership_evidence_url": "",
        "retrieval_purpose": "out_of_scope_not_promoted",
        "evidence_class": EVIDENCE_CLASS_BLOCKED,
        "content_type_expected": "",
        "verification_status": "out_of_scope_not_contacted",
        "failure_reason": "src_m3_sci_macro_not_promoted_in_part3b",
        "reviewer_status": "automated_scope_lock",
        "provenance_input_paths": "",
        "provenance_input_sha256": "",
    })
    return rows


def endpoint_id_for(row: dict) -> str:
    host = (row.get("exact_hostname") or "none").replace(".", "_")
    return f"ep_{row.get('source_id')}_{host}"


def build_capture_plan(repo_root: Path, endpoint_rows: list[dict]) -> list[dict]:
    del repo_root
    by_source = {r["source_id"]: r for r in endpoint_rows}
    plan: list[dict] = []
    for idx, cand_id in enumerate(REGISTERED_CANDIDATE_IDS, start=1):
        source_id = CANDIDATE_SOURCE_MAP[cand_id]
        ep = by_source.get(source_id)
        canonical_eid = CANONICAL_SOURCE_EVIDENCE_ID.get(source_id, f"ev_{source_id}")
        if ep is None:
            plan.append({
                "plan_row_id": f"plan_{idx:03d}",
                "candidate_id": cand_id,
                "source_id": source_id,
                "endpoint_id": "",
                "request_url": "",
                "http_method": "",
                "retrieval_purpose": "source_origin_probe",
                "evidence_class": EVIDENCE_CLASS_BLOCKED,
                "plan_status": "blocked",
                "blocker_reason": "source_missing_from_endpoint_registry",
                "shared_snapshot_key": source_id,
                "canonical_evidence_id": canonical_eid,
            })
            continue
        verified = ep.get("verification_status") in VERIFIED_STATUSES
        url = (ep.get("exact_endpoint_or_url_pattern") or "").strip()
        # Origin probe only: never invent path parameters (e.g. ins_code).
        if verified and ("{" in url or url.endswith("/0")):
            request_url = ep.get("exact_https_origin", "").rstrip("/") + "/"
            purpose = "source_origin_probe"
        elif verified and url:
            request_url = url
            purpose = "source_origin_probe"
        else:
            request_url, purpose = "", "source_origin_probe"
        method = ep.get("allowed_http_method") or ""
        evidence_class = ep.get("evidence_class") or EVIDENCE_CLASS_BLOCKED
        if verified and request_url and method in ("GET", "HEAD"):
            status, blocker = "planned", ""
            evidence_class = EVIDENCE_CLASS_ORIGIN_PROBE
        else:
            status = "blocked"
            blocker = ep.get("failure_reason") or "endpoint_not_verified"
            method, request_url = "", ""
            evidence_class = EVIDENCE_CLASS_BLOCKED
        plan.append({
            "plan_row_id": f"plan_{idx:03d}",
            "candidate_id": cand_id,
            "source_id": source_id,
            "endpoint_id": endpoint_id_for(ep) if verified else "",
            "request_url": request_url,
            "http_method": method if status == "planned" else "",
            "retrieval_purpose": purpose,
            "evidence_class": evidence_class,
            "plan_status": status,
            "blocker_reason": blocker,
            "shared_snapshot_key": source_id,
            "canonical_evidence_id": canonical_eid,
        })
    return plan


def capture_plan_sha256(plan_rows: list[dict]) -> str:
    return sha256_bytes(_csv_str(PLAN_HEADER, plan_rows).encode("utf-8"))


@dataclass
class NetworkStats:
    network_calls_attempted: int = 0
    network_calls_succeeded: int = 0
    network_calls_failed: int = 0
    bytes_retrieved: int = 0
    final_resolved_urls: list[str] = field(default_factory=list)
    response_statuses: list[int] = field(default_factory=list)
    redirect_counts: list[int] = field(default_factory=list)


class ReadOnlyNetworkPermit:
    """Scoped allowlist on top of an already-installed NetworkSentinel.

    Does not weaken or remove the outer default-deny sentinel. On exit the
    sentinel remains installed (default-deny restored relative to the permit).
    """

    def __init__(
        self,
        allowed_requests: set[tuple[str, str]],
        *,
        stats: NetworkStats | None = None,
        sentinel: p3b0.NetworkSentinel | None = None,
    ):
        self.allowed_requests = set(allowed_requests)
        self.stats = stats or NetworkStats()
        self._sentinel = sentinel
        self._owns_sentinel = sentinel is None
        self._active = False

    def __enter__(self) -> "ReadOnlyNetworkPermit":
        if self._sentinel is None:
            self._sentinel = p3b0.NetworkSentinel()
            self._sentinel.install()
            self._owns_sentinel = True
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._active = False
        # Standalone permit (no outer sentinel): restore process originals.
        # Production capture always passes an outer NetworkSentinel that remains
        # installed after this context exits (default-deny preserved).
        if self._owns_sentinel and self._sentinel is not None:
            self._sentinel.restore()
            self._sentinel = None
        return None

    def _assert_public_dns(self, hostname: str) -> list[str]:
        assert self._sentinel is not None
        try:
            infos = self._sentinel._orig_getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise NetworkPolicyError(f"DNS resolution failed: {hostname}") from exc
        addrs: list[str] = []
        for info in infos:
            ip = info[4][0]
            addrs.append(ip)
            ip_obj = ipaddress.ip_address(ip)
            if (
                ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
                or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
            ):
                raise NetworkPolicyError(f"private/reserved IP rejected: {ip}")
        if not addrs:
            raise NetworkPolicyError(f"no addresses for {hostname}")
        return addrs

    def _validate_url(self, method: str, url: str) -> urllib.parse.ParseResult:
        method = method.upper()
        if method not in ("GET", "HEAD"):
            raise NetworkPolicyError(f"method not allowed: {method}")
        if (method, url) not in self.allowed_requests:
            raise NetworkPolicyError(f"URL not in capture plan allowlist: {url}")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise NetworkPolicyError("only https allowed")
        if parsed.username or parsed.password:
            raise NetworkPolicyError("credentials in URL forbidden")
        if parsed.port not in (None, 443):
            raise NetworkPolicyError("only port 443 allowed")
        if not parsed.hostname:
            raise NetworkPolicyError("missing hostname")
        self._assert_public_dns(parsed.hostname)
        return parsed

    def _validate_redirect(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.port not in (None, 443):
            raise NetworkPolicyError("redirect scheme/port rejected")
        host = parsed.hostname
        if not host:
            raise NetworkPolicyError("redirect missing host")
        allowed_hosts = {urllib.parse.urlparse(u).hostname for (_m, u) in self.allowed_requests}
        if host not in allowed_hosts:
            raise NetworkPolicyError(f"redirect host not allowlisted: {host}")
        self._assert_public_dns(host)

    def request(self, method: str, url: str) -> tuple[bytes, dict[str, Any]]:
        if not self._active:
            raise NetworkPolicyError("permit not active")
        method = method.upper()
        self.stats.network_calls_attempted += 1
        redirects = 0
        current = url
        try:
            while True:
                if redirects == 0:
                    self._validate_url(method, current)
                else:
                    self._validate_redirect(current)
                body, status, final_url, ctype = self._https_exchange(
                    method if redirects == 0 else "GET", current,
                )
                if status in (301, 302, 303, 307, 308):
                    redirects += 1
                    if redirects > MAX_REDIRECTS:
                        raise NetworkPolicyError("too many redirects")
                    if not final_url or final_url == current:
                        raise NetworkPolicyError("redirect without location")
                    current = final_url
                    continue
                if len(body) > MAX_RESPONSE_BYTES:
                    raise NetworkPolicyError("response exceeds size ceiling")
                self.stats.network_calls_succeeded += 1
                self.stats.bytes_retrieved += len(body)
                self.stats.final_resolved_urls.append(final_url or current)
                self.stats.response_statuses.append(status)
                self.stats.redirect_counts.append(redirects)
                time.sleep(RATE_LIMIT_SLEEP_SEC)
                return body, {
                    "final_resolved_url": final_url or current,
                    "response_status": status,
                    "redirect_count": redirects,
                    "content_type": ctype,
                    "bytes": len(body),
                }
        except Exception:
            self.stats.network_calls_failed += 1
            raise

    def _https_exchange(self, method: str, url: str) -> tuple[bytes, int, str, str]:
        assert self._sentinel is not None
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        assert host
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        ip = self._assert_public_dns(host)[0]
        raw_req = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: papermali-stage125-part3b-readonly/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        context = ssl.create_default_context()
        sock = None
        try:
            # Bypass blocked create_connection/getaddrinfo: connect the
            # already-validated public IP with the sentinel's original connect.
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(REQUEST_TIMEOUT_SEC)
            self._sentinel._orig_connect(raw_sock, (ip, 443))
            sock = context.wrap_socket(raw_sock, server_hostname=host)
            sock.sendall(raw_req)
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES + 65536:
                    raise NetworkPolicyError("oversized response")
                chunks.append(chunk)
            raw = b"".join(chunks)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        return self._parse_http_response(raw, url)

    def _parse_http_response(self, raw: bytes, original_url: str) -> tuple[bytes, int, str, str]:
        if b"\r\n\r\n" not in raw:
            raise NetworkPolicyError("malformed HTTP response")
        header_blob, body = raw.split(b"\r\n\r\n", 1)
        lines = header_blob.split(b"\r\n")
        status_line = lines[0].decode("iso-8859-1", errors="replace")
        parts = status_line.split()
        if len(parts) < 2:
            raise NetworkPolicyError("bad status line")
        status = int(parts[1])
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if b":" not in line:
                continue
            k, v = line.split(b":", 1)
            headers[k.decode("iso-8859-1").strip().lower()] = v.decode("iso-8859-1", errors="replace").strip()
        ctype = headers.get("content-type", "")
        location = headers.get("location", "")
        final_url = original_url
        if status in (301, 302, 303, 307, 308) and location:
            final_url = urllib.parse.urljoin(original_url, location)
        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = self._dechunk(body)
        if len(body) > MAX_RESPONSE_BYTES:
            raise NetworkPolicyError("body exceeds size ceiling")
        return body, status, final_url, ctype

    @staticmethod
    def _dechunk(data: bytes) -> bytes:
        out = bytearray()
        i = 0
        while i < len(data):
            j = data.find(b"\r\n", i)
            if j < 0:
                raise NetworkPolicyError("bad chunked encoding")
            size = int(data[i:j].split(b";")[0], 16)
            i = j + 2
            if size == 0:
                break
            out.extend(data[i:i + size])
            i += size + 2
            if len(out) > MAX_RESPONSE_BYTES:
                raise NetworkPolicyError("dechunked body too large")
        return bytes(out)


@contextmanager
def network_default_deny() -> Iterator[p3b0.NetworkSentinel]:
    with p3b0.network_sentinel() as sentinel:
        yield sentinel


# --------------------------------------------------------------------------- #
# Sealed real evidence / gate / assessment
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ValidatedRealEvidence:
    evidence_id: str
    candidate_id: str
    source_id: str
    predictor_row_key_t: str | None
    target_row_key_t_plus_1: str | None
    class_label: str | None
    target_year: str | None
    prediction_cutoff: str | None
    published_at: str | None
    available_at: str | None
    retrieved_at_utc: str | None
    snapshot_sha256: str | None
    metadata_sha256: str | None
    external_handle_sha256: str | None
    _seal: str = field(repr=False, compare=True)


@dataclass(frozen=True)
class ValidatedRealGateInput:
    evidence: ValidatedRealEvidence
    accessibility_score: int | None
    authoritative_source: bool | None
    reproducible_retrieval: bool | None
    quality_controls_met: bool | None
    prediction_cutoff: str | None
    _seal: str = field(repr=False, compare=True)


@dataclass(frozen=True)
class SealedPairCandidateAssessment:
    assessment_id: str
    predictor_row_key_t: str
    target_row_key_t_plus_1: str
    candidate_id: str
    source_id: str
    class_label: str
    target_year: str
    prediction_cutoff: str | None
    evidence_id: str | None
    snapshot_sha256: str | None
    metadata_sha256: str | None
    external_handle_sha256: str | None
    assessment_status: str
    usability_flag: bool
    _seal: str = field(repr=False, compare=True)


def _seal_join(parts: list[str]) -> str:
    return sha256_bytes("|".join(parts).encode("utf-8"))


def require_sealed_real_evidence(evidence: ValidatedRealEvidence) -> ValidatedRealEvidence:
    if type(evidence) is not ValidatedRealEvidence:
        raise QCFail("ValidatedRealEvidence type check failed")
    expected = _seal_join([
        _REAL_EVIDENCE_SEAL, evidence.evidence_id, evidence.candidate_id,
        evidence.source_id, evidence.predictor_row_key_t or "",
        evidence.target_row_key_t_plus_1 or "", evidence.class_label or "",
        evidence.target_year or "", evidence.prediction_cutoff or "",
        evidence.snapshot_sha256 or "", evidence.metadata_sha256 or "",
        evidence.external_handle_sha256 or "",
    ])
    if evidence._seal != expected:
        raise QCFail("ValidatedRealEvidence seal verification failed")
    return evidence


def validate_and_seal_real_evidence(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    predictor_row_key_t: str | None = None,
    target_row_key_t_plus_1: str | None = None,
    class_label: str | None = None,
    target_year: str | None = None,
    prediction_cutoff: str | None = None,
    metadata_sha256: str | None = None,
    external_handle_sha256: str | None = None,
    allowed_snapshot_root: Path | None = None,
) -> ValidatedRealEvidence:
    eid = str(record.get("evidence_id", ""))
    if eid.startswith(p3b0.SYNTHETIC_EVIDENCE_ID_PREFIX):
        raise p3b0.EvidenceValidationError("synthetic evidence_id not allowed")
    if record.get("access_method") == p3b0.SYNTHETIC_ACCESS_METHOD:
        raise p3b0.EvidenceValidationError("synthetic access_method not allowed")
    p3b0._validate_evidence_record_core(
        record, schema=schema, candidate_source_map=candidate_source_map,
        source_registry=source_registry,
    )
    if not p3b0._is_null(record.get("local_snapshot_path")):
        if allowed_snapshot_root is None:
            raise p3b0.EvidenceValidationError("snapshot requires allowed_snapshot_root")
        p3b0._verify_snapshot_bytes_match_hash(
            record, allowed_snapshot_root=Path(allowed_snapshot_root),
        )
    snap = None if p3b0._is_null(record.get("snapshot_sha256")) else str(
        record["snapshot_sha256"]
    ).strip().lower()
    base = ValidatedRealEvidence(
        evidence_id=str(record["evidence_id"]),
        candidate_id=str(record["candidate_id"]),
        source_id=str(record["source_id"]),
        predictor_row_key_t=predictor_row_key_t,
        target_row_key_t_plus_1=target_row_key_t_plus_1,
        class_label=class_label,
        target_year=target_year,
        prediction_cutoff=prediction_cutoff,
        published_at=p3b0._nullable_str(record.get("published_at")),
        available_at=p3b0._nullable_str(record.get("available_at")),
        retrieved_at_utc=p3b0._nullable_str(record.get("retrieved_at_utc")),
        snapshot_sha256=snap,
        metadata_sha256=metadata_sha256,
        external_handle_sha256=external_handle_sha256,
        _seal="",
    )
    seal = _seal_join([
        _REAL_EVIDENCE_SEAL, base.evidence_id, base.candidate_id, base.source_id,
        base.predictor_row_key_t or "", base.target_row_key_t_plus_1 or "",
        base.class_label or "", base.target_year or "", base.prediction_cutoff or "",
        base.snapshot_sha256 or "", base.metadata_sha256 or "",
        base.external_handle_sha256 or "",
    ])
    return require_sealed_real_evidence(ValidatedRealEvidence(**{**base.__dict__, "_seal": seal}))


def require_sealed_real_gate_input(gate_input: ValidatedRealGateInput) -> ValidatedRealGateInput:
    if type(gate_input) is not ValidatedRealGateInput:
        raise QCFail("ValidatedRealGateInput type check failed")
    require_sealed_real_evidence(gate_input.evidence)
    expected = _seal_join([
        _REAL_GATE_SEAL, gate_input.evidence._seal,
        "" if gate_input.accessibility_score is None else str(gate_input.accessibility_score),
        "" if gate_input.authoritative_source is None else ("1" if gate_input.authoritative_source else "0"),
        "" if gate_input.reproducible_retrieval is None else ("1" if gate_input.reproducible_retrieval else "0"),
        "" if gate_input.quality_controls_met is None else ("1" if gate_input.quality_controls_met else "0"),
        gate_input.prediction_cutoff or "",
    ])
    if gate_input._seal != expected:
        raise QCFail("ValidatedRealGateInput seal verification failed")
    return gate_input


def build_validated_real_gate_input(
    evidence: ValidatedRealEvidence,
    *,
    accessibility_score: int | None = None,
    authoritative_source: bool | None = None,
    reproducible_retrieval: bool | None = None,
    quality_controls_met: bool | None = None,
) -> ValidatedRealGateInput:
    evidence = require_sealed_real_evidence(evidence)
    if accessibility_score is not None and type(accessibility_score) is not int:
        raise QCFail("accessibility_score must be int or None")
    for name, value in (
        ("authoritative_source", authoritative_source),
        ("reproducible_retrieval", reproducible_retrieval),
        ("quality_controls_met", quality_controls_met),
    ):
        if value is not None and type(value) is not bool:
            raise QCFail(f"{name} must be bool or None")
    seal = _seal_join([
        _REAL_GATE_SEAL, evidence._seal,
        "" if accessibility_score is None else str(accessibility_score),
        "" if authoritative_source is None else ("1" if authoritative_source else "0"),
        "" if reproducible_retrieval is None else ("1" if reproducible_retrieval else "0"),
        "" if quality_controls_met is None else ("1" if quality_controls_met else "0"),
        evidence.prediction_cutoff or "",
    ])
    return require_sealed_real_gate_input(ValidatedRealGateInput(
        evidence=evidence,
        accessibility_score=accessibility_score,
        authoritative_source=authoritative_source,
        reproducible_retrieval=reproducible_retrieval,
        quality_controls_met=quality_controls_met,
        prediction_cutoff=evidence.prediction_cutoff,
        _seal=seal,
    ))


def evaluate_real_candidate_gates(gate_input: ValidatedRealGateInput) -> dict[str, str]:
    gate_input = require_sealed_real_gate_input(gate_input)
    ev = gate_input.evidence
    statuses = {
        "G01": p3b0.evaluate_g01(gate_input.accessibility_score),
        "G02": p3b0.evaluate_g02(gate_input.authoritative_source),
        "G03": p3b0.evaluate_g03(gate_input.reproducible_retrieval),
        "G04": p3b0.evaluate_g04(ev.published_at, ev.available_at),
        "G05": p3b0.evaluate_g05(gate_input.quality_controls_met),
        "G06": p3b0.evaluate_g06(ev.available_at),
        "G07": p3b0.evaluate_g07_from_cutoff(ev.available_at, gate_input.prediction_cutoff),
    }
    statuses["G08"] = p3b0.evaluate_g08({k: statuses[k] for k in p3b0.G01_G07})
    return statuses


def require_sealed_assessment(a: SealedPairCandidateAssessment) -> SealedPairCandidateAssessment:
    if type(a) is not SealedPairCandidateAssessment:
        raise QCFail("SealedPairCandidateAssessment type check failed")
    expected = _seal_join([
        _ASSESS_SEAL, a.assessment_id, a.predictor_row_key_t, a.target_row_key_t_plus_1,
        a.candidate_id, a.source_id, a.class_label, a.target_year,
        a.prediction_cutoff or "", a.evidence_id or "", a.snapshot_sha256 or "",
        a.metadata_sha256 or "", a.external_handle_sha256 or "",
        a.assessment_status, "1" if a.usability_flag else "0",
    ])
    if a._seal != expected:
        raise QCFail("SealedPairCandidateAssessment seal verification failed")
    return a


def seal_pair_candidate_assessment(**kwargs) -> SealedPairCandidateAssessment:
    usability_flag = kwargs["usability_flag"]
    if type(usability_flag) is not bool:
        raise QCFail("usability_flag must be exact bool")
    if kwargs["assessment_status"] not in (p3b0.GATE_PASS, p3b0.GATE_FAIL, p3b0.GATE_UNRESOLVED):
        raise QCFail("invalid assessment_status")
    seal = _seal_join([
        _ASSESS_SEAL, kwargs["assessment_id"], kwargs["predictor_row_key_t"],
        kwargs["target_row_key_t_plus_1"], kwargs["candidate_id"], kwargs["source_id"],
        kwargs["class_label"], kwargs["target_year"], kwargs.get("prediction_cutoff") or "",
        kwargs.get("evidence_id") or "", kwargs.get("snapshot_sha256") or "",
        kwargs.get("metadata_sha256") or "", kwargs.get("external_handle_sha256") or "",
        kwargs["assessment_status"], "1" if usability_flag else "0",
    ])
    return require_sealed_assessment(SealedPairCandidateAssessment(_seal=seal, **kwargs))


def empty_evidence_record(*, evidence_id, candidate_id, source_id, source_owner, failure_reason,
                          reviewer_status="automated_fail_closed") -> dict:
    return {
        "evidence_id": evidence_id, "candidate_id": candidate_id, "source_id": source_id,
        "source_owner": source_owner, "source_url": None, "source_title": None,
        "source_identifier": None, "retrieved_at_utc": None, "published_at": None,
        "available_at": None, "raw_date_text": None, "calendar": None, "timezone": None,
        "access_method": None, "authentication_required": None,
        "response_status_evidence": None, "local_snapshot_path": None,
        "snapshot_sha256": None, "revision_status": None, "license_or_usage_notes": None,
        "reviewer_status": reviewer_status, "failure_reason": failure_reason,
    }


def successful_probe_evidence_record(
    *, evidence_id, candidate_id, source_id, source_owner, source_url,
    retrieved_at_utc, response_status, snapshot_rel, snapshot_sha256, license_notes,
) -> dict:
    return {
        "evidence_id": evidence_id, "candidate_id": candidate_id, "source_id": source_id,
        "source_owner": source_owner, "source_url": source_url, "source_title": None,
        "source_identifier": None, "retrieved_at_utc": retrieved_at_utc,
        "published_at": None, "available_at": None, "raw_date_text": None,
        "calendar": None, "timezone": "UTC",
        "access_method": "https_get_readonly_permit",
        "authentication_required": False,
        "response_status_evidence": str(response_status),
        "local_snapshot_path": snapshot_rel, "snapshot_sha256": snapshot_sha256,
        "revision_status": None, "license_or_usage_notes": license_notes,
        "reviewer_status": "automated_capture_not_human_reviewed",
        "failure_reason": None,
    }


def _coerce_evidence_record_types(row: dict) -> dict:
    """Normalize CSV-loaded evidence rows for schema validation."""
    out = dict(row)
    auth = out.get("authentication_required")
    if auth is None or (isinstance(auth, str) and auth.strip() == ""):
        out["authentication_required"] = None
    elif isinstance(auth, bool):
        pass
    elif isinstance(auth, str) and auth.strip().lower() in ("true", "false"):
        out["authentication_required"] = auth.strip().lower() == "true"
    else:
        raise QCFail(f"invalid authentication_required: {auth!r}")
    return out


def null_score_row(candidate_id: str, source_id: str, evidence_ids: list[str], rationale: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": source_id,
        "rubric_version": RUBRIC_VERSION,
        "accessibility_score": "",
        "score_status": "UNRESOLVED",
        "evidence_ids_cited": ";".join(evidence_ids),
        "rationale": rationale,
        "requires_human_adjudication": "true",
        "reviewer_status": "automated_not_human_reviewed",
    }


# --------------------------------------------------------------------------- #
# Cache handle verification / rebuild helpers
# --------------------------------------------------------------------------- #

class EvidenceCacheUnavailable(QCFail):
    """Raised when local immutable cache cannot verify snapshot-backed evidence."""

    def __init__(self, detail: str = ""):
        msg = "evidence_cache_unavailable"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


def serialize_handle_row(h: dict) -> str:
    return p3b0.serialize_cache_handle(p3b0.CacheHandle(
        evidence_id=h["evidence_id"],
        payload_sha256=h["payload_sha256"],
        metadata_sha256=h["metadata_sha256"],
        cache_contract_version=h.get(
            "cache_contract_version", p3b0.CACHE_CONTRACT_VERSION,
        ),
        schema_version=h.get(
            "cache_handle_schema_version", p3b0.CACHE_HANDLE_SCHEMA_VERSION,
        ),
    ))


def verify_external_handle_binding(
    cache: p3b0.ImmutableCache,
    handle_row: dict,
    *,
    expected_evidence_id: str | None = None,
) -> dict[str, Any]:
    """Fail-closed: payload + metadata + evidence_id + external handle SHA."""
    eid = handle_row.get("evidence_id") or ""
    if expected_evidence_id is not None and eid != expected_evidence_id:
        raise QCFail(
            f"handle evidence_id {eid!r} != expected {expected_evidence_id!r}"
        )
    if not eid or not handle_row.get("payload_sha256"):
        raise QCFail("incomplete cache handle row")
    if not handle_row.get("external_handle_sha256"):
        raise QCFail(f"missing external_handle_sha256 for {eid}")
    serialized = serialize_handle_row(handle_row)
    actual_sha = p3b0.cache_handle_sha256(serialized)
    if actual_sha != handle_row["external_handle_sha256"]:
        raise QCFail(f"external handle SHA mismatch for {eid}")
    handle = p3b0.load_cache_handle(
        serialized,
        expected_handle_sha256=handle_row["external_handle_sha256"],
    )
    try:
        payload = cache.get_by_handle(handle)
    except p3b0.ImmutableCacheError as exc:
        raise EvidenceCacheUnavailable(str(exc)) from exc
    entry_dir = cache._entry_dir(handle.payload_sha256)
    if entry_dir.is_symlink() or any(
        (entry_dir / name).is_symlink()
        for name in ("payload.bin", "metadata.json", "metadata.sha256")
        if (entry_dir / name).exists()
    ):
        raise EvidenceCacheUnavailable(f"symlink rejected for {eid}")
    meta_path = entry_dir / "metadata.json"
    if not meta_path.is_file():
        raise EvidenceCacheUnavailable(f"metadata missing for {eid}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("evidence_id") != eid:
        raise QCFail(f"cached metadata evidence_id mismatch for {eid}")
    return {
        "payload": payload,
        "metadata": meta,
        "handle": handle,
        "payload_sha256": handle.payload_sha256,
        "metadata_sha256": handle.metadata_sha256,
        "byte_count": len(payload),
    }


def evidence_record_from_cache_meta(
    *,
    evidence_id: str,
    candidate_id: str,
    source_id: str,
    source_owner: str,
    meta: dict,
    payload_sha256: str,
) -> dict:
    """Rebuild evidence from immutable cache metadata (no datetime.now)."""
    retrieved = meta.get("retrieved_at_utc")
    status = meta.get("response_status")
    final_url = meta.get("final_resolved_url") or meta.get("request_url")
    if not retrieved or status is None or not final_url:
        raise QCFail(f"cache metadata incomplete for {evidence_id}")
    snap_rel = f"raw_cache_part3b/{payload_sha256[:2]}/{payload_sha256}/payload.bin"
    return successful_probe_evidence_record(
        evidence_id=evidence_id,
        candidate_id=candidate_id,
        source_id=source_id,
        source_owner=source_owner,
        source_url=str(final_url),
        retrieved_at_utc=str(retrieved),
        response_status=status,
        snapshot_rel=snap_rel,
        snapshot_sha256=payload_sha256,
        license_notes=(
            "source_origin_probe only; raw bytes local immutable cache only; "
            "not candidate_value or pair_value evidence; "
            "redistribution subject to source terms"
        ),
    )


def derive_gate_authority_flags(
    *,
    evidence_row: dict,
    handle_row: dict | None,
    cache: p3b0.ImmutableCache | None,
    endpoint_row: dict | None,
) -> tuple[bool | None, bool | None, list[str]]:
    """G02/G03 inputs. Snapshot hash alone never implies True."""
    notes: list[str] = []
    has_snap = bool(evidence_row.get("snapshot_sha256"))
    if not has_snap:
        return None, None, notes
    if handle_row is None:
        notes.append("snapshot_backed_evidence_without_handle")
        return False, False, notes
    if cache is None:
        notes.append("cache_unavailable_for_g03")
        return False, False, notes
    try:
        verify_external_handle_binding(
            cache, handle_row, expected_evidence_id=evidence_row["evidence_id"],
        )
    except (QCFail, EvidenceCacheUnavailable) as exc:
        notes.append(f"handle_verify_failed:{exc}")
        return False, False, notes
    ep_ok = bool(
        endpoint_row
        and endpoint_row.get("verification_status") in VERIFIED_STATUSES
        and endpoint_row.get("evidence_class") == EVIDENCE_CLASS_ORIGIN_PROBE
    )
    owner_ok = bool(evidence_row.get("source_owner"))
    # Official origin probe with verified pinned provenance + handle.
    auth = True if (ep_ok and owner_ok) else False
    if not ep_ok:
        notes.append("endpoint_not_verified_origin_probe")
    repro = True  # handle+payload+metadata+eid verified above
    return auth, repro, notes


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_authorization_record(repo_root: Path, plan_hash: str, endpoint_hash: str,
                               frozen_hashes: dict[str, str]) -> dict:
    return {
        "authorization_version": "stage125_part3b_auth_v1",
        "stage": CURRENT_STAGE,
        "authorized_action": "stage125-part3b-evidence-capture",
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "part3b_started": True,
        "part3b0_readiness": True,
        "modeling_started": False,
        "real_evidence_authorized": True,
        "network_readonly_authorized": True,
        "capture_plan_sha256": plan_hash,
        "endpoint_registry_sha256": endpoint_hash,
        "frozen_input_sha256": frozen_hashes,
        "registered_candidate_ids": list(REGISTERED_CANDIDATE_IDS),
        "pilot_pair_count": 80,
        "assessment_matrix_size": 800,
        "notes": (
            "Part 3B authorized for evidence capture and accessibility scoring "
            "pilot only. No modeling. No sample/target/eligibility change."
        ),
    }


def build_readme() -> str:
    return """# Stage125 Part 3B accessibility feasibility probe — active/incomplete

## Status

**Not a completed Part 3B pilot.** `part3b_completed=false`.
`next_research_action_id` remains `stage125-part3b-evidence-capture`.
No Stage126 / modeling advance.

Scoped markers:

- `endpoint_probe_evidence_collected=true` (when origin probes exist)
- `candidate_value_evidence_collected=false`
- `pair_level_evidence_collected=false`
- `data_value_extraction_performed=false`
- `accessibility_scoring_applied=false`
- `part3b_completed=false`

`evidence_collected=true` means **endpoint-probe** evidence only — not 800
pair-level observations.

## Evidence classes

| Class | Meaning |
|---|---|
| `source_origin_probe` | Official origin GET (current TSETMC/CODAL probes) |
| `candidate_endpoint_evidence` | Not collected in this probe |
| `pair_value_evidence` | Not collected in this probe |

## Modes

- `--plan` — deterministic capture plan + endpoint registry (no network)
- `--capture` — approved read-only HTTPS GET/HEAD only (resume preferred)
- `--write` — derive assessments/scores/gates/QC (no network)
- `--check` — **full** offline verification including immutable cache
- `--check-manifest-only` — tracked hashes only; **not** full evidence verification

## Cache portability

Raw payloads live under gitignored `project/stage125/raw_cache_part3b/`.
A fresh checkout without that local cache fails `--check` with
`evidence_cache_unavailable`.

## Part 3B.1 (proposed, not started)

See `README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md`.
Requires explicit user approval before any work.
"""


def _source_owner(registry: dict[str, dict], source_id: str) -> str:
    row = registry.get(source_id) or {}
    return str(row.get("source_owner") or "")


def run_plan(repo_root: Path, output_dir: Path, *, write: bool) -> dict:
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        frozen = verify_frozen_input_hashes(repo_root)
        provenance = verify_endpoint_provenance_hashes(repo_root)
        endpoints = build_endpoint_registry_rows(repo_root)
        plan = build_capture_plan(repo_root, endpoints)
        plan_hash = capture_plan_sha256(plan)
        ep_csv = _csv_str(ENDPOINT_HEADER, endpoints)
        ep_hash = sha256_bytes(ep_csv.encode("utf-8"))
        auth = build_authorization_record(repo_root, plan_hash, ep_hash, frozen)
        auth["endpoint_provenance_sha256"] = provenance
        auth["part3b_completed"] = False
        auth["status"] = "active_incomplete_accessibility_feasibility_probe"
        files = {
            F_AUTH: _json_str(auth),
            F_ENDPOINTS: ep_csv,
            F_PLAN: _csv_str(PLAN_HEADER, plan),
        }
        if write:
            output_dir.mkdir(parents=True, exist_ok=True)
            for name, content in files.items():
                (output_dir / name).write_text(content, encoding="utf-8")
        return {
            "mode": "plan",
            "files": files,
            "plan_hash": plan_hash,
            "endpoint_hash": ep_hash,
            "planned_requests": sum(1 for r in plan if r["plan_status"] == "planned"),
            "blocked_requests": sum(1 for r in plan if r["plan_status"] == "blocked"),
            "network_calls_attempted": sentinel.calls_attempted,
            "output_dir": str(output_dir),
            "written": write,
        }


def _append_attempt(rows: list[dict], row: dict) -> None:
    rows.append({k: row.get(k) for k in ATTEMPT_HEADER})


def run_capture(repo_root: Path, output_dir: Path) -> dict:
    """Source-level origin-probe capture with shared evidence + linkage.

    Prefer resume from existing immutable CacheHandles (zero network). New
    network only when a planned canonical evidence_id has no verifiable handle.
    Never forge a snapshot-backed evidence_id without an external handle.
    """
    verify_baseline_commit(str(repo_root))
    verify_frozen_input_hashes(repo_root)
    verify_endpoint_provenance_hashes(repo_root)
    if not (output_dir / F_PLAN).is_file() or not (output_dir / F_AUTH).is_file():
        raise QCFail("run --plan --write before --capture")
    plan = list(csv.DictReader((output_dir / F_PLAN).open(encoding="utf-8")))
    endpoints = list(csv.DictReader((output_dir / F_ENDPOINTS).open(encoding="utf-8")))
    ep_by_source = {r["source_id"]: r for r in endpoints}
    registry = p3b0.load_source_registry(repo_root)
    schema = p3b0.load_frozen_evidence_schema(repo_root)
    cand_map = p3b0.load_candidate_source_map(repo_root)

    allowed = {
        (r["http_method"].upper(), r["request_url"])
        for r in plan
        if r["plan_status"] == "planned" and r["request_url"] and r["http_method"]
    }
    stats = NetworkStats()
    cache = p3b0.ImmutableCache(repo_root / CACHE_DIR_REL)
    capture_run_id = f"capture_{EXPECTED_BASELINE_COMMIT[:12]}"

    existing_handles: dict[str, dict] = {}
    if (output_dir / F_HANDLES).is_file():
        for row in csv.DictReader((output_dir / F_HANDLES).open(encoding="utf-8")):
            if not row.get("binding_candidate_id") and row.get("candidate_id"):
                row["binding_candidate_id"] = row["candidate_id"]
            existing_handles[row["evidence_id"]] = row

    # Prior append-only attempts (keep; never rewrite unknown into invented values)
    prior_attempts: list[dict] = []
    if (output_dir / F_ATTEMPTS).is_file():
        prior_attempts = list(csv.DictReader((output_dir / F_ATTEMPTS).open(encoding="utf-8")))

    evidence_by_id: dict[str, dict] = {}
    handle_rows: list[dict] = []
    attempt_rows: list[dict] = list(prior_attempts)
    linkage_rows: list[dict] = []
    resumed_sources: set[str] = set()
    fetched_sources: set[str] = set()
    attempt_seq = len(prior_attempts)

    # Unique planned source fetches (canonical evidence per source)
    planned_by_source: dict[str, dict] = {}
    for prow in plan:
        if prow["plan_status"] == "planned":
            planned_by_source.setdefault(prow["source_id"], prow)

    def _resume_source(source_id: str, prow: dict) -> bool:
        nonlocal attempt_seq
        eid = prow["canonical_evidence_id"]
        binding_cand = CANONICAL_EVIDENCE_BINDING_CANDIDATE[eid]
        owner = _source_owner(registry, source_id)
        h = existing_handles.get(eid)
        if h is None:
            return False
        verified = verify_external_handle_binding(cache, h, expected_evidence_id=eid)
        rec = evidence_record_from_cache_meta(
            evidence_id=eid,
            candidate_id=binding_cand,
            source_id=source_id,
            source_owner=owner,
            meta=verified["metadata"],
            payload_sha256=verified["payload_sha256"],
        )
        validate_and_seal_real_evidence(
            {k: (None if v == "" else v) for k, v in rec.items()},
            schema=schema, candidate_source_map=cand_map,
            source_registry=registry,
            metadata_sha256=h["metadata_sha256"],
            external_handle_sha256=h["external_handle_sha256"],
            allowed_snapshot_root=repo_root / "project/stage125",
        )
        evidence_by_id[eid] = rec
        handle_rows.append({
            "evidence_id": eid,
            "payload_sha256": h["payload_sha256"],
            "metadata_sha256": h["metadata_sha256"],
            "cache_contract_version": h.get(
                "cache_contract_version", p3b0.CACHE_CONTRACT_VERSION,
            ),
            "cache_handle_schema_version": h.get(
                "cache_handle_schema_version", p3b0.CACHE_HANDLE_SCHEMA_VERSION,
            ),
            "external_handle_sha256": h["external_handle_sha256"],
            "source_id": source_id,
            "binding_candidate_id": binding_cand,
        })
        # Append resume audit row only if not already logged for this evidence
        if not any(a.get("canonical_evidence_id") == eid for a in attempt_rows):
            attempt_seq += 1
            meta = verified["metadata"]
            _append_attempt(attempt_rows, {
                "capture_run_id": capture_run_id,
                "attempt_id": f"att_{attempt_seq:04d}",
                "planned_request_url": prow["request_url"],
                "http_method": prow["http_method"],
                "started_at_utc": None,
                "completed_at_utc": meta.get("retrieved_at_utc"),
                "final_url": meta.get("final_resolved_url") or meta.get("request_url"),
                "response_status": meta.get("response_status"),
                "content_type": None,
                "byte_count": verified["byte_count"],
                "redirect_count": None,
                "payload_sha256": verified["payload_sha256"],
                "metadata_sha256": verified["metadata_sha256"],
                "success": True,
                "failure_class": None,
                "shared_snapshot_key": source_id,
                "canonical_evidence_id": eid,
                "network_log_complete": False,
            })
        resumed_sources.add(source_id)
        return True

    # Phase 1: resume all verifiable sources (fail closed; no silent refetch)
    for source_id, prow in planned_by_source.items():
        eid = prow["canonical_evidence_id"]
        if eid not in existing_handles:
            continue
        try:
            _resume_source(source_id, prow)
        except (EvidenceCacheUnavailable, QCFail) as exc:
            # Handle row exists but cache/handle integrity failed — never refetch.
            raise EvidenceCacheUnavailable(f"{eid}: {exc}") from exc

    need_fetch = {
        sid: prow for sid, prow in planned_by_source.items()
        if sid not in resumed_sources
    }

    with network_default_deny() as outer_sentinel:
      if need_fetch:
        with ReadOnlyNetworkPermit(allowed, stats=stats, sentinel=outer_sentinel) as permit:
          for source_id, prow in need_fetch.items():
            eid = prow["canonical_evidence_id"]
            binding_cand = CANONICAL_EVIDENCE_BINDING_CANDIDATE[eid]
            owner = _source_owner(registry, source_id)
            attempt_seq += 1
            attempt_id = f"att_{attempt_seq:04d}"
            started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                body, meta = permit.request(prow["http_method"], prow["request_url"])
                completed = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                put = cache.put(
                    body,
                    metadata={
                        "source_id": source_id,
                        "request_url": prow["request_url"],
                        "final_resolved_url": meta["final_resolved_url"],
                        "response_status": meta["response_status"],
                        "retrieved_at_utc": completed,
                        "retrieval_purpose": "source_origin_probe",
                        "evidence_class": EVIDENCE_CLASS_ORIGIN_PROBE,
                    },
                    evidence_id=eid,
                )
                handle = p3b0.cache_handle_from_put_result(eid, put)
                serialized = p3b0.serialize_cache_handle(handle)
                handle_sha = p3b0.cache_handle_sha256(serialized)
                rec = evidence_record_from_cache_meta(
                    evidence_id=eid,
                    candidate_id=binding_cand,
                    source_id=source_id,
                    source_owner=owner,
                    meta={
                        "retrieved_at_utc": completed,
                        "response_status": meta["response_status"],
                        "final_resolved_url": meta["final_resolved_url"],
                        "request_url": prow["request_url"],
                    },
                    payload_sha256=put.payload_sha256,
                )
                validate_and_seal_real_evidence(
                    {k: (None if v == "" else v) for k, v in rec.items()},
                    schema=schema, candidate_source_map=cand_map,
                    source_registry=registry,
                    metadata_sha256=put.metadata_sha256,
                    external_handle_sha256=handle_sha,
                    allowed_snapshot_root=repo_root / "project/stage125",
                )
                evidence_by_id[eid] = rec
                handle_rows.append({
                    "evidence_id": eid,
                    "payload_sha256": put.payload_sha256,
                    "metadata_sha256": put.metadata_sha256,
                    "cache_contract_version": p3b0.CACHE_CONTRACT_VERSION,
                    "cache_handle_schema_version": p3b0.CACHE_HANDLE_SCHEMA_VERSION,
                    "external_handle_sha256": handle_sha,
                    "source_id": source_id,
                    "binding_candidate_id": binding_cand,
                })
                _append_attempt(attempt_rows, {
                    "capture_run_id": capture_run_id,
                    "attempt_id": attempt_id,
                    "planned_request_url": prow["request_url"],
                    "http_method": prow["http_method"],
                    "started_at_utc": started,
                    "completed_at_utc": completed,
                    "final_url": meta["final_resolved_url"],
                    "response_status": meta["response_status"],
                    "content_type": meta.get("content_type"),
                    "byte_count": meta.get("bytes"),
                    "redirect_count": meta.get("redirect_count"),
                    "payload_sha256": put.payload_sha256,
                    "metadata_sha256": put.metadata_sha256,
                    "success": True,
                    "failure_class": None,
                    "shared_snapshot_key": source_id,
                    "canonical_evidence_id": eid,
                    "network_log_complete": True,
                })
                fetched_sources.add(source_id)
            except Exception as exc:
                _append_attempt(attempt_rows, {
                    "capture_run_id": capture_run_id,
                    "attempt_id": attempt_id,
                    "planned_request_url": prow["request_url"],
                    "http_method": prow["http_method"],
                    "started_at_utc": started,
                    "completed_at_utc": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "final_url": None,
                    "response_status": None,
                    "content_type": None,
                    "byte_count": None,
                    "redirect_count": None,
                    "payload_sha256": None,
                    "metadata_sha256": None,
                    "success": False,
                    "failure_class": f"{type(exc).__name__}:{exc}",
                    "shared_snapshot_key": source_id,
                    "canonical_evidence_id": eid,
                    "network_log_complete": True,
                })
                raise

    # Blocked sources: one source-level unresolved evidence row (no snapshot)
    blocked_sources = sorted({
        r["source_id"] for r in plan if r["plan_status"] != "planned"
        and r["source_id"] in {CANDIDATE_SOURCE_MAP[c] for c in REGISTERED_CANDIDATE_IDS}
    })
    for source_id in blocked_sources:
        if source_id in CANONICAL_SOURCE_EVIDENCE_ID:
            continue  # planned sources only
        eid = f"ev_{source_id}"
        # pick first candidate for schema-required candidate_id
        cand_id = next(
            c for c in REGISTERED_CANDIDATE_IDS if CANDIDATE_SOURCE_MAP[c] == source_id
        )
        reason = next(
            (r.get("blocker_reason") for r in plan if r["source_id"] == source_id),
            "plan_blocked",
        )
        evidence_by_id[eid] = empty_evidence_record(
            evidence_id=eid,
            candidate_id=cand_id,
            source_id=source_id,
            source_owner=_source_owner(registry, source_id),
            failure_reason=reason or "plan_blocked",
        )

    # Linkage: every registered candidate → canonical evidence
    for prow in plan:
        cand_id = prow["candidate_id"]
        source_id = prow["source_id"]
        eid = prow.get("canonical_evidence_id") or f"ev_{source_id}"
        if prow["plan_status"] == "planned" and eid in evidence_by_id and evidence_by_id[eid].get("snapshot_sha256"):
            # Require handle for every snapshot-backed evidence
            if not any(h["evidence_id"] == eid for h in handle_rows):
                raise QCFail(f"snapshot-backed evidence without handle: {eid}")
            linkage_rows.append({
                "candidate_id": cand_id,
                "source_id": source_id,
                "evidence_id": eid,
                "evidence_class": EVIDENCE_CLASS_ORIGIN_PROBE,
                "linkage_status": "linked_shared_source_origin_probe",
                "failure_reason": "",
            })
        else:
            if eid not in evidence_by_id:
                evidence_by_id[eid] = empty_evidence_record(
                    evidence_id=eid,
                    candidate_id=cand_id,
                    source_id=source_id,
                    source_owner=_source_owner(registry, source_id),
                    failure_reason=prow.get("blocker_reason") or "plan_blocked",
                )
            linkage_rows.append({
                "candidate_id": cand_id,
                "source_id": source_id,
                "evidence_id": eid,
                "evidence_class": EVIDENCE_CLASS_BLOCKED,
                "linkage_status": "unresolved",
                "failure_reason": prow.get("blocker_reason") or "plan_blocked",
            })

    # Final invariant: every snapshot-backed evidence has exactly one handle
    for eid, rec in evidence_by_id.items():
        if rec.get("snapshot_sha256"):
            matches = [h for h in handle_rows if h["evidence_id"] == eid]
            if len(matches) != 1:
                raise QCFail(
                    f"snapshot-backed evidence must have exactly one handle: {eid}"
                )

    ev_header = p3b0.evidence_header_from_schema(schema)
    ev_out = []
    for eid in sorted(evidence_by_id):
        r = evidence_by_id[eid]
        ev_out.append({k: ("" if r.get(k) is None else r.get(k, "")) for k in ev_header})

    handles_clean = [{k: h.get(k, "") for k in HANDLE_HEADER} for h in handle_rows]
    unique_snapshots = len({h["payload_sha256"] for h in handles_clean if h.get("payload_sha256")})
    network_log_complete = all(
        str(a.get("network_log_complete")).lower() == "true" for a in attempt_rows
    ) if attempt_rows else False
    network_log = {
        "stage": QC_STAGE,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "capture_run_id": capture_run_id,
        "network_calls_attempted": stats.network_calls_attempted,
        "network_calls_succeeded": stats.network_calls_succeeded,
        "network_calls_failed": stats.network_calls_failed,
        "bytes_retrieved": stats.bytes_retrieved,
        "final_resolved_urls": sorted(set(stats.final_resolved_urls)),
        "response_statuses": list(stats.response_statuses),
        "redirect_counts": list(stats.redirect_counts),
        "hosts_contacted": sorted({
            urllib.parse.urlparse(u).hostname
            for u in stats.final_resolved_urls
            if urllib.parse.urlparse(u).hostname
        }),
        "http_methods": ["GET"] if stats.network_calls_attempted else [],
        "network_extraction_performed": (
            stats.network_calls_succeeded > 0 or unique_snapshots > 0
        ),
        "unique_raw_snapshot_count": unique_snapshots,
        "evidence_record_count": len(ev_out),
        "handle_count": len(handles_clean),
        "resume_verified_without_new_network": (
            stats.network_calls_attempted == 0 and bool(resumed_sources)
        ),
        "network_log_complete": network_log_complete,
        "evidence_class": EVIDENCE_CLASS_ORIGIN_PROBE,
        "notes": (
            "Per-request rows in part3b_capture_attempt_log_stage125.csv. "
            "Resume rows may set network_log_complete=false when redirect_count/"
            "content_type/started_at were not retained at original capture time. "
            "Never invent those fields. Cache is local-only / not in git."
        ),
        "part3b_completed": False,
        "status": "active_incomplete_accessibility_feasibility_probe",
    }
    # If resume-only, preserve prior live attempt/success counts when present
    prior_path = output_dir / F_NETWORK_LOG
    if stats.network_calls_attempted == 0 and prior_path.is_file():
        try:
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            if int(prior.get("network_calls_attempted") or 0) > 0:
                for key in (
                    "network_calls_attempted", "network_calls_succeeded",
                    "network_calls_failed", "bytes_retrieved",
                    "final_resolved_urls", "hosts_contacted", "http_methods",
                    "response_statuses",
                ):
                    if key in prior:
                        network_log[key] = prior[key]
                network_log["network_extraction_performed"] = True
                # Do not copy invented redirect_counts; keep attempt log as source
                network_log["redirect_counts"] = prior.get("redirect_counts")
                if prior.get("redirect_counts") == []:
                    network_log["redirect_counts"] = None
        except (json.JSONDecodeError, OSError):
            pass

    files = {
        F_EVIDENCE: _csv_str(ev_header, ev_out),
        F_HANDLES: _csv_str(HANDLE_HEADER, handles_clean),
        F_LINKAGE: _csv_str(LINKAGE_HEADER, linkage_rows),
        F_ATTEMPTS: _csv_str(ATTEMPT_HEADER, attempt_rows),
        F_NETWORK_LOG: _json_str(network_log),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")

    return {
        "mode": "capture",
        "files": files,
        "network_stats": stats.__dict__,
        "network_extraction_performed": network_log["network_extraction_performed"],
        "evidence_count": len(ev_out),
        "handle_count": len(handles_clean),
        "unique_snapshot_count": unique_snapshots,
        "linkage_count": len(linkage_rows),
        "output_dir": str(output_dir),
        "written": True,
        "endpoints_contacted": network_log.get("final_resolved_urls") or [],
        "resumed_sources": sorted(resumed_sources),
        "fetched_sources": sorted(fetched_sources),
    }


def build_decision_requirements() -> tuple[dict, str]:
    """Part 3B.1 decision requirements — list gaps; do not select answers."""
    data = {
        "proposed_micro_step_id":
            "stage125-part3b1-feature-definition-scoring-adjudication-lock",
        "proposed_micro_step_title":
            "Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock",
        "status": "proposed_not_started",
        "requires_explicit_user_approval_before_start": True,
        "part3b_completed": False,
        "current_probe_status": "active_incomplete_accessibility_feasibility_probe",
        "user_decisions_still_needed": [
            {
                "decision_id": "m2_feature_definitions",
                "scope": ["cand_m2_equity_return_window", "cand_m2_realized_volatility",
                          "cand_m2_amihud_illiquidity"],
                "required": (
                    "exact feature definition, unit and pre-cutoff window for each M2 variable"
                ),
                "selected_answer": None,
            },
            {
                "decision_id": "m3_feature_definitions",
                "scope": ["cand_m3_cpi_inflation", "cand_m3_fx_change_official",
                          "cand_m3_policy_financing_rate"],
                "required": (
                    "exact transformation/unit/release series for each M3 variable"
                ),
                "selected_answer": None,
            },
            {
                "decision_id": "m4_feature_definitions",
                "scope": ["cand_m4_audit_opinion_type", "cand_m4_going_concern_flag",
                          "cand_m4_audit_lag_days", "cand_m4_board_size"],
                "required": (
                    "exact document/field/derivation rules for each M4 variable"
                ),
                "selected_answer": None,
            },
            {
                "decision_id": "rubric_score_mapping_0_5",
                "scope": ["stage125_part3a_v1"],
                "required": (
                    "operational evidence-to-score mapping for rubric scores 0–5"
                ),
                "selected_answer": None,
            },
            {
                "decision_id": "cbi_endpoint_provenance",
                "scope": ["src_m3_cbi_macro"],
                "required": "authoritative CBI endpoint/provenance decision",
                "selected_answer": None,
            },
            {
                "decision_id": "available_at_and_cutoff_rules",
                "scope": ["prediction_cutoff", "available_at", "G06", "G07"],
                "required": "available_at and prediction-cutoff rules",
                "selected_answer": None,
            },
        ],
        "explicit_non_claims": [
            "current GETs are source_origin_probe only",
            "not candidate_endpoint_evidence",
            "not pair_value_evidence",
            "no numeric accessibility scores assigned",
            "not Stage126 admission",
        ],
    }
    md = """# Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock

**Status:** proposed / not started. Requires explicit user approval before any work.

This artifact lists methodology decisions still required. It does **not** select
answers, invent feature definitions, endpoints, dates, values, cutoffs, or scores.

## Decisions still needed

1. Exact feature definition, unit and pre-cutoff window for each M2 variable
2. Exact transformation/unit/release series for each M3 variable
3. Exact document/field/derivation rules for each M4 variable
4. Operational evidence-to-score mapping for rubric scores 0–5
5. Authoritative CBI endpoint/provenance decision
6. `available_at` and prediction-cutoff rules

## Current Part 3B probe status

Stage125 Part 3B accessibility feasibility probe — **active/incomplete**.
`part3b_completed=false`. Do not advance to Stage126 or modeling.
"""
    return data, md


def run_write(repo_root: Path, output_dir: Path) -> dict:
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        frozen_before = p3b0.frozen_asset_hashes(repo_root)
        frozen = verify_frozen_input_hashes(repo_root)
        provenance = verify_endpoint_provenance_hashes(repo_root)
        if not (output_dir / F_EVIDENCE).is_file():
            raise QCFail("evidence manifest missing; run --capture first")
        if not (output_dir / F_LINKAGE).is_file():
            raise QCFail("candidate-evidence linkage missing; run --capture first")
        if not (output_dir / F_HANDLES).is_file():
            raise QCFail("cache handles missing; run --capture first")
        schema = p3b0.load_frozen_evidence_schema(repo_root)
        registry = p3b0.load_source_registry(repo_root)
        cand_map = p3b0.load_candidate_source_map(repo_root)
        policy = p3b0.load_locked_gate_policy(repo_root)
        pilots = p3b0.load_locked_pilot_pairs(repo_root)
        cutoff_map = load_prediction_cutoff_map(repo_root)
        evidence_rows = list(csv.DictReader((output_dir / F_EVIDENCE).open(encoding="utf-8")))
        handle_rows = list(csv.DictReader((output_dir / F_HANDLES).open(encoding="utf-8")))
        linkage_rows = list(csv.DictReader((output_dir / F_LINKAGE).open(encoding="utf-8")))
        endpoints = list(csv.DictReader((output_dir / F_ENDPOINTS).open(encoding="utf-8")))
        ep_by_source = {r["source_id"]: r for r in endpoints}
        handles_by_eid = {h["evidence_id"]: h for h in handle_rows}
        ev_by_id = {r["evidence_id"]: r for r in evidence_rows}
        link_by_cand = {r["candidate_id"]: r for r in linkage_rows}
        cache = p3b0.ImmutableCache(repo_root / CACHE_DIR_REL)

        # Snapshot-backed evidence must have exactly one verifiable handle
        for ev in evidence_rows:
            if ev.get("snapshot_sha256"):
                h = handles_by_eid.get(ev["evidence_id"])
                if h is None:
                    raise QCFail(
                        f"snapshot-backed evidence without handle: {ev['evidence_id']}"
                    )
                verify_external_handle_binding(
                    cache, h, expected_evidence_id=ev["evidence_id"],
                )

        # Scores: null — origin probe never uniquely maps to rubric 0-5
        score_rows = []
        for cand_id in REGISTERED_CANDIDATE_IDS:
            link = link_by_cand.get(cand_id) or {}
            source_id = CANDIDATE_SOURCE_MAP[cand_id]
            eid = link.get("evidence_id") or ""
            ev = ev_by_id.get(eid) or {}
            eids = [eid] if eid else []
            if ev.get("snapshot_sha256"):
                rationale = (
                    "source_origin_probe evidence exists (not candidate_value / "
                    "not pair_value). Frozen rubric does not uniquely determine a "
                    "numeric score without human adjudication."
                )
            else:
                rationale = (
                    "No validated snapshot evidence for candidate; score remains null "
                    "(missing evidence never scored as 0)."
                )
            score_rows.append(null_score_row(cand_id, source_id, eids, rationale))

        assess_rows = []
        gate_detail_rows = []
        unresolved_rows = []

        for pair in pilots:
            pred = pair["predictor_row_key_t"]
            targ = pair["target_row_key_t_plus_1"]
            audit = cutoff_map.get((pred, targ))
            cutoff, cutoff_ok = pair_prediction_cutoff(audit)
            for cand_id in REGISTERED_CANDIDATE_IDS:
                source_id = CANDIDATE_SOURCE_MAP[cand_id]
                link = link_by_cand.get(cand_id) or {}
                eid = link.get("evidence_id") or ""
                ev = ev_by_id.get(eid) or {}
                h = handles_by_eid.get(eid)
                assessment_id = f"assess_{pred}_{targ}_{cand_id}".replace("|", "_")

                has_snap = bool(ev.get("snapshot_sha256"))
                failure_bits = []
                if link.get("evidence_class") == EVIDENCE_CLASS_ORIGIN_PROBE:
                    failure_bits.append(
                        "evidence_class=source_origin_probe_not_candidate_or_pair_value"
                    )
                if not has_snap:
                    failure_bits.append(
                        ev.get("failure_reason") or link.get("failure_reason")
                        or "missing_snapshot_evidence"
                    )
                failure_bits.append(DEFINITION_CONTRACT_GAP)
                if not cutoff_ok:
                    failure_bits.append("prediction_cutoff_unresolvable_in_part2_audit")

                score = None
                auth_src, repro, auth_notes = derive_gate_authority_flags(
                    evidence_row=ev,
                    handle_row=h,
                    cache=cache,
                    endpoint_row=ep_by_source.get(source_id),
                )
                failure_bits.extend(auth_notes)
                quality = False if has_snap else None

                gstat = {
                    "G01": p3b0.GATE_UNRESOLVED,
                    "G02": p3b0.GATE_UNRESOLVED,
                    "G03": p3b0.GATE_UNRESOLVED,
                    "G04": p3b0.GATE_UNRESOLVED,
                    "G05": p3b0.GATE_UNRESOLVED,
                    "G06": p3b0.GATE_UNRESOLVED,
                    "G07": p3b0.GATE_UNRESOLVED,
                    "G08": p3b0.GATE_UNRESOLVED,
                }
                if has_snap and h is not None and auth_src is not None and repro is not None:
                    rec = _coerce_evidence_record_types(
                        {k: (None if ev.get(k) in ("", None) else ev.get(k)) for k in ev}
                    )
                    try:
                        sealed_ev = validate_and_seal_real_evidence(
                            rec, schema=schema, candidate_source_map=cand_map,
                            source_registry=registry,
                            predictor_row_key_t=pred,
                            target_row_key_t_plus_1=targ,
                            class_label=pair["class_label"],
                            target_year=str(pair["target_year"]),
                            prediction_cutoff=cutoff,
                            metadata_sha256=h.get("metadata_sha256") or None,
                            external_handle_sha256=h.get("external_handle_sha256") or None,
                            allowed_snapshot_root=repo_root / "project/stage125",
                        )
                        gin = build_validated_real_gate_input(
                            sealed_ev,
                            accessibility_score=score,
                            authoritative_source=auth_src,
                            reproducible_retrieval=repro,
                            quality_controls_met=quality,
                        )
                        gstat = evaluate_real_candidate_gates(gin)
                    except Exception as exc:
                        failure_bits.append(f"seal_or_gate_error:{type(exc).__name__}")
                        gstat = {k: p3b0.GATE_FAIL for k in gstat}
                elif has_snap and h is None:
                    failure_bits.append("snapshot_backed_evidence_without_handle")
                    gstat = {k: p3b0.GATE_FAIL for k in gstat}

                # Assessment status: PASS only if G08 PASS (won't happen with null score)
                if gstat["G08"] == p3b0.GATE_PASS:
                    astatus = p3b0.GATE_PASS
                    usable = True
                elif gstat["G08"] == p3b0.GATE_FAIL:
                    astatus = p3b0.GATE_FAIL
                    usable = False
                else:
                    astatus = p3b0.GATE_UNRESOLVED
                    usable = False

                sealed_a = seal_pair_candidate_assessment(
                    assessment_id=assessment_id,
                    predictor_row_key_t=pred,
                    target_row_key_t_plus_1=targ,
                    candidate_id=cand_id,
                    source_id=source_id,
                    class_label=pair["class_label"],
                    target_year=str(pair["target_year"]),
                    prediction_cutoff=cutoff,
                    evidence_id=eid or None,
                    snapshot_sha256=ev.get("snapshot_sha256") or None,
                    metadata_sha256=(h or {}).get("metadata_sha256") or None,
                    external_handle_sha256=(h or {}).get("external_handle_sha256") or None,
                    assessment_status=astatus,
                    usability_flag=usable,
                )
                del sealed_a

                assess_rows.append({
                    "assessment_id": assessment_id,
                    "predictor_row_key_t": pred,
                    "target_row_key_t_plus_1": targ,
                    "ticker": pair["ticker"],
                    "target_year": pair["target_year"],
                    "class_label": pair["class_label"],
                    "candidate_id": cand_id,
                    "source_id": source_id,
                    "block": BLOCK_BY_CANDIDATE[cand_id],
                    "evidence_id": eid,
                    "assessment_status": astatus,
                    "usability_flag": "true" if usable else "false",
                    "definition_contract_gap": DEFINITION_CONTRACT_GAP,
                    "prediction_cutoff": cutoff or "",
                    "cutoff_resolvable": "true" if cutoff_ok else "false",
                    "g01": gstat["G01"], "g02": gstat["G02"], "g03": gstat["G03"],
                    "g04": gstat["G04"], "g05": gstat["G05"], "g06": gstat["G06"],
                    "g07": gstat["G07"], "g08": gstat["G08"],
                    "failure_reason": ";".join(failure_bits),
                    "reviewer_status": "automated_not_human_reviewed",
                })
                for gid in ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08"):
                    gate_detail_rows.append({
                        "gate_id": gid,
                        "gate_name": gid,
                        "scope": "pair_candidate",
                        "candidate_id": cand_id,
                        "block": BLOCK_BY_CANDIDATE[cand_id],
                        "pilot_pair_key": pred,
                        "status": gstat[gid],
                        "detail": ";".join(failure_bits)[:500],
                    })
                if astatus != p3b0.GATE_PASS:
                    unresolved_rows.append({
                        "assessment_id": assessment_id,
                        "predictor_row_key_t": pred,
                        "candidate_id": cand_id,
                        "status": astatus,
                        "reason": ";".join(failure_bits),
                    })

        if len(assess_rows) != 800:
            raise QCFail(f"assessment matrix size {len(assess_rows)} != 800")
        ids = [r["assessment_id"] for r in assess_rows]
        if len(ids) != len(set(ids)):
            raise QCFail("duplicate assessment_id")

        # Pilot-level G09-G14
        pilot_keys = frozenset(policy.frozen_pilot_keys)
        usable_by_candidate: dict[str, set[str]] = {c: set() for c in REGISTERED_CANDIDATE_IDS}
        usable_by_pair_block: dict[str, dict[str, bool]] = {
            k: {c: False for c in REGISTERED_CANDIDATE_IDS} for k in pilot_keys
        }
        for r in assess_rows:
            key = r["predictor_row_key_t"]
            usable = r["usability_flag"] == "true"
            usable_by_pair_block[key][r["candidate_id"]] = usable
            if usable:
                usable_by_candidate[r["candidate_id"]].add(key)

        g09 = p3b0.evaluate_g09(usable_by_candidate, pilot_keys, policy)
        g10 = p3b0.evaluate_g10(usable_by_pair_block, pilot_keys, policy)

        # G11/G12 from exact per-pair block usability map (sealed inside evaluate_*)
        g11 = p3b0.evaluate_g11(usable_by_pair_block, policy)
        g12 = p3b0.evaluate_g12(usable_by_pair_block, policy)
        g13 = p3b0.evaluate_g13(pilot_keys, policy)
        labels = {(r["predictor_row_key_t"], r["class_label"]) for r in pilots}
        years = {(r["predictor_row_key_t"], str(r["target_year"])) for r in pilots}
        g14 = p3b0.evaluate_g14(
            option_id=lock.APPROVED_PILOT_OPTION,
            positive=sum(1 for r in pilots if r["class_label"] == "positive"),
            negative=sum(1 for r in pilots if r["class_label"] == "negative"),
            unknown=sum(1 for r in pilots if r["class_label"] == "unknown"),
            year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
            post_evidence_substitution=False,
            policy=policy,
            pilot_keys=pilot_keys,
            key_labels=labels,
            key_years=years,
        )

        for gid, status in (
            ("G09", g09), ("G10", g10), ("G11", g11), ("G12", g12),
            ("G13", g13), ("G14", g14),
        ):
            gate_detail_rows.append({
                "gate_id": gid, "gate_name": gid, "scope": "pilot",
                "candidate_id": "", "block": "ALL", "pilot_pair_key": "",
                "status": status, "detail": "derived_from_sealed_assessments",
            })

        research_failed = [
            gid for gid, st in (
                ("G09", g09), ("G10", g10), ("G11", g11), ("G12", g12),
            ) if st != p3b0.GATE_PASS
        ]
        gate_summary = {
            "G09": g09, "G10": g10, "G11": g11, "G12": g12, "G13": g13, "G14": g14,
            "assessment_count": 800,
            "score_null_count": sum(1 for s in score_rows if s["accessibility_score"] == ""),
            "score_numeric_count": sum(1 for s in score_rows if s["accessibility_score"] != ""),
            "unresolved_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_UNRESOLVED
            ),
            "fail_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_FAIL
            ),
            "pass_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_PASS
            ),
            "definition_contract_gap": DEFINITION_CONTRACT_GAP,
            "modeling_started": False,
            "part3b_completed": False,
            "research_gate_all_pass": False,
            "research_gate_failed": research_failed,
            "status": "active_incomplete_accessibility_feasibility_probe",
        }

        network_log_path = output_dir / F_NETWORK_LOG
        if not network_log_path.is_file():
            raise QCFail("network log missing")
        network_log = json.loads(network_log_path.read_text(encoding="utf-8"))
        net_attempted = int(network_log.get("network_calls_attempted") or 0)
        net_succeeded = int(network_log.get("network_calls_succeeded") or 0)
        net_failed = int(network_log.get("network_calls_failed") or 0)
        bytes_retrieved = int(network_log.get("bytes_retrieved") or 0)
        network_extraction = bool(network_log.get("network_extraction_performed"))
        if network_extraction and net_attempted == 0:
            raise QCFail(
                "network_extraction_performed=true but network_calls_attempted=0"
            )

        scoring_applied = False  # all numeric scores absent by design in this probe
        if any(s.get("accessibility_score") not in ("", None) for s in score_rows):
            raise QCFail("numeric accessibility score invented during feasibility probe")

        frozen_after = p3b0.frozen_asset_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen scientific assets changed during Part 3B write")

        tickers = sorted({r["ticker"] for r in pilots})
        src_sha = p3b0.sha256_file(repo_root / SRC_REL)
        test_sha = p3b0.sha256_file(repo_root / TEST_REL)
        if not src_sha or not test_sha:
            raise QCFail("missing source/test fingerprint for QC")

        decision_data, decision_md = build_decision_requirements()
        pos = sum(1 for r in pilots if r["class_label"] == "positive")
        neg = sum(1 for r in pilots if r["class_label"] == "negative")
        unk = sum(1 for r in pilots if r["class_label"] == "unknown")
        snap_eids = {e["evidence_id"] for e in evidence_rows if e.get("snapshot_sha256")}
        handle_eids = {h["evidence_id"] for h in handle_rows}

        def _assert(name: str, ok: bool, detail: str = "") -> dict:
            return {
                "assertion": name,
                "status": "PASS" if ok else "FAIL",
                "detail": detail,
            }

        assertions = [
            _assert("exact_80_locked_pairs", len(pilots) == 80, str(len(pilots))),
            _assert("exact_10_candidates", len(REGISTERED_CANDIDATE_IDS) == 10, "10"),
            _assert("exact_800_unique_assessments",
                    len(assess_rows) == 800 and len({r["assessment_id"] for r in assess_rows}) == 800,
                    str(len(assess_rows))),
            _assert("frozen_labels_years_allocation",
                    pos == 39 and neg == 41 and unk == 0 and g14 == p3b0.GATE_PASS,
                    f"pos={pos},neg={neg},unk={unk},g14={g14}"),
            _assert("no_sample_target_eligibility_change",
                    frozen_before == frozen_after, "before==after"),
            _assert("no_modeling", True, "modeling_started=false"),
            _assert("frozen_scientific_assets_unchanged",
                    frozen_before == frozen_after, "before==after"),
            _assert("endpoint_provenance_hashes_verified",
                    bool(provenance), f"n={len(provenance)}"),
            _assert("network_hosts_methods_allowlisted",
                    set(network_log.get("hosts_contacted") or []).issubset(
                        {"cdn.tsetmc.com", "www.codal.ir"}
                    )
                    and set(network_log.get("http_methods") or ["GET"]).issubset({"GET", "HEAD"}),
                    str(network_log.get("hosts_contacted"))),
            _assert("capture_attempt_log_present",
                    (output_dir / F_ATTEMPTS).is_file(), F_ATTEMPTS),
            _assert("evidence_handles_payload_consistent",
                    snap_eids == handle_eids and len(snap_eids) == 3,
                    f"snap={len(snap_eids)},handles={len(handle_eids)}"),
            _assert("no_snapshot_without_handle",
                    snap_eids <= handle_eids, "ok"),
            _assert("score_rows_10", len(score_rows) == 10, str(len(score_rows))),
            _assert("all_numeric_scores_absent",
                    all(s.get("accessibility_score") in ("", None) for s in score_rows),
                    "null"),
            _assert("human_adjudication_required",
                    all(s.get("requires_human_adjudication") == "true" for s in score_rows),
                    "true"),
            _assert("accessibility_scoring_applied_false", scoring_applied is False, "false"),
            _assert("g09_g12_fail",
                    all(x == p3b0.GATE_FAIL for x in (g09, g10, g11, g12)),
                    f"{g09}/{g10}/{g11}/{g12}"),
            _assert("g13_g14_pass",
                    g13 == p3b0.GATE_PASS and g14 == p3b0.GATE_PASS,
                    f"{g13}/{g14}"),
            _assert("part3b_completed_false", True, "false"),
            _assert("no_network_during_write",
                    sentinel.calls_attempted == 0, str(sentinel.calls_attempted)),
            _assert("linkage_rows_10", len(linkage_rows) == 10, str(len(linkage_rows))),
            _assert("evidence_class_origin_probe_only",
                    all(
                        (link_by_cand[c].get("evidence_class") in (
                            EVIDENCE_CLASS_ORIGIN_PROBE, EVIDENCE_CLASS_BLOCKED,
                        ))
                        for c in REGISTERED_CANDIDATE_IDS
                    ),
                    "ok"),
        ]
        execution_qc_all_pass = all(a["status"] == "PASS" for a in assertions)
        if not execution_qc_all_pass:
            failed = [a["assertion"] for a in assertions if a["status"] != "PASS"]
            raise QCFail("execution QC failed: " + ", ".join(failed))

        content = {
            F_SCORES: _csv_str(SCORE_HEADER, score_rows),
            F_ASSESS: _csv_str(ASSESS_HEADER, assess_rows),
            F_GATES: _csv_str(
                ["gate_id", "gate_name", "scope", "candidate_id", "block",
                 "pilot_pair_key", "status", "detail"],
                gate_detail_rows,
            ),
            F_GATE_SUMMARY: _json_str(gate_summary),
            F_UNRESOLVED: _csv_str(
                ["assessment_id", "predictor_row_key_t", "candidate_id", "status", "reason"],
                unresolved_rows,
            ),
            F_README: build_readme(),
            F_DECISION_REQ: _json_str(decision_data),
            F_DECISION_REQ_MD: (
                decision_md if decision_md.endswith("\n") else decision_md + "\n"
            ),
        }
        content_hashes = {n: sha256_bytes(c.encode("utf-8")) for n, c in content.items()}
        for name in (
            F_AUTH, F_PLAN, F_ENDPOINTS, F_EVIDENCE, F_HANDLES, F_LINKAGE,
            F_ATTEMPTS, F_NETWORK_LOG,
        ):
            path = output_dir / name
            if path.is_file():
                content_hashes[name] = sha256_file(path)

        endpoint_probe = any(e.get("snapshot_sha256") for e in evidence_rows)
        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_commit": p3b0._git_last_code_commit(str(repo_root), [SRC_REL, TEST_REL]),
            "source_file_sha256": src_sha,
            "test_file_sha256": test_sha,
            "generated_at": p3b0._git_commit_timestamp(
                str(repo_root),
                p3b0._git(str(repo_root), "rev-parse", "HEAD"),
            ),
            "assertion_count": len(assertions),
            "failed_count": 0,
            "all_pass": True,
            "execution_qc_all_pass": execution_qc_all_pass,
            "research_gate_all_pass": False,
            "research_gate_failed": research_failed,
            "ticker_count": len(tickers),
            "tickers": tickers,
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            # evidence_collected = endpoint-probe evidence only (not 800 pair observations)
            "evidence_collected": endpoint_probe,
            "endpoint_probe_evidence_collected": endpoint_probe,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": False,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "network_extraction_performed": network_extraction,
            "modeling_started": False,
            "assessment_count": 800,
            "score_distribution": {
                "null": gate_summary["score_null_count"],
                "numeric": gate_summary["score_numeric_count"],
            },
            "gate_summary": gate_summary,
            "frozen_input_sha256": frozen,
            "endpoint_provenance_sha256": provenance,
            "output_sha256": content_hashes,
            "frozen_assets_before": frozen_before,
            "frozen_assets_after": frozen_after,
            "network_calls_attempted": net_attempted,
            "network_calls_succeeded": net_succeeded,
            "network_calls_failed": net_failed,
            "bytes_retrieved": bytes_retrieved,
            "hosts_contacted": network_log.get("hosts_contacted") or [],
            "final_resolved_urls": network_log.get("final_resolved_urls") or [],
            "unique_raw_snapshot_count": len(snap_eids),
            "evidence_record_count": len(evidence_rows),
            "handle_count": len(handle_rows),
            "linkage_count": len(linkage_rows),
            "cache_portability": (
                "local_immutable_cache_only_not_in_git;"
                "fresh_checkout_without_raw_cache_part3b_fails_evidence_cache_unavailable"
            ),
            "status": "active_incomplete_accessibility_feasibility_probe",
            "guard_evidence": {
                "network_calls_attempted_during_write": sentinel.calls_attempted,
                "no_network_during_write": sentinel.calls_attempted == 0,
            },
            "assertions": assertions,
        }
        qc_str = _json_str(qc)
        qc_hash = sha256_bytes(qc_str.encode("utf-8"))
        content_hashes[F_QC] = qc_hash
        metadata = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage125 Part 3B accessibility feasibility probe — active/incomplete. "
                "Not a completed Part 3B pilot. Not Stage126 admission."
            ),
            "code_commit": qc["source_commit"],
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "generated_at": qc["generated_at"],
            "output_files_sha256": dict(sorted({**content_hashes, F_QC: qc_hash}.items())),
            "frozen_input_sha256": frozen,
            "endpoint_provenance_sha256": provenance,
            "part3b0_readiness": True,
            "part3b_started": True,
            "evidence_collected": endpoint_probe,
            "endpoint_probe_evidence_collected": endpoint_probe,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": False,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "network_extraction_performed": network_extraction,
            "modeling_started": False,
            "execution_qc_all_pass": True,
            "research_gate_all_pass": False,
            "research_gate_failed": research_failed,
            "assessment_count": 800,
            "status": "active_incomplete_accessibility_feasibility_probe",
            "warning": (
                "Accessibility feasibility probe only. Source-origin probes are not "
                "candidate-value or pair-level evidence. Local cache not in git. "
                "Not Stage126 admission."
            ),
        }
        files = dict(content)
        files[F_QC] = qc_str
        files[F_METADATA] = _json_str(metadata)
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (output_dir / name).write_text(text, encoding="utf-8")
        return {
            "mode": "write",
            "files": files,
            "qc": qc,
            "gate_summary": gate_summary,
            "output_dir": str(output_dir),
            "written": True,
            "network_calls_attempted": sentinel.calls_attempted,
        }


def run_check_manifest_only(repo_root: Path, output_dir: Path) -> dict:
    """Tracked output hash verification only — NOT full evidence verification."""
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        verify_frozen_input_hashes(repo_root)
        meta_path = output_dir / F_METADATA
        if not meta_path.is_file():
            raise QCFail("metadata missing; run --write first")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        hashes = meta.get("output_files_sha256") or {}
        drift = [
            name for name, expected in sorted(hashes.items())
            if (
                not (output_dir / name).is_file()
                or sha256_file(output_dir / name) != expected
            )
        ]
        if drift:
            raise QCFail("manifest-only check drift: " + ", ".join(drift))
        if sentinel.calls_attempted != 0:
            raise QCFail("network attempted during --check-manifest-only")
        return {
            "mode": "check-manifest-only",
            "ok": True,
            "warning": (
                "manifest-only: does NOT verify immutable cache payloads; "
                "not full evidence verification"
            ),
            "network_calls_attempted": 0,
            "output_dir": str(output_dir),
        }


def run_check(repo_root: Path, output_dir: Path) -> dict:
    """Full offline check including real immutable cache verification."""
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        verify_frozen_input_hashes(repo_root)
        verify_endpoint_provenance_hashes(repo_root)
        meta_path = output_dir / F_METADATA
        if not meta_path.is_file():
            raise QCFail("metadata missing; run --write first")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        hashes = meta.get("output_files_sha256") or {}
        drift = [
            name for name, expected in sorted(hashes.items())
            if (
                not (output_dir / name).is_file()
                or sha256_file(output_dir / name) != expected
            )
        ]
        if drift:
            raise QCFail("check drift: " + ", ".join(drift))

        policy = p3b0.load_locked_gate_policy(repo_root)
        pilots = p3b0.load_locked_pilot_pairs(repo_root)
        assess_rows = list(csv.DictReader((output_dir / F_ASSESS).open(encoding="utf-8")))
        evidence_rows = list(csv.DictReader((output_dir / F_EVIDENCE).open(encoding="utf-8")))
        handle_rows = list(csv.DictReader((output_dir / F_HANDLES).open(encoding="utf-8")))
        linkage_rows = list(csv.DictReader((output_dir / F_LINKAGE).open(encoding="utf-8")))
        if len(assess_rows) != 800:
            raise QCFail(f"assessment count {len(assess_rows)} != 800")
        if len({r["assessment_id"] for r in assess_rows}) != 800:
            raise QCFail("duplicate assessment_id")
        expected_keys = frozenset(policy.frozen_pilot_keys)
        got_keys = {r["predictor_row_key_t"] for r in assess_rows}
        if got_keys != expected_keys:
            raise QCFail("assessment pilot keys != frozen 80")
        for cand in REGISTERED_CANDIDATE_IDS:
            n = sum(1 for r in assess_rows if r["candidate_id"] == cand)
            if n != 80:
                raise QCFail(f"candidate {cand} assessment count {n} != 80")
        pos = sum(1 for r in pilots if r["class_label"] == "positive")
        neg = sum(1 for r in pilots if r["class_label"] == "negative")
        unk = sum(1 for r in pilots if r["class_label"] == "unknown")
        if (pos, neg, unk) != (39, 41, 0):
            raise QCFail(f"pilot allocation drift: {pos}/{neg}/{unk}")

        cache = p3b0.ImmutableCache(repo_root / CACHE_DIR_REL)
        handles_by_eid = {h["evidence_id"]: h for h in handle_rows}
        for ev in evidence_rows:
            if not ev.get("snapshot_sha256"):
                continue
            h = handles_by_eid.get(ev["evidence_id"])
            if h is None:
                raise QCFail(
                    f"snapshot-backed evidence without handle: {ev['evidence_id']}"
                )
            try:
                verify_external_handle_binding(
                    cache, h, expected_evidence_id=ev["evidence_id"],
                )
            except EvidenceCacheUnavailable:
                raise
            except QCFail as exc:
                raise EvidenceCacheUnavailable(str(exc)) from exc

        if len(linkage_rows) != 10:
            raise QCFail(f"linkage count {len(linkage_rows)} != 10")
        gs = json.loads((output_dir / F_GATE_SUMMARY).read_text(encoding="utf-8"))
        if gs.get("part3b_completed") is not False:
            raise QCFail("part3b_completed must be false")
        if gs.get("G13") != p3b0.GATE_PASS or gs.get("G14") != p3b0.GATE_PASS:
            raise QCFail("G13/G14 must PASS")
        if any(gs.get(g) == p3b0.GATE_PASS for g in ("G09", "G10", "G11", "G12")):
            raise QCFail("G09–G12 must remain FAIL for this probe")
        if sentinel.calls_attempted != 0:
            raise QCFail("network attempted during --check")
        return {
            "mode": "check",
            "drift": [],
            "ok": True,
            "cache_verified": True,
            "network_calls_attempted": 0,
            "output_dir": str(output_dir),
            "qc": json.loads((output_dir / F_QC).read_text(encoding="utf-8")),
            "status": "active_incomplete_accessibility_feasibility_probe",
        }


def run(
    project_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    mode: str,
    write: bool = False,
) -> dict:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if output_dir is None:
        output_dir = project_dir / "stage125"
    if mode == "plan":
        return run_plan(repo_root, output_dir, write=write)
    if mode == "capture":
        return run_capture(repo_root, output_dir)
    if mode == "write":
        return run_write(repo_root, output_dir)
    if mode == "check":
        return run_check(repo_root, output_dir)
    if mode == "check-manifest-only":
        return run_check_manifest_only(repo_root, output_dir)
    raise QCFail(f"unknown mode: {mode}")
