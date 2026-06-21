#!/usr/bin/env python3
"""Stage123 runner — statement-scope correction + eligibility/panel rebuild.

Built on the approved Stage122 output. No modeling. Writes to stage123/.
Usage:  python run_stage123.py
"""
from src import utils
from src import stage123


def main():
    cfg = utils.load_config()
    utils.set_global_seed(cfg.get("seed", 42))
    res = stage123.build_full(cfg)
    qc = res["qc"]
    print("\n=== Stage123 QC summary ===")
    print("overall_pass:", qc["overall_pass"])
    print("rows before/after:", qc["rows_before"], "/", qc["rows_after"],
          "| dup keys after:", qc["duplicate_keys_after"])
    print("statement corrected rows:", qc["statement_scope_correction"]["affected_row_count"])
    print("re-eligible (correction):", qc["rows_re_eligible_due_to_correction"])
    print("pairs main before/after:", qc["pair_final_eligible_main_before_after"])
    print("pairs expanded before/after:", qc["pair_final_eligible_expanded_before_after"])
    print("pair pos/neg main after:", qc["pair_posneg_main_after"])
    print("events 1401/1402 main:", qc["events_1401_1402_main"])
    fails = [c["check"] for c in qc["checks"] if c["status"] == "FAIL"]
    print("FAILED checks:", fails if fails else "none")


if __name__ == "__main__":
    main()
