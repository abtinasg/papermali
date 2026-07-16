#!/usr/bin/env python3
"""Runner for Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot.

Usage:
    python project/run_stage125_part3b.py --plan [--write]
    python project/run_stage125_part3b.py --capture
    python project/run_stage125_part3b.py --write
    python project/run_stage125_part3b.py --check

``--capture`` is the only mode that may perform approved read-only network
retrieval. ``--check`` and ``--plan`` (without capture) never access the network.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b_evidence_capture as part3b  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default project/stage125)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true",
                      help="build capture plan + endpoint registry (no network)")
    mode.add_argument("--capture", action="store_true",
                      help="approved read-only retrieval into immutable cache")
    mode.add_argument("--write", action="store_true",
                      help="derive scores/gates/QC from cached evidence (no network)")
    mode.add_argument("--check", action="store_true",
                      help="offline validation of frozen Part 3B outputs")
    parser.add_argument(
        "--persist-plan", action="store_true",
        help="with --plan, write authorization/plan/registry to disk",
    )
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot")
    print("=" * 70)

    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        if args.plan:
            result = part3b.run(
                project_dir=ROOT, output_dir=output_dir,
                mode="plan", write=args.persist_plan or False,
            )
            # Convenience: --plan --write means persist plan
        elif args.capture:
            result = part3b.run(
                project_dir=ROOT, output_dir=output_dir, mode="capture",
            )
        elif args.write:
            result = part3b.run(
                project_dir=ROOT, output_dir=output_dir, mode="write",
            )
        else:
            result = part3b.run(
                project_dir=ROOT, output_dir=output_dir, mode="check",
            )
    except part3b.QCFail as exc:
        print(f"FAIL (fail-closed): {exc}", file=sys.stderr)
        return 1
    except part3b.NetworkPolicyError as exc:
        print(f"NETWORK POLICY FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"Mode: {result.get('mode')}")
    print(f"Output dir: {result.get('output_dir')}")
    if result.get("mode") == "plan":
        print(f"Planned requests: {result.get('planned_requests')}")
        print(f"Blocked requests: {result.get('blocked_requests')}")
        print(f"Plan sha256: {result.get('plan_hash')}")
    if result.get("mode") == "capture":
        stats = result.get("network_stats") or {}
        print(f"network_calls_attempted={stats.get('network_calls_attempted')}")
        print(f"network_calls_succeeded={stats.get('network_calls_succeeded')}")
        print(f"network_calls_failed={stats.get('network_calls_failed')}")
        print(f"bytes_retrieved={stats.get('bytes_retrieved')}")
        print(f"network_extraction_performed={result.get('network_extraction_performed')}")
        print(f"endpoints_contacted={result.get('endpoints_contacted')}")
    if result.get("mode") == "write":
        gs = result.get("gate_summary") or {}
        print(f"assessments={gs.get('assessment_count')}")
        print(f"G09–G14: G09={gs.get('G09')} G10={gs.get('G10')} "
              f"G11={gs.get('G11')} G12={gs.get('G12')} "
              f"G13={gs.get('G13')} G14={gs.get('G14')}")
    if result.get("mode") == "check":
        print("Offline --check OK (byte-stable).")
    print("modeling_started=false | no Stage126 admission")
    return 0


if __name__ == "__main__":
    # Support: python project/run_stage125_part3b.py --plan --write
    argv = sys.argv[1:]
    if "--plan" in argv and "--write" in argv:
        argv = [a for a in argv if a != "--write"] + ["--persist-plan"]
    raise SystemExit(main(argv))
