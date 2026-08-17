"""Tests for the Stage130 Phase 2 manuscript directory.

These tests run the focused acceptance checks in `validate_manuscript.py` and add
a small number of structural assertions about the deliverables. They compute no
scientific quantity, read no Final Test row and never open the row-level
prediction artifact.
"""
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

import pytest

MS_DIR = Path(__file__).resolve().parent
ROOT = MS_DIR.parents[1]
PKG = ROOT / "stage130" / "manuscript_evidence_package"

REQUIRED_SECTIONS = [
    "## Structured Abstract",
    "## Keywords",
    "## 1. Introduction",
    "## 2. Literature Review and Conceptual Motivation",
    "## 3. Institutional Context of the Tehran Stock Exchange",
    "## 4. Data and Sample",
    "## 5. Financial-Distress Target Construction",
    "## 6. Point-in-Time Predictor Architecture",
    "## 7. Leakage-Safe Temporal Validation and Empirical Design",
    "## 8. Development and Robustness Evidence",
    "## 9. Incremental Information Blocks M2–M4 and Their Dispositions",
    "## 10. Locked Final Test Results",
    "## 11. Model Interpretation",
    "## 12. Discussion",
    "## 13. Limitations",
    "## 14. Conclusion",
    "## 15. Reproducibility and Data/Code Availability",
    "## 16. References",
    "## 17. Table and Figure Callouts",
]

MATRIX_COLUMNS = [
    "claim_id", "manuscript_section", "manuscript_claim", "canonical_source_path",
    "canonical_source_field_or_row", "exact_committed_value", "source_sha256",
    "limitation_present", "status",
]

AUDIT_COLUMNS = [
    "citation_key", "title", "authors", "year", "journal_or_publisher", "DOI",
    "DOI_resolves", "authoritative_url", "source_type", "manuscript_role",
    "verification_status",
]


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "stage130_validate_manuscript", MS_DIR / "validate_manuscript.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def draft() -> str:
    return (MS_DIR / "manuscript_draft_en.md").read_text(encoding="utf-8")


def test_all_deliverables_exist():
    for name in ("manuscript_draft_en.md", "claim_traceability_matrix.csv",
                 "references.bib", "reference_audit.csv", "README.md",
                 "validate_manuscript.py"):
        assert (MS_DIR / name).is_file(), name


def test_manuscript_has_every_required_section(draft):
    missing = [s for s in REQUIRED_SECTIONS if s not in draft]
    assert not missing, missing


def test_manuscript_has_a_title_line(draft):
    assert draft.lstrip().startswith("# "), "manuscript must open with a title"


def test_acceptance_checks_pass():
    module = _load_validator()
    assert module.main() == 0


def test_traceability_matrix_schema_and_content():
    with (MS_DIR / "claim_traceability_matrix.csv").open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == MATRIX_COLUMNS
        rows = list(reader)
    assert rows, "traceability matrix must not be empty"
    ids = [r["claim_id"] for r in rows]
    assert len(ids) == len(set(ids)), "claim ids must be unique"
    for row in rows:
        assert re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"]), row["claim_id"]
        assert row["limitation_present"] in {"yes", "no"}, row["claim_id"]
        assert row["status"].startswith("TRACED"), row["claim_id"]
        assert row["manuscript_claim"].strip(), row["claim_id"]
        assert row["exact_committed_value"].strip(), row["claim_id"]


def test_reference_audit_schema_and_verification():
    with (MS_DIR / "reference_audit.csv").open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == AUDIT_COLUMNS
        rows = list(reader)
    assert rows, "reference audit must not be empty"
    for row in rows:
        assert row["verification_status"].startswith("VERIFIED"), row["citation_key"]
        assert row["title"].strip() and row["authors"].strip() and row["year"].strip()
        assert row["authoritative_url"].startswith("http"), row["citation_key"]
        if row["DOI"]:
            assert row["DOI_resolves"] == "true", row["citation_key"]


def test_no_fabricated_or_empty_bibliographic_fields():
    """Every bib entry must carry author, title, year and a locator."""
    text = (MS_DIR / "references.bib").read_text(encoding="utf-8")
    entries = re.findall(r"@\w+\{([^,]+),(.*?)\n\}", text, flags=re.S)
    assert entries, "bibliography must contain entries"
    for key, body in entries:
        for field in ("author", "title", "year"):
            assert re.search(rf"\n\s*{field}\s*=", body), f"{key} missing {field}"
        assert re.search(r"\n\s*(doi|url)\s*=", body), f"{key} has no DOI or URL"


def test_phase1_package_is_byte_identical():
    module = _load_validator()
    import json
    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    for rel, meta in manifest["package_files"].items():
        path = PKG / rel
        assert path.is_file(), rel
        assert module.sha256(path) == meta["sha256"], rel


def test_protected_pinned_sources_are_unchanged():
    module = _load_validator()
    import json
    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    for rel, digest in manifest["source_sha256"].items():
        path = ROOT.parent / rel
        assert path.is_file(), rel
        assert module.sha256(path) == digest, rel


def test_no_forbidden_source_is_referenced():
    module = _load_validator()
    draft_text = (MS_DIR / "manuscript_draft_en.md").read_text(encoding="utf-8")
    matrix_text = (MS_DIR / "claim_traceability_matrix.csv").read_text(encoding="utf-8")
    for bad in module.FORBIDDEN_SOURCES:
        assert bad not in draft_text, bad
        assert bad not in matrix_text, bad


def test_manuscript_directory_contains_no_figure_or_data_artifact():
    """This action produced prose and audit files only."""
    unexpected = [p.name for p in MS_DIR.iterdir()
                  if p.suffix.lower() in {".svg", ".png", ".pdf", ".jpg", ".jpeg", ".json", ".parquet"}]
    assert not unexpected, unexpected
