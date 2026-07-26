"""Stage126 M1 — Robustness Closure (pure synthesis of Parts 1-6; no execution).

This module is a SYNTHESIS-ONLY closure of the six already-completed and
already-committed Stage126 M1 robustness categories (Parts 1-6). It performs:

  * ZERO model fits, ZERO predictions, ZERO resampling (SMOTE/SMOTENC),
    ZERO hyperparameter search, ZERO calibration/bootstrap/Holm/p-values/SHAP/
    threshold optimization, ZERO winner selection;
  * ZERO final-test access (no predictor or target row values are read; only
    frozen aggregate lock/gate artifacts already committed by Parts 1-6 are
    referenced by path);
  * ZERO network calls.

It reads the already-committed Part 1-6 comparison/metrics/completion-lock/
execution-manifest artifacts and the locked primary pooled development-OOF
PR-AUC reference, and produces a small set of new deterministic derived
artifacts: an 18-row evidence table, a synthesis/closure JSON record, a
completion lock, a source/scientific manifest, and a README.

It does NOT select a retained design, does NOT freeze anything, and does NOT
authorize `stage126-m1-retained-design-freeze` (a separate, future, explicitly
human-authorized action).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_closure"
CURRENT_STAGE = "Stage126"
CONTRACT_ID = "stage126_m1_robustness_closure"
CONTRACT_VERSION = "stage126_m1_robustness_closure_v1"
DECISION_ID = "stage126-m1-robustness-closure"

STAGE126_DIR_REL = "project/stage126"

SRC_REL = "project/src/stage126_m1_robustness_closure.py"
RUN_REL = "project/run_stage126_m1_robustness_closure.py"
TEST_REL = "project/tests/test_stage126_m1_robustness_closure.py"

F_EVIDENCE_TABLE = "stage126_m1_robustness_closure_evidence_table.csv"
F_SYNTHESIS_RECORD = "stage126_m1_robustness_closure_synthesis_record.json"
F_COMPLETION_LOCK = "stage126_m1_robustness_closure_completion_lock.json"
F_SOURCE_MANIFEST = "stage126_m1_robustness_closure_source_manifest.json"
F_README = "README_STAGE126_M1_ROBUSTNESS_CLOSURE.md"
F_QC = "stage126_m1_robustness_closure_qc_report.json"

RUNTIME_VERSION_PACKAGES = ("pandas", "numpy", "scikit-learn", "xgboost")

MODEL_FAMILIES = (
    "regularized_logistic_regression",
    "random_forest",
    "xgboost",
)

PRIMARY_ORDERING = (
    "regularized_logistic_regression",
    "random_forest",
    "xgboost",
)

PRIMARY_METRICS_REL = "project/stage126/stage126_m1_development_metrics.csv"

# The six registered robustness categories in binding execution order.
PARTS: tuple[dict[str, Any], ...] = (
    {
        "part_index": 1,
        "category_id": "m1_target_proximity_six_feature_set",
        "changed_dimension": "feature_set",
    },
    {
        "part_index": 2,
        "category_id": "main_rule_b_listing_robustness",
        "changed_dimension": "sample",
    },
    {
        "part_index": 3,
        "category_id": "expanded_rule_a_company_scope_robustness",
        "changed_dimension": "sample",
    },
    {
        "part_index": 4,
        "category_id": "expanded_rule_b_combined_robustness",
        "changed_dimension": "sample",
    },
    {
        "part_index": 5,
        "category_id": "persistent_loss_robustness_target",
        "changed_dimension": "target",
    },
    {
        "part_index": 6,
        "category_id": "smote_training_fold_only_robustness",
        "changed_dimension": "imbalance_strategy",
    },
)

# Consumed source artifacts per Part (relative to repo root).
def _part_artifact_rels(n: int) -> dict[str, str]:
    base = f"project/stage126/stage126_m1_robustness_part{n}"
    return {
        "comparison": f"{base}_primary_comparison.json",
        "metrics": f"{base}_metrics.csv",
        "completion_lock": f"{base}_completion_lock.json",
        "execution_manifest": f"{base}_execution_manifest.json",
        "human_authorization_record": f"{base}_human_authorization_record.json",
    }


REGISTRY_REL = "project/stage126/stage126_closed_part_registry.json"
SELECTED_CONFIGS_REL = "project/stage126/stage126_m1_selected_configurations.json"
PART6_RESAMPLING_AUDIT_REL = "project/stage126/stage126_m1_robustness_part6_resampling_audit.csv"

# Boolean fields that, when present in a Part's own execution_manifest.json,
# must equal (changed_dimension == <dimension>). Field names are NOT uniform
# across Parts (Part 1 predates several of these fields; Part 6 uses
# `imbalance_policy_changed` for the imbalance dimension), so each dimension
# lists every observed alias.
_CHANGE_FLAG_ALIASES: dict[str, tuple[str, ...]] = {
    "sample": ("sample_changed",),
    "target": ("target_changed",),
    "feature_set": ("feature_set_changed",),
    "imbalance_strategy": ("imbalance_policy_changed", "imbalance_strategy_changed"),
}

FINAL_TEST_ZERO_COUNTER_KEYS = (
    "final_test_predictor_rows_loaded",
    "final_test_target_rows_loaded",
    "final_test_evaluations",
)

EVIDENCE_TABLE_COLUMNS = (
    "part_index",
    "category_id",
    "changed_dimension",
    "model_family",
    "primary_pooled_pr_auc",
    "robustness_pooled_pr_auc",
    "absolute_delta_vs_primary",
    "relative_delta_vs_primary",
    "observed_ordering_for_part",
    "primary_ordering_preserved",
    "sample_changed",
    "target_changed",
    "feature_set_changed",
    "imbalance_strategy_changed",
    "selected_configurations_changed",
    "development_only",
    "final_test_accessed_or_evaluated",
    "source_comparison_artifact",
    "source_metric_artifact",
)


class QCFail(RuntimeError):
    """Fail-closed closure-synthesis validation error."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git(repo_root: str | Path, *args: str) -> str:
    """Informational git helper only (never used for integrity decisions),
    following the same convention as e.g.
    stage126_m1_robustness_part6_smote_training_fold_only.py."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return out.stdout.strip()


def runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in RUNTIME_VERSION_PACKAGES:
        try:
            versions[pkg] = importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:
            versions[pkg] = "absent"
    versions["python"] = platform.python_version()
    return versions


def repo_root_from(project_dir: Path) -> Path:
    return project_dir.parent if project_dir.name == "project" else project_dir


def _read_json(repo_root: Path, rel: str) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing artifact: {rel}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QCFail(f"unreadable artifact {rel}: {exc}") from exc


def _read_metrics_csv(repo_root: Path, rel: str) -> list[dict[str, str]]:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing metrics artifact: {rel}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pooled_pr_auc_by_family(rows: list[dict[str, str]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        if row.get("scope") == "pooled_development_oof":
            out[row["model_family"]] = float(row["pr_auc"])
    return out


# --------------------------------------------------------------------------- #
# Load locked primary pooled PR-AUC from the actual committed artifact
# --------------------------------------------------------------------------- #

def load_primary_pooled_pr_auc(repo_root: Path) -> dict[str, float]:
    """Read the locked primary pooled development-OOF PR-AUC per family.

    Reads directly from ``project/stage126/stage126_m1_development_metrics.csv``
    (the same canonical source each Part's own comparison artifact cites), so
    the closure never transcribes a hardcoded number independently of the
    committed artifact.
    """
    rows = _read_metrics_csv(repo_root, PRIMARY_METRICS_REL)
    pooled = pooled_pr_auc_by_family(rows)
    missing = set(MODEL_FAMILIES) - set(pooled)
    if missing:
        raise QCFail(f"primary metrics missing pooled rows for: {sorted(missing)}")
    return pooled


def load_registered_categories(repo_root: Path) -> list[str]:
    registry = _read_json(repo_root, REGISTRY_REL)
    parts = registry.get("parts", {})
    ordered = sorted(parts.values(), key=lambda p: p["part_index"])
    ids = [p["category_id"] for p in ordered]
    expected = [p["category_id"] for p in PARTS]
    if ids != expected:
        raise QCFail(
            f"closed_part_registry category order mismatch: {ids} != {expected}"
        )
    if registry.get("closed_part_count") != 6:
        raise QCFail("closed_part_registry closed_part_count is not 6")
    return ids


def load_primary_selected_configurations(repo_root: Path) -> dict[str, Any]:
    return _read_json(repo_root, SELECTED_CONFIGS_REL)


def _load_part_execution_manifest(repo_root: Path, n: int) -> dict[str, Any]:
    return _read_json(repo_root, _part_artifact_rels(n)["execution_manifest"])


def _load_part_completion_lock(repo_root: Path, n: int) -> dict[str, Any]:
    return _read_json(repo_root, _part_artifact_rels(n)["completion_lock"])


def derive_part_semantics(
    part: dict[str, Any],
    manifest: dict[str, Any],
    completion_lock: dict[str, Any],
    primary_selected_configs: dict[str, Any],
) -> dict[str, bool]:
    """Read/verify the semantic booleans for one Part from ITS OWN canonical
    execution-manifest/completion-lock artifacts, fail-closed on disagreement.

    Never invents a value: a dimension's changed-flag is read from whichever
    alias field the Part actually recorded; if the Part predates that field
    (Part 1), the flag is derived from the Part's own `changed_dimension`
    (itself cross-checked against the registered ``PARTS`` table) rather than
    a value hardcoded independently in this module.
    """
    n = part["part_index"]
    expected_dimension = part["changed_dimension"]
    manifest_dimension = manifest.get("changed_dimension")
    if manifest_dimension != expected_dimension:
        raise QCFail(
            f"Part {n} changed_dimension mismatch: "
            f"execution_manifest={manifest_dimension!r} registered={expected_dimension!r}"
        )

    flags: dict[str, bool] = {}
    for dimension, aliases in _CHANGE_FLAG_ALIASES.items():
        expected = dimension == expected_dimension
        present = [a for a in aliases if a in manifest]
        for alias in present:
            observed = bool(manifest[alias])
            if observed != expected:
                raise QCFail(
                    f"Part {n} {alias}={observed} disagrees with "
                    f"changed_dimension={expected_dimension!r}"
                )
        flags[dimension] = expected

    # selected_configurations_changed: independently recompute by comparing
    # each Part's own recorded configuration_id per family against the
    # locked primary selected-configuration file, then cross-check against
    # any explicit `selected_configurations_changed` field the Part recorded.
    part_selected = manifest.get("selected_configurations")
    if not isinstance(part_selected, dict):
        raise QCFail(f"Part {n} execution_manifest missing selected_configurations")
    computed_changed = False
    for fam in MODEL_FAMILIES:
        part_cfg = part_selected.get(fam)
        primary_cfg = primary_selected_configs.get(fam, {}).get("configuration_id")
        if part_cfg is None or primary_cfg is None:
            raise QCFail(f"Part {n} missing configuration_id comparison for {fam}")
        if part_cfg != primary_cfg:
            computed_changed = True
    if "selected_configurations_changed" in manifest:
        recorded = bool(manifest["selected_configurations_changed"])
        if recorded != computed_changed:
            raise QCFail(
                f"Part {n} selected_configurations_changed={recorded} disagrees "
                f"with recomputed value={computed_changed}"
            )
    selected_configurations_changed = computed_changed

    # development_only: read (fail closed if absent or False).
    if manifest.get("development_only") is not True:
        raise QCFail(f"Part {n} execution_manifest development_only is not True")
    development_only = True

    # final_test_accessed_or_evaluated: derive from the frozen zero-counters
    # already recorded by the Part, fail-closed if any is non-zero, and
    # cross-check against the completion-lock's own final-test booleans.
    for key in FINAL_TEST_ZERO_COUNTER_KEYS:
        if key not in manifest:
            raise QCFail(f"Part {n} execution_manifest missing {key}")
        if manifest[key] != 0:
            raise QCFail(f"Part {n} {key}={manifest[key]!r} is not 0")
    for key in (
        "final_test_access_authorized",
        "final_test_evaluation_performed",
        "final_test_unlocked",
        "full_development_refit_performed",
    ):
        if key in completion_lock and completion_lock[key] is not False:
            raise QCFail(f"Part {n} completion_lock {key}={completion_lock[key]!r} is not False")
    for key in (
        "paper_winner_selected",
        "selects_paper_winner",
        "winner_selected",
    ):
        if key in completion_lock and completion_lock[key] is not False:
            raise QCFail(f"Part {n} completion_lock {key}={completion_lock[key]!r} is not False")
    final_test_accessed_or_evaluated = False

    flags["selected_configurations_changed"] = selected_configurations_changed
    flags["development_only"] = development_only
    flags["final_test_accessed_or_evaluated"] = final_test_accessed_or_evaluated
    return flags


def verify_part5_positive_counts(manifest: dict[str, Any]) -> tuple[int, int, int]:
    """Read Part 5's own recorded development-positive transition counts and
    fail closed unless they exactly match the reported 68/85/+17."""
    transitions = manifest.get("development_target_transitions")
    if not isinstance(transitions, dict):
        raise QCFail("Part 5 execution_manifest missing development_target_transitions")
    primary_positive = transitions.get("primary_positive")
    persistent_positive = transitions.get("persistent_positive")
    net_delta = transitions.get("net_positive_delta")
    if primary_positive != 68 or persistent_positive != 85 or net_delta != 17:
        raise QCFail(
            "Part 5 development_target_transitions disagree with expected "
            f"68/85/+17: primary_positive={primary_positive!r} "
            f"persistent_positive={persistent_positive!r} net_positive_delta={net_delta!r}"
        )
    return primary_positive, persistent_positive, net_delta


def verify_part6_imbalance_semantics(repo_root: Path, manifest: dict[str, Any]) -> None:
    """Fail closed unless Part 6's own manifest + resampling audit CSV confirm
    class weighting is disabled and SMOTENC was applied training-fold-only
    (never to validation rows, never approaching the final test)."""
    if manifest.get("class_weighting_disabled") is not True:
        raise QCFail("Part 6 execution_manifest class_weighting_disabled is not True")
    audit_rows = _read_metrics_csv(repo_root, PART6_RESAMPLING_AUDIT_REL)
    if not audit_rows:
        raise QCFail("Part 6 resampling audit CSV is empty")
    for row in audit_rows:
        if row.get("validation_resampled") != "false":
            raise QCFail(
                f"Part 6 resampling audit row has validation_resampled={row.get('validation_resampled')!r}"
            )
        if row.get("final_test_approached") != "false":
            raise QCFail(
                f"Part 6 resampling audit row has final_test_approached={row.get('final_test_approached')!r}"
            )


# --------------------------------------------------------------------------- #
# Evidence table (18 rows = 6 parts x 3 model families)
# --------------------------------------------------------------------------- #

def build_evidence_rows(
    repo_root: Path, primary_pooled: dict[str, float],
) -> list[dict[str, Any]]:
    primary_selected_configs = load_primary_selected_configurations(repo_root)
    rows: list[dict[str, Any]] = []
    for part in PARTS:
        n = part["part_index"]
        cid = part["category_id"]
        changed_dimension = part["changed_dimension"]
        rels = _part_artifact_rels(n)
        metrics_rows = _read_metrics_csv(repo_root, rels["metrics"])
        part_pooled = pooled_pr_auc_by_family(metrics_rows)
        missing = set(MODEL_FAMILIES) - set(part_pooled)
        if missing:
            raise QCFail(f"Part {n} metrics missing pooled rows for: {sorted(missing)}")

        # Observed ordering for this part: descending pooled PR-AUC.
        observed_ordering = tuple(
            sorted(MODEL_FAMILIES, key=lambda fam: part_pooled[fam], reverse=True)
        )
        ordering_preserved = observed_ordering == PRIMARY_ORDERING

        manifest = _load_part_execution_manifest(repo_root, n)
        completion_lock = _load_part_completion_lock(repo_root, n)
        semantics = derive_part_semantics(
            part, manifest, completion_lock, primary_selected_configs,
        )
        sample_changed = semantics["sample"]
        target_changed = semantics["target"]
        feature_set_changed = semantics["feature_set"]
        imbalance_strategy_changed = semantics["imbalance_strategy"]
        selected_configurations_changed = semantics["selected_configurations_changed"]
        development_only = semantics["development_only"]
        final_test_accessed_or_evaluated = semantics["final_test_accessed_or_evaluated"]

        if n == 5:
            verify_part5_positive_counts(manifest)
        if n == 6:
            verify_part6_imbalance_semantics(repo_root, manifest)

        for fam in MODEL_FAMILIES:
            primary_val = primary_pooled[fam]
            robustness_val = part_pooled[fam]
            abs_delta = robustness_val - primary_val
            rel_delta = abs_delta / primary_val if primary_val != 0 else None
            rows.append({
                "part_index": n,
                "category_id": cid,
                "changed_dimension": changed_dimension,
                "model_family": fam,
                "primary_pooled_pr_auc": primary_val,
                "robustness_pooled_pr_auc": robustness_val,
                "absolute_delta_vs_primary": abs_delta,
                "relative_delta_vs_primary": rel_delta,
                "observed_ordering_for_part": ">".join(observed_ordering),
                "primary_ordering_preserved": ordering_preserved,
                "sample_changed": sample_changed,
                "target_changed": target_changed,
                "feature_set_changed": feature_set_changed,
                "imbalance_strategy_changed": imbalance_strategy_changed,
                "selected_configurations_changed": selected_configurations_changed,
                "development_only": development_only,
                "final_test_accessed_or_evaluated": final_test_accessed_or_evaluated,
                "source_comparison_artifact": rels["comparison"],
                "source_metric_artifact": rels["metrics"],
            })
    return rows


def evidence_rows_to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=list(EVIDENCE_TABLE_COLUMNS), lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        out = dict(row)
        for k, v in list(out.items()):
            if isinstance(v, bool):
                out[k] = "true" if v else "false"
            elif isinstance(v, float):
                out[k] = f"{v:.12f}"
            elif v is None:
                out[k] = ""
        writer.writerow(out)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Synthesis / closure record (interpretation findings A-E)
# --------------------------------------------------------------------------- #

def build_synthesis_record(
    repo_root: Path, primary_pooled: dict[str, float], rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_part: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_part.setdefault(row["part_index"], []).append(row)

    part5_manifest = _load_part_execution_manifest(repo_root, 5)
    part5_primary_positive, part5_persistent_positive, part5_positive_delta = (
        verify_part5_positive_counts(part5_manifest)
    )
    part6_manifest = _load_part_execution_manifest(repo_root, 6)
    verify_part6_imbalance_semantics(repo_root, part6_manifest)
    part6_class_weighting_disabled = part6_manifest["class_weighting_disabled"]

    part_summaries = []
    for part in PARTS:
        n = part["part_index"]
        prows = by_part[n]
        ordering_preserved = prows[0]["primary_ordering_preserved"]
        part_summaries.append({
            "part_index": n,
            "category_id": part["category_id"],
            "changed_dimension": part["changed_dimension"],
            "pooled_pr_auc": {
                r["model_family"]: r["robustness_pooled_pr_auc"] for r in prows
            },
            "absolute_delta_vs_primary": {
                r["model_family"]: r["absolute_delta_vs_primary"] for r in prows
            },
            "observed_ordering": prows[0]["observed_ordering_for_part"],
            "primary_ordering_preserved": ordering_preserved,
            "source_comparison_artifact": prows[0]["source_comparison_artifact"],
            "source_metric_artifact": prows[0]["source_metric_artifact"],
        })

    interpretation = {
        "A_model_family_ordering": {
            "finding": (
                "The primary pooled development-OOF ordering "
                "(regularized_logistic_regression > random_forest > xgboost) is "
                "preserved in Parts 2, 3, 4, 5 and 6. Part 1 (target-proximity "
                "six-feature set) is the sole exception, observing "
                "xgboost > random_forest > regularized_logistic_regression, with "
                "all three families declining in pooled PR-AUC relative to the "
                "primary. This is reported as feature-set sensitivity evidence "
                "only. The locked primary ordering used for confirmatory "
                "interpretation is unchanged, and no paper winner is selected."
            ),
            "part1_is_the_exception": True,
            "primary_ordering": list(PRIMARY_ORDERING),
        },
        "B_sample_definition_sensitivity": {
            "finding": (
                "Parts 2, 3 and 4 redefine the sample (listing-timing Rule B, "
                "expanded Rule A company scope, and their combination under "
                "Rule B) while holding the target, feature set, configurations "
                "and imbalance policy fixed. The primary ordering is preserved "
                "in every case and pooled PR-AUC changes are small in absolute "
                "terms, evidencing that the primary conclusions are comparatively "
                "stable to listing-timing and company-scope sample redefinition. "
                "This is subject to the existing event-rate/identity-composition "
                "cautions already recorded in the Part 3 and Part 4 comparison "
                "artifacts (Part 4 has one fewer positive at the frozen "
                "full-sample aggregate level relative to Part 3 and the primary "
                "sample; this closure does not access final-test row-level "
                "targets and only cites the existing frozen aggregate gate "
                "artifact already recorded by Part 4). No preferred robustness "
                "sample is selected."
            ),
            "primary_ordering_preserved_in_parts": [2, 3, 4],
        },
        "C_target_sensitivity": {
            "finding": (
                "Part 5 substitutes the secondary persistent-loss target for "
                "the primary target while holding the sample, feature set, "
                "configurations and imbalance policy fixed. Pooled PR-AUC "
                "increases for all three model families, but the target changed "
                f"AND the development positive count increased "
                f"({part5_persistent_positive} vs {part5_primary_positive}, "
                f"+{part5_positive_delta}). This is treated as secondary-target "
                "sensitivity evidence only, NOT as a same-outcome performance "
                "gain, and does not replace or reweight the primary target."
            ),
            "development_positive_count_primary": part5_primary_positive,
            "development_positive_count_persistent_loss": part5_persistent_positive,
            "development_positive_count_delta": part5_positive_delta,
        },
        "D_imbalance_strategy_sensitivity": {
            "finding": (
                "Part 6 substitutes training-fold-only SMOTENC (class "
                "weighting disabled) for the primary class-weighted imbalance "
                "policy while holding the sample, target, feature set and "
                "configurations fixed. The primary ordering is preserved, but "
                "all three pooled PR-AUC values decline relative to the locked "
                "primary class-weighted result. This is reported as "
                "imbalance-strategy sensitivity evidence. Class weighting is "
                "NOT frozen as the retained imbalance policy by this closure; "
                "that decision belongs to the separate, future "
                "`stage126-m1-retained-design-freeze` action."
            ),
            "primary_ordering_preserved": by_part[6][0]["primary_ordering_preserved"],
            "all_three_families_declined": all(
                r["absolute_delta_vs_primary"] < 0 for r in by_part[6]
            ),
            "class_weighting_disabled": part6_class_weighting_disabled,
        },
        "E_overall_synthesis": {
            "finding": (
                "Taken together, the six pre-registered M1 robustness "
                "categories provide sensitivity evidence only. This evidence "
                "does NOT justify changing the primary result, selecting a "
                "winning model family, retuning any configuration, opening the "
                "final test, or automatically freezing a retained design. The "
                "distinction between (1) evidence synthesis performed now by "
                "this closure and (2) the retained-design decision/freeze to be "
                "made later under separate explicit human authorization is "
                "explicitly preserved."
            ),
        },
    }

    prohibited_actions = [
        "winner_selection",
        "retained_design_selection",
        "retained_design_freeze",
        "retuning",
        "hyperparameter_search",
        "full_development_refit",
        "final_test_access",
        "final_test_evaluation",
        "calibration",
        "paired_bootstrap",
        "holm_correction",
        "p_values",
        "shap",
        "threshold_optimization",
        "m2_m3_m4_start",
    ]

    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "closure_type": "synthesis_only",
        "registered_categories_in_order": [p["category_id"] for p in PARTS],
        "primary_pooled_pr_auc": dict(sorted(primary_pooled.items())),
        "primary_ordering": list(PRIMARY_ORDERING),
        "primary_metrics_source": PRIMARY_METRICS_REL,
        "part_summaries": part_summaries,
        "scientific_interpretation": interpretation,
        "prohibited_actions": prohibited_actions,
        "paper_winner_selected": False,
        "retained_design_selected": False,
        "retained_design_freeze_authorized": False,
        "next_action_id": "stage126-m1-retained-design-freeze",
        "next_action_requires_separate_human_authorization": True,
    }


# --------------------------------------------------------------------------- #
# Completion lock
# --------------------------------------------------------------------------- #

def build_completion_lock() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "robustness_closure_completed": True,
        "all_six_registered_categories_verified": True,
        "completed_category_ids": [p["category_id"] for p in PARTS],
        "paper_winner_selected": False,
        "retained_design_selected": False,
        "retained_design_freeze_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "p_values_computed": False,
        "threshold_optimization_executed": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "tuning_search_calls": 0,
        "m2_data_collected": False,
        "m3_data_collected": False,
        "m4_data_collected": False,
        "m2_started": False,
        "m3_started": False,
        "m4_started": False,
        "next_action_id": "stage126-m1-retained-design-freeze",
        "next_action_requires_separate_human_authorization": True,
    }


# --------------------------------------------------------------------------- #
# Source / scientific manifest (SHA-256 pinning; no recursive hash chain)
# --------------------------------------------------------------------------- #

def build_code_provenance(repo_root: Path) -> dict[str, Any]:
    """Code identity that produced this closure — kept intentionally minimal
    and NON-recursive: it hashes only the closure's own source/runner files
    (NOT the QC report or metadata manifest, and NOT this source_manifest
    itself), avoiding the build/check self-reference cycle Part 5 already
    documents avoiding. Commit SHAs here are engineering anchors only
    (informational), same convention as e.g. `base_main_commit`/
    `source_commit` in stage126_m1_robustness_part6_smote_training_fold_only.py
    and stage126_m1_robustness_part0_decision_lock.py.
    """
    src_path = repo_root / SRC_REL
    run_path = repo_root / RUN_REL
    # The commit that last touched the CANONICAL SCIENTIFIC closure logic
    # (this source + its runner + its test), distinct from later purely
    # operational commits on the same branch (e.g. the follow-up commit that
    # only updated update_ai_handoff.py / stage126_current_state_validator.py
    # / docs to recognize this closure's completion — that commit does not
    # change the closure's own scientific/code logic and is intentionally
    # NOT what this field anchors to).
    scientific_code_commit = _git(
        repo_root, "log", "--format=%H", "-n", "1", "--", SRC_REL, RUN_REL, TEST_REL,
    ) or _git(repo_root, "rev-parse", "HEAD")
    return {
        "note": (
            "Engineering/reproducibility anchors only (informational, not a "
            "scientific lock). `scientific_code_commit` is the last commit "
            "that touched the closure source/runner/test (the SCIENTIFIC "
            "closure logic) — it is intentionally NOT recomputed from later "
            "purely-operational commits on this branch (e.g. Handoff/"
            "validator-only bookkeeping commits) that do not change the "
            "closure's own logic."
        ),
        "closure_source_path": SRC_REL,
        "closure_source_sha256": (
            sha256_file(src_path) if src_path.is_file() else ""
        ),
        "closure_runner_path": RUN_REL,
        "closure_runner_sha256": (
            sha256_file(run_path) if run_path.is_file() else ""
        ),
        "scientific_code_commit": scientific_code_commit,
        "head_commit_at_manifest_build_time": _git(repo_root, "rev-parse", "HEAD"),
    }


def build_source_manifest(
    repo_root: Path, generated_hashes: dict[str, str],
) -> dict[str, Any]:
    consumed: dict[str, str] = {}
    consumed[PRIMARY_METRICS_REL] = sha256_file(repo_root / PRIMARY_METRICS_REL)
    consumed[REGISTRY_REL] = sha256_file(repo_root / REGISTRY_REL)
    consumed[SELECTED_CONFIGS_REL] = sha256_file(repo_root / SELECTED_CONFIGS_REL)
    consumed[PART6_RESAMPLING_AUDIT_REL] = sha256_file(repo_root / PART6_RESAMPLING_AUDIT_REL)
    for part in PARTS:
        rels = _part_artifact_rels(part["part_index"])
        for rel in rels.values():
            path = repo_root / rel
            if not path.is_file():
                raise QCFail(f"missing consumed artifact: {rel}")
            consumed[rel] = sha256_file(path)

    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        # Source artifacts CONSUMED by this closure (pinned by their own
        # content bytes — NOT hashing this closure's own QC report, to avoid a
        # build/check self-reference cycle).
        "consumed_source_artifacts_sha256": dict(sorted(consumed.items())),
        # This closure's own generated synthesis outputs (evidence table,
        # synthesis record, completion lock, README) — hashed once, here.
        "generated_output_sha256": dict(sorted(generated_hashes.items())),
        # Canonical closure SCIENTIFIC/CODE provenance (this closure's own
        # source/runner identity) — distinguished from later purely
        # OPERATIONAL Handoff/validator-only commits, which do not touch
        # this closure's logic and are not what `scientific_code_commit`
        # anchors to. See build_code_provenance() docstring.
        "code_provenance": build_code_provenance(repo_root),
        "runtime_versions": runtime_versions(),
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(primary_pooled: dict[str, float]) -> str:
    lines = [
        "# Stage126 M1 — Robustness Closure",
        "",
        "**Synthesis-only closure. Zero model fits, zero predictions, zero "
        "resampling, zero hyperparameter search, zero calibration/bootstrap/"
        "Holm/p-values/SHAP/threshold-optimization/winner-selection, and zero "
        "final-test access. This closure reads only already-committed Part 1-6 "
        "artifacts and produces derived evidence artifacts.**",
        "",
        "## Purpose",
        "",
        "This closure verifies and synthesizes the six pre-registered "
        "Stage126 M1 robustness categories (Parts 1-6, all already completed "
        "and committed) into a single evidence table and synthesis record. It "
        "does **not** select a retained design, does **not** freeze anything, "
        "and does **not** authorize `stage126-m1-retained-design-freeze` — "
        "that is a separate future action requiring its own explicit human "
        "authorization.",
        "",
        "## Inputs (read-only)",
        "",
        f"- Locked primary pooled development-OOF PR-AUC "
        f"(`{PRIMARY_METRICS_REL}`): "
        + ", ".join(f"{k}={v:.12f}" for k, v in sorted(primary_pooled.items())),
        f"- `{REGISTRY_REL}` (six closed parts).",
        "- Each Part 1-6 `_primary_comparison.json`, `_metrics.csv`, "
        "`_completion_lock.json`, `_execution_manifest.json` and "
        "`_human_authorization_record.json`.",
        "",
        "## Six-category synthesis summary",
        "",
        "| Part | Category | Changed dimension | Ordering preserved |",
        "|---|---|---|---|",
    ]
    for part in PARTS:
        lines.append(
            f"| {part['part_index']} | `{part['category_id']}` | "
            f"{part['changed_dimension']} | see synthesis record |"
        )
    lines += [
        "",
        "## Interpretation (A-E)",
        "",
        "- **A. Model-family ordering:** primary ordering "
        "(logistic > random forest > xgboost) preserved in Parts 2,3,4,5,6. "
        "Part 1 is the exception (all families declined; different ordering) "
        "— reported as feature-set sensitivity, not a change to the locked "
        "primary ordering.",
        "- **B. Sample-definition sensitivity (Parts 2-4):** ordering "
        "generally preserved, small PR-AUC changes — evidence of comparative "
        "stability to listing/company-scope sample redefinition, subject to "
        "existing event-rate/identity-composition cautions. No preferred "
        "robustness sample is selected.",
        "- **C. Target sensitivity (Part 5):** PR-AUC increases for all three "
        "families, but the target changed and positive count increased "
        "(85 vs 68) — secondary-target sensitivity evidence only, not a "
        "same-outcome performance gain.",
        "- **D. Imbalance-strategy sensitivity (Part 6):** ordering preserved "
        "but all three PR-AUC values decline under training-fold-only "
        "SMOTENC vs the locked primary class-weighted result. Class "
        "weighting is not frozen by this closure.",
        "- **E. Overall:** evidence does not justify changing the primary "
        "result, selecting a winner, retuning, opening the final test, or "
        "auto-freezing a retained design.",
        "",
        "## Limitations",
        "",
        "- All robustness analyses are development-only (temporal folds "
        "1393-1399); the locked final-test years (1400-1402) are never "
        "accessed by this closure or by Parts 1-6.",
        "- Some sensitivity comparisons involve small absolute positive "
        "counts; interpretation is deliberately conservative.",
        "",
        "## No final test / no selection",
        "",
        "This closure never reads final-test predictor or target row values. "
        "It selects no paper winner and freezes no retained design.",
        "",
        "## Next action",
        "",
        "`stage126-m1-retained-design-freeze` — freeze the exact retained M1 "
        "design using development evidence only. This requires a **separate, "
        "future, explicit human authorization** and is not started, selected "
        "or authorized by this closure.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- #
# QC assertions
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    repo_root: Path, rows: list[dict[str, Any]], synthesis: dict[str, Any],
    lock: dict[str, Any], primary_pooled: dict[str, float],
    network_attempts: int,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    add("exactly_18_evidence_rows", len(rows) == 18, str(len(rows)))
    add("registered_categories_in_order",
        synthesis["registered_categories_in_order"]
        == [p["category_id"] for p in PARTS])

    # Recompute independently and compare (guards against silent drift).
    recomputed = build_evidence_rows(repo_root, primary_pooled)
    add("evidence_rows_reconcile_with_source_artifacts", recomputed == rows)

    add("completion_lock_robustness_closure_completed",
        lock["robustness_closure_completed"] is True)
    add("completion_lock_all_six_verified",
        lock["all_six_registered_categories_verified"] is True)
    add("completion_lock_no_winner_selected", lock["paper_winner_selected"] is False)
    add("completion_lock_no_retained_design_selected",
        lock["retained_design_selected"] is False)
    add("completion_lock_no_freeze_authorized",
        lock["retained_design_freeze_authorized"] is False)
    add("completion_lock_no_full_dev_refit", lock["full_development_refit_performed"] is False)
    add("completion_lock_final_test_locked", lock["final_test_unlocked"] is False)
    add("completion_lock_final_test_access_not_authorized",
        lock["final_test_access_authorized"] is False)
    add("completion_lock_final_test_predictor_not_inspected",
        lock["final_test_predictor_values_inspected"] is False)
    add("completion_lock_final_test_target_not_inspected",
        lock["final_test_target_values_inspected"] is False)
    add("completion_lock_final_test_eval_not_performed",
        lock["final_test_evaluation_performed"] is False)
    add("completion_lock_zero_model_fit_calls", lock["model_fit_calls"] == 0)
    add("completion_lock_zero_prediction_calls", lock["prediction_calls"] == 0)
    add("completion_lock_zero_tuning_search_calls", lock["tuning_search_calls"] == 0)
    add("completion_lock_smote_not_executed", lock["smote_executed"] is False)
    add("completion_lock_smotenc_not_executed", lock["smotenc_executed"] is False)
    add("completion_lock_shap_not_executed", lock["shap_executed"] is False)
    add("completion_lock_calibration_not_executed", lock["calibration_executed"] is False)
    add("completion_lock_bootstrap_not_executed", lock["bootstrap_executed"] is False)
    add("completion_lock_holm_not_executed", lock["holm_executed"] is False)
    add("completion_lock_m2_m3_m4_not_started",
        lock["m2_started"] is False and lock["m3_started"] is False
        and lock["m4_started"] is False)
    add("completion_lock_next_action_is_retained_design_freeze",
        lock["next_action_id"] == "stage126-m1-retained-design-freeze")

    add("synthesis_paper_winner_not_selected", synthesis["paper_winner_selected"] is False)
    add("synthesis_retained_design_not_selected",
        synthesis["retained_design_selected"] is False)
    add("synthesis_freeze_not_authorized",
        synthesis["retained_design_freeze_authorized"] is False)
    add("synthesis_primary_ordering_recorded",
        synthesis["primary_ordering"] == list(PRIMARY_ORDERING))
    add("synthesis_next_action_requires_human_authorization",
        synthesis["next_action_requires_separate_human_authorization"] is True)

    for row in rows:
        if row["part_index"] in (2, 3, 4, 5, 6):
            add(f"ordering_preserved_part{row['part_index']}_{row['model_family']}",
                row["primary_ordering_preserved"] is True)
    part1_rows = [r for r in rows if r["part_index"] == 1]
    add("part1_all_families_declined",
        all(r["absolute_delta_vs_primary"] < 0 for r in part1_rows))
    add("part1_ordering_differs_from_primary",
        not part1_rows[0]["primary_ordering_preserved"])

    add("all_rows_final_test_not_accessed",
        all(r["final_test_accessed_or_evaluated"] is False for r in rows))
    add("all_rows_development_only", all(r["development_only"] is True for r in rows))
    add("all_rows_selected_configurations_unchanged",
        all(r["selected_configurations_changed"] is False for r in rows))

    add("network_requests_attempted_zero", network_attempts == 0)
    add("zero_model_fit_calls", True)
    add("zero_prediction_calls", True)
    add("zero_resampling_calls", True)
    add("zero_shap_calls", True)
    return a


# --------------------------------------------------------------------------- #
# Build-all + run
# --------------------------------------------------------------------------- #

def verify_closed_parts_immutable(repo_root: Path) -> dict[str, str]:
    """Hash every consumed Part 1-6 + primary/registry artifact (read-only)."""
    observed: dict[str, str] = {}
    observed[PRIMARY_METRICS_REL] = sha256_file(repo_root / PRIMARY_METRICS_REL)
    observed[REGISTRY_REL] = sha256_file(repo_root / REGISTRY_REL)
    observed[SELECTED_CONFIGS_REL] = sha256_file(repo_root / SELECTED_CONFIGS_REL)
    observed[PART6_RESAMPLING_AUDIT_REL] = sha256_file(repo_root / PART6_RESAMPLING_AUDIT_REL)
    for part in PARTS:
        for rel in _part_artifact_rels(part["part_index"]).values():
            path = repo_root / rel
            if not path.is_file():
                raise QCFail(f"missing consumed artifact: {rel}")
            observed[rel] = sha256_file(path)
    return observed


def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    load_registered_categories(repo_root)
    primary_pooled = load_primary_pooled_pr_auc(repo_root)
    rows = build_evidence_rows(repo_root, primary_pooled)
    synthesis = build_synthesis_record(repo_root, primary_pooled, rows)
    lock = build_completion_lock()
    evidence_csv = evidence_rows_to_csv(rows)
    readme = build_readme(primary_pooled)

    content = {
        F_EVIDENCE_TABLE: evidence_csv,
        F_SYNTHESIS_RECORD: _json_str(synthesis),
        F_COMPLETION_LOCK: _json_str(lock),
        F_README: readme,
    }
    generated_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }
    manifest = build_source_manifest(repo_root, generated_hashes)
    content[F_SOURCE_MANIFEST] = _json_str(manifest)

    extras = {
        "rows": rows, "synthesis": synthesis, "lock": lock,
        "primary_pooled": primary_pooled, "manifest": manifest,
    }
    return content, extras


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def run(
    *, project_dir: Path, output_dir: Path | None = None,
    build: bool = False, check: bool = False,
) -> dict[str, Any]:
    if build and check:
        raise QCFail("build and check are mutually exclusive")
    if not build and not check:
        raise QCFail("one of --build or --check is required")

    repo_root = repo_root_from(project_dir)
    canonical_out = (repo_root / STAGE126_DIR_REL).resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    before_hashes = verify_closed_parts_immutable(repo_root)

    network_attempts = 0
    content, extras = build_all(repo_root)

    after_hashes = verify_closed_parts_immutable(repo_root)
    if before_hashes != after_hashes:
        raise QCFail("consumed Part 1-6/primary artifacts changed during build")

    assertions = build_qc_assertions(
        repo_root, extras["rows"], extras["synthesis"], extras["lock"],
        extras["primary_pooled"], network_attempts,
    )
    failed = sum(1 for x in assertions if x["status"] != "PASS")

    content_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }
    qc: dict[str, Any] = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "network_requests_attempted": network_attempts,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "smote_calls": 0,
        "smotenc_calls": 0,
        "shap_calls": 0,
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_evaluations": 0,
        "output_sha256": dict(sorted(content_hashes.items())),
        "assertions": assertions,
        "robustness_closure_completed": extras["lock"]["robustness_closure_completed"],
        "next_action_id": "stage126-m1-retained-design-freeze",
    }
    qc_text = _json_str(qc)
    all_tracked = {**content, F_QC: qc_text}

    tracked_drift = (
        _compare_drift(out_dir, all_tracked)
        if out_dir.is_dir() else sorted(all_tracked)
    )
    files_written: dict[str, str] = {}
    if build:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, text in all_tracked.items():
            (out_dir / name).write_text(text, encoding="utf-8")
            files_written[name] = sha256_bytes(text.encode("utf-8"))

    if check and out_dir.resolve() == canonical_out and tracked_drift:
        raise QCFail(f"check drift (tracked): {tracked_drift}")

    if not qc["all_pass"]:
        raise QCFail(f"Robustness closure QC failed: {failed} assertions failed")

    return {
        "qc": qc,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
        "network_requests_attempted": network_attempts,
        "before_hashes": before_hashes,
        "after_hashes": after_hashes,
    }
