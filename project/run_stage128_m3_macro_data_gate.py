#!/usr/bin/env python3
"""Runner — Stage128 M3 macro DATA Gate.

Authorized action: ``stage128-m3-macro-data-gate`` (one action only, consumed
when the Gate result has been recorded and verified).

Executes the data-admission Gate for the exact frozen three-variable M3 macro
block. It fits no model, produces no prediction, computes no predictive
metric, runs no resampling, executes no M3-versus-M2 comparison and reads no
final-test predictor or target value.

Usage::

    PYTHONPATH=project python \\
        project/run_stage128_m3_macro_data_gate.py --build
    PYTHONPATH=project python \\
        project/run_stage128_m3_macro_data_gate.py --check
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m3_macro_data_gate as g  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true",
                    help="build and write the M3 macro data Gate package")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and verify the on-disk package")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args()
    if not (args.build or args.check):
        ap.error("one of --build or --check is required")

    built = g.build_package(args.root, write=bool(args.build))
    qc = built["qc_report"]

    if args.check:
        from pathlib import Path

        root = Path(args.root)
        drift = [
            rel for rel, text in built["artifact_texts"].items()
            if not (root / rel).is_file()
            or (root / rel).read_text(encoding="utf-8") != text
        ]
        if drift:
            print(f"DRIFT: on-disk package differs from a fresh build: {drift}")
            return 1

    decision = built["decision"]
    print(f"action: {g.ACTION_ID}")
    print(f"gate_status: {decision['gate_status']}")
    print(f"phase_a_lock_status: {built['definition_lock']['lock_status']}")
    print(f"phase_b_executed: {decision['phase_b_executed']}")
    print(f"parent_rows: {built['parent_surface']['parent_rows']} "
          f"positive: {built['parent_surface']['parent_positive']} "
          f"companies: {built['parent_surface']['parent_companies']}")
    print(f"model_fits: {decision['model_fits']} "
          f"predictions: {decision['predictions']} "
          f"predictive_metrics: {decision['predictive_metrics_computed']}")
    print(f"final_test_locked: {decision['final_test_locked']}")
    print(f"m3_incremental_evaluation_authorized: "
          f"{decision['m3_incremental_evaluation_authorized']}")
    print(f"assertions: {qc['assertion_count']} failed: {qc['failed_count']}")
    print(f"all_pass: {qc['all_pass']}")
    return 0 if qc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
