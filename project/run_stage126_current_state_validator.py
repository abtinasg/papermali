#!/usr/bin/env python3
"""Runner for the independent Stage126 current-state validator.

Usage:
    python project/run_stage126_current_state_validator.py --build
    python project/run_stage126_current_state_validator.py --check

This is the SOLE current-state validation surface for Stage126. Stage125 Part 5
is a frozen historical closure: it is neither imported nor executed here, and
`run_stage125_part5.py --check` is no longer a required live gate. Previous
robustness runners are not current-state gates either — previous scientific
artifacts are protected by immutable hashes.

Read-only and deterministic. No model fitting, no retuning, no full-development
refit, no final-test access, no final-test evaluation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage126_current_state_validator as v  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage126)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true",
                      help="offline deterministic build of the boundary artifacts")
    mode.add_argument("--check", action="store_true",
                      help="validate current state; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage126 — Independent Current-State Validator")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = v.run(
            project_dir=ROOT, output_dir=output_dir,
            build=args.build, check=args.check,
        )
    except v.ValidationFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    meta = result["metadata"]
    report = result["report"]
    print(f"Validator: {v.VALIDATOR_ID} ({v.VALIDATOR_VERSION})")
    print(f"Decision: {v.DECISION_ID} ({v.DECISION_VERSION})")
    print(f"Decision text SHA-256: {v.HUMAN_DECISION_TEXT_SHA256}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"Assertions: {meta['assertion_count']} "
        f"(failed={meta['failed_count']}, all_pass={meta['all_pass']})"
    )
    print("Stage125 Part 5: historical_immutable | "
          f"live gate active={report['stage125_part5_live_gate_active']} | "
          f"executed={meta['stage125_part5_executed']} | "
          f"imported={meta['stage125_part5_imported']}")
    print(
        "Completed categories: "
        + ", ".join(report["completed_category_ids"])
    )
    print(
        f"Next category: {report['next_category_id']} "
        f"(authorized={report['next_category_authorized']})"
    )
    print(
        f"M1 robustness completed={report['m1_robustness_completed']} | "
        f"full-development refit={report['full_development_refit_performed']} | "
        f"final test unlocked={report['final_test_unlocked']}"
    )
    print(
        "Prior-part verification regeneration allowed: "
        f"{report['prior_part_verification_artifact_regeneration_allowed']} | "
        "reopening requires scientific error + new authorization: "
        f"{report['prior_part_reopening_requires_scientific_error']}"
    )
    print(f"Last completed micro-part: {report['last_completed_micro_part']}")

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} boundary outputs.")
        return 0 if meta["all_pass"] else 1

    if result.get("drift"):
        print("DRIFT (on-disk differs from computed):", file=sys.stderr)
        for name in result["drift"]:
            print(f"  - {name}", file=sys.stderr)
        print("Run with --build to refresh.", file=sys.stderr)
        return 1
    print("Current state validated (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
