"""Generate the Stage127 external TSETMC retrieval-request package.

Derives everything from canonical repository artifacts. Retrieves no market
data, fits no model, and reads no final-test row.

Usage:
    python project/run_stage127_m2_external_retrieval_request.py --build
    python project/run_stage127_m2_external_retrieval_request.py --check
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import stage127_m2_external_retrieval_request as ext  # noqa: E402
from src import stage127_m2_market_data_gate as gate  # noqa: E402


def write_zip(out_dir: str, files: dict[str, str]) -> str:
    """Package ONLY the files the external programmer needs, deterministically."""
    zip_path = os.path.join(out_dir, ext.ZIP_NAME)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ext.PACKAGE_FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, files[name])
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.build == args.check:
        print("exactly one of --build or --check is required", file=sys.stderr)
        return 2

    project_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = gate.repo_root_from(project_dir)
    out_dir = os.path.join(repo_root, ext.EXTERNAL_DIR_REL)

    files = ext.build_all(repo_root)

    if args.check:
        drift = [
            name for name, text in files.items()
            if not os.path.isfile(os.path.join(out_dir, name))
            or open(os.path.join(out_dir, name), encoding="utf-8").read() != text
        ]
        if drift:
            print(f"DRIFT: {sorted(drift)}")
            return 1
        print("Stage127 external retrieval package is up to date")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(text)
    zip_path = write_zip(out_dir, files)

    import json
    manifest = json.loads(files[ext.REQUEST_MANIFEST_JSON])
    print("Stage127 external retrieval package built:")
    print(f"  pairs         : {manifest['pair_count']}")
    print(f"  tickers       : {manifest['ticker_count']}")
    print(f"  merged ranges : {manifest['ticker_range_count']}")
    print(f"  date range    : {manifest['date_min']} .. {manifest['date_max']}")
    print(f"  zip           : {zip_path}")
    print(f"  zip sha256    : {gate.sha256_file(zip_path)}")
    print(f"  zip bytes     : {os.path.getsize(zip_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
