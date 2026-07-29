"""Stage127 — import the zero-trade semantics evidence and adjudicate "trading day".

EVIDENCE IMPORT AND FROZEN-CONTRACT ADJUDICATION ONLY.

This runner does NOT fit a model, generate a prediction, read a final-test row,
change a feature, change a threshold, change t0 or T*, modify a frozen Stage125
contract, or alter the canonical M2 Gate. The canonical Gate remains
FAIL_M2_DATA_GATE and canonical coverage is untouched.

Usage:
    python project/run_stage127_m2_zero_trade_semantics_adjudication.py \
        --bundle PATH [--market-bundle PATH] [--write]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import stage127_m2_external_delivery_import as market_imp  # noqa: E402
import stage127_m2_market_data_gate as gate  # noqa: E402
import stage127_m2_trading_day_semantics_adjudication as adj  # noqa: E402
import stage127_m2_zero_trade_semantics_import as imp  # noqa: E402

OUT_DIR_REL = "project/stage127"

#: The canonical Gate this task must NOT change.
CANONICAL_GATE_STATUS = "FAIL_M2_DATA_GATE"
CANONICAL_COVERAGE = {
    "equity_return_window": {"usable": 269, "total": 666, "coverage": 0.4039039039},
    "realized_volatility": {"usable": 576, "total": 666, "coverage": 0.8648648649},
    "amihud_illiquidity": {"usable": 576, "total": 666, "coverage": 0.8648648649},
    "three_variable_common_sample": {
        "usable": 269, "total": 666, "coverage": 0.4039039039},
}

MARKET_BUNDLE_DEFAULT_NAMES = ("stage127_m2_tsetmc_full_delivery.zip",)


def resolve_bundle(explicit: str | None, filename: str) -> str | None:
    """Locate an immutable delivery without ever copying it into the repo."""
    if explicit:
        return explicit
    for directory in (
        os.path.expanduser("~/Library/Containers/ru.keepcoder.Telegram/Data/tmp"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Desktop"),
    ):
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def build_artifacts(
    repo_root: str, bundle_path: str, market_bundle: str | None,
) -> dict[str, str]:
    """Build every papermali-side artifact for this task."""
    derived = imp.build_derived_evidence(repo_root, bundle_path)
    qc = derived["qc"]

    trace = adj.build_contract_trace(repo_root)
    adjudication = adj.adjudicate(trace)

    counterfactuals: dict[str, object]
    if market_bundle:
        with market_imp.ExternalDelivery(market_bundle) as delivery:
            _market_qc, observations = market_imp.observations_by_ticker(
                delivery, repo_root)
        pairs = gate.load_development_pairs(repo_root)
        counterfactuals = adj.build_counterfactuals(pairs, observations, gate)
        counterfactuals["market_bundle_sha256"] = imp.sha256_file(market_bundle)
    else:
        counterfactuals = {
            "label": adj.COUNTERFACTUAL_LABEL,
            "computed": False,
            "reason": (
                "The immutable M2 market-data delivery "
                f"{MARKET_BUNDLE_DEFAULT_NAMES[0]} was not available to this "
                "run. Counterfactuals are diagnostic only and are never "
                "required for the adjudication."
            ),
        }
    counterfactuals["canonical_gate_status_unchanged"] = CANONICAL_GATE_STATUS
    counterfactuals["canonical_coverage_unchanged"] = CANONICAL_COVERAGE

    adjudication_record = dict(adjudication)
    adjudication_record.update({
        "artifact": "stage127_m2_trading_day_semantics_adjudication",
        "evidence_delivery": qc["provenance"],
        "contract_trace_artifact": (
            "project/stage127/"
            "stage127_m2_trading_day_semantics_contract_trace.json"
        ),
        "canonical_coverage_unchanged": CANONICAL_COVERAGE,
        "official_calendar_result": qc["calendar_point"],
        "range_calendar_vs_daily_result": qc["calendar_range_vs_daily"],
        "identity_result": qc["identity"],
        "model_fits": 0,
        "predictions_generated": 0,
        "final_test_access": 0,
        "human_review_required_before_any_canonical_change": True,
        "review_label": (
            "READY_FOR_STAGE127_SEMANTICS_REVIEW_CURRENT_IMPLEMENTATION_"
            "CONFORMANT"
            if adjudication["adjudication_outcome"] == adj.OUTCOME_A
            else "STAGE127_SEMANTIC_AMBIGUITY_REQUIRES_HUMAN_DECISION"
        ),
    })

    provenance = dict(qc["provenance"])
    provenance.update({
        "canonical_request_file": imp.CANONICAL_REQUEST_REL,
        "canonical_request_sha256": qc["requests"]["canonical_request_sha256"],
        "delivered_request_matches_canonical": True,
        "external_qc_flag_trusted": False,
        "independent_revalidation_performed_in": (
            "project/src/stage127_m2_zero_trade_semantics_import.py"
        ),
        "importer_module_sha256": imp.sha256_file(os.path.join(
            repo_root, "project/src/stage127_m2_zero_trade_semantics_import.py")),
        "adjudication_module_sha256": imp.sha256_file(os.path.join(
            repo_root,
            "project/src/stage127_m2_trading_day_semantics_adjudication.py")),
        "raw_full_escrow_present": False,
        "raw_full_escrow_requested_or_inspected": False,
        "bundle_committed_to_repository": False,
        "scientific_ingestion_bounded_to": f"{imp.ROOT}/raw_bounded/",
    })

    files: dict[str, str] = {
        "stage127_m2_zero_trade_semantics_import_qc.json": imp.json_dumps(qc),
        "stage127_m2_zero_trade_semantics_delivery_provenance.json":
            imp.json_dumps(provenance),
        "stage127_m2_trading_day_semantics_contract_trace.json":
            imp.json_dumps(trace),
        "stage127_m2_trading_day_semantics_adjudication.json":
            imp.json_dumps(adjudication_record),
        "stage127_m2_trading_day_semantics_counterfactuals.json":
            imp.json_dumps(counterfactuals),
        "stage127_m2_zero_trade_point_endpoint_evidence.csv": imp.csv_text(
            imp.POINT_EVIDENCE_COLUMNS, derived["point_rows"]),
        "stage127_m2_zero_trade_range_evidence.csv": imp.csv_text(
            imp.RANGE_EVIDENCE_COLUMNS, derived["range_rows"]),
        "stage127_m2_zero_trade_historical_identity_evidence.csv": imp.csv_text(
            imp.IDENTITY_EVIDENCE_COLUMNS, derived["identity_rows"]),
    }
    files["README_STAGE127_M2_ZERO_TRADE_SEMANTICS_ADJUDICATION.md"] = write_readme(
        qc, trace, adjudication_record, counterfactuals, derived)
    files["metadata_and_hashes_stage127_m2_zero_trade_semantics.json"] = (
        imp.json_dumps({
            "artifact_sha256": {
                name: imp.sha256_bytes(text.encode("utf-8"))
                for name, text in sorted(files.items())
            },
            "external_bundle_filename": imp.BUNDLE_FILENAME,
            "external_bundle_size_bytes": imp.BUNDLE_SIZE_BYTES,
            "external_bundle_sha256": imp.BUNDLE_SHA256,
            "canonical_gate_status_unchanged": CANONICAL_GATE_STATUS,
            "canonical_coverage_unchanged": CANONICAL_COVERAGE,
            "model_fits": 0,
            "predictions_generated": 0,
            "final_test_access": 0,
            "frozen_stage125_contracts_modified": False,
        }))
    return files


def write_readme(
    qc: dict, trace: dict, adjudication: dict, counterfactuals: dict,
    derived: dict,
) -> str:
    """Human-readable summary of the import and the adjudication."""
    cal = qc["calendar_point"]
    rng = qc["calendar_range_vs_daily"]
    ident = qc["identity"]
    raw = qc["raw"]
    readings = counterfactuals.get("readings", {})

    lines = [
        "# Stage127 M2 — zero-trade semantics evidence import and "
        "frozen-contract adjudication",
        "",
        "**Canonical Gate is UNCHANGED by this task: "
        f"`{CANONICAL_GATE_STATUS}`.** No model was fitted, no prediction was ",
        "generated, no final-test row was read, and no frozen Stage125 "
        "contract was modified.",
        "",
        "## 1. External evidence delivery",
        "",
        f"- filename: `{imp.BUNDLE_FILENAME}`",
        f"- size: {imp.BUNDLE_SIZE_BYTES:,} bytes (verified)",
        f"- SHA256: `{imp.BUNDLE_SHA256}` (verified)",
        "- The ZIP is immutable, was never edited, and is NOT committed to this "
        "repository.",
        "- The delivered `full_qc_report.json` was COMPARED AGAINST, never "
        "trusted:",
        f"  {qc['external_qc_comparison']['comparison_count']} independent "
        f"comparisons, "
        f"{qc['external_qc_comparison']['disagreement_count']} disagreements.",
        "",
        "## 2. Independent papermali-side validation",
        "",
        f"- raw bounded artifacts in ZIP: {raw['raw_artifact_count']}",
        f"- manifest rows: {raw['manifest_rows']}",
        f"- unique raw files: {raw['unique_raw_response_file_count']}",
        f"- SHA256 recomputed and verified: {raw['sha256_verified_count']} / "
        f"{raw['sha256_recomputed_count']} "
        f"(mismatches: {raw['sha256_mismatch_count']})",
        f"- exact official TSETMC endpoints verified: "
        f"{qc['endpoints']['exact_endpoint_verified_count']} "
        f"(generic: {qc['endpoints']['generic_endpoint_count']})",
        f"- artifacts with no request mapping: "
        f"{qc['mappings']['unmapped_artifact_count']}; with no evidence role: "
        f"{qc['mappings']['artifacts_without_role_count']}",
        f"- zero-byte artifacts: "
        f"{qc['zero_byte']['zero_byte_artifact_count']} "
        f"({qc['zero_byte']['zero_byte_status_counts']}); zero-byte "
        f"SUCCESS/CACHED: "
        f"{qc['zero_byte']['zero_byte_success_or_cached_count']}",
        f"- development-only firewall: maximum bounded dEven = "
        f"{qc['firewall']['maximum_bounded_dEven']}; observations at or after "
        f"{qc['firewall']['final_test_firewall_boundary_dEven']}: "
        f"{qc['firewall']['dEven_at_or_after_final_test_boundary_count']}",
        "",
        "## 3. Official calendar result",
        "",
        f"- POINT_DATE requests: {cal['point_date_requests']}",
        f"- present in official `ClosingPrice/GetInstrumentCalendar`: "
        f"{cal['point_present_in_official_instrument_calendar']}",
        f"- absent: {cal['point_absent_from_official_instrument_calendar']}; "
        f"unresolved: {cal['point_calendar_unresolved']}",
        f"- RANGE requests with InstrumentCalendar date set == "
        f"ClosingPriceDailyList date set: "
        f"{rng['calendar_vs_daily_date_sets_equal']} / {rng['range_requests']}",
        "",
        "The zero-trade endpoint dates are therefore REAL OFFICIAL "
        "InstrumentCalendar dates, not retrieval or extraction defects. The ",
        "hypothesis that these rows exist only because extraction included "
        "dates outside TSETMC's official calendar is NOT supported.",
        "",
        "## 4. Historical identity",
        "",
        f"- tickers checked: {ident['tickers_checked']}",
        f"- request_ISIN == raw instrumentID: "
        f"{ident['request_ISIN_equals_raw_instrumentID']} / "
        f"{ident['tickers_checked']}",
        f"- request_ISIN == raw cIsin: {ident['request_ISIN_equals_raw_cIsin']} "
        f"/ {ident['tickers_checked']}",
        f"- CANDIDATE_FOUND: {ident['candidate_found_count']}; NONE_FOUND: "
        f"{ident['none_found_count']}; UNRESOLVED: {ident['unresolved_count']}",
        "",
        "Identity uncertainty is preserved explicitly. Histories were NOT "
        "concatenated, `insCode=\"0\"` was NOT used as a predecessor, and the ",
        "absence of a demonstrated predecessor is NOT treated as proof that "
        "none exists.",
        "",
        "## 5. Frozen-contract semantics trace",
        "",
        f"{trace['statement_count']} frozen statements were traced "
        f"({trace['implication_strength_counts']}). Answers:",
        "",
    ]
    for q in trace["questions"]:
        lines.append(
            f"- **{q['question_id']}.** {q['question']}  \n"
            f"  → `{q['answer']}` ({q['implication_strength']})"
        )
    lines += [
        "",
        "The single decisive record is the FROZEN synthetic validation that "
        "locked the contract: a window of 248 days containing exactly one ",
        "zero-traded-value day produced 247 usable daily returns (= 248 − 1) "
        "and 246 usable Amihud days (= 247 − 1). The zero-trade day was ",
        "therefore retained in the trading-day sequence and still contributed "
        "returns; only Amihud excluded it.",
        "",
        "## 6. Adjudication outcome",
        "",
        f"**{adjudication['adjudication_outcome']}**",
        "",
        f"- current implementation conformant: "
        f"`{adjudication['current_implementation_conformant']}`",
        f"- canonical Gate changed: "
        f"`{adjudication['canonical_gate_changed']}`",
        f"- t0 changed: `{adjudication['t0_changed']}`; T* changed: "
        f"`{adjudication['t_star_changed']}`; thresholds changed: "
        f"`{adjudication['thresholds_changed']}`",
        "",
        "## 7. Diagnostic counterfactuals — NOT canonical results",
        "",
    ]
    if readings:
        lines.append(
            "| reading | equity_return | realized_vol | amihud | common |")
        lines.append("| --- | --- | --- | --- | --- |")
        for name, r in readings.items():
            lines.append(
                f"| `{name}` | {r['equity_return_window_usable']} "
                f"({r['equity_return_window_coverage']:.4f}) | "
                f"{r['realized_volatility_usable']} "
                f"({r['realized_volatility_coverage']:.4f}) | "
                f"{r['amihud_illiquidity_usable']} "
                f"({r['amihud_illiquidity_coverage']:.4f}) | "
                f"{r['three_variable_common_sample']} "
                f"({r['three_variable_common_sample_coverage']:.4f}) |"
            )
        lines += [
            "",
            "`INSTRUMENT_CALENDAR_MEMBERSHIP_READING` reproduces the canonical "
            "coverage exactly, which is what the frozen contract requires.",
            "",
            "`POSITIVE_EXECUTED_TRADE_DAY_READING` is a COUNTERFACTUAL ONLY. It "
            "is not supported by the frozen contract and is contradicted by ",
            "the frozen synthetic validation. It raises coverage, which is "
            "precisely why it may not be adopted on the strength of the Gate ",
            "result it would produce.",
        ]
    else:
        lines.append(
            f"Not computed: {counterfactuals.get('reason', 'unavailable')}")
    lines += [
        "",
        "## 8. Canonical state (unchanged)",
        "",
        f"- Gate: `{CANONICAL_GATE_STATUS}`",
        "- equity_return_window: 269 / 666 = 0.4039",
        "- realized_volatility: 576 / 666 = 0.8649",
        "- amihud_illiquidity: 576 / 666 = 0.8649",
        "- common sample: 269 / 666 = 0.4039",
        "",
        "M2 modeling is NOT authorized. M2 has NOT passed.",
        "",
        "## 9. Derived evidence artifacts",
        "",
        f"- `stage127_m2_zero_trade_point_endpoint_evidence.csv` — "
        f"{len(derived['point_rows'])} unique POINT_DATE requests covering "
        f"{derived['point_endpoint_occurrences_covered']} endpoint occurrences",
        f"- `stage127_m2_zero_trade_range_evidence.csv` — "
        f"{len(derived['range_rows'])} low-return RANGE requests",
        f"- `stage127_m2_zero_trade_historical_identity_evidence.csv` — "
        f"{len(derived['identity_rows'])} tickers",
        "",
        "Factual evidence and scientific interpretation are kept strictly "
        "separate: every evidence row carries ",
        "`scientific_inclusion_decision = "
        "NOT_A_SCIENTIFIC_DECISION_SEE_ADJUDICATION_ARTIFACT`, and TSETMC "
        "state codes remain literal with UNRESOLVED meaning.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=None,
                        help="path to the immutable v3 evidence delivery ZIP")
    parser.add_argument("--market-bundle", default=None,
                        help="path to the immutable M2 market-data delivery ZIP")
    parser.add_argument("--write", action="store_true",
                        help="write the artifacts to project/stage127/")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundle = resolve_bundle(args.bundle, imp.BUNDLE_FILENAME)
    if not bundle:
        print(f"ERROR: evidence delivery {imp.BUNDLE_FILENAME} not found",
              file=sys.stderr)
        return 2
    market = resolve_bundle(args.market_bundle, MARKET_BUNDLE_DEFAULT_NAMES[0])

    try:
        files = build_artifacts(repo_root, bundle, market)
    except imp.EvidenceImportError as exc:
        print(f"IMPORT FAILED CLOSED: {exc}", file=sys.stderr)
        return 1

    out_dir = os.path.join(repo_root, OUT_DIR_REL)
    for name, text in sorted(files.items()):
        if args.write:
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        print(f"{'wrote' if args.write else 'built'} {OUT_DIR_REL}/{name}")
    if not args.write:
        print("\n(dry run — pass --write to persist)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
