#!/usr/bin/env python3
"""Runner — Stage128 M3I-2 prospective contract lock.

Authorized action: ``stage128-m3i2-prospective-contract-lock`` (one action
only, consumed when the contract lock has been recorded and verified).

Builds and validates a METADATA-ONLY prospective contract lock. It retrieves no
macro observation, executes no Data Gate, fits no model, produces no prediction
or predictive metric, runs no M3I-versus-M2 comparison and reads no final-test
predictor or target value.

Usage::

    PYTHONPATH=project python \\
        project/run_stage128_m3_intl_macro_contract_lock.py --build
    PYTHONPATH=project python \\
        project/run_stage128_m3_intl_macro_contract_lock.py --check
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m3_intl_macro_contract_lock as c  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true",
                    help="build and write the M3I-2 contract-lock package")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and verify the on-disk package")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args()
    if not (args.build or args.check):
        ap.error("one of --build or --check is required")

    built = c.build_package(args.root, write=bool(args.build))
    qc = built["qc_report"]
    decision = built["decision"]

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

    print(f"action: {c.ACTION_ID}")
    print(f"contract_status: {decision['m3i2_contract_status']}")
    print(f"baseline: {decision['baseline_branch']} @ "
          f"{decision['baseline_commit']} (pr #{decision['baseline_pr_number']}"
          f", merged={decision['predecessor_pr_merged']})")
    print(f"pr_base_branch: {decision['pr_base_branch']} "
          f"draft={decision['pr_is_draft']}")
    print(f"m3_cbi_status: {decision['m3_cbi_gate_status']} "
          f"changed={decision['m3_cbi_contract_changed']}")
    print(f"m3i2_retrieval_started: {decision['m3i2_retrieval_started']} "
          f"gate_executed: {decision['m3i2_data_gate_executed']} "
          f"modeling_started: {decision['m3i2_modeling_started']}")
    print(f"m3i3_financing_lock: {decision['m3i3_financing_lock']} "
          f"admitted: {decision['m3i3_admitted']}")
    print(f"network_requests: {decision['network_requests']} "
          f"macro_observations_read: {decision['macro_observations_read']} "
          f"model_fits: {decision['model_fits']} "
          f"coverage_calculations: {decision['coverage_calculations']}")
    print(f"final_test_locked: {decision['final_test_locked']} "
          f"m4_started: {decision['m4_started']} "
          f"merge_authorized: {decision['merge_authorized']}")
    print(f"assertions: {qc['assertion_count']} failed: {qc['failed_count']}")
    print(f"all_pass: {qc['all_pass']}")
    return 0 if qc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
