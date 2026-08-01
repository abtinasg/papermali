"""Focused tests — ``stage128-m3-macro-data-gate``.

These are data-Gate tests. They read committed artifacts, rebuild the package
in memory and assert the Gate invariants. They deliberately run NO scientific
computation: no model is fit, nothing is predicted, no predictive metric is
computed, nothing is resampled, no final-test value is touched, and no
upstream scientific artifact is regenerated.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "project"))

from src import stage128_m3_macro_data_gate as g  # noqa: E402

SRC_PATH = REPO_ROOT / "project/src/stage128_m3_macro_data_gate.py"
RUNNER_PATH = REPO_ROOT / "project/run_stage128_m3_macro_data_gate.py"


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def _rows(rel: str) -> list[dict]:
    with (REPO_ROOT / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO_ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


@pytest.fixture(scope="module")
def decision() -> dict:
    return _load(g.DECISION_REL)


@pytest.fixture(scope="module")
def authorization() -> dict:
    return _load(g.AUTHORIZATION_REL)


@pytest.fixture(scope="module")
def lock() -> dict:
    return _load(g.LOCK_REL)


@pytest.fixture(scope="module")
def qc() -> dict:
    return _load(g.QC_REL)


@pytest.fixture(scope="module")
def metadata() -> dict:
    return _load(g.METADATA_REL)


@pytest.fixture(scope="module")
def firewall() -> dict:
    return _load(g.FIREWALL_REL)


@pytest.fixture(scope="module")
def temporal() -> dict:
    return _load(g.TEMPORAL_DEGREES_REL)


@pytest.fixture(scope="module")
def common_sample() -> dict:
    return _load(g.COMMON_SAMPLE_REL)


@pytest.fixture(scope="module")
def evidence_manifest() -> dict:
    return _load(g.RAW_EVIDENCE_REL)


# --------------------------------------------------------------------------- #
# 1-2. Exact human authorization
# --------------------------------------------------------------------------- #

def test_authorization_byte_length_is_exactly_28():
    raw = g.HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    assert len(raw) == 28 == g.HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH


def test_authorization_sha256_recomputed_independently():
    raw = g.HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == (
        "d4acc9698f160ed0f252fd3f2a698b2b17916144d3dc182333cd2892a5d23068")
    assert hashlib.sha256(raw).hexdigest() == g.HUMAN_SOURCE_UTTERANCE_SHA256


def test_authorization_has_no_trailing_newline():
    assert not g.HUMAN_SOURCE_UTTERANCE.endswith("\n")
    assert "\n" not in g.HUMAN_SOURCE_UTTERANCE


def test_authorization_fails_closed_on_byte_length_drift(monkeypatch):
    monkeypatch.setattr(g, "HUMAN_SOURCE_UTTERANCE", "بریم")
    with pytest.raises(g.M3MacroDataGateError, match="byte length"):
        g.verify_human_authorization()


def test_authorization_fails_closed_on_sha_drift(monkeypatch):
    monkeypatch.setattr(g, "HUMAN_SOURCE_UTTERANCE_SHA256", "0" * 64)
    with pytest.raises(g.M3MacroDataGateError, match="sha256"):
        g.verify_human_authorization()


def test_verbatim_and_normalized_authorization_are_separated(authorization):
    assert authorization["human_source_utterance"] == g.HUMAN_SOURCE_UTTERANCE
    assert authorization["human_source_utterance_is_verbatim_human_text"] is True
    assert authorization["normalized_authorization_scope"] == (
        g.NORMALIZED_AUTHORIZATION_SCOPE)
    assert authorization[
        "normalized_authorization_scope_is_derived_not_verbatim_human_text"
    ] is True
    assert (authorization["human_source_utterance"]
            != authorization["normalized_authorization_scope"])


def test_authorization_is_one_action_and_not_standing(authorization):
    assert authorization["authorization_type"] == "one_action_authorization"
    assert authorization["creates_standing_authorization"] is False
    assert authorization["scope_limited_to_this_action_only"] is True
    assert authorization["merge_authorized"] is False
    for forbidden in ("M3 predictive modeling", "M3-versus-M2 evaluation",
                      "final-test access", "merge"):
        assert forbidden in authorization["does_not_permit"]


def test_decision_records_authorization_consumed(decision):
    assert decision["m3_macro_data_gate_authorization_consumed"] is True


# --------------------------------------------------------------------------- #
# 3-6. Baseline, exact block, source id, forbidden substitutions
# --------------------------------------------------------------------------- #

def test_exact_baseline_commit(decision, metadata):
    assert g.BASELINE_COMMIT == "35aaf4b70e9341704ee38be6f8cf2e2519c70bb2"
    assert decision["source_main_commit"] == g.BASELINE_COMMIT
    assert metadata["source_main_commit"] == g.BASELINE_COMMIT


def test_exact_m3_block_list_and_order(decision, lock):
    expected = ("cpi_inflation", "fx_change_official", "policy_financing_rate")
    assert g.M3_BLOCK == expected
    assert tuple(decision["m3_block"]) == expected
    assert tuple(lock["m3_block"]) == expected
    assert tuple(decision["m3_candidate_ids"]) == (
        "cand_m3_cpi_inflation", "cand_m3_fx_change_official",
        "cand_m3_policy_financing_rate")


@pytest.mark.parametrize("bad", [
    ("cpi_inflation", "fx_change_official"),
    ("fx_change_official", "cpi_inflation", "policy_financing_rate"),
    ("cpi_inflation", "fx_change_official", "policy_financing_rate",
     "liquidity_growth"),
])
def test_block_may_not_be_reduced_expanded_or_reordered(bad):
    with pytest.raises(g.M3MacroDataGateError):
        g.assert_exact_m3_block(bad)


def test_exact_source_id_and_authority(decision):
    assert g.REQUIRED_SOURCE_ID == "src_m3_cbi_macro"
    assert g.REQUIRED_AUTHORITY == "Central Bank of Iran"
    assert decision["required_source_id"] == "src_m3_cbi_macro"
    assert decision["required_authority"] == "Central Bank of Iran"


def test_forbidden_substitutions_registered_and_unused(decision, lock):
    for name in ("src_m3_sci_macro_silent_remap", "sci_cpi_for_cbi_cpi",
                 "sci_for_cbi_fx", "sci_for_cbi_policy_rate",
                 "free_market_fx", "oos_free_market_fx"):
        assert name in g.FORBIDDEN_SUBSTITUTIONS
    assert decision["forbidden_substitutions_used"] == []
    assert lock["forbidden_substitutions_used"] == []
    assert decision["unofficial_or_sci_source_used"] is False


def test_forbidden_scope_expansions_registered_and_unused(decision):
    for name in ("liquidity_growth", "gdp", "production_index", "oil_price",
                 "unofficial_exchange_rate", "free_market_exchange_rate",
                 "scraped_aggregator_data", "private_commercial_macro_dataset",
                 "searched_macro_variable_universe", "economic_regime_variable",
                 "any_fourth_m3_variable"):
        assert name in g.FORBIDDEN_ADDITIONS
    assert decision["forbidden_additions_used"] == []


def test_no_fourth_variable_anywhere(decision):
    assert len(decision["m3_block"]) == 3
    assert len(decision["m3_candidate_ids"]) == 3
    assert len(decision["per_candidate_gate_rule_results"]) == 3


# --------------------------------------------------------------------------- #
# 7-9. Phase ordering — lock is prospective, Phase B is gated
# --------------------------------------------------------------------------- #

def test_definition_lock_created_before_value_level_execution(lock, decision):
    assert lock["locked_before_any_value_level_execution"] is True
    assert lock[
        "locked_from_schema_documentation_and_theory_not_from_coverage"] is True
    assert lock["locked_from_target_outcomes"] is False
    assert decision["phase_a_locked_before_value_level_execution"] is True
    assert decision["phase_b_executed"] is False


def test_gate_decision_cites_the_lock_by_path_and_sha256(decision):
    assert decision["phase_a_definition_lock_path"] == g.LOCK_REL
    on_disk = hashlib.sha256(
        (REPO_ROOT / g.LOCK_REL).read_bytes()).hexdigest()
    assert decision["phase_a_definition_lock_sha256"] == on_disk


def test_phase_b_is_refused_while_the_lock_is_unresolved(lock):
    assert lock["lock_status"] == g.LOCK_STATUS_UNRESOLVED
    with pytest.raises(g.M3MacroDataGateError, match="Phase B is not permitted"):
        g.assert_phase_b_permitted(lock)


def test_phase_b_guard_refuses_a_partially_resolved_lock():
    partial = {
        "lock_status": g.LOCK_STATUS_RESOLVED,
        "candidates": [
            {"candidate_id": "cand_m3_cpi_inflation", "uniquely_determined": True},
            {"candidate_id": "cand_m3_fx_change_official",
             "uniquely_determined": False},
        ],
    }
    with pytest.raises(g.M3MacroDataGateError, match="not uniquely determined"):
        g.assert_phase_b_permitted(partial)


def test_no_alternative_series_tried_after_coverage_inspection(lock):
    for candidate in lock["candidates"]:
        assert candidate[
            "alternative_series_tried_after_coverage_inspection"] is False
        assert candidate["candidate_dropped_or_substituted"] is False
        assert candidate["ambiguity_enumeration_is_not_a_menu_to_choose_from"]


def test_every_required_lock_field_is_present_for_every_candidate(lock):
    assert len(g.REQUIRED_LOCK_FIELDS) == 20
    for candidate in lock["candidates"]:
        assert set(candidate["lock_fields"]) == set(g.REQUIRED_LOCK_FIELDS)
        assert candidate["uniquely_determined"] is False
        assert candidate["unresolved_lock_field_count"] > 0


def test_source_manifest_covers_all_three_candidates():
    rows = _rows(g.SOURCE_MANIFEST_REL)
    assert [r["candidate_id"] for r in rows] == list(g.M3_CANDIDATE_IDS)
    for row in rows:
        assert row["official_source_id"] == "src_m3_cbi_macro"
        assert row["official_source_owner"] == "Central Bank of Iran"
        assert row["lock_status"] == g.LOCK_STATUS_UNRESOLVED
        # unresolved operational fields are blank, never guessed
        assert row["official_series_code_or_table_id"] == ""
        assert row["transformation_formula"] == ""
        assert row["revision_or_vintage_policy"] == ""


# --------------------------------------------------------------------------- #
# 10-14. Gate rules and frozen thresholds
# --------------------------------------------------------------------------- #

def test_g01_to_g08_evaluated_individually_for_each_candidate(decision):
    results = decision["per_candidate_gate_rule_results"]
    assert [r["candidate_id"] for r in results] == list(g.M3_CANDIDATE_IDS)
    for result in results:
        assert set(result["gate_rule_results"]) == {
            "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08"}
        assert result["all_rules_pass"] is False
        assert result["status"] == "UNRESOLVED"


def test_missing_evidence_is_unresolved_never_scored_as_zero(decision):
    for result in decision["per_candidate_gate_rule_results"]:
        # unresolved rules are None, not False and not 0
        for rule in result["unresolved_rules"]:
            assert result["gate_rule_results"][rule] is None
        assert 0 not in result["gate_rule_results"].values()


def test_thresholds_match_the_frozen_stage125_part4_contract(decision):
    thresholds = decision["thresholds"]
    assert thresholds["candidate_valid_coverage_min"] == 0.80
    assert thresholds["block_common_sample_coverage_min"] == 0.70
    assert thresholds[
        "min_positive_evaluable_each_temporal_validation_window"] == 5
    # re-verified against the committed contract, not just asserted here
    g.verify_thresholds_against_frozen_contract(REPO_ROOT)


def test_threshold_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(g, "CANDIDATE_VALID_COVERAGE_MIN", 0.5)
    with pytest.raises(g.M3MacroDataGateError, match="must not be lowered"):
        g.verify_thresholds_against_frozen_contract(REPO_ROOT)


def test_historical_80_pair_pilot_thresholds_are_not_applied(decision):
    thresholds = decision["thresholds"]
    assert thresholds["historical_80_pair_pilot_rules_applied"] is False
    assert tuple(thresholds["historical_80_pair_pilot_rules_not_applicable"]) \
        == ("G09", "G10", "G11", "G12", "G13", "G14")
    for rule in ("G09", "G10", "G11", "G12", "G13", "G14"):
        assert rule not in g.GATE_RULES


# --------------------------------------------------------------------------- #
# 15-17. Parent sample and locked folds
# --------------------------------------------------------------------------- #

def test_parent_surface_is_the_retained_m2_common_sample(decision):
    parent = decision["parent_surface"]
    assert parent["parent_rows"] == 539
    assert parent["parent_positive"] == 55
    assert parent["parent_negative"] == 484
    assert parent["parent_companies"] == 108
    assert parent["parent_surface_is_the_m3_gate_denominator"] is True


def test_parent_surface_is_derived_independently_not_hand_reproduced():
    """Recompute membership here from the committed D2 table."""
    with (REPO_ROOT / g.D2_FEATURES_REL).open(encoding="utf-8",
                                              newline="") as fh:
        rows = list(csv.DictReader(fh))
    selected = [r for r in rows
                if r["in_three_variable_common_sample"].strip() == "True"]
    assert len(rows) == 666
    assert len(selected) == 539
    assert len({r["ticker"] for r in selected}) == 108
    derived = g.derive_parent_surface(REPO_ROOT)
    assert derived["parent_rows"] == len(selected)
    assert derived["membership_altered"] is False
    assert derived[
        "membership_derived_programmatically_not_hand_reproduced"] is True


def test_m1_666_universe_is_audit_only_not_the_denominator(decision):
    parent = decision["parent_surface"]
    assert parent["m1_development_universe_rows"] == 666
    assert parent["m1_universe_reconciliation_is_audit_only"] is True
    assert parent["m1_universe_not_used_as_m3_gate_denominator"] is True
    for row in _rows(g.COVERAGE_AUDIT_REL):
        assert row["coverage_denominator_rows"] == "539"
        assert row["coverage_denominator_rows"] != "666"


def test_coverage_denominator_excludes_no_structurally_difficult_rows():
    for row in _rows(g.COVERAGE_AUDIT_REL):
        assert row[
            "structurally_difficult_rows_excluded_from_denominator"] == "False"


def test_required_join_keys_and_no_fuzzy_matching(decision):
    parent = decision["parent_surface"]
    assert tuple(parent["required_join_keys"]) == (
        "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
        "fiscal_year_t", "target_year")
    assert parent["fuzzy_matching_permitted"] is False
    assert g.FUZZY_MATCHING_PERMITTED is False


def test_exact_locked_temporal_folds(decision):
    assert g.DEVELOPMENT_TARGET_YEARS == (
        "1393", "1394", "1395", "1396", "1397", "1398", "1399")
    assert g.LOCKED_FOLDS["fold1"]["train"] == ("1393", "1394", "1395")
    assert g.LOCKED_FOLDS["fold1"]["validation"] == ("1396", "1397")
    assert g.LOCKED_FOLDS["fold2"]["train"] == (
        "1393", "1394", "1395", "1396", "1397")
    assert g.LOCKED_FOLDS["fold2"]["validation"] == ("1398", "1399")
    parent = decision["parent_surface"]
    assert set(parent["counts_by_target_year"]) == set(
        g.DEVELOPMENT_TARGET_YEARS)
    assert sum(parent["counts_by_target_year"].values()) == 539


def test_event_count_audit_covers_both_folds_and_roles():
    rows = _rows(g.EVENT_COUNT_REL)
    assert {(r["fold"], r["role"]) for r in rows} == {
        ("fold1", "train"), ("fold1", "validation"),
        ("fold2", "train"), ("fold2", "validation")}
    for row in rows:
        if row["role"] == "validation":
            assert row["min_positive_required"] == "5"
        assert row["m3_common_sample_positive"] == ""  # null, not zero
        assert row["counts_are_null_not_zero"] == "True"


def test_no_random_split_or_resampling_vocabulary_in_source():
    source = SRC_PATH.read_text(encoding="utf-8")
    for banned in ("train_test_split", "KFold", "StratifiedKFold",
                   "cross_val_score", "RandomizedSearchCV", "GridSearchCV"):
        assert banned not in source


# --------------------------------------------------------------------------- #
# 18-21. Point-in-time and vintage rules
# --------------------------------------------------------------------------- #

def test_available_at_comparison_is_strict():
    rule = g.AVAILABLE_AT_RULE
    assert rule["comparison"] == "available_at < cutoff"
    assert rule["strict"] is True
    assert "<=" not in rule["comparison"]


def test_same_day_observation_is_unavailable_unless_prefrozen_rule():
    rule = g.AVAILABLE_AT_RULE
    assert rule["same_day_is_unavailable"] is True
    assert rule[
        "same_day_exception_requires_prefrozen_verified_timestamp_rule"] is True
    assert rule["same_day_exception_invented_here"] is False


def test_missing_availability_means_unavailable():
    rule = g.AVAILABLE_AT_RULE
    assert rule["missing_published_at_means_unavailable"] is True
    assert rule["missing_available_at_means_unavailable"] is True
    assert rule["availability_inferred_from"] == []
    for banned in ("the observation month", "period end",
                   "file modification time", "a later web page",
                   "retrieval time", "an assumed publication lag"):
        assert banned in rule["availability_must_never_be_inferred_from"]


def test_revision_and_vintage_policy_is_not_assumed_safe():
    rule = g.AVAILABLE_AT_RULE
    assert rule[
        "current_revised_series_is_automatically_point_in_time_safe"] is False
    assert rule["backfill_with_later_revisions_permitted"] is False
    assert rule["vintage_evidence_required_for_each_accepted_observation"]
    assert rule["rows_without_vintage_evidence_remain_unresolved"] is True


def test_observation_schema_records_every_required_provenance_field():
    for field in ("observation_period", "observed_value", "unit",
                  "published_at", "available_at", "release_artifact_id",
                  "release_artifact_sha256", "source_url", "retrieved_at",
                  "revision_or_vintage_id"):
        assert field in g.NORMALIZED_OBSERVATION_COLUMNS


def test_no_observation_was_materialized():
    rows = _rows(g.NORMALIZED_OBS_REL)
    assert rows == []
    header = (REPO_ROOT / g.NORMALIZED_OBS_REL).read_text(
        encoding="utf-8").strip()
    assert header == ",".join(g.NORMALIZED_OBSERVATION_COLUMNS)


def test_no_m3_development_feature_row_was_materialized():
    assert _rows(g.DEV_FEATURES_REL) == []


# --------------------------------------------------------------------------- #
# 22-23. Official sources only
# --------------------------------------------------------------------------- #

def test_every_probe_targeted_an_official_cbi_host(evidence_manifest):
    assert evidence_manifest["probe_count"] >= 1
    for probe in evidence_manifest["probes"]:
        host = probe["source_url"].split("/")[2]
        assert host == "cbi.ir" or host.endswith(".cbi.ir"), host


def test_no_probe_returned_authoritative_data_evidence(evidence_manifest):
    for probe in evidence_manifest["probes"]:
        assert probe["usable_as_authoritative_data_evidence"] is False
        assert probe["contains_macro_data_series"] is False


def test_retrieval_is_not_byte_reproducible(evidence_manifest, decision):
    for probe in evidence_manifest["probes"]:
        assert probe["byte_identical_on_repeat"] is False
    assert decision["official_evidence_assessment"][
        "byte_reproducible_probe_count"] == 0


def test_captcha_was_never_solved_or_bypassed(evidence_manifest, decision):
    assert evidence_manifest["captcha_solved_or_bypassed"] is False
    assert decision["official_evidence_assessment"][
        "captcha_never_solved_or_bypassed"] is True


def test_no_aggregator_mirror_or_news_source_used(evidence_manifest, decision):
    assert evidence_manifest[
        "aggregator_mirror_blog_or_news_used_as_evidence"] is False
    assessment = decision["official_evidence_assessment"]
    assert assessment["official_hosts_only"] is True
    assert assessment["unofficial_or_aggregator_source_used"] is False
    assert assessment["sci_substitution_used"] is False


def test_non_official_host_in_evidence_fails_closed(tmp_path, monkeypatch):
    manifest = json.loads((REPO_ROOT / g.RAW_EVIDENCE_REL).read_text("utf-8"))
    manifest["probes"][0]["source_url"] = "https://tradingeconomics.com/iran"
    fake_root = tmp_path / "root"
    (fake_root / Path(g.RAW_EVIDENCE_REL).parent).mkdir(parents=True)
    (fake_root / g.RAW_EVIDENCE_REL).write_text(
        json.dumps(manifest), encoding="utf-8")
    with pytest.raises(g.M3MacroDataGateError, match="non-official host"):
        g.assess_official_evidence(fake_root)


# --------------------------------------------------------------------------- #
# 24-25. Temporal degrees of freedom
# --------------------------------------------------------------------------- #

def test_temporal_degrees_audit_is_present_and_unresolved(temporal):
    assert temporal["audit_status"] == "UNRESOLVED"
    assert temporal["independent_temporal_macro_support"] is None
    for candidate in g.M3_CANDIDATE_IDS:
        entry = temporal["per_candidate"][candidate]
        for field in ("unique_observation_periods",
                      "unique_official_release_dates",
                      "unique_available_at_dates", "unique_values",
                      "rows_per_macro_state",
                      "maximum_row_share_held_by_one_state",
                      "unique_states_by_fold", "unique_states_by_target_year"):
            assert field in entry
    joint = temporal["joint_m3_state_vector"]
    assert "unique_joint_macro_state_vectors" in joint


def test_company_year_rows_are_not_independent_macro_observations(temporal):
    assert temporal[
        "company_year_rows_reported_as_independent_macro_observations"] is False
    assert temporal["company_year_sample_size"] == 539
    assert temporal["independent_temporal_macro_support"] != 539


def test_no_new_temporal_degrees_threshold_was_invented(temporal):
    assert temporal["new_numeric_temporal_degrees_threshold_invented"] is False
    assert temporal[
        "low_temporal_degrees_is_a_mandatory_interpretation_limitation"] is True
    assert temporal[
        "low_temporal_degrees_used_to_search_more_macro_variables"] is False


# --------------------------------------------------------------------------- #
# 26-29. Final-test firewall and absolute modeling prohibitions
# --------------------------------------------------------------------------- #

def test_final_test_firewall_is_all_zero(firewall):
    assert firewall["final_test_target_years"] == ["1400", "1401", "1402"]
    assert firewall["final_test_rows_loaded"] == 0
    assert firewall["final_test_predictor_values_read"] == 0
    assert firewall["final_test_target_values_read"] == 0
    assert firewall["final_test_macro_values_materialized"] == 0
    assert firewall["final_test_predictions"] == 0
    assert firewall["final_test_evaluations"] == 0
    assert firewall["final_test_macro_coverage_inspected"] is False
    assert firewall["final_test_events_counted"] is False


def test_no_final_test_year_appears_in_the_parent_surface(decision):
    parent = decision["parent_surface"]
    assert parent["final_test_rows_in_parent_surface"] == 0
    assert set(parent["counts_by_target_year"]) & {"1400", "1401", "1402"} \
        == set()


def test_parent_surface_rejects_final_test_leakage(tmp_path, monkeypatch):
    """A final-test row reaching the parent surface must fail closed."""
    src = (REPO_ROOT / g.D2_FEATURES_REL).read_text(encoding="utf-8")
    lines = src.splitlines()
    header = lines[0].split(",")
    year_idx = header.index("target_year")
    tampered = list(lines)
    for i, line in enumerate(tampered[1:], start=1):
        parts = line.split(",")
        if parts[header.index("in_three_variable_common_sample")] == "True":
            parts[year_idx] = "1401"
            tampered[i] = ",".join(parts)
            break
    fake_root = tmp_path / "root"
    (fake_root / Path(g.D2_FEATURES_REL).parent).mkdir(parents=True)
    (fake_root / g.D2_FEATURES_REL).write_text(
        "\n".join(tampered) + "\n", encoding="utf-8")
    with pytest.raises(g.M3MacroDataGateError, match="final-test target years"):
        g.derive_parent_surface(fake_root)


def test_zero_model_fits_predictions_and_metrics(decision):
    assert decision["model_fits"] == 0
    assert decision["predictions"] == 0
    assert decision["predictive_metrics_computed"] == 0
    assert decision["bootstrap_holm_shap_smote_executions"] == 0
    assert decision["m3_versus_m2_evaluations"] == 0


def test_no_estimator_runtime_reached_this_module():
    g.assert_no_estimator_runtime()
    for name in g.FORBIDDEN_RUNTIME_MODULES:
        assert name not in sys.modules or getattr(
            sys.modules[name], "__name__", "") not in vars(g)


@pytest.mark.parametrize("module_path", ["src", "runner"])
def test_ast_proves_no_estimator_import_is_reachable(module_path):
    """Static proof: neither file imports a forbidden runtime."""
    path = SRC_PATH if module_path == "src" else RUNNER_PATH
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported & set(g.FORBIDDEN_RUNTIME_MODULES) == set()


def test_ast_proves_no_estimator_entry_point_is_called():
    """Static proof: no .fit()/.predict()/.resample() call site exists."""
    tree = ast.parse(SRC_PATH.read_text(encoding="utf-8"))
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    assert called & set(g.FORBIDDEN_ESTIMATOR_CALLS) == set()


def test_source_computes_no_predictive_metric():
    source = SRC_PATH.read_text(encoding="utf-8").lower()
    for banned in ("roc_auc_score", "average_precision_score",
                   "precision_recall_curve", "brier_score_loss",
                   "calibration_curve", "shap_values", "smote("):
        assert banned not in source


# --------------------------------------------------------------------------- #
# 30. Upstream immutability, verified against committed history
# --------------------------------------------------------------------------- #

def test_protected_path_set_is_enumerated_from_the_baseline_commit():
    paths = g.enumerate_protected_baseline_files(REPO_ROOT)
    assert tuple(sorted(paths)) == paths
    listed = _git("ls-tree", "-r", "--name-only", g.BASELINE_COMMIT, "--",
                  *g.PROTECTED_TREES).split()
    assert set(paths) == set(listed) | set(g.PROTECTED_EXTRA_FILES)


def test_complete_protected_manifest_is_committed(decision, metadata):
    paths = g.enumerate_protected_baseline_files(REPO_ROOT)
    for artifact in (decision, metadata):
        assert artifact["protected_baseline_commit"] == g.BASELINE_COMMIT
        assert artifact["protected_file_count"] == len(paths)
        assert tuple(sorted(artifact["protected_files_sha256"])) == paths
    assert decision["protected_files_sha256"] == metadata[
        "protected_files_sha256"]


def test_every_protected_file_matches_baseline_bytes(decision):
    for rel, sha in decision["protected_files_sha256"].items():
        path = REPO_ROOT / rel
        assert path.is_file(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, rel


def test_committed_history_is_compared_against_the_exact_baseline(decision):
    report = g.verify_protected_immutability(
        REPO_ROOT, decision["protected_files_sha256"])
    assert report["protected_committed_history_diff_empty"] is True
    changed = _git("diff", "--name-only", f"{g.BASELINE_COMMIT}..HEAD", "--",
                   *g.enumerate_protected_baseline_files(REPO_ROOT))
    assert changed.strip() == ""
    # the ineffective working-tree-only guard must not be used
    worktree_only = '", "'.join(["diff", "--name-only", "HEAD", '--"'])
    assert ('"' + worktree_only) not in SRC_PATH.read_text(encoding="utf-8")


def _sandbox(tmp_path: Path) -> Path:
    dest = tmp_path / "clone"
    subprocess.run(["git", "clone", "--quiet", "--shared",
                    str(REPO_ROOT), str(dest)], check=True, capture_output=True)
    for key, value in (("user.email", "qc@example.invalid"), ("user.name", "qc")):
        subprocess.run(["git", "config", key, value], cwd=dest, check=True)
    return dest


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", message],
                   cwd=root, check=True, capture_output=True)


@pytest.fixture(scope="module")
def manifest(decision) -> dict:
    return dict(decision["protected_files_sha256"])


def test_negative_committing_a_changed_protected_file_is_detected(
        tmp_path, manifest):
    root = _sandbox(tmp_path)
    target = next(iter(sorted(manifest)))
    (root / target).write_bytes((root / target).read_bytes() + b"\n#tamper\n")
    _commit(root, "tamper: modify a protected upstream file")
    with pytest.raises(g.M3MacroDataGateError) as exc:
        g.verify_protected_immutability(root, manifest)
    assert target in str(exc.value)


def test_negative_deleting_a_protected_file_is_detected(tmp_path, manifest):
    root = _sandbox(tmp_path)
    target = next(iter(sorted(manifest)))
    (root / target).unlink()
    _commit(root, "tamper: delete a protected upstream file")
    with pytest.raises(g.M3MacroDataGateError) as exc:
        g.verify_protected_immutability(root, manifest)
    assert target in str(exc.value)


def test_negative_adding_a_tracked_file_in_a_protected_tree_is_detected(
        tmp_path, manifest):
    root = _sandbox(tmp_path)
    intruder = f"{g.PROTECTED_TREES[0]}/intruder.json"
    (root / intruder).write_text("{}\n", encoding="utf-8")
    _commit(root, "tamper: add a tracked file inside a protected tree")
    with pytest.raises(g.M3MacroDataGateError) as exc:
        g.verify_protected_immutability(root, manifest)
    assert "new tracked file" in str(exc.value)


def test_negative_changing_a_stored_hash_is_detected(manifest):
    tampered = dict(manifest)
    target = next(iter(sorted(tampered)))
    tampered[target] = "0" * 64
    with pytest.raises(g.M3MacroDataGateError) as exc:
        g.verify_protected_immutability(REPO_ROOT, tampered)
    assert target in str(exc.value)


def test_negative_dropping_a_manifest_entry_is_detected(manifest):
    tampered = dict(manifest)
    del tampered[next(iter(sorted(tampered)))]
    with pytest.raises(g.M3MacroDataGateError) as exc:
        g.verify_protected_immutability(REPO_ROOT, tampered)
    assert "count" in str(exc.value) or "path set differs" in str(exc.value)


def test_definition_lock_remains_byte_identical_to_its_committed_bytes(lock):
    """The Phase-A lock must not drift after any later execution."""
    rebuilt = g.build_definition_lock(
        REPO_ROOT, g.assess_official_evidence(REPO_ROOT))
    assert rebuilt == lock


# --------------------------------------------------------------------------- #
# 31-35. Gate outcome vocabulary and consistency
# --------------------------------------------------------------------------- #

def test_gate_status_is_in_the_locked_vocabulary(decision):
    assert g.GATE_STATUS_VOCABULARY == (
        "PASS_FOR_M3_INCREMENTAL_EVALUATION",
        "FAIL_M3_DATA_GATE",
        "UNRESOLVED_M3_DATA_GATE")
    assert decision["gate_status"] in g.GATE_STATUS_VOCABULARY
    g.assert_gate_status_in_vocabulary(decision["gate_status"])


def test_unknown_gate_status_fails_closed():
    with pytest.raises(g.M3MacroDataGateError):
        g.assert_gate_status_in_vocabulary("PASS")


def test_observed_gate_status_is_unresolved_with_explicit_reasons(decision):
    assert decision["gate_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert len(decision["unresolved_or_blocker_reasons"]) > 0
    assert decision["human_decision_request"] is not None


def test_unresolved_was_not_converted_from_an_observed_failure(decision):
    """Missing evidence must not be reported as an observed FAIL."""
    assert decision["gate_status"] != "FAIL_M3_DATA_GATE"
    assert decision["official_evidence_assessment"][
        "any_authoritative_data_evidence_obtained"] is False
    for result in decision["per_candidate_gate_rule_results"]:
        assert result["status"] == "UNRESOLVED"


def test_fail_status_would_require_observed_evidence():
    """A FAIL is only reachable when authoritative evidence exists."""
    lock = {"lock_status": g.LOCK_STATUS_RESOLVED,
            "candidates": [{"candidate_id": c, "uniquely_determined": True,
                            "unresolved_lock_field_count": 0}
                           for c in g.M3_CANDIDATE_IDS]}
    evidence = {"any_authoritative_data_evidence_obtained": True,
                "byte_reproducible_probe_count": 3, "probe_count": 3,
                "probes_returning_waf_rejection": 0,
                "probes_returning_captcha": 0, "probes_unreachable": 0}
    results = [{"candidate_id": c, "unresolved_rules": [],
                "failed_rules": ["G01"], "status": "FAIL"}
               for c in g.M3_CANDIDATE_IDS]
    status, reasons = g.determine_gate_status(lock, results, evidence)
    assert status == "FAIL_M3_DATA_GATE"
    assert reasons


def test_pass_requires_every_candidate_and_the_whole_block():
    """A partial block can never produce PASS."""
    lock = {"lock_status": g.LOCK_STATUS_RESOLVED,
            "candidates": [{"candidate_id": c,
                            "uniquely_determined": c != "cand_m3_"
                            "policy_financing_rate",
                            "unresolved_lock_field_count": 0}
                           for c in g.M3_CANDIDATE_IDS]}
    evidence = {"any_authoritative_data_evidence_obtained": True,
                "byte_reproducible_probe_count": 3, "probe_count": 3,
                "probes_returning_waf_rejection": 0,
                "probes_returning_captcha": 0, "probes_unreachable": 0}
    results = [{"candidate_id": c, "unresolved_rules": [], "failed_rules": [],
                "status": "PASS"} for c in g.M3_CANDIDATE_IDS]
    lock["lock_status"] = g.LOCK_STATUS_UNRESOLVED
    status, _ = g.determine_gate_status(lock, results, evidence)
    assert status == "UNRESOLVED_M3_DATA_GATE"


def test_no_partial_block_admission(decision, common_sample):
    assert decision["partial_block_admitted"] is False
    assert decision["candidate_silently_dropped"] is False
    assert decision["block_reduced_expanded_or_reordered"] is False
    assert common_sample[
        "candidate_dropped_to_let_smaller_block_pass"] is False
    assert decision["m3_block_admitted_for_incremental_evaluation"] is False


def test_coverage_is_null_never_zero(common_sample):
    for row in _rows(g.COVERAGE_AUDIT_REL):
        assert row["valid_coverage"] == ""
        assert row["coverage_is_null_not_zero"] == "True"
        assert row["coverage_status"] == "UNRESOLVED"
    assert common_sample["exact_three_variable_common_sample_coverage"] is None
    assert common_sample["coverage_is_null_not_zero"] is True


# --------------------------------------------------------------------------- #
# 36-40. Pointers and state
# --------------------------------------------------------------------------- #

def test_pointer_did_not_advance_because_the_gate_did_not_pass(decision):
    assert decision["gate_status"] != "PASS_FOR_M3_INCREMENTAL_EVALUATION"
    assert decision["next_research_action_id"] != (
        "stage128-m3-incremental-evaluation")
    assert decision["last_completed_research_action_id"] == (
        "stage128-m2-retained-block-human-decision")
    assert decision["m3_macro_data_gate_human_review_required"] is True
    assert decision["research_pointer_advanced"] is False


def test_next_pointer_is_never_an_authorization(decision):
    assert decision["next_research_action_pointer_is_not_authorization"] is True
    assert decision["m3_incremental_evaluation_authorized"] is False


def test_gate_execution_is_distinguished_from_modeling(decision):
    assert decision["m3_macro_data_gate_executed"] is True
    assert decision["m3_data_workstream_started"] is True
    assert decision["m3_modeling_started"] is False
    assert decision["m3_incremental_evaluation_authorized"] is False


def test_m4_remains_unauthorized_and_unstarted(decision):
    assert decision["m4_authorized"] is False
    assert decision["m4_started"] is False


def test_final_test_remains_locked(decision):
    assert decision["final_test_locked"] is True
    assert decision["final_test_access_authorized"] is False
    assert decision["final_test_evaluation_performed"] is False


def test_merge_is_not_authorized(decision, authorization):
    assert decision["merge_authorized"] is False
    assert authorization["merge_authorized"] is False


# --------------------------------------------------------------------------- #
# QC report and package integrity
# --------------------------------------------------------------------------- #

def test_qc_report_passes_and_covers_the_required_checks(qc):
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["failed_assertions"] == []
    assert qc["assertion_count"] >= 40
    names = {a["name"] for a in qc["assertions"]}
    for required in (
        "authorization_byte_length_is_28",
        "authorization_sha256_matches",
        "verbatim_and_normalized_authorization_are_separated",
        "exact_baseline_commit",
        "exact_m3_candidate_list_and_order",
        "exact_source_id_requirement",
        "forbidden_substitutions_absent",
        "definition_lock_created_before_value_level_execution",
        "definition_lock_sha_referenced_by_gate_decision",
        "no_alternative_series_tried_after_coverage_inspection",
        "g01_to_g08_evaluated_individually",
        "candidate_coverage_threshold_is_exactly_0_80",
        "common_sample_threshold_is_exactly_0_70",
        "validation_positive_floor_is_exactly_5",
        "historical_80_pair_pilot_thresholds_not_used",
        "exact_retained_m2_parent_sample_identity",
        "no_parent_row_substitution",
        "exact_temporal_folds",
        "strict_available_at_before_cutoff_rule_registered",
        "same_day_observations_rejected_unless_timestamp_verified",
        "missing_availability_treated_as_unavailable",
        "revision_or_vintage_policy_verified",
        "no_unofficial_or_sci_substitution",
        "exact_joins_and_no_fuzzy_matching",
        "temporal_degrees_audit_completed",
        "company_year_rows_not_reported_as_independent_macro_observations",
        "final_test_rows_and_values_untouched",
        "zero_model_fits_and_predictions",
        "zero_predictive_metrics",
        "zero_bootstrap_holm_shap_smote",
        "upstream_scientific_artifacts_byte_identical",
        "gate_status_belongs_to_locked_vocabulary",
        "pass_cannot_coexist_with_a_failed_or_unresolved_gate",
        "fail_requires_observed_evidence",
        "unresolved_requires_explicit_unresolved_evidence_reason",
        "no_partial_block_admission",
        "next_pointer_advances_only_on_pass",
        "next_pointer_is_not_authorization",
        "m3_modeling_remains_unauthorized_and_unstarted",
        "m4_remains_unauthorized_and_unstarted",
        "final_test_remains_locked",
    ):
        assert required in names, required


def test_every_required_package_artifact_exists():
    for rel in (g.README_REL, g.AUTHORIZATION_REL, g.LOCK_REL,
                g.SOURCE_MANIFEST_REL, g.RAW_EVIDENCE_REL,
                g.NORMALIZED_OBS_REL, g.DEV_FEATURES_REL,
                g.COVERAGE_AUDIT_REL, g.COMMON_SAMPLE_REL, g.EVENT_COUNT_REL,
                g.TEMPORAL_DEGREES_REL, g.FIREWALL_REL, g.DECISION_REL,
                g.QC_REL, g.METADATA_REL):
        assert (REPO_ROOT / rel).is_file(), rel


def test_package_hashes_match_the_committed_artifacts(metadata):
    for rel, sha in metadata["package_artifacts_sha256"].items():
        on_disk = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert on_disk == sha, rel


def test_rebuild_is_deterministic_and_matches_disk():
    built = g.build_package(REPO_ROOT, write=False)
    assert built["gate_status"] == "UNRESOLVED_M3_DATA_GATE"
    for rel, text in built["artifact_texts"].items():
        assert (REPO_ROOT / rel).read_text(encoding="utf-8") == text, rel


def test_readme_states_the_gate_status_and_the_no_superiority_scope():
    readme = (REPO_ROOT / g.README_REL).read_text(encoding="utf-8")
    assert "UNRESOLVED_M3_DATA_GATE" in readme
    assert "does **not** answer whether M3 improves prediction" in readme
    assert "No partial block was admitted." in readme
