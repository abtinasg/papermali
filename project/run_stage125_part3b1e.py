#!/usr/bin/env python3
"""Runner for Stage125 Part 3B.1E — Conservative Six-Month Lag Decision Lock.

Usage:
    python project/run_stage125_part3b1e.py --write
    python project/run_stage125_part3b1e.py --check

Offline methodology lock only. Zero network. No CODAL capture.
No financial-value re-extraction. Merge requires explicit human approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b1e_conservative_lag_decision as part3b1e  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default=None,
        help="output directory (default project/stage125)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write deliverables")
    mode.add_argument(
        "--check", action="store_true",
        help="zero-network validation; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3B.1E — Conservative Six-Month Lag Decision Lock")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part3b1e.run(
            project_dir=ROOT,
            output_dir=output_dir,
            write=args.write,
            check=args.check,
        )
    except part3b1e.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part3b1e.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"network_requests_attempted={result['network_requests_attempted']} | "
        "broad_codal_capture_stopped=true | "
        "financial_data_researcher_verified_frozen=true | "
        "conservative_lag_months=6 | "
        "stage126_authorized=false | modeling_authorized=false"
    )
    print(
        f"research pointers: "
        f"last={qc['research_pointers']['last_completed_research_action_id']} "
        f"next={qc['research_pointers']['next_research_action_id']}"
    )

    if args.write:
        print(f"Wrote {len(result.get('files') or {})} tracked deliverables.")
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
