"""Tests for Stage124 Batch 2 Part 2.1B offline finalizer.

All tests use tmp_path and synthetic fixtures.  No network calls are
performed — all network paths are monkeypatched to fail immediately.
"""

import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

# ---- monkeypatch all network paths so any accidental call fails -----------------

def _fail_network(*args, **kwargs):
    raise AssertionError("Network function called in offline finalizer test")


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch):
    """Patch all network functions to fail immediately."""
    import requests
    monkeypatch.setattr(requests, "get", _fail_network)
    monkeypatch.setattr(requests.sessions.Session, "request", _fail_network)

    try:
        from project.src.stage124_batch02_v2 import tsetmc_probe_ticker
        monkeypatch.setattr("project.src.stage124_batch02_v2.tsetmc_probe_ticker", _fail_network)
    except ImportError:
        pass

    try:
        import project.src.stage124_batch02_part02 as p02
        monkeypatch.setattr(p02, "probe_tsetmc_for_tickers", _fail_network)
    except ImportError:
        pass

    try:
        import project.src.stage124_batch02_part02 as p02
        monkeypatch.setattr(p02, "fetch_sources_hkeshti", _fail_network)
    except ImportError:
        pass

    try:
        import project.src.stage124_batch02_part02 as p02
        monkeypatch.setattr(p02, "run", _fail_network)
    except ImportError:
        pass


# ---- imports --------------------------------------------------------------------

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from project.src.stage124_batch02_part02_finalize import (
    RESEARCH_STATE_COMMIT,
    INITIAL_GENERATION_SOURCE_COMMIT,
    EXPECTED_IMMUTABLE_HASHES,
    MANIFEST_ROWS,
    REQUIRED_PACKAGE_FILES,
    ADMISSION_ONLY_TICKERS,
    UNRESOLVED_TICKERS,
    HKESHTI_CONFLICT_DATES,
    build_tickers_csv,
    build_metadata,
    build_readme,
    update_summary,
    update_qc_report,
    build_manifest,
    prepare_outputs,
    seal_manifest,
    verify_final_package,
    _sha256_file,
    _check_immutable_hashes,
)

from project.src.stage124_batch02_part02 import (
    PART02_TICKERS,
    PART02_DIR,
    FROZEN_FILES,
)

from project.src.stage124_batch02_v2 import (
    sha,
    ROOT,
    STAGE122_INPUT,
    STAGE123_INPUT,
    EXPECTED_STAGE122_SHA,
    EXPECTED_STAGE123_SHA,
)

TEST_FINALIZER_COMMIT = "abcdef0123456789abcdef0123456789abcdef01"
TEST_RESEARCH_COMMIT = RESEARCH_STATE_COMMIT


# ---- synthetic fixture ----------------------------------------------------------

def _make_synthetic_package(tmp_path):
    """Create a synthetic Part 2 package directory under tmp_path.

    The directory structure mirrors:
      tmp_path / "stage124" / "batch02_parts" / ...
      tmp_path / "src" / ...
      tmp_path / "tests" / ...

    All 15 manifest files are created so manifest and verify tests can run.
    """
    pkg_dir = tmp_path / "stage124" / "batch02_parts"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = pkg_dir / "snapshots_hkeshti"
    snap_dir.mkdir(exist_ok=True)

    src_dir = tmp_path / "src"
    src_dir.mkdir(exist_ok=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Research screening
    screening_rows = []
    for tk in PART02_TICKERS:
        if tk in ADMISSION_ONLY_TICKERS:
            es = "requires_first_public_trade_evidence"
            et = ""
        elif tk == "حکشتی":
            es = "requires_manual_review"
            et = "unresolved"
        else:
            es = "requires_manual_review"
            et = ""
        screening_rows.append({
            "ticker": tk,
            "ticker_normalized": tk,
            "company_name": f"Company_{tk}",
            "admission_date_candidate_jalali": "",
            "admission_date_candidate_gregorian": "",
            "listing_date_candidate_jalali": "",
            "listing_date_candidate_gregorian": "",
            "first_public_offering_date_candidate_jalali": "",
            "first_public_offering_date_candidate_gregorian": "",
            "first_public_trading_date_candidate_jalali": "",
            "first_public_trading_date_candidate_gregorian": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "proposed_canonical_public_entry_date_gregorian": "",
            "proposed_canonical_event_type": et,
            "date_precision": "exact_day",
            "ordinary_share_confirmed": "true" if tk != "حکشتی" else "unknown",
            "evidence_status": es,
            "research_status": es,
            "ready_for_user_review": "false",
            "primary_source_type": "market_media",
            "primary_source_title": "test",
            "primary_source_url": "https://example.com",
            "secondary_source_type": "",
            "secondary_source_title": "",
            "secondary_source_url": "",
            "tsetmc_instrument_match_status": "network_unreachable",
            "tsetmc_candidate_date_jalali": "",
            "tsetmc_candidate_disposition": "network_unreachable",
            "ambiguity_notes": "test",
            "programmer_recommendation": "test",
        })
    screening_df = pd.DataFrame(screening_rows)
    screening_df.to_csv(pkg_dir / "part02_research_screening_10tickers.csv",
                        index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    # Provenance
    prov_rows = []
    for tk in PART02_TICKERS:
        prov_rows.append({
            "ticker": tk, "source_index": 1,
            "source_type": "market_media", "source_title": "test",
            "source_url": "https://example.com", "publication_date": "",
            "retrieved_at_utc": "2026-06-26T22:44:51Z", "http_status": "",
            "retrieval_status": "not_fetched_in_part02_research",
            "final_url": "https://example.com", "content_type": "",
            "response_size_bytes": "", "snapshot_path": "",
            "content_sha256": "", "extraction_notes": "test",
            "exact_text_or_event_summary": "test",
        })
    prov_df = pd.DataFrame(prov_rows)
    # Add حکشتی fetched source
    snap_content = b"test snapshot"
    snap_hash = hashlib.sha256(snap_content).hexdigest()
    hk_fetched = {
        "ticker": "حکشتی", "source_index": 1,
        "source_type": "news_website_contemporaneous", "source_title": "test",
        "source_url": "https://example.com/hk", "publication_date": "1387-02-28",
        "retrieved_at_utc": "2026-06-26T23:00:13Z", "http_status": "200",
        "retrieval_status": "fetched_ok",
        "final_url": "https://example.com/hk", "content_type": "text/html",
        "response_size_bytes": str(len(snap_content)),
        "snapshot_path": "stage124/batch02_parts/snapshots_hkeshti/source_1.html",
        "content_sha256": snap_hash,
        "extraction_notes": "test",
        "exact_text_or_event_summary": "test",
    }
    prov_df = pd.concat([prov_df, pd.DataFrame([hk_fetched])], ignore_index=True)
    prov_df.to_csv(pkg_dir / "part02_source_provenance_10tickers.csv",
                   index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    # TSETMC audit
    audit_rows = []
    for tk in PART02_TICKERS:
        audit_rows.append({
            "ticker": tk, "ticker_normalized": tk,
            "instrument_match_status": "network_unreachable",
            "tsetmc_candidate_date_jalali": "",
            "tsetmc_candidate_date_gregorian": "",
            "selected_inscode": "", "ordinary_instrument_count": "",
            "ordinary_instrument_candidates_json": "[]",
            "multiple_ordinary_instruments": 0,
            "probe_retrieved_at": "2026-06-26T22:44:51Z",
            "probe_raw_sha256": "", "probe_notes": "test",
            "probe_source": "live_probe", "source_file_path": "",
            "source_file_sha256": "", "valid_iran_run": "",
            "tsetmc_candidate_disposition": "network_unreachable",
        })
    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(pkg_dir / "part02_tsetmc_audit_10tickers.csv",
                    index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    # Snapshot
    (snap_dir / "source_1.html").write_bytes(snap_content)

    # Summary
    summary = {
        "stage": "stage124_batch02_part02",
        "generated_at": "2026-06-26T23:00:24Z",
        "source_commit": INITIAL_GENERATION_SOURCE_COMMIT,
        "ticker_count": 10,
        "tickers": list(PART02_TICKERS),
        "exact_day_dates": {},
        "admission_only_tickers": list(ADMISSION_ONLY_TICKERS),
        "unresolved_tickers": list(UNRESOLVED_TICKERS),
        "ready_for_user_review_tickers": [],
        "tsetmc_results": {},
        "hkeshti_conflict": {
            "date_28": "1387-02-28",
            "date_29": "1387-02-29",
            "resolution": "unresolved",
            "evidence_status": "requires_manual_review",
            "ready_for_user_review": False,
        },
        "hkeshti_fetch_results": {},
    }
    with open(pkg_dir / "part02_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # QC report
    qc = {
        "stage": "stage124_batch02_part02",
        "generated_at": "2026-06-26T23:00:24Z",
        "source_commit": INITIAL_GENERATION_SOURCE_COMMIT,
        "ticker_count": 10,
        "tickers": list(PART02_TICKERS),
        "all_pass": True,
        "assertion_count": 68,
        "failed_count": 0,
        "assertions": [],
    }
    with open(pkg_dir / "part02_qc_report.json", "w", encoding="utf-8") as f:
        json.dump(qc, f, ensure_ascii=False, indent=2)

    # Source and test files
    (src_dir / "stage124_batch02_part02.py").write_text("# part02 source\n")
    (src_dir / "stage124_batch02_part02_finalize.py").write_text("# finalizer source\n")
    (tests_dir / "test_stage124_batch02_part02.py").write_text("# part02 tests\n")
    (tests_dir / "test_stage124_batch02_part02_finalize.py").write_text("# finalizer tests\n")

    # Test output (placeholder, will be replaced)
    (pkg_dir / "part02_test_output.txt").write_text("test output placeholder\n")

    # Tickers CSV
    tickers_df = pd.DataFrame([
        {"ticker": tk, "ticker_normalized": tk, "company_name": f"Company_{tk}"}
        for tk in PART02_TICKERS
    ])
    tickers_df.to_csv(pkg_dir / "part02_tickers.csv",
                      index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    # Metadata
    metadata = {
        "stage": "stage124_batch02_part02",
        "part": "part02",
        "branch": "test-branch",
        "initial_generation_source_commit": INITIAL_GENERATION_SOURCE_COMMIT,
        "research_state_commit": TEST_RESEARCH_COMMIT,
        "finalizer_source_commit": TEST_FINALIZER_COMMIT,
        "generated_at_utc": "2026-06-27T00:00:00Z",
        "ticker_count": 10,
        "tickers": list(PART02_TICKERS),
        "exact_day_canonical_count": 0,
        "admission_only_count": 6,
        "unresolved_count": 4,
        "ready_for_user_review_count": 0,
        "network_requests_performed": False,
        "tsetmc_probe_performed": False,
        "source_fetch_performed": False,
        "gate_b_executed": False,
        "full_verified_master_created": False,
        "modeling_executed": False,
        "pr_created": False,
        "merged_to_main": False,
    }
    with open(pkg_dir / "part02_metadata_and_hashes.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # README
    (pkg_dir / "README_PART02.md").write_text("# Test README\n")

    return tmp_path


# ---- Test: No network calls -----------------------------------------------------

class TestNoNetworkCalls:
    def test_requests_get_not_called(self):
        import requests
        with pytest.raises(AssertionError):
            requests.get("https://example.com")

    def test_session_request_not_called(self):
        import requests
        with pytest.raises(AssertionError):
            requests.sessions.Session().request("GET", "https://example.com")

    def test_tsetmc_probe_ticker_not_called(self):
        from project.src.stage124_batch02_v2 import tsetmc_probe_ticker
        with pytest.raises(AssertionError):
            tsetmc_probe_ticker("test", None)

    def test_probe_tsetmc_for_tickers_not_called(self):
        import project.src.stage124_batch02_part02 as p02
        with pytest.raises(AssertionError):
            p02.probe_tsetmc_for_tickers(["test"])

    def test_fetch_sources_hkeshti_not_called(self):
        import project.src.stage124_batch02_part02 as p02
        with pytest.raises(AssertionError):
            p02.fetch_sources_hkeshti()

    def test_part02_run_not_called(self):
        import project.src.stage124_batch02_part02 as p02
        with pytest.raises(AssertionError):
            p02.run()


# ---- Test: Immutable hashes (real package) --------------------------------------

class TestImmutableHashes:
    def test_research_screening_sha_unchanged(self):
        results = _check_immutable_hashes()
        assert results["part02_research_screening_10tickers.csv"]["match"]

    def test_provenance_sha_unchanged(self):
        results = _check_immutable_hashes()
        assert results["part02_source_provenance_10tickers.csv"]["match"]

    def test_tsetmc_audit_sha_unchanged(self):
        results = _check_immutable_hashes()
        assert results["part02_tsetmc_audit_10tickers.csv"]["match"]

    def test_snapshot_sha_unchanged(self):
        results = _check_immutable_hashes()
        assert results["snapshots_hkeshti/source_1.html"]["match"]


# ---- Test: Tickers CSV (synthetic) ----------------------------------------------

class TestTickersCSV:
    def test_tickers_csv_has_10_rows(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        df = build_tickers_csv(pkg)
        assert len(df) == 10

    def test_tickers_csv_exact_order(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        df = build_tickers_csv(pkg)
        assert df["ticker"].tolist() == PART02_TICKERS

    def test_tickers_csv_no_duplicates(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        df = build_tickers_csv(pkg)
        assert df["ticker"].duplicated().sum() == 0

    def test_tickers_csv_columns(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        df = build_tickers_csv(pkg)
        assert list(df.columns) == ["ticker", "ticker_normalized", "company_name"]


# ---- Test: Metadata (synthetic) -------------------------------------------------

class TestMetadata:
    def test_metadata_counts(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["exact_day_canonical_count"] == 0
        assert m["admission_only_count"] == 6
        assert m["unresolved_count"] == 4
        assert m["ready_for_user_review_count"] == 0

    def test_metadata_commits(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["finalizer_source_commit"] == TEST_FINALIZER_COMMIT
        assert m["research_state_commit"] == TEST_RESEARCH_COMMIT
        assert m["initial_generation_source_commit"] == INITIAL_GENERATION_SOURCE_COMMIT

    def test_metadata_network_flags_false(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["network_requests_performed"] is False
        assert m["tsetmc_probe_performed"] is False
        assert m["source_fetch_performed"] is False
        assert m["gate_b_executed"] is False
        assert m["full_verified_master_created"] is False
        assert m["modeling_executed"] is False
        assert m["pr_created"] is False
        assert m["merged_to_main"] is False

    def test_metadata_hkeshti_status(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["hkeshti_status"]["evidence_status"] == "requires_manual_review"
        assert m["hkeshti_status"]["ready_for_user_review"] is False
        assert m["hkeshti_status"]["proposed_canonical_jalali"] == ""
        assert m["hkeshti_status"]["proposed_canonical_gregorian"] == ""
        assert m["hkeshti_status"]["proposed_canonical_event_type"] == "unresolved"
        assert m["hkeshti_conflict_dates"] == HKESHTI_CONFLICT_DATES

    def test_metadata_manifest_semantics(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["manifest_source_commit_semantics"] == \
            "commit containing the offline finalizer code used to seal Part 2"

    def test_metadata_ticker_count(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        m = build_metadata(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert m["ticker_count"] == 10
        assert m["tickers"] == list(PART02_TICKERS)


# ---- Test: README ---------------------------------------------------------------

class TestReadme:
    def test_readme_no_absolute_paths(self):
        content = build_readme()
        assert "/Users/" not in content
        assert "Desktop" not in content

    def test_readme_mentions_10_tickers(self):
        content = build_readme()
        assert "10" in content

    def test_readme_hkeshti_not_candidate_supported(self):
        content = build_readme()
        assert "candidate_supported" in content
        assert "not" in content.lower()

    def test_readme_ready_count_zero(self):
        content = build_readme()
        assert "0" in content

    def test_readme_no_tsetmc_in_part2_1b(self):
        content = build_readme()
        assert "Part 2.1B" in content
        assert "no TSETMC" in content or "No TSETMC" in content


# ---- Test: Summary (synthetic) --------------------------------------------------

class TestSummary:
    def test_summary_substantive_fields_unchanged(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        s = update_summary(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert s["exact_day_dates"] == {}
        assert s["admission_only_tickers"] == ADMISSION_ONLY_TICKERS
        assert s["unresolved_tickers"] == UNRESOLVED_TICKERS
        assert s["ready_for_user_review_tickers"] == []

    def test_summary_source_commit_preserved(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        s = update_summary(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert s["source_commit"] == INITIAL_GENERATION_SOURCE_COMMIT

    def test_summary_finalization_object(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        s = update_summary(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert "finalization" in s
        fin = s["finalization"]
        assert fin["research_state_commit"] == TEST_RESEARCH_COMMIT
        assert fin["finalizer_source_commit"] == TEST_FINALIZER_COMMIT
        assert fin["network_requests_performed"] is False
        assert fin["tsetmc_probe_performed"] is False
        assert fin["source_fetch_performed"] is False
        assert fin["package_sealed"] is True


# ---- Test: QC Report (synthetic) ------------------------------------------------

class TestQCReport:
    def test_qc_finalization_object_added(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        qc = update_qc_report(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert "finalization" in qc
        fin = qc["finalization"]
        assert fin["finalizer_source_commit"] == TEST_FINALIZER_COMMIT
        assert fin["research_state_commit"] == TEST_RESEARCH_COMMIT

    def test_qc_hkeshti_unresolved(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        qc = update_qc_report(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        fin = qc["finalization"]
        assertion_names = [a["assertion"] for a in fin["assertions"]]
        assert "hkeshti_evidence_requires_manual_review" in assertion_names
        assert "hkeshti_ready_for_user_review_false" in assertion_names
        assert "hkeshti_canonical_jalali_empty" in assertion_names
        assert "hkeshti_canonical_gregorian_empty" in assertion_names
        assert "hkeshti_event_type_unresolved" in assertion_names

    def test_qc_immutable_checks(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        qc = update_qc_report(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        fin = qc["finalization"]
        assertion_names = [a["assertion"] for a in fin["assertions"]]
        assert "immutable_sha_unchanged_part02_research_screening_10tickers.csv" in assertion_names
        assert "immutable_sha_unchanged_part02_source_provenance_10tickers.csv" in assertion_names
        assert "immutable_sha_unchanged_part02_tsetmc_audit_10tickers.csv" in assertion_names
        assert "immutable_sha_unchanged_snapshots_hkeshti/source_1.html" in assertion_names

    def test_qc_all_pass(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        qc = update_qc_report(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        fin = qc["finalization"]
        failed = [a for a in fin["assertions"] if not a["passed"]]
        assert fin["all_pass"] is True, f"Failed assertions: {[(a['assertion'], a['detail']) for a in failed]}"
        assert fin["failed_count"] == 0


# ---- Test: Manifest (synthetic) -------------------------------------------------

class TestManifest:
    def test_manifest_has_15_rows(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        assert len(df) == 15

    def test_manifest_paths_exact(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        expected_paths = [r[0] for r in MANIFEST_ROWS]
        assert df["relative_path"].tolist() == expected_paths

    def test_manifest_self_row_sha_empty(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        self_row = df[df["relative_path"] == "stage124/batch02_parts/part02_hash_manifest.csv"]
        assert len(self_row) == 1
        assert self_row.iloc[0]["sha256"] == ""

    def test_manifest_self_row_size_correct(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        self_row = df[df["relative_path"] == "stage124/batch02_parts/part02_hash_manifest.csv"]
        recorded_size = int(self_row.iloc[0]["size_bytes"])
        assert recorded_size == len(content.encode("utf-8"))

    def test_manifest_non_self_hashes_correct(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        for _, r in df.iterrows():
            rel = r["relative_path"]
            if rel == "stage124/batch02_parts/part02_hash_manifest.csv":
                continue
            fp = base / rel
            assert fp.exists(), f"File not found: {rel}"
            assert r["sha256"] != "", f"Empty sha256 for {rel}"
            actual = _sha256_file(fp)
            assert r["sha256"] == actual, f"sha256 mismatch for {rel}"

    def test_manifest_source_commit_all_same(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        for _, r in df.iterrows():
            assert r["source_commit"] == TEST_FINALIZER_COMMIT

    def test_manifest_generated_at_all_same(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        df = pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
        gen_ats = df["generated_at"].unique()
        assert len(gen_ats) == 1

    def test_manifest_no_absolute_paths(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        content = build_manifest(TEST_FINALIZER_COMMIT, pkg)
        assert "/Users/" not in content
        assert "Desktop" not in content


# ---- Test: prepare_outputs + seal_manifest + verify (synthetic) -----------------

class TestPrepareSealVerify:
    def test_prepare_outputs_creates_files(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        results = prepare_outputs(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        assert (pkg / "part02_tickers.csv").exists()
        assert (pkg / "part02_metadata_and_hashes.json").exists()
        assert (pkg / "README_PART02.md").exists()
        assert (pkg / "part02_summary.json").exists()
        assert (pkg / "part02_qc_report.json").exists()

    def test_seal_manifest_creates_manifest(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        prepare_outputs(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        seal_manifest(TEST_FINALIZER_COMMIT, pkg)
        assert (pkg / "part02_hash_manifest.csv").exists()

    def test_verify_final_package_passes(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        prepare_outputs(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)
        seal_manifest(TEST_FINALIZER_COMMIT, pkg)
        ok = verify_final_package(TEST_FINALIZER_COMMIT, pkg)
        assert ok is True

    def test_verify_fails_when_manifest_missing(self, tmp_path):
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"
        ok = verify_final_package(TEST_FINALIZER_COMMIT, pkg)
        assert ok is False

    def test_full_workflow_offline(self, tmp_path):
        """End-to-end: prepare, seal, verify — all offline."""
        base = _make_synthetic_package(tmp_path)
        pkg = base / "stage124" / "batch02_parts"

        # Prepare
        prepare_outputs(TEST_FINALIZER_COMMIT, TEST_RESEARCH_COMMIT, pkg)

        # Verify tickers CSV
        tdf = pd.read_csv(pkg / "part02_tickers.csv", dtype=str, keep_default_na=False)
        assert len(tdf) == 10
        assert tdf["ticker"].tolist() == PART02_TICKERS

        # Verify metadata
        with open(pkg / "part02_metadata_and_hashes.json") as f:
            m = json.load(f)
        assert m["network_requests_performed"] is False

        # Verify summary has finalization
        with open(pkg / "part02_summary.json") as f:
            s = json.load(f)
        assert "finalization" in s

        # Verify QC has finalization
        with open(pkg / "part02_qc_report.json") as f:
            qc = json.load(f)
        assert "finalization" in qc
        assert qc["finalization"]["all_pass"] is True

        # Seal and verify
        seal_manifest(TEST_FINALIZER_COMMIT, pkg)
        ok = verify_final_package(TEST_FINALIZER_COMMIT, pkg)
        assert ok is True


# ---- Test: Frozen files unchanged (real package) --------------------------------

class TestFrozenFilesUnchanged:
    def test_stage122_sha_unchanged(self):
        assert sha(STAGE122_INPUT) == EXPECTED_STAGE122_SHA

    def test_stage123_sha_unchanged(self):
        assert sha(STAGE123_INPUT) == EXPECTED_STAGE123_SHA

    def test_no_full_verified_master(self):
        from project.src.stage124_batch02_part02 import FULL_VERIFIED_FORBIDDEN
        assert not FULL_VERIFIED_FORBIDDEN.exists()


# ---- Test: Constants ------------------------------------------------------------

class TestConstants:
    def test_research_state_commit(self):
        assert RESEARCH_STATE_COMMIT == "9f8894a3dbc1c9507bb8e12035663eaa8cb8b9da"

    def test_initial_generation_source_commit(self):
        assert INITIAL_GENERATION_SOURCE_COMMIT == "6a4d6eb29c3e615efe65a124cd5c93f3d3b2aacc"

    def test_manifest_rows_count(self):
        assert len(MANIFEST_ROWS) == 15

    def test_admission_only_count(self):
        assert len(ADMISSION_ONLY_TICKERS) == 6

    def test_unresolved_count(self):
        assert len(UNRESOLVED_TICKERS) == 4

    def test_hkeshti_conflict_dates(self):
        assert HKESHTI_CONFLICT_DATES == ["1387-02-28", "1387-02-29"]
