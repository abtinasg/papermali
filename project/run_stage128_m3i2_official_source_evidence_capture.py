#!/usr/bin/env python3
"""Runner — Stage128 M3I-2 official-source evidence capture.

Three strictly separated modes:

``--capture``               the ONE authorized network session. Delegates every
                            socket to ``stage128_m3i2_capture_layer``.
``--build-from-bundle DIR`` offline rebuild of every artifact from retained raw
                            bytes.
``--check``                 offline verification of the committed package. No
                            network, no writes.

Only ``--capture`` may touch the network, and it is the only path that imports
the capture layer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage128_m3i2_official_source_evidence_capture as m  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _required_edition_targets(out: Path) -> list[dict]:
    """Derive the required-edition download targets from RETAINED bytes.

    Discovery must already have happened: the edition URLs exist only inside
    the official listing, so they cannot be known before it is captured. This
    reads the retained listing bytes offline and selects only the editions the
    development cutoffs actually require.
    """
    import csv as _csv

    manifest = out / "official_response_manifest.csv"
    if not manifest.is_file():
        return []
    with manifest.open(encoding="utf-8", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    listing = next((r for r in rows
                    if r.get("object_id") == "wb_wdi_archive_listing"
                    and r.get("capture_result") == "SUCCESS"), None)
    if not listing:
        return []
    blob = out / "raw" / listing["raw_body_filename"]
    if not blob.is_file():
        return []

    editions = m.parse_wdi_archive_listing(
        blob.read_text(encoding="utf-8", errors="replace"),
        listing["request_url"], listing["sha256"],
        listing.get("retrieval_timestamp_utc", ""))
    plan = m.build_unique_cutoff_plan(ROOT)
    _, required = m.plan_required_editions(plan, editions)
    already = {r["object_id"] for r in rows
               if r.get("capture_result") == "SUCCESS"}
    targets = m.required_edition_download_targets(required, editions)
    return [t for t in targets if t["object_id"] not in already]


def _capture(output_dir: str, complete: bool = False) -> int:
    """Run the authorized capture session.

    Two phases, because the second depends on the first: the official listing
    must be captured before the edition URLs inside it can be known. With
    ``complete=True`` the phase-2 downloads are appended to the SAME capture
    directory and the same manifests; nothing from phase 1 is deleted or
    rewritten.
    """
    # Imported HERE so that --check and --build-from-bundle never even load a
    # module that can open a socket.
    from src import stage128_m3i2_capture_layer as capture_layer

    m.verify_human_authorization()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if complete:
        targets = _required_edition_targets(out)
        if not targets:
            print("no outstanding required-edition downloads", file=sys.stderr)
            return 0
        print(f"completing capture session -> {out}")
        print(f"required editions outstanding: {len(targets)}")
        session = capture_layer.capture_objects(targets, out, append=True)
    else:
        print(f"capture session -> {out}")
        print(f"targets: {len(m.DISCOVERY_TARGETS)} official discovery objects")
        session = capture_layer.capture_objects(
            [dict(t) for t in m.DISCOVERY_TARGETS], out)

    print(json.dumps({
        "session_closed": session["session_closed"],
        "targets_requested": session["targets_requested"],
        "responses_recorded": session["responses_recorded"],
        "objects_succeeded": session["objects_succeeded"],
        "objects_failed": session["objects_failed"],
        "raw_bytes_retained": session["raw_bytes_retained"],
    }, ensure_ascii=False, indent=2))

    if not session["session_closed"]:
        print("STOP_CAPTURE_SESSION_NOT_CLOSED", file=sys.stderr)
        return 2
    return 0


def _summarize(built: dict) -> None:
    decision = built["decision"]
    qc = built["qc_report"]
    summary = built["evidence_summary"]
    print(f"action: {m.ACTION_ID}")
    print(f"baseline: {m.BASELINE_BRANCH} @ {m.BASELINE_COMMIT}")
    print(f"evidence status: "
          f"{decision['m3i2_official_source_evidence_status']}")
    print(f"result code: {decision['result_code']}")
    print(f"financing decision: "
          f"{decision['m3i3_financing_metadata_decision']}")
    print(f"unique development cutoffs: "
          f"{summary['unique_development_cutoffs']} "
          f"(integrity count, not coverage)")
    print(f"official responses retained: "
          f"{summary['official_responses_retained']} "
          f"(successful {summary['official_responses_successful']})")
    print(f"raw bytes retained: {summary['raw_bytes_total']}")
    print(f"required editions: {summary['required_editions_total']} "
          f"captured {summary['required_editions_captured']}")
    print("company joins: {} | feature materializations: {} | coverage: {} | "
          "gate executions: {}".format(
              decision["company_macro_joins"],
              decision["feature_materializations"],
              decision["coverage_calculations"],
              decision["data_gate_executions"]))
    print("model fits: {} | predictions: {} | holm: {} | final-test rows: {}"
          .format(decision["model_fits"], decision["predictions"],
                  decision["holm_calculations"],
                  decision["final_test_rows_read"]))
    print(f"final_test_locked: {decision['final_test_locked']} | "
          f"merge_authorized: {decision['merge_authorized']}")
    print(f"next: {decision['next_research_action_id']} "
          f"(authorized={decision['next_research_action_authorized']})")
    print(f"assertions: {qc['assertion_count']} failed: {qc['failed_count']}")
    print(f"all_pass: {qc['all_pass']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", action="store_true",
                       help="run the one authorized network capture session")
    group.add_argument("--complete-capture", action="store_true",
                       help="finish the SAME session: download the required "
                            "editions discovered by phase 1")
    group.add_argument("--build-from-bundle", metavar="DIR",
                       help="offline rebuild from a retained capture directory")
    group.add_argument("--check", action="store_true",
                       help="offline verification of the committed package")
    parser.add_argument("--output-dir", help="capture output directory")
    parser.add_argument("--bundle-dir", help="external bundle directory")
    args = parser.parse_args(argv)

    if args.capture or args.complete_capture:
        if not args.output_dir:
            parser.error("capture modes require --output-dir")
        return _capture(args.output_dir, complete=args.complete_capture)

    built = m.build_package(
        ROOT, capture_dir=args.build_from_bundle,
        bundle_dir=args.bundle_dir,
        write=bool(args.build_from_bundle))
    _summarize(built)

    if not built["qc_report"]["all_pass"]:
        print(f"QC FAILED: {built['qc_report']['failed_assertions']}",
              file=sys.stderr)
        return 1

    if args.check:
        for rel, text in built["artifact_texts"].items():
            path = ROOT / rel
            if not path.is_file():
                print(f"missing committed artifact: {rel}", file=sys.stderr)
                return 1
            if path.read_text(encoding="utf-8") != text:
                print(f"committed artifact differs from a fresh offline "
                      f"rebuild: {rel}", file=sys.stderr)
                return 1
        print("Committed package verified (--check).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
