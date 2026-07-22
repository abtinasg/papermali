"""Stage126 M1 — shared authorization transition guard.

Single fail-closed validator for the human authorization record that permits
Stage126 M1 *development-only* modeling under the frozen Part 4 / Part 5
contracts while keeping the final test locked.

Part 4, Part 5 and the Stage126 M1 implementation MUST all call this module.
No caller may treat ``authorization_text_sha256`` as trusted without
recomputing SHA-256 from the actual Persian ``authorization_text_fa``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

AUTHORIZATION_RECORD_REL = (
    "project/stage126/stage126_m1_human_authorization_record.json"
)

AUTHORIZATION_ID = "stage126_m1_financial_baseline_human_authorization_v1"
AUTHORIZING_ROLE = "human_supervisor_data_owner"
RESEARCH_ACTION_ID = "stage126-m1-financial-baseline"
AUTHORIZATION_DATE = "2026-07-19"

# Exact Persian authorization text (ZWNJ-preserving UTF-8).
AUTHORIZATION_TEXT_FA = (
    "Stage126 M1 Financial Baseline را با قرارداد قفل\u200cشده Part 4 و Part 5 "
    "مجاز می\u200cکنم؛ final test همچنان قفل بماند."
)
AUTHORIZATION_TEXT_SHA256 = (
    "eeba72fe612b292fb611729676eef0a1d7e4b0c1e5fc9d8b533d62d8dcf41a50"
)

# Exact required field contract (value must match exactly).
REQUIRED_EXACT_FIELDS: dict[str, Any] = {
    "authorization_id": AUTHORIZATION_ID,
    "authorization_date": AUTHORIZATION_DATE,
    "authorizing_role": AUTHORIZING_ROLE,
    "authorization_text_fa": AUTHORIZATION_TEXT_FA,
    "authorization_text_sha256": AUTHORIZATION_TEXT_SHA256,
    "research_action_id": RESEARCH_ACTION_ID,
    "stage126_authorized": True,
    "development_modeling_authorized": True,
    "final_test_unlocked": False,
    "final_test_access_authorized": False,
    "final_test_evaluation_authorized": False,
    "contract_change_authorized": False,
    "m2_m3_m4_authorized": False,
}

REQUIRED_FIELD_NAMES: tuple[str, ...] = tuple(REQUIRED_EXACT_FIELDS.keys())


class AuthorizationError(RuntimeError):
    """Fail-closed authorization / transition-guard violation."""


def recompute_authorization_text_sha256(text_fa: str) -> str:
    """SHA-256 of the UTF-8 bytes of the actual Persian authorization text."""
    return hashlib.sha256(text_fa.encode("utf-8")).hexdigest()


def validate_authorization_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a loaded authorization record. Fail closed on any mismatch.

    Steps (all required):
      1. every required field present with the exact approved value;
      2. ``authorization_text_fa`` byte-for-byte equals the approved text;
      3. SHA-256 recomputed from the actual UTF-8 text equals the approved SHA;
      4. JSON ``authorization_text_sha256`` equals the approved SHA (and the
         recomputed digest).

    Returns the validated record unchanged.
    """
    if not isinstance(record, dict):
        raise AuthorizationError("authorization record must be a JSON object")

    missing = [k for k in REQUIRED_FIELD_NAMES if k not in record]
    if missing:
        raise AuthorizationError(
            f"authorization record missing required fields: {missing}"
        )

    for key, expected in REQUIRED_EXACT_FIELDS.items():
        observed = record.get(key)
        if observed != expected:
            raise AuthorizationError(
                f"authorization field mismatch: {key}="
                f"{observed!r} != {expected!r}"
            )

    text_fa = record["authorization_text_fa"]
    if not isinstance(text_fa, str):
        raise AuthorizationError("authorization_text_fa must be a string")
    if text_fa != AUTHORIZATION_TEXT_FA:
        raise AuthorizationError(
            "authorization_text_fa mutated (byte-for-byte mismatch)"
        )
    # Compare as UTF-8 bytes to catch any non-canonical string equality edge.
    if text_fa.encode("utf-8") != AUTHORIZATION_TEXT_FA.encode("utf-8"):
        raise AuthorizationError(
            "authorization_text_fa UTF-8 bytes mutated"
        )

    recomputed = recompute_authorization_text_sha256(text_fa)
    if recomputed != AUTHORIZATION_TEXT_SHA256:
        raise AuthorizationError(
            f"recomputed authorization_text_fa SHA-256 mismatch: "
            f"{recomputed} != {AUTHORIZATION_TEXT_SHA256}"
        )
    field_hash = record.get("authorization_text_sha256")
    if field_hash != AUTHORIZATION_TEXT_SHA256:
        raise AuthorizationError(
            f"authorization_text_sha256 field mismatch: "
            f"{field_hash!r} != {AUTHORIZATION_TEXT_SHA256}"
        )
    if field_hash != recomputed:
        raise AuthorizationError(
            "authorization_text_sha256 field does not equal recomputed SHA-256"
        )
    return record


def load_authorization_record(repo_root: str | Path) -> dict[str, Any]:
    """Load and fully validate the on-disk authorization record. Fail closed."""
    path = Path(repo_root) / AUTHORIZATION_RECORD_REL
    if not path.is_file():
        raise AuthorizationError(
            f"missing authorization record: {AUTHORIZATION_RECORD_REL}"
        )
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError) as exc:
        raise AuthorizationError(
            f"unreadable authorization record: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise AuthorizationError(
            f"malformed authorization JSON: {exc}"
        ) from exc
    return validate_authorization_record(data)


def stage126_m1_development_authorized(repo_root: str | Path) -> bool:
    """True iff the shared exact authorization contract is present and valid.

    Fail-closed: any missing/malformed record or field mismatch yields False
    (the ``project/stage126`` surface stays forbidden for Part 4 / Part 5).
    """
    try:
        load_authorization_record(repo_root)
        return True
    except AuthorizationError:
        return False


def build_authorization_record() -> dict[str, Any]:
    """Deterministic builder for the approved authorization record."""
    digest = recompute_authorization_text_sha256(AUTHORIZATION_TEXT_FA)
    if digest != AUTHORIZATION_TEXT_SHA256:
        raise AuthorizationError(
            f"built-in authorization text hash mismatch: {digest} != "
            f"{AUTHORIZATION_TEXT_SHA256}"
        )
    return dict(REQUIRED_EXACT_FIELDS)
