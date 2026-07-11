#!/usr/bin/env python3
"""Runner for Stage124 Gate B Readiness dry-run.

Usage:
    python project/run_stage124_gate_b_readiness.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage124_gate_b_readiness as gate_b  # noqa: E402


def main() -> int:
    project_dir = ROOT
    print("=" * 70)
    print("Stage124 Gate B Readiness — Dry-Run Eligibility Rule Comparison")
    print("=" * 70)
    print()

    try:
        result = gate_b.run(project_dir)
    except gate_b.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1

    print(f"Output directory: {result['output_dir']}")
    print(f"Files created: {len(result['files_created'])}")
    for f in result["files_created"]:
        print(f"  - {f}")
    print()

    print("Hash verification:", "✅ all match" if result["hash_report"]["authoritative_csv_all_match"] else "❌ mismatch")
    print(f"Schema validation: {'✅ PASS' if result['schema_report']['overall_pass'] else '❌ FAIL'}")
    print()

    print("Rule comparison summary:")
    print(f"  {'Rule':<25} {'Pairs':>8} {'Pos':>6} {'Neg':>6}")
    print(f"  {'─' * 25} {'─' * 8} {'─' * 6} {'─' * 6}")
    for rule in ["rule_a", "rule_b", "rule_c"]:
        r = result["impact_summary"][rule]
        print(f"  {rule:<25} {r['eligible_pairs']:>8} {r['positive']:>6} {r['negative']:>6}")
    bl = result["impact_summary"]["stage123_baseline"]
    print(f"  {'stage123_baseline':<25} {bl['eligible_pairs']:>8} {bl['positive']:>6} {bl['negative']:>6}")
    print()

    print(f"QC all pass: {result['qc_all_pass']}")
    print()
    print("⚠️  No rule has been finalized.")
    print("   Next action: stage124-gate-b-rule-approval")
    print("   User and scientific reviewer must approve the final rule.")
    return 0 if result["qc_all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
