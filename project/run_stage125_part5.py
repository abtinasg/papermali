#!/usr/bin/env python3
"""Runner for Stage125 Part 5 — Readiness Closure.

Usage:
    python project/run_stage125_part5.py --build
    python project/run_stage125_part5.py --check

Offline. Deterministic. Zero network. No modeling. No Stage126.
Merge requires explicit human approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part5_readiness_closure as part5  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default=None,
        help="output directory (default project/stage125)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--build", action="store_true",
        help="offline deterministic build of Part 5 readiness-closure artifacts",
    )
    mode.add_argument(
        "--check", action="store_true",
        help="zero-network validation; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 5 — Readiness Closure")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part5.run(
            project_dir=ROOT,
            output_dir=output_dir,
            build=args.build,
            check=args.check,
        )
    except part5.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part5.EXPECTED_BASELINE_COMMIT}")
    print(f"Baseline tree: {part5.EXPECTED_BASELINE_TREE}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"gate_125_0={qc['stage125_gate_125_0']} | "
        f"network_requests_attempted={result['network_requests_attempted']} | "
        f"model_fit_calls={qc['model_fit_calls']} | "
        f"prediction_calls={qc['prediction_calls']} | "
        f"shap_calls={qc['shap_calls']} | "
        "stage126_authorized=false | modeling_authorized=false"
    )
    print(
        f"research pointers: "
        f"last={qc['research_pointers']['last_completed_research_action_id']} "
        f"next={qc['research_pointers']['next_research_action_id']}"
    )

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 5 outputs.")
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
