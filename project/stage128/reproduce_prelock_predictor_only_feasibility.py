"""REPRODUCTION_OF_PRELOCK_PREDICTOR_ONLY_FEASIBILITY

Independent, in-repository reproduction of the D0/D1/D2/D3/Jalali
predictor-only feasibility counts referenced by the Stage128 D2 design
freeze. This is NOT a new design search: it evaluates only the
already-defined D0/D1/D2/D3/Jalali definitions that were historically
examined before this freeze. No new thresholds, no new candidate design,
no target/distress value is read, and no model is fit or run here.

Honest scope limitation (recorded, not concealed):

* D0 is independently and exactly reproduced in this repository from the
  already-committed, target-free
  ``project/stage127/stage127_m2_development_features.csv`` (666 rows,
  one row per development ticker x fiscal_year_t pair; this file contains
  no distress/target label column).
* D1, D2 (Gregorian), D3, and the Jalali-boundary diagnostic each require
  raw PER-DAY adjusted-close observations for the full 12-calendar-month
  window of every development pair. Those raw daily rows were never
  committed to this repository -- only aggregate per-pair derived columns
  (as in ``stage127_m2_development_features.csv``) and external-bundle
  provenance (SHA256 ``d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27
  807f75c6c6ec``, 163,230 normalized daily rows, referenced by
  ``project/stage127/stage127_m2_external_delivery_provenance.json``) are
  present in-repo. Recomputing D1/D2/D3/Jalali therefore requires data this
  repository does not contain.

Rather than fabricate synthetic daily prices engineered to reproduce the
externally-supplied counts (which would manufacture false provenance for
numbers that must match real historical evidence), this script:

1. independently and exactly reproduces the D0 count from the committed
   development-features table;
2. records the D1/D2/D3/Jalali counts as EXTERNALLY-SUPPLIED historical
   evidence, explicitly flagged as NOT independently re-derived in this
   repository, anchored only by the authorizing human utterance that
   supplied them (see
   ``stage128_m2_d2_human_authorization_record.json``).

Run: ``PYTHONPATH=project python project/stage128/
reproduce_prelock_predictor_only_feasibility.py``
"""
from __future__ import annotations

import csv
import hashlib
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_PATH = os.path.join(
    REPO_ROOT, "stage127", "stage127_m2_development_features.csv"
)
AUDIT_TABLE_PATH = os.path.join(
    REPO_ROOT, "stage128", "stage128_m2_d0_reproduction_audit_table.csv"
)
OUTPUT_PATH = os.path.join(
    REPO_ROOT, "stage128", "stage128_m2_d2_feasibility_provenance.json"
)

EXPECTED_PAIR_COUNT = 666

#: Externally-supplied historical evidence (NOT reproduced in-repo). Values
#: as supplied verbatim by the authorizing human utterance for
#: stage128-m2-boundary-month-return-design-freeze.
EXTERNAL_FEASIBILITY_EVIDENCE = {
    "D0": {"usable": 269, "total": 666},
    "D1_diagnostic_upper_bound": {"usable": 576, "total": 666},
    "D2_gregorian": {"usable": 539, "total": 666},
    "D2_three_feature_common": {"usable": 539, "total": 666},
    "D3_monthly_as_of": {"usable": 555, "total": 666, "common": 553},
    "jalali_boundary_diagnostic": {"usable": 459, "total": 666},
    "gregorian_jalali_usability_switches": 86,
    "dual_usable_under_both_calendars": 456,
    "dual_usable_return_value_difference": 0,
    "d2_unusable_total": 127,
    "d2_failure_taxonomy_non_exclusive": {
        "LT126_VALID_RETURNS": 90,
        "NO_START_BOUNDARY_PRICE": 55,
        "NO_END_BOUNDARY_PRICE": 17,
    },
    "temporal_fold_coverage": {
        "fold1_train": {"usable": 173, "total": 245},
        "fold1_validation": {"usable": 159, "total": 205},
        "fold2_train": {"usable": 332, "total": 450},
        "fold2_validation": {"usable": 207, "total": 216},
    },
}


def _present(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def reproduce_d0(features_path: str = FEATURES_PATH) -> dict:
    """Exactly reproduce the D0 usable-pair count from in-repo evidence.

    ``stage127_m2_development_features.csv`` is a target-free, already-
    committed, per-pair derived table (no distress/target label column).
    D0 usability is exactly ``equity_return_window`` being present.
    """
    with open(features_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_PAIR_COUNT:
        raise ValueError(
            f"expected {EXPECTED_PAIR_COUNT} development pairs, got {len(rows)}"
        )
    usable = sum(1 for r in rows if _present(r["equity_return_window"]))
    realized_vol = sum(1 for r in rows if _present(r["realized_volatility"]))
    amihud = sum(1 for r in rows if _present(r["amihud_illiquidity"]))
    common = sum(
        1 for r in rows
        if r["in_three_variable_common_sample"].strip().lower() == "true"
    )
    return {
        "development_pair_count": len(rows),
        "d0_equity_return_window_usable": usable,
        "realized_volatility_usable": realized_vol,
        "amihud_illiquidity_usable": amihud,
        "three_variable_common_sample_usable": common,
        "target_or_distress_column_present": False,
        "target_values_accessed": 0,
    }


def write_audit_table(features_path: str = FEATURES_PATH,
                       audit_table_path: str = AUDIT_TABLE_PATH) -> str:
    """Write a deterministic, target-free 666-row D0 reproduction audit
    table derived only from already-committed diagnostic columns."""
    with open(features_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = [
        "ticker", "fiscal_year_t", "pair_cutoff_date",
        "t0_trading_date", "tN_trading_date",
        "window_trading_day_count", "usable_daily_return_count",
        "d0_equity_return_window_usable", "realized_volatility_usable",
        "amihud_illiquidity_usable", "in_three_variable_common_sample",
        "m2_value_status",
    ]
    with open(audit_table_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "ticker": r["ticker"],
                "fiscal_year_t": r["fiscal_year_t"],
                "pair_cutoff_date": r["pair_cutoff_date"],
                "t0_trading_date": r["t0_trading_date"],
                "tN_trading_date": r["tN_trading_date"],
                "window_trading_day_count": r["window_trading_day_count"],
                "usable_daily_return_count": r["usable_daily_return_count"],
                "d0_equity_return_window_usable": _present(
                    r["equity_return_window"]),
                "realized_volatility_usable": _present(
                    r["realized_volatility"]),
                "amihud_illiquidity_usable": _present(
                    r["amihud_illiquidity"]),
                "in_three_variable_common_sample": r[
                    "in_three_variable_common_sample"],
                "m2_value_status": r["m2_value_status"],
            })
    return audit_table_path


def build_provenance_record() -> dict:
    d0 = reproduce_d0()
    audit_path = write_audit_table()
    return {
        "label": "REPRODUCTION_OF_PRELOCK_PREDICTOR_ONLY_FEASIBILITY",
        "purpose": (
            "Independent in-repository reproduction check for the "
            "predictor-only feasibility counts referenced by the Stage128 "
            "D2 design freeze. Evaluates only already-defined D0/D1/D2/D3/"
            "Jalali definitions; introduces no new candidate design, "
            "threshold, target access, or model."
        ),
        "input_bundle": "stage127_m2_tsetmc_full_delivery.zip",
        "input_bundle_sha256": (
            "d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6"
            "c6ec"
        ),
        "input_bundle_present_in_repository": False,
        "starting_scientific_lineage_source_main_commit": (
            "b25804ab764258c846b391f4823f089552c855e3"
        ),
        "development_pair_count": EXPECTED_PAIR_COUNT,
        "target_columns_accessed": 0,
        "final_test_access": 0,
        "d0_independently_reproduced_in_repository": True,
        "d0_reproduction": d0,
        "d0_reproduction_matches_authorizing_utterance": (
            d0["d0_equity_return_window_usable"]
            == EXTERNAL_FEASIBILITY_EVIDENCE["D0"]["usable"]
        ),
        "d1_d2_d3_jalali_independently_reproduced_in_repository": False,
        "d1_d2_d3_jalali_non_reproduction_reason": (
            "D1/D2/D3/Jalali usability requires raw per-day adjusted-close "
            "market observations across each pair's 12-calendar-month "
            "window. Those raw daily rows are not committed to this "
            "repository; only aggregate per-pair columns (used for the D0 "
            "reproduction above) and external-bundle SHA256 provenance are "
            "present. Fabricating synthetic daily prices to reproduce "
            "these externally-supplied counts would manufacture false "
            "provenance for numbers that must match real historical "
            "evidence, so they are instead recorded verbatim as "
            "externally-supplied historical evidence, anchored to the "
            "authorizing human utterance."
        ),
        "externally_supplied_feasibility_evidence": (
            EXTERNAL_FEASIBILITY_EVIDENCE
        ),
        "externally_supplied_evidence_provenance": (
            "stage128_m2_d2_human_authorization_record.json:"
            "human_source_utterance_sha256"
        ),
        "audit_table_path": os.path.relpath(audit_path, REPO_ROOT),
        "audit_table_row_count": EXPECTED_PAIR_COUNT,
        "audit_table_target_free": True,
        "audit_table_sha256": _sha256_file(audit_path),
        "model_fits": 0,
        "predictions": 0,
        "canonical_gate_executions_in_this_reproduction": 0,
        "new_candidate_design_introduced": False,
        "new_threshold_introduced": False,
    }


def main() -> None:
    record = build_provenance_record()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
