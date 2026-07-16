#!/usr/bin/env python3
"""Runner for Stage125 Part 3B.0 — Evidence Capture Readiness.

Usage:
    python project/run_stage125_part3b0.py --write
    python project/run_stage125_part3b0.py --check

``--check`` never overwrites any tracked file; it only compares the freshly
computed deliverables against what is on disk and reports drift. There is no
network-enabled mode.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as readiness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage125)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the deliverables")
    mode.add_argument("--check", action="store_true",
                      help="compute + compare only; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3B.0 — Evidence Capture Readiness")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        result = readiness.run(project_dir=ROOT, output_dir=output_dir,
                               write=args.write)
    except readiness.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    guard = result.get("guard_evidence") or {}
    print(f"Baseline commit: {readiness.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(f"QC assertions: {qc['assertion_count']} "
          f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})")
    if result.get("historical_baseline_ok"):
        print("historical_baseline_mode=true (Part 3B authorized; "
              "Part 3B.0 artifacts verified byte-identical)")
    print("part3b0_readiness=true | part3b_started=false | "
          "evidence_collected=false | accessibility_scoring_applied=false")
    print(f"network_calls_attempted={guard.get('network_calls_attempted', 0)} | "
          "network_extraction_performed=false | modeling_started=false")

    if args.write:
        print(f"Wrote {len(result.get('files') or {})} files.")
        return 0 if qc["all_pass"] else 1

    if result.get("drift"):
        print("DRIFT (on-disk differs from computed):", file=sys.stderr)
        for name in result["drift"]:
            print(f"  - {name}", file=sys.stderr)
        print("Run with --write to refresh.", file=sys.stderr)
        return 1
    print("Deliverables up to date (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
