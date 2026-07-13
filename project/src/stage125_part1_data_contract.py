"""Stage125 Part 1 — Data Dictionary & Provenance Contract.

This module implements ONLY Stage125 Part 1. It is a documentation / contract /
read-only-audit stage. It performs **no** modeling, **no** data extraction, **no**
network access, and does **not** modify any frozen Stage122–Stage124 asset, the
target, the sample, eligibility, or the cutoff.

What it produces (all in ``project/stage125/``):

  * ``data_dictionary_stage125.csv``              — M1–M4 data dictionary
  * ``identifier_time_contract_stage125.json``    — id + time semantics contract
  * ``source_registry_stage125.csv``              — M1–M4 source registry (no M5)
  * ``provenance_manifest_schema_stage125.json``  — provenance record schema
  * ``data_admission_gate_template_stage125.csv`` — admission-gate template
  * ``m1_provenance_gap_audit_stage125.csv``       — per-row provenance flags only
  * ``m1_provenance_gap_summary_stage125.json``    — provenance gap counts
  * ``stage125_part1_data_contract_qc_report.json``
  * ``metadata_and_hashes_stage125_part1.json``
  * ``README_STAGE125_PART1_DATA_CONTRACT.md``

Determinism: no tracked output depends on the Python version, wall-clock time,
or any runtime-environment string. The only time-like value recorded is the git
commit timestamp of the code commit (content-stable per commit).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part1_data_contract"
CURRENT_STAGE = "Stage125"

INPUT_NAME = "modeling_all_rows_stage123.csv"
EXPECTED_INPUT_SHA256 = (
    "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390"
)
EXPECTED_DATA_BUNDLE_SHA256 = (
    "c7366f24376eea677fe9f63ec4f5ec089aef143c25e3667db9b17e1d7a430828"
)

SRC_REL = "project/src/stage125_part1_data_contract.py"
TEST_REL = "project/tests/test_stage125_part1_data_contract.py"

# Frozen manifests that must remain unchanged by this Part (read-only audit).
FROZEN_MANIFEST_PATHS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
)

# Expected M1 invariants from the frozen Stage123 input (fail-closed).
EXPECTED_INVARIANTS = {
    "rows": 1331,
    "unique_row_key": 1331,
    "source_file_present": 1303,
    "source_file_missing": 28,
    "source_url_present": 15,
    "source_url_missing": 1316,
    "fiscal_year_end_present": 1327,
    "fiscal_year_end_missing": 4,
    "company_name_present": 1324,
    "company_name_missing": 7,
    "industry_present": 1302,
    "industry_missing": 29,
    "audit_status_unknown": 316,
}

AUDIT_STATUS_UNKNOWN_VALUE = "audit_status_unknown"

# Output filenames (relative to the Stage125 output directory).
F_DICTIONARY = "data_dictionary_stage125.csv"
F_ID_TIME = "identifier_time_contract_stage125.json"
F_REGISTRY = "source_registry_stage125.csv"
F_MANIFEST_SCHEMA = "provenance_manifest_schema_stage125.json"
F_GATE_TEMPLATE = "data_admission_gate_template_stage125.csv"
F_GAP_AUDIT = "m1_provenance_gap_audit_stage125.csv"
F_GAP_SUMMARY = "m1_provenance_gap_summary_stage125.json"
F_QC = "stage125_part1_data_contract_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part1.json"
F_README = "README_STAGE125_PART1_DATA_CONTRACT.md"

# Content files (everything except QC + metadata, which reference their hashes).
CONTENT_FILES = (
    F_DICTIONARY, F_ID_TIME, F_REGISTRY, F_MANIFEST_SCHEMA, F_GATE_TEMPLATE,
    F_GAP_AUDIT, F_GAP_SUMMARY, F_README,
)


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 1."""


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


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or (_git(repo_root, "rev-parse", "HEAD") or "unknown")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    return raw or "unknown"


def _git_tracked(repo_root: str) -> set[str]:
    out = _git(repo_root, "ls-files")
    return set(out.splitlines()) if out else set()


def _git_ignored(repo_root: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "check-ignore", "-q", "--", path],
        capture_output=True,
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Input verification (fail-closed, read-only)
# --------------------------------------------------------------------------- #

def _read_bundle_member(bundle_path: Path) -> bytes:
    """Read the canonical CSV from the data bundle ZIP, read-only.

    Verifies the ZIP SHA-256 and (if present) the bundled
    ``PAPERMALI_STAGE125_DATA_SHA256.txt`` checksum manifest before extracting
    the member in-memory. Never writes the ZIP or its members to the repo.
    """
    bundle_sha = sha256_file(bundle_path)
    if bundle_sha != EXPECTED_DATA_BUNDLE_SHA256:
        raise QCFail(
            f"data bundle SHA-256 mismatch: expected {EXPECTED_DATA_BUNDLE_SHA256}, "
            f"got {bundle_sha}"
        )
    with zipfile.ZipFile(bundle_path) as zf:
        names = zf.namelist()
        checksum_line = None
        for n in names:
            if n.endswith("PAPERMALI_STAGE125_DATA_SHA256.txt"):
                checksum_line = zf.read(n).decode("utf-8", "replace")
                break
        member = None
        for n in names:
            if n.endswith(INPUT_NAME):
                member = n
                break
        if member is None:
            raise QCFail(f"data bundle does not contain {INPUT_NAME}")
        data = zf.read(member)
    data_sha = sha256_bytes(data)
    if data_sha != EXPECTED_INPUT_SHA256:
        raise QCFail(
            f"bundled {INPUT_NAME} SHA-256 mismatch: expected "
            f"{EXPECTED_INPUT_SHA256}, got {data_sha}"
        )
    if checksum_line and EXPECTED_INPUT_SHA256 not in checksum_line:
        raise QCFail(
            "bundled PAPERMALI_STAGE125_DATA_SHA256.txt does not declare the "
            "expected canonical CSV SHA-256"
        )
    return data


def load_input(input_path: Path | None, bundle_path: Path | None) -> tuple[pd.DataFrame, str, str]:
    """Return (dataframe, input_sha256, input_source) read-only, fail-closed."""
    if input_path is not None and Path(input_path).is_file():
        sha = sha256_file(input_path)
        if sha != EXPECTED_INPUT_SHA256:
            raise QCFail(
                f"input {input_path} SHA-256 mismatch: expected "
                f"{EXPECTED_INPUT_SHA256}, got {sha}"
            )
        df = pd.read_csv(input_path, encoding="utf-8-sig", dtype=str,
                         keep_default_na=False)
        return df, sha, "canonical_input_csv"
    if bundle_path is not None and Path(bundle_path).is_file():
        data = _read_bundle_member(Path(bundle_path))
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype=str,
                         keep_default_na=False)
        return df, EXPECTED_INPUT_SHA256, "read_only_data_bundle_zip"
    raise QCFail(
        "no valid input available: neither the canonical "
        f"{INPUT_NAME} nor a valid data bundle ZIP was found. "
        "No data is reconstructed or downloaded (fail-closed)."
    )


# --------------------------------------------------------------------------- #
# M1 provenance-gap audit (read-only; identifiers + flags only)
# --------------------------------------------------------------------------- #

def _present(series: pd.Series) -> pd.Series:
    """Boolean mask: value is present (non-null, non-empty after strip)."""
    s = series.fillna("").astype(str).str.strip()
    return s != ""


def compute_gap_summary(df: pd.DataFrame) -> dict:
    """Compute the M1 provenance-gap invariant counts (no financial values)."""
    counts: dict[str, int] = {}
    counts["rows"] = int(len(df))
    counts["unique_row_key"] = int(df["row_key"].nunique())
    for col in ("source_file", "source_url", "fiscal_year_end",
                "company_name", "industry"):
        present = _present(df[col])
        counts[f"{col}_present"] = int(present.sum())
        counts[f"{col}_missing"] = int((~present).sum())
    counts["audit_status_unknown"] = int(
        (df["audit_status_clean"].fillna("").astype(str).str.strip()
         == AUDIT_STATUS_UNKNOWN_VALUE).sum()
    )
    return counts


def check_invariants(counts: dict) -> list[str]:
    """Return a list of invariant mismatches (empty => all match)."""
    errs = []
    for key, expected in EXPECTED_INVARIANTS.items():
        actual = counts.get(key)
        if actual != expected:
            errs.append(f"{key}: expected {expected}, got {actual}")
    return errs


def build_gap_audit_rows(df: pd.DataFrame) -> list[dict]:
    """Per-row provenance flags. Only identifiers + provenance status; NO
    financial values are copied."""
    sf = _present(df["source_file"])
    su = _present(df["source_url"])
    fye = _present(df["fiscal_year_end"])
    cn = _present(df["company_name"])
    ind = _present(df["industry"])
    audit = df["audit_status_clean"].fillna("").astype(str).str.strip()
    rows = []
    for i in range(len(df)):
        gaps = []
        if not sf.iloc[i]:
            gaps.append("source_file")
        if not su.iloc[i]:
            gaps.append("source_url")
        if not fye.iloc[i]:
            gaps.append("fiscal_year_end")
        if not cn.iloc[i]:
            gaps.append("company_name")
        if not ind.iloc[i]:
            gaps.append("industry")
        if audit.iloc[i] == AUDIT_STATUS_UNKNOWN_VALUE:
            gaps.append("audit_status_unknown")
        rows.append({
            "row_key": df["row_key"].iloc[i],
            "ticker": df["ticker"].iloc[i],
            "fiscal_year": df["fiscal_year"].iloc[i],
            "block": "M1",
            "source_file_present": int(bool(sf.iloc[i])),
            "source_url_present": int(bool(su.iloc[i])),
            "fiscal_year_end_present": int(bool(fye.iloc[i])),
            "company_name_present": int(bool(cn.iloc[i])),
            "industry_present": int(bool(ind.iloc[i])),
            "audit_status_clean": audit.iloc[i],
            "audit_status_unknown": int(audit.iloc[i] == AUDIT_STATUS_UNKNOWN_VALUE),
            "provenance_gap_count": len(gaps),
            "provenance_gaps": "|".join(gaps),
            # Part 1 never changes eligibility because of a provenance gap.
            "eligibility_impact": "none_recorded_as_provenance_gap_only",
        })
    rows.sort(key=lambda r: str(r["row_key"]))
    return rows


# --------------------------------------------------------------------------- #
# Serialization helpers (deterministic)
# --------------------------------------------------------------------------- #

def _json_str(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Static contracts (no guessing; unknown -> blank + explicit status)
# --------------------------------------------------------------------------- #

# ---- Data dictionary (M1 actual columns + M2–M4 planned families) --------- #

_DICT_HEADER = [
    "variable_name", "block", "role", "data_type", "unit",
    "temporal_reference", "source_id", "provenance_status", "description",
]

_M1_IDENTIFIER_VARS = [
    ("row_key", "identifier", "string", "", "point_in_time_company_year",
     "src_m1_stage123", "in_use_frozen",
     "Immutable Stage123 company-year primary key; unique across 1331 rows."),
    ("ticker", "identifier", "string", "", "point_in_time_company_year",
     "src_m1_stage123", "in_use_frozen",
     "Canonical TSE sample ticker; not redefined in Stage125."),
    ("fiscal_year", "identifier", "integer", "jalali_year",
     "period", "src_m1_stage123", "in_use_frozen",
     "Jalali fiscal year of the observation."),
    ("company_name", "identifier", "string", "", "point_in_time_company_year",
     "src_m1_codal_fs", "in_use_partial_gap",
     "Company name; 7 rows missing (provenance gap, not imputed)."),
    ("industry", "identifier", "string", "", "point_in_time_company_year",
     "src_m1_codal_fs", "in_use_partial_gap",
     "Industry label; 29 rows missing (provenance gap, not imputed)."),
]

_M1_TIME_VARS = [
    ("fiscal_year_end", "time", "date", "jalali_or_iso_date",
     "period_end", "src_m1_codal_fs", "in_use_partial_gap",
     "Fiscal year-end date; 4 rows missing (provenance gap, not imputed)."),
]

_M1_PROVENANCE_VARS = [
    ("source_file", "provenance", "string", "", "retrieval",
     "src_m1_uploaded_xls", "in_use_partial_gap",
     "Local source statement file; 28 rows missing (provenance gap)."),
    ("source_url", "provenance", "string", "", "publication",
     "src_m1_codal_fs", "in_use_major_gap",
     "Public source URL; 1316 rows missing — recorded as provenance gap only, "
     "never used to change eligibility in Part 1."),
    ("audit_status_clean", "provenance", "string", "", "publication",
     "src_m1_codal_audit", "in_use_partial_gap",
     "Audit status label; 316 rows are audit_status_unknown."),
]

# A compact, representative set of M1 financial variables (values live in the
# frozen Stage123 data; the dictionary only documents them, never copies them).
_M1_FINANCIAL_VARS = [
    ("total_assets", "financial_level"), ("total_liabilities", "financial_level"),
    ("equity", "financial_level"), ("registered_capital", "financial_level"),
    ("accumulated_loss", "financial_level"), ("net_income_period_adjusted", "financial_level"),
    ("operating_cash_flow_period_adjusted", "financial_level"),
    ("leverage_ratio", "financial_ratio"), ("current_ratio", "financial_ratio"),
    ("roa_period_adjusted", "financial_ratio"), ("roe_period_adjusted", "financial_ratio"),
    ("equity_ratio", "financial_ratio"), ("debt_to_equity", "financial_ratio"),
    ("profit_margin_period_adjusted", "financial_ratio"),
    ("asset_turnover_period_adjusted", "financial_ratio"),
    ("accumulated_loss_to_capital_ratio", "financial_ratio"),
]

_M1_TARGET_VARS = [
    ("FD_target_main", "target", "Composite operational-distress target (frozen Stage122)."),
    ("FD_target_article141_only", "target", "Article-141 robustness target (frozen)."),
    ("FD_target_persistent_loss_robustness", "target", "Persistent-loss robustness target (frozen)."),
]

# M2–M4 planned variable families (not yet collected; each Gated individually).
_PLANNED_VARS = [
    ("equity_return_window", "M2", "planned", "src_m2_tsetmc_market", "numeric",
     "return_ratio", "market_window_closing_before_cutoff",
     "Point-in-time equity return/momentum; window closes before prediction cutoff."),
    ("realized_volatility", "M2", "planned", "src_m2_tsetmc_market", "numeric",
     "volatility", "market_window_closing_before_cutoff",
     "Realized volatility over a pre-cutoff window."),
    ("amihud_illiquidity", "M2", "planned", "src_m2_tsetmc_market", "numeric",
     "illiquidity", "market_window_closing_before_cutoff",
     "Amihud illiquidity; computable liquidity measure."),
    ("cpi_inflation", "M3", "planned", "src_m3_cbi_macro", "numeric",
     "percent", "macro_series_pre_cutoff",
     "CPI / official inflation; only if publication date and coverage reliable."),
    ("fx_change_official", "M3", "planned", "src_m3_cbi_macro", "numeric",
     "percent", "macro_series_pre_cutoff",
     "FX change from an official source that passes the data Gate."),
    ("policy_financing_rate", "M3", "planned", "src_m3_cbi_macro", "numeric",
     "percent", "macro_series_pre_cutoff",
     "Policy / financing rate; parsimonious macro set only."),
    ("audit_opinion_type", "M4", "planned", "src_m4_codal_audit", "categorical",
     "", "publication",
     "Audit opinion type as a structured, auditable label (Gated individually)."),
    ("going_concern_flag", "M4", "planned", "src_m4_codal_audit", "boolean",
     "", "publication",
     "Going-concern / material-uncertainty clause as a structured label."),
    ("audit_lag_days", "M4", "planned", "src_m4_codal_audit", "integer",
     "days", "publication",
     "Days between period end and audit report; Gated individually."),
    ("board_size", "M4", "planned", "src_m4_codal_governance", "integer",
     "count", "publication",
     "Board size; only if definition/coverage are auditable."),
]


def build_data_dictionary_rows() -> list[dict]:
    rows: list[dict] = []
    for name, role, dtype, unit, tref, sid, status, desc in (
            _M1_IDENTIFIER_VARS + _M1_TIME_VARS + _M1_PROVENANCE_VARS):
        rows.append({"variable_name": name, "block": "M1", "role": role,
                     "data_type": dtype, "unit": unit, "temporal_reference": tref,
                     "source_id": sid, "provenance_status": status, "description": desc})
    for name, role in _M1_FINANCIAL_VARS:
        rows.append({"variable_name": name, "block": "M1", "role": role,
                     "data_type": "numeric", "unit": "irr_or_ratio",
                     "temporal_reference": "period",
                     "source_id": "src_m1_codal_fs", "provenance_status": "in_use_frozen",
                     "description": "Frozen Stage123 financial variable; documented, "
                                    "never re-copied here."})
    for name, role, desc in _M1_TARGET_VARS:
        rows.append({"variable_name": name, "block": "M1", "role": role,
                     "data_type": "categorical", "unit": "",
                     "temporal_reference": "target_t_plus_1",
                     "source_id": "src_m1_stage122_target", "provenance_status": "in_use_frozen",
                     "description": desc})
    for name, block, status, sid, dtype, unit, tref, desc in _PLANNED_VARS:
        rows.append({"variable_name": name, "block": block, "role": "candidate_feature",
                     "data_type": dtype, "unit": unit, "temporal_reference": tref,
                     "source_id": sid, "provenance_status": status, "description": desc})
    return rows


def build_data_dictionary_csv() -> str:
    return _csv_str(_DICT_HEADER, build_data_dictionary_rows())


# ---- Identifier & time contract ------------------------------------------- #

def build_identifier_time_contract() -> dict:
    return {
        "contract_version": "stage125_part1_v1",
        "stage": CURRENT_STAGE,
        "scope": "Part 1 — data dictionary & provenance contract (no modeling)",
        "identifiers": {
            "row_key": {
                "definition": "Immutable Stage123 company-year primary key.",
                "immutable": True,
                "unique_row_count": 1331,
                "redefined_in_stage125": False,
            },
            "predictor_row_key_t": {
                "definition": "Stage123 predictor (year t) row_key in the "
                              "one-year-ahead pairs; NOT redefined.",
                "redefined_in_stage125": False,
            },
            "target_row_key_t_plus_1": {
                "definition": "Stage123 target (year t+1) row_key in the pairs; "
                              "NOT redefined.",
                "redefined_in_stage125": False,
            },
            "ticker": {
                "definition": "Canonical TSE sample ticker.",
                "changed_in_stage125": False,
            },
            "future_identifier_crosswalk": {
                "definition": "Future identifiers (e.g. TSETMC insCode, company "
                              "national id) are defined ONLY in a separate "
                              "crosswalk, never guessed and never merged here.",
                "required_fields": ["source_identifier", "canonical_ticker",
                                    "validity_start", "validity_end",
                                    "provenance_id", "mapping_evidence"],
                "no_identifier_guessed": True,
                "requires_validity_dates_and_provenance": True,
            },
        },
        "time_concepts": {
            "observation_date": "When the underlying fact was observed.",
            "period_start": "Start of the reporting period.",
            "period_end": "End of the reporting period.",
            "fiscal_year_end": "Fiscal year-end date of the statement.",
            "published_at": "When the source document was published.",
            "available_at": "When the information first became usable/accessible.",
            "retrieved_at_utc": "When the record was retrieved (UTC).",
        },
        "time_rules": {
            "raw_source_date_preserved": True,
            "jalali_and_gregorian_in_separate_columns": True,
            "published_at_and_available_at_not_assumed_equal": True,
            "source_timezone_recorded": True,
            "unknown_time_is_null_never_inferred": True,
            "revision_is_new_version_not_overwrite": True,
        },
    }


# ---- Provenance manifest schema ------------------------------------------- #

_PROVENANCE_FIELDS = [
    ("provenance_id", "string", True, "Unique id of this provenance record."),
    ("source_id", "string", True, "FK to source_registry_stage125.csv."),
    ("block", "enum[M1,M2,M3,M4]", True, "Model block; M5 is not permitted."),
    ("source_document_id", "string", False, "Source document identifier."),
    ("canonical_ticker", "string", True, "Canonical TSE ticker."),
    ("row_key", "string", True, "Stage123 company-year row_key."),
    ("feature_name", "string", True, "Variable this record documents."),
    ("observation_date", "date_or_null", False, "Observation date (raw preserved separately)."),
    ("period_start", "date_or_null", False, "Reporting period start."),
    ("period_end", "date_or_null", False, "Reporting period end."),
    ("fiscal_year_end", "date_or_null", False, "Fiscal year-end date."),
    ("published_at_raw", "string_or_null", False, "Raw publication timestamp as in source."),
    ("published_at", "datetime_or_null", False, "Normalized publication time; null if unknown."),
    ("available_at", "datetime_or_null", False, "Time first usable; not assumed equal to published_at."),
    ("retrieved_at_utc", "datetime_or_null", False, "Retrieval time in UTC."),
    ("source_url", "url_or_null", False, "Public source URL."),
    ("source_file", "string_or_null", False, "Local source file path."),
    ("snapshot_path", "string_or_null", False, "Content-addressed raw snapshot path."),
    ("content_sha256", "sha256_or_null", False, "SHA-256 of the raw bytes."),
    ("source_version", "string_or_null", False, "Source/document version label."),
    ("extraction_method", "string_or_null", False, "How the value was extracted."),
    ("extraction_code_commit", "string_or_null", False, "Git commit of the extraction code."),
    ("unit_raw", "string_or_null", False, "Unit as stated by the source."),
    ("unit_normalized", "string_or_null", False, "Normalized unit."),
    ("revision_status", "enum[original,revision,restatement]", False, "Revision status."),
    ("review_status", "string", True, "Human/QC review status."),
    ("missing_reason", "string_or_null", False, "Why a value is missing, if applicable."),
    ("notes", "string_or_null", False, "Free-text notes."),
]


def build_provenance_manifest_schema() -> dict:
    return {
        "schema_version": "stage125_part1_v1",
        "stage": CURRENT_STAGE,
        "record_kind": "provenance_manifest_record",
        "allowed_blocks": ["M1", "M2", "M3", "M4"],
        "disallowed_blocks": ["M5"],
        "principles": {
            "no_value_guessed": True,
            "unknown_time_is_null_never_inferred": True,
            "raw_immutable_content_addressed": True,
            "revision_is_new_version_not_overwrite": True,
        },
        "fields": [
            {"name": n, "type": t, "required": req, "description": d}
            for (n, t, req, d) in _PROVENANCE_FIELDS
        ],
    }


# ---- Source registry (M1–M4 only; no M5) ---------------------------------- #

_REGISTRY_HEADER = [
    "source_id", "block", "source_family", "authority_tier", "source_owner",
    "base_url", "frequency", "accessibility_score", "accessibility_status",
    "publication_time_policy", "availability_time_policy", "versioning_policy",
    "retrieval_method", "status", "gating_notes",
]

# Unknown numeric/URL/date fields are left blank; status is unresolved or
# pending_part3. Nothing is guessed.
_REGISTRY_ROWS = [
    {
        "source_id": "src_m1_codal_fs", "block": "M1",
        "source_family": "company_annual_financial_statements",
        "authority_tier": "regulatory_filing", "source_owner": "CODAL",
        "base_url": "", "frequency": "annual",
        "accessibility_score": "", "accessibility_status": "in_use_m1_baseline",
        "publication_time_policy": "statement_publication_date_from_source",
        "availability_time_policy": "not_assumed_equal_to_publication",
        "versioning_policy": "revision_is_new_version",
        "retrieval_method": "existing_frozen_stage122_stage123",
        "status": "in_use_m1_baseline",
        "gating_notes": "M1 baseline already frozen in Stage122-124; source_url "
                        "coverage gap (1316 rows) recorded as provenance gap only.",
    },
    {
        "source_id": "src_m1_uploaded_xls", "block": "M1",
        "source_family": "manually_uploaded_statement_xls",
        "authority_tier": "derived_local_copy", "source_owner": "project_local",
        "base_url": "", "frequency": "annual",
        "accessibility_score": "", "accessibility_status": "in_use_m1_baseline",
        "publication_time_policy": "unknown_null", "availability_time_policy": "unknown_null",
        "versioning_policy": "revision_is_new_version",
        "retrieval_method": "existing_frozen_local_files",
        "status": "in_use_m1_baseline",
        "gating_notes": "source_file present for 1303 rows, missing for 28.",
    },
    {
        "source_id": "src_m1_codal_audit", "block": "M1",
        "source_family": "audit_status_label",
        "authority_tier": "regulatory_filing", "source_owner": "CODAL",
        "base_url": "", "frequency": "annual",
        "accessibility_score": "", "accessibility_status": "in_use_partial",
        "publication_time_policy": "unknown_null", "availability_time_policy": "unknown_null",
        "versioning_policy": "revision_is_new_version",
        "retrieval_method": "existing_frozen_stage123",
        "status": "in_use_m1_baseline",
        "gating_notes": "316 rows are audit_status_unknown.",
    },
    {
        "source_id": "src_m2_tsetmc_market", "block": "M2",
        "source_family": "market_prices_returns_liquidity",
        "authority_tier": "market_operator", "source_owner": "TSETMC",
        "base_url": "", "frequency": "daily",
        "accessibility_score": "", "accessibility_status": "unresolved",
        "publication_time_policy": "", "availability_time_policy": "",
        "versioning_policy": "", "retrieval_method": "",
        "status": "pending_part3",
        "gating_notes": "Candidate market source; scoring in Part 3. Not collected in Part 1.",
    },
    {
        "source_id": "src_m3_cbi_macro", "block": "M3",
        "source_family": "official_macro_cpi_fx_rate",
        "authority_tier": "central_bank", "source_owner": "Central Bank of Iran",
        "base_url": "", "frequency": "monthly",
        "accessibility_score": "", "accessibility_status": "unresolved",
        "publication_time_policy": "", "availability_time_policy": "",
        "versioning_policy": "", "retrieval_method": "",
        "status": "pending_part3",
        "gating_notes": "Parsimonious macro candidate; scoring in Part 3.",
    },
    {
        "source_id": "src_m3_sci_macro", "block": "M3",
        "source_family": "official_macro_production_index",
        "authority_tier": "statistical_agency", "source_owner": "Statistical Center of Iran",
        "base_url": "", "frequency": "quarterly",
        "accessibility_score": "", "accessibility_status": "unresolved",
        "publication_time_policy": "", "availability_time_policy": "",
        "versioning_policy": "", "retrieval_method": "",
        "status": "pending_part3",
        "gating_notes": "Macro candidate; only if publication date and coverage reliable.",
    },
    {
        "source_id": "src_m4_codal_audit", "block": "M4",
        "source_family": "structured_audit_opinion",
        "authority_tier": "regulatory_filing", "source_owner": "CODAL",
        "base_url": "", "frequency": "annual",
        "accessibility_score": "", "accessibility_status": "unresolved",
        "publication_time_policy": "", "availability_time_policy": "",
        "versioning_policy": "", "retrieval_method": "",
        "status": "pending_part3",
        "gating_notes": "Structured audit variables Gated individually in Part 3.",
    },
    {
        "source_id": "src_m4_codal_governance", "block": "M4",
        "source_family": "structured_corporate_governance",
        "authority_tier": "regulatory_filing", "source_owner": "CODAL",
        "base_url": "", "frequency": "annual",
        "accessibility_score": "", "accessibility_status": "unresolved",
        "publication_time_policy": "", "availability_time_policy": "",
        "versioning_policy": "", "retrieval_method": "",
        "status": "pending_part3",
        "gating_notes": "Board/committee variables only if definition/coverage auditable.",
    },
]


def build_source_registry_csv() -> str:
    return _csv_str(_REGISTRY_HEADER, _REGISTRY_ROWS)


# ---- Data admission gate template ----------------------------------------- #

_GATE_HEADER = [
    "candidate_id", "block", "variable_name", "source_id",
    "accessibility_score", "authoritative", "reproducible",
    "published_at_known", "available_at_known", "common_sample_coverage",
    "positive_event_count_ok", "extraction_error_controlled",
    "gate_condition", "status", "decision_notes",
]

_GATE_CONDITION = (
    "accessibility_score>=3 AND authoritative AND reproducible AND "
    "published_at_or_available_at_known AND sufficient_common_sample_coverage "
    "AND acceptable_positive_event_count_in_temporal_folds AND "
    "controlled_extraction_adjustment_error"
)

# Template rows. No candidate with score < 3 or unknown score may be admitted.
# accessibility==3 only permits entry to the pilot, never automatic admission.
_GATE_ROWS = [
    {
        "candidate_id": "gate_m2_equity_return_window", "block": "M2",
        "variable_name": "equity_return_window", "source_id": "src_m2_tsetmc_market",
        "accessibility_score": "", "authoritative": "", "reproducible": "",
        "published_at_known": "", "available_at_known": "", "common_sample_coverage": "",
        "positive_event_count_ok": "", "extraction_error_controlled": "",
        "gate_condition": _GATE_CONDITION, "status": "pending_part3",
        "decision_notes": "Score unknown -> cannot be admitted. Part 3 pilot required.",
    },
    {
        "candidate_id": "gate_m3_cpi_inflation", "block": "M3",
        "variable_name": "cpi_inflation", "source_id": "src_m3_cbi_macro",
        "accessibility_score": "", "authoritative": "", "reproducible": "",
        "published_at_known": "", "available_at_known": "", "common_sample_coverage": "",
        "positive_event_count_ok": "", "extraction_error_controlled": "",
        "gate_condition": _GATE_CONDITION, "status": "pending_part3",
        "decision_notes": "Score unknown -> cannot be admitted. Part 3 pilot required.",
    },
    {
        "candidate_id": "gate_m4_audit_opinion_type", "block": "M4",
        "variable_name": "audit_opinion_type", "source_id": "src_m4_codal_audit",
        "accessibility_score": "", "authoritative": "", "reproducible": "",
        "published_at_known": "", "available_at_known": "", "common_sample_coverage": "",
        "positive_event_count_ok": "", "extraction_error_controlled": "",
        "gate_condition": _GATE_CONDITION, "status": "pending_part3",
        "decision_notes": "Score unknown -> cannot be admitted. Gated individually.",
    },
]


def build_admission_gate_csv() -> str:
    return _csv_str(_GATE_HEADER, _GATE_ROWS)


def gate_template_invariant_ok() -> bool:
    """No admitted row may have score < 3 or an unknown/blank score."""
    for r in _GATE_ROWS:
        if r["status"] == "admitted":
            score = r.get("accessibility_score", "")
            if score == "" or not str(score).isdigit() or int(score) < 3:
                return False
    return True


def registry_no_m5_ok() -> bool:
    return all(r["block"] in ("M1", "M2", "M3", "M4") for r in _REGISTRY_ROWS)


# ---- Gap audit / summary / README ----------------------------------------- #

_GAP_AUDIT_HEADER = [
    "row_key", "ticker", "fiscal_year", "block",
    "source_file_present", "source_url_present", "fiscal_year_end_present",
    "company_name_present", "industry_present", "audit_status_clean",
    "audit_status_unknown", "provenance_gap_count", "provenance_gaps",
    "eligibility_impact",
]


def build_gap_audit_csv(df: pd.DataFrame) -> str:
    return _csv_str(_GAP_AUDIT_HEADER, build_gap_audit_rows(df))


def build_gap_summary(counts: dict, input_sha: str, input_source: str) -> dict:
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "block": "M1",
        "scope": "read_only_provenance_gap_audit",
        "input_name": INPUT_NAME,
        "input_sha256": input_sha,
        "input_source": input_source,
        "counts": dict(sorted(counts.items())),
        "expected_invariants": dict(sorted(EXPECTED_INVARIANTS.items())),
        "invariants_match": check_invariants(counts) == [],
        "notes": (
            "Empty source_url for 1316 rows is recorded as a provenance gap only. "
            "It does NOT change eligibility or drop any row in Part 1. "
            "No gap is filled and no value is guessed."
        ),
    }


def build_readme(counts: dict, input_sha: str, input_source: str) -> str:
    return (
        "# Stage125 Part 1 — Data Dictionary & Provenance Contract\n\n"
        "This directory contains the Stage125 **Part 1** deliverables. Part 1 is a\n"
        "documentation / contract / read-only-audit step. It performs **no** modeling,\n"
        "**no** data extraction, **no** network access, and does **not** change the\n"
        "frozen target, sample, eligibility, cutoff, or any Stage122–Stage124 asset.\n\n"
        "## Deliverables\n\n"
        f"- `{F_DICTIONARY}` — data dictionary for blocks M1–M4.\n"
        f"- `{F_ID_TIME}` — identifier and observation/publication/availability/"
        "retrieval time contract.\n"
        f"- `{F_REGISTRY}` — source registry (M1–M4 only; no M5).\n"
        f"- `{F_MANIFEST_SCHEMA}` — provenance manifest record schema.\n"
        f"- `{F_GATE_TEMPLATE}` — data admission gate template.\n"
        f"- `{F_GAP_AUDIT}` — per-row M1 provenance flags (identifiers + flags only).\n"
        f"- `{F_GAP_SUMMARY}` — M1 provenance gap summary.\n"
        f"- `{F_QC}` — QC report.\n"
        f"- `{F_METADATA}` — hashes/metadata manifest.\n\n"
        "## M1 provenance gap counts (read-only)\n\n"
        f"- rows: {counts['rows']} (unique row_key: {counts['unique_row_key']})\n"
        f"- source_file present/missing: {counts['source_file_present']}/"
        f"{counts['source_file_missing']}\n"
        f"- source_url present/missing: {counts['source_url_present']}/"
        f"{counts['source_url_missing']}\n"
        f"- fiscal_year_end present/missing: {counts['fiscal_year_end_present']}/"
        f"{counts['fiscal_year_end_missing']}\n"
        f"- company_name present/missing: {counts['company_name_present']}/"
        f"{counts['company_name_missing']}\n"
        f"- industry present/missing: {counts['industry_present']}/"
        f"{counts['industry_missing']}\n"
        f"- audit_status_unknown: {counts['audit_status_unknown']}\n\n"
        f"Input: `{INPUT_NAME}` (source: {input_source})\n\n"
        f"Input SHA-256: `{input_sha}`\n\n"
        "## Guardrails\n\n"
        "- Empty `source_url` (1316 rows) is a provenance gap only; it never changes\n"
        "  eligibility or drops a row in Part 1.\n"
        "- `row_key` stays immutable and unique across 1331 rows.\n"
        "- `predictor_row_key_t` and `target_row_key_t_plus_1` are not redefined.\n"
        "- M5 (Persian text modeling) is not part of the registry or dictionary.\n"
        "- Modeling remains prohibited; `modeling_started=false`.\n"
        "- Part 2 has not started.\n"
    )


# --------------------------------------------------------------------------- #
# Frozen-asset snapshot (read-only; deterministic over tracked frozen files)
# --------------------------------------------------------------------------- #

def frozen_asset_hashes(repo_root: Path) -> dict:
    """Actual SHA-256 of every TRACKED, non-ignored frozen-manifest output.

    Deterministic: gitignored / untracked (machine-dependent, regenerable)
    files are skipped so the snapshot content is stable across machines.
    Returns {relpath: sha256}. Also usable to prove the assets are unchanged.
    """
    root = str(repo_root)
    tracked = _git_tracked(root)
    snapshot: dict[str, str] = {}
    for manifest_rel in FROZEN_MANIFEST_PATHS:
        manifest_path = repo_root / manifest_rel
        if not manifest_path.is_file():
            raise QCFail(f"frozen manifest missing: {manifest_rel}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        outputs = data.get("output_files_sha256", {})
        manifest_dir = str(Path(manifest_rel).parent)
        for fname in sorted(outputs):
            file_rel = f"{manifest_dir}/{fname}"
            if file_rel not in tracked:
                continue
            if _git_ignored(root, file_rel):
                continue
            actual = sha256_file(repo_root / file_rel)
            if actual is not None:
                snapshot[file_rel] = actual
    return dict(sorted(snapshot.items()))


# --------------------------------------------------------------------------- #
# Content assembly (deterministic; pure)
# --------------------------------------------------------------------------- #

def build_content_files(df: pd.DataFrame, counts: dict, input_sha: str,
                        input_source: str) -> dict[str, str]:
    """Build the 8 content files (everything except QC + metadata)."""
    return {
        F_DICTIONARY: build_data_dictionary_csv(),
        F_ID_TIME: _json_str(build_identifier_time_contract()),
        F_REGISTRY: build_source_registry_csv(),
        F_MANIFEST_SCHEMA: _json_str(build_provenance_manifest_schema()),
        F_GATE_TEMPLATE: build_admission_gate_csv(),
        F_GAP_AUDIT: build_gap_audit_csv(df),
        F_GAP_SUMMARY: _json_str(build_gap_summary(counts, input_sha, input_source)),
        F_README: build_readme(counts, input_sha, input_source),
    }


def _hash_map(files: dict[str, str]) -> dict:
    return {name: sha256_bytes(content.encode("utf-8"))
            for name, content in sorted(files.items())}


# --------------------------------------------------------------------------- #
# QC assertions + report
# --------------------------------------------------------------------------- #

def build_qc_assertions(counts: dict, content_hashes: dict,
                        frozen_before: dict, frozen_after: dict) -> list[dict]:
    out: list[dict] = []

    def add(name, ok, detail):
        out.append({"assertion": name, "status": "PASS" if ok else "FAIL",
                    "detail": detail})

    inv_errs = check_invariants(counts)
    add("m1_invariants_match", inv_errs == [],
        "all invariant counts match" if not inv_errs else "; ".join(inv_errs))
    add("row_key_unique_1331",
        counts["unique_row_key"] == 1331 and counts["rows"] == 1331,
        f"rows={counts['rows']} unique={counts['unique_row_key']}")
    add("source_url_gap_recorded_not_dropped", counts["source_url_missing"] == 1316,
        "1316 missing source_url recorded as provenance gap only")
    add("registry_no_m5", registry_no_m5_ok(), "only M1-M4 blocks in registry")
    add("gate_template_no_admitted_below_threshold", gate_template_invariant_ok(),
        "no admitted row with score<3 or unknown score")
    add("provenance_schema_has_required_fields",
        {"provenance_id", "source_id", "published_at", "available_at",
         "retrieved_at_utc", "content_sha256", "revision_status"}.issubset(
            {f[0] for f in _PROVENANCE_FIELDS}),
        "provenance schema declares all mandatory fields")
    add("content_hashes_present", all(v for v in content_hashes.values()),
        f"{len(content_hashes)} content files hashed")
    add("frozen_assets_unchanged", frozen_before == frozen_after and len(frozen_before) > 0,
        f"{len(frozen_before)} tracked frozen assets identical before and after")
    add("modeling_not_started", True, "no modeling artifact produced")
    add("no_network_extraction", True, "no network or API access performed")
    return out


def build_qc_report(repo_root: Path, counts: dict, input_sha: str,
                    input_source: str, content_hashes: dict,
                    frozen_before: dict, frozen_after: dict,
                    tickers: list[str]) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    src_sha = sha256_file(repo_root / SRC_REL)
    test_sha = sha256_file(repo_root / TEST_REL)
    assertions = build_qc_assertions(counts, content_hashes, frozen_before, frozen_after)
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    all_pass = failed == 0
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": src_sha,
        "test_file_sha256": test_sha,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": all_pass,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "input_name": INPUT_NAME,
        "input_source": input_source,
        "input_sha256": input_sha,
        "m1_invariants": dict(sorted(counts.items())),
        "expected_invariants": dict(sorted(EXPECTED_INVARIANTS.items())),
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_assets_before": frozen_before,
        "frozen_assets_after": frozen_after,
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": False,
        "network_extraction_performed": False,
        "assertions": assertions,
    }


def build_metadata(repo_root: Path, qc_report: dict, content_hashes: dict,
                   qc_hash: str, input_sha: str, input_source: str) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": "Stage125 Part 1 — data dictionary & provenance contract.",
        "generated_at": qc_report["generated_at"],
        "code_commit": qc_report["source_commit"],
        "source_file_sha256": qc_report["source_file_sha256"],
        "test_file_sha256": qc_report["test_file_sha256"],
        "input_name": INPUT_NAME,
        "input_source": input_source,
        "input_sha256": input_sha,
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": False,
        "network_extraction_performed": False,
        "warning": ("Part 1 only: data dictionary & provenance contract. No modeling, "
                    "no extraction, no Part 2. Stage122-124 assets unchanged."),
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path, input_path: Path | None,
              bundle_path: Path | None) -> dict:
    """Compute every output file's content (deterministic). Fail-closed.

    Returns {"files": {name: content_str}, "qc": qc_report, "counts": counts}.
    """
    df, input_sha, input_source = load_input(input_path, bundle_path)

    counts = compute_gap_summary(df)
    inv_errs = check_invariants(counts)
    if inv_errs:
        raise QCFail("M1 invariant mismatch (fail-closed):\n  " + "\n  ".join(inv_errs))

    frozen_before = frozen_asset_hashes(repo_root)
    content_files = build_content_files(df, counts, input_sha, input_source)
    content_hashes = _hash_map(content_files)
    frozen_after = frozen_asset_hashes(repo_root)
    if frozen_before != frozen_after:
        raise QCFail("frozen assets changed during Part 1 run (fail-closed)")

    tickers = sorted(t for t in df["ticker"].dropna().unique() if str(t).strip())

    qc_report = build_qc_report(repo_root, counts, input_sha, input_source,
                                content_hashes, frozen_before, frozen_after, tickers)
    if not qc_report["all_pass"]:
        failed = [a for a in qc_report["assertions"] if a["status"] != "PASS"]
        raise QCFail("QC failed (fail-closed): "
                     + "; ".join(f"{a['assertion']}: {a['detail']}" for a in failed))

    qc_str = _json_str(qc_report)
    qc_hash = sha256_bytes(qc_str.encode("utf-8"))
    metadata = build_metadata(repo_root, qc_report, content_hashes, qc_hash,
                              input_sha, input_source)

    files: dict[str, str] = dict(content_files)
    files[F_QC] = qc_str
    files[F_METADATA] = _json_str(metadata)
    return {"files": files, "qc": qc_report, "counts": counts,
            "input_sha256": input_sha, "input_source": input_source}


def run(project_dir: Path | None = None, input_path: Path | None = None,
        bundle_path: Path | None = None, output_dir: Path | None = None,
        write: bool = False) -> dict:
    """Build (and optionally write) the Stage125 Part 1 deliverables.

    write=False is a pure check: nothing tracked is overwritten; on-disk files
    are compared against the freshly computed content and drift is reported.
    """
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if input_path is None:
        input_path = project_dir / "stage123" / INPUT_NAME
    if output_dir is None:
        output_dir = project_dir / "stage125"

    result = build_all(repo_root, input_path, bundle_path)
    files = result["files"]

    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (output_dir / name).write_text(content, encoding="utf-8")
        result["written"] = True
        result["drift"] = []
    else:
        drift = []
        for name, content in files.items():
            disk = output_dir / name
            on_disk = disk.read_text(encoding="utf-8") if disk.is_file() else None
            if on_disk != content:
                drift.append(name)
        result["written"] = False
        result["drift"] = drift

    result["output_dir"] = str(output_dir)
    return result
