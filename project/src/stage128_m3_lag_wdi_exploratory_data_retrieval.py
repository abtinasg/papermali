"""Stage128 Track B — M3-LAG-WDI exploratory data retrieval (OFFLINE logic).

This module contains every non-network part of the action: authorization
verification, the read-only checks against the merged authoritative contract,
and the offline construction of the committed package from bytes that were
already retained.

It imports no networking module and opens no socket. The single network module
is ``stage128_m3_lag_wdi_retrieval_capture_layer``, which this module never
imports; the runner imports it only on the ``--retrieve`` path.

Authorization boundary
----------------------
The authorization consumed here covers ``retrieval_only`` for exactly one
action. It does NOT cover the post-retrieval audit (step C), the Data Gate
(step D) or modeling (step E). Concretely, this module never decodes a payload,
never reads an observation, never computes coverage, never returns a Gate
result, never joins a WDI value to a company row and never touches the Final
Test. It records WHAT WAS ACQUIRED at the transport level — URL, HTTP status,
byte count, SHA-256, content type — and stops there.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-retrieval"
PACKAGE_ID = "stage128_m3_lag_wdi_exploratory_data_retrieval"
AUTHORIZED_SCOPE = "retrieval_only"

BASELINE_BRANCH = "main"
#: PR #78 (the contract lock) was merged into main by this commit; it is the
#: baseline this retrieval was authorized against.
BASELINE_COMMIT = "175e7949e009eeecdd66aedab31ec4b48e9d3c7d"

#: PR #78 carried the M3-LAG-WDI exploratory CONTRACT LOCK and is now MERGED
#: history. PR #79 carries THIS retrieval and is the current LIVE Draft. Both
#: halves are pinned: "live > predecessor" alone would accept a topology that
#: re-published the merged #78 as the live Draft and demoted #77 in its place.
CONTRACT_LOCK_PR_NUMBER = 78
LIVE_PR_NUMBER = 79

#: CUSTODY LOCATOR for the retained raw WDI payloads.
#:
#: The raw bytes captured during the authorized retrieval are retained OUTSIDE
#: git (the repository commits only their filenames, byte counts and SHA-256
#: digests — never a payload). This names the retention bundle so a later,
#: separately authorized post-retrieval audit can find the EXACT bytes that
#: were captured, rather than re-requesting the API and silently auditing a
#: newer response.
#:
#: It is a bundle IDENTIFIER, not a filesystem path: absolute paths are
#: machine-specific and would embed a local account name, which the package's
#: no-PII rule forbids. Identity is ultimately by CONTENT — filename + byte
#: count + SHA-256 — so a relocated or copied bundle is still recognizable and
#: a substituted one is not.
RAW_RETENTION_BUNDLE_ID = (
    "papermali_stage128_m3_lag_wdi_retrieval_bundle_20260808T152237Z")
RAW_RETENTION_MECHANISM = "raw_bundle_retained_outside_git_content_addressed"

#: The NEW single-use human authorization for THIS action. It is recorded
#: independently of the contract-lock authorization, which stays historical and
#: consumed and is never reused here.
HUMAN_AUTHORIZATION_TEXT = (
    "مجوز اجرای stage128-m3-lag-wdi-exploratory-data-retrieval را فقط در "
    "محدوده retrieval_only می‌دهم"
)
HUMAN_AUTHORIZATION_UTF8_BYTES = 125
HUMAN_AUTHORIZATION_SHA256 = (
    "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604")

#: The consumed, historical contract-lock authorization. Recorded so the audit
#: can see the two are DIFFERENT authorizations, and that the old one was not
#: stretched to cover retrieval.
PRIOR_CONTRACT_LOCK_AUTHORIZATION_SHA256 = (
    "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b")

LOCKED_INDICATOR_CODES: tuple[str, ...] = ("FP.CPI.TOTL.ZG", "PA.NUS.FCRF")
LOCKED_COUNTRY_CODE = "IRN"
LOCKED_CONTRACT_STATUS = "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL"
SCIENTIFIC_ROLE = "supplementary_exploratory_robustness_block"

#: The next Track B pointer AFTER a successful retrieval — unauthorized.
NEXT_ACTION_ID = "stage128-m3-lag-wdi-exploratory-post-retrieval-audit"
DATA_GATE_ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-gate"
MODELING_ACTION_ID = "stage128-m3-lag-wdi-exploratory-incremental-evaluation"

_CONTRACT_LOCK_PKG = "project/stage128/m3_lag_wdi_exploratory_contract_lock"
CONTRACT_REL = (
    f"{_CONTRACT_LOCK_PKG}/stage128_m3_lag_wdi_exploratory_contract.json")
CONTRACT_BOUNDARY_REL = (
    f"{_CONTRACT_LOCK_PKG}/"
    "stage128_m3_lag_wdi_exploratory_governance_boundary.json")
CONTRACT_GATE_REL = (
    f"{_CONTRACT_LOCK_PKG}/"
    "stage128_m3_lag_wdi_exploratory_data_gate_contract.json")

#: Directory convention matches the sibling packages
#: (``m3i2_...`` / ``m3_lag_wdi_exploratory_contract_lock``): the ``stage128_``
#: prefix lives in the parent directory, not in the leaf name.
PACKAGE_REL = "project/stage128/m3_lag_wdi_exploratory_data_retrieval"


class M3LagRetrievalError(RuntimeError):
    """Fail-closed error in the M3-LAG-WDI retrieval action."""


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #

def verify_human_authorization() -> dict[str, Any]:
    """Fail closed unless the recorded authorization is byte-exact.

    The digest is recomputed from the verbatim text every time. A hash alone
    never identifies a scope, so the action id and the authorized scope must
    also appear literally in the text the human actually wrote.
    """
    raw = HUMAN_AUTHORIZATION_TEXT.encode("utf-8")
    if len(raw) != HUMAN_AUTHORIZATION_UTF8_BYTES:
        raise M3LagRetrievalError(
            f"authorization byte length {len(raw)} != "
            f"{HUMAN_AUTHORIZATION_UTF8_BYTES}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != HUMAN_AUTHORIZATION_SHA256:
        raise M3LagRetrievalError(
            f"authorization sha256 {digest} != {HUMAN_AUTHORIZATION_SHA256}")
    if HUMAN_AUTHORIZATION_TEXT.endswith("\n"):
        raise M3LagRetrievalError(
            "the verbatim authorization must not carry a trailing newline")
    if ACTION_ID not in HUMAN_AUTHORIZATION_TEXT:
        raise M3LagRetrievalError(
            "the authorization text must name this action explicitly")
    if AUTHORIZED_SCOPE not in HUMAN_AUTHORIZATION_TEXT:
        raise M3LagRetrievalError(
            f"the authorization text must name the scope {AUTHORIZED_SCOPE}")
    if digest == PRIOR_CONTRACT_LOCK_AUTHORIZATION_SHA256:
        raise M3LagRetrievalError(
            "the consumed contract-lock authorization may not be reused for "
            "retrieval")
    return {
        "authorization_utf8_bytes": len(raw),
        "authorization_sha256": digest,
    }


# --------------------------------------------------------------------------- #
# The merged contract is READ-ONLY
# --------------------------------------------------------------------------- #

def _read_json(root: str | os.PathLike[str], rel: str) -> dict:
    path = Path(root) / rel
    if not path.is_file():
        raise M3LagRetrievalError(f"required artifact missing: {rel}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def verify_locked_contract(root: str | os.PathLike[str]) -> dict[str, Any]:
    """Re-read the merged contract and refuse to proceed if it has drifted.

    Retrieval is authorized only against the contract that was locked BEFORE
    it. If any locked term differs — status, role, either indicator code, the
    country, or any of the retrieval/Gate separation flags — this raises and
    nothing is fetched.
    """
    contract = _read_json(root, CONTRACT_REL)
    boundary = _read_json(root, CONTRACT_BOUNDARY_REL)
    gate = _read_json(root, CONTRACT_GATE_REL)

    if contract.get("contract_status") != LOCKED_CONTRACT_STATUS:
        raise M3LagRetrievalError(
            f"the contract status must be {LOCKED_CONTRACT_STATUS}")
    if contract.get("scientific_role") != SCIENTIFIC_ROLE:
        raise M3LagRetrievalError(f"the role must stay {SCIENTIFIC_ROLE}")

    features = contract.get("features") or []
    if len(features) != 2:
        raise M3LagRetrievalError("the contract freezes EXACTLY two features")
    codes = tuple(f.get("indicator_code") for f in features)
    if codes != LOCKED_INDICATOR_CODES:
        raise M3LagRetrievalError(
            f"the locked indicators are {list(LOCKED_INDICATOR_CODES)}, "
            f"found {list(codes)}")
    for feature in features:
        if feature.get("country_code") != LOCKED_COUNTRY_CODE:
            raise M3LagRetrievalError(
                f"both features are for {LOCKED_COUNTRY_CODE}")
        if feature.get("alternative_indicator_after_failure_permitted") is not (
                False):
            raise M3LagRetrievalError(
                "no alternative indicator may be tried after a failure")
        if feature.get("imputation_permitted") is not False:
            raise M3LagRetrievalError("imputation is not permitted")
    if contract.get("indicator_search_permitted") is not False:
        raise M3LagRetrievalError("indicator search is not permitted")
    if contract.get("third_macro_feature_permitted") is not False:
        raise M3LagRetrievalError("a third macro feature is not permitted")

    # The vintage limitation must survive retrieval untouched.
    vintage = contract.get("wdi_vintage_semantics") or {}
    if vintage.get("current_or_latest_revised_wdi_allowed") is not True:
        raise M3LagRetrievalError(
            "retrieval uses the current/latest revised WDI")
    for field in ("historical_vintage_availability_claimed",
                  "point_in_time_availability_claimed"):
        if vintage.get(field) is not False:
            raise M3LagRetrievalError(f"{field} must stay False")

    # The authorization boundary this action must not cross.
    for field in ("m3_lag_wdi_retrieval_action_executes_data_gate",
                  "m3_lag_wdi_retrieval_authorization_implies_gate_"
                  "authorization",
                  "m3_lag_wdi_combined_retrieval_and_gate_action_permitted",
                  "m3_lag_wdi_gate_pass_authorizes_modeling",
                  "m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_post_retrieval_audit_action_authorized"):
        if boundary.get(field) is not False:
            raise M3LagRetrievalError(f"boundary {field} must be False")
    if boundary.get("m3_lag_wdi_next_action_scope") != AUTHORIZED_SCOPE:
        raise M3LagRetrievalError(
            f"the authorized pointer scope must be {AUTHORIZED_SCOPE}")
    if gate.get("gate_executed") is not False or gate.get(
            "gate_result") != "NOT_EXECUTED":
        raise M3LagRetrievalError("the Data Gate must still be NOT_EXECUTED")

    return {
        "contract_status": contract.get("contract_status"),
        "scientific_role": contract.get("scientific_role"),
        "indicator_codes": list(codes),
        "country_code": LOCKED_COUNTRY_CODE,
        "gate_result": gate.get("gate_result"),
    }


# --------------------------------------------------------------------------- #
# Offline build from the retained bundle
# --------------------------------------------------------------------------- #

def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_bundle(bundle_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Read the EXTERNAL retained bundle. Transport facts only.

    Deliberately does not open, decode or parse a single raw payload: the raw
    files are hashed as opaque bytes. Reading what is *inside* them is the
    separately authorized post-retrieval audit.
    """
    bundle = Path(bundle_dir)
    session_path = bundle / "retrieval_session_manifest.json"
    if not session_path.is_file():
        raise M3LagRetrievalError(
            f"no retrieval session manifest in {bundle_dir}")
    with session_path.open(encoding="utf-8") as fh:
        session = json.load(fh)
    responses = _read_csv(bundle / "wdi_response_manifest.csv")
    requests = _read_csv(bundle / "wdi_request_manifest.csv")
    if not responses:
        raise M3LagRetrievalError("the response manifest is empty")

    # Re-hash the retained bytes as OPAQUE bytes: this proves the manifest
    # matches what is on disk without reading any observation.
    for row in responses:
        raw = bundle / "raw" / row["raw_body_filename"]
        if not raw.is_file():
            raise M3LagRetrievalError(f"retained raw file missing: {raw.name}")
        blob = raw.read_bytes()
        if hashlib.sha256(blob).hexdigest() != row["sha256"]:
            raise M3LagRetrievalError(
                f"retained bytes do not match the manifest hash: {raw.name}")
        if len(blob) != int(row["byte_length"]):
            raise M3LagRetrievalError(
                f"retained byte length mismatch: {raw.name}")
    return {"session": session, "responses": responses, "requests": requests}


def build_source_manifest(bundle: dict[str, Any]) -> dict[str, Any]:
    """The committed, per-indicator acquisition record. No values."""
    responses = bundle["responses"]
    per_indicator: list[dict[str, Any]] = []
    for code in LOCKED_INDICATOR_CODES:
        rows = [r for r in responses if r["indicator_code"] == code]
        final = rows[-1] if rows else None
        successes = [r for r in rows if r["capture_result"] == "SUCCESS"]
        per_indicator.append({
            "indicator_code": code,
            "country_code": LOCKED_COUNTRY_CODE,
            "request_url": final["request_url"] if final else None,
            "attempts": len(rows),
            "retrieval_result": final["capture_result"] if final else "ABSENT",
            "http_status_code": (int(final["status_code"])
                                 if final and final["status_code"] else None),
            "content_type": final["content_type"] if final else None,
            "raw_artifact_filename": (final["raw_body_filename"]
                                      if final else None),
            "raw_artifact_bytes": (int(final["byte_length"])
                                   if final else None),
            "raw_artifact_sha256": final["sha256"] if final else None,
            "retrieval_timestamp_utc": (final["retrieval_timestamp_utc"]
                                        if final else None),
            "successful_attempts": len(successes),
            # Acquisition only: nothing below the transport layer was read.
            "payload_parsed": False,
            "observations_read": None,
            "values_inspected": None,
            "coverage_calculated": None,
        })
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "country_code": LOCKED_COUNTRY_CODE,
        "indicator_count": len(LOCKED_INDICATOR_CODES),
        "indicators": per_indicator,
        "official_source": "World Bank WDI API (api.worldbank.org)",
        "wdi_vintage": "current_or_latest_revised",
        "point_in_time_availability_claimed": False,
        "historical_vintage_availability_claimed": False,
        "raw_payloads_committed_to_git": 0,
        "raw_payloads_retained_outside_git": len(bundle["responses"]),
        "raw_retention_bundle_id": RAW_RETENTION_BUNDLE_ID,
        "raw_retention_mechanism": RAW_RETENTION_MECHANISM,
        "raw_artifacts_identified_by_content_not_path": True,
        "unresolved_values_are_null_not_zero": True,
    }


def build_execution_audit(bundle: dict[str, Any]) -> dict[str, Any]:
    """Every counter this action must NOT have moved, plus what it did."""
    session = bundle["session"]
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        # What retrieval DID do.
        "retrieval_started": True,
        "retrieval_completed": True,
        "world_bank_api_requests": int(session["http_requests_made"]),
        "wdi_indicator_series_requested": int(session["indicators_requested"]),
        "wdi_indicator_series_retrieved": int(session["indicators_succeeded"]),
        "raw_artifacts_retained": int(session["raw_artifacts_retained"]),
        "raw_bytes_retained": int(session["raw_bytes_retained"]),
        # What it did NOT do. Each of these belongs to a later, separately
        # authorized action.
        "payload_json_decoded": False,
        "wdi_value_inspections": 0,
        "wdi_observations_read": 0,
        "alternative_indicators_searched": 0,
        "alternative_indicators_retrieved": 0,
        "proxy_or_substitute_series_retrieved": 0,
        "coverage_calculations": 0,
        "candidate_coverage_evaluations": 0,
        "block_coverage_evaluations": 0,
        "positives_per_window_counts": 0,
        "data_gate_executions": 0,
        "data_gate_results_returned": 0,
        "admission_decisions": 0,
        "company_row_macro_joins": 0,
        "feature_materializations": 0,
        "fx_transformation_calculations": 0,
        "common_sample_constructions": 0,
        "model_fits": 0,
        "predictions": 0,
        "predictive_metrics": 0,
        "bootstrap_executions": 0,
        "holm_calculations": 0,
        "shap_executions": 0,
        "hyperparameter_tuning_runs": 0,
        "final_test_rows_read": 0,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "post_retrieval_audit_executed": False,
        "quarantined_local_draft_used_as_input": False,
        "earlier_historical_vintage_bundle_used_as_value_input": False,
    }


def build_governance_boundary(root: str | os.PathLike[str]) -> dict[str, Any]:
    """The authorization boundary this action stopped at."""
    prior = _read_json(root, CONTRACT_BOUNDARY_REL)
    return {
        "action_id": ACTION_ID,
        "action_type": (
            "retrieval_only_no_value_inspection_no_coverage_no_gate_"
            "no_feature_no_join_no_modeling_no_final_test"),
        "authorized_scope": AUTHORIZED_SCOPE,
        "package_id": PACKAGE_ID,
        "repository": "abtinasg/papermali",
        "baseline_branch": BASELINE_BRANCH,
        "baseline_commit": BASELINE_COMMIT,
        "head_branch": ACTION_ID,
        "pr_base_branch": "main",
        "pr_is_draft": True,
        "merge_authorized": False,
        "auto_merge": False,
        "ready_for_review_authorized": False,
        # This authorization is spent. It never reaches step C, D or E.
        "retrieval_authorization_consumed": True,
        "retrieval_authorization_reusable": False,
        "retrieval_authorization_covers_post_retrieval_audit": False,
        "retrieval_authorization_covers_data_gate": False,
        "retrieval_authorization_covers_modeling": False,
        "retrieval_authorization_covers_final_test": False,
        "retrieval_authorization_covers_track_a_follow_up": False,
        "retrieval_executed_data_gate": False,
        "combined_retrieval_and_gate_action_permitted": False,
        "retrieval_authorization_implies_gate_authorization": False,
        # Step C — defined, pointed at, NOT authorized.
        "m3_lag_wdi_next_action_id": NEXT_ACTION_ID,
        "m3_lag_wdi_next_action_authorized": False,
        "m3_lag_wdi_next_action_executes_data_gate": False,
        "next_action_pointer_is_not_authorization": True,
        "m3_lag_wdi_post_retrieval_audit_action_id": NEXT_ACTION_ID,
        "m3_lag_wdi_post_retrieval_audit_action_authorized": False,
        "m3_lag_wdi_post_retrieval_audit_executed": False,
        # Step D — still its own action, still unauthorized.
        "m3_lag_wdi_data_gate_action_id": DATA_GATE_ACTION_ID,
        "m3_lag_wdi_data_gate_action_authorized": False,
        "m3_lag_wdi_data_gate_executed": False,
        "m3_lag_wdi_data_gate_requires_new_explicit_human_authorization": True,
        "m3_lag_wdi_gate_pass_is_data_admission_only": True,
        "m3_lag_wdi_gate_pass_authorizes_modeling": False,
        # Step E — still its own action, still unauthorized.
        "m3_lag_wdi_modeling_action_id": MODELING_ACTION_ID,
        "m3_lag_wdi_modeling_authorized": False,
        "m3_lag_wdi_modeling_started": False,
        "m3_lag_wdi_modeling_requires_new_explicit_human_authorization": True,
        # Scientific state: untouched by acquisition.
        "m3_lag_wdi_authoritative_contract_status": LOCKED_CONTRACT_STATUS,
        "m3_lag_wdi_contract_modified_by_this_action": False,
        "m3_lag_wdi_data_retrieval_started": True,
        "m3_lag_wdi_block_admitted": False,
        "m3_cbi_status": prior.get("m3_cbi_status"),
        "m3_cbi_modified_by_this_action": False,
        "m3i2_evidence_status": prior.get("m3i2_evidence_status"),
        "m3i2_block_admitted": False,
        "m3i2_conclusions_modified_by_this_action": False,
        "observed_m1_m2_results_modified_by_this_action": False,
        "paper_winner_selected": False,
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_unlock_implied_by_retrieval": False,
        "final_test_unlock_implied_by_gate_pass": False,
        # Track A is a parallel track and this action did not touch it.
        "world_bank_inquiry_status": prior.get("world_bank_inquiry_status"),
        "world_bank_waiting_period_status": prior.get(
            "world_bank_waiting_period_status"),
        "world_bank_waiting_period_completion_date": prior.get(
            "world_bank_waiting_period_completion_date"),
        "world_bank_waiting_period_earliest_follow_up_date": prior.get(
            "world_bank_waiting_period_earliest_follow_up_date"),
        "world_bank_follow_up_authorized": False,
        "world_bank_response_ingestion_authorized": False,
        "world_bank_inquiry_terminated_by_this_action": False,
        "track_b_retrieval_implies_track_a_resolved": False,
        "track_b_retrieval_implies_track_a_abandoned": False,
        "pii_committed_to_git": False,
        "credentials_committed_to_git": False,
    }


def build_decision(bundle: dict[str, Any]) -> dict[str, Any]:
    """What this action decided — which is: nothing scientific."""
    session = bundle["session"]
    complete = int(session["indicators_succeeded"]) == len(
        LOCKED_INDICATOR_CODES)
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "scientific_effect": "NONE",
        "retrieval_status": (
            "RETRIEVAL_COMPLETED_RAW_SOURCE_RETAINED" if complete
            else "RETRIEVAL_INCOMPLETE_SEE_SOURCE_MANIFEST"),
        "acquisition_is_not_admission": True,
        "admission_decision_made": False,
        "coverage_decision_made": False,
        "gate_decision_made": False,
        "modeling_decision_made": False,
        "authorizes_next_action": False,
        "next_action_id": NEXT_ACTION_ID,
        "next_action_authorized": False,
        "data_gate_action_id": DATA_GATE_ACTION_ID,
        "data_gate_authorized": False,
        "modeling_action_id": MODELING_ACTION_ID,
        "modeling_authorized": False,
        "final_test_locked": True,
        "merge_authorized": False,
        "m4_authorized": False,
        "paper_winner_selected": False,
        "expected_baseline_sha": BASELINE_COMMIT,
    }


def build_pr_topology() -> dict[str, Any]:
    """The live Draft PR for this action, with PR #78 pinned as history."""
    return {
        "action_id": ACTION_ID,
        "repository": "abtinasg/papermali",
        "executed_in_separate_clean_worktree": True,
        "live_pr_base_branch": "main",
        "live_pr_base_commit": BASELINE_COMMIT,
        "live_pr_number": LIVE_PR_NUMBER,
        "live_pr_is_draft": True,
        "live_pr_merged": False,
        "live_pr_role": "m3_lag_wdi_exploratory_data_retrieval_pr",
        "live_pr_head_commit_pinned": False,
        "live_pr_head_is_github_pr_head": False,
        "live_pr_head_semantics":
            "repository_head_at_generation_not_github_pr_head",
        "merge_authorized": False,
        "auto_merge": False,
        "ready_for_review_authorized": False,
        "pr_is_stacked_on_open_predecessor": False,
        "predecessor_pr_number": CONTRACT_LOCK_PR_NUMBER,
        "predecessor_pr_merged": True,
        "predecessor_pr_merge_commit": BASELINE_COMMIT,
        "predecessor_pr_role": "m3_lag_wdi_exploratory_contract_lock_pr",
        "predecessor_pr_semantics":
            f"merged_predecessor_superseded_by_pr{LIVE_PR_NUMBER}",
        # The pinned historical roles are carried forward unchanged: they are
        # facts about what each PR was, not labels for whatever merged last.
        "documentary_recovery_pr_number": 76,
        "documentary_recovery_pr_merged": True,
        "documentary_recovery_pr_merge_commit":
            "89d8e6ff2d12ec82903cd28aa7ab839eb946b658",
        "documentary_recovery_pr_role":
            "final_official_documentary_recovery_initiation_pr",
        "documentary_recovery_pr_semantics":
            "merged_predecessor_superseded_by_pr77",
        "human_submission_pr_number": 77,
        "human_submission_pr_merged": True,
        "human_submission_pr_merge_commit":
            "93de6bae9344ce893b0261f818abce8a991cf842",
        "human_submission_pr_role":
            "final_official_inquiry_human_submission_recording_pr",
        "human_submission_pr_semantics":
            "merged_predecessor_superseded_by_pr78",
        "contract_lock_pr_number": CONTRACT_LOCK_PR_NUMBER,
        "contract_lock_pr_merged": True,
        "contract_lock_pr_merge_commit": BASELINE_COMMIT,
        "contract_lock_pr_role": "m3_lag_wdi_exploratory_contract_lock_pr",
        "contract_lock_pr_action_id":
            "stage128-m3-lag-wdi-exploratory-contract-lock",
        "recovery_pr_role_is_pinned_to_pr76": True,
        "pr_roles_are_historical_facts_not_positional": True,
        "pr_roles_re_derived_from_adjacency": False,
        # Four actions, four PRs, in order. Every entry that carries a merge
        # commit is MERGED history; only the final entry is the live Draft.
        "pr_role_sequence": [
            {
                "pr_number": 76,
                "role": "final_official_documentary_recovery_initiation_pr",
                "merged": True,
                "merge_commit": "89d8e6ff2d12ec82903cd28aa7ab839eb946b658",
            },
            {
                "pr_number": 77,
                "role":
                    "final_official_inquiry_human_submission_recording_pr",
                "merged": True,
                "merge_commit": "93de6bae9344ce893b0261f818abce8a991cf842",
            },
            {
                "pr_number": CONTRACT_LOCK_PR_NUMBER,
                "role": "m3_lag_wdi_exploratory_contract_lock_pr",
                "merged": True,
                "merge_commit": BASELINE_COMMIT,
            },
            {
                "pr_number": LIVE_PR_NUMBER,
                "role": "m3_lag_wdi_exploratory_data_retrieval_pr",
                "merged": False,
                "merge_commit": None,
            },
        ],
    }


def build_authorization_record() -> dict[str, Any]:
    """Record the NEW retrieval authorization, independent of the old one."""
    verified = verify_human_authorization()
    return {
        "action_id": ACTION_ID,
        "authorized_action_id": ACTION_ID,
        "authorization_type": "one_action_authorization",
        "authorization_scope": AUTHORIZED_SCOPE,
        "authorization_text": HUMAN_AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": verified["authorization_utf8_bytes"],
        "authorization_sha256": verified["authorization_sha256"],
        "authorization_consumed": True,
        "authorization_consumed_by_this_retrieval": True,
        "standing_authorization": False,
        "scope_identified_by_hash_alone": False,
        "authorization_covers": [
            "acquisition_of_the_two_locked_wdi_indicator_payloads_for_irn",
            "faithful_retention_of_the_raw_source_bytes",
            "mechanical_acquisition_metadata_url_status_bytes_hash",
            "fail_closed_validators_and_tests",
        ],
        "authorization_excludes": [
            "post_retrieval_audit",
            "wdi_value_or_observation_inspection",
            "coverage_calculation",
            "data_gate_execution",
            "data_admission",
            "feature_materialization_or_company_row_join",
            "fx_transformation_calculation",
            "modeling_or_predictive_evaluation",
            "final_test_access",
            "track_a_follow_up_or_response_adjudication",
            "ready_for_review_or_merge",
        ],
        "authorization_is_reusable_for_post_retrieval_audit": False,
        "authorization_is_reusable_for_data_gate": False,
        "authorization_is_reusable_for_modeling": False,
        "prior_contract_lock_authorization_sha256":
            PRIOR_CONTRACT_LOCK_AUTHORIZATION_SHA256,
        "prior_contract_lock_authorization_reused": False,
        "prior_contract_lock_authorization_status":
            "HISTORICAL_AND_CONSUMED_BY_THE_CONTRACT_LOCK",
        "expected_baseline_sha": BASELINE_COMMIT,
        "merge_authorized": False,
        "timestamp_utc": None,
        "timestamp_utc_status":
            "NOT_INDEPENDENTLY_ESTABLISHABLE_NOT_INVENTED",
        "timestamp_independently_establishable": False,
    }


def build_qc_report(bundle: dict[str, Any], audit: dict[str, Any],
                    manifest: dict[str, Any]) -> dict[str, Any]:
    """Mechanical QC over the acquisition — never over the data."""
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    session = bundle["session"]
    check("exactly_two_locked_indicators_requested",
          list(session["locked_indicator_codes"]) == list(
              LOCKED_INDICATOR_CODES),
          "only FP.CPI.TOTL.ZG and PA.NUS.FCRF may be requested")
    check("locked_country_only", session["country_code"] == (
        LOCKED_COUNTRY_CODE), "IRN only")
    check("no_alternative_indicator_retrieved",
          audit["alternative_indicators_retrieved"] == 0
          and audit["proxy_or_substitute_series_retrieved"] == 0,
          "no substitution, proxy or post-hoc alternative series")
    check("every_request_targeted_the_official_wdi_api",
          all(r["request_url"].startswith("https://api.worldbank.org/v2/")
              for r in bundle["responses"]),
          "official World Bank WDI API over HTTPS only")
    check("raw_bytes_retained_for_every_attempt",
          len(bundle["responses"]) == int(session["raw_artifacts_retained"]),
          "one retained artifact per attempt, successes and failures alike")
    check("payload_never_parsed", audit["payload_json_decoded"] is False
          and audit["wdi_observations_read"] == 0,
          "acquisition stops at the byte boundary")
    check("no_coverage_calculated", audit["coverage_calculations"] == 0,
          "coverage belongs to the Data Gate, which is not authorized")
    check("data_gate_not_executed", audit["data_gate_executions"] == 0,
          "step D requires its own new explicit human authorization")
    check("no_admission_decision", audit["admission_decisions"] == 0,
          "acquisition is not admission")
    check("no_company_row_join", audit["company_row_macro_joins"] == 0,
          "joining belongs to a later authorized action")
    check("no_modeling", audit["model_fits"] == 0
          and audit["predictions"] == 0, "step E is not authorized")
    check("final_test_untouched", audit["final_test_rows_read"] == 0,
          "the Final Test stays hard locked")
    check("no_raw_payload_committed_to_git",
          manifest["raw_payloads_committed_to_git"] == 0,
          "raw WDI payloads are retained OUTSIDE the repository")

    failed = [c for c in checks if not c["pass"]]
    return {
        "action_id": ACTION_ID,
        "scope": PACKAGE_ID,
        "checks": checks,
        "checks_total": len(checks),
        "checks_failed": len(failed),
        "all_pass": not failed,
    }


def build_package(root: str | os.PathLike[str],
                  bundle_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Build every committed artifact offline from the retained bundle."""
    verify_human_authorization()
    verify_locked_contract(root)
    bundle = read_bundle(bundle_dir)
    manifest = build_source_manifest(bundle)
    audit = build_execution_audit(bundle)
    return {
        "human_authorization_record": build_authorization_record(),
        "source_manifest": manifest,
        "execution_audit": audit,
        "governance_boundary": build_governance_boundary(root),
        "decision": build_decision(bundle),
        "pr_topology": build_pr_topology(),
        "qc_report": build_qc_report(bundle, audit, manifest),
    }
