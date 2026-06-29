#!/usr/bin/env python3
"""Repository-driven AI Handoff Package generator.

Generates the 🤖 auto-managed files in ``project/docs/ai/`` from the repository
state (git + QC reports + frozen-asset manifests):

    - handoff_state.json   (machine-readable snapshot + semantic fingerprint)
    - CURRENT_STATE.md     (human-readable render of the snapshot)
    - FROZEN_ASSETS.md     (report over Stage122/Stage123 hash manifests)

Design rules (see docs/ai/README.md):
    * A tracked file cannot store the SHA of the commit that contains it, so we
      never persist "HEAD == X". We anchor on ``generated_from_commit`` (an
      ancestor of HEAD) and a semantic ``state_fingerprint``.
    * QC freshness is checked by source/test SHA-256 fingerprint, not by
      ``qc_source_commit == HEAD`` (code-commit -> artifact-commit -> merge).
    * Human files (ROADMAP/DECISIONS/OPEN_TASKS/CHANGELOG/README/HANDOFF_PACKAGE)
      are *inputs*; this script never overwrites them.
    * Generation is atomic and fail-closed: everything is built and validated in a
      temp dir, then atomically moved into place. ``--check`` writes nothing.

Usage:
    python project/scripts/update_ai_handoff.py --from-repository --write
    python project/scripts/update_ai_handoff.py --from-repository --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# Paths & constants
# --------------------------------------------------------------------------- #

STAGE_SUBJECT_RE = re.compile(r"\bStage\d+\b.*\bPart\b", re.IGNORECASE)

# Auto-managed (generator output) files, relative to repo root.
AUTO_FILES = (
    "project/docs/ai/handoff_state.json",
    "project/docs/ai/CURRENT_STATE.md",
    "project/docs/ai/FROZEN_ASSETS.md",
)

# Human (input) files the generator must never overwrite.
HUMAN_FILES = (
    "project/docs/ai/README.md",
    "project/docs/ai/HANDOFF_PACKAGE.md",
    "project/docs/ai/ROADMAP.md",
    "project/docs/ai/DECISIONS.md",
    "project/docs/ai/OPEN_TASKS.md",
    "project/docs/ai/CHANGELOG.md",
)

# Paths a Handoff/maintenance commit is allowed to touch (used for "Handoff-only"
# commit detection and for the change allowlist in the validator).
HANDOFF_ALLOWLIST = (
    "project/docs/ai/",
    "project/scripts/update_ai_handoff.py",
    "project/scripts/validate_ai_handoff.py",
    "project/tests/test_ai_handoff.py",
    "AGENTS.md",
    "CLAUDE.md",
)

# Frozen-asset hash manifests, relative to repo root. Each declares
# ``output_files_sha256`` (filename -> sha256) relative to the manifest's dir.
FROZEN_MANIFESTS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
)

# Explicit, allow-listed markers (NOT broad filename search). Legacy Stage121
# artifacts under outputs/04_models/ must never flip these to True.
VERIFIED_MASTER_PATH = "project/stage124/listing_master_verified_stage124.csv"
GATE_B_MARKER_PATHS = (
    "project/stage124/stage124_batch02_gate_b_qc_report.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
)
# A run-manifest for the *new* (post-Stage123) modeling pipeline. The legacy
# baseline lives in outputs/04_models/ and is intentionally excluded.
MODELING_MARKER_PATHS = (
    "project/outputs/stage_modeling/run_manifest.json",
)

GENERATOR_VERSION = 1


class HandoffError(RuntimeError):
    """Fatal, fail-closed error during extraction/generation."""


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #

def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise HandoffError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root() -> str:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:  # pragma: no cover - env guard
        raise HandoffError(f"not inside a git repository: {exc.stderr}") from exc
    return top


def head_commit(root: str) -> str:
    return _git(root, "rev-parse", "HEAD")


def current_branch(root: str) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD")


def is_ancestor(root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", root, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def _commit_changed_files(root: str, sha: str) -> list[str]:
    # Files changed by a single commit (vs its first parent). Empty for the very
    # first commit; that's fine - it won't be Handoff-only.
    out = _git(root, "show", "--no-renames", "--name-only", "--format=", sha)
    return [line for line in out.splitlines() if line.strip()]


def _is_handoff_only(files: list[str]) -> bool:
    if not files:
        return False
    for f in files:
        if not any(f == p or f.startswith(p) for p in HANDOFF_ALLOWLIST):
            return False
    return True


def last_stage_commit(root: str) -> str:
    """Latest reachable, non-merge, non-Handoff commit with a Stage/Part subject."""
    log = _git(root, "log", "--format=%H%x1f%P%x1f%s")
    for line in log.splitlines():
        sha, parents, subject = line.split("\x1f", 2)
        if len(parents.split()) > 1:
            continue  # skip merge commits
        if not STAGE_SUBJECT_RE.search(subject):
            continue
        if _is_handoff_only(root_files := _commit_changed_files(root, sha)):
            continue
        del root_files
        return sha
    raise HandoffError("no qualifying Stage/Part commit found in history")


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #

def sha256_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# ROADMAP front matter
# --------------------------------------------------------------------------- #

def read_roadmap(root: str) -> dict:
    path = os.path.join(root, "project/docs/ai/ROADMAP.md")
    if not os.path.isfile(path):
        raise HandoffError("ROADMAP.md missing - bootstrap the human files first")
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        raise HandoffError("ROADMAP.md has no YAML front matter")
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    body = text[m.end():]
    required = (
        "active_research_workstream_id",
        "last_completed_research_action_id",
        "next_research_action_id",
        "active_maintenance_task_id",
    )
    for key in required:
        if key not in fm:
            raise HandoffError(f"ROADMAP front matter missing '{key}'")
    # Every research action ID must also appear in the body.
    for key in (
        "last_completed_research_action_id",
        "next_research_action_id",
    ):
        if fm[key] not in body:
            raise HandoffError(
                f"ROADMAP body does not list action id '{fm[key]}' (from {key})"
            )
    return fm


# --------------------------------------------------------------------------- #
# QC discovery
# --------------------------------------------------------------------------- #

def _qc_source_test_paths(stage: str) -> tuple[str, str]:
    """Convention: src/<stage>.py and tests/test_<stage>.py (repo-relative)."""
    return f"project/src/{stage}.py", f"project/tests/test_{stage}.py"


def select_qc_report(root: str, workstream: str, head: str) -> dict:
    """Pick the newest *valid* QC report whose scope matches the workstream.

    Validity (per plan): reachable source_commit, matching source/test
    fingerprints, scope match. Selection among valid candidates: newest
    generated_at. ``workstream`` like ``stage124_batch02_part03``.
    """
    qc_dir = os.path.join(root, "project")
    candidates: list[dict] = []
    for dirpath, _dirs, files in os.walk(qc_dir):
        for name in files:
            if not (name.endswith(".json") and "qc" in name.lower()):
                continue
            full = os.path.join(dirpath, name)
            try:
                data = json.load(open(full, encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            stage = data.get("stage")
            if stage != workstream:
                continue
            required = (
                "source_commit", "source_file_sha256", "test_file_sha256",
                "assertion_count", "failed_count", "all_pass", "tickers",
            )
            if any(k not in data for k in required):
                continue
            rel = os.path.relpath(full, root)
            data["_path"] = rel
            candidates.append(data)

    if not candidates:
        raise HandoffError(f"no QC report found with stage == '{workstream}'")

    valid: list[dict] = []
    for data in candidates:
        src_commit = data["source_commit"]
        if not is_ancestor(root, src_commit, head):
            continue
        src_rel, test_rel = _qc_source_test_paths(data["stage"])
        if sha256_file(os.path.join(root, src_rel)) != data["source_file_sha256"]:
            continue
        if sha256_file(os.path.join(root, test_rel)) != data["test_file_sha256"]:
            continue
        data["_source_path"] = src_rel
        data["_test_path"] = test_rel
        valid.append(data)

    if not valid:
        raise HandoffError(
            f"QC report(s) for '{workstream}' exist but none are valid "
            "(unreachable source_commit or source/test fingerprint mismatch)"
        )
    valid.sort(key=lambda d: d.get("generated_at", ""), reverse=True)
    return valid[0]


# --------------------------------------------------------------------------- #
# Frozen assets
# --------------------------------------------------------------------------- #

def _tracked_files(root: str) -> set[str]:
    """Repo-relative paths tracked by git (single batch call)."""
    out = _git(root, "ls-files")
    return set(out.splitlines())


def frozen_asset_report(root: str) -> list[dict]:
    """Report on frozen-manifest files that are **git-tracked**.

    The manifests' ``output_files_sha256`` also list gitignored, locally
    regenerated bulky outputs (xlsx workbooks, large panels) whose SHA-256 is
    machine-dependent; those are excluded from verification (reported as
    regenerable). Among tracked files, a *missing* file is fail-closed (handled by
    the caller); a content mismatch is reported but not fatal, because the
    committed tree may carry a pre-existing manifest/file drift outside this
    maintenance task's scope. Each file's expected SHA + match status feeds the
    semantic fingerprint, so future drift is still detected.
    """
    tracked = _tracked_files(root)
    rows: list[dict] = []
    for manifest_rel in FROZEN_MANIFESTS:
        manifest_path = os.path.join(root, manifest_rel)
        if not os.path.isfile(manifest_path):
            raise HandoffError(f"frozen manifest missing: {manifest_rel}")
        data = json.load(open(manifest_path, encoding="utf-8"))
        outputs = data.get("output_files_sha256", {})
        if not outputs:
            raise HandoffError(f"manifest {manifest_rel} has no output_files_sha256")
        manifest_dir = os.path.dirname(manifest_rel)
        for fname, expected in sorted(outputs.items()):
            file_rel = f"{manifest_dir}/{fname}"
            if file_rel not in tracked:
                rows.append({
                    "manifest": manifest_rel,
                    "path": file_rel,
                    "expected_sha256": expected,
                    "actual_sha256": None,
                    "tracked": False,
                    "exists": os.path.isfile(os.path.join(root, file_rel)),
                    "matches": None,  # not verified (regenerable / gitignored)
                })
                continue
            actual = sha256_file(os.path.join(root, file_rel))
            rows.append({
                "manifest": manifest_rel,
                "path": file_rel,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "tracked": True,
                "exists": actual is not None,
                "matches": actual == expected,
            })
    return rows


# --------------------------------------------------------------------------- #
# Markers
# --------------------------------------------------------------------------- #

def detect_markers(root: str) -> dict:
    def any_exists(paths) -> bool:
        return any(os.path.isfile(os.path.join(root, p)) for p in paths)

    return {
        "verified_master_created": os.path.isfile(
            os.path.join(root, VERIFIED_MASTER_PATH)
        ),
        "gate_b_started": any_exists(GATE_B_MARKER_PATHS),
        "modeling_started": any_exists(MODELING_MARKER_PATHS),
    }


# --------------------------------------------------------------------------- #
# State assembly + fingerprint
# --------------------------------------------------------------------------- #

def semantic_state(root: str) -> dict:
    head = head_commit(root)
    roadmap = read_roadmap(root)
    workstream = roadmap["active_research_workstream_id"].replace("-", "_")
    qc = select_qc_report(root, workstream, head)
    frozen = frozen_asset_report(root)

    # Fail-closed: a tracked frozen asset that has been deleted is unambiguous
    # tampering. (Content mismatches are reported, not fatal — see
    # frozen_asset_report docstring.)
    missing_tracked = [r["path"] for r in frozen if r["tracked"] and not r["exists"]]
    if missing_tracked:
        raise HandoffError(
            "tracked frozen asset(s) missing (fail-closed): "
            + ", ".join(missing_tracked)
        )

    state = {
        "last_stage_commit": last_stage_commit(root),
        "selected_qc": {
            "path": qc["_path"],
            "source_commit": qc["source_commit"],
            "assertion_count": qc["assertion_count"],
            "failed_count": qc["failed_count"],
            "all_pass": qc["all_pass"],
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
        },
        # Fingerprint over tracked frozen files: expected SHA + match status, so a
        # later content change (matches flips) is detected as drift.
        "frozen_assets": {
            r["path"]: {"expected": r["expected_sha256"], "matches": r["matches"]}
            for r in sorted(frozen, key=lambda x: x["path"]) if r["tracked"]
        },
        "roadmap": {
            "active_research_workstream_id": roadmap["active_research_workstream_id"],
            "last_completed_research_action_id": roadmap["last_completed_research_action_id"],
            "next_research_action_id": roadmap["next_research_action_id"],
        },
        "markers": detect_markers(root),
        "tickers": sorted(qc["tickers"]),
    }
    return state, head, qc, roadmap, frozen


def fingerprint(state: dict) -> str:
    payload = json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_handoff_state(root: str) -> tuple[dict, dict, list[dict]]:
    state, head, qc, roadmap, frozen = semantic_state(root)
    fp = fingerprint(state)
    record = {
        "schema_version": GENERATOR_VERSION,
        "repository": "abtinasg/papermali",
        # Informational only - never required to equal current HEAD/branch.
        "observed_branch": current_branch(root),
        "observed_repository_head_commit": head,
        "baseline_branch": "origin/main",
        "baseline_commit": _safe(lambda: _git(root, "rev-parse", "origin/main")),
        # Anchors used by the validator.
        "generated_from_commit": head,
        "last_stage_commit": state["last_stage_commit"],
        "qc_source_commit": state["selected_qc"]["source_commit"],
        "current_stage": "Stage124",
        "current_batch": "Batch02",
        "active_workstream": roadmap["active_research_workstream_id"].replace("-", "_"),
        "last_completed_micro_part": roadmap["last_completed_research_action_id"],
        "next_research_action_id": roadmap["next_research_action_id"],
        "selected_qc_scope": qc["stage"],
        "selected_qc_path": state["selected_qc"]["path"],
        "qc_assertions": state["selected_qc"]["assertion_count"],
        "qc_failed": state["selected_qc"]["failed_count"],
        "qc_all_pass": state["selected_qc"]["all_pass"],
        "modeling_started": state["markers"]["modeling_started"],
        "gate_b_started": state["markers"]["gate_b_started"],
        "verified_master_created": state["markers"]["verified_master_created"],
        "tickers": state["tickers"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state_fingerprint": fp,
    }
    return record, state, frozen


def _safe(fn):
    try:
        return fn()
    except HandoffError:
        return None


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_AUTO_BANNER = (
    "<!-- AUTO-GENERATED by project/scripts/update_ai_handoff.py — do not edit by "
    "hand. Run `python project/scripts/update_ai_handoff.py --from-repository "
    "--write` to refresh. -->\n\n"
)


def render_current_state(record: dict) -> str:
    qc_ok = "✅" if record["qc_all_pass"] and record["qc_failed"] == 0 else "❌"
    lines = [
        _AUTO_BANNER,
        "# CURRENT STATE\n",
        "_Generated from the repository (git + QC). Do not edit by hand._\n",
        "## Snapshot\n",
        f"- **Stage / Batch:** {record['current_stage']} / {record['current_batch']}",
        f"- **Active workstream:** `{record['active_workstream']}`",
        f"- **Last completed research action:** `{record['last_completed_micro_part']}`",
        f"- **Next research action:** `{record['next_research_action_id']}`",
        f"- **Last stage commit:** `{record['last_stage_commit']}`",
        f"- **Generated from commit:** `{record['generated_from_commit']}` "
        f"(branch `{record['observed_branch']}`, informational)",
        f"- **Baseline:** `{record['baseline_branch']}` @ "
        f"`{record['baseline_commit']}`",
        "",
        "## QC\n",
        f"- {qc_ok} **{record['qc_assertions']} assertions, "
        f"{record['qc_failed']} failed**, all_pass={record['qc_all_pass']}",
        f"- Scope: `{record['selected_qc_scope']}`",
        f"- Report: `{record['selected_qc_path']}`",
        f"- QC source commit (code): `{record['qc_source_commit']}`",
        "",
        "## Workflow markers\n",
        f"- modeling_started: **{record['modeling_started']}**",
        f"- gate_b_started: **{record['gate_b_started']}**",
        f"- verified_master_created: **{record['verified_master_created']}**",
        "",
        "## Tickers in current research scope\n",
        "، ".join(record["tickers"]),
        "",
        f"_state_fingerprint: `{record['state_fingerprint']}`_",
        f"_generated_at_utc: {record['generated_at_utc']} (informational)_",
        "",
    ]
    return "\n".join(lines)


def render_frozen_assets(frozen: list[dict]) -> str:
    def status(r: dict) -> str:
        if not r["tracked"]:
            return "➖ regenerable (gitignored, not verified)"
        if not r["exists"]:
            return "⚠️ MISSING (tracked)"
        return "✅ match" if r["matches"] else "❌ mismatch"

    n_tracked = sum(1 for r in frozen if r["tracked"])
    n_match = sum(1 for r in frozen if r["tracked"] and r["matches"])
    n_mismatch = sum(1 for r in frozen if r["tracked"] and r["exists"] and not r["matches"])
    lines = [
        _AUTO_BANNER,
        "# FROZEN ASSETS\n",
        "_Generated from the Stage122/Stage123 hash manifests "
        "(`metadata_and_hashes_stage12{2,3}.json`)._\n",
        f"- Tracked frozen files verified: **{n_match}/{n_tracked} match**"
        + (f", **{n_mismatch} mismatch**" if n_mismatch else "") + ".",
        "- Gitignored, locally-regenerated outputs (xlsx workbooks, bulky panels) are "
        "listed as `regenerable` and not hash-verified (their SHA is machine-dependent).",
        "- A *missing* tracked file fails generation. A mismatch is flagged here and "
        "folded into the state fingerprint, but is not fatal.",
        "",
        "| Status | Path | Manifest |",
        "|---|---|---|",
    ]
    for r in sorted(frozen, key=lambda x: x["path"]):
        lines.append(f"| {status(r)} | `{r['path']}` | `{r['manifest']}` |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Atomic write
# --------------------------------------------------------------------------- #

def _atomic_write(root: str, rel_outputs: dict[str, str]) -> None:
    """Write all outputs atomically: build in a temp dir, then os.replace each."""
    tmp_paths: dict[str, str] = {}
    docs_dir = os.path.join(root, "project/docs/ai")
    with tempfile.TemporaryDirectory(prefix="handoff_", dir=docs_dir) as tmp:
        for rel, content in rel_outputs.items():
            tmp_file = os.path.join(tmp, os.path.basename(rel))
            with open(tmp_file, "w", encoding="utf-8") as fh:
                fh.write(content)
            tmp_paths[rel] = tmp_file
        for rel, tmp_file in tmp_paths.items():
            os.replace(tmp_file, os.path.join(root, rel))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def generate(root: str) -> dict[str, str]:
    """Return {repo_relative_path: content} for all auto files."""
    record, _state, frozen = build_handoff_state(root)
    return {
        "project/docs/ai/handoff_state.json":
            json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "project/docs/ai/CURRENT_STATE.md": render_current_state(record),
        "project/docs/ai/FROZEN_ASSETS.md": render_frozen_assets(frozen),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-repository", action="store_true",
                        help="extract state from the repository (required)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the auto files")
    mode.add_argument("--check", action="store_true",
                      help="compute outputs and compare; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    if not args.from_repository:
        parser.error("--from-repository is required")

    try:
        root = repo_root()
        outputs = generate(root)
    except HandoffError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        _atomic_write(root, outputs)
        print("Handoff Package regenerated:")
        for rel in outputs:
            print(f"  - {rel}")
        return 0

    # --check: compare generated content to on-disk content (ignore volatile
    # generated_at_utc for the JSON file).
    drift = False
    for rel, content in outputs.items():
        disk_path = os.path.join(root, rel)
        on_disk = open(disk_path, encoding="utf-8").read() if os.path.isfile(disk_path) else None
        if rel.endswith("handoff_state.json"):
            if _semantic_json_differs(on_disk, content):
                drift = True
                print(f"DRIFT: {rel} (semantic state differs)", file=sys.stderr)
        elif on_disk != content:
            # CURRENT_STATE.md carries a volatile timestamp line; compare without it.
            if _strip_volatile(on_disk) != _strip_volatile(content):
                drift = True
                print(f"DRIFT: {rel}", file=sys.stderr)
    if drift:
        print("Handoff Package is OUT OF DATE — run with --write.", file=sys.stderr)
        return 1
    print("Handoff Package is up to date.")
    return 0


def _strip_volatile(text: str | None) -> str:
    if text is None:
        return ""
    return "\n".join(
        l for l in text.splitlines() if "generated_at_utc" not in l
    )


def _semantic_json_differs(on_disk: str | None, fresh: str) -> bool:
    if on_disk is None:
        return True
    try:
        a = json.loads(on_disk)
        b = json.loads(fresh)
    except json.JSONDecodeError:
        return True
    # The fingerprint summarizes the semantic state; compare it plus the anchors.
    keys = ("state_fingerprint", "last_stage_commit", "qc_source_commit",
            "qc_assertions", "qc_failed", "qc_all_pass", "next_research_action_id",
            "last_completed_micro_part", "modeling_started", "gate_b_started",
            "verified_master_created")
    return any(a.get(k) != b.get(k) for k in keys)


if __name__ == "__main__":
    raise SystemExit(main())
