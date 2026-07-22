#!/usr/bin/env python3
"""Runner for Stage126 M1 — Primary Development-Fold Tuning.

Usage:
    python project/run_stage126_m1_primary_development_tuning.py --build
    python project/run_stage126_m1_primary_development_tuning.py --check

Human-authorized. Offline. Deterministic. Zero network. Development-only.
The final test remains locked; no final-test predictor/target values are
inspected; no final-test evaluation occurs. No SMOTE. No SHAP. No robustness.
No full-development refit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_m1_primary_development_tuning as m1  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of Stage126 M1 tuning")
    mode.add_argument("--check", action="store_true",
                      help="zero-network validation; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 M1 — Primary Development-Fold Tuning")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = m1.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except m1.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {m1.EXPECTED_BASELINE_COMMIT}")
    print(f"Baseline tree: {m1.EXPECTED_BASELINE_TREE}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"network={result['network_requests_attempted']} | "
        f"final_test_predictor_rows_loaded={qc['final_test_predictor_rows_loaded']} | "
        f"final_test_target_rows_loaded={qc['final_test_target_rows_loaded']} | "
        f"final_test_evaluations={qc['final_test_evaluations']} | "
        f"shap_calls={qc['shap_calls']} | smote_calls={qc['smote_calls']}"
    )
    for fam, cid in qc["selected_configurations"].items():
        print(f"  selected[{fam}] = {cid}")

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Stage126 M1 outputs.")
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
