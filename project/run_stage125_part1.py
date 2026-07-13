#!/usr/bin/env python3
"""Runner for Stage125 Part 1 — Data Dictionary & Provenance Contract.

Usage:
    python project/run_stage125_part1.py --write
    python project/run_stage125_part1.py --check
    python project/run_stage125_part1.py --input PATH --output-dir DIR --write
    python project/run_stage125_part1.py --data-bundle bundle.zip --check

``--check`` never overwrites any tracked file; it only compares the freshly
computed deliverables against what is on disk and reports drift.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part1_data_contract as part1  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None,
                        help="path to modeling_all_rows_stage123.csv (canonical input)")
    parser.add_argument("--data-bundle", default=None,
                        help="read-only fallback data bundle ZIP (verified by SHA-256)")
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage125)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the deliverables")
    mode.add_argument("--check", action="store_true",
                      help="compute + compare only; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 1 — Data Dictionary & Provenance Contract")
    print("=" * 70)

    input_path = Path(args.input) if args.input else None
    bundle_path = Path(args.data_bundle) if args.data_bundle else None
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        result = part1.run(project_dir=ROOT, input_path=input_path,
                           bundle_path=bundle_path, output_dir=output_dir,
                           write=args.write)
    except part1.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    counts = result["counts"]
    print(f"Input source: {result['input_source']}")
    print(f"Input SHA-256: {result['input_sha256']}")
    print(f"Output dir: {result['output_dir']}")
    print(f"M1 rows={counts['rows']} unique_row_key={counts['unique_row_key']} "
          f"source_url_missing={counts['source_url_missing']} "
          f"audit_status_unknown={counts['audit_status_unknown']}")
    print(f"QC assertions: {qc['assertion_count']} "
          f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})")
    print("modeling_started=false | part2_started=false | no network extraction")

    if args.write:
        print(f"Wrote {len(result['files'])} files.")
        return 0 if qc["all_pass"] else 1

    if result["drift"]:
        print("DRIFT (on-disk differs from computed):", file=sys.stderr)
        for name in result["drift"]:
            print(f"  - {name}", file=sys.stderr)
        print("Run with --write to refresh.", file=sys.stderr)
        return 1
    print("Deliverables up to date (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
