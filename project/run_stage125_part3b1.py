#!/usr/bin/env python3
"""Runner for Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock.

Usage:
    python project/run_stage125_part3b1.py --write
    python project/run_stage125_part3b1.py --check

Decision-lock / schema / synthetic validation only. No network, no real
extraction, no real scoring, no modeling. Merge requires explicit user approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b1_decision_lock as part3b1  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage125)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write deliverables")
    mode.add_argument("--check", action="store_true",
                      help="compute + compare only; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3B.1 — Feature Definition & Scoring Adjudication Lock")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part3b1.run(
            project_dir=ROOT, output_dir=output_dir, write=args.write,
        )
    except part3b1.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part3b1.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(f"QC assertions: {qc['assertion_count']} "
          f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})")
    print(
        "part3b1_decision_locked=true | part3b_completed=false | "
        "modeling_started=false | no network | no real extraction | no real scoring"
    )

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
