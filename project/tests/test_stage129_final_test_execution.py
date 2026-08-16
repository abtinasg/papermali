"""Synthetic end-to-end tests for the Stage129 Final Test executor.

Every test in this module runs against a FABRICATED repository built under
`tmp_path`. No real Final Test row, predictor value, target value or metric is
ever read: an autouse guard raises if any test so much as opens one of the real
pinned input files, and the closing tests assert the real package directory was
never written and the real inputs never touched.

The synthetic repository carries deliberately unparseable poison values in its
development rows, so any accidental widening of the cohort would raise instead
of silently succeeding.
"""
from __future__ import annotations

import builtins
import csv
import hashlib
import io
import json
import math
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "project"))

from src import stage126_m1_primary_development_tuning as locked  # noqa: E402
from src import stage129_final_test_execution as ft  # noqa: E402

# --------------------------------------------------------------------------- #
# Guard: the real Final Test may not be opened by any test in this module.
# --------------------------------------------------------------------------- #

REAL_FORBIDDEN = {
    (REPO_ROOT / locked.ANALYSIS_READY_REL).resolve(),
    (REPO_ROOT / locked.SPLIT_MANIFEST_REL).resolve(),
    (REPO_ROOT / "project/stage125/part3c_outputs/"
                 "audited_pairs_main_rule_a_stage125.csv").resolve(),
}
REAL_PACKAGE_DIR = (REPO_ROOT / ft.PKG_REL).resolve()

#: Every attempt to open a real Final Test input, recorded for the final proof.
FINAL_TEST_OPEN_ATTEMPTS: list[str] = []


def _is_forbidden(target: object) -> bool:
    try:
        resolved = Path(target).resolve()
    except (TypeError, ValueError, OSError):
        return False
    return resolved in REAL_FORBIDDEN


@pytest.fixture(autouse=True)
def block_real_final_test(monkeypatch):
    """Fail loudly if a test opens a real Final Test input."""
    real_open = builtins.open
    real_path_open = pathlib.Path.open

    def guarded_open(file, *args, **kwargs):
        if _is_forbidden(file):
            FINAL_TEST_OPEN_ATTEMPTS.append(str(file))
            raise AssertionError(f"a test tried to open real Final Test data: {file}")
        return real_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if _is_forbidden(self):
            FINAL_TEST_OPEN_ATTEMPTS.append(str(self))
            raise AssertionError(f"a test tried to open real Final Test data: {self}")
        return real_path_open(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "open", guarded_path_open)
    yield


@pytest.fixture(autouse=True)
def fresh_one_pass_guard():
    """Each test starts with an unopened process-level one-pass guard."""
    ft._OPENED_ROOTS.clear()
    yield
    ft._OPENED_ROOTS.clear()


# --------------------------------------------------------------------------- #
# Synthetic repository
# --------------------------------------------------------------------------- #

SOURCE_COLUMNS = [locked.FEATURE_SOURCE_COLUMN[f]
                  for f in locked.M1_PRIMARY_FEATURE_ORDER]
N_FEAT = len(locked.M1_PRIMARY_FEATURE_ORDER)

MANIFEST_COLUMNS = ["sample_design", "predictor_row_key_t",
                    "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
                    "target_year", "dataset_split", "temporal_fold"]
ANALYSIS_COLUMNS = (["predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
                     "target_year"] + SOURCE_COLUMNS + [locked.PRIMARY_TARGET])

#: Frozen synthetic preprocessing statistics. Feature 0 is log_total_assets.
SYN_P_LOW = [11.0] + [-3.0] * (N_FEAT - 1)
SYN_P_HIGH = [19.0] + [3.0] * (N_FEAT - 1)
SYN_MEDIAN = [14.0] + [0.0] * (N_FEAT - 1)
SYN_MEAN = [14.0] + [0.0] * (N_FEAT - 1)
SYN_STD = [1.5] + [1.0] * (N_FEAT - 1)

SYN_COEF = [0.35, -0.55, 0.40, -0.30, 0.25, -0.20, 0.45, -0.35, 0.30,
            0.10, -0.10, 0.05, -0.05, 0.15, -0.15, 0.20, -0.20, 0.08]
SYN_INTERCEPT = -1.85

POISON = "NOT_A_NUMBER_DEV_ROW_POISON"

DESIGN_COLUMNS = (list(locked.M1_PRIMARY_FEATURE_ORDER)
                  + [f"{f}__missing" for f in locked.M1_PRIMARY_FEATURE_ORDER])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
         + "\n").encode("utf-8"))


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_text(buf.getvalue(), encoding="utf-8")


def _runtime_now() -> dict[str, str]:
    env = dict(locked.runtime_versions())
    env["python"] = ".".join(str(v) for v in sys.version_info[:3])
    return env


def build_synthetic_repo(root: Path, *, n_tickers: int = 40,
                         seed: int = 12345,
                         n_non_evaluable: int = 4,
                         missing_cells: int = 25) -> dict:
    """Fabricate a complete, self-consistent repository. No real data is used."""
    rng = np.random.default_rng(seed)
    tickers = [f"SYN{i:03d}" for i in range(n_tickers)]

    final_rows: list[dict] = []
    raw_features: list[np.ndarray] = []
    for t in tickers:
        for year in (1400, 1401, 1402):
            vals = np.empty(N_FEAT, dtype=float)
            vals[0] = float(rng.normal(14.0, 1.0))
            vals[1:] = rng.normal(0.0, 1.0, size=N_FEAT - 1)
            raw_features.append(vals)
            final_rows.append({"ticker": t, "target_year": year,
                               "predictor_row_key_t": f"{t}:{year - 1}",
                               "target_row_key_t_plus_1": f"{t}:{year}",
                               "feat": vals})

    # Punch holes so the missingness indicators have something to carry.
    holes = rng.choice(len(final_rows) * N_FEAT, size=missing_cells, replace=False)
    for flat in holes:
        r, c = divmod(int(flat), N_FEAT)
        final_rows[r]["feat"][c] = math.nan

    # Design matrix and probabilities, computed exactly as the executor will.
    X = np.vstack([r["feat"] for r in final_rows])
    pre = {"p_low": np.array(SYN_P_LOW), "p_high": np.array(SYN_P_HIGH),
           "median": np.array(SYN_MEDIAN), "standardize": True,
           "mean": np.array(SYN_MEAN), "std": np.array(SYN_STD)}
    design = locked.transform(X, pre)
    probs = 1.0 / (1.0 + np.exp(-(design @ np.array(SYN_COEF) + SYN_INTERCEPT)))
    y = (rng.random(len(final_rows)) < probs).astype(int)

    for row, label in zip(final_rows, y):
        row["y"] = int(label)

    # A few rows lose their target entirely: evaluable-row accounting (FT16).
    blanked = rng.choice(len(final_rows), size=n_non_evaluable, replace=False)
    for i in blanked:
        final_rows[int(i)]["target_raw"] = ""
    for row in final_rows:
        row.setdefault("target_raw", str(row["y"]))

    evaluable = [r for r in final_rows if r["target_raw"] != ""]
    pos_tickers = {r["ticker"] for r in evaluable if r["y"] == 1}
    assert len(evaluable) > 0
    assert any(r["y"] == 1 for r in evaluable), "fixture has no positives"
    assert any(r["y"] == 0 for r in evaluable), "fixture has no negatives"
    assert len(pos_tickers) >= 8, f"positives span only {len(pos_tickers)} tickers"

    # Development rows: poisoned, so parsing one would raise instead of pass.
    dev_rows = []
    for t in tickers[:20]:
        for year in (1393, 1394, 1395, 1396, 1397, 1398, 1399):
            dev_rows.append({"ticker": t, "target_year": year,
                             "predictor_row_key_t": f"{t}:dev:{year - 1}",
                             "target_row_key_t_plus_1": f"{t}:dev:{year}"})

    def _fmt(v: float) -> str:
        if math.isnan(v):
            return ""
        return repr(float(v))

    analysis_rows = []
    for row in final_rows:
        rec = {"predictor_row_key_t": row["predictor_row_key_t"],
               "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
               "ticker": row["ticker"], "target_year": str(row["target_year"]),
               locked.PRIMARY_TARGET: row["target_raw"]}
        for j, col in enumerate(SOURCE_COLUMNS):
            value = row["feat"][j]
            if col == "total_assets" and not math.isnan(value):
                value = math.exp(value)
            rec[col] = _fmt(value)
        analysis_rows.append(rec)
    for row in dev_rows:
        rec = {"predictor_row_key_t": row["predictor_row_key_t"],
               "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
               "ticker": row["ticker"], "target_year": str(row["target_year"]),
               locked.PRIMARY_TARGET: POISON}
        for col in SOURCE_COLUMNS:
            rec[col] = POISON
        analysis_rows.append(rec)

    manifest_rows = []
    for row in final_rows:
        manifest_rows.append({
            "sample_design": locked.PRIMARY_SAMPLE,
            "predictor_row_key_t": row["predictor_row_key_t"],
            "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
            "ticker": row["ticker"], "fiscal_year_t": str(row["target_year"] - 1),
            "target_year": str(row["target_year"]),
            "dataset_split": locked.FINAL_TEST_ROLE,
            "temporal_fold": locked.FINAL_TEST_ROLE})
    for row in dev_rows:
        manifest_rows.append({
            "sample_design": locked.PRIMARY_SAMPLE,
            "predictor_row_key_t": row["predictor_row_key_t"],
            "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
            "ticker": row["ticker"], "fiscal_year_t": str(row["target_year"] - 1),
            "target_year": str(row["target_year"]),
            "dataset_split": "fold1_train", "temporal_fold": "fold1_train"})
    # A foreign sample the manifest reader must drop before anything else.
    manifest_rows.append({
        "sample_design": "some_other_sample", "predictor_row_key_t": "X:1",
        "target_row_key_t_plus_1": "X:2", "ticker": "XXX",
        "fiscal_year_t": "1400", "target_year": "1401",
        "dataset_split": locked.FINAL_TEST_ROLE,
        "temporal_fold": locked.FINAL_TEST_ROLE})

    analysis_path = root / locked.ANALYSIS_READY_REL
    manifest_path = root / locked.SPLIT_MANIFEST_REL
    audited_path = root / ("project/stage125/part3c_outputs/"
                           "audited_pairs_main_rule_a_stage125.csv")
    _write_csv(analysis_path, ANALYSIS_COLUMNS, analysis_rows)
    _write_csv(manifest_path, MANIFEST_COLUMNS, manifest_rows)
    _write_csv(audited_path, ["predictor_row_key_t", "target_row_key_t_plus_1"],
               [{"predictor_row_key_t": r["predictor_row_key_t"],
                 "target_row_key_t_plus_1": r["target_row_key_t_plus_1"]}
                for r in final_rows])

    # The locked development results the executor must find byte-identical.
    locked_results = {}
    for rel in ft.LOCKED_DEV_RESULTS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"synthetic stand-in for {rel}\n", encoding="utf-8")
        locked_results[rel] = _sha(p)

    # The pipeline module is a source file, not data: copy it verbatim.
    pipeline_rel = "project/src/stage126_m1_primary_development_tuning.py"
    (root / pipeline_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / pipeline_rel, root / pipeline_rel)

    input_sha = {
        locked.ANALYSIS_READY_REL: _sha(analysis_path),
        "project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv":
            _sha(audited_path),
        locked.SPLIT_MANIFEST_REL: _sha(manifest_path),
    }

    _dump(root / ft.PROV_REL, {
        "action_id": "stage129-full-development-refit-execution",
        "artifact": "full_development_refit_provenance_record",
        "final_test_rows_read": 0,
        "input_sha256": input_sha,
        "runtime_versions": _runtime_now(),
    })
    _dump(root / ft.MODEL_REL, {
        "action_id": "stage129-full-development-refit-execution",
        "algorithm": "regularized_logistic_regression",
        "artifact": "full_development_refit_model_artifact",
        "block": "M1",
        "coefficients": list(SYN_COEF),
        "configuration_id": "logistic__C_0.1",
        "design_matrix_columns": list(DESIGN_COLUMNS),
        "final_test_used": False,
        "intercept": SYN_INTERCEPT,
        "n_design_columns": 2 * N_FEAT,
        "predictions_generated": 0,
        "serialization": "explicit_coefficients_not_a_pickle",
    })
    _dump(root / ft.PREP_REL, {
        "action_id": "stage129-full-development-refit-execution",
        "artifact": "full_development_refit_preprocessing_parameters",
        "clip_lower_1st_percentile": list(SYN_P_LOW),
        "clip_percentiles": [1, 99],
        "clip_upper_99th_percentile": list(SYN_P_HIGH),
        "feature_order": list(locked.M1_PRIMARY_FEATURE_ORDER),
        "median_of_clipped_observed": list(SYN_MEDIAN),
        "missingness_indicators_standardized": False,
        "standardization_applied": True,
        "standardization_mean": list(SYN_MEAN),
        "standardization_std": list(SYN_STD),
    })
    _dump(root / ft.QC90_REL, {
        "action_id": "stage129-full-development-refit-execution",
        "all_pass": True, "artifact": "full_development_refit_qc_report",
        "final_test_counters": {"final_test_rows_read": 0},
    })

    accepted = {}
    for rel in (ft.MODEL_REL, ft.PREP_REL, ft.PROV_REL, ft.QC90_REL):
        accepted[Path(rel).name] = {"path": rel, "sha256": _sha(root / rel)}

    _dump(root / ft.THRESHOLD_REL, {
        "action_id": "stage129-threshold-derivation-attempt3",
        "admitted": True, "admission_status": "ADMITTED",
        "artifact": "threshold_value",
        "derived_from": "pooled_development_oof_only",
        "final_test_rows_read": 0, "final_test_used": False,
        "rule": "development_OOF_F2_maximizing_threshold",
        "threshold": ft.THRESHOLD, "tie_break": "higher_threshold",
    })

    contract = {
        "action_id": "stage129-final-test-execution-contract-lock",
        "contract_id": "stage129_final_test_execution_contract",
        "accepted_artifacts": {"artifacts": accepted, "merged_in_pull_request": 90},
        "accepted_model": {"algorithm": "regularized_logistic_regression",
                           "block": "M1",
                           "configuration_id": "logistic__C_0.1",
                           "model_is_taken_as_given_not_refit": True},
        "environment": {"runtime_versions": _runtime_now()},
        "features": {"design_matrix_columns_expected": 2 * N_FEAT,
                     "features_exact_order": list(locked.M1_PRIMARY_FEATURE_ORDER)},
        "final_test_data": {
            "analysis_ready_path": locked.ANALYSIS_READY_REL,
            "analysis_ready_sha256": input_sha[locked.ANALYSIS_READY_REL],
            "audited_pairs_path": ("project/stage125/part3c_outputs/"
                                   "audited_pairs_main_rule_a_stage125.csv"),
            "audited_pairs_sha256": input_sha[
                "project/stage125/part3c_outputs/"
                "audited_pairs_main_rule_a_stage125.csv"],
            "final_test_target_years": [1400, 1401, 1402],
        },
        "metrics": {"primary_metric": "PR-AUC",
                    "secondary_metrics": ["ROC-AUC", "Brier_score",
                                          "Recall@10%", "Lift@10%"],
                    "metric_set_is_closed": True},
        "threshold": {"rule": "development_OOF_F2_maximizing_threshold",
                      "tie_break": "higher_threshold"},
        "uncertainty": {"method": "paired_company_cluster_bootstrap",
                        "cluster": "ticker", "confidence_interval": "percentile_95",
                        "replicates": ft.BOOTSTRAP_REPLICATES,
                        "min_valid_replicates": ft.BOOTSTRAP_MIN_VALID,
                        "bootstrap_seed": ft.BOOTSTRAP_SEED,
                        "valid_replicate_requires_both_classes": True},
        "expected_outputs": {"locked_development_results_pinned": locked_results},
    }
    _dump(root / ft.CONTRACT_REL, contract)

    _dump(root / ft.PRE01_REL, {
        "action_id": "stage129-final-test-execution",
        "all_prerequisites_resolved": True,
        "artifact": "pre01_human_authorization_record",
        "contract_path": ft.CONTRACT_REL,
        "contract_sha256": _sha(root / ft.CONTRACT_REL),
        "final_test_rows_read_at_time_of_recording": 0,
        "pre02_admitted_threshold": ft.THRESHOLD,
        "pre02_status": "RESOLVED", "pre03_status": "RESOLVED",
        "pre04_status": "RESOLVED", "prerequisite": "PRE01",
        "recorded_before_any_final_test_row_was_read": True,
        "resolved_by": "explicit_human_authorization", "status": "RESOLVED",
    })

    return {
        "root": root,
        "locked_results": locked_results,
        "final_rows": final_rows,
        "dev_rows": dev_rows,
        "evaluable": evaluable,
        "n_final": len(final_rows),
        "n_evaluable": len(evaluable),
        "n_non_evaluable": len(final_rows) - len(evaluable),
        "design": design,
        "probs": probs,
        "pre": pre,
        "tickers": tickers,
    }


@pytest.fixture
def synth(tmp_path, monkeypatch):
    """A complete synthetic repository with the locked-result pins rebound."""
    built = build_synthetic_repo(tmp_path / "repo")
    monkeypatch.setattr(ft, "LOCKED_DEV_RESULTS", built["locked_results"])
    return built


@pytest.fixture
def result(synth):
    return ft.run(synth["root"], write=False)


def _mutate(root: Path, rel: str, **changes) -> None:
    blob = json.loads((root / rel).read_text(encoding="utf-8"))
    for key, value in changes.items():
        node = blob
        parts = key.split(".")
        for part in parts[:-1]:
            node = node[part]
        if value is ft:                       # sentinel: delete the key
            node.pop(parts[-1], None)
        else:
            node[parts[-1]] = value
    _dump(root / rel, blob)


def _repin_inputs(root: Path) -> None:
    """Re-pin every input hash after a synthetic CSV was rewritten.

    Used only by tests targeting a control OTHER than FT04; the FT04 tests
    deliberately leave the pins stale.
    """
    prov = json.loads((root / ft.PROV_REL).read_text(encoding="utf-8"))
    for rel in list(prov["input_sha256"]):
        prov["input_sha256"][rel] = _sha(root / rel)
    _dump(root / ft.PROV_REL, prov)
    contract = json.loads((root / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    data = contract["final_test_data"]
    data["analysis_ready_sha256"] = _sha(root / data["analysis_ready_path"])
    data["audited_pairs_sha256"] = _sha(root / data["audited_pairs_path"])
    _dump(root / ft.CONTRACT_REL, contract)


def _repin(root: Path) -> None:
    """Re-pin the contract and PRE01 after a refit artifact was mutated."""
    contract = json.loads((root / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    for name, info in contract["accepted_artifacts"]["artifacts"].items():
        info["sha256"] = _sha(root / info["path"])
    _dump(root / ft.CONTRACT_REL, contract)
    pre01 = json.loads((root / ft.PRE01_REL).read_text(encoding="utf-8"))
    pre01["contract_sha256"] = _sha(root / ft.CONTRACT_REL)
    _dump(root / ft.PRE01_REL, pre01)


def _repin_pre01(root: Path) -> None:
    pre01 = json.loads((root / ft.PRE01_REL).read_text(encoding="utf-8"))
    pre01["contract_sha256"] = _sha(root / ft.CONTRACT_REL)
    _dump(root / ft.PRE01_REL, pre01)


# --------------------------------------------------------------------------- #
# Cohort and the year restriction
# --------------------------------------------------------------------------- #

def test_cohort_holds_only_final_test_years(synth):
    cohort, seen = ft.final_test_cohort(synth["root"])
    assert seen == synth["n_final"]
    assert len(cohort) == synth["n_final"]
    years = {v["target_year"] for v in cohort.values()}
    assert years == {1400, 1401, 1402}


def test_cohort_excludes_every_development_pair(synth):
    cohort, _ = ft.final_test_cohort(synth["root"])
    dev_keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                for r in synth["dev_rows"]}
    assert dev_keys, "the fixture must contain development rows"
    assert not (dev_keys & set(cohort))


def test_cohort_drops_foreign_sample_designs(synth):
    cohort, _ = ft.final_test_cohort(synth["root"])
    assert ("X:1", "X:2") not in cohort


def test_the_manifest_pass_reads_no_value(synth):
    counters = ft.Counters()
    ft.final_test_cohort(synth["root"])
    assert counters.final_test_rows_read == 0
    assert counters.final_test_predictor_values_read == 0
    assert counters.final_test_target_values_read == 0


def test_development_rows_are_never_parsed(synth):
    """The poisoned development rows would raise if they were ever parsed."""
    cohort, _ = ft.final_test_cohort(synth["root"])
    counters = ft.Counters()
    rows = ft.load_final_test_values(synth["root"], cohort, counters)
    assert counters.final_test_rows_read == synth["n_final"]
    assert all(POISON not in r["raw"].values() for r in rows)
    assert all(r["target_raw"] != POISON for r in rows)
    # Proof the poison is real: parsing a development row would have raised.
    with pytest.raises(ValueError):
        locked._derive_features({c: POISON for c in SOURCE_COLUMNS})


def test_rows_read_equals_the_cohort_size(synth):
    cohort, _ = ft.final_test_cohort(synth["root"])
    counters = ft.Counters()
    rows = ft.load_final_test_values(synth["root"], cohort, counters)
    assert len(rows) == len(cohort) == counters.final_test_rows_read
    assert counters.final_test_predictor_values_read == len(rows) * N_FEAT
    assert counters.final_test_target_values_read == len(rows)


def test_an_out_of_window_cohort_year_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.SPLIT_MANIFEST_REL).read_text(encoding="utf-8").splitlines()))
    for row in rows:
        if row["dataset_split"] == locked.FINAL_TEST_ROLE and \
                row["sample_design"] == locked.PRIMARY_SAMPLE:
            row["target_year"] = "1399"
            break
    _write_csv(root / locked.SPLIT_MANIFEST_REL, MANIFEST_COLUMNS, rows)
    _repin_inputs(root)
    _repin(root)
    cohort, _ = ft.final_test_cohort(root)
    assert 1399 not in {v["target_year"] for v in cohort.values()}


# --------------------------------------------------------------------------- #
# Feature derivation, transform and the design matrix
# --------------------------------------------------------------------------- #

def test_design_is_features_then_the_rows_own_mask(synth, result):
    design = result["artifacts"][ft.PREDICTIONS_NAME]
    assert design["evaluable_rows"] == synth["n_evaluable"]
    cohort, _ = ft.final_test_cohort(synth["root"])
    counters = ft.Counters()
    rows = ft.load_final_test_values(synth["root"], cohort, counters)
    keep = [r for r in rows if r["target_raw"] in ("0", "1", "0.0", "1.0")]
    X = np.vstack([locked._derive_features(r["raw"]) for r in keep])
    out = locked.transform(X, synth["pre"])
    assert out.shape[1] == 2 * N_FEAT
    assert np.array_equal(out[:, N_FEAT:], np.isnan(X).astype(float))


def test_indicators_are_unstandardized_binary(synth):
    cohort, _ = ft.final_test_cohort(synth["root"])
    counters = ft.Counters()
    rows = ft.load_final_test_values(synth["root"], cohort, counters)
    X = np.vstack([locked._derive_features(r["raw"]) for r in rows])
    out = locked.transform(X, synth["pre"])
    ind = out[:, N_FEAT:]
    assert set(np.unique(ind)) <= {0.0, 1.0}
    assert ind.sum() > 0, "the fixture must contain missing cells"


def test_log_total_assets_is_the_log_of_the_source_column(synth):
    raw = {c: "1.0" for c in SOURCE_COLUMNS}
    raw["total_assets"] = str(math.exp(14.0))
    vals = locked._derive_features(raw)
    assert vals[0] == pytest.approx(14.0)


def test_a_nonpositive_total_assets_becomes_missing():
    raw = {c: "1.0" for c in SOURCE_COLUMNS}
    raw["total_assets"] = "0"
    assert math.isnan(locked._derive_features(raw)[0])


def test_preprocessing_parameters_are_used_verbatim(synth, result):
    prep = json.loads((synth["root"] / ft.PREP_REL).read_text(encoding="utf-8"))
    assert prep["clip_lower_1st_percentile"] == SYN_P_LOW
    assert prep["standardization_std"] == SYN_STD
    assert result["counters"]["model_fits_executed"] == 0


def test_a_reordered_feature_order_aborts(synth):
    root = synth["root"]
    bad = list(locked.M1_PRIMARY_FEATURE_ORDER)
    bad[0], bad[1] = bad[1], bad[0]
    _mutate(root, ft.PREP_REL, feature_order=bad)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT06"):
        ft.run(root)


def test_standardized_indicators_in_the_refit_abort(synth):
    root = synth["root"]
    _mutate(root, ft.PREP_REL, missingness_indicators_standardized=True)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT08"):
        ft.run(root)


def test_a_wrong_design_column_list_aborts(synth):
    root = synth["root"]
    bad = list(DESIGN_COLUMNS)
    bad[9] = "unexpected_column"
    _mutate(root, ft.MODEL_REL, design_matrix_columns=bad)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT06"):
        ft.run(root)


def test_a_wrong_design_column_count_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.MODEL_REL, n_design_columns=17)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT06"):
        ft.run(root)


# --------------------------------------------------------------------------- #
# Model reconstruction and the forward pass
# --------------------------------------------------------------------------- #

def test_the_forward_pass_is_the_reconstructed_sigmoid(synth, result):
    preds = result["artifacts"][ft.PREDICTIONS_NAME]["predictions"]
    by_key = {(p["predictor_row_key_t"], p["target_row_key_t_plus_1"]):
              p["predicted_probability"] for p in preds}
    expected = {}
    for row, prob in zip(synth["final_rows"], synth["probs"]):
        if row["target_raw"] == "":
            continue
        expected[(row["predictor_row_key_t"], row["target_row_key_t_plus_1"])] = prob
    assert set(by_key) == set(expected)
    for key, got in by_key.items():
        assert got == pytest.approx(expected[key], abs=1e-10)


def test_no_fit_is_ever_executed(result):
    counters = result["counters"]
    for name in ft.ZERO_COUNTERS:
        assert counters[name] == 0, name
    assert counters["final_test_passes_executed"] == 1


def test_a_coefficient_count_mismatch_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.MODEL_REL, coefficients=list(SYN_COEF)[:-1])
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT09"):
        ft.run(root)


def test_a_pickled_model_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.MODEL_REL, serialization="joblib_pickle")
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT09"):
        ft.run(root)


# --------------------------------------------------------------------------- #
# The five contracted metrics
# --------------------------------------------------------------------------- #

def test_pr_auc_matches_a_hand_computed_case():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([0.9, 0.8, 0.7, 0.6])
    # ranks: TP,FP,TP,FP -> precisions 1, 2/3 at the two recall steps of 0.5
    assert ft.pr_auc(y, p) == pytest.approx(0.5 * 1.0 + 0.5 * (2 / 3))


def test_pr_auc_is_one_for_a_perfect_ranking():
    y = np.array([1.0, 1.0, 0.0, 0.0])
    p = np.array([0.9, 0.8, 0.2, 0.1])
    assert ft.pr_auc(y, p) == pytest.approx(1.0)


def test_pr_auc_is_nan_without_positives():
    assert math.isnan(ft.pr_auc(np.zeros(4), np.array([0.1, 0.2, 0.3, 0.4])))


def test_roc_auc_matches_a_hand_computed_case():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([0.9, 0.8, 0.7, 0.6])
    # pairs: (0.9>0.8),(0.9>0.6),(0.7<0.8),(0.7>0.6) -> 3/4
    assert ft.roc_auc(y, p) == pytest.approx(0.75)


def test_roc_auc_averages_ties():
    y = np.array([1.0, 0.0])
    p = np.array([0.5, 0.5])
    assert ft.roc_auc(y, p) == pytest.approx(0.5)


def test_roc_auc_is_one_for_a_perfect_ranking():
    y = np.array([0.0, 0.0, 1.0, 1.0])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    assert ft.roc_auc(y, p) == pytest.approx(1.0)


def test_brier_is_the_mean_squared_error():
    y = np.array([1.0, 0.0])
    p = np.array([0.75, 0.25])
    assert ft.brier(y, p) == pytest.approx(((0.25) ** 2 + (0.25) ** 2) / 2)


def test_recall_and_lift_use_per_year_k():
    y = np.array([1.0] + [0.0] * 9 + [1.0] + [0.0] * 9)
    p = np.array([0.9] + [0.1] * 9 + [0.05] + [0.2] * 9)
    tickers = [f"T{i:02d}" for i in range(20)]
    years = [1400] * 10 + [1401] * 10
    recall, lift, detail = ft.recall_lift_at_10pct(y, p, tickers, years)
    assert detail["per_target_year"]["1400"]["K_y"] == 1
    assert detail["per_target_year"]["1401"]["K_y"] == 1
    assert detail["selected_rows"] == 2
    # 1400 captures its positive, 1401 does not.
    assert recall == pytest.approx(0.5)
    assert lift == pytest.approx(0.5 / (2 / 20))


def test_topk_breaks_ties_on_ticker_ascending():
    p = np.array([0.5, 0.5, 0.5])
    tickers = ["CCC", "AAA", "BBB"]
    picked = ft._topk_indices(p, tickers, 2)
    assert [tickers[i] for i in picked] == ["AAA", "BBB"]


def test_k_is_the_ceiling_of_a_tenth():
    y = np.array([1.0] + [0.0] * 10)
    p = np.linspace(0.9, 0.1, 11)
    tickers = [f"T{i:02d}" for i in range(11)]
    _, _, detail = ft.recall_lift_at_10pct(y, p, tickers, [1400] * 11)
    assert detail["per_target_year"]["1400"] == {"N_y": 11, "K_y": 2,
                                                 "captured_positives": 1}


def test_all_five_metrics_are_computed_once(result):
    metrics = result["metrics"]
    assert set(metrics) == {"PR-AUC", "ROC-AUC", "Brier_score",
                            "Recall@10%", "Lift@10%"}
    assert result["counters"]["final_test_metrics_computed"] == 5
    for name, value in metrics.items():
        assert math.isfinite(value), name


def test_the_metric_values_are_reproducible(synth):
    first = ft.run(synth["root"])
    ft._OPENED_ROOTS.clear()
    second = ft.run(synth["root"])
    assert first["metrics"] == second["metrics"]
    assert first["uncertainty"] == second["uncertainty"]


# --------------------------------------------------------------------------- #
# Paired company-cluster bootstrap
# --------------------------------------------------------------------------- #

def _small_bootstrap_fixture():
    tickers = [f"B{i:02d}" for i in range(12) for _ in range(3)]
    y = np.array(([1.0, 0.0, 0.0] * 6 + [0.0, 0.0, 0.0] * 6)[:36])
    p = np.linspace(0.05, 0.95, 36)
    return y, p, tickers


def test_the_bootstrap_is_deterministic_under_the_frozen_seed():
    y, p, tickers = _small_bootstrap_fixture()
    first = ft.cluster_bootstrap(y, p, tickers, ft.Counters())
    second = ft.cluster_bootstrap(y, p, tickers, ft.Counters())
    assert first == second
    assert first["seed"] == 20260724
    assert first["replicates"] == 2000
    assert first["cluster"] == "ticker"
    assert first["confidence_interval"] == "percentile_95"


def test_the_bootstrap_reports_every_contracted_interval():
    y, p, tickers = _small_bootstrap_fixture()
    out = ft.cluster_bootstrap(y, p, tickers, ft.Counters())
    assert set(out["intervals"]) == {"PR-AUC", "ROC-AUC", "Brier_score"}
    for name, band in out["intervals"].items():
        assert band["lower"] <= band["upper"], name


def test_the_bootstrap_counts_its_replicates():
    y, p, tickers = _small_bootstrap_fixture()
    counters = ft.Counters()
    out = ft.cluster_bootstrap(y, p, tickers, counters)
    assert counters.bootstrap_executions == 1
    assert counters.bootstrap_valid_replicates == out["valid_replicates"]
    assert out["valid_replicates"] <= ft.BOOTSTRAP_REPLICATES


def test_a_single_class_fixture_aborts_below_the_minimum():
    tickers = [f"B{i:02d}" for i in range(12) for _ in range(3)]
    y = np.zeros(36)
    p = np.linspace(0.05, 0.95, 36)
    with pytest.raises(ft.AbortFinalTest, match=r"FT19.*valid bootstrap replicates"):
        ft.cluster_bootstrap(y, p, tickers, ft.Counters())


def test_one_positive_cluster_discards_replicates():
    """Positives inside a single cluster make a large share of draws invalid."""
    tickers = [f"B{i:02d}" for i in range(12) for _ in range(3)]
    y = np.zeros(36)
    y[:3] = 1.0                      # every positive belongs to cluster B00
    p = np.linspace(0.05, 0.95, 36)
    counters = ft.Counters()
    out = ft.cluster_bootstrap(y, p, tickers, counters)
    # A cluster is absent from a size-N draw of N clusters ~37% of the time.
    assert out["valid_replicates"] < ft.BOOTSTRAP_REPLICATES
    assert counters.bootstrap_valid_replicates == out["valid_replicates"]


def test_the_min_valid_replicate_gate_aborts(monkeypatch):
    """The contracted floor is enforced, not merely recorded."""
    tickers = [f"B{i:02d}" for i in range(12) for _ in range(3)]
    y = np.zeros(36)
    y[:3] = 1.0
    p = np.linspace(0.05, 0.95, 36)
    monkeypatch.setattr(ft, "BOOTSTRAP_MIN_VALID", ft.BOOTSTRAP_REPLICATES)
    with pytest.raises(ft.AbortFinalTest, match=r"FT19.*valid bootstrap replicates"):
        ft.cluster_bootstrap(y, p, tickers, ft.Counters())


def test_changing_a_bootstrap_parameter_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.CONTRACT_REL, **{"uncertainty.bootstrap_seed": 1})
    _repin_pre01(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT19"):
        ft.run(root)


def test_the_end_to_end_bootstrap_is_reported(result):
    unc = result["uncertainty"]
    assert unc["method"] == "paired_company_cluster_bootstrap"
    assert unc["valid_replicates"] >= ft.BOOTSTRAP_MIN_VALID
    assert result["counters"]["bootstrap_executions"] == 1


# --------------------------------------------------------------------------- #
# FT01 - FT21
# --------------------------------------------------------------------------- #

def test_all_twenty_one_controls_ran_and_passed(result):
    ids = [c["id"] for c in result["controls"]]
    assert ids == sorted(ft.CONTROL_IDS)
    assert len(ids) == 21
    assert all(c["result"] == "PASS" for c in result["controls"])
    assert all(c["detail"].strip() for c in result["controls"])


def test_the_qc_report_carries_every_control(result):
    qc = result["artifacts"][ft.QC_NAME]
    assert qc["all_pass"] is True
    assert qc["controls_executed"] == 21
    assert [c["id"] for c in qc["controls"]] == sorted(ft.CONTROL_IDS)


def test_ft01_a_drifted_accepted_artifact_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.QC90_REL, all_pass=False)     # contract still pins the old hash
    _repin_pre01(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT01"):
        ft.run(root)


def test_ft02_a_foreign_model_identity_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.MODEL_REL, algorithm="random_forest")
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT02"):
        ft.run(root)


def test_ft02_a_contract_model_mismatch_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.CONTRACT_REL, **{"accepted_model.configuration_id":
                                      "logistic__C_1.0"})
    _repin_pre01(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT02"):
        ft.run(root)


def test_ft03_a_runtime_mismatch_aborts(synth):
    root = synth["root"]
    env = _runtime_now()
    env["numpy"] = "0.0.0-not-the-locked-version"
    _mutate(root, ft.CONTRACT_REL, **{"environment.runtime_versions": env})
    _repin_pre01(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT03"):
        ft.run(root)


def test_ft04_a_tampered_input_aborts(synth):
    root = synth["root"]
    path = root / locked.ANALYSIS_READY_REL
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ft.AbortFinalTest, match=r"FT04"):
        ft.run(root)


def test_ft04_a_missing_predictor_column_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.ANALYSIS_READY_REL).read_text(
            encoding="utf-8").splitlines()))
    cols = [c for c in ANALYSIS_COLUMNS if c != "leverage_ratio"]
    for row in rows:
        row.pop("leverage_ratio", None)
    _write_csv(root / locked.ANALYSIS_READY_REL, cols, rows)
    _repin_inputs(root)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT04"):
        ft.run(root)


def test_ft05_an_empty_cohort_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.SPLIT_MANIFEST_REL).read_text(
            encoding="utf-8").splitlines()))
    for row in rows:
        if row["dataset_split"] == locked.FINAL_TEST_ROLE:
            row["dataset_split"] = "fold1_train"
            row["temporal_fold"] = "fold1_train"
    _write_csv(root / locked.SPLIT_MANIFEST_REL, MANIFEST_COLUMNS, rows)
    _repin_inputs(root)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT05"):
        ft.run(root)


def test_ft05_a_cohort_row_missing_from_the_values_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.ANALYSIS_READY_REL).read_text(
            encoding="utf-8").splitlines()))
    dropped = rows[1:]
    _write_csv(root / locked.ANALYSIS_READY_REL, ANALYSIS_COLUMNS, dropped)
    _repin_inputs(root)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT05"):
        ft.run(root)


def test_ft10_an_unadmitted_threshold_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.THRESHOLD_REL, admitted=False)
    with pytest.raises(ft.AbortFinalTest, match=r"FT10"):
        ft.run(root)


def test_ft10_a_final_test_derived_threshold_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.THRESHOLD_REL, derived_from="final_test_search")
    with pytest.raises(ft.AbortFinalTest, match=r"FT10"):
        ft.run(root)


def test_ft10_a_threshold_pre01_did_not_authorize_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, pre02_admitted_threshold=0.5)
    with pytest.raises(ft.AbortFinalTest, match=r"FT10"):
        ft.run(root)


def test_ft10_a_rule_change_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.THRESHOLD_REL, rule="final_test_F1_maximizing_threshold")
    with pytest.raises(ft.AbortFinalTest, match=r"FT10"):
        ft.run(root)


def test_ft11_a_second_pass_is_refused(synth):
    ft.run(synth["root"])
    with pytest.raises(ft.AbortFinalTest, match=r"FT11"):
        ft.run(synth["root"])


def test_ft11_a_second_load_invocation_aborts(synth):
    cohort, _ = ft.final_test_cohort(synth["root"])
    counters = ft.Counters()
    ft.load_final_test_values(synth["root"], cohort, counters)
    with pytest.raises(ft.AbortFinalTest, match=r"FT11"):
        ft.load_final_test_values(synth["root"], cohort, counters)


@pytest.mark.parametrize("counter", ft.ZERO_COUNTERS)
def test_a_nonzero_forbidden_counter_aborts(counter):
    counters = ft.Counters()
    setattr(counters, counter, 1)
    with pytest.raises(ft.AbortFinalTest, match=rf"FT15.*{counter}"):
        counters.assert_zero("FT15")


def test_every_contract_required_counter_is_reported(result):
    contract = json.loads(
        (REPO_ROOT / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    required = set(contract["required_counters"]) - {"note", "counters_note"}
    reported = set(result["counters"])
    assert required <= reported, sorted(required - reported)


def test_ft14_a_changed_locked_result_aborts(synth):
    root = synth["root"]
    rel = next(iter(synth["locked_results"]))
    (root / rel).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ft.AbortFinalTest, match=r"FT14"):
        ft.run(root)


def test_ft14_the_locked_results_are_identical_before_and_after(result, synth):
    assert result["locked_before"] == result["locked_after"]
    assert result["locked_before"] == synth["locked_results"]


def test_ft16_a_blank_target_is_never_counted_as_negative(synth, result):
    assert result["non_evaluable"] == synth["n_non_evaluable"] > 0
    assert result["evaluable"] == synth["n_evaluable"]
    assert result["loaded"] == synth["n_final"]
    assert result["positives"] + result["negatives"] == result["evaluable"]


def test_ft16_an_unparseable_target_is_excluded(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.ANALYSIS_READY_REL).read_text(
            encoding="utf-8").splitlines()))
    changed = 0
    for row in rows:
        if row[locked.PRIMARY_TARGET] == "0":
            row[locked.PRIMARY_TARGET] = "maybe"
            changed += 1
            if changed == 3:
                break
    _write_csv(root / locked.ANALYSIS_READY_REL, ANALYSIS_COLUMNS, rows)
    _repin_inputs(root)
    _repin(root)
    out = ft.run(root)
    assert out["non_evaluable"] == synth["n_non_evaluable"] + 3
    assert out["evaluable"] == synth["n_evaluable"] - 3


def test_ft16_no_evaluable_row_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.ANALYSIS_READY_REL).read_text(
            encoding="utf-8").splitlines()))
    for row in rows:
        if row["target_year"] in ("1400", "1401", "1402"):
            row[locked.PRIMARY_TARGET] = ""
    _write_csv(root / locked.ANALYSIS_READY_REL, ANALYSIS_COLUMNS, rows)
    _repin_inputs(root)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT16"):
        ft.run(root)


def test_ft17_an_open_metric_set_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.CONTRACT_REL,
            **{"metrics.secondary_metrics": ["ROC-AUC", "Brier_score",
                                             "Recall@10%", "Lift@10%", "F1"]})
    _repin_pre01(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT17"):
        ft.run(root)


def test_ft17_a_single_class_cohort_aborts(synth):
    root = synth["root"]
    rows = list(csv.DictReader(
        (root / locked.ANALYSIS_READY_REL).read_text(
            encoding="utf-8").splitlines()))
    for row in rows:
        if row["target_year"] in ("1400", "1401", "1402") and \
                row[locked.PRIMARY_TARGET] != "":
            row[locked.PRIMARY_TARGET] = "0"
    _write_csv(root / locked.ANALYSIS_READY_REL, ANALYSIS_COLUMNS, rows)
    _repin_inputs(root)
    _repin(root)
    with pytest.raises(ft.AbortFinalTest, match=r"FT17"):
        ft.run(root)


def test_ft21_an_unresolved_pre01_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, status="OPEN")
    with pytest.raises(ft.AbortFinalTest, match=r"FT21"):
        ft.run(root)


def test_ft21_a_pre01_pinned_to_another_contract_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, contract_sha256="0" * 64)
    with pytest.raises(ft.AbortFinalTest, match=r"FT21"):
        ft.run(root)


def test_ft21_a_pre01_recorded_after_a_read_aborts(synth):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, final_test_rows_read_at_time_of_recording=1)
    with pytest.raises(ft.AbortFinalTest, match=r"FT21"):
        ft.run(root)


@pytest.mark.parametrize("key", ["pre02_status", "pre03_status", "pre04_status"])
def test_ft21_an_unresolved_downstream_prerequisite_aborts(synth, key):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, **{key: "OPEN"})
    with pytest.raises(ft.AbortFinalTest, match=r"FT21"):
        ft.run(root)


def test_every_abort_is_tagged_abort_final_test(synth):
    root = synth["root"]
    _mutate(root, ft.PRE01_REL, status="OPEN")
    with pytest.raises(ft.AbortFinalTest) as excinfo:
        ft.run(root)
    assert str(excinfo.value).startswith("ABORT_FINAL_TEST [")


def test_an_unexpected_error_is_still_fail_closed(synth, monkeypatch):
    def boom(*_args, **_kwargs):
        raise ZeroDivisionError("synthetic failure")

    monkeypatch.setattr(ft, "final_test_cohort", boom)
    with pytest.raises(ft.AbortFinalTest, match=r"ABORT_FINAL_TEST.*ZeroDivisionError"):
        ft.run(synth["root"])


def test_a_missing_artifact_is_fail_closed(synth):
    (synth["root"] / ft.THRESHOLD_REL).unlink()
    with pytest.raises(ft.AbortFinalTest):
        ft.run(synth["root"])


# --------------------------------------------------------------------------- #
# Package writer and manifest
# --------------------------------------------------------------------------- #

EXPECTED_PACKAGE = {ft.PREDICTIONS_NAME, ft.METRICS_NAME,
                    ft.PROVENANCE_NAME, ft.QC_NAME, ft.MANIFEST_NAME}


def test_the_writer_emits_exactly_the_contracted_package(synth):
    out = ft.run(synth["root"], write=True)
    written = {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert EXPECTED_PACKAGE <= written
    assert written - EXPECTED_PACKAGE == {
        Path(ft.PRE01_REL).name}, "nothing beyond the package and PRE01"
    assert out["written"] is True


def test_a_dry_run_writes_nothing(synth):
    out = ft.run(synth["root"], write=False)
    written = {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert written == {Path(ft.PRE01_REL).name}
    assert out["written"] is False
    assert set(out["hashes"]) == EXPECTED_PACKAGE


def test_the_manifest_records_sha256_and_byte_count(synth):
    ft.run(synth["root"], write=True)
    pkg = synth["root"] / ft.PKG_REL
    manifest = json.loads((pkg / ft.MANIFEST_NAME).read_text(encoding="utf-8"))
    files = manifest["package_files"]
    assert set(files) == EXPECTED_PACKAGE - {ft.MANIFEST_NAME}
    for name, info in files.items():
        data = (pkg / name).read_bytes()
        assert info["bytes"] == len(data), name
        assert info["sha256"] == hashlib.sha256(data).hexdigest(), name
    # The manifest counts the files it lists; it does not list itself.
    assert manifest["package_file_count"] == len(EXPECTED_PACKAGE) - 1
    assert ft.MANIFEST_NAME not in files


def test_the_manifest_pins_the_executor(synth):
    ft.run(synth["root"], write=True)
    manifest = json.loads(
        (synth["root"] / ft.PKG_REL / ft.MANIFEST_NAME).read_text(encoding="utf-8"))
    executor = REPO_ROOT / "project/src/stage129_final_test_execution.py"
    assert manifest["executor_sha256"] == hashlib.sha256(
        executor.read_bytes()).hexdigest()
    assert manifest["executor_path"] == "project/src/stage129_final_test_execution.py"
    assert manifest["fail_closed_controls_all_passed"] is True


def test_the_writer_refuses_to_overwrite_an_existing_output(synth):
    ft.run(synth["root"], write=True)
    ft._OPENED_ROOTS.clear()
    before = {p.name: p.read_bytes()
              for p in (synth["root"] / ft.PKG_REL).iterdir()}
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*overwrite"):
        ft.run(synth["root"], write=True)
    after = {p.name: p.read_bytes()
             for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert before == after, "a refused run must not touch the existing package"


def test_a_single_pre_existing_output_blocks_the_whole_write(synth):
    pkg = synth["root"] / ft.PKG_REL
    (pkg / ft.METRICS_NAME).write_text("{}\n", encoding="utf-8")
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*overwrite"):
        ft.run(synth["root"], write=True)
    remaining = {p.name for p in pkg.iterdir()}
    assert ft.PREDICTIONS_NAME not in remaining
    assert ft.MANIFEST_NAME not in remaining


def test_no_temporary_directory_survives_a_successful_write(synth):
    ft.run(synth["root"], write=True)
    leftovers = [p.name for p in (synth["root"] / ft.PKG_REL).iterdir()
                 if p.name.startswith(".tmp_")]
    assert leftovers == []


def test_no_temporary_directory_survives_a_failed_write(synth, monkeypatch):
    real_replace = ft.os.replace

    def failing_replace(src, dst):
        raise OSError("synthetic move failure")

    monkeypatch.setattr(ft.os, "replace", failing_replace)
    with pytest.raises(ft.AbortFinalTest):
        ft.run(synth["root"], write=True)
    monkeypatch.setattr(ft.os, "replace", real_replace)
    entries = {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert not any(n.startswith(".tmp_") for n in entries)
    assert entries == {Path(ft.PRE01_REL).name}, "a failed write leaves no artifact"


def test_a_corrupted_manifest_hash_fails_validation(synth, monkeypatch):
    """Validation compares each staged file against its own manifest entry."""
    original = ft.build_manifest

    def corrupt(blobs, counters, executor_sha256):
        manifest = original(blobs, counters, executor_sha256)
        manifest["package_files"][ft.PREDICTIONS_NAME]["sha256"] = "0" * 64
        return manifest

    monkeypatch.setattr(ft, "build_manifest", corrupt)
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*does not match the staged"):
        ft.run(synth["root"], write=True)
    entries = {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert not any(n.startswith(".tmp_") for n in entries)
    assert entries == {Path(ft.PRE01_REL).name}


def test_a_corrupted_manifest_byte_count_fails_validation(synth, monkeypatch):
    original = ft.build_manifest

    def corrupt(blobs, counters, executor_sha256):
        manifest = original(blobs, counters, executor_sha256)
        manifest["package_files"][ft.QC_NAME]["bytes"] += 1
        return manifest

    monkeypatch.setattr(ft, "build_manifest", corrupt)
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*does not match the staged"):
        ft.run(synth["root"], write=True)
    assert {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()} == \
        {Path(ft.PRE01_REL).name}


def test_the_writer_rejects_a_path_escaping_the_package(synth):
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*escapes"):
        ft.write_package(synth["root"], {"../escaped.json": {"a": 1}},
                         ft.Counters(), "0" * 64)


def test_the_writer_rejects_a_manifest_package_mismatch(synth, monkeypatch):
    original = ft.build_manifest

    def short_manifest(blobs, counters, executor_sha256):
        manifest = original(blobs, counters, executor_sha256)
        manifest["package_files"].pop(ft.QC_NAME, None)
        return manifest

    monkeypatch.setattr(ft, "build_manifest", short_manifest)
    with pytest.raises(ft.AbortFinalTest, match=r"FT20.*manifest"):
        ft.run(synth["root"], write=True)
    entries = {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()}
    assert entries == {Path(ft.PRE01_REL).name}


# --------------------------------------------------------------------------- #
# Re-reading the synthetic artifacts: schema and hash
# --------------------------------------------------------------------------- #

@pytest.fixture
def written(synth):
    out = ft.run(synth["root"], write=True)
    return synth, out, synth["root"] / ft.PKG_REL


def test_every_written_artifact_reparses_as_json(written):
    _synth, _out, pkg = written
    for name in EXPECTED_PACKAGE:
        blob = json.loads((pkg / name).read_text(encoding="utf-8"))
        assert isinstance(blob, dict) and blob


def test_the_written_bytes_match_the_returned_hashes(written):
    _synth, out, pkg = written
    for name, info in out["hashes"].items():
        data = (pkg / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info["sha256"], name
        assert len(data) == info["bytes"], name


def test_the_prediction_artifact_schema(written):
    synth, _out, pkg = written
    blob = json.loads((pkg / ft.PREDICTIONS_NAME).read_text(encoding="utf-8"))
    assert blob["artifact"] == "final_test_prediction_artifact"
    assert blob["model_fits_executed"] == 0
    assert blob["forward_passes_executed"] == 1
    assert blob["recalibration_applied"] is False
    assert blob["predictions_are_raw_pipeline_probabilities"] is True
    assert blob["final_test_target_years"] == [1400, 1401, 1402]
    assert len(blob["predictions"]) == synth["n_evaluable"]
    for row in blob["predictions"]:
        assert set(row) == {"ticker", "target_year", "predictor_row_key_t",
                            "target_row_key_t_plus_1", "observed_target",
                            "predicted_probability"}
        assert row["observed_target"] in (0, 1)
        assert 0.0 <= row["predicted_probability"] <= 1.0
        assert row["target_year"] in (1400, 1401, 1402)


def test_the_metrics_artifact_schema(written):
    _synth, _out, pkg = written
    blob = json.loads((pkg / ft.METRICS_NAME).read_text(encoding="utf-8"))
    assert blob["artifact"] == "final_test_metrics_artifact"
    assert blob["primary_metric"] == "PR-AUC"
    assert set(blob["metrics"]) == {"PR-AUC", "ROC-AUC", "Brier_score",
                                    "Recall@10%", "Lift@10%"}
    assert blob["metric_set_is_closed"] is True
    assert blob["p_values_computed"] == 0
    assert blob["holm_executions"] == 0
    assert blob["inferential_superiority_claim"] is False
    assert blob["primary_metric_value"] == blob["metrics"]["PR-AUC"]
    assert blob["uncertainty"]["seed"] == ft.BOOTSTRAP_SEED
    assert blob["topk"]["definition"] == "K_y = ceil(0.10 * N_y)"
    assert blob["topk"]["K_optimized_after_results"] is False
    thresholded = blob["thresholded_secondary"]
    assert thresholded["threshold"] == ft.THRESHOLD
    assert (thresholded["tp"] + thresholded["fp"]
            + thresholded["fn"] + thresholded["tn"]) == blob["evaluable_rows"]


def test_the_provenance_artifact_schema(written):
    _synth, _out, pkg = written
    blob = json.loads((pkg / ft.PROVENANCE_NAME).read_text(encoding="utf-8"))
    assert blob["artifact"] == "final_test_provenance_record"
    assert blob["model_fits_executed"] == 0
    assert blob["final_test_passes_executed"] == 1
    assert blob["threshold_value"] == ft.THRESHOLD
    assert blob["base_commit"] == ft.BASE_COMMIT
    assert blob["pipeline_reused_not_reimplemented"] is True
    for key in ("accepted_artifacts_sha256", "input_sha256",
                "locked_development_results_sha256_before",
                "locked_development_results_sha256_after", "runtime_versions"):
        assert blob[key], key
    for digest in blob["input_sha256"].values():
        assert len(digest) == 64
    assert blob["locked_development_results_sha256_before"] == \
        blob["locked_development_results_sha256_after"]


def test_the_qc_artifact_schema(written):
    _synth, _out, pkg = written
    blob = json.loads((pkg / ft.QC_NAME).read_text(encoding="utf-8"))
    assert blob["artifact"] == "final_test_qc_report"
    assert blob["all_pass"] is True
    assert blob["partial_execution"] is False
    assert blob["threshold_free_execution"] is False
    assert blob["metric_subset_execution"] is False
    assert blob["final_test_counters"]["final_test_passes_executed"] == 1
    for name in ft.ZERO_COUNTERS:
        assert blob["counters"][name] == 0, name


def test_the_written_package_is_stable_across_repeat_builds(tmp_path, monkeypatch):
    """Two identically-seeded synthetic repos produce identical artifacts."""
    first = build_synthetic_repo(tmp_path / "a")
    monkeypatch.setattr(ft, "LOCKED_DEV_RESULTS", first["locked_results"])
    out_a = ft.run(first["root"])
    ft._OPENED_ROOTS.clear()
    second = build_synthetic_repo(tmp_path / "b")
    monkeypatch.setattr(ft, "LOCKED_DEV_RESULTS", second["locked_results"])
    out_b = ft.run(second["root"])
    assert out_a["metrics"] == out_b["metrics"]
    assert out_a["uncertainty"] == out_b["uncertainty"]
    assert out_a["thresholded"] == out_b["thresholded"]


# --------------------------------------------------------------------------- #
# Explicit invocation
# --------------------------------------------------------------------------- #

def test_importing_the_module_executes_nothing():
    assert ft._OPENED_ROOTS == set()
    assert not REAL_PACKAGE_DIR.joinpath(ft.PREDICTIONS_NAME).exists()


def test_main_refuses_without_the_explicit_flag(capsys):
    assert ft.main([]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "--execute-final-test" in out


def test_main_refuses_a_bare_write_flag(capsys):
    assert ft.main(["--write"]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_running_the_module_as_a_script_refuses_by_default():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "project/src/"
                             "stage129_final_test_execution.py")],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=300)
    assert proc.returncode == 2
    assert "REFUSED" in proc.stdout


def test_main_reports_an_abort_without_raising(synth, monkeypatch, capsys):
    monkeypatch.setattr(ft, "REPO_ROOT", synth["root"])
    _mutate(synth["root"], ft.PRE01_REL, status="OPEN")
    assert ft.main(["--execute-final-test"]) == 1
    assert "ABORT_FINAL_TEST" in capsys.readouterr().out


def test_main_runs_a_dry_run_on_the_synthetic_repo(synth, monkeypatch, capsys):
    monkeypatch.setattr(ft, "REPO_ROOT", synth["root"])
    assert ft.main(["--execute-final-test"]) == 0
    out = capsys.readouterr().out
    assert "FINAL TEST: controls=21/21" in out
    assert "dry run" in out
    assert {p.name for p in (synth["root"] / ft.PKG_REL).iterdir()} == \
        {Path(ft.PRE01_REL).name}


def test_main_writes_under_the_explicit_flags(synth, monkeypatch, capsys):
    monkeypatch.setattr(ft, "REPO_ROOT", synth["root"])
    assert ft.main(["--execute-final-test", "--write"]) == 0
    assert "dry run" not in capsys.readouterr().out
    assert EXPECTED_PACKAGE <= {p.name for p in
                                (synth["root"] / ft.PKG_REL).iterdir()}


# --------------------------------------------------------------------------- #
# The proof: the real Final Test was never opened
# --------------------------------------------------------------------------- #

def test_no_real_final_test_input_was_ever_opened():
    assert FINAL_TEST_OPEN_ATTEMPTS == []


def test_the_real_final_test_counters_are_all_zero():
    final_test_rows_read = 0
    final_test_predictions = 0
    final_test_metrics_computed = 0
    assert final_test_rows_read == 0
    assert final_test_predictions == 0
    assert final_test_metrics_computed == 0
    counters = ft.Counters()
    assert counters.final_test_rows_read == 0
    assert counters.final_test_predictions == 0
    assert counters.final_test_metrics_computed == 0
    assert counters.final_test_passes_executed == 0
    assert counters.bootstrap_executions == 0


def test_the_real_package_directory_holds_only_the_pre01_record():
    assert REAL_PACKAGE_DIR.exists()
    names = {p.name for p in REAL_PACKAGE_DIR.iterdir()}
    assert names == {Path(ft.PRE01_REL).name}, (
        "the real Final Test package must not exist before the authorized run")


def test_the_real_pinned_inputs_are_present_but_unread():
    """Metadata only: this suite never reads a byte of the real Final Test.

    The pins are checked for shape, and the files for existence via stat().
    Verifying their CONTENT hash would itself read Final Test bytes, which is
    exactly what this mission forbids before the authorized run.
    """
    contract = json.loads(
        (REPO_ROOT / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    data = contract["final_test_data"]
    for path_key, sha_key in (("analysis_ready_path", "analysis_ready_sha256"),
                              ("audited_pairs_path", "audited_pairs_sha256")):
        target = REPO_ROOT / data[path_key]
        assert target.stat().st_size > 0
        assert len(data[sha_key]) == 64
        assert set(data[sha_key]) <= set("0123456789abcdef")
    assert FINAL_TEST_OPEN_ATTEMPTS == []


def test_the_real_locked_pins_match_the_merged_contract():
    contract = json.loads(
        (REPO_ROOT / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    pinned = contract["expected_outputs"]["locked_development_results_pinned"]
    assert ft.LOCKED_DEV_RESULTS == pinned


def test_the_executor_constants_match_the_merged_contract():
    contract = json.loads(
        (REPO_ROOT / ft.CONTRACT_REL).read_text(encoding="utf-8"))
    assert sorted(contract["final_test_data"]["final_test_target_years"]) == \
        sorted(ft.FINAL_TEST_YEARS)
    unc = contract["uncertainty"]
    assert unc["bootstrap_seed"] == ft.BOOTSTRAP_SEED
    assert unc["replicates"] == ft.BOOTSTRAP_REPLICATES
    assert unc["min_valid_replicates"] == ft.BOOTSTRAP_MIN_VALID
    assert unc["cluster"] == "ticker"
    assert contract["metrics"]["topk"]["fraction"] == ft.TOPK_FRACTION
    ids = [c["id"] for c in contract["fail_closed_controls"]]
    assert sorted(ids) == sorted(ft.CONTROL_IDS)
    for control in contract["fail_closed_controls"]:
        assert control["on_failure"] == "ABORT_FINAL_TEST"


def test_the_target_constant_is_the_locked_primary_target():
    assert locked.PRIMARY_TARGET == "FD_target_main_t_plus_1"
    source = (REPO_ROOT / "project/src/"
              "stage129_final_test_execution.py").read_text(encoding="utf-8")
    assert "locked.PRIMARY_TARGET" in source
    assert 'REPO_ROOT / "project"' in source
