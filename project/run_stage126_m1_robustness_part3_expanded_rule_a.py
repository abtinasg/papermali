#!/usr/bin/env python3
"""Runner for Stage126 M1 — Robustness Part 3: expanded Rule A company scope.

Usage:
    python project/run_stage126_m1_robustness_part3_expanded_rule_a.py --build
    python project/run_stage126_m1_robustness_part3_expanded_rule_a.py --check

Explicitly human-authorized. Development folds only. Offline. Deterministic.
Zero network. Only the company-scope sample changes. No retuning, no
full-development refit, no final-test predictor/target access, no final-test
evaluation, no calibration, no threshold optimization, no bootstrap, no Holm
correction, no p-values, no winner selection, no SMOTE/SMOTENC, no SHAP.
Part 4 is not authorized. Stage125 Part 5 is historical and is not a gate.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_m1_robustness_part3_expanded_rule_a as p3  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of the Part 3 artifacts")
    mode.add_argument("--check", action="store_true",
                      help="zero-network validation; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 M1 — Robustness Part 3: Expanded Rule A Company Scope")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = p3.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except p3.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    cmp_ = result["comparison"]
    print(f"Category: {p3.CATEGORY_ID} (changed dimension: {qc['changed_dimension']})")
    print(f"Micro-part: {p3.MICRO_PART_ID}")
    print(f"Sample: {qc['sample']} (primary: {qc['primary_sample']})")
    print(f"Target: {qc['target']} | Feature set: {qc['feature_set']} "
          f"({qc['base_feature_count']} base -> "
          f"{qc['transformed_feature_count']} model-matrix columns)")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"Analysis-ready rows={qc['analysis_ready_rows']} "
        f"companies={qc['analysis_ready_companies']} "
        f"pos={qc['analysis_ready_positive']} neg={qc['analysis_ready_negative']} | "
        f"development={qc['development_rows_loaded']} "
        f"(pos={qc['development_positive']}, neg={qc['development_negative']})"
    )
    print(
        f"folds: {qc['fold1_train_rows']}/{qc['fold1_validation_rows']}/"
        f"{qc['fold2_train_rows']}/{qc['fold2_validation_rows']}"
    )
    print(
        f"model_fit_calls={qc['model_fit_calls']} | "
        f"prediction_calls={qc['prediction_calls']} | "
        f"network={qc['network_requests_attempted']}"
    )
    print("zero counters: " + ", ".join(
        f"{k}={v}" for k, v in sorted(qc["zero_counters"].items())
    ))
    print(
        f"final_test_identities_counted={qc['final_test_identities_counted']} | "
        f"predictor_rows_loaded={qc['final_test_predictor_rows_loaded']} | "
        f"target_rows_loaded={qc['final_test_target_rows_loaded']} | "
        f"predictions={qc['final_test_predictions_generated']} | "
        f"evaluations={qc['final_test_evaluations']}"
    )
    d = qc["sample_delta"]
    print(
        f"sample delta vs primary: +{d['expanded_only_rows']} rows, "
        f"+{d['company_delta']} companies, {d['positive_delta']:+d} positive, "
        f"+{d['negative_delta']} negative | development +"
        f"{d['development_rows_added']} | OOF +{d['oof_identities_added']} | "
        f"final-test identities +{d['final_test_identities_added']}"
    )
    print(f"OOF rows: {qc['oof_rows_total']} | metrics rows: {qc['metrics_rows']}")
    for r in result["metrics_rows"]:
        if r["scope"] == "pooled_development_oof":
            print(
                f"  pooled[{r['model_family']}] PR-AUC={r['pr_auc']} "
                f"ROC-AUC={r['roc_auc']} Brier={r['brier_score']} "
                f"Recall@10%={r['recall_at_10pct']} Lift@10%={r['lift_at_10pct']}"
            )
    print("  primary ordering: " + " > ".join(cmp_["primary_observed_ordering"]))
    print("  Part 3 ordering:  " + " > ".join(cmp_["part3_observed_ordering"]))
    print(f"  primary ordering preserved: {cmp_['primary_ordering_preserved']}")
    print("Part 4 authorized: false | final test: locked | "
          "development-only sample sensitivity")

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 3 outputs.")
        return 0 if qc["all_pass"] else 1

    if result.get("drift"):
        print("DRIFT (on-disk differs from computed):", file=sys.stderr)
        for name in result["drift"]:
            print(f"  - {name}", file=sys.stderr)
        print("Run with --build to refresh.", file=sys.stderr)
        return 1
    print("Deliverables up to date (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
