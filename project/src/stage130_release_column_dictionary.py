"""Stage130 — the complete release dictionary for all 115 released columns.

The committed Stage125 artifacts split the job of documenting a column in two,
and neither half is a release dictionary:

  * ``part3c_column_role_map_stage125.csv`` names all 115 released columns and
    gives each exactly one role — but no definition, no unit, no formula and no
    source.
  * ``data_dictionary_stage125.csv`` carries prose, type, unit and provenance —
    but it is a Part 1 dictionary written over the *upstream source panel* and
    its candidate blocks, so it reaches only 25 of the 115 released columns and
    describes 13 variables that were never released at all.

A public dataset needs one row per released column, complete. This module is
that row set. It is a DOCUMENTATION join, not a new measurement: every field it
publishes is transcribed from a committed contract, dictionary, decision record,
QC record or frozen generator, and every row names the exact repository path and
the field or code section the fact came from.

Fail-closed, in this order:

  * the column set is taken from the role map and must match it EXACTLY — a
    column present here but absent there, or the reverse, aborts;
  * every column must carry a fact entry; an undefined column aborts and is
    reported by name rather than filled with a plausible-sounding sentence;
  * every field of every row must be non-empty, and ``definition_status``,
    ``model_eligibility`` and ``source_provider_or_author_derived`` must come
    from their closed vocabularies;
  * every ``authoritative_source_path`` must exist in the repository.

What this module never does: read a data row, recompute a value, fit anything,
or open the Final Test surface. It reads the role map's column names and the
committed documentation. Nothing else.

Usage::

    python project/src/stage130_release_column_dictionary.py --write
"""
from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Authoritative column set. Whatever this file lists, in this order, is what
#: the release contains — this module never invents a column or drops one.
ROLE_MAP_REL = "project/stage125/part3c_column_role_map_stage125.csv"
#: Where the generated dictionary is committed, and shipped from.
OUTPUT_REL = ("project/stage130/dataset_release_candidate/release_payload/"
              "RELEASE_COLUMN_DICTIONARY.csv")
#: The bundle path it occupies inside the release archive.
BUNDLE_REL = "RELEASE_COLUMN_DICTIONARY.csv"

EXPECTED_COLUMN_COUNT = 115

FIELDNAMES = (
    "column_name",
    "definition",
    "data_type",
    "unit",
    "column_role",
    "model_eligibility",
    "source_block",
    "source_provider_or_author_derived",
    "temporal_reference",
    "missing_value_semantics",
    "derivation_or_formula",
    "authoritative_source_path",
    "authoritative_source_field_or_section",
    "definition_status",
    "limitations",
)


class ColumnDictionaryError(RuntimeError):
    """Raised when a column cannot be fully defined from committed sources."""


# --------------------------------------------------------------------------- #
# Authoritative sources
# --------------------------------------------------------------------------- #

S121_DICT = ("project/raw_handoff/financial_distress_programmer_handoff_"
             "stage121(1)/data_dictionary_stage121.csv")
S122_TARGET_DEF = "project/stage122/target_definition_stage122.csv"
S122_SRC = "project/src/stage122.py"
S123_SRC = "project/src/stage123.py"
S124_GATE_B_SRC = "project/src/stage124_gate_b_execution.py"
S125_DICT = "project/stage125/data_dictionary_stage125.csv"
S125_CONTRACT = ("project/stage125/"
                 "part3c_leakage_safe_dataset_contract_stage125.json")
S125_PART3C_SRC = ("project/src/"
                   "stage125_part3c_leakage_safe_dataset_finalization.py")

#: Every path a row is allowed to cite. Keeping the set closed means a typo in
#: an anchor fails the build rather than pointing a reuser at nothing.
AUTHORITATIVE_SOURCES = frozenset({
    S121_DICT, S122_TARGET_DEF, S122_SRC, S123_SRC, S124_GATE_B_SRC,
    S125_DICT, S125_CONTRACT, S125_PART3C_SRC,
})

# --------------------------------------------------------------------------- #
# Closed vocabularies
# --------------------------------------------------------------------------- #

#: How a fact reached this table. Not a quality grade — a provenance class.
DEFINITION_STATUS = frozenset({
    "committed_dictionary",
    "committed_contract",
    "committed_target_definition",
    "frozen_generator_code",
})

PROVENANCE_CLASS = frozenset({
    "provider_CODAL_statement_line_item_compiled_by_the_authors",
    "provider_CODAL_label_compiled_by_the_authors",
    "author_compiled_ratio_over_CODAL_line_items",
    "author_derived_from_committed_project_rules",
    "author_assigned_key_or_label",
})

#: Derived from the role map, one value per role. Part 3C approved NOTHING for
#: model entry -- every released column carries enters_model_feature_matrix
#: = false -- so no value here reads as an approval.
MODEL_ELIGIBILITY_BY_ROLE = {
    "predictor_candidate":
        "candidate_inventory_only_pending_part4_sap_not_approved_for_model_entry",
    "forbidden_from_model_matrix":
        "forbidden_never_enters_the_model_feature_matrix_target_derived",
    "target": "outcome_variable_never_a_predictor_feature",
    "identifier": "identifier_not_a_predictor_feature",
    "provenance_audit": "audit_only_never_a_predictor_feature",
    "sample_eligibility_audit": "audit_only_never_a_predictor_feature",
    "timing_eligibility_audit": "audit_only_never_a_predictor_feature",
    "timing_assumption":
        "methodological_timing_field_never_a_predictor_feature",
}

# --------------------------------------------------------------------------- #
# Shared clauses
# --------------------------------------------------------------------------- #

NO_IMPUTATION = (
    "Missing is left missing. The Stage125 contract lists "
    "no_imputation_or_scaling among its explicit non-claims, so no released "
    "value was filled, scaled or reconstructed.")

S121_PRESERVE = (
    "Preserved as supplied by the upstream panel; the Stage121 dictionary "
    "records missing_policy = 'Preserve as supplied; no imputation was applied "
    "in this handoff.' " + NO_IMPUTATION)

S121_TRAIN_ONLY = (
    "Material missingness remains. The Stage121 dictionary records "
    "missing_policy = 'Do not fill automatically; handle only inside the "
    "modeling pipeline with a documented train-only strategy.' " + NO_IMPUTATION)

POPULATED_BY_CONSTRUCTION = (
    "Not applicable: the value is populated on every released row because the "
    "generator assigns it unconditionally. Nothing was imputed to make that "
    "true.")

COPIED_FROM_PREDICTOR = (
    "Copied byte-for-byte from the joined Stage123 predictor row for fiscal "
    "year t; the Part 3C builder copies this column and never recomputes it.")

COPIED_FROM_PAIR = (
    "Copied byte-for-byte from the frozen Gate B pair row; the Part 3C builder "
    "copies this column and never recomputes it.")

MONETARY_LIMITATION = (
    "Nominal monetary level. The study period covers years of high inflation "
    "in Iran and no deflation, currency conversion or purchasing-power "
    "adjustment was applied; the per-row monetary scale is recorded in the "
    "`unit` column. Cross-year comparison of nominal levels is the reuser's "
    "responsibility.")

RATIO_LIMITATION = (
    "Supplied as a stored ratio in the upstream panel and reconciled by QC as "
    "arithmetic agreement with its stored components, not re-audited against "
    "the original filing. QC coverage differs by check (1,273-1,312 of 1,331 "
    "upstream rows evaluable); zero mismatches among evaluable rows says "
    "nothing about rows that could not be evaluated.")

TARGET_DERIVED_LIMITATION = (
    "Target-derived. Using it as a predictor produces a model that predicts "
    "the outcome from the outcome. The role map marks it "
    "forbidden_from_model_matrix; check the role map, never a name pattern.")

AUDIT_LIMITATION = (
    "Eligibility bookkeeping, not a measurement of the company. Eligibility is "
    "recorded per dimension and the counts are NOT additive: one row may fail "
    "more than one rule.")

TIMING_LIMITATION = (
    "Rests on the fixed four-Jalali-month regulatory-lag assumption, not on an "
    "observed filing date. Row-level publication timestamps were never "
    "collected and the contract records is_observed_publication_timestamp = "
    "false; any point-in-time claim built on this field is a claim about the "
    "proxy.")

GATE_B_AUDIT_LIMITATION = (
    "Gate B pair-level eligibility bookkeeping for one of the four locked "
    "sample designs. It describes sample membership, not company condition, "
    "and it is never a predictor feature.")


def _fact(
    definition: str,
    data_type: str,
    unit: str,
    source_block: str,
    provenance: str,
    temporal_reference: str,
    missing_value_semantics: str,
    derivation: str,
    source_path: str,
    source_anchor: str,
    definition_status: str,
    limitations: str,
) -> dict[str, str]:
    return {
        "definition": definition,
        "data_type": data_type,
        "unit": unit,
        "source_block": source_block,
        "source_provider_or_author_derived": provenance,
        "temporal_reference": temporal_reference,
        "missing_value_semantics": missing_value_semantics,
        "derivation_or_formula": derivation,
        "authoritative_source_path": source_path,
        "authoritative_source_field_or_section": source_anchor,
        "definition_status": definition_status,
        "limitations": limitations,
    }


COLUMN_FACTS: dict[str, dict[str, str]] = {}


def _add(name: str, **kwargs: str) -> None:
    if name in COLUMN_FACTS:
        raise ColumnDictionaryError(f"duplicate fact entry for {name!r}")
    COLUMN_FACTS[name] = _fact(**kwargs)


# --------------------------------------------------------------------------- #
# Identifiers (role map: identifier, 10 columns)
# --------------------------------------------------------------------------- #

_add(
    "ticker",
    definition="Canonical Tehran Stock Exchange / Fara Bourse ticker symbol of "
               "the company the company-year pair belongs to.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_assigned_key_or_label",
    temporal_reference="point_in_time_company_year",
    missing_value_semantics="Never missing: the pair surface is keyed on it "
                            "and the Part 3C builder aborts on a ticker "
                            "mismatch between the pair, the predictor row and "
                            "the target row.",
    derivation="Copied from the frozen Gate B pair row; the Part 3C builder "
               "cross-checks it against both joined Stage123 rows and raises "
               "QCFail on any disagreement.",
    source_path=S125_DICT,
    source_anchor="row variable_name=ticker (block M1, role identifier)",
    definition_status="committed_dictionary",
    limitations="Ticker identity only. It is not a company legal identifier "
                "and it is not stable against a market-wide re-listing.",
)

_add(
    "company_name",
    definition="Company name attached to the predictor company-year row.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="point_in_time_company_year",
    missing_value_semantics="Recorded as a provenance gap where absent: the "
                            "Stage125 dictionary records 7 missing rows in the "
                            "upstream panel, not imputed. " + NO_IMPUTATION,
    derivation=COPIED_FROM_PAIR,
    source_path=S125_DICT,
    source_anchor="row variable_name=company_name (block M1, provenance_status "
                  "in_use_partial_gap)",
    definition_status="committed_dictionary",
    limitations="A display label, not a key. Join on `ticker` or on the row "
                "keys, never on the name.",
)

_add(
    "industry",
    definition="Industry classification label of the predictor company-year "
               "row, as recorded in the upstream panel.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="point_in_time_company_year",
    missing_value_semantics="Recorded as a provenance gap where absent: the "
                            "Stage125 dictionary records 29 missing rows in "
                            "the upstream panel, not imputed. " + NO_IMPUTATION,
    derivation=COPIED_FROM_PREDICTOR,
    source_path=S125_DICT,
    source_anchor="row variable_name=industry (block M1, provenance_status "
                  "in_use_partial_gap)",
    definition_status="committed_dictionary",
    limitations="Free-text sector label; the Stage121 dictionary defers any "
                "encoding decision to modeling. Financial-industry firms are "
                "excluded from the main sample by an explicit, "
                "version-controlled company mapping, not by matching this "
                "text.",
)

_add(
    "fiscal_year_t",
    definition="Jalali fiscal year of the PREDICTOR row of the pair — the year "
               "whose statement supplies every predictor value.",
    data_type="integer",
    unit="jalali_year",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_assigned_key_or_label",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Never missing: the Part 3C builder parses it as "
                            "an integer and aborts if it is unparseable or "
                            "disagrees with the joined predictor row.",
    derivation="Stage123 pair construction sets fiscal_year_t = the predictor "
               "row's Jalali fiscal_year.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: rows.append({'fiscal_year_t': r.year})",
    definition_status="frozen_generator_code",
    limitations="Jalali years 1392-1402 only. No Gregorian span is claimed for "
                "the sample.",
)

_add(
    "target_year",
    definition="Jalali fiscal year of the OUTCOME row of the pair; always "
               "fiscal_year_t + 1.",
    data_type="integer",
    unit="jalali_year",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_assigned_key_or_label",
    temporal_reference="target_fiscal_year_t_plus_1",
    missing_value_semantics="Never missing: the Part 3C builder aborts unless "
                            "target_year == fiscal_year_t + 1 for every row.",
    derivation="Stage123 pair construction sets target_year = fiscal_year_t + "
               "1; Part 3C re-asserts the relation per row.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: rows.append({'target_year': r.year + 1})",
    definition_status="frozen_generator_code",
    limitations="One-year-ahead horizon only. The panel supports no other "
                "prediction horizon without rebuilding the pair surface.",
)

_add(
    "predictor_row_key_t",
    definition="Stage123 row key of the predictor company-year row, used to "
               "join the pair to the frozen panel.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_assigned_key_or_label",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Never missing: Part 3C requires exactly one "
                            "Stage123 match per key and aborts on a missing or "
                            "duplicated join.",
    derivation="predictor_row_key_t == stage123.row_key; exactly one match. "
               "The row key itself is ticker + fiscal_year.",
    source_path=S125_CONTRACT,
    source_anchor="predictor_join_rule",
    definition_status="committed_contract",
    limitations="An internal project key. It is not a provider identifier and "
                "resolves to nothing outside this dataset.",
)

_add(
    "target_row_key_t_plus_1",
    definition="Stage123 row key of the outcome company-year row (t+1), used "
               "for the identity and fiscal-year-end audit of the pair.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_assigned_key_or_label",
    temporal_reference="target_fiscal_year_t_plus_1",
    missing_value_semantics="Never missing: Part 3C requires exactly one "
                            "Stage123 match per key and aborts on a missing or "
                            "duplicated join.",
    derivation="target_row_key_t_plus_1 == stage123.row_key; exactly one "
               "match; identity/FYE audit only.",
    source_path=S125_CONTRACT,
    source_anchor="target_join_rule",
    definition_status="committed_contract",
    limitations="Used for the identity audit and the outcome copy. It is not a "
                "predictor and must not be treated as one.",
)

_add(
    "row_key_predictor",
    definition="The predictor row's own Stage123 row key as read back from the "
               "joined panel row — the join's answer, held next to the join's "
               "question in predictor_row_key_t.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_assigned_key_or_label",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="row['row_key_predictor'] = pred['row_key'], where pred is the "
               "single Stage123 row matched by predictor_row_key_t.",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: row['row_key_predictor'] = "
                  "pred['row_key']",
    definition_status="frozen_generator_code",
    limitations="Deliberately redundant with predictor_row_key_t so a broken "
                "join is visible in the released file rather than only in the "
                "builder. Redundancy is the point; it carries no extra "
                "information.",
)

_add(
    "sample_design",
    definition="Which of the four locked sample designs the file belongs to: "
               "main_rule_a_primary, main_rule_b_listing_robustness, "
               "expanded_rule_a_company_scope_robustness or "
               "expanded_rule_b_combined_robustness.",
    data_type="categorical",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="design_constant_within_a_released_file",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="row['sample_design'] = design, set once per released file from "
               "the four locked design names.",
    source_path=S125_CONTRACT,
    source_anchor="four_locked_sample_designs",
    definition_status="committed_contract",
    limitations="Constant within each released file. Only "
                "main_rule_a_primary is the primary surface; the other three "
                "are prespecified robustness surfaces and a result quoted from "
                "one of them is a robustness result.",
)

_add(
    "unit",
    definition="Unit of the raw financial-statement amounts recorded for the "
               "predictor row.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="An empty unit makes the row fail "
                            "eligible_source_quality, so it is recorded rather "
                            "than filled. " + NO_IMPUTATION,
    derivation=COPIED_FROM_PREDICTOR,
    source_path=S121_DICT,
    source_anchor="row column_name=unit (role metadata)",
    definition_status="committed_dictionary",
    limitations="Declares the monetary scale of the level columns. It is not a "
                "currency conversion and it carries no deflator.",
)

# --------------------------------------------------------------------------- #
# Predictor candidates — financial levels (13 of 31)
# --------------------------------------------------------------------------- #

_LEVELS = (
    ("total_assets", "Total assets of the company at fiscal year t.",
     "Total assets", "in_use_frozen"),
    ("total_liabilities", "Total liabilities of the company at fiscal year t.",
     "Total liabilities", "in_use_frozen"),
    ("equity", "Total equity of the company at fiscal year t.",
     "Total equity", "in_use_frozen"),
    ("registered_capital",
     "Registered capital of the company at fiscal year t.",
     "Registered capital", "in_use_frozen"),
    ("accumulated_loss",
     "Accumulated loss / retained deficit at fiscal year t, as standardized "
     "by the upstream panel.",
     "Accumulated loss / retained deficit as standardized", "in_use_frozen"),
    ("current_assets", "Current assets of the company at fiscal year t.",
     "Current assets", None),
    ("current_liabilities",
     "Current liabilities of the company at fiscal year t.",
     "Current liabilities", None),
    ("revenue_period_adjusted",
     "Revenue for fiscal year t, adjusted to the canonical annual period where "
     "the source period required it.",
     "Revenue adjusted to the canonical period where required", None),
    ("operating_profit_period_adjusted",
     "Operating profit for fiscal year t, adjusted to the canonical annual "
     "period.",
     "Operating profit adjusted to the canonical period", None),
    ("net_income_period_adjusted",
     "Net income for fiscal year t, adjusted to the canonical annual period.",
     "Net income adjusted to the canonical period", "in_use_frozen"),
    ("financial_expense_period_adjusted",
     "Financial expense for fiscal year t, adjusted to the canonical annual "
     "period. Expenses may carry a negative sign under the source's own "
     "convention.",
     "Financial expense adjusted to the canonical period; expenses may be "
     "negative per source sign convention", None),
)

for _name, _definition, _s121_text, _s125_status in _LEVELS:
    _add(
        _name,
        definition=_definition,
        data_type="numeric",
        unit="million_IRR",
        source_block="M1_upstream_source_panel",
        provenance="provider_CODAL_statement_line_item_compiled_by_the_authors",
        temporal_reference="predictor_fiscal_year_t",
        missing_value_semantics=S121_PRESERVE,
        derivation="Statement line item compiled by the authors from the "
                   "annual separate/parent-company CODAL filing. "
                   + COPIED_FROM_PREDICTOR,
        source_path=S121_DICT,
        source_anchor=f"row column_name={_name} :: definition = "
                      f"{_s121_text!r}",
        definition_status="committed_dictionary",
        limitations=MONETARY_LIMITATION,
    )

# Two level columns carry material, documented missingness of their own.
_add(
    "gross_profit_period_adjusted",
    definition="Gross profit for fiscal year t, adjusted to the canonical "
               "annual period.",
    data_type="numeric",
    unit="million_IRR",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_statement_line_item_compiled_by_the_authors",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_TRAIN_ONLY,
    derivation="Statement line item compiled by the authors from the annual "
               "separate/parent-company CODAL filing. " + COPIED_FROM_PREDICTOR,
    source_path=S121_DICT,
    source_anchor="row column_name=gross_profit_period_adjusted (role "
                  "raw_feature_optional) :: 'Gross profit adjusted to the "
                  "canonical period; material missingness remains'",
    definition_status="committed_dictionary",
    limitations=MONETARY_LIMITATION + " Material missingness remains, and "
                "gross_profit_resolution_status records why per row.",
)

_add(
    "operating_cash_flow_period_adjusted",
    definition="Operating cash flow for fiscal year t, adjusted to the "
               "canonical annual period.",
    data_type="numeric",
    unit="million_IRR",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_statement_line_item_compiled_by_the_authors",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_TRAIN_ONLY,
    derivation="Statement line item compiled by the authors from the annual "
               "separate/parent-company CODAL filing. " + COPIED_FROM_PREDICTOR,
    source_path=S121_DICT,
    source_anchor="row column_name=operating_cash_flow_period_adjusted (role "
                  "raw_feature_optional) :: 'Operating cash flow adjusted to "
                  "the canonical period; unresolved values remain outside the "
                  "training-candidate subset'",
    definition_status="committed_dictionary",
    limitations=MONETARY_LIMITATION + " It is also an input to the "
                "fd_ocf_high_leverage target criterion, so its missingness "
                "propagates into the three-valued outcome. "
                "ocf_resolution_status records why a value is absent.",
)

# --------------------------------------------------------------------------- #
# Predictor candidates — ratios (18 of 31)
# --------------------------------------------------------------------------- #

_RATIOS = (
    ("leverage_ratio", "Leverage: total liabilities relative to total assets, "
     "at fiscal year t.", "total_liabilities / total_assets"),
    ("current_ratio", "Liquidity: current assets relative to current "
     "liabilities, at fiscal year t.", "current_assets / current_liabilities"),
    ("roa_period_adjusted", "Return on assets for fiscal year t, on the "
     "period-adjusted net income.",
     "net_income_period_adjusted / total_assets"),
    ("roe_period_adjusted", "Return on equity for fiscal year t, on the "
     "period-adjusted net income.", "net_income_period_adjusted / equity"),
    ("equity_ratio", "Equity relative to total assets at fiscal year t.",
     "equity / total_assets"),
    ("ocf_to_assets_period_adjusted", "Period-adjusted operating cash flow "
     "relative to total assets at fiscal year t.",
     "operating_cash_flow_period_adjusted / total_assets"),
    ("financial_expense_to_assets_period_adjusted", "Period-adjusted financial "
     "expense relative to total assets at fiscal year t.",
     "financial_expense_period_adjusted / total_assets"),
    ("profit_margin_period_adjusted", "Period-adjusted net income relative to "
     "revenue at fiscal year t.",
     "net_income_period_adjusted / revenue_period_adjusted"),
    ("operating_margin_period_adjusted", "Period-adjusted operating profit "
     "relative to revenue at fiscal year t.",
     "operating_profit_period_adjusted / revenue_period_adjusted"),
    ("gross_margin_period_adjusted", "Period-adjusted gross profit relative to "
     "revenue at fiscal year t.",
     "gross_profit_period_adjusted / revenue_period_adjusted"),
    ("net_margin_period_adjusted", "Period-adjusted net income relative to "
     "revenue at fiscal year t.",
     "net_income_period_adjusted / revenue_period_adjusted"),
    ("financial_expense_to_revenue_period_adjusted", "Period-adjusted "
     "financial expense relative to revenue at fiscal year t.",
     "financial_expense_period_adjusted / revenue_period_adjusted"),
    ("asset_turnover_period_adjusted", "Period-adjusted revenue relative to "
     "total assets at fiscal year t.",
     "revenue_period_adjusted / total_assets"),
    ("revenue_growth_period_adjusted", "Period-adjusted year-over-year revenue "
     "growth into fiscal year t.",
     "period-adjusted year-over-year revenue growth"),
    ("net_income_growth_period_adjusted", "Period-adjusted year-over-year "
     "net-income growth into fiscal year t.",
     "period-adjusted year-over-year net-income growth"),
    ("sales_growth_period_adjusted", "Period-adjusted sales/revenue growth "
     "into fiscal year t, retained under the source's own alias.",
     "alias retained from source for period-adjusted sales/revenue growth"),
    ("accumulated_loss_to_capital_ratio", "Accumulated loss relative to "
     "registered capital at fiscal year t.",
     "accumulated_loss / registered_capital"),
    ("debt_to_equity", "Total liabilities relative to equity at fiscal year t.",
     "total_liabilities / equity"),
)

_RATIO_TRAIN_ONLY = {
    "ocf_to_assets_period_adjusted", "gross_margin_period_adjusted",
}

for _name, _definition, _formula in _RATIOS:
    _limits = RATIO_LIMITATION
    if _name == "accumulated_loss_to_capital_ratio":
        _limits = (RATIO_LIMITATION + " It is also the quantity the "
                   "fd_accumulated_loss target criterion thresholds at 0.5, so "
                   "it sits very close to the outcome; the Part 4 plan removes "
                   "it from the primary feature set on target-proximity "
                   "grounds.")
    elif _name == "leverage_ratio":
        _limits = (RATIO_LIMITATION + " It is also an input to the "
                   "fd_ocf_high_leverage target criterion (threshold 0.70), so "
                   "it sits close to the outcome; the Part 4 plan removes it "
                   "from the primary feature set on target-proximity grounds.")
    _add(
        _name,
        definition=_definition,
        data_type="numeric",
        unit="ratio",
        source_block="M1_upstream_source_panel",
        provenance="author_compiled_ratio_over_CODAL_line_items",
        temporal_reference="predictor_fiscal_year_t",
        missing_value_semantics=(S121_TRAIN_ONLY
                                 if _name in _RATIO_TRAIN_ONLY
                                 else S121_PRESERVE),
        derivation=_formula + ". Supplied as a stored ratio in the upstream "
                   "panel and " + COPIED_FROM_PREDICTOR[0].lower()
                   + COPIED_FROM_PREDICTOR[1:],
        source_path=S121_DICT,
        source_anchor=f"row column_name={_name} :: definition = {_formula!r}",
        definition_status="committed_dictionary",
        limitations=_limits,
    )

# --------------------------------------------------------------------------- #
# Outcomes (role map: target, 3 columns)
# --------------------------------------------------------------------------- #

_TARGETS = (
    ("FD_target_main_t_plus_1", "FD_target_main",
     "The PRIMARY outcome: the composite operational financial-distress "
     "indicator evaluated on the t+1 company-year.",
     "modified three-valued OR with non-blocking unavailable direct "
     "Article-141 evidence. 1 if any criterion definitely 1; 0 if all "
     "evaluable quantitative criteria definitely 0; missing otherwise. NOT an "
     "Article-141 target.",
     "This is an operational composite, NOT an Article-141 legal insolvency "
     "determination and not a bankruptcy filing. Direct Article-141 evidence "
     "was unavailable for every row, so that criterion is missing throughout "
     "and the composite does not rest on it. The primary surface carries 80 "
     "positives against 932 negatives (about 7.9%), and the positive class "
     "gets sparser in later years."),
    ("FD_target_article141_only_t_plus_1", "FD_target_article141_only",
     "ROBUSTNESS outcome: the stricter Article-141-oriented definition "
     "evaluated on the t+1 company-year.",
     "modified three-valued OR(fd_article141_direct, fd_accumulated_loss); "
     "with 141 absent reduces to accumulated_loss >= 50% of registered "
     "capital. Robustness only.",
     "Robustness only, never the headline outcome. Because direct Article-141 "
     "evidence is missing for every row, this reduces in practice to the "
     "accumulated-loss criterion alone and must not be reported as an "
     "Article-141 determination."),
    ("FD_target_persistent_loss_robustness_t_plus_1",
     "FD_target_persistent_loss_robustness",
     "ROBUSTNESS outcome: the composite widened with a two-consecutive-year "
     "net-loss criterion, evaluated on the t+1 company-year.",
     "modified three-valued OR(FD_target_main, two-consecutive-year net "
     "loss). Robustness only.",
     "Robustness only, never the headline outcome. It is a broader definition "
     "than FD_target_main and its positives are not interchangeable with the "
     "primary outcome's."),
)

for _name, _base, _definition, _rule, _limits in _TARGETS:
    _add(
        _name,
        definition=_definition,
        data_type="three_valued_1_0_missing",
        unit="not_applicable",
        source_block="M1_derived_stage122_target_construction",
        provenance="author_derived_from_committed_project_rules",
        temporal_reference="target_fiscal_year_t_plus_1",
        missing_value_semantics="Three-valued. A company-year whose evidence "
                                "did not permit a determination is recorded as "
                                "unknown and is NEVER converted to a healthy "
                                "zero. " + NO_IMPUTATION,
        derivation=f"{_base} evaluated on the t+1 row: {_rule} Targets are "
                   "copied byte-for-byte from the frozen Gate B pair files and "
                   "never recomputed from accounting values.",
        source_path=S122_TARGET_DEF,
        source_anchor=f"row criterion={_base} :: rule",
        definition_status="committed_target_definition",
        limitations=_limits,
    )

# --------------------------------------------------------------------------- #
# Forbidden from the model matrix (role map: 14 columns)
# --------------------------------------------------------------------------- #

_CRITERIA = (
    ("fd_article141_direct",
     "Direct Article-141 evidence criterion at fiscal year t.",
     "1 if direct Article-141 inclusion verified from a controlled source; 0 "
     "if non-inclusion verified; else missing. Stage121 has NO such source -> "
     "missing for ALL rows.",
     TARGET_DERIVED_LIMITATION + " It is also missing for EVERY row: no "
     "controlled Article-141 source existed. It therefore carries no "
     "information at all, and exists so the composite's non-blocking treatment "
     "of it stays inspectable."),
    ("fd_accumulated_loss",
     "Accumulated-loss criterion at fiscal year t: accumulated loss at or "
     "above half of registered capital.",
     "1 if accumulated_loss/registered_capital >= 0.5; 0 if < 0.5; missing if "
     "registered_capital <=0/missing OR accumulated_loss missing.",
     TARGET_DERIVED_LIMITATION),
    ("fd_negative_equity",
     "Negative-equity criterion at fiscal year t.",
     "1 if equity<0; 0 if equity>=0; missing if equity missing.",
     TARGET_DERIVED_LIMITATION),
    ("fd_ocf_high_leverage",
     "Combined criterion at fiscal year t: negative operating cash flow "
     "together with high leverage.",
     "1 if OCF<0 AND liabilities/assets>0.70; definite 0 if OCF>=0 OR "
     "leverage<=0.70; missing otherwise (three-valued).",
     TARGET_DERIVED_LIMITATION),
)

for _name, _definition, _rule, _limits in _CRITERIA:
    _add(
        _name,
        definition=_definition,
        data_type="three_valued_1_0_missing",
        unit="not_applicable",
        source_block="M1_derived_stage122_target_construction",
        provenance="author_derived_from_committed_project_rules",
        temporal_reference="predictor_fiscal_year_t",
        missing_value_semantics="Three-valued: an indeterminate criterion is "
                                "recorded as missing and never collapsed to 0. "
                                + NO_IMPUTATION,
        derivation=_rule,
        source_path=S122_TARGET_DEF,
        source_anchor=f"row criterion={_name} :: rule",
        definition_status="committed_target_definition",
        limitations=_limits,
    )

_YEAR_T_TARGETS = (
    ("FD_target_main",
     "The composite operational financial-distress indicator evaluated on the "
     "PREDICTOR year t (not the outcome year).",
     "composite operational financial distress target",
     "modified three-valued OR with non-blocking unavailable direct "
     "Article-141 evidence. 1 if any criterion definitely 1; 0 if all "
     "evaluable quantitative criteria definitely 0; missing otherwise. NOT an "
     "Article-141 target."),
    ("FD_target_article141_only",
     "The stricter Article-141-oriented robustness target evaluated on the "
     "PREDICTOR year t.",
     "stricter Article-141 robustness definition",
     "modified three-valued OR(fd_article141_direct, fd_accumulated_loss); "
     "with 141 absent reduces to accumulated_loss>=50%. Robustness only."),
    ("FD_target_persistent_loss_robustness",
     "The persistent-loss robustness target evaluated on the PREDICTOR year t.",
     "robustness target (composite + 2-year persistent loss)",
     "modified three-valued OR(FD_target_main, two-consecutive-year net "
     "loss). Robustness only."),
)

for _name, _definition, _label, _rule in _YEAR_T_TARGETS:
    _add(
        _name,
        definition=_definition,
        data_type="three_valued_1_0_missing",
        unit="not_applicable",
        source_block="M1_derived_stage122_target_construction",
        provenance="author_derived_from_committed_project_rules",
        temporal_reference="predictor_fiscal_year_t",
        missing_value_semantics="Three-valued: an unknown outcome stays "
                                "unknown and is never converted to a healthy "
                                "zero. " + NO_IMPUTATION,
        derivation=f"{_label}: {_rule}",
        source_path=S122_TARGET_DEF,
        source_anchor=f"row criterion={_name} :: label, rule",
        definition_status="committed_target_definition",
        limitations=TARGET_DERIVED_LIMITATION + " It is the SAME target "
                    "construction as the t+1 outcome, one year earlier. Using "
                    "it as a feature is a lagged-target design and must be "
                    "declared as one; the role map forbids it by default.",
    )

_add(
    "loss_dummy",
    definition="Binary flag at fiscal year t: the source's loss condition is "
               "met.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="1 when loss condition is met under source rule; otherwise 0.",
    source_path=S121_DICT,
    source_anchor="row column_name=loss_dummy (role binary_feature)",
    definition_status="committed_dictionary",
    limitations=TARGET_DERIVED_LIMITATION + " It is a component of the "
                "persistent-loss robustness target.",
)

_add(
    "equity_negative_dummy",
    definition="Binary flag at fiscal year t: equity is negative.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="1 when equity is negative; otherwise 0.",
    source_path=S121_DICT,
    source_anchor="row column_name=equity_negative_dummy (role binary_feature)",
    definition_status="committed_dictionary",
    limitations=TARGET_DERIVED_LIMITATION + " It restates the "
                "fd_negative_equity criterion, which is a component of "
                "FD_target_main.",
)

_add(
    "distressed_target_reviewed",
    definition="The reviewed/canonical financial-distress target carried "
               "forward from the upstream panel for the predictor year t.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Reviewed/canonical financial-distress target; 1=distressed, "
               "0=not distressed.",
    source_path=S121_DICT,
    source_anchor="row column_name=distressed_target_reviewed (role target)",
    definition_status="committed_dictionary",
    limitations=TARGET_DERIVED_LIMITATION + " It is the upstream reviewed "
                "target, retained for audit. The study's own outcome is "
                "FD_target_main_t_plus_1, not this column.",
)

_add(
    "target_status_reviewed",
    definition="Status label describing how the upstream reviewed target was "
               "constructed for the predictor year t.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Status of reviewed target construction, carried forward "
               "unchanged from the upstream panel.",
    source_path=S121_DICT,
    source_anchor="row column_name=target_status_reviewed (role "
                  "target_metadata)",
    definition_status="committed_dictionary",
    limitations=TARGET_DERIVED_LIMITATION + " Target metadata: it describes "
                "the outcome's construction and therefore leaks it.",
)

_add(
    "distressed_flag_source_reviewed",
    definition="Documented source or rule behind the upstream reviewed "
               "distress flag for the predictor year t.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Documented source/rule for reviewed target, carried forward "
               "unchanged from the upstream panel.",
    source_path=S121_DICT,
    source_anchor="row column_name=distressed_flag_source_reviewed (role "
                  "target_metadata)",
    definition_status="committed_dictionary",
    limitations=TARGET_DERIVED_LIMITATION + " Target metadata: it describes "
                "the outcome's construction and therefore leaks it.",
)

_add(
    "positive_target_reasons",
    definition="For a definite-positive predictor year t, the list of ALL "
               "criteria that were active, pipe-separated.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage122_target_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Empty string for every row whose FD_target_main "
                            "is not definitely 1. Empty means 'not a "
                            "definite positive', never 'unknown reason'.",
    derivation="For every row with FD_target_main == 1, joins the active "
               "criteria among accumulated_loss, negative_equity, "
               "ocf_high_leverage and article141_direct with ' | '.",
    source_path=S122_SRC,
    source_anchor="positive_target_reasons()",
    definition_status="frozen_generator_code",
    limitations=TARGET_DERIVED_LIMITATION + " It states exactly why a row is "
                "positive, so it is the most direct target leak in the file.",
)

_add(
    "target_missing_reason",
    definition="For a predictor year t whose target is missing, the exact "
               "inputs that blocked the determination.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage122_target_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Empty string for every row whose FD_target_main "
                            "is determinate. Empty means 'the target was "
                            "determinable', never 'unknown'.",
    derivation="For every row with a missing FD_target_main, emits the tokens "
               "naming the unavailable inputs (for example "
               "missing_accumulated_loss_and_capital, "
               "missing_or_invalid_registered_capital).",
    source_path=S122_SRC,
    source_anchor="target_missing_reason()",
    definition_status="frozen_generator_code",
    limitations=TARGET_DERIVED_LIMITATION + " It is the audit trail for the "
                "three-valued outcome: 28 upstream rows are preserved as "
                "unknown rather than converted to a healthy zero.",
)

# --------------------------------------------------------------------------- #
# Provenance audit (role map: 5 columns)
# --------------------------------------------------------------------------- #

_add(
    "source_file",
    definition="Filename of the source statement workbook the predictor row "
               "was extracted from. Filename only — no directory component, no "
               "local path and no file content.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_assigned_key_or_label",
    temporal_reference="retrieval",
    missing_value_semantics="Absent for 28 of the 1,331 upstream panel rows — "
                            "a documented provenance gap, not imputed and not "
                            "reclassified. An empty value also fails "
                            "eligible_source_quality. " + NO_IMPUTATION,
    derivation=COPIED_FROM_PREDICTOR,
    source_path=S125_DICT,
    source_anchor="row variable_name=source_file (source_id "
                  "src_m1_uploaded_xls, provenance_status in_use_partial_gap)",
    definition_status="committed_dictionary",
    limitations="Provenance here is file-level, not row-level. The workbook "
                "itself is NOT redistributed in this release, so the filename "
                "resolves to nothing a reuser holds.",
)

_add(
    "source_url",
    definition="Public CODAL report URL for the predictor row, where one was "
               "recorded.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="publication",
    missing_value_semantics="Missing for 1,316 of the 1,331 upstream panel "
                            "rows. Recorded as a provenance gap only; it was "
                            "never used to change eligibility. " + NO_IMPUTATION,
    derivation=COPIED_FROM_PREDICTOR,
    source_path=S125_DICT,
    source_anchor="row variable_name=source_url (source_id src_m1_codal_fs, "
                  "provenance_status in_use_major_gap)",
    definition_status="committed_dictionary",
    limitations="A partial convenience pointer, not a provenance guarantee. It "
                "is populated for only a small minority of rows and a URL may "
                "not resolve at a later date.",
)

_TARGET_IDENTITY = (
    ("target_row_ticker",
     "Ticker read back from the joined t+1 outcome row, for the pair identity "
     "audit.",
     "row['target_row_ticker'] = tgt['ticker']"),
    ("target_row_fiscal_year",
     "Jalali fiscal year read back from the joined t+1 outcome row, for the "
     "pair identity audit.",
     "row['target_row_fiscal_year'] = str(tgt['fiscal_year'])"),
    ("target_row_key_matched",
     "Stage123 row key read back from the joined t+1 outcome row, for the pair "
     "identity audit.",
     "row['target_row_key_matched'] = tgt['row_key']"),
)

for _name, _definition, _code in _TARGET_IDENTITY:
    _add(
        _name,
        definition=_definition,
        data_type="string",
        unit="not_applicable",
        source_block="M1_derived_stage125_part3c",
        provenance="author_assigned_key_or_label",
        temporal_reference="target_fiscal_year_t_plus_1",
        missing_value_semantics=POPULATED_BY_CONSTRUCTION,
        derivation=_code + ", where tgt is the single Stage123 row matched by "
                   "target_row_key_t_plus_1.",
        source_path=S125_PART3C_SRC,
        source_anchor=f"build_design_rows() :: {_code}",
        definition_status="frozen_generator_code",
        limitations="Identity audit only. It proves the pair joined to the "
                    "company-year it claims to; it says nothing about the "
                    "company and is never a predictor feature.",
    )

# --------------------------------------------------------------------------- #
# Sample eligibility audit — predictor-year dimensions (22 columns)
# --------------------------------------------------------------------------- #

_add(
    "eligible_listing",
    definition="Predictor-year listing eligibility under the Stage123 "
               "baseline: 1 unless the row is marked pre-listing.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="0 where ocf_resolution_status == "
               "'pre_listing_missing_excluded', else 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_listing']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " This is the Stage123 baseline listing "
                "rule; the Gate B listing rules that actually define the four "
                "locked designs are separate and are recorded in the "
                "pair-level columns. 19 pre-listing rows are excluded on this "
                "ground.",
)

_add(
    "eligible_statement_type",
    definition="Predictor-year statement-scope eligibility: whether the row's "
               "statement is a valid separate/parent-company statement.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Set to 1 for every row in Stage123: the data owner confirmed "
               "every numeric value comes from the annual separate/parent "
               "company statements, so the prior consolidated / unknown labels "
               "were file-title artifacts and the scope was corrected to "
               "annual_separate_company_user_confirmed.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_statement_type'] = 1",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " Constant at 1 after the Stage123 scope "
                "correction, so it carries no discriminating information in "
                "the released files. The 95 rows excluded on "
                "consolidated-or-unresolved-scope grounds were excluded under "
                "the earlier Stage122 rule, which is retained as history.",
)

_add(
    "eligible_annual_period",
    definition="Predictor-year period eligibility: whether the statement "
               "covers a standard 12-month annual period.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="0 where non_12_month_period_flag == '1', else 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_annual_period']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " 6 non-12-month-period rows are excluded "
                "on this ground.",
)

_add(
    "eligible_source_quality",
    definition="Predictor-year source-traceability eligibility: whether both a "
               "source file and a unit were recorded.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="0 where source_file is blank OR unit is blank, else 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_source_quality']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " It tests whether a filename and a unit "
                "were recorded, not whether the filing was independently "
                "re-verified.",
)

_add(
    "eligible_accounting_quality",
    definition="Predictor-year accounting-quality eligibility: whether the "
               "balance-sheet identity reconciles within tolerance.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="rel = |total_assets - (total_liabilities + equity)| / "
               "max(|total_assets|, 1); 0 where rel is present and > 0.005, "
               "else 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_accounting_quality']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " A row whose components are missing "
                "cannot produce a residual and is therefore NOT marked "
                "ineligible by this rule — 1 here can mean 'reconciles' or "
                "'was not evaluable'. The identity check was evaluable on "
                "1,312 of 1,331 upstream rows.",
)

_add(
    "eligible_company_main",
    definition="Whether the company is inside the MAIN company scope, which "
               "excludes financial/investment firms and operating holdings.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="company_constant",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Read from the explicit, version-controlled nine-company "
               "COMPANY_SAMPLE_MAPPING; defaults to 1 for any ticker not "
               "listed there. No keyword re-guessing.",
    source_path=S123_SRC,
    source_anchor="COMPANY_SAMPLE_MAPPING; rebuild_eligibility() :: "
                  "el['eligible_company_main']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " Company-constant, so it varies across "
                "companies and never within one. 43 rows are excluded from the "
                "main scope on financial-industry grounds.",
)

_add(
    "eligible_company_expanded",
    definition="Whether the company is inside the EXPANDED company scope, "
               "which readmits operating holdings but still excludes "
               "financial/investment firms.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="company_constant",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Read from the explicit, version-controlled nine-company "
               "COMPANY_SAMPLE_MAPPING; defaults to 1 for any ticker not "
               "listed there. No keyword re-guessing.",
    source_path=S123_SRC,
    source_anchor="COMPANY_SAMPLE_MAPPING; rebuild_eligibility() :: "
                  "el['eligible_company_expanded']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " It defines the prespecified "
                "company-scope robustness surfaces, not the primary sample.",
)

_add(
    "eligible_target",
    definition="Whether the predictor row's OWN FD_target_main is determinate "
               "(0 or 1) rather than unknown.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="0 where the row's own FD_target_main is missing, else 1. "
               "Recorded as a column only; Stage123 deliberately does NOT make "
               "it a predictor-eligibility condition.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['eligible_target'] "
                  "(# column only, NOT predictor)",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " It describes the year-t target, not the "
                "t+1 outcome the pair predicts; valid_target_t_plus_1 is the "
                "column that governs pair admission.",
)

_add(
    "predictor_eligible_main",
    definition="Stage123 predictor-year eligibility under the MAIN company "
               "scope: every base quality dimension passes and the company is "
               "in the main scope.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="AND(eligible_listing, eligible_statement_type, "
               "eligible_annual_period, eligible_source_quality, "
               "eligible_accounting_quality) AND eligible_company_main == 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['predictor_eligible_main']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " This is the Stage123 BASELINE rollup. "
                "The four locked designs are defined by the Gate B rollups in "
                "the pair-level columns, which additionally apply a listing "
                "rule; the two can disagree and both are published.",
)

_add(
    "predictor_eligible_expanded",
    definition="Stage123 predictor-year eligibility under the EXPANDED company "
               "scope.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="AND(eligible_listing, eligible_statement_type, "
               "eligible_annual_period, eligible_source_quality, "
               "eligible_accounting_quality) AND eligible_company_expanded "
               "== 1.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['predictor_eligible_expanded']",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " Stage123 baseline rollup for the "
                "expanded scope; see predictor_eligible_main.",
)

_add(
    "model_exclusion_reason_main",
    definition="Pipe-separated reasons the predictor year failed MAIN-scope "
               "Stage123 eligibility.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Empty string when the row is eligible. Empty "
                            "means 'no exclusion reason', never 'unknown'.",
    derivation="Joins with ' | ' the tokens pre_listing, non_12_month_period, "
               "source_not_traceable, accounting_quality_issue for each failed "
               "dimension, plus financial_or_holding_company where "
               "eligible_company_main == 0.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: "
                  "el['model_exclusion_reason_main'], reason_map",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " A row may carry more than one reason, so "
                "reason counts do not sum to the excluded-row count.",
)

_add(
    "model_exclusion_reason_expanded",
    definition="Pipe-separated reasons the predictor year failed "
               "EXPANDED-scope Stage123 eligibility.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics="Empty string when the row is eligible. Empty "
                            "means 'no exclusion reason', never 'unknown'.",
    derivation="Joins with ' | ' the tokens pre_listing, non_12_month_period, "
               "source_not_traceable, accounting_quality_issue for each failed "
               "dimension, plus financial_company where "
               "eligible_company_expanded == 0.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: "
                  "el['model_exclusion_reason_expanded'], reason_map",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " A row may carry more than one reason, so "
                "reason counts do not sum to the excluded-row count.",
)

_add(
    "usable_for_model_flag",
    definition="The upstream source workbook's own quality filter, used there "
               "to build the training-candidates sheet.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Existing source flag used to create the training_candidates "
               "sheet, carried forward unchanged.",
    source_path=S121_DICT,
    source_anchor="row column_name=usable_for_model_flag (role "
                  "quality_filter)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " It is the UPSTREAM flag and is NOT the "
                "study's eligibility rule. The project's eligibility lives in "
                "the predictor_eligible_* and pair_final_eligible_* columns; "
                "this one is retained for audit only.",
)

_add(
    "data_quality_flag",
    definition="The upstream source workbook's own data-quality flag for the "
               "predictor row.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Existing data-quality flag from the source workbook, carried "
               "forward unchanged.",
    source_path=S121_DICT,
    source_anchor="row column_name=data_quality_flag (role quality_metadata)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " An upstream label, retained for audit. "
                "It does not drive any eligibility decision in this study.",
)

_add(
    "audit_status_clean",
    definition="Standardized audit-status classification of the predictor "
               "row's filing.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="publication",
    missing_value_semantics="316 rows carry audit_status_unknown — a recorded "
                            "coverage gap, not an imputed value. "
                            + NO_IMPUTATION,
    derivation=COPIED_FROM_PREDICTOR,
    source_path=S125_DICT,
    source_anchor="row variable_name=audit_status_clean (source_id "
                  "src_m1_codal_audit, provenance_status in_use_partial_gap)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " It is a status label, not the structured "
                "audit-opinion variable: the M4 structured audit block was "
                "never admitted to the study and no M4 field is in this "
                "release.",
)

_add(
    "statement_scope_status",
    definition="Canonical separate / parent-company / consolidated scope "
               "status of the predictor row's statement, after the Stage123 "
               "correction.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="The Stage123 canonical scope: rows previously labelled "
               "possible_consolidated_statement or statement_scope_unknown "
               "were corrected to annual_separate_company_user_confirmed on "
               "the data owner's direct confirmation; all other rows keep "
               "their original label.",
    source_path=S123_SRC,
    source_anchor="rebuild_eligibility() :: el['statement_scope_canonical']; "
                  "CORRECTED_SCOPE",
    definition_status="frozen_generator_code",
    limitations=AUDIT_LIMITATION + " The correction rests on the data owner's "
                "confirmation, not on a re-reading of each filing. The prior "
                "labels are retained in the Stage123 immutable audit log, not "
                "in this release.",
)

_add(
    "statement_scope_display_fa",
    definition="Persian display label for the corrected statement scope: "
               "'annual separate financial statements of the company'.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_eligibility",
    provenance="author_assigned_key_or_label",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Set to the single constant DISPLAY_LABEL_FA for every row.",
    source_path=S123_SRC,
    source_anchor="DISPLAY_LABEL_FA; allrows['statement_scope_display_fa'] = "
                  "DISPLAY_LABEL_FA",
    definition_status="frozen_generator_code",
    limitations="A constant display string, identical on every row. It carries "
                "no per-row information and exists only so the corrected scope "
                "is legible in Persian.",
)

_add(
    "non_12_month_period_flag",
    definition="Flag: the predictor row's source period is not a standard "
               "12-month period.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="1 when the source period is not a standard 12-month period.",
    source_path=S121_DICT,
    source_anchor="row column_name=non_12_month_period_flag (role "
                  "quality_filter)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " It is the input to "
                "eligible_annual_period; 6 rows are excluded on this ground.",
)

_add(
    "exclusion_flag",
    definition="The upstream source workbook's standardized exclusion flag for "
               "the predictor row.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Standardized source exclusion flag; the Stage121 dictionary "
               "records that it is NOT automatically applied in all_rows.",
    source_path=S121_DICT,
    source_anchor="row column_name=exclusion_flag (role quality_filter)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " An upstream flag that this study does "
                "not act on. Do not read it as the study's exclusion decision; "
                "that lives in the pair_final_eligible_* columns.",
)

_add(
    "manual_review_required_clean",
    definition="Standardized flag: the upstream panel marked the predictor row "
               "as requiring manual review.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Standardized manual-review flag, carried forward unchanged.",
    source_path=S121_DICT,
    source_anchor="row column_name=manual_review_required_clean (role "
                  "quality_filter)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " It records that a review was flagged, "
                "not that one was performed or what it concluded.",
)

_add(
    "ocf_resolution_status",
    definition="Why the predictor row's operating cash flow is present or "
               "absent: observed, pre-listing excluded, source unavailable in "
               "CODAL, or deferred unresolved.",
    data_type="categorical",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Observed, pre-listing excluded, source unavailable in Codal, "
               "or deferred unresolved.",
    source_path=S121_DICT,
    source_anchor="row column_name=ocf_resolution_status (role "
                  "missingness_metadata)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " Its pre_listing_missing_excluded value "
                "is also the controlled marker that drives eligible_listing, "
                "so it is doing two jobs at once.",
)

_add(
    "gross_profit_resolution_status",
    definition="Why the predictor row's gross profit is present or absent: "
               "observed, pre-listing excluded, or deferred unresolved.",
    data_type="categorical",
    unit="not_applicable",
    source_block="M1_upstream_source_panel",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=S121_PRESERVE,
    derivation="Observed, pre-listing excluded, or deferred unresolved.",
    source_path=S121_DICT,
    source_anchor="row column_name=gross_profit_resolution_status (role "
                  "missingness_metadata)",
    definition_status="committed_dictionary",
    limitations=AUDIT_LIMITATION + " It explains gross-profit missingness; it "
                "does not remove it.",
)

# --------------------------------------------------------------------------- #
# Sample eligibility audit — Gate B pair-level dimensions (15 columns)
# --------------------------------------------------------------------------- #

_add(
    "valid_target_t_plus_1",
    definition="Whether the t+1 outcome row exists and its FD_target_main is "
               "determinate — the condition that makes the pair usable at all.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="target_fiscal_year_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="0 if the t+1 row's FD_target_main is missing, else 1.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: valid_t1",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " It is the pair-level expression "
                "of the three-valued outcome: an unknown t+1 target removes "
                "the pair rather than being converted to a healthy zero.",
)

_add(
    "predictor_eligible_main_t",
    definition="The predictor row's MAIN-scope Stage123 eligibility, carried "
               "onto the pair.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Copied onto the pair from the predictor row's "
               "predictor_eligible_main.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: 'predictor_eligible_main_t': "
                  "int(r.pe_main)",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " It is the Stage123 baseline, not "
                "the Gate B rollup that defines the locked designs.",
)

_add(
    "predictor_eligible_expanded_t",
    definition="The predictor row's EXPANDED-scope Stage123 eligibility, "
               "carried onto the pair.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_fiscal_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Copied onto the pair from the predictor row's "
               "predictor_eligible_expanded.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: 'predictor_eligible_expanded_t': "
                  "int(r.pe_exp)",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " It is the Stage123 baseline, not "
                "the Gate B rollup that defines the locked designs.",
)

_add(
    "pair_final_eligible_main",
    definition="Stage123 BASELINE pair eligibility under the main company "
               "scope, before the Gate B listing rules.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="1 if predictor_eligible_main_t == 1 AND "
               "valid_target_t_plus_1 == 1, else 0.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: pem",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " HISTORICAL baseline. The four "
                "locked designs are governed by the "
                "pair_final_eligible_*_gate_b_* columns, not by this one.",
)

_add(
    "pair_final_eligible_expanded",
    definition="Stage123 BASELINE pair eligibility under the expanded company "
               "scope, before the Gate B listing rules.",
    data_type="boolean_0_1",
    unit="binary_0_1",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="1 if predictor_eligible_expanded_t == 1 AND "
               "valid_target_t_plus_1 == 1, else 0.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: pex",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " HISTORICAL baseline; see "
                "pair_final_eligible_main.",
)

_add(
    "pair_exclusion_reason_main",
    definition="Why the pair failed the Stage123 BASELINE main-scope rule.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics="Empty string when the pair is eligible. Empty "
                            "means 'no exclusion reason', never 'unknown'.",
    derivation="Joins with ' | ' the tokens "
               "'predictor_not_eligible:<model_exclusion_reason_main>' and "
               "'target_t+1_missing', each emitted only when the "
               "corresponding condition failed.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: reason(r.pe_main, r.rsn_main)",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " HISTORICAL baseline reason "
                "string; the Gate B reason columns govern the locked designs.",
)

_add(
    "pair_exclusion_reason_expanded",
    definition="Why the pair failed the Stage123 BASELINE expanded-scope rule.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage123_pair_construction",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics="Empty string when the pair is eligible. Empty "
                            "means 'no exclusion reason', never 'unknown'.",
    derivation="Joins with ' | ' the tokens "
               "'predictor_not_eligible:<model_exclusion_reason_expanded>' and "
               "'target_t+1_missing', each emitted only when the "
               "corresponding condition failed.",
    source_path=S123_SRC,
    source_anchor="build_pairs123() :: reason(r.pe_exp, r.rsn_exp)",
    definition_status="frozen_generator_code",
    limitations=GATE_B_AUDIT_LIMITATION + " HISTORICAL baseline reason "
                "string; the Gate B reason columns govern the locked designs.",
)

#: (column, scope, rule, design, human label)
_GATE_B_DESIGNS = (
    ("main", "gate_b_primary", "rule_a", "main_rule_a_primary",
     "first_observed_trading_date <= fiscal_year_end",
     "the PRIMARY design"),
    ("main", "gate_b_robustness", "rule_b", "main_rule_b_listing_robustness",
     "first_observed_trading_date <= fiscal_year_start",
     "the listing-rule robustness design"),
    ("expanded", "gate_b_primary", "rule_a",
     "expanded_rule_a_company_scope_robustness",
     "first_observed_trading_date <= fiscal_year_end",
     "the company-scope robustness design"),
    ("expanded", "gate_b_robustness", "rule_b",
     "expanded_rule_b_combined_robustness",
     "first_observed_trading_date <= fiscal_year_start",
     "the combined robustness design"),
)

for _scope, _suffix, _rule, _design, _rule_expr, _design_label in _GATE_B_DESIGNS:
    _flag = f"pair_final_eligible_{_scope}_{_suffix}"
    _reason = f"pair_exclusion_reason_{_scope}_{_suffix}"
    _add(
        _flag,
        definition=f"Gate B pair eligibility for {_design_label} "
                   f"({_design}): the {_scope} company scope combined with "
                   f"listing {_rule}.",
        data_type="boolean_0_1",
        unit="binary_0_1",
        source_block="M1_derived_stage124_gate_b",
        provenance="author_derived_from_committed_project_rules",
        temporal_reference="pair_t_to_t_plus_1",
        missing_value_semantics=POPULATED_BY_CONSTRUCTION,
        derivation=f"Pair-level rollup of the Gate B predictor eligibility "
                   f"predictor_eligible_{_scope}_{_suffix}, which is 1 only "
                   f"when eligible_company_{_scope} == 1 AND every base flag "
                   f"(eligible_statement_type, eligible_annual_period, "
                   f"eligible_source_quality, eligible_accounting_quality) == "
                   f"1 AND the listing rule {_rule} holds "
                   f"({_rule_expr}).",
        source_path=S124_GATE_B_SRC,
        source_anchor=f"SAMPLE_DESIGNS['{_design}']; PREDICTOR_COLS; "
                      f"OTHER_BASE_FLAGS; build_company_year()",
        definition_status="frozen_generator_code",
        limitations=GATE_B_AUDIT_LIMITATION + f" It defines membership of "
                    f"{_design} only. The listing dates come from the official "
                    f"TSE API as first_observed_trading_date; an unresolved "
                    f"listing date is treated as not eligible, not as "
                    f"eligible-by-default.",
    )
    _add(
        _reason,
        definition=f"Why the pair failed Gate B eligibility for {_design}.",
        data_type="string",
        unit="not_applicable",
        source_block="M1_derived_stage124_gate_b",
        provenance="author_derived_from_committed_project_rules",
        temporal_reference="pair_t_to_t_plus_1",
        missing_value_semantics="Empty string when the pair is eligible. Empty "
                                "means 'no exclusion reason', never 'unknown'.",
        derivation=f"Semicolon-joined failure tokens for {_design}: "
                   f"company_scope_{_scope} where the company scope excludes "
                   f"the firm, the name of each failed base flag, and "
                   f"'listing_' + the listing exclusion reason or status.",
        source_path=S124_GATE_B_SRC,
        source_anchor=f"PAIR_REASON_COLS['{_design}']; build_company_year() "
                      f":: reasons",
        definition_status="frozen_generator_code",
        limitations=GATE_B_AUDIT_LIMITATION + " A pair may carry more than "
                    "one token, so token counts do not sum to the excluded "
                    "pair count.",
    )

# --------------------------------------------------------------------------- #
# Timing assumption (role map: 10 columns)
# --------------------------------------------------------------------------- #

_add(
    "fiscal_year_end_t_jalali",
    definition="Fiscal year end of the PREDICTOR year t, as a Jalali date.",
    data_type="date_jalali_iso",
    unit="jalali_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="predictor_period_end",
    missing_value_semantics="Never missing in a released row: Part 3C parses "
                            "the predictor row's fiscal_year_end as a Jalali "
                            "date and aborts if it cannot. The upstream panel "
                            "records 4 rows with a missing fiscal-year-end as "
                            "a provenance gap.",
    derivation="jalali_to_iso(parse_jalali_date(pred['fiscal_year_end'])).",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: "
                  "row['fiscal_year_end_t_jalali'] = jalali_to_iso(fye_t)",
    definition_status="frozen_generator_code",
    limitations="Jalali is the primary calendar for this panel. This is the "
                "statement period end, not a filing or publication date.",
)

_add(
    "fiscal_year_end_t_gregorian",
    definition="The same predictor-year fiscal year end, converted to the "
               "Gregorian calendar.",
    data_type="date_gregorian_iso",
    unit="gregorian_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="predictor_period_end",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="gregorian_iso(fye_t) — a pure calendar conversion of "
               "fiscal_year_end_t_jalali. No new date information.",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: "
                  "row['fiscal_year_end_t_gregorian'] = gregorian_iso(fye_t)",
    definition_status="frozen_generator_code",
    limitations="A conversion, not an observation. The sample is defined over "
                "Jalali years 1392-1402 and no Gregorian span is claimed.",
)

_add(
    "assumed_available_at_regulatory_jalali",
    definition="The ASSUMED date on which the fiscal-year-t statement is "
               "treated as available: fiscal year end plus four Jalali "
               "calendar months.",
    data_type="date_jalali_iso",
    unit="jalali_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="assumed_availability_of_predictor_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="add_jalali_calendar_months(fiscal_year_end_t, 4), clamping the "
               "day to the last valid day of the target Jalali month.",
    source_path=S125_CONTRACT,
    source_anchor="assumed_availability_field_name; active_lag_months; "
                  "availability_method",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " The field name says 'assumed' because "
                "it is: the builder refuses to write this value into any "
                "observed-publication field name, and the contract lists "
                "no_observed_PublishDateTime_claim among its non-claims.",
)

_add(
    "assumed_available_at_regulatory_gregorian",
    definition="The same assumed availability date, converted to the Gregorian "
               "calendar.",
    data_type="date_gregorian_iso",
    unit="gregorian_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="assumed_availability_of_predictor_year_t",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="assumed.togregorian().isoformat() — a pure calendar conversion "
               "of assumed_available_at_regulatory_jalali.",
    source_path=S125_PART3C_SRC,
    source_anchor="compute_assumed_available_at_regulatory() :: "
                  "'assumed_available_at_regulatory_gregorian'",
    definition_status="frozen_generator_code",
    limitations=TIMING_LIMITATION + " Converting an assumption to another "
                "calendar does not make it an observation.",
)

_add(
    "regulatory_lag_months",
    definition="The size of the availability lag in Jalali calendar months. "
               "Constant at 4 across the release.",
    data_type="integer",
    unit="jalali_calendar_months",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="design_constant_within_the_release",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Constant 4, guarded: the builder raises unless the value is "
               "exactly the approved integer 4.",
    source_path=S125_CONTRACT,
    source_anchor="active_lag_months; four_month_regulatory_lag_locked",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " The historical six-month lag is "
                "superseded for the active path but retained as provenance; "
                "the contract records six_month_lag_superseded = true and "
                "historical_six_month_decision_retained = true.",
)

_add(
    "availability_method",
    definition="How the availability date was produced. Constant at "
               "'fixed_regulatory_lag'.",
    data_type="categorical",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="design_constant_within_the_release",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Constant 'fixed_regulatory_lag'.",
    source_path=S125_CONTRACT,
    source_anchor="availability_method",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " It names a method, not a data source. "
                "No per-company or per-ticker timing rule was authorized: the "
                "contract lists no_ticker_specific_timing_authorization among "
                "its non-claims.",
)

_add(
    "availability_date_semantics",
    definition="What the availability date means. Constant at "
               "'assumed_regulatory_deadline_not_observed_publication_"
               "timestamp'.",
    data_type="categorical",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="design_constant_within_the_release",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Constant "
               "'assumed_regulatory_deadline_not_observed_publication_"
               "timestamp'.",
    source_path=S125_CONTRACT,
    source_anchor="availability_date_semantics",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " This column exists so the caveat "
                "travels with the data rather than only with the README.",
)

_add(
    "is_observed_publication_timestamp",
    definition="Whether the availability date is an observed publication "
               "timestamp. Constant FALSE across the release.",
    data_type="boolean_true_false",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="design_constant_within_the_release",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="Constant 'false'. Row-level publication timestamps were never "
               "collected: the contract records "
               "row_level_publish_datetime_collection_authorized = false and "
               "row_level_real_available_at_assignment_authorized = false.",
    source_path=S125_CONTRACT,
    source_anchor="is_observed_publication_timestamp",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " It is false on every row. A future "
                "dataset that collected real filing timestamps would be a "
                "different dataset, not a corrected version of this one.",
)

_add(
    "target_fiscal_year_end_t_plus_1_jalali",
    definition="Fiscal year end of the OUTCOME year t+1, as a Jalali date — "
               "the cutoff the availability date is compared against.",
    data_type="date_jalali_iso",
    unit="jalali_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="provider_CODAL_label_compiled_by_the_authors",
    temporal_reference="target_period_end",
    missing_value_semantics="Never missing in a released row: Part 3C parses "
                            "the outcome row's fiscal_year_end as a Jalali "
                            "date and aborts if it cannot.",
    derivation="jalali_to_iso(parse_jalali_date(tgt['fiscal_year_end'])).",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: "
                  "row['target_fiscal_year_end_t_plus_1_jalali']",
    definition_status="frozen_generator_code",
    limitations="It is a period end, not an outcome-observation date. The "
                "outcome itself is the frozen target copied from the Gate B "
                "pair.",
)

_add(
    "target_fiscal_year_end_t_plus_1_gregorian",
    definition="The same outcome-year fiscal year end, converted to the "
               "Gregorian calendar.",
    data_type="date_gregorian_iso",
    unit="gregorian_date_YYYY_MM_DD",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="target_period_end",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="gregorian_iso(fye_t1) — a pure calendar conversion of "
               "target_fiscal_year_end_t_plus_1_jalali.",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: "
                  "row['target_fiscal_year_end_t_plus_1_gregorian']",
    definition_status="frozen_generator_code",
    limitations="A conversion, not an observation. The timing comparison "
                "itself is performed in the Jalali calendar.",
)

# --------------------------------------------------------------------------- #
# Timing eligibility audit (role map: 5 columns)
# --------------------------------------------------------------------------- #

_add(
    "assumed_before_target_fiscal_year_end",
    definition="Whether the assumed availability date falls strictly before "
               "the outcome year's fiscal year end — the leakage-safe timing "
               "condition.",
    data_type="boolean_true_false",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="assumed_available_at_regulatory < "
               "target_fiscal_year_end_t_plus_1, evaluated in the Jalali "
               "calendar.",
    source_path=S125_CONTRACT,
    source_anchor="analysis_ready_rule",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " It is TRUE on every row of the four "
                "analysis-ready files by construction, and can be FALSE only "
                "in the audited_pairs_* surfaces.",
)

_add(
    "timing_relation_violation",
    definition="The complement of assumed_before_target_fiscal_year_end: the "
               "predictor would not have been available before the outcome "
               "year ended.",
    data_type="boolean_true_false",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="NOT assumed_before_target_fiscal_year_end. The builder "
               "cross-checks the two and aborts if they ever agree.",
    source_path=S125_PART3C_SRC,
    source_anchor="build_design_rows() :: timing_violation = not relation_ok; "
                  "split_analysis_ready()",
    definition_status="frozen_generator_code",
    limitations=TIMING_LIMITATION + " The contract expects exactly one "
                "violating pair per design, and it is retained in the audited "
                "surface rather than silently dropped.",
)

_add(
    "timing_eligible_for_analysis",
    definition="Whether the pair may enter the leakage-safe analysis-ready "
               "surface.",
    data_type="boolean_true_false",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="timing_eligible_for_analysis = "
               "assumed_available_at_regulatory < "
               "target_fiscal_year_end_t_plus_1.",
    source_path=S125_CONTRACT,
    source_anchor="timing_eligibility_rule",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " TRUE on every row of the "
                "analysis-ready files. In the audited_pairs_* files it is the "
                "column that marks which rows must NOT be modelled.",
)

_add(
    "timing_eligible_for_model",
    definition="Whether the pair may enter a model under the timing rule. "
               "Identical to timing_eligible_for_analysis.",
    data_type="boolean_true_false",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics=POPULATED_BY_CONSTRUCTION,
    derivation="timing_eligible_for_model = timing_eligible_for_analysis.",
    source_path=S125_CONTRACT,
    source_anchor="timing_eligibility_rule",
    definition_status="committed_contract",
    limitations=TIMING_LIMITATION + " Timing eligibility alone is not model "
                "approval: the contract records feature_selection_authorized = "
                "false and zero features approved before Part 4.",
)

_add(
    "timing_exclusion_reason",
    definition="Why the pair was excluded from the analysis-ready surface on "
               "timing grounds.",
    data_type="string",
    unit="not_applicable",
    source_block="M1_derived_stage125_part3c",
    provenance="author_derived_from_committed_project_rules",
    temporal_reference="pair_t_to_t_plus_1",
    missing_value_semantics="Empty string for every timing-eligible pair; the "
                            "builder aborts if a timing-eligible row carries a "
                            "reason. Empty means 'not excluded on timing "
                            "grounds', never 'unknown'.",
    derivation="Set to the single constant "
               "'regulatory_lag_not_before_target_fiscal_year_end' when "
               "timing_relation_violation is true, otherwise the empty string.",
    source_path=S125_PART3C_SRC,
    source_anchor="TIMING_EXCLUSION_REASON; build_design_rows()",
    definition_status="frozen_generator_code",
    limitations=TIMING_LIMITATION + " It takes exactly one non-empty value in "
                "this release, so it is a marker rather than a taxonomy.",
)


# --------------------------------------------------------------------------- #
# Assembly — fail-closed
# --------------------------------------------------------------------------- #

def read_role_map(root: Path) -> list[dict[str, str]]:
    """The authoritative column set, in the role map's own order."""
    path = root / ROLE_MAP_REL
    if not path.is_file():
        raise ColumnDictionaryError(
            f"the authoritative column-role map is missing: {ROLE_MAP_REL}")
    reader = csv.DictReader(
        io.StringIO(path.read_text(encoding="utf-8-sig"), newline=""))
    rows = list(reader)
    if len(rows) != EXPECTED_COLUMN_COUNT:
        raise ColumnDictionaryError(
            f"{ROLE_MAP_REL} lists {len(rows)} columns, expected "
            f"{EXPECTED_COLUMN_COUNT}")
    names = [row["column_name"] for row in rows]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ColumnDictionaryError(
            f"{ROLE_MAP_REL} repeats columns: {duplicates}")
    return rows


def build_rows(root: Path | str = REPO_ROOT) -> list[dict[str, str]]:
    """One complete row per released column. Fail-closed on any gap."""
    root = Path(root).resolve()
    role_rows = read_role_map(root)

    role_names = [row["column_name"] for row in role_rows]
    undefined = [name for name in role_names if name not in COLUMN_FACTS]
    if undefined:
        raise ColumnDictionaryError(
            "these released columns cannot be fully defined from committed "
            f"sources and the dictionary refuses to invent them: {undefined}")
    orphaned = sorted(set(COLUMN_FACTS) - set(role_names))
    if orphaned:
        raise ColumnDictionaryError(
            "these dictionary entries name columns the authoritative role map "
            f"does not release: {orphaned}")

    rows: list[dict[str, str]] = []
    for role_row in role_rows:
        name = role_row["column_name"]
        role = role_row["role"]
        if role not in MODEL_ELIGIBILITY_BY_ROLE:
            raise ColumnDictionaryError(
                f"{name}: unknown role {role!r} in the role map")
        if (role_row.get("enters_model_feature_matrix") or "").strip() \
                != "false":
            raise ColumnDictionaryError(
                f"{name}: the role map must record "
                "enters_model_feature_matrix = false; Part 3C approved no "
                "column for model entry")
        row = {"column_name": name, "column_role": role,
               "model_eligibility": MODEL_ELIGIBILITY_BY_ROLE[role]}
        row.update(COLUMN_FACTS[name])
        rows.append({field: row[field] for field in FIELDNAMES})

    _validate(root, rows)
    return rows


def _validate(root: Path, rows: list[dict[str, str]]) -> None:
    """Every row complete, every anchor real, every vocabulary respected."""
    if len(rows) != EXPECTED_COLUMN_COUNT:
        raise ColumnDictionaryError(
            f"dictionary has {len(rows)} rows, expected "
            f"{EXPECTED_COLUMN_COUNT}")
    seen: set[str] = set()
    for row in rows:
        name = row["column_name"]
        if name in seen:
            raise ColumnDictionaryError(f"duplicate dictionary row: {name}")
        seen.add(name)
        for field in FIELDNAMES:
            if not (row.get(field) or "").strip():
                raise ColumnDictionaryError(
                    f"{name}: {field} is empty; a release dictionary row must "
                    "be complete or the column must be reported as undefined")
        if row["definition_status"] not in DEFINITION_STATUS:
            raise ColumnDictionaryError(
                f"{name}: definition_status {row['definition_status']!r} is "
                f"not one of {sorted(DEFINITION_STATUS)}")
        if row["source_provider_or_author_derived"] not in PROVENANCE_CLASS:
            raise ColumnDictionaryError(
                f"{name}: source_provider_or_author_derived "
                f"{row['source_provider_or_author_derived']!r} is not one of "
                f"{sorted(PROVENANCE_CLASS)}")
        source = row["authoritative_source_path"]
        if source not in AUTHORITATIVE_SOURCES:
            raise ColumnDictionaryError(
                f"{name}: authoritative_source_path {source!r} is not one of "
                "the declared authoritative sources")
        if not (root / source).is_file():
            raise ColumnDictionaryError(
                f"{name}: authoritative_source_path {source!r} does not exist "
                "in the repository")


def render_csv(rows: list[dict[str, str]]) -> bytes:
    """Deterministic UTF-8 CSV: fixed field order, LF endings, no BOM."""
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(FIELDNAMES),
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def build_csv(root: Path | str = REPO_ROOT) -> bytes:
    return render_csv(build_rows(root))


def coverage(root: Path | str = REPO_ROOT) -> dict[str, object]:
    """Coverage of the release dictionary against the authoritative role map."""
    root = Path(root).resolve()
    rows = build_rows(root)
    role_names = [row["column_name"] for row in read_role_map(root)]
    statuses: dict[str, int] = {}
    for row in rows:
        key = row["definition_status"]
        statuses[key] = statuses.get(key, 0) + 1
    return {
        "released_columns": len(role_names),
        "release_dictionary_rows": len(rows),
        "released_columns_documented": len(rows),
        "released_columns_undocumented": 0,
        "duplicate_rows": 0,
        "column_set_matches_authoritative_role_map": True,
        "rows_by_definition_status": statuses,
        "authoritative_sources": sorted(
            {row["authoritative_source_path"] for row in rows}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help=f"write {OUTPUT_REL}")
    args = parser.parse_args(argv)

    data = build_csv(REPO_ROOT)
    target = REPO_ROOT / OUTPUT_REL
    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"wrote {OUTPUT_REL} ({len(data)} bytes)")
    else:
        current = target.read_bytes() if target.is_file() else None
        state = "up to date" if current == data else "OUT OF DATE"
        print(f"{OUTPUT_REL}: {state}")
    stats = coverage(REPO_ROOT)
    print(f"columns documented: {stats['released_columns_documented']}"
          f"/{stats['released_columns']}")
    for status, count in sorted(stats["rows_by_definition_status"].items()):
        print(f"  {status}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
