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


def _load_json(path: Path):
    import json
    return json.loads(path.read_text(encoding="utf-8"))


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
    # End matter, deliberately unnumbered: captions are not a results section.
    "## Table and Figure Captions/Callouts",
]

MATRIX_COLUMNS = [
    "claim_id", "manuscript_section", "scope", "manuscript_claim",
    "canonical_source_path", "canonical_source_field_or_row",
    "exact_committed_value", "source_sha256", "limitation_present", "status",
]

#: A claim about the panel, a modelling pair, the fit set and the Final Test are
#: four different populations. Every traceability row must say which one it is
#: talking about, drawn from this closed vocabulary.
SCOPE_LABELS = {
    "upstream_source_panel", "stage122_target_qc", "model_eligible_pairs",
    "development_fit_set", "development_out_of_fold", "final_test_cohort",
    "temporal_design", "outcome_definition", "prespecified_analysis_plan",
    "block_governance", "repository_provenance",
}

EXACT_TITLE = (
    "# Auditable Data Construction and Incremental Information in "
    "Financial-Distress Prediction: Leakage-Constrained Evidence from the "
    "Tehran Stock Exchange"
)

REQUIRED_KEYWORDS = ("data provenance", "reproducible research")

#: Unqualified wording that the audited record does not support. None of these
#: is rescued by a negation: the claim itself is what must not be made.
BANNED_DATA_CLAIMS = (
    "high-quality dataset", "high quality dataset",
    "fully point-in-time verified", "complete row-level provenance",
    "all observations fully traceable", "open dataset", "open benchmark",
    "external validation", "independent validation",
    "deployment-ready", "well calibrated", "well-calibrated",
)

#: Committed Final Test values. This revision is a wording revision, so every
#: one of them must survive string-for-string.
FROZEN_SCIENTIFIC_STRINGS = (
    "0.243879669979", "0.053272572767", "0.541675572242",
    "0.907684630739", "0.787834897749", "0.97144045144",
    "0.071625345916", "0.053164118058", "0.092580775647",
    "0.03468208092485549", "0.426878838687",
    "0.666666666667", "6.407407407407", "0.2222222222222222",
    "0.445756964048", "0.40244183002", "0.356545008162",
)

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


def test_callouts_are_end_matter_not_a_numbered_results_section(draft):
    assert "## 17." not in draft
    assert "## Table and Figure Captions/Callouts" in draft
    assert "_End matter." in draft


def test_abstract_is_between_250_and_350_words(draft):
    module = _load_validator()
    body = re.sub(r"\[@[^\]]+\]", "", module.section(draft, "## Structured Abstract"))
    words = len(body.replace("**", "").split())
    assert 250 <= words <= 350, words


def test_keywords_are_exactly_seven_and_carry_the_data_contribution(draft):
    module = _load_validator()
    kws = [k.strip() for k in module.section(draft, "## Keywords").split(";")
           if k.strip()]
    assert len(kws) == 7, kws
    for required in REQUIRED_KEYWORDS:
        assert required in kws, required


def test_title_is_the_exact_approved_string(draft):
    assert draft.splitlines()[0] == EXACT_TITLE, draft.splitlines()[0]


def test_title_claims_no_verified_filing_dates(draft):
    title = draft.splitlines()[0].lower()
    for banned in ("point-in-time", "point in time", "filing date"):
        assert banned not in title, banned


def test_no_unqualified_data_quality_claim(draft):
    """Each phrase may survive only as an explicit disclaimer, never as a claim."""
    module = _load_validator()
    low = draft.lower()
    for phrase in BANNED_DATA_CLAIMS:
        for m in re.finditer(re.escape(phrase), low):
            assert module.is_negated(low, m.start()), (
                phrase, low[max(0, m.start() - 80): m.start() + 40])


def test_every_frozen_scientific_value_survives_string_for_string(draft):
    missing = [v for v in FROZEN_SCIENTIFIC_STRINGS if v not in draft]
    assert not missing, missing


def test_no_sha256_or_ft_control_in_the_journal_facing_narrative(draft):
    narrative = draft[: draft.index("## 16. References")]
    assert not re.search(r"\b[0-9a-f]{64}\b", narrative)
    assert not re.search(r"\bFT\d{2}\b", narrative)


def test_every_section_cross_reference_resolves(draft):
    numbered = {m.group(1) for m in re.finditer(r"^## (\d+)\. ", draft, re.M)}
    subs = {m.group(1) for m in re.finditer(r"^### (\d+\.\d+) ", draft, re.M)}
    unresolved = []
    for m in re.finditer(r"Section (\d+(?:\.\d+)?)", draft):
        ref = m.group(1)
        ok = ref in numbered if "." not in ref else ref in subs
        if not ok:
            unresolved.append(ref)
    assert not unresolved, sorted(set(unresolved))


def test_no_absolute_deployment_or_screening_recommendation(draft):
    module = _load_validator()
    low = draft.lower()
    for phrase in module.BANNED_OUTRIGHT:
        assert phrase not in low, phrase
    for phrase in module.REQUIRED_RESTRAINT:
        assert phrase in low, phrase


def test_acceptance_checks_pass():
    module = _load_validator()
    assert module.main() == 0


def test_required_subsection_and_discussion_contribution_are_present(draft):
    assert "### 4.1 Data construction, verification and provenance" in draft
    assert "Data construction and auditability as a contribution" in draft


def test_upstream_panel_figures_are_scoped_to_the_panel(draft):
    """1,331 rows describe the source panel, never an evaluation cohort."""
    module = _load_validator()
    results = module.section(draft, "## 10. Locked Final Test Results")
    for figure in module.PANEL_ONLY_FIGURES:
        assert figure not in results, figure
    assert "1,331 firm-year rows for 130 companies" in draft
    for cohort in ("666 company-year rows", "346 evaluable company-year rows"):
        assert cohort in draft, cohort


def test_accounting_identity_values_are_exact(draft):
    qc = _load_json(ROOT.parent / _load_validator().STAGE121_QC)["accounting_identity"]
    assert qc["rows_checked"] == 1312
    assert qc["exact_matches"] == 1311
    assert qc["rounding_tolerance_matches_abs_diff_le_1_million_irr"] == 1
    assert qc["failures"] == []
    assert "1,312 rows for which it was evaluable" in draft
    assert "1,311 rows reconciled exactly" in draft


def test_ratio_recalculation_claim_matches_the_committed_source(draft):
    qc = _load_json(ROOT.parent / _load_validator().STAGE121_QC)
    families = qc["ratio_recalculation_checks"]
    assert len(families) == 7, sorted(families)
    assert all(f["mismatches"] == 0 for f in families.values())
    assert "seven recorded ratio families" in draft and "zero mismatches" in draft


def test_the_provenance_gap_is_not_concealed(draft):
    qc = _load_json(ROOT.parent / _load_validator().STAGE122_QC)
    assert qc["eligibility_counts"]["eligible_source_quality"] == 1303
    assert qc["exclusion_reason_counts_row"]["source_not_traceable"] == 28
    assert "1,303 of the 1,331 rows and is absent for 28" in draft
    assert "provenance gap" in draft.lower()


def test_unknown_target_evidence_was_preserved(draft):
    qc = _load_json(ROOT.parent / _load_validator().STAGE122_QC)
    assert qc["target_counts"] == {"0": 1205, "1": 98, "missing": 28}
    assert qc["assertions"]["no_missing_target_converted_to_zero"] is True
    assert qc["assertions"]["rows_preserved"] is True
    assert "98 are positive, 1,205 are negative and 28 are unknown" in draft
    assert "no unknown was converted into a negative observation" in draft


def test_table_9_matches_its_sources_and_the_claim_freeze():
    validator = _load_validator()
    qc121 = _load_json(ROOT.parent / validator.STAGE121_QC)
    qc122 = _load_json(ROOT.parent / validator.STAGE122_QC)
    with (PKG / "manuscript_results_tables" / validator.TABLE9).open(
            encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == [
            "item", "scope", "committed_result", "scientific_meaning",
            "mandatory_limitation", "canonical_source"]
        t9 = {r["item"]: r for r in reader}
    assert t9["source_panel_rows"]["committed_result"] == str(
        qc121["source_dimensions"]["rows"])
    assert t9["source_panel_companies"]["committed_result"] == str(
        qc122["n_companies_before"])
    assert t9["source_file_provenance_absent"]["committed_result"] == "28"
    freeze = (PKG / "manuscript_claim_freeze.md").read_text(encoding="utf-8")
    assert "## C12 — Data construction and QC" in freeze
    c12 = freeze[freeze.index("## C12"):]
    assert "not a result" in c12
    for item in ("source_panel_rows", "accounting_identity_exact_matches",
                 "source_file_provenance_absent"):
        assert t9[item]["committed_result"] in c12, item


def test_no_stage122_to_stage129_artifact_was_modified():
    """Every pinned upstream source still hashes to its committed digest."""
    module = _load_validator()
    with (MS_DIR / "claim_traceability_matrix.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    upstream = [r for r in rows
                if r["canonical_source_path"].startswith(
                    ("project/stage122/", "project/stage125/", "project/stage126/",
                     "project/stage128/", "project/stage129/", "project/raw_handoff/"))]
    assert upstream, "no upstream source is pinned"
    for row in upstream:
        path = ROOT.parent / row["canonical_source_path"]
        assert module.sha256(path) == row["source_sha256"], row["claim_id"]


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
        assert row["scope"] in SCOPE_LABELS, f"{row['claim_id']}: {row['scope']}"


def test_no_traceability_row_is_unresolved():
    with (MS_DIR / "claim_traceability_matrix.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    unresolved = [r["claim_id"] for r in rows
                  if not r["status"].startswith("TRACED")
                  or any(bad in r["status"].upper()
                         for bad in ("UNRESOLVED", "PENDING", "TODO", "UNKNOWN"))]
    assert not unresolved, unresolved


def test_the_new_data_construction_claims_are_traced():
    """The data contribution must not rest on untraced prose."""
    with (MS_DIR / "claim_traceability_matrix.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    panel = [r for r in rows if r["scope"] in {
        "upstream_source_panel", "stage122_target_qc", "model_eligible_pairs"}]
    assert len(panel) >= 25, len(panel)
    legacy = [r["claim_id"] for r in panel
              if "outputs/09_report" in r["canonical_source_path"]
              or "stage123" in r["canonical_source_path"].lower()]
    assert not legacy, legacy


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
