#!/usr/bin/env python3
"""Repository-driven AI Handoff Package generator.

Generates the 🤖 auto-managed files in ``project/docs/ai/`` from the repository
state (git + QC reports + frozen-asset manifests):

    - handoff_state.json   (machine-readable snapshot + semantic fingerprint)
    - CURRENT_STATE.md     (human-readable render of the snapshot)
    - FROZEN_ASSETS.md     (report over Stage122/Stage123/Stage124 hash manifests)

Design rules (see docs/ai/README.md):
    * A tracked file cannot store the SHA of the commit that contains it, so we
      never persist "HEAD == X". We anchor on ``generated_from_commit`` (an
      ancestor of HEAD) and a semantic ``state_fingerprint``.
    * QC freshness is checked by source/test SHA-256 fingerprint, not by
      ``qc_source_commit == HEAD`` (code-commit -> artifact-commit -> merge).
    * Frozen-asset mismatch/absence is FATAL, unless the file is explicitly
      classified as regenerable/non-frozen (NON_FROZEN_TRACKED) or is gitignored.
    * Human files (ROADMAP/DECISIONS/OPEN_TASKS/CHANGELOG/README/HANDOFF_PACKAGE)
      are *inputs*; this script never overwrites them.
    * Generation is package-atomic and fail-closed: outputs are written to temp
      siblings, originals are moved aside, and on any error everything is rolled
      back so no partial state is left behind. ``--check`` writes nothing.

Usage:
    python project/scripts/update_ai_handoff.py --from-repository --write
    python project/scripts/update_ai_handoff.py --from-repository --check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# Matches a research-workflow commit anywhere in the full commit body.
STAGE_BODY_RE = re.compile(r"\bStage\d+\b", re.IGNORECASE)

AUTO_FILES = (
    "project/docs/ai/handoff_state.json",
    "project/docs/ai/CURRENT_STATE.md",
    "project/docs/ai/FROZEN_ASSETS.md",
)

HUMAN_FILES = (
    "project/docs/ai/README.md",
    "project/docs/ai/HANDOFF_PACKAGE.md",
    "project/docs/ai/ROADMAP.md",
    "project/docs/ai/DECISIONS.md",
    "project/docs/ai/OPEN_TASKS.md",
    "project/docs/ai/CHANGELOG.md",
)

# Change allowlist, split by kind so matching is precise (no prefix attacks):
#   * directory entries match via startswith(dir) and MUST end with "/".
#   * file entries match by EXACT path only.
ALLOWLIST_DIRS = (
    "project/docs/ai/",
)
ALLOWLIST_FILES = (
    "project/scripts/update_ai_handoff.py",
    "project/scripts/validate_ai_handoff.py",
    "project/tests/test_ai_handoff.py",
    "AGENTS.md",
    "CLAUDE.md",
)

FROZEN_MANIFESTS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
)

# Tracked files declared in a frozen manifest that are EXPLICITLY classified as
# regenerable / non-frozen, and therefore allowed to mismatch without aborting.
# Each entry must have a documented reason.
NON_FROZEN_TRACKED = {
    # pytest log: last line "N passed in X.XXs" embeds a non-deterministic wall
    # time, so the byte content (and SHA) varies per run while the tests pass.
    "project/stage123/stage123_unit_test_output.txt",
}

# Explicit, allow-listed workflow markers (NOT broad filename search). Legacy
# Stage121 artifacts under outputs/04_models/ must never flip these to True.
VERIFIED_MASTER_PATH = "project/stage124/listing_master_verified_stage124.csv"
GATE_B_MARKER_PATHS = (
    "project/stage124/stage124_batch02_gate_b_qc_report.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
)
MODELING_MARKER_PATHS = (
    "project/outputs/stage_modeling/run_manifest.json",
)

# handoff_state.json fields that are informational / HEAD-relative and must be
# EXCLUDED from the full semantic-projection equality check.
VOLATILE_FIELDS = frozenset({
    "generated_at_utc",
    "observed_branch",
    "observed_repository_head_commit",
    "generated_from_commit",
    "baseline_commit",
})

GENERATOR_VERSION = 2


class HandoffError(RuntimeError):
    """Fatal, fail-closed error during extraction/generation."""


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #

def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise HandoffError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:  # pragma: no cover - env guard
        raise HandoffError(f"not inside a git repository: {exc.stderr}") from exc


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


def _introduced_files(root: str, sha: str) -> list[str]:
    """Files a commit introduced relative to its first parent.

    Works for merge commits too (diff against the first parent shows what the
    merge brought in). The root commit (no parent) lists all its files.
    """
    parents = _git(root, "rev-list", "--parents", "-n", "1", sha).split()[1:]
    if not parents:
        out = _git(root, "show", "--no-renames", "--name-only", "--format=", sha)
    else:
        out = _git(root, "diff", "--no-renames", "--name-only", f"{sha}^1", sha)
    return [line for line in out.splitlines() if line.strip()]


def path_allowlisted(path: str) -> bool:
    """Directory allowlist => startswith(dir + '/'); file allowlist => exact."""
    if path in ALLOWLIST_FILES:
        return True
    return any(path.startswith(d) for d in ALLOWLIST_DIRS)


def _is_handoff_only(files: list[str]) -> bool:
    if not files:
        return False
    return all(path_allowlisted(f) for f in files)


def last_stage_commit(root: str) -> str:
    """Latest reachable, non-Handoff-only commit whose full body names a Stage/Part.

    Merge commits are NOT skipped blindly: their introduced files (vs first
    parent) are inspected; a merge that brings in only Handoff files is skipped,
    and the body of every candidate is matched against the Stage/Part pattern.
    """
    for sha in _git(root, "rev-list", "HEAD").splitlines():
        if _is_handoff_only(_introduced_files(root, sha)):
            continue
        body = _git(root, "log", "-1", "--format=%B", sha)
        if STAGE_BODY_RE.search(body):
            return sha
    raise HandoffError("no qualifying Stage/Part commit found in history")


def derive_repository(root: str) -> str | None:
    url = _safe(lambda: _git(root, "remote", "get-url", "origin"))
    if not url:
        return None
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else url


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
    for key in ("last_completed_research_action_id", "next_research_action_id"):
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


def derive_stage_batch(qc_stage: str) -> tuple[str | None, str | None]:
    s = re.search(r"stage(\d+)", qc_stage, re.IGNORECASE)
    b = re.search(r"batch(\d+)", qc_stage, re.IGNORECASE)
    return (f"Stage{s.group(1)}" if s else None,
            f"Batch{b.group(1)}" if b else None)


def select_qc_report(root: str, workstream: str, head: str) -> dict:
    """Pick the newest *valid* QC report whose scope matches the workstream."""
    candidates: list[dict] = []
    for dirpath, _dirs, files in os.walk(os.path.join(root, "project")):
        for name in files:
            if not (name.endswith(".json") and "qc" in name.lower()):
                continue
            full = os.path.join(dirpath, name)
            try:
                data = json.load(open(full, encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("stage") != workstream:
                continue
            required = (
                "source_commit", "source_file_sha256", "test_file_sha256",
                "assertion_count", "failed_count", "all_pass", "tickers",
            )
            if any(k not in data for k in required):
                continue
            data["_path"] = os.path.relpath(full, root)
            candidates.append(data)

    if not candidates:
        raise HandoffError(f"no QC report found with stage == '{workstream}'")

    valid: list[dict] = []
    for data in candidates:
        if not is_ancestor(root, data["source_commit"], head):
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
    return set(_git(root, "ls-files").splitlines())


def _is_git_ignored(root: str, path: str) -> bool:
    """True iff `git check-ignore` confirms the path is ignored (rc 0)."""
    proc = subprocess.run(
        ["git", "-C", root, "check-ignore", "-q", "--", path],
        capture_output=True,
    )
    return proc.returncode == 0


def frozen_asset_report(root: str) -> list[dict]:
    """Classify every frozen-manifest file (fail-closed).

    A file is *regenerable* (exempt from hash verification) ONLY when:
      * it is git-tracked and explicitly listed in NON_FROZEN_TRACKED, or
      * it is untracked AND (explicitly NON_FROZEN_TRACKED OR proven gitignored).
    Everything else is *frozen* and must be tracked, present, and matching —
    otherwise the caller treats it as fatal. An untracked, non-ignored,
    unclassified manifest file is therefore fatal (it is not really frozen).
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
            is_tracked = file_rel in tracked
            classified = file_rel in NON_FROZEN_TRACKED
            if is_tracked:
                regenerable = classified
            else:
                regenerable = classified or _is_git_ignored(root, file_rel)
            frozen = not regenerable
            # Hash only what we must verify (tracked frozen files).
            actual = (sha256_file(os.path.join(root, file_rel))
                      if (frozen and is_tracked) else None)
            rows.append({
                "manifest": manifest_rel,
                "path": file_rel,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "tracked": is_tracked,
                "frozen": frozen,                 # frozen => must be tracked & match
                "exists": os.path.isfile(os.path.join(root, file_rel)),
                "matches": (actual == expected) if (frozen and is_tracked) else None,
            })
    return rows


# --------------------------------------------------------------------------- #
# Markers
# --------------------------------------------------------------------------- #

def detect_markers(root: str) -> dict:
    def any_exists(paths) -> bool:
        return any(os.path.isfile(os.path.join(root, p)) for p in paths)

    return {
        "verified_master_created": os.path.isfile(os.path.join(root, VERIFIED_MASTER_PATH)),
        "gate_b_started": any_exists(GATE_B_MARKER_PATHS),
        "modeling_started": any_exists(MODELING_MARKER_PATHS),
    }


def _verified_master_tickers(root: str) -> list[str] | None:
    """Read tickers from the verified master CSV if it exists."""
    vm_path = os.path.join(root, VERIFIED_MASTER_PATH)
    if not os.path.isfile(vm_path):
        return None
    try:
        with open(vm_path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return [row["ticker"] for row in reader if row.get("ticker")]
    except (OSError, KeyError):
        return None


# --------------------------------------------------------------------------- #
# State assembly + fingerprint
# --------------------------------------------------------------------------- #

def semantic_state(root: str):
    head = head_commit(root)
    roadmap = read_roadmap(root)
    workstream = roadmap["active_research_workstream_id"].replace("-", "_")
    qc_scope_val = roadmap.get("qc_scope", "")
    qc_scope = qc_scope_val.replace("-", "_") if qc_scope_val else workstream
    qc = select_qc_report(root, qc_scope, head)
    frozen = frozen_asset_report(root)

    # Fatal: any FROZEN (non-regenerable) tracked asset that is missing or
    # mismatched. Regenerable / gitignored files are exempt by classification.
    fatal = []
    for r in frozen:
        if not r["frozen"]:
            continue
        if not r["tracked"]:
            fatal.append(f"untracked non-ignored frozen asset {r['path']}")
        elif not r["exists"]:
            fatal.append(f"missing {r['path']}")
        elif not r["matches"]:
            fatal.append(f"mismatch {r['path']}")
    if fatal:
        raise HandoffError("frozen-asset integrity failure (fail-closed): "
                           + "; ".join(fatal))

    # Use verified master tickers when available (Gate B readiness scope);
    # fall back to QC report tickers when the verified master does not exist.
    vm_tickers = _verified_master_tickers(root)
    tickers = sorted(vm_tickers) if vm_tickers is not None else sorted(qc["tickers"])

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
        # Only FROZEN (verified) files feed the fingerprint, by expected SHA.
        # Regenerable files are excluded so benign log churn is not "drift".
        "frozen_assets": {
            r["path"]: r["expected_sha256"]
            for r in sorted(frozen, key=lambda x: x["path"]) if r["frozen"]
        },
        "roadmap": {
            "active_research_workstream_id": roadmap["active_research_workstream_id"],
            "last_completed_research_action_id": roadmap["last_completed_research_action_id"],
            "next_research_action_id": roadmap["next_research_action_id"],
        },
        "markers": detect_markers(root),
        "tickers": tickers,
    }
    return state, head, qc, roadmap, frozen


def fingerprint(state: dict) -> str:
    payload = json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_handoff_state(root: str):
    state, head, qc, roadmap, frozen = semantic_state(root)
    derived_stage, derived_batch = derive_stage_batch(qc["stage"])
    stage = qc.get("current_stage") or derived_stage
    batch = qc.get("current_batch") or derived_batch
    record = {
        "schema_version": GENERATOR_VERSION,
        "repository": derive_repository(root),
        # Informational only (see VOLATILE_FIELDS).
        "observed_branch": current_branch(root),
        "observed_repository_head_commit": head,
        "baseline_branch": "origin/main",
        "baseline_commit": _safe(lambda: _git(root, "rev-parse", "origin/main")),
        "generated_from_commit": head,
        # Semantic anchors (checked by the validator).
        "last_stage_commit": state["last_stage_commit"],
        "qc_source_commit": state["selected_qc"]["source_commit"],
        "current_stage": stage,
        "current_batch": batch,
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
        "state_fingerprint": fingerprint(state),
    }
    return record, state, frozen


def compute_record(root: str) -> dict:
    return build_handoff_state(root)[0]


def _safe(fn):
    try:
        return fn()
    except HandoffError:
        return None


def projection(record: dict) -> dict:
    """Non-volatile semantic projection of a handoff_state record."""
    return {k: v for k, v in record.items() if k not in VOLATILE_FIELDS}


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
        f"- **Baseline:** `{record['baseline_branch']}` @ `{record['baseline_commit']}`",
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
        if not r["frozen"]:
            return ("➖ regenerable (classified non-frozen)" if r["tracked"]
                    else "➖ regenerable (gitignored, not verified)")
        if not r["tracked"]:
            return "❌ UNTRACKED non-ignored (frozen)"
        if not r["exists"]:
            return "⚠️ MISSING (frozen)"
        return "✅ match" if r["matches"] else "❌ MISMATCH (frozen)"

    frozen_rows = [r for r in frozen if r["frozen"] and r["tracked"]]
    n_frozen = len(frozen_rows)
    n_match = sum(1 for r in frozen_rows if r["matches"])
    lines = [
        _AUTO_BANNER,
        "# FROZEN ASSETS\n",
        "_Generated from the Stage122/Stage123/Stage124 hash manifests "
        "(`metadata_and_hashes_stage12{2,3}.json`, "
        "`metadata_and_hashes_stage124_batch02_gate_b.json`)._\n",
        f"- Frozen (verified) files: **{n_match}/{n_frozen} match**. A missing or "
        "mismatched frozen file is **fatal** (generation/validation fails).",
        "- Files are *regenerable* when gitignored (machine-dependent SHA) or "
        "explicitly classified non-frozen (`NON_FROZEN_TRACKED`, e.g. a pytest log "
        "whose timing line is non-deterministic); these are not hash-verified.",
        "",
        "| Status | Path | Manifest |",
        "|---|---|---|",
    ]
    for r in sorted(frozen, key=lambda x: x["path"]):
        lines.append(f"| {status(r)} | `{r['path']}` | `{r['manifest']}` |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Package-atomic write with rollback
# --------------------------------------------------------------------------- #

def _atomic_write(root: str, rel_outputs: dict[str, str]) -> None:
    """All-or-nothing write of the auto files.

    1) Write every new file to a ``.handoff_tmp`` sibling.
    2) Move each existing target aside to ``.handoff_bak``, then move the temp in.
    3) On success, delete backups. On any error, restore backups / remove newly
       created files so the package is never left half-updated.
    """
    targets = {rel: os.path.join(root, rel) for rel in rel_outputs}
    tmpfiles: dict[str, str] = {}
    backups: dict[str, str] = {}
    created_new: list[str] = []   # targets we created that had no prior version

    for rel, content in rel_outputs.items():
        os.makedirs(os.path.dirname(targets[rel]), exist_ok=True)
        tmp = targets[rel] + ".handoff_tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        tmpfiles[rel] = tmp

    try:
        for rel in rel_outputs:
            tgt = targets[rel]
            if os.path.exists(tgt):
                bak = tgt + ".handoff_bak"
                os.replace(tgt, bak)
                backups[rel] = bak  # recorded BEFORE the risky tmp->tgt replace
            os.replace(tmpfiles[rel], tgt)
            if rel not in backups:
                created_new.append(rel)
    except Exception:
        # Restore EVERY original we moved aside — even one whose tmp->tgt replace
        # failed (it has a backup but never made it past the failing step).
        for rel, bak in backups.items():
            tgt = targets[rel]
            if os.path.exists(tgt):
                _silent_remove(tgt)
            try:
                os.replace(bak, tgt)
            except OSError:
                pass
        # Remove only targets WE created (had no prior version); never touch
        # originals that were simply not reached before the failure.
        for rel in created_new:
            _silent_remove(targets[rel])
        for tmp in tmpfiles.values():
            _silent_remove(tmp)
        raise
    else:
        for bak in backups.values():
            _silent_remove(bak)


def _silent_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def generate(root: str) -> dict[str, str]:
    record, _state, frozen = build_handoff_state(root)
    return generate_from(record, frozen)


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
        record, _state, frozen = build_handoff_state(root)
        outputs = generate_from(record, frozen)
    except HandoffError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        _atomic_write(root, outputs)
        print("Handoff Package regenerated:")
        for rel in outputs:
            print(f"  - {rel}")
        return 0

    # --check: full semantic-projection comparison for the JSON, content compare
    # (minus volatile timestamp) for the markdown.
    drift = False
    state_path = os.path.join(root, "project/docs/ai/handoff_state.json")
    on_disk = _load_json(state_path)
    if on_disk is None or projection(on_disk) != projection(record):
        drift = True
        print("DRIFT: handoff_state.json (semantic projection differs)", file=sys.stderr)
    for rel, content in outputs.items():
        if rel.endswith("handoff_state.json"):
            continue
        disk = open(os.path.join(root, rel), encoding="utf-8").read() \
            if os.path.isfile(os.path.join(root, rel)) else None
        if _strip_volatile(disk) != _strip_volatile(content):
            drift = True
            print(f"DRIFT: {rel}", file=sys.stderr)
    if drift:
        print("Handoff Package is OUT OF DATE — run with --write.", file=sys.stderr)
        return 1
    print("Handoff Package is up to date.")
    return 0


def generate_from(record: dict, frozen: list[dict]) -> dict[str, str]:
    return {
        "project/docs/ai/handoff_state.json":
            json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "project/docs/ai/CURRENT_STATE.md": render_current_state(record),
        "project/docs/ai/FROZEN_ASSETS.md": render_frozen_assets(frozen),
    }


def _load_json(path: str):
    if not os.path.isfile(path):
        return None
    try:
        return json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _strip_volatile(text: str | None) -> str:
    if text is None:
        return ""
    return "\n".join(l for l in text.splitlines() if "generated_at_utc" not in l)


if __name__ == "__main__":
    raise SystemExit(main())
