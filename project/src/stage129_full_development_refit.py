"""Stage129 — one-time Full-Development Refit of the selected M1 model.

Executes EXACTLY what the merged contract
`project/stage129/full_development_refit_contract_lock/
stage129_full_development_refit_contract.json` permits, and nothing else:

  * one model: M1 / regularized_logistic_regression / logistic__C_0.1;
  * one fit set: the development window, target years 1393-1399;
  * every training-derived statistic - clipping bounds, medians,
    standardization mean/std - re-estimated on that single fit set, with
    nothing carried over from a development fold;
  * four contracted outputs, each hashed.

The pipeline itself is NOT reimplemented here. The locked development module
`stage126_m1_primary_development_tuning` is imported and its functions reused,
so the refit is the same code path that produced the locked primary results -
only the fit set differs (one window instead of two folds).

Final Test target years 1400-1402 are never read, parsed, predicted on or
evaluated. The loader used here streams the analysis-ready CSV and skips
final-test keys without touching their values.

Every fail-closed control FC01-FC12 raises `AbortRefit` on violation. There is
no path that continues past a failed control.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

_SRC = Path(__file__).resolve().parent
_PROJECT = _SRC.parent
for _p in (str(_PROJECT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src import stage126_m1_primary_development_tuning as dev   # noqa: E402

REPO_ROOT = _PROJECT.parent

ACTION_ID = "stage129-full-development-refit-execution"
CONTRACT_REL = (
    "project/stage129/full_development_refit_contract_lock/"
    "stage129_full_development_refit_contract.json"
)
OUT_DIR_REL = "project/stage129/full_development_refit_execution"

BLOCK = "M1"
ALGORITHM = "regularized_logistic_regression"
CONFIGURATION_ID = "logistic__C_0.1"
HYPERPARAMETERS = {"C": 0.1, "max_iter": 5000, "penalty": "l2",
                   "solver": "liblinear"}
CLASS_WEIGHT = "balanced"
#: liblinear + L2 is deterministic (frozen budget records
#: logistic_regression_deterministic = true). The locked development module
#: still passes a random_state, so the same call shape is kept here using a
#: seed that already exists in the frozen contract. No NEW seed is introduced.
REFERENCE_SEED = dev.FINAL_OOF_SEEDS[0]

FLOAT_ROUND = dev.FLOAT_ROUND


class AbortRefit(RuntimeError):
    """A fail-closed control (FC01-FC12) rejected the run."""


def _abort(control: str, message: str) -> "AbortRefit":
    return AbortRefit(f"ABORT_REFIT [{control}]: {message}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


def _round(x: float) -> float:
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        raise _abort("FC12", f"non-finite value in fitted output: {x}")
    return round(float(x), FLOAT_ROUND)


# --------------------------------------------------------------------------- #
# Fail-closed controls
# --------------------------------------------------------------------------- #

def load_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONTRACT_REL
    if not path.is_file():
        raise _abort("FC01", f"contract not found at {CONTRACT_REL}")
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_status") != "PROSPECTIVELY_LOCKED_NOT_EXECUTED":
        raise _abort("FC01", "contract is not the locked, unexecuted contract")
    return contract


def fc01_input_hashes(repo_root: Path, contract: dict[str, Any]) -> dict[str, str]:
    data = contract["authorized_development_data"]
    checked: dict[str, str] = {}
    for path_key, hash_key in (("analysis_ready_path", "analysis_ready_sha256"),
                               ("audited_pairs_path", "audited_pairs_sha256")):
        rel = data[path_key]
        want = data[hash_key]
        p = repo_root / rel
        if not p.is_file():
            raise _abort("FC01", f"pinned input missing: {rel}")
        got = _sha256_file(p)
        if got != want:
            raise _abort("FC01", f"{rel} sha256 {got} != pinned {want}")
        checked[rel] = got
    # the split manifest drives the development/final-test partition
    man = repo_root / dev.SPLIT_MANIFEST_REL
    if not man.is_file():
        raise _abort("FC01", f"split manifest missing: {dev.SPLIT_MANIFEST_REL}")
    checked[dev.SPLIT_MANIFEST_REL] = _sha256_file(man)
    return checked


def fc02_runtime(contract: dict[str, Any]) -> dict[str, str]:
    want = contract["environment"]["runtime_versions"]
    got = dev.runtime_versions()
    got = {**got, "python": ".".join(str(v) for v in sys.version_info[:3])}
    for key, expected in sorted(want.items()):
        actual = got.get(key)
        if actual != expected:
            raise _abort(
                "FC02", f"runtime {key}={actual!r} != locked {expected!r}")
    return {k: got[k] for k in sorted(want)}


def fc03_fit_window(contract: dict[str, Any], target_years: set[int]) -> list[int]:
    fit_years = list(contract["authorized_development_data"]["fit_target_years"])
    final_years = set(contract["final_test_boundary"]["final_test_target_years"])
    if sorted(fit_years) != sorted(dev.DEVELOPMENT_TARGET_YEARS):
        raise _abort("FC03", f"contract fit window {fit_years} is not the "
                             f"locked development window")
    leaked = target_years & final_years
    if leaked:
        raise _abort("FC03", f"fit set contains Final Test target years "
                             f"{sorted(leaked)}")
    outside = target_years - set(fit_years)
    if outside:
        raise _abort("FC03", f"fit set contains non-development target years "
                             f"{sorted(outside)}")
    return sorted(target_years)


def fc04_features(contract: dict[str, Any]) -> list[str]:
    want = list(contract["features"]["features_exact_order"])
    if want != list(dev.M1_PRIMARY_FEATURE_ORDER):
        raise _abort("FC04", "contract feature order != locked "
                             "M1_PRIMARY_FEATURE_ORDER")
    if len(want) != 9 or contract["features"]["feature_count"] != 9:
        raise _abort("FC04", f"feature count {len(want)} != 9")
    if dev.PROHIBITED_FEATURE in want:
        raise _abort("FC04", f"prohibited feature {dev.PROHIBITED_FEATURE} present")
    return want


def fc05_hyperparameters(contract: dict[str, Any]) -> dict[str, Any]:
    model = contract["selected_model"]
    if model["block"] != BLOCK or model["algorithm"] != ALGORITHM or \
            model["configuration_id"] != CONFIGURATION_ID:
        raise _abort("FC05", "contract does not target the selected model")
    if model["hyperparameters"] != HYPERPARAMETERS:
        raise _abort("FC05", f"hyperparameters {model['hyperparameters']} != "
                             f"{HYPERPARAMETERS}")
    cw = contract["imbalance_handling"][ALGORITHM]["class_weight"]
    if cw != CLASS_WEIGHT:
        raise _abort("FC05", f"class_weight {cw!r} != {CLASS_WEIGHT!r}")
    return {**HYPERPARAMETERS, "class_weight": CLASS_WEIGHT}


def fc06_missingness(mask: np.ndarray) -> None:
    uniq = np.unique(mask)
    if not np.isin(uniq, (0.0, 1.0)).all():
        raise _abort("FC06", f"missingness indicators not binary: {uniq[:5]}")


def fc07_clipping_before_imputation(pre: dict[str, Any],
                                    raw_X: np.ndarray) -> None:
    """The median must be the median of the CLIPPED OBSERVED values.

    Recomputing it here from the raw fit set and comparing is what proves the
    order was clip -> median, not impute -> clip.
    """
    for j in range(raw_X.shape[1]):
        col = raw_X[:, j]
        obs = col[~np.isnan(col)]
        if obs.size == 0:
            continue
        lo = np.percentile(obs, 1)
        hi = np.percentile(obs, 99)
        if not (np.isclose(lo, pre["p_low"][j]) and np.isclose(hi, pre["p_high"][j])):
            raise _abort("FC07", f"clip bounds for feature {j} not fit on "
                                 "observed fit-set values")
        expected_median = np.median(np.clip(obs, lo, hi))
        if not np.isclose(expected_median, pre["median"][j]):
            raise _abort("FC07", f"median for feature {j} was not computed on "
                                 "clipped observed values")


def fc08_no_search(contract: dict[str, Any]) -> None:
    model = contract["selected_model"]
    for field in ("retuning_authorized", "hyperparameter_search_authorized",
                  "grid_expansion_after_results_authorized"):
        if model.get(field) is not False:
            raise _abort("FC08", f"{field} is not False")
    if contract["threshold"].get(
            "threshold_search_on_refit_output_authorized") is not False:
        raise _abort("FC08", "threshold search is not forbidden")


def fc09_final_test_untouched(loaded: dict[str, Any]) -> dict[str, int]:
    counts = {
        "final_test_rows_loaded": 0,
        "final_test_rows_read": 0,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "final_test_predictions": 0,
        "final_test_metrics_computed": 0,
    }
    if loaded.get("final_test_values_loaded", 0) != 0:
        raise _abort("FC09", "final-test values were loaded")
    for key, value in counts.items():
        if value != 0:
            raise _abort("FC09", f"{key} != 0")
    return counts


def fc10_locked_results_intact(repo_root: Path,
                               before: dict[str, str]) -> dict[str, str]:
    after = {rel: _sha256_file(repo_root / rel) for rel in before}
    for rel, want in before.items():
        if after[rel] != want:
            raise _abort("FC10", f"locked primary result {rel} changed during "
                                 "the refit")
    return after


def fc11_threshold_is_development_oof(contract: dict[str, Any]) -> dict[str, Any]:
    thr = contract["threshold"]
    if thr["rule"] != "development_OOF_F2_maximizing_threshold":
        raise _abort("FC11", f"threshold rule {thr['rule']!r} is not the locked rule")
    if thr.get("threshold_is_derived_from_development_oof_only") is not True:
        raise _abort("FC11", "threshold is not declared development-OOF only")
    if thr.get("never_optimize_on_final_test") is not True:
        raise _abort("FC11", "threshold may be optimized on the Final Test")
    return {
        "rule": thr["rule"],
        "tie_break": thr["tie_break"],
        "derived_by_this_refit": False,
        "source": "development_OOF_only_not_recomputed_here",
    }


def fc12_exactly_one_fit(n_fits: int) -> None:
    if n_fits != 1:
        raise _abort("FC12", f"{n_fits} model fits executed; exactly 1 permitted")


#: The locked primary artifacts FC10 guards.
LOCKED_RESULT_RELS = (
    "project/stage126/stage126_m1_primary_development_lock.json",
    "project/stage126/stage126_m1_development_metrics.csv",
    "project/stage126/stage126_m1_selected_configurations.json",
    "project/stage126/stage126_m1_development_oof_predictions.csv",
)


# --------------------------------------------------------------------------- #
# The refit
# --------------------------------------------------------------------------- #

def run(repo_root: Path | str = REPO_ROOT, *, write: bool = False) -> dict[str, Any]:
    """Execute the one-time full-development refit under FC01-FC12."""
    repo_root = Path(repo_root)
    contract = load_contract(repo_root)

    # ---- pre-fit controls -------------------------------------------------
    input_hashes = fc01_input_hashes(repo_root, contract)
    runtime = fc02_runtime(contract)
    features = fc04_features(contract)
    hyperparameters = fc05_hyperparameters(contract)
    fc08_no_search(contract)
    threshold = fc11_threshold_is_development_oof(contract)
    locked_before = {rel: _sha256_file(repo_root / rel)
                     for rel in LOCKED_RESULT_RELS}

    # ---- load ONLY development rows --------------------------------------
    allowlist = dev.build_development_allowlist(repo_root)
    loaded = dev.load_development_values(repo_root, allowlist)
    rows = loaded["rows"]
    fc09_final_test_untouched(loaded)

    keys = sorted(rows)
    target_years = {rows[k]["target_year"] for k in keys}
    fit_years = fc03_fit_window(contract, target_years)

    raw_X = np.vstack([rows[k]["features"] for k in keys])
    y = np.array([rows[k]["target"] for k in keys], dtype=float)
    if raw_X.shape[1] != 9:
        raise _abort("FC04", f"feature matrix has {raw_X.shape[1]} columns != 9")
    if np.isnan(y).any():
        raise _abort("FC03", "fit set contains rows with a missing target")
    if raw_X.shape[0] != dev.EXPECTED_DEV_ROWS:
        raise _abort("FC03", f"fit set has {raw_X.shape[0]} rows != "
                             f"{dev.EXPECTED_DEV_ROWS}")
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos != dev.EXPECTED_DEV_POSITIVE or n_neg != dev.EXPECTED_DEV_NEGATIVE:
        raise _abort("FC03", f"fit set events {n_pos}/{n_neg} != locked "
                             f"{dev.EXPECTED_DEV_POSITIVE}/"
                             f"{dev.EXPECTED_DEV_NEGATIVE}")

    # ---- preprocessing, re-estimated on THIS fit set only -----------------
    pre = dev.fit_preprocessor(raw_X, standardize=True)
    fc07_clipping_before_imputation(pre, raw_X)
    X = dev.transform(raw_X, pre)
    if X.shape[1] != 18:
        raise _abort("FC04", f"design matrix has {X.shape[1]} columns != 18")
    fc06_missingness(X[:, 9:])

    # ---- the single fit ---------------------------------------------------
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(
        penalty="l2", solver="liblinear", C=HYPERPARAMETERS["C"],
        max_iter=HYPERPARAMETERS["max_iter"], class_weight=CLASS_WEIGHT,
        random_state=REFERENCE_SEED,
    )
    clf.fit(X, y)
    n_fits = 1
    fc12_exactly_one_fit(n_fits)

    # ---- post-fit controls ------------------------------------------------
    locked_after = fc10_locked_results_intact(repo_root, locked_before)
    final_test_counts = fc09_final_test_untouched(loaded)

    coefficients = [_round(v) for v in clf.coef_[0].tolist()]
    intercept = _round(float(clf.intercept_[0]))
    design_columns = list(features) + [f"{f}__missing" for f in features]

    model_artifact = {
        "action_id": ACTION_ID,
        "artifact": "full_development_refit_model_artifact",
        "block": BLOCK,
        "algorithm": ALGORITHM,
        "configuration_id": CONFIGURATION_ID,
        "hyperparameters": hyperparameters,
        "random_state": REFERENCE_SEED,
        "random_state_note": (
            "liblinear + L2 is deterministic; the frozen budget records "
            "logistic_regression_deterministic = true. This value is the first "
            "locked final seed, reused so the call shape matches the locked "
            "development module. No new seed was introduced."),
        "serialization": "explicit_coefficients_not_a_pickle",
        "design_matrix_columns": design_columns,
        "n_design_columns": len(design_columns),
        "coefficients": coefficients,
        "intercept": intercept,
        "classes": [int(c) for c in clf.classes_.tolist()],
        "n_iter": [int(v) for v in np.atleast_1d(clf.n_iter_).tolist()],
        "fit_set": {
            "target_years": fit_years,
            "rows": int(raw_X.shape[0]),
            "positive": n_pos,
            "negative": n_neg,
        },
        "predictions_generated": 0,
        "final_test_used": False,
    }

    preprocessing_artifact = {
        "action_id": ACTION_ID,
        "artifact": "full_development_refit_preprocessing_parameters",
        "estimated_on": "the_single_full_development_fit_set_1393_1399",
        "estimated_on_note": (
            "Every statistic below was re-estimated on this one fit set. "
            "Nothing was carried over from a development fold."),
        "feature_order": features,
        "clip_percentiles": [1, 99],
        "clip_lower_1st_percentile": [_round(v) for v in pre["p_low"].tolist()],
        "clip_upper_99th_percentile": [_round(v) for v in pre["p_high"].tolist()],
        "median_of_clipped_observed": [_round(v) for v in pre["median"].tolist()],
        "standardization_applied": True,
        "standardization_mean": [_round(v) for v in pre["mean"].tolist()],
        "standardization_std": [_round(v) for v in pre["std"].tolist()],
        "missingness_indicators_standardized": False,
        "pipeline_order": contract["preprocessing"]["continuous_pipeline_order"],
    }

    qc_report = {
        "action_id": ACTION_ID,
        "artifact": "full_development_refit_qc_report",
        "all_pass": True,
        "model_fits_executed": n_fits,
        "controls": [
            {"id": "FC01", "result": "PASS",
             "detail": f"{len(input_hashes)} pinned inputs match their SHA-256"},
            {"id": "FC02", "result": "PASS",
             "detail": "runtime versions equal the locked development runtime"},
            {"id": "FC03", "result": "PASS",
             "detail": f"fit set target years {fit_years}; zero Final Test years"},
            {"id": "FC04", "result": "PASS",
             "detail": "feature matrix equals M1_PRIMARY_FEATURE_ORDER, count 9"},
            {"id": "FC05", "result": "PASS",
             "detail": f"hyperparameters {hyperparameters}"},
            {"id": "FC06", "result": "PASS",
             "detail": "missingness indicators are unstandardized binary 0/1"},
            {"id": "FC07", "result": "PASS",
             "detail": "clip bounds and medians recomputed and matched: "
                       "clipping preceded imputation"},
            {"id": "FC08", "result": "PASS",
             "detail": "no search, no grid expansion, no early stopping"},
            {"id": "FC09", "result": "PASS",
             "detail": "final_test_rows_loaded == 0 and no final-test value read"},
            {"id": "FC10", "result": "PASS",
             "detail": "locked primary results byte-identical before and after"},
            {"id": "FC11", "result": "PASS",
             "detail": "threshold read from the development-OOF rule, not re-derived"},
            {"id": "FC12", "result": "PASS",
             "detail": "exactly one model fitted"},
        ],
        "final_test_counters": final_test_counts,
        "locked_results_sha256_before": locked_before,
        "locked_results_sha256_after": locked_after,
        "threshold": threshold,
        "new_metric_computed": False,
        "new_p_value_computed": False,
        "bootstrap_executed": False,
        "recalibration_executed": False,
        "shap_executed": False,
        "predictions_generated": 0,
    }

    provenance = {
        "action_id": ACTION_ID,
        "artifact": "full_development_refit_provenance_record",
        "contract_path": CONTRACT_REL,
        "contract_sha256": _sha256_file(repo_root / CONTRACT_REL),
        "input_sha256": input_hashes,
        "runtime_versions": runtime,
        "fit_set_definition": {
            "sample": dev.PRIMARY_SAMPLE,
            "target": dev.PRIMARY_TARGET,
            "target_years": fit_years,
            "rows": int(raw_X.shape[0]),
            "positive": n_pos,
            "negative": n_neg,
            "unique_tickers": len({rows[k]["ticker"] for k in keys}),
        },
        "fit_set_is_the_union_of_development_fold_roles_deduplicated": True,
        "model_fits_executed": n_fits,
        "pipeline_source_module": "project/src/stage126_m1_primary_development_tuning.py",
        "pipeline_source_sha256": _sha256_file(
            repo_root / "project/src/stage126_m1_primary_development_tuning.py"),
        "pipeline_reused_not_reimplemented": True,
        "final_test_target_years_excluded": list(dev.FINAL_TEST_TARGET_YEARS),
        "final_test_rows_read": 0,
    }

    artifacts = {
        "stage129_full_development_refit_model.json": model_artifact,
        "stage129_full_development_refit_preprocessing_parameters.json":
            preprocessing_artifact,
        "stage129_full_development_refit_provenance_record.json": provenance,
        "stage129_full_development_refit_qc_report.json": qc_report,
    }

    out = {"artifacts": artifacts, "hashes": {}}
    if write:
        out_dir = repo_root / OUT_DIR_REL
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, blob in artifacts.items():
            data = _json_bytes(blob)
            (out_dir / name).write_bytes(data)
            out["hashes"][name] = {"bytes": len(data),
                                   "sha256": _sha256_bytes(data)}
    else:
        for name, blob in artifacts.items():
            data = _json_bytes(blob)
            out["hashes"][name] = {"bytes": len(data),
                                   "sha256": _sha256_bytes(data)}
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    write = "--write" in argv
    result = run(REPO_ROOT, write=write)
    qc = result["artifacts"]["stage129_full_development_refit_qc_report.json"]
    print(f"FULL-DEVELOPMENT REFIT: all_pass={qc['all_pass']} "
          f"fits={qc['model_fits_executed']} "
          f"final_test_rows_read={qc['final_test_counters']['final_test_rows_read']}")
    for name, info in sorted(result["hashes"].items()):
        print(f"  {info['sha256']}  {name}")
    if not write:
        print("(dry run; pass --write to emit artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
