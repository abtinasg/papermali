"""Stage130 Phase 1 — canonical manuscript evidence package.

Presentation only. This module performs NO scientific estimation:

  * It reads already-committed AGGREGATE artifacts and re-displays them.
  * The single arithmetic operation it performs is ``exp(beta)`` on the locked
    logistic coefficients -- a deterministic transformation of a frozen
    artifact, not a new estimate on data.
  * It never opens a raw Final Test input, and it never opens the row-level
    prediction artifact. ``FORBIDDEN_SOURCES`` names those files and
    :func:`_guarded_open` refuses them, so a future edit that reached for one
    would abort rather than silently succeed.

Nothing here computes a metric, interval, replicate, p-value, subgroup,
per-year performance figure, calibration quantity or threshold.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

ACTION_ID = "stage130-manuscript-evidence-package"
BASE_COMMIT = "02af8c56235f70f4ec45f0dad15e4ad3aebf7a21"
PKG_REL = "project/stage130/manuscript_evidence_package"
TABLES_SUBDIR = "manuscript_results_tables"
FIGURES_SUBDIR = "manuscript_figures"

# ---------------------------------------------------------------- sources
FT_METRICS_REL = ("project/stage129/final_test_execution/"
                  "stage129_final_test_metrics.json")
FT_QC_REL = ("project/stage129/final_test_execution/"
             "stage129_final_test_qc_report.json")
FT_PROV_REL = ("project/stage129/final_test_execution/"
               "stage129_final_test_provenance_record.json")
FT_MANIFEST_REL = ("project/stage129/final_test_execution/"
                   "metadata_and_hashes_stage129_final_test_execution.json")
MODEL_REL = ("project/stage129/full_development_refit_execution/"
             "stage129_full_development_refit_model.json")
PREP_REL = ("project/stage129/full_development_refit_execution/"
            "stage129_full_development_refit_preprocessing_parameters.json")
THRESHOLD_REL = ("project/stage129/threshold_derivation_attempt3/"
                 "stage129_threshold_value_attempt3.json")
DEV_METRICS_REL = "project/stage126/stage126_m1_development_metrics.csv"
ROBUST_SYNTH_REL = ("project/stage126/"
                    "stage126_m1_robustness_closure_synthesis_record.json")
SPLIT_CONTRACT_REL = "project/stage125/part4_temporal_split_contract_stage125.json"

#: Never opened by this module. The row-level prediction artifact is excluded
#: by the Stage130 Phase 1 authorization; the raw inputs are Final Test data.
FORBIDDEN_SOURCES = (
    "project/stage129/final_test_execution/stage129_final_test_predictions.json",
    "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv",
    "project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv",
    "project/stage125/part4_temporal_split_manifest_stage125.csv",
)

#: The obsolete Stage123-era report tree. Preserved byte-identical; never cited.
LEGACY_DIR_REL = "project/outputs/09_report"
LEGACY_STATUS = "LEGACY_STAGE123_NONCANONICAL_DO_NOT_CITE"
#: Values that appear in the legacy tree and must never appear in this package.
LEGACY_FORBIDDEN_VALUES = ("0.628", "0.608", "0.263", "0.777", "0.873", "0.866")


class Stage130Error(RuntimeError):
    """Raised when a prohibited source is reached for, or an input drifted."""


def _guarded_open(repo_root: Path, rel: str) -> bytes:
    """Read a permitted source. Refuse every forbidden one, fail-closed."""
    normalized = rel.replace("\\", "/")
    if normalized in FORBIDDEN_SOURCES:
        raise Stage130Error(
            f"refusing to open a prohibited Stage130 Phase 1 source: {rel}")
    return (repo_root / rel).read_bytes()


def _load(repo_root: Path, rel: str) -> dict[str, Any]:
    return json.loads(_guarded_open(repo_root, rel).decode("utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _num(x: float) -> str:
    """Full-precision, round-trippable display. No rounding is applied here."""
    return repr(float(x))


def _csv_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


# ------------------------------------------------------- coefficient table
def build_coefficient_table(model: dict[str, Any],
                            prep: dict[str, Any]) -> bytes:
    """Coefficients and odds ratios, in the model's own term order.

    The only arithmetic is ``exp(beta)``. No confidence interval, standard
    error, p-value or significance marker is produced, because none exists in
    the locked artifact and inventing one would be new inference. Terms are
    NOT reordered by magnitude: an importance ranking would be an implicit new
    claim.
    """
    columns = list(model["design_matrix_columns"])
    coefs = list(model["coefficients"])
    if len(columns) != len(coefs):
        raise Stage130Error("locked model columns and coefficients disagree")
    continuous = list(prep["feature_order"])
    std = list(prep["standardization_std"])
    mean = list(prep["standardization_mean"])
    if prep.get("missingness_indicators_standardized") is not False:
        raise Stage130Error(
            "preprocessing artifact no longer reports unstandardized indicators")

    header = ["term_order", "term", "term_type", "effect_scale",
              "coefficient_beta", "odds_ratio_exp_beta",
              "standardization_mean", "standardization_std",
              "interpretation_class"]
    rows: list[list[str]] = []

    rows.append([
        "0", "(intercept)", "intercept",
        "baseline_log_odds_at_standardized_feature_means_and_all_indicators_zero",
        _num(model["intercept"]), _num(math.exp(model["intercept"])),
        "", "", "not_an_association_baseline_term",
    ])

    for i, (name, beta) in enumerate(zip(columns, coefs)):
        if name.endswith("__missing"):
            term_type = "binary_missingness_indicator"
            scale = "odds_ratio_for_indicator_1_versus_0"
            m_disp = s_disp = ""
        else:
            term_type = "standardized_continuous_feature"
            scale = "odds_ratio_per_1_SD_increase"
            idx = continuous.index(name)
            m_disp, s_disp = _num(mean[idx]), _num(std[idx])
        rows.append([
            str(i + 1), name, term_type, scale,
            _num(beta), _num(math.exp(beta)), m_disp, s_disp,
            "regularized_conditional_association",
        ])
    return _csv_bytes(header, rows)


# ------------------------------------------------------------ result tables
def build_tables(ft: dict[str, Any], prov: dict[str, Any],
                 model: dict[str, Any], split: dict[str, Any],
                 dev_csv: str, robust: dict[str, Any],
                 coef_csv: bytes) -> dict[str, bytes]:
    thr = ft["thresholded_secondary"]
    topk = ft["topk"]
    unc = ft["uncertainty"]
    fit = model["fit_set"]

    t1 = _csv_bytes(
        ["item", "value", "source_artifact"],
        [
            ["development_target_years",
             "-".join(str(y) for y in (split["development_target_years"][0],
                                       split["development_target_years"][-1])),
             SPLIT_CONTRACT_REL],
            ["final_test_target_years",
             "-".join(str(y) for y in (split["final_test_target_years"][0],
                                       split["final_test_target_years"][-1])),
             SPLIT_CONTRACT_REL],
            ["temporal_validation_fold_1",
             json.dumps(split["temporal_validation_fold_1"], sort_keys=True),
             SPLIT_CONTRACT_REL],
            ["temporal_validation_fold_2",
             json.dumps(split["temporal_validation_fold_2"], sort_keys=True),
             SPLIT_CONTRACT_REL],
            ["split_variable", split["split_variable"], SPLIT_CONTRACT_REL],
            ["random_split_authorized",
             str(split["random_split_authorized"]).lower(), SPLIT_CONTRACT_REL],
            ["shuffle_authorized",
             str(split["shuffle_authorized"]).lower(), SPLIT_CONTRACT_REL],
            ["development_fit_set_rows", str(fit["rows"]), MODEL_REL],
            ["development_fit_set_positive", str(fit["positive"]), MODEL_REL],
            ["development_fit_set_negative", str(fit["negative"]), MODEL_REL],
            ["final_test_cohort_pairs", str(prov["cohort_pairs"]), FT_PROV_REL],
            ["final_test_evaluable_rows", str(ft["evaluable_rows"]), FT_METRICS_REL],
            ["final_test_positive", str(ft["positive"]), FT_METRICS_REL],
            ["final_test_negative", str(ft["negative"]), FT_METRICS_REL],
            ["final_test_unique_tickers", str(ft["unique_tickers"]), FT_METRICS_REL],
            ["final_test_prevalence",
             _num(topk["pooled_test_prevalence"]), FT_METRICS_REL],
        ])

    m = ft["metrics"]
    iv = unc["intervals"]
    t2 = _csv_bytes(
        ["metric", "role", "value", "ci_lower_95", "ci_upper_95",
         "interval_available", "source_artifact"],
        [
            ["PR-AUC", "primary", _num(m["PR-AUC"]),
             _num(iv["PR-AUC"]["lower"]), _num(iv["PR-AUC"]["upper"]),
             "true", FT_METRICS_REL],
            ["ROC-AUC", "secondary", _num(m["ROC-AUC"]),
             _num(iv["ROC-AUC"]["lower"]), _num(iv["ROC-AUC"]["upper"]),
             "true", FT_METRICS_REL],
            ["Brier_score", "secondary", _num(m["Brier_score"]),
             _num(iv["Brier_score"]["lower"]), _num(iv["Brier_score"]["upper"]),
             "true", FT_METRICS_REL],
            ["Recall@10%", "secondary", _num(m["Recall@10%"]), "", "",
             "false", FT_METRICS_REL],
            ["Lift@10%", "secondary", _num(m["Lift@10%"]), "", "",
             "false", FT_METRICS_REL],
        ])

    t3 = _csv_bytes(
        ["item", "value", "source_artifact"],
        [
            ["threshold", _num(thr["threshold"]), THRESHOLD_REL],
            ["threshold_rule", thr["rule"], THRESHOLD_REL],
            ["threshold_tie_break", thr["tie_break"], THRESHOLD_REL],
            ["threshold_derived_from", thr["derived_from"], THRESHOLD_REL],
            ["true_positives", str(thr["tp"]), FT_METRICS_REL],
            ["false_positives", str(thr["fp"]), FT_METRICS_REL],
            ["true_negatives", str(thr["tn"]), FT_METRICS_REL],
            ["false_negatives", str(thr["fn"]), FT_METRICS_REL],
        ])

    per_year = topk["per_target_year"]
    rows4 = [["definition", topk["definition"], "", "", FT_METRICS_REL],
             ["fraction", _num(topk["fraction"]), "", "", FT_METRICS_REL]]
    for year in sorted(per_year):
        y = per_year[year]
        rows4.append([f"target_year_{year}", str(y["N_y"]), str(y["K_y"]),
                      str(y["captured_positives"]), FT_METRICS_REL])
    rows4 += [
        ["pooled_selected_rows", str(topk["selected_rows"]), "", "", FT_METRICS_REL],
        ["pooled_captured_positives", str(topk["captured_positives"]), "", "",
         FT_METRICS_REL],
        ["pooled_total_positives", str(topk["total_positives"]), "", "",
         FT_METRICS_REL],
        ["pooled_precision_among_selected",
         _num(topk["pooled_precision_among_selected"]), "", "", FT_METRICS_REL],
        ["K_optimized_after_results",
         str(topk["K_optimized_after_results"]).lower(), "", "", FT_METRICS_REL],
        ["Recall@10%_point_estimate_no_interval",
         _num(m["Recall@10%"]), "", "", FT_METRICS_REL],
        ["Lift@10%_point_estimate_no_interval",
         _num(m["Lift@10%"]), "", "", FT_METRICS_REL],
    ]
    t4 = _csv_bytes(["item", "N_y_or_value", "K_y", "captured_positives",
                     "source_artifact"], rows4)

    si = robust["scientific_interpretation"]
    t5 = _csv_bytes(
        ["item", "status_or_finding", "source_artifact"],
        [
            ["primary_development_ordering",
             " > ".join(robust["primary_ordering"]), ROBUST_SYNTH_REL],
            ["ordering_preserved_in_parts",
             json.dumps(si["B_sample_definition_sensitivity"]
                        ["primary_ordering_preserved_in_parts"]),
             ROBUST_SYNTH_REL],
            ["part1_is_the_exception",
             str(si["A_model_family_ordering"]["part1_is_the_exception"]).lower(),
             ROBUST_SYNTH_REL],
            ["robustness_evidence_class", robust["closure_type"], ROBUST_SYNTH_REL],
            ["retained_design_selected",
             str(robust["retained_design_selected"]).lower(), ROBUST_SYNTH_REL],
            ["paper_winner_selected_by_robustness_closure",
             str(robust["paper_winner_selected"]).lower(), ROBUST_SYNTH_REL],
        ])

    return {
        f"{TABLES_SUBDIR}/table_1_cohort_and_temporal_design.csv": t1,
        f"{TABLES_SUBDIR}/table_2_final_test_aggregate_performance.csv": t2,
        f"{TABLES_SUBDIR}/table_3_operating_point_confusion_matrix.csv": t3,
        f"{TABLES_SUBDIR}/table_4_top10_percent_screening.csv": t4,
        f"{TABLES_SUBDIR}/table_5_robustness_and_block_dispositions.csv": t5,
        f"{TABLES_SUBDIR}/table_6_model_coefficients_and_odds_ratios.csv": coef_csv,
    }


# ------------------------------------------------------------------ figures
def _svg(width: int, height: int, body: str) -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="Helvetica,Arial,sans-serif">\n'
        f'{body}</svg>\n'
    ).encode("utf-8")


def build_figures(model: dict[str, Any], split: dict[str, Any]) -> dict[str, bytes]:
    """Schematics and a coefficient plot. No performance curve is drawn."""
    dev = split["development_target_years"]
    test = split["final_test_target_years"]

    parts = ['<text x="20" y="30" font-size="16" font-weight="bold">'
             'Study timeline and leakage-safe temporal design</text>\n']
    x0, w = 60, 60
    for i, year in enumerate(dev + test):
        x = x0 + i * w
        fill = "#d7e3f4" if year in dev else "#f6dcc8"
        parts.append(f'<rect x="{x}" y="70" width="{w - 6}" height="40" '
                     f'fill="{fill}" stroke="#333"/>\n')
        parts.append(f'<text x="{x + 8}" y="95" font-size="13">{year}</text>\n')
    parts.append('<text x="60" y="135" font-size="12">Development '
                 f'{dev[0]}–{dev[-1]}</text>\n')
    parts.append(f'<text x="{x0 + len(dev) * w}" y="135" font-size="12">'
                 f'Final Test {test[0]}–{test[-1]} (opened once)</text>\n')
    f1v = split["temporal_validation_fold_1"]
    f2v = split["temporal_validation_fold_2"]
    parts.append('<text x="20" y="175" font-size="12">Fold 1 — train '
                 f'{f1v["train_target_years"]} → validate '
                 f'{f1v["validation_target_years"]}</text>\n')
    parts.append('<text x="20" y="197" font-size="12">Fold 2 — train '
                 f'{f2v["train_target_years"]} → validate '
                 f'{f2v["validation_target_years"]}</text>\n')
    parts.append('<text x="20" y="225" font-size="12">Forward-chaining only: '
                 'no shuffling, no random split.</text>\n')
    fig1 = _svg(720, 245, "".join(parts))

    steps = ["Leakage-safe dataset (Stage125)",
             "Temporal folds — development only",
             "Model tuning (Stage126, development OOF)",
             "Robustness — 6 pre-registered categories",
             "Full-development refit (PR #90)",
             "Threshold from development OOF (PR #95)",
             "Final Test — one pre-registered pass (PR #96)"]
    sp = ['<text x="20" y="30" font-size="16" font-weight="bold">'
          'Model development and evaluation workflow</text>\n']
    for i, label in enumerate(steps):
        y = 60 + i * 46
        fill = "#f6dcc8" if i == len(steps) - 1 else "#d7e3f4"
        sp.append(f'<rect x="40" y="{y}" width="560" height="32" fill="{fill}" '
                  f'stroke="#333"/>\n')
        sp.append(f'<text x="52" y="{y + 21}" font-size="13">{label}</text>\n')
        if i < len(steps) - 1:
            sp.append(f'<line x1="320" y1="{y + 32}" x2="320" y2="{y + 46}" '
                      f'stroke="#333" stroke-width="2"/>\n')
    fig2 = _svg(660, 60 + len(steps) * 46 + 20, "".join(sp))

    columns = list(model["design_matrix_columns"])
    coefs = list(model["coefficients"])
    span = max(abs(c) for c in coefs)
    mid, scale = 380, 250.0
    cp = ['<text x="20" y="30" font-size="16" font-weight="bold">'
          'Locked logistic coefficients (model term order)</text>\n',
          '<text x="20" y="50" font-size="11">Regularized conditional '
          'associations on the log-odds scale. No confidence interval exists.'
          '</text>\n']
    for i, (name, beta) in enumerate(zip(columns, coefs)):
        y = 76 + i * 22
        length = (abs(beta) / span) * scale
        x = mid if beta >= 0 else mid - length
        fill = "#c0504d" if beta >= 0 else "#4f81bd"
        cp.append(f'<text x="16" y="{y + 11}" font-size="11">{name}</text>\n')
        cp.append(f'<rect x="{x:.4f}" y="{y}" width="{length:.4f}" height="14" '
                  f'fill="{fill}"/>\n')
    cp.append(f'<line x1="{mid}" y1="70" x2="{mid}" y2="{76 + len(coefs) * 22}" '
              f'stroke="#333" stroke-width="1"/>\n')
    fig3 = _svg(700, 96 + len(coefs) * 22, "".join(cp))

    return {
        f"{FIGURES_SUBDIR}/figure_1_study_timeline_and_leakage_safe_design.svg": fig1,
        f"{FIGURES_SUBDIR}/figure_2_model_development_workflow.svg": fig2,
        f"{FIGURES_SUBDIR}/figure_3_coefficient_plot.svg": fig3,
    }


# -------------------------------------------------------------- narrative
def build_claim_freeze(ft: dict[str, Any], prov: dict[str, Any],
                       model: dict[str, Any]) -> bytes:
    m, thr, topk = ft["metrics"], ft["thresholded_secondary"], ft["topk"]
    iv = ft["uncertainty"]["intervals"]
    fit = model["fit_set"]
    prevalence = _num(topk["pooled_test_prevalence"])
    text = f"""# Stage130 Phase 1 — manuscript claim freeze

Every claim below is pinned to a committed artifact and an exact committed
value. Wording outside this file is not frozen and is not authorized.

**PR-AUC is the primary metric.** ROC-AUC, Brier score, Recall@10% and
Lift@10% are secondary. The metric set was closed before the Final Test was
opened and no metric was added afterwards.

No confirmatory inference and no superiority test was conducted:
`p_values_computed = 0`, `holm_executions = 0`,
`inferential_superiority_claim = false`. The Holm family is incomplete and its
final adjustment is deferred. No claim of superiority over any model, block or
comparator is permitted anywhere in the manuscript.

---

## C1 — Primary predictive performance

* **Source:** `{FT_METRICS_REL}`
* **Committed value:** PR-AUC = `{_num(m["PR-AUC"])}`,
  95% cluster-bootstrap interval `[{_num(iv["PR-AUC"]["lower"])}, {_num(iv["PR-AUC"]["upper"])}]`
* **Final Test prevalence (reported separately):** `{prevalence}`
* **Permissible wording:** "On the held-out Final Test the model achieved a
  PR-AUC of {_num(m["PR-AUC"])} (95% cluster-bootstrap CI
  {_num(iv["PR-AUC"]["lower"])}–{_num(iv["PR-AUC"]["upper"])}). The Final Test
  prevalence was {prevalence}."
* **Prohibited overclaim:** stating or computing any ratio of PR-AUC to
  prevalence, including "approximately 7x prevalence" or any equivalent
  multiple. The two quantities are reported separately and are never combined.
  No claim of accuracy, reliability or readiness for deployment.
* **Mandatory accompanying limitation:** the interval is wide and its lower
  bound lies close to the prevalence, so this single evaluation does not
  establish a precise effect size.

## C2 — Discrimination

* **Source:** `{FT_METRICS_REL}`
* **Committed value:** ROC-AUC = `{_num(m["ROC-AUC"])}`, 95% CI
  `[{_num(iv["ROC-AUC"]["lower"])}, {_num(iv["ROC-AUC"]["upper"])}]`
* **Permissible wording:** "ROC-AUC was {_num(m["ROC-AUC"])} (95% CI
  {_num(iv["ROC-AUC"]["lower"])}–{_num(iv["ROC-AUC"]["upper"])})." Report the
  number only.
* **Prohibited overclaim:** the words "strong", "excellent", "high",
  "outstanding" or any synonym applied to ROC-AUC; any use of ROC-AUC as
  evidence of superiority; leading the abstract with ROC-AUC in place of the
  primary metric.
* **Mandatory accompanying limitation:** under severe class imbalance,
  ROC-AUC is less informative about positive-class retrieval and must be
  interpreted alongside the pre-specified primary PR-AUC.

## C3 — Brier score

* **Source:** `{FT_METRICS_REL}`
* **Committed value:** Brier = `{_num(m["Brier_score"])}`, 95% CI
  `[{_num(iv["Brier_score"]["lower"])}, {_num(iv["Brier_score"]["upper"])}]`
* **Permissible wording:** "The observed Brier score on raw, unrecalibrated
  predicted probabilities was {_num(m["Brier_score"])}."
* **Prohibited overclaim:** any statement that calibration was assessed,
  evaluated or established; any claim that the model "is well calibrated";
  any calibration slope, intercept, curve or reliability statement.
  `recalibration_executions = 0` and `isotonic_executions = 0`.
* **Mandatory accompanying limitation:** calibration was **not** fully
  assessed. A single Brier score at a low event rate is not a calibration
  assessment.

## C4 — Threshold-based operating performance

* **Source:** `{FT_METRICS_REL}`, threshold from `{THRESHOLD_REL}`
* **Committed value:** threshold `{_num(thr["threshold"])}`; TP `{thr["tp"]}`,
  FP `{thr["fp"]}`, TN `{thr["tn"]}`, FN `{thr["fn"]}`
* **Permissible wording:** "At the pre-specified operating threshold
  {_num(thr["threshold"])}, derived from pooled development out-of-fold
  predictions only, the confusion counts were TP {thr["tp"]}, FP {thr["fp"]},
  TN {thr["tn"]}, FN {thr["fn"]}."
* **Prohibited overclaim:** describing the threshold as optimal, tuned or
  selected on the Final Test; deriving any new threshold.
* **Mandatory accompanying limitation:** the threshold was fixed before Final
  Test access and was not re-derived afterwards.

## C5 — Top-10% screening

* **Source:** `{FT_METRICS_REL}`
* **Committed values:** Recall@10% = `{_num(m["Recall@10%"])}`,
  Lift@10% = `{_num(m["Lift@10%"])}`; `K_y = ceil(0.10 * N_y)`;
  {topk["selected_rows"]} rows selected; {topk["captured_positives"]} of
  {topk["total_positives"]} positives captured
* **Permissible wording:** report both as **point estimates**, explicitly
  noting that no confidence interval is available for either.
* **Prohibited overclaim:** attaching any interval, standard error or
  significance statement to these two metrics; computing one now.
* **Mandatory accompanying limitation:** per-year capture counts rest on very
  few events and support no stability claim in either direction.

## C6 — Robustness and temporal design

* **Source:** `{ROBUST_SYNTH_REL}`, `{SPLIT_CONTRACT_REL}`
* **Permissible wording:** six pre-registered robustness categories provide
  **sensitivity evidence only**; validation was strictly forward-chaining with
  no shuffling and no random split.
* **Prohibited overclaim:** presenting robustness as model selection, as proof
  of generalization, or as a superiority argument.
* **Mandatory accompanying limitation:** the primary ordering was preserved in
  Parts 2-6 and not in Part 1; no winner was selected on this evidence.

## C7 — Explainability

* **Source:** `{MODEL_REL}`, `{PREP_REL}`
* **Committed values:** intercept plus {model["n_design_columns"]} coefficients
* **Permissible wording:** "regularized conditional associations"; odds ratios
  per 1-SD increase for standardized continuous features and for
  indicator = 1 versus 0 for the binary missingness indicators.
* **Prohibited overclaim:** causal language; variable-importance ranking;
  significance marks; confidence intervals or p-values on any coefficient;
  reordering terms by magnitude.
* **Mandatory accompanying limitation:** coefficients are penalized (L2,
  C = 0.1) and conditional on the remaining terms. Six of the nine
  missingness-indicator coefficients are exactly zero in the locked model;
  three are non-zero. This pattern is reported descriptively and does not
  establish statistical significance or a general claim that missingness is
  informative.

## C8 — Sample size and precision

* **Source:** `{FT_METRICS_REL}`, `{FT_PROV_REL}`
* **Committed values:** {ft["evaluable_rows"]} evaluable rows,
  **{ft["positive"]} positive** and {ft["negative"]} negative observations,
  {ft["unique_tickers"]} unique tickers; development fit set {fit["rows"]} rows
  with {fit["positive"]} positives
* **Permissible wording:** "Only {ft["positive"]} positive observations were
  present in the Final Test." This must appear explicitly in the Results and
  the Limitations.
* **Prohibited overclaim:** any precision, stability or generalization claim
  that the event count cannot support.

## C9 — Reproducibility and auditability

* **Source:** `{FT_QC_REL}`, `{FT_MANIFEST_REL}`, `{FT_PROV_REL}`
* **Committed values:** 21 fail-closed controls FT01-FT21 all PASS; one pass;
  `model_fits_executed = {prov["model_fits_executed"]}`;
  `final_test_rows_read = {prov["final_test_rows_read"]}`
* **Permissible wording:** the executor was frozen and hashed before Final Test
  access; the Final Test was opened exactly once; artifacts are SHA-256 pinned.
* **Prohibited overclaim:** describing this as external or independent
  validation.

---

## Standing prohibitions for the manuscript

1. No second Final Test pass, and no re-reading of Final Test rows.
2. No new metric, interval, replicate, p-value, subgroup or per-year
   performance value.
3. No calibration curve, decision curve or net-benefit quantity.
4. No refit, recalibration, tuning, model reselection or SHAP.
5. No causal claim from a predictive model.
6. No statement that the full repository test suite passes.
"""
    return text.encode("utf-8")


def build_legacy_supersession() -> bytes:
    text = f"""# Legacy output supersession — {LEGACY_DIR_REL}

## Status

    {LEGACY_STATUS}

`{LEGACY_DIR_REL}/` is **non-canonical**. Nothing in it may be cited, quoted,
copied or used as a source for any manuscript value.

## Why

That tree was produced by the Stage123-era pipeline, long before the
leakage-safe Stage125 dataset, the Stage126 tuning lock, the accepted
full-development refit and the single authorized Stage129 Final Test pass. It
describes a **different sample and a different analysis**:

* roughly 200 evaluation rows with about 9 positive observations, against the
  accepted Final Test cohort of 346 rows with 12 positives;
* an XGBoost-best conclusion, whereas the accepted analysis applies the
  human-selected `M1 / regularized_logistic_regression / logistic__C_0.1`;
* metric values that do not correspond to any accepted artifact.

Its numbers are therefore not merely outdated -- they **contradict** the
accepted analysis, and reusing them would misreport the study.

## Disposition

* The legacy files are **preserved byte-identical** for audit history.
* They are **not** deleted, overwritten, edited or regenerated by this package.
* No value from that tree appears anywhere in
  `{PKG_REL}/`.

## Canonical replacements

| legacy role | canonical source |
|---|---|
| test metrics table | `{PKG_REL}/{TABLES_SUBDIR}/table_2_final_test_aggregate_performance.csv` |
| operating point | `{PKG_REL}/{TABLES_SUBDIR}/table_3_operating_point_confusion_matrix.csv` |
| model description | `{PKG_REL}/table_model_coefficients_and_odds_ratios.csv` |
| figures | `{PKG_REL}/{FIGURES_SUBDIR}/` |
| claim wording | `{PKG_REL}/manuscript_claim_freeze.md` |
"""
    return text.encode("utf-8")


def build_readme(ft: dict[str, Any], model: dict[str, Any]) -> bytes:
    text = f"""# Stage130 Phase 1 — canonical manuscript evidence package

Presentation only. **No new scientific analysis was performed.**

* The Final Test was not reopened; `final_test_rows_read` by this action = 0.
* The row-level prediction artifact
  `stage129_final_test_predictions.json` was **never opened**; it is listed in
  `FORBIDDEN_SOURCES` and the loader refuses it fail-closed.
* No metric, confidence interval, bootstrap replicate, p-value, subgroup
  result, per-year performance value, calibration quantity, decision curve or
  threshold was computed. SHAP executions = 0.
* The only arithmetic applied is `exp(beta)` on the locked coefficients -- a
  deterministic transformation of a frozen artifact, authorized as manuscript
  presentation rather than as new estimation.

## Contents

| file | role |
|---|---|
| `manuscript_claim_freeze.md` | frozen claims: source, exact value, permissible wording, prohibited overclaim, mandatory limitation |
| `table_model_coefficients_and_odds_ratios.csv` | canonical coefficient/OR table ({model["n_design_columns"]} terms + intercept) |
| `{TABLES_SUBDIR}/` | six deterministic result tables |
| `{FIGURES_SUBDIR}/` | three schematic figures (no performance curves) |
| `legacy_outputs_supersession.md` | `{LEGACY_DIR_REL}` marked {LEGACY_STATUS} |
| `manifest.json` | SHA-256 + byte count per file, and the authoritative source of every displayed value |

## Reading the coefficient table

Continuous features are **standardized**, so their odds ratios are **per 1-SD
increase**; the standardizing mean and SD are shown per row. The nine
missingness indicators are **unstandardized binary**, so their odds ratios are
for **indicator = 1 versus 0**. Terms appear in the model's own order -- this
is deliberately **not** an importance ranking. No confidence interval, standard
error, p-value or significance marker is present, because none exists in the
locked artifact. All effects are **regularized conditional associations**, never
causal.

**Missingness indicators — descriptive fact only.** Six of the nine
missingness-indicator coefficients are exactly zero in the locked model; three
are non-zero (`ocf_to_assets_period_adjusted__missing`,
`operating_margin_period_adjusted__missing`,
`financial_expense_to_assets_period_adjusted__missing`). This pattern is
reported descriptively and does not establish statistical significance or a
general claim that missingness is informative.

## Figures

Only schematics and a coefficient plot. ROC, precision-recall, calibration,
subgroup and per-year performance curves are **absent by design**: each would
require row-level Final Test data or a new scientific calculation.

## Not authorized by this package

Ready-for-review, merge, a second Final Test pass, any new scientific
computation, and Stage130 scientific execution
(`stage130_scientific_execution_started = false`).
"""
    return text.encode("utf-8")


# ------------------------------------------------------------------- build
def build_package(repo_root: Path | str = REPO_ROOT) -> dict[str, bytes]:
    """Deterministic: identical inputs produce byte-identical outputs."""
    root = Path(repo_root).resolve()
    ft = _load(root, FT_METRICS_REL)
    prov = _load(root, FT_PROV_REL)
    qc = _load(root, FT_QC_REL)
    ft_manifest = _load(root, FT_MANIFEST_REL)
    model = _load(root, MODEL_REL)
    prep = _load(root, PREP_REL)
    split = _load(root, SPLIT_CONTRACT_REL)
    robust = _load(root, ROBUST_SYNTH_REL)
    dev_csv = _guarded_open(root, DEV_METRICS_REL).decode("utf-8")

    counters = qc["counters"]
    for field in ("model_fits_executed", "refits_executed",
                  "recalibration_executions", "shap_executions",
                  "p_values_computed", "holm_executions"):
        if counters[field] != 0:
            raise Stage130Error(f"source QC reports non-zero {field}")

    coef_csv = build_coefficient_table(model, prep)
    files: dict[str, bytes] = {
        "table_model_coefficients_and_odds_ratios.csv": coef_csv,
    }
    files.update(build_tables(ft, prov, model, split, dev_csv, robust, coef_csv))
    files.update(build_figures(model, split))
    files["manuscript_claim_freeze.md"] = build_claim_freeze(ft, prov, model)
    files["legacy_outputs_supersession.md"] = build_legacy_supersession()
    files["README.md"] = build_readme(ft, model)

    manifest = {
        "action_id": ACTION_ID,
        "artifact": "stage130_manuscript_evidence_package_manifest",
        "phase": "stage130_phase1_manuscript_evidence_package_and_claim_freeze",
        "base_commit": BASE_COMMIT,
        "new_scientific_analysis_performed": False,
        "final_test_rows_read_by_this_action": 0,
        "final_test_prediction_artifact_opened": False,
        "shap_executions": 0,
        "new_metrics_computed": 0,
        "new_confidence_intervals_computed": 0,
        "new_bootstrap_replicates": 0,
        "p_values_computed": 0,
        "thresholds_derived": 0,
        "models_fitted_or_refitted": 0,
        "only_deterministic_transformation_applied": "exp(beta) on locked coefficients",
        "prohibited_sources_never_opened": list(FORBIDDEN_SOURCES),
        "authoritative_value_sources": {
            "final_test_aggregate_metrics": FT_METRICS_REL,
            "final_test_provenance": FT_PROV_REL,
            "final_test_qc": FT_QC_REL,
            "final_test_manifest": FT_MANIFEST_REL,
            "locked_model": MODEL_REL,
            "locked_preprocessing": PREP_REL,
            "admitted_threshold": THRESHOLD_REL,
            "development_metrics": DEV_METRICS_REL,
            "robustness_closure": ROBUST_SYNTH_REL,
            "temporal_split_contract": SPLIT_CONTRACT_REL,
        },
        "source_sha256": {
            rel: _sha256(_guarded_open(root, rel)) for rel in sorted((
                FT_METRICS_REL, FT_PROV_REL, FT_QC_REL, FT_MANIFEST_REL,
                MODEL_REL, PREP_REL, THRESHOLD_REL, DEV_METRICS_REL,
                ROBUST_SYNTH_REL, SPLIT_CONTRACT_REL))
        },
        # The pinned SHA-256 of the Final Test package manifest itself. This
        # must be a digest, not an identifier: it is the value the field name
        # promises, and it must agree with `source_sha256` for the same file.
        "final_test_package_manifest_sha256_at_source":
            _sha256(_guarded_open(root, FT_MANIFEST_REL)),
        "legacy_outputs_status": {LEGACY_DIR_REL: LEGACY_STATUS},
        "package_files": {
            name: {"sha256": _sha256(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        },
        "stage130_scientific_execution_started": False,
        "ready_for_review_authorized": False,
        "merge_authorized": False,
    }
    files["manifest.json"] = _json_bytes(manifest)
    return files


def write_package(repo_root: Path | str = REPO_ROOT) -> dict[str, bytes]:
    root = Path(repo_root).resolve()
    files = build_package(root)
    out = root / PKG_REL
    for name, data in sorted(files.items()):
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return files


def main(argv: list[str] | None = None) -> int:
    files = write_package(REPO_ROOT)
    print(f"Stage130 Phase 1 package written: {len(files)} files")
    for name, data in sorted(files.items()):
        print(f"  {_sha256(data)}  {len(data):>7}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
