"""Stage130 — the complete 115-column release dictionary.

A public dataset whose columns are undocumented is not usable, and a dataset
whose columns are documented from guesswork is worse. These tests pin both
halves:

  * **complete** — one row for each of the 115 released columns, no duplicate,
    no omission, and a column set that equals the authoritative Stage125
    role map exactly;
  * **anchored** — every row names a repository file that exists, from a closed
    set of authoritative sources, and no field is left blank;
  * **fail-closed** — a column the generator cannot anchor is REPORTED BY NAME,
    never filled with a plausible sentence, and a blank field or a dangling
    source anchor aborts;
  * **custody only** — the generator reads dictionaries, contracts and the role
    map. It reads no data row, recomputes no value, and never touches the Final
    Test surface.
"""
import csv
import importlib
import io
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))

import stage130_release_column_dictionary as dictionary  # noqa: E402

ROLE_MAP_REL = "project/stage125/part3c_column_role_map_stage125.csv"
COMMITTED_REL = ("project/stage130/dataset_release_candidate/release_payload/"
                 "RELEASE_COLUMN_DICTIONARY.csv")
EXPECTED_COLUMNS = 115

#: The role counts the Stage125 contract itself publishes, restated here so a
#: silently edited contract cannot also edit the expectation.
CONTRACT_ROLE_COUNTS = {
    "sample_eligibility_audit": 37,
    "predictor_candidate": 31,
    "forbidden_from_model_matrix": 14,
    "identifier": 10,
    "timing_assumption": 10,
    "provenance_audit": 5,
    "timing_eligibility_audit": 5,
    "target": 3,
}


@pytest.fixture(scope="module")
def rows():
    return dictionary.build_rows(REPO_ROOT)


@pytest.fixture(scope="module")
def committed():
    with open(os.path.join(REPO_ROOT, COMMITTED_REL), "rb") as fh:
        data = fh.read()
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))


@pytest.fixture(scope="module")
def released():
    with open(os.path.join(REPO_ROOT, ROLE_MAP_REL), encoding="utf-8-sig",
              newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# Complete
# --------------------------------------------------------------------------- #

def test_every_released_column_is_documented_exactly_once(rows, released):
    documented = [r["column_name"] for r in rows]
    expected = [r["column_name"] for r in released]
    assert len(expected) == EXPECTED_COLUMNS
    assert len(documented) == EXPECTED_COLUMNS
    assert sorted(documented) == sorted(expected)
    assert len(set(documented)) == len(documented)


def test_the_column_set_matches_the_authoritative_role_map_exactly(rows,
                                                                   released):
    assert {r["column_name"] for r in rows} == \
        {r["column_name"] for r in released}


def test_the_committed_csv_matches_a_fresh_generation(committed, rows):
    """A hand-edited dictionary must not be able to ship."""
    with open(os.path.join(REPO_ROOT, COMMITTED_REL), "rb") as fh:
        on_disk = fh.read()
    assert on_disk == dictionary.render_csv(rows)
    assert len(committed) == EXPECTED_COLUMNS


def test_the_committed_csv_carries_every_declared_field(committed):
    for row in committed:
        assert tuple(row) == dictionary.FIELDNAMES, row["column_name"]


def test_the_role_and_role_counts_come_from_the_role_map(rows, released):
    by_name = {r["column_name"]: r["role"] for r in released}
    counts = {}
    for row in rows:
        assert row["column_role"] == by_name[row["column_name"]]
        counts[row["column_role"]] = counts.get(row["column_role"], 0) + 1
    assert counts == CONTRACT_ROLE_COUNTS
    assert sum(counts.values()) == EXPECTED_COLUMNS


# --------------------------------------------------------------------------- #
# Anchored, and never invented
# --------------------------------------------------------------------------- #

def test_no_field_of_any_row_is_blank(rows):
    for row in rows:
        for field in dictionary.FIELDNAMES:
            assert row[field].strip(), (row["column_name"], field)


def test_every_row_names_an_authoritative_repository_source_that_exists(rows):
    for row in rows:
        source = row["authoritative_source_path"]
        assert source in dictionary.AUTHORITATIVE_SOURCES, row["column_name"]
        assert os.path.isfile(os.path.join(REPO_ROOT, source)), source


def test_every_row_names_the_section_inside_that_source(rows):
    for row in rows:
        assert len(row["authoritative_source_field_or_section"]) > 3, \
            row["column_name"]


def test_definition_status_comes_from_the_closed_vocabulary(rows):
    for row in rows:
        assert row["definition_status"] in dictionary.DEFINITION_STATUS, \
            (row["column_name"], row["definition_status"])


def test_provenance_class_comes_from_the_closed_vocabulary(rows):
    for row in rows:
        assert row["source_provider_or_author_derived"] in \
            dictionary.PROVENANCE_CLASS, row["column_name"]


def test_no_source_is_declared_that_the_dictionary_never_cites():
    """A dangling entry in the allowlist points a reuser at nothing."""
    rows = dictionary.build_rows(REPO_ROOT)
    cited = {r["authoritative_source_path"] for r in rows}
    assert cited == set(dictionary.AUTHORITATIVE_SOURCES)


# --------------------------------------------------------------------------- #
# The roles a reuser must not get wrong
# --------------------------------------------------------------------------- #

def test_no_column_is_marked_eligible_to_enter_the_model_matrix(rows,
                                                                released):
    """Part 3C approved nothing. Every role map row says so, and so must we."""
    for row in released:
        assert row["enters_model_feature_matrix"] == "false", \
            row["column_name"]
    for row in rows:
        assert "approved" not in row["model_eligibility"] or \
            "not_approved" in row["model_eligibility"], row["column_name"]


def test_target_derived_columns_are_unmistakably_labelled(rows):
    forbidden = [r for r in rows
                 if r["column_role"] == "forbidden_from_model_matrix"]
    assert len(forbidden) == 14
    for row in forbidden:
        assert row["model_eligibility"] == \
            "forbidden_never_enters_the_model_feature_matrix_target_derived"
        assert "target-derived" in row["limitations"].lower()


def test_the_three_outcomes_are_labelled_as_outcomes(rows):
    targets = [r for r in rows if r["column_role"] == "target"]
    assert {r["column_name"] for r in targets} == {
        "FD_target_main_t_plus_1",
        "FD_target_article141_only_t_plus_1",
        "FD_target_persistent_loss_robustness_t_plus_1",
    }
    for row in targets:
        assert row["model_eligibility"] == \
            "outcome_variable_never_a_predictor_feature"
        assert row["temporal_reference"] == "target_fiscal_year_t_plus_1"


def test_identifier_and_audit_columns_are_not_predictor_candidates(rows):
    for row in rows:
        if row["column_role"] == "identifier":
            assert row["model_eligibility"] == "identifier_not_a_predictor_feature"
        if row["column_role"] in ("provenance_audit", "sample_eligibility_audit",
                                  "timing_eligibility_audit"):
            assert row["model_eligibility"] == \
                "audit_only_never_a_predictor_feature"


def test_the_predictor_candidates_are_candidates_and_nothing_more(rows):
    candidates = [r for r in rows if r["column_role"] == "predictor_candidate"]
    assert len(candidates) == 31
    for row in candidates:
        assert row["model_eligibility"] == (
            "candidate_inventory_only_pending_part4_sap_not_approved_for_"
            "model_entry")


#: The timing fields that actually encode the four-month assumption, as
#: opposed to the four fiscal-year-end fields, which are real period ends.
ASSUMPTION_BEARING_TIMING_FIELDS = {
    "assumed_available_at_regulatory_jalali",
    "assumed_available_at_regulatory_gregorian",
    "regulatory_lag_months",
    "availability_method",
    "availability_date_semantics",
    "is_observed_publication_timestamp",
    "assumed_before_target_fiscal_year_end",
    "timing_relation_violation",
    "timing_eligible_for_analysis",
    "timing_eligible_for_model",
    "timing_exclusion_reason",
}
PERIOD_END_TIMING_FIELDS = {
    "fiscal_year_end_t_jalali",
    "fiscal_year_end_t_gregorian",
    "target_fiscal_year_end_t_plus_1_jalali",
    "target_fiscal_year_end_t_plus_1_gregorian",
}


def test_the_availability_fields_disclose_that_they_are_assumptions(rows):
    timing = [r for r in rows
              if r["column_role"] in ("timing_assumption",
                                      "timing_eligibility_audit")]
    assert {r["column_name"] for r in timing} == (
        ASSUMPTION_BEARING_TIMING_FIELDS | PERIOD_END_TIMING_FIELDS)
    for row in timing:
        limits = row["limitations"].lower()
        if row["column_name"] in ASSUMPTION_BEARING_TIMING_FIELDS:
            assert "assum" in limits or "proxy" in limits, row["column_name"]
        else:
            # A period end is an observed statement date, not the assumption.
            # It must not be sold as one, in either direction.
            assert "period end" in limits or "conversion" in limits, \
                row["column_name"]


def test_the_primary_outcome_is_not_described_as_a_legal_determination(rows):
    row = next(r for r in rows if r["column_name"] == "FD_target_main_t_plus_1")
    limits = row["limitations"].lower()
    assert "not an article-141 legal insolvency determination" in limits
    assert "not a bankruptcy filing" in limits


# --------------------------------------------------------------------------- #
# Fail-closed
# --------------------------------------------------------------------------- #

def test_an_undefined_column_is_reported_by_name_not_invented(monkeypatch):
    facts = dict(dictionary.COLUMN_FACTS)
    facts.pop("total_assets")
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    with pytest.raises(dictionary.ColumnDictionaryError) as excinfo:
        dictionary.build_rows(REPO_ROOT)
    assert "total_assets" in str(excinfo.value)
    assert "invent" in str(excinfo.value)


def test_an_entry_for_a_column_that_is_not_released_aborts(monkeypatch):
    facts = dict(dictionary.COLUMN_FACTS)
    facts["a_column_that_was_never_released"] = facts["total_assets"]
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    with pytest.raises(dictionary.ColumnDictionaryError,
                       match="does not release"):
        dictionary.build_rows(REPO_ROOT)


def test_a_blank_field_aborts(monkeypatch):
    facts = {k: dict(v) for k, v in dictionary.COLUMN_FACTS.items()}
    facts["total_assets"]["definition"] = "   "
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    with pytest.raises(dictionary.ColumnDictionaryError, match="definition"):
        dictionary.build_rows(REPO_ROOT)


def test_a_source_anchor_that_does_not_exist_aborts(monkeypatch):
    facts = {k: dict(v) for k, v in dictionary.COLUMN_FACTS.items()}
    facts["total_assets"]["authoritative_source_path"] = \
        "project/stage125/a_file_that_does_not_exist.csv"
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    sources = set(dictionary.AUTHORITATIVE_SOURCES) | {
        "project/stage125/a_file_that_does_not_exist.csv"}
    monkeypatch.setattr(dictionary, "AUTHORITATIVE_SOURCES", frozenset(sources))
    with pytest.raises(dictionary.ColumnDictionaryError,
                       match="does not exist"):
        dictionary.build_rows(REPO_ROOT)


def test_a_source_outside_the_declared_set_aborts(monkeypatch):
    facts = {k: dict(v) for k, v in dictionary.COLUMN_FACTS.items()}
    facts["total_assets"]["authoritative_source_path"] = "README.md"
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    with pytest.raises(dictionary.ColumnDictionaryError,
                       match="not one of the declared authoritative sources"):
        dictionary.build_rows(REPO_ROOT)


def test_a_role_map_that_lost_a_column_aborts(tmp_path, monkeypatch):
    shim = tmp_path / "repo"
    (shim / "project" / "stage125").mkdir(parents=True)
    with open(os.path.join(REPO_ROOT, ROLE_MAP_REL), encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines(keepends=True)
    (shim / ROLE_MAP_REL).write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(dictionary.ColumnDictionaryError, match="expected 115"):
        dictionary.build_rows(shim)


def test_a_role_map_with_a_duplicate_column_aborts(tmp_path):
    shim = tmp_path / "repo"
    (shim / "project" / "stage125").mkdir(parents=True)
    with open(os.path.join(REPO_ROOT, ROLE_MAP_REL), encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines(keepends=True)
    duplicated = lines[:-1] + [lines[1]]
    (shim / ROLE_MAP_REL).write_text("".join(duplicated), encoding="utf-8")
    with pytest.raises(dictionary.ColumnDictionaryError, match="repeats"):
        dictionary.build_rows(shim)


# --------------------------------------------------------------------------- #
# Custody only
# --------------------------------------------------------------------------- #

#: Path fragments naming a surface that carries released row VALUES, or the
#: spent Final Test. The dictionary documents columns; opening one of these
#: would be reading data, which this action is not authorized to do.
FORBIDDEN_READ_FRAGMENTS = (
    "part3c_outputs", "analysis_ready_", "audited_pairs_",
    "final_test", "predictions", "stage129",
)


def _record_opened_paths(monkeypatch):
    """Capture every path the generator actually opens, however it opens it."""
    import builtins
    import pathlib

    opened = []
    real_open = builtins.open
    real_read_bytes = pathlib.Path.read_bytes
    real_read_text = pathlib.Path.read_text

    def spy_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def spy_read_bytes(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_bytes(self, *args, **kwargs)

    def spy_read_text(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(pathlib.Path, "read_bytes", spy_read_bytes)
    monkeypatch.setattr(pathlib.Path, "read_text", spy_read_text)
    return opened


def test_the_generator_opens_no_released_data_file(monkeypatch):
    """It documents columns. It never opens a surface that carries values.

    Asserted on what the generator DOES, not on what its source text says: a
    grep over source would also trip on the contract key names it legitimately
    cites in prose.
    """
    opened = _record_opened_paths(monkeypatch)
    dictionary.build_rows(REPO_ROOT)
    assert opened, "the generator opened nothing at all -- the spy is not wired"
    for path in opened:
        lowered = path.lower()
        for fragment in FORBIDDEN_READ_FRAGMENTS:
            assert fragment not in lowered, (fragment, path)


def test_no_declared_source_is_a_released_value_surface():
    for source in dictionary.AUTHORITATIVE_SOURCES:
        lowered = source.lower()
        for fragment in FORBIDDEN_READ_FRAGMENTS:
            assert fragment not in lowered, (fragment, source)


def test_the_coverage_report_claims_no_more_than_it_proves():
    stats = dictionary.coverage(REPO_ROOT)
    assert stats["released_columns"] == EXPECTED_COLUMNS
    assert stats["released_columns_documented"] == EXPECTED_COLUMNS
    assert stats["released_columns_undocumented"] == 0
    assert stats["duplicate_rows"] == 0
    assert stats["column_set_matches_authoritative_role_map"] is True
    assert sum(stats["rows_by_definition_status"].values()) == EXPECTED_COLUMNS


def test_the_module_is_importable_by_the_release_builder():
    """The builder imports it by name; a rename must break here, loudly."""
    module = importlib.import_module("stage130_release_column_dictionary")
    assert hasattr(module, "build_csv")
    assert hasattr(module, "FIELDNAMES")
    assert hasattr(module, "ColumnDictionaryError")
