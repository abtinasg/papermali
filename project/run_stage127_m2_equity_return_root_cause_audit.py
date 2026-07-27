"""Run the Stage127 equity_return_window root-cause audit.

DIAGNOSTIC ONLY. Produces:
  project/stage127/stage127_m2_equity_return_root_cause_audit.csv
  project/stage127/stage127_m2_equity_return_tN_detail.csv
  project/stage127/stage127_m2_equity_return_t0_detail.csv
  project/stage127/stage127_m2_equity_return_low_return_detail.csv
  project/stage127/stage127_m2_low_return_semantics_upper_bound_audit.csv
  project/stage127/stage127_m2_equity_return_root_cause_summary.json

Never modifies the canonical Gate decision or any frozen artifact.

Usage:
    python project/run_stage127_m2_equity_return_root_cause_audit.py --bundle PATH
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_equity_return_root_cause_audit as rca  # noqa: E402
from src import stage127_m2_market_data_gate as gate  # noqa: E402


def csv_text(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    args = ap.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = gate.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, gate.OUT_DIR_REL)

    result = rca.run(repo_root, args.bundle)

    files = {
        "stage127_m2_equity_return_root_cause_audit.csv": csv_text(
            result["main_rows"]),
        "stage127_m2_equity_return_tN_detail.csv": csv_text(result["tN_rows"]),
        "stage127_m2_equity_return_t0_detail.csv": csv_text(result["t0_rows"]),
        "stage127_m2_equity_return_low_return_detail.csv": csv_text(
            result["low_return_rows"]) if result["low_return_rows"] else "",
        "stage127_m2_low_return_semantics_upper_bound_audit.csv": csv_text(
            result["upper_bound_rows"]) if result["upper_bound_rows"] else "",
        "stage127_m2_equity_return_root_cause_summary.json": gate.json_dumps(
            result["summary"]),
    }

    os.makedirs(out_dir, exist_ok=True)
    for name, text in files.items():
        if not text:
            continue
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    s = result["summary"]
    print("Root-cause audit complete (DIAGNOSTIC ONLY).")
    print(f"  equity_return unavailable: {s['equity_return_unavailable_current']}")
    print(f"  root causes: {s['root_cause_counts']}")
    print(f"  recoverable (proven defect): {s['recoverable_due_to_proven_data_capture_defect']}")
    print(f"  nonrecoverable (frozen contract): {s['nonrecoverable_under_current_frozen_contract']}")
    print(f"  unresolved: {s['unresolved_root_cause_count']}")
    print(f"  DIAGNOSTIC counterfactual coverage: "
          f"{s['diagnostic_counterfactual_not_canonical_result']['counterfactual_equity_return_coverage']}")
    print(f"  crosses 0.80 threshold: "
          f"{s['diagnostic_counterfactual_not_canonical_result']['crosses_0_80_candidate_threshold']}")
    print("  Canonical Gate status UNCHANGED: FAIL_M2_DATA_GATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
