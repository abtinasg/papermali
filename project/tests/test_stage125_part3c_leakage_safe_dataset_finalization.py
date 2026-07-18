"""Tests for Stage125 Part 3C Leakage-Safe Dataset Finalization."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import jdatetime
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b1e_conservative_lag_decision as part3b1e  # noqa: E402
from src import stage125_part3c_leakage_safe_dataset_finalization as m  # noqa: E402


def _with_pairs_count(design: str, n: int):
    """Temporarily patch DESIGN_SPECS pair count; restore all fields after."""
    import copy
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        orig = copy.deepcopy(m.DESIGN_SPECS[design])
        try:
            m.DESIGN_SPECS[design]["pairs"] = n
            yield
        finally:
            m.DESIGN_SPECS[design] = orig
    return _ctx()


def test_input_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    fake = dict(m.FROZEN_BULKY_INPUTS)
    key = next(iter(fake))
    fake[key] = "0" * 64
    monkeypatch.setattr(m, "FROZEN_BULKY_INPUTS", fake)
    with pytest.raises(m.QCFail, match="input hash mismatch"):
        m.frozen_bulky_hashes(REPO_ROOT)


def test_missing_bulky_input_fails_closed(tmp_path, monkeypatch):
    missing = "project/stage125/does_not_exist_part3c.csv"
    monkeypatch.setattr(
        m, "FROZEN_BULKY_INPUTS",
        {missing: "a" * 64},
    )
    with pytest.raises(m.QCFail, match="missing bulky input"):
        m.frozen_bulky_hashes(REPO_ROOT)


def test_duplicate_predictor_row_key_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:3]
    pairs[1]["predictor_row_key_t"] = pairs[0]["predictor_row_key_t"]
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="duplicate predictor_row_key_t"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_duplicate_target_row_key_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:3]
    pairs[1]["target_row_key_t_plus_1"] = pairs[0]["target_row_key_t_plus_1"]
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="duplicate target_row_key_t_plus_1"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_missing_predictor_join_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:2]
    pairs[0]["predictor_row_key_t"] = "NO_SUCH_KEY|1390"
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="missing predictor join"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_missing_target_join_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:2]
    pairs[0]["target_row_key_t_plus_1"] = "NO_SUCH_TARGET|1391"
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="missing target join"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_ticker_mismatch_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:2]
    pairs[0]["ticker"] = "WRONG_TICKER"
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="ticker mismatch"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_target_year_not_t_plus_1_fails():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )[:2]
    pairs[0]["target_year"] = str(int(pairs[0]["fiscal_year_t"]) + 2)
    design = "main_rule_a_primary"
    with _with_pairs_count(design, len(pairs)):
        with pytest.raises(m.QCFail, match="target_year != fiscal_year_t\\+1"):
            m.build_design_rows(
                design=design, pair_rows=pairs, stage123=stage123,
            )


def test_target_value_mutation_detected_via_hash_pin():
    before = m.frozen_bulky_hashes(REPO_ROOT)
    after = dict(before)
    key = m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    after[key] = "f" * 64
    assert before[key] != after[key]


def test_financial_value_mutation_detected_via_hash_pin():
    before = m.frozen_bulky_hashes(REPO_ROOT)
    after = dict(before)
    key = "project/stage123/modeling_all_rows_stage123.csv"
    after[key] = "e" * 64
    assert before[key] != after[key]


def test_sample_row_removal_fails_count():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )
    with pytest.raises(m.QCFail, match="pair count"):
        m.build_design_rows(
            design="main_rule_a_primary",
            pair_rows=pairs[:-1],
            stage123=stage123,
        )


def test_positive_count_drift_fails(monkeypatch):
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )
    # Flip a positive to negative to drift the count after construction.
    for p in pairs:
        if str(p["FD_target_main_t_plus_1"]).strip() in {"1", "1.0"}:
            p["FD_target_main_t_plus_1"] = "0"
            break
    with pytest.raises(m.QCFail, match="positive/negative"):
        m.build_design_rows(
            design="main_rule_a_primary",
            pair_rows=pairs,
            stage123=stage123,
        )


def test_six_month_lag_five_or_seven_rejected():
    with pytest.raises(part3b1e.AuthorizationError):
        part3b1e.require_approved_lag_months(5)
    with pytest.raises(part3b1e.AuthorizationError):
        part3b1e.require_approved_lag_months(7)


def test_jalali_day_clamping_boundaries():
    # day 31 → shorter month
    assert part3b1e.add_jalali_calendar_months(
        jdatetime.date(1401, 6, 31), 6,
    ) == jdatetime.date(1401, 12, 29)
    # day 30
    assert part3b1e.add_jalali_calendar_months(
        jdatetime.date(1400, 4, 30), 6,
    ) == jdatetime.date(1400, 10, 30)
    # day 29
    assert part3b1e.add_jalali_calendar_months(
        jdatetime.date(1401, 12, 29), 6,
    ) == jdatetime.date(1402, 6, 29)
    # Esfand leap (1403 is leap in Jalali? 1399 was leap with 30 days)
    # 1399/12/30 + 6m → 1400/06/30
    assert part3b1e.add_jalali_calendar_months(
        jdatetime.date(1399, 12, 30), 6,
    ) == jdatetime.date(1400, 6, 30)
    # year rollover
    assert part3b1e.add_jalali_calendar_months(
        jdatetime.date(1400, 10, 30), 6,
    ) == jdatetime.date(1401, 4, 30)


def test_assumed_date_at_or_after_target_fye_fails_closed():
    assumed = jdatetime.date(1397, 6, 29)
    target = jdatetime.date(1397, 1, 31)
    with pytest.raises(m.QCFail, match="not before"):
        m.require_timing_relation(
            assumed, target,
            exception_key=None,
            row_key="synthetic|1396",
        )


def test_authorized_timing_exception_preserves_membership():
    assumed = jdatetime.date(1397, 6, 29)
    target = jdatetime.date(1397, 1, 31)
    key = ("رمپنا", 1396, 1397, "رمپنا|1396", "رمپنا|1397")
    ok, is_exc = m.require_timing_relation(
        assumed, target, exception_key=key, row_key="رمپنا|1396",
    )
    assert ok is False
    assert is_exc is True


def test_authorized_exception_retained_in_audit_excluded_from_analysis_ready():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    for design, spec in m.DESIGN_SPECS.items():
        pairs = m._read_csv_dicts(REPO_ROOT / spec["input_rel"])
        rows, audit = m.build_design_rows(
            design=design, pair_rows=pairs, stage123=stage123,
        )
        ready, excluded = m.split_analysis_ready(rows, design=design)
        assert len(rows) == spec["pairs"]
        assert len(ready) + len(excluded) == len(rows)
        assert len(excluded) == 1
        exc = excluded[0]
        assert exc["predictor_row_key_t"] == "رمپنا|1396"
        assert exc["target_row_key_t_plus_1"] == "رمپنا|1397"
        assert exc["assumed_before_target_fiscal_year_end"] == "false"
        assert exc["timing_relation_exception"] == "true"
        assert exc["timing_eligible_for_analysis"] == "false"
        assert exc["timing_eligible_for_model"] == "false"
        assert exc["timing_exclusion_reason"] == (
            m.TIMING_EXCLUSION_REASON_AUTHORIZED
        )
        audit_exc = [
            a for a in audit
            if a["predictor_row_key_t"] == "رمپنا|1396"
            and a["target_row_key_t_plus_1"] == "رمپنا|1397"
        ]
        assert len(audit_exc) == 1
        assert audit_exc[0]["timing_eligible_for_analysis"] == "false"
        assert audit_exc[0]["timing_eligible_for_model"] == "false"
        assert audit_exc[0]["row_silently_dropped"] == "false"
        assert all(
            r["assumed_before_target_fiscal_year_end"] == "true"
            for r in ready
        )
        assert all(r["timing_relation_exception"] == "false" for r in ready)
        assert all(
            r["timing_eligible_for_analysis"] == "true"
            and r["timing_eligible_for_model"] == "true"
            for r in ready
        )


def test_unauthorized_timing_violation_fails_closed_not_silently_dropped():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    design = "main_rule_a_primary"
    pairs = m._read_csv_dicts(REPO_ROOT / m.DESIGN_SPECS[design]["input_rel"])
    rows, _ = m.build_design_rows(
        design=design, pair_rows=pairs, stage123=stage123,
    )
    # Synthesize an unauthorized timing violation after construction.
    victim = next(
        r for r in rows
        if r["timing_relation_exception"] == "false"
        and r["assumed_before_target_fiscal_year_end"] == "true"
    )
    victim["assumed_before_target_fiscal_year_end"] = "false"
    victim["timing_relation_exception"] = "false"
    victim["timing_eligible_for_analysis"] = "false"
    victim["timing_eligible_for_model"] = "false"
    victim["timing_exclusion_reason"] = "synthetic_unauthorized"
    with pytest.raises(m.QCFail, match="unauthorized timing violation"):
        m.split_analysis_ready(rows, design=design)


def test_attempt_to_populate_PublishDateTime_rejected():
    with pytest.raises(m.AuthorizationError, match="PublishDateTime"):
        m.reject_assumed_date_as_observed_field("PublishDateTime", "1402-06-29")


def test_attempt_to_populate_observed_available_at_rejected():
    with pytest.raises(m.AuthorizationError, match="available_at"):
        m.reject_assumed_date_as_observed_field("available_at", "1402-06-29")
    with pytest.raises(m.AuthorizationError):
        m.reject_assumed_date_as_observed_field(
            "observed_available_at", "1402-06-29",
        )


def test_target_derived_field_not_in_feature_surface():
    roles = m.build_column_role_rows()
    by_name = {r["column_name"]: r for r in roles}
    for col in (
        "FD_target_main_t_plus_1",
        "loss_dummy",
        "equity_negative_dummy",
        "distressed_target_reviewed",
        "source_file",
        "source_url",
        "assumed_available_at_conservative_jalali",
        "timing_eligible_for_analysis",
        "timing_eligible_for_model",
        "timing_exclusion_reason",
        "timing_relation_exception",
        "assumed_before_target_fiscal_year_end",
    ):
        assert by_name[col]["enters_model_feature_matrix"] == "false"
    for col in (
        "timing_eligible_for_analysis",
        "timing_eligible_for_model",
        "timing_exclusion_reason",
        "timing_relation_exception",
        "assumed_before_target_fiscal_year_end",
    ):
        assert by_name[col]["role"] == "timing_eligibility_audit"
    # Predictor financials may be candidates only via explicit whitelist.
    assert by_name["total_assets"]["role"] == "predictor_candidate"
    assert by_name["total_assets"]["enters_model_feature_matrix"] == "true"
    feature_cols = {
        r["column_name"]
        for r in roles
        if r["enters_model_feature_matrix"] == "true"
    }
    assert feature_cols == m.PREDICTOR_FEATURE_WHITELIST


def test_network_attempt_blocked_and_counted():
    with p3b0.network_sentinel() as sentinel:
        content, bulky, extras = m.build_all(REPO_ROOT)
        assert content and bulky and extras
        assert sentinel.calls_attempted == 0
        with pytest.raises(Exception):
            import socket
            socket.create_connection(("example.com", 80), timeout=1)
        assert sentinel.calls_attempted >= 1


def test_non_deterministic_output_ordering_rejected():
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    pairs = m._read_csv_dicts(
        REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
    )
    rows_a, _ = m.build_design_rows(
        design="main_rule_a_primary", pair_rows=list(pairs), stage123=stage123,
    )
    rows_b, _ = m.build_design_rows(
        design="main_rule_a_primary",
        pair_rows=list(reversed(pairs)),
        stage123=stage123,
    )
    keys_a = [r["predictor_row_key_t"] for r in rows_a]
    keys_b = [r["predictor_row_key_t"] for r in rows_b]
    assert keys_a == keys_b
    text_a = m._csv_str(m.final_output_header(), rows_a)
    text_b = m._csv_str(m.final_output_header(), rows_b)
    assert m.sha256_bytes(text_a.encode("utf-8")) == m.sha256_bytes(
        text_b.encode("utf-8")
    )


def test_part3b1e_locks_required():
    locks = m.require_part3b1e_locks(REPO_ROOT)
    assert m.PART3B1E_DECISION_LOCK_REL in locks
    assert m.PART3B1E_FROZEN_MANIFEST_REL in locks


def test_four_design_expected_counts_match_frozen_inputs():
    for design, spec in m.DESIGN_SPECS.items():
        rows = m._read_csv_dicts(REPO_ROOT / spec["input_rel"])
        assert len(rows) == spec["pairs"]
        pos = sum(
            1 for r in rows
            if str(r["FD_target_main_t_plus_1"]).strip() in {"1", "1.0"}
        )
        assert pos == spec["positive"]
        assert len({r["ticker"] for r in rows}) == spec["companies"]


def test_build_all_offline_preserves_targets_and_financials():
    with p3b0.network_sentinel() as sentinel:
        content, bulky, extras = m.build_all(REPO_ROOT)
        assert sentinel.calls_attempted == 0
    expected_bulky = set(m.AUDITED_OUTPUT_FILES.values()) | set(
        m.ANALYSIS_READY_OUTPUT_FILES.values()
    )
    assert set(bulky) == expected_bulky
    # Spot-check main rule A first audited row financial copy equals Stage123.
    stage123 = m.load_stage123_by_row_key(REPO_ROOT)
    reader = csv.DictReader(
        bulky[m.AUDITED_OUTPUT_FILES["main_rule_a_primary"]].splitlines()
    )
    row = next(reader)
    src = stage123[row["predictor_row_key_t"]]
    assert row["total_assets"] == src["total_assets"]
    assert row["leverage_ratio"] == src["leverage_ratio"]
    # Target comes from Gate B, not Stage123 predictor-year target.
    gate = {
        r["predictor_row_key_t"]: r
        for r in m._read_csv_dicts(
            REPO_ROOT / m.DESIGN_SPECS["main_rule_a_primary"]["input_rel"]
        )
    }
    assert row["FD_target_main_t_plus_1"] == gate[row["predictor_row_key_t"]][
        "FD_target_main_t_plus_1"
    ]
    # Analysis-ready must exclude the authorized exception and keep frozen
    # target polarity of remaining rows unchanged.
    for design, spec in m.DESIGN_SPECS.items():
        audited = list(csv.DictReader(
            bulky[m.AUDITED_OUTPUT_FILES[design]].splitlines()
        ))
        ready = list(csv.DictReader(
            bulky[m.ANALYSIS_READY_OUTPUT_FILES[design]].splitlines()
        ))
        assert len(audited) == spec["pairs"]
        assert len(ready) == spec["pairs"] - 1
        assert all(
            r["predictor_row_key_t"] != "رمپنا|1396"
            or r["target_row_key_t_plus_1"] != "رمپنا|1397"
            for r in ready
        )
        summary = next(
            s for s in extras["summaries"] if s["sample_design"] == design
        )
        assert int(summary["excluded_timing_exception_count"]) == 1
        assert int(summary["analysis_ready_pairs"]) == len(ready)
        assert int(summary["audited_pairs"]) == len(audited)
    contract = json.loads(content[m.F_CONTRACT])
    assert contract["six_month_lag_exact"] == 6
    assert contract["contract_version"] == m.CONTRACT_VERSION
    assert contract["research_pointers"]["next_research_action_id"] == (
        m.RESEARCH_NEXT
    )


def test_run_build_check_offline(tmp_path):
    src_commit = m._git(
        str(REPO_ROOT), "log", "--format=%H", "-n", "1",
        "--", m.SRC_REL, m.TEST_REL, m.RUN_REL,
    )
    if not src_commit:
        pytest.skip("source/test/runner not yet committed")
    with p3b0.network_sentinel() as sentinel:
        result = m.run(
            project_dir=ROOT,
            output_dir=tmp_path,
            build=True,
        )
        assert sentinel.calls_attempted == 0
    assert result["qc"]["all_pass"] is True
    assert result["network_requests_attempted"] == 0
    assert (tmp_path / m.F_CONTRACT).is_file()
    assert (
        tmp_path / "part3c_outputs"
        / m.AUDITED_OUTPUT_FILES["main_rule_a_primary"]
    ).is_file()
    assert (
        tmp_path / "part3c_outputs"
        / m.ANALYSIS_READY_OUTPUT_FILES["main_rule_a_primary"]
    ).is_file()
    # Second build byte-identical.
    result2 = m.run(project_dir=ROOT, output_dir=tmp_path, build=True)
    for name in list(m.AUDITED_OUTPUT_FILES.values()) + list(
        m.ANALYSIS_READY_OUTPUT_FILES.values()
    ):
        p = tmp_path / "part3c_outputs" / name
        assert p.read_bytes() == (
            tmp_path / "part3c_outputs" / name
        ).read_bytes()
    check = m.run(project_dir=ROOT, output_dir=tmp_path, check=True)
    assert check["qc"]["all_pass"] is True
    assert not check["drift"] or all(
        str(x).startswith("part3c_outputs/") for x in check["drift"]
    ) is False or check["drift"] == []
    # QC assertions include the analysis-ready fail-closed surface.
    names = {a["assertion"] for a in check["qc"]["assertions"]}
    assert "analysis_ready_assumed_before_target_fye_true" in names
    assert "no_authorized_timing_exception_in_analysis_ready" in names
    assert "audit_and_analysis_ready_counts_reconcile" in names
    assert "authorized_rampna_exception_visible_in_audit" in names
    assert "predictor_feature_whitelist_exact" in names
