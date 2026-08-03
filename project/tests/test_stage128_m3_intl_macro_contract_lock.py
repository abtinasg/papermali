"""Tests — Stage128 M3I-2 prospective contract lock.

Offline and deterministic. No test performs a network request, reads a macro
observation, loads a company row, touches the final test, fits a model or runs
a Data Gate.

The forbidden-token scanners are exercised with tokens assembled at runtime
from fragments, so this file never itself contains a literal forbidden
execution token.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import stage128_m3_intl_macro_contract_lock as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ERROR = m.M3IntlMacroContractLockError


@pytest.fixture(scope="module")
def built():
    return m.build_package(ROOT, write=False)


# --------------------------------------------------------------------------- #
# Identity, authorization and topology
# --------------------------------------------------------------------------- #

def test_action_identity():
    assert m.ACTION_ID == "stage128-m3i2-prospective-contract-lock"
    assert m.CONTRACT_TYPE == (
        "prospective_contract_lock_only_no_data_no_gate_no_modeling")
    assert m.PREDECESSOR_ACTION_ID == "stage128-m3-macro-data-gate"


def test_baseline_is_the_exact_pr73_head_not_main():
    assert m.BASELINE_COMMIT == "e6db63fb7d105f0d3a39db101c9e364161c367e9"
    assert m.BASELINE_BRANCH == "stage128-m3-macro-data-gate"
    assert m.MAIN_COMMIT == "35aaf4b70e9341704ee38be6f8cf2e2519c70bb2"
    assert m.PR_BASE_BRANCH == m.BASELINE_BRANCH != m.MAIN_BRANCH


def test_human_authorization_is_byte_exact():
    checks = m.verify_human_authorization()
    assert checks["human_source_utterance_byte_length"] == 28
    assert checks["human_source_utterance_sha256"] == (
        "d4acc9698f160ed0f252fd3f2a698b2b17916144d3dc182333cd2892a5d23068")


def test_authorization_record_required_fields(built):
    rec = built["authorization_record"]
    assert rec["authorization_text"] == "بریم مرحله بعدی"
    assert rec["authorization_utf8_bytes"] == 28
    assert rec["authorization_sha256"] == m.HUMAN_SOURCE_UTTERANCE_SHA256
    assert rec["authorization_local_timestamp"] == "2026-08-02T20:32:00+03:30"
    assert rec["identical_text_hash_used_for_prior_distinct_action"] is True
    assert rec["scope_identified_by_hash_alone"] is False
    assert rec["authorized_action_id"] == m.ACTION_ID
    assert rec["authorization_consumed"] is True
    assert rec["standing_authorization"] is False
    for field in ("data_retrieval_authorized", "data_gate_authorized",
                  "modeling_authorized",
                  "m3i_incremental_evaluation_authorized", "m4_authorized",
                  "final_test_access_authorized", "merge_authorized"):
        assert rec[field] is False


def test_verbatim_and_derived_authorization_are_separated(built):
    rec = built["authorization_record"]
    assert rec["authorization_text_is_verbatim_human_text"] is True
    assert rec[
        "normalized_authorization_scope_is_derived_not_verbatim_human_text"
    ] is True
    assert rec["authorization_text"] != rec["normalized_authorization_scope"]


# --------------------------------------------------------------------------- #
# Rule 19 — the repeated phrase may not identify scope
# --------------------------------------------------------------------------- #

def test_scope_may_not_be_identified_by_the_repeated_hash_alone(built):
    rec = copy.deepcopy(built["authorization_record"])
    m.assert_scope_not_identified_by_hash_alone(rec)
    rec["scope_identified_by_hash_alone"] = True
    with pytest.raises(ERROR):
        m.assert_scope_not_identified_by_hash_alone(rec)


def test_prior_distinct_use_of_the_same_text_must_be_recorded(built):
    rec = copy.deepcopy(built["authorization_record"])
    rec["identical_text_hash_used_for_prior_distinct_action"] = False
    with pytest.raises(ERROR):
        m.assert_scope_not_identified_by_hash_alone(rec)


# --------------------------------------------------------------------------- #
# Rule 1 — M3-CBI preserved
# --------------------------------------------------------------------------- #

def test_m3_cbi_block_is_preserved_exactly(built):
    block = built["governance_boundary"]["m3_cbi_block"]
    assert block["block"] == [
        "cpi_inflation", "fx_change_official", "policy_financing_rate"]
    assert block["source_id"] == "src_m3_cbi_macro"
    assert block["status"] == "UNRESOLVED_M3_DATA_GATE"
    assert block["block_admitted"] is False
    assert block["modified_by_this_action"] is False
    m.assert_m3_cbi_block_preserved(block)


@pytest.mark.parametrize("mutation", [
    {"block": ["fx_change_official", "cpi_inflation",
               "policy_financing_rate"]},
    {"block": ["cpi_inflation", "fx_change_official"]},
    {"source_id": "src_m3i_wdi_imf_ifs_cpi"},
    {"status": "PASS_FOR_M3_INCREMENTAL_EVALUATION"},
    {"block_admitted": True},
])
def test_m3_cbi_mutations_fail_closed(built, mutation):
    block = copy.deepcopy(built["governance_boundary"]["m3_cbi_block"])
    block.update(mutation)
    with pytest.raises(ERROR):
        m.assert_m3_cbi_block_preserved(block)


def test_m3i_is_not_a_substitution_for_m3_cbi(built):
    gov = built["governance_boundary"]
    assert gov["supplementary_relationship"] == (
        "distinct_supplementary_family_not_substitution_not_correction_not_"
        "continuation_of_M3_CBI")
    assert gov["m3i_is_confirmatory_m3"] is False
    assert built["decision"]["m3_cbi_contract_changed"] is False


# --------------------------------------------------------------------------- #
# Rule 2 — new source ids only
# --------------------------------------------------------------------------- #

def test_source_ids_are_exactly_the_three_new_ones(built):
    rows = built["definition_lock"]["sources"]
    assert [r["source_id"] for r in rows] == [
        "src_m3i_wdi_imf_ifs_cpi", "src_m3i_wdi_imf_ifs_fx",
        "src_m3i_imf_mfs_interest_rate"]
    m.assert_source_ids_not_reused(rows)


@pytest.mark.parametrize("reused", ["src_m3_cbi_macro", "src_m3_sci_macro"])
def test_reusing_a_frozen_source_id_fails_closed(built, reused):
    rows = copy.deepcopy(built["definition_lock"]["sources"])
    rows[0]["source_id"] = reused
    with pytest.raises(ERROR):
        m.assert_source_ids_not_reused(rows)


def test_reference_urls_are_frozen_strings_never_fetched(built):
    lock = built["definition_lock"]
    assert lock["reference_urls_fetched_in_this_action"] is False
    for row in lock["sources"]:
        assert row["reference_fetched_in_this_action"] is False
        assert row["retrieval_status"] == "not_authorized"
        assert row["admitted"] is False
    assert m.CPI_METADATA_URL.endswith("FP.CPI.TOTL.ZG")
    assert m.FX_METADATA_URL.endswith("PA.NUS.FCRF")
    assert m.FINANCING_DATASET_URL.endswith("IMF.STA%3AMFS_IR")


# --------------------------------------------------------------------------- #
# Rules 3-7 — the exact M3I-2 definition lock
# --------------------------------------------------------------------------- #

def test_m3i2_block_and_positions(built):
    lock = built["definition_lock"]
    assert lock["m3i2_block"] == [
        "intl_cpi_inflation_annual", "intl_fx_change_official_annual"]
    cpi, fx = lock["m3i2_candidates"]
    assert (cpi["block_id"], cpi["block_position"]) == ("M3I-2", 1)
    assert (fx["block_id"], fx["block_position"]) == ("M3I-2", 2)
    assert cpi["role"] == fx["role"] == "supplementary_candidate"


def test_cpi_candidate_is_the_exact_wdi_series(built):
    cpi = built["definition_lock"]["m3i2_candidates"][0]
    assert cpi["candidate_id"] == "cand_m3i_cpi_inflation_annual"
    assert cpi["indicator_code"] == "FP.CPI.TOTL.ZG"
    assert cpi["official_series_title"] == (
        "Inflation, consumer prices (annual % growth)")
    assert cpi["frequency"] == "annual"
    assert cpi["unit"] == "percent"
    assert cpi["calendar"] == "Gregorian calendar year"
    assert cpi["transformation_formula"] == "identity"
    assert cpi["transformation_window"] == "none"
    assert cpi["higher_value_interpretation"] == (
        "higher consumer-price inflation")
    assert cpi["uniquely_determined"] is True
    m.assert_cpi_indicator_code(cpi)


@pytest.mark.parametrize("mutation", [
    {"indicator_code": "FP.CPI.TOTL"},
    {"indicator_code": "NY.GDP.DEFL.KD.ZG"},
    {"transformation_formula": "12-month moving average"},
    {"frequency": "monthly"},
])
def test_wrong_cpi_definition_fails_closed(built, mutation):
    cpi = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][0])
    cpi.update(mutation)
    with pytest.raises(ERROR):
        m.assert_cpi_indicator_code(cpi)


def test_fx_candidate_is_the_exact_official_rate(built):
    fx = built["definition_lock"]["m3i2_candidates"][1]
    assert fx["candidate_id"] == "cand_m3i_fx_change_official_annual"
    assert fx["indicator_code"] == "PA.NUS.FCRF"
    assert fx["source_unit"] == "LCU per US dollar"
    assert fx["output_unit"] == "percent_log_change"
    assert fx["transformation_formula"] == "100 * ln(E_y / E_(y-1))"
    assert fx["transformation_window"] == (
        "two consecutive annual observations from the same vintage")
    assert fx["higher_value_interpretation"] == (
        "local-currency depreciation against the US dollar")
    m.assert_fx_indicator_code(fx)
    m.assert_fx_transformation(fx)


def test_fx_atls_is_rejected(built):
    fx = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][1])
    fx["indicator_code"] = "PA.NUS.ATLS"
    with pytest.raises(ERROR):
        m.assert_fx_indicator_code(fx)


@pytest.mark.parametrize("formula", [
    "100 * (E_y / E_(y-1) - 1)",
    "ln(E_y / E_(y-1))",
    "100 * ln(E_(y-1) / E_y)",
])
def test_wrong_fx_transformation_fails_closed(built, formula):
    fx = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][1])
    fx["transformation_formula"] = formula
    with pytest.raises(ERROR):
        m.assert_fx_transformation(fx)


def test_fx_fail_closed_conditions_are_exact(built):
    fx = built["definition_lock"]["m3i2_candidates"][1]
    assert fx["fail_closed_transformation_conditions"] == [
        "E_y missing -> null",
        "E_(y-1) missing -> null",
        "E_y <= 0 -> null",
        "E_(y-1) <= 0 -> null",
        "years non-consecutive -> null",
        "vintages differ -> null",
    ]


def test_forbidden_alternatives_are_recorded(built):
    cpi, fx = built["definition_lock"]["m3i2_candidates"]
    assert "monthly inflation" in cpi["forbidden_alternatives"]
    assert "silent SCI substitution" in cpi["forbidden_alternatives"]
    assert "PA.NUS.ATLS" in fx["forbidden_alternatives"]
    assert "manual Iranian regime splice" in fx["forbidden_alternatives"]


# --------------------------------------------------------------------------- #
# Blocker 1 — the observation year INSIDE the selected vintage
# --------------------------------------------------------------------------- #


def test_both_candidates_carry_an_exact_observation_year_rule(built):
    for cand in built["definition_lock"]["m3i2_candidates"]:
        m.assert_observation_year_selection_rule(cand)
        m.assert_uniqueness_requires_selection_rule(cand)
        assert cand["annual_period_end_definition"] == (
            "December 31 of the labelled Gregorian observation year")
        assert cand["completed_annual_period_required"] is True
        assert cand["selected_observation_tie_breaker"] == (
            "maximum_observation_year")
        assert cand["current_or_future_incomplete_calendar_year_allowed"] is (
            False)
        assert cand["fiscal_year_label_only_mapping_allowed"] is False
        assert cand["no_eligible_observation_policy"] is None
        assert cand["observation_year_operational_definition"]


def test_cpi_observation_year_rule_text_is_exact(built):
    cpi = built["definition_lock"]["m3i2_candidates"][0]
    assert cpi["observation_year_selection_rule"] == (
        "Within the selected pre-cutoff WDI archive vintage, choose the "
        "maximum Gregorian observation year y for which FP.CPI.TOTL.ZG[y] is "
        "non-missing and December 31 of y is strictly earlier than the pair "
        "prediction cutoff.")
    steps = cpi["observation_year_operational_definition"]
    assert any(s.startswith("y = max {year:") for s in steps)
    assert "If the set is empty, return null." in steps
    assert "Do not use fiscal year as a direct year lookup." in steps
    assert "Do not try another indicator." in steps


def test_fx_observation_year_rule_text_and_eligibility_are_exact(built):
    fx = built["definition_lock"]["m3i2_candidates"][1]
    assert fx["observation_year_selection_rule"] == (
        "Within the selected pre-cutoff WDI archive vintage, choose the "
        "maximum Gregorian observation year y such that E_y and E_(y-1) are "
        "both non-missing, positive, consecutive annual observations, "
        "December 31 of y is strictly earlier than the pair prediction "
        "cutoff, and both observations have the same verified currency "
        "denomination and valuation definition.")
    assert fx["observation_year_eligibility_conditions"] == [
        "E_y present", "E_(y-1) present", "E_y > 0", "E_(y-1) > 0",
        "years consecutive", "same selected vintage",
        "Dec-31(y) < pair_cutoff", "same verified currency denomination",
        "same verified local-currency valuation definition",
    ]
    steps = fx["observation_year_operational_definition"]
    assert "selected y = maximum eligible y" in steps
    assert "If no eligible pair exists, return null." in steps


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("mutation", [
    # the first/earliest available year selected instead of the maximum
    {"selected_observation_tie_breaker": "first_available_observation_year"},
    {"selected_observation_tie_breaker": "minimum_observation_year"},
    # a fiscal-year label mapped directly onto the WDI year
    {"fiscal_year_label_only_mapping_allowed": True},
    # an annual period that ends on or after the cutoff
    {"current_or_future_incomplete_calendar_year_allowed": True},
    {"completed_annual_period_required": False},
    {"annual_period_end_definition": "the fiscal year-end of the company"},
    # "no eligible observation" silently resolved to something other than null
    {"no_eligible_observation_policy": "use_nearest_available_year"},
    {"no_eligible_observation_policy": "carry_forward_last_value"},
    # the rule itself removed
    {"observation_year_selection_rule": ""},
    {"observation_year_operational_definition": []},
])
def test_observation_year_rule_mutations_fail_closed(built, index, mutation):
    cand = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    cand.update(mutation)
    with pytest.raises(ERROR):
        m.assert_observation_year_selection_rule(cand)


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("field", [
    "observation_year_selection_rule",
    "observation_year_operational_definition",
    "selected_observation_tie_breaker",
    "current_or_future_incomplete_calendar_year_allowed",
    "no_eligible_observation_policy",
    "annual_period_end_definition",
    "completed_annual_period_required",
    "fiscal_year_label_only_mapping_allowed",
])
def test_a_deleted_observation_year_field_fails_closed(built, index, field):
    cand = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    cand.pop(field)
    with pytest.raises(ERROR):
        m.assert_observation_year_selection_rule(cand)


@pytest.mark.parametrize("index", [0, 1])
def test_uniqueness_claimed_after_rule_removal_fails_closed(built, index):
    cand = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    assert cand["uniquely_determined"] is True
    cand.pop("observation_year_selection_rule")
    with pytest.raises(ERROR):
        m.assert_uniqueness_requires_selection_rule(cand)

    other = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    other["observation_year_operational_definition"] = []
    with pytest.raises(ERROR):
        m.assert_uniqueness_requires_selection_rule(other)


def test_an_arbitrary_consecutive_fx_pair_is_not_eligible(built):
    """Only the MAXIMUM eligible pair may be used, never any pair."""
    fx = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][1])
    fx["observation_year_selection_rule"] = (
        "Use any two consecutive annual observations available in the "
        "selected vintage.")
    fx["selected_observation_tie_breaker"] = "any_consecutive_pair"
    with pytest.raises(ERROR):
        m.assert_observation_year_selection_rule(fx)


def test_prediction_time_contract_carries_the_selection_rules(built):
    pt = built["prediction_time_contract"]
    rules = pt["observation_year_selection_rules"]
    assert set(rules) == {"cand_m3i_cpi_inflation_annual",
                          "cand_m3i_fx_change_official_annual"}
    assert pt["selected_observation_tie_breaker"] == (
        "maximum_observation_year")
    assert pt["current_or_future_incomplete_calendar_year_allowed"] is False
    assert pt["no_eligible_observation_policy"] is None
    assert pt["observation_years_selected_in_this_action"] == 0


# --------------------------------------------------------------------------- #
# Blocker 2 — historical-vintage semantic / currency-unit compatibility
# --------------------------------------------------------------------------- #


def test_both_candidates_require_vintage_semantic_compatibility(built):
    for cand in built["definition_lock"]["m3i2_candidates"]:
        m.assert_vintage_semantic_compatibility(cand)
        assert cand["vintage_semantic_compatibility_required"] is True
        assert cand["vintage_semantic_compatibility_status"] == "NOT_EXECUTED"
        assert cand[
            "historical_archive_metadata_assumed_identical_to_current"] is (
            False)
        assert cand[
            "semantic_compatibility_evidence_required_before_value_use"] is True
        assert cand["semantic_mismatch_policy"] == (
            "null_and_invalid_for_coverage")
        assert cand["alternative_series_after_mismatch_allowed"] is False
        assert cand["vintage_evidence_required_fields"] == [
            "archive edition identifier",
            "release date and, if available, release time",
            "Iran economy identity",
            "indicator code",
            "series title or archived label compatible with the locked title",
            "frequency = annual",
            "unit compatible with the locked unit",
            "calendar-year observation semantics",
            "raw archive artifact SHA-256",
        ]


def test_cpi_must_remain_an_annual_inflation_rate_series(built):
    cpi = built["definition_lock"]["m3i2_candidates"][0]
    text = cpi["semantic_compatibility_requirement"]
    assert "inflation-RATE" in text and "percent" in text
    assert "index-level" in text and "GDP-deflator" in text
    assert "index level instead of annual rate" in cpi[
        "semantic_mismatch_examples"]


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("mutation", [
    # the compatibility requirement switched off
    {"vintage_semantic_compatibility_required": False},
    {"semantic_compatibility_evidence_required_before_value_use": False},
    # current metadata silently assumed to describe every historical vintage
    {"historical_archive_metadata_assumed_identical_to_current": True},
    # a mismatch tolerated instead of nulled
    {"semantic_mismatch_policy": "use_value_anyway"},
    {"semantic_mismatch_policy": "rescale_to_the_current_base_year"},
    # a mismatch followed by an alternative-series selection
    {"alternative_series_after_mismatch_allowed": True},
    # verification falsely claimed complete in this metadata-only action
    {"vintage_semantic_compatibility_status": "VERIFIED"},
    # the evidence list quietly shortened
    {"vintage_evidence_required_fields": ["indicator code"]},
])
def test_vintage_compatibility_mutations_fail_closed(built, index, mutation):
    cand = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    cand.update(mutation)
    with pytest.raises(ERROR):
        m.assert_vintage_semantic_compatibility(cand)


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("field", [
    "vintage_semantic_compatibility_required",
    "vintage_semantic_compatibility_status",
    "historical_archive_metadata_assumed_identical_to_current",
    "semantic_compatibility_evidence_required_before_value_use",
    "semantic_mismatch_policy",
    "alternative_series_after_mismatch_allowed",
    "vintage_evidence_required_fields",
])
def test_an_absent_compatibility_field_fails_closed(built, index, field):
    cand = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][index])
    cand.pop(field)
    with pytest.raises(ERROR):
        m.assert_vintage_semantic_compatibility(cand)


def test_fx_pair_must_share_currency_denomination_and_valuation(built):
    fx = built["definition_lock"]["m3i2_candidates"][1]
    m.assert_fx_currency_compatibility(fx)
    assert fx["same_currency_denomination_required_across_pair"] is True
    assert fx[
        "same_local_currency_valuation_definition_required_across_pair"] is True
    assert fx["redenomination_or_unit_break_policy"] == (
        "null_and_invalid_for_coverage")
    assert fx["pair_compatibility_verification_required"] == [
        "E_y and E_(y-1) use identical currency denomination",
        "E_y and E_(y-1) use identical local-currency valuation convention",
        "no currency-unit break or redenomination exists across the pair",
        "E_y and E_(y-1) belong to the same archive vintage",
    ]


@pytest.mark.parametrize("mutation", [
    # a currency-denomination mismatch tolerated
    {"same_currency_denomination_required_across_pair": False},
    # a valuation-definition mismatch tolerated
    {"same_local_currency_valuation_definition_required_across_pair": False},
    # a redenomination or unit break accepted instead of nulled
    {"redenomination_or_unit_break_policy": "rescale_by_the_conversion_factor"},
    {"redenomination_or_unit_break_policy": "accept"},
    # the verification list shortened
    {"pair_compatibility_verification_required": []},
])
def test_fx_currency_compatibility_mutations_fail_closed(built, mutation):
    fx = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][1])
    fx.update(mutation)
    with pytest.raises(ERROR):
        m.assert_fx_currency_compatibility(fx)


@pytest.mark.parametrize("field", m.FX_CURRENCY_COMPATIBILITY_REQUIRED_FIELDS)
def test_an_absent_fx_currency_field_fails_closed(built, field):
    fx = copy.deepcopy(built["definition_lock"]["m3i2_candidates"][1])
    fx.pop(field)
    with pytest.raises(ERROR):
        m.assert_fx_currency_compatibility(fx)


def test_an_unverified_vintage_is_never_valid_coverage(built):
    gate = built["data_gate_contract"]
    m.assert_unverified_vintage_is_not_valid_coverage(gate)
    assert gate["unverified_vintage_counts_as_valid_coverage"] is False
    assert gate["semantic_mismatch_policy"] == "null_and_invalid_for_coverage"
    assert gate["alternative_series_after_mismatch_allowed"] is False


@pytest.mark.parametrize("mutation", [
    {"unverified_vintage_counts_as_valid_coverage": True},
    {"semantic_mismatch_policy": "count_as_valid"},
])
def test_counting_an_unverified_vintage_fails_closed(built, mutation):
    gate = copy.deepcopy(built["data_gate_contract"])
    gate.update(mutation)
    with pytest.raises(ERROR):
        m.assert_unverified_vintage_is_not_valid_coverage(gate)


def test_prediction_time_contract_records_zero_vintage_work(built):
    pt = built["prediction_time_contract"]
    assert pt["vintage_semantic_compatibility_required"] is True
    assert pt["vintage_semantic_compatibility_status"] == "NOT_EXECUTED"
    assert pt["historical_archive_metadata_assumed_identical_to_current"] is (
        False)
    assert pt["unverified_vintage_counts_as_valid_coverage"] is False
    assert pt["vintage_compatibility_verifications_in_this_action"] == 0
    assert pt["archive_editions_downloaded_in_this_action"] == 0
    assert pt["vintages_applied_in_this_action"] == 0


def test_a_reduced_one_variable_block_fails_closed():
    m.assert_m3i2_block_not_reduced(m.M3I2_BLOCK)
    with pytest.raises(ERROR):
        m.assert_m3i2_block_not_reduced(("intl_cpi_inflation_annual",))
    with pytest.raises(ERROR):
        m.assert_m3i2_block_not_reduced(
            ("intl_fx_change_official_annual", "intl_cpi_inflation_annual"))


# --------------------------------------------------------------------------- #
# Rules 8-9 — the contingent financing shell
# --------------------------------------------------------------------------- #

def test_financing_shell_is_entirely_unresolved(built):
    fin = built["definition_lock"]["m3i3_candidate"]
    assert fin["candidate_id"] == "cand_m3i_financing_rate"
    assert fin["block_id"] == "M3I-3"
    assert fin["block_position"] == 3
    assert fin["role"] == "contingent_supplementary_candidate"
    assert fin["preferred_dataset_id"] == "IMF.STA:MFS_IR"
    assert fin["unit"] == "percent"
    for field in m.FINANCING_REQUIRED_METADATA_FIELDS:
        assert fin[field] is None
    assert fin["candidate_selection_status"] == "UNRESOLVED_METADATA_LOCK"
    assert fin["uniquely_determined"] is False
    assert fin["admitted"] is False
    m.assert_financing_metadata_lock(fin)


def test_financing_admitted_with_null_metadata_fails_closed(built):
    fin = copy.deepcopy(built["definition_lock"]["m3i3_candidate"])
    fin["admitted"] = True
    with pytest.raises(ERROR):
        m.assert_financing_metadata_lock(fin)


def test_financing_cannot_be_uniquely_determined_while_null(built):
    fin = copy.deepcopy(built["definition_lock"]["m3i3_candidate"])
    fin["uniquely_determined"] = True
    with pytest.raises(ERROR):
        m.assert_financing_metadata_lock(fin)


@pytest.mark.parametrize("title", [
    "Deposit interest rate",
    "Deposit-rate ceiling, one-year",
    "Real interest rate",
    "Interest-rate spread",
    "Repo transaction volume",
])
def test_forbidden_financing_proxies_fail_closed(built, title):
    fin = copy.deepcopy(built["definition_lock"]["m3i3_candidate"])
    fin["exact_series_title"] = title
    with pytest.raises(ERROR):
        m.assert_financing_construct_not_a_forbidden_proxy(fin)


def test_financing_forbidden_proxy_list_may_not_be_shortened(built):
    fin = copy.deepcopy(built["definition_lock"]["m3i3_candidate"])
    fin["forbidden_proxies"] = fin["forbidden_proxies"][:3]
    with pytest.raises(ERROR):
        m.assert_financing_construct_not_a_forbidden_proxy(fin)


def test_financing_stop_rule_keeps_m3i2_valid(built):
    fin = built["definition_lock"]["m3i3_candidate"]
    assert "M3I-2 is not invalidated" in fin["stop_rule"]
    assert "No fourth variable" in fin["stop_rule"]
    assert built["decision"]["m3i3_admitted"] is False
    assert built["decision"]["m3i3_financing_lock"] == (
        "UNRESOLVED_METADATA_LOCK")


def test_m3i3_block_is_m3i2_plus_financing():
    assert m.M3I3_BLOCK == m.M3I2_BLOCK + ("intl_financing_rate",)


# --------------------------------------------------------------------------- #
# Rule 10 — multiplicity
# --------------------------------------------------------------------------- #

def test_original_confirmatory_family_is_unchanged(built):
    mult = built["multiplicity_contract"]
    assert mult["original_confirmatory_family"] == [
        "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
    assert mult["original_confirmatory_family_complete"] is False
    assert mult["M3I_inserted_into_original_family"] is False
    m.assert_confirmatory_family_unchanged(mult)


def test_inserting_m3i_into_the_confirmatory_family_fails_closed(built):
    mult = copy.deepcopy(built["multiplicity_contract"])
    mult["original_confirmatory_family"] = [
        "M2_minus_M1", "M3_CBI_minus_M2", "M3I_2_minus_retained_M2",
        "M4_minus_M3_CBI"]
    with pytest.raises(ERROR):
        m.assert_confirmatory_family_unchanged(mult)


def test_declaring_the_confirmatory_family_complete_fails_closed(built):
    mult = copy.deepcopy(built["multiplicity_contract"])
    mult["original_confirmatory_family_complete"] = True
    with pytest.raises(ERROR):
        m.assert_confirmatory_family_unchanged(mult)


def test_no_holm_execution_in_this_action(built):
    mult = built["multiplicity_contract"]
    assert mult["holm_executions"] == 0
    assert mult["comparisons_executed"] == 0
    bad = copy.deepcopy(mult)
    bad["holm_executions"] = 1
    with pytest.raises(ERROR):
        m.assert_confirmatory_family_unchanged(bad)


def test_supplementary_family_is_separate_and_not_yet_existing(built):
    mult = built["multiplicity_contract"]
    assert [row["comparison"] for row in mult["supplementary_family"]] == [
        "M3I_2_minus_retained_M2", "M3I_3_minus_M3I_2"]
    assert all(row["exists_now"] is False
               for row in mult["supplementary_family"])
    assert mult["supplementary_family_size_now"] == 0
    assert mult["results_label"] == "supplementary_robustness_only"
    assert mult["confirmatory_superiority_claim_permitted"] is False


# --------------------------------------------------------------------------- #
# Rule 11 — unresolved is null, never zero
# --------------------------------------------------------------------------- #

def test_gate_contract_is_not_executed_and_values_are_null(built):
    gate = built["data_gate_contract"]
    assert gate["gate_result"] == "NOT_EXECUTED"
    assert gate["gate_executed"] is False
    assert gate["coverage_calculations"] == 0
    assert set(gate["observed_values"]) == set(m.UNRESOLVED_NULL_FIELDS)
    assert all(v is None for v in gate["observed_values"].values())
    m.assert_unresolved_values_are_null_not_zero(gate)


@pytest.mark.parametrize("field", list(m.UNRESOLVED_NULL_FIELDS))
def test_zero_in_place_of_unresolved_fails_closed(built, field):
    gate = copy.deepcopy(built["data_gate_contract"])
    gate["observed_values"][field] = 0
    with pytest.raises(ERROR):
        m.assert_unresolved_values_are_null_not_zero(gate)


def test_claiming_gate_execution_fails_closed(built):
    gate = copy.deepcopy(built["data_gate_contract"])
    gate["gate_result"] = "PASS_FOR_M3I2_INCREMENTAL_EVALUATION"
    with pytest.raises(ERROR):
        m.assert_unresolved_values_are_null_not_zero(gate)


def test_gate_thresholds_are_inherited_unchanged(built):
    t = built["data_gate_contract"]["thresholds"]
    assert t["candidate_valid_coverage_min"] == 0.80
    assert t["block_common_sample_coverage_min"] == 0.70
    assert t["minimum_positive_evaluable_each_locked_validation_window"] == 5
    assert t["coverage_scope"] == "development_only"
    assert t["denominator"] == "retained_M2_development_common_sample"
    assert t["expected_parent_rows"] == 539
    assert t["expected_parent_positive"] == 55
    assert t["expected_parent_negative"] == 484
    assert t["expected_parent_companies"] == 108
    assert t["final_test_access_for_admission"] is False


def test_future_gate_rules_forbid_a_reduced_block(built):
    rules = built["data_gate_contract"]["future_rules"]
    assert "A reduced one-variable M3I-1 cannot pass." in rules
    assert built["data_gate_contract"][
        "reduced_one_variable_block_can_pass"] is False
    assert any("Financing failure does not invalidate" in r for r in rules)


# --------------------------------------------------------------------------- #
# Prediction-time, vintage and missing-value contracts
# --------------------------------------------------------------------------- #

def test_frozen_prediction_cutoff_is_preserved(built):
    pt = built["prediction_time_contract"]
    assert pt["frozen_project_prediction_cutoff"].startswith(
        "The earliest verified available_at timestamp")
    assert pt["frozen_project_prediction_cutoff_changed_by_this_action"] is (
        False)
    assert pt["macro_availability_rule"] == (
        "macro_release_available_at < pair_prediction_cutoff")


def test_wdi_as_of_rules_are_complete_and_ordered(built):
    rules = built["prediction_time_contract"]["wdi_as_of_rules"]
    assert len(rules) == 10
    assert rules[0].startswith("Use the latest official WDI Database Archive")
    assert "00:00:00 UTC on the next calendar day" in rules[4]
    assert built["prediction_time_contract"][
        "date_only_release_on_cutoff_date_is_excluded"] is True
    assert built["prediction_time_contract"][
        "fiscal_year_label_only_mapping_allowed"] is False
    assert built["prediction_time_contract"][
        "jalali_and_gregorian_dates_preserved_separately"] is True


def test_fx_levels_must_share_a_vintage(built):
    assert built["prediction_time_contract"]["fx_same_vintage_rule"] == (
        "Both annual exchange-rate levels used in the log change must come "
        "from the same selected vintage.")


def test_missing_value_contract_forbids_every_fill(built):
    mv = built["definition_lock"]["missing_value_contract"]
    assert mv["rules"] == [
        "missing remains null", "no interpolation", "no extrapolation",
        "no cross-source fill",
        "no backward reconstruction from a later vintage",
        "no source switching", "no manual correction",
        "no imputation before Data Gate admission"]
    assert mv["value_level_imputation_authorized"] is False


# --------------------------------------------------------------------------- #
# Rules 12-15 — no execution paths anywhere in this action's code
# --------------------------------------------------------------------------- #

def test_implementation_files_exist():
    for rel in m.IMPLEMENTATION_FILES:
        assert (ROOT / rel).is_file(), rel


def test_no_network_observation_estimator_or_final_test_path():
    m.assert_no_network_paths(ROOT)
    m.assert_no_observation_ingestion_paths(ROOT)
    m.assert_no_estimator_paths(ROOT)
    m.assert_no_final_test_access_paths(ROOT)
    m.assert_no_estimator_runtime()


def _write_probe(tmp_path: Path, body: str) -> Path:
    """Materialize a fake repo whose implementation files contain ``body``."""
    for rel in m.IMPLEMENTATION_FILES:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("fragments,checker", [
    (("import ", "requests"), "assert_no_network_paths"),
    (("import ", "urllib.request"), "assert_no_network_paths"),
    (("x = ", "requests", ".get(url)"), "assert_no_network_paths"),
    (("x = url", "open(url)"), "assert_no_network_paths"),
    (("import ", "pandas as pd"), "assert_no_observation_ingestion_paths"),
    (("df = pd.", "read_", "csv", "(path)"),
     "assert_no_observation_ingestion_paths"),
    (("import ", "sklearn.linear_model"), "assert_no_estimator_paths"),
    (("model", ".fit", "(X, y)"), "assert_no_estimator_paths"),
    (("p = model", ".predict", "(X)"), "assert_no_estimator_paths"),
    (("path = 'outputs/", "05_final_test", "/rows.csv'"),
     "assert_no_final_test_access_paths"),
])
def test_forbidden_paths_fail_closed(tmp_path, fragments, checker):
    body = "".join(fragments) + "\n"
    root = _write_probe(tmp_path, body)
    with pytest.raises(ERROR):
        getattr(m, checker)(root)


def test_a_clean_probe_repo_passes_every_scanner(tmp_path):
    root = _write_probe(tmp_path, "VALUE = 1\n")
    m.assert_no_network_paths(root)
    m.assert_no_observation_ingestion_paths(root)
    m.assert_no_estimator_paths(root)
    m.assert_no_final_test_access_paths(root)


def test_missing_implementation_file_fails_closed(tmp_path):
    with pytest.raises(ERROR):
        m.assert_no_network_paths(tmp_path)


def test_module_imports_only_the_standard_library():
    forbidden = set(m.FORBIDDEN_RUNTIME_MODULES)
    imported = {getattr(v, "__name__", "")
                for v in vars(m).values() if hasattr(v, "__name__")}
    assert not (imported & forbidden)


# --------------------------------------------------------------------------- #
# Rules 16-17 — firewall flags
# --------------------------------------------------------------------------- #

def test_no_m4_or_merge_flag_anywhere_in_the_package(built):
    payload = {k: v for k, v in built.items() if k != "artifact_texts"}
    m.assert_no_m4_start_flag(payload)
    m.assert_no_merge_authorized_flag(payload)


def test_an_m4_start_flag_fails_closed():
    with pytest.raises(ERROR):
        m.assert_no_m4_start_flag({"state": {"m4_started": True}})
    with pytest.raises(ERROR):
        m.assert_no_m4_start_flag({"state": {"m4_authorized": True}})


def test_a_merge_authorized_flag_fails_closed():
    with pytest.raises(ERROR):
        m.assert_no_merge_authorized_flag({"pr": {"merge_authorized": True}})


def test_final_test_stays_locked(built):
    d = built["decision"]
    assert d["final_test_locked"] is True
    assert d["final_test_access_authorized"] is False
    assert d["final_test_rows_loaded"] == 0
    assert built["governance_boundary"]["final_test_target_years"] == [
        1400, 1401, 1402]


# --------------------------------------------------------------------------- #
# Rule 18 — the stacked PR may not target main
# --------------------------------------------------------------------------- #

def test_pr_base_is_the_open_pr73_branch(built):
    d = built["decision"]
    assert d["pr_base_branch"] == "stage128-m3-macro-data-gate"
    assert d["pr_is_draft"] is True
    assert d["predecessor_pr_merged"] is False
    assert d["may_target_main"] is False
    m.assert_pr_base_is_not_main(d)


@pytest.mark.parametrize("mutation", [
    {"pr_base_branch": "main"},
    {"predecessor_pr_merged": True},
])
def test_retargeting_to_main_fails_closed(built, mutation):
    d = copy.deepcopy(built["decision"])
    d.update(mutation)
    with pytest.raises(ERROR):
        m.assert_pr_base_is_not_main(d)


# --------------------------------------------------------------------------- #
# Rule 20 — protected prior scientific artifacts
# --------------------------------------------------------------------------- #

def test_protected_trees_cover_the_required_scope():
    assert "project/stage125" in m.PROTECTED_TREES
    assert "project/stage127" in m.PROTECTED_TREES
    assert "project/stage128/m3_macro_data_gate" in m.PROTECTED_TREES
    assert any(t.startswith("project/stage128/m2_") for t in m.PROTECTED_TREES)


def test_protected_artifacts_are_byte_identical_to_the_pr73_head(built):
    imm = built["decision"]["protected_immutability"]
    assert imm["protected_baseline_commit"] == m.BASELINE_COMMIT
    assert imm["protected_bytes_match_baseline"] is True
    assert imm["protected_paths_match_baseline"] is True
    assert imm["protected_tree_has_no_new_tracked_files"] is True
    assert imm["protected_committed_history_diff_empty"] is True
    assert imm["protected_file_count"] > 100


def test_a_tampered_protected_manifest_fails_closed(built):
    manifest = dict(built["protected_manifest"])
    victim = sorted(manifest)[0]
    manifest[victim] = "0" * 64
    with pytest.raises(ERROR):
        m.verify_protected_immutability(ROOT, manifest)


def test_the_operational_exclusion_list_is_closed():
    assert m.PROTECTED_OPERATIONAL_EXCLUSIONS == (
        "project/stage126/README_STAGE126_CURRENT_STATE_VALIDATION.md",
        "project/stage126/metadata_and_hashes_stage126_current_state_"
        "validator.json",
        "project/stage126/stage126_current_state_validation_report.json",
    )


# --------------------------------------------------------------------------- #
# Package, QC and on-disk consistency
# --------------------------------------------------------------------------- #

REQUIRED_ARTIFACTS = (
    m.README_REL, m.AUTHORIZATION_REL, m.GOVERNANCE_REL,
    m.SOURCE_REGISTRY_REL, m.DEFINITION_LOCK_REL, m.PREDICTION_TIME_REL,
    m.DATA_GATE_REL, m.MULTIPLICITY_REL, m.DECISION_REL, m.QC_REL,
    m.METADATA_REL,
)


def test_every_required_artifact_is_produced(built):
    assert set(built["artifact_texts"]) == set(REQUIRED_ARTIFACTS)
    assert len(REQUIRED_ARTIFACTS) == 11


def test_qc_passes_and_counts_every_execution_as_zero(built):
    qc = built["qc_report"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 60
    assert qc["execution_counters"] == {
        "network_requests": 0,
        "data_files_downloaded": 0,
        "macro_observations_read": 0,
        "company_rows_loaded": 0,
        "final_test_rows_loaded": 0,
        "model_fits": 0,
        "predictions": 0,
        "predictive_metrics": 0,
        "coverage_calculations": 0,
        "Holm_calculations": 0,
    }


def test_decision_records_the_contract_state(built):
    d = built["decision"]
    assert d["action_id"] == m.ACTION_ID
    assert d["m3i2_contract_lock_executed"] is True
    assert d["m3i2_contract_status"] == "PROSPECTIVELY_LOCKED_NO_DATA"
    assert d["m3i2_retrieval_started"] is False
    assert d["m3i2_data_gate_executed"] is False
    assert d["m3i2_block_admitted"] is False
    assert d["m3i2_incremental_evaluation_authorized"] is False
    assert d["m3i2_modeling_started"] is False
    assert d["m4_authorized"] is False and d["m4_started"] is False
    assert d["data_collection_started"] is False
    assert d["result_code"] == (
        "M3I2_PROSPECTIVE_CONTRACT_LOCK_READY_FOR_INDEPENDENT_REAUDIT")
    assert d["correction_of_prior_head"] == (
        "6351381283c14b248b4349b1d5ca240dde5cfe3f")
    assert d["correction_widened_scope"] is False
    assert d["correction_closes_audit_blockers"] == [
        "observation_year_selection_rule_inside_the_selected_wdi_vintage",
        "historical_archive_vintage_semantic_and_currency_unit_compatibility",
    ]


def test_next_pointer_is_informational_only(built):
    d = built["decision"]
    assert d["next_research_action_id"] == (
        "stage128-m3i2-official-source-evidence-capture")
    assert d["next_action_authorized"] is False
    assert d["next_research_action_pointer_is_not_authorization"] is True


def test_build_is_deterministic():
    first = m.build_package(ROOT, write=False)["artifact_texts"]
    second = m.build_package(ROOT, write=False)["artifact_texts"]
    assert first == second


def test_on_disk_package_matches_a_fresh_build(built):
    for rel, text in built["artifact_texts"].items():
        path = ROOT / rel
        assert path.is_file(), rel
        assert path.read_text(encoding="utf-8") == text, rel


def test_metadata_hashes_cover_every_artifact(built):
    meta = built["metadata"]
    covered = set(meta["package_artifacts_sha256"])
    assert covered == set(REQUIRED_ARTIFACTS) - {m.METADATA_REL}
    assert meta["protected_baseline_commit"] == m.BASELINE_COMMIT
    assert meta["protected_file_count"] == len(meta["protected_files_sha256"])


def test_source_registry_csv_has_the_locked_columns(built):
    text = built["artifact_texts"][m.SOURCE_REGISTRY_REL]
    header, *rows = text.strip().splitlines()
    assert header == ",".join(m.SOURCE_REGISTRY_COLUMNS)
    assert len(rows) == 3
    assert all("not_authorized" in row for row in rows)


def test_readme_states_the_boundary(built):
    text = built["artifact_texts"][m.README_REL]
    for line in ("CONTRACT LOCK ONLY", "NO DATA RETRIEVAL", "NO DATA GATE",
                 "NO MODELING", "NO M3I-vs-M2", "NO M4",
                 "FINAL TEST LOCKED", "NO MERGE AUTHORIZATION"):
        assert line in text
    assert m.BASELINE_COMMIT in text


def test_artifacts_are_valid_json_and_sorted(built):
    for rel, text in built["artifact_texts"].items():
        if not rel.endswith(".json"):
            continue
        payload = json.loads(text)
        assert text == json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
