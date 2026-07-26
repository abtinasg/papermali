#!/usr/bin/env python3
"""Runner for Stage126 M1 — Robustness Closure.

Usage:
    python project/run_stage126_m1_robustness_closure.py --build
    python project/run_stage126_m1_robustness_closure.py --check

Synthesis-only closure of the already-completed Parts 1-6. Offline.
Deterministic. Zero network. Never fits or predicts a model, never resamples,
never accesses the final test, and never selects a retained design or paper
winner.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_m1_robustness_closure as closure  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of the closure artifacts")
    mode.add_argument("--check", action="store_true",
                      help="zero-network validation; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 M1 — Robustness Closure (synthesis only)")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = closure.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except closure.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Contract: {closure.CONTRACT_ID} ({closure.CONTRACT_VERSION})")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"network={result['network_requests_attempted']} | "
        f"model_fit_calls={qc['model_fit_calls']} | "
        f"prediction_calls={qc['prediction_calls']} | "
        f"smote_calls={qc['smote_calls']} | smotenc_calls={qc['smotenc_calls']} | "
        f"shap_calls={qc['shap_calls']}"
    )
    print(f"robustness_closure_completed={qc['robustness_closure_completed']}")
    print(f"next_action_id={qc['next_action_id']} (requires separate human authorization)")
    print(
        "consumed Part1-6/primary artifacts immutable: "
        f"{result['before_hashes'] == result['after_hashes']}"
    )

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} closure outputs.")
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
