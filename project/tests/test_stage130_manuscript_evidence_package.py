"""Focused tests for the Stage130 Phase 1 manuscript evidence package.

These prove exactly the properties the Phase 1 authorization requires, and
nothing more. They do not open a raw Final Test input or the row-level
prediction artifact, and an autouse recorder proves the package builder does
not either.
"""
from __future__ import annotations

import builtins
import csv
import hashlib
import io
import json
import pathlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "project"))

from src import stage130_manuscript_evidence_package as pkg  # noqa: E402

PKG_DIR = REPO_ROOT / pkg.PKG_REL
FT_METRICS = REPO_ROOT / pkg.FT_METRICS_REL

#: Files this action must never open, at any point.
PROHIBITED = tuple(pkg.FORBIDDEN_SOURCES)

#: Every path the builder opened, recorded for the closing proof.
OPENED: list[str] = []


@pytest.fixture(autouse=True)
def _record_every_open(monkeypatch):
    """Record every file open so the prohibition can be proven, not asserted."""
    real_open = builtins.open
    real_read_bytes = pathlib.Path.read_bytes
    real_read_text = pathlib.Path.read_text

    def note(p):
        try:
            resolved = Path(p).resolve()
            OPENED.append(str(resolved))
        except (OSError, ValueError):
            OPENED.append(str(p))

    def guarded_open(file, *a, **kw):
        note(file)
        return real_open(file, *a, **kw)

    def guarded_read_bytes(self, *a, **kw):
        note(self)
        return real_read_bytes(self, *a, **kw)

    def guarded_read_text(self, *a, **kw):
        note(self)
        return real_read_text(self, *a, **kw)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(pathlib.Path, "read_text", guarded_read_text)
    yield


def _metrics() -> dict:
    return json.loads(FT_METRICS.read_text(encoding="utf-8"))


def _built() -> dict[str, bytes]:
    return pkg.build_package(REPO_ROOT)


def _rows(name: str) -> list[dict[str, str]]:
    text = (PKG_DIR / name).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


# --------------------------------------------------------------------------- #
# 1. The Final Test was not reopened, and the prediction artifact never read
# --------------------------------------------------------------------------- #

def test_building_the_package_opens_no_prohibited_source():
    OPENED.clear()
    _built()
    for rel in PROHIBITED:
        target = str((REPO_ROOT / rel).resolve())
        assert target not in OPENED, rel


def test_the_loader_refuses_the_prediction_artifact_fail_closed():
    predictions = ("project/stage129/final_test_execution/"
                   "stage129_final_test_predictions.json")
    assert predictions in pkg.FORBIDDEN_SOURCES
    with pytest.raises(pkg.Stage130Error):
        pkg._guarded_open(REPO_ROOT, predictions)


@pytest.mark.parametrize("rel", PROHIBITED)
def test_every_forbidden_source_is_refused(rel):
    with pytest.raises(pkg.Stage130Error):
        pkg._guarded_open(REPO_ROOT, rel)


def test_the_package_declares_zero_final_test_access():
    man = json.loads((PKG_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert man["final_test_rows_read_by_this_action"] == 0
    assert man["final_test_prediction_artifact_opened"] is False
    assert man["new_scientific_analysis_performed"] is False
    assert man["shap_executions"] == 0
    for field in ("new_metrics_computed", "new_confidence_intervals_computed",
                  "new_bootstrap_replicates", "p_values_computed",
                  "thresholds_derived", "models_fitted_or_refitted"):
        assert man[field] == 0, field
    assert man["stage130_scientific_execution_started"] is False


# --------------------------------------------------------------------------- #
# 2. Every displayed Final Test value matches the committed aggregate artifact
# --------------------------------------------------------------------------- #

def test_performance_table_matches_the_committed_metrics_exactly():
    m = _metrics()
    iv = m["uncertainty"]["intervals"]
    rows = {r["metric"]: r
            for r in _rows("manuscript_results_tables/"
                           "table_2_final_test_aggregate_performance.csv")}
    assert set(rows) == set(m["metrics"])
    for name, row in rows.items():
        assert float(row["value"]) == m["metrics"][name], name
        if name in iv:
            assert float(row["ci_lower_95"]) == iv[name]["lower"], name
            assert float(row["ci_upper_95"]) == iv[name]["upper"], name
            assert row["interval_available"] == "true"
        else:
            assert row["ci_lower_95"] == "" and row["ci_upper_95"] == ""
            assert row["interval_available"] == "false"


def test_recall_and_lift_carry_no_interval():
    rows = {r["metric"]: r
            for r in _rows("manuscript_results_tables/"
                           "table_2_final_test_aggregate_performance.csv")}
    for name in ("Recall@10%", "Lift@10%"):
        assert rows[name]["ci_lower_95"] == ""
        assert rows[name]["ci_upper_95"] == ""


def test_primary_metric_is_pr_auc():
    rows = {r["metric"]: r["role"]
            for r in _rows("manuscript_results_tables/"
                           "table_2_final_test_aggregate_performance.csv")}
    assert rows["PR-AUC"] == "primary"
    assert all(v == "secondary" for k, v in rows.items() if k != "PR-AUC")


def test_operating_point_matches_the_committed_confusion_counts():
    thr = _metrics()["thresholded_secondary"]
    rows = {r["item"]: r["value"] for r in _rows(
        "manuscript_results_tables/table_3_operating_point_confusion_matrix.csv")}
    assert float(rows["threshold"]) == thr["threshold"]
    assert int(rows["true_positives"]) == thr["tp"]
    assert int(rows["false_positives"]) == thr["fp"]
    assert int(rows["true_negatives"]) == thr["tn"]
    assert int(rows["false_negatives"]) == thr["fn"]


def test_cohort_table_matches_the_committed_counts():
    m = _metrics()
    rows = {r["item"]: r["value"] for r in _rows(
        "manuscript_results_tables/table_1_cohort_and_temporal_design.csv")}
    assert int(rows["final_test_evaluable_rows"]) == m["evaluable_rows"]
    assert int(rows["final_test_positive"]) == m["positive"]
    assert int(rows["final_test_negative"]) == m["negative"]
    assert int(rows["final_test_unique_tickers"]) == m["unique_tickers"]
    assert float(rows["final_test_prevalence"]) == \
        m["topk"]["pooled_test_prevalence"]


def test_topk_table_matches_the_committed_per_year_counts():
    topk = _metrics()["topk"]
    rows = {r["item"]: r for r in _rows(
        "manuscript_results_tables/table_4_top10_percent_screening.csv")}
    for year, vals in topk["per_target_year"].items():
        row = rows[f"target_year_{year}"]
        assert int(row["N_y_or_value"]) == vals["N_y"]
        assert int(row["K_y"]) == vals["K_y"]
        assert int(row["captured_positives"]) == vals["captured_positives"]
    assert int(rows["pooled_selected_rows"]["N_y_or_value"]) == topk["selected_rows"]
    assert int(rows["pooled_captured_positives"]["N_y_or_value"]) == \
        topk["captured_positives"]


# --------------------------------------------------------------------------- #
# 3. Coefficient / OR rows map one-to-one onto the locked model terms
# --------------------------------------------------------------------------- #

def _model() -> dict:
    return json.loads(
        (REPO_ROOT / pkg.MODEL_REL).read_text(encoding="utf-8"))


def test_coefficient_rows_map_one_to_one_and_in_model_order():
    model = _model()
    rows = _rows("table_model_coefficients_and_odds_ratios.csv")
    assoc = [r for r in rows if r["term_type"] != "intercept"]
    intercepts = [r for r in rows if r["term_type"] == "intercept"]
    assert len(intercepts) == 1
    assert len(assoc) == len(model["coefficients"])
    assert [r["term"] for r in assoc] == list(model["design_matrix_columns"])
    for row, beta in zip(assoc, model["coefficients"]):
        assert float(row["coefficient_beta"]) == beta, row["term"]


def test_odds_ratio_is_exactly_exp_of_the_locked_coefficient():
    import math
    for row in _rows("table_model_coefficients_and_odds_ratios.csv"):
        assert float(row["odds_ratio_exp_beta"]) == \
            math.exp(float(row["coefficient_beta"])), row["term"]


def test_terms_are_not_reordered_into_an_importance_ranking():
    model = _model()
    assoc = [r["term"] for r in
             _rows("table_model_coefficients_and_odds_ratios.csv")
             if r["term_type"] != "intercept"]
    assert assoc == list(model["design_matrix_columns"])
    by_magnitude = sorted(
        model["design_matrix_columns"],
        key=lambda n: -abs(model["coefficients"][
            model["design_matrix_columns"].index(n)]))
    assert assoc != by_magnitude or assoc == list(model["design_matrix_columns"])


def test_effect_scales_distinguish_standardized_from_binary_terms():
    for row in _rows("table_model_coefficients_and_odds_ratios.csv"):
        if row["term_type"] == "standardized_continuous_feature":
            assert row["effect_scale"] == "odds_ratio_per_1_SD_increase"
            assert row["standardization_std"] != ""
        elif row["term_type"] == "binary_missingness_indicator":
            assert row["effect_scale"] == "odds_ratio_for_indicator_1_versus_0"
            assert row["standardization_std"] == ""


def test_no_interval_p_value_or_significance_marker_on_any_coefficient():
    text = (PKG_DIR / "table_model_coefficients_and_odds_ratios.csv").read_text(
        encoding="utf-8")
    header = text.splitlines()[0].lower()
    for banned in ("ci_", "conf", "std_err", "stderr", "se_", "p_value",
                   "pvalue", "signif", "star", "t_stat", "z_stat"):
        assert banned not in header, banned
    assert "*" not in text
    assert all(r["interpretation_class"] in
               ("regularized_conditional_association",
                "not_an_association_baseline_term")
               for r in _rows("table_model_coefficients_and_odds_ratios.csv"))


# --------------------------------------------------------------------------- #
# 4. The obsolete Stage123 numbers never enter the canonical package
# --------------------------------------------------------------------------- #

def test_no_legacy_stage123_value_appears_anywhere_in_the_package():
    offenders = []
    for path in sorted(PKG_DIR.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for value in pkg.LEGACY_FORBIDDEN_VALUES:
            if value in text:
                offenders.append((path.name, value))
    assert offenders == [], offenders


def test_legacy_tree_is_marked_do_not_cite():
    text = (PKG_DIR / "legacy_outputs_supersession.md").read_text(
        encoding="utf-8")
    assert pkg.LEGACY_STATUS in text
    assert pkg.LEGACY_DIR_REL in text
    man = json.loads((PKG_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert man["legacy_outputs_status"][pkg.LEGACY_DIR_REL] == pkg.LEGACY_STATUS


def test_legacy_files_are_untouched_by_this_action():
    """The legacy tree is preserved byte-identical against the merged base."""
    import subprocess
    changed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only",
         pkg.BASE_COMMIT, "HEAD", "--", pkg.LEGACY_DIR_REL],
        capture_output=True, text=True, check=True).stdout.strip()
    assert changed == "", changed


# --------------------------------------------------------------------------- #
# 5. Deterministic and semantically idempotent
# --------------------------------------------------------------------------- #

def test_package_build_is_deterministic():
    first, second = _built(), _built()
    assert set(first) == set(second)
    for name in first:
        assert first[name] == second[name], name


def test_written_package_matches_a_fresh_build_byte_for_byte():
    built = _built()
    for name, data in built.items():
        on_disk = (PKG_DIR / name).read_bytes()
        assert on_disk == data, name


def test_manifest_pins_every_file_with_hash_and_byte_count():
    man = json.loads((PKG_DIR / "manifest.json").read_text(encoding="utf-8"))
    listed = man["package_files"]
    on_disk = {
        str(p.relative_to(PKG_DIR)).replace("\\", "/")
        for p in PKG_DIR.rglob("*") if p.is_file() and p.name != "manifest.json"
    }
    assert set(listed) == on_disk, (sorted(set(listed) ^ on_disk))
    for name, want in listed.items():
        raw = (PKG_DIR / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == want["sha256"], name
        assert len(raw) == want["bytes"], name


def test_manifest_names_the_authoritative_source_of_every_value():
    man = json.loads((PKG_DIR / "manifest.json").read_text(encoding="utf-8"))
    sources = man["authoritative_value_sources"]
    assert sources["final_test_aggregate_metrics"] == pkg.FT_METRICS_REL
    assert sources["locked_model"] == pkg.MODEL_REL
    assert sources["admitted_threshold"] == pkg.THRESHOLD_REL
    for rel, digest in man["source_sha256"].items():
        raw = (REPO_ROOT / rel).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest, rel


# --------------------------------------------------------------------------- #
# 6. Previously frozen scientific artifacts remain byte-identical
# --------------------------------------------------------------------------- #

FROZEN = {
    "project/src/stage129_final_test_execution.py":
        "d85234ee4c7e2b14dc21084348a059fceb083cf8bcc0ecbf30ee64eef79c56a4",
    "project/stage129/final_test_execution/stage129_final_test_metrics.json":
        "0b1ea6c086430d6ecc65432c8001cc3b028422e7c1293a9ea2fb6c44d7ef4392",
    "project/stage129/final_test_execution/stage129_final_test_provenance_record.json":
        "5b5d4d66ed4ca0770667547752c0436380c8960f0d5296f62bda83b3fa80c551",
    "project/stage129/final_test_execution/stage129_final_test_qc_report.json":
        "016eaa19149a9247574e13931e9aae4a10fede26316a63f1321a6643c96ad9f5",
    "project/stage129/final_test_execution/"
    "metadata_and_hashes_stage129_final_test_execution.json":
        "0ac59f9bef0fc984b78b3398a8ffe022906a07953db236331c892b8d6b73c4c9",
    "project/stage129/final_test_execution/"
    "stage129_pre01_human_authorization_record.json":
        "70ed6dddcd2a7cdd6468844ebe1fda27f163006a5fd54735e5b5278fc69d3ca4",
    "project/stage129/full_development_refit_execution/"
    "stage129_full_development_refit_model.json":
        "48faab1ef186206508385713fb3b885a88a55bb072fb586d56e63d2777c97690",
    "project/stage129/threshold_derivation_attempt3/"
    "stage129_threshold_value_attempt3.json":
        "9b8a7d799616eb12d6e70a6dcf623ff1a636b4ec4b1bde37c21116252876b534",
    "project/tests/test_stage125_part5_readiness_closure.py":
        "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71",
}


@pytest.mark.parametrize("rel,want", sorted(FROZEN.items()))
def test_frozen_scientific_artifacts_are_byte_identical(rel, want):
    raw = (REPO_ROOT / rel).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == want, rel


def test_the_prediction_artifact_still_exists_and_was_simply_not_read():
    """Its presence is required; its CONTENT is never opened by this action."""
    predictions = (REPO_ROOT / "project/stage129/final_test_execution"
                   / "stage129_final_test_predictions.json")
    assert predictions.is_file()


def test_no_figure_is_a_performance_curve():
    names = sorted(p.name for p in
                   (PKG_DIR / pkg.FIGURES_SUBDIR).iterdir() if p.is_file())
    for banned in ("roc", "precision_recall", "pr_curve", "calibration",
                   "reliability", "subgroup", "yearly", "per_year",
                   "decision_curve", "net_benefit"):
        assert not any(banned in n.lower() for n in names), banned
    assert len(names) == 3

# --------------------------------------------------------------------------- #
# 7. Stage130 has STARTED as a programme phase; its SCIENCE has not
# --------------------------------------------------------------------------- #

def _state() -> dict:
    return json.loads(
        (REPO_ROOT / "project/docs/ai/handoff_state.json").read_text(
            encoding="utf-8"))


def _roadmap_front_matter() -> dict:
    import re
    text = (REPO_ROOT / "project/docs/ai/ROADMAP.md").read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert m
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def test_live_state_says_the_stage130_programme_phase_has_started():
    state = _state()
    assert state["stage130_started"] is True
    assert state["stage130_phase1_started"] is True
    assert state["stage130_phase1_completed"] is True
    assert state["stage130_phase1_presentation_only"] is True


def test_live_state_says_stage130_scientific_execution_has_not_started():
    """The whole point of the distinction: a package is not a scientific stage."""
    state = _state()
    assert state["stage130_scientific_execution_started"] is False
    assert state["stage130_phase1_new_scientific_analysis_performed"] is False
    assert state["stage130_authorized"] is False
    for field in ("stage130_phase1_final_test_rows_read",
                  "stage130_phase1_shap_executions",
                  "stage130_phase1_new_metrics_computed",
                  "stage130_phase1_new_confidence_intervals_computed",
                  "stage130_phase1_thresholds_derived",
                  "stage130_phase1_models_fitted_or_refitted"):
        assert state[field] == 0, field
    assert state["stage130_phase1_prediction_artifact_opened"] is False


def test_the_two_stage130_markers_are_not_collapsed_into_one():
    state = _state()
    assert state["stage130_started"] != \
        state["stage130_scientific_execution_started"]


def test_roadmap_front_matter_agrees_with_the_live_handoff():
    """A key added to the ROADMAP but absent from the generated state is a lie."""
    fm, state = _roadmap_front_matter(), _state()
    pairs = {
        "stage130_started": True,
        "stage130_phase1_started": True,
        "stage130_phase1_completed": True,
        "stage130_scientific_execution_started": False,
    }
    for key, want in pairs.items():
        assert key in fm, f"ROADMAP front matter missing {key}"
        assert fm[key] == str(want).lower(), key
        assert state[key] is want, key


def test_current_state_renders_the_stage130_phase1_distinction():
    text = (REPO_ROOT / "project/docs/ai/CURRENT_STATE.md").read_text(
        encoding="utf-8")
    assert "Stage130 Phase 1" in text
    assert "Stage130 scientific execution started:** False" in text


def test_historical_stage129_stage130_markers_are_unchanged():
    """Earlier actions said stage130 had not started. That stays true of them."""
    state = _state()
    assert state["stage129_audit_stage130_started"] is False
    assert state["stage129_final_test_stage130_authorized"] is False
    assert state["stage129_refit_stage130_authorized"] is False


# --------------------------------------------------------------------------- #
# 8. Corrected wording and the missingness facts
# --------------------------------------------------------------------------- #

def _flat(name: str) -> str:
    """Markdown wraps; compare on whitespace-normalized text."""
    import re
    return re.sub(r"\s+", " ", (PKG_DIR / name).read_text(encoding="utf-8"))


def test_roc_auc_limitation_uses_the_corrected_wording():
    flat = _flat("manuscript_claim_freeze.md")
    assert ("under severe class imbalance, ROC-AUC is less informative about "
            "positive-class retrieval and must be interpreted alongside the "
            "pre-specified primary PR-AUC") in flat
    assert "optimistic under a low" not in flat


def test_roc_auc_overclaim_wording_stays_prohibited():
    text = (PKG_DIR / "manuscript_claim_freeze.md").read_text(encoding="utf-8")
    assert "may not be" in text or "Prohibited overclaim" in text
    assert "superiority" in text
    assert "leading the abstract with ROC-AUC" in text


def test_missingness_indicator_counts_are_exactly_six_zero_and_three_nonzero():
    rows = [r for r in _rows("table_model_coefficients_and_odds_ratios.csv")
            if r["term_type"] == "binary_missingness_indicator"]
    assert len(rows) == 9
    zero = [r["term"] for r in rows if float(r["coefficient_beta"]) == 0.0]
    nonzero = [r["term"] for r in rows if float(r["coefficient_beta"]) != 0.0]
    assert len(zero) == 6, zero
    assert sorted(nonzero) == sorted([
        "ocf_to_assets_period_adjusted__missing",
        "operating_margin_period_adjusted__missing",
        "financial_expense_to_assets_period_adjusted__missing",
    ]), nonzero


def test_narrative_states_the_missingness_pattern_descriptively():
    for name in ("manuscript_claim_freeze.md", "README.md"):
        flat = _flat(name)
        assert ("Six of the nine missingness-indicator coefficients are exactly "
                "zero in the locked model; three are non-zero") in flat, name
        assert ("does not establish statistical significance or a general claim "
                "that missingness is informative") in flat, name


def test_no_narrative_claims_all_nine_or_only_two_missingness_terms():
    for path in sorted(PKG_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        assert "all nine missingness" not in text, path.name
        assert "only two missingness" not in text, path.name
        assert "two missingness indicators are non-zero" not in text, path.name
