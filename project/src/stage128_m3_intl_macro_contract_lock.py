"""Stage128 — ``stage128-m3i2-prospective-contract-lock``.

Create and validate the **prospective** source / definition / statistical
contract lock for the supplementary international-macro block **M3I-2**, with a
**contingent but unresolved** M3I-3 financing component.

What this module is
-------------------
A deterministic, **offline** contract generator and validator. It writes a
metadata-only contract package and fails closed when that package contradicts
the frozen governance boundary.

What this module is **not**
---------------------------
It is not a data pipeline and not an evaluation. It contains:

* no HTTP client, no ``requests``/``urllib``/``curl``, no browser automation,
  no API query;
* no observation reader (no ``pandas``, no ``openpyxl``, no CSV *ingestion*);
* no estimator, no prediction entry point, no resampling, no Holm execution;
* no final-test file or target access;
* no coverage calculation and no Data Gate execution.

The only bytes it reads from the repository are **git blob bytes of protected
upstream paths, hashed as opaque bytes and never decoded**, plus the artifacts
this action itself writes (re-read only by ``--check``).

Relationship to M3-CBI
----------------------
The frozen CBI block (``cpi_inflation``, ``fx_change_official``,
``policy_financing_rate``; source ``src_m3_cbi_macro``; status
``UNRESOLVED_M3_DATA_GATE``) is preserved **exactly**. M3I-2 is a **distinct
supplementary family**: not a substitution, not a correction and not a
continuation of M3-CBI. No M3I block may ever be presented as confirmatory M3.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

ACTION_ID = "stage128-m3i2-prospective-contract-lock"
CONTRACT_ID = "stage128_m3_intl_macro_contract_lock"
CONTRACT_VERSION = "stage128_m3_intl_macro_contract_lock_v1"
CONTRACT_TYPE = "prospective_contract_lock_only_no_data_no_gate_no_modeling"

REPOSITORY = "abtinasg/papermali"

#: Live ``origin/main`` at the time this action was authorized. This action is
#: NOT based on main: PR #73 is still open and unmerged.
MAIN_BRANCH = "main"
MAIN_COMMIT = "35aaf4b70e9341704ee38be6f8cf2e2519c70bb2"

#: The exact PR #73 head this branch is stacked on.
BASELINE_BRANCH = "stage128-m3-macro-data-gate"
BASELINE_COMMIT = "e6db63fb7d105f0d3a39db101c9e364161c367e9"
BASELINE_PR_NUMBER = 73

HEAD_BRANCH = "stage128-m3i2-prospective-contract-lock"
PR_BASE_BRANCH = BASELINE_BRANCH

PREDECESSOR_ACTION_ID = "stage128-m3-macro-data-gate"

#: Informational pointer only. A pointer is never an authorization.
NEXT_ACTION_ID = "stage128-m3i2-official-source-evidence-capture"
NEXT_ACTION_AUTHORIZED = False

PACKAGE_DIR_REL = "project/stage128/m3_intl_macro_contract_lock"

README_REL = (
    f"{PACKAGE_DIR_REL}/README_STAGE128_M3_INTL_MACRO_CONTRACT_LOCK.md")
AUTHORIZATION_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_human_authorization_record.json")
GOVERNANCE_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_governance_boundary.json")
SOURCE_REGISTRY_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_source_registry.csv")
DEFINITION_LOCK_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_definition_lock.json")
PREDICTION_TIME_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_prediction_time_contract.json")
DATA_GATE_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_data_gate_contract.json")
MULTIPLICITY_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_multiplicity_contract.json")
DECISION_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_contract_decision.json")
QC_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_intl_macro_contract_qc_report.json")
METADATA_REL = (
    f"{PACKAGE_DIR_REL}/metadata_and_hashes_stage128_m3_intl_macro_contract"
    "_lock.json")

#: Source files this action introduces. Scanned by the no-execution validators.
IMPLEMENTATION_FILES: tuple[str, ...] = (
    "project/src/stage128_m3_intl_macro_contract_lock.py",
    "project/run_stage128_m3_intl_macro_contract_lock.py",
    "project/tests/test_stage128_m3_intl_macro_contract_lock.py",
)


class M3IntlMacroContractLockError(RuntimeError):
    """Fail-closed error for the M3I contract lock."""


# --------------------------------------------------------------------------- #
# Human authorization (section 11 of the authorizing prompt)
# --------------------------------------------------------------------------- #

#: The EXACT human source utterance, one UTF-8 line, no trailing newline.
#: Verbatim human text; authoritative ONLY in the authorization record.
HUMAN_SOURCE_UTTERANCE = "بریم مرحله بعدی"
HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH = 28
HUMAN_SOURCE_UTTERANCE_SHA256 = (
    "d4acc9698f160ed0f252fd3f2a698b2b17916144d3dc182333cd2892a5d23068")
AUTHORIZATION_LOCAL_TIMESTAMP = "2026-08-02T20:32:00+03:30"
AUTHORIZATION_OCCURRENCE_CONTEXT = (
    "Immediately after M3-INTL-MACRO prospective contract audit v1")

#: The SAME text and hash were used for an earlier, DIFFERENT action (the M3
#: macro data Gate). The hash therefore cannot identify scope on its own; the
#: scope of this occurrence comes from the immediately preceding assistant
#: message, recorded below.
IDENTICAL_TEXT_HASH_USED_FOR_PRIOR_DISTINCT_ACTION = True
SCOPE_IDENTIFIED_BY_HASH_ALONE = False
SCOPE_RESOLUTION_BASIS = (
    "The immediately preceding assistant message identified the next action as "
    "formal prospective lock of M3I-2 only.")

#: DERIVED, NON-VERBATIM restatement of the authorized scope.
NORMALIZED_AUTHORIZATION_SCOPE = (
    "Create and validate the prospective source/definition/statistical "
    "contract lock for the supplementary M3I-2 block, with a contingent but "
    "unresolved M3I-3 financing component.")


def verify_human_authorization() -> dict[str, Any]:
    """Fail closed unless the recorded authorization is byte-exact."""
    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    if len(raw) != HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH:
        raise M3IntlMacroContractLockError(
            f"authorization byte length {len(raw)} != "
            f"{HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != HUMAN_SOURCE_UTTERANCE_SHA256:
        raise M3IntlMacroContractLockError(
            f"authorization sha256 {digest} != {HUMAN_SOURCE_UTTERANCE_SHA256}")
    if HUMAN_SOURCE_UTTERANCE.endswith("\n"):
        raise M3IntlMacroContractLockError(
            "the verbatim authorization must not carry a trailing newline")
    return {
        "human_source_utterance_byte_length": len(raw),
        "human_source_utterance_sha256": digest,
        "normalized_authorization_scope_sha256": hashlib.sha256(
            NORMALIZED_AUTHORIZATION_SCOPE.encode("utf-8")).hexdigest(),
    }


# --------------------------------------------------------------------------- #
# The preserved M3-CBI block (never modified by this action)
# --------------------------------------------------------------------------- #

M3_CBI_BLOCK: tuple[str, ...] = (
    "cpi_inflation",
    "fx_change_official",
    "policy_financing_rate",
)
M3_CBI_SOURCE_ID = "src_m3_cbi_macro"
M3_CBI_STATUS = "UNRESOLVED_M3_DATA_GATE"
M3_CBI_BLOCK_ADMITTED = False

#: Source ids that belong to the frozen CBI/SCI families and may never be
#: reused for an international candidate.
FORBIDDEN_REUSED_SOURCE_IDS: tuple[str, ...] = (
    "src_m3_cbi_macro",
    "src_m3_sci_macro",
)

# --------------------------------------------------------------------------- #
# The supplementary international families
# --------------------------------------------------------------------------- #

M3I2_BLOCK_ID = "M3I-2"
M3I3_BLOCK_ID = "M3I-3"

M3I2_BLOCK: tuple[str, ...] = (
    "intl_cpi_inflation_annual",
    "intl_fx_change_official_annual",
)
M3I3_BLOCK: tuple[str, ...] = M3I2_BLOCK + ("intl_financing_rate",)

M3I2_CANDIDATE_IDS: tuple[str, ...] = (
    "cand_m3i_cpi_inflation_annual",
    "cand_m3i_fx_change_official_annual",
)
M3I3_FINANCING_CANDIDATE_ID = "cand_m3i_financing_rate"

M3I2_CONTRACT_STATUS = "PROSPECTIVELY_LOCKED_NO_DATA"
M3I3_FINANCING_LOCK_STATUS = "UNRESOLVED_METADATA_LOCK"

#: The relationship to M3-CBI, stated once and asserted by QC.
SUPPLEMENTARY_RELATIONSHIP = (
    "distinct_supplementary_family_not_substitution_not_correction_not_"
    "continuation_of_M3_CBI")

# --------------------------------------------------------------------------- #
# Source registry (section 4)
# --------------------------------------------------------------------------- #

SRC_CPI = "src_m3i_wdi_imf_ifs_cpi"
SRC_FX = "src_m3i_wdi_imf_ifs_fx"
SRC_FINANCING = "src_m3i_imf_mfs_interest_rate"

M3I_SOURCE_IDS: tuple[str, ...] = (SRC_CPI, SRC_FX, SRC_FINANCING)

CPI_INDICATOR_CODE = "FP.CPI.TOTL.ZG"
FX_INDICATOR_CODE = "PA.NUS.FCRF"
FINANCING_DATASET_ID = "IMF.STA:MFS_IR"

#: Frozen reference strings. **Never fetched by this action.**
CPI_METADATA_URL = (
    "https://databank.worldbank.org/metadataglossary/"
    "world-development-indicators/series/FP.CPI.TOTL.ZG")
FX_METADATA_URL = (
    "https://databank.worldbank.org/metadataglossary/"
    "world-development-indicators/series/PA.NUS.FCRF")
FINANCING_DATASET_URL = "https://data.imf.org/en/datasets/IMF.STA%3AMFS_IR"

REFERENCE_URLS_FETCHED_IN_THIS_ACTION = False

SOURCE_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "source_id": SRC_CPI,
        "source_family": "official_international_macro_cpi_inflation",
        "distribution_authority": "World Bank",
        "dataset": "World Development Indicators",
        "dataset_id": None,
        "dataset_title": None,
        "upstream_statistical_authority": "International Monetary Fund",
        "upstream_dataset": "International Financial Statistics",
        "indicator_code": CPI_INDICATOR_CODE,
        "official_series_title":
            "Inflation, consumer prices (annual % growth)",
        "exact_series_code": None,
        "exact_series_title": None,
        "frequency": "annual",
        "unit": "percent",
        "source_unit": None,
        "authority_tier": "official_international_statistical_distribution",
        "candidate_selection_status": "RESOLVED_PROSPECTIVE_LOCK",
        "retrieval_status": "not_authorized",
        "admitted": False,
        "official_metadata_reference": CPI_METADATA_URL,
        "reference_fetched_in_this_action": False,
    },
    {
        "source_id": SRC_FX,
        "source_family": "official_international_macro_exchange_rate",
        "distribution_authority": "World Bank",
        "dataset": "World Development Indicators",
        "dataset_id": None,
        "dataset_title": None,
        "upstream_statistical_authority": "International Monetary Fund",
        "upstream_dataset": "International Financial Statistics",
        "indicator_code": FX_INDICATOR_CODE,
        "official_series_title":
            "Official exchange rate (LCU per US$, period average)",
        "exact_series_code": None,
        "exact_series_title": None,
        "frequency": "annual",
        "unit": None,
        "source_unit": "LCU per US dollar",
        "authority_tier": "official_international_statistical_distribution",
        "candidate_selection_status": "RESOLVED_PROSPECTIVE_LOCK",
        "retrieval_status": "not_authorized",
        "admitted": False,
        "official_metadata_reference": FX_METADATA_URL,
        "reference_fetched_in_this_action": False,
    },
    {
        "source_id": SRC_FINANCING,
        "source_family": "official_international_interest_rate",
        "distribution_authority": "International Monetary Fund",
        "dataset": None,
        "dataset_id": FINANCING_DATASET_ID,
        "dataset_title":
            "Monetary and Financial Statistics (MFS), Interest Rate",
        "upstream_statistical_authority": None,
        "upstream_dataset": None,
        "indicator_code": None,
        "official_series_title": None,
        "exact_series_code": None,
        "exact_series_title": None,
        "frequency": None,
        "unit": "percent",
        "source_unit": None,
        "authority_tier": None,
        "candidate_selection_status": M3I3_FINANCING_LOCK_STATUS,
        "retrieval_status": "not_authorized",
        "admitted": False,
        "official_metadata_reference": FINANCING_DATASET_URL,
        "reference_fetched_in_this_action": False,
    },
)

SOURCE_REGISTRY_COLUMNS: tuple[str, ...] = (
    "source_id", "source_family", "distribution_authority", "dataset",
    "dataset_id", "dataset_title", "upstream_statistical_authority",
    "upstream_dataset", "indicator_code", "official_series_title",
    "exact_series_code", "exact_series_title", "frequency", "unit",
    "source_unit", "authority_tier", "candidate_selection_status",
    "retrieval_status", "admitted", "official_metadata_reference",
    "reference_fetched_in_this_action",
)

# --------------------------------------------------------------------------- #
# Exact M3I-2 definition lock (section 5)
# --------------------------------------------------------------------------- #

FX_TRANSFORMATION_FORMULA = "100 * ln(E_y / E_(y-1))"

CPI_FORBIDDEN_ALTERNATIVES: tuple[str, ...] = (
    "FP.CPI.TOTL conversion",
    "monthly inflation",
    "month-on-month inflation",
    "point-to-point inflation",
    "twelve-month moving-average inflation",
    "GDP-deflator inflation",
    "silent SCI substitution",
    "alternative indicator search after coverage inspection",
)

FX_FORBIDDEN_ALTERNATIVES: tuple[str, ...] = (
    "PA.NUS.ATLS",
    "free-market rate",
    "unofficial rate",
    "commercial aggregator",
    "crypto-implied rate",
    "manual Iranian regime splice",
    "mixing Interbank, Banknote and Preferred regimes",
    "alternative transformation after coverage/model inspection",
)

FX_FAIL_CLOSED_CONDITIONS: tuple[str, ...] = (
    "E_y missing -> null",
    "E_(y-1) missing -> null",
    "E_y <= 0 -> null",
    "E_(y-1) <= 0 -> null",
    "years non-consecutive -> null",
    "vintages differ -> null",
)

CPI_CANDIDATE: dict[str, Any] = {
    "candidate_id": "cand_m3i_cpi_inflation_annual",
    "variable_name": "intl_cpi_inflation_annual",
    "block_id": M3I2_BLOCK_ID,
    "block_position": 1,
    "role": "supplementary_candidate",
    "source_id": SRC_CPI,
    "indicator_code": CPI_INDICATOR_CODE,
    "official_series_title": "Inflation, consumer prices (annual % growth)",
    "frequency": "annual",
    "unit": "percent",
    "calendar": "Gregorian calendar year",
    "observation_period_definition": (
        "annual percentage change in consumer prices for the labelled "
        "calendar year"),
    "transformation_formula": "identity",
    "transformation_window": "none",
    "higher_value_interpretation": "higher consumer-price inflation",
    "uniquely_determined": True,
    "admitted": False,
    "retrieval_status": "not_authorized",
    "forbidden_alternatives": list(CPI_FORBIDDEN_ALTERNATIVES),
}

FX_CANDIDATE: dict[str, Any] = {
    "candidate_id": "cand_m3i_fx_change_official_annual",
    "variable_name": "intl_fx_change_official_annual",
    "block_id": M3I2_BLOCK_ID,
    "block_position": 2,
    "role": "supplementary_candidate",
    "source_id": SRC_FX,
    "indicator_code": FX_INDICATOR_CODE,
    "official_series_title":
        "Official exchange rate (LCU per US$, period average)",
    "frequency": "annual",
    "source_unit": "LCU per US dollar",
    "output_unit": "percent_log_change",
    "calendar": "Gregorian calendar year",
    "observation_period_definition": (
        "annual average official exchange rate for the labelled calendar "
        "year"),
    "transformation_formula": FX_TRANSFORMATION_FORMULA,
    "transformation_window":
        "two consecutive annual observations from the same vintage",
    "higher_value_interpretation":
        "local-currency depreciation against the US dollar",
    "uniquely_determined": True,
    "admitted": False,
    "retrieval_status": "not_authorized",
    "fail_closed_transformation_conditions": list(FX_FAIL_CLOSED_CONDITIONS),
    "forbidden_alternatives": list(FX_FORBIDDEN_ALTERNATIVES),
}

# --------------------------------------------------------------------------- #
# Contingent financing contract (section 6)
# --------------------------------------------------------------------------- #

FINANCING_ACCEPTABLE_CONSTRUCT = (
    "An exact official Iran rate representing the cost of bank "
    "lending/financing to the private sector, or an explicitly named "
    "financing/facility rate with the same economic construct.")

FINANCING_FORBIDDEN_PROXIES: tuple[str, ...] = (
    "deposit interest rate",
    "deposit-rate ceiling",
    "real interest rate",
    "interest-rate spread",
    "repo transaction volume",
    "reverse-repo transaction volume",
    "standing-facility transaction amount",
    "any currency-volume series",
    "a differently defined policy rate silently relabelled as financing rate",
    "World Bank FR.INR.LEND admitted without a separate coverage Gate",
)

FINANCING_STOP_RULE = (
    "If no exact IMF series later passes metadata and coverage review, M3I-3 "
    "remains unavailable. M3I-2 is not invalidated. No fourth variable and no "
    "substitute proxy may be introduced.")

#: Every metadata field that must be non-null before financing could ever be
#: considered. All of them are null now, so financing stays inadmissible.
FINANCING_REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
    "exact_series_code",
    "exact_series_title",
    "frequency",
    "calendar",
    "observation_period_definition",
    "publication_or_release_date_field",
    "available_at_definition",
    "revision_or_vintage_policy",
)

FINANCING_CANDIDATE: dict[str, Any] = {
    "candidate_id": M3I3_FINANCING_CANDIDATE_ID,
    "variable_name": "intl_financing_rate",
    "block_id": M3I3_BLOCK_ID,
    "block_position": 3,
    "role": "contingent_supplementary_candidate",
    "source_id": SRC_FINANCING,
    "preferred_dataset_id": FINANCING_DATASET_ID,
    "unit": "percent",
    "exact_series_code": None,
    "exact_series_title": None,
    "frequency": None,
    "calendar": None,
    "observation_period_definition": None,
    "publication_or_release_date_field": None,
    "available_at_definition": None,
    "revision_or_vintage_policy": None,
    "candidate_selection_status": M3I3_FINANCING_LOCK_STATUS,
    "uniquely_determined": False,
    "admitted": False,
    "retrieval_status": "not_authorized",
    "predefined_acceptable_construct": FINANCING_ACCEPTABLE_CONSTRUCT,
    "forbidden_proxies": list(FINANCING_FORBIDDEN_PROXIES),
    "stop_rule": FINANCING_STOP_RULE,
}

# --------------------------------------------------------------------------- #
# Prediction-time and vintage contract (section 7)
# --------------------------------------------------------------------------- #

FROZEN_PREDICTION_CUTOFF_DEFINITION = (
    "The earliest verified available_at timestamp of the predictor-year "
    "financial statement for each t -> t+1 pair.")

MACRO_AVAILABILITY_RULE = "macro_release_available_at < pair_prediction_cutoff"

WDI_AS_OF_RULES: tuple[str, ...] = (
    "Use the latest official WDI Database Archive release strictly before the "
    "pair cutoff.",
    "Use only values contained in that archived release.",
    "available_at is the verified release timestamp of that WDI edition.",
    "A later archive edition is a new vintage and never overwrites an earlier "
    "vintage.",
    "If exact time is unavailable but the release date is verified, "
    "available_at = 00:00:00 UTC on the next calendar day.",
    "Therefore a date-only release on the same calendar date as the cutoff is "
    "excluded.",
    "If no pre-cutoff vintage can be verified, the feature value is null.",
    "No mapping based only on fiscal-year labels is allowed.",
    "Jalali and Gregorian dates must remain separately preserved with "
    "provenance.",
    "No current WDI value may be treated as historically available merely "
    "because its observation year precedes the cutoff.",
)

FX_SAME_VINTAGE_RULE = (
    "Both annual exchange-rate levels used in the log change must come from "
    "the same selected vintage.")

# --------------------------------------------------------------------------- #
# Missing-value contract (section 8)
# --------------------------------------------------------------------------- #

MISSING_VALUE_RULES: tuple[str, ...] = (
    "missing remains null",
    "no interpolation",
    "no extrapolation",
    "no cross-source fill",
    "no backward reconstruction from a later vintage",
    "no source switching",
    "no manual correction",
    "no imputation before Data Gate admission",
)
VALUE_LEVEL_IMPUTATION_AUTHORIZED = False

# --------------------------------------------------------------------------- #
# Data Gate contract (section 9) — INHERITED, never redesigned
# --------------------------------------------------------------------------- #

CANDIDATE_VALID_COVERAGE_MIN = 0.80
BLOCK_COMMON_SAMPLE_COVERAGE_MIN = 0.70
MIN_POSITIVE_EACH_VALIDATION_WINDOW = 5
COVERAGE_SCOPE = "development_only"
COVERAGE_DENOMINATOR = "retained_M2_development_common_sample"
EXPECTED_PARENT_ROWS = 539
EXPECTED_PARENT_POSITIVE = 55
EXPECTED_PARENT_NEGATIVE = 484
EXPECTED_PARENT_COMPANIES = 108
FINAL_TEST_ACCESS_FOR_ADMISSION = False

GATE_RESULT_NOT_EXECUTED = "NOT_EXECUTED"

M3I_GATE_FUTURE_RULES: tuple[str, ...] = (
    "M3I-2 passes only if both CPI inflation and FX change pass.",
    "A reduced one-variable M3I-1 cannot pass.",
    "Failure of either M3I-2 candidate rejects M3I-2.",
    "M3I-3 may be considered only if M3I-2 passed, the financing metadata "
    "lock was completed prospectively, and financing independently passed the "
    "same candidate Gate.",
    "Financing failure does not invalidate a passing M3I-2.",
    "No alternative series may be tried after coverage inspection.",
)

#: Fields that must be null (never zero) while the Gate has not executed.
UNRESOLVED_NULL_FIELDS: tuple[str, ...] = (
    "candidate_valid_coverage",
    "block_common_sample_coverage",
    "common_sample_rows",
    "common_sample_positive",
    "common_sample_negative",
    "positive_events_each_locked_validation_window",
)

# --------------------------------------------------------------------------- #
# Statistical and multiplicity contract (section 10)
# --------------------------------------------------------------------------- #

ORIGINAL_CONFIRMATORY_FAMILY: tuple[str, ...] = (
    "M2_minus_M1",
    "M3_CBI_minus_M2",
    "M4_minus_M3_CBI",
)
ORIGINAL_CONFIRMATORY_FAMILY_COMPLETE = False
M3I_INSERTED_INTO_ORIGINAL_FAMILY = False

SUPPLEMENTARY_FAMILY: tuple[dict[str, Any], ...] = (
    {
        "hypothesis_id": "S1",
        "comparison": "M3I_2_minus_retained_M2",
        "exists_only_if": "M3I-2 later passes the Data Gate",
        "exists_now": False,
    },
    {
        "hypothesis_id": "S2",
        "comparison": "M3I_3_minus_M3I_2",
        "exists_only_if": (
            "financing later receives a prospective exact lock and passes its "
            "Gate"),
        "exists_now": False,
    },
)

SUPPLEMENTARY_FAMILY_RULES: tuple[str, ...] = (
    "S1 exists only if M3I-2 later passes the Data Gate.",
    "S2 exists only if financing later receives a prospective exact lock and "
    "passes its Gate.",
    "If only S1 exists, supplementary_family_size = 1 and the Holm adjustment "
    "is mathematically unnecessary, but the family identity remains recorded.",
    "If S1 and S2 exist, Holm is applied across exactly S1 and S2.",
    "All results must be labelled supplementary/robustness.",
    "No confirmatory superiority claim is permitted.",
)

# --------------------------------------------------------------------------- #
# No-execution guarantee
# --------------------------------------------------------------------------- #

FORBIDDEN_RUNTIME_MODULES: tuple[str, ...] = (
    "requests", "urllib", "urllib3", "http", "httpx", "aiohttp", "socket",
    "webbrowser", "selenium", "playwright",
    "pandas", "openpyxl", "xlrd", "pyarrow",
    "sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "imblearn",
    "shap", "scipy", "numpy",
)

def _import_pattern(*modules: str) -> re.Pattern[str]:
    return re.compile(
        r"^\s*(?:from|import)\s+(" + "|".join(modules) + r")\b", re.MULTILINE)


FORBIDDEN_NETWORK_IMPORTS = _import_pattern(
    "requests", "urllib", "urllib3", "http", "httpx", "aiohttp", "socket",
    "webbrowser", "selenium", "playwright")
FORBIDDEN_INGESTION_IMPORTS = _import_pattern(
    "pandas", "openpyxl", "xlrd", "pyarrow")
FORBIDDEN_ESTIMATOR_IMPORTS = _import_pattern(
    "sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "imblearn",
    "shap", "scipy", "numpy")

#: Every forbidden import, in one pattern.
FORBIDDEN_IMPORT_PATTERN = _import_pattern(*FORBIDDEN_RUNTIME_MODULES)

FORBIDDEN_NETWORK_TOKENS: tuple[str, ...] = (
    "requests.get", "requests.post", "urlopen", "HTTPConnection",
    "session.get", "\"curl\"", "'curl'", "\"wget\"", "'wget'",
    "webdriver", "async_playwright",
)

FORBIDDEN_INGESTION_TOKENS: tuple[str, ...] = (
    "read_csv", "read_excel", "load_workbook", "csv.reader", "csv.DictReader",
    "pd.read", "np.loadtxt",
)

FORBIDDEN_ESTIMATOR_TOKENS: tuple[str, ...] = (
    ".fit(", ".fit_predict(", ".fit_resample(", ".fit_transform(",
    ".predict(", ".predict_proba(", ".decision_function(", "SMOTE(",
    "roc_auc_score", "average_precision_score", "bootstrap(", "multipletests",
)

FORBIDDEN_FINAL_TEST_TOKENS: tuple[str, ...] = (
    "final_test_features", "final_test_panel", "final_test_predictors",
    "final_test_targets", "load_final_test", "read_final_test",
    "outputs/04_models", "outputs/05_final_test",
)

FINAL_TEST_TARGET_YEARS: tuple[int, ...] = (1400, 1401, 1402)


def assert_no_estimator_runtime() -> None:
    """Fail closed if a forbidden runtime reached THIS module's namespace."""
    own = sys.modules[__name__]
    imported = sorted(
        name for name, value in vars(own).items()
        if getattr(value, "__name__", "") in FORBIDDEN_RUNTIME_MODULES)
    if imported:
        raise M3IntlMacroContractLockError(
            f"forbidden runtime imported: {imported}")


def _read_implementation_sources(root: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for rel in IMPLEMENTATION_FILES:
        path = root / rel
        if not path.is_file():
            raise M3IntlMacroContractLockError(
                f"implementation file missing: {rel}")
        texts[rel] = path.read_text(encoding="utf-8")
    return texts


def _scan_tokens(
    texts: dict[str, str], tokens: tuple[str, ...], label: str,
) -> None:
    """Fail closed when a forbidden token is *used* rather than *declared*.

    The declaration tuples above necessarily contain the token strings
    themselves, so a line that is part of a forbidden-token declaration is
    skipped. Any other occurrence is a violation.
    """
    declaration_markers = (
        "FORBIDDEN_NETWORK_TOKENS", "FORBIDDEN_INGESTION_TOKENS",
        "FORBIDDEN_ESTIMATOR_TOKENS", "FORBIDDEN_FINAL_TEST_TOKENS",
        "FORBIDDEN_ESTIMATOR_CALLS",
    )
    hits: list[str] = []
    for rel, text in texts.items():
        in_declaration = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in declaration_markers):
                in_declaration = line.rstrip().endswith("(")
                continue
            if in_declaration:
                if line.strip() == ")":
                    in_declaration = False
                continue
            for token in tokens:
                if token in line:
                    hits.append(f"{rel}:{lineno}:{token}")
    if hits:
        raise M3IntlMacroContractLockError(
            f"forbidden {label} path(s) present: {sorted(hits)}")


def _scan_imports(
    texts: dict[str, str], pattern: re.Pattern[str], label: str,
) -> None:
    for rel, text in texts.items():
        hit = pattern.search(text)
        if hit:
            raise M3IntlMacroContractLockError(
                f"forbidden {label} import {hit.group(1)!r} in {rel}")


def assert_no_network_paths(root: Path) -> None:
    """Validator rule 12 — no HTTP/requests/urllib/curl/browser/API path."""
    texts = _read_implementation_sources(root)
    _scan_imports(texts, FORBIDDEN_NETWORK_IMPORTS, "network")
    _scan_tokens(texts, FORBIDDEN_NETWORK_TOKENS, "network")


def assert_no_observation_ingestion_paths(root: Path) -> None:
    """Validator rule 13 — no pandas/openpyxl/CSV observation ingestion."""
    texts = _read_implementation_sources(root)
    _scan_imports(texts, FORBIDDEN_INGESTION_IMPORTS, "observation-ingestion")
    _scan_tokens(texts, FORBIDDEN_INGESTION_TOKENS, "observation-ingestion")


def assert_no_estimator_paths(root: Path) -> None:
    """Validator rule 14 — no estimator or prediction path."""
    assert_no_estimator_runtime()
    texts = _read_implementation_sources(root)
    _scan_imports(texts, FORBIDDEN_ESTIMATOR_IMPORTS, "estimator")
    _scan_tokens(texts, FORBIDDEN_ESTIMATOR_TOKENS, "estimator")


def assert_no_final_test_access_paths(root: Path) -> None:
    """Validator rule 15 — no final-test file or target access."""
    _scan_tokens(_read_implementation_sources(root),
                 FORBIDDEN_FINAL_TEST_TOKENS, "final-test-access")


# --------------------------------------------------------------------------- #
# Recursive payload guards
# --------------------------------------------------------------------------- #

def _walk(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.append((path, value))
            out.extend(_walk(value, path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}[{index}]"
            out.extend(_walk(value, path))
    return out


_M4_START_KEY = re.compile(r"m4_.*(start|authoriz)", re.IGNORECASE)
_MERGE_KEY = re.compile(r"merge", re.IGNORECASE)


def assert_no_m4_start_flag(payload: Any) -> None:
    """Validator rule 16 — no M4-start flag may be true anywhere."""
    bad = [path for path, value in _walk(payload)
           if value is True and _M4_START_KEY.search(path.rsplit(".", 1)[-1])]
    if bad:
        raise M3IntlMacroContractLockError(f"M4 start/authorization flag: {bad}")


def assert_no_merge_authorized_flag(payload: Any) -> None:
    """Validator rule 17 — no merge-authorized flag may be true anywhere."""
    bad = [path for path, value in _walk(payload)
           if value is True and _MERGE_KEY.search(path.rsplit(".", 1)[-1])]
    if bad:
        raise M3IntlMacroContractLockError(f"merge-authorized flag: {bad}")


def assert_unresolved_values_are_null_not_zero(gate: dict[str, Any]) -> None:
    """Validator rule 11 — unresolved is null, never zero."""
    if gate.get("gate_result") != GATE_RESULT_NOT_EXECUTED:
        raise M3IntlMacroContractLockError(
            "the M3I Data Gate must be recorded as NOT_EXECUTED")
    observed = gate.get("observed_values") or {}
    missing = [f for f in UNRESOLVED_NULL_FIELDS if f not in observed]
    if missing:
        raise M3IntlMacroContractLockError(
            f"unresolved Gate fields absent from observed_values: {missing}")
    bad = [path for path, value in _walk(observed)
           if value is not None]
    if bad:
        raise M3IntlMacroContractLockError(
            f"unresolved Gate value encoded as a number instead of null: "
            f"{bad}")


# --------------------------------------------------------------------------- #
# Contract-content validators (rules 1-10, 18-19)
# --------------------------------------------------------------------------- #

def assert_m3_cbi_block_preserved(block: dict[str, Any]) -> None:
    """Rule 1 — no change to M3-CBI candidate order or source."""
    if tuple(block.get("block") or ()) != M3_CBI_BLOCK:
        raise M3IntlMacroContractLockError(
            f"M3-CBI block must remain exactly {M3_CBI_BLOCK} in this order; "
            f"got {tuple(block.get('block') or ())}")
    if block.get("source_id") != M3_CBI_SOURCE_ID:
        raise M3IntlMacroContractLockError(
            f"M3-CBI source must remain {M3_CBI_SOURCE_ID}")
    if block.get("status") != M3_CBI_STATUS:
        raise M3IntlMacroContractLockError(
            f"M3-CBI status must remain {M3_CBI_STATUS}")
    if block.get("block_admitted") is not False:
        raise M3IntlMacroContractLockError(
            "M3-CBI must remain not admitted")


def assert_source_ids_not_reused(rows: list[dict[str, Any]]) -> None:
    """Rule 2 — M3I source ids may never be CBI/SCI source ids."""
    ids = [row.get("source_id") for row in rows]
    reused = sorted(set(ids) & set(FORBIDDEN_REUSED_SOURCE_IDS))
    if reused:
        raise M3IntlMacroContractLockError(
            f"M3I source registry reuses frozen source id(s): {reused}")
    if tuple(ids) != M3I_SOURCE_IDS:
        raise M3IntlMacroContractLockError(
            f"M3I source ids must be exactly {M3I_SOURCE_IDS}; got "
            f"{tuple(ids)}")


def assert_cpi_indicator_code(candidate: dict[str, Any]) -> None:
    """Rule 3 — the CPI indicator code is exact."""
    if candidate.get("indicator_code") != CPI_INDICATOR_CODE:
        raise M3IntlMacroContractLockError(
            f"CPI indicator code must be {CPI_INDICATOR_CODE}; got "
            f"{candidate.get('indicator_code')!r}")
    if candidate.get("transformation_formula") != "identity":
        raise M3IntlMacroContractLockError(
            "the CPI transformation must be identity")
    if candidate.get("frequency") != "annual":
        raise M3IntlMacroContractLockError("the CPI series must be annual")


def assert_fx_indicator_code(candidate: dict[str, Any]) -> None:
    """Rules 4 and 6 — the FX indicator code is exact and never ATLS."""
    code = candidate.get("indicator_code")
    if code == "PA.NUS.ATLS":
        raise M3IntlMacroContractLockError(
            "PA.NUS.ATLS is forbidden as the FX source series")
    if code != FX_INDICATOR_CODE:
        raise M3IntlMacroContractLockError(
            f"FX indicator code must be {FX_INDICATOR_CODE}; got {code!r}")


def assert_fx_transformation(candidate: dict[str, Any]) -> None:
    """Rule 5 — the FX transformation is exactly the locked log change."""
    if candidate.get("transformation_formula") != FX_TRANSFORMATION_FORMULA:
        raise M3IntlMacroContractLockError(
            f"FX transformation must be exactly "
            f"{FX_TRANSFORMATION_FORMULA!r}; got "
            f"{candidate.get('transformation_formula')!r}")
    conditions = tuple(
        candidate.get("fail_closed_transformation_conditions") or ())
    if conditions != FX_FAIL_CLOSED_CONDITIONS:
        raise M3IntlMacroContractLockError(
            "the FX fail-closed transformation conditions were altered")


def assert_m3i2_block_not_reduced(block: list[str] | tuple[str, ...]) -> None:
    """Rule 7 — a one-variable reduced M3I block can never be admitted."""
    if tuple(block) != M3I2_BLOCK:
        raise M3IntlMacroContractLockError(
            f"M3I-2 must be exactly {M3I2_BLOCK} in this order; got "
            f"{tuple(block)}")


def assert_financing_metadata_lock(candidate: dict[str, Any]) -> None:
    """Rule 8 — financing may not be admitted while its metadata is null."""
    nulls = [f for f in FINANCING_REQUIRED_METADATA_FIELDS
             if candidate.get(f) is None]
    if candidate.get("admitted") and nulls:
        raise M3IntlMacroContractLockError(
            f"financing marked admitted while metadata is unresolved: {nulls}")
    if nulls and candidate.get("candidate_selection_status") != (
            M3I3_FINANCING_LOCK_STATUS):
        raise M3IntlMacroContractLockError(
            "unresolved financing metadata must be recorded as "
            f"{M3I3_FINANCING_LOCK_STATUS}")
    if nulls and candidate.get("uniquely_determined") is not False:
        raise M3IntlMacroContractLockError(
            "financing cannot be uniquely determined while metadata is null")


def assert_financing_construct_not_a_forbidden_proxy(
    candidate: dict[str, Any],
) -> None:
    """Rule 9 — deposit rate / deposit ceiling and friends are forbidden."""
    haystack = " ".join(
        str(candidate.get(field) or "").lower()
        for field in ("exact_series_title", "exact_series_code",
                      "official_series_title", "selected_construct"))
    for proxy in FINANCING_FORBIDDEN_PROXIES:
        needle = proxy.lower()
        if needle in haystack:
            raise M3IntlMacroContractLockError(
                f"forbidden financing proxy selected: {proxy}")
    declared = tuple(candidate.get("forbidden_proxies") or ())
    if declared != FINANCING_FORBIDDEN_PROXIES:
        raise M3IntlMacroContractLockError(
            "the forbidden financing-proxy list was altered")


def assert_confirmatory_family_unchanged(mult: dict[str, Any]) -> None:
    """Rule 10 — M3I may never enter the original confirmatory Holm family."""
    family = tuple(mult.get("original_confirmatory_family") or ())
    if family != ORIGINAL_CONFIRMATORY_FAMILY:
        raise M3IntlMacroContractLockError(
            f"the original confirmatory family must remain "
            f"{ORIGINAL_CONFIRMATORY_FAMILY}; got {family}")
    if any("M3I" in member for member in family):
        raise M3IntlMacroContractLockError(
            "an M3I comparison was inserted into the confirmatory family")
    if mult.get("M3I_inserted_into_original_family") is not False:
        raise M3IntlMacroContractLockError(
            "M3I_inserted_into_original_family must be false")
    if mult.get("original_confirmatory_family_complete") is not False:
        raise M3IntlMacroContractLockError(
            "original_confirmatory_family_complete must be false")
    if mult.get("holm_executions") != 0:
        raise M3IntlMacroContractLockError(
            "no Holm adjustment may be executed in this action")


def assert_pr_base_is_not_main(decision: dict[str, Any]) -> None:
    """Rule 18 — no direct base on ``main`` while PR #73 remains open."""
    if decision.get("pr_base_branch") != PR_BASE_BRANCH:
        raise M3IntlMacroContractLockError(
            f"the stacked PR base must be {PR_BASE_BRANCH}; got "
            f"{decision.get('pr_base_branch')!r}")
    if decision.get("pr_base_branch") == MAIN_BRANCH:
        raise M3IntlMacroContractLockError(
            "this PR may not target main while PR #73 is open")
    if decision.get("predecessor_pr_merged") is not False:
        raise M3IntlMacroContractLockError(
            "PR #73 is recorded as unmerged; a merged claim is a scope breach")


def assert_scope_not_identified_by_hash_alone(auth: dict[str, Any]) -> None:
    """Rule 19 — the repeated authorization hash cannot identify scope."""
    if auth.get("identical_text_hash_used_for_prior_distinct_action") is not (
            True):
        raise M3IntlMacroContractLockError(
            "the authorization record must state that the same text and hash "
            "were used for an earlier, distinct action")
    if auth.get("scope_identified_by_hash_alone") is not False:
        raise M3IntlMacroContractLockError(
            "scope may never be identified by the repeated text hash alone")
    if not auth.get("scope_resolution_basis"):
        raise M3IntlMacroContractLockError(
            "the authorization record must record how scope was resolved")
    if auth.get("authorized_action_id") != ACTION_ID:
        raise M3IntlMacroContractLockError(
            f"authorized_action_id must be {ACTION_ID}")


# --------------------------------------------------------------------------- #
# Protected scope (rule 20)
# --------------------------------------------------------------------------- #

#: Every tracked file under these trees, AS OF ``BASELINE_COMMIT`` (the exact
#: PR #73 head), is a protected prior scientific artifact.
PROTECTED_TREES: tuple[str, ...] = (
    "project/stage125",
    "project/stage126",
    "project/stage127",
    "project/stage128/m2_incremental_evaluation",
    "project/stage128/m2_retained_block_human_decision",
    "project/stage128/m3_macro_data_gate",
)

PROTECTED_EXTRA_FILES: tuple[str, ...] = (
    "project/stage128/stage128_m2_d2_development_features.csv",
)

#: OPERATIONAL verification artifacts regenerated by
#: ``run_stage126_current_state_validator.py --build`` whenever the validator
#: source legitimately changes. Repository governance permits exactly that
#: (``prior_part_operational_verification_artifact_evolution_permitted``), so
#: they are excluded from the protected SCIENTIFIC set. This list is CLOSED.
PROTECTED_OPERATIONAL_EXCLUSIONS: tuple[str, ...] = (
    "project/stage126/README_STAGE126_CURRENT_STATE_VALIDATION.md",
    "project/stage126/metadata_and_hashes_stage126_current_state_validator.json",
    "project/stage126/stage126_current_state_validation_report.json",
)


def _git(root: Path, *args: str) -> str:
    """Run a read-only git command; fail closed on a non-zero exit."""
    import subprocess

    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise M3IntlMacroContractLockError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_files_under(root: Path, commit: str) -> tuple[str, ...]:
    out = _git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--",
               *PROTECTED_TREES)
    return tuple(sorted(p for p in out.split("\0") if p))


def enumerate_protected_baseline_files(root: Path) -> tuple[str, ...]:
    """The complete protected SCIENTIFIC path set at the PR #73 head."""
    paths = set(_tracked_files_under(root, BASELINE_COMMIT))
    paths -= set(PROTECTED_OPERATIONAL_EXCLUSIONS)
    for rel in PROTECTED_EXTRA_FILES:
        _git(root, "cat-file", "-e", f"{BASELINE_COMMIT}:{rel}")
        paths.add(rel)
    if not paths:
        raise M3IntlMacroContractLockError(
            "protected baseline enumeration produced no files")
    return tuple(sorted(paths))


def baseline_protected_manifest(root: Path) -> dict[str, str]:
    """SHA-256 of the BASELINE bytes of every protected path.

    Blobs are hashed as opaque bytes. They are never parsed or decoded, so no
    observation and no final-test value is read here.
    """
    import subprocess

    paths = enumerate_protected_baseline_files(root)
    proc = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=str(root), capture_output=True,
        input="".join(f"{BASELINE_COMMIT}:{rel}\n" for rel in paths
                      ).encode("utf-8"))
    if proc.returncode != 0:
        raise M3IntlMacroContractLockError(
            f"git cat-file --batch failed: {proc.stderr.decode()!r}")
    manifest: dict[str, str] = {}
    buf, pos = proc.stdout, 0
    for rel in paths:
        nl = buf.find(b"\n", pos)
        if nl < 0:
            raise M3IntlMacroContractLockError(
                f"truncated git cat-file output at {rel}")
        header = buf[pos:nl].decode("utf-8").split()
        if len(header) != 3 or header[1] != "blob":
            raise M3IntlMacroContractLockError(
                f"protected baseline path is not a blob: {rel} ({header})")
        size = int(header[2])
        start = nl + 1
        manifest[rel] = hashlib.sha256(buf[start:start + size]).hexdigest()
        pos = start + size + 1
    return dict(sorted(manifest.items()))


def verify_protected_immutability(
    root: Path, manifest: dict[str, str],
) -> dict[str, Any]:
    """Rule 20 — fail closed unless every protected artifact is unchanged."""
    expected_paths = enumerate_protected_baseline_files(root)
    expected = baseline_protected_manifest(root)

    if tuple(sorted(manifest)) != expected_paths:
        missing = sorted(set(expected_paths) - set(manifest))
        extra = sorted(set(manifest) - set(expected_paths))
        raise M3IntlMacroContractLockError(
            f"protected path set differs: missing={missing} extra={extra}")

    for rel in expected_paths:
        if manifest[rel] != expected[rel]:
            raise M3IntlMacroContractLockError(
                f"stored protected hash differs from baseline blob: {rel}")
        path = root / rel
        if not path.is_file():
            raise M3IntlMacroContractLockError(
                f"protected baseline file is absent on this branch: {rel}")
        if _sha256_file(path) != expected[rel]:
            raise M3IntlMacroContractLockError(
                f"protected file bytes differ from baseline: {rel}")

    added = sorted(set(_tracked_files_under(root, "HEAD"))
                   - set(expected_paths)
                   - set(PROTECTED_OPERATIONAL_EXCLUSIONS))
    if added:
        raise M3IntlMacroContractLockError(
            f"new tracked file(s) inside a protected tree: {added}")

    changed = [p for p in _git(
        root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD", "--",
        *expected_paths).splitlines() if p.strip()]
    if changed:
        raise M3IntlMacroContractLockError(
            f"protected paths changed in committed history: {sorted(changed)}")

    return {
        "protected_baseline_branch": BASELINE_BRANCH,
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_operational_exclusions": list(
            PROTECTED_OPERATIONAL_EXCLUSIONS),
        "protected_operational_exclusions_are_not_scientific_artifacts": True,
        "protected_file_count": len(expected_paths),
        "protected_paths_match_baseline": True,
        "protected_bytes_match_baseline": True,
        "protected_tree_has_no_new_tracked_files": True,
        "protected_committed_history_diff_empty": True,
    }


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_authorization_record() -> dict[str, Any]:
    checks = verify_human_authorization()
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,

        # verbatim human text — authoritative ONLY here
        "authorization_text": HUMAN_SOURCE_UTTERANCE,
        "authorization_text_is_verbatim_human_text": True,
        "authorization_utf8_bytes": checks["human_source_utterance_byte_length"],
        "authorization_sha256": checks["human_source_utterance_sha256"],
        "authorization_encoding": "utf-8",
        "authorization_has_trailing_newline": False,
        "authorization_local_timestamp": AUTHORIZATION_LOCAL_TIMESTAMP,
        "authorization_occurrence_context": AUTHORIZATION_OCCURRENCE_CONTEXT,

        # the repeated-phrase problem, stated explicitly
        "identical_text_hash_used_for_prior_distinct_action":
            IDENTICAL_TEXT_HASH_USED_FOR_PRIOR_DISTINCT_ACTION,
        "prior_distinct_action_id": PREDECESSOR_ACTION_ID,
        "scope_identified_by_hash_alone": SCOPE_IDENTIFIED_BY_HASH_ALONE,
        "scope_resolution_basis": SCOPE_RESOLUTION_BASIS,

        # derived, non-verbatim restatement
        "normalized_authorization_scope": NORMALIZED_AUTHORIZATION_SCOPE,
        "normalized_authorization_scope_is_derived_not_verbatim_human_text":
            True,
        "normalized_authorization_scope_sha256": checks[
            "normalized_authorization_scope_sha256"],

        # scope
        "authorized_action_id": ACTION_ID,
        "authorization_type": "one_action_authorization",
        "authorization_consumed": True,
        "standing_authorization": False,
        "scope_limited_to_this_action_only": True,
        "permits": [
            "creating the prospective M3I-2 source/definition/statistical "
            "contract lock",
            "creating a contingent, unresolved M3I-3 financing contract shell",
            "validating those contracts offline and deterministically",
        ],
        "does_not_permit": [
            "downloading or retrieving value-level macro observations",
            "querying World Bank, IMF, SCI, CBI, FRED, ALFRED or any other "
            "data API",
            "creating normalized macro observations",
            "joining macro values to company-year rows",
            "coverage calculation or Data Gate execution",
            "model fitting, prediction or M3I-versus-M2 evaluation",
            "bootstrap, confidence intervals, Holm execution, SHAP or SMOTE",
            "M4",
            "final-test access",
            "merging PR #73 or any new PR",
            "writing directly to main",
            "changing the frozen CBI-based M3 contract",
        ],
        "data_retrieval_authorized": False,
        "data_gate_authorized": False,
        "modeling_authorized": False,
        "m3i_incremental_evaluation_authorized": False,
        "m4_authorized": False,
        "final_test_access_authorized": False,
        "merge_authorized": False,

        "source_repository": REPOSITORY,
        "source_main_branch": MAIN_BRANCH,
        "source_main_commit": MAIN_COMMIT,
        "branch_baseline_branch": BASELINE_BRANCH,
        "branch_baseline_commit": BASELINE_COMMIT,
    }


def build_governance_boundary() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "contract_type": CONTRACT_TYPE,
        "repository": REPOSITORY,
        "main_branch": MAIN_BRANCH,
        "main_commit": MAIN_COMMIT,
        "baseline_pr_number": BASELINE_PR_NUMBER,
        "baseline_branch": BASELINE_BRANCH,
        "baseline_commit": BASELINE_COMMIT,
        "head_branch": HEAD_BRANCH,
        "pr_base_branch": PR_BASE_BRANCH,
        "pr_is_draft": True,
        "pr_is_stacked_on_open_pr": True,
        "predecessor_action_id": PREDECESSOR_ACTION_ID,
        "predecessor_pr_merged": False,
        "may_target_main": False,
        "merge_authorized": False,

        # the preserved CBI block
        "m3_cbi_block": {
            "block": list(M3_CBI_BLOCK),
            "source_id": M3_CBI_SOURCE_ID,
            "status": M3_CBI_STATUS,
            "block_admitted": M3_CBI_BLOCK_ADMITTED,
            "modified_by_this_action": False,
        },

        # the new supplementary families
        "m3i2_block": list(M3I2_BLOCK),
        "m3i3_block": list(M3I3_BLOCK),
        "supplementary_relationship": SUPPLEMENTARY_RELATIONSHIP,
        "m3i_is_confirmatory_m3": False,
        "m3i2_contract_status": M3I2_CONTRACT_STATUS,
        "m3i2_contract_prospectively_locked": True,
        "m3i2_data_retrieval_started": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "m3i2_block_admitted": False,
        "m3i2_incremental_evaluation_authorized": False,
        "m3i3_financing_metadata_lock": M3I3_FINANCING_LOCK_STATUS,
        "m3i3_admitted": False,

        # the frozen firewall
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_target_years": list(FINAL_TEST_TARGET_YEARS),

        "next_action_id": NEXT_ACTION_ID,
        "next_action_authorized": NEXT_ACTION_AUTHORIZED,
        "next_action_pointer_is_not_authorization": True,
    }


def build_definition_lock() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "contract_version": CONTRACT_VERSION,
        "lock_type": "prospective_metadata_only_definition_lock",
        "locked_before_any_value_level_work": True,
        "locked_from_official_metadata_not_from_observed_coverage": True,
        "m3_cbi_block_preserved": {
            "block": list(M3_CBI_BLOCK),
            "source_id": M3_CBI_SOURCE_ID,
            "status": M3_CBI_STATUS,
            "block_admitted": M3_CBI_BLOCK_ADMITTED,
        },
        "m3i2_block_id": M3I2_BLOCK_ID,
        "m3i2_block": list(M3I2_BLOCK),
        "m3i2_candidate_ids": list(M3I2_CANDIDATE_IDS),
        "m3i2_lock_status": M3I2_CONTRACT_STATUS,
        "m3i2_candidates": [CPI_CANDIDATE, FX_CANDIDATE],
        "m3i3_block_id": M3I3_BLOCK_ID,
        "m3i3_block": list(M3I3_BLOCK),
        "m3i3_candidate": FINANCING_CANDIDATE,
        "m3i3_lock_status": M3I3_FINANCING_LOCK_STATUS,
        "m3i3_admitted": False,
        "missing_value_contract": {
            "rules": list(MISSING_VALUE_RULES),
            "value_level_imputation_authorized":
                VALUE_LEVEL_IMPUTATION_AUTHORIZED,
        },
        "sources": [dict(row) for row in SOURCE_REGISTRY],
        "reference_urls_fetched_in_this_action":
            REFERENCE_URLS_FETCHED_IN_THIS_ACTION,
    }


def build_prediction_time_contract() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "frozen_project_prediction_cutoff":
            FROZEN_PREDICTION_CUTOFF_DEFINITION,
        "frozen_project_prediction_cutoff_changed_by_this_action": False,
        "macro_availability_rule": MACRO_AVAILABILITY_RULE,
        "wdi_as_of_rules": list(WDI_AS_OF_RULES),
        "fx_same_vintage_rule": FX_SAME_VINTAGE_RULE,
        "date_only_release_on_cutoff_date_is_excluded": True,
        "no_pre_cutoff_vintage_verified_yields_null": True,
        "fiscal_year_label_only_mapping_allowed": False,
        "jalali_and_gregorian_dates_preserved_separately": True,
        "current_value_treated_as_historically_available": False,
        "vintages_applied_in_this_action": 0,
        "observations_timestamped_in_this_action": 0,
    }


def build_data_gate_contract() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "thresholds_inherited_not_redesigned": True,
        "thresholds": {
            "candidate_valid_coverage_min": CANDIDATE_VALID_COVERAGE_MIN,
            "block_common_sample_coverage_min":
                BLOCK_COMMON_SAMPLE_COVERAGE_MIN,
            "minimum_positive_evaluable_each_locked_validation_window":
                MIN_POSITIVE_EACH_VALIDATION_WINDOW,
            "coverage_scope": COVERAGE_SCOPE,
            "denominator": COVERAGE_DENOMINATOR,
            "expected_parent_rows": EXPECTED_PARENT_ROWS,
            "expected_parent_positive": EXPECTED_PARENT_POSITIVE,
            "expected_parent_negative": EXPECTED_PARENT_NEGATIVE,
            "expected_parent_companies": EXPECTED_PARENT_COMPANIES,
            "final_test_access_for_admission": FINAL_TEST_ACCESS_FOR_ADMISSION,
        },
        "future_rules": list(M3I_GATE_FUTURE_RULES),
        "reduced_one_variable_block_can_pass": False,
        "gate_result": GATE_RESULT_NOT_EXECUTED,
        "gate_executed": False,
        "coverage_calculations": 0,
        # Unresolved is NULL. Zero is never used in place of not-executed.
        "observed_values": {field: None for field in UNRESOLVED_NULL_FIELDS},
        "unresolved_values_are_null_not_zero": True,
    }


def build_multiplicity_contract() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "original_confirmatory_family": list(ORIGINAL_CONFIRMATORY_FAMILY),
        "original_confirmatory_family_complete":
            ORIGINAL_CONFIRMATORY_FAMILY_COMPLETE,
        "original_confirmatory_family_changed_by_this_action": False,
        "M3I_inserted_into_original_family": M3I_INSERTED_INTO_ORIGINAL_FAMILY,
        "supplementary_family": [dict(row) for row in SUPPLEMENTARY_FAMILY],
        "supplementary_family_rules": list(SUPPLEMENTARY_FAMILY_RULES),
        "supplementary_family_size_now": 0,
        "results_label": "supplementary_robustness_only",
        "confirmatory_superiority_claim_permitted": False,
        "holm_executions": 0,
        "comparisons_executed": 0,
    }


def build_decision(
    root: Path, protected_manifest: dict[str, str],
) -> dict[str, Any]:
    immutability = verify_protected_immutability(root, protected_manifest)
    return {
        "contract_id": CONTRACT_ID,
        "action_id": ACTION_ID,
        "contract_type": CONTRACT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "decision": "M3I2_CONTRACT_PROSPECTIVELY_LOCKED",
        "result_code": "M3I2_PROSPECTIVE_CONTRACT_LOCK_READY_FOR_INDEPENDENT_"
                       "AUDIT",

        # topology
        "repository": REPOSITORY,
        "source_main_branch": MAIN_BRANCH,
        "source_main_commit": MAIN_COMMIT,
        "baseline_pr_number": BASELINE_PR_NUMBER,
        "baseline_branch": BASELINE_BRANCH,
        "baseline_commit": BASELINE_COMMIT,
        "head_branch": HEAD_BRANCH,
        "pr_base_branch": PR_BASE_BRANCH,
        "pr_is_draft": True,
        "predecessor_action_id": PREDECESSOR_ACTION_ID,
        "predecessor_pr_merged": False,
        "may_target_main": False,

        # the preserved CBI contract
        "m3_cbi_gate_status": M3_CBI_STATUS,
        "m3_cbi_block_admitted": M3_CBI_BLOCK_ADMITTED,
        "m3_cbi_contract_changed": False,

        # M3I-2
        "m3i2_contract_lock_executed": True,
        "m3i2_contract_status": M3I2_CONTRACT_STATUS,
        "m3i2_block": list(M3I2_BLOCK),
        "m3i2_candidate_ids": list(M3I2_CANDIDATE_IDS),
        "m3i2_retrieval_started": False,
        "m3i2_data_gate_executed": False,
        "m3i2_block_admitted": False,
        "m3i2_incremental_evaluation_authorized": False,
        "m3i2_modeling_started": False,

        # M3I-3
        "m3i3_financing_lock": M3I3_FINANCING_LOCK_STATUS,
        "m3i3_admitted": False,

        # execution audit
        "network_requests": 0,
        "data_files_downloaded": 0,
        "macro_observations_read": 0,
        "company_rows_loaded": 0,
        "final_test_rows_loaded": 0,
        "model_fits": 0,
        "predictions": 0,
        "predictive_metrics": 0,
        "coverage_calculations": 0,
        "holm_calculations": 0,

        # firewall
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "merge_authorized": False,

        # pointers
        "last_completed_research_action_id": ACTION_ID,
        "next_research_action_id": NEXT_ACTION_ID,
        "next_action_authorized": NEXT_ACTION_AUTHORIZED,
        "next_research_action_pointer_is_not_authorization": True,
        "data_collection_started": False,

        "protected_immutability": immutability,
    }


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_report(
    root: Path,
    authorization: dict[str, Any],
    governance: dict[str, Any],
    lock: dict[str, Any],
    prediction_time: dict[str, Any],
    gate: dict[str, Any],
    multiplicity: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        entry: dict[str, Any] = {
            "name": name, "status": "PASS" if ok else "FAIL"}
        if detail:
            entry["detail"] = detail
        assertions.append(entry)

    def guard(name: str, fn) -> None:
        try:
            fn()
        except M3IntlMacroContractLockError as exc:
            check(name, False, str(exc))
        else:
            check(name, True)

    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")

    # -- authorization ----------------------------------------------------- #
    check("authorization_byte_length_is_28",
          len(raw) == HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH == 28)
    check("authorization_sha256_matches",
          hashlib.sha256(raw).hexdigest() == HUMAN_SOURCE_UTTERANCE_SHA256
          and authorization["authorization_sha256"]
          == HUMAN_SOURCE_UTTERANCE_SHA256)
    check("verbatim_and_normalized_authorization_are_separated",
          authorization["authorization_text"] == HUMAN_SOURCE_UTTERANCE
          and authorization["normalized_authorization_scope"]
          == NORMALIZED_AUTHORIZATION_SCOPE
          and authorization["authorization_text"]
          != authorization["normalized_authorization_scope"])
    check("authorization_is_one_action_and_consumed",
          authorization["authorization_type"] == "one_action_authorization"
          and authorization["authorization_consumed"] is True
          and authorization["standing_authorization"] is False)
    # rule 19
    guard("scope_not_identified_by_repeated_hash_alone",
          lambda: assert_scope_not_identified_by_hash_alone(authorization))

    # -- topology ---------------------------------------------------------- #
    check("exact_pr73_head_baseline",
          decision["baseline_commit"] == BASELINE_COMMIT
          == "e6db63fb7d105f0d3a39db101c9e364161c367e9"
          and decision["baseline_branch"] == BASELINE_BRANCH)
    check("live_main_commit_recorded",
          decision["source_main_commit"] == MAIN_COMMIT)
    # rule 18
    guard("stacked_pr_base_is_not_main",
          lambda: assert_pr_base_is_not_main(decision))
    check("pr_is_draft_and_unmerged",
          decision["pr_is_draft"] is True
          and decision["predecessor_pr_merged"] is False)

    # -- rule 1: M3-CBI preserved ------------------------------------------ #
    guard("m3_cbi_block_order_and_source_preserved",
          lambda: assert_m3_cbi_block_preserved(governance["m3_cbi_block"]))
    check("m3_cbi_contract_unchanged_by_this_action",
          decision["m3_cbi_contract_changed"] is False
          and decision["m3_cbi_gate_status"] == M3_CBI_STATUS
          and decision["m3_cbi_block_admitted"] is False)
    check("m3i_is_a_distinct_supplementary_family",
          governance["supplementary_relationship"]
          == SUPPLEMENTARY_RELATIONSHIP
          and governance["m3i_is_confirmatory_m3"] is False)

    # -- rule 2: source ids ------------------------------------------------ #
    guard("m3i_source_ids_are_new_and_never_reused",
          lambda: assert_source_ids_not_reused(lock["sources"]))
    check("source_reference_urls_recorded_but_not_fetched",
          lock["reference_urls_fetched_in_this_action"] is False
          and all(row["reference_fetched_in_this_action"] is False
                  for row in lock["sources"])
          and all(row["retrieval_status"] == "not_authorized"
                  for row in lock["sources"]))

    # -- rules 3-7: the M3I-2 definition lock ------------------------------ #
    cpi, fx = lock["m3i2_candidates"]
    guard("cpi_indicator_code_is_exact", lambda: assert_cpi_indicator_code(cpi))
    guard("fx_indicator_code_is_exact_and_not_atls",
          lambda: assert_fx_indicator_code(fx))
    guard("fx_transformation_is_exactly_the_locked_log_change",
          lambda: assert_fx_transformation(fx))
    guard("m3i2_block_is_never_reduced_to_one_variable",
          lambda: assert_m3i2_block_not_reduced(lock["m3i2_block"]))
    check("cpi_forbidden_alternatives_recorded",
          tuple(cpi["forbidden_alternatives"]) == CPI_FORBIDDEN_ALTERNATIVES)
    check("fx_forbidden_alternatives_recorded",
          tuple(fx["forbidden_alternatives"]) == FX_FORBIDDEN_ALTERNATIVES)
    check("both_m3i2_candidates_uniquely_determined",
          cpi["uniquely_determined"] is True
          and fx["uniquely_determined"] is True)
    check("no_m3i2_candidate_is_admitted_without_a_gate",
          cpi["admitted"] is False and fx["admitted"] is False
          and decision["m3i2_block_admitted"] is False)

    # -- rules 8-9: the contingent financing shell ------------------------- #
    financing = lock["m3i3_candidate"]
    guard("financing_not_admitted_while_metadata_is_null",
          lambda: assert_financing_metadata_lock(financing))
    guard("financing_construct_is_not_a_forbidden_proxy",
          lambda: assert_financing_construct_not_a_forbidden_proxy(financing))
    check("financing_metadata_fields_are_all_null",
          all(financing[f] is None
              for f in FINANCING_REQUIRED_METADATA_FIELDS))
    check("financing_stop_rule_recorded",
          financing["stop_rule"] == FINANCING_STOP_RULE
          and financing["candidate_selection_status"]
          == M3I3_FINANCING_LOCK_STATUS)

    # -- rule 10: multiplicity --------------------------------------------- #
    guard("original_confirmatory_family_unchanged",
          lambda: assert_confirmatory_family_unchanged(multiplicity))
    check("supplementary_family_is_separate_and_empty_now",
          [row["hypothesis_id"] for row in multiplicity[
              "supplementary_family"]] == ["S1", "S2"]
          and all(row["exists_now"] is False
                  for row in multiplicity["supplementary_family"])
          and multiplicity["supplementary_family_size_now"] == 0)
    check("no_confirmatory_superiority_claim_is_permitted",
          multiplicity["confirmatory_superiority_claim_permitted"] is False
          and multiplicity["results_label"]
          == "supplementary_robustness_only")

    # -- rule 11: null, never zero ----------------------------------------- #
    guard("unresolved_gate_values_are_null_not_zero",
          lambda: assert_unresolved_values_are_null_not_zero(gate))
    check("gate_thresholds_are_inherited_unchanged",
          gate["thresholds_inherited_not_redesigned"] is True
          and gate["thresholds"]["candidate_valid_coverage_min"]
          == CANDIDATE_VALID_COVERAGE_MIN
          and gate["thresholds"]["block_common_sample_coverage_min"]
          == BLOCK_COMMON_SAMPLE_COVERAGE_MIN
          and gate["thresholds"][
              "minimum_positive_evaluable_each_locked_validation_window"]
          == MIN_POSITIVE_EACH_VALIDATION_WINDOW
          and gate["thresholds"]["expected_parent_rows"]
          == EXPECTED_PARENT_ROWS)
    check("gate_is_recorded_as_not_executed",
          gate["gate_result"] == GATE_RESULT_NOT_EXECUTED
          and gate["gate_executed"] is False
          and decision["m3i2_data_gate_executed"] is False)

    # -- prediction time and missing values -------------------------------- #
    check("frozen_prediction_cutoff_preserved",
          prediction_time["frozen_project_prediction_cutoff"]
          == FROZEN_PREDICTION_CUTOFF_DEFINITION
          and prediction_time[
              "frozen_project_prediction_cutoff_changed_by_this_action"]
          is False)
    check("wdi_as_of_rules_complete",
          tuple(prediction_time["wdi_as_of_rules"]) == WDI_AS_OF_RULES
          and prediction_time["fx_same_vintage_rule"] == FX_SAME_VINTAGE_RULE)
    check("missing_value_contract_forbids_imputation",
          tuple(lock["missing_value_contract"]["rules"]) == MISSING_VALUE_RULES
          and lock["missing_value_contract"][
              "value_level_imputation_authorized"] is False)

    # -- rules 12-15: no execution paths ----------------------------------- #
    guard("no_network_or_api_execution_path",
          lambda: assert_no_network_paths(root))
    guard("no_observation_ingestion_path",
          lambda: assert_no_observation_ingestion_paths(root))
    guard("no_estimator_or_prediction_path",
          lambda: assert_no_estimator_paths(root))
    guard("no_final_test_file_or_target_access_path",
          lambda: assert_no_final_test_access_paths(root))

    # -- rules 16-17: firewall flags --------------------------------------- #
    payload = {
        "authorization": authorization, "governance": governance,
        "definition_lock": lock, "prediction_time": prediction_time,
        "data_gate": gate, "multiplicity": multiplicity,
        "decision": decision,
    }
    guard("no_m4_start_or_authorization_flag",
          lambda: assert_no_m4_start_flag(payload))
    guard("no_merge_authorized_flag",
          lambda: assert_no_merge_authorized_flag(payload))
    check("final_test_remains_locked",
          decision["final_test_locked"] is True
          and decision["final_test_access_authorized"] is False
          and governance["final_test_locked"] is True)

    # -- rule 20: protected scope ------------------------------------------ #
    immutability = decision["protected_immutability"]
    check("protected_prior_scientific_artifacts_unchanged",
          immutability["protected_bytes_match_baseline"] is True
          and immutability["protected_paths_match_baseline"] is True
          and immutability["protected_committed_history_diff_empty"] is True
          and immutability["protected_tree_has_no_new_tracked_files"] is True
          and immutability["protected_baseline_commit"] == BASELINE_COMMIT)

    # -- execution counters ------------------------------------------------ #
    counters = {
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
    check("execution_counters_are_all_zero",
          all(decision[key if key != "Holm_calculations" else
                       "holm_calculations"] == 0 for key in counters))
    check("no_data_collection_claim",
          decision["data_collection_started"] is False
          and decision["m3i2_retrieval_started"] is False)
    check("next_action_pointer_is_not_an_authorization",
          decision["next_research_action_id"] == NEXT_ACTION_ID
          and decision["next_action_authorized"] is False)

    failed = [a["name"] for a in assertions if a["status"] != "PASS"]
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "contract_status": M3I2_CONTRACT_STATUS,
        "assertion_count": len(assertions),
        "failed_count": len(failed),
        "failed_assertions": failed,
        "all_pass": not failed,
        "assertions": assertions,
        "execution_counters": counters,
        "protected_immutability": immutability,
        "scope_note": (
            "This QC report checks the internal consistency of a "
            "METADATA-ONLY prospective contract lock. It retrieved no macro "
            "observation, executed no Data Gate, fit no model and produced no "
            "scientific result about whether M3I-2 improves prediction. "
            "M3I-2 is a supplementary/robustness family and is never "
            "confirmatory M3."
        ),
    }


# --------------------------------------------------------------------------- #
# Rendering and build
# --------------------------------------------------------------------------- #

def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"


def _render_csv(columns: tuple[str, ...],
                rows: tuple[dict[str, Any], ...]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns),
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if row.get(k) is None else row.get(k))
                         for k in columns})
    return buf.getvalue()


def build_metadata(package_sha256: dict[str, str],
                   protected_manifest: dict[str, str]) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "contract_version": CONTRACT_VERSION,
        "package_artifacts_sha256": dict(sorted(package_sha256.items())),
        "protected_baseline_branch": BASELINE_BRANCH,
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_file_count": len(protected_manifest),
        "protected_files_sha256": dict(protected_manifest),
        "source_repository": REPOSITORY,
        "source_main_branch": MAIN_BRANCH,
        "source_main_commit": MAIN_COMMIT,
        "immutability_requirement": (
            "Every path listed in protected_files_sha256 must remain "
            "byte-identical to its bytes at the exact PR #73 head "
            f"{BASELINE_COMMIT}, no protected path may be deleted, and no new "
            "tracked file may appear inside a protected tree."
        ),
    }


def render_readme(decision: dict[str, Any], qc: dict[str, Any]) -> str:
    return f"""# Stage128 — M3I-2 prospective contract lock

**Action id:** `{ACTION_ID}`
**Contract type:** `{CONTRACT_TYPE}`
**Contract status:** `{decision["m3i2_contract_status"]}`
**Stacked on:** PR #{BASELINE_PR_NUMBER} head `{BASELINE_COMMIT}`
(branch `{BASELINE_BRANCH}`), which is **not merged**.

```text
CONTRACT LOCK ONLY
NO DATA RETRIEVAL
NO DATA GATE
NO MODELING
NO M3I-vs-M2
NO M4
FINAL TEST LOCKED
NO MERGE AUTHORIZATION
```

## What this action is

A **prospective** source / definition / statistical contract lock for the
supplementary international-macro block **M3I-2**, plus a **contingent and
unresolved** M3I-3 financing shell. Everything here is metadata. No macro
observation was retrieved, no value was normalized or joined, no coverage was
computed, no Gate was executed, no model was fit and no comparison was run.

## Relationship to M3-CBI — supplementary, not a replacement

The frozen CBI block is preserved exactly:

```text
M3-CBI: cpi_inflation, fx_change_official, policy_financing_rate
source: {M3_CBI_SOURCE_ID}
status: {M3_CBI_STATUS}
```

M3I-2 is **not** a substitution, correction or continuation of M3-CBI. It is a
distinct supplementary family, and **no M3I block may ever be presented as
confirmatory M3**.

## M3I-2 — prospectively locked

1. `intl_cpi_inflation_annual` — `{SRC_CPI}`, indicator `{CPI_INDICATOR_CODE}`,
   annual, percent, transformation `identity`.
2. `intl_fx_change_official_annual` — `{SRC_FX}`, indicator
   `{FX_INDICATOR_CODE}`, annual, LCU per US dollar, transformation
   `{FX_TRANSFORMATION_FORMULA}` over two consecutive annual observations from
   the **same vintage**, fail-closed to null on any missing, non-positive,
   non-consecutive or cross-vintage input.

`PA.NUS.ATLS`, free-market/unofficial rates, aggregators, crypto-implied rates
and manual regime splices are forbidden, as is any alternative indicator or
transformation chosen **after** coverage or model inspection.

## M3I-3 — contingent and unresolved

`intl_financing_rate` exists only as a contract shell against
`{SRC_FINANCING}` / `{FINANCING_DATASET_ID}`. Every operational metadata field
is `null`, `candidate_selection_status` = `{M3I3_FINANCING_LOCK_STATUS}`, and
`admitted` = **false**. Deposit rates, deposit-rate ceilings, real rates,
spreads, repo/reverse-repo volumes, standing-facility amounts and any
relabelled policy rate are forbidden proxies.

**Stop rule.** {FINANCING_STOP_RULE}

## Data Gate contract — inherited, not redesigned, not executed

Thresholds are the existing frozen ones (candidate coverage
{CANDIDATE_VALID_COVERAGE_MIN}, block common sample
{BLOCK_COMMON_SAMPLE_COVERAGE_MIN}, ≥{MIN_POSITIVE_EACH_VALIDATION_WINDOW}
positives per locked validation window, development-only over the retained-M2
development common sample: {EXPECTED_PARENT_ROWS} rows,
{EXPECTED_PARENT_POSITIVE} positive, {EXPECTED_PARENT_NEGATIVE} negative,
{EXPECTED_PARENT_COMPANIES} companies).

In this action every observed value is `null` and the Gate result is
`{GATE_RESULT_NOT_EXECUTED}`. **Zero is never used in place of
unresolved/not-executed.**

M3I-2 passes only if **both** candidates pass; a reduced one-variable M3I-1
cannot pass; financing may be considered only after M3I-2 passes, its metadata
lock is completed prospectively and it independently passes the same candidate
Gate — and financing failure never invalidates a passing M3I-2.

## Multiplicity — a separate supplementary family

The original confirmatory Holm family stays exactly
`M2_minus_M1`, `M3_CBI_minus_M2`, `M4_minus_M3_CBI`
(`original_confirmatory_family_complete` = false,
`M3I_inserted_into_original_family` = false).

The supplementary family is `S1 = M3I_2_minus_retained_M2` and
`S2 = M3I_3_minus_M3I_2`; neither exists yet. All future M3I results are
labelled supplementary/robustness, and no confirmatory superiority claim is
permitted.

## Execution audit

All zero: network requests, data files downloaded, macro observations read,
company rows loaded, final-test rows loaded, model fits, predictions,
predictive metrics, coverage calculations, Holm calculations.

QC: **{qc["assertion_count"]} assertions, {qc["failed_count"]} failed**,
all_pass = **{qc["all_pass"]}**.

## State

* `m3i2_contract_lock_executed` = **true**, status
  `{decision["m3i2_contract_status"]}`
* `m3i2_retrieval_started` = **false**, `m3i2_data_gate_executed` = **false**
* `m3i2_block_admitted` = **false**,
  `m3i2_incremental_evaluation_authorized` = **false**
* `m3i2_modeling_started` = **false**
* `m3i3_financing_lock` = `{M3I3_FINANCING_LOCK_STATUS}`, `m3i3_admitted` =
  **false**
* `m4_authorized` = **false**, `m4_started` = **false**,
  `final_test_locked` = **true**
* `merge_authorized` = **false**

Next pointer (informational only): `{NEXT_ACTION_ID}` with
`next_action_authorized` = **false**. Data collection has **not** started.
"""


def build_package(
    repo_root: str | os.PathLike[str], write: bool = False,
) -> dict[str, Any]:
    """Build (and optionally write) the M3I-2 prospective contract lock."""
    assert_no_estimator_runtime()
    root = Path(repo_root)
    verify_human_authorization()

    protected_manifest = baseline_protected_manifest(root)

    authorization = build_authorization_record()
    governance = build_governance_boundary()
    lock = build_definition_lock()
    prediction_time = build_prediction_time_contract()
    gate = build_data_gate_contract()
    multiplicity = build_multiplicity_contract()
    decision = build_decision(root, protected_manifest)

    qc = build_qc_report(root, authorization, governance, lock,
                         prediction_time, gate, multiplicity, decision)
    if not qc["all_pass"]:
        raise M3IntlMacroContractLockError(
            f"M3I contract-lock QC failed: {qc['failed_assertions']}")

    readme_text = render_readme(decision, qc)
    texts: dict[str, str] = {
        README_REL: readme_text,
        AUTHORIZATION_REL: _json_text(authorization),
        GOVERNANCE_REL: _json_text(governance),
        SOURCE_REGISTRY_REL: _render_csv(
            SOURCE_REGISTRY_COLUMNS, SOURCE_REGISTRY),
        DEFINITION_LOCK_REL: _json_text(lock),
        PREDICTION_TIME_REL: _json_text(prediction_time),
        DATA_GATE_REL: _json_text(gate),
        MULTIPLICITY_REL: _json_text(multiplicity),
        DECISION_REL: _json_text(decision),
        QC_REL: _json_text(qc),
    }
    package_sha256 = {rel: _sha256_text(text) for rel, text in texts.items()}
    metadata = build_metadata(package_sha256, protected_manifest)
    texts[METADATA_REL] = _json_text(metadata)

    if write:
        for rel, text in texts.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    return {
        "authorization_record": authorization,
        "governance_boundary": governance,
        "definition_lock": lock,
        "prediction_time_contract": prediction_time,
        "data_gate_contract": gate,
        "multiplicity_contract": multiplicity,
        "decision": decision,
        "qc_report": qc,
        "metadata": metadata,
        "artifact_texts": texts,
        "protected_manifest": protected_manifest,
    }
