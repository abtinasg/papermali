#!/usr/bin/env python3
"""Runner for Stage125 Part 3A.1 — User-Approved Pilot Decision Lock.

Usage:
    python project/run_stage125_part3a_decision_lock.py --write
    python project/run_stage125_part3a_decision_lock.py --check
    python project/run_stage125_part3a_decision_lock.py --all-rows PATH --pairs PATH --write

``--check`` never overwrites any tracked file; it only compares the freshly
computed deliverables against what is on disk and reports drift.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3a_decision_lock as lock  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-rows", default=None,
                        help="path to modeling_all_rows_stage124_gate_b.csv")
    parser.add_argument("--pairs", default=None,
                        help="path to modeling_one_year_ahead_stage124_gate_b.csv")
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage125)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the deliverables")
    mode.add_argument("--check", action="store_true",
                      help="compute + compare only; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3A.1 — User-Approved Pilot Decision Lock")
    print("=" * 70)

    all_rows_path = Path(args.all_rows) if args.all_rows else None
    pairs_path = Path(args.pairs) if args.pairs else None
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        result = lock.run(project_dir=ROOT, all_rows_path=all_rows_path,
                          pairs_path=pairs_path, output_dir=output_dir,
                          write=args.write)
    except lock.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    counts = result.get("counts") or {}
    pilot = result.get("pilot_selection") or {}
    print(f"Baseline commit: {lock.EXPECTED_BASELINE_COMMIT}")
    if result.get("historical_baseline_ok"):
        print("historical_baseline_mode=true (Part 3B authorized; "
              "Part 3A.1 artifacts verified byte-identical)")
    else:
        print(f"Input all_rows SHA-256: {result.get('input_all_rows_sha256')}")
        print(f"Input pairs SHA-256: {result.get('input_pairs_sha256')}")
        print(f"Pairs={counts.get('pairs')} all_rows={counts.get('all_rows')} "
              f"tickers={counts.get('unique_tickers_pairs')}")
    print(f"Output dir: {result['output_dir']}")
    print(f"Selected pilot: {lock.APPROVED_PILOT_OPTION} "
          f"n={pilot.get('sample_size')} pos={pilot.get('positive')} "
          f"neg={pilot.get('negative')}")
    print(f"QC assertions: {qc['assertion_count']} "
          f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})")
    print("modeling_started=false | part3a_decision_locked=true | "
          "part3b_started=false | no evidence | no network extraction")

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
