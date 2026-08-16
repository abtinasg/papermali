"""Stage129 M4 observational audit-field extraction (V4.3.1) — custody tests.

This package is EVIDENCE CUSTODY ONLY. These tests pin:
  * the observational, not-admitted-to-M4 status of the package,
  * the exact counts and their reconciliation to the 1331-row canonical
    population,
  * the semantic corrections that distinguish V4.3.1 from V4.3,
  * repository custody hygiene (no raw archive, no absolute local paths),
  * the unchanged Stage129 M4 governance markers and the Final Test lock.

They check counts and semantics, never mere file existence.
"""
import csv
import hashlib
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PKG_REL = "project/stage129/m4_observational_audit_extraction_v4_3_1"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)

ACTION_ID = "stage129-m4-observational-audit-extraction-v4-3-1-custody"
PACKAGE_STATUS = "OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT"

CANONICAL_ROWS = 1331
CANONICAL_TICKERS = 130
CANONICAL_YEARS = set(range(1392, 1403))

EXPECTED_COVERAGE = {
    "MATCHED_SEPARATE_VALID": 828,
    "MATCHED_SEPARATE_CORRECTION_SELECTED": 74,
    "MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED": 1,
    "ONLY_CONSOLIDATED_AVAILABLE": 368,
    "NO_ARCHIVE_MATCH": 60,
}
EXPECTED_OPINIONS = {"مشروط": 224, "مقبول": 220}
EXPECTED_VERIFIED_OPINIONS = 444
EXPECTED_FYE = 889
EXPECTED_REPORT_DATE = 446
EXPECTED_MISSING = 2214

SOURCE_ARCHIVE_SHA256 = "f33ee950ffdd7042f6fe60f411e2d81b8cbe38b51ec84d30c2e224de1a1c6bb2"
CANONICAL_SHA256 = "f6b6bc41cbe757d19d4397ffc5898629d0fca8ab0480351f75040a71d7ce7376"
SYMBOLIC_ARCHIVE = "LOCAL_SOURCE_ARCHIVE_NOT_REPOSITORY_RETAINED"

OPINION_VOCAB = {"مقبول", "مشروط", "مردود", "عدم اظهارنظر", "UNVERIFIED"}


def _walk_package():
    """Yield package-relative paths of COMMITTABLE files.

    `__pycache__` is created by simply running the package's own scripts and is
    git-ignored, so it is not a committed artefact. Walking it would make these
    tests fail for anyone who ran the pipeline once; a separate test pins the
    .gitignore rule that keeps it out of the repository.
    """
    for dirpath, dirnames, filenames in os.walk(_PKG):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            yield os.path.relpath(os.path.join(dirpath, fn), _PKG)


def _json(name):
    with open(os.path.join(_PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


def _csv(name):
    with open(os.path.join(_PKG, name), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def extracted():
    return _csv("audit_fields_extracted_v4_3_1.csv")


@pytest.fixture(scope="module")
def evidence():
    return {r["row_key"]: r for r in _csv("audit_field_evidence_v4_3_1.csv")}


@pytest.fixture(scope="module")
def coverage():
    return _csv("canonical_1331_coverage.csv")


@pytest.fixture(scope="module")
def inventory():
    return _csv("archive_file_inventory.csv")


@pytest.fixture(scope="module")
def qa():
    return _json("qa_report_v4_3_1.json")


@pytest.fixture(scope="module")
def boundary():
    return _json("stage129_m4_observational_extraction_governance_boundary.json")


@pytest.fixture(scope="module")
def meta():
    return _json("metadata_and_hashes_stage129_m4_observational_audit_extraction_v4_3_1.json")


# ---------------------------------------------------------------- 1. status
def test_package_status_is_exactly_observational(boundary, meta, extracted):
    assert boundary["package_status"] == PACKAGE_STATUS
    assert meta["package_status"] == PACKAGE_STATUS
    assert boundary["action_id"] == ACTION_ID
    # every single extracted row carries the label; no row is silently promoted
    assert {r["scientific_status"] for r in extracted} == {PACKAGE_STATUS}


def test_package_makes_no_admission_or_resolution_claim(boundary):
    for marker in (
        "is_structured_field_extraction_for_stage125_definition",
        "free_text_extraction_equals_structured_field_claim_made",
        "audit_opinion_type_taxonomy_resolved_by_this_action",
        "audit_opinion_type_admitted_to_m4",
        "audit_lag_days_computed",
        "going_concern_flag_derived_from_text",
        "codal_identity_prerequisite_resolved_by_this_action",
        "calendar_conversion_prerequisite_resolved_by_this_action",
    ):
        assert boundary[marker] is False, marker


def test_readme_states_status_and_denies_every_admission_claim():
    """The README must carry an explicit no-claims table, and every verdict in it
    must be 'No'. This checks the claims are DENIED, not merely that some words
    are absent -- a substring ban would trip over the denial table itself."""
    text = open(os.path.join(
        _PKG, "README_STAGE129_M4_OBSERVATIONAL_AUDIT_EXTRACTION_V4_3_1.md"),
        encoding="utf-8").read()
    assert PACKAGE_STATUS in text
    assert "human_scientific_decision_required" in text
    assert SYMBOLIC_ARCHIVE in text

    section = text.split("does NOT claim", 1)
    assert len(section) == 2, "README must carry an explicit no-claims section"
    body = section[1].split("\n---", 1)[0]
    rows = [ln for ln in body.splitlines()
            if ln.startswith("|") and "---" not in ln and "| Status |" not in ln]
    assert len(rows) >= 8, "expected the full no-claims table, got %d rows" % len(rows)

    claims = {
        "taxonomy": False, "structured field": False, "admitted to M4": False,
        "audit_lag_days": False, "going_concern_flag": False,
        "CODAL identity": False, "Data Gate": False,
    }
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) == 2, row
        claim, verdict = cells
        assert verdict.startswith("**No**"), row
        for key in claims:
            if key.lower() in claim.lower():
                claims[key] = True
    missing = [k for k, seen in claims.items() if not seen]
    assert not missing, "no-claims table is missing: %s" % missing


# ------------------------------------------------- 2/3. population + coverage
def test_canonical_population_is_preserved(extracted, coverage):
    assert len(extracted) == CANONICAL_ROWS
    assert len(coverage) == CANONICAL_ROWS
    assert len({r["row_key"] for r in extracted}) == CANONICAL_ROWS
    assert len({r["ticker"] for r in extracted}) == CANONICAL_TICKERS
    assert {int(r["fiscal_year"]) for r in extracted} <= CANONICAL_YEARS


def test_canonical_identity_records_the_unchanged_population_hash():
    c = _json("canonical_source_identity_v4_3_1.json")
    assert c["selected_sha256"] == CANONICAL_SHA256
    assert c["rows"] == CANONICAL_ROWS and c["tickers"] == CANONICAL_TICKERS
    assert c["modified_by_this_mission"] is False
    assert c["hash_scope"] == "committed_repository_artifact"
    # the committed canonical file must still hash to the recorded value
    with open(os.path.join(REPO_ROOT, c["selected_canonical_repository_path"]), "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == CANONICAL_SHA256


def test_coverage_statuses_sum_to_1331_with_the_expected_split(coverage):
    counts = {}
    for row in coverage:
        counts[row["coverage_status"]] = counts.get(row["coverage_status"], 0) + 1
    assert counts == EXPECTED_COVERAGE
    assert sum(counts.values()) == CANONICAL_ROWS


# ----------------------------------------------------------- 4. source rules
def test_no_consolidated_or_unaudited_payload_was_used_as_separate(extracted):
    used = [r for r in extracted if r["source_relative_path"]]
    assert used, "expected at least one selected source"
    assert all(r["statement_scope"] != "consolidated" for r in used)
    assert all(r["audit_status"] != "unaudited" for r in used)
    assert all(r["statement_scope"] == "separate" for r in used)


# --------------------------------------------- 5/6. named regression cases
def test_fanavard_1400_rejects_the_non_substantive_correction(extracted):
    row = next(r for r in extracted if r["row_key"] == "فنورد|1400")
    assert row["coverage_status"] == "MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED"
    assert row["correction_status"] == "original"
    assert row["selected_role"] == "original"
    # the original's data must actually be recovered, not merely retained in name
    assert row["fiscal_year_end"] == "1400/12/29"

    audit = [r for r in _csv("correction_selection_audit_v4_3_1.csv")
             if r["row_key"] == "فنورد|1400"]
    assert audit, "the correction pair must be audited"
    assert all(r["selected"] == "NO" for r in audit)
    assert all(r["correction_payload_verdict"] != "PAYLOAD_SUBSTANTIVE" for r in audit)


def test_no_selected_correction_is_a_non_substantive_payload():
    for r in _csv("correction_selection_audit_v4_3_1.csv"):
        if r.get("selected") == "YES":
            assert r["correction_payload_verdict"] == "PAYLOAD_SUBSTANTIVE"
            assert "SUSPICIOUS_SMALL_PAYLOAD" not in (r.get("correction_verdict_reason") or "")


def test_sakhoz_1392_opinion_is_not_transferred_between_versions(extracted):
    row = next(r for r in extracted if r["row_key"] == "سخوز|1392")
    assert row["auditor_opinion_type"] == "UNVERIFIED"
    audit = [r for r in _csv("correction_selection_audit_v4_3_1.csv")
             if r["row_key"] == "سخوز|1392"]
    sel = [r for r in audit if r["selected"] == "YES"]
    assert sel, "a correction must have been selected for this row"
    # the original's مشروط must be disclosed as NOT transferred, with a reason
    assert sel[0]["original_opinion"] == "مشروط"
    assert "auditor_opinion_type" in sel[0]["fields_lost_vs_original"]
    assert sel[0]["field_loss_reason"].strip() != ""


def test_khosaz_1396_is_qualified_not_a_disclaimer(extracted, evidence):
    row = next(r for r in extracted if r["row_key"] == "خوساز|1396")
    assert row["auditor_opinion_type"] == "مشروط"
    ev = evidence["خوساز|1396"]
    # the real opinion heading governs, not the stray "مبانی عدم اظهارنظر" label
    assert "مشروط" in ev["opinion_heading_text"]
    assert not ev["opinion_heading_text"].strip().startswith("مبانی")


def test_no_opinion_is_taken_from_a_basis_label(evidence, extracted):
    for row in extracted:
        if row["auditor_opinion_type"] == "UNVERIFIED":
            continue
        heading = (evidence[row["row_key"]]["opinion_heading_text"] or "").strip()
        assert not heading.startswith("مبانی"), row["row_key"]


# --------------------------------------------------------- 7/8. exact counts
def test_verified_opinion_count_and_distribution(extracted):
    dist = {}
    for r in extracted:
        dist[r["auditor_opinion_type"]] = dist.get(r["auditor_opinion_type"], 0) + 1
    assert set(dist) <= OPINION_VOCAB
    assert dist.get("مشروط") == EXPECTED_OPINIONS["مشروط"]
    assert dist.get("مقبول") == EXPECTED_OPINIONS["مقبول"]
    assert dist.get("عدم اظهارنظر", 0) == 0
    assert dist.get("مردود", 0) == 0
    verified = sum(v for k, v in dist.items() if k != "UNVERIFIED")
    assert verified == EXPECTED_VERIFIED_OPINIONS


def test_fiscal_year_end_and_report_date_counts(extracted):
    fye = [r for r in extracted if r["fiscal_year_end"] != "NOT_FOUND"]
    dates = [r for r in extracted if r["auditor_report_date"] != "NOT_FOUND"]
    assert len(fye) == EXPECTED_FYE
    assert len(dates) == EXPECTED_REPORT_DATE
    # a fiscal year end must belong to its own fiscal year
    assert all(r["fiscal_year_end"].startswith(str(r["fiscal_year"])) for r in fye)


def test_missing_worklist_is_field_level_and_reconciles(extracted):
    miss = _csv("audit_fields_missing_worklist_v4_3_1.csv")
    assert len(miss) == EXPECTED_MISSING
    observed = EXPECTED_FYE + EXPECTED_VERIFIED_OPINIONS + EXPECTED_REPORT_DATE
    assert len(miss) == CANONICAL_ROWS * 3 - observed
    assert {m["missing_field"] for m in miss} == {
        "fiscal_year_end", "auditor_opinion_type", "auditor_report_date"}
    assert all(m["reason"].strip() for m in miss)


def test_qa_report_agrees_with_the_committed_csvs(qa):
    assert qa["qa_passed"] is True
    assert qa["checks_failed"] == []
    assert qa["rows_with_fiscal_year_end"] == EXPECTED_FYE
    assert qa["rows_with_verified_opinion"] == EXPECTED_VERIFIED_OPINIONS
    assert qa["rows_with_verified_report_date"] == EXPECTED_REPORT_DATE
    assert qa["field_level_missing"] == EXPECTED_MISSING
    assert qa["coverage_status_counts"] == EXPECTED_COVERAGE


# ------------------------------------------------------------- 9. evidence
def test_every_verified_opinion_has_block_scoped_evidence(extracted, evidence):
    loc = re.compile(r"^(?P<sheet>.+)!R(?P<row>\d+)C\d+$")
    for row in extracted:
        if row["auditor_opinion_type"] == "UNVERIFIED":
            continue
        ev = evidence[row["row_key"]]
        assert ev["auditor_block_sheet"], row["row_key"]
        m = loc.match(ev["opinion_paragraph_location"])
        assert m, row["row_key"]
        # the paragraph must sit inside the recorded block, on the block's sheet
        assert m.group("sheet") == ev["auditor_block_sheet"], row["row_key"]
        assert (int(ev["auditor_block_start"]) <= int(m.group("row"))
                <= int(ev["auditor_block_end"])), row["row_key"]
        assert ev["opinion_paragraph_text"].strip(), row["row_key"]
        assert ev["source_sha256"], row["row_key"]


def test_unqualified_opinions_show_the_complete_decisive_phrase(extracted, evidence):
    fair = re.compile(r"ب[ه]?نحو[ه]?(مطلوب|منصفانه)نشانمی")
    exception = re.compile(r"بهاستثنا|باستثنا|بااستثنا|بهاسثنا|بهاستثای|بهجز|بجز")
    n = 0
    for row in extracted:
        if row["auditor_opinion_type"] != "مقبول":
            continue
        n += 1
        squashed = re.sub(r"\s+", "", evidence[row["row_key"]]["opinion_paragraph_text"])
        assert fair.search(squashed), row["row_key"]
        assert not exception.search(squashed), row["row_key"]
    assert n == EXPECTED_OPINIONS["مقبول"]


def test_every_verified_report_date_is_anchored_inside_its_block(extracted, evidence):
    loc = re.compile(r"^(?P<sheet>.+)!R(?P<row>\d+)C\d+$")
    for row in extracted:
        if row["auditor_report_date"] == "NOT_FOUND":
            continue
        ev = evidence[row["row_key"]]
        m = loc.match(ev["auditor_report_date_location"])
        assert m, row["row_key"]
        assert m.group("sheet") == ev["auditor_block_sheet"], row["row_key"]
        assert (int(ev["auditor_block_start"]) <= int(m.group("row"))
                <= int(ev["auditor_block_end"])), row["row_key"]
        assert "تاریخ تهیه گزارش" in ev["auditor_report_date_anchor_text"], row["row_key"]
        assert ev["auditor_report_date_context"].strip(), row["row_key"]


# ------------------------------------------- 10. structured field boundary
def test_structured_field_payloads_are_pre_canonical_and_contribute_nothing(
        inventory, extracted):
    structured = [r for r in inventory
                  if r["opinion_evidence_kind"] == "STRUCTURED_FIELD_نظر_حسابرس"]
    assert len(structured) == 65
    years = {int(r["fiscal_year_inferred"]) for r in structured}
    assert years == set(range(1380, 1391))
    assert not (years & CANONICAL_YEARS), "structured-field years must be pre-canonical"
    # ...and therefore no canonical row may be backed by the structured field
    assert all("STRUCTURED_FIELD" not in r["auditor_opinion_evidence_kind"]
               for r in extracted)


# -------------------------------------------------- 11. forbidden features
def test_no_audit_lag_or_going_concern_column_anywhere_in_the_package():
    forbidden = ("audit_lag", "going_concern")
    checked = 0
    for rel in _walk_package():
        if not rel.endswith(".csv"):
            continue
        checked += 1
        with open(os.path.join(_PKG, rel), encoding="utf-8-sig") as fh:
            header = fh.readline().lower()
        for token in forbidden:
            assert token not in header, "%s in %s" % (token, rel)
    assert checked >= 10, "expected the package CSVs to be scanned"


# ------------------------------------------------------- 12. custody hygiene
def test_no_raw_archive_or_payload_is_committed(meta):
    assert meta["raw_archive_committed"] is False
    assert meta["raw_payload_files_committed"] == 0
    assert meta["m4_value_files_committed"] == 0
    for rel in _walk_package():
        assert not rel.lower().endswith((".zip", ".xlsx", ".xls")), rel
        assert not os.path.basename(rel).startswith("._"), rel
        assert "__MACOSX" not in rel, rel


def test_no_absolute_local_path_or_username_in_any_committed_file():
    offenders = []
    for rel in _walk_package():
        with open(os.path.join(_PKG, rel), "rb") as fh:
            blob = fh.read()
        if b"/Users/" in blob or b"/home/" in blob:
            offenders.append(rel)
    assert offenders == []


def test_build_artifacts_cannot_reach_the_repository():
    """Running the package's own scripts creates __pycache__; the repository
    must ignore it, so it can never become a committed artefact."""
    rules = open(os.path.join(REPO_ROOT, ".gitignore"), encoding="utf-8").read()
    assert "__pycache__/" in rules


def test_filenames_are_portable():
    illegal = set('<>:"|?*\\')
    for rel in _walk_package():
        assert not (set(os.path.basename(rel)) & illegal), rel


def test_archive_identity_keeps_the_fingerprint_but_not_the_location():
    a = _json("archive_identity_v4_3_1.json")
    assert a["sha256"] == SOURCE_ARCHIVE_SHA256
    assert a["archive_location"] == SYMBOLIC_ARCHIVE
    assert "archive_absolute_path" not in a
    assert a["raw_archive_retained_in_repository"] is False
    assert a["byte_for_byte_reproducibility_without_the_archive"] is False
    assert a["hash_scope"] == "observed_external_local_source_not_repository_retained"
    assert a["nested_zip_count"] == 128
    assert a["payload_file_count"] == 1628


def test_every_recorded_hash_declares_its_scope(meta):
    for entry in meta["external_source_fingerprints"].values():
        assert entry["hash_scope"] == "observed_external_local_source_not_repository_retained"
    for entry in meta["committed_repository_input_fingerprints"].values():
        assert entry["hash_scope"] == "committed_repository_artifact"


def test_package_hash_manifest_matches_every_committed_file(meta):
    listed = set(meta["package_files"])
    on_disk = {
        rel for rel in _walk_package()
        if rel != "metadata_and_hashes_stage129_m4_observational_audit_extraction_v4_3_1.json"
    }
    assert listed == on_disk
    for rel, info in meta["package_files"].items():
        with open(os.path.join(_PKG, rel), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], rel
        assert len(blob) == info["bytes"], rel


# --------------------------------------- 13/14. governance markers unchanged
def test_stage129_m4_governance_markers_are_unchanged_and_gate_is_shut(boundary):
    assert boundary["m4_contract_complete"] is False
    assert boundary["m4_contract_fully_executable"] is False
    assert boundary["m4_data_gate_executable"] is False
    assert boundary["m4_data_gate_authorized"] is False
    assert boundary["m4_data_gate_executed"] is False
    assert boundary["m4_candidates_the_gate_may_execute_for"] == []
    assert boundary["m4_block_admitted"] is False
    assert boundary["m4_modeling_started"] is False
    assert boundary["m4_incremental_evaluation_authorized"] is False
    assert boundary["modeling_executed"] is False
    assert boundary["holm_family_modified_by_this_action"] is False
    assert boundary["paper_winner_selected"] is False
    assert boundary["final_model_selected"] is False


def test_the_live_stage129_contract_still_reports_a_shut_gate():
    """This package must not have edited the contract packages it sits beside."""
    contract = json.load(open(os.path.join(
        REPO_ROOT, "project/stage129/m4_governance_data_gate_contract",
        "stage129_m4_data_gate_contract.json"), encoding="utf-8"))
    blob = json.dumps(contract, ensure_ascii=False)
    assert '"m4_contract_complete": false' in blob
    assert '"m4_data_gate_executable": false' in blob
    assert '"m4_data_gate_authorized": false' in blob
    assert '"m4_candidates_the_gate_may_execute_for": []' in blob

    handoff = json.load(open(os.path.join(
        REPO_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8"))
    assert handoff["m4_data_gate_authorized"] is False
    assert handoff["m4_data_gate_executable"] is False
    assert handoff["m4_contract_fully_executable"] is False
    assert handoff["stage129_m4_candidates_the_gate_may_execute_for"] == []


def test_final_test_stays_locked_with_zero_rows_read(boundary):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_rows_read"] == 0
    handoff = json.load(open(os.path.join(
        REPO_ROOT, "project/docs/ai/handoff_state.json"), encoding="utf-8"))
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this extraction.
    assert handoff["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert handoff["stage129_m4_final_test_rows_read"] == 0


def test_this_action_is_draft_only_and_advances_no_pointer(boundary):
    assert boundary["merge_authorized"] is False
    assert boundary["ready_for_review_authorized"] is False
    assert boundary["pr_is_draft"] is True
    assert boundary["next_action"] == "human_scientific_decision_required"
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert boundary["main_research_pointer_advanced_by_this_action"] is False
    assert boundary["canonical_population_modified_by_this_action"] is False
