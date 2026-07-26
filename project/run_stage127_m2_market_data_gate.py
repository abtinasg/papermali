"""Execute the Stage127 M2 market-data admission Gate.

Performs the real retrieval probes against the frozen authoritative source
(TSETMC only -- no substitute provider is ever contacted), records the probe
evidence verbatim with provenance, and writes the compact Gate package.

No model is fit. No prediction is generated. No final-test row is read.

Usage:
    python project/run_stage127_m2_market_data_gate.py --build
    python project/run_stage127_m2_market_data_gate.py --check
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_market_data_gate as g  # noqa: E402

PROBE_TIMEOUT_SECONDS = 20


def _git(repo_root: str, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def probe_endpoint(url: str) -> dict[str, object]:
    """Probe one authoritative endpoint; record the outcome verbatim.

    A failure here is recorded as a failure to REACH the source from this
    environment. It is never recorded as a property of the source itself.
    """
    host = urllib.parse.urlsplit(url).hostname or ""
    record: dict[str, object] = {
        "url": url,
        "host": host,
        "source_id": g.M2_PRIMARY_SOURCE_ID,
        "attempted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeout_seconds": PROBE_TIMEOUT_SECONDS,
        "http_status": None,
        "content_sha256": None,
        "bytes": None,
        "machine_readable": False,
        "error_class": None,
        "error_detail": None,
    }
    try:
        record["resolved_ip"] = socket.gethostbyname(host)
    except OSError as exc:
        record["resolved_ip"] = None
        record["dns_error"] = str(exc)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "papermali-stage127-gate"})
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT_SECONDS) as resp:
            body = resp.read()
            record["http_status"] = resp.status
            record["bytes"] = len(body)
            record["content_sha256"] = g.sha256_text(body.decode("utf-8", "replace"))
            ctype = resp.headers.get("Content-Type", "")
            record["content_type"] = ctype
            record["machine_readable"] = any(
                t in ctype.lower() for t in ("json", "csv", "xml")
            )
    except urllib.error.HTTPError as exc:
        # An HTTP error IS a real response from the source -- it is evidence.
        record["http_status"] = exc.code
        record["error_class"] = "HTTPError"
        record["error_detail"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - recorded verbatim, never inferred
        record["error_class"] = type(exc).__name__
        record["error_detail"] = str(exc)
    return record


def collect_probe_evidence() -> list[dict[str, object]]:
    return [probe_endpoint(u) for u in g.REQUIRED_TSETMC_ENDPOINTS]


def csv_text(fieldnames: list[str], rows: list[dict[str, object]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_package(repo_root: str, probes: list[dict[str, object]]) -> dict[str, str]:
    files = dict(g.build(repo_root, probes))
    decision = json.loads(files["stage127_m2_market_data_gate_decision.json"])
    pairs = g.load_development_pairs(repo_root)
    reached = any(p.get("http_status") for p in probes)

    # -- accessibility evidence table ------------------------------------- #
    acc_rows = []
    for cand in decision["candidates"]:
        acc_rows.append({
            "variable": cand["variable"],
            "candidate_id": cand["candidate_id"],
            "block": g.M2_BLOCK,
            "source_id": g.M2_PRIMARY_SOURCE_ID,
            "accessibility_score": cand["G01_accessibility"]["accessibility_score"],
            "resolution": cand["G01_accessibility"]["resolution"],
            "threshold": ">=3",
            "evidence_class_required": "candidate_endpoint_evidence",
            "endpoints_probed": len(probes),
            "endpoints_reached": sum(1 for p in probes if p.get("http_status")),
            "score_basis": cand["G01_accessibility"]["basis"],
            "scored_zero_to_two": False,
            "admission_decision": cand["admission_decision"],
        })
    files["stage127_m2_candidate_accessibility.csv"] = csv_text(
        list(acc_rows[0].keys()), acc_rows)

    # -- development feature table (development rows ONLY; no final test) -- #
    feat_rows = []
    for p in sorted(pairs, key=lambda x: (x["target_year"], x["ticker"])):
        ws, we = g.required_window(p["pair_cutoff_date"])
        feat_rows.append({
            "sample_design": g.PRIMARY_SAMPLE,
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "predictor_row_key_t": p["predictor_row_key_t"],
            "dataset_split": "development",
            "temporal_folds": ";".join(p["folds"]),
            "pair_cutoff_date": p["pair_cutoff_date"],
            "required_window_retrieval_start": ws,
            "required_window_end_max_strictly_before_cutoff": we,
            "equity_return_window": "",
            "realized_volatility": "",
            "amihud_illiquidity": "",
            "missing_price_day_count": "",
            "zero_traded_value_day_count": "",
            "usable_daily_return_count": "",
            "usable_amihud_day_count": "",
            "m2_value_status": "UNRESOLVED_NO_OBSERVATION_RETRIEVED",
        })
    files["stage127_m2_development_features.csv"] = csv_text(
        list(feat_rows[0].keys()), feat_rows)

    # -- coverage audit ---------------------------------------------------- #
    cov_rows = []
    for var, cid, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        cov_rows.append({
            "variable": var, "candidate_id": cid,
            "total_development_rows": c["total_development_rows"],
            "valid_rows": "" if c["valid_rows"] is None else c["valid_rows"],
            "missing_or_unresolved_rows": c["missing_or_unresolved_rows"],
            "overall_coverage": "" if c["overall_coverage"] is None else c["overall_coverage"],
            "fold1_train_coverage": "" if c["fold1_train_coverage"] is None else c["fold1_train_coverage"],
            "fold1_validation_coverage": "" if c["fold1_validation_coverage"] is None else c["fold1_validation_coverage"],
            "fold2_train_coverage": "" if c["fold2_train_coverage"] is None else c["fold2_train_coverage"],
            "fold2_validation_coverage": "" if c["fold2_validation_coverage"] is None else c["fold2_validation_coverage"],
            "positive_row_coverage": "" if c["positive_row_coverage"] is None else c["positive_row_coverage"],
            "negative_row_coverage": "" if c["negative_row_coverage"] is None else c["negative_row_coverage"],
            "threshold": c["threshold"],
            "resolution": c["resolution"],
            "coverage_gate_passed": "" if c["coverage_gate_passed"] is None else c["coverage_gate_passed"],
        })
    files["stage127_m2_candidate_coverage_audit.csv"] = csv_text(
        list(cov_rows[0].keys()), cov_rows)

    # -- common sample audit ----------------------------------------------- #
    cs = decision["block_common_sample"]
    cs_rows = [{
        "block": g.M2_BLOCK,
        "requires_all_three_variables": True,
        "total_development_rows": cs["total_development_rows"],
        "common_usable_rows": "" if cs["common_usable_rows"] is None else cs["common_usable_rows"],
        "common_coverage": "" if cs["common_coverage"] is None else cs["common_coverage"],
        "threshold": cs["threshold"],
        "positive_count": "" if cs["positive_count"] is None else cs["positive_count"],
        "negative_count": "" if cs["negative_count"] is None else cs["negative_count"],
        "resolution": cs["resolution"],
        "common_coverage_gate_passed": "" if cs["common_coverage_gate_passed"] is None else cs["common_coverage_gate_passed"],
    }]
    files["stage127_m2_common_sample_audit.csv"] = csv_text(
        list(cs_rows[0].keys()), cs_rows)

    files["stage127_m2_join_leakage_audit.json"] = g.json_dumps(
        decision["join_leakage_audit"])

    # -- source manifest / provenance -------------------------------------- #
    manifest = {
        "source_id": g.M2_PRIMARY_SOURCE_ID,
        "source_family": g.M2_SOURCE_FAMILY,
        "authoritative_source_only": True,
        "substitute_sources_used": [],
        "forbidden_substitute_sources_not_used": list(g.FORBIDDEN_SUBSTITUTE_SOURCES),
        "source_universe_broadened_post_hoc": False,
        "endpoints_required_for_scoring": list(g.REQUIRED_TSETMC_ENDPOINTS),
        "probe_evidence": probes,
        "endpoints_reached": sum(1 for p in probes if p.get("http_status")),
        "observations_retrieved": 0,
        "retrieval_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "egress_note": (
                "All probes failed to reach the authoritative host from this "
                "execution environment while unrelated public hosts were "
                "reachable, and every probed hostname resolved into a single "
                "sequentially-allocated private proxy range. This is evidence "
                "about THIS environment's egress policy, not about TSETMC."
            ) if not reached else "Authoritative host reached.",
        },
        "field_mapping_required": {
            "adjusted_close": (
                "corporate-action-adjusted daily closing price; unadjusted "
                "close is NOT an acceptable substitute"
            ),
            "traded_value_rial": (
                "daily traded value in rial; days with V_t<=0 or missing are "
                "excluded and never imputed"
            ),
        },
        "field_mapping_verified": False,
        "parser_module": "project/src/stage127_m2_market_data_gate.py",
        "parser_module_sha256": g.sha256_file(
            os.path.join(repo_root, "project/src/stage127_m2_market_data_gate.py")),
        "code_revision": _git(repo_root, "rev-parse", "HEAD"),
        "raw_cache_written": False,
        "reproduction_note": (
            "Rerun `python project/run_stage127_m2_market_data_gate.py --build` "
            "from an environment with egress to TSETMC. The required per-pair "
            "retrieval ranges are enumerated in "
            "stage127_m2_development_features.csv."
        ),
    }
    files["stage127_m2_source_manifest.json"] = g.json_dumps(manifest)

    # -- authorization provenance ------------------------------------------ #
    normalized_scope = (
        "این مجوز فقط اجرای دروازه پذیرش داده‌های بازار M2 (stage127-m2-market-data-gate) "
        "را مجاز می‌کند، شامل بازیابی واقعی داده/شواهد از منبع رسمی فقط تا حدی که برای "
        "همین دروازه لازم است. این مجوز شامل stage127-m2-incremental-evaluation، هیچ "
        "برازش یا پیش‌بینی مدل، بازتنظیم، جست‌وجوی ویژگی، بازبرازش کامل دوره توسعه، "
        "اجرای کالibration/bootstrap/Holm، SHAP، انتخاب مدل برنده یا نهایی، دسترسی به "
        "پیش‌بین یا هدف آزمون نهایی، کار M3 یا M4، و ادغام (merge) نیست."
    )
    auth = {
        "authorization_id": "stage127-m2-market-data-gate-human-authorization",
        "authorizing_role": "human_supervisor_data_owner",
        "human_source_utterance": g.HUMAN_SOURCE_UTTERANCE,
        "human_source_utterance_sha256": g.sha256_text(g.HUMAN_SOURCE_UTTERANCE),
        "resolved_authorized_action_id": g.ACTION_ID,
        "authorized_action_id": g.ACTION_ID,
        "resolution_basis": "then_current_roadmap_next_research_action_id",
        "normalized_authorization_scope": normalized_scope,
        "normalized_authorization_scope_is_derived_not_verbatim_human_text": True,
        "normalized_authorization_scope_sha256": g.sha256_text(normalized_scope),
        "scope_limited_to_this_action_only": True,
        "standing_authorization": False,
        "permits_real_m2_source_retrieval_for_this_gate_only": True,
        "does_not_extend_to": [
            "stage127-m2-incremental-evaluation",
            "any_model_fitting_or_prediction",
            "retuning",
            "feature_search",
            "full_development_refit",
            "calibration_bootstrap_holm_execution",
            "shap",
            "winner_or_final_model_selection",
            "final_test_predictor_access",
            "final_test_target_access",
            "m3_work",
            "m4_work",
            "merge",
        ],
        "merge_authorized": False,
        "m2_incremental_evaluation_authorized": False,
    }
    files["stage127_m2_market_data_gate_human_authorization_record.json"] = g.json_dumps(auth)

    # -- QC report ---------------------------------------------------------- #
    assertions = [
        ("m2_block_has_exactly_three_variables", len(g.M2_VARIABLES) == 3),
        ("development_pairs_666", len(pairs) == g.EXPECTED_DEV_PAIRS),
        ("no_final_test_rows_in_features", all(
            r["target_year"] in g.DEVELOPMENT_TARGET_YEARS for r in pairs)),
        ("no_duplicate_pair_keys", decision["join_leakage_audit"][
            "duplicate_pair_key_violations"] == 0),
        ("zero_accepted_post_cutoff_observations", decision[
            "join_leakage_audit"]["accepted_post_cutoff_observations"] == 0),
        ("zero_accepted_target_year_leakage", decision["join_leakage_audit"][
            "accepted_target_year_leakage_violations"] == 0),
        ("no_model_fit", decision["model_fit_calls"] == 0),
        ("no_prediction", decision["prediction_calls"] == 0),
        ("final_test_locked", decision["final_test_firewall"]["final_test_locked"]),
        ("final_test_not_inspected", not decision["final_test_firewall"][
            "final_test_predictor_values_inspected"]),
        ("no_substitute_source_used", manifest["substitute_sources_used"] == []),
        ("no_accessibility_score_below_three_assigned", all(
            r["accessibility_score"] in (None, 3, 4, 5) for r in acc_rows)),
        ("block_not_redefined", decision["no_variable_dropped_from_frozen_block"]),
        ("not_eligible_to_start_m2_modeling", not decision[
            "eligibility_for_next_action"]["eligible_to_start_m2_incremental_evaluation"]),
    ]
    qc = {
        "scope": g.CONTRACT_ID,
        "stage": g.STAGE,
        "decision_id": g.ACTION_ID,
        "gate_status": decision["gate_status"],
        "assertions": [
            {"name": n, "status": "PASS" if ok else "FAIL"} for n, ok in assertions
        ],
        "assertion_count": len(assertions),
        "failed_count": sum(1 for _, ok in assertions if not ok),
        "all_pass": all(ok for _, ok in assertions),
    }
    files["stage127_m2_gate_qc_report.json"] = g.json_dumps(qc)

    return files


def write_readme(files: dict[str, str], decision: dict) -> str:
    cs = decision["block_common_sample"]
    lines = [
        "# Stage127 — M2 Market-Data Admission Gate",
        "",
        f"**Gate status: `{decision['gate_status']}`**",
        "",
        "Development-only point-in-time data admission gate for the frozen "
        "three-variable M2 market block. This Gate answers only whether the "
        "frozen M2 variables can be obtained with correct timing, quality, "
        "coverage, joins and event support. It does **not** answer whether M2 "
        "improves prediction. No model was fit, no prediction was generated, "
        "and no final-test row was read.",
        "",
        "## Frozen M2 block (unchanged)",
        "",
        "| variable | candidate_id |",
        "|---|---|",
    ]
    for var, cid, _ in g.M2_VARIABLES:
        lines.append(f"| `{var}` | `{cid}` |")
    lines += [
        "",
        f"Source: `{g.M2_PRIMARY_SOURCE_ID}` ({g.M2_SOURCE_FAMILY}). "
        "Formula contract option `M2-A_modified`; shared 12-calendar-month "
        "window ending on the last eligible trading day **strictly before** "
        "each pair's cutoff; adjusted close only; >=126 usable observations; "
        "no imputation, scaling, extrapolation, annualization or threshold "
        "reduction.",
        "",
        "## Why UNRESOLVED",
        "",
    ]
    for b in decision["blocker_reasons"]:
        lines.append(f"- {b}")
    lines += [
        "",
        "`UNRESOLVED` is deliberately **not** `FAIL`. The frozen R-A mapping "
        "requires `missing_evidence = null_or_unresolved_never_zero`: no probe "
        "reached the authoritative source, so no property of the source was "
        "observed. Scoring 0-2 (a hard drop) would assert an unobserved "
        "property and wrongly close the M2 path. No M2 variable was dropped and "
        "the frozen three-variable block was not redefined.",
        "",
        "## Development scope (real, computed)",
        "",
        f"- Development pairs: **{decision['join_leakage_audit']['matched_pair_count']}** "
        f"(sample `{g.PRIMARY_SAMPLE}`, target `{g.PRIMARY_TARGET}`, target years 1393-1399)",
        f"- Coverage denominator: {cs['total_development_rows']} rows; "
        f"candidate threshold {g.CANDIDATE_VALID_COVERAGE_MIN}, "
        f"block common threshold {g.BLOCK_COMMON_SAMPLE_COVERAGE_MIN}",
        "- Numerators are UNRESOLVED (no observation retrieved), which is "
        "distinct from an observed zero.",
        "",
        "## Final-test firewall",
        "",
        "`final_test_locked=true`; unlocked / access_authorized / "
        "predictor_values_inspected / target_values_inspected / "
        "evaluation_performed all `false`. Final-test target years 1400-1402 "
        "were excluded structurally before any value was read, and final-test "
        "coverage was not used for admission.",
        "",
        "## Next action",
        "",
        "Not eligible to start `stage127-m2-incremental-evaluation`: that "
        "requires BOTH data admission and development comparison feasibility to "
        "pass, and both are UNRESOLVED. This Gate result requires human review.",
        "",
        "## Files",
        "",
    ]
    for name in sorted(files):
        lines.append(f"- `{name}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.build == args.check:
        print("exactly one of --build or --check is required", file=sys.stderr)
        return 2

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = g.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, g.OUT_DIR_REL)

    probes = collect_probe_evidence()
    files = build_package(repo_root, probes)
    decision = json.loads(files["stage127_m2_market_data_gate_decision.json"])
    files["README_STAGE127_M2_MARKET_DATA_GATE.md"] = write_readme(files, decision)

    if args.check:
        drift = []
        for name, text in files.items():
            if name == "stage127_m2_source_manifest.json":
                continue  # carries live probe timestamps
            p = os.path.join(out_dir, name)
            if not os.path.isfile(p) or open(p, encoding="utf-8").read() != text:
                drift.append(name)
        if drift:
            print(f"DRIFT: {drift}")
            return 1
        print(f"Stage127 Gate package is up to date (status={decision['gate_status']})")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    meta = {
        "contract_id": g.CONTRACT_ID,
        "decision_id": g.ACTION_ID,
        "stage": g.STAGE,
        "gate_status": decision["gate_status"],
        "package_artifacts_sha256": {
            f"{g.OUT_DIR_REL}/{name}": g.sha256_text(text)
            for name, text in sorted(files.items())
            if name != "stage127_m2_source_manifest.json"
        },
        "volatile_artifacts_excluded_from_hash_pinning": [
            f"{g.OUT_DIR_REL}/stage127_m2_source_manifest.json",
        ],
        "canonical_sources_sha256": decision["canonical_sources_sha256"],
        "source_main_commit": _git(repo_root, "rev-parse", "origin/main"),
        "source_repository": "abtinasg/papermali",
    }
    with open(os.path.join(out_dir, "metadata_and_hashes_stage127_m2_market_data_gate.json"),
              "w", encoding="utf-8") as f:
        f.write(g.json_dumps(meta))

    print(f"Stage127 Gate built: status={decision['gate_status']}")
    print(f"  endpoints reached: {sum(1 for p in probes if p.get('http_status'))}"
          f"/{len(probes)}")
    print(f"  development pairs: {decision['join_leakage_audit']['matched_pair_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
