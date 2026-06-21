#!/usr/bin/env python3
"""Stage124 Part 1 runner — build the listing-master review template only.

No modeling / Optuna / SHAP / SMOTE / calibration / macro merge. Reads the frozen
Stage123 dataset (read-only) and writes stage124/. On QC failure the report is saved,
then the process exits non-zero with no success metadata. Usage: python run_stage124.py
"""
import sys

from src import utils
from src import stage124


def main():
    cfg = utils.load_config()
    utils.set_global_seed(cfg.get("seed", 42))
    try:
        res = stage124.build_template(cfg)
    except stage124.QCFail as e:
        print(f"[stage124] QC FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    qc = res["qc"]
    print("\n=== Stage124 Part 1 (template) report ===")
    print("unique tickers:", qc["n_unique_tickers"], "| duplicates:",
          qc["duplicate_ticker_count"])
    print("covers all Stage123 tickers:", qc["covers_all_stage123_tickers"],
          "| added:", qc["tickers_added_vs_stage123"],
          "| removed:", qc["tickers_missing_vs_stage123"])
    print("tickers with incomplete name:", qc["n_tickers_incomplete_name"],
          qc["tickers_incomplete_name"])
    print("tickers with multiple name spellings:",
          qc["n_tickers_multiple_name_spellings"])
    print("Stage123 input sha256:", qc["stage123_input_sha256"][:16], "…")
    print("overall_pass:", qc["overall_pass"])


if __name__ == "__main__":
    main()
