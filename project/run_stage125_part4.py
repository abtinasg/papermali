#!/usr/bin/env python3
"""Runner for Stage125 Part 4 — Statistical Analysis Plan.

Usage:
    python project/run_stage125_part4.py --build
    python project/run_stage125_part4.py --check

Offline. Deterministic. Zero network. No modeling. No Stage126.
Merge requires explicit human approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part4_statistical_analysis_plan as part4  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default=None,
        help="output directory (default project/stage125)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--build", action="store_true",
        help="offline deterministic build of Part 4 SAP contracts",
    )
    mode.add_argument(
        "--check", action="store_true",
        help="zero-network validation; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 4 — Statistical Analysis Plan")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part4.run(
            project_dir=ROOT,
            output_dir=output_dir,
            build=args.build,
            check=args.check,
        )
    except part4.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part4.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"network_requests_attempted={result['network_requests_attempted']} | "
        f"model_fit_calls={qc['model_fit_calls']} | "
        f"prediction_calls={qc['prediction_calls']} | "
        f"final_test_accessed_for_modeling="
        f"{qc['final_test_accessed_for_modeling']} | "
        "stage126_authorized=false | modeling_authorized=false"
    )
    print(
        f"research pointers: "
        f"last={qc['research_pointers']['last_completed_research_action_id']} "
        f"next={qc['research_pointers']['next_research_action_id']}"
    )
    print(
        f"primary sample={part4.PRIMARY_SAMPLE} "
        f"target={part4.PRIMARY_TARGET} "
        f"M1_features={len(part4.M1_PRIMARY_FEATURE_ORDER)}"
    )

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 4 outputs.")
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
