#!/usr/bin/env python3
"""Validator for the repository-driven AI Handoff Package.

Two independent modes:

  --check
      Verify the committed/on-disk handoff state is consistent with the
      repository. Fails (exit 1) on semantic drift. Key checks:
        * handoff_state.json parses;
        * generated_from_commit is an ancestor of HEAD;
        * every commit between generated_from_commit and HEAD (merge commits
          included) is Handoff-only;
        * the FULL non-volatile semantic projection equals the freshly computed
          state (so any tampered field — current_stage, current_batch, tickers,
          counts, commits, markers, fingerprint — is caught);
        * the selected QC is valid (source/test fingerprints) and clean;
        * ROADMAP action IDs are ordered and consistent;
        * docs contain no forbidden stale phrases;
        * internal markdown links in docs/ai/ resolve.

  --check-changes --baseline-ref REF [--include-working-tree]
      Enforce the file-change allowlist. Inspects `git diff --name-only REF...HEAD`
      and, with --include-working-tree, also the unstaged diff, staged diff, and
      untracked files. Directory allowlist matches by path prefix; file allowlist
      matches exact paths only (no prefix attacks). Any path outside the allowlist
      fails (exit 1).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_ai_handoff as gen  # noqa: E402

HANDOFF_STATE = "project/docs/ai/handoff_state.json"
DOCS_DIR = "project/docs/ai"

FORBIDDEN_PHRASES = (
    "git راه‌اندازی نشده",
    "git not initialized",
    "n/a (git",
    "git init",
)


class ValidationError(RuntimeError):
    pass


def _load_state(root: str) -> dict:
    path = os.path.join(root, HANDOFF_STATE)
    if not os.path.isfile(path):
        raise ValidationError(f"{HANDOFF_STATE} not found — run the generator first")
    try:
        return json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{HANDOFF_STATE} is not valid JSON: {exc}") from exc


# --------------------------------------------------------------------------- #
# --check
# --------------------------------------------------------------------------- #

def _research_action_order(root: str) -> list[str]:
    text = open(os.path.join(root, DOCS_DIR, "ROADMAP.md"), encoding="utf-8").read()
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    section = re.search(r"##\s*Research actions.*?(?=\n##\s|\Z)", body, re.DOTALL)
    scope = section.group(0) if section else body
    ids = re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", scope)
    seen, ordered = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def _check_roadmap(root: str, errors: list[str]) -> None:
    fm = gen.read_roadmap(root)
    order = _research_action_order(root)
    last, nxt = fm["last_completed_research_action_id"], fm["next_research_action_id"]
    if last not in order:
        errors.append(f"ROADMAP: last_completed id '{last}' not in Research actions list")
    if nxt not in order:
        errors.append(f"ROADMAP: next id '{nxt}' not in Research actions list")
    if last in order and nxt in order and order.index(nxt) <= order.index(last):
        errors.append(
            f"ROADMAP: next_research_action_id '{nxt}' does not come after "
            f"last_completed '{last}'"
        )


def _check_commit_anchors(root: str, state: dict, errors: list[str]) -> None:
    head = gen.head_commit(root)
    gfc = state.get("generated_from_commit")
    if not gfc:
        errors.append("handoff_state: missing generated_from_commit")
        return
    if not (gfc == head or gen.is_ancestor(root, gfc, head)):
        errors.append(
            f"generated_from_commit {gfc[:8]} is not an ancestor of HEAD {head[:8]}"
        )
        return
    if gfc != head:
        # Every commit in (gfc, HEAD] — merge commits included — must be
        # Handoff-only (inspected via files introduced vs the first parent).
        for sha in gen._git(root, "rev-list", f"{gfc}..{head}").splitlines():
            files = gen._introduced_files(root, sha)
            if not gen._is_handoff_only(files):
                errors.append(
                    f"non-Handoff commit {sha[:8]} between generated_from_commit and "
                    "HEAD — regenerate the Handoff Package"
                )


def _check_full_projection(root: str, state: dict, errors: list[str]) -> None:
    """Compare the entire non-volatile semantic projection, not a key subset."""
    try:
        fresh = gen.compute_record(root)
    except gen.HandoffError as exc:
        errors.append(f"cannot recompute state (QC/frozen invalid): {exc}")
        return
    want, have = gen.projection(fresh), gen.projection(state)
    for key in sorted(set(want) | set(have)):
        if want.get(key) != have.get(key):
            errors.append(
                f"semantic drift: {key} stored={have.get(key)!r} != repo={want.get(key)!r}"
            )
    if not (fresh["qc_all_pass"] and fresh["qc_failed"] == 0):
        errors.append("selected QC report is not all-pass / has failures")


def _check_forbidden_phrases(root: str, errors: list[str]) -> None:
    for name in os.listdir(os.path.join(root, DOCS_DIR)):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(root, DOCS_DIR, name), encoding="utf-8").read().lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in text:
                errors.append(f"{DOCS_DIR}/{name}: forbidden stale phrase '{phrase}'")


_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _check_links(root: str, errors: list[str]) -> None:
    docs = os.path.join(root, DOCS_DIR)
    for name in os.listdir(docs):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(docs, name), encoding="utf-8").read()
        for target in _LINK_RE.findall(text):
            target = target.strip()
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(docs, target))
            if not os.path.exists(resolved):
                errors.append(f"{DOCS_DIR}/{name}: broken link -> {target}")


def run_check(root: str) -> int:
    errors: list[str] = []
    try:
        state = _load_state(root)
    except ValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    _check_commit_anchors(root, state, errors)
    _check_full_projection(root, state, errors)
    try:
        _check_roadmap(root, errors)
    except gen.HandoffError as exc:
        errors.append(f"ROADMAP: {exc}")
    _check_forbidden_phrases(root, errors)
    _check_links(root, errors)

    if errors:
        print("Handoff validation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("Handoff validation passed (--check).")
    return 0


# --------------------------------------------------------------------------- #
# --check-changes
# --------------------------------------------------------------------------- #

def _changed_paths(root: str, baseline_ref: str, include_wt: bool) -> set[str]:
    paths: set[str] = set()
    paths.update(
        p for p in gen._git(root, "diff", "--name-only", f"{baseline_ref}...HEAD").splitlines() if p
    )
    if include_wt:
        paths.update(p for p in gen._git(root, "diff", "--name-only").splitlines() if p)
        paths.update(p for p in gen._git(root, "diff", "--name-only", "--cached").splitlines() if p)
        for line in gen._git(root, "status", "--porcelain", "-uall").splitlines():
            if line.startswith("?? "):
                paths.add(line[3:].strip().strip('"'))
    return paths


def run_check_changes(root: str, baseline_ref: str, include_wt: bool) -> int:
    try:
        changed = _changed_paths(root, baseline_ref, include_wt)
    except gen.HandoffError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    offenders = sorted(p for p in changed if not gen.path_allowlisted(p))
    if offenders:
        print(
            f"Handoff change-allowlist FAILED ({len(offenders)} path(s) outside "
            "allowlist):", file=sys.stderr,
        )
        for p in offenders:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"Change allowlist OK ({len(changed)} changed path(s), all allowlisted).")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="validate handoff state against the repository")
    mode.add_argument("--check-changes", action="store_true",
                      help="enforce the file-change allowlist")
    parser.add_argument("--baseline-ref", default="origin/main",
                        help="baseline ref for --check-changes (default origin/main)")
    parser.add_argument("--include-working-tree", action="store_true",
                        help="also inspect staged/unstaged/untracked changes")
    args = parser.parse_args(argv)

    try:
        root = gen.repo_root()
    except gen.HandoffError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.check:
        return run_check(root)
    return run_check_changes(root, args.baseline_ref, args.include_working_tree)


if __name__ == "__main__":
    raise SystemExit(main())
