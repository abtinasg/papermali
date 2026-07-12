#!/usr/bin/env python3
"""Runner for Stage124 Gate B execution.

Usage:
    python project/run_stage124_gate_b_execution.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage124_gate_b_execution as gate_b  # noqa: E402


def main() -> int:
    print("=" * 70)
    print("Stage124 Gate B Execution — final eligibility rule application")
    print("=" * 70)
    print()

    try:
        result = gate_b.run(ROOT)
    except gate_b.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    print(f"Output directory: {result['output_dir']}")
    print()
    print(f"{'Sample design':<44} {'Pairs':>6} {'Pos':>5} {'Neg':>5} {'Miss':>5}")
    print("  " + "-" * 66)
    for design, s in result["stats"].items():
        print(f"{design:<44} {s['pairs']:>6} {s['positive']:>5} "
              f"{s['negative']:>5} {s['target_missing']:>5}")
    print()
    print(f"Unresolved counts: {result['unresolved_counts']}")
    print(f"QC assertions: {result['qc']['assertion_count']} "
          f"(failed={result['qc']['failed_count']}, all_pass={result['qc']['all_pass']})")
    print()
    print("gate_b_started = true | modeling_started = false")
    print("Next action: stage125-modeling-readiness")
    return 0 if result["qc"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
