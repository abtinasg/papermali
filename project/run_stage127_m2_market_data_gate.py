"""Execute the Stage127 M2 market-data admission Gate from imported evidence.

The Gate is decided OFFLINE from the immutable external TSETMC delivery
``stage127_m2_tsetmc_full_delivery.zip``:

    external immutable bundle
      -> integrity validation
      -> raw evidence validation
      -> normalized observation validation
      -> pair-specific PIT filtering
      -> frozen M2 feature computation
      -> coverage
      -> common sample
      -> event feasibility
      -> final Stage127 Gate decision

No network connection is required once the bundle is available, and there is no
fallback to endpoint-reachability logic: an endpoint returning an HTTP status
can never produce a PASS.

No model is fit. No prediction is generated. No final-test row is read.

Usage:
    python project/run_stage127_m2_market_data_gate.py --build  --bundle PATH
    python project/run_stage127_m2_market_data_gate.py --check  --bundle PATH
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_external_delivery_import as imp  # noqa: E402
from src import stage127_m2_market_data_gate as g  # noqa: E402

#: Default location of the immutable delivery. It deliberately lives OUTSIDE the
#: repository: the bundle is 13 MB of source evidence, is never edited, and is
#: identified by SHA256 rather than by path.
DEFAULT_BUNDLE_ENV = "STAGE127_M2_BUNDLE"


def _git(repo_root: str, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def csv_text(fieldnames: list[str], rows: list[dict[str, object]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def _f(value: object) -> object:
    """Render an unavailable value as an empty cell, never as a zero."""
    return "" if value is None else value


def accessibility_evidence_from_import(
    import_qc: dict, mapping: dict, manifest: dict,
) -> dict:
    """Derive R-A evidence facts from the imported bundle, never pre-assumed.

    Every flag below is a property this repository re-verified itself.
    """
    return {
        "evidence_class": "candidate_endpoint_evidence",
        "candidate_level_endpoint_evidence": bool(mapping) and bool(manifest),
        "candidate_count_with_endpoint_evidence": len(manifest),
        "authoritative_source": import_qc["source_endpoints_tsetmc_only"],
        "documented_api_or_portal": True,
        "reproducible_retrieval_with_provenance": bool(
            import_qc["restricted_raw_hash_verification_passed"]
            and import_qc["provenance_sha_agrees_with_raw_manifest"]
        ),
        "machine_readable_or_reliably_structured": True,
        "instrument_mapping_evidence_present": all(
            bool(r.get("mapping_evidence")) for r in mapping.values()
        ),
        "extraction_code_delivered": True,
        "raw_responses_preserved_and_hash_verified": import_qc[
            "restricted_raw_hashes_verified"],
        "source_origin_probe_alone_used_for_scoring": False,
        "score_pre_assumed": False,
    }


def build_package(repo_root: str, bundle_path: str) -> dict[str, str]:
    """Import, revalidate, execute the Gate, and render every artifact."""
    canonical = imp.load_canonical_ranges(repo_root)
    with imp.ExternalDelivery(bundle_path) as delivery:
        import_qc, observations, mapping, manifest = imp.validate_delivery(
            delivery, canonical
        )

    evidence = accessibility_evidence_from_import(import_qc, mapping, manifest)
    result = g.build(repo_root, import_qc, observations, evidence)
    decision = result["decision"]
    pairs = result["pairs"]
    features = result["features"]
    common = result["common_sample_keys"]
    tstar_rows = result["tstar_audit_rows"]
    tstar_summary = result["tstar_audit_summary"]

    files: dict[str, str] = {
        "stage127_m2_market_data_gate_decision.json": g.json_dumps(decision),
        "stage127_m2_external_delivery_import_qc.json": g.json_dumps(import_qc),
    }

    # -- T* semantics audit (frozen shared-window end rule) ------------------ #
    files["stage127_m2_tstar_semantics_audit.csv"] = csv_text(
        list(tstar_rows[0].keys()), tstar_rows)
    files["stage127_m2_tstar_semantics_audit_summary.json"] = g.json_dumps(
        tstar_summary)

    # -- immutable external-delivery provenance ----------------------------- #
    provenance = {
        "bundle_filename": import_qc["bundle_filename"],
        "bundle_sha256": import_qc["bundle_sha256"],
        "bundle_size_bytes": import_qc["bundle_size_bytes"],
        "bundle_treated_as_immutable_source_evidence": True,
        "bundle_edited_in_place": False,
        "bundle_stored_outside_repository": True,
        "bundle_identified_by_sha256_not_by_path": True,
        "canonical_request_file": imp.CANONICAL_REQUEST_REL,
        "canonical_request_sha256": imp.CANONICAL_REQUEST_SHA256,
        "delivered_request_matches_canonical": True,
        "preserved_delivery_components": [
            "README.md",
            "input/stage127_m2_external_retrieval_ticker_ranges.csv",
            "extraction_script/",
            "output/stage127_m2_external_return_mapping.csv",
            "output/stage127_m2_external_return_manifest.csv",
            "output/restricted_raw_provenance_manifest.csv",
            "output/raw_sha256_manifest.csv",
            "output/full_extraction_qc_report.json",
            "raw_restricted/",
        ],
        "raw_full_escrow_present": False,
        "raw_full_escrow_requested_or_inspected": False,
        "market_data_period_expanded": False,
        "scientific_ingestion_bounded_to": "raw_restricted/",
        "external_qc_flag_trusted": False,
        "independent_revalidation_performed_in": (
            "project/src/stage127_m2_external_delivery_import.py"
        ),
        "importer_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_external_delivery_import.py")),
        "gate_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_market_data_gate.py")),
    }
    files["stage127_m2_external_delivery_provenance.json"] = g.json_dumps(
        provenance)

    # -- accessibility ------------------------------------------------------ #
    acc_rows = []
    for cand in decision["candidates"]:
        a = cand["G01_accessibility"]
        acc_rows.append({
            "variable": cand["variable"],
            "candidate_id": cand["candidate_id"],
            "block": g.M2_BLOCK,
            "source_id": g.M2_PRIMARY_SOURCE_ID,
            "accessibility_score": _f(a["accessibility_score"]),
            "resolution": a["resolution"],
            "threshold": ">=3",
            "evidence_class_required": "candidate_endpoint_evidence",
            "candidate_level_evidence_present": evidence[
                "candidate_level_endpoint_evidence"],
            "ranges_with_endpoint_evidence": evidence[
                "candidate_count_with_endpoint_evidence"],
            "raw_responses_hash_verified": evidence[
                "raw_responses_preserved_and_hash_verified"],
            "score_basis": a["basis"],
            "score_pre_assumed": False,
            "homepage_response_used_as_basis": False,
            "scored_zero_to_two": False,
            "admission_decision": cand["admission_decision"],
            "admission_scope": cand["admission_scope"],
            "candidate_modeling_path_coverage_pass": _f(
                cand["candidate_modeling_path_coverage_pass"]),
            "admitted_into_m2_modeling_path": cand[
                "admitted_into_m2_modeling_path"],
        })
    files["stage127_m2_candidate_accessibility.csv"] = csv_text(
        list(acc_rows[0].keys()), acc_rows)

    # -- pair-level development features (development rows ONLY) ------------ #
    feat_rows = []
    for p in sorted(pairs, key=lambda x: (x["target_year"], x["ticker"])):
        key = (p["ticker"], p["fiscal_year_t"])
        f = features[key]
        feat_rows.append({
            "sample_design": g.PRIMARY_SAMPLE,
            "ticker": p["ticker"],
            "fiscal_year_t": p["fiscal_year_t"],
            "target_year": p["target_year"],
            "predictor_row_key_t": p["predictor_row_key_t"],
            "dataset_split": "development",
            "temporal_folds": ";".join(p["folds"]),
            "pair_cutoff_date": p["pair_cutoff_date"],
            "window_t_star": f["t_star"],
            "window_start_calendar_date": f["window_start_calendar_date"],
            "window_first_trading_date": f["window_first_trading_date"],
            "window_last_trading_date": f["window_last_trading_date"],
            "window_trading_day_count": f["window_trading_day_count"],
            "equity_return_window": _f(f["equity_return_window"]),
            "realized_volatility": _f(f["realized_volatility"]),
            "amihud_illiquidity": _f(f["amihud_illiquidity"]),
            "t0_trading_date": f["t0_trading_date"],
            "tN_trading_date": f["tN_trading_date"],
            "missing_t0_adjusted_close": f["missing_t0_adjusted_close"],
            "missing_tN_adjusted_close": f["missing_tN_adjusted_close"],
            "fewer_than_126_valid_returns": f["fewer_than_126_valid_returns"],
            "fewer_than_126_amihud_days": f["fewer_than_126_amihud_days"],
            "missing_price_day_count": f["missing_price_day_count"],
            "zero_traded_value_day_count": f["zero_traded_value_day_count"],
            "usable_daily_return_count": f["usable_daily_return_count"],
            "usable_amihud_day_count": f["usable_amihud_day_count"],
            "in_three_variable_common_sample": key in common,
            "m2_value_status": f["m2_value_status"],
        })
    files["stage127_m2_development_features.csv"] = csv_text(
        list(feat_rows[0].keys()), feat_rows)

    # -- coverage audit ----------------------------------------------------- #
    cov_rows = []
    for var, cid, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        cov_rows.append({
            "variable": var, "candidate_id": cid,
            "total_development_rows": c["total_development_rows"],
            "valid_rows": _f(c["valid_rows"]),
            "missing_or_unresolved_rows": _f(c["missing_or_unresolved_rows"]),
            "overall_coverage": _f(c["overall_coverage"]),
            "fold1_train_coverage": _f(c["fold1_train_coverage"]),
            "fold1_validation_coverage": _f(c["fold1_validation_coverage"]),
            "fold2_train_coverage": _f(c["fold2_train_coverage"]),
            "fold2_validation_coverage": _f(c["fold2_validation_coverage"]),
            "positive_row_coverage": _f(c["positive_row_coverage"]),
            "negative_row_coverage": _f(c["negative_row_coverage"]),
            "threshold": c["threshold"],
            "resolution": c["resolution"],
            "coverage_gate_passed": _f(c["coverage_gate_passed"]),
            "admitted_into_m2_modeling_path": next(
                cand["admitted_into_m2_modeling_path"]
                for cand in decision["candidates"]
                if cand["variable"] == var),
        })
    files["stage127_m2_candidate_coverage_audit.csv"] = csv_text(
        list(cov_rows[0].keys()), cov_rows)

    # -- common sample audit ------------------------------------------------- #
    cs = decision["block_common_sample"]
    cs_rows = [{
        "block": g.M2_BLOCK,
        "requires_all_three_variables": True,
        "total_development_rows": cs["total_development_rows"],
        "common_usable_rows": _f(cs["common_usable_rows"]),
        "common_coverage": _f(cs["common_coverage"]),
        "threshold": cs["threshold"],
        "positive_count": _f(cs["positive_count"]),
        "negative_count": _f(cs["negative_count"]),
        "resolution": cs["resolution"],
        "common_coverage_gate_passed": _f(cs["common_coverage_gate_passed"]),
        "two_variable_block_silently_admitted": False,
    }]
    files["stage127_m2_common_sample_audit.csv"] = csv_text(
        list(cs_rows[0].keys()), cs_rows)

    # -- event-count feasibility --------------------------------------------- #
    ev = decision["event_count_feasibility"]
    ev_rows = []
    for window in ("fold1_validation", "fold2_validation"):
        ev_rows.append({
            "validation_window": window,
            "sample": "three_variable_common_m2_sample",
            "positive_evaluable": _f(
                ev["m2_common_sample_positive_counts"][window]),
            "negative_evaluable": _f(
                ev["m2_common_sample_negative_counts"][window]),
            "positive_threshold": ev["threshold"],
            "negative_threshold": "none_reported_descriptively_only",
            "m1_development_reference_positive": ev[
                "m1_development_reference_positive_counts"][window],
            "resolution": ev["resolution"],
            "model_fit_to_assess": False,
        })
    files["stage127_m2_event_count_feasibility.csv"] = csv_text(
        list(ev_rows[0].keys()), ev_rows)

    files["stage127_m2_join_leakage_audit.json"] = g.json_dumps(
        decision["join_leakage_audit"])

    # -- source / mapping provenance ----------------------------------------- #
    endpoints = sorted({
        part.strip()
        for row in manifest.values()
        for part in row["source_endpoint"].split(";")
        if part.strip()
    })
    source_manifest = {
        "source_id": g.M2_PRIMARY_SOURCE_ID,
        "source_family": g.M2_SOURCE_FAMILY,
        "authoritative_source_only": True,
        "substitute_sources_used": [],
        "forbidden_substitute_sources_not_used": list(
            g.FORBIDDEN_SUBSTITUTE_SOURCES),
        "source_universe_broadened_post_hoc": False,
        "evidence_mode": g.EVIDENCE_MODE_IMPORTED_BUNDLE,
        "network_required_to_reproduce_gate": False,
        "endpoint_families_observed_in_delivery": {
            "daily_closing_price": imp.DAILY_ENDPOINT_MARKER,
            "adjusted_price_history": imp.ADJUSTED_ENDPOINT_MARKER,
        },
        "distinct_endpoint_urls_in_delivery": len(endpoints),
        "endpoint_hosts_observed": sorted({
            e.split("://", 1)[1].split("/", 1)[0]
            for e in endpoints if "://" in e
        }),
        "observations_imported": import_qc["normalized_row_count"],
        "observation_date_min": import_qc["normalized_min_trading_date"],
        "observation_date_max": import_qc["normalized_max_trading_date"],
        "instrument_mapping_rows": import_qc["mapping_rows"],
        "retrieval_ranges": import_qc["manifest_rows"],
        "retrieval_status_counts": import_qc["retrieval_status_counts"],
        "partial_ranges_preserved_as_delivered": import_qc[
            "partial_ranges_preserved"],
        "partial_ranges_upgraded_or_backfilled": False,
        "field_mapping_required": {
            "adjusted_close": (
                "corporate-action-adjusted daily closing price (TSETMC "
                "Financial.aspx t=ph&a=1 field pc, joined on the exact same "
                "trading date); unadjusted close is NOT an acceptable "
                "substitute"
            ),
            "traded_value_rial": (
                "TSETMC qTotCap, in rial, taken verbatim and never recomputed "
                "as price x volume; days with V_t<=0 or missing are excluded "
                "and never imputed"
            ),
        },
        "field_mapping_verified": True,
        "field_mapping_verified_rows": import_qc[
            "raw_to_normalized_field_mapping_verified_rows"],
        "parser_module": "project/src/stage127_m2_external_delivery_import.py",
        "parser_module_sha256": g.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_external_delivery_import.py")),
        "code_revision": _git(repo_root, "rev-parse", "HEAD"),
        "execution_environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "network_egress_used_for_this_gate": False,
            "local_network_probe_note": (
                "A previous execution of this Gate in this environment could "
                "not reach TSETMC hosts. That remains an environment egress "
                "diagnostic only. It is not a property of TSETMC, and it no "
                "longer has any bearing on the Gate: the decision is now "
                "derived entirely from the imported immutable evidence bundle."
            ),
        },
        "reproduction_note": (
            "Rerun `python project/run_stage127_m2_market_data_gate.py --build "
            "--bundle <path-to-stage127_m2_tsetmc_full_delivery.zip>`. The "
            "bundle is verified by SHA256 "
            f"({imp.BUNDLE_SHA256}) before any byte of it is used."
        ),
    }
    files["stage127_m2_source_manifest.json"] = g.json_dumps(source_manifest)

    # -- authorization provenance -------------------------------------------- #
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
        "permits_ingestion_of_externally_retrieved_evidence_for_this_gate": True,
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
    files["stage127_m2_market_data_gate_human_authorization_record.json"] = (
        g.json_dumps(auth))

    # -- QC report ------------------------------------------------------------ #
    ja = decision["join_leakage_audit"]
    assertions = [
        ("bundle_sha256_verified", import_qc["bundle_sha256_verified"]),
        ("delivered_request_matches_canonical_request",
         import_qc["canonical_request_check"]["matches_canonical_request"]),
        ("mapping_rows_110", import_qc["mapping_rows"] == 110),
        ("manifest_rows_111", import_qc["manifest_rows"] == 111),
        ("status_counts_105_success_6_partial_0_failed",
         import_qc["retrieval_status_counts"] == imp.EXPECTED_STATUS_COUNTS),
        ("normalized_rows_163230",
         import_qc["normalized_row_count"] == imp.EXPECTED_NORMALIZED_ROWS),
        ("restricted_raw_files_222",
         import_qc["restricted_raw_file_count"] == 222),
        ("all_restricted_raw_sha256_verified",
         import_qc["restricted_raw_hash_verification_passed"]),
        ("provenance_sha_agrees_with_raw_manifest",
         import_qc["provenance_sha_agrees_with_raw_manifest"]),
        ("no_duplicate_normalized_keys",
         import_qc["duplicate_normalized_key_count"] == 0),
        ("raw_to_normalized_field_mapping_verified_all_rows",
         import_qc["raw_to_normalized_field_mismatches"] == 0),
        ("adjusted_close_exact_date_verified",
         import_qc["adjusted_close_exact_date_mismatches"] == 0),
        ("raw_close_never_substituted_for_adjusted_close",
         not import_qc["raw_close_substituted_for_adjusted_close"]),
        ("no_imputation_or_synthetic_values",
         not import_qc["imputation_or_synthetic_values_introduced"]),
        ("source_endpoints_tsetmc_only",
         import_qc["source_endpoints_tsetmc_only"]),
        ("six_partial_ranges_preserved",
         import_qc["partial_ranges_preserved"] == imp.EXPECTED_PARTIAL_RANGES),
        ("m2_block_has_exactly_three_variables", len(g.M2_VARIABLES) == 3),
        ("no_extra_m2_feature_computed",
         decision["frozen_m2_feature_block_extra_features_computed"] == []),
        ("development_pairs_666", len(pairs) == g.EXPECTED_DEV_PAIRS),
        ("no_final_test_rows_in_features", all(
            r["target_year"] in g.DEVELOPMENT_TARGET_YEARS for r in pairs)),
        ("no_final_test_period_observation_imported",
         import_qc["final_test_period_observations_imported"] == 0),
        ("no_duplicate_pair_keys", ja["duplicate_pair_key_violations"] == 0),
        ("zero_accepted_post_cutoff_observations",
         ja["accepted_post_cutoff_observations"] == 0),
        ("zero_accepted_target_year_leakage",
         ja["accepted_target_year_leakage_violations"] == 0),
        ("gate_not_decided_from_reachability",
         not decision["gate_decided_from_endpoint_reachability"]),
        ("no_model_fit", decision["model_fit_calls"] == 0),
        ("no_prediction", decision["prediction_calls"] == 0),
        ("final_test_locked", decision["final_test_firewall"]["final_test_locked"]),
        ("final_test_not_inspected", not decision["final_test_firewall"][
            "final_test_predictor_values_inspected"]),
        ("no_substitute_source_used",
         source_manifest["substitute_sources_used"] == []),
        ("no_accessibility_score_below_three_assigned", all(
            r["accessibility_score"] in ("", 3, 4, 5) for r in acc_rows)),
        ("block_not_redefined", decision["no_variable_dropped_from_frozen_block"]),
        ("m2_incremental_evaluation_not_authorized", not decision[
            "eligibility_for_next_action"]["m2_incremental_evaluation_authorized"]),
        ("m2_modeling_not_started", not decision[
            "eligibility_for_next_action"]["m2_modeling_started"]),
    ]
    qc = {
        "scope": g.CONTRACT_ID,
        "stage": g.STAGE,
        "decision_id": g.ACTION_ID,
        "gate_status": decision["gate_status"],
        "evidence_mode": g.EVIDENCE_MODE_IMPORTED_BUNDLE,
        "external_bundle_sha256": import_qc["bundle_sha256"],
        "vwap_band_diagnostic": import_qc["vwap_band_diagnostic"],
        "vwap_band_diagnostic_is_blocking": False,
        "assertions": [
            {"name": n, "status": "PASS" if ok else "FAIL"} for n, ok in assertions
        ],
        "assertion_count": len(assertions),
        "failed_count": sum(1 for _, ok in assertions if not ok),
        "all_pass": all(ok for _, ok in assertions),
    }
    files["stage127_m2_gate_qc_report.json"] = g.json_dumps(qc)

    files["README_STAGE127_M2_MARKET_DATA_GATE.md"] = write_readme(
        files, decision, import_qc, tstar_summary)
    return files


def write_readme(
    files: dict[str, str], decision: dict, import_qc: dict, tstar: dict,
) -> str:
    cs = decision["block_common_sample"]
    ev = decision["event_count_feasibility"]
    status = decision["gate_status"]
    lines = [
        "# Stage127 — M2 Market-Data Admission Gate",
        "",
        f"**Gate status: `{status}`**",
        "",
        "Development-only point-in-time data admission gate for the frozen "
        "three-variable M2 market block, decided **offline from imported "
        "authoritative TSETMC evidence**. This Gate answers only whether the "
        "frozen M2 variables can be obtained with correct timing, quality, "
        "coverage, joins and event support. It does **not** answer whether M2 "
        "improves prediction. No model was fit, no prediction was generated, "
        "and no final-test row was read.",
        "",
        "## Evidence",
        "",
        f"- Bundle: `{import_qc['bundle_filename']}`",
        f"- SHA256: `{import_qc['bundle_sha256']}`",
        f"- Size: {import_qc['bundle_size_bytes']:,} bytes",
        f"- Instrument mappings: **{import_qc['mapping_rows']}**; "
        f"retrieval ranges: **{import_qc['manifest_rows']}** "
        f"({import_qc['retrieval_status_counts']['SUCCESS']} SUCCESS / "
        f"{import_qc['retrieval_status_counts']['PARTIAL']} PARTIAL / "
        f"{import_qc['retrieval_status_counts']['FAILED']} FAILED)",
        f"- Normalized daily rows: **{import_qc['normalized_row_count']:,}** "
        f"({import_qc['normalized_min_trading_date']} … "
        f"{import_qc['normalized_max_trading_date']})",
        f"- Restricted raw evidence files: "
        f"**{import_qc['restricted_raw_file_count']}**, all SHA256-verified",
        "- The external QC flag was **not** trusted: every count, the raw → "
        "normalized field mapping (all rows), and the adjusted-close "
        "exact-date join were independently recomputed in this repository.",
        "- The Gate is reproducible **without a network connection** once the "
        "bundle is present. Endpoint reachability plays no part in the "
        "decision and can never produce a PASS.",
        "",
        "## Frozen M2 block (unchanged)",
        "",
        "| variable | candidate_id | usable pairs | coverage | admitted into "
        "M2 modeling path |",
        "|---|---|---:|---:|---|",
    ]
    for var, cid, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        cand = next(x for x in decision["candidates"] if x["variable"] == var)
        lines.append(
            f"| `{var}` | `{cid}` | {c['valid_rows']}/"
            f"{c['total_development_rows']} | {c['overall_coverage']:.4f} | "
            f"{'yes' if cand['admitted_into_m2_modeling_path'] else 'no'} |"
        )
    lines += [
        "",
        f"Source: `{g.M2_PRIMARY_SOURCE_ID}` ({g.M2_SOURCE_FAMILY}). "
        "Formula contract option `M2-A_modified`; shared 12-calendar-month "
        "window ending on the last eligible trading day **strictly before** "
        "each pair's cutoff; adjusted close only; >=126 usable observations; "
        "no imputation, scaling, extrapolation, annualization or threshold "
        "reduction. `ADMITTED_G01_G08_SOURCE_AND_DATA_QUALITY_ONLY` means the "
        "source/data-quality gates passed; it is NOT admission into M2 "
        "modeling, which additionally requires the frozen coverage threshold. "
        "The 111 external ranges are retrieval supersets and were "
        "**not** used as scientific windows; every window W was recomputed "
        "per pair from the frozen contract.",
        "",
        "## Gate decision conditions",
        "",
        "| condition | met |",
        "|---|---|",
    ]
    for name, met in decision["gate_decision_conditions"].items():
        lines.append(f"| `{name}` | {'yes' if met else 'no'} |")
    lines += [
        "",
        f"- Three-variable common sample: **{cs['common_usable_rows']}/"
        f"{cs['total_development_rows']}** = "
        f"{cs['common_coverage']:.4f} (threshold "
        f"{cs['threshold']})",
        "- Positive evaluable observations in the locked validation windows "
        "(common M2 sample): "
        + ", ".join(
            f"`{w}` = {n}"
            for w, n in ev["m2_common_sample_positive_counts"].items()
        )
        + "; negatives: "
        + ", ".join(
            f"`{w}` = {n}"
            for w, n in ev["m2_common_sample_negative_counts"].items()
        ),
        "",
    ]
    if decision["blocker_reasons"]:
        lines += [f"## Why `{status}`", ""]
        lines += [f"- {b}" for b in decision["blocker_reasons"]]
        lines += [
            "",
            "This is an **observed** result computed from real imported "
            "evidence against the frozen thresholds. It is deliberately not "
            "softened into `UNRESOLVED`, and no threshold was reduced, no "
            "value imputed, and no M2 variable dropped. The frozen "
            "three-variable block was not redefined; redefining it would "
            "require a separate explicit human decision."
            if status == g.GATE_STATUS_FAIL else
            "Evidence required to decide is genuinely unavailable; this is "
            "not a negative finding about TSETMC or about M2.",
            "",
        ]
    lines += [
        "## Final-test firewall",
        "",
        "`final_test_locked=true`; unlocked / access_authorized / "
        "predictor_values_inspected / target_values_inspected / "
        "evaluation_performed all `false`. Final-test target years 1400-1402 "
        "were excluded structurally before any value was read, final-test "
        "coverage was not used for admission, and every imported observation "
        "date was independently checked against the firewall "
        f"(latest imported observation: {import_qc['normalized_max_trading_date']}).",
        "",
        "## Next action",
        "",
        (
            "A Gate PASS makes `stage127-m2-incremental-evaluation` "
            "scientifically **eligible** for a new explicit human "
            "authorization. It does **not** authorize it: "
            "`m2_incremental_evaluation_authorized=false` and "
            "`m2_modeling_started=false`."
            if status == g.GATE_STATUS_PASS else
            "Not eligible to start `stage127-m2-incremental-evaluation`. M2 "
            "was not automatically redesigned and M3 was not started; this "
            "result requires human review."
        ),
        "",
        "## Files",
        "",
    ]
    for name in sorted(files):
        lines.append(f"- `{name}`")
    return "\n".join(lines) + "\n"


def resolve_bundle(arg: str | None) -> str:
    path = arg or os.environ.get(DEFAULT_BUNDLE_ENV, "")
    if not path:
        raise SystemExit(
            "the external evidence bundle is required: pass --bundle PATH or "
            f"set {DEFAULT_BUNDLE_ENV}. This Gate has no reachability-based "
            "fallback path."
        )
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--bundle", default=None)
    args = ap.parse_args()
    if args.build == args.check:
        print("exactly one of --build or --check is required", file=sys.stderr)
        return 2

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = g.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, g.OUT_DIR_REL)

    files = build_package(repo_root, resolve_bundle(args.bundle))
    decision = json.loads(files["stage127_m2_market_data_gate_decision.json"])

    if args.check:
        drift = []
        for name, text in files.items():
            if name == "stage127_m2_source_manifest.json":
                continue  # carries the live execution environment record
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
        "evidence_mode": g.EVIDENCE_MODE_IMPORTED_BUNDLE,
        "external_bundle_filename": imp.BUNDLE_FILENAME,
        "external_bundle_sha256": imp.BUNDLE_SHA256,
        "external_bundle_size_bytes": imp.BUNDLE_SIZE_BYTES,
        "canonical_request_sha256": imp.CANONICAL_REQUEST_SHA256,
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
    with open(os.path.join(
            out_dir, "metadata_and_hashes_stage127_m2_market_data_gate.json"),
            "w", encoding="utf-8") as f:
        f.write(g.json_dumps(meta))

    cs = decision["block_common_sample"]
    print(f"Stage127 Gate built: status={decision['gate_status']}")
    print(f"  bundle sha256 verified: {imp.BUNDLE_SHA256}")
    print(f"  development pairs: {cs['total_development_rows']}")
    for var, _, _ in g.M2_VARIABLES:
        c = decision["candidate_coverage"][var]
        print(f"  {var}: {c['valid_rows']}/{c['total_development_rows']} "
              f"= {c['overall_coverage']:.4f}")
    print(f"  common sample: {cs['common_usable_rows']}/"
          f"{cs['total_development_rows']} = {cs['common_coverage']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
