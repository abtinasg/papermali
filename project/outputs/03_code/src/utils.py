"""Shared helpers: config loading, paths, logging, hashing, seeding."""
from __future__ import annotations
import os
import sys
import json
import time
import hashlib
import random
import platform
import contextlib
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | None = None) -> dict:
    cfg_path = Path(path) if path else (PROJECT_ROOT / "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_project_root"] = str(PROJECT_ROOT)
    return cfg


def raw_path(cfg: dict, key: str) -> Path:
    return PROJECT_ROOT / cfg["paths"]["raw_dir"] / cfg["paths"][key]


def out_dir(cfg: dict, sub: str) -> Path:
    d = PROJECT_ROOT / cfg["paths"]["outputs_dir"] / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(obj, path: str | os.PathLike) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    return str(o)


class Tee:
    """Duplicate stdout to a run log file."""

    def __init__(self, log_path: str | os.PathLike):
        self.terminal = sys.stdout
        self.log = open(log_path, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


@contextlib.contextmanager
def tee_stdout(log_path):
    old = sys.stdout
    tee = Tee(log_path)
    sys.stdout = tee
    try:
        yield
    finally:
        sys.stdout = old
        tee.log.close()


def env_report() -> dict:
    import sklearn, xgboost, shap, imblearn, optuna, scipy, pandas, matplotlib
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "numpy": np.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "shap": shap.__version__,
        "imbalanced_learn": imblearn.__version__,
        "optuna": optuna.__version__,
        "matplotlib": matplotlib.__version__,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
