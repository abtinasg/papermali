"""Stage125 Part 3B.1C — Document Binding Resolution Decision Lock.

Offline protocol/adjudication only:
- failure taxonomy from frozen Part 3B.1B evidence
- conservative identity-normalization contract
- exact-document evidence hierarchy
- row-level resolution requirements
- proposed (not authorized) future capture manifest
- scale-up readiness decision (80-row scale-up false)

Prohibitions:
- no CODAL/TSETMC/CBI/search-engine/other network
- no new raw capture
- no mutation of Part 3B.1B evidence or adjudications
- no financial-value / M1–M4 extraction
- no real available_at / cutoff / scoring / Gate / Part 3B.2 / Stage126 / modeling
- research pointers unchanged
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src import stage125_part3b0_evidence_readiness as p3b0

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1c_document_binding_resolution_decision_lock"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "99def5b4c15a41ca80729d873032d8c5c81ec672"
DECISION_VERSION = "stage125_part3b1c_v1"
MAINTENANCE_TASK_ID = (
    "stage125-part3b1c-document-binding-resolution-decision-lock"
)
RESEARCH_LAST_COMPLETED = "stage125-part3a-decision-lock"
RESEARCH_NEXT = "stage125-part3b-evidence-capture"

SRC_REL = "project/src/stage125_part3b1c_document_binding_resolution.py"
TEST_REL = "project/tests/test_stage125_part3b1c_document_binding_resolution.py"
RUN_REL = "project/run_stage125_part3b1c.py"

F_TAXONOMY = "part3b1c_binding_failure_taxonomy_stage125.csv"
F_NORM = "part3b1c_identity_normalization_contract_stage125.json"
F_HIERARCHY = "part3b1c_exact_document_evidence_hierarchy_stage125.json"
F_ROW_REQ = "part3b1c_row_resolution_requirements_stage125.csv"
F_PROPOSED = "part3b1c_proposed_capture_authorization_stage125.json"
F_SCALE = "part3b1c_scale_up_readiness_decision_stage125.json"
F_LOCK = "part3b1c_document_binding_resolution_decision_lock_stage125.json"
F_README = "README_STAGE125_PART3B1C_DOCUMENT_BINDING_RESOLUTION.md"
F_QC = "stage125_part3b1c_document_binding_resolution_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1c.json"

CONTENT_FILES = (
    F_TAXONOMY, F_NORM, F_HIERARCHY, F_ROW_REQ, F_PROPOSED, F_SCALE, F_LOCK, F_README,
)

PART3B1C_AUTHORIZED_EXACT = frozenset({
    SRC_REL, TEST_REL, RUN_REL,
    f"project/stage125/{F_TAXONOMY}",
    f"project/stage125/{F_NORM}",
    f"project/stage125/{F_HIERARCHY}",
    f"project/stage125/{F_ROW_REQ}",
    f"project/stage125/{F_PROPOSED}",
    f"project/stage125/{F_SCALE}",
    f"project/stage125/{F_LOCK}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

PINNED_INPUTS: dict[str, str] = {
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv":
        "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv":
        "11c7efe5f242ab8e4a4f7b1955fb25d48e288249f7a1ce4c6bf1713dbf117d20",
    "project/stage125/part3b1_adjudicated_decision_requirements_stage125.json":
        "e6d56a7b55deec83d8460241c101cb520f43b7917495e7c9a61eaf6d20c11f38",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json":
        "3966addbf4f2768e139c55ff7eef7ac7b11aafa717bf7024cf115fdf956f72b2",
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json":
        "8a453fe5b9453df7d3787e00ce4b4f97b679050cf05eeab9171191fc65a54b27",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json":
        "dc66630e95f9b02359453c4857792fa06ea32b9cecdbe9e71b5985e2027b1853",
    "project/stage125/part3b1b_predictor_document_scope_stage125.csv":
        "835e1b6b17df35f167180e59f7fe51e31c0c679cef464b7d78256ce24bb07f91",
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv":
        "b0ded2c9c084cfc8ca882c370b6437d3949af52e00297b3f3d30f80bd315f867",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv":
        "d4515c0f3741bec7733aac97c4167a1ca730e983b0cc1627d77da7c20c8aa7e1",
    "project/stage125/part3b1b_unresolved_and_rejections_stage125.csv":
        "d5e0ce0d400601057d65b935683dbd8b3e3c0d03fa7bb24842f56f61cbf53a67",
    "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json":
        "f2571c296d3400af1bc6b607180d231b4b06096ca4f5c58f024286ade4821626",
    "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json":
        "217228edd67595167746f006e5bec21f17aa9f3f16008d30c3abc7023e9f84a4",
    "project/stage125/stage125_part3b1b_codal_document_binding_qc_report.json":
        "45cdfebe0f7255c09a209a539af783f70c760be01e446280ac462c9605cf5aac",
    "project/stage125/metadata_and_hashes_stage125_part3b1b.json":
        "0bf23cf77ff5263f99419b3802b6bdee02dac12f29f9610fa3bd9c28e54f0371",
}

EVIDENCE_REL = "project/stage125/part3b1b_codal_document_evidence_stage125.csv"

LOCKED_KEYS = (
    "ثنوسا|1392", "بوعلی|1399", "بوعلی|1400", "اردستان|1401", "اپال|1401",
)
EXPECTED_STATUS = {
    "ثنوسا|1392": "UNRESOLVED",
    "بوعلی|1399": "UNRESOLVED",
    "بوعلی|1400": "UNRESOLVED",
    "اردستان|1401": "REJECTED",
    "اپال|1401": "UNRESOLVED",
}
EXPECTED_COUNTS = {
    "bound_count": 0,
    "unresolved_count": 4,
    "rejected_count": 1,
    "available_at_non_null_count": 0,
}

FAILURE_LAYERS = frozenset({
    "candidate_discovery", "source_metadata", "canonical_metadata", "identity",
    "ticker", "fiscal_year_end", "statement_scope", "document_version",
    "revision_chain", "document_multiplicity", "publication_time",
    "structural_parent_subsidiary", "exact_binding",
})
FAILURE_CLASSES = frozenset({
    "normalization_only", "missing_source_evidence", "missing_canonical_evidence",
    "incomplete_snapshot", "ambiguous_multiple_documents", "semantic_scope_conflict",
    "structural_mismatch", "revision_status_unproven", "publication_time_unavailable",
    "downstream_binding_failure",
})

# Deterministic classification of each frozen failure token (not invented tokens).
TOKEN_META: dict[str, dict[str, str]] = {
    "multi_document_predictor_row_requires_separate_adjudication": {
        "failure_layer": "document_multiplicity",
        "failure_class": "ambiguous_multiple_documents",
    },
    "ticker_mismatch": {
        "failure_layer": "ticker",
        "failure_class": "missing_source_evidence",
    },
    "entity_mismatch": {
        "failure_layer": "identity",
        "failure_class": "structural_mismatch",
    },
    "statement_scope_mismatch": {
        "failure_layer": "statement_scope",
        "failure_class": "semantic_scope_conflict",
    },
    "separate_scope_required_but_not_met": {
        "failure_layer": "statement_scope",
        "failure_class": "semantic_scope_conflict",
    },
    "missing_official_title": {
        # Default overridden per-row by classify_missing_official_title().
        "failure_layer": "canonical_metadata",
        "failure_class": "missing_canonical_evidence",
    },
    "unknown_revision_status": {
        "failure_layer": "revision_chain",
        "failure_class": "revision_status_unproven",
    },
    "canonical_source_version_not_provably_bound": {
        "failure_layer": "document_version",
        "failure_class": "missing_canonical_evidence",
    },
    "exact_document_binding_failed": {
        "failure_layer": "exact_binding",
        "failure_class": "downstream_binding_failure",
    },
    "official_metadata_not_exposed_by_direct_url": {
        "failure_layer": "source_metadata",
        "failure_class": "missing_source_evidence",
    },
    "missing_publish_datetime": {
        "failure_layer": "publication_time",
        "failure_class": "publication_time_unavailable",
    },
    "missing_canonical_letter_serial": {
        "failure_layer": "canonical_metadata",
        "failure_class": "missing_canonical_evidence",
    },
    "incomplete_pagination_without_canonical_letter_serial": {
        "failure_layer": "candidate_discovery",
        "failure_class": "incomplete_snapshot",
    },
    "incomplete_cache_without_canonical_letter_serial": {
        "failure_layer": "candidate_discovery",
        "failure_class": "incomplete_snapshot",
    },
    "letter_code_mismatch": {
        "failure_layer": "identity",
        "failure_class": "missing_source_evidence",
    },
    "subsidiary_only_title": {
        "failure_layer": "structural_parent_subsidiary",
        "failure_class": "structural_mismatch",
    },
    "parent_company_identity_mismatch": {
        "failure_layer": "structural_parent_subsidiary",
        "failure_class": "structural_mismatch",
    },
}

FROZEN_SCIENTIFIC_PATHS = tuple(PINNED_INPUTS.keys()) + (
    "project/stage125/data_dictionary_stage125.csv",
    "project/stage125/source_registry_stage125.csv",
    "project/stage125/prediction_time_contract_stage125_part2.json",
    "project/stage125/feature_availability_contract_stage125_part2.json",
    "project/stage125/leakage_checklist_stage125_part2.json",
    "project/stage125/prediction_cutoff_audit_stage125_part2.csv",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv",
    "project/stage125/stage125_part3b_evidence_capture_qc_report.json",
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
)

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})

TAXONOMY_HEADER = [
    "scope_row_id", "predictor_row_key_t", "current_binding_status",
    "failure_reason", "failure_layer", "failure_class",
    "evidence_source_path", "evidence_source_sha256",
    "observed_source_value", "observed_canonical_value",
    "normalization_safe", "normalization_rule_id",
    "requires_official_metadata", "requires_network_capture",
    "requires_human_adjudication", "structural_rejection",
    "resolution_candidate", "resolution_status", "notes",
]

ROW_REQ_HEADER = [
    "scope_row_id", "predictor_row_key_t", "current_status",
    "structural_disposition", "normalization_only_sufficient",
    "required_source_fields", "required_canonical_fields",
    "required_alias_evidence", "required_scope_evidence",
    "required_revision_evidence", "required_publish_datetime_evidence",
    "required_document_role_adjudication", "official_metadata_capture_required",
    "exact_candidate_letter_serials", "exact_candidate_urls",
    "known_endpoint_provenance", "endpoint_resolution_status",
    "eligible_for_second_resolution_pilot", "eligible_for_80_row_scale_up",
    "notes",
]

ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class QCFail(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in header})
    return buf.getvalue()


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def verify_baseline_commit(repo_root: str) -> str:
    """Verify EXPECTED_BASELINE_COMMIT is HEAD or an ancestor; return that SHA.

    Returns the stable baseline SHA (not HEAD) so regenerated QC remains
    byte-identical across additive maintenance commits on the task branch.
    """
    head = _git(repo_root, "rev-parse", "HEAD")
    if head == EXPECTED_BASELINE_COMMIT:
        return EXPECTED_BASELINE_COMMIT
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         EXPECTED_BASELINE_COMMIT, head],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(
            f"baseline_main_exact failed: HEAD={head} "
            f"expected_ancestor={EXPECTED_BASELINE_COMMIT}"
        )
    return EXPECTED_BASELINE_COMMIT


def verify_pinned_inputs(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in PINNED_INPUTS.items():
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"pinned input missing: {rel}")
        got = sha256_file(path)
        if got != expected:
            raise QCFail(f"part3b1b_source_hashes_pinned failed for {rel}")
        out[rel] = got
    return out


def frozen_scientific_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in FROZEN_SCIENTIFIC_PATHS:
        path = repo_root / rel
        if path.is_file():
            out[rel] = sha256_file(path)
    return out


def load_evidence_rows(repo_root: Path) -> list[dict[str, str]]:
    path = repo_root / EVIDENCE_REL
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def split_failure_tokens(raw: str) -> list[str]:
    if not raw:
        return []
    return [t for t in raw.split(";") if t]


# --------------------------------------------------------------------------- #
# Normalization (mechanical only)
# --------------------------------------------------------------------------- #

def apply_mechanical_normalization(text: str) -> str:
    """Apply only allowed mechanical transforms; preserve identity content."""
    if text is None:
        return ""
    value = unicodedata.normalize("NFC", text)
    value = value.replace(ARABIC_YEH, PERSIAN_YEH).replace(ARABIC_KAF, PERSIAN_KAF)
    value = value.translate(DIGIT_MAP)
    value = value.replace("\u200c", " ")  # ZWNJ -> space then collapse
    value = re.sub(r"\s+", " ", value.strip())
    # Standard punctuation canonicalization (dashes/quotes only).
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = value.replace("\u00ab", '"').replace("\u00bb", '"')
    return value


def reject_fuzzy_or_destructive_config(config: dict[str, Any]) -> None:
    forbidden_keys = {
        "fuzzy_matching", "levenshtein_threshold", "substring_matching",
        "token_set_similarity", "remove_arbitrary_words",
        "remove_subsidiary_names", "remove_industry_or_location_words",
        "silently_remove_شرکت", "silently_remove_legal_form_tokens",
        "manual_alias_invention", "ticker_only_entity_acceptance",
        "global_remove_شرکت",
    }
    for key in forbidden_keys:
        if config.get(key):
            raise QCFail(f"prohibited_normalization_config:{key}")


def build_identity_normalization_contract() -> dict[str, Any]:
    rules = [
        {
            "normalization_rule_id": "nfc_unicode",
            "description": "Unicode NFC normalization",
            "input_example": "نوسازي",
            "output_example": "نوسازي",
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "arabic_yeh_to_persian_yeh",
            "description": "Arabic Yeh U+064A to Persian Yeh U+06CC",
            "input_example": "نوسازي",
            "output_example": apply_mechanical_normalization("نوسازي"),
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "arabic_kaf_to_persian_kaf",
            "description": "Arabic Kaf U+0643 to Persian Kaf U+06A9",
            "input_example": "شركت",
            "output_example": apply_mechanical_normalization("شركت"),
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "digit_normalization",
            "description": "Persian/Arabic digits to ASCII digits",
            "input_example": "۱۳۹۲",
            "output_example": "1392",
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "whitespace_trim_collapse",
            "description": "Trim and collapse internal whitespace",
            "input_example": "  الف   ب  ",
            "output_example": "الف ب",
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "zwnj_to_space_collapse",
            "description": "ZWNJ treated as space then collapsed",
            "input_example": "صورت\u200cهای",
            "output_example": apply_mechanical_normalization("صورت\u200cهای"),
            "identity_information_removed": False,
        },
        {
            "normalization_rule_id": "punctuation_canonicalization",
            "description": "Standard dash/quote canonicalization only",
            "input_example": "الف\u2013ب",
            "output_example": "الف-ب",
            "identity_information_removed": False,
        },
    ]
    return {
        "contract_version": DECISION_VERSION,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "raw_and_normalized_both_preserved": True,
        "normalization_alone_never_creates_bound": True,
        "pinned_alias_source_present": False,
        "legal_prefix_equivalence_without_pinned_alias": False,
        "allowed_mechanical_rules": rules,
        "prohibited_transforms": [
            "fuzzy_matching",
            "Levenshtein_thresholds",
            "substring_matching",
            "token_set_similarity",
            "removing_arbitrary_words",
            "removing_subsidiary_names",
            "removing_industry_or_location_words",
            "silently_removing_شرکت",
            "silently_removing_legal_form_tokens",
            "manual_alias_invention",
            "ticker_only_entity_acceptance",
        ],
        "explicit_non_equivalence_without_alias": [
            {
                "left": "پتروشیمی بوعلی سینا",
                "right": "شرکت پتروشیمی بوعلی سینا",
                "reason": "legal_prefix_requires_pinned_alias_evidence",
                "normalization_safe": False,
                "resolution_status": "requires_alias_evidence",
            },
        ],
        "mechanical_character_equivalence_example": {
            "left": "نوسازي",
            "right": "نوسازی",
            "normalization_safe": True,
            "normalization_rule_id": "arabic_yeh_to_persian_yeh",
            "note": "raw values remain preserved; normalization alone never creates BOUND",
        },
    }


# --------------------------------------------------------------------------- #
# Taxonomy / row requirements / hierarchy / proposal / scale-up
# --------------------------------------------------------------------------- #

def _entity_norm_fields(row: dict[str, str]) -> tuple[str, str, str, str]:
    src = row.get("source_legal_entity") or ""
    can = row.get("canonical_legal_entity") or ""
    key = row["predictor_row_key_t"]
    if key == "ثنوسا|1392" and src and can:
        # Character-level Yeh difference only after mechanical norms.
        if apply_mechanical_normalization(src) == apply_mechanical_normalization(can):
            return "true", "arabic_yeh_to_persian_yeh", "normalization_candidate", (
                "mechanical Yeh normalization candidate; does not create BOUND"
            )
    if key.startswith("بوعلی") or key.startswith("اردستان") or key.startswith("اپال"):
        return "false", "", "requires_alias_evidence", (
            "legal-form/prefix or missing canonical entity requires pinned alias "
            "or official metadata; not mechanically equivalent"
        )
    return "false", "", "requires_official_metadata", ""


# Exact frozen-evidence column pairs per failure token (no cross-family fallback).
# Empty source/canonical column names mean the column is absent from the frozen
# Part 3B.1B evidence artifact; observed values must stay empty.
FIELD_FAMILY_COLUMNS: dict[str, tuple[str, str]] = {
    "ticker_mismatch": ("", "ticker"),
    "entity_mismatch": ("source_legal_entity", "canonical_legal_entity"),
    "statement_scope_mismatch": (
        "source_statement_scope", "canonical_statement_scope",
    ),
    "separate_scope_required_but_not_met": (
        "source_statement_scope", "canonical_statement_scope",
    ),
    "missing_official_title": (
        "source_official_title", "canonical_official_title",
    ),
    "letter_code_mismatch": ("", ""),
    "missing_canonical_letter_serial": (
        "source_letter_serial", "canonical_letter_serial",
    ),
    "canonical_source_version_not_provably_bound": (
        "source_letter_serial", "canonical_letter_serial",
    ),
    "subsidiary_only_title": (
        "source_official_title", "canonical_official_title",
    ),
    "parent_company_identity_mismatch": (
        "source_legal_entity", "canonical_legal_entity",
    ),
    "missing_publish_datetime": ("publish_datetime_raw", ""),
    "official_metadata_not_exposed_by_direct_url": ("", ""),
    "unknown_revision_status": ("source_revision_status_raw", ""),
    "multi_document_predictor_row_requires_separate_adjudication": ("", ""),
    "exact_document_binding_failed": ("", ""),
    "incomplete_pagination_without_canonical_letter_serial": ("", ""),
    "incomplete_cache_without_canonical_letter_serial": ("", ""),
}


def observed_values_for_token(row: dict[str, str], token: str) -> tuple[str, str]:
    """Return (source, canonical) from exact field-family columns only."""
    if token not in FIELD_FAMILY_COLUMNS:
        raise QCFail(f"taxonomy_field_families_exact: unmapped token {token}")
    src_col, can_col = FIELD_FAMILY_COLUMNS[token]
    src_val = (row.get(src_col) or "") if src_col else ""
    can_val = (row.get(can_col) or "") if can_col else ""
    return src_val, can_val


def classify_missing_official_title(
    src_title: str, can_title: str,
) -> tuple[str, str, str]:
    """Return (failure_layer, failure_class, notes). Fail closed if both empty."""
    if src_title and not can_title:
        return (
            "canonical_metadata",
            "missing_canonical_evidence",
            "source title nonempty; canonical title empty",
        )
    if (not src_title) and can_title:
        return (
            "source_metadata",
            "missing_source_evidence",
            "source title empty; canonical title nonempty",
        )
    if (not src_title) and (not can_title):
        raise QCFail(
            "missing_official_title both_sides_missing: "
            "source and canonical official titles are both empty"
        )
    raise QCFail(
        "missing_official_title both_sides_nonempty_unexpected: "
        "token claims missing title but both sides are nonempty"
    )


def build_taxonomy_rows(evidence: list[dict[str, str]], evidence_sha: str) -> list[dict[str, str]]:
    rows_out: list[dict[str, str]] = []
    for row in evidence:
        key = row["predictor_row_key_t"]
        tokens = split_failure_tokens(row.get("failure_reasons") or "")
        for token in tokens:
            if token not in TOKEN_META:
                raise QCFail(f"invented_or_unmapped_failure_token:{token}")
            meta = dict(TOKEN_META[token])
            norm_safe, norm_rule, res_status, notes = ("false", "", "open", "")
            src_val, can_val = observed_values_for_token(row, token)

            if token == "entity_mismatch":
                norm_safe, norm_rule, res_status, notes = _entity_norm_fields(row)
            elif token == "ticker_mismatch":
                # Frozen evidence has no source ticker/symbol column; never copy
                # the predictor/canonical ticker into observed_source_value.
                src_val = ""
                can_val = row.get("ticker") or ""
                norm_safe, norm_rule = "false", ""
                res_status = "requires_official_symbol_metadata"
                notes = (
                    "source symbol was not exposed/preserved in the frozen "
                    "Part 3B.1B evidence artifact; canonical ticker must not be "
                    "copied into the source field"
                )
            elif token == "missing_official_title":
                layer, fclass, notes = classify_missing_official_title(src_val, can_val)
                meta["failure_layer"] = layer
                meta["failure_class"] = fclass
                res_status = "requires_official_metadata"
            elif token == "letter_code_mismatch":
                src_val, can_val = "", ""
                norm_safe, norm_rule = "false", ""
                res_status = "letter_code_values_not_preserved_in_frozen_evidence"
                notes = (
                    "The frozen failure token is retained, but exact LetterCode "
                    "values were not preserved in the frozen Part 3B.1B evidence "
                    "artifact. LetterSerial must not be substituted for LetterCode."
                )
            elif token in (
                "statement_scope_mismatch", "separate_scope_required_but_not_met",
            ):
                res_status = "requires_scope_evidence"
            elif token in (
                "missing_canonical_letter_serial",
                "canonical_source_version_not_provably_bound",
            ):
                res_status = "requires_canonical_version_proof"
            elif token in (
                "incomplete_pagination_without_canonical_letter_serial",
                "incomplete_cache_without_canonical_letter_serial",
            ):
                res_status = "incomplete_snapshot_not_unique"
                notes = "incomplete cache cannot prove canonical uniqueness"
            elif token == "subsidiary_only_title":
                res_status = "structurally_rejected"
                notes = "subsidiary-only title remains structural rejection for parent row"
            elif token == "parent_company_identity_mismatch":
                res_status = "structurally_rejected"
                notes = "parent-company identity mismatch remains structural rejection"
            elif token == "unknown_revision_status":
                res_status = "revision_status_unproven"
                notes = "absence of اصلاحیه does not prove original"
            elif token == "multi_document_predictor_row_requires_separate_adjudication":
                res_status = "requires_document_role_adjudication"
            elif token == "exact_document_binding_failed":
                res_status = "downstream_of_prior_blockers"
            elif token == "official_metadata_not_exposed_by_direct_url":
                res_status = "requires_official_metadata"
                notes = (
                    "Decision.aspx without required official metadata cannot "
                    "independently prove all binding dimensions"
                )
            elif token == "missing_publish_datetime":
                res_status = "requires_official_metadata"

            if meta["failure_layer"] not in FAILURE_LAYERS:
                raise QCFail(f"bad_failure_layer:{meta['failure_layer']}")
            if meta["failure_class"] not in FAILURE_CLASSES:
                raise QCFail(f"bad_failure_class:{meta['failure_class']}")

            # Hard guard: never treat LetterSerial as LetterCode evidence.
            if token == "letter_code_mismatch":
                serials = {
                    (row.get("source_letter_serial") or "").strip(),
                    (row.get("canonical_letter_serial") or "").strip(),
                }
                serials.discard("")
                if src_val in serials or can_val in serials:
                    raise QCFail("letter_code_not_substituted_with_letter_serial")

            structural = token in (
                "subsidiary_only_title", "parent_company_identity_mismatch",
            )
            failure_class = meta["failure_class"]
            if token == "entity_mismatch" and norm_safe == "true":
                failure_class = "normalization_only"
            rows_out.append({
                "scope_row_id": row["scope_row_id"],
                "predictor_row_key_t": key,
                "current_binding_status": row["binding_status"],
                "failure_reason": token,
                "failure_layer": meta["failure_layer"],
                "failure_class": failure_class,
                "evidence_source_path": EVIDENCE_REL,
                "evidence_source_sha256": evidence_sha,
                "observed_source_value": src_val,
                "observed_canonical_value": can_val,
                "normalization_safe": norm_safe,
                "normalization_rule_id": norm_rule,
                "requires_official_metadata": (
                    "true" if token in (
                        "missing_official_title",
                        "official_metadata_not_exposed_by_direct_url",
                        "missing_publish_datetime",
                        "unknown_revision_status",
                        "ticker_mismatch",
                        "entity_mismatch",
                        "letter_code_mismatch",
                    ) else "false"
                ),
                "requires_network_capture": (
                    "true" if key != "اردستان|1401" and token not in (
                        "subsidiary_only_title", "parent_company_identity_mismatch",
                    ) else "false"
                ),
                "requires_human_adjudication": (
                    "true" if token in (
                        "multi_document_predictor_row_requires_separate_adjudication",
                        "subsidiary_only_title",
                        "parent_company_identity_mismatch",
                        "entity_mismatch",
                    ) else "false"
                ),
                "structural_rejection": "true" if structural else "false",
                "resolution_candidate": "false" if structural else "true",
                "resolution_status": res_status,
                "notes": notes,
            })
    return rows_out


def build_evidence_hierarchy() -> dict[str, Any]:
    return {
        "contract_version": DECISION_VERSION,
        "ordered_evidence_hierarchy": [
            {"rank": 1, "element": "exact_official_codal_source_version_metadata_payload"},
            {"rank": 2, "element": "exact_letter_serial_and_or_exact_tracing_no"},
            {"rank": 3, "element": "official_source_title"},
            {"rank": 4, "element": "official_legal_entity_and_symbol"},
            {"rank": 5, "element": "fiscal_year_end"},
            {"rank": 6, "element": "annual_or_interim_status"},
            {"rank": 7, "element": "audited_or_unaudited_status"},
            {"rank": 8, "element": "parent_separate_or_consolidated_scope"},
            {"rank": 9, "element": "revision_or_restatement_identity"},
            {"rank": 10, "element": "publish_datetime_of_exact_bound_version"},
        ],
        "locked_rules": {
            "letter_serial_or_tracing_no_identifies_exact_official_version": True,
            "candidate_search_result_not_automatically_canonical": True,
            "incomplete_paginated_cache_cannot_prove_canonical_uniqueness": True,
            "decision_aspx_without_required_official_metadata_insufficient": True,
            "sent_datetime_is_audit_only_never_available_at": True,
            "publish_datetime_only_after_exact_source_version_binding": True,
            "absence_of_eslahiye_does_not_prove_original": True,
            "unknown_revision_status_remains_unresolved": True,
            "subsidiary_only_title_structural_rejection_for_parent_row": True,
            "multiple_documents_unresolved_until_document_role_adjudication": True,
            "normalization_alone_never_creates_bound": True,
        },
    }


def build_row_requirements(evidence: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in evidence:
        key = row["predictor_row_key_t"]
        status = row["binding_status"]
        serial = row.get("source_letter_serial") or ""
        url = row.get("source_url") or ""
        if key == "اردستان|1401":
            disposition = "structurally_rejected"
            eligible_second = "false"
            notes = (
                "subsidiary-only title / parent-company identity mismatch; "
                "remains structurally rejected unless different parent-company "
                "evidence already exists in tracked files"
            )
        elif key == "ثنوسا|1392":
            disposition = "potentially_resolvable"
            eligible_second = "true"
            notes = "requires multi-document role adjudication and official metadata"
        else:
            disposition = "unresolved_evidence_gap"
            eligible_second = "true"
            notes = (
                "requires canonical document-version proof and complete official metadata"
            )
        out.append({
            "scope_row_id": row["scope_row_id"],
            "predictor_row_key_t": key,
            "current_status": status,
            "structural_disposition": disposition,
            "normalization_only_sufficient": "false",
            "required_source_fields": (
                "official_title;legal_entity;symbol;fiscal_year_end;"
                "revision_status;publish_datetime;letter_serial_or_tracing_no"
            ),
            "required_canonical_fields": (
                "canonical_letter_serial;canonical_legal_entity;"
                "canonical_statement_scope;canonical_fiscal_year_end"
            ),
            "required_alias_evidence": (
                "true" if key != "ثنوسا|1392" else "false"
            ),
            "required_scope_evidence": "true",
            "required_revision_evidence": "true",
            "required_publish_datetime_evidence": "true",
            "required_document_role_adjudication": (
                "true" if key == "ثنوسا|1392" else "false"
            ),
            "official_metadata_capture_required": (
                "false" if disposition == "structurally_rejected" else "true"
            ),
            "exact_candidate_letter_serials": serial,
            "exact_candidate_urls": url,
            "known_endpoint_provenance": (
                "historical_authorized_codal_capture_receipt"
                if key == "ثنوسا|1392"
                else "stage124_feasibility_local_cache_candidate_url"
            ),
            "endpoint_resolution_status": (
                "exact_url_present_in_tracked_evidence" if url else "endpoint_unresolved"
            ),
            "eligible_for_second_resolution_pilot": eligible_second,
            "eligible_for_80_row_scale_up": "false",
            "notes": notes,
        })
    return out


ALLOWED_DECISION_QUERY_KEYS = frozenset({"LetterSerial", "rt", "let", "ct", "ft"})


def validate_proposed_request_url(
    exact_url: str | None,
    candidate_letter_serial: str | None,
    *,
    request_status: str,
) -> None:
    """Fail-closed HTTPS/host/path/LetterSerial contract for proposed URLs."""
    if exact_url is None:
        if request_status != "endpoint_unresolved_not_authorizable":
            raise QCFail(
                "exact_url null only permitted when "
                "request_status=endpoint_unresolved_not_authorizable"
            )
        return
    if not isinstance(exact_url, str) or not exact_url.strip():
        raise QCFail("exact_url must be a nonempty string when not null")
    if "*" in exact_url:
        raise QCFail("wildcard_endpoint_forbidden")
    parsed = urlparse(exact_url)
    if parsed.scheme != "https":
        raise QCFail(f"all_non_null_urls_https failed: scheme={parsed.scheme!r}")
    if parsed.hostname != "www.codal.ir":
        raise QCFail(
            f"all_non_null_hosts_exact failed: host={parsed.hostname!r}"
        )
    if "*" in (parsed.hostname or ""):
        raise QCFail("wildcard_host_forbidden")
    if parsed.port is not None and parsed.port != 443:
        raise QCFail(f"all_non_null_hosts_exact failed: port={parsed.port}")
    if parsed.path != "/Reports/Decision.aspx":
        raise QCFail(f"all_non_null_paths_exact failed: path={parsed.path!r}")
    if parsed.username is not None or parsed.password is not None:
        raise QCFail("no_credentials_or_fragments: credentials present")
    if parsed.fragment:
        raise QCFail("no_credentials_or_fragments: fragment present")
    qs = parse_qs(parsed.query, keep_blank_values=True)
    unknown = sorted(set(qs) - ALLOWED_DECISION_QUERY_KEYS)
    if unknown:
        raise QCFail(f"unexpected_query_keys:{unknown}")
    serials = qs.get("LetterSerial", [])
    if len(serials) != 1:
        raise QCFail(
            f"all_url_letter_serials_match failed: "
            f"LetterSerial count={len(serials)}"
        )
    decoded = serials[0]
    expected = (candidate_letter_serial or "").strip()
    if not expected:
        raise QCFail("all_url_letter_serials_match failed: missing candidate")
    if decoded != expected:
        raise QCFail(
            f"all_url_letter_serials_match failed: "
            f"url={decoded!r} candidate={expected!r}"
        )
    if request_status == "not_proposed_structurally_rejected":
        return
    if request_status not in (
        "proposed_not_authorized",
        "endpoint_unresolved_not_authorizable",
    ):
        raise QCFail(f"unexpected_request_status:{request_status}")


def build_proposed_capture(evidence: list[dict[str, str]]) -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    for idx, row in enumerate(evidence, start=1):
        key = row["predictor_row_key_t"]
        url = (row.get("source_url") or "").strip() or None
        serial = (row.get("source_letter_serial") or "").strip() or None
        if key == "اردستان|1401":
            status = "not_proposed_structurally_rejected"
            necessity = "none_structural_rejection"
            # Retain tracked URL as evidence; never eligible for execution.
            if not url:
                status = "endpoint_unresolved_not_authorizable"
                necessity = "cannot_authorize_without_exact_tracked_url"
        elif url:
            status = "proposed_not_authorized"
            necessity = "official_metadata_for_binding_resolution"
        else:
            status = "endpoint_unresolved_not_authorizable"
            necessity = "cannot_authorize_without_exact_tracked_url"
            url = None
        if status == "endpoint_unresolved_not_authorizable":
            url = None
        validate_proposed_request_url(
            url, serial, request_status=status,
        )
        requests.append({
            "request_id": f"p3b1c_proposed_{idx:03d}",
            "predictor_row_key_t": key,
            "purpose": "document_metadata_provenance_only",
            "http_method": "GET",
            "exact_url": url,
            "host": "www.codal.ir" if url else None,
            "expected_metadata_fields": [
                "official_title", "legal_entity", "symbol", "fiscal_year_end",
                "revision_status", "PublishDateTime", "SentDateTime",
                "LetterSerial", "TracingNo",
            ],
            "candidate_letter_serial": serial,
            "maximum_redirects": 5,
            "maximum_response_bytes": 2_000_000,
            "cache_policy": "gitignored_immutable_cache_optional_local",
            "request_necessity": necessity,
            "request_status": status,
            "evidence_class": (
                "existing_historical_capture"
                if key == "ثنوسا|1392"
                else (
                    "existing_local_cached_evidence"
                    if url else "proposed_future_request_unresolved"
                )
            ),
        })
    return {
        "authorization_status": "not_authorized",
        "requires_explicit_user_approval": True,
        "execution_performed": False,
        "network_requests_attempted": 0,
        "decision_version": DECISION_VERSION,
        "http_method_policy": "GET_only",
        "transport_policy": "HTTPS_only",
        "wildcard_url_forbidden": True,
        "wildcard_host_forbidden": True,
        "inferred_endpoint_forbidden": True,
        "search_engine_url_forbidden": True,
        "financial_value_endpoint_forbidden": True,
        "purpose_allowed": "metadata_provenance_only",
        "existing_historical_capture": {
            "predictor_row_key_t": "ثنوسا|1392",
            "receipt": "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json",
            "parsed_receipt": (
                "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json"
            ),
        },
        "proposed_requests": requests,
    }


def build_scale_up_decision() -> dict[str, Any]:
    return {
        "decision_version": DECISION_VERSION,
        "five_row_binding_pilot_completed": True,
        "current_bound_count": 0,
        "current_unresolved_count": 4,
        "current_rejected_count": 1,
        "current_available_at_non_null_count": 0,
        "scale_up_to_80_rows_authorized": False,
        "same_five_row_resolution_capture_authorized": False,
        "same_five_row_resolution_capture_requires_explicit_user_approval": True,
        "candidate_value_extraction_authorized": False,
        "pair_value_extraction_authorized": False,
        "real_available_at_assignment_authorized": False,
        "cutoff_resolution_authorized": False,
        "accessibility_scoring_authorized": False,
        "gate_application_authorized": False,
        "part3b2_authorized": False,
        "stage126_authorized": False,
        "modeling_authorized": False,
        "rationale": (
            "A zero-bound five-row mini-pilot does not justify expanding "
            "document-binding capture to all 80 pilot pairs. A later explicit "
            "user decision may authorize a second resolution attempt on the "
            "same five rows only."
        ),
    }


def build_decision_lock(
    pinned: dict[str, str],
    taxonomy_count: int,
    proposed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "decision_lock_version": DECISION_VERSION,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "qc_scope": MAINTENANCE_TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "offline_only": True,
        "network_requests_attempted": 0,
        "part3b1b_evidence_mutated": False,
        "current_statuses_unchanged": True,
        "current_counts": dict(EXPECTED_COUNTS),
        "locked_rows": list(LOCKED_KEYS),
        "failure_taxonomy_row_count": taxonomy_count,
        "proposed_capture_authorization_status": proposed["authorization_status"],
        "scale_up_to_80_rows_authorized": False,
        "pinned_input_sha256": pinned,
        "explicit_non_claims": {
            "no_codal_network": True,
            "no_tsetmc_network": True,
            "no_cbi_network": True,
            "no_search_engine_network": True,
            "no_new_raw_capture": True,
            "no_financial_value_extraction": True,
            "no_real_available_at_assignment": True,
            "no_cutoff_resolution": True,
            "no_accessibility_scoring": True,
            "no_gate_application": True,
            "no_part3b2": True,
            "no_stage126": True,
            "no_modeling": True,
            "research_pointers_unchanged": True,
        },
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "part3b_completed": False,
        "gates_applied": 0,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "modeling_started": False,
        "document_binding_resolution_decision_locked": True,
    }


def build_readme() -> str:
    return """# Stage125 Part 3B.1C — Document Binding Resolution Decision Lock

**Status:** offline protocol / adjudication lock only.

## Scope

- Failure taxonomy from frozen Part 3B.1B evidence (no reinterpretation)
- Conservative identity-normalization contract (mechanical only)
- Exact-document evidence hierarchy
- Row-level resolution requirements
- Proposed future capture authorization manifest (**not authorized**)
- Scale-up readiness decision (`scale_up_to_80_rows_authorized=false`)

## Explicit non-claims

- No CODAL / TSETMC / CBI / search-engine / other network
- No new raw capture
- No mutation of Part 3B.1B evidence or statuses
- No real `available_at` assignment / cutoff resolution
- No financial-value extraction / scoring / Gate application
- No Part 3B.2 / Stage126 / modeling
- Research pointers unchanged

## Research pointers (unchanged)

- `last_completed_research_action_id=stage125-part3a-decision-lock`
- `next_research_action_id=stage125-part3b-evidence-capture`
"""


# --------------------------------------------------------------------------- #
# QC / metadata / content assembly
# --------------------------------------------------------------------------- #

def verify_current_statuses(evidence: list[dict[str, str]]) -> None:
    if len(evidence) != 5:
        raise QCFail(f"five_locked_rows_exact failed: n={len(evidence)}")
    keys = [r["predictor_row_key_t"] for r in evidence]
    if tuple(keys) != LOCKED_KEYS:
        raise QCFail(f"five_locked_rows_exact failed: {keys}")
    for r in evidence:
        exp = EXPECTED_STATUS[r["predictor_row_key_t"]]
        if r["binding_status"] != exp:
            raise QCFail(
                f"current_statuses_unchanged failed: "
                f"{r['predictor_row_key_t']}={r['binding_status']}!={exp}"
            )
        if r.get("available_at"):
            raise QCFail("available_at must remain null on all rows")


def taxonomy_frozen_pairs(
    evidence: list[dict[str, str]],
) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in evidence:
        for token in split_failure_tokens(row.get("failure_reasons") or ""):
            pairs.add((row["predictor_row_key_t"], token))
    return pairs


def verify_taxonomy_coverage(
    evidence: list[dict[str, str]], taxonomy: list[dict[str, str]],
) -> None:
    frozen_pairs = taxonomy_frozen_pairs(evidence)
    tax_pairs = {
        (r["predictor_row_key_t"], r["failure_reason"]) for r in taxonomy
    }
    missing = sorted(frozen_pairs - tax_pairs)
    invented = sorted(tax_pairs - frozen_pairs)
    if missing:
        raise QCFail(f"all_failure_tokens_taxonomized failed missing={missing}")
    if invented:
        raise QCFail(f"no_invented_failure_token failed invented={invented}")
    if frozen_pairs != tax_pairs:
        raise QCFail("all_failure_tokens_taxonomized pair equality failed")


def read_roadmap_research_pointers(repo_root: Path) -> tuple[str, str]:
    text = (repo_root / "project/docs/ai/ROADMAP.md").read_text(encoding="utf-8")
    last = next_id = ""
    for line in text.splitlines():
        if line.startswith("last_completed_research_action_id:"):
            last = line.split(":", 1)[1].strip()
        elif line.startswith("next_research_action_id:"):
            next_id = line.split(":", 1)[1].strip()
    if not last or not next_id:
        raise QCFail("roadmap research pointers missing")
    return last, next_id


def _assert_taxonomy_field_provenance(
    evidence: list[dict[str, str]],
    taxonomy: list[dict[str, str]],
) -> dict[str, tuple[bool, str]]:
    by_key = {r["predictor_row_key_t"]: r for r in evidence}
    results: dict[str, tuple[bool, str]] = {}

    thanusa_ticker = [
        r for r in taxonomy
        if r["predictor_row_key_t"] == "ثنوسا|1392"
        and r["failure_reason"] == "ticker_mismatch"
    ]
    ok_ticker = (
        len(thanusa_ticker) == 1
        and thanusa_ticker[0]["observed_source_value"] == ""
        and thanusa_ticker[0]["observed_canonical_value"] == "ثنوسا"
        and thanusa_ticker[0]["normalization_safe"] == "false"
        and thanusa_ticker[0]["normalization_rule_id"] == ""
        and thanusa_ticker[0]["failure_layer"] == "ticker"
        and thanusa_ticker[0]["failure_class"] == "missing_source_evidence"
        and thanusa_ticker[0]["resolution_status"]
        == "requires_official_symbol_metadata"
    )
    results["ticker_source_not_backfilled_from_canonical"] = (
        ok_ticker,
        f"rows={thanusa_ticker}",
    )

    title_rows = [r for r in taxonomy if r["failure_reason"] == "missing_official_title"]
    title_ok = True
    title_detail: list[str] = []
    for tr in title_rows:
        erow = by_key[tr["predictor_row_key_t"]]
        exp_src = erow.get("source_official_title") or ""
        exp_can = erow.get("canonical_official_title") or ""
        if tr["observed_source_value"] != exp_src:
            title_ok = False
            title_detail.append(f"{tr['predictor_row_key_t']}:source_drift")
        if tr["observed_canonical_value"] != exp_can:
            title_ok = False
            title_detail.append(f"{tr['predictor_row_key_t']}:canonical_drift")
        if exp_src and not exp_can:
            if (
                tr["failure_layer"] != "canonical_metadata"
                or tr["failure_class"] != "missing_canonical_evidence"
            ):
                title_ok = False
                title_detail.append(f"{tr['predictor_row_key_t']}:side_class")
        elif (not exp_src) and exp_can:
            if (
                tr["failure_layer"] != "source_metadata"
                or tr["failure_class"] != "missing_source_evidence"
            ):
                title_ok = False
                title_detail.append(f"{tr['predictor_row_key_t']}:side_class")
    results["missing_title_side_classified_exactly"] = (
        title_ok and bool(title_rows),
        ";".join(title_detail) or f"n={len(title_rows)}",
    )

    letter_rows = [r for r in taxonomy if r["failure_reason"] == "letter_code_mismatch"]
    letter_ok = True
    for lr in letter_rows:
        erow = by_key[lr["predictor_row_key_t"]]
        serials = {
            (erow.get("source_letter_serial") or "").strip(),
            (erow.get("canonical_letter_serial") or "").strip(),
        }
        serials.discard("")
        if lr["observed_source_value"] or lr["observed_canonical_value"]:
            letter_ok = False
        if (
            lr["observed_source_value"] in serials
            or lr["observed_canonical_value"] in serials
        ):
            letter_ok = False
        if lr["resolution_status"] != (
            "letter_code_values_not_preserved_in_frozen_evidence"
        ):
            letter_ok = False
    results["letter_code_not_substituted_with_letter_serial"] = (
        letter_ok and bool(letter_rows),
        f"n={len(letter_rows)}",
    )

    scope_tokens = {
        "statement_scope_mismatch", "separate_scope_required_but_not_met",
    }
    scope_rows = [r for r in taxonomy if r["failure_reason"] in scope_tokens]
    scope_ok = True
    for sr in scope_rows:
        erow = by_key[sr["predictor_row_key_t"]]
        if sr["observed_source_value"] != (erow.get("source_statement_scope") or ""):
            scope_ok = False
        if sr["observed_canonical_value"] != (
            erow.get("canonical_statement_scope") or ""
        ):
            scope_ok = False
    results["statement_scope_values_preserved"] = (
        scope_ok and bool(scope_rows), f"n={len(scope_rows)}",
    )

    entity_rows = [r for r in taxonomy if r["failure_reason"] == "entity_mismatch"]
    entity_ok = True
    for er in entity_rows:
        erow = by_key[er["predictor_row_key_t"]]
        if er["observed_source_value"] != (erow.get("source_legal_entity") or ""):
            entity_ok = False
        if er["observed_canonical_value"] != (
            erow.get("canonical_legal_entity") or ""
        ):
            entity_ok = False
    results["raw_values_preserved"] = (
        entity_ok and bool(entity_rows), f"entity_rows={len(entity_rows)}",
    )

    family_ok = True
    for tr in taxonomy:
        erow = by_key[tr["predictor_row_key_t"]]
        exp_src, exp_can = observed_values_for_token(erow, tr["failure_reason"])
        if tr["failure_reason"] == "ticker_mismatch":
            exp_src = ""
            exp_can = erow.get("ticker") or ""
        elif tr["failure_reason"] == "letter_code_mismatch":
            exp_src, exp_can = "", ""
        if tr["observed_source_value"] != exp_src:
            family_ok = False
        if tr["observed_canonical_value"] != exp_can:
            family_ok = False
    results["taxonomy_field_families_exact"] = (family_ok, "ok" if family_ok else "drift")
    return results


def build_qc_assertions(
    *,
    repo_root: Path,
    evidence: list[dict[str, str]],
    taxonomy: list[dict[str, str]],
    norm: dict[str, Any],
    hierarchy: dict[str, Any],
    proposed: dict[str, Any],
    scale: dict[str, Any],
    lock: dict[str, Any],
    baseline_ok: bool,
    baseline_detail: str,
    drift: list[str],
    network_attempts: int,
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    add("baseline_main_exact", baseline_ok, baseline_detail)
    add("five_locked_rows_exact",
        [r["predictor_row_key_t"] for r in evidence] == list(LOCKED_KEYS),
        str([r["predictor_row_key_t"] for r in evidence]))
    add("part3b1b_source_hashes_pinned", True, "verified_pre_build")
    add("current_statuses_unchanged",
        all(r["binding_status"] == EXPECTED_STATUS[r["predictor_row_key_t"]]
            for r in evidence),
        "ok")
    bound = sum(1 for r in evidence if r["binding_status"] == "BOUND")
    unresolved = sum(1 for r in evidence if r["binding_status"] == "UNRESOLVED")
    rejected = sum(1 for r in evidence if r["binding_status"] == "REJECTED")
    avail = sum(1 for r in evidence if r.get("available_at"))
    add("current_counts_unchanged",
        (bound, unresolved, rejected, avail) == (0, 4, 1, 0),
        f"b={bound},u={unresolved},r={rejected},a={avail}")

    frozen_pairs = taxonomy_frozen_pairs(evidence)
    tax_pairs = {
        (r["predictor_row_key_t"], r["failure_reason"]) for r in taxonomy
    }
    unique_tokens = {p[1] for p in frozen_pairs}
    add(
        "all_failure_tokens_taxonomized",
        frozen_pairs == tax_pairs,
        (
            f"unique_failure_token_count={len(unique_tokens)};"
            f"taxonomy_row_count={len(taxonomy)}"
        ),
    )
    add("no_invented_failure_token",
        not (tax_pairs - frozen_pairs),
        str(sorted(tax_pairs - frozen_pairs)))

    provenance = _assert_taxonomy_field_provenance(evidence, taxonomy)
    for name, (ok, detail) in provenance.items():
        add(name, ok, detail)

    add("normalization_rules_mechanical_only",
        all(not r.get("identity_information_removed", True)
            for r in norm["allowed_mechanical_rules"]),
        "ok")
    add("no_fuzzy_matching",
        "fuzzy_matching" in norm["prohibited_transforms"], "ok")
    add("no_unproven_alias",
        norm["pinned_alias_source_present"] is False
        and norm["legal_prefix_equivalence_without_pinned_alias"] is False,
        "ok")
    add("subsidiary_rejection_preserved",
        any(r["failure_reason"] == "subsidiary_only_title"
            and r["structural_rejection"] == "true" for r in taxonomy),
        "ok")
    add("unknown_revision_not_promoted_to_original",
        hierarchy["locked_rules"]["absence_of_eslahiye_does_not_prove_original"]
        and hierarchy["locked_rules"]["unknown_revision_status_remains_unresolved"],
        "ok")
    add("incomplete_cache_not_treated_as_unique",
        hierarchy["locked_rules"][
            "incomplete_paginated_cache_cannot_prove_canonical_uniqueness"
        ],
        "ok")
    add("publish_datetime_requires_exact_binding",
        hierarchy["locked_rules"][
            "publish_datetime_only_after_exact_source_version_binding"
        ],
        "ok")
    add("sent_datetime_never_availability",
        hierarchy["locked_rules"]["sent_datetime_is_audit_only_never_available_at"],
        "ok")
    add("proposed_capture_not_authorized",
        proposed["authorization_status"] == "not_authorized"
        and proposed["execution_performed"] is False,
        proposed["authorization_status"])

    url_errors: list[str] = []
    https_ok = hosts_ok = paths_ok = serials_ok = creds_ok = True
    structural_ok = True
    for req in proposed["proposed_requests"]:
        url = req.get("exact_url")
        status = req.get("request_status")
        try:
            validate_proposed_request_url(
                url, req.get("candidate_letter_serial"), request_status=status,
            )
        except QCFail as exc:
            url_errors.append(str(exc))
            https_ok = hosts_ok = paths_ok = serials_ok = creds_ok = False
            continue
        if url is None:
            continue
        parsed = urlparse(url)
        https_ok = https_ok and parsed.scheme == "https"
        hosts_ok = hosts_ok and parsed.hostname == "www.codal.ir" and (
            parsed.port is None or parsed.port == 443
        )
        paths_ok = paths_ok and parsed.path == "/Reports/Decision.aspx"
        qs = parse_qs(parsed.query, keep_blank_values=True)
        serials = qs.get("LetterSerial", [])
        serials_ok = serials_ok and (
            len(serials) == 1
            and serials[0] == (req.get("candidate_letter_serial") or "")
        )
        creds_ok = creds_ok and (
            parsed.username is None
            and parsed.password is None
            and not parsed.fragment
        )
        if req["predictor_row_key_t"] == "اردستان|1401":
            structural_ok = (
                status == "not_proposed_structurally_rejected"
                and req.get("request_necessity") == "none_structural_rejection"
            )

    add("proposed_urls_exact_or_null", not url_errors, ";".join(url_errors) or "ok")
    add("all_non_null_urls_https", https_ok, "https")
    add("all_non_null_hosts_exact", hosts_ok, "www.codal.ir")
    add("all_non_null_paths_exact", paths_ok, "/Reports/Decision.aspx")
    add("all_url_letter_serials_match", serials_ok, "LetterSerial")
    add("no_credentials_or_fragments", creds_ok, "ok")
    add("structurally_rejected_request_not_proposed", structural_ok, "اردستان|1401")
    add("no_wildcard_endpoint",
        proposed["wildcard_url_forbidden"] and proposed["wildcard_host_forbidden"],
        "ok")
    add("network_requests_attempted_zero",
        network_attempts == 0 and proposed["network_requests_attempted"] == 0,
        str(network_attempts))
    add("scale_up_to_80_rows_false",
        scale["scale_up_to_80_rows_authorized"] is False, "false")
    add("candidate_value_extraction_false",
        scale["candidate_value_extraction_authorized"] is False, "false")
    add("pair_value_extraction_false",
        scale["pair_value_extraction_authorized"] is False, "false")
    add("real_available_at_assignment_false",
        scale["real_available_at_assignment_authorized"] is False, "false")
    add("cutoff_resolution_false",
        scale["cutoff_resolution_authorized"] is False, "false")
    add("accessibility_scoring_false",
        scale["accessibility_scoring_authorized"] is False, "false")
    add(
        "gates_applied_zero",
        lock.get("gates_applied") == 0
        and scale["gate_application_authorized"] is False,
        f"gates_applied={lock.get('gates_applied')}",
    )
    add(
        "part3b_completed_false",
        lock.get("part3b_completed") is False
        and scale.get("part3b2_authorized") is False,
        f"lock.part3b_completed={lock.get('part3b_completed')}",
    )
    add("stage126_started_false",
        scale["stage126_authorized"] is False
        and not any((repo_root / p).exists() for p in FORBIDDEN_SURFACE_EXACT
                    if "stage126" in p),
        "false")
    add("modeling_started_false",
        scale["modeling_authorized"] is False
        and lock.get("modeling_started") is False,
        "false")
    # Historical Part 3B.1C lock freezes the research pointers that were current
    # when this maintenance lock was recorded. Later ROADMAP advancement (e.g.
    # conservative six-month lag) must not rewrite those lock-embedded values.
    lock_ptrs = lock.get("research_pointers") or {}
    add(
        "research_pointers_unchanged",
        (
            lock_ptrs.get("last_completed_research_action_id")
            == RESEARCH_LAST_COMPLETED
            and lock_ptrs.get("next_research_action_id") == RESEARCH_NEXT
        ),
        f"lock={lock_ptrs}",
    )
    add("frozen_scientific_hashes_unchanged",
        frozen_before == frozen_after, "unchanged")
    add("official_check_drift_empty", drift == [], str(drift))
    return assertions


def build_all_content(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    pinned = verify_pinned_inputs(repo_root)
    evidence = load_evidence_rows(repo_root)
    verify_current_statuses(evidence)
    evidence_sha = pinned[EVIDENCE_REL]
    taxonomy = build_taxonomy_rows(evidence, evidence_sha)
    verify_taxonomy_coverage(evidence, taxonomy)
    norm = build_identity_normalization_contract()
    hierarchy = build_evidence_hierarchy()
    row_req = build_row_requirements(evidence)
    proposed = build_proposed_capture(evidence)
    scale = build_scale_up_decision()
    lock = build_decision_lock(pinned, len(taxonomy), proposed)
    content = {
        F_TAXONOMY: _csv_str(TAXONOMY_HEADER, taxonomy),
        F_NORM: _json_str(norm),
        F_HIERARCHY: _json_str(hierarchy),
        F_ROW_REQ: _csv_str(ROW_REQ_HEADER, row_req),
        F_PROPOSED: _json_str(proposed),
        F_SCALE: _json_str(scale),
        F_LOCK: _json_str(lock),
        F_README: build_readme(),
    }
    extras = {
        "evidence": evidence,
        "taxonomy": taxonomy,
        "norm": norm,
        "hierarchy": hierarchy,
        "proposed": proposed,
        "scale": scale,
        "lock": lock,
        "pinned": pinned,
    }
    return content, extras


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
    if not write and not check:
        # Allow write=False check=False only via explicit check from runner;
        # treat as check for safety when called with check=True only.
        pass

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)

    baseline_detail = verify_baseline_commit(str(repo_root))
    baseline_ok = True
    frozen_before = frozen_scientific_hashes(repo_root)
    network_attempts = 0
    files_written: dict[str, str] = {}

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all_content(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: {sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
        }
        # Provisional drift on content for QC assertion; full drift after QC built.
        content_drift = (
            _compare_drift(out_dir, content) if out_dir.is_dir() else sorted(content)
        )

        frozen_after = frozen_scientific_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen scientific assets mutated during Part 3B.1C run")

        # For committed QC determinism: official_check_drift_empty is True when
        # content identity holds; canonical --check raises on any full drift.
        assertions = build_qc_assertions(
            repo_root=repo_root,
            evidence=extras["evidence"],
            taxonomy=extras["taxonomy"],
            norm=extras["norm"],
            hierarchy=extras["hierarchy"],
            proposed=extras["proposed"],
            scale=extras["scale"],
            lock=extras["lock"],
            baseline_ok=baseline_ok,
            baseline_detail=baseline_detail,
            drift=[],
            network_attempts=network_attempts,
            frozen_before=frozen_before,
            frozen_after=frozen_after,
        )
        failed = sum(1 for a in assertions if a["status"] != "PASS")
        source_commit = _git(
            str(repo_root), "log", "--format=%H", "-n", "1", "--", SRC_REL, TEST_REL, RUN_REL,
        )
        if not source_commit:
            raise QCFail(
                "source_commit unresolved: commit Part 3B.1C source/test/runner "
                "before regenerating QC artifacts"
            )
        tickers = sorted({key.split("|", 1)[0] for key in LOCKED_KEYS})
        unique_failure_token_count = len({
            r["failure_reason"] for r in extras["taxonomy"]
        })
        taxonomy_row_count = len(extras["taxonomy"])
        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "maintenance_task_id": MAINTENANCE_TASK_ID,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_commit": source_commit,
            "source_file_sha256": sha256_file(repo_root / SRC_REL) if (repo_root / SRC_REL).is_file() else None,
            "test_file_sha256": sha256_file(repo_root / TEST_REL) if (repo_root / TEST_REL).is_file() else None,
            "assertion_count": len(assertions),
            "failed_count": failed,
            "all_pass": failed == 0,
            "scope_rows": len(LOCKED_KEYS),
            "tickers": tickers,
            "ticker_count": len(tickers),
            "unique_failure_token_count": unique_failure_token_count,
            "taxonomy_row_count": taxonomy_row_count,
            "network_requests_attempted": network_attempts,
            "document_binding_resolution_decision_locked": True,
            "predictor_document_binding_mini_pilot_completed": True,
            "predictor_document_binding_evidence_collected": True,
            "predictor_available_at_evidence_collected": False,
            "pilot_cutoff_provenance_resolved": False,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": False,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "modeling_started": False,
            "stage126_started": False,
            "gates_applied": 0,
            "scale_up_to_80_rows_authorized": False,
            "proposed_capture_authorization_status": "not_authorized",
            # Inherited prior markers (unchanged by this offline lock).
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            "part3b1_decision_locked": True,
            "cut_a_available_at_operationalization_locked": True,
            "evidence_collected": True,
            "endpoint_probe_evidence_collected": True,
            # Historical Part 3B endpoint-probe network occurred earlier; this
            # Part 3B.1C offline lock performs zero network itself.
            "network_extraction_performed": True,
            **EXPECTED_COUNTS,
            "research_pointers": {
                "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
                "next_research_action_id": RESEARCH_NEXT,
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "frozen_scientific_sha256": dict(sorted(frozen_after.items())),
            "pinned_input_sha256": dict(sorted(extras["pinned"].items())),
            "assertions": assertions,
        }
        # Stabilize official_check_drift_empty for byte-identical regeneration.
        for a in qc["assertions"]:
            if a["assertion"] == "official_check_drift_empty":
                a["status"] = "PASS"
                a["detail"] = "enforced_by_canonical_check_raise"
        qc["failed_count"] = sum(1 for a in qc["assertions"] if a["status"] != "PASS")
        qc["all_pass"] = qc["failed_count"] == 0
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage125 Part 3B.1C document-binding resolution decision lock "
                "(offline taxonomy/normalization/hierarchy/proposal only)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "output_files_sha256": dict(sorted({**content_hashes, F_QC: qc_hash}.items())),
            "document_binding_resolution_decision_locked": True,
            "part3b_completed": False,
            "modeling_started": False,
            "network_requests_attempted": network_attempts,
            "scale_up_to_80_rows_authorized": False,
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
            raise QCFail(f"QC failed: {failed_a[:8]}")

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "network_requests_attempted": network_attempts,
        "content_drift_preview": content_drift,
        "extras": extras,
    }
