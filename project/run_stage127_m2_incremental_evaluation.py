#!/usr/bin/env python3
"""Runner — Stage127 M2 paired incremental evaluation (development-only).

Usage::

    PYTHONPATH=project python project/run_stage127_m2_incremental_evaluation.py --build
    PYTHONPATH=project python project/run_stage127_m2_incremental_evaluation.py --check
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_incremental_evaluation as ev  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.build == args.check:
        print("exactly one of --build or --check is required", file=sys.stderr)
        return 2

    project_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    result = ev.run(project_dir=project_dir, build=args.build,
                    check=args.check)

    decision = result["decision"]
    qc = result["qc"]
    print("=" * 70)
    print("Stage127 — M2 vs M1 paired incremental evaluation "
          "(development-only)")
    print("=" * 70)
    print(f"Action: {ev.ACTION_ID} (one authorized execution, consumed)")
    print(f"Mode: {result['mode']}")
    print(f"Common sample: {decision['common_sample_rows']} rows — "
          f"pooled OOF: {decision['pooled_oof_rows']}")
    print(f"Primary predictive model fits: "
          f"{decision['primary_predictive_model_fits']}")
    for family, e in decision["per_family_primary_metric"].items():
        print(f"  {family}: M1 PR-AUC {e['m1_pr_auc']} | M2 {e['m2_pr_auc']} "
              f"| delta {e['m2_minus_m1_pr_auc']} "
              f"| 95% CI [{e['ci_lower']}, {e['ci_upper']}] "
              f"| {e['observed_direction']}")
    print(f"QC: {qc['assertion_count']} assertions, {qc['failed_count']} "
          f"failed, all_pass={qc['all_pass']}")
    print("Winner selected: NO — retained-block decision requires a separate "
          "human authorization.")
    print("Final-test access: 0 — M3/M4 not started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
