#!/usr/bin/env python3
"""Validate Part 3 manual evidence intake. Dry-run by default; no network."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
from src import stage124_batch02_part03 as p3  # noqa: E402
from src import stage124_batch02_part03_manual_intake as mi  # noqa: E402

BASE = p3.PART03_DIR
DEFAULT_INTAKE = BASE / "part03_manual_evidence_intake_template.csv"
DEFAULT_REGISTRY = BASE / "part03_source_registry.csv"
DEFAULT_PROVENANCE = BASE / "part03_source_provenance_10tickers.csv"
DEFAULT_AUDIT = BASE / "part03_manual_evidence_intake_audit.csv"
DEFAULT_MANIFEST = BASE / "part03_manual_evidence_intake_apply_manifest.json"


def file_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def csv_bytes(df: pd.DataFrame) -> bytes:
    return ("\ufeff" + df.to_csv(index=False, lineterminator="\n")).encode("utf-8")


def atomic_write(outputs: dict[Path, bytes]) -> None:
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    created: list[Path] = []
    for target, payload in outputs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".intake_tmp")
        tmp.write_bytes(payload)
        temps[target] = tmp
    try:
        for target in outputs:
            if target.exists():
                bak = target.with_name(target.name + ".intake_bak")
                os.replace(target, bak)
                backups[target] = bak
            os.replace(temps[target], target)
            if target not in backups:
                created.append(target)
    except Exception:
        for target, bak in backups.items():
            if target.exists():
                target.unlink()
            if bak.exists():
                os.replace(bak, target)
        for target in created:
            if target.exists():
                target.unlink()
        for tmp in temps.values():
            if tmp.exists():
                tmp.unlink()
        raise
    else:
        for bak in backups.values():
            if bak.exists():
                bak.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake", type=Path, default=DEFAULT_INTAKE)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    ap.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--snapshot-root", type=Path, default=p3.ROOT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    for path in (args.intake, args.registry, args.provenance):
        if not path.is_file():
            print(f"ERROR: missing required file: {path}", file=sys.stderr)
            return 2

    intake = mi.read_intake_csv(args.intake)
    if intake.empty:
        if list(intake.columns) != mi.INTAKE_COLUMNS:
            print("ERROR: intake schema mismatch", file=sys.stderr)
            return 2
        if args.apply:
            print("ERROR: refusing --apply with an empty intake", file=sys.stderr)
            return 2
        print("DRY RUN: header-only intake is valid; no files changed.")
        return 0

    try:
        registry = read_csv(args.registry)
        provenance = read_csv(args.provenance)
        new_registry, new_provenance, audit = mi.ingest_manual_evidence_intake(
            registry, provenance, intake, args.snapshot_root,
            apply_mode="apply" if args.apply else "dry_run",
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Validated {len(intake)} row(s); registry={len(new_registry)}, provenance={len(new_provenance)}")
    if not args.apply:
        print("DRY RUN ONLY: no files changed.")
        return 0

    before_frozen = {"stage122": file_sha(Path(p3.STAGE122_INPUT)),
                     "stage123": file_sha(Path(p3.STAGE123_INPUT))}
    reg_b = csv_bytes(new_registry[p3.SOURCE_REGISTRY_COLUMNS])
    prov_b = csv_bytes(new_provenance[p3.PROVENANCE_COLUMNS])
    audit_b = csv_bytes(audit[mi.AUDIT_COLUMNS])
    manifest = {
        "stage": "stage124_batch02_part03_1b_0_manual_intake",
        "applied_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "network_request_performed": False,
        "intake_path": str(args.intake),
        "intake_sha256": file_sha(args.intake),
        "intake_row_count": len(intake),
        "source_registry_rows": len(new_registry),
        "provenance_rows": len(new_provenance),
        "audit_rows": len(audit),
        "frozen_before_sha256": before_frozen,
    }
    outputs = {
        args.registry: reg_b,
        args.provenance: prov_b,
        args.audit: audit_b,
        args.manifest: (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    }
    try:
        atomic_write(outputs)
    except Exception as exc:
        print(f"ERROR: atomic apply rolled back: {exc}", file=sys.stderr)
        return 2

    after_frozen = {"stage122": file_sha(Path(p3.STAGE122_INPUT)),
                    "stage123": file_sha(Path(p3.STAGE123_INPUT))}
    if after_frozen != before_frozen:
        print("ERROR: frozen inputs changed unexpectedly", file=sys.stderr)
        return 3
    print("APPLIED: registry/provenance/audit/manifest updated; no network used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
