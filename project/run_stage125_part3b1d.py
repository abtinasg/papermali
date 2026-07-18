#!/usr/bin/env python3
"""Runner for Stage125 Part 3B.1D — Controlled Same-Five Metadata Resolution Capture.

Usage:
    python project/run_stage125_part3b1d.py --capture
    python project/run_stage125_part3b1d.py --check

Exactly four authorized CODAL Decision.aspx GET requests within the existing
five-row pilot. اردستان receives zero network requests. Metadata provenance
only. No binding-status mutation, available_at assignment, financial-value
extraction, accessibility scoring, Gate application, 80-row scale-up,
Part 3B.2, Stage126, or modeling. Merge requires explicit human approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b1d_same_five_metadata_resolution_capture as part3b1d  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="output directory (default project/stage125)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--capture",
        action="store_true",
        help="perform exactly four authorized CODAL GETs and write receipts",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="zero-network validation; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3B.1D — Controlled Same-Five Metadata Resolution Capture")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part3b1d.run(
            project_dir=ROOT,
            output_dir=output_dir,
            capture=args.capture,
            check=args.check,
        )
    except part3b1d.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1
    except part3b1d.NetworkPolicyError as exc:
        print(f"FAIL (network policy): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part3b1d.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"bound={qc['bound_count']} unresolved={qc['unresolved_count']} "
        f"rejected={qc['rejected_count']} "
        f"available_at_non_null={qc['available_at_non_null_count']}"
    )
    print(
        f"logical_network_requests_attempted="
        f"{qc['logical_network_requests_attempted']} "
        f"(authorized_max={qc['authorized_logical_requests']})"
    )
    print(
        "same_five_metadata_resolution_capture_completed="
        f"{qc['same_five_metadata_resolution_capture_completed']} | "
        "predictor_available_at_evidence_collected="
        f"{qc['predictor_available_at_evidence_collected']} | "
        "part3b_completed=false | modeling_started=false"
    )

    if args.capture:
        print(f"Wrote {len(result.get('files') or {})} tracked deliverables.")
        return 0 if qc["all_pass"] else 1

    if result.get("drift"):
        print("DRIFT (on-disk differs from computed):", file=sys.stderr)
        for name in result["drift"]:
            print(f"  - {name}", file=sys.stderr)
        print("Run with --capture to refresh.", file=sys.stderr)
        return 1
    print("Deliverables up to date (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
