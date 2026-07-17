"""Stage125 Part 3B.1A — CUT-A Available-at Operationalization Decision Lock.

Maintenance-only decision lock that operationalizes how `available_at` is derived
from an exact-version-bound official CODAL document:

    operational available_at =
        PublishDateTime of the exact matched official CODAL LetterSerial/version

Explicit non-claims / prohibitions for this task:
- no network (CODAL / TSETMC / CBI)
- no real available_at assignment to pilot rows
- no cutoff resolution on real pairs
- no candidate / pair evidence capture
- no value extraction / accessibility scoring / Gate admission
- no Part 3B.2 / Stage126 / modeling
- research action pointers unchanged

Synthetic validation and schema/contracts only.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jdatetime

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1a_cut_a_available_at_operationalization_lock"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "3a54a79c935f27e311679e8582e4c46330590a43"
DECISION_LOCK_VERSION = "stage125_part3b1a_v1"
MAINTENANCE_TASK_ID = (
    "stage125-part3b1a-cut-a-available-at-operationalization-lock"
)
RESEARCH_LAST_COMPLETED = "stage125-part3a-decision-lock"
RESEARCH_NEXT = "stage125-part3b-evidence-capture"

SRC_REL = (
    "project/src/stage125_part3b1a_cut_a_available_at_operationalization.py"
)
TEST_REL = (
    "project/tests/test_stage125_part3b1a_cut_a_available_at_operationalization.py"
)
RUN_REL = "project/run_stage125_part3b1a.py"

F_CONTRACT = "part3b1a_cut_a_available_at_operationalization_contract_stage125.json"
F_LOCK = "part3b1a_cut_a_available_at_decision_lock_stage125.json"
F_README = "README_STAGE125_PART3B1A_CUT_A_AVAILABLE_AT_LOCK.md"
F_QC = "stage125_part3b1a_cut_a_available_at_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1a.json"

CONTENT_FILES = (F_CONTRACT, F_LOCK, F_README)

PART3B1A_AUTHORIZED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    RUN_REL,
    f"project/stage125/{F_CONTRACT}",
    f"project/stage125/{F_LOCK}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

FROZEN_SCIENTIFIC_PATHS = (
    "project/stage125/data_dictionary_stage125.csv",
    "project/stage125/source_registry_stage125.csv",
    "project/stage125/prediction_time_contract_stage125_part2.json",
    "project/stage125/feature_availability_contract_stage125_part2.json",
    "project/stage125/leakage_checklist_stage125_part2.json",
    "project/stage125/prediction_cutoff_audit_stage125_part2.csv",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv",
    "project/stage125/stage125_part3b_evidence_capture_qc_report.json",
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
)

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})

TEHRAN_TZ_NAME = "Asia/Tehran"
CODAL_TS_RE = re.compile(
    r"^(?P<y>\d{4})/(?P<m>\d{1,2})/(?P<d>\d{1,2})\s+"
    r"(?P<H>\d{1,2}):(?P<M>\d{1,2}):(?P<S>\d{1,2})$"
)

PERSIAN_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

CUTOFF_STATUS_RESOLVED = "RESOLVED"
CUTOFF_STATUS_UNRESOLVED = "UNRESOLVED"

REASON_MULTI_DOCUMENT = "multi_document_predictor_row_requires_separate_adjudication"
REASON_SENT_AFTER_PUBLISH = "sent_datetime_after_publish_datetime_inconsistency"
REASON_MISSING_PUBLISH = "missing_publish_datetime"
REASON_MALFORMED_PUBLISH = "malformed_publish_datetime"
REASON_NAIVE_DATETIME = "naive_datetime_rejected"
REASON_TZ_UNAVAILABLE = "timezone_library_or_data_unavailable"
REASON_NONEXISTENT_LOCAL = "nonexistent_local_time"
REASON_AMBIGUOUS_LOCAL = "ambiguous_local_time_without_deterministic_rule"
REASON_BINDING_FAILED = "exact_document_binding_failed"
REASON_UNKNOWN_REVISION = "unknown_revision_status"
REASON_CANONICAL_VERSION_UNBOUND = "canonical_source_version_not_provably_bound"
REASON_VALUES_SOURCE_SERIAL_MISMATCH = "values_source_letter_serial_mismatch"
REASON_MISSING_CANONICAL_LETTER_SERIAL = "missing_canonical_letter_serial"
REASON_MISSING_REQUIRED_TRACING_NO = "missing_required_tracing_no"
REASON_MISSING_OFFICIAL_TITLE = "missing_official_title"
# Deprecated as primary enforcement; retained only as a redundant audit flag.
# Exact LetterSerial equality (values_source / letter / canonical) is authoritative.
REASON_CORRECTION_USES_ORIGINAL = (
    "correction_values_cannot_use_original_publication_cutoff"
)
REASON_MULTIPLE_CANDIDATES = "multiple_letter_serial_candidates"
REASON_INCOMPLETE_CACHE = "incomplete_cache_without_canonical_letter_serial"
REASON_SENT_USED_AS_AVAILABILITY = "sent_datetime_must_never_be_availability"

# Matches frozen provenance_manifest_schema_stage125.json revision_status enum.
NORMALIZED_REVISION_STATUS = frozenset({"original", "revision", "restatement"})
CODAL_ESLAHIYE_RAW = "اصلاحیه"

BINDING_FAIL_REASONS = (
    "subsidiary_only_title",
    "entity_ambiguity",
    "consolidated_separate_ambiguity",
    "annual_interim_ambiguity",
    "multiple_candidate_letters",
    "incomplete_pagination_without_canonical_letter_serial",
    "source_filename_only_match",
    "ticker_year_only_match",
    "title_only_match",
    "missing_letter_serial",
    REASON_MISSING_CANONICAL_LETTER_SERIAL,
    REASON_MISSING_REQUIRED_TRACING_NO,
    REASON_VALUES_SOURCE_SERIAL_MISMATCH,
    REASON_MISSING_OFFICIAL_TITLE,
    "unknown_revision_status",
    "canonical_source_version_not_provably_bound",
    "ticker_mismatch",
    "entity_mismatch",
    "fiscal_year_mismatch",
    "fiscal_year_end_mismatch",
    "interim_statement",
    "unaudited_statement",
    "parent_company_identity_mismatch",
    "statement_scope_mismatch",
    "separate_scope_required_but_not_met",
    "letter_code_mismatch",
    "letter_serial_mismatch",
    "tracing_no_mismatch",
    "official_title_mismatch",
    "missing_public_codal_url",
    "missing_raw_payload_or_snapshot_hash",
)


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.1A."""


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


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or (_git(repo_root, "rev-parse", "HEAD") or "unknown")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    return raw or "unknown"


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
    if head == EXPECTED_BASELINE_COMMIT:
        return head
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head):
        raise QCFail(
            f"baseline {EXPECTED_BASELINE_COMMIT} is not an ancestor of HEAD {head}"
        )
    return head


def frozen_scientific_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in FROZEN_SCIENTIFIC_PATHS:
        digest = sha256_file(repo_root / rel)
        if digest is None:
            raise QCFail(f"missing frozen scientific artifact: {rel}")
        out[rel] = digest
    return out


# --------------------------------------------------------------------------- #
# Timestamp normalization (pure)
# --------------------------------------------------------------------------- #

def normalize_persian_digits(text: str) -> str:
    """Map Persian/Arabic-Indic digits to ASCII. Leaves other chars unchanged."""
    return (text or "").translate(PERSIAN_DIGIT_MAP)


def preserve_raw_codal_timestamp(raw: str | None) -> str | None:
    """Return the raw CODAL timestamp string unchanged (or None)."""
    if raw is None:
        return None
    return raw


@dataclass(frozen=True)
class NormalizedTimestamp:
    raw: str
    raw_normalized_digits: str
    jalali_year: int
    jalali_month: int
    jalali_day: int
    hour: int
    minute: int
    second: int
    local_tehran: datetime
    utc: datetime
    utc_iso8601: str


@dataclass(frozen=True)
class TimestampParseFailure:
    raw: str | None
    reason: str


def _tehran_zone() -> ZoneInfo:
    try:
        return ZoneInfo(TEHRAN_TZ_NAME)
    except ZoneInfoNotFoundError as exc:
        raise QCFail(REASON_TZ_UNAVAILABLE) from exc


def classify_tehran_wall_time(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
    tz: ZoneInfo,
) -> tuple[str, datetime | None]:
    """Classify a naive Asia/Tehran wall time via UTC round-trips.

    For each fold candidate (0 and 1):
      construct local → convert to UTC → convert back to Asia/Tehran →
      compare returned naive wall components with the original wall time.

    Classification:
      - neither fold round-trips exactly → nonexistent_local_time
      - both round-trip exactly and produce different UTC instants →
        ambiguous_local_time_without_deterministic_rule
      - exactly one fold round-trips exactly → valid (use that fold)
      - both round-trip exactly and represent the same instant → valid
    """
    wall = (year, month, day, hour, minute, second)
    surviving: list[tuple[int, datetime, datetime]] = []
    for fold in (0, 1):
        local = datetime(
            year, month, day, hour, minute, second, tzinfo=tz, fold=fold,
        )
        utc = local.astimezone(timezone.utc)
        back = utc.astimezone(tz)
        back_wall = (
            back.year, back.month, back.day, back.hour, back.minute, back.second,
        )
        if back_wall == wall:
            surviving.append((fold, local, utc))

    if not surviving:
        return REASON_NONEXISTENT_LOCAL, None
    if len(surviving) == 1:
        return "valid", surviving[0][1]
    # Both folds round-trip.
    if surviving[0][2] != surviving[1][2]:
        return REASON_AMBIGUOUS_LOCAL, None
    return "valid", surviving[0][1]


def jalali_string_from_tehran_gregorian_wall(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> str:
    """Deterministic Jalali CODAL string from a Gregorian Tehran wall time.

    Uses the pinned project `jdatetime` so DST fixtures are not manually guessed.
    """
    g = jdatetime.datetime.fromgregorian(
        datetime=datetime(year, month, day, hour, minute, second),
    )
    return (
        f"{g.year:04d}/{g.month:02d}/{g.day:02d} "
        f"{g.hour:02d}:{g.minute:02d}:{g.second:02d}"
    )


def explicit_normalized_revision_for_codal_eslahiye(
    *,
    revision_status_raw: str | None,
    map_eslahiye_to_revision: bool,
) -> str | None:
    """Map CODAL «اصلاحیه» to normalized `revision` only when explicitly requested.

    Raw wording may be retained separately in `revision_status_raw`. This helper
    never silently maps اصلاحیه to `restatement`, and never invents a status
    when the mapping flag is false.
    """
    raw = (revision_status_raw or "").strip()
    if map_eslahiye_to_revision and raw == CODAL_ESLAHIYE_RAW:
        return "revision"
    return None


def parse_codal_publish_datetime(
    raw: str | None,
) -> NormalizedTimestamp | TimestampParseFailure:
    """Parse a CODAL PublishDateTime into timezone-aware UTC.

    Raw format expected after digit normalization:
        YYYY/MM/DD HH:MM:SS  (Jalali calendar, Asia/Tehran local wall time)

    Fail-closed on malformed / invalid / nonexistent / ambiguous local times.
    Never invents fixed offsets like +03:30 for all years.
    """
    if raw is None or str(raw).strip() == "":
        return TimestampParseFailure(raw=raw, reason=REASON_MISSING_PUBLISH)

    raw_s = str(raw)
    digits = normalize_persian_digits(raw_s).strip()
    m = CODAL_TS_RE.match(digits)
    if not m:
        return TimestampParseFailure(raw=raw_s, reason=REASON_MALFORMED_PUBLISH)

    try:
        jy = int(m.group("y"))
        jm = int(m.group("m"))
        jd = int(m.group("d"))
        hh = int(m.group("H"))
        mm = int(m.group("M"))
        ss = int(m.group("S"))
    except ValueError:
        return TimestampParseFailure(raw=raw_s, reason=REASON_MALFORMED_PUBLISH)

    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return TimestampParseFailure(raw=raw_s, reason=REASON_MALFORMED_PUBLISH)

    try:
        jdt = jdatetime.datetime(jy, jm, jd, hh, mm, ss)
    except ValueError:
        return TimestampParseFailure(raw=raw_s, reason=REASON_MALFORMED_PUBLISH)

    gregorian_naive = jdt.togregorian()
    if gregorian_naive.tzinfo is not None:
        # jdatetime should yield naive Gregorian; reject otherwise.
        return TimestampParseFailure(raw=raw_s, reason=REASON_NAIVE_DATETIME)

    try:
        tz = _tehran_zone()
    except QCFail:
        return TimestampParseFailure(raw=raw_s, reason=REASON_TZ_UNAVAILABLE)

    kind, local = classify_tehran_wall_time(
        gregorian_naive.year,
        gregorian_naive.month,
        gregorian_naive.day,
        gregorian_naive.hour,
        gregorian_naive.minute,
        gregorian_naive.second,
        tz,
    )
    if kind != "valid" or local is None:
        return TimestampParseFailure(raw=raw_s, reason=kind)

    if local.tzinfo is None:
        return TimestampParseFailure(raw=raw_s, reason=REASON_NAIVE_DATETIME)

    utc = local.astimezone(timezone.utc)
    return NormalizedTimestamp(
        raw=raw_s,
        raw_normalized_digits=digits,
        jalali_year=jy,
        jalali_month=jm,
        jalali_day=jd,
        hour=hh,
        minute=mm,
        second=ss,
        local_tehran=local,
        utc=utc,
        utc_iso8601=utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def reject_naive_datetime(dt: datetime | None) -> bool:
    """Return True when dt is timezone-aware; False (reject) when naive/None."""
    return dt is not None and dt.tzinfo is not None and dt.utcoffset() is not None


# --------------------------------------------------------------------------- #
# Exact-document binding (pure, synthetic)
# --------------------------------------------------------------------------- #

@dataclass
class ExactDocumentBindingInput:
    """Synthetic binding evidence for a predictor-row ↔ CODAL letter match."""

    canonical_ticker: str
    letter_ticker: str
    legal_entity_canonical: str
    legal_entity_letter: str
    predictor_fiscal_year: int
    letter_fiscal_year: int
    fiscal_year_end_canonical: str
    fiscal_year_end_letter: str
    is_annual: bool
    is_interim: bool
    is_audited: bool
    is_parent_company: bool
    statement_scope_canonical: str  # e.g. separate / consolidated
    statement_scope_letter: str
    requires_separate_non_consolidated: bool
    letter_code_canonical: str
    letter_code_letter: str
    letter_serial: str | None
    canonical_letter_serial: str | None
    tracing_no: str | None
    canonical_tracing_no: str | None
    official_title: str
    canonical_official_title: str
    # Normalized status must match frozen provenance schema enum only:
    # original | revision | restatement. Null/unknown/other → UNRESOLVED.
    # CODAL «اصلاحیه» raw wording may be retained in revision_status_raw;
    # normalized status is never silently invented from raw text alone.
    revision_status: str | None
    public_codal_url: str | None
    raw_payload_or_snapshot_hash: str | None
    candidate_letter_serials: list[str] = field(default_factory=list)
    incomplete_pagination: bool = False
    match_basis: str = "exact_letter_serial"  # or filename_only / ticker_year / title_only
    subsidiary_only_title: bool = False
    entity_ambiguous: bool = False
    consolidated_separate_ambiguous: bool = False
    annual_interim_ambiguous: bool = False
    # Redundant audit flag only; exact identifier equality is authoritative.
    canonical_source_version_bound: bool = False
    multi_document_predictor_row: bool = False
    # Values-source LetterSerial for the version that supplied canonical values.
    values_source_letter_serial: str | None = None
    # Raw/audit CODAL revision wording (e.g. «اصلاحیه»); not a normalized enum.
    revision_status_raw: str | None = None
    # Deprecated as primary enforcement; redundant audit flag only.
    publish_of_original_used_for_correction_values: bool = False


@dataclass(frozen=True)
class BindingResult:
    ok: bool
    reasons: tuple[str, ...]


def _nonempty(value: str | None) -> bool:
    return value is not None and str(value).strip() != ""


def evaluate_exact_document_binding(
    inp: ExactDocumentBindingInput,
) -> BindingResult:
    """Fail-closed exact-document binding checks (synthetic)."""
    reasons: list[str] = []

    if inp.multi_document_predictor_row:
        reasons.append(REASON_MULTI_DOCUMENT)

    if inp.subsidiary_only_title:
        reasons.append("subsidiary_only_title")
    if inp.entity_ambiguous:
        reasons.append("entity_ambiguity")
    if inp.consolidated_separate_ambiguous:
        reasons.append("consolidated_separate_ambiguity")
    if inp.annual_interim_ambiguous:
        reasons.append("annual_interim_ambiguity")

    if inp.match_basis == "source_filename_only":
        reasons.append("source_filename_only_match")
    elif inp.match_basis == "ticker_year_only":
        reasons.append("ticker_year_only_match")
    elif inp.match_basis == "title_only":
        reasons.append("title_only_match")

    if not _nonempty(inp.letter_serial):
        reasons.append("missing_letter_serial")
    if not _nonempty(inp.canonical_letter_serial):
        reasons.append(REASON_MISSING_CANONICAL_LETTER_SERIAL)
    if inp.incomplete_pagination and not _nonempty(inp.canonical_letter_serial):
        reasons.append("incomplete_pagination_without_canonical_letter_serial")
        reasons.append(REASON_INCOMPLETE_CACHE)
    if len(inp.candidate_letter_serials) > 1:
        reasons.append("multiple_candidate_letters")
        reasons.append(REASON_MULTIPLE_CANDIDATES)

    if inp.canonical_ticker != inp.letter_ticker:
        reasons.append("ticker_mismatch")
    if inp.legal_entity_canonical != inp.legal_entity_letter:
        reasons.append("entity_mismatch")
    if inp.predictor_fiscal_year != inp.letter_fiscal_year:
        reasons.append("fiscal_year_mismatch")
    if inp.fiscal_year_end_canonical != inp.fiscal_year_end_letter:
        reasons.append("fiscal_year_end_mismatch")
    if inp.is_interim or not inp.is_annual:
        reasons.append("interim_statement")
    if not inp.is_audited:
        reasons.append("unaudited_statement")
    if not inp.is_parent_company:
        reasons.append("parent_company_identity_mismatch")
    if inp.statement_scope_canonical != inp.statement_scope_letter:
        reasons.append("statement_scope_mismatch")
    if (
        inp.requires_separate_non_consolidated
        and inp.statement_scope_letter != "separate"
    ):
        reasons.append("separate_scope_required_but_not_met")
    if inp.letter_code_canonical != inp.letter_code_letter:
        reasons.append("letter_code_mismatch")

    # Exact source-version binding: structural identifier equality is authoritative.
    # Boolean flags cannot bypass these checks.
    if (
        _nonempty(inp.letter_serial)
        and _nonempty(inp.canonical_letter_serial)
        and inp.letter_serial != inp.canonical_letter_serial
    ):
        reasons.append("letter_serial_mismatch")

    if _nonempty(inp.canonical_tracing_no):
        if not _nonempty(inp.tracing_no):
            reasons.append(REASON_MISSING_REQUIRED_TRACING_NO)
        elif inp.canonical_tracing_no != inp.tracing_no:
            reasons.append("tracing_no_mismatch")

    if not _nonempty(inp.official_title) or not _nonempty(inp.canonical_official_title):
        reasons.append(REASON_MISSING_OFFICIAL_TITLE)
    elif inp.official_title != inp.canonical_official_title:
        reasons.append("official_title_mismatch")

    if inp.revision_status not in NORMALIZED_REVISION_STATUS:
        reasons.append("unknown_revision_status")
        reasons.append(REASON_UNKNOWN_REVISION)
    elif inp.revision_status in {"revision", "restatement"}:
        # Canonical values must come from this exact Serial only.
        if (
            not _nonempty(inp.values_source_letter_serial)
            or inp.values_source_letter_serial != inp.letter_serial
            or inp.values_source_letter_serial != inp.canonical_letter_serial
            or inp.letter_serial != inp.canonical_letter_serial
        ):
            reasons.append(REASON_VALUES_SOURCE_SERIAL_MISMATCH)

    if not inp.public_codal_url:
        reasons.append("missing_public_codal_url")
    if not inp.raw_payload_or_snapshot_hash:
        reasons.append("missing_raw_payload_or_snapshot_hash")
    # Redundant audit flags — cannot authorize a structurally unbound row.
    if not inp.canonical_source_version_bound:
        reasons.append("canonical_source_version_not_provably_bound")
        reasons.append(REASON_CANONICAL_VERSION_UNBOUND)
    if inp.publish_of_original_used_for_correction_values:
        reasons.append(REASON_CORRECTION_USES_ORIGINAL)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    uniq: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return BindingResult(ok=len(uniq) == 0, reasons=tuple(uniq))


# --------------------------------------------------------------------------- #
# Available-at resolution (pure; never assigns to real pilot rows)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AvailableAtResolution:
    available_at: str | None  # ISO-8601 UTC or null
    available_at_raw_publish: str | None
    sent_datetime_raw: str | None
    source_field: str | None  # always PublishDateTime when resolved
    cutoff_status: str
    reasons: tuple[str, ...]
    binding_ok: bool
    sent_publish_relation: str  # equal | sent_before_publish | sent_after_publish | unknown
    real_pilot_row_assigned: bool = False


def _sent_publish_relation(
    sent_raw: str | None, publish_raw: str | None,
) -> str:
    if not sent_raw or not publish_raw:
        return "unknown"
    sent = parse_codal_publish_datetime(sent_raw)
    pub = parse_codal_publish_datetime(publish_raw)
    if isinstance(sent, TimestampParseFailure) or isinstance(pub, TimestampParseFailure):
        return "unknown"
    if sent.utc == pub.utc:
        return "equal"
    if sent.utc < pub.utc:
        return "sent_before_publish"
    return "sent_after_publish"


def resolve_operational_available_at(
    *,
    publish_datetime_raw: str | None,
    sent_datetime_raw: str | None,
    binding: ExactDocumentBindingInput,
    force_use_sent_as_availability: bool = False,
) -> AvailableAtResolution:
    """Resolve operational available_at from PublishDateTime under CUT-A.1A rules.

    Never treats SentDateTime as availability. Never assigns to real pilot rows.
    """
    bind = evaluate_exact_document_binding(binding)
    relation = _sent_publish_relation(sent_datetime_raw, publish_datetime_raw)

    if force_use_sent_as_availability:
        return AvailableAtResolution(
            available_at=None,
            available_at_raw_publish=preserve_raw_codal_timestamp(publish_datetime_raw),
            sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
            source_field=None,
            cutoff_status=CUTOFF_STATUS_UNRESOLVED,
            reasons=(REASON_SENT_USED_AS_AVAILABILITY,),
            binding_ok=bind.ok,
            sent_publish_relation=relation,
        )

    if not bind.ok:
        return AvailableAtResolution(
            available_at=None,
            available_at_raw_publish=preserve_raw_codal_timestamp(publish_datetime_raw),
            sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
            source_field=None,
            cutoff_status=CUTOFF_STATUS_UNRESOLVED,
            reasons=(REASON_BINDING_FAILED,) + bind.reasons,
            binding_ok=False,
            sent_publish_relation=relation,
        )

    if relation == "sent_after_publish":
        return AvailableAtResolution(
            available_at=None,
            available_at_raw_publish=preserve_raw_codal_timestamp(publish_datetime_raw),
            sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
            source_field=None,
            cutoff_status=CUTOFF_STATUS_UNRESOLVED,
            reasons=(REASON_SENT_AFTER_PUBLISH,),
            binding_ok=True,
            sent_publish_relation=relation,
        )

    parsed = parse_codal_publish_datetime(publish_datetime_raw)
    if isinstance(parsed, TimestampParseFailure):
        return AvailableAtResolution(
            available_at=None,
            available_at_raw_publish=preserve_raw_codal_timestamp(publish_datetime_raw),
            sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
            source_field=None,
            cutoff_status=CUTOFF_STATUS_UNRESOLVED,
            reasons=(parsed.reason,),
            binding_ok=True,
            sent_publish_relation=relation,
        )

    if not reject_naive_datetime(parsed.local_tehran):
        return AvailableAtResolution(
            available_at=None,
            available_at_raw_publish=parsed.raw,
            sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
            source_field=None,
            cutoff_status=CUTOFF_STATUS_UNRESOLVED,
            reasons=(REASON_NAIVE_DATETIME,),
            binding_ok=True,
            sent_publish_relation=relation,
        )

    # Revision/restatement values must use that exact LetterSerial's PublishDateTime.
    # Enforced structurally via values_source_letter_serial == letter_serial ==
    # canonical_letter_serial (boolean audit flags cannot bypass).
    return AvailableAtResolution(
        available_at=parsed.utc_iso8601,
        available_at_raw_publish=parsed.raw,
        sent_datetime_raw=preserve_raw_codal_timestamp(sent_datetime_raw),
        source_field="PublishDateTime",
        cutoff_status=CUTOFF_STATUS_RESOLVED,
        reasons=(),
        binding_ok=True,
        sent_publish_relation=relation,
    )


def synthetic_valid_binding(**overrides: Any) -> ExactDocumentBindingInput:
    """Return a fully valid synthetic binding; tests override fields to fail-close."""
    base = ExactDocumentBindingInput(
        canonical_ticker="بوعلی",
        letter_ticker="بوعلی",
        legal_entity_canonical="شرکت بوعلی",
        legal_entity_letter="شرکت بوعلی",
        predictor_fiscal_year=1400,
        letter_fiscal_year=1400,
        fiscal_year_end_canonical="1400/12/29",
        fiscal_year_end_letter="1400/12/29",
        is_annual=True,
        is_interim=False,
        is_audited=True,
        is_parent_company=True,
        statement_scope_canonical="separate",
        statement_scope_letter="separate",
        requires_separate_non_consolidated=True,
        letter_code_canonical="ن-۱۰",
        letter_code_letter="ن-۱۰",
        letter_serial="ABC123",
        canonical_letter_serial="ABC123",
        tracing_no="T-9",
        canonical_tracing_no="T-9",
        official_title="اطلاعات و صورت‌های مالی سالانه دوره ۱۲ ماهه منتهی به ۱۴۰۰/۱۲/۲۹ (حسابرسی شده)",
        canonical_official_title=(
            "اطلاعات و صورت‌های مالی سالانه دوره ۱۲ ماهه منتهی به ۱۴۰۰/۱۲/۲۹ (حسابرسی شده)"
        ),
        revision_status="original",
        revision_status_raw=None,
        public_codal_url="https://codal.ir/Reports/Decision.aspx?LetterSerial=ABC123",
        raw_payload_or_snapshot_hash="a" * 64,
        candidate_letter_serials=["ABC123"],
        incomplete_pagination=False,
        match_basis="exact_letter_serial",
        subsidiary_only_title=False,
        entity_ambiguous=False,
        consolidated_separate_ambiguous=False,
        annual_interim_ambiguous=False,
        canonical_source_version_bound=True,
        multi_document_predictor_row=False,
        values_source_letter_serial="ABC123",
        publish_of_original_used_for_correction_values=False,
    )
    for key, value in overrides.items():
        if not hasattr(base, key):
            raise TypeError(f"unknown binding field: {key}")
        setattr(base, key, value)
    return base


# --------------------------------------------------------------------------- #
# Contract / decision-lock payloads
# --------------------------------------------------------------------------- #

def build_operationalization_contract() -> dict:
    return {
        "contract_version": DECISION_LOCK_VERSION,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "decision_id": "cut_a_available_at_operationalization",
        "option_id": "CUT-A",
        "parent_cutoff_contract": "part3b1_cutoff_available_at_contract_stage125.json",
        "frozen_cut_a_unchanged": True,
        "operational_available_at": {
            "definition": (
                "PublishDateTime of the exact matched official CODAL "
                "LetterSerial/version for the predictor-year financial statement."
            ),
            "mapping_allowed_only_when": (
                "official document is exactly bound to the predictor row and the "
                "canonical source version"
            ),
            "source_field": "PublishDateTime",
            "sent_datetime_policy": {
                "sent_datetime_is_available_at": False,
                "preserve_raw": True,
                "allowed_uses": ["audit", "comparison"],
                "forbidden_uses": [
                    "cutoff",
                    "public_availability",
                    "prediction_time_gate",
                ],
                "even_when_equal_to_publish": (
                    "mapping_still_uses_PublishDateTime_only"
                ),
            },
            "selection_rationale": [
                "PublishDateTime is the operational public-release timestamp in this project",
                "SentDateTime may be publisher-send time and does not prove public availability",
                "PublishDateTime is more conservative / leakage-safe than SentDateTime",
                "This is a locked methodological operationalization, not inference from "
                "local filenames or local cache mtimes",
            ],
        },
        "exact_document_binding_required": {
            "must_all_hold": [
                "canonical_ticker_exact_match",
                "legal_entity_exact_match",
                "predictor_fiscal_year_exact_match",
                "fiscal_year_end_exact_match",
                "annual_statement_not_interim",
                "audited_statement",
                "parent_company_identity",
                "statement_scope_compatible_with_canonical_row",
                "separate_non_consolidated_when_canonical_requires",
                "letter_code_compatible",
                "exact_letter_serial",
                "exact_canonical_letter_serial",
                "letter_serial_equals_canonical_letter_serial",
                "exact_tracing_no_when_canonical_tracing_no_present",
                "exact_official_title_nonempty_both_sides",
                "normalized_revision_status_in_frozen_provenance_enum",
                "values_source_letter_serial_equals_bound_serial_for_revision_or_restatement",
                "public_codal_url_recorded",
                "raw_payload_or_snapshot_hash_bound",
            ],
            "fail_closed": list(BINDING_FAIL_REASONS),
        },
        "source_version_and_revision_policy": {
            "each_letter_serial_is_independent_version": True,
            "normalized_revision_status_enum": sorted(NORMALIZED_REVISION_STATUS),
            "normalized_revision_status_matches_frozen_provenance_schema": True,
            "correction_is_not_a_normalized_revision_status": True,
            "codal_eslahiye_raw_field": "revision_status_raw",
            "codal_eslahiye_maps_to_revision_only_when_explicit": True,
            "restatement_only_when_source_version_evidence_supports": True,
            "missing_or_unclassifiable_revision_status_is_unresolved": True,
            "exact_values_source_serial_binding_authoritative": True,
            "boolean_flags_cannot_bypass_identifier_mismatch": True,
            "publish_of_original_used_for_correction_values_is_redundant_audit_only": True,
            "rules": [
                "original_revision_restatement_never_overwrite_each_other",
                "each_version_has_independent_provenance_record",
                "cutoff_taken_only_from_version_that_supplied_canonical_predictor_values",
                "values_source_letter_serial_must_equal_letter_serial_and_canonical_letter_serial_for_revision_or_restatement",
                "if_canonical_row_from_revision_or_restatement_then_available_at_is_that_exact_LetterSerial_PublishDateTime",
                "if_exact_source_version_identifiers_unbound_then_available_at_null_cutoff_UNRESOLVED",
                "multi_document_predictor_row_requires_separate_adjudication",
            ],
            "multi_document_reason_code": REASON_MULTI_DOCUMENT,
            "no_new_earliest_or_max_rule_invented": True,
            "frozen_cut_a_without_new_decision": True,
        },
        "timezone_and_normalization": {
            "raw_preserved_format": "YYYY/MM/DD HH:MM:SS Persian digits Jalali",
            "steps": [
                "persian_digits_to_ascii",
                "jalali_to_gregorian_via_project_canonical_jdatetime",
                "source_local_timezone_Asia_Tehran_via_zoneinfo",
                "utc_round_trip_fold0_and_fold1_wall_time_classification",
                "timezone_aware_datetime_required",
                "convert_to_UTC",
                "ISO-8601_UTC_output",
            ],
            "wall_time_classification": {
                "neither_fold_round_trips": REASON_NONEXISTENT_LOCAL,
                "both_folds_round_trip_different_utc": REASON_AMBIGUOUS_LOCAL,
                "exactly_one_fold_round_trips": "valid_use_that_fold",
                "both_folds_round_trip_same_instant": "valid_non_ambiguous",
            },
            "forbidden": [
                "fixed_offset_plus_0330_for_all_years",
                "naive_datetime_as_available_at",
                "classify_nonexistent_spring_forward_as_ambiguous",
            ],
            "fail_closed_to_null": [
                "malformed_jalali_date",
                "invalid_time",
                "nonexistent_local_time",
                "ambiguous_local_time_without_deterministic_documented_rule",
                "missing_timezone_library_or_data",
                "naive_datetime",
                "impossible_calendar_conversion",
            ],
            "timezone": TEHRAN_TZ_NAME,
            "calendar_library": "jdatetime",
            "calendar_library_pin": "jdatetime==6.0.1",
        },
        "implementation_scope": {
            "allowed": [
                "schema",
                "contracts",
                "pure_parsers",
                "synthetic_validators",
            ],
            "forbidden": [
                "codal_network",
                "tsetmc_network",
                "cbi_network",
                "real_timestamp_assignment_to_pilot_pairs",
                "mutation_of_prediction_cutoff_audit_stage125_part2_csv",
                "dataset_mutation",
                "candidate_or_pair_evidence_capture",
                "real_data_extraction",
                "accessibility_scoring",
                "real_gate_application",
                "candidate_admit_reject",
                "part3b_completion",
                "stage126",
                "modeling",
            ],
            "local_cache_read_only_for_regression_vocabulary": True,
            "local_cache_must_not_become_real_row_admission": True,
        },
        "real_available_at_assignment_authorized": False,
        "real_cutoff_resolution_authorized": False,
        "network_access_authorized": False,
        "synthetic_validation_only": True,
    }


def build_decision_lock_record(contract: dict) -> dict:
    return {
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "qc_scope": QC_STAGE,
        "decision_lock_version": DECISION_LOCK_VERSION,
        "status": "cut_a_available_at_operationalization_locked_contracts_only",
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "cut_a_available_at_operationalization_locked": True,
        "part3b1_decision_locked": True,
        "part3b_started": True,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "modeling_started": False,
        "part3b2_started": False,
        "stage126_started": False,
        "research_pointers_unchanged": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "locked_decisions": {
            "operational_available_at_source_field": "PublishDateTime",
            "sent_datetime_is_available_at": False,
            "exact_document_binding_required": True,
            "each_letter_serial_independent_version": True,
            "normalized_revision_status_enum": sorted(NORMALIZED_REVISION_STATUS),
            "exact_values_source_serial_binding_authoritative": True,
            "tehran_wall_time_utc_round_trip_classification": True,
            "timezone": TEHRAN_TZ_NAME,
            "multi_document_reason_code": REASON_MULTI_DOCUMENT,
        },
        "contract_file": F_CONTRACT,
        "contract_version": contract["contract_version"],
        "explicit_non_claims": [
            "maintenance_decision_lock_only",
            "synthetic_validation_only",
            "zero_network_calls",
            "zero_real_available_at_assignments",
            "zero_resolved_pilot_cutoffs",
            "zero_candidate_values",
            "zero_pair_values",
            "zero_accessibility_scores",
            "zero_gate_admissions",
            "no_part3b_completion",
            "no_part3b2",
            "no_stage126",
            "no_modeling",
            "research_pointers_unchanged",
            "merge_requires_explicit_user_approval",
        ],
        "real_pilot_rows_assigned": 0,
        "resolved_pilot_cutoffs": 0,
    }


def build_readme() -> str:
    return """# Stage125 Part 3B.1A — CUT-A Available-at Operationalization Lock

**Status:** maintenance decision lock only (schema / pure parsers / synthetic validation).

## What is locked

For a predictor-year financial-statement row `t`:

```text
operational available_at =
  PublishDateTime of the exact matched official CODAL LetterSerial/version
```

only when the official document is exactly bound to the predictor row **and** the
canonical source version.

## SentDateTime

`SentDateTime != available_at`.

- preserved raw for audit/comparison only
- never used as cutoff or public availability
- even when equal to `PublishDateTime`, mapping still uses `PublishDateTime`

## Why PublishDateTime

- operational public-release timestamp in this project
- `SentDateTime` may be publisher-send time and does not prove public availability
- more conservative / leakage-safe than `SentDateTime`
- methodological operationalization lock — not inference from local filenames/mtimes

## Normalized revision vocabulary

Normalized `revision_status` matches the frozen provenance schema enum only:

```text
original
revision
restatement
```

`correction` is **not** a normalized status. CODAL «اصلاحیه» may be retained in
`revision_status_raw`; it maps to normalized `revision` only when that mapping is
explicit. `restatement` is used only when source/version evidence supports it.
Missing/unclassifiable status → `UNRESOLVED`.

## Exact source-version binding

Authoritative structural checks (boolean flags cannot bypass):

- non-empty `letter_serial` and `canonical_letter_serial` with exact equality
- if `canonical_tracing_no` is present, `tracing_no` must be present and equal
- non-empty official titles on both sides with exact equality
- for `revision` / `restatement`:
  `values_source_letter_serial == letter_serial == canonical_letter_serial`
- official URL and raw payload/snapshot hash present

## Asia/Tehran wall time

Jalali CODAL timestamps are classified with UTC round-trips over `fold=0` and
`fold=1` (`zoneinfo` `Asia/Tehran`). Nonexistent spring-forward times are
`nonexistent_local_time` (not ambiguous). Ambiguous fall-back times without a
deterministic fold rule are
`ambiguous_local_time_without_deterministic_rule`. No fixed `+03:30`.

## Non-claims

- no CODAL / TSETMC / CBI network
- no real `available_at` assignment
- no pilot cutoff resolution
- no extraction / scoring / Gate admission
- no Part 3B.2 / Stage126 / modeling
- research pointers remain
  `last_completed_research_action_id=stage125-part3a-decision-lock`,
  `next_research_action_id=stage125-part3b-evidence-capture`

## Marker

`cut_a_available_at_operationalization_locked=true`

`part3b_completed` remains `false`.
"""


# --------------------------------------------------------------------------- #
# Build / QC
# --------------------------------------------------------------------------- #

def build_all(_repo_root: Path) -> dict[str, str]:
    contract = build_operationalization_contract()
    lock = build_decision_lock_record(contract)
    return {
        F_CONTRACT: _json_str(contract),
        F_LOCK: _json_str(lock),
        F_README: build_readme(),
    }


def _synth_qc_checks() -> list[tuple[str, bool, str]]:
    """Machine-checkable synthetic assertions embedded in the QC report."""
    checks: list[tuple[str, bool, str]] = []

    # 1) PublishDateTime mapping success with exact bound LetterSerial
    ok_bind = synthetic_valid_binding()
    r = resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=ok_bind,
    )
    checks.append((
        "synth_publish_mapping_success",
        r.available_at is not None
        and r.source_field == "PublishDateTime"
        and r.cutoff_status == CUTOFF_STATUS_RESOLVED,
        f"available_at={r.available_at}",
    ))

    # 2) SentDateTime never availability
    r2 = resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=ok_bind,
        force_use_sent_as_availability=True,
    )
    checks.append((
        "synth_sent_never_availability",
        r2.available_at is None
        and REASON_SENT_USED_AS_AVAILABILITY in r2.reasons,
        str(r2.reasons),
    ))

    # 3) Sent == Publish still selects Publish
    r3 = resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 10:30:00",
        binding=ok_bind,
    )
    checks.append((
        "synth_equal_still_publish",
        r3.source_field == "PublishDateTime"
        and r3.sent_publish_relation == "equal"
        and r3.available_at is not None,
        r3.source_field or "none",
    ))

    # 4) Sent before Publish → cutoff from Publish
    r4 = resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/14 18:00:00",
        binding=ok_bind,
    )
    checks.append((
        "synth_sent_before_publish_uses_publish",
        r4.sent_publish_relation == "sent_before_publish"
        and r4.source_field == "PublishDateTime"
        and r4.available_at is not None,
        r4.sent_publish_relation,
    ))

    # 5) Sent after Publish → inconsistency, no fallback
    r5 = resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/16 08:00:00",
        binding=ok_bind,
    )
    checks.append((
        "synth_sent_after_publish_unresolved",
        r5.available_at is None
        and r5.cutoff_status == CUTOFF_STATUS_UNRESOLVED
        and REASON_SENT_AFTER_PUBLISH in r5.reasons,
        str(r5.reasons),
    ))

    # 6) malformed → null
    r6 = resolve_operational_available_at(
        publish_datetime_raw="not-a-date",
        sent_datetime_raw=None,
        binding=ok_bind,
    )
    checks.append((
        "synth_malformed_null",
        r6.available_at is None and REASON_MALFORMED_PUBLISH in r6.reasons,
        str(r6.reasons),
    ))

    # 7) missing → null
    r7 = resolve_operational_available_at(
        publish_datetime_raw=None,
        sent_datetime_raw=None,
        binding=ok_bind,
    )
    checks.append((
        "synth_missing_null",
        r7.available_at is None and REASON_MISSING_PUBLISH in r7.reasons,
        str(r7.reasons),
    ))

    # 8) Persian digits
    parsed_fa = parse_codal_publish_datetime("۱۴۰۰/۰۱/۱۵ ۱۰:۳۰:۰۰")
    parsed_en = parse_codal_publish_datetime("1400/01/15 10:30:00")
    checks.append((
        "synth_persian_digit_normalization",
        isinstance(parsed_fa, NormalizedTimestamp)
        and isinstance(parsed_en, NormalizedTimestamp)
        and parsed_fa.utc_iso8601 == parsed_en.utc_iso8601,
        getattr(parsed_fa, "utc_iso8601", str(parsed_fa)),
    ))

    # 9) Jalali conversion (1400/01/01 12:00:00 → 2021-03-21)
    parsed_j = parse_codal_publish_datetime("1400/01/01 12:00:00")
    checks.append((
        "synth_jalali_conversion",
        isinstance(parsed_j, NormalizedTimestamp)
        and parsed_j.utc.year == 2021
        and parsed_j.utc.month == 3
        and parsed_j.utc.day == 21,
        getattr(parsed_j, "utc_iso8601", str(parsed_j)),
    ))

    # 10) historical Asia/Tehran (DST in 1400/06 vs no DST in 1400/01)
    p_winter = parse_codal_publish_datetime("1400/01/01 12:00:00")
    p_summer = parse_codal_publish_datetime("1400/06/01 12:00:00")
    checks.append((
        "synth_historical_tehran_timezone",
        isinstance(p_winter, NormalizedTimestamp)
        and isinstance(p_summer, NormalizedTimestamp)
        and p_winter.local_tehran.utcoffset() != p_summer.local_tehran.utcoffset(),
        "winter/summer offsets differ",
    ))

    # 11) naive datetime rejected
    checks.append((
        "synth_naive_datetime_rejected",
        reject_naive_datetime(datetime(2021, 3, 21, 12, 0, 0)) is False
        and reject_naive_datetime(
            datetime(2021, 3, 21, 12, 0, 0, tzinfo=timezone.utc)
        ) is True,
        "naive rejected",
    ))

    # Binding rejections 12–24
    cases = [
        ("synth_subsidiary_rejected", {"subsidiary_only_title": True},
         "subsidiary_only_title"),
        ("synth_interim_rejected", {"is_interim": True, "is_annual": False},
         "interim_statement"),
        ("synth_unaudited_rejected", {"is_audited": False}, "unaudited_statement"),
        ("synth_fye_mismatch_rejected",
         {"fiscal_year_end_letter": "1399/12/29"}, "fiscal_year_end_mismatch"),
        ("synth_ticker_mismatch_rejected",
         {"letter_ticker": "اپال"}, "ticker_mismatch"),
        ("synth_entity_mismatch_rejected",
         {"legal_entity_letter": "دیگر"}, "entity_mismatch"),
        ("synth_scope_mismatch_rejected",
         {"statement_scope_letter": "consolidated"}, "statement_scope_mismatch"),
        ("synth_multiple_letterserial_unresolved",
         {"candidate_letter_serials": ["A", "B"]}, "multiple_candidate_letters"),
        ("synth_incomplete_cache_unresolved",
         {"incomplete_pagination": True, "canonical_letter_serial": None,
          "letter_serial": None},
         "incomplete_pagination_without_canonical_letter_serial"),
        ("synth_unknown_revision_unresolved",
         {"revision_status": "unknown"}, "unknown_revision_status"),
        ("synth_correction_not_normalized_status",
         {"revision_status": "correction"}, "unknown_revision_status"),
        ("synth_multi_document_unresolved",
         {"multi_document_predictor_row": True}, REASON_MULTI_DOCUMENT),
        ("synth_missing_canonical_letter_serial",
         {"canonical_letter_serial": None}, REASON_MISSING_CANONICAL_LETTER_SERIAL),
        ("synth_letter_serial_mismatch",
         {"letter_serial": "A1", "canonical_letter_serial": "B2",
          "values_source_letter_serial": "A1",
          "candidate_letter_serials": ["A1"]},
         "letter_serial_mismatch"),
        ("synth_missing_required_tracing_no",
         {"tracing_no": None, "canonical_tracing_no": "T-9"},
         REASON_MISSING_REQUIRED_TRACING_NO),
        ("synth_tracing_no_mismatch",
         {"tracing_no": "T-1", "canonical_tracing_no": "T-9"},
         "tracing_no_mismatch"),
        ("synth_revision_values_source_serial_differs",
         {"revision_status": "revision",
          "revision_status_raw": CODAL_ESLAHIYE_RAW,
          "letter_serial": "REV9",
          "canonical_letter_serial": "REV9",
          "candidate_letter_serials": ["REV9"],
          "values_source_letter_serial": "ORIG1"},
         REASON_VALUES_SOURCE_SERIAL_MISMATCH),
        ("synth_restatement_values_source_serial_differs",
         {"revision_status": "restatement",
          "letter_serial": "RST9",
          "canonical_letter_serial": "RST9",
          "candidate_letter_serials": ["RST9"],
          "values_source_letter_serial": "ORIG1"},
         REASON_VALUES_SOURCE_SERIAL_MISMATCH),
        ("synth_boolean_cannot_bypass_serial_mismatch",
         {"letter_serial": "A1", "canonical_letter_serial": "B2",
          "values_source_letter_serial": "A1",
          "candidate_letter_serials": ["A1"],
          "canonical_source_version_bound": True,
          "publish_of_original_used_for_correction_values": False},
         "letter_serial_mismatch"),
    ]
    for name, overrides, needle in cases:
        res = resolve_operational_available_at(
            publish_datetime_raw="1400/01/15 10:30:00",
            sent_datetime_raw=None,
            binding=synthetic_valid_binding(**overrides),
        )
        checks.append((
            name,
            res.available_at is None
            and res.cutoff_status == CUTOFF_STATUS_UNRESOLVED
            and any(needle in x for x in res.reasons),
            str(res.reasons),
        ))

    # Exact revision / restatement / original bindings
    rev = resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=synthetic_valid_binding(
            revision_status="revision",
            revision_status_raw=CODAL_ESLAHIYE_RAW,
            letter_serial="REV9",
            canonical_letter_serial="REV9",
            candidate_letter_serials=["REV9"],
            values_source_letter_serial="REV9",
            canonical_source_version_bound=True,
        ),
    )
    checks.append((
        "synth_exact_revision_binding",
        rev.available_at is not None and rev.source_field == "PublishDateTime",
        str(rev.available_at),
    ))

    rest = resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=synthetic_valid_binding(
            revision_status="restatement",
            letter_serial="RST9",
            canonical_letter_serial="RST9",
            candidate_letter_serials=["RST9"],
            values_source_letter_serial="RST9",
        ),
    )
    checks.append((
        "synth_exact_restatement_binding",
        rest.available_at is not None and rest.source_field == "PublishDateTime",
        str(rest.available_at),
    ))

    checks.append((
        "synth_exact_original_binding",
        r.available_at is not None and r.source_field == "PublishDateTime",
        str(r.available_at),
    ))

    # Explicit اصلاحیه → revision mapping (test-backed); never silent restatement.
    mapped = explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=CODAL_ESLAHIYE_RAW,
        map_eslahiye_to_revision=True,
    )
    unmapped = explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=CODAL_ESLAHIYE_RAW,
        map_eslahiye_to_revision=False,
    )
    checks.append((
        "synth_eslahiye_explicit_map_to_revision",
        mapped == "revision" and unmapped is None,
        f"mapped={mapped} unmapped={unmapped}",
    ))

    # Historical Tehran gap / fold classification (Gregorian walls → Jalali via jdatetime)
    gap_jalali = jalali_string_from_tehran_gregorian_wall(2021, 3, 22, 0, 0, 0)
    fold_jalali = jalali_string_from_tehran_gregorian_wall(2021, 9, 21, 23, 0, 0)
    pre_gap = jalali_string_from_tehran_gregorian_wall(2021, 3, 21, 23, 0, 0)
    post_gap = jalali_string_from_tehran_gregorian_wall(2021, 3, 22, 1, 0, 0)
    post_dst = jalali_string_from_tehran_gregorian_wall(2024, 3, 22, 0, 0, 0)
    p_gap = parse_codal_publish_datetime(gap_jalali)
    p_fold = parse_codal_publish_datetime(fold_jalali)
    p_pre = parse_codal_publish_datetime(pre_gap)
    p_post = parse_codal_publish_datetime(post_gap)
    p_abolition = parse_codal_publish_datetime(post_dst)
    checks.append((
        "synth_historical_nonexistent_tehran_time",
        isinstance(p_gap, TimestampParseFailure)
        and p_gap.reason == REASON_NONEXISTENT_LOCAL,
        f"{gap_jalali}->{getattr(p_gap, 'reason', p_gap)}",
    ))
    checks.append((
        "synth_historical_ambiguous_tehran_time",
        isinstance(p_fold, TimestampParseFailure)
        and p_fold.reason == REASON_AMBIGUOUS_LOCAL,
        f"{fold_jalali}->{getattr(p_fold, 'reason', p_fold)}",
    ))
    checks.append((
        "synth_pre_transition_timestamp_resolves",
        isinstance(p_pre, NormalizedTimestamp),
        getattr(p_pre, "utc_iso8601", str(p_pre)),
    ))
    checks.append((
        "synth_post_transition_timestamp_resolves",
        isinstance(p_post, NormalizedTimestamp),
        getattr(p_post, "utc_iso8601", str(p_post)),
    ))
    checks.append((
        "synth_post_dst_abolition_no_fabricated_fold",
        isinstance(p_abolition, NormalizedTimestamp)
        and p_abolition.local_tehran.fold == 0,
        getattr(p_abolition, "utc_iso8601", str(p_abolition)),
    ))
    gap_res = resolve_operational_available_at(
        publish_datetime_raw=gap_jalali,
        sent_datetime_raw=None,
        binding=ok_bind,
    )
    fold_res = resolve_operational_available_at(
        publish_datetime_raw=fold_jalali,
        sent_datetime_raw=None,
        binding=ok_bind,
    )
    checks.append((
        "synth_gap_fold_failures_null_available_at",
        gap_res.available_at is None
        and fold_res.available_at is None
        and REASON_NONEXISTENT_LOCAL in gap_res.reasons
        and REASON_AMBIGUOUS_LOCAL in fold_res.reasons,
        f"gap={gap_res.reasons} fold={fold_res.reasons}",
    ))

    # Redundant audit flag still fails closed, but Serial equality is authoritative.
    bad_audit = resolve_operational_available_at(
        publish_datetime_raw="1400/01/01 10:00:00",
        sent_datetime_raw=None,
        binding=synthetic_valid_binding(
            revision_status="revision",
            revision_status_raw=CODAL_ESLAHIYE_RAW,
            letter_serial="REV9",
            canonical_letter_serial="REV9",
            candidate_letter_serials=["REV9"],
            values_source_letter_serial="REV9",
            publish_of_original_used_for_correction_values=True,
        ),
    )
    checks.append((
        "synth_redundant_audit_flag_still_fail_closed",
        bad_audit.available_at is None
        and REASON_CORRECTION_USES_ORIGINAL in bad_audit.reasons,
        str(bad_audit.reasons),
    ))

    checks.append((
        "synth_no_pilot_row_assignment",
        r.real_pilot_row_assigned is False,
        "real_pilot_row_assigned=false",
    ))

    return checks


def build_qc_assertions(
    repo_root: Path,
    content: dict[str, str],
    frozen: dict[str, str],
    *,
    network_calls_attempted: int,
) -> list[dict]:
    assertions: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    lock = json.loads(content[F_LOCK])
    contract = json.loads(content[F_CONTRACT])

    add("baseline_commit_constant",
        EXPECTED_BASELINE_COMMIT == "3a54a79c935f27e311679e8582e4c46330590a43",
        EXPECTED_BASELINE_COMMIT)
    add("decision_lock_only",
        lock.get("status") == (
            "cut_a_available_at_operationalization_locked_contracts_only"
        ),
        lock.get("status", ""))
    add("cut_a_available_at_operationalization_locked",
        lock.get("cut_a_available_at_operationalization_locked") is True, "locked")
    add("part3b1_decision_locked_preserved",
        lock.get("part3b1_decision_locked") is True, "preserved")
    add("part3b_started_preserved",
        lock.get("part3b_started") is True, "preserved")
    add("predictor_available_at_evidence_collected_false",
        lock.get("predictor_available_at_evidence_collected") is False, "false")
    add("pilot_cutoff_provenance_resolved_false",
        lock.get("pilot_cutoff_provenance_resolved") is False, "false")
    add("candidate_value_evidence_collected_false",
        lock.get("candidate_value_evidence_collected") is False, "false")
    add("pair_level_evidence_collected_false",
        lock.get("pair_level_evidence_collected") is False, "false")
    add("data_value_extraction_performed_false",
        lock.get("data_value_extraction_performed") is False, "false")
    add("accessibility_scoring_applied_false",
        lock.get("accessibility_scoring_applied") is False, "false")
    add("part3b_completed_false", lock.get("part3b_completed") is False, "false")
    add("modeling_started_false", lock.get("modeling_started") is False, "false")
    add("zero_network_calls", network_calls_attempted == 0,
        f"calls={network_calls_attempted}")
    add("zero_real_available_at_assignments",
        lock.get("real_pilot_rows_assigned") == 0, "0")
    add("zero_resolved_pilot_cutoffs",
        lock.get("resolved_pilot_cutoffs") == 0, "0")
    add("publish_is_source_field",
        contract["operational_available_at"]["source_field"] == "PublishDateTime",
        "PublishDateTime")
    add("sent_not_availability",
        contract["operational_available_at"]["sent_datetime_policy"][
            "sent_datetime_is_available_at"
        ] is False,
        "sent!=available_at")
    add("timezone_asia_tehran",
        contract["timezone_and_normalization"]["timezone"] == TEHRAN_TZ_NAME,
        TEHRAN_TZ_NAME)
    add("no_fixed_offset_all_years",
        "fixed_offset_plus_0330_for_all_years"
        in contract["timezone_and_normalization"]["forbidden"],
        "no fixed +03:30")
    rev_pol = contract["source_version_and_revision_policy"]
    add("normalized_revision_enum_matches_frozen_provenance_schema",
        rev_pol.get("normalized_revision_status_enum")
        == sorted(NORMALIZED_REVISION_STATUS)
        and rev_pol.get("normalized_revision_status_matches_frozen_provenance_schema")
        is True,
        str(rev_pol.get("normalized_revision_status_enum")))
    add("correction_not_emitted_as_normalized_revision_status",
        rev_pol.get("correction_is_not_a_normalized_revision_status") is True
        and "correction" not in set(rev_pol.get("normalized_revision_status_enum") or []),
        "correction excluded")
    add("exact_values_source_serial_binding",
        rev_pol.get("exact_values_source_serial_binding_authoritative") is True
        and REASON_VALUES_SOURCE_SERIAL_MISMATCH in BINDING_FAIL_REASONS,
        REASON_VALUES_SOURCE_SERIAL_MISMATCH)
    add("missing_canonical_serial_rejected",
        REASON_MISSING_CANONICAL_LETTER_SERIAL in BINDING_FAIL_REASONS,
        REASON_MISSING_CANONICAL_LETTER_SERIAL)
    add("missing_required_tracing_no_rejected",
        REASON_MISSING_REQUIRED_TRACING_NO in BINDING_FAIL_REASONS,
        REASON_MISSING_REQUIRED_TRACING_NO)
    add("canonical_jdatetime_pin_documented",
        contract["timezone_and_normalization"].get("calendar_library_pin")
        == "jdatetime==6.0.1",
        str(contract["timezone_and_normalization"].get("calendar_library_pin")))
    try:
        from importlib.metadata import version as _pkg_version
        _jd_ver = _pkg_version("jdatetime")
    except Exception as exc:  # pragma: no cover - environment contract
        _jd_ver = f"unavailable:{exc}"
    add("canonical_jdatetime_runtime_pin",
        _jd_ver == "6.0.1",
        f"jdatetime=={_jd_ver}")
    add("multi_document_reason_locked",
        rev_pol["multi_document_reason_code"] == REASON_MULTI_DOCUMENT,
        REASON_MULTI_DOCUMENT)
    add("frozen_cut_a_unchanged",
        contract.get("frozen_cut_a_unchanged") is True, "unchanged")
    add("research_pointers_unchanged",
        lock["research_pointers_unchanged"]["last_completed_research_action_id"]
        == RESEARCH_LAST_COMPLETED
        and lock["research_pointers_unchanged"]["next_research_action_id"]
        == RESEARCH_NEXT,
        "research pointers fixed")
    add("no_part3b2", lock.get("part3b2_started") is False, "false")
    add("no_stage126", lock.get("stage126_started") is False, "false")
    add("synthetic_validation_only",
        contract.get("synthetic_validation_only") is True, "synthetic")
    add("network_not_authorized",
        contract.get("network_access_authorized") is False, "false")
    add("frozen_scientific_present",
        len(frozen) == len(FROZEN_SCIENTIFIC_PATHS), f"n={len(frozen)}")
    add("content_exact_allowlist",
        set(content) == set(CONTENT_FILES), f"keys={sorted(content)}")
    forbidden_present = [
        rel for rel in FORBIDDEN_SURFACE_EXACT if (repo_root / rel).exists()
    ]
    add("no_part3b2_or_stage126_surfaces", not forbidden_present,
        f"forbidden={forbidden_present}")

    for name, ok, detail in _synth_qc_checks():
        add(name, ok, detail)

    return assertions


def build_qc_report(
    repo_root: Path,
    content: dict[str, str],
    content_hashes: dict[str, str],
    frozen: dict[str, str],
    *,
    network_calls_attempted: int,
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL, RUN_REL])
    ts = _git_commit_timestamp(root, source_commit)
    assertions = build_qc_assertions(
        repo_root, content, frozen,
        network_calls_attempted=network_calls_attempted,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")

    # Tickers from Part 3B QC (scope continuity); no new admission.
    part3b_qc_path = (
        repo_root / "project/stage125/stage125_part3b_evidence_capture_qc_report.json"
    )
    tickers: list[str] = []
    if part3b_qc_path.is_file():
        part3b_qc = json.loads(part3b_qc_path.read_text(encoding="utf-8"))
        tickers = list(part3b_qc.get("tickers") or [])

    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": sha256_file(repo_root / TEST_REL),
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_scientific_sha256": dict(sorted(frozen.items())),
        "decision_lock_only": True,
        "synthetic_validation_only": True,
        "zero_network_calls": network_calls_attempted == 0,
        "zero_real_available_at_assignments": True,
        "zero_resolved_pilot_cutoffs": True,
        "zero_candidate_values": True,
        "zero_pair_values": True,
        "zero_accessibility_scores": True,
        "zero_gate_admissions": True,
        "no_part3b_completion": True,
        "no_modeling": True,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "network_extraction_performed": True,
        "part3b1a_network_calls_attempted": network_calls_attempted,
        "modeling_started": False,
        "part3b2_started": False,
        "stage126_started": False,
        "decision_lock_version": DECISION_LOCK_VERSION,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "assertions": assertions,
    }


def build_metadata(qc: dict, content_hashes: dict[str, str], qc_hash: str) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage125 Part 3B.1A — CUT-A available-at operationalization lock "
            "(contracts + synthetic validation only)."
        ),
        "generated_at": qc["generated_at"],
        "code_commit": qc["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "part3b_completed": False,
        "part3b1_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "part3b1a_network_calls_attempted": qc["part3b1a_network_calls_attempted"],
    }


def run(project_dir: Path, output_dir: Path | None = None, write: bool = False) -> dict:
    from src import stage125_part3b0_evidence_readiness as p3b0

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    out_dir = output_dir or (repo_root / "project" / "stage125")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    verify_baseline_commit(str(repo_root))

    with p3b0.network_sentinel() as sentinel:
        frozen = frozen_scientific_hashes(repo_root)
        content = build_all(repo_root)
        content_hashes = {
            name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
        }
        qc = build_qc_report(
            repo_root, content, content_hashes, frozen,
            network_calls_attempted=sentinel.calls_attempted,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)

        drift: list[str] = []
        for name, text in list(content.items()) + [(F_QC, qc_text), (F_METADATA, meta_text)]:
            path = out_dir / name
            if path.is_file():
                if path.read_text(encoding="utf-8") != text:
                    drift.append(name)
            else:
                drift.append(name)

        files_written: dict[str, str] = {}
        if write:
            for name, text in content.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = content_hashes[name]
            (out_dir / F_QC).write_text(qc_text, encoding="utf-8")
            (out_dir / F_METADATA).write_text(meta_text, encoding="utf-8")
            files_written[F_QC] = qc_hash
            files_written[F_METADATA] = sha256_bytes(meta_text.encode("utf-8"))

        if not qc["all_pass"]:
            failed = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:3]}")

        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"Part 3B.1A network sentinel calls_attempted="
                f"{sentinel.calls_attempted}"
            )

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "frozen_scientific_sha256": frozen,
        "network_calls_attempted": 0,
    }


# Re-export dataclass helper for tests/debugging.
def resolution_as_dict(res: AvailableAtResolution) -> dict:
    return asdict(res)
