"""Stage125 Part 3A — Accessibility, Coverage & Event Pilot Protocol Lock.

This module implements ONLY Stage125 Part 3A. It locks the pilot protocol
BEFORE any source-accessibility or coverage evidence is collected. It performs
**no** modeling, **no** data extraction, **no** network access, and does **not**
modify any frozen Stage122–Stage124 asset, the target, the sample, eligibility,
or the cutoff.

Part 3B (evidence capture) is explicitly NOT started by this module.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import socket
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3a_pilot_protocol"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "c6cbb6b7a7dc4dfe7ca3fa6ea0bcf34d7f0612c0"

INPUT_ALL_ROWS_NAME = "modeling_all_rows_stage124_gate_b.csv"
INPUT_PAIRS_NAME = "modeling_one_year_ahead_stage124_gate_b.csv"

EXPECTED_INPUT_ALL_ROWS_SHA256 = (
    "f6b6bc41cbe757d19d4397ffc5898629d0fca8ab0480351f75040a71d7ce7376"
)
EXPECTED_INPUT_PAIRS_SHA256 = (
    "9743c49337c66a3699bce34dfd02a151e34f48f0717f225ad487fe1487031d05"
)

SRC_REL = "project/src/stage125_part3a_pilot_protocol.py"
TEST_REL = "project/tests/test_stage125_part3a_pilot_protocol.py"

FROZEN_MANIFEST_PATHS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
    "project/stage125/metadata_and_hashes_stage125_part1.json",
    "project/stage125/metadata_and_hashes_stage125_part2.json",
)

EXPECTED_INVARIANTS = {
    "all_rows": 1331,
    "pairs": 1200,
    "unique_tickers_pairs": 130,
    "predictor_keys_in_all_rows": 1200,
    "target_keys_in_all_rows": 1200,
}

EXPECTED_ELIGIBILITY = {
    "rule_a_eligible_pairs": 1013,
    "rule_a_positive": 81,
    "rule_a_negative": 932,
    "rule_a_unknown": 0,
    "rule_b_eligible_pairs": 994,
    "rule_b_positive": 80,
    "rule_b_negative": 914,
    "rule_b_unknown": 0,
}

ELIGIBILITY_SNAPSHOT_COLUMNS = (
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "pair_final_eligible_main_gate_b_primary",
    "pair_final_eligible_main_gate_b_robustness",
)

MODELING_ARTIFACT_PATTERNS = (
    "shap", "smote", "calibration", "temporal_split",
    "predictions", "model_results",
)
MODELING_ARTIFACT_EXTENSIONS = (".joblib", ".npz", ".pickle", ".pkl", ".model")

PART3B_FORBIDDEN_EXACT = (
    "project/run_stage125_part3b.py",
)
PART3B_FORBIDDEN_PREFIXES = (
    "project/src/stage125_part3b",
    "project/tests/test_stage125_part3b",
    "project/stage125/part3b/",
)
PART3B_FORBIDDEN_GLOBS = (
    "part3_evidence_",
    "part3b_evidence_",
    "part3_captured_",
    "part3_raw_snapshot_",
)
PART3B_ALLOWED_EXACT = (
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json",
)
PART3B0_ALLOWED_EXACT = (
    "project/src/stage125_part3b0_evidence_readiness.py",
    "project/tests/test_stage125_part3b0_evidence_readiness.py",
    "project/run_stage125_part3b0.py",
    "project/stage125/part3b0_evidence_capture_contract_stage125.json",
    "project/stage125/part3b0_evidence_manifest_template_stage125.csv",
    "project/stage125/part3b0_gate_result_template_stage125.csv",
    "project/stage125/part3b0_immutable_cache_contract_stage125.json",
    "project/stage125/part3b0_network_denial_contract_stage125.json",
    "project/stage125/README_STAGE125_PART3B0_EVIDENCE_READINESS.md",
    "project/stage125/stage125_part3b0_evidence_readiness_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b0.json",
)

REGISTERED_CANDIDATES = (
    {"candidate_id": "cand_m2_equity_return_window", "block": "M2",
     "variable_name": "equity_return_window", "source_id": "src_m2_tsetmc_market"},
    {"candidate_id": "cand_m2_realized_volatility", "block": "M2",
     "variable_name": "realized_volatility", "source_id": "src_m2_tsetmc_market"},
    {"candidate_id": "cand_m2_amihud_illiquidity", "block": "M2",
     "variable_name": "amihud_illiquidity", "source_id": "src_m2_tsetmc_market"},
    {"candidate_id": "cand_m3_cpi_inflation", "block": "M3",
     "variable_name": "cpi_inflation", "source_id": "src_m3_cbi_macro"},
    {"candidate_id": "cand_m3_fx_change_official", "block": "M3",
     "variable_name": "fx_change_official", "source_id": "src_m3_cbi_macro"},
    {"candidate_id": "cand_m3_policy_financing_rate", "block": "M3",
     "variable_name": "policy_financing_rate", "source_id": "src_m3_cbi_macro"},
    {"candidate_id": "cand_m4_audit_opinion_type", "block": "M4",
     "variable_name": "audit_opinion_type", "source_id": "src_m4_codal_audit"},
    {"candidate_id": "cand_m4_going_concern_flag", "block": "M4",
     "variable_name": "going_concern_flag", "source_id": "src_m4_codal_audit"},
    {"candidate_id": "cand_m4_audit_lag_days", "block": "M4",
     "variable_name": "audit_lag_days", "source_id": "src_m4_codal_audit"},
    {"candidate_id": "cand_m4_board_size", "block": "M4",
     "variable_name": "board_size", "source_id": "src_m4_codal_governance"},
)

RESEARCH_DESIGN_ONLY = (
    {"candidate_id": "rd_m2_volume_turnover", "block": "M2",
     "variable_name": "volume_turnover", "source_id": ""},
    {"candidate_id": "rd_m2_no_trade_days", "block": "M2",
     "variable_name": "no_trade_days", "source_id": ""},
    {"candidate_id": "rd_m2_beta", "block": "M2",
     "variable_name": "beta", "source_id": ""},
    {"candidate_id": "rd_m2_drawdown", "block": "M2",
     "variable_name": "drawdown", "source_id": ""},
    {"candidate_id": "rd_m2_market_index", "block": "M2",
     "variable_name": "market_index", "source_id": ""},
    {"candidate_id": "rd_m3_liquidity_growth", "block": "M3",
     "variable_name": "liquidity_growth", "source_id": ""},
    {"candidate_id": "rd_m3_gdp_production_index", "block": "M3",
     "variable_name": "gdp_production_index", "source_id": ""},
    {"candidate_id": "rd_m3_oil_price", "block": "M3",
     "variable_name": "oil_price", "source_id": ""},
    {"candidate_id": "rd_m4_auditor_change", "block": "M4",
     "variable_name": "auditor_change", "source_id": ""},
    {"candidate_id": "rd_m4_non_executive_ratio", "block": "M4",
     "variable_name": "non_executive_ratio", "source_id": ""},
    {"candidate_id": "rd_m4_ownership_concentration", "block": "M4",
     "variable_name": "ownership_concentration", "source_id": ""},
    {"candidate_id": "rd_m4_audit_committee_size", "block": "M4",
     "variable_name": "audit_committee_size", "source_id": ""},
)

OUT_OF_SCOPE_LOCKED = (
    {"candidate_id": "oos_m5_persian_text", "block": "M5",
     "variable_name": "persian_text_modeling", "source_id": ""},
    {"candidate_id": "oos_order_book", "block": "M2",
     "variable_name": "order_book_bid_ask", "source_id": ""},
    {"candidate_id": "oos_free_market_fx", "block": "M3",
     "variable_name": "free_market_fx_non_reproducible", "source_id": ""},
    {"candidate_id": "oos_director_network", "block": "M4",
     "variable_name": "director_biography_network", "source_id": ""},
    {"candidate_id": "oos_interlocking", "block": "M4",
     "variable_name": "director_interlocking", "source_id": ""},
    {"candidate_id": "oos_social_news_esg", "block": "M4",
     "variable_name": "social_news_esg", "source_id": ""},
)

F_CANDIDATE_INVENTORY = "part3_candidate_inventory_stage125.csv"
F_ACCESSIBILITY_RUBRIC = "accessibility_scoring_rubric_stage125_part3a.json"
F_GATE_PROTOCOL = "part3_gate_decision_protocol_stage125.csv"
F_SAMPLING_SUMMARY = "part3_sampling_frame_summary_stage125.json"
F_SAMPLING_BY_YEAR = "part3_sampling_frame_by_target_year_stage125.csv"
F_PILOT_OPTIONS = "part3_pilot_sampling_options_stage125.csv"
F_EVIDENCE_SCHEMA = "part3_source_evidence_manifest_schema_stage125.json"
F_QC = "stage125_part3a_pilot_protocol_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3a.json"
F_README = "README_STAGE125_PART3A_PILOT_PROTOCOL.md"

CONTENT_FILES = (
    F_CANDIDATE_INVENTORY, F_ACCESSIBILITY_RUBRIC, F_GATE_PROTOCOL,
    F_SAMPLING_SUMMARY, F_SAMPLING_BY_YEAR, F_PILOT_OPTIONS,
    F_EVIDENCE_SCHEMA, F_README,
)

_CANDIDATE_HEADER = [
    "candidate_id", "block", "variable_name", "source_id",
    "dictionary_status", "registry_status", "research_design_status",
    "candidate_scope_status", "evidence_status", "accessibility_score",
    "gate_status", "decision_status", "notes",
]

_GATE_HEADER = [
    "gate_id", "gate_name", "gate_category", "lock_status",
    "threshold_value", "approval_status", "description", "notes",
]

_PILOT_OPTIONS_HEADER = [
    "option_id", "proposed_sample_size", "proposed_class_allocation",
    "allocation_by_target_year", "proposed_temporal_allocation",
    "proposed_ticker_industry_diversity_rule",
    "rule_a_pool_positive_total", "rule_a_pool_negative_total",
    "expected_document_api_workload_m2", "expected_document_api_workload_m3",
    "expected_document_api_workload_m4", "advantages", "limitations",
    "sampling_purpose", "population_representative", "modeling_sample",
    "eligibility_impact", "status",
]

_PILOT_METHODOLOGY_SCOPE = {
    "sampling_purpose": "event_enriched_accessibility_coverage_pilot",
    "population_representative": "false",
    "modeling_sample": "false",
    "eligibility_impact": "none_protocol_only",
}

_PILOT_METHODOLOGY_DISCLAIMER = (
    "Not population-representative; intended only for accessibility, "
    "provenance, and coverage testing; must not be used to estimate "
    "population class prevalence or report model performance; does not "
    "alter the final modeling sample or eligibility."
)

_SAMPLING_BY_YEAR_HEADER = [
    "target_year", "total_pairs", "positive_count", "negative_count",
    "unknown_count", "rule_a_eligible_pairs", "rule_a_positive",
    "rule_a_negative", "rule_a_unknown", "rule_b_eligible_pairs",
    "rule_b_positive", "rule_b_negative", "rule_b_unknown",
    "industry_present_pairs", "industry_missing_pairs",
]


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3A."""


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


def _git_tracked(repo_root: str) -> set[str]:
    out = _git(repo_root, "ls-files")
    return set(out.splitlines()) if out else set()


def _git_ignored(repo_root: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "check-ignore", "-q", "--", path],
        capture_output=True,
    )
    return proc.returncode == 0


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Serialization helpers (deterministic)
# --------------------------------------------------------------------------- #

def _json_str(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in header})
    return buf.getvalue()


def _target_class(val: str) -> str:
    v = str(val).strip()
    if v == "1.0":
        return "positive"
    if v == "0.0":
        return "negative"
    if v == "":
        return "unknown"
    return "unknown"


# --------------------------------------------------------------------------- #
# Input verification (fail-closed, read-only)
# --------------------------------------------------------------------------- #

def load_inputs(
    all_rows_path: Path | None,
    pairs_path: Path | None,
) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    if all_rows_path is None or not Path(all_rows_path).is_file():
        raise QCFail(
            f"input {INPUT_ALL_ROWS_NAME} not found. No data is downloaded "
            "(fail-closed)."
        )
    if pairs_path is None or not Path(pairs_path).is_file():
        raise QCFail(
            f"input {INPUT_PAIRS_NAME} not found. No data is downloaded "
            "(fail-closed)."
        )
    sha_all = sha256_file(all_rows_path)
    if sha_all != EXPECTED_INPUT_ALL_ROWS_SHA256:
        raise QCFail(
            f"input {INPUT_ALL_ROWS_NAME} SHA-256 mismatch: expected "
            f"{EXPECTED_INPUT_ALL_ROWS_SHA256}, got {sha_all}"
        )
    sha_pairs = sha256_file(pairs_path)
    if sha_pairs != EXPECTED_INPUT_PAIRS_SHA256:
        raise QCFail(
            f"input {INPUT_PAIRS_NAME} SHA-256 mismatch: expected "
            f"{EXPECTED_INPUT_PAIRS_SHA256}, got {sha_pairs}"
        )
    df_all = pd.read_csv(all_rows_path, encoding="utf-8-sig", dtype=str,
                         keep_default_na=False)
    df_pairs = pd.read_csv(pairs_path, encoding="utf-8-sig", dtype=str,
                           keep_default_na=False)
    return df_all, df_pairs, sha_all, sha_pairs


def compute_invariants(df_all: pd.DataFrame, df_pairs: pd.DataFrame) -> dict:
    counts: dict[str, int] = {}
    counts["all_rows"] = int(len(df_all))
    counts["pairs"] = int(len(df_pairs))
    counts["unique_tickers_pairs"] = int(df_pairs["ticker"].nunique())
    all_keys = set(df_all["row_key"])
    pred_keys = set(df_pairs["predictor_row_key_t"])
    target_keys = set(df_pairs["target_row_key_t_plus_1"])
    counts["predictor_keys_in_all_rows"] = int(len(pred_keys & all_keys))
    counts["target_keys_in_all_rows"] = int(len(target_keys & all_keys))
    return counts


def check_invariants(counts: dict) -> list[str]:
    errs = []
    for key, expected in EXPECTED_INVARIANTS.items():
        actual = counts.get(key)
        if actual != expected:
            errs.append(f"{key}: expected {expected}, got {actual}")
    return errs


def verify_baseline_commit(repo_root: str) -> None:
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, "HEAD"):
        raise QCFail(
            f"expected baseline commit {EXPECTED_BASELINE_COMMIT} is not an "
            "ancestor of HEAD (fail-closed)"
        )
    origin_main = _git(repo_root, "rev-parse", "origin/main")
    if origin_main and origin_main != EXPECTED_BASELINE_COMMIT:
        mb = _git(repo_root, "merge-base", "origin/main", EXPECTED_BASELINE_COMMIT)
        if mb != EXPECTED_BASELINE_COMMIT:
            raise QCFail(
                f"origin/main ({origin_main}) does not contain expected "
                f"baseline {EXPECTED_BASELINE_COMMIT}"
            )


# --------------------------------------------------------------------------- #
# Fail-closed guardrails (evidence-based)
# --------------------------------------------------------------------------- #

class NetworkSentinel:
    """Count outbound socket connect attempts during Part 3A execution."""

    def __init__(self) -> None:
        self.calls_attempted = 0
        self._orig_connect = socket.socket.connect

    def _blocked_connect(self, _sock, *args, **kwargs):
        self.calls_attempted += 1
        raise OSError(f"network blocked by Part 3A sentinel: {args!r}")

    def install(self) -> None:
        socket.socket.connect = self._blocked_connect  # type: ignore[method-assign]

    def restore(self) -> None:
        socket.socket.connect = self._orig_connect  # type: ignore[method-assign]


@contextmanager
def network_sentinel() -> Iterator[NetworkSentinel]:
    sentinel = NetworkSentinel()
    sentinel.install()
    try:
        yield sentinel
    finally:
        sentinel.restore()


def scan_for_modeling_artifacts(project_dir: Path) -> dict:
    """Reuse Stage124 guardrail semantics for modeling-artifact detection."""
    modeling_paths = [
        project_dir / "outputs" / "stage_modeling" / "run_manifest.json",
    ]
    path_hits = [str(p.relative_to(project_dir.parent))
                 for p in modeling_paths if p.is_file()]
    artifact_hits: list[str] = []
    scan_dirs = [
        project_dir / "stage124" / "gate_b_final",
        project_dir / "stage125",
    ]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for f in scan_dir.rglob("*"):
            if not f.is_file():
                continue
            low = f.name.lower()
            if low.startswith("modeling_") and low.endswith(".csv"):
                continue
            rel = str(f.relative_to(project_dir.parent))
            for ext in MODELING_ARTIFACT_EXTENSIONS:
                if low.endswith(ext):
                    artifact_hits.append(rel)
                    break
            else:
                for pat in MODELING_ARTIFACT_PATTERNS:
                    if pat in low:
                        artifact_hits.append(rel)
                        break
    return {
        "path_hits": sorted(path_hits),
        "artifact_hits": sorted(artifact_hits),
        "no_modeling": len(path_hits) == 0 and len(artifact_hits) == 0,
    }


def _part3b0_allowed(rel: str, basename: str) -> bool:
    del basename  # exact-path allowlist only; no prefix/directory-wide bypass
    return rel in PART3B0_ALLOWED_EXACT


def scan_for_part3b_artifacts(repo_root: Path) -> dict:
    """Detect Part 3B runner/implementation/captured evidence (schema allowed)."""
    hits: list[str] = []
    for rel in PART3B_FORBIDDEN_EXACT:
        if (repo_root / rel).exists():
            hits.append(rel)
    stage125 = repo_root / "project" / "stage125"
    if stage125.is_dir():
        for f in stage125.rglob("*"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(repo_root))
            if rel in PART3B_ALLOWED_EXACT:
                continue
            if _part3b0_allowed(rel, f.name):
                continue
            low = f.name.lower()
            if any(low.startswith(prefix) for prefix in PART3B_FORBIDDEN_GLOBS):
                hits.append(rel)
    src = repo_root / "project" / "src"
    if src.is_dir():
        for f in src.iterdir():
            if not f.is_file():
                continue
            rel = str(f.relative_to(repo_root))
            if _part3b0_allowed(rel, f.name):
                continue
            if any(rel.startswith(p) for p in PART3B_FORBIDDEN_PREFIXES):
                hits.append(rel)
    tests = repo_root / "project" / "tests"
    if tests.is_dir():
        for f in tests.iterdir():
            if not f.is_file():
                continue
            rel = str(f.relative_to(repo_root))
            if _part3b0_allowed(rel, f.name):
                continue
            if any(rel.startswith(p) for p in PART3B_FORBIDDEN_PREFIXES):
                hits.append(rel)
    for prefix in PART3B_FORBIDDEN_PREFIXES:
        if (repo_root / prefix).is_dir():
            for f in (repo_root / prefix).rglob("*"):
                if f.is_file():
                    hits.append(str(f.relative_to(repo_root)))
    return {"hits": sorted(set(hits)), "no_part3b": len(hits) == 0}


def eligibility_snapshot(df_pairs: pd.DataFrame) -> str:
    """Deterministic fingerprint of frozen pair keys and eligibility fields."""
    cols = [c for c in ELIGIBILITY_SNAPSHOT_COLUMNS if c in df_pairs.columns]
    sub = df_pairs[cols].copy()
    sub = sub.sort_values(cols[:2]).reset_index(drop=True)
    return sha256_bytes(sub.to_csv(index=False).encode("utf-8"))


def compute_eligibility_counts_with_targets(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame,
) -> dict:
    merged = _merge_pairs_targets(df_all, df_pairs)
    ra = merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"]
    rb = merged[merged["pair_final_eligible_main_gate_b_robustness"] == "1"]

    def _class_counts(sub: pd.DataFrame) -> tuple[int, int, int]:
        pos = int(sum(sub["FD_target_main"].map(_target_class) == "positive"))
        neg = int(sum(sub["FD_target_main"].map(_target_class) == "negative"))
        unk = int(sum(sub["FD_target_main"].map(_target_class) == "unknown"))
        return pos, neg, unk

    ra_pos, ra_neg, ra_unk = _class_counts(ra)
    rb_pos, rb_neg, rb_unk = _class_counts(rb)
    return {
        "rule_a_eligible_pairs": int(len(ra)),
        "rule_a_positive": ra_pos,
        "rule_a_negative": ra_neg,
        "rule_a_unknown": ra_unk,
        "rule_b_eligible_pairs": int(len(rb)),
        "rule_b_positive": rb_pos,
        "rule_b_negative": rb_neg,
        "rule_b_unknown": rb_unk,
        "pair_count": int(len(df_pairs)),
        "unique_predictor_keys": int(df_pairs["predictor_row_key_t"].nunique()),
        "unique_target_keys": int(df_pairs["target_row_key_t_plus_1"].nunique()),
        "snapshot_sha256": eligibility_snapshot(df_pairs),
    }


def run_guardrails(
    project_dir: Path,
    repo_root: Path,
    df_all: pd.DataFrame,
    df_pairs: pd.DataFrame,
    network_calls: int,
) -> dict:
    modeling = scan_for_modeling_artifacts(project_dir)
    part3b = scan_for_part3b_artifacts(repo_root)
    eligibility = compute_eligibility_counts_with_targets(df_all, df_pairs)
    elig_mismatches = []
    for key in (
        "rule_a_eligible_pairs", "rule_a_positive", "rule_a_negative",
        "rule_a_unknown", "rule_b_eligible_pairs", "rule_b_positive",
        "rule_b_negative", "rule_b_unknown", "pair_count",
        "unique_predictor_keys", "unique_target_keys",
    ):
        expected = EXPECTED_ELIGIBILITY.get(key, EXPECTED_INVARIANTS.get(key))
        if expected is not None and eligibility.get(key) != expected:
            elig_mismatches.append(
                f"{key}: expected {expected}, got {eligibility.get(key)}"
            )
    return {
        "modeling": modeling,
        "part3b": part3b,
        "eligibility": eligibility,
        "eligibility_mismatches": elig_mismatches,
        "eligibility_unchanged": not elig_mismatches,
        "network_calls_attempted": network_calls,
        "no_network_calls": network_calls == 0,
    }


# --------------------------------------------------------------------------- #
# Candidate inventory
# --------------------------------------------------------------------------- #

def build_candidate_inventory_rows() -> list[dict]:
    rows: list[dict] = []
    for c in REGISTERED_CANDIDATES:
        rows.append({
            "candidate_id": c["candidate_id"],
            "block": c["block"],
            "variable_name": c["variable_name"],
            "source_id": c["source_id"],
            "dictionary_status": "registered_in_data_dictionary",
            "registry_status": "registered_in_source_registry",
            "research_design_status": "registered_in_research_design",
            "candidate_scope_status": "registered_candidate",
            "evidence_status": "unresolved",
            "accessibility_score": "",
            "gate_status": "unresolved",
            "decision_status": "pending_part3b_evidence",
            "notes": (
                "Registered candidate from Stage125 Part 1 contracts. "
                "No evidence collected in Part 3A; score and gates unresolved."
            ),
        })
    rows.append({
        "candidate_id": "src_m3_sci_macro_registry",
        "block": "M3",
        "variable_name": "",
        "source_id": "src_m3_sci_macro",
        "dictionary_status": "not_registered",
        "registry_status": "registry_only_not_registered",
        "research_design_status": "mentioned_in_research_design_narrative",
        "candidate_scope_status": "registry_only_not_registered",
        "evidence_status": "unresolved",
        "accessibility_score": "",
        "gate_status": "unresolved",
        "decision_status": "registry_only_not_registered",
        "notes": (
            "Source exists in source_registry only; NOT promoted to a "
            "registered candidate variable."
        ),
    })
    for c in RESEARCH_DESIGN_ONLY:
        rows.append({
            "candidate_id": c["candidate_id"],
            "block": c["block"],
            "variable_name": c["variable_name"],
            "source_id": c["source_id"],
            "dictionary_status": "not_registered",
            "registry_status": "not_registered",
            "research_design_status": "research_design_only_not_registered",
            "candidate_scope_status": "research_design_only_not_registered",
            "evidence_status": "unresolved",
            "accessibility_score": "",
            "gate_status": "unresolved",
            "decision_status": "research_design_only_not_registered",
            "notes": (
                "Mentioned in STAGE125_RESEARCH_DESIGN narrative only; "
                "not registered in data_dictionary or source_registry."
            ),
        })
    for c in OUT_OF_SCOPE_LOCKED:
        rows.append({
            "candidate_id": c["candidate_id"],
            "block": c["block"],
            "variable_name": c["variable_name"],
            "source_id": c["source_id"],
            "dictionary_status": "not_registered",
            "registry_status": "not_registered",
            "research_design_status": "out_of_scope_locked",
            "candidate_scope_status": "out_of_scope_locked",
            "evidence_status": "unresolved",
            "accessibility_score": "",
            "gate_status": "unresolved",
            "decision_status": "out_of_scope_locked",
            "notes": "Firm out-of-scope per STAGE125_RESEARCH_DESIGN section 5.",
        })
    rows.sort(key=lambda r: r["candidate_id"])
    return rows


# --------------------------------------------------------------------------- #
# Accessibility rubric
# --------------------------------------------------------------------------- #

def build_accessibility_rubric() -> dict:
    return {
        "rubric_version": "stage125_part3a_v1",
        "stage": CURRENT_STAGE,
        "approval_status": "pending_user_approval",
        "applied_to_sources": False,
        "label": "proposed, not yet applied",
        "scoring_rules": {
            "missing_evidence": "null_or_unresolved_never_zero",
            "score_below_3": "hard_drop",
            "score_equals_3": "pilot_permission_only_not_automatic_admission",
            "score_4_or_5": "must_still_pass_every_other_gate",
            "no_memory_or_reputation_scoring": True,
            "every_score_requires_captured_evidence_and_provenance": True,
        },
        "score_definitions": {
            "0": {
                "label": "proposed, not yet applied",
                "description": (
                    "Source inaccessible or unusable; no reproducible retrieval "
                    "path. Hard drop if ever scored."
                ),
            },
            "1": {
                "label": "proposed, not yet applied",
                "description": (
                    "Marginal accessibility; manual-only, unstable, or "
                    "non-reproducible access. Hard drop if ever scored."
                ),
            },
            "2": {
                "label": "proposed, not yet applied",
                "description": (
                    "Limited accessibility; significant barriers to systematic "
                    "retrieval. Hard drop if ever scored."
                ),
            },
            "3": {
                "label": "proposed, not yet applied",
                "description": (
                    "Pilot-eligible only: systematic retrieval is plausible but "
                    "coverage/quality unproven. Does NOT automatically admit "
                    "to main analysis."
                ),
            },
            "4": {
                "label": "proposed, not yet applied",
                "description": (
                    "Good accessibility with documented API/portal and "
                    "reproducible retrieval; must still pass all other Gates."
                ),
            },
            "5": {
                "label": "proposed, not yet applied",
                "description": (
                    "Excellent accessibility: authoritative, fully reproducible, "
                    "machine-readable or reliably structured; must still pass "
                    "all other Gates."
                ),
            },
        },
    }


# --------------------------------------------------------------------------- #
# Gate decision protocol
# --------------------------------------------------------------------------- #

def build_gate_protocol_rows() -> list[dict]:
    locked = [
        ("G01", "accessibility_score_gte_3", "accessibility",
         "accessibility score >= 3 required; score < 3 is hard drop"),
        ("G02", "authoritative_source_required", "provenance",
         "Source must be valid, citable, and authoritative"),
        ("G03", "reproducibility_required", "provenance",
         "Retrieval path must be reproducible with captured evidence"),
        ("G04", "published_or_available_at_verified", "temporal",
         "published_at or available_at must be verified from evidence"),
        ("G05", "extraction_adjustment_join_error_controlled", "quality",
         "Extraction, adjustment, unit, calendar, and join error controlled"),
        ("G06", "missing_availability_means_unavailable", "temporal",
         "Missing availability time means unavailable; never inferred"),
        ("G07", "no_future_or_target_year_information", "leakage",
         "No future or target-year information at prediction time"),
        ("G08", "all_gates_must_pass", "composite",
         "All Gates must pass; one failure is sufficient for rejection"),
    ]
    pending = [
        ("G09", "minimum_company_year_coverage", "coverage",
         "Numeric minimum company-year coverage threshold"),
        ("G10", "minimum_common_sample_coverage", "coverage",
         "Numeric minimum common-sample coverage threshold"),
        ("G11", "minimum_positive_event_count_per_fold", "events",
         "Minimum positive-event count per proposed temporal fold"),
        ("G12", "minimum_negative_event_count_per_fold", "events",
         "Minimum negative-event count per proposed temporal fold"),
        ("G13", "final_pilot_sample_size", "sampling",
         "Final pilot sample size selection"),
        ("G14", "final_pilot_sampling_allocation", "sampling",
         "Final pilot class/temporal/ticker allocation"),
    ]
    rows: list[dict] = []
    for gid, name, cat, desc in locked:
        rows.append({
            "gate_id": gid,
            "gate_name": name,
            "gate_category": cat,
            "lock_status": "locked",
            "threshold_value": "",
            "approval_status": "locked_in_protocol",
            "description": desc,
            "notes": "Locked in Part 3A protocol; no threshold invented.",
        })
    for gid, name, cat, desc in pending:
        rows.append({
            "gate_id": gid,
            "gate_name": name,
            "gate_category": cat,
            "lock_status": "pending_user_approval",
            "threshold_value": "",
            "approval_status": "pending_user_approval",
            "description": desc,
            "notes": (
                "Threshold not defined in Part 3A; requires explicit user "
                "approval before application."
            ),
        })
    return rows


# --------------------------------------------------------------------------- #
# Sampling frame (from frozen data only)
# --------------------------------------------------------------------------- #

def _merge_pairs_targets(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame,
) -> pd.DataFrame:
    return df_pairs.merge(
        df_all[["row_key", "FD_target_main", "industry", "fiscal_year"]],
        left_on="target_row_key_t_plus_1",
        right_on="row_key",
        how="left",
        suffixes=("", "_target"),
    )


def build_sampling_by_year_rows(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame,
) -> list[dict]:
    merged = _merge_pairs_targets(df_all, df_pairs)
    rows: list[dict] = []
    for ty in sorted(merged["target_year"].unique()):
        all_sub = merged[merged["target_year"] == ty]
        ra_sub = all_sub[all_sub["pair_final_eligible_main_gate_b_primary"] == "1"]
        rb_sub = all_sub[all_sub["pair_final_eligible_main_gate_b_robustness"] == "1"]

        def _class_counts(sub: pd.DataFrame) -> tuple[int, int, int]:
            pos = int(sum(sub["FD_target_main"].map(_target_class) == "positive"))
            neg = int(sum(sub["FD_target_main"].map(_target_class) == "negative"))
            unk = int(sum(sub["FD_target_main"].map(_target_class) == "unknown"))
            return pos, neg, unk

        pos, neg, unk = _class_counts(all_sub)
        ra_pos, ra_neg, ra_unk = _class_counts(ra_sub)
        rb_pos, rb_neg, rb_unk = _class_counts(rb_sub)
        ind_present = int(sum(all_sub["industry"].fillna("").str.strip() != ""))
        ind_missing = int(len(all_sub) - ind_present)
        rows.append({
            "target_year": ty,
            "total_pairs": len(all_sub),
            "positive_count": pos,
            "negative_count": neg,
            "unknown_count": unk,
            "rule_a_eligible_pairs": len(ra_sub),
            "rule_a_positive": ra_pos,
            "rule_a_negative": ra_neg,
            "rule_a_unknown": ra_unk,
            "rule_b_eligible_pairs": len(rb_sub),
            "rule_b_positive": rb_pos,
            "rule_b_negative": rb_neg,
            "rule_b_unknown": rb_unk,
            "industry_present_pairs": ind_present,
            "industry_missing_pairs": ind_missing,
        })
    return rows


def build_sampling_summary(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame, counts: dict,
) -> dict:
    merged = _merge_pairs_targets(df_all, df_pairs)
    ra = merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"]
    rb = merged[merged["pair_final_eligible_main_gate_b_robustness"] == "1"]

    def _totals(sub: pd.DataFrame) -> dict:
        return {
            "pairs": int(len(sub)),
            "positive": int(sum(sub["FD_target_main"].map(_target_class) == "positive")),
            "negative": int(sum(sub["FD_target_main"].map(_target_class) == "negative")),
            "unknown": int(sum(sub["FD_target_main"].map(_target_class) == "unknown")),
            "unique_tickers": int(sub["ticker"].nunique()),
            "industry_present": int(
                sum(sub["industry"].fillna("").str.strip() != "")
            ),
            "industry_missing": int(
                sum(sub["industry"].fillna("").str.strip() == "")
            ),
            "unique_industries": int(
                sub.loc[sub["industry"].fillna("").str.strip() != "", "industry"].nunique()
            ),
        }

    fiscal_years = sorted(df_all["fiscal_year"].unique())
    rows_per_fy = {
        fy: int(sum(df_all["fiscal_year"] == fy)) for fy in fiscal_years
    }
    return {
        "frame_version": "stage125_part3a_v1",
        "stage": CURRENT_STAGE,
        "total_company_year_rows": counts["all_rows"],
        "total_pairs": counts["pairs"],
        "unique_tickers": counts["unique_tickers_pairs"],
        "target_class_all_pairs": _totals(merged),
        "rule_a_primary_sample": _totals(ra),
        "rule_b_listing_robustness_sample": _totals(rb),
        "fiscal_year_coverage": {
            "fiscal_years_present": fiscal_years,
            "rows_per_fiscal_year": rows_per_fy,
        },
        "target_year_coverage": {
            "target_years_present": sorted(merged["target_year"].unique()),
            "pairs_per_target_year": {
                ty: int(sum(merged["target_year"] == ty))
                for ty in sorted(merged["target_year"].unique())
            },
        },
        "industry_summary_all_rows": {
            "industry_present_rows": int(
                sum(df_all["industry"].fillna("").str.strip() != "")
            ),
            "industry_missing_rows": int(
                sum(df_all["industry"].fillna("").str.strip() == "")
            ),
            "unique_industries": int(
                df_all.loc[
                    df_all["industry"].fillna("").str.strip() != "", "industry"
                ].nunique()
            ),
        },
        "pilot_design_notes": (
            "Counts derived from frozen Stage124 Gate B inputs only. "
            "Final temporal CV and locked final test belong to Part 4. "
            "No coverage or event thresholds applied in Part 3A."
        ),
    }


# --------------------------------------------------------------------------- #
# Pilot sampling options (deterministic; frozen identifiers only)
# --------------------------------------------------------------------------- #

def _deterministic_pilot_pairs(
    df_all: pd.DataFrame,
    df_pairs: pd.DataFrame,
    max_pos_per_year: int | None,
    per_year_quota: int,
) -> tuple[list[dict], dict[str, dict[str, int]]]:
    """Select pairs deterministically from frozen identifiers only."""
    merged = _merge_pairs_targets(df_all, df_pairs)
    ra = merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"].copy()
    ra["_class"] = ra["FD_target_main"].map(_target_class)
    ra = ra.sort_values(
        ["target_year", "_class", "ticker", "predictor_row_key_t"],
        ascending=[True, True, True, True],
    )
    selected: list[dict] = []
    used_keys: set[str] = set()
    year_allocation: dict[str, dict[str, int]] = {}

    for ty in sorted(ra["target_year"].unique()):
        sub = ra[ra["target_year"] == ty]
        pos = sub[sub["_class"] == "positive"]
        neg = sub[sub["_class"] == "negative"]
        unk = sub[sub["_class"] == "unknown"]
        picked: list[pd.Series] = []
        pos_cap = len(pos) if max_pos_per_year is None else max_pos_per_year

        for _, row in pos.iterrows():
            if len(picked) >= per_year_quota:
                break
            if sum(1 for p in picked if p["_class"] == "positive") >= pos_cap:
                break
            key = row["predictor_row_key_t"]
            if key in used_keys:
                continue
            picked.append(row)
            used_keys.add(key)

        for _, row in neg.iterrows():
            if len(picked) >= per_year_quota:
                break
            key = row["predictor_row_key_t"]
            if key in used_keys:
                continue
            picked.append(row)
            used_keys.add(key)

        if len(picked) < per_year_quota:
            for _, row in unk.iterrows():
                if len(picked) >= per_year_quota:
                    break
                key = row["predictor_row_key_t"]
                if key in used_keys:
                    continue
                picked.append(row)
                used_keys.add(key)

        year_allocation[str(ty)] = {
            "positive": sum(1 for p in picked if p["_class"] == "positive"),
            "negative": sum(1 for p in picked if p["_class"] == "negative"),
            "unknown": sum(1 for p in picked if p["_class"] == "unknown"),
        }
        for row in picked:
            selected.append({
                "predictor_row_key_t": row["predictor_row_key_t"],
                "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
                "ticker": row["ticker"],
                "target_year": row["target_year"],
                "class": row["_class"],
                "industry": row["industry"],
            })
    return selected, year_allocation


def _format_year_allocation(year_allocation: dict[str, dict[str, int]]) -> str:
    parts = []
    for ty in sorted(year_allocation):
        a = year_allocation[ty]
        parts.append(
            f"{ty}:pos={a['positive']},neg={a['negative']},unk={a['unknown']}"
        )
    return ";".join(parts)


def build_pilot_sampling_options(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame,
) -> list[dict]:
    merged = _merge_pairs_targets(df_all, df_pairs)
    ra = merged[merged["pair_final_eligible_main_gate_b_primary"] == "1"]
    pool_pos = int(sum(ra["FD_target_main"].map(_target_class) == "positive"))
    pool_neg = int(sum(ra["FD_target_main"].map(_target_class) == "negative"))

    options_spec = [
        (
            "pilot_option_compact",
            2,
            4,
            "Compact event-enriched accessibility pilot: 4 Rule-A pairs per "
            "target year (2 positive where available + 2 negative); "
            "deliberately oversamples positive distress events relative to "
            f"Rule A pool prevalence (~8%). {_PILOT_METHODOLOGY_DISCLAIMER}",
        ),
        (
            "pilot_option_event_enriched",
            4,
            8,
            "Event-enriched temporally stratified accessibility pilot: 8 "
            "Rule-A pairs per target year (up to 4 positive where available + "
            "negatives); deliberately oversamples positive distress events "
            "(~48.75% positive in this option vs ~8% in the Rule A pool); "
            "temporally stratified across target years. "
            f"{_PILOT_METHODOLOGY_DISCLAIMER}",
        ),
        (
            "pilot_option_extended",
            None,
            16,
            "Extended event-enriched accessibility pilot: 16 Rule-A pairs per "
            "target year (all available positives per year up to quota + "
            "negatives); uses the full 81 Rule A positives where year supply "
            "allows; deliberately event-enriched (not population-"
            f"representative). {_PILOT_METHODOLOGY_DISCLAIMER}",
        ),
    ]
    rows: list[dict] = []
    for opt_id, max_pos, per_year, temporal_desc in options_spec:
        selected, year_allocation = _deterministic_pilot_pairs(
            df_all, df_pairs, max_pos, per_year,
        )
        n = len(selected)
        pos_n = sum(1 for s in selected if s["class"] == "positive")
        neg_n = sum(1 for s in selected if s["class"] == "negative")
        unk_n = sum(1 for s in selected if s["class"] == "unknown")
        unique_tickers = len({s["ticker"] for s in selected})
        unique_industries = len({
            s["industry"] for s in selected if str(s["industry"]).strip()
        })
        company_years = len({s["predictor_row_key_t"] for s in selected})
        target_years = len({s["target_year"] for s in selected})
        rows.append({
            "option_id": opt_id,
            "proposed_sample_size": n,
            "proposed_class_allocation": (
                f"positive={pos_n};negative={neg_n};unknown={unk_n}"
            ),
            "allocation_by_target_year": _format_year_allocation(year_allocation),
            "proposed_temporal_allocation": (
                f"{per_year} pairs per target year (Rule A eligible); "
                f"{temporal_desc}"
            ),
            "proposed_ticker_industry_diversity_rule": (
                f"deterministic without replacement by predictor_row_key_t; "
                f"unique_tickers={unique_tickers}; "
                f"unique_industries={unique_industries}"
            ),
            "rule_a_pool_positive_total": pool_pos,
            "rule_a_pool_negative_total": pool_neg,
            "expected_document_api_workload_m2": (
                f"~{company_years} company-years x 3 M2 variables "
                f"(market series retrieval)"
            ),
            "expected_document_api_workload_m3": (
                f"~{target_years} target years x 3 M3 variables "
                f"(macro series retrieval)"
            ),
            "expected_document_api_workload_m4": (
                f"~{company_years} company-years x 4 M4 variables "
                f"(audit/governance document retrieval)"
            ),
            "advantages": (
                f"Deterministic selection from frozen identifiers; "
                f"positive={pos_n} of Rule A pool={pool_pos}; temporal spread "
                f"across {target_years} target years"
            ),
            "limitations": (
                "Does not account for future accessibility results; "
                f"Rule A pool has only {pool_pos} positives / {pool_neg} "
                "negatives (~8% positive prevalence) — pilot options "
                "deliberately oversample positives for accessibility testing "
                "and must not be interpreted as population-representative"
            ),
            **_PILOT_METHODOLOGY_SCOPE,
            "status": "pending_user_approval",
        })
    return rows


# --------------------------------------------------------------------------- #
# Evidence manifest schema (for Part 3B)
# --------------------------------------------------------------------------- #

def build_evidence_manifest_schema() -> dict:
    return {
        "schema_version": "stage125_part3b_evidence_v1",
        "stage": CURRENT_STAGE,
        "purpose": (
            "Required fields for Part 3B evidence capture. Unknown fields "
            "must be null; never inferred."
        ),
        "required_fields": [
            {"name": "evidence_id", "type": "string", "nullable": False},
            {"name": "candidate_id", "type": "string", "nullable": False},
            {"name": "source_id", "type": "string", "nullable": False},
            {"name": "source_owner", "type": "string", "nullable": True},
            {"name": "source_url", "type": "string", "nullable": True},
            {"name": "source_title", "type": "string", "nullable": True},
            {"name": "source_identifier", "type": "string", "nullable": True},
            {"name": "retrieved_at_utc", "type": "datetime", "nullable": True},
            {"name": "published_at", "type": "datetime", "nullable": True},
            {"name": "available_at", "type": "datetime", "nullable": True},
            {"name": "raw_date_text", "type": "string", "nullable": True},
            {"name": "calendar", "type": "string", "nullable": True},
            {"name": "timezone", "type": "string", "nullable": True},
            {"name": "access_method", "type": "string", "nullable": True},
            {"name": "authentication_required", "type": "boolean", "nullable": True},
            {"name": "response_status_evidence", "type": "string", "nullable": True},
            {"name": "local_snapshot_path", "type": "string", "nullable": True},
            {"name": "snapshot_sha256", "type": "string", "nullable": True},
            {"name": "revision_status", "type": "string", "nullable": True},
            {"name": "license_or_usage_notes", "type": "string", "nullable": True},
            {"name": "reviewer_status", "type": "string", "nullable": True},
            {"name": "failure_reason", "type": "string", "nullable": True},
        ],
        "null_rules": {
            "unknown_fields_must_be_null": True,
            "never_infer_from_memory_or_reputation": True,
            "no_guessed_urls_or_dates": True,
        },
    }


# --------------------------------------------------------------------------- #
# Frozen-asset snapshot (read-only; deterministic)
# --------------------------------------------------------------------------- #

def frozen_asset_hashes(repo_root: Path) -> dict:
    root = str(repo_root)
    tracked = _git_tracked(root)
    snapshot: dict[str, str] = {}
    for manifest_rel in FROZEN_MANIFEST_PATHS:
        manifest_path = repo_root / manifest_rel
        if not manifest_path.is_file():
            raise QCFail(f"frozen manifest missing: {manifest_rel}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        outputs = data.get("output_files_sha256", {})
        manifest_dir = str(Path(manifest_rel).parent)
        for fname in sorted(outputs):
            file_rel = f"{manifest_dir}/{fname}"
            if file_rel not in tracked:
                continue
            if _git_ignored(root, file_rel):
                continue
            actual = sha256_file(repo_root / file_rel)
            if actual is not None:
                snapshot[file_rel] = actual
    return dict(sorted(snapshot.items()))


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(counts: dict) -> str:
    return (
        "# Stage125 Part 3A — Accessibility & Pilot Protocol Lock\n\n"
        "## Scope\n\n"
        "Part 3A locks the pilot protocol **before** any source-accessibility "
        "or coverage evidence is collected. It performs:\n"
        "- **No** modeling, **no** data extraction, **no** network access.\n"
        "- **No** changes to eligibility, targets, samples, or frozen assets.\n"
        "- **No** candidate admitted, passed, or scored from evidence.\n"
        "- Part 3B (evidence capture) is **not** started.\n\n"
        "## Registered candidate inventory (exactly 10)\n\n"
        "**M2 (3):** equity_return_window, realized_volatility, "
        "amihud_illiquidity\n\n"
        "**M3 (3):** cpi_inflation, fx_change_official, "
        "policy_financing_rate\n\n"
        "**M4 (4):** audit_opinion_type, going_concern_flag, "
        "audit_lag_days, board_size\n\n"
        "`src_m3_sci_macro` is registry-only (not a registered variable). "
        "Broader research-design narrative items are marked "
        "`research_design_only_not_registered`. M5 and Persian-text modeling "
        "remain `out_of_scope_locked`.\n\n"
        "## Inputs (read-only, SHA-256 verified)\n\n"
        f"- `{INPUT_ALL_ROWS_NAME}` — {counts['all_rows']} rows\n"
        f"- `{INPUT_PAIRS_NAME}` — {counts['pairs']} pairs, "
        f"{counts['unique_tickers_pairs']} tickers\n\n"
        "## Accessibility rubric\n\n"
        "- Proposed 0–5 scale; `approval_status=pending_user_approval`.\n"
        "- `applied_to_sources=false` in Part 3A.\n"
        "- Missing evidence → null/unresolved, never zero.\n"
        "- Score < 3 → hard drop; score = 3 → pilot permission only.\n"
        "- Scores 4–5 must still pass every other Gate.\n\n"
        "## Gate protocol\n\n"
        "Eight Gates are locked (accessibility ≥ 3, authoritative source, "
        "reproducibility, published/available_at, extraction error control, "
        "missing availability, no future info, all-must-pass). Six thresholds "
        "(coverage, event counts, pilot size/allocation) remain "
        "`pending_user_approval` — no numeric values invented.\n\n"
        "## Sampling frame\n\n"
        "Derived from frozen Gate B data only. Rule A primary = 1013 eligible "
        "(81 pos / 932 neg). Rule B robustness = 994 eligible (80 pos / 914 neg). "
        "Three event-enriched accessibility/coverage pilot options "
        "(`pilot_option_compact`, `pilot_option_event_enriched`, "
        "`pilot_option_extended`) provided for later human approval; none "
        "executed in Part 3A. All options share "
        "`sampling_purpose=event_enriched_accessibility_coverage_pilot`, "
        "`population_representative=false`, `modeling_sample=false`, "
        "`eligibility_impact=none_protocol_only`. They deliberately "
        "oversample positive distress events relative to Rule A prevalence "
        "(~8%) and must not be used to estimate population class prevalence "
        "or report model performance.\n\n"
        "## Guardrails\n\n"
        "- `modeling_started` remains `false`.\n"
        "- `part3a_protocol_locked` = `true`; `part3b_started` = `false`.\n"
        "- `eligibility_impact` = `none_protocol_only`.\n"
        "- Stage122–Stage125 Part 1/Part 2 frozen assets unchanged.\n"
    )


# --------------------------------------------------------------------------- #
# QC assertions + report
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    counts: dict,
    content_hashes: dict,
    frozen_before: dict,
    frozen_after: dict,
    inventory_rows: list[dict],
    gate_rows: list[dict],
    rubric: dict,
    pilot_options: list[dict],
    repo_root: str,
    guard_evidence: dict,
) -> list[dict]:
    out: list[dict] = []

    def add(name, ok, detail):
        out.append({"assertion": name, "status": "PASS" if ok else "FAIL",
                    "detail": detail})

    inv_errs = check_invariants(counts)
    add("invariants_match", inv_errs == [],
        "all invariant counts match" if not inv_errs else "; ".join(inv_errs))

    add("baseline_commit_exact",
        _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, "HEAD"),
        f"baseline {EXPECTED_BASELINE_COMMIT} is ancestor of HEAD")

    registered = [r for r in inventory_rows
                  if r["candidate_scope_status"] == "registered_candidate"]
    add("registered_candidate_count_10", len(registered) == 10,
        f"registered={len(registered)}")
    m2 = sum(1 for r in registered if r["block"] == "M2")
    m3 = sum(1 for r in registered if r["block"] == "M3")
    m4 = sum(1 for r in registered if r["block"] == "M4")
    add("m2_count_3", m2 == 3, f"m2={m2}")
    add("m3_count_3", m3 == 3, f"m3={m3}")
    add("m4_count_4", m4 == 4, f"m4={m4}")
    add("no_m5_candidate",
        not any(r["block"] == "M5" and
                r["candidate_scope_status"] == "registered_candidate"
                for r in inventory_rows),
        "no M5 registered candidate")

    add("src_m3_sci_macro_registry_only",
        any(r["registry_status"] == "registry_only_not_registered" and
            r["source_id"] == "src_m3_sci_macro" for r in inventory_rows),
        "src_m3_sci_macro marked registry_only_not_registered")

    add("no_unregistered_promoted",
        all(r["candidate_scope_status"] != "registered_candidate" or
            r["dictionary_status"] == "registered_in_data_dictionary"
            for r in inventory_rows),
        "all registered candidates appear in data_dictionary contract")

    add("evidence_scores_null",
        all(r["accessibility_score"] == "" for r in registered),
        "all registered candidate accessibility_score null/unresolved")

    add("no_candidate_admitted",
        all(r["decision_status"] != "admitted" for r in inventory_rows),
        "no candidate marked admitted")
    add("no_candidate_passed",
        all("pass" not in r["decision_status"].lower() for r in inventory_rows),
        "no candidate marked passed")

    add("accessibility_lt3_rule_recorded",
        rubric["scoring_rules"]["score_below_3"] == "hard_drop",
        "score < 3 hard drop recorded")
    add("score_3_pilot_only_rule_recorded",
        rubric["scoring_rules"]["score_equals_3"] ==
        "pilot_permission_only_not_automatic_admission",
        "score = 3 pilot-only rule recorded")

    pending_gates = [g for g in gate_rows
                     if g["approval_status"] == "pending_user_approval"]
    add("coverage_thresholds_pending",
        any(g["gate_name"] == "minimum_company_year_coverage" for g in pending_gates)
        and all(g["threshold_value"] == "" for g in pending_gates),
        f"pending_gates={len(pending_gates)} with no invented thresholds")
    add("event_thresholds_pending",
        any(g["gate_name"] == "minimum_positive_event_count_per_fold"
            for g in pending_gates),
        "event-count gates pending user approval")

    add("rubric_pending_approval",
        rubric["approval_status"] == "pending_user_approval" and
        rubric["applied_to_sources"] is False,
        "rubric proposed but not applied")

    add("content_hashes_present", all(v for v in content_hashes.values()),
        f"{len(content_hashes)} content files hashed")

    add("frozen_assets_unchanged",
        frozen_before == frozen_after and len(frozen_before) > 0,
        f"{len(frozen_before)} tracked frozen assets identical")

    modeling = guard_evidence["modeling"]
    add("modeling_not_started", modeling["no_modeling"],
        "checked paths and artifact patterns"
        if modeling["no_modeling"] else
        f"paths={modeling['path_hits']}; artifacts={modeling['artifact_hits']}")

    add("no_network_extraction", guard_evidence["no_network_calls"],
        f"network_calls_attempted={guard_evidence['network_calls_attempted']}")

    part3b = guard_evidence["part3b"]
    add("no_data_extraction", part3b["no_part3b"],
        "no Part 3B evidence datasets or extraction outputs"
        if part3b["no_part3b"] else f"part3b_hits={part3b['hits']}")

    add("part3b_not_started", part3b["no_part3b"],
        "no Part 3B runner/implementation/captured evidence"
        if part3b["no_part3b"] else f"part3b_hits={part3b['hits']}")

    eligibility = guard_evidence["eligibility"]
    add("eligibility_impact_none", guard_evidence["eligibility_unchanged"],
        f"snapshot_sha256={eligibility['snapshot_sha256']}; "
        f"rule_a={eligibility['rule_a_eligible_pairs']}/"
        f"{eligibility['rule_a_positive']}pos/"
        f"{eligibility['rule_a_negative']}neg"
        if guard_evidence["eligibility_unchanged"] else
        "; ".join(guard_evidence["eligibility_mismatches"]))

    add("part1_part2_frozen_unchanged",
        len(frozen_before) > 0 and frozen_before == frozen_after,
        "Stage122-Stage125 Part1/Part2 frozen deliverables unchanged")

    pilot_ids = {o["option_id"] for o in pilot_options}
    bad_representative = [
        o["option_id"] for o in pilot_options
        if "representative" in o["option_id"].lower()
    ]
    bad_desc = [
        o["option_id"] for o in pilot_options
        if "representative pilot" in o.get("proposed_temporal_allocation", "").lower()
        or o.get("proposed_temporal_allocation", "").lower().startswith(
            "representative "
        )
    ]
    add("pilot_options_no_representative_label",
        "pilot_option_representative" not in pilot_ids and
        not bad_representative and not bad_desc,
        f"option_ids={sorted(pilot_ids)}; bad_ids={bad_representative + bad_desc}")
    add("pilot_options_all_non_population_representative",
        len(pilot_options) == 3 and all(
            o.get("population_representative") == "false"
            for o in pilot_options
        ),
        "all options population_representative=false")
    add("pilot_options_all_non_modeling_pilot",
        len(pilot_options) == 3 and all(
            o.get("modeling_sample") == "false" and
            o.get("sampling_purpose") ==
            "event_enriched_accessibility_coverage_pilot"
            for o in pilot_options
        ),
        "all options event_enriched_accessibility_coverage_pilot; "
        "modeling_sample=false")
    add("pilot_options_all_pending_user_approval",
        len(pilot_options) == 3 and all(
            o.get("status") == "pending_user_approval" for o in pilot_options
        ),
        "all options pending_user_approval")
    add("pilot_options_no_final_selection",
        "pilot_option_event_enriched" in pilot_ids and
        "pilot_option_representative" not in pilot_ids and
        all(o.get("eligibility_impact") == "none_protocol_only"
            for o in pilot_options),
        "no final pilot selected or executed")
    return out


def build_qc_report(
    repo_root: Path, counts: dict,
    input_all_sha: str, input_pairs_sha: str,
    content_hashes: dict,
    frozen_before: dict, frozen_after: dict,
    tickers: list[str],
    inventory_rows: list[dict],
    gate_rows: list[dict],
    rubric: dict,
    pilot_options: list[dict],
    guard_evidence: dict,
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    src_sha = sha256_file(repo_root / SRC_REL)
    test_sha = sha256_file(repo_root / TEST_REL)
    assertions = build_qc_assertions(
        counts, content_hashes, frozen_before, frozen_after,
        inventory_rows, gate_rows, rubric, pilot_options, root, guard_evidence,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    all_pass = failed == 0
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
        "all_pass": all_pass,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "input_all_rows_name": INPUT_ALL_ROWS_NAME,
        "input_pairs_name": INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "invariants": dict(sorted(counts.items())),
        "expected_invariants": dict(sorted(EXPECTED_INVARIANTS.items())),
        "registered_candidate_count": 10,
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_assets_before": frozen_before,
        "frozen_assets_after": frozen_after,
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "part3_started": True,
        "part3a_protocol_locked": True,
        "part3b_started": False,
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
            "Stage125 Part 3A — accessibility & pilot protocol lock."
        ),
        "generated_at": qc_report["generated_at"],
        "code_commit": qc_report["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc_report["source_file_sha256"],
        "test_file_sha256": qc_report["test_file_sha256"],
        "input_all_rows_name": INPUT_ALL_ROWS_NAME,
        "input_pairs_name": INPUT_PAIRS_NAME,
        "input_all_rows_sha256": input_all_sha,
        "input_pairs_sha256": input_pairs_sha,
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "part3_started": True,
        "part3a_protocol_locked": True,
        "part3b_started": False,
        "pilot_extraction_started": False,
        "network_extraction_performed": qc_report.get(
            "network_extraction_performed", False),
        "network_calls_attempted": qc_report.get("network_calls_attempted", 0),
        "warning": (
            "Part 3A only: protocol lock before evidence collection. "
            "No modeling, no extraction, no network access. "
            "Part 3B not started. Stage122-Stage125 Part 1/2 assets unchanged."
        ),
    }


# --------------------------------------------------------------------------- #
# Content assembly (deterministic; pure)
# --------------------------------------------------------------------------- #

def build_content_files(
    df_all: pd.DataFrame, df_pairs: pd.DataFrame, counts: dict,
) -> dict[str, str]:
    inventory_rows = build_candidate_inventory_rows()
    gate_rows = build_gate_protocol_rows()
    rubric = build_accessibility_rubric()
    sampling_summary = build_sampling_summary(df_all, df_pairs, counts)
    sampling_by_year = build_sampling_by_year_rows(df_all, df_pairs)
    pilot_options = build_pilot_sampling_options(df_all, df_pairs)
    evidence_schema = build_evidence_manifest_schema()
    return {
        F_CANDIDATE_INVENTORY: _csv_str(_CANDIDATE_HEADER, inventory_rows),
        F_ACCESSIBILITY_RUBRIC: _json_str(rubric),
        F_GATE_PROTOCOL: _csv_str(_GATE_HEADER, gate_rows),
        F_SAMPLING_SUMMARY: _json_str(sampling_summary),
        F_SAMPLING_BY_YEAR: _csv_str(_SAMPLING_BY_YEAR_HEADER, sampling_by_year),
        F_PILOT_OPTIONS: _csv_str(_PILOT_OPTIONS_HEADER, pilot_options),
        F_EVIDENCE_SCHEMA: _json_str(evidence_schema),
        F_README: build_readme(counts),
        "_inventory_rows": inventory_rows,
        "_gate_rows": gate_rows,
        "_rubric": rubric,
        "_pilot_options": pilot_options,
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
    with network_sentinel() as sentinel:
        df_all, df_pairs, sha_all, sha_pairs = load_inputs(all_rows_path, pairs_path)

        counts = compute_invariants(df_all, df_pairs)
        inv_errs = check_invariants(counts)
        if inv_errs:
            raise QCFail(
                "invariant mismatch (fail-closed):\n  " + "\n  ".join(inv_errs)
            )

        frozen_before = frozen_asset_hashes(repo_root)
        raw_content = build_content_files(df_all, df_pairs, counts)
        inventory_rows = raw_content.pop("_inventory_rows")
        gate_rows = raw_content.pop("_gate_rows")
        rubric = raw_content.pop("_rubric")
        pilot_options = raw_content.pop("_pilot_options")
        content_files = {
            k: v for k, v in raw_content.items() if not k.startswith("_")
        }
        content_hashes = _hash_map(content_files)
        frozen_after = frozen_asset_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen assets changed during Part 3A run (fail-closed)")

        guard_evidence = run_guardrails(
            project_dir, repo_root, df_all, df_pairs, sentinel.calls_attempted,
        )

        tickers = sorted(
            t for t in df_pairs["ticker"].dropna().unique() if str(t).strip()
        )
        qc_report = build_qc_report(
            repo_root, counts, sha_all, sha_pairs, content_hashes,
            frozen_before, frozen_after, tickers,
            inventory_rows, gate_rows, rubric, pilot_options, guard_evidence,
        )
        if not qc_report["all_pass"]:
            failed = [a for a in qc_report["assertions"] if a["status"] != "PASS"]
            raise QCFail("QC failed (fail-closed): "
                         + "; ".join(f"{a['assertion']}: {a['detail']}"
                                     for a in failed))

        qc_str = _json_str(qc_report)
        qc_hash = sha256_bytes(qc_str.encode("utf-8"))
        metadata = build_metadata(repo_root, qc_report, content_hashes, qc_hash,
                                  sha_all, sha_pairs)

        files: dict[str, str] = dict(content_files)
        files[F_QC] = qc_str
        files[F_METADATA] = _json_str(metadata)
        return {
            "files": files,
            "qc": qc_report,
            "counts": counts,
            "inventory_rows": inventory_rows,
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
            project_dir / "stage124" / "gate_b_final" / INPUT_ALL_ROWS_NAME
        )
    if pairs_path is None:
        pairs_path = (
            project_dir / "stage124" / "gate_b_final" / INPUT_PAIRS_NAME
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
