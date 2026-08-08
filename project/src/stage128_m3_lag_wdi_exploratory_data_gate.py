"""Stage128 — Track B step D: the M3-LAG-WDI EXPLORATORY DATA GATE.

Authorized action: ``stage128-m3-lag-wdi-exploratory-data-gate``
Authorized scope:  ``data_gate_only``

Step C decoded the retained evidence and characterised the two SERIES. This
step — under its own new, single-use human authorization — is the first and
only action permitted to bring those series to the SAMPLE: it computes, for
every row of the retained-M2 development common sample, whether the two
contract-locked lagged WDI features are constructible, compares the resulting
coverage to the PRE-EXISTING inherited thresholds, and records the formal
data-admission verdict.

It does not answer, and may not answer:

* whether the block improves prediction            (step E, modeling — never
  authorized by a Gate PASS)
* whether the FX feature is scientifically informative in every year (a Gate
  PASS is a coverage statement, never an information-content claim)
* anything about the Final Test                    (locked; 0 rows read)

The Gate is executed under the ALREADY-LOCKED contract
(``stage128_m3_lag_wdi_exploratory_contract_lock``) and its inherited
thresholds. Nothing here invents, relaxes, tightens or reinterprets a
criterion, and every threshold is re-read from the locked contract at run time
so drift fails closed.

The unlocked calendar-mapping detail
------------------------------------
The locked contract indexes both features by a GREGORIAN predictor year
``t`` (worked example: ``t = 2019`` uses the 2018 CPI observation), but the
development rows are keyed by a JALALI fiscal year, and the contract does not
lock the Jalali-to-Gregorian mapping for ``predictor_year_t``. A Jalali year
spans exactly two Gregorian years, so any faithful convention must assign a
row's predictor year to one of the two: the Gregorian year in which the Jalali
year BEGINS (``jalali + 621``) or the one in which it ENDS (``jalali + 622``).

This Gate refuses to invent the missing convention. Instead it computes every
row-level constructibility status under BOTH admissible conventions and
requires them to be IDENTICAL: only then is the coverage — and therefore the
verdict — well-defined despite the unlocked mapping. If any row's status
differed between the conventions, the Gate would return UNRESOLVED rather than
pick the convention that flatters coverage. Feature VALUES do differ between
the conventions, which is exactly why this Gate materializes row STATUSES
only, never an authoritative feature-value table: the mapping must be locked
by a human before any value-level modeling table may exist.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-gate"
AUTHORIZED_SCOPE = "data_gate_only"
PACKAGE_ID = "stage128_m3_lag_wdi_exploratory_data_gate"
PACKAGE_REL = "project/stage128/m3_lag_wdi_exploratory_data_gate"

#: The locked contracts and audited evidence this Gate executes against. The
#: Gate defines nothing itself: it re-reads all of these and fails closed on
#: any disagreement.
CONTRACT_REL = ("project/stage128/m3_lag_wdi_exploratory_contract_lock/"
                "stage128_m3_lag_wdi_exploratory_contract.json")
GATE_CONTRACT_REL = ("project/stage128/m3_lag_wdi_exploratory_contract_lock/"
                     "stage128_m3_lag_wdi_exploratory_data_gate_contract.json")
THRESHOLD_ANCESTOR_REL = (
    "project/stage128/m3_intl_macro_contract_lock/"
    "stage128_m3_intl_macro_data_gate_contract.json")
RETRIEVAL_MANIFEST_REL = (
    "project/stage128/m3_lag_wdi_exploratory_data_retrieval/"
    "stage128_m3_lag_wdi_retrieval_source_manifest.json")
STEP_C_REPORT_REL = (
    "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit/"
    "stage128_m3_lag_wdi_post_retrieval_audit_report.json")
STEP_C_DECISION_REL = (
    "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit/"
    "stage128_m3_lag_wdi_post_retrieval_audit_decision.json")
D2_FEATURES_REL = "project/stage128/stage128_m2_d2_development_features.csv"
M2_JOIN_AUDIT_REL = ("project/stage128/m2_incremental_evaluation/"
                     "stage127_m2_common_sample_join_audit.json")
M2_ATTRITION_REL = ("project/stage128/m2_incremental_evaluation/"
                    "stage127_m2_parent_to_common_sample_attrition_audit.json")
M2_OOF_PREDICTIONS_REL = ("project/stage128/m2_incremental_evaluation/"
                          "stage127_m2_paired_oof_predictions.csv")

#: The NEW single-use human authorization for THIS step, verbatim opening
#: lines of the human supervisor's Step D authorization message, pinned by
#: byte length and digest. It is distinct from the contract-lock, retrieval
#: and step C authorizations, all of which stay historical, consumed and
#: never stretched to cover step D.
HUMAN_AUTHORIZATION_TEXT = (
    "HUMAN AUTHORIZATION — STAGE128 M3-LAG-WDI STEP D / DATA GATE ONLY\n"
    "\n"
    "I explicitly authorize execution of:\n"
    "\n"
    "stage128-m3-lag-wdi-exploratory-data-gate"
)

CPI_CODE = "FP.CPI.TOTL.ZG"
FX_CODE = "PA.NUS.FCRF"
CPI_FEATURE_ID = "intl_cpi_inflation_lag1_wdi"
FX_FEATURE_ID = "intl_fx_change_official_lag1_wdi"
LOCKED_COUNTRY_CODE = "IRN"

#: The two admissible Jalali-to-Gregorian offsets for ``predictor_year_t``.
#: A Jalali year begins in Gregorian ``jalali + 621`` and ends in
#: ``jalali + 622``; the locked contract does not choose between them, and
#: this Gate never does either — it requires the verdict to be identical
#: under both.
JALALI_TO_GREGORIAN_OFFSETS: tuple[int, ...] = (621, 622)

#: Locked development / final-test partition (Jalali target years).
DEVELOPMENT_TARGET_YEARS: tuple[str, ...] = (
    "1393", "1394", "1395", "1396", "1397", "1398", "1399")
FINAL_TEST_TARGET_YEARS: tuple[str, ...] = ("1400", "1401", "1402")

#: Locked temporal validation windows (Jalali target years), inherited from
#: the retained-M2 evaluation architecture.
LOCKED_VALIDATION_WINDOWS: dict[str, tuple[str, ...]] = {
    "fold1_validation": ("1396", "1397"),
    "fold2_validation": ("1398", "1399"),
}

EXPECTED_PARENT_ROWS = 539
EXPECTED_PARENT_POSITIVE = 55
EXPECTED_PARENT_NEGATIVE = 484
EXPECTED_PARENT_COMPANIES = 108

#: Gate outcome vocabulary. A PASS is DATA ADMISSION ONLY; it is not modeling
#: authorization, not an information-content claim and not a Final Test
#: unlock.
GATE_STATUS_PASS = "PASS_M3_LAG_WDI_DATA_GATE"
GATE_STATUS_FAIL = "FAIL_M3_LAG_WDI_DATA_GATE"
GATE_STATUS_UNRESOLVED = "UNRESOLVED_M3_LAG_WDI_DATA_GATE"
GATE_STATUS_VOCABULARY: tuple[str, ...] = (
    GATE_STATUS_PASS, GATE_STATUS_FAIL, GATE_STATUS_UNRESOLVED)


class M3LagWdiDataGateError(RuntimeError):
    """Raised whenever a fail-closed precondition of the Gate is violated."""


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(root: Path, rel: str) -> Any:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def verify_human_authorization() -> dict[str, Any]:
    """The step D authorization, pinned by its own byte length and digest."""
    raw = HUMAN_AUTHORIZATION_TEXT.encode("utf-8")
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "authorization_text": HUMAN_AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": len(raw),
        "authorization_sha256": _sha256_bytes(raw),
        "authorization_is_single_use": True,
        "authorization_covers_modeling": False,
        "authorization_covers_model_fitting": False,
        "authorization_covers_final_test": False,
        "authorization_covers_new_retrieval": False,
        "authorization_covers_step_e": False,
        "authorization_covers_merge": False,
        "authorization_covers_ready_for_review": False,
        "gate_pass_is_not_modeling_authorization": True,
        "prior_step_c_authorization_reused": False,
        "prior_retrieval_authorization_reused": False,
        "prior_contract_lock_authorization_reused": False,
        "standing_authorization": False,
    }


def load_locked_thresholds(root: Path) -> dict[str, Any]:
    """Re-read the PRE-EXISTING thresholds from the locked Gate contract.

    The thresholds live in the already-committed, already-locked
    ``stage128_m3_lag_wdi_exploratory_data_gate_contract.json`` and were
    inherited — not redesigned — from the M3 intl-macro Gate contract. Both
    files are re-read here and must agree; the Gate carries no threshold
    constant of its own that could drift or be quietly edited to pass.
    """
    gate_contract = _read_json(root, GATE_CONTRACT_REL)
    ancestor = _read_json(root, THRESHOLD_ANCESTOR_REL)
    thresholds = gate_contract["thresholds"]
    if gate_contract.get("thresholds_inherited_not_redesigned") is not True:
        raise M3LagWdiDataGateError(
            "the locked Gate contract must mark its thresholds as inherited")
    for key in ("candidate_valid_coverage_min",
                "block_common_sample_coverage_min",
                "minimum_positive_evaluable_each_locked_validation_window",
                "expected_parent_rows", "expected_parent_positive",
                "expected_parent_negative", "expected_parent_companies"):
        if key not in thresholds:
            raise M3LagWdiDataGateError(
                f"threshold {key} absent from the locked Gate contract")
        if float(thresholds[key]) != float(ancestor["thresholds"][key]):
            raise M3LagWdiDataGateError(
                f"threshold {key} differs between the locked Gate contract "
                "and its inheritance source; thresholds must not drift")
    if thresholds["coverage_scope"] != "development_only":
        raise M3LagWdiDataGateError("the Gate is development-only")
    if thresholds["final_test_access_for_admission"] is not False:
        raise M3LagWdiDataGateError(
            "the locked contract forbids Final Test access for admission")
    return {
        "candidate_valid_coverage_min":
            float(thresholds["candidate_valid_coverage_min"]),
        "block_common_sample_coverage_min":
            float(thresholds["block_common_sample_coverage_min"]),
        "minimum_positive_evaluable_each_locked_validation_window":
            int(thresholds[
                "minimum_positive_evaluable_each_locked_validation_window"]),
        "denominator": thresholds["denominator"],
        "coverage_scope": thresholds["coverage_scope"],
        "thresholds_source": GATE_CONTRACT_REL,
        "thresholds_source_sha256": _sha256_file(root / GATE_CONTRACT_REL),
        "thresholds_inherited_from": THRESHOLD_ANCESTOR_REL,
        "thresholds_inherited_from_sha256":
            _sha256_file(root / THRESHOLD_ANCESTOR_REL),
        "thresholds_inherited_not_redesigned": True,
        "thresholds_changed_by_this_action": False,
    }


def verify_locked_feature_contract(root: Path) -> dict[str, Any]:
    """Fail closed unless the locked two-feature contract is what step D
    believes it is executing: the exact indicator codes, lag rules and
    transformations, with no substitution and no imputation."""
    contract = _read_json(root, CONTRACT_REL)
    features = {f["feature_id"]: f for f in contract["features"]}
    if set(features) != {CPI_FEATURE_ID, FX_FEATURE_ID}:
        raise M3LagWdiDataGateError(
            f"locked contract features are {sorted(features)}")
    cpi, fx = features[CPI_FEATURE_ID], features[FX_FEATURE_ID]
    if cpi["indicator_code"] != CPI_CODE or fx["indicator_code"] != FX_CODE:
        raise M3LagWdiDataGateError("locked indicator codes do not match")
    if cpi["required_observation_years"] != ["t-1"]:
        raise M3LagWdiDataGateError("CPI must require exactly year t-1")
    if fx["required_observation_years"] != ["t-1", "t-2"]:
        raise M3LagWdiDataGateError("FX must require years t-1 and t-2")
    if contract["imputation_permitted"] is not False:
        raise M3LagWdiDataGateError("imputation is forbidden by the contract")
    if contract["complete_case_policy"][
            "both_lagged_wdi_features_required_complete"] is not True:
        raise M3LagWdiDataGateError(
            "the contract requires BOTH features complete per row")
    return {
        "contract_source": CONTRACT_REL,
        "contract_source_sha256": _sha256_file(root / CONTRACT_REL),
        "contract_version": contract["contract_version"],
        "cpi_indicator_code": CPI_CODE,
        "cpi_transformation": cpi["transformation"],
        "fx_indicator_code": FX_CODE,
        "fx_transformation": fx["transformation"],
        "observation_year_rule": "t - 1",
        "same_year_t_observation_permitted": False,
        "imputation_permitted": False,
        "alternative_indicator_after_failure_permitted": False,
        "predictor_year_calendar_mapping_locked_by_contract": False,
    }


def load_retained_values(
        root: Path, bundle_dir: str) -> dict[str, dict[int, Any]]:
    """Load both retained payloads, prove identity BYTE-FIRST, then decode.

    Identity is proven against the committed retrieval manifest (itself
    anchored to the immutable Zenodo deposit) before any parsing. This step
    performs no network access of any kind and modifies no retained byte.
    """
    manifest = _read_json(root, RETRIEVAL_MANIFEST_REL)
    values: dict[str, dict[int, Any]] = {}
    for entry in manifest["indicators"]:
        code = entry["indicator_code"]
        path = os.path.join(bundle_dir, "raw", entry["raw_artifact_filename"])
        if not os.path.isfile(path):
            raise M3LagWdiDataGateError(f"retained payload not found: {path}")
        blob = Path(path).read_bytes()
        if len(blob) != entry["raw_artifact_bytes"]:
            raise M3LagWdiDataGateError(
                f"retained payload byte count mismatch for {code}")
        if _sha256_bytes(blob) != entry["raw_artifact_sha256"]:
            raise M3LagWdiDataGateError(
                f"retained payload SHA-256 mismatch for {code}")
        document = json.loads(blob.decode("utf-8"))
        rows = document[1]
        iso3 = sorted({row.get("countryiso3code") for row in rows})
        if iso3 != [LOCKED_COUNTRY_CODE]:
            raise M3LagWdiDataGateError(
                f"{code}: payload carries country codes {iso3}")
        values[code] = {int(row["date"]): row.get("value") for row in rows}
    if set(values) != {CPI_CODE, FX_CODE}:
        raise M3LagWdiDataGateError(
            f"retained evidence carries indicators {sorted(values)}")
    return values


def derive_parent_surface(root: Path) -> tuple[
        list[dict[str, str]], dict[str, Any]]:
    """Derive the 539-row retained-M2 development common sample.

    Membership is read programmatically from the committed D2 feature table's
    ``in_three_variable_common_sample`` flag and reconciled against the
    committed M2 join audit. It is never hand-reproduced and never altered.
    Final-test rows must never enter this surface.
    """
    with (root / D2_FEATURES_REL).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    selected = [r for r in rows
                if r["in_three_variable_common_sample"].strip() == "True"]

    leaked = sorted({r["target_year"] for r in selected}
                    & set(FINAL_TEST_TARGET_YEARS))
    if leaked:
        raise M3LagWdiDataGateError(
            f"final-test target years present in the parent surface: {leaked}")
    unknown = sorted({r["target_year"] for r in selected}
                     - set(DEVELOPMENT_TARGET_YEARS))
    if unknown:
        raise M3LagWdiDataGateError(
            f"unexpected target years in the parent surface: {unknown}")

    join_audit = _read_json(root, M2_JOIN_AUDIT_REL)
    companies = len({r["ticker"] for r in selected})
    if len(selected) != join_audit["common_rows"]:
        raise M3LagWdiDataGateError(
            f"derived parent rows {len(selected)} != committed join audit "
            f"{join_audit['common_rows']}")
    if len(selected) != EXPECTED_PARENT_ROWS:
        raise M3LagWdiDataGateError(
            f"derived parent rows {len(selected)} != {EXPECTED_PARENT_ROWS}")
    if companies != EXPECTED_PARENT_COMPANIES:
        raise M3LagWdiDataGateError(
            f"derived companies {companies} != {EXPECTED_PARENT_COMPANIES}")
    if join_audit["common_positive"] != EXPECTED_PARENT_POSITIVE:
        raise M3LagWdiDataGateError("committed parent positive count drifted")
    if join_audit["common_negative"] != EXPECTED_PARENT_NEGATIVE:
        raise M3LagWdiDataGateError("committed parent negative count drifted")

    surface = {
        "parent_surface_id": "retained_m2_development_common_sample",
        "parent_rows": len(selected),
        "parent_positive": join_audit["common_positive"],
        "parent_negative": join_audit["common_negative"],
        "parent_companies": companies,
        "derived_from": D2_FEATURES_REL,
        "derived_from_sha256": _sha256_file(root / D2_FEATURES_REL),
        "reconciled_against": M2_JOIN_AUDIT_REL,
        "reconciled_against_sha256": _sha256_file(root / M2_JOIN_AUDIT_REL),
        "membership_derived_programmatically_not_hand_reproduced": True,
        "membership_altered": False,
        "final_test_rows_in_parent_surface": 0,
        "development_target_years": list(DEVELOPMENT_TARGET_YEARS),
        "jalali_fiscal_year_first": min(r["fiscal_year_t"] for r in selected),
        "jalali_fiscal_year_last": max(r["fiscal_year_t"] for r in selected),
    }
    return selected, surface


def derive_validation_targets(root: Path) -> dict[str, dict[str, int]]:
    """Per-row validation targets from the committed M2 OOF prediction table.

    The OOF table repeats each validation row once per model configuration;
    rows are deduplicated on (fold, ticker, fiscal_year_t) and the resulting
    per-window positive counts are reconciled against the committed attrition
    audit. Only development validation rows exist in this table; the Final
    Test appears nowhere in it.
    """
    seen: dict[tuple[str, str, str], int] = {}
    with (root / M2_OOF_PREDICTIONS_REL).open(
            encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row["temporal_fold"], row["ticker"], row["fiscal_year_t"])
            target = int(row["target"])
            if key in seen and seen[key] != target:
                raise M3LagWdiDataGateError(
                    f"inconsistent target for OOF row {key}")
            seen[key] = target
            if row["target_year"] in FINAL_TEST_TARGET_YEARS:
                raise M3LagWdiDataGateError(
                    "final-test target year in the OOF table")

    attrition = _read_json(root, M2_ATTRITION_REL)
    windows: dict[str, dict[str, int]] = {}
    targets_by_row: dict[str, dict[tuple[str, str], int]] = {}
    for fold in LOCKED_VALIDATION_WINDOWS:
        fold_rows = {(t, y): v for (f, t, y), v in seen.items() if f == fold}
        committed = attrition["common_fold_counts"][fold]
        if len(fold_rows) != committed["rows"]:
            raise M3LagWdiDataGateError(
                f"{fold}: derived {len(fold_rows)} rows != committed "
                f"{committed['rows']}")
        if sum(fold_rows.values()) != committed["positive"]:
            raise M3LagWdiDataGateError(
                f"{fold}: derived {sum(fold_rows.values())} positives != "
                f"committed {committed['positive']}")
        windows[fold] = {"rows": len(fold_rows),
                         "positive": sum(fold_rows.values())}
        targets_by_row[fold] = fold_rows
    return {"window_counts": windows, "targets_by_row": targets_by_row,
            "source": M2_OOF_PREDICTIONS_REL,
            "source_sha256": _sha256_file(root / M2_OOF_PREDICTIONS_REL),
            "reconciled_against": M2_ATTRITION_REL,
            "reconciled_against_sha256":
                _sha256_file(root / M2_ATTRITION_REL)}


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def row_feature_status(cpi_values: dict[int, Any], fx_values: dict[int, Any],
                       jalali_fiscal_year: int, offset: int) -> dict[str, Any]:
    """Constructibility of both locked features for one row, one convention.

    Applies the locked null policies exactly: CPI needs a numeric ``t-1``
    observation; FX needs ``t-1`` and ``t-2`` present, numeric, strictly
    positive and consecutive. Also reports whether the (constructible) FX
    log-ratio would be identically zero — the step C degeneracy — which is a
    STATUS, never an admission criterion: the locked contract contains no
    zero-change rejection rule and none is invented here.
    """
    t = jalali_fiscal_year + offset
    cpi_ok = _numeric(cpi_values.get(t - 1))
    e1, e2 = fx_values.get(t - 1), fx_values.get(t - 2)
    fx_ok = _numeric(e1) and _numeric(e2) and e1 > 0 and e2 > 0
    fx_zero = bool(fx_ok and e1 == e2)
    return {"predictor_year_gregorian": t, "cpi_constructible": cpi_ok,
            "fx_constructible": fx_ok, "both_constructible": cpi_ok and fx_ok,
            "fx_zero_change": fx_zero}


def compute_gate(root: Path, values: dict[str, dict[int, Any]],
                 parent_rows: list[dict[str, str]],
                 thresholds: dict[str, Any],
                 validation: dict[str, Any]) -> dict[str, Any]:
    """Execute the locked Gate calculations. Development rows only.

    Every row's status is computed under BOTH admissible calendar
    conventions. The verdict is only issued if the statuses are identical
    under both; otherwise the Gate is UNRESOLVED. Missing coverage is a FAIL
    against the locked thresholds, never repaired here.
    """
    cpi_values, fx_values = values[CPI_CODE], values[FX_CODE]

    row_records: list[dict[str, Any]] = []
    invariant = True
    for row in parent_rows:
        jalali = int(row["fiscal_year_t"])
        per_offset = {
            offset: row_feature_status(cpi_values, fx_values, jalali, offset)
            for offset in JALALI_TO_GREGORIAN_OFFSETS}
        statuses = [
            (s["cpi_constructible"], s["fx_constructible"],
             s["fx_zero_change"]) for s in per_offset.values()]
        row_invariant = len(set(statuses)) == 1
        invariant = invariant and row_invariant
        record = {
            "ticker": row["ticker"],
            "fiscal_year_t": row["fiscal_year_t"],
            "target_year": row["target_year"],
            "temporal_folds": row["temporal_folds"],
            "status_invariant_across_calendar_conventions": row_invariant,
        }
        for offset in JALALI_TO_GREGORIAN_OFFSETS:
            s = per_offset[offset]
            record[f"predictor_year_gregorian_offset{offset}"] = s[
                "predictor_year_gregorian"]
            record[f"cpi_constructible_offset{offset}"] = s[
                "cpi_constructible"]
            record[f"fx_constructible_offset{offset}"] = s["fx_constructible"]
            record[f"both_constructible_offset{offset}"] = s[
                "both_constructible"]
            record[f"fx_zero_change_offset{offset}"] = s["fx_zero_change"]
        # Canonical (convention-invariant when row_invariant) statuses.
        first = per_offset[JALALI_TO_GREGORIAN_OFFSETS[0]]
        record["cpi_constructible"] = first["cpi_constructible"]
        record["fx_constructible"] = first["fx_constructible"]
        record["both_constructible"] = first["both_constructible"]
        record["fx_zero_change"] = first["fx_zero_change"]
        row_records.append(record)

    n = len(row_records)
    cpi_rows = sum(1 for r in row_records if r["cpi_constructible"])
    fx_rows = sum(1 for r in row_records if r["fx_constructible"])
    both_rows = sum(1 for r in row_records if r["both_constructible"])
    zero_rows = sum(1 for r in row_records if r["fx_zero_change"])

    cpi_cov, fx_cov, block_cov = cpi_rows / n, fx_rows / n, both_rows / n
    cand_min = thresholds["candidate_valid_coverage_min"]
    block_min = thresholds["block_common_sample_coverage_min"]
    pos_min = thresholds[
        "minimum_positive_evaluable_each_locked_validation_window"]

    # Positive evaluable rows per locked validation window, WITHIN the rows
    # the block actually covers (complete-case on both features).
    covered_keys = {(r["ticker"], r["fiscal_year_t"]): r["both_constructible"]
                    for r in row_records}
    window_results: dict[str, dict[str, Any]] = {}
    for fold, target_years in LOCKED_VALIDATION_WINDOWS.items():
        fold_targets = validation["targets_by_row"][fold]
        evaluable_pos = sum(
            target for (ticker, year), target in fold_targets.items()
            if covered_keys.get((ticker, year), False))
        window_results[fold] = {
            "target_years": list(target_years),
            "validation_rows": validation["window_counts"][fold]["rows"],
            "validation_positive": validation["window_counts"][fold][
                "positive"],
            "positive_evaluable_in_m3_lag_wdi_common_sample": evaluable_pos,
            "minimum_positive_required": pos_min,
            "meets_positive_floor": evaluable_pos >= pos_min,
        }

    checks = {
        "cpi_candidate_coverage_meets_threshold": cpi_cov >= cand_min,
        "fx_candidate_coverage_meets_threshold": fx_cov >= cand_min,
        "block_common_sample_coverage_meets_threshold": block_cov >= block_min,
        "every_validation_window_meets_positive_floor": all(
            w["meets_positive_floor"] for w in window_results.values()),
    }
    if not invariant:
        verdict = GATE_STATUS_UNRESOLVED
    elif all(checks.values()):
        verdict = GATE_STATUS_PASS
    else:
        verdict = GATE_STATUS_FAIL
    if verdict not in GATE_STATUS_VOCABULARY:
        raise M3LagWdiDataGateError(f"verdict {verdict!r} out of vocabulary")

    # Development predictor-year spans under each convention — reported so
    # the step C series-level findings can be located relative to the sample.
    spans = {}
    for offset in JALALI_TO_GREGORIAN_OFFSETS:
        years = [r[f"predictor_year_gregorian_offset{offset}"]
                 for r in row_records]
        spans[f"offset{offset}"] = {"first": min(years), "last": max(years)}

    return {
        "rows": n,
        "cpi_constructible_rows": cpi_rows,
        "fx_constructible_rows": fx_rows,
        "both_constructible_rows": both_rows,
        "fx_zero_change_rows": zero_rows,
        "cpi_candidate_coverage": cpi_cov,
        "fx_candidate_coverage": fx_cov,
        "block_common_sample_coverage": block_cov,
        "candidate_valid_coverage_min": cand_min,
        "block_common_sample_coverage_min": block_min,
        "minimum_positive_evaluable_each_locked_validation_window": pos_min,
        "threshold_checks": checks,
        "validation_windows": window_results,
        "status_invariant_across_calendar_conventions": invariant,
        "development_predictor_year_spans_gregorian": spans,
        "verdict": verdict,
        "row_records": row_records,
    }
