"""Stage128 — ``stage128-m2-retained-block-human-decision``.

Record the HUMAN retained-block decision that the completed paired M2-versus-M1
incremental evaluation (PR #71, roadmap item 24) deliberately left open.

What this module is
-------------------
A **decision recorder**. It reads already-committed evidence, re-verifies the
exact human authorization, re-derives every reported number from the committed
PR #71 artifacts, and writes a small decision package. It is *not* a scientific
runner:

* it never fits an estimator, never predicts, never resamples;
* it never touches a final-test predictor or target value;
* it never refits on the full development period;
* it never starts, authorizes or prepares M3 or M4;
* it never rewrites a historical D0/D2 Gate result or any PR #71 artifact.

The decision recorded is ``RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK``: M2
stays the intermediate block of the preregistered nested chain M1→M2→M3→M4 and
the comparator for a future paired ``M3 − M2`` evaluation. It is a
**governance/design** decision, **not** a superiority decision. The observed M2
development evidence is approximately null (all three 95% paired-bootstrap
PR-AUC intervals include zero, point-estimate signs disagree across families)
and is preserved and reported as such.

No-execution guarantee
----------------------
``FORBIDDEN_RUNTIME_MODULES`` lists the estimator / resampling libraries this
module must never pull in, and :func:`assert_no_estimator_runtime` fails closed
if any of them is imported by this module's import graph. The module imports
only the standard library.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

ACTION_ID = "stage128-m2-retained-block-human-decision"
DECISION_ID = ACTION_ID
CONTRACT_ID = "stage128_m2_retained_block_human_decision"
CONTRACT_VERSION = "stage128_m2_retained_block_human_decision_v1"
DECISION_TYPE = "human_retained_block_decision_only_no_scientific_execution"
DECISION_OUTCOME = "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK"
REPOSITORY = "abtinasg/papermali"
BASELINE_BRANCH = "main"
BASELINE_COMMIT = "bdac807788b377690be0a879765cfe4ac148970d"

#: The next research action. A pointer is NOT an authorization.
NEXT_RESEARCH_ACTION_ID = "stage128-m3-macro-data-gate"
PREDECESSOR_ACTION_ID = "stage127-m2-incremental-evaluation"

PACKAGE_DIR_REL = "project/stage128/m2_retained_block_human_decision"

README_REL = (
    f"{PACKAGE_DIR_REL}/"
    "README_STAGE128_M2_RETAINED_BLOCK_HUMAN_DECISION.md"
)
DECISION_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m2_retained_block_human_decision.json"
)
AUTHORIZATION_REL = (
    f"{PACKAGE_DIR_REL}/"
    "stage128_m2_retained_block_human_authorization_record.json"
)
METADATA_REL = (
    f"{PACKAGE_DIR_REL}/"
    "metadata_and_hashes_stage128_m2_retained_block_human_decision.json"
)
QC_REL = (
    f"{PACKAGE_DIR_REL}/"
    "stage128_m2_retained_block_human_decision_qc_report.json"
)

# --------------------------------------------------------------------------- #
# Exact human authorization
# --------------------------------------------------------------------------- #

#: The EXACT human source utterance, one UTF-8 line, no trailing newline. This
#: is verbatim human text and is authoritative ONLY in the authorization
#: record artifact. Never paraphrase it into a field that implies verbatimness.
HUMAN_SOURCE_UTTERANCE = (
    "با حفظ M2 به‌عنوان بلوک میانی در زنجیره تأییدی M1→M2→M3→M4 موافقم. "
    "این تصمیم به معنی بهتر بودن M2، انتخاب مدل نهایی یا بازشدن final test "
    "نیست."
)
HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH = 240
HUMAN_SOURCE_UTTERANCE_SHA256 = (
    "91edbdedbf69fd3af4ec5a378b1b0506ed4df941f1331be91755068c6fb6e2b4"
)

#: DERIVED, NON-VERBATIM restatement of the authorized scope. It is labelled as
#: derived everywhere it appears and must never be presented as human text.
NORMALIZED_AUTHORIZATION_SCOPE = (
    "ناظر انسانی و مالک تصمیم پژوهشی، فقط و فقط ثبت تصمیم «نگه‌داشتن M2 "
    "به‌عنوان بلوک میانی زنجیره تأییدی از پیش‌ثبت‌شده M1→M2→M3→M4» را مجاز "
    "می‌کند. این مجوز صریحاً به معنی برتری پیش‌بینی M2، معناداری آماری، "
    "انتخاب بلوک برنده، انتخاب مدل نهایی، بازبرازش کامل دوره توسعه، یا باز "
    "شدن/دسترسی به آزمون نهایی نیست، و هیچ اجازه‌ای برای شروع M3 یا M4 ایجاد "
    "نمی‌کند. محدود به یک اقدام "
    "(stage128-m2-retained-block-human-decision) است و با ثبت و تأیید همین "
    "تصمیم مصرف می‌شود."
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RetainedBlockDecisionError(RuntimeError):
    """Raised whenever any fail-closed precondition is violated."""


def verify_human_authorization() -> dict[str, Any]:
    """Recompute the authorization byte length and SHA-256; fail closed."""
    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    if len(raw) != HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH:
        raise RetainedBlockDecisionError(
            f"human authorization byte length {len(raw)} != "
            f"{HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH}"
        )
    digest = hashlib.sha256(raw).hexdigest()
    if digest != HUMAN_SOURCE_UTTERANCE_SHA256:
        raise RetainedBlockDecisionError(
            f"human authorization sha256 {digest} != "
            f"{HUMAN_SOURCE_UTTERANCE_SHA256}"
        )
    if HUMAN_SOURCE_UTTERANCE.endswith("\n"):
        raise RetainedBlockDecisionError(
            "human authorization must be one line with no trailing newline"
        )
    if NORMALIZED_AUTHORIZATION_SCOPE == HUMAN_SOURCE_UTTERANCE:
        raise RetainedBlockDecisionError(
            "normalized scope must be derived, not the verbatim human text"
        )
    return {
        "human_source_utterance_byte_length": len(raw),
        "human_source_utterance_sha256": digest,
        "normalized_authorization_scope_sha256": _sha256_text(
            NORMALIZED_AUTHORIZATION_SCOPE),
    }


# --------------------------------------------------------------------------- #
# No-execution guarantee
# --------------------------------------------------------------------------- #

#: Estimator / resampling runtimes this decision recorder must never import.
FORBIDDEN_RUNTIME_MODULES: tuple[str, ...] = (
    "sklearn",
    "xgboost",
    "imblearn",
    "shap",
    "lightgbm",
    "catboost",
    "statsmodels",
)

#: Estimator entry points this decision recorder must never call.
FORBIDDEN_ESTIMATOR_CALLS: tuple[str, ...] = (
    "fit",
    "fit_predict",
    "fit_resample",
    "fit_transform",
    "predict",
    "predict_proba",
    "decision_function",
    "resample",
)


def assert_no_estimator_runtime() -> None:
    """Fail closed if an estimator/resampling runtime reached this process.

    Only modules this package pulled in are relevant, so the check is applied
    to this module's own import graph: it imports the standard library only.
    """
    own = sys.modules[__name__]
    imported = {
        name for name, value in vars(own).items()
        if getattr(value, "__name__", "") in FORBIDDEN_RUNTIME_MODULES
    }
    if imported:
        raise RetainedBlockDecisionError(
            f"forbidden estimator runtime imported: {sorted(imported)}"
        )


# --------------------------------------------------------------------------- #
# Frozen M2 definition (retained exactly as already evaluated)
# --------------------------------------------------------------------------- #

M1_FEATURE_ORDER: tuple[str, ...] = (
    "log_total_assets",
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
)
M2_ADDED_FEATURES: tuple[str, ...] = (
    "equity_return_window",
    "realized_volatility",
    "amihud_illiquidity",
)
M2_FEATURE_ORDER: tuple[str, ...] = M1_FEATURE_ORDER + M2_ADDED_FEATURES
EQUITY_RETURN_WINDOW_SEMANTICS = "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN"
EQUITY_RETURN_WINDOW_CALENDAR = "Gregorian"
#: Eligibility-audit-only; never an M2 predictor.
AUDIT_ONLY_FIELD = "zero_trade_day_ratio_W"

CONFIRMATORY_FAMILY: tuple[str, ...] = (
    "M2_minus_M1",
    "M3_minus_M2",
    "M4_minus_M3",
)
NESTED_CHAIN: tuple[str, ...] = ("M1", "M2", "M3", "M4")

# --------------------------------------------------------------------------- #
# Expected, source-derived evidence (all re-verified against PR #71 artifacts)
# --------------------------------------------------------------------------- #

EXPECTED_COMMON_SAMPLE = {
    "rows": 539,
    "parent_rows": 666,
    "positive": 55,
    "negative": 484,
    "companies": 108,
}
EXPECTED_ATTRITION = {
    "rows": 127,
    "parent_rows": 666,
    "positive": 13,
    "negative": 114,
    "distinct_companies": 53,
    "fraction": 0.190690690691,
}
EXPECTED_POOLED_OOF = {"rows": 366, "positive": 28}
EXPECTED_ELIGIBILITY_AUDIT = {
    "comparison_count": 53,
    "flagged_comparison_count": 35,
    "smd_flag_threshold": 0.1,
}
EXPECTED_PR_AUC_DELTAS: dict[str, dict[str, float]] = {
    "regularized_logistic_regression": {
        "delta": 0.008530265112,
        "ci_lower": -0.021177343686,
        "ci_upper": 0.035281506756,
    },
    "random_forest": {
        "delta": -0.007313160157,
        "ci_lower": -0.049131999282,
        "ci_upper": 0.031850216682,
    },
    "xgboost": {
        "delta": 0.018802067544,
        "ci_lower": -0.026163341118,
        "ci_upper": 0.072970509355,
    },
}

SOURCE_DIR_REL = "project/stage128/m2_incremental_evaluation"
SRC_DECISION_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_incremental_evaluation_decision.json"
)
SRC_BOOTSTRAP_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_paired_bootstrap_delta_summary.json"
)
SRC_ATTRITION_REL = (
    f"{SOURCE_DIR_REL}/"
    "stage127_m2_parent_to_common_sample_attrition_audit.json"
)
SRC_JOIN_REL = f"{SOURCE_DIR_REL}/stage127_m2_common_sample_join_audit.json"
SRC_ELIGIBILITY_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_post_lock_d2_eligibility_audit.json"
)
SRC_ELIGIBILITY_SMD_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_post_lock_d2_eligibility_smd.csv"
)
SRC_MULTIPLICITY_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_multiplicity_family_status.json"
)
SRC_FIREWALL_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_final_test_firewall_audit.json"
)
SRC_FIT_COUNT_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_predictive_fit_count_audit.json"
)
SRC_FEATURE_MANIFEST_REL = (
    f"{SOURCE_DIR_REL}/stage127_m2_feature_configuration_manifest.json"
)
SRC_METRICS_REL = f"{SOURCE_DIR_REL}/stage127_m2_block_model_metrics.csv"
SRC_OOF_REL = f"{SOURCE_DIR_REL}/stage127_m2_paired_oof_predictions.csv"
SRC_CALIBRATION_REL = f"{SOURCE_DIR_REL}/stage127_m2_calibration_report.json"

#: Pinned immutable evidence outside the PR #71 package.
PINNED_EXTERNAL_SOURCES: tuple[str, ...] = (
    "project/stage128/stage128_m2_d2_development_features.csv",
    "project/stage126/stage126_m1_retained_design_freeze.json",
    "project/stage126/stage126_m1_selected_configurations.json",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
)

#: Every PR #71 scientific artifact that must remain byte-identical.
PINNED_PR71_SOURCES: tuple[str, ...] = (
    SRC_DECISION_REL,
    SRC_BOOTSTRAP_REL,
    SRC_ATTRITION_REL,
    SRC_JOIN_REL,
    SRC_ELIGIBILITY_REL,
    SRC_ELIGIBILITY_SMD_REL,
    SRC_MULTIPLICITY_REL,
    SRC_FIREWALL_REL,
    SRC_FIT_COUNT_REL,
    SRC_FEATURE_MANIFEST_REL,
    SRC_METRICS_REL,
    SRC_OOF_REL,
    SRC_CALIBRATION_REL,
)

TOLERANCE = 1e-12


def _load_json(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        raise RetainedBlockDecisionError(f"missing source artifact: {rel}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
        raise RetainedBlockDecisionError(
            f"unreadable source artifact {rel}: {exc}") from exc


def _close(observed: Any, expected: float) -> bool:
    return isinstance(observed, (int, float)) and abs(
        float(observed) - expected) <= TOLERANCE


# --------------------------------------------------------------------------- #
# Source-derived evidence
# --------------------------------------------------------------------------- #

def read_source_evidence(root: Path) -> dict[str, Any]:
    """Re-derive every reported number from the committed PR #71 artifacts."""
    decision = _load_json(root, SRC_DECISION_REL)
    bootstrap = _load_json(root, SRC_BOOTSTRAP_REL)
    attrition = _load_json(root, SRC_ATTRITION_REL)
    join = _load_json(root, SRC_JOIN_REL)
    eligibility = _load_json(root, SRC_ELIGIBILITY_REL)
    multiplicity = _load_json(root, SRC_MULTIPLICITY_REL)
    features = _load_json(root, SRC_FEATURE_MANIFEST_REL)

    if decision.get("decision_id") != PREDECESSOR_ACTION_ID:
        raise RetainedBlockDecisionError(
            "source decision artifact is not the M2 incremental evaluation")
    if decision.get("human_retained_block_decision_required") is not True:
        raise RetainedBlockDecisionError(
            "source decision does not record an open retained-block question")

    common = attrition.get("common_sample") or {}
    dropped = attrition.get("dropped_by_d2_ineligibility") or {}
    parent = attrition.get("parent_development") or {}
    pooled = attrition.get("common_pooled_oof") or {}

    observed = {
        "common_sample": {
            "rows": common.get("rows"),
            "parent_rows": parent.get("rows"),
            "positive": common.get("positive"),
            "negative": common.get("negative"),
            "companies": common.get("companies"),
        },
        "attrition": {
            "rows": attrition.get("attrition_rows"),
            "parent_rows": parent.get("rows"),
            "positive": dropped.get("positive"),
            "negative": dropped.get("negative"),
            "distinct_companies": dropped.get("companies"),
            "fraction": attrition.get("attrition_fraction"),
        },
        "pooled_locked_validation_oof": {
            "rows": pooled.get("rows"),
            "positive": pooled.get("positive"),
        },
        "post_lock_d2_eligibility_audit": {
            "comparison_count": eligibility.get("comparison_count"),
            "flagged_comparison_count": eligibility.get(
                "flagged_comparison_count"),
            "smd_flag_threshold": eligibility.get("smd_flag_threshold"),
        },
    }

    # --- exact counts ---------------------------------------------------- #
    for key, expected in (
        ("common_sample", EXPECTED_COMMON_SAMPLE),
        ("pooled_locked_validation_oof", EXPECTED_POOLED_OOF),
        ("post_lock_d2_eligibility_audit", EXPECTED_ELIGIBILITY_AUDIT),
    ):
        for field, want in expected.items():
            got = observed[key][field]
            if got != want:
                raise RetainedBlockDecisionError(
                    f"{key}.{field}={got!r} != {want!r}")
    for field, want in EXPECTED_ATTRITION.items():
        got = observed["attrition"][field]
        if field == "fraction":
            if not _close(got, want):
                raise RetainedBlockDecisionError(
                    f"attrition.fraction={got!r} != {want!r}")
        elif got != want:
            raise RetainedBlockDecisionError(
                f"attrition.{field}={got!r} != {want!r}")

    # Cross-check the join audit independently of the attrition audit.
    for field, want in (
        ("common_rows", 539), ("common_positive", 55),
        ("common_negative", 484), ("pooled_oof_rows", 366),
        ("pooled_oof_positive", 28), ("parent_rows", 666),
        ("final_test_rows_loaded", 0), ("final_test_rows_in_join", 0),
    ):
        if join.get(field) != want:
            raise RetainedBlockDecisionError(
                f"join audit {field}={join.get(field)!r} != {want!r}")

    # --- primary pooled PR-AUC deltas ------------------------------------ #
    per_family = decision.get("per_family_primary_metric") or {}
    deltas: dict[str, Any] = {}
    for family, want in EXPECTED_PR_AUC_DELTAS.items():
        row = per_family.get(family) or {}
        boot = (((bootstrap.get("by_family") or {}).get(family) or {}
                 ).get("metrics") or {}).get("pr_auc") or {}
        got = {
            "m2_minus_m1_pr_auc": row.get("m2_minus_m1_pr_auc"),
            "ci_lower": row.get("ci_lower"),
            "ci_upper": row.get("ci_upper"),
        }
        if not _close(got["m2_minus_m1_pr_auc"], want["delta"]):
            raise RetainedBlockDecisionError(
                f"{family} PR-AUC delta {got['m2_minus_m1_pr_auc']!r} != "
                f"{want['delta']!r}")
        if not _close(got["ci_lower"], want["ci_lower"]) or not _close(
                got["ci_upper"], want["ci_upper"]):
            raise RetainedBlockDecisionError(f"{family} PR-AUC CI mismatch")
        if not _close(boot.get("m2_minus_m1_delta"), want["delta"]):
            raise RetainedBlockDecisionError(
                f"{family} bootstrap delta disagrees with the decision record")
        if boot.get("ci_excludes_zero") is not False:
            raise RetainedBlockDecisionError(
                f"{family} PR-AUC interval must include zero")
        if not (float(got["ci_lower"]) <= 0.0 <= float(got["ci_upper"])):
            raise RetainedBlockDecisionError(
                f"{family} PR-AUC interval does not bracket zero")
        got["interval_includes_zero"] = True
        got["point_estimate_sign"] = (
            "positive" if float(got["m2_minus_m1_pr_auc"]) > 0 else "negative"
        )
        got["configuration_id"] = row.get("configuration_id")
        got["bootstrap_replicates"] = boot.get("bootstrap_delta_replicates")
        deltas[family] = got

    signs = {v["point_estimate_sign"] for v in deltas.values()}
    if len(signs) < 2:
        raise RetainedBlockDecisionError(
            "point-estimate signs must be recorded as disagreeing across "
            "model families")
    if decision.get("families_agree_on_point_estimate_sign") is not False:
        raise RetainedBlockDecisionError(
            "source decision must record sign disagreement across families")

    # --- multiplicity family --------------------------------------------- #
    if tuple(multiplicity.get("confirmatory_family") or ()) != \
            CONFIRMATORY_FAMILY:
        raise RetainedBlockDecisionError("confirmatory family changed")
    if multiplicity.get("holm_family_complete") is not False:
        raise RetainedBlockDecisionError("Holm family must remain incomplete")
    if multiplicity.get("holm_final_adjustment_deferred") is not True:
        raise RetainedBlockDecisionError("Holm adjustment must remain deferred")

    # --- frozen M2 definition -------------------------------------------- #
    if tuple(features.get("m1_feature_order") or ()) != M1_FEATURE_ORDER:
        raise RetainedBlockDecisionError("M1 feature order changed")
    if tuple(features.get("m2_feature_order") or ()) != M2_FEATURE_ORDER:
        raise RetainedBlockDecisionError("M2 feature order changed")
    if tuple(features.get("m2_market_features") or ()) != M2_ADDED_FEATURES:
        raise RetainedBlockDecisionError("M2 market features changed")
    if features.get("equity_return_window_implementation") != \
            EQUITY_RETURN_WINDOW_SEMANTICS:
        raise RetainedBlockDecisionError("D2 equity-return semantics changed")
    if AUDIT_ONLY_FIELD in tuple(features.get("m2_feature_order") or ()):
        raise RetainedBlockDecisionError(
            f"{AUDIT_ONLY_FIELD} must remain eligibility-audit-only")
    if features.get("m2_is_nested_superset_of_m1") is not True:
        raise RetainedBlockDecisionError("M2 must remain nested in M1")

    return {
        "counts": observed,
        "pr_auc_deltas": deltas,
        "all_primary_intervals_include_zero": True,
        "families_agree_on_point_estimate_sign": False,
        "observed_point_estimate_signs": {
            f: v["point_estimate_sign"] for f, v in deltas.items()},
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "confirmatory_family": list(CONFIRMATORY_FAMILY),
    }


def source_artifact_hashes(root: Path) -> dict[str, str]:
    """SHA-256 of every pinned immutable source artifact."""
    out: dict[str, str] = {}
    for rel in tuple(PINNED_PR71_SOURCES) + PINNED_EXTERNAL_SOURCES:
        path = root / rel
        if not path.is_file():
            raise RetainedBlockDecisionError(f"missing pinned source: {rel}")
        out[rel] = _sha256_file(path)
    return out


# --------------------------------------------------------------------------- #
# Whole-tree protected immutability manifest
# --------------------------------------------------------------------------- #

#: Every tracked file under these trees, AS OF ``BASELINE_COMMIT``, is
#: protected. New tracked files appearing inside them are a violation too.
PROTECTED_TREES: tuple[str, ...] = (
    "project/stage128/m2_incremental_evaluation",
    "project/stage127",
)

#: Individually protected files outside the protected trees.
PROTECTED_EXTRA_FILES: tuple[str, ...] = (
    "project/stage128/stage128_m2_d2_development_features.csv",
    "project/stage126/stage126_m1_retained_design_freeze.json",
    "project/stage126/stage126_m1_selected_configurations.json",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
)


def _git(root: Path, *args: str) -> str:
    """Run a read-only git command; fail closed on a non-zero exit."""
    import subprocess

    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RetainedBlockDecisionError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _tracked_files_under(root: Path, commit: str) -> tuple[str, ...]:
    """Tracked paths under :data:`PROTECTED_TREES` at ``commit``."""
    out = _git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--",
               *PROTECTED_TREES)
    return tuple(sorted(p for p in out.split("\0") if p))


def enumerate_protected_baseline_files(root: Path) -> tuple[str, ...]:
    """The complete protected path set, enumerated FROM the baseline commit.

    Never derived from the working tree. Each extra file must also exist at
    the baseline commit, otherwise the enumeration fails closed.
    """
    paths = set(_tracked_files_under(root, BASELINE_COMMIT))
    for rel in PROTECTED_EXTRA_FILES:
        try:
            _git(root, "cat-file", "-e", f"{BASELINE_COMMIT}:{rel}")
        except RetainedBlockDecisionError as exc:
            raise RetainedBlockDecisionError(
                f"protected extra file absent at baseline {BASELINE_COMMIT}: "
                f"{rel}") from exc
        paths.add(rel)
    if not paths:
        raise RetainedBlockDecisionError(
            "protected baseline enumeration produced no files")
    return tuple(sorted(paths))


def baseline_protected_manifest(root: Path) -> dict[str, str]:
    """SHA-256 of the BASELINE bytes of every protected path.

    Baseline blobs are hashed as opaque bytes. They are never parsed, decoded
    or evaluated, so no final-test predictor or target value is ever read.
    """
    import subprocess

    paths = enumerate_protected_baseline_files(root)
    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=str(root), capture_output=True,
        input="".join(f"{BASELINE_COMMIT}:{rel}\n" for rel in paths
                      ).encode("utf-8"),
    )
    if proc.returncode != 0:
        raise RetainedBlockDecisionError(
            f"git cat-file --batch failed: {proc.stderr.decode()!r}")
    manifest: dict[str, str] = {}
    buf = proc.stdout
    pos = 0
    for rel in paths:
        nl = buf.find(b"\n", pos)
        if nl < 0:
            raise RetainedBlockDecisionError(
                f"truncated git cat-file output at {rel}")
        header = buf[pos:nl].decode("utf-8").split()
        if len(header) != 3 or header[1] != "blob":
            raise RetainedBlockDecisionError(
                f"protected baseline path is not a blob: {rel} ({header})")
        size = int(header[2])
        start = nl + 1
        manifest[rel] = hashlib.sha256(buf[start:start + size]).hexdigest()
        pos = start + size + 1  # trailing newline
    if len(manifest) != len(paths):  # pragma: no cover - defensive
        raise RetainedBlockDecisionError("incomplete baseline manifest")
    return dict(sorted(manifest.items()))


def verify_protected_immutability(
    root: Path, manifest: dict[str, str],
) -> dict[str, Any]:
    """Fail closed unless the branch reproduces the baseline byte-for-byte.

    Checks, in order:

    * the persisted manifest count equals the independently enumerated count;
    * the persisted path set equals the baseline path set;
    * every protected baseline file still exists on this branch;
    * every protected file's current bytes hash to the baseline SHA-256;
    * no NEW tracked file appeared inside a protected tree;
    * ``git diff --name-only BASELINE..HEAD -- <protected paths>`` is empty.
    """
    expected_paths = enumerate_protected_baseline_files(root)
    expected = baseline_protected_manifest(root)

    if len(manifest) != len(expected_paths):
        raise RetainedBlockDecisionError(
            f"protected manifest count {len(manifest)} != enumerated "
            f"{len(expected_paths)}")
    if tuple(sorted(manifest)) != expected_paths:
        missing = sorted(set(expected_paths) - set(manifest))
        extra = sorted(set(manifest) - set(expected_paths))
        raise RetainedBlockDecisionError(
            f"protected path set differs: missing={missing} extra={extra}")

    for rel in expected_paths:
        if manifest[rel] != expected[rel]:
            raise RetainedBlockDecisionError(
                f"stored protected hash differs from baseline blob: {rel}")
        path = root / rel
        if not path.is_file():
            raise RetainedBlockDecisionError(
                f"protected baseline file is absent on this branch: {rel}")
        if _sha256_file(path) != expected[rel]:
            raise RetainedBlockDecisionError(
                f"protected file bytes differ from baseline: {rel}")

    head_tree = set(_tracked_files_under(root, "HEAD"))
    added = sorted(head_tree - set(expected_paths))
    if added:
        raise RetainedBlockDecisionError(
            f"new tracked file(s) inside a protected tree: {added}")

    changed = [p for p in _git(
        root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD", "--",
        *expected_paths).splitlines() if p.strip()]
    if changed:
        raise RetainedBlockDecisionError(
            f"protected paths changed in committed history: {sorted(changed)}")

    return {
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_file_count": len(expected_paths),
        "protected_paths_match_baseline": True,
        "protected_bytes_match_baseline": True,
        "protected_tree_has_no_new_tracked_files": True,
        "protected_committed_history_diff_empty": True,
    }


# --------------------------------------------------------------------------- #
# Decision rationale (source-derived, never rewritten as positive support)
# --------------------------------------------------------------------------- #

RATIONALE: tuple[str, ...] = (
    "The M2 incremental comparison was development-only and completed "
    "(stage127-m2-incremental-evaluation, roadmap item 24).",
    "The exact M2 common sample was 539 of 666 development rows: 55 positive, "
    "484 negative, 108 companies.",
    "Parent-to-common-sample attrition was 127 of 666 rows (13 positive, 114 "
    "negative, 53 distinct companies), a proportion of 0.1906906907.",
    "The pooled locked-validation OOF surface was 366 rows with 28 positives.",
    "The post-lock D2 eligibility audit contained 53 comparisons of which 35 "
    "carry a descriptive |SMD| >= 0.10 flag. These flags limit interpretation "
    "only: they did not change sample membership, weighting, matching, D2 "
    "construction or model specification.",
    "Primary pooled OOF PR-AUC deltas (M2 - M1) were: regularized logistic "
    "regression +0.008530265112 [-0.021177343686, +0.035281506756]; random "
    "forest -0.007313160157 [-0.049131999282, +0.031850216682]; xgboost "
    "+0.018802067544 [-0.026163341118, +0.072970509355].",
    "All three confidence intervals include zero.",
    "Point-estimate signs disagree across model families.",
    "The observed M2 evidence is approximately null and does not support a "
    "superiority claim.",
    "Retention is justified as a governance/design decision: it preserves the "
    "prospectively defined nested confirmatory architecture and avoids "
    "post-outcome deletion or redefinition of the M3 - M2 comparator after "
    "observing the M2 results.",
    "Negative or null incremental evidence remains a reportable scientific "
    "result.",
)

M2_RETENTION_BASIS = (
    "preregistered_nested_confirmatory_architecture_preservation_not_"
    "observed_predictive_superiority"
)

RETENTION_DOES_NOT_IMPLY: tuple[str, ...] = (
    "predictive_improvement",
    "statistical_significance",
    "paper_winner_selection",
    "final_model_selection",
    "full_development_refit_authorization",
    "final_test_unlock_or_access_authorization",
    "m3_authorization",
    "m4_authorization",
)

NOT_AUTHORIZED: tuple[str, ...] = (
    "model_fit",
    "prediction",
    "new_oof_generation",
    "hyperparameter_tuning",
    "feature_search",
    "threshold_search",
    "calibration_execution",
    "bootstrap_execution",
    "holm_adjustment_execution",
    "p_value_computation",
    "smote_or_smotenc_execution",
    "shap",
    "full_development_refit",
    "final_test_predictor_value_inspection",
    "final_test_target_value_inspection",
    "final_test_prediction",
    "final_test_evaluation",
    "m3_data_collection",
    "m3_gate_execution",
    "m3_modeling",
    "m4_action_of_any_kind",
    "paper_winner_selection",
    "final_model_selection",
    "merge_of_the_resulting_pull_request",
)


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_authorization_record() -> dict[str, Any]:
    """The ONLY authoritative location of the exact human utterance."""
    checks = verify_human_authorization()
    return {
        "authorization_id": (
            "stage128-m2-retained-block-human-decision-human-authorization"),
        "authorized_action_id": ACTION_ID,
        "authorizing_role": "human_supervisor_data_owner",
        "authorization_context": (
            "Follows the Stage128 paired M2-versus-M1 incremental evaluation "
            "(PR #71), which reported approximately null development evidence "
            "and explicitly left the retained-block question open for a human "
            "decision (human_retained_block_decision_required = true)."
        ),
        "decision_type": DECISION_TYPE,
        "human_source_utterance": HUMAN_SOURCE_UTTERANCE,
        "human_source_utterance_is_verbatim_human_text": True,
        "human_source_utterance_byte_encoding": "UTF-8",
        "human_source_utterance_byte_length": checks[
            "human_source_utterance_byte_length"],
        "human_source_utterance_sha256": checks["human_source_utterance_sha256"],
        "human_source_utterance_trailing_newline": False,
        "normalized_authorization_scope": NORMALIZED_AUTHORIZATION_SCOPE,
        "normalized_authorization_scope_is_derived_not_verbatim_human_text":
            True,
        "normalized_authorization_scope_sha256": checks[
            "normalized_authorization_scope_sha256"],
        "verbatim_and_normalized_are_recorded_separately": True,
        "scope_limited_to_this_action_only": True,
        "creates_standing_authorization": False,
        "authorization_consumed_when": (
            "this retained-block decision has been recorded and verified"),
        "not_authorized": list(NOT_AUTHORIZED),
        "does_not_extend_to": [
            NEXT_RESEARCH_ACTION_ID,
            "stage128-m3-incremental-evaluation",
            "stage129-m4-governance-data-gate",
            "stage130-pre-final-design-and-claim-freeze",
            "stage131-full-development-refit",
            "stage132-locked-final-temporal-evaluation",
        ],
        "merge_authorized": False,
        "final_test_access_authorized": False,
        "full_development_refit_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "retained_block_decision_recording_authorized": True,
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
    }


def build_decision(
    root: Path,
    authorization_sha256: str,
    protected_manifest: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The main decision artifact. It never duplicates the human utterance."""
    evidence = read_source_evidence(root)
    if protected_manifest is None:
        protected_manifest = baseline_protected_manifest(root)
    return {
        "action_id": ACTION_ID,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "decision_type": DECISION_TYPE,
        "decision_outcome": DECISION_OUTCOME,
        "decision_is_a_retained_block_decision_not_a_superiority_decision":
            True,
        "stage": "Stage128",
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
        "predecessor_action_id": PREDECESSOR_ACTION_ID,
        "evidence_class": "already_committed_development_evidence_only",

        # --- authorization provenance (by reference only) ----------------- #
        "human_authorization_record_path": AUTHORIZATION_REL,
        "human_authorization_record_sha256": authorization_sha256,
        "human_authorization_record_note": (
            "The exact human utterance lives ONLY in the authorization record "
            "referenced above. This decision artifact deliberately does not "
            "duplicate verbatim human text under any field name, and the "
            "derived normalized scope is labelled as derived there."
        ),
        "human_source_utterance_duplicated_here": False,

        # --- the decision -------------------------------------------------- #
        "m2_block_retained": True,
        "m2_retention_basis": M2_RETENTION_BASIS,
        "m2_retention_does_not_imply": list(RETENTION_DOES_NOT_IMPLY),
        "m2_predictive_superiority_claim_supported": False,
        "m2_role": "intermediate_confirmatory_block",
        "nested_confirmatory_chain": list(NESTED_CHAIN),
        "m2_remains_comparator_for": "M3_minus_M2",
        "m3_minus_m2_conditional_on": (
            "a separately authorized M3 data Gate that passes"),
        "confirmatory_comparison_family": list(CONFIRMATORY_FAMILY),
        "confirmatory_comparison_family_unchanged": True,
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "approximately_null_m2_development_result_preserved_and_reported":
            True,

        # --- rationale, source-derived ------------------------------------ #
        "decision_rationale": list(RATIONALE),
        "source_derived_evidence": evidence,
        "source_artifacts_sha256": source_artifact_hashes(root),

        # --- whole-tree protected immutability manifest -------------------- #
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_file_count": len(protected_manifest),
        "protected_files_sha256": dict(protected_manifest),
        "protected_manifest_note": (
            "protected_files_sha256 is the COMPLETE SHA-256 manifest of every "
            f"tracked file that existed at baseline commit {BASELINE_COMMIT} "
            "under the protected trees, plus the individually protected extra "
            "files. The paths were enumerated from the baseline commit itself, "
            "not from the working tree, and the baseline blobs were hashed as "
            "opaque bytes without parsing or evaluating their contents. "
            "source_artifacts_sha256 above is the smaller subset of pinned "
            "artifacts whose values this decision re-derives; it is NOT the "
            "immutability scope."
        ),

        # --- frozen retained M2 definition -------------------------------- #
        "retained_m2_definition": {
            "m1_feature_order": list(M1_FEATURE_ORDER),
            "m2_added_features": list(M2_ADDED_FEATURES),
            "m2_feature_order": list(M2_FEATURE_ORDER),
            "equity_return_window_semantics":
                EQUITY_RETURN_WINDOW_SEMANTICS,
            "equity_return_window_calendar_convention":
                EQUITY_RETURN_WINDOW_CALENDAR,
            "audit_only_field_not_in_m2": AUDIT_ONLY_FIELD,
            "frozen_exactly_as_already_evaluated": True,
            "reopened_design_components": [],
        },

        # --- status flags -------------------------------------------------- #
        "m2_retained_block_decision_required": False,
        "m2_retained_block_human_decision_completed": True,
        "m2_retained_block_human_decision_authorization_consumed": True,
        "authorization_consumed": True,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_locked": True,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "m3_authorized": False,
        "m3_started": False,
        "m4_authorized": False,
        "m4_started": False,

        # --- no-execution proof -------------------------------------------- #
        "execution_audit": {
            "model_fits": 0,
            "predictions": 0,
            "new_oof_rows_generated": 0,
            "resampling_executions": 0,
            "bootstrap_executions": 0,
            "holm_adjustment_executions": 0,
            "p_value_computations": 0,
            "calibration_executions": 0,
            "shap_executions": 0,
            "full_development_refits": 0,
            "final_test_predictor_values_read": 0,
            "final_test_target_values_read": 0,
            "final_test_predictions": 0,
            "final_test_evaluations": 0,
            "m3_executions": 0,
            "m4_executions": 0,
            "scientific_artifacts_regenerated": 0,
            "forbidden_runtime_modules": list(FORBIDDEN_RUNTIME_MODULES),
            "forbidden_estimator_calls": list(FORBIDDEN_ESTIMATOR_CALLS),
            "built_only_by_reading_existing_committed_evidence": True,
        },
        "not_authorized": list(NOT_AUTHORIZED),

        # --- pointers ------------------------------------------------------ #
        "last_completed_research_action_id": ACTION_ID,
        "next_research_action_id": NEXT_RESEARCH_ACTION_ID,
        "next_research_action_pointer_is_not_authorization": True,
        "authorizes_next_action": False,
        "merge_authorized": False,
    }


def build_metadata(
    root: Path, package_sha256: dict[str, str],
    protected_manifest: dict[str, str] | None = None,
) -> dict[str, Any]:
    if protected_manifest is None:
        protected_manifest = baseline_protected_manifest(root)
    return {
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_file_count": len(protected_manifest),
        "protected_files_sha256": dict(protected_manifest),
        "contract_id": CONTRACT_ID,
        "decision_id": DECISION_ID,
        "generated_for": ACTION_ID,
        "package_artifacts_sha256": dict(sorted(package_sha256.items())),
        "source_artifacts_sha256": source_artifact_hashes(root),
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
        "immutability_requirement": (
            "Every path listed in protected_files_sha256 must remain "
            "byte-identical to its baseline bytes, no protected path may be "
            "deleted, and no new tracked file may appear inside a protected "
            "tree. protected_files_sha256 is the authoritative and complete "
            "immutability scope; source_artifacts_sha256 is only the smaller "
            "subset of artifacts whose numeric values this action re-derives. "
            "No historical D0 Gate or D2 Gate result may be rewritten by this "
            "action."
        ),
    }


README_TEXT = f"""# Stage128 — retain M2 as the intermediate confirmatory block

**Action id:** `{ACTION_ID}`
**Decision type:** `{DECISION_TYPE}`
**Decision outcome:** `{DECISION_OUTCOME}`
**Baseline:** `{REPOSITORY}` `{BASELINE_BRANCH}` @ `{BASELINE_COMMIT}`

## What was decided

M2 is **retained as the intermediate block** of the preregistered nested
confirmatory chain `M1 → M2 → M3 → M4`, and remains the comparator for a future
paired `M3 − M2` evaluation — but only if the M3 data Gate is **separately
authorized** and passes.

This is a **retained-block decision, not a superiority decision.**

## What was NOT decided

Retention does **not** imply predictive improvement, does **not** imply
statistical significance, does **not** select a paper winner, does **not**
select a final model, does **not** authorize a full-development refit, and does
**not** unlock or authorize the final test. M3 and M4 remain unauthorized and
unstarted.

## The evidence, unchanged

The M2 incremental comparison was development-only and completed under its own
one-action authorization (roadmap item 24, PR #71):

* common sample **539 / 666** development rows — 55 positive, 484 negative,
  108 companies;
* parent-to-common-sample attrition **127 / 666** rows — 13 positive, 114
  negative, 53 distinct companies (proportion `0.1906906907`);
* pooled locked-validation OOF **366 rows, 28 positive**;
* post-lock D2 eligibility audit: **53 comparisons, 35** descriptive
  `|SMD| ≥ 0.10` flags — interpretation-limiting only; they changed no sample
  membership, weighting, matching, D2 construction or model specification.

Primary pooled OOF PR-AUC deltas (M2 − M1):

| family | delta | 95% CI |
| --- | --- | --- |
| regularized logistic regression | +0.008530265112 | [−0.021177343686, +0.035281506756] |
| random forest | −0.007313160157 | [−0.049131999282, +0.031850216682] |
| xgboost | +0.018802067544 | [−0.026163341118, +0.072970509355] |

**All three intervals include zero and the point-estimate signs disagree across
model families. The observed M2 evidence is approximately null and does not
support a superiority claim.** Negative or null incremental evidence remains a
reportable scientific result, and it is reported here rather than rewritten.

## Why retain, then

Retention is a **governance/design** decision. It preserves the prospectively
defined nested confirmatory architecture and avoids post-outcome deletion or
redefinition of the `M3 − M2` comparator after the M2 results were observed.
The incomplete Holm family (`M2_minus_M1`, `M3_minus_M2`, `M4_minus_M3`) stays
incomplete and its final adjustment stays deferred.

## Exact retained M2 definition (frozen as already evaluated)

M1 base features, in exact order:

{chr(10).join('1. `' + f + '`' for f in M1_FEATURE_ORDER)}

M2 adds exactly `equity_return_window`, `realized_volatility`,
`amihud_illiquidity`. `equity_return_window` keeps its frozen D2 semantics
`{EQUITY_RETURN_WINDOW_SEMANTICS}` under the {EQUITY_RETURN_WINDOW_CALENDAR}
calendar convention. `{AUDIT_ONLY_FIELD}` remains **eligibility-audit-only** and
is not an M2 predictor. Nothing else about D2, the boundary-month convention,
`W`, `t0`, `T*`, the trading-day sequence, daily-return adjacency, the 126-return
floors, realized-volatility or Amihud construction, source evidence, coverage
thresholds, the sample rule, preprocessing, model families, selected
configurations, temporal folds, metric definitions, the bootstrap design or the
multiplicity family was reopened.

## No scientific execution

This package was built **only by reading existing committed evidence**: zero
model fits, zero predictions, zero new OOF rows, zero resampling, zero bootstrap
or Holm execution, zero p-values, zero calibration runs, zero SHAP, zero
full-development refits, and zero final-test predictor or target values read.
The builder imports the standard library only; the focused tests assert that it
cannot reach an estimator `.fit()` / `.predict()` / `.predict_proba()` or any
resampling procedure.

## Pointers

* `last_completed_research_action_id` = `{ACTION_ID}`
* `next_research_action_id` = `{NEXT_RESEARCH_ACTION_ID}`
* `next_research_action_pointer_is_not_authorization` = **true**

The M3 Gate is a pointer only. It is not authorized, no macro data was
collected, no M3 variable was created, no M3 Gate was executed and no M3 model
was fit.

## Protected immutability scope

The immutability guarantee covers **every tracked file that existed at baseline
commit `{BASELINE_COMMIT}`** under `project/stage128/m2_incremental_evaluation/`
and `project/stage127/`, plus these individually protected files:

* `project/stage128/stage128_m2_d2_development_features.csv`
* `project/stage126/stage126_m1_retained_design_freeze.json`
* `project/stage126/stage126_m1_selected_configurations.json`
* `project/stage125/part4_metrics_uncertainty_contract_stage125.json`

The path set is enumerated **from the baseline commit itself**, never from the
working tree, and the complete SHA-256 manifest of the baseline bytes is
committed as `protected_files_sha256` in both the decision artifact and the
metadata artifact (`protected_baseline_commit`, `protected_file_count`,
`protected_files_sha256`). Verification requires: every protected path still
present, every protected file byte-identical to baseline, no new tracked file
inside a protected tree, an identical path set, a manifest count equal to the
independently enumerated count, and an empty
`git diff --name-only {BASELINE_COMMIT}..HEAD` over the protected paths — a
**committed-history** comparison, not a working-tree comparison.

Baseline blobs are hashed as **opaque bytes only**. They are never parsed,
decoded or evaluated, so no final-test predictor or target value is read.

The smaller `source_artifacts_sha256` field lists only the artifacts whose
numeric values this decision re-derives. It is **not** the immutability scope.

## Package

* `stage128_m2_retained_block_human_decision.json` — the decision
* `stage128_m2_retained_block_human_authorization_record.json` — the only
  authoritative location of the exact human utterance, with the derived
  normalized scope recorded separately and labelled as derived
* `metadata_and_hashes_stage128_m2_retained_block_human_decision.json`
* `stage128_m2_retained_block_human_decision_qc_report.json`
"""


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_report(
    root: Path,
    decision: dict[str, Any],
    authorization: dict[str, Any],
    package_sha256: dict[str, str],
    pinned_before: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fail-closed QC over the recorded decision. Returns the report."""
    assertions: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        entry: dict[str, Any] = {
            "name": name, "status": "PASS" if ok else "FAIL"}
        if detail:
            entry["detail"] = detail
        assertions.append(entry)

    ev = decision["source_derived_evidence"]
    counts = ev["counts"]
    deltas = ev["pr_auc_deltas"]
    hashes = decision["source_artifacts_sha256"]

    # 1 exact authorization byte length and SHA
    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    check("authorization_byte_length_is_240",
          len(raw) == HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH)
    check("authorization_sha256_matches",
          hashlib.sha256(raw).hexdigest() == HUMAN_SOURCE_UTTERANCE_SHA256)
    check("authorization_record_reproduces_byte_length_and_sha",
          authorization["human_source_utterance_byte_length"] == 240
          and authorization["human_source_utterance_sha256"]
          == HUMAN_SOURCE_UTTERANCE_SHA256)
    # 2 verbatim vs normalized separation
    check("verbatim_and_normalized_authorization_are_separate_fields",
          authorization["human_source_utterance"] != authorization[
              "normalized_authorization_scope"]
          and authorization[
              "normalized_authorization_scope_is_derived_not_verbatim_human_"
              "text"] is True
          and authorization["verbatim_and_normalized_are_recorded_separately"]
          is True)
    check("decision_artifact_does_not_duplicate_the_human_utterance",
          HUMAN_SOURCE_UTTERANCE not in json.dumps(decision,
                                                   ensure_ascii=False)
          and decision["human_source_utterance_duplicated_here"] is False)
    check("decision_references_authorization_record_by_path_and_sha",
          decision["human_authorization_record_path"] == AUTHORIZATION_REL
          and decision["human_authorization_record_sha256"]
          == package_sha256.get(AUTHORIZATION_REL))
    # 3 baseline commit
    check("baseline_commit_is_the_canonical_main_sha",
          decision["source_main_commit"] == BASELINE_COMMIT
          and authorization["source_main_commit"] == BASELINE_COMMIT)
    # 4 decision outcome
    check("decision_outcome_is_retain_m2_as_intermediate_block",
          decision["decision_outcome"] == DECISION_OUTCOME
          and decision["decision_type"] == DECISION_TYPE
          and decision["action_id"] == ACTION_ID)
    # 5-8 retention semantics
    check("m2_block_retained_is_true", decision["m2_block_retained"] is True)
    check("m2_superiority_claim_is_false",
          decision["m2_predictive_superiority_claim_supported"] is False)
    check("no_paper_winner_selected",
          decision["paper_winner_selected"] is False)
    check("no_final_model_selected", decision["final_model_selected"] is False)
    check("retention_is_governance_not_superiority",
          decision["m2_retention_basis"] == M2_RETENTION_BASIS
          and decision[
              "decision_is_a_retained_block_decision_not_a_superiority_"
              "decision"] is True)
    # 9-11 no execution
    audit = decision["execution_audit"]
    check("zero_model_fits_and_predictions",
          audit["model_fits"] == 0 and audit["predictions"] == 0
          and audit["new_oof_rows_generated"] == 0)
    check("zero_resampling_and_new_uncertainty_execution",
          audit["resampling_executions"] == 0
          and audit["bootstrap_executions"] == 0
          and audit["holm_adjustment_executions"] == 0
          and audit["p_value_computations"] == 0
          and audit["calibration_executions"] == 0
          and audit["shap_executions"] == 0)
    check("zero_full_development_refits",
          audit["full_development_refits"] == 0
          and decision["full_development_refit_performed"] is False)
    check("builder_imports_no_estimator_runtime",
          _no_estimator_runtime_ok())
    # 12-13 final test
    check("final_test_remains_locked",
          decision["final_test_locked"] is True
          and decision["final_test_unlocked"] is False
          and decision["final_test_access_authorized"] is False
          and decision["final_test_evaluation_performed"] is False)
    check("final_test_predictor_and_target_values_uninspected",
          decision["final_test_predictor_values_inspected"] is False
          and decision["final_test_target_values_inspected"] is False
          and audit["final_test_predictor_values_read"] == 0
          and audit["final_test_target_values_read"] == 0
          and audit["final_test_predictions"] == 0
          and audit["final_test_evaluations"] == 0)
    # 14-15 successors
    check("m3_remains_unauthorized_and_unstarted",
          decision["m3_authorized"] is False
          and decision["m3_started"] is False
          and audit["m3_executions"] == 0)
    check("m4_remains_unauthorized_and_unstarted",
          decision["m4_authorized"] is False
          and decision["m4_started"] is False
          and audit["m4_executions"] == 0)
    # 16 features and D2 semantics
    rm2 = decision["retained_m2_definition"]
    check("exact_m1_and_m2_feature_lists",
          rm2["m1_feature_order"] == list(M1_FEATURE_ORDER)
          and rm2["m2_feature_order"] == list(M2_FEATURE_ORDER)
          and rm2["m2_added_features"] == list(M2_ADDED_FEATURES))
    check("frozen_d2_equity_return_semantics_preserved",
          rm2["equity_return_window_semantics"]
          == EQUITY_RETURN_WINDOW_SEMANTICS
          and rm2["equity_return_window_calendar_convention"]
          == EQUITY_RETURN_WINDOW_CALENDAR)
    check("zero_trade_day_ratio_remains_audit_only",
          AUDIT_ONLY_FIELD not in rm2["m2_feature_order"]
          and rm2["audit_only_field_not_in_m2"] == AUDIT_ONLY_FIELD)
    # 17-19 exact counts
    check("exact_common_sample_counts",
          counts["common_sample"] == EXPECTED_COMMON_SAMPLE)
    check("exact_attrition_counts",
          all(counts["attrition"][k] == v
              if k != "fraction" else _close(counts["attrition"][k], v)
              for k, v in EXPECTED_ATTRITION.items()))
    check("exact_pooled_oof_counts",
          counts["pooled_locked_validation_oof"] == EXPECTED_POOLED_OOF)
    # 20-22 deltas
    check("exact_pr_auc_deltas_and_intervals",
          all(_close(deltas[f]["m2_minus_m1_pr_auc"], w["delta"])
              and _close(deltas[f]["ci_lower"], w["ci_lower"])
              and _close(deltas[f]["ci_upper"], w["ci_upper"])
              for f, w in EXPECTED_PR_AUC_DELTAS.items()))
    check("all_primary_intervals_include_zero",
          all(float(v["ci_lower"]) <= 0.0 <= float(v["ci_upper"])
              for v in deltas.values())
          and ev["all_primary_intervals_include_zero"] is True)
    check("model_family_point_estimate_signs_disagree",
          len({v["point_estimate_sign"] for v in deltas.values()}) >= 2
          and ev["families_agree_on_point_estimate_sign"] is False)
    check("observed_evidence_recorded_as_approximately_null",
          decision[
              "approximately_null_m2_development_result_preserved_and_"
              "reported"] is True)
    # 23 eligibility audit
    check("eligibility_audit_counts_53_and_35",
          counts["post_lock_d2_eligibility_audit"]
          == EXPECTED_ELIGIBILITY_AUDIT)
    # 24 Holm
    check("holm_family_remains_incomplete_and_deferred",
          decision["holm_family_complete"] is False
          and decision["holm_final_adjustment_deferred"] is True
          and decision["confirmatory_comparison_family"]
          == list(CONFIRMATORY_FAMILY))
    # 25 byte-identical scientific artifacts
    recomputed = source_artifact_hashes(root)
    check("pinned_scientific_artifacts_are_byte_identical",
          recomputed == hashes
          and (pinned_before is None
               or all(recomputed.get(k) == v
                      for k, v in pinned_before.items()
                      if k in recomputed)),
          "recomputed SHA-256 of every pinned PR #71 and upstream artifact "
          "equals the SHA recorded in this package")
    check("all_pr71_artifacts_pinned",
          all(rel in hashes for rel in PINNED_PR71_SOURCES)
          and all(rel in hashes for rel in PINNED_EXTERNAL_SOURCES))
    # 25b complete whole-tree protected immutability manifest
    enumerated = enumerate_protected_baseline_files(root)
    stored_manifest = decision.get("protected_files_sha256") or {}
    check("protected_manifest_is_complete_and_matches_baseline_enumeration",
          decision.get("protected_baseline_commit") == BASELINE_COMMIT
          and decision.get("protected_file_count") == len(enumerated)
          and len(stored_manifest) == len(enumerated)
          and tuple(sorted(stored_manifest)) == enumerated,
          f"{len(enumerated)} protected files enumerated from baseline "
          f"{BASELINE_COMMIT}; the manifest count and path set match exactly")
    try:
        immutability = verify_protected_immutability(root, stored_manifest)
        immutability_ok, immutability_detail = True, ""
    except RetainedBlockDecisionError as exc:
        immutability = {}
        immutability_ok, immutability_detail = False, str(exc)
    check("protected_tree_is_byte_identical_to_baseline_in_committed_history",
          immutability_ok,
          immutability_detail or (
              "every protected baseline path exists, every protected file's "
              "current bytes equal the baseline bytes, no new tracked file "
              "appeared inside a protected tree, and "
              f"git diff {BASELINE_COMMIT}..HEAD over the protected paths is "
              "empty"))
    # 26 pointer
    check("next_pointer_is_m3_gate_and_is_not_authorization",
          decision["next_research_action_id"] == NEXT_RESEARCH_ACTION_ID
          and decision["next_research_action_pointer_is_not_authorization"]
          is True
          and decision["authorizes_next_action"] is False
          and decision["last_completed_research_action_id"] == ACTION_ID)
    # authorization consumption
    check("one_action_authorization_is_consumed_not_standing",
          decision["authorization_consumed"] is True
          and decision[
              "m2_retained_block_human_decision_authorization_consumed"]
          is True
          and decision["m2_retained_block_human_decision_completed"] is True
          and decision["m2_retained_block_decision_required"] is False
          and authorization["creates_standing_authorization"] is False
          and authorization["scope_limited_to_this_action_only"] is True)
    check("merge_is_not_authorized",
          decision["merge_authorized"] is False
          and authorization["merge_authorized"] is False)

    failed = [a["name"] for a in assertions if a["status"] != "PASS"]
    return {
        "contract_id": CONTRACT_ID,
        "decision_id": DECISION_ID,
        "generated_for": ACTION_ID,
        "assertion_count": len(assertions),
        "failed_count": len(failed),
        "failed_assertions": failed,
        "all_pass": not failed,
        "assertions": assertions,
        "protected_immutability": immutability or {
            "protected_baseline_commit": BASELINE_COMMIT,
            "protected_file_count": len(enumerated),
            "verification_error": immutability_detail,
        },
        "scope_note": (
            "This QC report checks the internal consistency of the Stage128 "
            "retained-block decision package: the exact human authorization, "
            "the separation of verbatim and derived text, the source-derived "
            "evidence, the frozen retained M2 definition, the complete "
            f"whole-tree byte-level immutability of the {len(enumerated)} "
            f"protected files enumerated at baseline {BASELINE_COMMIT}, and "
            "the no-execution and "
            "final-test-firewall guarantees. It re-runs no scientific "
            "computation and constitutes no scientific result."
        ),
        "checks_28_requirement_note": (
            "Roadmap/Handoff agreement (27) and clean working tree (28) are "
            "verified by the focused test file and the official validators, "
            "which run outside this in-process QC builder: "
            "project/tests/test_stage128_m2_retained_block_human_decision.py, "
            "project/run_stage126_current_state_validator.py --check and "
            "project/scripts/validate_ai_handoff.py --check."
        ),
    }


def _no_estimator_runtime_ok() -> bool:
    try:
        assert_no_estimator_runtime()
    except RetainedBlockDecisionError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

def _dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def build_package(
    repo_root: str | os.PathLike[str], write: bool = False,
) -> dict[str, Any]:
    """Build (and optionally write) the retained-block decision package."""
    assert_no_estimator_runtime()
    root = Path(repo_root)
    verify_human_authorization()

    pinned_before = source_artifact_hashes(root)
    protected_manifest = baseline_protected_manifest(root)
    verify_protected_immutability(root, protected_manifest)

    authorization = build_authorization_record()
    auth_text = json.dumps(
        authorization, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    auth_sha = _sha256_text(auth_text)

    decision = build_decision(root, auth_sha, protected_manifest)
    decision_text = json.dumps(
        decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    package_sha256 = {
        README_REL: _sha256_text(README_TEXT),
        AUTHORIZATION_REL: auth_sha,
        DECISION_REL: _sha256_text(decision_text),
    }
    metadata = build_metadata(root, package_sha256, protected_manifest)
    metadata_text = json.dumps(
        metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    qc = build_qc_report(
        root, decision, authorization, package_sha256, pinned_before)
    if not qc["all_pass"]:
        raise RetainedBlockDecisionError(
            f"retained-block QC failed: {qc['failed_assertions']}")

    if write:
        (root / README_REL).parent.mkdir(parents=True, exist_ok=True)
        (root / README_REL).write_text(README_TEXT, encoding="utf-8")
        (root / AUTHORIZATION_REL).write_text(auth_text, encoding="utf-8")
        (root / DECISION_REL).write_text(decision_text, encoding="utf-8")
        (root / METADATA_REL).write_text(metadata_text, encoding="utf-8")
        _dump(root / QC_REL, qc)
        after = source_artifact_hashes(root)
        if after != pinned_before:
            raise RetainedBlockDecisionError(
                "pinned scientific artifacts changed during the build")

    return {
        "authorization_record": authorization,
        "decision": decision,
        "metadata": metadata,
        "qc_report": qc,
        "readme_text": README_TEXT,
        "package_artifacts_sha256": package_sha256,
        "pinned_source_artifacts_sha256": pinned_before,
    }
