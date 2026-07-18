"""Stage125 Part 3B.1E — Conservative Six-Month Availability-Lag Decision Lock.

Locks the human-supervisor-approved methodological pivot:

- researcher-verified financial dataset is frozen (no re-extraction)
- broad CODAL metadata / financial-statement capture is stopped
- availability uses a fixed conservative six-calendar-month lag
- assumed availability is methodological, never an observed PublishDateTime
- predictors from fiscal year t may only predict distress target t+1

Offline decision lock only. Zero network. No modeling. No Stage126.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import jdatetime

from src import stage125_part3b0_evidence_readiness as p3b0

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1e_conservative_six_month_lag_decision_lock"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "f1bc5eb770d883754078f15427dac45fe40a8c0b"
DECISION_VERSION = "stage125_part3b1e_v1"
MAINTENANCE_TASK_ID = (
    "stage125-part3b1e-conservative-six-month-lag-decision-lock"
)
RESEARCH_ACTION_ID = "stage125-part3b-conservative-lag-decision-lock"
RESEARCH_LAST_COMPLETED = RESEARCH_ACTION_ID
RESEARCH_NEXT = "stage125-part3c-leakage-safe-dataset-finalization"

# Closed unmerged PR #47 audit anchors (history retained; none enter main).
PR47_NUMBER = 47
PR47_BASE_OID = "f1bc5eb770d883754078f15427dac45fe40a8c0b"
PR47_HEAD_OID = "6fc1b9a3ae4f6d3e1ac678ad706f84021d8c5797"
PR47_BRANCH = "stage125-part3b1d-same-five-metadata-resolution-capture"
PR3_HEAD_OID = "2dd65bae93d2bafb0dc752b9331a75838f16742b"

APPROVED_LAG_MONTHS = 6
ASSUMED_FIELD_NAME = "assumed_available_at_conservative"
AVAILABILITY_METHOD = "fixed_conservative_lag"
AVAILABILITY_DATE_SEMANTICS = (
    "assumed_methodological_date_not_observed_publication_timestamp"
)

FORBIDDEN_OBSERVED_FIELD_NAMES = frozenset({
    "available_at",
    "PublishDateTime",
    "publish_datetime",
    "publish_date_time",
    "observed_available_at",
    "real_available_at",
    "verified_source_timestamp",
    "actual_PublishDateTime",
    "actual_CODAL_publication_date",
})

SRC_REL = "project/src/stage125_part3b1e_conservative_lag_decision.py"
TEST_REL = "project/tests/test_stage125_part3b1e_conservative_lag_decision.py"
RUN_REL = "project/run_stage125_part3b1e.py"

F_LOCK = "part3b1e_conservative_lag_decision_lock_stage125.json"
F_MANIFEST = "part3b1e_frozen_financial_data_manifest_stage125.json"
F_README = "README_STAGE125_PART3B1E_CONSERVATIVE_LAG.md"
F_QC = "stage125_part3b1e_conservative_lag_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1e.json"

CONTENT_FILES = (F_LOCK, F_MANIFEST, F_README)

PART3B1E_AUTHORIZED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    RUN_REL,
    f"project/stage125/{F_LOCK}",
    f"project/stage125/{F_MANIFEST}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

# Canonical inputs for future lag operationalization (read-only; hashed).
FROZEN_CANONICAL_INPUTS: dict[str, str] = {
    "project/stage122/modeling_all_rows_stage122.csv":
        "ece991c5ff280afa50c2ced6acfecbed4e57937cf2048cd7a11ae496a3ae7437",
    "project/stage122/modeling_one_year_ahead_stage122.csv":
        "b621491a0cbf8f73226182b42395260b43210ce84110f586c216d494e154865d",
    "project/stage122/target_definition_stage122.csv":
        "573bc1e47bef8b9e48b11acd1bf87b7fc89ea22b926b2add94da67b9f95abb98",
    "project/stage123/modeling_all_rows_stage123.csv":
        "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390",
    "project/stage123/modeling_one_year_ahead_stage123.csv":
        "e3d3063e840d61a39c3b4477aabe347050be6c829755acdcead05359fa9181ac",
    "project/stage123/eligibility_audit_stage123.csv":
        "a6a18b9894761b75a0363f93a436ba07e97bc5442ce7897719e7c921b15dfcf5",
    "project/stage124/listing_master_verified_stage124.csv":
        "968cf0cc4613aadd738d14e3cd3058e25920256c891b431d9e99776de3479fd7",
    "project/stage125/prediction_cutoff_audit_stage125_part2.csv":
        "d50e6617b011a7818d972de8e5c8a862a45f73fb07a0a22cdb5c9f59b6dc88f0",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv":
        "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5",
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv":
        "b0ded2c9c084cfc8ca882c370b6437d3949af52e00297b3f3d30f80bd315f867",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv":
        "d4515c0f3741bec7733aac97c4167a1ca730e983b0cc1627d77da7c20c8aa7e1",
}

# Financial / target / ratio surfaces that must remain byte-identical.
FINANCIAL_VALUE_PATHS = (
    "project/stage122/modeling_all_rows_stage122.csv",
    "project/stage123/modeling_all_rows_stage123.csv",
)
TARGET_PATHS = (
    "project/stage122/modeling_one_year_ahead_stage122.csv",
    "project/stage123/modeling_one_year_ahead_stage123.csv",
    "project/stage122/target_definition_stage122.csv",
)
DERIVED_RATIO_PATHS = FINANCIAL_VALUE_PATHS  # ratios live inside modeling rows

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.1E."""


class AuthorizationError(QCFail):
    """Raised when a prohibited authorization or mutation is attempted."""


# --------------------------------------------------------------------------- #
# Hashing / git helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str) -> str:
    head = _git(repo_root, "rev-parse", "HEAD")
    if not head:
        raise QCFail("unable to resolve HEAD")
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head):
        if head != EXPECTED_BASELINE_COMMIT:
            raise QCFail(
                f"baseline {EXPECTED_BASELINE_COMMIT} is not an ancestor of "
                f"HEAD {head}"
            )
    return head


def frozen_canonical_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_CANONICAL_INPUTS.items():
        digest = sha256_file(repo_root / rel)
        if digest is None:
            raise QCFail(f"missing frozen canonical input: {rel}")
        if digest != expected:
            raise QCFail(
                f"canonical input hash mismatch for {rel}: "
                f"got {digest}, expected {expected}"
            )
        out[rel] = digest
    return out


# --------------------------------------------------------------------------- #
# Lag / alignment policy (pure)
# --------------------------------------------------------------------------- #

def require_approved_lag_months(months: int) -> int:
    """Reject any lag other than the approved six calendar months."""
    if not isinstance(months, int) or isinstance(months, bool):
        raise AuthorizationError(
            f"conservative_lag_months must be int 6; got {months!r}"
        )
    if months < APPROVED_LAG_MONTHS:
        raise AuthorizationError(
            f"lag shorter than six months rejected: {months}"
        )
    if months > APPROVED_LAG_MONTHS:
        raise AuthorizationError(
            f"lag longer than approved six months rejected: {months}"
        )
    if months != APPROVED_LAG_MONTHS:
        raise AuthorizationError(
            f"lag different from approved six months rejected: {months}"
        )
    return months


def add_jalali_calendar_months(d: jdatetime.date, months: int) -> jdatetime.date:
    """Add Jalali calendar months; clamp day to last valid day of target month."""
    require_approved_lag_months(months)
    total = d.year * 12 + (d.month - 1) + months
    year = total // 12
    month = (total % 12) + 1
    for day in range(d.day, 0, -1):
        try:
            return jdatetime.date(year, month, day)
        except ValueError:
            continue
    raise QCFail(f"unable to add {months} months to {d}")


def compute_assumed_available_at_conservative(
    fiscal_year_end: jdatetime.date,
    *,
    lag_months: int = APPROVED_LAG_MONTHS,
) -> dict[str, Any]:
    """Methodological anti-leakage date: fiscal_year_end + 6 calendar months.

    Never labeled as observed PublishDateTime / CODAL publication / available_at.
    """
    require_approved_lag_months(lag_months)
    assumed = add_jalali_calendar_months(fiscal_year_end, lag_months)
    g = assumed.togregorian()
    return {
        "field_name": ASSUMED_FIELD_NAME,
        "assumed_available_at_conservative_jalali": assumed.strftime("%Y-%m-%d"),
        "assumed_available_at_conservative_gregorian": g.isoformat(),
        "availability_method": AVAILABILITY_METHOD,
        "availability_date_semantics": AVAILABILITY_DATE_SEMANTICS,
        "conservative_lag_months": lag_months,
        "is_observed_publication_timestamp": False,
        "is_PublishDateTime": False,
        "is_real_available_at": False,
    }


def reject_assumed_date_as_observed_field(
    field_name: str,
    value: Any,
) -> None:
    """Assumed methodological dates must not populate observed timestamp fields."""
    if field_name in FORBIDDEN_OBSERVED_FIELD_NAMES:
        raise AuthorizationError(
            f"assumed date cannot populate observed field {field_name!r} "
            f"(value={value!r}); use {ASSUMED_FIELD_NAME}"
        )
    if field_name == "PublishDateTime" or field_name.lower() == "publishdatetime":
        raise AuthorizationError(
            "assumed date cannot be called PublishDateTime"
        )


def validate_predictor_target_alignment(
    predictor_fiscal_year: int,
    target_fiscal_year: int,
) -> None:
    """Financial predictors from year t may only predict distress target t+1."""
    if target_fiscal_year == predictor_fiscal_year:
        raise AuthorizationError(
            "same-year t target alignment rejected "
            f"(predictor={predictor_fiscal_year}, target={target_fiscal_year})"
        )
    if target_fiscal_year != predictor_fiscal_year + 1:
        raise AuthorizationError(
            "predictor_target_alignment requires t → t+1; "
            f"got predictor={predictor_fiscal_year}, target={target_fiscal_year}"
        )


def assert_authorization_policy(lock: dict[str, Any]) -> None:
    """Fail-closed authorization surface for the approved pivot."""
    if lock.get("financial_value_reextraction_required") is not False:
        raise AuthorizationError("financial-value re-extraction is not authorized")
    if lock.get("broad_codal_capture_authorized") is not False:
        raise AuthorizationError("CODAL capture authorization rejected")
    if lock.get("row_level_publish_datetime_collection_authorized") is not False:
        raise AuthorizationError(
            "row-level PublishDateTime collection is not authorized"
        )
    if lock.get("row_level_real_available_at_assignment_authorized") is not False:
        raise AuthorizationError(
            "row-level real available_at assignment is not authorized"
        )
    if lock.get("scale_up_to_80_rows_authorized") is not False:
        raise AuthorizationError("80-row scale-up rejected")
    if lock.get("scale_up_to_130_company_source_revalidation_authorized") is not False:
        raise AuthorizationError("130-company source revalidation rejected")
    if lock.get("stage126_authorized") is not False:
        raise AuthorizationError("Stage126 authorization rejected")
    if lock.get("modeling_authorized") is not False:
        raise AuthorizationError("modeling authorization rejected")
    if lock.get("conservative_lag_months") != APPROVED_LAG_MONTHS:
        raise AuthorizationError("six_month_lag_exact failed")
    if lock.get("availability_method") != AVAILABILITY_METHOD:
        raise AuthorizationError("availability_method must be fixed_conservative_lag")


def reject_financial_value_mutation(
    repo_root: Path,
    *,
    before: dict[str, str],
    after: dict[str, str] | None = None,
) -> None:
    after = after or frozen_canonical_hashes(repo_root)
    for rel in FINANCIAL_VALUE_PATHS:
        if before.get(rel) != after.get(rel):
            raise AuthorizationError(
                f"financial-value mutation rejected for {rel}"
            )
    for rel in DERIVED_RATIO_PATHS:
        if before.get(rel) != after.get(rel):
            raise AuthorizationError(
                f"derived-ratio mutation rejected for {rel}"
            )


def reject_target_mutation(
    repo_root: Path,
    *,
    before: dict[str, str],
    after: dict[str, str] | None = None,
) -> None:
    after = after or frozen_canonical_hashes(repo_root)
    for rel in TARGET_PATHS:
        if before.get(rel) != after.get(rel):
            raise AuthorizationError(f"target mutation rejected for {rel}")


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_decision_lock(pinned: dict[str, str]) -> dict[str, Any]:
    return {
        "decision_lock_version": DECISION_VERSION,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "research_action_id": RESEARCH_ACTION_ID,
        "qc_scope": MAINTENANCE_TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "status": "conservative_six_month_availability_lag_decision_locked",
        # Locked methodology principles (exact).
        "financial_data_status": "researcher_verified_frozen",
        "financial_value_reextraction_required": False,
        "broad_codal_capture_authorized": False,
        "row_level_publish_datetime_collection_authorized": False,
        "row_level_real_available_at_assignment_authorized": False,
        "availability_method": AVAILABILITY_METHOD,
        "conservative_lag_months": APPROVED_LAG_MONTHS,
        "availability_date_semantics": AVAILABILITY_DATE_SEMANTICS,
        "assumed_availability_field_name": ASSUMED_FIELD_NAME,
        "assumed_available_at_formula": (
            "fiscal_year_end + 6 calendar months"
        ),
        "predictor_target_alignment": (
            "financial predictors from fiscal year t may only predict "
            "distress target t+1"
        ),
        "modeling_rule": (
            "a predictor observation may only be used after the six-month "
            "lag has elapsed"
        ),
        "stage126_authorized": False,
        "modeling_authorized": False,
        "scale_up_to_80_rows_authorized": False,
        "scale_up_to_130_company_source_revalidation_authorized": False,
        # Methodology status markers for Handoff / Roadmap.
        "broad_codal_capture_stopped": True,
        "financial_data_researcher_verified_frozen": True,
        "conservative_availability_lag_locked": True,
        "row_level_publish_datetime_collection_required": False,
        # Scientific interpretation.
        "scientific_interpretation": {
            "financial_values_manually_extracted_and_verified_by_researcher": True,
            "financial_values_frozen_not_revalidated_or_reextracted": True,
            "six_month_lag_purpose": "prevent_temporal_leakage_only",
            "six_month_lag_does_not_verify_accounting_value_correctness": True,
            "previous_five_row_codal_metadata_pilot_did_not_justify_expansion": True,
            "pr47_closed_unmerged_and_superseded": True,
            "no_80_row_or_130_company_codal_metadata_capture_planned": True,
        },
        "pr47_audit": {
            "number": PR47_NUMBER,
            "state_expected": "CLOSED",
            "merged_at_expected": None,
            "base_ref_oid": PR47_BASE_OID,
            "head_ref_oid": PR47_HEAD_OID,
            "branch_retained": PR47_BRANCH,
            "commits_enter_main": False,
        },
        "pr3_audit": {
            "number": 3,
            "head_ref_oid_expected": PR3_HEAD_OID,
            "must_remain_unchanged": True,
        },
        "forbidden_representations_for_assumed_date": sorted(FORBIDDEN_OBSERVED_FIELD_NAMES),
        "pinned_canonical_input_count": len(pinned),
        # Workflow markers (Stage125 incomplete; modeling/Stage126 false).
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "document_binding_resolution_decision_locked": True,
        "conservative_six_month_lag_decision_locked": True,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "stage126_started": False,
        "modeling_started": False,
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "explicit_non_claims": [
            "no_financial_value_reextraction",
            "no_broad_codal_capture",
            "no_row_level_PublishDateTime_collection",
            "no_real_available_at_assignment",
            "assumed_availability_is_not_observed_PublishDateTime",
            "no_80_row_scale_up",
            "no_130_company_source_revalidation",
            "no_stage126",
            "no_modeling",
            "stage125_not_complete",
            "merge_requires_explicit_human_approval",
        ],
    }


def build_frozen_manifest(pinned: dict[str, str]) -> dict[str, Any]:
    return {
        "manifest_version": DECISION_VERSION,
        "description": (
            "SHA-256 hashes of canonical inputs used by future conservative "
            "lag operationalization. Accounting values must not change."
        ),
        "financial_data_status": "researcher_verified_frozen",
        "financial_value_reextraction_required": False,
        "canonical_inputs_sha256": dict(sorted(pinned.items())),
        "financial_value_surfaces_sha256": {
            rel: pinned[rel] for rel in FINANCIAL_VALUE_PATHS
        },
        "derived_ratio_surfaces_sha256": {
            rel: pinned[rel] for rel in DERIVED_RATIO_PATHS
        },
        "target_surfaces_sha256": {
            rel: pinned[rel] for rel in TARGET_PATHS
        },
        "prediction_cutoff_audit_sha256": pinned[
            "project/stage125/prediction_cutoff_audit_stage125_part2.csv"
        ],
        "part3b1b_scientific_evidence_sha256": {
            "project/stage125/part3b1b_codal_document_evidence_stage125.csv":
                pinned[
                    "project/stage125/part3b1b_codal_document_evidence_stage125.csv"
                ],
            "project/stage125/part3b1b_document_binding_adjudication_stage125.csv":
                pinned[
                    "project/stage125/"
                    "part3b1b_document_binding_adjudication_stage125.csv"
                ],
        },
        "immutability_rule": (
            "before/after SHA-256 equality required; any mismatch is QC failure"
        ),
    }


def build_readme() -> str:
    return (
        "# Stage125 Part 3B.1E — Conservative Six-Month Availability-Lag "
        "Decision Lock\n\n"
        "**Status:** methodology decision lock (offline). "
        "Stage125 remains incomplete.\n\n"
        "## Approved methodology\n\n"
        "- `financial_data_status = researcher_verified_frozen`\n"
        "- `financial_value_reextraction_required = false`\n"
        "- `broad_codal_capture_authorized = false`\n"
        "- `row_level_publish_datetime_collection_authorized = false`\n"
        "- `row_level_real_available_at_assignment_authorized = false`\n"
        "- `availability_method = fixed_conservative_lag`\n"
        "- `conservative_lag_months = 6`\n"
        "- `availability_date_semantics = "
        "assumed_methodological_date_not_observed_publication_timestamp`\n"
        "- `assumed_available_at = fiscal_year_end + 6 calendar months` "
        f"(field `{ASSUMED_FIELD_NAME}` only)\n"
        "- predictors from fiscal year **t** may only predict distress "
        "target **t+1**\n"
        "- a predictor observation may only be used after the six-month lag "
        "has elapsed\n"
        "- `stage126_authorized = false`\n"
        "- `modeling_authorized = false`\n\n"
        "## Scientific interpretation\n\n"
        "The existing accounting values were manually extracted and verified "
        "by the researcher. They are frozen and are not being revalidated or "
        "re-extracted in this stage.\n\n"
        "The purpose of the six-month lag is only to prevent temporal leakage. "
        "It is not intended to verify the correctness of accounting values.\n\n"
        "The previous five-row CODAL metadata pilot did not justify expansion. "
        "PR #47 was closed unmerged and superseded by this methodology. "
        "No 80-row or 130-company CODAL metadata capture is planned.\n\n"
        "## Explicit non-claims\n\n"
        "- Assumed availability is **not** an actual `PublishDateTime`, CODAL "
        "publication date, verified source timestamp, or observed "
        "`available_at`.\n"
        "- No broad CODAL capture, financial-value extraction, or row-level "
        "publication-date assignment.\n"
        "- No Stage126 / modeling.\n\n"
        "## Research pointers\n\n"
        f"- `last_completed_research_action_id={RESEARCH_LAST_COMPLETED}`\n"
        f"- `next_research_action_id={RESEARCH_NEXT}`\n"
    )


def build_all_content(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    pinned = frozen_canonical_hashes(repo_root)
    lock = build_decision_lock(pinned)
    assert_authorization_policy(lock)
    manifest = build_frozen_manifest(pinned)
    content = {
        F_LOCK: _json_str(lock),
        F_MANIFEST: _json_str(manifest),
        F_README: build_readme(),
    }
    extras = {"lock": lock, "manifest": manifest, "pinned": pinned}
    return content, extras


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def _assert(
    assertions: list[dict[str, str]],
    name: str,
    ok: bool,
    detail: str,
) -> None:
    assertions.append({
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
    })


def build_qc_assertions(
    *,
    repo_root: Path,
    lock: dict[str, Any],
    pinned: dict[str, str],
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
    network_attempts: int,
    head: str,
) -> list[dict[str, str]]:
    assertions: list[dict[str, str]] = []

    baseline_exact = EXPECTED_BASELINE_COMMIT == PR47_BASE_OID
    _assert(
        assertions, "baseline_main_exact",
        baseline_exact and _is_ancestor(
            str(repo_root), EXPECTED_BASELINE_COMMIT, head,
        ),
        f"baseline={EXPECTED_BASELINE_COMMIT} head={head}",
    )

    pr47_not_in_main = not _is_ancestor(str(repo_root), PR47_HEAD_OID, head)
    # Also ensure main tip itself (when HEAD==baseline) lacks PR47.
    origin_main = _git(str(repo_root), "rev-parse", "origin/main") or ""
    if origin_main:
        pr47_not_in_main = pr47_not_in_main and not _is_ancestor(
            str(repo_root), PR47_HEAD_OID, origin_main,
        )
    _assert(
        assertions, "pr47_closed_unmerged",
        lock["pr47_audit"]["merged_at_expected"] is None
        and lock["pr47_audit"]["commits_enter_main"] is False,
        "PR #47 recorded closed-unmerged in decision lock",
    )
    _assert(
        assertions, "pr47_head_not_in_main",
        pr47_not_in_main,
        f"pr47_head={PR47_HEAD_OID} not ancestor of HEAD/origin/main",
    )

    _assert(
        assertions, "six_month_lag_exact",
        lock.get("conservative_lag_months") == APPROVED_LAG_MONTHS,
        str(lock.get("conservative_lag_months")),
    )
    _assert(
        assertions, "lag_semantics_assumed_not_observed",
        lock.get("availability_date_semantics") == AVAILABILITY_DATE_SEMANTICS
        and lock.get("assumed_availability_field_name") == ASSUMED_FIELD_NAME
        and ASSUMED_FIELD_NAME not in FORBIDDEN_OBSERVED_FIELD_NAMES,
        lock.get("availability_date_semantics", ""),
    )
    _assert(
        assertions, "financial_data_frozen",
        lock.get("financial_data_status") == "researcher_verified_frozen"
        and lock.get("financial_value_reextraction_required") is False,
        str(lock.get("financial_data_status")),
    )
    _assert(
        assertions, "canonical_input_hashes_recorded",
        pinned == FROZEN_CANONICAL_INPUTS and len(pinned) == len(
            FROZEN_CANONICAL_INPUTS
        ),
        f"count={len(pinned)}",
    )
    _assert(
        assertions, "financial_values_unchanged",
        all(frozen_before[p] == frozen_after[p] for p in FINANCIAL_VALUE_PATHS),
        "before/after SHA-256 equal",
    )
    _assert(
        assertions, "derived_ratios_unchanged",
        all(frozen_before[p] == frozen_after[p] for p in DERIVED_RATIO_PATHS),
        "before/after SHA-256 equal",
    )
    _assert(
        assertions, "targets_unchanged",
        all(frozen_before[p] == frozen_after[p] for p in TARGET_PATHS),
        "before/after SHA-256 equal",
    )
    _assert(
        assertions, "no_real_available_at_assignment",
        lock.get("row_level_real_available_at_assignment_authorized") is False
        and lock.get("predictor_available_at_evidence_collected") is False,
        "authorized=false; evidence=false",
    )
    _assert(
        assertions, "no_publish_datetime_assignment",
        lock.get("row_level_publish_datetime_collection_authorized") is False
        and lock.get("row_level_publish_datetime_collection_required") is False,
        "collection not authorized/required",
    )
    _assert(
        assertions, "no_codal_network_capture",
        network_attempts == 0
        and lock.get("broad_codal_capture_authorized") is False
        and lock.get("broad_codal_capture_stopped") is True,
        f"network_attempts={network_attempts}",
    )
    _assert(
        assertions, "no_80_row_scale_up",
        lock.get("scale_up_to_80_rows_authorized") is False,
        "false",
    )
    _assert(
        assertions, "no_130_company_source_revalidation",
        lock.get("scale_up_to_130_company_source_revalidation_authorized")
        is False,
        "false",
    )
    _assert(
        assertions, "t_predicts_t_plus_1",
        "t+1" in lock.get("predictor_target_alignment", ""),
        lock.get("predictor_target_alignment", ""),
    )
    _assert(
        assertions, "stage126_false",
        lock.get("stage126_authorized") is False
        and lock.get("stage126_started") is False,
        "authorized=false started=false",
    )
    _assert(
        assertions, "modeling_false",
        lock.get("modeling_authorized") is False
        and lock.get("modeling_started") is False,
        "authorized=false started=false",
    )

    pr3_ref = _git(str(repo_root), "rev-parse", "origin/stage124-iran-source-freeze")
    if not pr3_ref:
        pr3_ref = _git(
            str(repo_root), "rev-parse",
            f"refs/remotes/origin/stage124-iran-source-freeze",
        )
    pr3_ok = (not pr3_ref) or (pr3_ref == PR3_HEAD_OID)
    _assert(
        assertions, "pr3_unchanged",
        pr3_ok and lock["pr3_audit"]["head_ref_oid_expected"] == PR3_HEAD_OID,
        f"expected={PR3_HEAD_OID} observed={pr3_ref or 'ref_absent_ok'}",
    )

    # Synthetic policy probes (non-tautological: exercise pure guards).
    lag_short_rejected = False
    try:
        require_approved_lag_months(5)
    except AuthorizationError:
        lag_short_rejected = True
    _assert(assertions, "policy_lag_shorter_rejected", lag_short_rejected, "5")

    lag_long_rejected = False
    try:
        require_approved_lag_months(7)
    except AuthorizationError:
        lag_long_rejected = True
    _assert(assertions, "policy_lag_longer_rejected", lag_long_rejected, "7")

    observed_reject = False
    try:
        reject_assumed_date_as_observed_field("available_at", "1402-06-29")
    except AuthorizationError:
        observed_reject = True
    _assert(
        assertions, "policy_assumed_not_observed_available_at",
        observed_reject, "available_at",
    )

    publish_reject = False
    try:
        reject_assumed_date_as_observed_field("PublishDateTime", "1402-06-29")
    except AuthorizationError:
        publish_reject = True
    _assert(
        assertions, "policy_assumed_not_PublishDateTime",
        publish_reject, "PublishDateTime",
    )

    same_year_reject = False
    try:
        validate_predictor_target_alignment(1400, 1400)
    except AuthorizationError:
        same_year_reject = True
    _assert(assertions, "policy_same_year_rejected", same_year_reject, "1400→1400")

    t_plus_1_ok = True
    try:
        validate_predictor_target_alignment(1400, 1401)
    except AuthorizationError:
        t_plus_1_ok = False
    _assert(assertions, "policy_t_to_t_plus_1_accepted", t_plus_1_ok, "1400→1401")

    sample = compute_assumed_available_at_conservative(
        jdatetime.date(1401, 12, 29)
    )
    _assert(
        assertions, "formula_fiscal_year_end_plus_six_months",
        sample["assumed_available_at_conservative_jalali"] == "1402-06-29"
        and sample["is_PublishDateTime"] is False
        and sample["field_name"] == ASSUMED_FIELD_NAME,
        str(sample["assumed_available_at_conservative_jalali"]),
    )

    _assert(
        assertions, "frozen_canonical_hashes_unchanged",
        frozen_before == frozen_after,
        "before==after",
    )
    _assert(
        assertions, "forbidden_surfaces_absent",
        all(not (repo_root / rel).exists() for rel in FORBIDDEN_SURFACE_EXACT),
        "stage126/part3b2 absent",
    )
    return assertions


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    write: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if write and check:
        raise QCFail("write and check are mutually exclusive")

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)

    head = verify_baseline_commit(str(repo_root))
    frozen_before = frozen_canonical_hashes(repo_root)
    network_attempts = 0
    files_written: dict[str, str] = {}

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all_content(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: "
                f"{sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

        frozen_after = frozen_canonical_hashes(repo_root)
        reject_financial_value_mutation(
            repo_root, before=frozen_before, after=frozen_after,
        )
        reject_target_mutation(
            repo_root, before=frozen_before, after=frozen_after,
        )
        if frozen_before != frozen_after:
            raise QCFail("frozen canonical inputs mutated during Part 3B.1E run")

        assertions = build_qc_assertions(
            repo_root=repo_root,
            lock=extras["lock"],
            pinned=extras["pinned"],
            frozen_before=frozen_before,
            frozen_after=frozen_after,
            network_attempts=network_attempts,
            head=head,
        )
        failed = sum(1 for a in assertions if a["status"] != "PASS")
        source_commit = _git(
            str(repo_root), "log", "--format=%H", "-n", "1",
            "--", SRC_REL, TEST_REL, RUN_REL,
        )
        if not source_commit:
            raise QCFail(
                "source_commit unresolved: commit Part 3B.1E source/test/"
                "runner before regenerating QC artifacts"
            )

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8"))
            for name, text in content.items()
        }
        lock = extras["lock"]
        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "maintenance_task_id": MAINTENANCE_TASK_ID,
            "research_action_id": RESEARCH_ACTION_ID,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_commit": source_commit,
            "source_file_sha256": sha256_file(repo_root / SRC_REL),
            "test_file_sha256": sha256_file(repo_root / TEST_REL),
            "assertion_count": len(assertions),
            "failed_count": failed,
            "all_pass": failed == 0,
            "tickers": [],
            "ticker_count": 0,
            "network_requests_attempted": network_attempts,
            "part3b1e_network_requests_attempted": network_attempts,
            # Methodology markers
            "broad_codal_capture_stopped": True,
            "financial_data_researcher_verified_frozen": True,
            "conservative_availability_lag_locked": True,
            "conservative_lag_months": APPROVED_LAG_MONTHS,
            "row_level_publish_datetime_collection_required": False,
            "conservative_six_month_lag_decision_locked": True,
            # Inherited / prior markers
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            "part3b1_decision_locked": True,
            "cut_a_available_at_operationalization_locked": True,
            "predictor_document_binding_mini_pilot_completed": True,
            "predictor_document_binding_evidence_collected": True,
            "document_binding_resolution_decision_locked": True,
            "predictor_available_at_evidence_collected": False,
            "pilot_cutoff_provenance_resolved": False,
            "evidence_collected": True,
            "endpoint_probe_evidence_collected": True,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": False,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "network_extraction_performed": True,
            "modeling_started": False,
            "stage126_started": False,
            "stage126_authorized": False,
            "modeling_authorized": False,
            "scale_up_to_80_rows_authorized": False,
            "research_pointers": {
                "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
                "next_research_action_id": RESEARCH_NEXT,
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "frozen_canonical_sha256": dict(sorted(frozen_after.items())),
            "assertions": assertions,
            "decision_lock_version": DECISION_VERSION,
            "financial_data_status": lock["financial_data_status"],
            "availability_method": lock["availability_method"],
            "availability_date_semantics": lock["availability_date_semantics"],
        }
        qc["failed_count"] = sum(
            1 for a in qc["assertions"] if a["status"] != "PASS"
        )
        qc["all_pass"] = qc["failed_count"] == 0
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage125 Part 3B.1E conservative six-month availability-lag "
                "decision lock (offline methodology; financial data frozen)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "output_files_sha256": dict(
                sorted({**content_hashes, F_QC: qc_hash}.items())
            ),
            "conservative_six_month_lag_decision_locked": True,
            "broad_codal_capture_stopped": True,
            "financial_data_researcher_verified_frozen": True,
            "conservative_lag_months": APPROVED_LAG_MONTHS,
            "part3b_completed": False,
            "modeling_started": False,
            "stage126_started": False,
            "network_requests_attempted": network_attempts,
            "research_pointers": qc["research_pointers"],
        }
        meta_text = _json_str(meta)
        all_payloads = {**content, F_QC: qc_text, F_METADATA: meta_text}
        drift = (
            _compare_drift(out_dir, all_payloads)
            if out_dir.is_dir()
            else sorted(all_payloads)
        )

        if write:
            for name, text in all_payloads.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = sha256_bytes(text.encode("utf-8"))

        canonical = out_dir.resolve() == canonical_out
        if check and canonical and drift:
            raise QCFail(f"check drift: {drift}")

        if not qc["all_pass"]:
            failed_a = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed_a[:12]}")

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "network_requests_attempted": network_attempts,
        "extras": extras,
    }
