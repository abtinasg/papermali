"""Stage128 — Track B step E: the M3-LAG-WDI EXPLORATORY INCREMENTAL EVALUATION.

Authorized action: ``stage128-m3-lag-wdi-exploratory-incremental-evaluation``
Authorized scope:  ``exploratory_incremental_evaluation_only``

Step D admitted the two lagged WDI features as DATA (coverage 539/539) and a
separate human decision LOCKED the calendar mapping
(``predictor_year_t = jalali_fiscal_year_t + 621``). Neither authorized a
model fit. This step — under its own new, single-use human authorization — is
the first and only action permitted to:

* materialize the M3-LAG-WDI modeling FEATURE-VALUE table (step D deliberately
  produced row STATUSES only, because feature values are not invariant to the
  calendar convention that was unlocked at the time);
* refit the retained M2 comparator and the 14-feature M3-LAG-WDI block on the
  IDENTICAL post-complete-case development sample;
* compute the paired exploratory comparison ``E1``.

What it may never become
------------------------
The block's scientific role is frozen as
``supplementary_exploratory_robustness_block``. A favourable predictive result
does not promote it, does not repair M3-CBI, does not replace M3I-2, does not
enter the confirmatory Holm family and cannot select the paper winner. An
unfavourable one does not retire any confirmatory conclusion either. The
comparison lives in its own family ``M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY``
and is reported as ``supplementary_exploratory_robustness_only``.

Everything inherited, nothing invented
--------------------------------------
The validation architecture, canonical metric definitions, seed policy,
paired company-cluster bootstrap and the three retained model configurations
are IMPORTED from the retained-M2 evaluation module rather than restated, so
they cannot drift. This module defines no threshold, no metric, no seed and no
hyperparameter of its own. There is no tuning code path, no grid search, no
feature-selection code path, no imputation code path, no SHAP code path (the
frozen step-E contract does not require one) and no network code path.

The comparator is REFIT, never reused
-------------------------------------
The retained M2 numbers published by ``stage127-m2-incremental-evaluation``
were computed on that action's own common sample. This step does not import
them as the comparator: it refits M2 on the sample this step actually
materializes. Because both lagged WDI features are constructible for all 539
rows, that sample is mechanically the same 539 rows — which is a fact this
module VERIFIES and reports, never one it assumes.

Final Test: locked. Rows read: 0. There is no code path that opens it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
from pathlib import Path
from typing import Any

import numpy as np

from src import stage126_m1_primary_development_tuning as m1
from src import stage127_m2_incremental_evaluation as m2ie

ACTION_ID = "stage128-m3-lag-wdi-exploratory-incremental-evaluation"
AUTHORIZED_SCOPE = "exploratory_incremental_evaluation_only"
PACKAGE_ID = "stage128_m3_lag_wdi_exploratory_incremental_evaluation"
PACKAGE_REL = "project/stage128/m3_lag_wdi_exploratory_incremental_evaluation"

SRC_REL = ("project/src/"
           "stage128_m3_lag_wdi_exploratory_incremental_evaluation.py")
RUN_REL = ("project/"
           "run_stage128_m3_lag_wdi_exploratory_incremental_evaluation.py")
TEST_REL = ("project/tests/"
            "test_stage128_m3_lag_wdi_exploratory_incremental_evaluation.py")


class M3LagWdiEvaluationError(RuntimeError):
    """Raised whenever a fail-closed precondition of step E is violated."""


class FinalTestLockError(M3LagWdiEvaluationError):
    """Raised if any code path would reach a locked final-test row."""


# --------------------------------------------------------------------------- #
# The NEW single-use human authorization for THIS step
# --------------------------------------------------------------------------- #

#: Verbatim opening lines of the human supervisor's step E authorization
#: message, pinned by byte length and digest. It is distinct from the
#: contract-lock, retrieval, step C, Data Gate and calendar-mapping-lock
#: authorizations, every one of which stays historical, consumed and is never
#: stretched to cover step E.
HUMAN_AUTHORIZATION_TEXT = (
    "HUMAN SCIENTIFIC DECISION — AUTHORIZE STEP E ONLY\n"
    "\n"
    "I explicitly authorize ONE new single-use action only:\n"
    "\n"
    "stage128-m3-lag-wdi-exploratory-incremental-evaluation"
)

#: One-time authorizations that this step must NOT reuse. Each is recorded as
#: consumed and non-reusable; step E consumes only its own.
NON_REUSABLE_PRIOR_AUTHORIZATIONS: tuple[str, ...] = (
    "stage128-m3-lag-wdi-exploratory-contract-lock",
    "stage128-m3-lag-wdi-exploratory-data-retrieval",
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit",
    "stage128-m3-lag-wdi-exploratory-data-gate",
    "stage128-m3-lag-wdi-exploratory-calendar-mapping-lock",
)


def verify_human_authorization() -> dict[str, Any]:
    """The step E authorization, pinned by its own byte length and digest."""
    raw = HUMAN_AUTHORIZATION_TEXT.encode("utf-8")
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "authorization_text": HUMAN_AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": len(raw),
        "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        "authorization_is_single_use": True,
        "authorization_is_development_only": True,
        "standing_authorization": False,
        # What it does NOT authorize.
        "authorization_covers_final_test": False,
        "authorization_covers_final_test_unlock": False,
        "authorization_covers_new_retrieval": False,
        "authorization_covers_step_c_rerun": False,
        "authorization_covers_step_d_rerun": False,
        "authorization_covers_calendar_mapping_change": False,
        "authorization_covers_retuning": False,
        "authorization_covers_feature_search": False,
        "authorization_covers_new_scientific_design_choice": False,
        "authorization_covers_confirmatory_holm": False,
        "authorization_covers_paper_winner_selection": False,
        "authorization_covers_m4": False,
        "authorization_covers_ready_for_review": False,
        "authorization_covers_merge": False,
        # Prior grants stay historical and are never stretched to cover this.
        "prior_authorizations_reused": False,
        "prior_authorizations_not_reused": list(
            NON_REUSABLE_PRIOR_AUTHORIZATIONS),
    }


# --------------------------------------------------------------------------- #
# Frozen inputs this step executes AGAINST (re-read at run time; never edited)
# --------------------------------------------------------------------------- #

CONTRACT_REL = ("project/stage128/m3_lag_wdi_exploratory_contract_lock/"
                "stage128_m3_lag_wdi_exploratory_contract.json")
MODELING_CONTRACT_REL = (
    "project/stage128/m3_lag_wdi_exploratory_contract_lock/"
    "stage128_m3_lag_wdi_exploratory_modeling_contract.json")
GATE_DECISION_REL = ("project/stage128/m3_lag_wdi_exploratory_data_gate/"
                     "stage128_m3_lag_wdi_data_gate_decision.json")
GATE_REPORT_REL = ("project/stage128/m3_lag_wdi_exploratory_data_gate/"
                   "stage128_m3_lag_wdi_data_gate_report.json")
CALMAP_DECISION_REL = (
    "project/stage128/m3_lag_wdi_exploratory_calendar_mapping_lock/"
    "stage128_m3_lag_wdi_calendar_mapping_decision.json")
RETRIEVAL_MANIFEST_REL = (
    "project/stage128/m3_lag_wdi_exploratory_data_retrieval/"
    "stage128_m3_lag_wdi_retrieval_source_manifest.json")
STEP_C_DECISION_REL = (
    "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit/"
    "stage128_m3_lag_wdi_post_retrieval_audit_decision.json")

CPI_CODE = "FP.CPI.TOTL.ZG"
FX_CODE = "PA.NUS.FCRF"
CPI_FEATURE_ID = "intl_cpi_inflation_lag1_wdi"
FX_FEATURE_ID = "intl_fx_change_official_lag1_wdi"
LOCKED_COUNTRY_CODE = "IRN"

GATE_STATUS_PASS = "PASS_M3_LAG_WDI_DATA_GATE"

#: The locked Jalali-to-Gregorian mapping. It is a fail-closed EXPECTATION,
#: not a definition: the value actually applied is re-read from the committed
#: calendar-mapping lock at run time and must equal this.
LOCKED_CALENDAR_OFFSET = 621
LOCKED_CALENDAR_RULE = "jalali_fiscal_year_t_plus_621"
LOCKED_CALENDAR_FORMULA = "predictor_year_t = jalali_fiscal_year_t + 621"
REJECTED_CALENDAR_OFFSET = 622


# --------------------------------------------------------------------------- #
# Blocks — 12 versus 14, nested, in a frozen order
# --------------------------------------------------------------------------- #

#: The retained M2 comparator, imported unchanged: 9 M1 financial features
#: plus the 3 frozen market features.
M2_FEATURE_ORDER: list[str] = list(m2ie.M2_FEATURE_ORDER)

#: Exactly the two admitted WDI features, appended to the NESTED M2 set.
WDI_FEATURE_ORDER: list[str] = [CPI_FEATURE_ID, FX_FEATURE_ID]
M3_LAG_WDI_FEATURE_ORDER: list[str] = M2_FEATURE_ORDER + WDI_FEATURE_ORDER

EXPECTED_M2_FEATURE_COUNT = 12
EXPECTED_M3_LAG_WDI_FEATURE_COUNT = 14

BLOCKS = ("M2", "M3_LAG_WDI")

#: Inherited verbatim. This module selects nothing.
MODEL_FAMILIES: tuple[str, ...] = tuple(m2ie.MODEL_FAMILIES)
FROZEN_CONFIGURATIONS: dict[str, dict[str, Any]] = m2ie.FROZEN_CONFIGURATIONS
DETERMINISTIC_FAMILIES: tuple[str, ...] = tuple(m2ie.DETERMINISTIC_FAMILIES)
FINAL_OOF_SEEDS: tuple[int, ...] = tuple(m2ie.FINAL_OOF_SEEDS)
LOGISTIC_FIT_SEED = m2ie.LOGISTIC_FIT_SEED

#: 2 blocks x 2 folds x (1 logistic + 5 RF + 5 XGB) — the same architecture as
#: the retained M2 action, applied to a different second block.
EXPECTED_PRIMARY_FIT_COUNT = 44

#: Inherited metric and uncertainty machinery. Not redefined here.
PRIMARY_METRIC = m2ie.PRIMARY_METRIC
SECONDARY_METRICS: tuple[str, ...] = tuple(m2ie.SECONDARY_METRICS)
ALL_METRICS: tuple[str, ...] = tuple(m2ie.ALL_METRICS)
CALIBRATION_BINS = m2ie.CALIBRATION_BINS
BOOTSTRAP_METHOD = m2ie.BOOTSTRAP_METHOD
BOOTSTRAP_CLUSTER = m2ie.BOOTSTRAP_CLUSTER
BOOTSTRAP_REPLICATES = m2ie.BOOTSTRAP_REPLICATES
BOOTSTRAP_SEED = m2ie.BOOTSTRAP_SEED
BOOTSTRAP_CI = m2ie.BOOTSTRAP_CI
BOOTSTRAP_MIN_VALID_REPLICATES = m2ie.BOOTSTRAP_MIN_VALID_REPLICATES
FLOAT_ROUND = m2ie.FLOAT_ROUND

#: The exploratory family this comparison belongs to — and the confirmatory
#: family it must never enter.
EXPLORATORY_FAMILY_ID = "M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY"
EXPLORATORY_HYPOTHESIS_ID = "E1"
EXPLORATORY_COMPARISON = "M3_LAG_WDI_minus_retained_M2"
CONFIRMATORY_HOLM_FAMILY: tuple[str, ...] = (
    "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI")
RESULTS_LABEL = "supplementary_exploratory_robustness_only"
SCIENTIFIC_ROLE = "supplementary_exploratory_robustness_block"

#: Frozen sample expectations. Fail-closed checks; never used to relax loading.
EXPECTED_PARENT_ROWS = 539
EXPECTED_PARENT_POSITIVE = 55
EXPECTED_PARENT_NEGATIVE = 484
EXPECTED_PARENT_COMPANIES = 108
EXPECTED_POOLED_OOF_ROWS = 366
EXPECTED_POOLED_OOF_POSITIVE = 28
EXPECTED_VALIDATION_POSITIVES = {"fold1_validation": 18,
                                 "fold2_validation": 10}


def _round(x: float) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return x
    return round(float(x), FLOAT_ROUND)


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(root: Path, rel: str) -> Any:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# --------------------------------------------------------------------------- #
# Preconditions — every frozen rule re-read, never restated
# --------------------------------------------------------------------------- #

def verify_frozen_preconditions(root: Path) -> dict[str, Any]:
    """Fail closed unless the state step E believes it inherits is real.

    Re-reads the locked contract, the modeling contract, the step D Gate
    verdict and the calendar-mapping lock from committed bytes. If any of them
    disagrees with what this module executes, the step stops rather than
    proceeding under an assumption.
    """
    contract = _read_json(root, CONTRACT_REL)
    modeling = _read_json(root, MODELING_CONTRACT_REL)
    gate_decision = _read_json(root, GATE_DECISION_REL)
    calmap = _read_json(root, CALMAP_DECISION_REL)

    # ---- the two admitted features, unchanged -------------------------- #
    features = {f["feature_id"]: f for f in contract["features"]}
    if set(features) != {CPI_FEATURE_ID, FX_FEATURE_ID}:
        raise M3LagWdiEvaluationError(
            f"the locked contract carries features {sorted(features)}; step E "
            "may not add, substitute or search for a third macro feature")
    cpi, fx = features[CPI_FEATURE_ID], features[FX_FEATURE_ID]
    if cpi["indicator_code"] != CPI_CODE or fx["indicator_code"] != FX_CODE:
        raise M3LagWdiEvaluationError("locked indicator codes do not match")
    if cpi["required_observation_years"] != ["t-1"]:
        raise M3LagWdiEvaluationError("CPI must require exactly year t-1")
    if fx["required_observation_years"] != ["t-1", "t-2"]:
        raise M3LagWdiEvaluationError("FX must require years t-1 and t-2")
    if contract["imputation_permitted"] is not False:
        raise M3LagWdiEvaluationError("imputation is forbidden by the contract")
    if contract["complete_case_policy"][
            "both_lagged_wdi_features_required_complete"] is not True:
        raise M3LagWdiEvaluationError(
            "the contract requires BOTH features complete per row")

    # ---- the modeling contract step E is executing --------------------- #
    if modeling["modeling_action_id"] != ACTION_ID:
        raise M3LagWdiEvaluationError(
            "the locked modeling contract names a different modeling action")
    if modeling["primary_comparison"] != EXPLORATORY_COMPARISON:
        raise M3LagWdiEvaluationError("the primary comparison drifted")
    if modeling["comparison_family_id"] != EXPLORATORY_FAMILY_ID:
        raise M3LagWdiEvaluationError("the exploratory family id drifted")
    if list(modeling["model_families"]) != list(MODEL_FAMILIES):
        raise M3LagWdiEvaluationError("the frozen model families drifted")
    if list(modeling["confirmatory_holm_family"]) != list(
            CONFIRMATORY_HOLM_FAMILY):
        raise M3LagWdiEvaluationError("the confirmatory Holm family drifted")
    for field in ("retuning_permitted", "grid_search_permitted",
                  "hyperparameter_search_permitted",
                  "model_family_search_permitted",
                  "confirmatory_superiority_claim_permitted",
                  "exploratory_comparison_inserted_into_confirmatory_holm_"
                  "family", "gate_pass_authorizes_modeling"):
        if modeling.get(field) is not False:
            raise M3LagWdiEvaluationError(
                f"the locked modeling contract field {field} must be False")
    for field in ("inherits_locked_validation_architecture",
                  "inherits_canonical_metric_definitions",
                  "inherits_seed_policy",
                  "inherits_bootstrap_and_paired_comparison_machinery",
                  "retained_configurations_used_unchanged",
                  "modeling_requires_new_explicit_human_authorization"):
        if modeling.get(field) is not True:
            raise M3LagWdiEvaluationError(
                f"the locked modeling contract field {field} must be True")
    if modeling["results_label"] != RESULTS_LABEL:
        raise M3LagWdiEvaluationError("the frozen results label drifted")
    # SHAP is run only if the frozen contract explicitly requires it. It does
    # not, so there is no SHAP code path in this module at all.
    shap_required = bool(modeling.get("shap_required", False))
    if shap_required:
        raise M3LagWdiEvaluationError(
            "the frozen contract now requires SHAP, which this module does "
            "not implement; step E must stop rather than improvise one")

    # ---- step D admitted the data ------------------------------------- #
    if gate_decision["gate_result"] != GATE_STATUS_PASS:
        raise M3LagWdiEvaluationError(
            f"step D verdict is {gate_decision['gate_result']}; step E may "
            "only run on an admitted block")
    if gate_decision["admission_is_data_admission_only"] is not True:
        raise M3LagWdiEvaluationError(
            "the Gate PASS must stay a data-admission statement")
    if gate_decision["rows_excluded"] != 0:
        raise M3LagWdiEvaluationError("step D excluded rows; step E expects 0")

    # ---- the calendar mapping is locked, and locked to +621 ------------ #
    if calmap.get("calendar_mapping_locked") is not True:
        raise M3LagWdiEvaluationError("the calendar mapping is not locked")
    offset = calmap.get("calendar_mapping_locked_offset")
    if offset != LOCKED_CALENDAR_OFFSET:
        raise M3LagWdiEvaluationError(
            f"the locked calendar offset is {offset}, not "
            f"{LOCKED_CALENDAR_OFFSET}; step E may not change it")
    if calmap.get("calendar_mapping_rule") != LOCKED_CALENDAR_RULE:
        raise M3LagWdiEvaluationError("the locked calendar rule id drifted")
    if calmap.get("rejected_offset") != REJECTED_CALENDAR_OFFSET:
        raise M3LagWdiEvaluationError("the rejected calendar offset drifted")
    if calmap.get("locked_offset_timing_violation_rows") != 0:
        raise M3LagWdiEvaluationError(
            "the locked mapping no longer has zero timing violations")
    if not calmap.get("rejected_offset_timing_violation_rows", 0) > 0:
        raise M3LagWdiEvaluationError(
            "the rejected mapping no longer shows a timing violation, so the "
            "lock would rest on a justification its evidence contradicts")

    return {
        "contract_source": CONTRACT_REL,
        "contract_source_sha256": _sha256_file(root / CONTRACT_REL),
        "modeling_contract_source": MODELING_CONTRACT_REL,
        "modeling_contract_source_sha256":
            _sha256_file(root / MODELING_CONTRACT_REL),
        "gate_decision_source": GATE_DECISION_REL,
        "gate_decision_source_sha256": _sha256_file(root / GATE_DECISION_REL),
        "gate_result": gate_decision["gate_result"],
        "calendar_mapping_source": CALMAP_DECISION_REL,
        "calendar_mapping_source_sha256":
            _sha256_file(root / CALMAP_DECISION_REL),
        "calendar_mapping_rule": LOCKED_CALENDAR_RULE,
        "calendar_mapping_rule_formula": LOCKED_CALENDAR_FORMULA,
        "calendar_mapping_locked_offset": LOCKED_CALENDAR_OFFSET,
        "calendar_mapping_rejected_offset": REJECTED_CALENDAR_OFFSET,
        "calendar_mapping_changed_by_this_action": False,
        "cpi_observation_year_rule": "t-1",
        "fx_observation_year_rule": "t-1 and t-2",
        "same_year_t_observation_permitted": False,
        "imputation_permitted": False,
        "feature_substitution_permitted": False,
        "third_macro_feature_permitted": False,
        "shap_required_by_frozen_contract": False,
        "shap_executed": False,
        "thresholds_changed_by_this_action": False,
        "step_c_artifacts_modified": False,
        "step_d_artifacts_modified": False,
        "calendar_lock_artifacts_modified": False,
    }


def load_retained_values(root: Path, bundle_dir: str) -> dict[str, dict[int, Any]]:
    """Load both retained payloads, prove identity BYTE-FIRST, then decode.

    Identical to the step D loader in behaviour and intent: identity is proven
    against the committed retrieval manifest (anchored to the immutable Zenodo
    deposit) before any parsing. This step performs no network access of any
    kind and modifies no retained byte.
    """
    manifest = _read_json(root, RETRIEVAL_MANIFEST_REL)
    values: dict[str, dict[int, Any]] = {}
    for entry in manifest["indicators"]:
        code = entry["indicator_code"]
        path = os.path.join(bundle_dir, "raw", entry["raw_artifact_filename"])
        if not os.path.isfile(path):
            raise M3LagWdiEvaluationError(f"retained payload not found: {path}")
        blob = Path(path).read_bytes()
        if len(blob) != entry["raw_artifact_bytes"]:
            raise M3LagWdiEvaluationError(
                f"retained payload byte count mismatch for {code}")
        if _sha256_bytes(blob) != entry["raw_artifact_sha256"]:
            raise M3LagWdiEvaluationError(
                f"retained payload SHA-256 mismatch for {code}")
        document = json.loads(blob.decode("utf-8"))
        iso3 = sorted({row.get("countryiso3code") for row in document[1]})
        if iso3 != [LOCKED_COUNTRY_CODE]:
            raise M3LagWdiEvaluationError(
                f"{code}: payload carries country codes {iso3}")
        values[code] = {int(row["date"]): row.get("value")
                        for row in document[1]}
    if set(values) != {CPI_CODE, FX_CODE}:
        raise M3LagWdiEvaluationError(
            f"retained evidence carries indicators {sorted(values)}")
    return values


# --------------------------------------------------------------------------- #
# Feature-value materialization — permitted for the first time, only here
# --------------------------------------------------------------------------- #

def build_wdi_features(cpi_values: dict[int, Any], fx_values: dict[int, Any],
                       jalali_fiscal_year: int) -> dict[str, Any]:
    """The two locked features for one row, under the LOCKED mapping only.

    ``predictor_year_t = jalali_fiscal_year_t + 621``. CPI is the identity
    transformation of the ``t-1`` observation; FX is
    ``100 * ln(E_(t-1) / E_(t-2))``. No same-year ``t`` observation is read.
    A row that fails either null policy yields ``None`` — never an imputed
    value.
    """
    t = jalali_fiscal_year + LOCKED_CALENDAR_OFFSET
    cpi_obs = cpi_values.get(t - 1)
    cpi = float(cpi_obs) if _numeric(cpi_obs) else None

    e1, e2 = fx_values.get(t - 1), fx_values.get(t - 2)
    fx_ok = _numeric(e1) and _numeric(e2) and e1 > 0 and e2 > 0
    fx = 100.0 * math.log(float(e1) / float(e2)) if fx_ok else None

    return {
        "predictor_year_t": t,
        "cpi_observation_year": t - 1,
        "fx_observation_year_numerator": t - 1,
        "fx_observation_year_denominator": t - 2,
        "same_year_t_observation_used": False,
        CPI_FEATURE_ID: cpi,
        FX_FEATURE_ID: fx,
        "cpi_constructible": cpi is not None,
        "fx_constructible": fx is not None,
        "both_constructible": cpi is not None and fx is not None,
        "fx_zero_change": bool(fx_ok and e1 == e2),
    }


def build_step_e_sample(root: Path,
                        values: dict[str, dict[int, Any]]) -> dict[str, Any]:
    """Materialize the modeling feature table and the step-E common sample.

    The parent surface is the retained-M2 development common sample, built by
    the retained-M2 module itself (never hand-reproduced). The two WDI
    features are attached under the locked mapping and the frozen complete-case
    rule is applied. The resulting sample is the ONLY sample either block is
    evaluated on.
    """
    parent = m2ie.build_common_sample(root)
    common = parent["common"]
    if len(common) != EXPECTED_PARENT_ROWS:
        raise M3LagWdiEvaluationError(
            f"parent common sample {len(common)} != {EXPECTED_PARENT_ROWS}")

    cpi_values, fx_values = values[CPI_CODE], values[FX_CODE]
    for key, rec in common.items():
        if rec["target_year"] in m1.FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError(
                "a final-test target year reached the step E sample")
        feats = build_wdi_features(
            cpi_values, fx_values, int(rec["fiscal_year_t"]))
        rec.update(feats)

    # ---- the frozen complete-case rule; no imputation, no substitution -- #
    step_e = {k: v for k, v in common.items() if v["both_constructible"]}
    dropped = [k for k in common if k not in step_e]

    attrition = {
        "parent_rows": len(common),
        "step_e_rows": len(step_e),
        "dropped_rows": len(dropped),
        "dropped_by_incomplete_cpi": sum(
            1 for k in dropped if not common[k]["cpi_constructible"]),
        "dropped_by_incomplete_fx": sum(
            1 for k in dropped if not common[k]["fx_constructible"]),
        "imputation_used": False,
        "feature_substitution_used": False,
        "exclusions_outside_the_frozen_complete_case_rule": 0,
        "attrition_follows_mechanically_from_the_frozen_complete_case_rule":
            True,
    }
    # Step D admitted 539/539, so the frozen rule must drop nothing. Any drop
    # here would be a discrepancy against an already-audited Gate result, and
    # the contract says STOP rather than model a quietly different sample.
    if len(step_e) != EXPECTED_PARENT_ROWS:
        raise M3LagWdiEvaluationError(
            f"step E modeling sample is {len(step_e)} rows, but step D "
            f"admitted {EXPECTED_PARENT_ROWS}/{EXPECTED_PARENT_ROWS} on the "
            "same complete-case rule; this discrepancy must be reported to "
            "the human supervisor before any model is fit")

    pos = sum(1 for v in step_e.values() if v["target"] == 1.0)
    neg = sum(1 for v in step_e.values() if v["target"] == 0.0)
    companies = len({v["ticker"] for v in step_e.values()})
    if pos != EXPECTED_PARENT_POSITIVE or neg != EXPECTED_PARENT_NEGATIVE:
        raise M3LagWdiEvaluationError(
            f"step E composition {pos}/{neg} != {EXPECTED_PARENT_POSITIVE}/"
            f"{EXPECTED_PARENT_NEGATIVE}")
    if companies != EXPECTED_PARENT_COMPANIES:
        raise M3LagWdiEvaluationError(
            f"step E companies {companies} != {EXPECTED_PARENT_COMPANIES}")

    role_keys = {role: sorted(k for k, v in step_e.items()
                              if role in v["roles"])
                 for role in m1.DEV_ROLES}
    for role, expected in EXPECTED_VALIDATION_POSITIVES.items():
        got = sum(1 for k in role_keys[role] if step_e[k]["target"] == 1.0)
        if got != expected:
            raise M3LagWdiEvaluationError(
                f"step E {role} positives {got} != {expected}")
    pooled = sorted(role_keys["fold1_validation"]
                    + role_keys["fold2_validation"])
    if len(set(pooled)) != len(pooled):
        raise M3LagWdiEvaluationError("validation windows overlap")
    if len(pooled) != EXPECTED_POOLED_OOF_ROWS:
        raise M3LagWdiEvaluationError(
            f"pooled OOF rows {len(pooled)} != {EXPECTED_POOLED_OOF_ROWS}")
    pooled_pos = sum(1 for k in pooled if step_e[k]["target"] == 1.0)
    if pooled_pos != EXPECTED_POOLED_OOF_POSITIVE:
        raise M3LagWdiEvaluationError(
            f"pooled OOF positives {pooled_pos} != "
            f"{EXPECTED_POOLED_OOF_POSITIVE}")

    # ---- missingness AFTER construction, over both blocks --------------- #
    # Two different things are counted here and must not be conflated.
    #
    # The two NEW WDI features and the three market features carry a
    # complete-case requirement, so any missing value is a fail-closed error.
    #
    # The nine M1 financial features carry PRE-EXISTING missingness that the
    # retained architecture already handles inside the frozen preprocessor
    # (train-fold-only clip -> median impute, plus a missingness indicator per
    # feature). That is inherited behaviour, identical for both blocks and
    # untouched by this action — it is NOT an imputation introduced by step E,
    # and step E adds none of its own.
    missing: dict[str, int] = {}
    for feat in M3_LAG_WDI_FEATURE_ORDER:
        if feat in WDI_FEATURE_ORDER:
            missing[feat] = sum(1 for v in step_e.values() if v[feat] is None)
        elif feat in m2ie.M2_MARKET_FEATURE_ORDER:
            missing[feat] = sum(1 for v in step_e.values()
                                if math.isnan(v[feat]))
        else:
            idx = m2ie.M1_FEATURE_ORDER.index(feat)
            missing[feat] = sum(1 for v in step_e.values()
                                if math.isnan(float(v["m1_features"][idx])))

    complete_case_required = list(WDI_FEATURE_ORDER) + list(
        m2ie.M2_MARKET_FEATURE_ORDER)
    violated = {f: missing[f] for f in complete_case_required if missing[f]}
    if violated:
        raise M3LagWdiEvaluationError(
            f"complete-case features missing after construction: {violated}")

    missingness = {
        "new_wdi_features": {f: missing[f] for f in WDI_FEATURE_ORDER},
        "m2_market_features": {f: missing[f]
                               for f in m2ie.M2_MARKET_FEATURE_ORDER},
        "m1_financial_features": {f: missing[f]
                                  for f in m2ie.M1_FEATURE_ORDER},
        "complete_case_required_features": complete_case_required,
        "complete_case_violations": 0,
        "new_wdi_feature_missing_values": 0,
        "m1_pre_existing_missing_values": sum(
            missing[f] for f in m2ie.M1_FEATURE_ORDER),
        "m1_missingness_handled_by": (
            "the inherited frozen preprocessor: training-fold-only clip to "
            "the 1st/99th percentile, median imputation, and a per-feature "
            "missingness indicator column"),
        "m1_missingness_is_pre_existing_and_identical_for_both_blocks": True,
        "m1_missingness_introduced_by_this_action": False,
        "new_imputation_introduced_by_this_action": False,
    }

    years = sorted({v["predictor_year_t"] for v in step_e.values()})
    zero_fx = sum(1 for v in step_e.values() if v["fx_zero_change"])

    # Both features are national annual macro series, so within a predictor
    # year every company shares one value. The block therefore contributes at
    # most as many distinct values as there are predictor years — a structural
    # property of the design, recorded here so it cannot be discovered late.
    distinct = {feat: len({v[feat] for v in step_e.values()})
                for feat in WDI_FEATURE_ORDER}
    per_year = {
        str(year): {
            "rows": sum(1 for v in step_e.values()
                        if v["predictor_year_t"] == year),
            CPI_FEATURE_ID: _round(next(
                v[CPI_FEATURE_ID] for v in step_e.values()
                if v["predictor_year_t"] == year)),
            FX_FEATURE_ID: _round(next(
                v[FX_FEATURE_ID] for v in step_e.values()
                if v["predictor_year_t"] == year)),
        }
        for year in years
    }
    for feat, count in distinct.items():
        if count > len(years):
            raise M3LagWdiEvaluationError(
                f"{feat} takes {count} distinct values across {len(years)} "
                "predictor years; a national annual series cannot vary "
                "within a year")

    return {
        "parent": parent,
        "common": step_e,
        "role_keys": role_keys,
        "pooled_validation_keys": pooled,
        "attrition": attrition,
        "composition": {
            "rows": len(step_e),
            "positive": pos,
            "negative": neg,
            "companies": companies,
            "event_rate": _round(pos / len(step_e)),
            "pooled_oof_rows": len(pooled),
            "pooled_oof_positive": pooled_pos,
            "fold_counts": {r: len(k) for r, k in role_keys.items()},
            "validation_positives": {
                r: sum(1 for k in role_keys[r] if step_e[k]["target"] == 1.0)
                for r in EXPECTED_VALIDATION_POSITIVES},
        },
        "missingness_after_construction": missingness,
        "predictor_year_first": years[0],
        "predictor_year_last": years[-1],
        "predictor_years": years,
        "distinct_predictor_years": len(years),
        # Observation-year semantics, stated separately per feature so the
        # binding t-1 rule is never confused with the FX denominator year.
        "cpi_observation_year_rule": "t-1",
        "cpi_observation_year_first": years[0] - 1,
        "cpi_observation_year_last": years[-1] - 1,
        "fx_observation_year_rule": "t-1 (numerator) and t-2 (denominator)",
        "fx_observation_year_numerator_first": years[0] - 1,
        "fx_observation_year_numerator_last": years[-1] - 1,
        "fx_observation_year_denominator_first": years[0] - 2,
        "fx_observation_year_denominator_last": years[-1] - 2,
        "earliest_observation_year_touched": years[0] - 2,
        "latest_observation_year_touched": years[-1] - 1,
        "same_year_t_observations_read": 0,
        "wdi_distinct_values": distinct,
        "wdi_values_by_predictor_year": per_year,
        "wdi_features_are_constant_within_a_predictor_year": True,
        "fx_zero_change_rows": zero_fx,
        "identical_sample_for_both_blocks": True,
        "final_test_rows_in_sample": 0,
    }


def feature_value_rows(sample: dict[str, Any]) -> list[dict[str, Any]]:
    """The committed modeling feature-value table, one row per sample row."""
    out: list[dict[str, Any]] = []
    for key in sorted(sample["common"]):
        rec = sample["common"][key]
        row = {
            "ticker": rec["ticker"],
            "fiscal_year_t": rec["fiscal_year_t"],
            "target_year": rec["target_year"],
            "temporal_folds": ",".join(sorted(rec["roles"])),
            "target": int(rec["target"]),
            "predictor_year_t": rec["predictor_year_t"],
            "cpi_observation_year": rec["cpi_observation_year"],
            "fx_observation_year_numerator":
                rec["fx_observation_year_numerator"],
            "fx_observation_year_denominator":
                rec["fx_observation_year_denominator"],
            CPI_FEATURE_ID: _round(rec[CPI_FEATURE_ID]),
            FX_FEATURE_ID: _round(rec[FX_FEATURE_ID]),
            "fx_zero_change": rec["fx_zero_change"],
        }
        out.append(row)
    return out


FEATURE_VALUE_COLUMNS: tuple[str, ...] = (
    "ticker", "fiscal_year_t", "target_year", "temporal_folds", "target",
    "predictor_year_t", "cpi_observation_year",
    "fx_observation_year_numerator", "fx_observation_year_denominator",
    CPI_FEATURE_ID, FX_FEATURE_ID, "fx_zero_change",
)


# --------------------------------------------------------------------------- #
# Paired evaluation — the inherited architecture, a different second block
# --------------------------------------------------------------------------- #

def _block_matrix(common: dict[Any, dict[str, Any]], keys: list[Any],
                  block: str) -> np.ndarray:
    if block == "M2":
        return np.vstack([
            np.concatenate([
                common[k]["m1_features"],
                np.array([common[k][f]
                          for f in m2ie.M2_MARKET_FEATURE_ORDER], dtype=float),
            ]) for k in keys])
    if block == "M3_LAG_WDI":
        return np.vstack([
            np.concatenate([
                common[k]["m1_features"],
                np.array([common[k][f]
                          for f in m2ie.M2_MARKET_FEATURE_ORDER], dtype=float),
                np.array([common[k][f] for f in WDI_FEATURE_ORDER],
                         dtype=float),
            ]) for k in keys])
    raise M3LagWdiEvaluationError(f"unknown block {block}")


def _targets(common, keys) -> np.ndarray:
    return np.array([common[k]["target"] for k in keys], dtype=float)


def run_paired_evaluation(sample: dict[str, Any]) -> dict[str, Any]:
    """Refit BOTH blocks on identical rows; predict on identical rows.

    Preprocessing parameters come only from the training fold of the fold
    being fit, exactly as in the retained architecture. Nothing about the
    procedure depends on the observed WDI values.
    """
    common = sample["common"]
    role_keys = sample["role_keys"]
    fit_log: list[dict[str, Any]] = []
    predictions: dict[tuple[str, Any], dict[str, Any]] = {}

    for fold, spec in m1.FOLD_SPEC.items():
        tr_keys = role_keys[spec["train_role"]]
        va_keys = role_keys[spec["validation_role"]]
        if set(tr_keys) & set(va_keys):
            raise M3LagWdiEvaluationError(f"{fold}: train/validation overlap")
        ytr = _targets(common, tr_keys)
        yva = _targets(common, va_keys)
        if np.isnan(ytr).any() or np.isnan(yva).any():
            raise M3LagWdiEvaluationError(f"{fold}: missing target")

        for family in MODEL_FAMILIES:
            cfg = FROZEN_CONFIGURATIONS[family]
            hp = cfg["hyperparameters"]
            standardize = m1._requires_standardization(family)
            seeds = ((LOGISTIC_FIT_SEED,) if family in DETERMINISTIC_FAMILIES
                     else FINAL_OOF_SEEDS)
            per_block: dict[str, np.ndarray] = {}
            for block in BLOCKS:
                Xtr_raw = _block_matrix(common, tr_keys, block)
                Xva_raw = _block_matrix(common, va_keys, block)
                pre = m1.fit_preprocessor(Xtr_raw, standardize=standardize)
                Xtr = m1.transform(Xtr_raw, pre)
                Xva = m1.transform(Xva_raw, pre)
                probs = []
                for seed in seeds:
                    p = m1._fit_predict(family, hp, seed, Xtr, ytr, Xva)
                    probs.append(np.asarray(p, dtype=float))
                    fit_log.append({
                        "block": block, "fold": fold, "family": family,
                        "configuration_id": cfg["configuration_id"],
                        "seed": seed,
                        "feature_count": Xtr_raw.shape[1],
                        "train_rows": len(tr_keys),
                        "train_positive": int((ytr == 1).sum()),
                        "train_negative": int((ytr == 0).sum()),
                    })
                per_block[block] = np.mean(np.vstack(probs), axis=0)
            for i, key in enumerate(va_keys):
                rec = common[key]
                predictions[(family, key)] = {
                    "model_family": family,
                    "configuration_id": cfg["configuration_id"],
                    "temporal_fold": spec["validation_role"],
                    "ticker": rec["ticker"],
                    "fiscal_year_t": rec["fiscal_year_t"],
                    "target_year": rec["target_year"],
                    "predictor_year_t": rec["predictor_year_t"],
                    "target": int(rec["target"]),
                    "m2_probability": float(per_block["M2"][i]),
                    "m3_lag_wdi_probability": float(
                        per_block["M3_LAG_WDI"][i]),
                    "m3_lag_wdi_minus_m2_probability": float(
                        per_block["M3_LAG_WDI"][i] - per_block["M2"][i]),
                    "seed_aggregation": (
                        "deterministic_single_fit"
                        if family in DETERMINISTIC_FAMILIES
                        else "mean_of_5_frozen_final_oof_seeds"),
                }

    if len(fit_log) != EXPECTED_PRIMARY_FIT_COUNT:
        raise M3LagWdiEvaluationError(
            f"primary predictive fit count {len(fit_log)} != "
            f"{EXPECTED_PRIMARY_FIT_COUNT}")
    for entry in fit_log:
        expected = (EXPECTED_M2_FEATURE_COUNT if entry["block"] == "M2"
                    else EXPECTED_M3_LAG_WDI_FEATURE_COUNT)
        if entry["feature_count"] != expected:
            raise M3LagWdiEvaluationError(
                f"{entry['block']} was fit on {entry['feature_count']} "
                f"features, not {expected}")
    return {"fit_log": fit_log, "predictions": predictions}


def oof_rows(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(evaluation["predictions"].values())
    rows.sort(key=lambda r: (r["model_family"], r["temporal_fold"],
                             r["ticker"], r["fiscal_year_t"]))
    return rows


OOF_COLUMNS: tuple[str, ...] = (
    "model_family", "configuration_id", "temporal_fold", "ticker",
    "fiscal_year_t", "target_year", "predictor_year_t", "target",
    "m2_probability", "m3_lag_wdi_probability",
    "m3_lag_wdi_minus_m2_probability", "seed_aggregation",
)

METRICS_COLUMNS: tuple[str, ...] = (
    ("model_family", "configuration_id", "scope", "block", "n_rows",
     "n_positive", "k_top10") + ALL_METRICS)


# --------------------------------------------------------------------------- #
# Metrics — the inherited canonical definitions, unchanged
# --------------------------------------------------------------------------- #

def _metrics_for(rows: list[dict[str, Any]], prob_key: str) -> dict[str, Any]:
    return m1.compute_metrics(
        np.array([r["target"] for r in rows], dtype=float),
        np.array([r[prob_key] for r in rows], dtype=float),
        [r["ticker"] for r in rows],
        [r["target_year"] for r in rows])


def build_metrics_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        fam_rows = [r for r in rows if r["model_family"] == family]
        cfg = FROZEN_CONFIGURATIONS[family]["configuration_id"]
        scopes: list[tuple[str, list[dict[str, Any]]]] = [
            ("pooled_oof", fam_rows)]
        for role in ("fold1_validation", "fold2_validation"):
            scopes.append(
                (role, [r for r in fam_rows if r["temporal_fold"] == role]))
        for scope, subset in scopes:
            if not subset:
                continue
            m2m = _metrics_for(subset, "m2_probability")
            m3m = _metrics_for(subset, "m3_lag_wdi_probability")
            for block, mets in (("M2", m2m), ("M3_LAG_WDI", m3m)):
                out.append({"model_family": family, "configuration_id": cfg,
                            "scope": scope, "block": block, **mets})
            out.append({
                "model_family": family, "configuration_id": cfg,
                "scope": scope, "block": "M3_LAG_WDI_minus_M2",
                "n_rows": m2m["n_rows"], "n_positive": m2m["n_positive"],
                "k_top10": m2m["k_top10"],
                **{k: _round(m3m[k] - m2m[k]) for k in ALL_METRICS},
            })
    return out


def build_calibration_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calibration under the inherited raw-probability surface.

    No recalibration of any kind is executed; the primary surface is the raw
    locked-pipeline probability, exactly as in the retained architecture.
    """
    from sklearn.metrics import brier_score_loss
    out: dict[str, Any] = {
        "probability_surface": "raw_locked_pipeline_probabilities",
        "primary_probabilities_are_raw": True,
        "isotonic_calibration_allowed": m2ie.ISOTONIC_CALIBRATION_ALLOWED,
        "isotonic_calibration_executed": False,
        "platt_recalibration_executed": False,
        "recalibrated_probabilities_used_as_primary_surface": False,
        "recalibration_influenced_conclusion": False,
        "bins": CALIBRATION_BINS,
        "by_family": {},
    }
    for family in MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        y = np.array([r["target"] for r in fam], dtype=float)
        entry = {}
        for block, key in (("M2", "m2_probability"),
                           ("M3_LAG_WDI", "m3_lag_wdi_probability")):
            p = np.array([r[key] for r in fam], dtype=float)
            entry[block] = {
                "n_rows": int(y.size),
                "n_positive": int(y.sum()),
                "brier_score": _round(float(brier_score_loss(y, p))),
                "calibration_curve_quantile_bins": m2ie._calibration_curve(
                    y, p, CALIBRATION_BINS),
                **m2ie._calibration_fit(y, p),
            }
        out["by_family"][family] = entry
    return out


# --------------------------------------------------------------------------- #
# Paired company-cluster bootstrap — the inherited machinery
# --------------------------------------------------------------------------- #

def run_paired_bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Same resampled companies and rows for BOTH blocks in every replicate.

    Seed, replicate count, cluster, interval type and validity floor are all
    inherited constants. Models are not refit inside the bootstrap.
    """
    summary: dict[str, Any] = {
        "method": BOOTSTRAP_METHOD,
        "cluster": BOOTSTRAP_CLUSTER,
        "replicates_attempted": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "seed_changed_after_seeing_results": False,
        "confidence_interval": BOOTSTRAP_CI,
        "interval_type": "percentile",
        "minimum_valid_replicates": BOOTSTRAP_MIN_VALID_REPLICATES,
        "valid_replicate_requires_both_classes": True,
        "same_resampled_rows_for_both_blocks": True,
        "models_refit_during_bootstrap": False,
        "primary_metric": PRIMARY_METRIC,
        "comparison": EXPLORATORY_COMPARISON,
        "family": EXPLORATORY_FAMILY_ID,
        "by_family": {},
    }
    for family in MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        tickers = sorted({r["ticker"] for r in fam})
        by_ticker: dict[str, list[int]] = {t: [] for t in tickers}
        for i, r in enumerate(fam):
            by_ticker[r["ticker"]].append(i)
        y_all = np.array([r["target"] for r in fam], dtype=float)
        p2_all = np.array([r["m2_probability"] for r in fam], dtype=float)
        p3_all = np.array([r["m3_lag_wdi_probability"] for r in fam],
                          dtype=float)
        tick_all = [r["ticker"] for r in fam]
        year_all = [r["target_year"] for r in fam]

        rng = np.random.default_rng(BOOTSTRAP_SEED)
        deltas: dict[str, list[float]] = {m: [] for m in ALL_METRICS}
        valid = 0
        for _ in range(BOOTSTRAP_REPLICATES):
            picked = rng.integers(0, len(tickers), size=len(tickers))
            idx: list[int] = []
            for j in picked:
                idx.extend(by_ticker[tickers[int(j)]])
            y = y_all[idx]
            if len(set(y.tolist())) < 2:
                continue
            p2, p3 = p2_all[idx], p3_all[idx]
            tk = [tick_all[i] for i in idx]
            yr = [year_all[i] for i in idx]
            ok = True
            rep: dict[str, float] = {}
            for metric in ALL_METRICS:
                a = m2ie._metric_value(y, p2, tk, yr, metric)
                b = m2ie._metric_value(y, p3, tk, yr, metric)
                if math.isnan(a) or math.isnan(b):
                    ok = False
                    break
                rep[metric] = b - a
            if not ok:
                continue
            valid += 1
            for metric, v in rep.items():
                deltas[metric].append(v)

        point: dict[str, Any] = {}
        for metric in ALL_METRICS:
            a = m2ie._metric_value(y_all, p2_all, tick_all, year_all, metric)
            b = m2ie._metric_value(y_all, p3_all, tick_all, year_all, metric)
            arr = np.array(deltas[metric], dtype=float)
            enough = valid >= BOOTSTRAP_MIN_VALID_REPLICATES and arr.size > 0
            lo = float(np.percentile(arr, 2.5)) if enough else None
            hi = float(np.percentile(arr, 97.5)) if enough else None
            point[metric] = {
                "m2_estimate": _round(a),
                "m3_lag_wdi_estimate": _round(b),
                "m3_lag_wdi_minus_m2_delta": _round(b - a),
                "ci_lower": _round(lo) if lo is not None else None,
                "ci_upper": _round(hi) if hi is not None else None,
                "ci_estimable": bool(enough),
                "ci_excludes_zero": bool(enough and ((lo > 0) or (hi < 0))),
                "bootstrap_delta_replicates": int(arr.size),
            }
        summary["by_family"][family] = {
            "configuration_id": FROZEN_CONFIGURATIONS[family][
                "configuration_id"],
            "clusters": len(tickers),
            "rows": len(fam),
            "valid_replicates": valid,
            "valid_replicate_fraction": _round(valid / BOOTSTRAP_REPLICATES),
            "minimum_valid_replicates_met":
                valid >= BOOTSTRAP_MIN_VALID_REPLICATES,
            "metrics": point,
        }
    return summary


def _direction(delta: float, lo: Any, hi: Any) -> str:
    """The inherited direction vocabulary, applied to an exploratory delta."""
    if lo is None or hi is None:
        return "uncertainty_not_estimable"
    if lo > 0:
        return "positive_interval_excludes_zero"
    if hi < 0:
        return "negative_interval_excludes_zero"
    return "approximately_null_interval_includes_zero"


# --------------------------------------------------------------------------- #
# Multiplicity — a SEPARATE family; the confirmatory one is untouched
# --------------------------------------------------------------------------- #

def build_multiplicity_record() -> dict[str, Any]:
    """E1 lives in its own exploratory family and nowhere else.

    No Holm adjustment is executed here, for either family: the confirmatory
    family is not this action's to run, and a one-member exploratory family
    has nothing to adjust.
    """
    return {
        "exploratory_family_id": EXPLORATORY_FAMILY_ID,
        "exploratory_family_members": [EXPLORATORY_HYPOTHESIS_ID],
        "exploratory_family_size": 1,
        "exploratory_hypothesis_id": EXPLORATORY_HYPOTHESIS_ID,
        "exploratory_comparison": EXPLORATORY_COMPARISON,
        "exploratory_family_holm_adjusted": False,
        "exploratory_family_holm_adjustment_reason": (
            "a single-member exploratory family has no multiplicity to "
            "adjust, and adjusting it would not make it confirmatory"),
        "confirmatory_holm_family": list(CONFIRMATORY_HOLM_FAMILY),
        "confirmatory_holm_family_size": len(CONFIRMATORY_HOLM_FAMILY),
        "confirmatory_holm_family_changed_by_this_action": False,
        "confirmatory_holm_executed_by_this_action": False,
        "confirmatory_holm_modified_by_this_action": False,
        "exploratory_comparison_inserted_into_confirmatory_family": False,
        "e1_is_confirmatory": False,
        "confirmatory_superiority_claim_made": False,
        "results_label": RESULTS_LABEL,
        "paper_winner_selected_by_this_action": False,
        "main_confirmatory_conclusion_changed_by_this_action": False,
    }


# --------------------------------------------------------------------------- #
# Firewall
# --------------------------------------------------------------------------- #

def build_firewall_audit(sample: dict[str, Any]) -> dict[str, Any]:
    """The Final Test was never opened. Counted, not asserted."""
    parent = sample["parent"]
    for rec in sample["common"].values():
        if rec["target_year"] in m1.FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError("final-test row in the step E sample")
    return {
        "final_test_target_years": list(m1.FINAL_TEST_TARGET_YEARS),
        "final_test_locked": True,
        "final_test_unlocked_by_this_action": False,
        "final_test_rows_read": 0,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "final_test_rows_evaluated": 0,
        "final_test_predictions": 0,
        "final_test_metrics_computed": 0,
        "final_test_rows_structurally_encountered_and_skipped":
            parent["join_audit"]["final_test_rows_seen_and_skipped"],
        "final_test_rows_in_step_e_sample": 0,
        "development_only": True,
        "firewall_intact": True,
    }


def build_execution_audit(fit_log: list[dict[str, Any]],
                          sample: dict[str, Any]) -> dict[str, Any]:
    """What this action did, and the long list of what it did not."""
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "modeling_executed": True,
        "modeling_executions": 1,
        "feature_value_tables_materialized": 1,
        "feature_values_computed": 2 * sample["composition"]["rows"],
        "company_rows_touched": sample["composition"]["rows"],
        "model_fits": len(fit_log),
        "m2_model_fits": sum(1 for f in fit_log if f["block"] == "M2"),
        "m3_lag_wdi_model_fits": sum(
            1 for f in fit_log if f["block"] == "M3_LAG_WDI"),
        "predictions": sample["composition"]["pooled_oof_rows"] * len(
            MODEL_FAMILIES) * len(BLOCKS),
        "bootstrap_executions": len(MODEL_FAMILIES),
        "paired_comparisons": len(MODEL_FAMILIES),
        # Everything this action was forbidden to do, counted at zero.
        "world_bank_api_requests": 0,
        "new_payloads_retrieved": 0,
        "alternative_indicators_searched": 0,
        "alternative_indicators_retrieved": 0,
        "step_c_reruns": 0,
        "step_d_reruns": 0,
        "data_gate_executions": 0,
        "calendar_mapping_lock_reruns": 0,
        "calendar_mapping_changes": 0,
        "third_macro_features_added": 0,
        "feature_searches": 0,
        "feature_selections": 0,
        "feature_substitutions": 0,
        "imputations": 0,
        "rows_excluded_outside_frozen_complete_case_rule": 0,
        "tuning_runs": 0,
        "grid_searches": 0,
        "hyperparameter_searches": 0,
        "model_family_searches": 0,
        "model_selections": 0,
        "metric_definitions_created": 0,
        "metric_definitions_changed": 0,
        "validation_windows_changed": 0,
        "thresholds_changed": 0,
        "seed_policy_changes": 0,
        "shap_executions": 0,
        "holm_calculations": 0,
        "confirmatory_holm_executions": 0,
        "confirmatory_family_modifications": 0,
        "paper_winner_selections": 0,
        "final_test_rows_read": 0,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "final_test_unlocks": 0,
        "m4_actions": 0,
        "pr_ready_for_review_transitions": 0,
        "pr_merges": 0,
        # Upstream artifacts left byte-identical.
        "retained_bytes_modified": False,
        "deposited_evidence_modified": False,
        "step_c_artifacts_modified": False,
        "step_d_artifacts_modified": False,
        "calendar_lock_artifacts_modified": False,
        "authoritative_contract_edited": False,
        "confirmatory_holm_state_modified": False,
    }


# --------------------------------------------------------------------------- #
# Provenance of the ONE authorized scientific execution
# --------------------------------------------------------------------------- #

def execution_environment(*, scientific: bool) -> dict[str, Any]:
    """Environment record. A ``--check`` rebuild is explicitly not scientific."""
    return {
        "role": ("original_authorized_scientific_execution" if scientific
                 else "verification_or_maintenance_regeneration_only"),
        "scientific_execution": bool(scientific),
        "new_scientific_decision": bool(scientific),
        "new_human_authorization": False,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "runtime_versions": m1.runtime_versions(),
    }


EXECUTION_COUNT_SEMANTICS = {
    "canonical_authorized_scientific_executions": 1,
    "scientific_decisions": 0,
    "canonical_primary_predictive_fits_in_that_execution":
        EXPECTED_PRIMARY_FIT_COUNT,
    "note": (
        "44 is the CANONICAL SCIENTIFIC fit count of the single authorized "
        "execution of this action. `--check` and the test suite "
        "deterministically RECOMPUTE the same models to verify the committed "
        "artifacts; those recomputations are verification, not new scientific "
        "executions, they consume no new human authorization and they never "
        "change the canonical counts. This action makes NO new scientific "
        "design decision at all: every rule it applies was frozen before it "
        "ran."),
    "deterministic_verification_recomputation_is_not_a_new_execution": True,
    "verification_recomputation_changes_canonical_counts": False,
}


# --------------------------------------------------------------------------- #
# The limitations that survive whatever the numbers say
# --------------------------------------------------------------------------- #

def build_limitations(sample: dict[str, Any]) -> list[dict[str, Any]]:
    """Limitations a favourable predictive result does not erase.

    Each is stated with what it does and does not bind, so that neither a
    positive nor a negative E1 result can be read as having resolved it.
    """
    return [
        {
            "id": "point_in_time_wdi_availability_unproven",
            "statement": (
                "The retained WDI values are the CURRENT/REVISED series. WDI "
                "`lastupdated` is a revision marker, not evidence of what was "
                "published at any past date, so historical point-in-time "
                "availability remains UNPROVEN."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "lagging_does_not_create_point_in_time_data",
            "statement": (
                "The one-year lag is a conservative temporal-separation "
                "design only. Lagging a revised series does not convert it "
                "into point-in-time data, and the locked +621 calendar "
                "mapping does not either."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "fx_degenerate_2021_2024",
            "statement": (
                "The FX log-ratio is defined but identically ZERO for "
                "predictor years 2021-2024, because the official rate is "
                "pegged at 42000 across the 2019-2023 observations. Under the "
                "locked mapping the development sample spans predictor years "
                f"{sample['predictor_year_first']}-"
                f"{sample['predictor_year_last']}, so "
                f"{sample['fx_zero_change_rows']} of "
                f"{sample['composition']['rows']} rows are zero-change here — "
                "the degeneracy binds any extension of the block, not this "
                "evaluation."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "fx_missing_2024_2025",
            "statement": (
                "PA.NUS.FCRF carries no value for observation years "
                "2024-2025, capping the jointly constructible predictor-year "
                "ceiling at 2024. This does not bind the development sample "
                "but caps any future extension of the block."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "exploratory_role_is_frozen",
            "statement": (
                "The block's role is frozen as "
                f"`{SCIENTIFIC_ROLE}`. It is not confirmatory M3, not a "
                "replacement for or repair of M3-CBI, not a replacement for "
                "M3I-2, not historical-vintage or real-time WDI, not part of "
                "the confirmatory Holm family, and not independently capable "
                "of selecting the paper winner."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "macro_features_are_year_level_not_company_level",
            "statement": (
                "Both features are NATIONAL annual series, so within a "
                "predictor year every company carries the same value: across "
                f"the {sample['composition']['rows']} rows they take only "
                f"{sample['wdi_distinct_values'][CPI_FEATURE_ID]} and "
                f"{sample['wdi_distinct_values'][FX_FEATURE_ID]} distinct "
                f"values respectively, one per predictor year "
                f"{sample['predictor_year_first']}-"
                f"{sample['predictor_year_last']}. Because the temporal folds "
                "make training and validation years DISJOINT by construction, "
                "every value the block sees in a validation window is one it "
                "never saw in training. The block can therefore shift or "
                "rescale predictions within a validation year but cannot "
                "contribute company-level discrimination inside it, which is "
                "what the ranking metrics measure. This is a structural "
                "property of the design, not an artefact of the observed "
                "result, and it constrains the interpretation of E1 in either "
                "direction."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
        {
            "id": "two_validation_windows_few_positives",
            "statement": (
                "The paired comparison rests on "
                f"{sample['composition']['pooled_oof_rows']} pooled "
                f"out-of-fold rows carrying "
                f"{sample['composition']['pooled_oof_positive']} positives "
                "across two temporal windows. Interval width, not point "
                "estimates, is the honest summary at this event count."),
            "resolved_by_this_action": False,
            "erased_by_a_favourable_predictive_result": False,
        },
    ]
