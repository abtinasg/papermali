"""Tests for Stage125 Part 1 — Data Dictionary & Provenance Contract.

These are read-only / deterministic tests. They never start modeling, never
access the network, and never modify frozen Stage122–Stage124 assets.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from src import stage125_part1_data_contract as part1  # noqa: E402

REPO_ROOT = PROJECT.parent
INPUT = PROJECT / "stage123" / part1.INPUT_NAME


def _build():
    return part1.build_all(REPO_ROOT, INPUT, None)


# --------------------------------------------------------------------------- #
# Input verification
# --------------------------------------------------------------------------- #

def test_input_present_with_expected_sha():
    assert INPUT.is_file(), "canonical Stage123 input missing"
    assert part1.sha256_file(INPUT) == part1.EXPECTED_INPUT_SHA256


def test_input_sha_mismatch_fails(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("row_key,ticker\n1,X\n", encoding="utf-8")
    with pytest.raises(part1.QCFail):
        part1.load_input(bad, None)


def test_no_input_and_no_bundle_fails(tmp_path):
    with pytest.raises(part1.QCFail):
        part1.load_input(tmp_path / "missing.csv", tmp_path / "missing.zip")


# --------------------------------------------------------------------------- #
# M1 invariants (fail-closed)
# --------------------------------------------------------------------------- #

def test_m1_invariants_exact():
    df, _, _ = part1.load_input(INPUT, None)
    counts = part1.compute_gap_summary(df)
    assert part1.check_invariants(counts) == []
    for key, expected in part1.EXPECTED_INVARIANTS.items():
        assert counts[key] == expected, key


def test_invariant_mismatch_detected():
    counts = dict(part1.EXPECTED_INVARIANTS)
    counts["rows"] = 1330
    assert part1.check_invariants(counts) != []


def test_gap_audit_rows_ids_and_flags_only():
    df, _, _ = part1.load_input(INPUT, None)
    rows = part1.build_gap_audit_rows(df)
    assert len(rows) == 1331
    keys = set(rows[0].keys())
    # No raw financial value columns leak into the audit.
    forbidden = {"total_assets", "equity", "revenue_period_adjusted",
                 "net_income_period_adjusted", "leverage_ratio"}
    assert keys.isdisjoint(forbidden)
    # row_key is unique across the audit.
    assert len({r["row_key"] for r in rows}) == 1331


def test_source_url_missing_recorded_not_dropped():
    df, _, _ = part1.load_input(INPUT, None)
    counts = part1.compute_gap_summary(df)
    assert counts["source_url_missing"] == 1316
    rows = part1.build_gap_audit_rows(df)
    # Every row is still present; provenance gap only.
    assert all(r["eligibility_impact"] == "none_recorded_as_provenance_gap_only"
               for r in rows)


# --------------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------------- #

def test_registry_only_m1_to_m4_no_m5():
    reader = csv.DictReader(io.StringIO(part1.build_source_registry_csv()))
    blocks = {r["block"] for r in reader}
    assert blocks <= {"M1", "M2", "M3", "M4"}
    assert "M5" not in blocks
    assert part1.registry_no_m5_ok() is True


def test_registry_unknown_fields_blank_and_unresolved():
    reader = list(csv.DictReader(io.StringIO(part1.build_source_registry_csv())))
    for r in reader:
        if r["accessibility_score"] == "":
            assert r["accessibility_status"] in {
                "unresolved", "pending_part3", "in_use_m1_baseline", "in_use_partial"
            }, r


def test_gate_template_no_admitted_below_threshold():
    assert part1.gate_template_invariant_ok() is True
    reader = list(csv.DictReader(io.StringIO(part1.build_admission_gate_csv())))
    for r in reader:
        if r["status"] == "admitted":
            assert r["accessibility_score"].isdigit() and int(r["accessibility_score"]) >= 3


def test_provenance_schema_required_fields():
    schema = part1.build_provenance_manifest_schema()
    names = {f["name"] for f in schema["fields"]}
    required = {"provenance_id", "source_id", "block", "source_document_id",
                "canonical_ticker", "row_key", "feature_name", "published_at_raw",
                "published_at", "available_at", "retrieved_at_utc", "source_url",
                "source_file", "snapshot_path", "content_sha256", "source_version",
                "extraction_method", "extraction_code_commit", "unit_raw",
                "unit_normalized", "revision_status", "review_status",
                "missing_reason", "notes"}
    assert required.issubset(names)
    assert schema["allowed_blocks"] == ["M1", "M2", "M3", "M4"]
    assert "M5" in schema["disallowed_blocks"]


def test_identifier_time_contract_semantics():
    c = part1.build_identifier_time_contract()
    assert c["identifiers"]["row_key"]["immutable"] is True
    assert c["identifiers"]["row_key"]["unique_row_count"] == 1331
    assert c["identifiers"]["predictor_row_key_t"]["redefined_in_stage125"] is False
    assert c["identifiers"]["target_row_key_t_plus_1"]["redefined_in_stage125"] is False
    for k in ("observation_date", "period_start", "period_end", "fiscal_year_end",
              "published_at", "available_at", "retrieved_at_utc"):
        assert k in c["time_concepts"]
    assert c["time_rules"]["published_at_and_available_at_not_assumed_equal"] is True
    assert c["time_rules"]["unknown_time_is_null_never_inferred"] is True


def test_data_dictionary_covers_m1_to_m4():
    reader = list(csv.DictReader(io.StringIO(part1.build_data_dictionary_csv())))
    blocks = {r["block"] for r in reader}
    assert {"M1", "M2", "M3", "M4"} <= blocks
    assert "M5" not in blocks


# --------------------------------------------------------------------------- #
# Determinism + QC + frozen assets
# --------------------------------------------------------------------------- #

def test_build_is_deterministic():
    a = _build()["files"]
    b = _build()["files"]
    assert a == b


def test_outputs_have_no_runtime_dependency():
    """No tracked output may embed a Python version or platform string."""
    files = _build()["files"]
    import platform
    pyver = platform.python_version()
    for name, content in files.items():
        assert "python_version" not in content, name
        assert pyver not in content, name


def test_qc_all_pass_and_counts():
    res = _build()
    qc = res["qc"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["stage"] == "stage125_part1_data_contract"
    assert qc["current_stage"] == "Stage125"
    assert qc["modeling_started"] is False
    assert qc["input_sha256"] == part1.EXPECTED_INPUT_SHA256
    assert len(qc["frozen_assets_before"]) > 0
    assert qc["frozen_assets_before"] == qc["frozen_assets_after"]


def test_metadata_manifest_excludes_itself_includes_qc():
    files = _build()["files"]
    meta = json.loads(files[part1.F_METADATA])
    ofs = meta["output_files_sha256"]
    assert part1.F_METADATA not in ofs
    assert part1.F_QC in ofs
    # Recorded content hashes match the actual computed content bytes.
    for name, sha in ofs.items():
        assert sha == part1.sha256_bytes(files[name].encode("utf-8")), name


def test_frozen_assets_snapshot_matches_manifests():
    snap = part1.frozen_asset_hashes(REPO_ROOT)
    assert len(snap) > 0
    # Every entry equals the recomputed file hash (proves unchanged).
    for rel, sha in snap.items():
        assert part1.sha256_file(REPO_ROOT / rel) == sha


# --------------------------------------------------------------------------- #
# run() write/check
# --------------------------------------------------------------------------- #

def test_run_write_then_check_clean(tmp_path):
    out = tmp_path / "stage125"
    w = part1.run(project_dir=PROJECT, output_dir=out, write=True)
    assert w["written"] is True
    assert (out / part1.F_QC).is_file()
    assert (out / part1.F_METADATA).is_file()
    c = part1.run(project_dir=PROJECT, output_dir=out, write=False)
    assert c["drift"] == []


def test_run_check_detects_drift(tmp_path):
    out = tmp_path / "stage125"
    part1.run(project_dir=PROJECT, output_dir=out, write=True)
    (out / part1.F_README).write_text("tampered\n", encoding="utf-8")
    c = part1.run(project_dir=PROJECT, output_dir=out, write=False)
    assert part1.F_README in c["drift"]


def test_run_check_does_not_write_when_missing(tmp_path):
    out = tmp_path / "stage125_empty"
    c = part1.run(project_dir=PROJECT, output_dir=out, write=False)
    # Nothing is created in check mode.
    assert not out.exists() or not any(out.iterdir())
    assert set(c["drift"])  # everything reported as drift (absent on disk)
