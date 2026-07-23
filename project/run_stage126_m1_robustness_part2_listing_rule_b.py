#!/usr/bin/env python3
"""Runner for Stage126 M1 — Robustness Part 2: listing Rule B sample.

Usage:
    python project/run_stage126_m1_robustness_part2_listing_rule_b.py --build
    python project/run_stage126_m1_robustness_part2_listing_rule_b.py --check

Explicitly human-authorized. Development folds only. Offline. Deterministic.
Zero network. Only the sample changes. No retuning, no full-development refit,
no final-test access or evaluation, no SMOTE/SMOTENC, no SHAP, no calibration,
no bootstrap/Holm, no winner selection. Part 3 is not authorized.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_m1_robustness_part2_listing_rule_b as p2  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of the Part 2 artifacts")
    mode.add_argument("--check", action="store_true",
                      help="zero-network validation; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 M1 — Robustness Part 2: Listing Rule B Sample")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = p2.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except p2.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    cmp_ = result["comparison"]
    print(f"Category: {p2.CATEGORY_ID} (changed dimension: {qc['changed_dimension']})")
    print(f"Sample: {qc['sample']} (primary: {qc['primary_sample']})")
    print(f"Target: {qc['target']} | Feature set: {qc['feature_set']} "
          f"({qc['base_feature_count']} base -> "
          f"{qc['transformed_feature_count']} transformed columns)")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"Rule B rows={qc['rule_b_total_rows']} companies={qc['rule_b_companies']} "
        f"pos={qc['rule_b_positive']} neg={qc['rule_b_negative']} | "
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
        f"tuning_search_calls={qc['tuning_search_calls']} | "
        f"smote={qc['smote_calls']} | smotenc={qc['smotenc_calls']} | "
        f"shap={qc['shap_calls']} | network={qc['network_requests_attempted']}"
    )
    print(
        f"final_test_identities_seen={qc['final_test_rows_seen_but_not_parsed']} | "
        f"final_test_predictor_rows_loaded={qc['final_test_predictor_rows_loaded']} | "
        f"final_test_target_rows_loaded={qc['final_test_target_rows_loaded']} | "
        f"final_test_evaluations={qc['final_test_evaluations']}"
    )
    nd = qc["sample_delta"]["net_difference"]
    print(
        f"sample delta vs Rule A: rows={nd['analysis_ready']['rows']} "
        f"companies={nd['analysis_ready']['companies']} "
        f"development={nd['development']['rows']} "
        f"oof={nd['oof_validation']['rows']} "
        f"final_test_identities={nd['final_test_identities']}"
    )
    print(f"OOF rows: {qc['oof_rows_total']} | metrics rows: {qc['metrics_rows']}")
    for r in result["metrics_rows"]:
        if r["scope"] == "pooled_development_oof":
            print(
                f"  pooled[{r['model_family']}] PR-AUC={r['pr_auc']} "
                f"ROC-AUC={r['roc_auc']} Brier={r['brier_score']} "
                f"Recall@10%={r['recall_at_10pct']} Lift@10%={r['lift_at_10pct']}"
            )
    print(
        "  primary ordering: "
        + " > ".join(cmp_["primary_observed_ordering"])
    )
    print(
        "  Part 2 observed ordering: "
        + " > ".join(cmp_["part2_observed_sensitivity_ordering"])
        + f" (differs={cmp_['observed_ordering_differs_from_primary']})"
    )
    print("Part 3 authorized: false | final test: locked | sensitivity only")

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 2 outputs.")
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
