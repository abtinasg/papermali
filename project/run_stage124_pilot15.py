#!/usr/bin/env python3
import sys

from src import utils
from src import stage124_pilot15


def main():
    cfg = utils.load_config()
    utils.set_global_seed(cfg.get("seed", 42))
    try:
        res = stage124_pilot15.run()
    except stage124_pilot15.QCFail as e:
        print(f"[stage124_pilot15] QC FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    qc = res["qc"]
    meta = res["metadata"]
    print("\n=== Stage124 Pilot15 user-confirmed report ===")
    print("overall_pass:", qc["overall_pass"])
    print("confirmed tickers:", meta["n_confirmed_tickers"])
    print("pending tickers:", meta["n_pending_tickers"])
    print("panel rows audited:", meta["n_panel_rows_audited"])
    print("eligibility changes vs proxy:", meta["n_eligibility_changes_vs_proxy"])


if __name__ == "__main__":
    main()
