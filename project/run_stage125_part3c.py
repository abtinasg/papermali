#!/usr/bin/env python3
"""Runner for Stage125 Part 3C — Leakage-Safe Dataset Finalization.

Usage:
    python project/run_stage125_part3c.py --build
    python project/run_stage125_part3c.py --check

Offline. Deterministic. Zero network. No CODAL. No modeling. No Stage126.
Merge requires explicit human approval.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3c_leakage_safe_dataset_finalization as part3c  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default=None,
        help="output directory (default project/stage125)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--build", action="store_true",
        help="offline deterministic build of authorized Part 3C outputs",
    )
    mode.add_argument(
        "--check", action="store_true",
        help="zero-network validation; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3C — Leakage-Safe Dataset Finalization")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = part3c.run(
            project_dir=ROOT,
            output_dir=output_dir,
            build=args.build,
            check=args.check,
        )
    except part3c.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    qc = result["qc"]
    print(f"Baseline commit: {part3c.EXPECTED_BASELINE_COMMIT}")
    print(f"Output dir: {result['output_dir']}")
    print(f"Bulky dir: {result['bulky_dir']}")
    print(
        f"QC assertions: {qc['assertion_count']} "
        f"(failed={qc['failed_count']}, all_pass={qc['all_pass']})"
    )
    print(
        f"network_requests_attempted={result['network_requests_attempted']} | "
        "broad_codal_capture_stopped=true | "
        "financial_data_researcher_verified_frozen=true | "
        f"active_availability_method={qc.get('active_availability_method')} | "
        f"active_availability_lag_months="
        f"{qc.get('active_availability_lag_months')} | "
        "stage126_authorized=false | modeling_authorized=false"
    )
    print(
        f"research pointers: "
        f"last={qc['research_pointers']['last_completed_research_action_id']} "
        f"next={qc['research_pointers']['next_research_action_id']}"
    )
    for s in qc.get("sample_summaries") or []:
        print(
            f"  {s['sample_design']}: "
            f"audited={s.get('audited_pairs', s['pairs'])}/"
            f"{s.get('audited_companies', s['companies'])}/"
            f"{s.get('audited_positive', s['positive'])}/"
            f"{s.get('audited_negative', s['negative'])} "
            f"analysis_ready={s.get('analysis_ready_pairs', '?')}/"
            f"{s.get('analysis_ready_companies', '?')}/"
            f"{s.get('analysis_ready_positive', '?')}/"
            f"{s.get('analysis_ready_negative', '?')} "
            f"excluded={s.get('excluded_timing_exception_count', '?')}"
        )

    if args.build:
        print(f"Wrote {len(result.get('files') or {})} Part 3C outputs.")
        return 0 if qc["all_pass"] else 1

    if result.get("drift"):
        # Drift only fails --check when canonical tracked files differ;
        # run() already raised if so. Residual bulky-absent drift is informational.
        bulky_only = all(
            str(x).startswith("part3c_outputs/") for x in result["drift"]
        )
        if not bulky_only:
            print("DRIFT (on-disk differs from computed):", file=sys.stderr)
            for name in result["drift"]:
                print(f"  - {name}", file=sys.stderr)
            print("Run with --build to refresh.", file=sys.stderr)
            return 1
    print("Deliverables up to date (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
