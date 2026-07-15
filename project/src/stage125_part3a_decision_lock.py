"""Stage125 Part 3A.1 — User-Approved Pilot Decision Lock.

Additive overlay on frozen Part 3A protocol assets. Records user-approved
rubric version, G09–G14 pilot thresholds, and the locked event-enriched
pilot pair selection. Performs **no** modeling, **no** evidence collection,
**no** network access, and does **not** modify any frozen Part 3A deliverable.

Part 3B (evidence capture) is explicitly NOT started by this module.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Iterator

import pandas as pd

from src import stage125_part3a_pilot_protocol as part3a

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3a_decision_lock"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "4e15cb7bdec07bfc007e6abe854c877ffd2ac1cc"

SRC_REL = "project/src/stage125_part3a_decision_lock.py"
TEST_REL = "project/tests/test_stage125_part3a_decision_lock.py"

PART3A_METADATA_REL = "project/stage125/metadata_and_hashes_stage125_part3a.json"

FROZEN_MANIFEST_PATHS = part3a.FROZEN_MANIFEST_PATHS + (PART3A_METADATA_REL,)

APPROVED_RUBRIC_VERSION = "stage125_part3a_v1"
APPROVED_PILOT_OPTION = "pilot_option_event_enriched"
NOT_SELECTED_OPTIONS = ("pilot_option_compact", "pilot_option_extended")

APPROVED_SAMPLE_SIZE = 80
APPROVED_POSITIVE = 39
APPROVED_NEGATIVE = 41
APPROVED_UNKNOWN = 0
APPROVED_UNIQUE_TICKERS = 26
INDUSTRY_UNKNOWN_SENTINEL = "نامشخص در فایل ارسالی"
APPROVED_UNIQUE_KNOWN_INDUSTRIES = 10
APPROVED_INDUSTRY_PRESENT_PAIRS = 53
APPROVED_INDUSTRY_MISSING_PAIRS = 27
LEGACY_NONEMPTY_INDUSTRY_LABEL_COUNT = 11

PILOT_MAX_POS_PER_YEAR = 4
PILOT_PER_YEAR_QUOTA = 8

EXPECTED_YEAR_ALLOCATION: dict[str, dict[str, int]] = {
    str(y): {"positive": 4, "negative": 4, "unknown": 0}
    for y in range(1393, 1402)
}
EXPECTED_YEAR_ALLOCATION["1402"] = {"positive": 3, "negative": 5, "unknown": 0}

F_DECISION = "part3a_decision_lock_stage125.json"
F_GATE_THRESHOLDS = "part3a_approved_gate_thresholds_stage125.csv"
F_SELECTED_PAIRS = "part3a_selected_pilot_pairs_stage125.csv"
F_QC = "stage125_part3a_decision_lock_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3a_decision_lock.json"
F_README = "README_STAGE125_PART3A_DECISION_LOCK.md"

CONTENT_FILES = (
    F_DECISION, F_GATE_THRESHOLDS, F_SELECTED_PAIRS, F_README,
)

_GATE_THRESHOLDS_HEADER = [
    "gate_id", "gate_name", "threshold_value", "unit", "denominator",
    "blocks_included", "computation_method", "pass_criterion", "scope",
    "approval_status", "notes",
]

_SELECTED_PAIRS_HEADER = [
    "selection_rank", "option_id", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t", "target_year",
    "class_label", "industry", "industry_present", "industry_missing_reason",
    "rule_a_eligible", "selection_method",
    "post_evidence_substitution_allowed", "selection_status",
]


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3A.1."""


def is_industry_missing(industry: str) -> bool:
    """Industry is missing when blank/whitespace or the unknown sentinel."""
    value = str(industry or "").strip()
    return not value or value == INDUSTRY_UNKNOWN_SENTINEL


def industry_missing_reason(industry: str) -> str:
    """Return a fail-closed missing-reason token, or empty when present."""
    value = str(industry or "").strip()
    if not value:
        return "blank_or_whitespace"
    if value == INDUSTRY_UNKNOWN_SENTINEL:
        return "unknown_sentinel"
    return ""


def classify_industry(industry: str) -> tuple[bool, str]:
    """Return (industry_present, industry_missing_reason)."""
    if is_industry_missing(industry):
        return False, industry_missing_reason(industry)
    return True, ""


def summarize_industry_counts(industries: list[str]) -> dict:
    """Aggregate industry accounting for the locked pilot selection."""
    present_pairs = sum(1 for ind in industries if not is_industry_missing(ind))
    missing_pairs = len(industries) - present_pairs
    known = sorted({
        str(ind).strip() for ind in industries if not is_industry_missing(ind)
    })
    nonempty_labels = sorted({
        str(ind).strip() for ind in industries if str(ind or "").strip()
    })
    return {
        "unique_known_industries": len(known),
        "unique_nonempty_industry_labels": len(nonempty_labels),
        "legacy_nonempty_industry_label_count": len(nonempty_labels),
        "industry_present_pairs": present_pairs,
        "industry_missing_pairs": missing_pairs,
        "known_industries": known,
    }


# --------------------------------------------------------------------------- #
# Hashing / git helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_str(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _git_last_code_commit(repo_root: str, code_paths: list[str]) -> str:
    sha = _git(repo_root, "log", "--format=%H", "-n", "1", "--", *code_paths)
    return sha or (_git(repo_root, "rev-parse", "HEAD") or "unknown")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    raw = _git(repo_root, "log", "-1", "--format=%cI", commit)
    return raw or "unknown"


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Baseline + frozen Part 3A verification
# --------------------------------------------------------------------------- #

def _resolve_commit(repo_root: str, ref: str, label: str) -> str:
    sha = _git(repo_root, "rev-parse", ref)
    if not sha:
        raise QCFail(f"{label} ({ref!r}) is not resolvable (fail-closed)")
    return sha


def _baseline_ancestry_ok(repo_root: str) -> tuple[bool, str]:
    baseline = _resolve_commit(
        repo_root, EXPECTED_BASELINE_COMMIT, "EXPECTED_BASELINE_COMMIT",
    )
    origin_main = _resolve_commit(repo_root, "origin/main", "origin/main")
    head = _resolve_commit(repo_root, "HEAD", "HEAD")

    if not _is_ancestor(repo_root, baseline, origin_main):
        return False, (
            f"expected baseline {baseline} is not an ancestor of "
            f"origin/main ({origin_main})"
        )
    if not _is_ancestor(repo_root, baseline, head):
        return False, (
            f"expected baseline {baseline} is not an ancestor of HEAD ({head})"
        )
    if not _is_ancestor(repo_root, origin_main, head):
        return False, (
            f"origin/main ({origin_main}) is not an ancestor of HEAD ({head})"
        )
    return True, (
        f"baseline {EXPECTED_BASELINE_COMMIT} is ancestor of origin/main "
        f"and HEAD; origin/main is ancestor of HEAD"
    )


def verify_baseline_commit(repo_root: str) -> None:
    ok, detail = _baseline_ancestry_ok(repo_root)
    if not ok:
        raise QCFail(f"{detail} (fail-closed)")


def part3a_frozen_hashes(repo_root: Path) -> dict[str, str]:
    """Expected SHA-256 for every tracked Part 3A frozen deliverable."""
    manifest_path = repo_root / PART3A_METADATA_REL
    if not manifest_path.is_file():
        raise QCFail(f"Part 3A metadata manifest missing: {PART3A_METADATA_REL}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = data.get("output_files_sha256", {})
    manifest_dir = Path(PART3A_METADATA_REL).parent
    snapshot: dict[str, str] = {}
    for fname in sorted(outputs):
        rel = f"{manifest_dir}/{fname}"
        expected = outputs[fname]
        actual = sha256_file(repo_root / rel)
        if actual is None:
            raise QCFail(f"Part 3A frozen file missing: {rel}")
        if actual != expected:
            raise QCFail(
                f"Part 3A frozen file hash mismatch for {rel}: "
                f"expected {expected}, got {actual}"
            )
        snapshot[rel] = actual
    return snapshot


def frozen_asset_hashes(repo_root: Path) -> dict:
    return part3a.frozen_asset_hashes(repo_root)


# --------------------------------------------------------------------------- #
# Rubric approval (read frozen rubric; do not modify)
# --------------------------------------------------------------------------- #

def load_frozen_rubric(repo_root: Path) -> dict:
    path = repo_root / "project/stage125" / part3a.F_ACCESSIBILITY_RUBRIC
    if not path.is_file():
        raise QCFail(f"missing frozen rubric: {part3a.F_ACCESSIBILITY_RUBRIC}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_rubric_approval_record(repo_root: Path) -> dict:
    rubric = load_frozen_rubric(repo_root)
    if rubric.get("rubric_version") != APPROVED_RUBRIC_VERSION:
        raise QCFail(
            f"frozen rubric version {rubric.get('rubric_version')!r} != "
            f"approved {APPROVED_RUBRIC_VERSION!r}"
        )
    rules = rubric.get("scoring_rules", {})
    return {
        "rubric_version": APPROVED_RUBRIC_VERSION,
        "rubric_approval_status": "approved_for_part3b_evidence_pilot",
        "applied_to_sources": False,
        "frozen_rubric_path": (
            f"project/stage125/{part3a.F_ACCESSIBILITY_RUBRIC}"
        ),
        "scoring_rules_locked": {
            "missing_evidence": "null_or_unresolved_never_zero",
            "score_below_3": "hard_drop",
            "score_equals_3": "pilot_permission_only_not_automatic_admission",
            "score_4_or_5": "must_still_pass_every_other_gate",
            "no_score_without_evidence_and_provenance": True,
        },
        "frozen_rubric_scoring_rules_match": (
            rules.get("missing_evidence") == "null_or_unresolved_never_zero"
            and rules.get("score_below_3") == "hard_drop"
            and rules.get("score_equals_3") ==
            "pilot_permission_only_not_automatic_admission"
            and rules.get("score_4_or_5") == "must_still_pass_every_other_gate"
            and rules.get("every_score_requires_captured_evidence_and_provenance")
            is True
        ),
        "notes": (
            "User approved rubric version stage125_part3a_v1 for Part 3B "
            "evidence pilot. Rubric file is frozen and not modified; "
            "applied_to_sources remains false until Part 3B evidence capture."
        ),
    }


# --------------------------------------------------------------------------- #
# G09–G14 approved thresholds
# --------------------------------------------------------------------------- #

def build_gate_threshold_rows() -> list[dict]:
    return [
        {
            "gate_id": "G09",
            "gate_name": "minimum_company_year_coverage",
            "threshold_value": "0.80",
            "unit": "proportion",
            "denominator": "80 selected pilot pairs",
            "blocks_included": "per_candidate",
            "computation_method": (
                "Compute separately for each registered candidate. Numerator "
                "counts pilot pairs where the candidate value has valid "
                "provenance, acceptable quality, and valid prediction-time "
                "availability. Denominator is 80 locked pilot pairs."
            ),
            "pass_criterion": (
                "coverage >= 0.80 for every candidate (each candidate "
                "evaluated independently)"
            ),
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": (
                "Pilot-only threshold; not a final modeling sample threshold."
            ),
        },
        {
            "gate_id": "G10",
            "gate_name": "minimum_common_sample_coverage",
            "threshold_value": "0.70",
            "unit": "proportion",
            "denominator": "80 selected pilot pairs",
            "blocks_included": "M2;M3;M4",
            "computation_method": (
                "Compute separately for each block (M2=all three registered "
                "M2 variables; M3=all three registered M3 variables; "
                "M4=all four registered M4 variables). Numerator counts "
                "pilot pairs where all variables in the block simultaneously "
                "pass Gates G01–G07. Denominator is 80 locked pilot pairs."
            ),
            "pass_criterion": (
                "common coverage >= 0.70 for every block (M2, M3, M4 "
                "evaluated independently)"
            ),
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": (
                "Pilot-only threshold; not a final modeling sample threshold."
            ),
        },
        {
            "gate_id": "G11",
            "gate_name": "minimum_positive_events",
            "threshold_value": "3",
            "unit": "usable_positive_pairs_per_target_year_stratum",
            "denominator": "per_target_year_stratum_per_block",
            "blocks_included": "M2;M3;M4",
            "computation_method": (
                "After applying Gates G01–G07, for each block and each "
                "target_year temporal stratum (not final modeling folds), "
                "count usable positive pilot pairs."
            ),
            "pass_criterion": (
                ">= 3 usable positive pairs in every target_year stratum "
                "for every block"
            ),
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": (
                "Temporal stratum is target_year for this pilot only."
            ),
        },
        {
            "gate_id": "G12",
            "gate_name": "minimum_negative_events",
            "threshold_value": "3",
            "unit": "usable_negative_pairs_per_target_year_stratum",
            "denominator": "per_target_year_stratum_per_block",
            "blocks_included": "M2;M3;M4",
            "computation_method": (
                "After applying Gates G01–G07, for each block and each "
                "target_year temporal stratum, count usable negative pilot "
                "pairs."
            ),
            "pass_criterion": (
                ">= 3 usable negative pairs in every target_year stratum "
                "for every block"
            ),
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": (
                "Temporal stratum is target_year for this pilot only."
            ),
        },
        {
            "gate_id": "G13",
            "gate_name": "final_pilot_sample_size",
            "threshold_value": "80",
            "unit": "selected_rule_a_eligible_pairs",
            "denominator": "locked_pilot_selection",
            "blocks_included": "all",
            "computation_method": (
                "Count of unique predictor_row_key_t in the locked pilot "
                "selection (deterministic without replacement from Rule A "
                "eligible pool, before accessibility evidence)."
            ),
            "pass_criterion": "exactly 80 selected pairs",
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": "Locked in Part 3A.1; not the final modeling sample size.",
        },
        {
            "gate_id": "G14",
            "gate_name": "final_pilot_allocation",
            "threshold_value": APPROVED_PILOT_OPTION,
            "unit": "pilot_option",
            "denominator": "80 selected pilot pairs",
            "blocks_included": "all",
            "computation_method": (
                "Deterministic without-replacement selection from Rule A "
                "eligible pool by frozen identifiers before evidence; "
                "positive=39 negative=41 unknown=0; allocation_by_target_year "
                "as locked; unique_tickers=26 "
                f"unique_known_industries={APPROVED_UNIQUE_KNOWN_INDUSTRIES} "
                f"industry_present_pairs={APPROVED_INDUSTRY_PRESENT_PAIRS} "
                f"industry_missing_pairs={APPROVED_INDUSTRY_MISSING_PAIRS} "
                f"legacy_nonempty_industry_label_count="
                f"{LEGACY_NONEMPTY_INDUSTRY_LABEL_COUNT}; "
                "no post-evidence substitution."
            ),
            "pass_criterion": (
                f"option={APPROVED_PILOT_OPTION}; positive=39; negative=41; "
                "allocation_by_target_year matches locked table"
            ),
            "scope": "evidence_accessibility_pilot_only_not_final_modeling",
            "approval_status": "approved_for_part3b_pilot",
            "notes": (
                "Failed pairs after evidence must be recorded fail/unresolved; "
                "pairs must not be replaced post-evidence."
            ),
        },
    ]


# --------------------------------------------------------------------------- #
# Pilot pair selection (deterministic; frozen identifiers only)
# --------------------------------------------------------------------------- #

def select_approved_pilot_pairs(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame,
) -> tuple[list[dict], dict[str, dict[str, int]]]:
    selected, year_allocation = part3a._deterministic_pilot_pairs(
        df_all, df_pairs, PILOT_MAX_POS_PER_YEAR, PILOT_PER_YEAR_QUOTA,
    )
    return selected, year_allocation


def build_selected_pilot_pairs_rows(
    df_pairs: pd.DataFrame, selected: list[dict],
) -> list[dict]:
    pair_lookup = df_pairs.set_index("predictor_row_key_t")
    rows: list[dict] = []
    for rank, s in enumerate(selected, start=1):
        pred_key = s["predictor_row_key_t"]
        pair_row = pair_lookup.loc[pred_key]
        present, missing_reason = classify_industry(s["industry"])
        rows.append({
            "selection_rank": rank,
            "option_id": APPROVED_PILOT_OPTION,
            "predictor_row_key_t": pred_key,
            "target_row_key_t_plus_1": s["target_row_key_t_plus_1"],
            "ticker": s["ticker"],
            "fiscal_year_t": pair_row["fiscal_year_t"],
            "target_year": s["target_year"],
            "class_label": s["class"],
            "industry": s["industry"],
            "industry_present": "true" if present else "false",
            "industry_missing_reason": missing_reason,
            "rule_a_eligible": "1",
            "selection_method": (
                "deterministic_without_replacement_rule_a_eligible_"
                "frozen_identifiers_pre_evidence"
            ),
            "post_evidence_substitution_allowed": "false",
            "selection_status": "approved_for_part3b_pilot",
        })
    return rows


def build_pilot_selection_record(
    selected: list[dict], year_allocation: dict[str, dict[str, int]],
) -> dict:
    pos = sum(1 for s in selected if s["class"] == "positive")
    neg = sum(1 for s in selected if s["class"] == "negative")
    unk = sum(1 for s in selected if s["class"] == "unknown")
    tickers = sorted({s["ticker"] for s in selected})
    industries = [s["industry"] for s in selected]
    industry_summary = summarize_industry_counts(industries)
    return {
        "selected_option": APPROVED_PILOT_OPTION,
        "not_selected_options": list(NOT_SELECTED_OPTIONS),
        "sample_size": len(selected),
        "positive": pos,
        "negative": neg,
        "unknown": unk,
        "population_representative": False,
        "modeling_sample": False,
        "eligibility_impact": "none_protocol_only",
        "sampling_purpose": "event_enriched_accessibility_coverage_pilot",
        "status": "approved_for_part3b_pilot",
        "unique_tickers": len(tickers),
        "unique_known_industries": industry_summary["unique_known_industries"],
        "unique_nonempty_industry_labels": (
            industry_summary["unique_nonempty_industry_labels"]
        ),
        "legacy_nonempty_industry_label_count": (
            industry_summary["legacy_nonempty_industry_label_count"]
        ),
        "industry_present_pairs": industry_summary["industry_present_pairs"],
        "industry_missing_pairs": industry_summary["industry_missing_pairs"],
        "tickers": tickers,
        "known_industries": industry_summary["known_industries"],
        "allocation_by_target_year": year_allocation,
        "selection_method": (
            "deterministic without replacement from Rule A eligible pool; "
            "before accessibility evidence; based on frozen identifiers"
        ),
        "post_evidence_substitution_policy": (
            "forbidden — failed pairs recorded fail/unresolved; sample not "
            "redesigned after evidence observation"
        ),
    }


def build_decision_lock_json(
    repo_root: Path,
    rubric_approval: dict,
    pilot_selection: dict,
    gate_thresholds: list[dict],
) -> dict:
    return {
        "decision_lock_version": "stage125_part3a1_v1",
        "stage": CURRENT_STAGE,
        "micro_part": "Part3A.1",
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b_started": False,
        "evidence_collected": False,
        "modeling_started": False,
        "network_extraction_performed": False,
        "eligibility_impact": "none_protocol_only",
        "candidate_decisions": "unresolved_pending_part3b_evidence",
        "rubric": rubric_approval,
        "pilot_selection": pilot_selection,
        "approved_gate_thresholds_g09_g14": gate_thresholds,
        "pilot_scope_disclaimer": (
            "Event-enriched accessibility/coverage pilot only. Not "
            "population-representative and not the modeling sample. G09–G14 "
            "thresholds apply to the evidence pilot only and must not be "
            "presented as final modeling thresholds."
        ),
        "next_action": (
            "Part 3B evidence capture (authorized only after this decision "
            "lock is merged; Part 3B not started by Part 3A.1)"
        ),
        "frozen_part3a_assets_unchanged": True,
        "frozen_part3a_metadata": PART3A_METADATA_REL,
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(pilot_selection: dict) -> str:
    alloc_lines = []
    for ty in sorted(pilot_selection["allocation_by_target_year"]):
        a = pilot_selection["allocation_by_target_year"][ty]
        alloc_lines.append(
            f"- {ty}: {a['positive']} positive / {a['negative']} negative"
        )
    alloc_block = "\n".join(alloc_lines)
    return (
        "# Stage125 Part 3A.1 — User-Approved Pilot Decision Lock\n\n"
        "## Scope\n\n"
        "Part 3A.1 records **user-approved decisions** on top of the frozen "
        "Part 3A protocol. It performs:\n"
        "- **No** modeling, **no** evidence collection, **no** network access.\n"
        "- **No** changes to frozen Part 3A protocol files or Stage122–Stage124 "
        "assets.\n"
        "- **No** accessibility scores applied to sources.\n"
        "- Part 3B (evidence capture) is **not** started.\n\n"
        "## Rubric approval\n\n"
        f"- Version `{APPROVED_RUBRIC_VERSION}` approved for Part 3B evidence "
        "pilot.\n"
        "- `rubric_approval_status=approved_for_part3b_evidence_pilot`\n"
        "- `applied_to_sources=false` (frozen rubric file unchanged)\n"
        "- Score 0–2 = hard drop; score 3 = pilot permission only; scores 4–5 "
        "must still pass all other Gates.\n"
        "- Missing evidence = null/unresolved, never zero.\n\n"
        "## Pilot selection\n\n"
        f"- Selected option: `{APPROVED_PILOT_OPTION}`\n"
        f"- Sample size: {APPROVED_SAMPLE_SIZE} "
        f"({APPROVED_POSITIVE} positive / {APPROVED_NEGATIVE} negative / "
        f"{APPROVED_UNKNOWN} unknown)\n"
        "- `population_representative=false`, `modeling_sample=false`\n"
        "- `eligibility_impact=none_protocol_only`\n"
        "- Compact and extended options remain `not_selected`.\n"
        "- Selection is deterministic, without replacement, Rule A eligible "
        "only, before evidence, from frozen identifiers.\n"
        "- **No post-evidence substitution** — failed pairs are "
        "fail/unresolved, not replaced.\n\n"
        "### Allocation by target year\n\n"
        f"{alloc_block}\n\n"
        f"- Unique tickers: {APPROVED_UNIQUE_TICKERS}\n"
        f"- Unique known industries: {APPROVED_UNIQUE_KNOWN_INDUSTRIES}\n"
        f"- Industry present pairs: {APPROVED_INDUSTRY_PRESENT_PAIRS}\n"
        f"- Industry missing pairs: {APPROVED_INDUSTRY_MISSING_PAIRS}\n"
        f"- Legacy nonempty industry label count "
        f"(includes unknown sentinel): "
        f"{LEGACY_NONEMPTY_INDUSTRY_LABEL_COUNT}\n"
        "- Unknown sentinel `نامشخص در فایل ارسالی` is **not** a known "
        "industry.\n\n"
        "## Approved G09–G14 thresholds\n\n"
        "Pilot-only coverage/event thresholds (not final modeling thresholds). "
        "See `part3a_approved_gate_thresholds_stage125.csv`.\n\n"
        "## Guardrails\n\n"
        "- `part3a_protocol_locked=true`\n"
        "- `part3a_decision_locked=true`\n"
        "- `part3b_started=false`\n"
        "- `modeling_started=false`\n"
        "- Candidate decisions remain unresolved pending Part 3B evidence.\n"
    )


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def _year_allocation_matches(
    actual: dict[str, dict[str, int]],
) -> tuple[bool, str]:
    for ty, expected in EXPECTED_YEAR_ALLOCATION.items():
        got = actual.get(ty)
        if got is None:
            return False, f"missing target_year {ty}"
        for key in ("positive", "negative", "unknown"):
            if got.get(key) != expected[key]:
                return False, (
                    f"{ty} {key}: expected {expected[key]}, got {got.get(key)}"
                )
    return True, "allocation matches locked table"


def build_qc_assertions(
    counts: dict,
    content_hashes: dict,
    frozen_before: dict,
    frozen_after: dict,
    part3a_before: dict,
    part3a_after: dict,
    rubric_approval: dict,
    pilot_selection: dict,
    selected_rows: list[dict],
    gate_rows: list[dict],
    repo_root: str,
    guard_evidence: dict,
    df_all: pd.DataFrame,
    df_pairs: pd.DataFrame,
) -> list[dict]:
    out: list[dict] = []

    def add(name, ok, detail):
        out.append({"assertion": name, "status": "PASS" if ok else "FAIL",
                    "detail": detail})

    inv_errs = part3a.check_invariants(counts)
    add("invariants_match", inv_errs == [],
        "all invariant counts match" if not inv_errs else "; ".join(inv_errs))

    baseline_ok, baseline_detail = _baseline_ancestry_ok(repo_root)
    add("baseline_ancestry_chain", baseline_ok, baseline_detail)

    add("eighty_unique_pairs", len(selected_rows) == APPROVED_SAMPLE_SIZE,
        f"selected={len(selected_rows)}")
    keys = [r["predictor_row_key_t"] for r in selected_rows]
    add("eighty_unique_pair_keys", len(keys) == len(set(keys)),
        f"unique_keys={len(set(keys))}")

    all_keys = set(df_all["row_key"])
    pred_ok = all(r["predictor_row_key_t"] in all_keys for r in selected_rows)
    tgt_ok = all(
        r["target_row_key_t_plus_1"] in all_keys for r in selected_rows
    )
    add("predictor_target_keys_in_all_rows", pred_ok and tgt_ok,
        f"predictor_ok={pred_ok}; target_ok={tgt_ok}")

    merged = part3a._merge_pairs_targets(df_all, df_pairs)
    ra_keys = set(
        merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"][
            "predictor_row_key_t"
        ]
    )
    add("all_pairs_rule_a_eligible",
        all(r["predictor_row_key_t"] in ra_keys for r in selected_rows),
        f"rule_a_pool={len(ra_keys)}")

    pos = sum(1 for r in selected_rows if r["class_label"] == "positive")
    neg = sum(1 for r in selected_rows if r["class_label"] == "negative")
    unk = sum(1 for r in selected_rows if r["class_label"] == "unknown")
    add("class_allocation_locked",
        pos == APPROVED_POSITIVE and neg == APPROVED_NEGATIVE
        and unk == APPROVED_UNKNOWN,
        f"pos={pos} neg={neg} unk={unk}")

    alloc_ok, alloc_detail = _year_allocation_matches(
        pilot_selection["allocation_by_target_year"]
    )
    add("year_allocation_locked", alloc_ok, alloc_detail)

    tickers = {r["ticker"] for r in selected_rows}
    industry_values = [r["industry"] for r in selected_rows]
    industry_summary = summarize_industry_counts(industry_values)
    add("ticker_diversity_locked",
        len(tickers) == APPROVED_UNIQUE_TICKERS,
        f"tickers={len(tickers)}")
    add("industry_accounting_locked",
        industry_summary["unique_known_industries"] == APPROVED_UNIQUE_KNOWN_INDUSTRIES
        and industry_summary["industry_present_pairs"] == APPROVED_INDUSTRY_PRESENT_PAIRS
        and industry_summary["industry_missing_pairs"] == APPROVED_INDUSTRY_MISSING_PAIRS
        and industry_summary["legacy_nonempty_industry_label_count"]
        == LEGACY_NONEMPTY_INDUSTRY_LABEL_COUNT,
        (
            f"known={industry_summary['unique_known_industries']} "
            f"present_pairs={industry_summary['industry_present_pairs']} "
            f"missing_pairs={industry_summary['industry_missing_pairs']} "
            f"legacy_nonempty={industry_summary['legacy_nonempty_industry_label_count']}"
        ))
    add("industry_present_columns_fail_closed",
        all("industry_present" in r and "industry_missing_reason" in r
            for r in selected_rows)
        and all(
            (r["industry_present"] == "true") == (r["industry_missing_reason"] == "")
            for r in selected_rows
        )
        and all(
            r["industry_present"] == "false"
            if is_industry_missing(r["industry"]) else r["industry_present"] == "true"
            for r in selected_rows
        ),
        "industry_present/industry_missing_reason consistent for all pairs")
    add("unknown_sentinel_not_known_industry",
        INDUSTRY_UNKNOWN_SENTINEL not in industry_summary["known_industries"],
        "unknown sentinel excluded from known industries")

    add("no_post_evidence_substitution",
        all(r["post_evidence_substitution_allowed"] == "false"
            for r in selected_rows),
        "post_evidence_substitution_allowed=false for all pairs")

    add("rubric_approved_not_applied",
        rubric_approval["rubric_approval_status"] ==
        "approved_for_part3b_evidence_pilot"
        and rubric_approval["applied_to_sources"] is False
        and rubric_approval["rubric_version"] == APPROVED_RUBRIC_VERSION
        and rubric_approval["frozen_rubric_scoring_rules_match"] is True,
        f"version={rubric_approval['rubric_version']}")

    gids = {g["gate_id"] for g in gate_rows}
    add("gates_g09_g14_complete",
        gids == {"G09", "G10", "G11", "G12", "G13", "G14"}
        and all(g["threshold_value"] for g in gate_rows)
        and all(g["computation_method"] for g in gate_rows),
        f"gates={sorted(gids)}")

    add("event_enriched_selected",
        pilot_selection["selected_option"] == APPROVED_PILOT_OPTION
        and pilot_selection["status"] == "approved_for_part3b_pilot",
        f"option={pilot_selection['selected_option']}")

    add("compact_extended_not_selected",
        pilot_selection["not_selected_options"] == list(NOT_SELECTED_OPTIONS),
        f"not_selected={pilot_selection['not_selected_options']}")

    add("no_accessibility_evidence_or_scores",
        rubric_approval["applied_to_sources"] is False
        and guard_evidence["part3b"]["no_part3b"],
        "no evidence files and rubric not applied")

    inv_rows = part3a.build_candidate_inventory_rows()
    registered = [
        r for r in inv_rows
        if r["candidate_scope_status"] == "registered_candidate"
    ]
    add("no_candidate_admitted_or_rejected",
        all(r["decision_status"] == "pending_part3b_evidence"
            for r in registered)
        and all(r["accessibility_score"] == "" for r in registered),
        f"registered={len(registered)}")

    part3b = guard_evidence["part3b"]
    add("no_part3b_artifacts", part3b["no_part3b"],
        "no Part 3B runner/module/evidence"
        if part3b["no_part3b"] else f"hits={part3b['hits']}")

    add("no_network_extraction", guard_evidence["no_network_calls"],
        f"network_calls={guard_evidence['network_calls_attempted']}")

    modeling = guard_evidence["modeling"]
    add("no_modeling_artifacts", modeling["no_modeling"],
        "no modeling artifacts"
        if modeling["no_modeling"] else str(modeling))

    add("eligibility_unchanged", guard_evidence["eligibility_unchanged"],
        f"rule_a={guard_evidence['eligibility']['rule_a_eligible_pairs']}"
        if guard_evidence["eligibility_unchanged"] else
        "; ".join(guard_evidence["eligibility_mismatches"]))

    add("frozen_assets_unchanged",
        frozen_before == frozen_after and len(frozen_before) > 0,
        f"{len(frozen_before)} stage manifests unchanged")

    add("part3a_frozen_files_unchanged",
        part3a_before == part3a_after and len(part3a_before) > 0,
        f"{len(part3a_before)} Part 3A files byte-identical")

    add("content_hashes_present", all(v for v in content_hashes.values()),
        f"{len(content_hashes)} content files hashed")

    add("pilot_not_modeling_sample",
        pilot_selection["modeling_sample"] is False
        and pilot_selection["population_representative"] is False,
        "event-enriched pilot; not modeling sample")

    return out


def build_qc_report(
    repo_root: Path, counts: dict,
    input_all_sha: str, input_pairs_sha: str,
    content_hashes: dict,
    frozen_before: dict, frozen_after: dict,
    part3a_before: dict, part3a_after: dict,
    tickers: list[str],
    rubric_approval: dict,
    pilot_selection: dict,
    selected_rows: list[dict],
    gate_rows: list[dict],
    guard_evidence: dict,
    df_all: pd.DataFrame,
    df_pairs: pd.DataFrame,
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    src_sha = sha256_file(repo_root / SRC_REL)
    test_sha = sha256_file(repo_root / TEST_REL)
    assertions = build_qc_assertions(
        counts, content_hashes, frozen_before, frozen_after,
        part3a_before, part3a_after, rubric_approval, pilot_selection,
        selected_rows, gate_rows, root, guard_evidence, df_all, df_pairs,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": src_sha,
        "test_file_sha256": test_sha,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "input_all_rows_name": part3a.INPUT_ALL_ROWS_NAME,
        "input_pairs_name": part3a.INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "invariants": dict(sorted(counts.items())),
        "selected_pilot_option": APPROVED_PILOT_OPTION,
        "selected_pilot_pairs": APPROVED_SAMPLE_SIZE,
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_assets_before": frozen_before,
        "frozen_assets_after": frozen_after,
        "part3a_frozen_before": part3a_before,
        "part3a_frozen_after": part3a_after,
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "part3_started": True,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b_started": False,
        "evidence_collected": False,
        "pilot_extraction_started": False,
        "network_extraction_performed": not guard_evidence["no_network_calls"],
        "network_calls_attempted": guard_evidence["network_calls_attempted"],
        "guard_evidence": guard_evidence,
        "eligibility_impact": (
            "none_protocol_only"
            if guard_evidence["eligibility_unchanged"] else "protocol_check_failed"
        ),
        "assertions": assertions,
    }


def build_metadata(
    repo_root: Path, qc_report: dict, content_hashes: dict,
    qc_hash: str, input_all_sha: str, input_pairs_sha: str,
) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage125 Part 3A.1 — user-approved pilot decision lock."
        ),
        "generated_at": qc_report["generated_at"],
        "code_commit": qc_report["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc_report["source_file_sha256"],
        "test_file_sha256": qc_report["test_file_sha256"],
        "input_all_rows_name": part3a.INPUT_ALL_ROWS_NAME,
        "input_pairs_name": part3a.INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "part3_started": True,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b_started": False,
        "evidence_collected": False,
        "pilot_extraction_started": False,
        "network_extraction_performed": qc_report.get(
            "network_extraction_performed", False),
        "network_calls_attempted": qc_report.get("network_calls_attempted", 0),
        "warning": (
            "Part 3A.1 only: records approved rubric, G09–G14 thresholds, and "
            "locked pilot selection. No modeling, no extraction, no network "
            "access. Part 3B not started. Frozen Part 3A assets unchanged."
        ),
    }


def _hash_map(files: dict[str, str]) -> dict:
    return {name: sha256_bytes(content.encode("utf-8"))
            for name, content in sorted(files.items())
            if not name.startswith("_")}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_all(
    repo_root: Path,
    all_rows_path: Path | None,
    pairs_path: Path | None,
) -> dict:
    verify_baseline_commit(str(repo_root))
    project_dir = repo_root / "project"
    with part3a.network_sentinel() as sentinel:
        part3a_before = part3a_frozen_hashes(repo_root)
        df_all, df_pairs, sha_all, sha_pairs = part3a.load_inputs(
            all_rows_path, pairs_path,
        )

        counts = part3a.compute_invariants(df_all, df_pairs)
        inv_errs = part3a.check_invariants(counts)
        if inv_errs:
            raise QCFail(
                "invariant mismatch (fail-closed):\n  " + "\n  ".join(inv_errs)
            )

        frozen_before = frozen_asset_hashes(repo_root)
        rubric_approval = build_rubric_approval_record(repo_root)
        gate_rows = build_gate_threshold_rows()
        selected, year_allocation = select_approved_pilot_pairs(
            df_all, df_pairs,
        )
        pilot_selection = build_pilot_selection_record(selected, year_allocation)
        selected_rows = build_selected_pilot_pairs_rows(df_pairs, selected)
        decision_json = build_decision_lock_json(
            repo_root, rubric_approval, pilot_selection, gate_rows,
        )

        content_files = {
            F_DECISION: _json_str(decision_json),
            F_GATE_THRESHOLDS: _csv_str(_GATE_THRESHOLDS_HEADER, gate_rows),
            F_SELECTED_PAIRS: _csv_str(_SELECTED_PAIRS_HEADER, selected_rows),
            F_README: build_readme(pilot_selection),
        }
        content_hashes = _hash_map(content_files)

        part3a_after = part3a_frozen_hashes(repo_root)
        if part3a_before != part3a_after:
            raise QCFail("Part 3A frozen files changed during run (fail-closed)")

        frozen_after = frozen_asset_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen assets changed during Part 3A.1 run (fail-closed)")

        guard_evidence = part3a.run_guardrails(
            project_dir, repo_root, df_all, df_pairs, sentinel.calls_attempted,
        )

        tickers = sorted(
            t for t in df_pairs["ticker"].dropna().unique() if str(t).strip()
        )
        qc_report = build_qc_report(
            repo_root, counts, sha_all, sha_pairs, content_hashes,
            frozen_before, frozen_after, part3a_before, part3a_after,
            tickers, rubric_approval, pilot_selection, selected_rows,
            gate_rows, guard_evidence, df_all, df_pairs,
        )
        if not qc_report["all_pass"]:
            failed = [a for a in qc_report["assertions"] if a["status"] != "PASS"]
            raise QCFail("QC failed (fail-closed): "
                         + "; ".join(f"{a['assertion']}: {a['detail']}"
                                     for a in failed))

        qc_str = _json_str(qc_report)
        qc_hash = sha256_bytes(qc_str.encode("utf-8"))
        metadata = build_metadata(
            repo_root, qc_report, content_hashes, qc_hash, sha_all, sha_pairs,
        )

        files: dict[str, str] = dict(content_files)
        files[F_QC] = qc_str
        files[F_METADATA] = _json_str(metadata)
        return {
            "files": files,
            "qc": qc_report,
            "counts": counts,
            "selected_rows": selected_rows,
            "pilot_selection": pilot_selection,
            "guard_evidence": guard_evidence,
            "input_all_rows_sha256": sha_all,
            "input_pairs_sha256": sha_pairs,
        }


def run(
    project_dir: Path | None = None,
    all_rows_path: Path | None = None,
    pairs_path: Path | None = None,
    output_dir: Path | None = None,
    write: bool = False,
) -> dict:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if all_rows_path is None:
        all_rows_path = (
            project_dir / "stage124" / "gate_b_final" / part3a.INPUT_ALL_ROWS_NAME
        )
    if pairs_path is None:
        pairs_path = (
            project_dir / "stage124" / "gate_b_final" / part3a.INPUT_PAIRS_NAME
        )
    if output_dir is None:
        output_dir = project_dir / "stage125"

    result = build_all(repo_root, all_rows_path, pairs_path)
    files = result["files"]

    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (output_dir / name).write_text(content, encoding="utf-8")
        result["written"] = True
        result["drift"] = []
    else:
        drift = []
        for name, content in files.items():
            disk = output_dir / name
            on_disk = disk.read_text(encoding="utf-8") if disk.is_file() else None
            if on_disk != content:
                drift.append(name)
        result["written"] = False
        result["drift"] = drift

    result["output_dir"] = str(output_dir)
    return result
