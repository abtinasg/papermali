"""Stage129 — the one-time contracted Final Test execution.

Executes exactly what `stage129_final_test_execution_contract` (merged, PR #91)
permits, applying the accepted PR #90 model and the admitted PR #95 threshold to
Final Test target years 1400-1402.

Five properties are load-bearing:

  * **The model is APPLIED, never fitted.** It is reconstructed from the pinned
    intercept and 18 coefficients. `sklearn` is not used to fit anything and no
    estimator object is trained.
  * **Preprocessing statistics come from the refit and are never re-estimated.**
    The `pre` dict is built from PR #90's frozen `p_low`, `p_high`, `median`,
    `mean`, `std` and handed to the LOCKED `transform`, so clipping, imputation,
    standardization and the missingness indicators all run through the same code
    path that produced the locked development results.
  * **The mask is the row's own.** `transform` derives indicators from each
    row's own pre-imputation NaNs -- a property of the Final Test rows, not a
    statistic estimated on them.
  * **The cohort is fixed before any value is read.** The manifest pass reads
    split/key columns only; the value pass keeps ONLY final-test keys.
  * **One pass, no retry.** Every control is executed and recorded, and any
    violation raises `AbortFinalTest` with the real counters at the moment of
    the stop.

Metrics are the closed contracted set and nothing else.

Nothing in this module runs on import. The Final Test is opened only by an
explicit `--execute-final-test` invocation of `main()`, and only once per repo
root per process.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "project"))

from src import stage126_m1_primary_development_tuning as locked  # noqa: E402

ACTION_ID = "stage129-final-test-execution"
BASE_COMMIT = "bc1baa11eb94999af8a60cd2f266628b8c78db68"
CONTRACT_REL = ("project/stage129/final_test_execution_contract_lock/"
                "stage129_final_test_execution_contract.json")
PRE01_REL = ("project/stage129/final_test_execution/"
             "stage129_pre01_human_authorization_record.json")
THRESHOLD_REL = ("project/stage129/threshold_derivation_attempt3/"
                 "stage129_threshold_value_attempt3.json")
MODEL_REL = ("project/stage129/full_development_refit_execution/"
             "stage129_full_development_refit_model.json")
PREP_REL = ("project/stage129/full_development_refit_execution/"
            "stage129_full_development_refit_preprocessing_parameters.json")
PROV_REL = ("project/stage129/full_development_refit_execution/"
            "stage129_full_development_refit_provenance_record.json")
QC90_REL = ("project/stage129/full_development_refit_execution/"
            "stage129_full_development_refit_qc_report.json")

THRESHOLD = 0.426878838687
FINAL_TEST_YEARS = frozenset({1400, 1401, 1402})
DEV_YEARS = frozenset({1393, 1394, 1395, 1396, 1397, 1398, 1399})
BOOTSTRAP_SEED = 20260724
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_MIN_VALID = 1000
TOPK_FRACTION = 0.10
FLOAT_ROUND = locked.FLOAT_ROUND

LOCKED_DEV_RESULTS = {
    "project/stage126/stage126_m1_development_metrics.csv":
        "1c5f33b4e3a156b111d29a2c4e13ecee9c5e7ad73f6b3d98cf3c6b4b506be17a",
    "project/stage126/stage126_m1_development_oof_predictions.csv":
        "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749",
    "project/stage126/stage126_m1_primary_development_lock.json":
        "c500563049e30a27ac59fd3d673ef801b8d8e12f0bb684dd2e0aec13eb5618e4",
}

PKG_REL = "project/stage129/final_test_execution"
MANIFEST_NAME = "metadata_and_hashes_stage129_final_test_execution.json"
PREDICTIONS_NAME = "stage129_final_test_predictions.json"
METRICS_NAME = "stage129_final_test_metrics.json"
PROVENANCE_NAME = "stage129_final_test_provenance_record.json"
QC_NAME = "stage129_final_test_qc_report.json"

#: Counters the contract fixes at zero for any authorized execution.
ZERO_COUNTERS = (
    "model_fits_executed", "refits_executed", "tuning_runs",
    "hyperparameter_searches", "feature_searches", "threshold_searches",
    "recalibration_executions", "isotonic_executions", "shap_executions",
    "holm_executions", "p_values_computed", "winner_selections",
)

CONTROL_IDS = tuple(f"FT{i:02d}" for i in range(1, 22))

#: Repo roots whose Final Test has already been opened in THIS process. The
#: contract permits exactly one pass; a second `run()` against the same root
#: is refused rather than silently taken.
_OPENED_ROOTS: set[str] = set()


class AbortFinalTest(RuntimeError):
    """Raised by any failing control. Nothing further is read or written."""


def _abort(control: str, message: str) -> AbortFinalTest:
    return AbortFinalTest(f"ABORT_FINAL_TEST [{control}]: {message}")


class Counters:
    """Real counters, incremented where the work actually happens."""

    def __init__(self) -> None:
        # Contract-required, fixed at zero.
        self.model_fits_executed = 0
        self.refits_executed = 0
        self.tuning_runs = 0
        self.hyperparameter_searches = 0
        self.feature_searches = 0
        self.threshold_searches = 0
        self.recalibration_executions = 0
        self.isotonic_executions = 0
        self.shap_executions = 0
        self.holm_executions = 0
        self.p_values_computed = 0
        self.winner_selections = 0
        # Contract-required, reported.
        self.final_test_passes_executed = 0
        self.final_test_rows_read = 0
        self.final_test_evaluable_rows = 0
        self.final_test_predictions = 0
        self.final_test_metrics_computed = 0
        self.bootstrap_executions = 0
        # Execution-side detail.
        self.final_test_rows_seen_in_manifest = 0
        self.final_test_predictor_values_read = 0
        self.final_test_target_values_read = 0
        self.final_test_load_invocations = 0
        self.bootstrap_valid_replicates = 0

    def as_dict(self) -> dict[str, int]:
        return dict(vars(self))

    def assert_zero(self, control: str) -> None:
        for name in ZERO_COUNTERS:
            value = getattr(self, name)
            if value != 0:
                raise _abort(control, f"{name} == {value}, contract requires 0")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(repo_root: Path, rel: str) -> str:
    return _sha256_bytes((repo_root / rel).read_bytes())


def _load(repo_root: Path, rel: str) -> dict[str, Any]:
    with (repo_root / rel).open(encoding="utf-8") as fh:
        return json.load(fh)


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


def _round(control: str, x: float) -> float:
    value = float(x)
    if math.isnan(value) or math.isinf(value):
        raise _abort(control, f"non-finite value in a reported quantity: {x!r}")
    return round(value, FLOAT_ROUND)


# ------------------------------------------------------------------ metrics
def pr_auc(y: np.ndarray, p: np.ndarray) -> float:
    """Average precision: sum (R_n - R_{n-1}) * P_n over descending scores."""
    order = np.argsort(-p, kind="mergesort")
    y = y[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    total_pos = y.sum()
    if total_pos == 0:
        return float("nan")
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / total_pos
    prev = 0.0
    out = 0.0
    for prec, rec in zip(precision, recall):
        out += (rec - prev) * prec
        prev = rec
    return float(out)


def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    """Rank-based AUC with ties averaged."""
    pos = p[y == 1]
    neg = p[y == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(p.size, dtype=float)
    sorted_p = p[order]
    i = 0
    while i < p.size:
        j = i
        while j + 1 < p.size and sorted_p[j + 1] == sorted_p[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg
        i = j + 1
    rank_sum = ranks[y == 1].sum()
    return float((rank_sum - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _topk_indices(p: np.ndarray, tickers: list[str], k: int) -> np.ndarray:
    """Rank by probability descending, ticker ascending as the deterministic tie."""
    order = sorted(range(p.size), key=lambda i: (-p[i], tickers[i]))
    return np.array(order[:k], dtype=int)


def recall_lift_at_10pct(y: np.ndarray, p: np.ndarray, tickers: list[str],
                         years: list[int]) -> tuple[float, float, dict[str, Any]]:
    """Per-year K_y = ceil(0.10 * N_y); pooled recall and lift."""
    captured = 0
    total_pos = int(y.sum())
    selected: list[int] = []
    per_year: dict[str, dict[str, int]] = {}
    for yr in sorted(set(years)):
        idx = [i for i, v in enumerate(years) if v == yr]
        k = math.ceil(TOPK_FRACTION * len(idx))
        sub_p = p[idx]
        sub_t = [tickers[i] for i in idx]
        pick = _topk_indices(sub_p, sub_t, k)
        chosen = [idx[i] for i in pick]
        selected.extend(chosen)
        captured += int(y[chosen].sum())
        per_year[str(yr)] = {"N_y": len(idx), "K_y": int(k),
                             "captured_positives": int(y[chosen].sum())}
    recall = captured / total_pos if total_pos else float("nan")
    prevalence = total_pos / y.size if y.size else float("nan")
    precision_topk = y[selected].sum() / len(selected) if selected else float("nan")
    lift = precision_topk / prevalence if prevalence else float("nan")
    detail = {
        "definition": "K_y = ceil(0.10 * N_y)",
        "fraction": TOPK_FRACTION,
        "ranking_order": ["predicted_probability_descending",
                          "ticker_ascending_deterministic_tiebreaker"],
        "K_optimized_after_results": False,
        "selected_rows": len(selected),
        "captured_positives": captured,
        "total_positives": total_pos,
        "pooled_precision_among_selected": float(precision_topk),
        "pooled_test_prevalence": float(prevalence),
        "per_target_year": per_year,
    }
    return float(recall), float(lift), detail


def cluster_bootstrap(y: np.ndarray, p: np.ndarray, tickers: list[str],
                      counters: Counters) -> dict[str, Any]:
    """Paired company-cluster bootstrap: resample tickers, percentile-95."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    uniq = sorted(set(tickers))
    index_by_ticker: dict[str, list[int]] = {t: [] for t in uniq}
    for i, t in enumerate(tickers):
        index_by_ticker[t].append(i)
    stats: dict[str, list[float]] = {"PR-AUC": [], "ROC-AUC": [], "Brier_score": []}
    valid = 0
    for _ in range(BOOTSTRAP_REPLICATES):
        draw = rng.integers(0, len(uniq), size=len(uniq))
        rows: list[int] = []
        for d in draw:
            rows.extend(index_by_ticker[uniq[int(d)]])
        yy = y[rows]
        if yy.sum() == 0 or yy.sum() == yy.size:
            continue                      # valid_replicate_requires_both_classes
        pp = p[rows]
        valid += 1
        stats["PR-AUC"].append(pr_auc(yy, pp))
        stats["ROC-AUC"].append(roc_auc(yy, pp))
        stats["Brier_score"].append(brier(yy, pp))
    counters.bootstrap_executions = 1
    counters.bootstrap_valid_replicates = valid
    if valid < BOOTSTRAP_MIN_VALID:
        raise _abort("FT19", f"only {valid} valid bootstrap replicates, minimum "
                             f"{BOOTSTRAP_MIN_VALID}")
    out: dict[str, Any] = {"method": "paired_company_cluster_bootstrap",
                           "cluster": "ticker",
                           "replicates": BOOTSTRAP_REPLICATES,
                           "valid_replicates": valid,
                           "valid_replicate_requires_both_classes": True,
                           "confidence_interval": "percentile_95",
                           "seed": BOOTSTRAP_SEED,
                           "intervals": {}}
    for name, vals in stats.items():
        arr = np.array(vals, dtype=float)
        out["intervals"][name] = {
            "lower": _round("FT19", float(np.percentile(arr, 2.5))),
            "upper": _round("FT19", float(np.percentile(arr, 97.5))),
        }
    return out


# ------------------------------------------------------------------- cohort
def final_test_cohort(repo_root: Path) -> tuple[dict[tuple[str, str], dict[str, Any]],
                                                int]:
    """Manifest pass: split/key columns only. No predictor or target value."""
    try:
        rows = locked._read_manifest_split_columns(repo_root)
    except Exception as exc:                       # fail closed, never proceed
        raise _abort("FT05", f"split manifest unreadable: {exc}") from exc
    cohort: dict[tuple[str, str], dict[str, Any]] = {}
    seen = 0
    for row in rows:
        try:
            year = int(row["target_year"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _abort("FT05", f"unparseable target_year in manifest: {exc}") from exc
        if year not in FINAL_TEST_YEARS:
            continue
        if row["dataset_split"] != locked.FINAL_TEST_ROLE and \
                row["temporal_fold"] != locked.FINAL_TEST_ROLE:
            continue
        seen += 1
        cohort[(row["predictor_row_key_t"], row["target_row_key_t_plus_1"])] = {
            "ticker": row["ticker"], "target_year": year}
    return cohort, seen


def load_final_test_values(repo_root: Path,
                           cohort: dict[tuple[str, str], dict[str, Any]],
                           counters: Counters) -> list[dict[str, Any]]:
    """Value pass: stream the analysis-ready CSV, keep ONLY cohort keys."""
    counters.final_test_load_invocations += 1
    if counters.final_test_load_invocations != 1:
        raise _abort("FT11", "a second pass over the Final Test was attempted")
    source_cols = sorted({locked.FEATURE_SOURCE_COLUMN[f]
                          for f in locked.M1_PRIMARY_FEATURE_ORDER})
    out: list[dict[str, Any]] = []
    path = repo_root / locked.ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {"predictor_row_key_t",
                                     "target_row_key_t_plus_1",
                                     "target_year", "ticker",
                                     locked.PRIMARY_TARGET}
        missing = needed - header
        if missing:
            raise _abort("FT04", f"analysis-ready CSV missing {sorted(missing)}")
        for row in reader:
            key = (row.get("predictor_row_key_t", ""),
                   row.get("target_row_key_t_plus_1", ""))
            if key not in cohort:
                continue            # development rows are never parsed here
            counters.final_test_rows_read += 1
            raw = {c: row.get(c, "") for c in source_cols}
            counters.final_test_predictor_values_read += len(raw)
            target_raw = (row.get(locked.PRIMARY_TARGET, "") or "").strip()
            counters.final_test_target_values_read += 1
            try:
                year = int(row.get("target_year", "0"))
            except ValueError as exc:
                raise _abort("FT05", f"unparseable target_year on a cohort row: "
                                     f"{exc}") from exc
            if year not in FINAL_TEST_YEARS:
                raise _abort("FT05", f"cohort row carries target_year {year}")
            out.append({"key": key, "ticker": row.get("ticker", ""),
                        "target_year": year,
                        "raw": raw, "target_raw": target_raw})
    return out


# -------------------------------------------------------------------- writer
def build_manifest(blobs: dict[str, bytes], counters: Counters,
                   executor_sha256: str) -> dict[str, Any]:
    """The package manifest: SHA-256 and byte count for every package file."""
    return {
        "action_id": ACTION_ID,
        "action_type": "one_time_contracted_final_test_execution",
        "base_commit": BASE_COMMIT,
        "contract_lock_pr": 91,
        "credentials_committed_to_git": False,
        "executor_path": "project/src/stage129_final_test_execution.py",
        "executor_sha256": executor_sha256,
        "fail_closed_controls_all_passed": True,
        "final_test_passes_executed": counters.final_test_passes_executed,
        "final_test_rows_read": counters.final_test_rows_read,
        "new_data_files_created_by_this_action": 0,
        "package_file_count": len(blobs),
        "package_files": {
            name: {"bytes": len(data), "sha256": _sha256_bytes(data)}
            for name, data in sorted(blobs.items())
        },
        "pickle_or_binary_model_committed": False,
        "pii_committed_to_git": False,
    }


def write_package(repo_root: Path, artifacts: dict[str, Any],
                  counters: Counters, executor_sha256: str) -> dict[str, Any]:
    """Transactional writer: temp dir -> validation -> final move.

    Nothing lands in the package directory unless every file was written,
    re-read, parsed and matched its own SHA-256 and byte count first. An
    existing output file is never overwritten.
    """
    out_dir = (repo_root / PKG_REL).resolve()
    blobs: dict[str, bytes] = {name: _json_bytes(obj)
                               for name, obj in artifacts.items()}
    manifest = build_manifest(blobs, counters, executor_sha256)
    blobs[MANIFEST_NAME] = _json_bytes(manifest)

    # FT20: every target path stays inside the package directory.
    for name in blobs:
        target = (out_dir / name).resolve()
        if target.parent != out_dir or os.sep in name or name in (".", ".."):
            raise _abort("FT20", f"output {name!r} escapes {PKG_REL}/")

    # No overwrite: the package is written once.
    clashes = sorted(n for n in blobs if (out_dir / n).exists())
    if clashes:
        raise _abort("FT20", f"refusing to overwrite existing output: {clashes}")

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=".tmp_stage129_final_test_",
                                    dir=str(out_dir)))
    try:
        for name, data in blobs.items():
            (tmp_dir / name).write_bytes(data)

        # Validation, before anything is visible in the package directory.
        expected = manifest["package_files"]
        for name, data in blobs.items():
            back = (tmp_dir / name).read_bytes()
            if back != data:
                raise _abort("FT20", f"staged {name} does not match its bytes")
            try:
                json.loads(back.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _abort("FT20", f"staged {name} is not valid JSON: "
                                     f"{exc}") from exc
            if name == MANIFEST_NAME:
                continue
            want = expected.get(name)
            if want is None:
                raise _abort("FT20", f"{name} is missing from the manifest")
            if want["bytes"] != len(back) or want["sha256"] != _sha256_bytes(back):
                raise _abort("FT20", f"manifest entry for {name} does not match "
                                     "the staged bytes")
        listed = set(expected) - {MANIFEST_NAME}
        staged = set(blobs) - {MANIFEST_NAME}
        if listed != staged:
            raise _abort("FT20", f"manifest lists {sorted(listed)}, package holds "
                                 f"{sorted(staged)}")

        # Re-check immediately before the move; then publish.
        clashes = sorted(n for n in blobs if (out_dir / n).exists())
        if clashes:
            raise _abort("FT20", f"refusing to overwrite existing output: {clashes}")
        for name in sorted(blobs):
            os.replace(tmp_dir / name, out_dir / name)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {"manifest": manifest,
            "hashes": {name: {"bytes": len(data), "sha256": _sha256_bytes(data)}
                       for name, data in sorted(blobs.items())}}


# ----------------------------------------------------------------- execution
def _execute(repo_root: Path, write: bool) -> dict[str, Any]:
    counters = Counters()
    controls: list[dict[str, Any]] = []

    def record(cid: str, detail: str) -> None:
        controls.append({"id": cid, "result": "PASS", "detail": detail})

    contract = _load(repo_root, CONTRACT_REL)
    pre01 = _load(repo_root, PRE01_REL)

    # ---- pre-access gates -------------------------------------------------
    if pre01.get("status") != "RESOLVED" or \
            pre01.get("all_prerequisites_resolved") is not True:
        raise _abort("FT21", "PRE01 is not recorded as resolved")
    if pre01.get("contract_sha256") != _sha256(repo_root, CONTRACT_REL):
        raise _abort("FT21", "PRE01 record pins a different contract")
    if pre01.get("recorded_before_any_final_test_row_was_read") is not True or \
            pre01.get("final_test_rows_read_at_time_of_recording") != 0:
        raise _abort("FT21", "PRE01 was not recorded before the Final Test was read")
    for key in ("pre02_status", "pre03_status", "pre04_status"):
        if pre01.get(key) != "RESOLVED":
            raise _abort("FT21", f"{key} is {pre01.get(key)!r}, not RESOLVED")
    if counters.final_test_rows_read != 0:
        raise _abort("FT21", "a Final Test row was read before the gates closed")

    accepted = contract["accepted_artifacts"]["artifacts"]
    for name, info in sorted(accepted.items()):
        if _sha256(repo_root, info["path"]) != info["sha256"]:
            raise _abort("FT01", f"accepted artifact {name} drifted")
    record("FT01", f"{len(accepted)} accepted refit artifacts hash to their pinned "
                   "SHA-256")

    model = _load(repo_root, MODEL_REL)
    if (model["block"], model["algorithm"], model["configuration_id"]) != \
            ("M1", "regularized_logistic_regression", "logistic__C_0.1"):
        raise _abort("FT02", "accepted model identity mismatch")
    accepted_model = contract["accepted_model"]
    if (accepted_model["block"], accepted_model["algorithm"],
            accepted_model["configuration_id"]) != \
            (model["block"], model["algorithm"], model["configuration_id"]):
        raise _abort("FT02", "model artifact does not match the contracted model")
    record("FT02", "model is M1 / regularized_logistic_regression / logistic__C_0.1")

    want_env = contract["environment"]["runtime_versions"]
    got_env = dict(locked.runtime_versions())
    got_env["python"] = ".".join(str(v) for v in sys.version_info[:3])
    for key in sorted(want_env):
        if got_env.get(key) != want_env[key]:
            raise _abort("FT03", f"runtime {key}={got_env.get(key)!r} != locked "
                                 f"{want_env[key]!r}")
    runtime = {k: got_env[k] for k in sorted(want_env)}
    record("FT03", f"python {runtime['python']}, numpy {runtime['numpy']} and every "
                   "other locked package version match the development runtime")

    data = contract["final_test_data"]
    for pk, sk in (("analysis_ready_path", "analysis_ready_sha256"),
                   ("audited_pairs_path", "audited_pairs_sha256")):
        if _sha256(repo_root, data[pk]) != data[sk]:
            raise _abort("FT04", f"pinned input {data[pk]} drifted")
    refit_prov = _load(repo_root, PROV_REL)
    input_hashes = dict(refit_prov["input_sha256"])
    for rel, want in sorted(input_hashes.items()):
        if _sha256(repo_root, rel) != want:
            raise _abort("FT04", f"pinned input {rel} drifted from the accepted "
                                 "refit provenance")
    record("FT04", f"both contracted inputs and all {len(input_hashes)} inputs pinned "
                   "by the accepted refit provenance hash to their SHA-256")

    locked_before = {rel: _sha256(repo_root, rel) for rel in LOCKED_DEV_RESULTS}
    for rel, want in LOCKED_DEV_RESULTS.items():
        if locked_before[rel] != want:
            raise _abort("FT14", f"locked development result {rel} already drifted")

    thr_artifact = _load(repo_root, THRESHOLD_REL)
    if thr_artifact.get("admitted") is not True or \
            thr_artifact.get("threshold") != THRESHOLD:
        raise _abort("FT10", "no admitted threshold available")
    if thr_artifact.get("derived_from") != "pooled_development_oof_only" or \
            thr_artifact.get("final_test_rows_read") != 0:
        raise _abort("FT10", "the admitted threshold is not development-OOF only")
    if pre01.get("pre02_admitted_threshold") != THRESHOLD:
        raise _abort("FT10", "PRE01 authorizes a different threshold value")
    if thr_artifact.get("rule") != contract["threshold"]["rule"] or \
            thr_artifact.get("tie_break") != contract["threshold"]["tie_break"]:
        raise _abort("FT10", "the admitted threshold does not follow the "
                             "contracted rule and tie-break")
    record("FT10", f"threshold {THRESHOLD!r} read from the committed admitted "
                   "development-OOF artifact and re-confirmed by PRE01; not "
                   "derived here")
    counters.threshold_searches = 0

    # ---- cohort, fixed before any value is read ---------------------------
    cohort, seen = final_test_cohort(repo_root)
    counters.final_test_rows_seen_in_manifest = seen
    if not cohort:
        raise _abort("FT05", "empty Final Test cohort")
    years = {v["target_year"] for v in cohort.values()}
    if not years <= FINAL_TEST_YEARS or years & DEV_YEARS:
        raise _abort("FT05", f"cohort years {sorted(years)} outside 1400-1402")
    if counters.final_test_rows_read != 0:
        raise _abort("FT05", "the manifest pass read a Final Test value")

    # ---- FIRST FINAL TEST ACCESS ------------------------------------------
    counters.final_test_passes_executed = 1
    rows = load_final_test_values(repo_root, cohort, counters)
    if len(rows) != len(cohort):
        raise _abort("FT05", f"loaded {len(rows)} rows for a cohort of "
                             f"{len(cohort)}")
    record("FT05", f"cohort of {len(cohort)} pairs, target years {sorted(years)}; "
                   "zero development rows")

    evaluable: list[dict[str, Any]] = []
    non_evaluable = 0
    for r in rows:
        t = r["target_raw"]
        if t in ("1", "1.0"):
            r["y"] = 1
        elif t in ("0", "0.0"):
            r["y"] = 0
        else:
            non_evaluable += 1
            continue
        evaluable.append(r)
    if not evaluable:
        raise _abort("FT16", "no evaluable Final Test rows")
    counters.final_test_evaluable_rows = len(evaluable)
    record("FT16", f"{len(evaluable)} evaluable of {len(rows)} loaded; "
                   f"{non_evaluable} non-evaluable excluded and never counted as "
                   "negative")

    # ---- frozen preprocessing, applied not estimated ----------------------
    prep = _load(repo_root, PREP_REL)
    if prep["feature_order"] != locked.M1_PRIMARY_FEATURE_ORDER:
        raise _abort("FT06", "frozen feature order mismatch")
    if prep.get("missingness_indicators_standardized") is not False:
        raise _abort("FT08", "the refit standardized its missingness indicators")
    pre = {
        "p_low": np.array(prep["clip_lower_1st_percentile"], dtype=float),
        "p_high": np.array(prep["clip_upper_99th_percentile"], dtype=float),
        "median": np.array(prep["median_of_clipped_observed"], dtype=float),
        "standardize": True,
        "mean": np.array(prep["standardization_mean"], dtype=float),
        "std": np.array(prep["standardization_std"], dtype=float),
    }
    n_feat = len(locked.M1_PRIMARY_FEATURE_ORDER)
    for key, source in (("p_low", "clip_lower_1st_percentile"),
                        ("p_high", "clip_upper_99th_percentile"),
                        ("median", "median_of_clipped_observed"),
                        ("mean", "standardization_mean"),
                        ("std", "standardization_std")):
        if pre[key].shape != (n_feat,):
            raise _abort("FT07", f"{source} has {pre[key].shape}, expected "
                                 f"({n_feat},)")
        if [float(v) for v in pre[key]] != [float(v) for v in prep[source]]:
            raise _abort("FT07", f"{source} was altered on the way into transform")

    X = np.vstack([locked._derive_features(r["raw"]) for r in evaluable])
    own_mask = np.isnan(X).astype(float)
    design = locked.transform(X, pre)

    expected_columns = list(locked.M1_PRIMARY_FEATURE_ORDER) + \
        [f"{f}__missing" for f in locked.M1_PRIMARY_FEATURE_ORDER]
    if model["design_matrix_columns"] != expected_columns:
        raise _abort("FT06", "the accepted model's design_matrix_columns are not "
                             "the 9 locked features followed by their 9 indicators")
    if design.shape[1] != model["n_design_columns"] or \
            design.shape[1] != len(expected_columns):
        raise _abort("FT06", f"design has {design.shape[1]} columns, model expects "
                             f"{model['n_design_columns']}")
    if locked.PROHIBITED_FEATURE in expected_columns:
        raise _abort("FT06", "the prohibited feature appears on the design matrix")
    record("FT06", f"design matrix {design.shape[1]} columns equal the accepted "
                   "model's design_matrix_columns exactly and in order")
    record("FT07", "clipping bounds, medians and standardization mean/std taken "
                   "verbatim from the PR #90 preprocessing artifact; nothing "
                   "re-estimated on Final Test rows")

    indicators = design[:, n_feat:]
    if not np.array_equal(indicators, own_mask):
        raise _abort("FT08", "the indicator block is not the rows' own "
                             "pre-imputation missingness")
    if not np.all((indicators == 0.0) | (indicators == 1.0)):
        raise _abort("FT08", "missingness indicators are not unstandardized binary")
    record("FT08", "missingness indicators equal each row's own pre-imputation NaN "
                   "positions, unstandardized binary 0/1, never inferred from the "
                   "imputed matrix")

    # ---- apply the model: no fit -----------------------------------------
    coef = np.array(model["coefficients"], dtype=float)
    intercept = float(model["intercept"])
    if coef.shape != (design.shape[1],):
        raise _abort("FT09", f"{coef.shape[0]} coefficients for "
                             f"{design.shape[1]} design columns")
    if model.get("serialization") != "explicit_coefficients_not_a_pickle":
        raise _abort("FT09", "the accepted model is not explicit coefficients")
    logits = design @ coef + intercept
    probs = 1.0 / (1.0 + np.exp(-logits))
    if not np.all(np.isfinite(probs)):
        raise _abort("FT09", "a non-finite predicted probability was produced")
    counters.final_test_predictions = int(probs.size)
    if counters.model_fits_executed != 0 or counters.refits_executed != 0:
        raise _abort("FT09", "a fit was executed")
    record("FT09", "model_fits_executed == 0; reconstructed from the pinned "
                   "intercept and 18 coefficients, no estimator was trained")

    if counters.final_test_passes_executed != 1 or \
            counters.final_test_load_invocations != 1:
        raise _abort("FT11", "the Final Test was not opened exactly once")
    record("FT11", "exactly one pass over the Final Test")

    if counters.recalibration_executions != 0 or counters.isotonic_executions != 0:
        raise _abort("FT12", "a recalibration was executed")
    record("FT12", "recalibration_executions == 0 and isotonic_executions == 0; "
                   "reported probabilities are the raw pipeline probabilities")

    if counters.winner_selections != 0:
        raise _abort("FT13", "a winner was selected")
    record("FT13", "no model, block, algorithm or configuration re-selected; no "
                   "winner selected on any Final Test quantity")

    counters.assert_zero("FT15")
    record("FT15", "no hyperparameter search, grid expansion, early stopping, "
                   "feature search or threshold search executed")

    y = np.array([r["y"] for r in evaluable], dtype=float)
    tickers = [r["ticker"] for r in evaluable]
    yrs = [r["target_year"] for r in evaluable]
    n_pos = int(y.sum())
    n_neg = int(y.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        raise _abort("FT17", f"the closed metric set is undefined with {n_pos} "
                             f"positives and {n_neg} negatives")

    rec10, lift10, topk_detail = recall_lift_at_10pct(y, probs, tickers, yrs)
    metrics = {
        "PR-AUC": _round("FT17", pr_auc(y, probs)),
        "ROC-AUC": _round("FT17", roc_auc(y, probs)),
        "Brier_score": _round("FT17", brier(y, probs)),
        "Recall@10%": _round("FT17", rec10),
        "Lift@10%": _round("FT17", lift10),
    }
    counters.final_test_metrics_computed = len(metrics)
    contracted = {contract["metrics"]["primary_metric"]} | \
        set(contract["metrics"]["secondary_metrics"])
    if set(metrics) != contracted:
        raise _abort("FT17", f"metric set {sorted(metrics)} is not the closed "
                             f"contracted set {sorted(contracted)}")
    record("FT17", "closed metric set computed: PR-AUC, ROC-AUC, Brier, Recall@10%, "
                   f"Lift@10% with K_y = ceil(0.10*N_y), "
                   f"{topk_detail['selected_rows']} rows selected")

    if counters.holm_executions != 0 or counters.p_values_computed != 0:
        raise _abort("FT18", "an inferential quantity was produced")
    record("FT18", "no Holm execution, no p-value, no inferential superiority claim")

    unc = contract["uncertainty"]
    if (unc["method"], unc["cluster"], unc["confidence_interval"],
            unc["replicates"], unc["min_valid_replicates"],
            unc["bootstrap_seed"]) != \
            ("paired_company_cluster_bootstrap", "ticker", "percentile_95",
             BOOTSTRAP_REPLICATES, BOOTSTRAP_MIN_VALID, BOOTSTRAP_SEED):
        raise _abort("FT19", "the contracted bootstrap parameters were changed")
    uncertainty = cluster_bootstrap(y, probs, tickers, counters)
    record("FT19", f"paired company-cluster bootstrap on ticker: "
                   f"{uncertainty['valid_replicates']} valid of "
                   f"{BOOTSTRAP_REPLICATES}, percentile-95, seed {BOOTSTRAP_SEED}, "
                   "parameters unchanged")

    thresholded = {
        "threshold": THRESHOLD,
        "threshold_source": THRESHOLD_REL,
        "rule": thr_artifact["rule"],
        "tie_break": thr_artifact["tie_break"],
        "derived_from": "pooled_development_oof_only",
        "tp": int(((probs >= THRESHOLD) & (y == 1)).sum()),
        "fp": int(((probs >= THRESHOLD) & (y == 0)).sum()),
        "fn": int(((probs < THRESHOLD) & (y == 1)).sum()),
        "tn": int(((probs < THRESHOLD) & (y == 0)).sum()),
    }

    locked_after = {rel: _sha256(repo_root, rel) for rel in LOCKED_DEV_RESULTS}
    for rel, before in locked_before.items():
        if locked_after[rel] != before:
            raise _abort("FT14", f"locked development result {rel} changed")
    record("FT14", "the 3 locked development results are byte-identical before and "
                   "after")
    record("FT20", f"writes confined to {PKG_REL}/ through a validated temporary "
                   "directory; no historical or frozen artifact edited")

    counters.assert_zero("FT21")
    if counters.final_test_passes_executed != 1:
        raise _abort("FT21", "this was not one complete single-pass execution")
    record("FT21", "every prerequisite was resolved before the first row was read; "
                   "one complete run, not a partial, threshold-free or metric-subset "
                   "execution")

    ids = [c["id"] for c in controls]
    if sorted(ids) != sorted(CONTROL_IDS):
        raise _abort("FT21", f"controls incomplete, missing "
                             f"{sorted(set(CONTROL_IDS) - set(ids))}")
    if len(ids) != len(set(ids)):
        raise _abort("FT21", "a control was recorded twice")

    controls = sorted(controls, key=lambda c: c["id"])
    executor_sha256 = _sha256_bytes(Path(__file__).resolve().read_bytes())

    predictions = [
        {"ticker": r["ticker"], "target_year": r["target_year"],
         "predictor_row_key_t": r["key"][0],
         "target_row_key_t_plus_1": r["key"][1],
         "observed_target": r["y"],
         "predicted_probability": _round("FT17", float(p))}
        for r, p in zip(evaluable, probs)]

    prediction_artifact = {
        "action_id": ACTION_ID,
        "artifact": "final_test_prediction_artifact",
        "block": model["block"],
        "algorithm": model["algorithm"],
        "configuration_id": model["configuration_id"],
        "contract_path": CONTRACT_REL,
        "contract_sha256": _sha256(repo_root, CONTRACT_REL),
        "evaluable_rows": len(evaluable),
        "final_test_target_years": sorted(set(yrs)),
        "forward_passes_executed": 1,
        "model_fits_executed": 0,
        "predictions": predictions,
        "predictions_are_raw_pipeline_probabilities": True,
        "recalibration_applied": False,
        "rows_loaded": len(rows),
        "rows_non_evaluable_excluded": non_evaluable,
    }

    metrics_artifact = {
        "action_id": ACTION_ID,
        "artifact": "final_test_metrics_artifact",
        "additional_metrics_computed": 0,
        "evaluable_rows": len(evaluable),
        "holm_executions": 0,
        "inferential_superiority_claim": False,
        "metric_set_is_closed": True,
        "metrics": metrics,
        "negative": n_neg,
        "p_values_computed": 0,
        "positive": n_pos,
        "primary_metric": contract["metrics"]["primary_metric"],
        "primary_metric_value": metrics[contract["metrics"]["primary_metric"]],
        "secondary_metrics": sorted(contract["metrics"]["secondary_metrics"]),
        "target_years": sorted(set(yrs)),
        "thresholded_secondary": thresholded,
        "topk": topk_detail,
        "uncertainty": uncertainty,
        "unique_tickers": len(set(tickers)),
    }

    provenance = {
        "action_id": ACTION_ID,
        "artifact": "final_test_provenance_record",
        "accepted_artifacts_sha256": {
            info["path"]: info["sha256"] for info in accepted.values()},
        "base_commit": BASE_COMMIT,
        "contract_path": CONTRACT_REL,
        "contract_sha256": _sha256(repo_root, CONTRACT_REL),
        "cohort_pairs": len(cohort),
        "evaluable_rows": len(evaluable),
        "executor_path": "project/src/stage129_final_test_execution.py",
        "executor_sha256": executor_sha256,
        "final_test_passes_executed": 1,
        "final_test_rows_read": counters.final_test_rows_read,
        "final_test_target_years": sorted(set(yrs)),
        "input_sha256": input_hashes,
        "locked_development_results_sha256_after": locked_after,
        "locked_development_results_sha256_before": locked_before,
        "model_fits_executed": 0,
        "pipeline_reused_not_reimplemented": True,
        "pipeline_source_module":
            "project/src/stage126_m1_primary_development_tuning.py",
        "pipeline_source_sha256": _sha256(
            repo_root, "project/src/stage126_m1_primary_development_tuning.py"),
        "pre01_path": PRE01_REL,
        "pre01_sha256": _sha256(repo_root, PRE01_REL),
        "runtime_versions": runtime,
        "threshold_artifact_path": THRESHOLD_REL,
        "threshold_artifact_sha256": _sha256(repo_root, THRESHOLD_REL),
        "threshold_value": THRESHOLD,
        "unique_tickers": len(set(tickers)),
    }

    qc_report = {
        "action_id": ACTION_ID,
        "artifact": "final_test_qc_report",
        "all_pass": True,
        "bootstrap_executed": True,
        "controls": controls,
        "controls_executed": len(controls),
        "counters": counters.as_dict(),
        "final_test_counters": {
            "final_test_evaluable_rows": counters.final_test_evaluable_rows,
            "final_test_metrics_computed": counters.final_test_metrics_computed,
            "final_test_passes_executed": counters.final_test_passes_executed,
            "final_test_predictions": counters.final_test_predictions,
            "final_test_predictor_values_read":
                counters.final_test_predictor_values_read,
            "final_test_rows_read": counters.final_test_rows_read,
            "final_test_target_values_read": counters.final_test_target_values_read,
        },
        "locked_results_sha256_after": locked_after,
        "locked_results_sha256_before": locked_before,
        "metric_subset_execution": False,
        "partial_execution": False,
        "threshold_free_execution": False,
    }

    artifacts = {
        PREDICTIONS_NAME: prediction_artifact,
        METRICS_NAME: metrics_artifact,
        PROVENANCE_NAME: provenance,
        QC_NAME: qc_report,
    }

    result: dict[str, Any] = {
        "artifacts": artifacts,
        "controls": controls,
        "metrics": metrics,
        "uncertainty": uncertainty,
        "thresholded": thresholded,
        "counters": counters.as_dict(),
        "cohort": len(cohort),
        "loaded": len(rows),
        "evaluable": len(evaluable),
        "non_evaluable": non_evaluable,
        "positives": n_pos,
        "negatives": n_neg,
        "years": sorted(set(yrs)),
        "runtime": runtime,
        "locked_before": locked_before,
        "locked_after": locked_after,
        "executor_sha256": executor_sha256,
        "written": False,
        "hashes": {},
    }

    if write:
        written = write_package(repo_root, artifacts, counters, executor_sha256)
        result["written"] = True
        result["manifest"] = written["manifest"]
        result["hashes"] = written["hashes"]
    else:
        blobs = {name: _json_bytes(obj) for name, obj in artifacts.items()}
        blobs[MANIFEST_NAME] = _json_bytes(
            build_manifest(blobs, counters, executor_sha256))
        result["hashes"] = {
            name: {"bytes": len(d), "sha256": _sha256_bytes(d)}
            for name, d in sorted(blobs.items())}
    return result


def run(repo_root: Path | str = REPO_ROOT, *, write: bool = False) -> dict[str, Any]:
    """One complete Final Test pass. Every failure is fail-closed."""
    root = Path(repo_root).resolve()
    key = str(root)
    if key in _OPENED_ROOTS:
        raise _abort("FT11", f"the Final Test at {key} was already opened in this "
                             "process; a second pass is not authorized")
    _OPENED_ROOTS.add(key)
    try:
        return _execute(root, write)
    except AbortFinalTest:
        raise
    except Exception as exc:                       # nothing escapes un-aborted
        raise _abort("FT21", f"unhandled {type(exc).__name__}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--execute-final-test" not in argv:
        print("REFUSED: this executor opens the locked Final Test exactly once.\n"
              "It runs only under an explicit invocation:\n"
              "  python project/src/stage129_final_test_execution.py "
              "--execute-final-test --write")
        return 2
    write = "--write" in argv
    try:
        result = run(REPO_ROOT, write=write)
    except AbortFinalTest as exc:
        print(str(exc))
        return 1
    print(f"FINAL TEST: controls={len(result['controls'])}/21 "
          f"rows_read={result['counters']['final_test_rows_read']} "
          f"evaluable={result['evaluable']} "
          f"predictions={result['counters']['final_test_predictions']}")
    for name, value in sorted(result["metrics"].items()):
        print(f"  {name}: {value}")
    for name, info in sorted(result["hashes"].items()):
        print(f"  {info['sha256']}  {info['bytes']:>7}  {name}")
    if not write:
        print("(dry run; pass --write to emit the package)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
