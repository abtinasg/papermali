#!/usr/bin/env python3
"""End-to-end pipeline: one command rebuilds every output from the raw handoff.

Usage:
    python run_all.py [--config config.yaml]

Nothing here overwrites the original handoff files; all results land in outputs/.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

# sklearn 1.9 deprecates the LogisticRegression `penalty` kwarg (still functional);
# silence only that specific notice so genuine ConvergenceWarnings stay visible.
warnings.filterwarnings("ignore", message=r".*'penalty' was deprecated.*")

from src import utils
from src import build_dataset as bd
from src import data_audit, cv, tuning, train_final, evaluate
from src import calibration, explain, robustness, plots, report, deliverables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = utils.load_config(args.config)
    utils.set_global_seed(cfg["seed"])
    repro = utils.out_dir(cfg, "10_reproducibility")
    log_path = repro / "run_log.txt"
    open(log_path, "w").close()
    t0 = time.time()

    with utils.tee_stdout(log_path):
        print("=" * 70)
        print("Financial Distress Prediction — Stage121 pipeline")
        print("=" * 70)

        # ---- 02 build dataset ------------------------------------------
        built, audit = bd.build_one_year_ahead(cfg)
        bd.write_dataset_artifacts(cfg, built, audit)
        print(f"[02] one-year-ahead dataset: {audit['n_built']} rows, "
              f"{audit['n_positive']} positives ({audit['positive_rate']*100:.2f}%)")

        # ---- 01 data audit ---------------------------------------------
        data_audit.run(cfg, built, audit)

        main_feats, ext_feats, cat = bd.feature_lists(cfg)
        state = {
            "built": built, "audit": audit,
            "dev": built[built["split"] == "dev"].reset_index(drop=True),
            "test": built[built["split"] == "test"].reset_index(drop=True),
            "numeric": list(cfg["features"]["numeric_main"]),
            "categorical": cat,
        }
        cv.fold_summary(state["dev"], cfg).to_csv(
            utils.out_dir(cfg, "06_metrics") / "cv_fold_design.csv", index=False,
            encoding="utf-8-sig")
        print(f"   dev: {len(state['dev'])} rows / {int(state['dev']['target_next_year'].sum())} pos | "
              f"test: {len(state['test'])} rows / {int(state['test']['target_next_year'].sum())} pos")

        # ---- 03/11 tuning ----------------------------------------------
        state["tuning"] = {}
        for m in ["logistic", "random_forest", "xgboost"]:
            print(f"[tune] {m} ...")
            res = tuning.tune_model(m, state["dev"], state["numeric"],
                                    state["categorical"], cfg) \
                if cfg["run"]["do_tuning"] else None
            state["tuning"][m] = res
            print(f"   best CV PR-AUC={res['best_cv_pr_auc']:.4f}")

        # ---- 06 cv tables + 04 finalize + seed stability ---------------
        evaluate.cv_metric_tables(state, cfg)
        train_final.finalize_models(state, cfg)
        train_final.seed_stability(state, cfg)

        # ---- 05 predictions + 06 test metrics --------------------------
        evaluate.predictions_table(state, cfg)
        evaluate.test_metrics(state, cfg)

        # ---- 15 calibration --------------------------------------------
        calibration.run(state, cfg)

        # ---- 06 comparison workbook ------------------------------------
        evaluate.comparison_workbook(state, cfg)

        # ---- 07 explainability -----------------------------------------
        explain.run(state, cfg)

        # ---- 16 robustness ---------------------------------------------
        robustness.run(state, cfg)

        # ---- 08 figures ------------------------------------------------
        if cfg["run"]["do_figures"]:
            plots.run_all_basic(state, cfg)

        # ---- 09 reports ------------------------------------------------
        # ---- 10 reproducibility (env first, so reports can read it) -----
        _repro_env(cfg, repro)

        if cfg["run"]["do_reports"]:
            report.run(state, cfg)
            deliverables.run(cfg)   # PDF/DOCX, tables, fig index, full report, notebook

        # ---- 10 reproducibility (hashes computed last over all outputs) -
        _repro_hashes(cfg, repro, t0)
        print(f"\nDONE in {time.time()-t0:.1f}s. Outputs in {cfg['paths']['outputs_dir']}/")


def _repro_env(cfg, repro):
    utils.save_json(utils.env_report(), repro / "environment_info.json")
    seeds = {"main_seed": cfg["seed"],
             "stability_seeds": list(range(cfg["stability"]["seeds_start"],
                                           cfg["stability"]["seeds_start"]
                                           + cfg["stability"]["n_seeds"])),
             "bootstrap_seed": cfg["seed"]}
    utils.save_json(seeds, repro / "random_seeds.json")
    shutil.copy(Path(cfg["_project_root"]) / "config.yaml", repro / "final_config.yaml")
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True).stdout
        (repro / "requirements_frozen.txt").write_text(freeze, encoding="utf-8")
    except Exception as e:
        print(f"   ! pip freeze failed: {e}")


def _repro_hashes(cfg, repro, t0):
    # hashes of all produced outputs
    lines = []
    for p in sorted(Path(cfg["_project_root"], cfg["paths"]["outputs_dir"]).rglob("*")):
        if p.is_file() and p.name != "file_hashes.txt":
            lines.append(f"{utils.sha256_file(p)}  {p.relative_to(cfg['_project_root'])}")
    (repro / "file_hashes.txt").write_text("\n".join(lines), encoding="utf-8")
    (repro / "runtime_seconds.txt").write_text(f"{time.time()-t0:.1f}", encoding="utf-8")
    print(f"[10] reproducibility artifacts saved -> {repro}")


if __name__ == "__main__":
    main()
