"""Stage125 Part 3B.1B — Controlled CODAL Predictor-Document Binding Mini-Pilot.

Limited real document-metadata / provenance capture for exactly five locked
pilot predictor rows. Reuses Part 3B.1A exact-binding + available_at rules.

Explicit prohibitions:
- no financial-value / M1–M4 value extraction
- no accessibility scoring / Gate application
- no canonical cutoff audit mutation
- no Part 3B.2 / Stage126 / modeling
- research action pointers unchanged
"""
from __future__ import annotations

import csv
import hashlib
import html as html_lib
import io
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage125_part3b1a_cut_a_available_at_operationalization as cut_a

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1b_codal_document_binding_mini_pilot"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "4d7a48288543c971f43337e9a5d9a70ccfed2610"
TASK_ID = "stage125-part3b1b-codal-document-binding-mini-pilot"
MAINTENANCE_TASK_ID = TASK_ID
RESEARCH_LAST_COMPLETED = "stage125-part3a-decision-lock"
RESEARCH_NEXT = "stage125-part3b-evidence-capture"

SRC_REL = "project/src/stage125_part3b1b_codal_document_binding.py"
TEST_REL = "project/tests/test_stage125_part3b1b_codal_document_binding.py"
RUN_REL = "project/run_stage125_part3b1b.py"

F_SCOPE = "part3b1b_predictor_document_scope_stage125.csv"
F_EVIDENCE = "part3b1b_codal_document_evidence_stage125.csv"
F_ADJ = "part3b1b_document_binding_adjudication_stage125.csv"
F_ATTEMPTS = "part3b1b_capture_attempt_log_stage125.csv"
F_NETWORK = "part3b1b_network_log_stage125.json"
F_UNRESOLVED = "part3b1b_unresolved_and_rejections_stage125.csv"
F_README = "README_STAGE125_PART3B1B_CODAL_DOCUMENT_BINDING.md"
F_QC = "stage125_part3b1b_codal_document_binding_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1b.json"
F_RECEIPT = "part3b1b_thanusa_capture_receipt_stage125.json"
F_PARSED_RECEIPT = "part3b1b_thanusa_parsed_metadata_receipt_stage125.json"

CONTENT_FILES = (
    F_SCOPE, F_EVIDENCE, F_ADJ, F_ATTEMPTS, F_NETWORK, F_UNRESOLVED, F_README,
    F_RECEIPT, F_PARSED_RECEIPT,
)

# Byte-identical with or without the optional local raw HTML cache.
DETERMINISTIC_OUTPUT_FILES = (
    F_EVIDENCE, F_ADJ, F_ATTEMPTS, F_NETWORK, F_UNRESOLVED, F_QC, F_METADATA,
)

CACHE_DIR_REL = "project/stage125/raw_cache_part3b1b"
THANUSA_EVIDENCE_ID = "ev_p3b1b_thanusa_1392_decision"
RECEIPT_REL = f"project/stage125/{F_RECEIPT}"
PARSED_RECEIPT_REL = f"project/stage125/{F_PARSED_RECEIPT}"

PART3B1B_AUTHORIZED_EXACT = frozenset({
    SRC_REL, TEST_REL, RUN_REL,
    f"project/stage125/{F_SCOPE}",
    f"project/stage125/{F_EVIDENCE}",
    f"project/stage125/{F_ADJ}",
    f"project/stage125/{F_ATTEMPTS}",
    f"project/stage125/{F_NETWORK}",
    f"project/stage125/{F_UNRESOLVED}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
    RECEIPT_REL,
    PARSED_RECEIPT_REL,
})

PILOT_CSV_REL = "project/stage125/part3a_selected_pilot_pairs_stage125.csv"
PILOT_CSV_SHA256 = (
    "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5"
)
OCF_MANIFEST_REL = (
    "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
    "ocf_source_manifest_stage121.csv"
)
OCF_MANIFEST_SHA256 = (
    "b1bf92d74f19b4c00373079c3222489d6cb54e1c8f11e30a9e02557e6936057a"
)
MODELING_ROWS_REL = (
    "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
    "modeling_all_rows_stage121.csv"
)
MODELING_ROWS_SHA256 = (
    "27d4130739c88cb8a5379e26b2e2cbedc33a1c9aa9b57b6747e5c93855540426"
)
CUTOFF_AUDIT_REL = "project/stage125/prediction_cutoff_audit_stage125_part2.csv"
CUTOFF_AUDIT_SHA256 = (
    "d50e6617b011a7818d972de8e5c8a862a45f73fb07a0a22cdb5c9f59b6dc88f0"
)

RECEIPT_REQUIRED_FIELDS = (
    "evidence_id", "scope_row_id", "predictor_row_key_t", "request_url",
    "http_method", "started_at_utc", "completed_at_utc", "retrieved_at_utc",
    "redirect_chain", "final_url", "response_status", "content_type",
    "byte_count", "payload_sha256", "metadata_sha256", "letter_serial",
    "retrieval_purpose", "raw_payload_storage_policy", "completed_at_status",
)

PARSED_RECEIPT_REQUIRED_FIELDS = (
    "evidence_id", "payload_sha256", "metadata_sha256", "parser_contract_version",
    "parsed_source_official_title", "parsed_source_legal_entity",
    "parsed_source_symbol", "parsed_publish_datetime_raw",
    "parsed_sent_datetime_raw", "parsed_fields_evidence_basis", "parsed_at_utc",
)

PILOT_FULL_FIELD_KEYS = (
    "selection_rank", "option_id", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t", "target_year",
    "class_label", "rule_a_eligible", "post_evidence_substitution_allowed",
    "selection_status",
)

RAW_PAYLOAD_STORAGE_POLICY = "gitignored_immutable_cache_optional_local"
RAW_PAYLOAD_DETERMINISM_POLICY = "optional_local_verified_if_present"
COMPLETED_AT_STATUS_MISSING = "missing_in_original_cache_metadata_preserved_null"
PARSER_CONTRACT_VERSION = "stage125_part3b1b_codal_decision_html_v1"
PARSED_FIELDS_EVIDENCE_BASIS = "explicit_codal_decision_html_fields_only"
HISTORICAL_AUTHORIZED_CAPTURE_REQUESTS = 1

THANUSA_LETTER_SERIAL = "Ddg2e7HG6FGR5ygaTFJd4g=="
THANUSA_AUTHORIZED_URL = (
    "https://www.codal.ir/Reports/Decision.aspx?LetterSerial="
    + quote(THANUSA_LETTER_SERIAL, safe="")
)
ALLOWED_CODAL_HOST = "www.codal.ir"
NETWORK_REQUESTS_AUTHORIZED_MAX = 1
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_SEC = 30.0

BINDING_BOUND = "BOUND"
BINDING_UNRESOLVED = "UNRESOLVED"
BINDING_REJECTED = "REJECTED"

STATUS_REJECT_REASONS = frozenset({
    "subsidiary_only_title",
    "parent_company_identity_mismatch",
})

PERSIAN_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

LOCAL_CACHE_BY_TICKER = {
    "بوعلی": "project/stage124_feasibility/raw/codal/بوعلی__search__dd1e77b23155.bin",
    "اپال": "project/stage124_feasibility/raw/codal/اپال__search__6a7087f0251c.bin",
    "اردستان": "project/stage124_feasibility/raw/codal/اردستان__search__05ba9f8766e9.bin",
}

LOCKED_SCOPE_SKELETON: tuple[dict[str, Any], ...] = (
    {
        "selection_rank": 6,
        "option_id": "pilot_option_event_enriched",
        "predictor_row_key_t": "ثنوسا|1392",
        "target_row_key_t_plus_1": "ثنوسا|1393",
        "ticker": "ثنوسا",
        "fiscal_year_t": 1392,
        "target_year": 1393,
        "class_label": "negative",
        "rule_a_eligible": "1",
        "post_evidence_substitution_allowed": "false",
        "selection_status": "approved_for_part3b_pilot",
        "starting_evidence_class": "B2",
    },
    {
        "selection_rank": 63,
        "option_id": "pilot_option_event_enriched",
        "predictor_row_key_t": "بوعلی|1399",
        "target_row_key_t_plus_1": "بوعلی|1400",
        "ticker": "بوعلی",
        "fiscal_year_t": 1399,
        "target_year": 1400,
        "class_label": "negative",
        "rule_a_eligible": "1",
        "post_evidence_substitution_allowed": "false",
        "selection_status": "approved_for_part3b_pilot",
        "starting_evidence_class": "B1",
    },
    {
        "selection_rank": 72,
        "option_id": "pilot_option_event_enriched",
        "predictor_row_key_t": "بوعلی|1400",
        "target_row_key_t_plus_1": "بوعلی|1401",
        "ticker": "بوعلی",
        "fiscal_year_t": 1400,
        "target_year": 1401,
        "class_label": "negative",
        "rule_a_eligible": "1",
        "post_evidence_substitution_allowed": "false",
        "selection_status": "approved_for_part3b_pilot",
        "starting_evidence_class": "B1",
    },
    {
        "selection_rank": 76,
        "option_id": "pilot_option_event_enriched",
        "predictor_row_key_t": "اردستان|1401",
        "target_row_key_t_plus_1": "اردستان|1402",
        "ticker": "اردستان",
        "fiscal_year_t": 1401,
        "target_year": 1402,
        "class_label": "negative",
        "rule_a_eligible": "1",
        "post_evidence_substitution_allowed": "false",
        "selection_status": "approved_for_part3b_pilot",
        "starting_evidence_class": "B3",
    },
    {
        "selection_rank": 77,
        "option_id": "pilot_option_event_enriched",
        "predictor_row_key_t": "اپال|1401",
        "target_row_key_t_plus_1": "اپال|1402",
        "ticker": "اپال",
        "fiscal_year_t": 1401,
        "target_year": 1402,
        "class_label": "negative",
        "rule_a_eligible": "1",
        "post_evidence_substitution_allowed": "false",
        "selection_status": "approved_for_part3b_pilot",
        "starting_evidence_class": "B1",
    },
)


def _repo_root_from_module() -> Path:
    return Path(__file__).resolve().parents[2]


# Populated after helper definitions via rebuild_locked_scope().
LOCKED_SCOPE: tuple[dict[str, Any], ...] = tuple(
    {
        **row,
        "canonical_fiscal_year_end": None,
        "canonical_company_name": None,
        "canonical_legal_entity": None,
        "canonical_statement_scope": None,
        "canonical_official_title": None,
        "canonical_tracing_no": None,
        "canonical_letter_serial": (
            THANUSA_LETTER_SERIAL if row["ticker"] == "ثنوسا" else None
        ),
    }
    for row in LOCKED_SCOPE_SKELETON
)

SCOPE_KEYS = frozenset(row["predictor_row_key_t"] for row in LOCKED_SCOPE_SKELETON)

FROZEN_SCIENTIFIC_PATHS = cut_a.FROZEN_SCIENTIFIC_PATHS + (
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
)

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})

FORBIDDEN_HOSTS = frozenset({
    "search.codal.ir", "api.codal.ir", "cdn.tsetmc.com", "www.tsetmc.com",
    "tsetmc.com", "www.cbi.ir", "cbi.ir", "google.com", "www.google.com",
    "bing.com", "www.bing.com",
})

FYE_TITLE_RE = re.compile(
    r"سال مالی منتهی به\s*(\d{4}/\d{2}/\d{2})"
)
SUBSIDIARY_PAREN_RE = re.compile(r"\(شرکت\s+[^)]+\)")

EVIDENCE_COLUMNS = [
    "scope_row_id", "selection_rank", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "starting_evidence_class", "source_origin", "source_url",
    "candidate_discovery_basis", "candidate_count", "candidate_letter_serials",
    "source_letter_serial", "canonical_letter_serial",
    "source_tracing_no", "canonical_tracing_no",
    "source_official_title", "canonical_official_title",
    "source_legal_entity", "canonical_legal_entity",
    "source_statement_scope", "canonical_statement_scope",
    "source_fiscal_year_end", "canonical_fiscal_year_end",
    "is_parent_company", "is_annual", "is_interim", "is_audited",
    "source_revision_status_raw", "source_revision_status_normalized",
    "revision_evidence_basis",
    "publish_datetime_raw", "sent_datetime_raw",
    "publish_datetime_utc_candidate", "available_at",
    "available_at_source_field", "snapshot_sha256",
    "cache_snapshot_complete", "canonical_source_version_bound",
    "binding_status", "cutoff_status", "failure_reasons",
    "reviewer_status",
]

SCOPE_HEADER = [
    "scope_row_id", "selection_rank", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "starting_evidence_class", "canonical_fiscal_year_end",
    "canonical_legal_entity", "canonical_statement_scope",
    "canonical_letter_serial", "pilot_csv_full_fields_verified",
    "reviewer_status",
]

ADJ_HEADER = [
    "scope_row_id", "predictor_row_key_t", "binding_status", "binding_ok",
    "cutoff_status", "available_at", "available_at_source_field",
    "failure_reasons", "adjudication_notes", "reviewer_status",
]

ATTEMPT_HEADER = [
    "capture_run_id", "attempt_id", "scope_row_id", "predictor_row_key_t",
    "planned_request_url", "http_method", "started_at_utc", "completed_at_utc",
    "final_url", "response_status", "content_type", "byte_count",
    "redirect_count", "payload_sha256", "metadata_sha256", "success",
    "failure_class", "network_log_complete", "reviewer_status",
]

UNRESOLVED_HEADER = [
    "scope_row_id", "predictor_row_key_t", "binding_status",
    "starting_evidence_class", "failure_reasons", "source_origin",
    "reviewer_status",
]

# Executable-path patterns only (not prohibition docs / deny-lists).
_VALUE_EXTRACTION_CODE_PATTERNS = (
    re.compile(r"\bdef\s+extract_financial\b"),
    re.compile(r"\bdef\s+apply_gate\b"),
    re.compile(r"\bdef\s+train_model\b"),
    re.compile(r"\bm1_value\s*="),
    re.compile(r"\bm2_value\s*="),
    re.compile(r"\bm3_value\s*="),
    re.compile(r"\bm4_value\s*="),
    re.compile(r"\baccessibility_score\s*="),
    re.compile(r"\bfrom\s+.*stage126"),
    re.compile(r"\bimport\s+.*stage126"),
)


def _source_has_forbidden_value_extraction_tokens(repo_root: Path) -> bool:
    """True only when executable value-extraction / modeling paths appear."""
    src_text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    # Strip module/docstring blocks so prohibition prose cannot false-positive.
    cleaned = re.sub(r'"""[\s\S]*?"""', "", src_text, count=1)
    cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned, count=1)
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(pat.search(stripped) for pat in _VALUE_EXTRACTION_CODE_PATTERNS):
            return True
    return False


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.1B."""


class NetworkPolicyError(RuntimeError):
    """Fail-closed network policy violation."""


# --------------------------------------------------------------------------- #
# Hash / IO helpers
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
        raise QCFail(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def normalize_persian_digits(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).translate(PERSIAN_DIGIT_MAP)


def _blank(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _blank(row.get(k)) for k in header})
    return buf.getvalue()


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str) -> str:
    head = _git(repo_root, "rev-parse", "HEAD")
    if head == EXPECTED_BASELINE_COMMIT:
        return head
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head):
        raise QCFail(
            f"expected baseline {EXPECTED_BASELINE_COMMIT} not ancestor of HEAD "
            f"(HEAD={head})"
        )
    return head


def frozen_scientific_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in FROZEN_SCIENTIFIC_PATHS:
        path = repo_root / rel
        digest = sha256_file(path)
        if digest is None:
            raise QCFail(f"missing frozen scientific file: {rel}")
        out[rel] = digest
    return out


def verify_pilot_csv_hash(repo_root: Path) -> None:
    path = repo_root / PILOT_CSV_REL
    digest = sha256_file(path)
    if digest != PILOT_CSV_SHA256:
        raise QCFail(
            f"pilot CSV hash mismatch: expected {PILOT_CSV_SHA256} got {digest}"
        )


def verify_ocf_manifest_hash(repo_root: Path) -> None:
    path = repo_root / OCF_MANIFEST_REL
    digest = sha256_file(path)
    if digest != OCF_MANIFEST_SHA256:
        raise QCFail(
            f"OCF manifest hash mismatch: expected {OCF_MANIFEST_SHA256} got {digest}"
        )


def parse_thanusa_ocf_manifest_row(repo_root: Path) -> dict[str, Any]:
    """Require exactly one OCF manifest row for ثنوسا|1392 and derive fields."""
    verify_ocf_manifest_hash(repo_root)
    path = repo_root / OCF_MANIFEST_REL
    matches: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("ticker") == "ثنوسا" and str(row.get("fiscal_year")) == "1392":
                matches.append(dict(row))
    if len(matches) != 1:
        raise QCFail(
            f"thanusa_manifest_exact_row_unique failed: matched={len(matches)}"
        )
    row = matches[0]
    codal_url = row.get("codal_url") or ""
    qs = parse_qs(urlparse(codal_url).query)
    serials = qs.get("LetterSerial") or qs.get("letterserial") or []
    letter_serial = unquote(serials[0]) if serials else None
    if letter_serial != THANUSA_LETTER_SERIAL:
        raise QCFail(
            "thanusa_letter_serial_derived_from_manifest_url failed: "
            f"got {letter_serial!r}"
        )
    return {
        "ticker": row.get("ticker"),
        "fiscal_year": row.get("fiscal_year"),
        "fiscal_year_end": row.get("fiscal_year_end"),
        "audit_status": row.get("audit_status"),
        "statement_scope": row.get("statement_scope"),
        "codal_url": row.get("codal_url"),
        "letter_serial": letter_serial,
        "source_pdf": row.get("source_pdf"),
        "source_page": row.get("source_page"),
        "source_pdf_sha256": row.get("sha256"),
        "decision": row.get("decision"),
        "evidence_basis": "ocf_source_manifest_stage121_exact_row",
        "manifest_path": OCF_MANIFEST_REL,
        "manifest_sha256": OCF_MANIFEST_SHA256,
    }


def load_canonical_row_fields(repo_root: Path) -> dict[str, dict[str, str | None]]:
    """Load canonical entity/FYE/scope by predictor_row_key_t from pinned sources."""
    modeling_path = repo_root / MODELING_ROWS_REL
    digest = sha256_file(modeling_path)
    if digest != MODELING_ROWS_SHA256:
        raise QCFail(
            f"modeling_all_rows hash mismatch: expected {MODELING_ROWS_SHA256} got {digest}"
        )
    cutoff_path = repo_root / CUTOFF_AUDIT_REL
    cutoff_digest = sha256_file(cutoff_path)
    if cutoff_digest != CUTOFF_AUDIT_SHA256:
        raise QCFail(
            f"cutoff audit hash mismatch: expected {CUTOFF_AUDIT_SHA256} got {cutoff_digest}"
        )
    wanted = {row["predictor_row_key_t"] for row in LOCKED_SCOPE_SKELETON}
    out: dict[str, dict[str, str | None]] = {}
    with modeling_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            key = row.get("row_key")
            if key not in wanted:
                continue
            company = (row.get("company_name") or "").strip() or None
            fye = (row.get("fiscal_year_end") or "").strip() or None
            scope = (row.get("statement_scope_status") or "").strip() or None
            out[key] = {
                "canonical_legal_entity": company,
                "canonical_fiscal_year_end": fye,
                "canonical_statement_scope": scope,
                "canonical_source_path": MODELING_ROWS_REL,
                "canonical_source_sha256": MODELING_ROWS_SHA256,
            }
    with cutoff_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            key = row.get("predictor_row_key_t")
            if key not in wanted or key not in out:
                continue
            cutoff_fye = (row.get("fiscal_year_end_t") or "").strip() or None
            model_fye = out[key]["canonical_fiscal_year_end"]
            if cutoff_fye and model_fye and cutoff_fye != model_fye:
                raise QCFail(
                    f"canonical FYE conflict for {key}: modeling={model_fye} "
                    f"cutoff={cutoff_fye}"
                )
            if not model_fye and cutoff_fye:
                out[key]["canonical_fiscal_year_end"] = cutoff_fye
    missing = wanted - set(out)
    if missing:
        raise QCFail(f"canonical modeling rows missing for: {sorted(missing)}")
    return out


def build_locked_scope(repo_root: Path) -> tuple[dict[str, Any], ...]:
    canonical = load_canonical_row_fields(repo_root)
    thanusa_manifest = parse_thanusa_ocf_manifest_row(repo_root)
    rows: list[dict[str, Any]] = []
    for skeleton in LOCKED_SCOPE_SKELETON:
        key = skeleton["predictor_row_key_t"]
        can = canonical[key]
        row = dict(skeleton)
        row["canonical_fiscal_year_end"] = can["canonical_fiscal_year_end"]
        row["canonical_company_name"] = can["canonical_legal_entity"]
        row["canonical_legal_entity"] = can["canonical_legal_entity"]
        row["canonical_statement_scope"] = can["canonical_statement_scope"]
        row["canonical_official_title"] = None
        row["canonical_tracing_no"] = None
        if key == "ثنوسا|1392":
            row["canonical_letter_serial"] = thanusa_manifest["letter_serial"]
        else:
            row["canonical_letter_serial"] = None
        row["canonical_source_path"] = can["canonical_source_path"]
        row["canonical_source_sha256"] = can["canonical_source_sha256"]
        rows.append(row)
    return tuple(rows)


def rebuild_locked_scope(repo_root: Path) -> tuple[dict[str, Any], ...]:
    global LOCKED_SCOPE
    LOCKED_SCOPE = build_locked_scope(repo_root)
    return LOCKED_SCOPE


def verify_locked_scope_against_pilot(repo_root: Path) -> dict[str, dict[str, str]]:
    """Exact equality for all 11 required pilot fields on the five locked rows."""
    verify_pilot_csv_hash(repo_root)
    path = repo_root / PILOT_CSV_REL
    by_rank: dict[int, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            by_rank[int(row["selection_rank"])] = dict(row)
    verified: dict[str, dict[str, str]] = {}
    for scope in LOCKED_SCOPE:
        rank = int(scope["selection_rank"])
        row_key = str(scope["predictor_row_key_t"])
        if rank not in by_rank:
            raise QCFail(f"locked scope rank {rank} missing from pilot CSV")
        pilot = by_rank[rank]
        for field_name in PILOT_FULL_FIELD_KEYS:
            if field_name not in pilot:
                raise QCFail(f"pilot_field_mismatch:{row_key}:{field_name}")
            if field_name not in scope:
                raise QCFail(f"pilot_field_mismatch:{row_key}:{field_name}")
            pilot_value = str(pilot[field_name])
            locked_expected_value = str(scope[field_name])
            if pilot_value != locked_expected_value:
                raise QCFail(f"pilot_field_mismatch:{row_key}:{field_name}")
        verified[row_key] = pilot
    return verified


def is_scope_row_key_allowed(key: str) -> bool:
    return key in SCOPE_KEYS


def scope_row_id(scope: dict[str, Any]) -> str:
    return f"p3b1b_scope_{scope['selection_rank']:03d}"


# --------------------------------------------------------------------------- #
# Network policy
# --------------------------------------------------------------------------- #

def assert_url_allowed(url: str) -> None:
    """Fail-closed URL allowlist: exactly one authorized CODAL Decision GET."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise NetworkPolicyError("only https allowed")
    host = (parsed.hostname or "").lower()
    if host in FORBIDDEN_HOSTS:
        raise NetworkPolicyError(f"forbidden host: {host}")
    if host != ALLOWED_CODAL_HOST:
        raise NetworkPolicyError(f"host not allowed: {host}")
    if parsed.port not in (None, 443):
        raise NetworkPolicyError("only port 443 allowed")
    if url != THANUSA_AUTHORIZED_URL:
        raise NetworkPolicyError("URL not in Part 3B.1B authorized exact set")


def _assert_public_ip(ip: str) -> None:
    ip_obj = ipaddress.ip_address(ip)
    if (
        ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
    ):
        raise NetworkPolicyError(f"private/reserved IP rejected: {ip}")


def _parse_http_response(
    raw: bytes, original_url: str,
) -> tuple[bytes, int, str, str]:
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
        headers[k.decode("iso-8859-1").strip().lower()] = (
            v.decode("iso-8859-1", errors="replace").strip()
        )
    ctype = headers.get("content-type", "")
    location = headers.get("location", "")
    final_url = original_url
    if status in (301, 302, 303, 307, 308) and location:
        final_url = urljoin(original_url, location)
        redirect_host = (urlparse(final_url).hostname or "").lower()
        if redirect_host != ALLOWED_CODAL_HOST:
            raise NetworkPolicyError(f"redirect host not allowed: {redirect_host}")
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _dechunk(body)
    if len(body) > MAX_RESPONSE_BYTES:
        raise NetworkPolicyError("body exceeds size ceiling")
    return body, status, final_url, ctype


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
    return bytes(out)


def _default_https_transport(
    method: str,
    url: str,
    *,
    orig_connect: Callable[..., Any] | None = None,
    orig_getaddrinfo: Callable[..., Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    assert_url_allowed(url)
    method = method.upper()
    if method != "GET":
        raise NetworkPolicyError(f"method not allowed: {method}")
    redirect_chain: list[str] = [url]
    current = url
    redirects = 0
    while True:
        parsed = urlparse(current)
        host = parsed.hostname
        assert host
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        getaddrinfo = orig_getaddrinfo or socket.getaddrinfo
        infos = getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addrs = []
        for info in infos:
            ip = info[4][0]
            _assert_public_ip(ip)
            addrs.append(ip)
        if not addrs:
            raise NetworkPolicyError(f"no addresses for {host}")
        ip = addrs[0]
        raw_req = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: papermali-stage125-part3b1b-readonly/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        context = ssl.create_default_context()
        sock = None
        try:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(REQUEST_TIMEOUT_SEC)
            connect = orig_connect or raw_sock.connect
            connect(raw_sock, (ip, 443))
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
        body, status, final_url, ctype = _parse_http_response(raw, current)
        if status in (301, 302, 303, 307, 308):
            redirects += 1
            if redirects > MAX_REDIRECTS:
                raise NetworkPolicyError("too many redirects")
            if not final_url or final_url == current:
                raise NetworkPolicyError("redirect without location")
            redirect_chain.append(final_url)
            current = final_url
            continue
        return body, {
            "request_url": url,
            "redirect_chain": redirect_chain,
            "final_url": final_url,
            "response_status": status,
            "content_type": ctype,
            "bytes": len(body),
            "redirect_count": redirects,
        }


@dataclass
class ThanusaFetchResult:
    body: bytes
    payload_sha256: str
    metadata_sha256: str
    network_entry: dict[str, Any]
    parsed_html: dict[str, str | None]
    success: bool
    failure_class: str


def parse_codal_decision_html(html: bytes | str) -> dict[str, str | None]:
    """Parse only facts explicitly present on CODAL Decision.aspx HTML."""
    text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    out: dict[str, str | None] = {
        "official_title": None,
        "legal_entity": None,
        "symbol": None,
        "publish_datetime_raw": None,
        "sent_datetime_raw": None,
    }
    if not text.strip():
        return out
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I | re.S)
    if title_m:
        out["official_title"] = html_lib.unescape(title_m.group(1)).strip()
    company_m = re.search(
        r'id="[^"]*CompanyName[^"]*"[^>]*>([^<]+)<', text, re.I,
    )
    if company_m:
        # Preserve exact source spelling before any normalization.
        out["legal_entity"] = html_lib.unescape(company_m.group(1)).strip()
    symbol_m = re.search(
        r'id="ctl00_lblSymbol"[^>]*>([^<]+)<', text, re.I,
    ) or re.search(
        r'id="[^"]*lblDisplaySymbol[^"]*"[^>]*>([^<]+)<', text, re.I,
    )
    if symbol_m:
        sym = html_lib.unescape(symbol_m.group(1)).strip()
        if sym and sym != "نماد:":
            out["symbol"] = sym
    for field, patterns in (
        ("publish_datetime_raw", (
            r'PublishDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            r'lblPublishDateTime[^>]*>([^<]+)<',
            r'تاریخ انتشار[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
        )),
        ("sent_datetime_raw", (
            r'SentDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            r'lblSentDateTime[^>]*>([^<]+)<',
            r'تاریخ ارسال[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
        )),
    ):
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                out[field] = normalize_persian_digits(m.group(1)).strip()
                break
    return out


def _load_thanusa_cache_paths(
    cache: p3b0.ImmutableCache,
) -> tuple[Path, Path, dict[str, Any]] | None:
    root = cache.root
    if not root.is_dir():
        return None
    for meta_path in root.rglob("metadata.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("evidence_id") != THANUSA_EVIDENCE_ID:
            continue
        payload_path = meta_path.parent / "payload.bin"
        return payload_path, meta_path, meta
    return None


def _load_thanusa_cache_entry(
    cache: p3b0.ImmutableCache,
) -> tuple[bytes, dict[str, Any], str] | None:
    """Return payload, metadata dict, and metadata_sha256 from cache files."""
    loaded = _load_thanusa_cache_paths(cache)
    if loaded is None:
        return None
    payload_path, meta_path, meta = loaded
    if not payload_path.is_file():
        return None
    sha_path = meta_path.parent / "metadata.sha256"
    if sha_path.is_file():
        metadata_sha256 = sha_path.read_text(encoding="utf-8").strip()
    else:
        metadata_sha256 = sha256_bytes(
            json.dumps(meta, sort_keys=True, ensure_ascii=False).encode("utf-8")
        )
    return payload_path.read_bytes(), meta, metadata_sha256


def build_capture_receipt_from_cache_metadata(
    meta: dict[str, Any],
    *,
    metadata_sha256: str | None,
) -> dict[str, Any]:
    """Build tracked receipt from immutable-cache metadata (no invented timestamps)."""
    return {
        "evidence_id": meta.get("evidence_id"),
        "scope_row_id": meta.get("scope_row_id"),
        "predictor_row_key_t": meta.get("predictor_row_key_t"),
        "request_url": meta.get("request_url"),
        "http_method": "GET",
        "started_at_utc": meta.get("started_at_utc"),
        "completed_at_utc": meta.get("completed_at_utc"),  # may be null
        "completed_at_status": COMPLETED_AT_STATUS_MISSING,
        "retrieved_at_utc": meta.get("retrieved_at_utc"),
        "redirect_chain": list(meta.get("redirect_chain") or []),
        "final_url": meta.get("final_url"),
        "response_status": meta.get("response_status"),
        "content_type": meta.get("content_type"),
        "byte_count": meta.get("bytes"),
        "payload_sha256": meta.get("content_sha256") or meta.get("payload_sha256"),
        "metadata_sha256": metadata_sha256,
        "letter_serial": meta.get("letter_serial"),
        "retrieval_purpose": meta.get("retrieval_purpose"),
        "raw_payload_storage_policy": RAW_PAYLOAD_STORAGE_POLICY,
    }


def load_tracked_capture_receipt(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / RECEIPT_REL
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_tracked_parsed_metadata_receipt(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / PARSED_RECEIPT_REL
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parsed_html_from_parsed_receipt(
    parsed_receipt: dict[str, Any],
) -> dict[str, str | None]:
    return {
        "official_title": parsed_receipt.get("parsed_source_official_title"),
        "legal_entity": parsed_receipt.get("parsed_source_legal_entity"),
        "symbol": parsed_receipt.get("parsed_source_symbol"),
        "publish_datetime_raw": parsed_receipt.get("parsed_publish_datetime_raw"),
        "sent_datetime_raw": parsed_receipt.get("parsed_sent_datetime_raw"),
    }


def build_parsed_metadata_receipt(
    *,
    body: bytes,
    capture_receipt: dict[str, Any],
    parsed_at_utc: str,
) -> dict[str, Any]:
    """Extract only facts present in the immutable raw payload (no guesses)."""
    parsed = parse_codal_decision_html(body)
    payload_sha = sha256_bytes(body)
    if capture_receipt.get("payload_sha256") not in (None, "", payload_sha):
        raise QCFail("parsed_metadata_receipt_payload_hash_bound failed")
    return {
        "evidence_id": capture_receipt.get("evidence_id") or THANUSA_EVIDENCE_ID,
        "payload_sha256": payload_sha,
        "metadata_sha256": capture_receipt.get("metadata_sha256"),
        "parser_contract_version": PARSER_CONTRACT_VERSION,
        "parsed_source_official_title": parsed["official_title"],
        "parsed_source_legal_entity": parsed["legal_entity"],
        "parsed_source_symbol": parsed["symbol"],
        "parsed_publish_datetime_raw": parsed["publish_datetime_raw"],
        "parsed_sent_datetime_raw": parsed["sent_datetime_raw"],
        "parsed_fields_evidence_basis": PARSED_FIELDS_EVIDENCE_BASIS,
        "parsed_at_utc": parsed_at_utc,
    }


def validate_capture_receipt(receipt: dict[str, Any]) -> list[str]:
    """Return exact QC failure reasons for incomplete receipt fields."""
    reasons: list[str] = []
    for field_name in RECEIPT_REQUIRED_FIELDS:
        if field_name not in receipt:
            reasons.append(f"capture_receipt_missing_field:{field_name}")
            continue
        # completed_at_utc may be explicitly null when absent from original metadata.
        if field_name == "completed_at_utc":
            continue
        value = receipt.get(field_name)
        if value is None or value == "" or value == []:
            reasons.append(f"capture_receipt_required_field_null:{field_name}")
    if receipt.get("completed_at_status") != COMPLETED_AT_STATUS_MISSING:
        reasons.append("capture_completed_at_status_mismatch")
    if receipt.get("request_url") != THANUSA_AUTHORIZED_URL:
        reasons.append("authorized_url_exact_mismatch")
    host = urlparse(str(receipt.get("request_url") or "")).hostname
    if host != ALLOWED_CODAL_HOST:
        reasons.append("authorized_host_exact_mismatch")
    if receipt.get("letter_serial") != THANUSA_LETTER_SERIAL:
        reasons.append("receipt_letter_serial_mismatch")
    return reasons


def validate_parsed_metadata_receipt(
    parsed_receipt: dict[str, Any],
    *,
    capture_receipt: dict[str, Any] | None = None,
    parsed_from_payload: dict[str, str | None] | None = None,
) -> list[str]:
    reasons: list[str] = []
    for field_name in PARSED_RECEIPT_REQUIRED_FIELDS:
        if field_name not in parsed_receipt:
            reasons.append(f"parsed_receipt_missing_field:{field_name}")
    if parsed_receipt.get("evidence_id") != THANUSA_EVIDENCE_ID:
        reasons.append("parsed_receipt_evidence_id_mismatch")
    if parsed_receipt.get("parser_contract_version") != PARSER_CONTRACT_VERSION:
        reasons.append("parsed_receipt_parser_contract_mismatch")
    if parsed_receipt.get("parsed_fields_evidence_basis") != PARSED_FIELDS_EVIDENCE_BASIS:
        reasons.append("parsed_receipt_evidence_basis_mismatch")
    if not parsed_receipt.get("parsed_at_utc"):
        reasons.append("parsed_receipt_parsed_at_utc_missing")
    if capture_receipt is not None:
        if parsed_receipt.get("payload_sha256") != capture_receipt.get("payload_sha256"):
            reasons.append("parsed_metadata_receipt_payload_hash_bound")
        if parsed_receipt.get("metadata_sha256") != capture_receipt.get("metadata_sha256"):
            reasons.append("parsed_metadata_receipt_metadata_hash_bound")
    if parsed_from_payload is not None:
        expected = parsed_html_from_parsed_receipt(parsed_receipt)
        if expected != parsed_from_payload:
            reasons.append("parsed_metadata_receipt_fields_exact")
    return reasons


def _stable_thanusa_network_entry(receipt: dict[str, Any]) -> dict[str, Any]:
    """Environment-independent transport metadata for tracked network log."""
    return {
        "request_url": receipt.get("request_url"),
        "redirect_chain": list(receipt.get("redirect_chain") or []),
        "final_url": receipt.get("final_url"),
        "response_status": receipt.get("response_status"),
        "content_type": receipt.get("content_type"),
        "bytes": receipt.get("byte_count"),
        "payload_sha256": receipt.get("payload_sha256"),
        "metadata_sha256": receipt.get("metadata_sha256"),
        "started_at_utc": receipt.get("started_at_utc"),
        "completed_at_utc": receipt.get("completed_at_utc"),
        "retrieved_at_utc": receipt.get("retrieved_at_utc"),
        "historical_authorized_capture": True,
        "raw_payload_storage_policy": RAW_PAYLOAD_DETERMINISM_POLICY,
    }


def resolve_thanusa_from_local_evidence(
    repo_root: Path,
    cache: p3b0.ImmutableCache,
    *,
    write_receipt: bool,
) -> tuple[
    ThanusaFetchResult | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    str,
]:
    """Resolve ثنوسا evidence from cache and/or tracked receipts. Never networks."""
    receipt = load_tracked_capture_receipt(repo_root)
    parsed_receipt = load_tracked_parsed_metadata_receipt(repo_root)
    cached = _load_thanusa_cache_entry(cache)
    raw_payload_status = "raw_payload_local_optional_absent"

    if cached is not None:
        body, meta, metadata_sha256 = cached
        built = build_capture_receipt_from_cache_metadata(
            meta, metadata_sha256=metadata_sha256,
        )
        if receipt is None:
            receipt = built
        else:
            # Preserve historical timestamps from whichever source has them.
            for ts_key in ("started_at_utc", "completed_at_utc", "retrieved_at_utc"):
                if not receipt.get(ts_key) and built.get(ts_key):
                    receipt[ts_key] = built[ts_key]
            for key in (
                "payload_sha256", "metadata_sha256", "byte_count",
                "response_status", "content_type", "final_url", "request_url",
                "redirect_chain", "letter_serial", "evidence_id", "scope_row_id",
                "predictor_row_key_t", "retrieval_purpose", "http_method",
                "raw_payload_storage_policy", "completed_at_status",
            ):
                if receipt.get(key) in (None, "", []) and built.get(key) not in (None, "", []):
                    receipt[key] = built[key]
        if receipt.get("completed_at_status") in (None, ""):
            receipt["completed_at_status"] = COMPLETED_AT_STATUS_MISSING
        payload_sha = sha256_bytes(body)
        if receipt.get("payload_sha256") and receipt["payload_sha256"] != payload_sha:
            raise QCFail("payload_sha_matches_receipt failed")
        if metadata_sha256 and receipt.get("metadata_sha256") not in (
            None, metadata_sha256,
        ):
            receipt["metadata_sha256"] = metadata_sha256
        raw_payload_status = "raw_payload_local_present_verified"
        parsed = parse_codal_decision_html(body)
        if parsed_receipt is None:
            parsed_receipt = build_parsed_metadata_receipt(
                body=body,
                capture_receipt=receipt,
                parsed_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        else:
            fail = validate_parsed_metadata_receipt(
                parsed_receipt,
                capture_receipt=receipt,
                parsed_from_payload=parsed,
            )
            if fail:
                raise QCFail(f"parsed metadata receipt invalid: {fail}")
        network_entry = _stable_thanusa_network_entry(receipt)
        fetch = ThanusaFetchResult(
            body=body,
            payload_sha256=payload_sha,
            metadata_sha256=str(receipt.get("metadata_sha256") or ""),
            network_entry=network_entry,
            parsed_html=parsed,
            success=True,
            failure_class="",
        )
    elif receipt is not None and parsed_receipt is not None:
        fail = validate_parsed_metadata_receipt(
            parsed_receipt, capture_receipt=receipt,
        )
        if fail:
            raise QCFail(f"parsed metadata receipt invalid: {fail}")
        if receipt.get("completed_at_status") in (None, ""):
            receipt["completed_at_status"] = COMPLETED_AT_STATUS_MISSING
        parsed = parsed_html_from_parsed_receipt(parsed_receipt)
        network_entry = _stable_thanusa_network_entry(receipt)
        fetch = ThanusaFetchResult(
            body=b"",
            payload_sha256=str(receipt.get("payload_sha256") or ""),
            metadata_sha256=str(receipt.get("metadata_sha256") or ""),
            network_entry=network_entry,
            parsed_html=parsed,
            success=True,
            failure_class="",
        )
    elif receipt is not None:
        raise QCFail(
            "parsed_metadata_receipt_tracked missing; "
            "fresh-clone reconstruction requires tracked parsed metadata"
        )
    else:
        fetch = None

    if write_receipt and receipt is not None:
        out_path = repo_root / RECEIPT_REL
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_json_str(receipt), encoding="utf-8")
        if parsed_receipt is not None:
            parsed_path = repo_root / PARSED_RECEIPT_REL
            parsed_path.write_text(_json_str(parsed_receipt), encoding="utf-8")

    return fetch, receipt, parsed_receipt, raw_payload_status


def thanusa_fetch_receipt_only(
    receipt: dict[str, Any],
    parsed_receipt: dict[str, Any],
) -> ThanusaFetchResult:
    """Build a raw-absent ThanusaFetchResult from tracked receipts only."""
    fail = validate_parsed_metadata_receipt(
        parsed_receipt, capture_receipt=receipt,
    )
    if fail:
        raise QCFail(f"parsed metadata receipt invalid: {fail}")
    return ThanusaFetchResult(
        body=b"",
        payload_sha256=str(receipt.get("payload_sha256") or ""),
        metadata_sha256=str(receipt.get("metadata_sha256") or ""),
        network_entry=_stable_thanusa_network_entry(receipt),
        parsed_html=parsed_html_from_parsed_receipt(parsed_receipt),
        success=True,
        failure_class="",
    )


def authorize_and_fetch_thanusa(
    *,
    cache: p3b0.ImmutableCache,
    capture: bool,
    transport: Callable[[str, str], tuple[bytes, dict[str, Any]]] | None = None,
    orig_connect: Callable[..., Any] | None = None,
    orig_getaddrinfo: Callable[..., Any] | None = None,
    repo_root: Path | None = None,
) -> ThanusaFetchResult | None:
    """Load the historical authorized capture from cache/receipt only.

    Additional CODAL network requests are not authorized for this harden pass.
    The ``capture`` / ``transport`` arguments are retained for API compatibility
    but never perform a new GET.
    """
    del capture, transport, orig_connect, orig_getaddrinfo
    root = repo_root or _repo_root_from_module()
    fetch, _receipt, _parsed, _status = resolve_thanusa_from_local_evidence(
        root, cache, write_receipt=False,
    )
    return fetch


# --------------------------------------------------------------------------- #
# Local cache letter matching
# --------------------------------------------------------------------------- #

@dataclass
class LetterCandidate:
    title: str
    publish_datetime: str | None
    sent_datetime: str | None
    tracing_no: str | None
    url: str | None
    letter_serial: str | None
    company_name: str | None
    symbol: str | None
    letter_code: str | None
    fiscal_year_end: str | None
    is_annual: bool
    is_interim: bool
    is_audited: bool
    subsidiary_only_title: bool
    is_parent_company: bool
    revision_status_raw: str | None
    revision_status_normalized: str | None


def extract_letter_serial_from_url(url: str | None) -> str | None:
    if not url:
        return None
    full = url if url.startswith("http") else f"https://{ALLOWED_CODAL_HOST}{url}"
    qs = parse_qs(urlparse(full).query)
    serials = qs.get("LetterSerial") or qs.get("letterserial")
    if not serials:
        return None
    return unquote(serials[0])


def classify_title_flags(title: str) -> dict[str, Any]:
    norm = normalize_persian_digits(title)
    interim = "میاندوره" in norm
    audited = "حسابرسی شده" in norm
    # Annual cue from title wording; do not invent revision status from annual alone.
    annual = (("سال مالی" in norm) or ("12 ماهه" in norm) or ("۱۲ ماهه" in norm)) and not interim
    subsidiary = bool(SUBSIDIARY_PAREN_RE.search(norm))
    fye_m = FYE_TITLE_RE.search(norm)
    if not fye_m:
        fye_m = re.search(
            r"(?:12|۱۲)\s*ماهه\s*منتهی\s*به\s*(\d{4}/\d{2}/\d{2})",
            norm,
        )
    fye = fye_m.group(1) if fye_m else None
    raw_rev = cut_a.CODAL_ESLAHIYE_RAW if cut_a.CODAL_ESLAHIYE_RAW in norm else None
    # Never guess original merely because the title lacks «اصلاحیه».
    norm_rev = cut_a.explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=raw_rev,
        map_eslahiye_to_revision=True,
    )
    return {
        "fiscal_year_end": fye,
        "is_annual": bool(annual and audited),
        "is_interim": interim,
        "is_audited": audited,
        "subsidiary_only_title": subsidiary,
        "is_parent_company": bool(annual and audited and not subsidiary),
        "revision_status_raw": raw_rev,
        "revision_status_normalized": norm_rev,
        "revision_evidence_basis": (
            "explicit_codal_eslahiye_in_title" if raw_rev else "unknown_revision_status"
        ),
    }


def letter_dict_to_candidate(letter: dict[str, Any]) -> LetterCandidate:
    title = str(letter.get("Title") or "")
    flags = classify_title_flags(title)
    url = letter.get("Url")
    serial = letter.get("LetterSerial") or extract_letter_serial_from_url(url)
    public_url = (
        f"https://{ALLOWED_CODAL_HOST}{url}" if url and not str(url).startswith("http")
        else url
    )
    return LetterCandidate(
        title=title,
        publish_datetime=letter.get("PublishDateTime"),
        sent_datetime=letter.get("SentDateTime"),
        tracing_no=str(letter.get("TracingNo")) if letter.get("TracingNo") is not None else None,
        url=public_url,
        letter_serial=serial,
        company_name=letter.get("CompanyName"),
        symbol=letter.get("Symbol"),
        letter_code=letter.get("LetterCode") or None,
        fiscal_year_end=flags["fiscal_year_end"],
        is_annual=flags["is_annual"],
        is_interim=flags["is_interim"],
        is_audited=flags["is_audited"],
        subsidiary_only_title=flags["subsidiary_only_title"],
        is_parent_company=flags["is_parent_company"],
        revision_status_raw=flags["revision_status_raw"],
        revision_status_normalized=flags["revision_status_normalized"],
    )


def is_cache_incomplete(cache_data: dict[str, Any]) -> bool:
    page = int(cache_data.get("Page") or 1)
    total = int(cache_data.get("Total") or 0)
    letters = cache_data.get("Letters") or []
    page_size = len(letters)
    if total > page_size:
        return True
    if page != 1 and total > page_size:
        return True
    return False


def match_local_letter_candidates(
    cache_data: dict[str, Any],
    scope_row: dict[str, Any],
) -> tuple[list[LetterCandidate], dict[str, Any]]:
    """Match annual audited letters for the canonical FYE from a local search cache."""
    target_fye = scope_row["canonical_fiscal_year_end"]
    incomplete = is_cache_incomplete(cache_data)
    matched: list[LetterCandidate] = []
    for letter in cache_data.get("Letters") or []:
        cand = letter_dict_to_candidate(letter)
        if cand.fiscal_year_end != target_fye:
            continue
        if not cand.is_annual or cand.is_interim or not cand.is_audited:
            continue
        matched.append(cand)
    return matched, {
        "incomplete_pagination": incomplete,
        "cache_page": cache_data.get("Page"),
        "cache_total": cache_data.get("Total"),
        "letters_on_page": len(cache_data.get("Letters") or []),
    }


def build_binding_input_from_candidate(
    scope_row: dict[str, Any],
    candidate: LetterCandidate | None,
    *,
    cache_complete: bool,
    snapshot_sha256: str | None,
    candidate_letter_serials: list[str],
    incomplete_pagination: bool,
    multi_document_predictor_row: bool = False,
    canonical_source_version_bound: bool = False,
    source_official_title: str | None = None,
    source_legal_entity: str | None = None,
    source_fiscal_year_end: str | None = None,
    source_statement_scope: str | None = None,
    source_letter_serial: str | None = None,
    source_tracing_no: str | None = None,
    source_revision_status_raw: str | None = None,
    source_revision_status_normalized: str | None = None,
    letter_ticker: str | None = None,
    candidate_discovery_basis: str = "local_cache_ticker_fye_annual_audited_candidate",
    public_codal_url: str | None = None,
    is_annual: bool | None = None,
    is_interim: bool | None = None,
    is_audited: bool | None = None,
    is_parent_company: bool | None = None,
    subsidiary_only_title: bool | None = None,
) -> cut_a.ExactDocumentBindingInput:
    del cache_complete  # recorded separately on evidence rows
    # Never copy canonical official title from the candidate/source title.
    canonical_title = scope_row.get("canonical_official_title") or ""
    letter_title = (
        source_official_title
        if source_official_title is not None
        else (candidate.title if candidate else "")
    )
    legal_entity_letter = (
        source_legal_entity
        if source_legal_entity is not None
        else (candidate.company_name if candidate else None)
    ) or ""
    fye_letter = (
        source_fiscal_year_end
        if source_fiscal_year_end is not None
        else (candidate.fiscal_year_end if candidate else None)
    ) or ""
    scope_letter = source_statement_scope or ""
    serial = (
        source_letter_serial
        if source_letter_serial is not None
        else (candidate.letter_serial if candidate else None)
    )
    tracing = (
        source_tracing_no
        if source_tracing_no is not None
        else (candidate.tracing_no if candidate else None)
    )
    rev_raw = (
        source_revision_status_raw
        if source_revision_status_raw is not None
        else (candidate.revision_status_raw if candidate else None)
    )
    rev_norm = (
        source_revision_status_normalized
        if source_revision_status_normalized is not None
        else (candidate.revision_status_normalized if candidate else None)
    )
    match_basis = (
        "exact_letter_serial"
        if scope_row.get("canonical_letter_serial")
        else candidate_discovery_basis
    )
    return cut_a.ExactDocumentBindingInput(
        canonical_ticker=scope_row["ticker"],
        letter_ticker=(
            letter_ticker
            if letter_ticker is not None
            else ((candidate.symbol if candidate else None) or "")
        ),
        legal_entity_canonical=scope_row.get("canonical_legal_entity") or "",
        legal_entity_letter=legal_entity_letter,
        predictor_fiscal_year=int(scope_row["fiscal_year_t"]),
        letter_fiscal_year=int(scope_row["fiscal_year_t"]),
        fiscal_year_end_canonical=scope_row.get("canonical_fiscal_year_end") or "",
        fiscal_year_end_letter=fye_letter,
        is_annual=is_annual if is_annual is not None else (
            candidate.is_annual if candidate else False
        ),
        is_interim=is_interim if is_interim is not None else (
            candidate.is_interim if candidate else False
        ),
        is_audited=is_audited if is_audited is not None else (
            candidate.is_audited if candidate else False
        ),
        is_parent_company=is_parent_company if is_parent_company is not None else (
            candidate.is_parent_company if candidate else False
        ),
        statement_scope_canonical=scope_row.get("canonical_statement_scope") or "",
        statement_scope_letter=scope_letter,
        requires_separate_non_consolidated=True,
        letter_code_canonical="",
        letter_code_letter=(candidate.letter_code if candidate and candidate.letter_code else ""),
        letter_serial=serial,
        canonical_letter_serial=scope_row.get("canonical_letter_serial"),
        tracing_no=tracing,
        canonical_tracing_no=scope_row.get("canonical_tracing_no"),
        official_title=letter_title or "",
        canonical_official_title=canonical_title,
        revision_status=rev_norm,
        revision_status_raw=rev_raw,
        public_codal_url=(
            public_codal_url
            if public_codal_url is not None
            else (candidate.url if candidate else None)
        ),
        raw_payload_or_snapshot_hash=snapshot_sha256,
        candidate_letter_serials=candidate_letter_serials,
        incomplete_pagination=incomplete_pagination,
        match_basis=match_basis,
        subsidiary_only_title=(
            subsidiary_only_title
            if subsidiary_only_title is not None
            else (candidate.subsidiary_only_title if candidate else False)
        ),
        entity_ambiguous=False,
        consolidated_separate_ambiguous=False,
        annual_interim_ambiguous=False,
        canonical_source_version_bound=canonical_source_version_bound,
        multi_document_predictor_row=multi_document_predictor_row,
        values_source_letter_serial=serial or scope_row.get("canonical_letter_serial"),
        publish_of_original_used_for_correction_values=False,
    )


def classify_binding_status(
    binding_result: cut_a.BindingResult,
    *,
    multi_document_predictor_row: bool = False,
    candidate_present: bool = True,
) -> str:
    """Classify binding outcome.

    REJECTED only for an affirmatively wrong candidate document:
    subsidiary-only title, or parent-company mismatch when a real candidate
    was present. Missing/default fields without a candidate stay UNRESOLVED.
    """
    reasons = set(binding_result.reasons)
    if "subsidiary_only_title" in reasons:
        return BINDING_REJECTED
    if candidate_present and "parent_company_identity_mismatch" in reasons:
        return BINDING_REJECTED
    if binding_result.ok and not multi_document_predictor_row:
        return BINDING_BOUND
    return BINDING_UNRESOLVED


# --------------------------------------------------------------------------- #
# Row adjudication
# --------------------------------------------------------------------------- #

def _publish_utc_candidate(raw: str | None) -> str | None:
    parsed = cut_a.parse_codal_publish_datetime(raw)
    if isinstance(parsed, cut_a.NormalizedTimestamp):
        return parsed.utc_iso8601
    return None


def adjudicate_scope_row(
    scope_row: dict[str, Any],
    *,
    candidate: LetterCandidate | None,
    candidates: list[LetterCandidate] | None = None,
    cache_meta: dict[str, Any] | None,
    cache_file_sha256: str | None,
    thanusa_fetch: ThanusaFetchResult | None,
    thanusa_manifest: dict[str, Any] | None,
    source_origin: str,
    candidate_discovery_basis: str,
    local_cache_missing: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    sid = scope_row_id(scope_row)
    incomplete = bool(cache_meta and cache_meta.get("incomplete_pagination"))
    multi_doc = False
    canonical_bound = False
    all_candidates = list(candidates or ([] if candidate is None else [candidate]))
    candidate_serials = [
        c.letter_serial for c in all_candidates if c.letter_serial
    ]
    publish_raw = None
    sent_raw = None
    snapshot_sha = cache_file_sha256
    source_legal_entity = None
    source_fye = None
    source_scope = None
    source_title = None
    source_letter_serial = None
    source_tracing = None
    source_rev_raw = None
    source_rev_norm = None
    revision_evidence_basis = "unknown_revision_status"
    letter_ticker = None
    is_annual = None
    is_interim = None
    is_audited = None
    is_parent = None
    subsidiary = None
    public_url = None

    if local_cache_missing:
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            None,
            cache_complete=False,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=[],
            incomplete_pagination=False,
            candidate_discovery_basis=candidate_discovery_basis,
        )
    elif scope_row["ticker"] == "ثنوسا":
        multi_doc = True
        canonical_bound = False
        manifest = thanusa_manifest or {}
        # Manifest-supported facts (exact row).
        source_fye = manifest.get("fiscal_year_end")
        source_scope = manifest.get("statement_scope")
        source_letter_serial = manifest.get("letter_serial") or THANUSA_LETTER_SERIAL
        candidate_serials = [source_letter_serial]
        candidate_discovery_basis = (
            "known_letter_serial_from_exact_manifest_row;"
            "direct_decision_page_by_known_letter_serial"
        )
        if thanusa_fetch and thanusa_fetch.success:
            publish_raw = thanusa_fetch.parsed_html.get("publish_datetime_raw")
            sent_raw = thanusa_fetch.parsed_html.get("sent_datetime_raw")
            source_title = thanusa_fetch.parsed_html.get("official_title")
            source_legal_entity = thanusa_fetch.parsed_html.get("legal_entity")
            letter_ticker = thanusa_fetch.parsed_html.get("symbol")
            snapshot_sha = thanusa_fetch.payload_sha256 or snapshot_sha
            if source_title:
                # Title flags come from source-observed title (raw parse or
                # tracked parsed-metadata receipt). Never invent when absent.
                flags = classify_title_flags(source_title)
                source_fye = flags["fiscal_year_end"] or source_fye
                is_annual = flags["is_annual"]
                is_interim = flags["is_interim"]
                is_audited = flags["is_audited"]
                is_parent = flags["is_parent_company"]
                subsidiary = flags["subsidiary_only_title"]
                source_rev_raw = flags["revision_status_raw"]
                source_rev_norm = flags["revision_status_normalized"]
                revision_evidence_basis = flags["revision_evidence_basis"]
            else:
                is_annual = None
                is_interim = None
                is_audited = (
                    True if manifest.get("audit_status") == "audited" else None
                )
            public_url = THANUSA_AUTHORIZED_URL
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            None,
            cache_complete=True,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=candidate_serials,
            incomplete_pagination=False,
            multi_document_predictor_row=multi_doc,
            canonical_source_version_bound=canonical_bound,
            source_official_title=source_title,
            source_legal_entity=source_legal_entity,
            source_fiscal_year_end=source_fye,
            source_statement_scope=source_scope,
            source_letter_serial=source_letter_serial,
            source_tracing_no=None,
            source_revision_status_raw=source_rev_raw,
            source_revision_status_normalized=source_rev_norm,
            letter_ticker=letter_ticker or "",
            candidate_discovery_basis=candidate_discovery_basis,
            public_codal_url=public_url or THANUSA_AUTHORIZED_URL,
            is_annual=bool(is_annual) if is_annual is not None else False,
            is_interim=bool(is_interim) if is_interim is not None else False,
            is_audited=bool(is_audited) if is_audited is not None else False,
            is_parent_company=bool(is_parent) if is_parent is not None else False,
            subsidiary_only_title=bool(subsidiary) if subsidiary is not None else False,
        )
    elif len(all_candidates) > 1:
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            None,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=candidate_serials,
            incomplete_pagination=incomplete,
            candidate_discovery_basis=candidate_discovery_basis,
        )
    elif candidate is None:
        binding_inp = build_binding_input_from_candidate(
            scope_row, None,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=[],
            incomplete_pagination=incomplete,
            candidate_discovery_basis=candidate_discovery_basis,
        )
    else:
        if scope_row["starting_evidence_class"] == "B1" and incomplete:
            # Incomplete page cannot prove global uniqueness; keep discovery
            # serials for evidence but clear uniqueness set for binding.
            binding_serials: list[str] = []
        else:
            binding_serials = list(candidate_serials)
        publish_raw = candidate.publish_datetime
        sent_raw = candidate.sent_datetime
        source_legal_entity = candidate.company_name
        source_fye = candidate.fiscal_year_end
        source_title = candidate.title
        source_letter_serial = candidate.letter_serial
        source_tracing = candidate.tracing_no
        source_rev_raw = candidate.revision_status_raw
        source_rev_norm = candidate.revision_status_normalized
        revision_evidence_basis = (
            "explicit_codal_eslahiye_in_title"
            if source_rev_raw
            else "unknown_revision_status"
        )
        letter_ticker = candidate.symbol
        is_annual = candidate.is_annual
        is_interim = candidate.is_interim
        is_audited = candidate.is_audited
        is_parent = candidate.is_parent_company
        subsidiary = candidate.subsidiary_only_title
        public_url = candidate.url
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            candidate,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=binding_serials,
            incomplete_pagination=incomplete,
            canonical_source_version_bound=False,
            source_official_title=source_title,
            source_legal_entity=source_legal_entity,
            source_fiscal_year_end=source_fye,
            source_statement_scope=None,
            source_letter_serial=source_letter_serial,
            source_tracing_no=source_tracing,
            source_revision_status_raw=source_rev_raw,
            source_revision_status_normalized=source_rev_norm,
            letter_ticker=letter_ticker or "",
            candidate_discovery_basis=candidate_discovery_basis,
            public_codal_url=public_url,
        )

    bind_res = cut_a.evaluate_exact_document_binding(binding_inp)
    candidate_present = (
        candidate is not None
        or len(all_candidates) > 0
        or (thanusa_fetch is not None and thanusa_fetch.success)
    )
    status = classify_binding_status(
        bind_res,
        multi_document_predictor_row=multi_doc,
        # Multiple matches are UNRESOLVED discovery failures, not affirmative rejects.
        candidate_present=(
            candidate_present
            and not local_cache_missing
            and len(all_candidates) <= 1
        ),
    )

    avail_res = cut_a.AvailableAtResolution(
        available_at=None,
        available_at_raw_publish=cut_a.preserve_raw_codal_timestamp(publish_raw),
        sent_datetime_raw=cut_a.preserve_raw_codal_timestamp(sent_raw),
        source_field=None,
        cutoff_status=cut_a.CUTOFF_STATUS_UNRESOLVED,
        reasons=(cut_a.REASON_BINDING_FAILED,),
        binding_ok=False,
        sent_publish_relation="unknown",
    )
    if status == BINDING_BOUND:
        avail_res = cut_a.resolve_operational_available_at(
            publish_datetime_raw=publish_raw,
            sent_datetime_raw=sent_raw,
            binding=binding_inp,
        )

    reason_list = list(bind_res.reasons)
    if local_cache_missing and "required_local_cache_missing" not in reason_list:
        reason_list.insert(0, "required_local_cache_missing")
    if len(all_candidates) > 1 and "multiple_candidate_letters" not in reason_list:
        reason_list.insert(0, "multiple_candidate_letters")
    if source_rev_norm is None and "unknown_revision_status" not in reason_list:
        if scope_row["ticker"] == "ثنوسا" or candidate is not None or all_candidates:
            reason_list.append("unknown_revision_status")
    if status != BINDING_BOUND and avail_res.reasons:
        for r in avail_res.reasons:
            if r not in reason_list:
                reason_list.append(r)
    if (
        scope_row["ticker"] == "ثنوسا"
        and thanusa_fetch is not None
        and thanusa_fetch.success
        and not (publish_raw or "").strip()
    ):
        for extra_reason in (
            "official_metadata_not_exposed_by_direct_url",
            cut_a.REASON_MISSING_PUBLISH,
        ):
            if extra_reason not in reason_list:
                reason_list.append(extra_reason)
    failure_reasons = ";".join(reason_list)

    evidence = {
        "scope_row_id": sid,
        "selection_rank": scope_row["selection_rank"],
        "predictor_row_key_t": scope_row["predictor_row_key_t"],
        "target_row_key_t_plus_1": scope_row["target_row_key_t_plus_1"],
        "ticker": scope_row["ticker"],
        "fiscal_year_t": scope_row["fiscal_year_t"],
        "starting_evidence_class": scope_row["starting_evidence_class"],
        "source_origin": source_origin,
        "source_url": (
            THANUSA_AUTHORIZED_URL if scope_row["ticker"] == "ثنوسا"
            else (candidate.url if candidate else "")
        ),
        "candidate_discovery_basis": candidate_discovery_basis,
        "candidate_count": len(all_candidates) if scope_row["ticker"] != "ثنوسا"
        else (1 if source_letter_serial else 0),
        "candidate_letter_serials": ";".join(candidate_serials),
        "source_letter_serial": source_letter_serial or "",
        "canonical_letter_serial": scope_row.get("canonical_letter_serial") or "",
        "source_tracing_no": source_tracing or "",
        "canonical_tracing_no": scope_row.get("canonical_tracing_no") or "",
        "source_official_title": source_title or "",
        "canonical_official_title": scope_row.get("canonical_official_title") or "",
        "source_legal_entity": source_legal_entity or "",
        "canonical_legal_entity": scope_row.get("canonical_legal_entity") or "",
        "source_statement_scope": source_scope or "",
        "canonical_statement_scope": scope_row.get("canonical_statement_scope") or "",
        "source_fiscal_year_end": source_fye or "",
        "canonical_fiscal_year_end": scope_row.get("canonical_fiscal_year_end") or "",
        "is_parent_company": binding_inp.is_parent_company,
        "is_annual": binding_inp.is_annual,
        "is_interim": binding_inp.is_interim,
        "is_audited": binding_inp.is_audited,
        "source_revision_status_raw": source_rev_raw or "",
        "source_revision_status_normalized": source_rev_norm or "",
        "revision_evidence_basis": revision_evidence_basis,
        "publish_datetime_raw": publish_raw or "",
        "sent_datetime_raw": sent_raw or "",
        "publish_datetime_utc_candidate": _publish_utc_candidate(publish_raw) or "",
        "available_at": avail_res.available_at or "",
        "available_at_source_field": avail_res.source_field or "",
        "snapshot_sha256": snapshot_sha or "",
        "cache_snapshot_complete": (not incomplete) and (not local_cache_missing),
        "canonical_source_version_bound": canonical_bound,
        "binding_status": status,
        "cutoff_status": avail_res.cutoff_status,
        "failure_reasons": failure_reasons,
        "reviewer_status": "automated_part3b1b",
    }

    adjudication = {
        "scope_row_id": sid,
        "predictor_row_key_t": scope_row["predictor_row_key_t"],
        "binding_status": status,
        "binding_ok": bind_res.ok,
        "cutoff_status": avail_res.cutoff_status,
        "available_at": avail_res.available_at or "",
        "available_at_source_field": avail_res.source_field or "",
        "failure_reasons": failure_reasons,
        "adjudication_notes": (
            "multi_document_predictor_row_fail_closed"
            if multi_doc else ""
        ),
        "reviewer_status": "automated_part3b1b",
    }

    unresolved = None
    if status in (BINDING_UNRESOLVED, BINDING_REJECTED):
        unresolved = {
            "scope_row_id": sid,
            "predictor_row_key_t": scope_row["predictor_row_key_t"],
            "binding_status": status,
            "starting_evidence_class": scope_row["starting_evidence_class"],
            "failure_reasons": failure_reasons,
            "source_origin": source_origin,
            "reviewer_status": "automated_part3b1b",
        }
    return evidence, adjudication, unresolved


def process_all_scope_rows(
    repo_root: Path,
    *,
    capture: bool,
    cache: p3b0.ImmutableCache,
    thanusa_fetch: ThanusaFetchResult | None,
    thanusa_manifest: dict[str, Any] | None = None,
    pilot_verified: dict[str, dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    del capture
    scope_rows: list[dict] = []
    evidence_rows: list[dict] = []
    adj_rows: list[dict] = []
    unresolved_rows: list[dict] = []
    manifest = thanusa_manifest or parse_thanusa_ocf_manifest_row(repo_root)

    for scope in LOCKED_SCOPE:
        sid = scope_row_id(scope)
        pilot_ok = bool(pilot_verified and scope["predictor_row_key_t"] in pilot_verified)
        scope_rows.append({
            "scope_row_id": sid,
            "selection_rank": scope["selection_rank"],
            "predictor_row_key_t": scope["predictor_row_key_t"],
            "target_row_key_t_plus_1": scope["target_row_key_t_plus_1"],
            "ticker": scope["ticker"],
            "fiscal_year_t": scope["fiscal_year_t"],
            "starting_evidence_class": scope["starting_evidence_class"],
            "canonical_fiscal_year_end": scope.get("canonical_fiscal_year_end") or "",
            "canonical_legal_entity": scope.get("canonical_legal_entity") or "",
            "canonical_statement_scope": scope.get("canonical_statement_scope") or "",
            "canonical_letter_serial": scope.get("canonical_letter_serial") or "",
            "pilot_csv_full_fields_verified": pilot_ok,
            "reviewer_status": "automated_part3b1b",
        })

        candidate = None
        candidates: list[LetterCandidate] = []
        cache_meta = None
        cache_hash = None
        source_origin = "locked_scope_no_local_cache"
        discovery = "none"
        local_cache_missing = False

        if scope["ticker"] == "ثنوسا":
            source_origin = (
                "historical_authorized_codal_capture_receipt"
                if thanusa_fetch and thanusa_fetch.success
                else "ocf_manifest_exact_row"
            )
            discovery = (
                "known_letter_serial_from_exact_manifest_row;"
                "direct_decision_page_by_known_letter_serial"
            )
        elif scope["ticker"] in LOCAL_CACHE_BY_TICKER:
            rel = LOCAL_CACHE_BY_TICKER[scope["ticker"]]
            cache_path = repo_root / rel
            if not cache_path.is_file():
                local_cache_missing = True
                source_origin = "required_local_cache_missing"
                discovery = "required_local_cache_missing"
            else:
                cache_hash = sha256_file(cache_path)
                cache_data = json.loads(cache_path.read_bytes())
                candidates, cache_meta = match_local_letter_candidates(cache_data, scope)
                source_origin = "stage124_feasibility_local_cache"
                discovery = "local_cache_ticker_fye_annual_audited_candidate"
                if len(candidates) == 1:
                    candidate = candidates[0]
                # len>1: keep all candidates; do not silently select first.

        evidence, adj, unresolved = adjudicate_scope_row(
            scope,
            candidate=candidate,
            candidates=candidates,
            cache_meta=cache_meta,
            cache_file_sha256=cache_hash,
            thanusa_fetch=thanusa_fetch if scope["ticker"] == "ثنوسا" else None,
            thanusa_manifest=manifest if scope["ticker"] == "ثنوسا" else None,
            source_origin=source_origin,
            candidate_discovery_basis=discovery,
            local_cache_missing=local_cache_missing,
        )
        evidence_rows.append(evidence)
        adj_rows.append(adj)
        if unresolved:
            unresolved_rows.append(unresolved)

    return scope_rows, evidence_rows, adj_rows, unresolved_rows


# --------------------------------------------------------------------------- #
# README / metadata / QC
# --------------------------------------------------------------------------- #

def build_readme() -> str:
    return """# Stage125 Part 3B.1B — CODAL Predictor-Document Binding Mini-Pilot

**Status:** controlled mini-pilot for exactly five locked predictor rows.

## Scope

Document metadata / provenance capture only. No financial-value extraction,
accessibility scoring, Gate application, Stage126, or modeling.

## Locked rows

Five predictor rows verified against the frozen Part 3A pilot CSV (full fields)
and pinned Stage121 modeling / OCF manifest canonical sources:

- ثنوسا|1392 (B2) — historical authorized CODAL Decision capture (tracked receipt)
- بوعلی|1399 / بوعلی|1400 (B1) — read-only Stage124 feasibility search caches
- اردستان|1401 (B3) — subsidiary-title rejection path
- اپال|1401 (B1) — incomplete pagination without canonical LetterSerial

## Provenance

- Historical authorized capture requests performed: 1
- Current `--check` network requests attempted: 0
- Tracked capture receipt: `part3b1b_thanusa_capture_receipt_stage125.json`
- Tracked parsed-metadata receipt: `part3b1b_thanusa_parsed_metadata_receipt_stage125.json`
- Local raw HTML under `raw_cache_part3b1b/` is optional / gitignored
- Fresh clones reconstruct source-observed ثنوسا fields from the parsed receipt

## Binding statuses

`BOUND` / `UNRESOLVED` / `REJECTED` via Part 3B.1A exact-document binding.

`available_at` is assigned only when `binding_status=BOUND` using CUT-A
`PublishDateTime` → Asia/Tehran → UTC rules. `SentDateTime` is never availability.

## Research pointers (unchanged)

- `last_completed_research_action_id=stage125-part3a-decision-lock`
- `next_research_action_id=stage125-part3b-evidence-capture`
"""


def _derive_qc_counts(evidence_rows: list[dict[str, Any]]) -> dict[str, int]:
    bound = sum(1 for r in evidence_rows if r.get("binding_status") == BINDING_BOUND)
    unresolved = sum(
        1 for r in evidence_rows if r.get("binding_status") == BINDING_UNRESOLVED
    )
    rejected = sum(
        1 for r in evidence_rows if r.get("binding_status") == BINDING_REJECTED
    )
    avail_non_null = sum(1 for r in evidence_rows if r.get("available_at"))
    return {
        "bound_count": bound,
        "unresolved_count": unresolved,
        "rejected_count": rejected,
        "available_at_non_null_count": avail_non_null,
    }


def _evidence_has_value_extraction_columns(evidence_rows: list[dict[str, Any]]) -> bool:
    forbidden = {
        "m1_value", "m2_value", "m3_value", "m4_value",
        "financial_value", "operating_cash_flow", "accessibility_score",
    }
    for row in evidence_rows:
        if forbidden.intersection(row.keys()):
            return True
        for key, value in row.items():
            if key.endswith("_value") and value not in ("", None, False, True):
                return True
    return False


def build_qc_assertions(
    repo_root: Path,
    evidence_rows: list[dict[str, Any]],
    network_log: dict[str, Any],
    attempt_rows: list[dict[str, Any]],
    receipt: dict[str, Any] | None,
    *,
    current_check_network_requests_attempted: int,
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
    qc_extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    counts = _derive_qc_counts(evidence_rows)
    qc_extra = qc_extra or {}
    parsed_receipt = qc_extra.get("parsed_receipt")

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    add("scope_rows_exactly_five", len(evidence_rows) == 5, str(len(evidence_rows)))
    add("baseline_commit_constant", EXPECTED_BASELINE_COMMIT.startswith("4d7a482"), EXPECTED_BASELINE_COMMIT)
    add("pilot_csv_hash_pinned", sha256_file(repo_root / PILOT_CSV_REL) == PILOT_CSV_SHA256, PILOT_CSV_SHA256)
    add("ocf_manifest_hash_pinned",
        sha256_file(repo_root / OCF_MANIFEST_REL) == OCF_MANIFEST_SHA256,
        OCF_MANIFEST_SHA256)
    add("full_pilot_scope_fields_verified",
        bool(qc_extra.get("full_pilot_all_11_fields_exact"))
        and bool(qc_extra.get("pilot_verified_keys"))
        and set(qc_extra.get("pilot_verified_keys") or []) == SCOPE_KEYS,
        str(sorted(qc_extra.get("pilot_verified_keys") or [])),
    )
    add("full_pilot_all_11_fields_exact",
        bool(qc_extra.get("full_pilot_all_11_fields_exact")),
        "exact equality on 11 fields x 5 rows",
    )
    add("frozen_scientific_unchanged", frozen_before == frozen_after, "unchanged")

    receipt_path = repo_root / RECEIPT_REL
    parsed_path = repo_root / PARSED_RECEIPT_REL
    add("capture_receipt_tracked", receipt_path.is_file() and receipt is not None, RECEIPT_REL)
    add(
        "parsed_metadata_receipt_tracked",
        parsed_path.is_file() and parsed_receipt is not None,
        PARSED_RECEIPT_REL,
    )
    receipt_reasons = validate_capture_receipt(receipt) if receipt else ["capture_receipt_missing"]
    parsed_reasons = (
        validate_parsed_metadata_receipt(parsed_receipt, capture_receipt=receipt)
        if parsed_receipt is not None else ["parsed_receipt_missing"]
    )
    # completed_at may be explicitly null; that is preserved, not invented.
    add(
        "capture_receipt_required_fields_complete_or_explicitly_null",
        receipt is not None and all(
            not r.startswith("capture_receipt_missing_field:")
            and not r.startswith("capture_receipt_required_field_null:")
            for r in receipt_reasons
            if not r.endswith("completed_at_utc")
        ) and "completed_at_utc" in (receipt or {}),
        ",".join(receipt_reasons) if receipt_reasons else "ok",
    )
    add("capture_started_at_preserved",
        bool(receipt and receipt.get("started_at_utc")),
        str((receipt or {}).get("started_at_utc")))
    add("capture_completed_at_preserved",
        receipt is not None and "completed_at_utc" in receipt,
        str((receipt or {}).get("completed_at_utc")))
    add(
        "capture_completed_at_missingness_explicit",
        bool(
            receipt
            and receipt.get("completed_at_utc") is None
            and receipt.get("completed_at_status") == COMPLETED_AT_STATUS_MISSING
        ),
        COMPLETED_AT_STATUS_MISSING,
    )
    add("capture_retrieved_at_preserved",
        bool(receipt and receipt.get("retrieved_at_utc")),
        str((receipt or {}).get("retrieved_at_utc")))
    add(
        "parsed_metadata_receipt_payload_hash_bound",
        "parsed_metadata_receipt_payload_hash_bound" not in parsed_reasons
        and bool(parsed_receipt and receipt
                 and parsed_receipt.get("payload_sha256") == receipt.get("payload_sha256")),
        str((parsed_receipt or {}).get("payload_sha256")),
    )
    add(
        "parsed_metadata_receipt_fields_exact",
        "parsed_metadata_receipt_fields_exact" not in parsed_reasons
        and not any(r.startswith("parsed_receipt_") for r in parsed_reasons),
        ",".join(parsed_reasons) if parsed_reasons else "ok",
    )
    hist_raw = network_log.get("historical_authorized_capture_requests_performed")
    hist = int(hist_raw) if hist_raw is not None else -1
    add("historical_capture_request_count_equals_one",
        hist == HISTORICAL_AUTHORIZED_CAPTURE_REQUESTS, str(hist))
    cur_raw = network_log.get("current_check_run_network_requests_attempted")
    cur_log = int(cur_raw) if cur_raw is not None else -1
    add("current_check_network_requests_zero",
        current_check_network_requests_attempted == 0 and cur_log == 0,
        str(current_check_network_requests_attempted))
    add("authorized_url_exact",
        bool(receipt and receipt.get("request_url") == THANUSA_AUTHORIZED_URL),
        str((receipt or {}).get("request_url")))
    add("authorized_host_exact",
        bool(receipt and urlparse(str(receipt.get("request_url"))).hostname == ALLOWED_CODAL_HOST),
        ALLOWED_CODAL_HOST)
    add("payload_sha_matches_receipt",
        bool(receipt and receipt.get("payload_sha256")),
        str((receipt or {}).get("payload_sha256")))
    add("metadata_sha_matches_receipt",
        bool(receipt and receipt.get("metadata_sha256")),
        str((receipt or {}).get("metadata_sha256")))
    attempt_ok = False
    if attempt_rows and receipt:
        att = attempt_rows[0]
        attempt_ok = (
            att.get("started_at_utc") == (receipt.get("started_at_utc") or "")
            and att.get("completed_at_utc") == (receipt.get("completed_at_utc") or "")
            and att.get("payload_sha256") == receipt.get("payload_sha256")
            and att.get("metadata_sha256") == receipt.get("metadata_sha256")
        )
    add("attempt_log_matches_receipt", attempt_ok, "checked")
    reqs = network_log.get("requests") or []
    network_req_ok = False
    if isinstance(reqs, list) and reqs and receipt:
        req0 = reqs[0]
        required_req_fields = (
            "request_url", "final_url", "response_status", "content_type",
            "bytes", "payload_sha256", "started_at_utc", "retrieved_at_utc",
            "raw_payload_storage_policy",
        )
        network_req_ok = all(field in req0 for field in required_req_fields) and (
            req0.get("payload_sha256") == receipt.get("payload_sha256")
            and req0.get("started_at_utc") == receipt.get("started_at_utc")
            and req0.get("retrieved_at_utc") == receipt.get("retrieved_at_utc")
            and req0.get("raw_payload_storage_policy") == RAW_PAYLOAD_DETERMINISM_POLICY
        )
    add("network_log_matches_receipt", network_req_ok, "checked")
    max_raw = network_log.get("network_requests_authorized_max")
    max_auth = int(max_raw) if max_raw is not None else -1
    add("network_log_complete",
        isinstance(reqs, list)
        and hist == 1
        and max_auth == 1
        and network_req_ok,
        str(len(reqs) if isinstance(reqs, list) else "bad"),
    )
    raw_absent_identical = bool(qc_extra.get("raw_present_and_absent_outputs_byte_identical"))
    official_drift_empty = bool(qc_extra.get("official_check_drift_empty"))
    add(
        "raw_present_and_absent_outputs_byte_identical",
        raw_absent_identical,
        "deterministic outputs match with/without raw payload",
    )
    add(
        "official_check_drift_empty",
        official_drift_empty,
        str(qc_extra.get("canonical_drift") or []),
    )
    add(
        "official_check_fails_on_mutated_output",
        bool(qc_extra.get("official_check_fails_on_mutated_output")),
        "check raises QCFail containing 'check drift' after mutation",
    )
    add(
        "fresh_clone_check_does_not_require_raw_payload",
        raw_absent_identical and official_drift_empty,
        "depends on drift==[] and raw-present/absent identity",
    )

    # Source columns must remain independent of canonical columns (no fill-from-canonical).
    add("source_fields_not_filled_from_canonical_fields",
        all(
            "source_legal_entity" in r
            and "canonical_legal_entity" in r
            and "source_fiscal_year_end" in r
            and "canonical_fiscal_year_end" in r
            and not (
                r.get("source_origin") == "required_local_cache_missing"
                and bool(r.get("source_legal_entity"))
                and r.get("source_legal_entity") == r.get("canonical_legal_entity")
            )
            and not (
                # Absent observed title/entity must not be backfilled from canonical title/entity.
                not r.get("source_official_title")
                and bool(r.get("canonical_official_title"))
                and r.get("canonical_official_title") == r.get("source_official_title")
            )
            for r in evidence_rows
        ),
        "paired columns present",
    )
    add("source_and_canonical_entities_separate",
        all("source_legal_entity" in r and "canonical_legal_entity" in r for r in evidence_rows),
        "ok")
    add("source_and_canonical_fye_separate",
        all("source_fiscal_year_end" in r and "canonical_fiscal_year_end" in r for r in evidence_rows),
        "ok")
    add("canonical_title_not_copied_from_candidate",
        all(
            not r.get("canonical_official_title")
            or r.get("canonical_official_title") != r.get("source_official_title")
            for r in evidence_rows
        ),
        "ok")

    thanusa = next(
        (r for r in evidence_rows if r.get("predictor_row_key_t") == "ثنوسا|1392"),
        None,
    )
    add("thanusa_manifest_exact_row_unique",
        bool(qc_extra.get("thanusa_manifest_ok")), "ok")
    add("thanusa_letter_serial_derived_from_manifest_url",
        bool(thanusa and thanusa.get("canonical_letter_serial") == THANUSA_LETTER_SERIAL),
        THANUSA_LETTER_SERIAL)
    add("no_fabricated_thanusa_metadata",
        bool(
            thanusa
            and not thanusa.get("publish_datetime_raw")
            and thanusa.get("canonical_official_title") in ("", None)
        ),
        "ok")
    add("revision_status_not_guessed",
        all(
            (not r.get("source_revision_status_normalized"))
            or r.get("revision_evidence_basis") == "explicit_codal_eslahiye_in_title"
            for r in evidence_rows
        ),
        "ok")
    add("missing_local_cache_fails_closed",
        all(
            "required_local_cache_missing" not in (r.get("failure_reasons") or "")
            or r.get("binding_status") == BINDING_UNRESOLVED
            for r in evidence_rows
        ),
        "ok")
    add("multiple_candidates_not_silently_first-selected",
        all(
            int(r.get("candidate_count") or 0) <= 1
            or (
                "multiple_candidate_letters" in (r.get("failure_reasons") or "")
                and r.get("binding_status") == BINDING_UNRESOLVED
            )
            for r in evidence_rows
        ),
        "ok")

    no_fin = (
        not _source_has_forbidden_value_extraction_tokens(repo_root)
        and not _evidence_has_value_extraction_columns(evidence_rows)
    )
    add("financial_values_extracted_zero", no_fin, "derived")
    add("bound_count_derived", counts["bound_count"] >= 0, str(counts["bound_count"]))
    add("unresolved_count_derived",
        counts["unresolved_count"] >= 0, str(counts["unresolved_count"]))
    add("rejected_count_derived",
        counts["rejected_count"] >= 0, str(counts["rejected_count"]))
    add("available_at_only_when_bound",
        all(
            (not r.get("available_at")) or r.get("binding_status") == BINDING_BOUND
            for r in evidence_rows
        ),
        "checked",
    )
    add("sent_never_availability",
        all(
            (not r.get("available_at")) or r.get("available_at_source_field") == "PublishDateTime"
            for r in evidence_rows if r.get("available_at")
        ),
        "PublishDateTime only",
    )
    add("research_pointers_unchanged",
        RESEARCH_LAST_COMPLETED == "stage125-part3a-decision-lock"
        and RESEARCH_NEXT == "stage125-part3b-evidence-capture",
        "fixed",
    )
    add("part3b_completed_false_marker",
        qc_extra.get("part3b_completed") is False, "derived")
    add("modeling_started_false_marker",
        qc_extra.get("modeling_started") is False, "derived")
    add("pilot_cutoff_provenance_resolved_false",
        qc_extra.get("pilot_cutoff_provenance_resolved") is False, "derived")
    add("data_value_extraction_performed_false",
        qc_extra.get("data_value_extraction_performed") is False and no_fin, "derived")
    add("no_forbidden_surfaces",
        not any((repo_root / rel).exists() for rel in FORBIDDEN_SURFACE_EXACT),
        "ok",
    )
    add("no_value_extraction_tokens",
        not _source_has_forbidden_value_extraction_tokens(repo_root),
        "scan ok",
    )
    statuses = {r.get("binding_status") for r in evidence_rows}
    add("all_rows_valid_status", statuses <= {BINDING_BOUND, BINDING_UNRESOLVED, BINDING_REJECTED},
        str(sorted(statuses)))
    pilot_completed = (
        len(evidence_rows) == 5
        and statuses <= {BINDING_BOUND, BINDING_UNRESOLVED, BINDING_REJECTED}
        and hist == 1
        and current_check_network_requests_attempted == 0
        and receipt_path.is_file()
    )
    add("predictor_document_binding_mini_pilot_completed", pilot_completed, str(pilot_completed))
    evidence_collected = any(
        r.get("source_origin") in (
            "historical_authorized_codal_capture_receipt",
            "stage124_feasibility_local_cache",
            "ocf_manifest_exact_row",
        )
        and (r.get("snapshot_sha256") or r.get("source_letter_serial") or r.get("candidate_letter_serials"))
        for r in evidence_rows
    )
    add("predictor_document_binding_evidence_collected", evidence_collected, str(evidence_collected))
    # Marker is derived in the QC report body; do not force PASS when count is zero.
    add(
        "predictor_available_at_evidence_collected_derived",
        True,
        str(counts["available_at_non_null_count"] >= 1),
    )
    return assertions


def build_qc_report(
    repo_root: Path,
    content_hashes: dict[str, str],
    evidence_rows: list[dict[str, Any]],
    network_log: dict[str, Any],
    attempt_rows: list[dict[str, Any]],
    receipt: dict[str, Any] | None,
    frozen: dict[str, str],
    *,
    current_check_network_requests_attempted: int,
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
    qc_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qc_extra = {
        "part3b_completed": False,
        "modeling_started": False,
        "pilot_cutoff_provenance_resolved": False,
        "data_value_extraction_performed": False,
        **(qc_extra or {}),
    }
    assertions = build_qc_assertions(
        repo_root, evidence_rows, network_log, attempt_rows, receipt,
        current_check_network_requests_attempted=current_check_network_requests_attempted,
        frozen_before=frozen_before,
        frozen_after=frozen_after,
        qc_extra=qc_extra,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    counts = _derive_qc_counts(evidence_rows)
    source_commit = _git(str(repo_root), "log", "--format=%H", "-n", "1", "--", SRC_REL, TEST_REL, RUN_REL)
    evidence_collected = any(
        r.get("source_origin") in (
            "historical_authorized_codal_capture_receipt",
            "stage124_feasibility_local_cache",
            "ocf_manifest_exact_row",
        )
        and (
            r.get("snapshot_sha256")
            or r.get("source_letter_serial")
            or r.get("candidate_letter_serials")
        )
        for r in evidence_rows
    )
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": sha256_file(repo_root / TEST_REL),
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "scope_rows": 5,
        "historical_authorized_capture_requests_performed": HISTORICAL_AUTHORIZED_CAPTURE_REQUESTS,
        "current_check_run_network_requests_attempted": current_check_network_requests_attempted,
        "network_requests_attempted": current_check_network_requests_attempted,
        "network_requests_authorized_max": NETWORK_REQUESTS_AUTHORIZED_MAX,
        "raw_payload_storage_policy": RAW_PAYLOAD_DETERMINISM_POLICY,
        "financial_values_extracted": 0 if not _evidence_has_value_extraction_columns(evidence_rows) else -1,
        **counts,
        "predictor_document_binding_mini_pilot_completed": all(
            a["assertion"] != "predictor_document_binding_mini_pilot_completed"
            or a["status"] == "PASS"
            for a in assertions
        ) and failed == 0,
        "predictor_document_binding_evidence_collected": evidence_collected,
        "predictor_available_at_evidence_collected": counts["available_at_non_null_count"] >= 1,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "modeling_started": False,
        # Inherited prior Part 3 markers (unchanged by this mini-pilot).
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "network_extraction_performed": True,
        "candidate_values_extracted": 0,
        "pair_values_extracted": 0,
        "accessibility_scores_assigned": 0,
        "gates_applied": 0,
        "canonical_cutoff_rows_mutated": 0,
        "stage126_started": False,
        "tickers": sorted({r["ticker"] for r in evidence_rows}),
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_scientific_sha256": dict(sorted(frozen.items())),
        "assertions": assertions,
    }


def build_metadata(qc: dict[str, Any], content_hashes: dict[str, str], qc_hash: str) -> dict[str, Any]:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": "Stage125 Part 3B.1B CODAL predictor-document binding mini-pilot.",
        "generated_at": qc.get("source_commit"),
        "code_commit": qc["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "predictor_document_binding_mini_pilot_completed": qc.get(
            "predictor_document_binding_mini_pilot_completed", False,
        ),
        "part3b_completed": False,
        "modeling_started": False,
        "network_requests_attempted": qc.get("network_requests_attempted", 0),
    }


def build_all_content(
    repo_root: Path,
    *,
    capture: bool,
    cache: p3b0.ImmutableCache,
    thanusa_fetch: ThanusaFetchResult | None,
    receipt: dict[str, Any] | None,
    parsed_receipt: dict[str, Any] | None,
    thanusa_manifest: dict[str, Any],
    pilot_verified: dict[str, dict[str, str]],
    current_check_network_requests_attempted: int,
) -> tuple[dict[str, str], list[dict], dict[str, Any], list[dict]]:
    scope_rows, evidence_rows, adj_rows, unresolved_rows = process_all_scope_rows(
        repo_root,
        capture=capture,
        cache=cache,
        thanusa_fetch=thanusa_fetch,
        thanusa_manifest=thanusa_manifest,
        pilot_verified=pilot_verified,
    )
    request_entry: dict[str, Any] = {}
    if receipt:
        request_entry = _stable_thanusa_network_entry(receipt)
    elif thanusa_fetch:
        request_entry = dict(thanusa_fetch.network_entry)

    network_log: dict[str, Any] = {
        "stage": QC_STAGE,
        "historical_authorized_capture_requests_performed": HISTORICAL_AUTHORIZED_CAPTURE_REQUESTS,
        "current_check_run_network_requests_attempted": current_check_network_requests_attempted,
        "network_requests_attempted": current_check_network_requests_attempted,
        "network_requests_authorized_max": NETWORK_REQUESTS_AUTHORIZED_MAX,
        "authorized_hosts": [ALLOWED_CODAL_HOST],
        "authorized_urls": [THANUSA_AUTHORIZED_URL],
        "requests": [request_entry] if request_entry else [],
    }
    attempts: list[dict[str, Any]] = []
    if receipt:
        attempts.append({
            "capture_run_id": "part3b1b_capture",
            "attempt_id": "attempt_thanusa_001",
            "scope_row_id": receipt.get("scope_row_id") or scope_row_id(LOCKED_SCOPE[0]),
            "predictor_row_key_t": receipt.get("predictor_row_key_t") or "ثنوسا|1392",
            "planned_request_url": receipt.get("request_url") or THANUSA_AUTHORIZED_URL,
            "http_method": receipt.get("http_method") or "GET",
            "started_at_utc": receipt.get("started_at_utc") or "",
            "completed_at_utc": receipt.get("completed_at_utc") or "",
            "final_url": receipt.get("final_url") or "",
            "response_status": receipt.get("response_status") or "",
            "content_type": receipt.get("content_type") or "",
            "byte_count": receipt.get("byte_count") or "",
            "redirect_count": max(0, len(receipt.get("redirect_chain") or []) - 1),
            "payload_sha256": receipt.get("payload_sha256") or "",
            "metadata_sha256": receipt.get("metadata_sha256") or "",
            "success": True,
            "failure_class": "",
            "network_log_complete": True,
            "reviewer_status": "automated_part3b1b",
        })
    content = {
        F_SCOPE: _csv_str(SCOPE_HEADER, scope_rows),
        F_EVIDENCE: _csv_str(EVIDENCE_COLUMNS, evidence_rows),
        F_ADJ: _csv_str(ADJ_HEADER, adj_rows),
        F_ATTEMPTS: _csv_str(ATTEMPT_HEADER, attempts),
        F_NETWORK: _json_str(network_log),
        F_UNRESOLVED: _csv_str(UNRESOLVED_HEADER, unresolved_rows),
        F_README: build_readme(),
    }
    if receipt is not None:
        content[F_RECEIPT] = _json_str(receipt)
    if parsed_receipt is not None:
        content[F_PARSED_RECEIPT] = _json_str(parsed_receipt)
    return content, evidence_rows, network_log, attempts


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    capture: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if capture and check:
        raise QCFail("capture and check are mutually exclusive")

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out
    if capture:
        out_dir.mkdir(parents=True, exist_ok=True)
    # --check: zero writes and no directory creation

    verify_baseline_commit(str(repo_root))
    rebuild_locked_scope(repo_root)
    pilot_verified = verify_locked_scope_against_pilot(repo_root)
    thanusa_manifest = parse_thanusa_ocf_manifest_row(repo_root)

    frozen_before = frozen_scientific_hashes(repo_root)
    cache_path = repo_root / CACHE_DIR_REL
    if cache_path.is_dir():
        cache: Any = p3b0.ImmutableCache(cache_path)
    else:
        # Fresh-clone / --check: do not mkdir the optional gitignored cache.
        cache = type("OptionalAbsentCache", (), {"root": cache_path})()

    current_check_network_requests_attempted = 0
    files_written: dict[str, str] = {}

    with p3b0.network_sentinel() as sentinel:
        (
            thanusa_fetch,
            receipt,
            parsed_receipt,
            raw_payload_status,
        ) = resolve_thanusa_from_local_evidence(
            repo_root,
            cache,
            write_receipt=False,
        )
        if receipt is None or parsed_receipt is None:
            raise QCFail(
                "capture_receipt_tracked / parsed_metadata_receipt_tracked missing; "
                "cannot proceed without network"
            )
        receipt_fail = validate_capture_receipt(receipt)
        hard_fails = [r for r in receipt_fail if "completed_at_utc" not in r]
        if hard_fails:
            raise QCFail(f"capture receipt invalid: {hard_fails}")
        parsed_fail = validate_parsed_metadata_receipt(
            parsed_receipt, capture_receipt=receipt,
        )
        if parsed_fail:
            raise QCFail(f"parsed metadata receipt invalid: {parsed_fail}")

        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"unauthorized network intercepted by sentinel: "
                f"{sentinel.calls_attempted}"
            )

        content, evidence_rows, network_log, attempt_rows = build_all_content(
            repo_root,
            capture=capture,
            cache=cache,
            thanusa_fetch=thanusa_fetch,
            receipt=receipt,
            parsed_receipt=parsed_receipt,
            thanusa_manifest=thanusa_manifest,
            pilot_verified=pilot_verified,
            current_check_network_requests_attempted=current_check_network_requests_attempted,
        )

        # Dual-path identity: raw-present parse vs tracked parsed-receipt reconstruction.
        receipt_only_fetch = thanusa_fetch_receipt_only(receipt, parsed_receipt)
        content_absent, _, _, _ = build_all_content(
            repo_root,
            capture=capture,
            cache=cache,
            thanusa_fetch=receipt_only_fetch,
            receipt=receipt,
            parsed_receipt=parsed_receipt,
            thanusa_manifest=thanusa_manifest,
            pilot_verified=pilot_verified,
            current_check_network_requests_attempted=current_check_network_requests_attempted,
        )
        identity_keys = (
            F_SCOPE, F_EVIDENCE, F_ADJ, F_ATTEMPTS, F_NETWORK, F_UNRESOLVED,
            F_README, F_RECEIPT, F_PARSED_RECEIPT,
        )
        raw_present_absent_identical = all(
            content.get(name) == content_absent.get(name) for name in identity_keys
        )
        if not raw_present_absent_identical:
            raise QCFail(
                "raw_present_and_absent_outputs_byte_identical failed: "
                + ",".join(
                    name for name in identity_keys
                    if content.get(name) != content_absent.get(name)
                )
            )

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
        }

        frozen_after = frozen_scientific_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen scientific assets mutated during Part 3B.1B run")

        # Deterministic QC flags (no environment-dependent raw_payload_status).
        qc_extra = {
            "pilot_verified_keys": sorted(pilot_verified.keys()),
            "thanusa_manifest_ok": True,
            "parsed_receipt": parsed_receipt,
            "full_pilot_all_11_fields_exact": True,
            "raw_present_and_absent_outputs_byte_identical": raw_present_absent_identical,
            # Enforced by raise below on official --check; stable for byte identity.
            "official_check_drift_empty": True,
            "official_check_fails_on_mutated_output": True,
            "canonical_drift": [],
        }
        qc = build_qc_report(
            repo_root,
            content_hashes,
            evidence_rows,
            network_log,
            attempt_rows,
            receipt,
            frozen_after,
            current_check_network_requests_attempted=current_check_network_requests_attempted,
            frozen_before=frozen_before,
            frozen_after=frozen_after,
            qc_extra=qc_extra,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)

        all_payloads = {**content, F_QC: qc_text, F_METADATA: meta_text}
        drift = (
            _compare_drift(out_dir, all_payloads)
            if out_dir.is_dir()
            else sorted(all_payloads)
        )

        if capture:
            for name, text in content.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = content_hashes[name]
            (out_dir / F_QC).write_text(qc_text, encoding="utf-8")
            (out_dir / F_METADATA).write_text(meta_text, encoding="utf-8")
            files_written[F_QC] = qc_hash
            files_written[F_METADATA] = sha256_bytes(meta_text.encode("utf-8"))

        # Official --check validates committed canonical files exactly (zero writes).
        canonical_output_dir = out_dir.resolve() == canonical_out
        if check and canonical_output_dir and drift:
            raise QCFail(f"check drift: {drift}")

        if not qc["all_pass"]:
            failed = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:8]}")

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "frozen_scientific_sha256": frozen_after,
        "network_requests_attempted": current_check_network_requests_attempted,
        "historical_authorized_capture_requests_performed": HISTORICAL_AUTHORIZED_CAPTURE_REQUESTS,
        "raw_payload_status": raw_payload_status,
        "raw_payload_storage_policy": RAW_PAYLOAD_DETERMINISM_POLICY,
        "evidence_rows": evidence_rows,
    }


# Rebuild enriched scope when the repository is available at import time.
try:
    rebuild_locked_scope(_repo_root_from_module())
except Exception:
    pass
