#!/usr/bin/env python3
"""Runner — Stage128 M2 retained-block HUMAN decision.

Authorized action: ``stage128-m2-retained-block-human-decision`` (one action
only, consumed by recording and verifying this decision).

Records the human governance decision
``RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK`` from already-committed
evidence. It fits no model, produces no prediction, runs no resampling,
computes no p-value, performs no refit and reads no final-test predictor or
target value.

Usage::

    PYTHONPATH=project python \\
        project/run_stage128_m2_retained_block_human_decision.py --build
    PYTHONPATH=project python \\
        project/run_stage128_m2_retained_block_human_decision.py --check
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m2_retained_block_human_decision as d  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true",
                    help="build and write the retained-block decision package")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and verify the on-disk package")
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args()
    if not (args.build or args.check):
        ap.error("one of --build or --check is required")

    built = d.build_package(args.root, write=bool(args.build))
    qc = built["qc_report"]

    if args.check:
        import json
        from pathlib import Path

        root = Path(args.root)
        expected = {
            d.README_REL: built["readme_text"],
            d.AUTHORIZATION_REL: json.dumps(
                built["authorization_record"], ensure_ascii=False, indent=2,
                sort_keys=True) + "\n",
            d.DECISION_REL: json.dumps(
                built["decision"], ensure_ascii=False, indent=2,
                sort_keys=True) + "\n",
            d.METADATA_REL: json.dumps(
                built["metadata"], ensure_ascii=False, indent=2,
                sort_keys=True) + "\n",
            d.QC_REL: json.dumps(
                qc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        }
        drift = [
            rel for rel, text in expected.items()
            if not (root / rel).is_file()
            or (root / rel).read_text(encoding="utf-8") != text
        ]
        if drift:
            print(f"DRIFT: on-disk package differs from a fresh build: {drift}")
            return 1

    print(f"action: {d.ACTION_ID}")
    print(f"decision_outcome: {d.DECISION_OUTCOME}")
    print(f"assertions: {qc['assertion_count']} failed: {qc['failed_count']}")
    print(f"all_pass: {qc['all_pass']}")
    return 0 if qc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
