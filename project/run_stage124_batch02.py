#!/usr/bin/env python3
"""Stage124 Batch 2 — Gate A runner (priority + research candidate package)."""
import sys

from src import utils
from src import stage124_batch02


def main():
    cfg = utils.load_config()
    utils.set_global_seed(cfg.get("seed", 42))
    try:
        res = stage124_batch02.run()
    except stage124_batch02.QCFail as e:
        print(f"[stage124_batch02] QC FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    qc = res["qc"]
    meta = res["metadata"]
    print("\n=== Stage124 Batch 2 Gate A report ===")
    print("overall_pass:", qc["overall_pass"])
    print("pending tickers:", meta["n_pending"])
    print("selected for Batch 2:", meta["n_selected_batch02"])
    print("selection note:", meta["selection_note"])
    print("selected:", " ".join(meta["selected_tickers"]))


if __name__ == "__main__":
    main()
