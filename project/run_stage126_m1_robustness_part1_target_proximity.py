#!/usr/bin/env python3
"""Runner for Stage126 M1 — Robustness Part 1: target-proximity six-feature set.

Usage:
    python project/run_stage126_m1_robustness_part1_target_proximity.py --build
    python project/run_stage126_m1_robustness_part1_target_proximity.py --check

Explicitly human-authorized. Development folds only. Offline. Deterministic.
Zero network. Only the feature set changes. No retuning, no full-development
refit, no final-test access or evaluation, no SMOTE/SMOTENC, no SHAP, no
calibration, no bootstrap/Holm, no winner selection. Part 2 is not authorized.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_m1_robustness_part1_target_proximity as p1  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of the Part 1 artifacts")
    mode.add_argument("--check", action="store_true",
                      help="zero-network validation; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 M1 — Robustness Part 1: Target-Proximity Six-Feature Set")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = p1.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except p1.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Category: {p1.CATEGORY_ID}")
    print(f"Feature set: {p1.FEATURE_SET_NAME} "
          f"({qc['base_feature_count']} base -> "
          f"{qc['transformed_feature_count']} transformed columns)")
    print(f"Sample: {qc['sample']} | Target: {qc['target']}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"model_fit_calls={qc['model_fit_calls']} | "
        f"prediction_calls={qc['prediction_calls']} | "
        f"tuning_search_calls={qc['tuning_search_calls']} | "
        f"smote={qc['smote_calls']} | smotenc={qc['smotenc_calls']} | "
        f"shap={qc['shap_calls']} | network={qc['network_requests_attempted']}"
    )
    print(
        f"final_test_predictor_rows_loaded={qc['final_test_predictor_rows_loaded']} | "
        f"final_test_target_rows_loaded={qc['final_test_target_rows_loaded']} | "
        f"final_test_evaluations={qc['final_test_evaluations']}"
    )
    print(f"OOF rows: {qc['oof_rows_total']} | metrics rows: {qc['metrics_rows']}")
    for r in result["metrics_rows"]:
        if r["scope"] == "pooled_development_oof":
            print(
                f"  pooled[{r['model_family']}] PR-AUC={r['pr_auc']} "
                f"ROC-AUC={r['roc_auc']} Brier={r['brier_score']} "
                f"Recall@10%={r['recall_at_10pct']} Lift@10%={r['lift_at_10pct']}"
            )
    print("Part 2 authorized: false | final test: locked")

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 1 outputs.")
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
