#!/usr/bin/env python3
"""Stage122 runner — target rebuild + eligibility + t->t+1 pairs + QC.

No modeling. Reads Stage121 files read-only; writes everything to stage122/.
Usage:  python run_stage122.py
"""
from src import utils
from src import stage122


def main():
    cfg = utils.load_config()
    utils.set_global_seed(cfg.get("seed", 42))
    res = stage122.build_full(cfg)
    qc = res["qc"]
    print("\n=== Stage122 QC summary ===")
    print("rows before/after:", qc["rows_before"], "/", qc["rows_after"],
          "| dup keys after:", qc["duplicate_keys_after"])
    print("FD_target_main:", qc["target_counts"])
    print("final_model_eligible:", qc["eligibility_counts"]["final_model_eligible"],
          "| pairs final-eligible:", qc["pairs_final_eligible"])
    print("assertions:", qc["assertions"])


if __name__ == "__main__":
    main()
