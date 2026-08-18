"""Focused acceptance checks for the Stage130 Phase 2 manuscript directory.

Read-only. This script computes no scientific quantity: it only compares strings
and SHA-256 digests that already exist in committed artifacts. It reads no Final
Test row and never opens the row-level prediction artifact.

Run:  python project/stage130/manuscript/validate_manuscript.py
Exit 0 when every check passes; exit 1 otherwise.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS_DIR = ROOT / "stage130" / "manuscript"
PKG = ROOT / "stage130" / "manuscript_evidence_package"
TABLES = PKG / "manuscript_results_tables"

DRAFT = MS_DIR / "manuscript_draft_en.md"
MATRIX = MS_DIR / "claim_traceability_matrix.csv"
BIB = MS_DIR / "references.bib"
AUDIT = MS_DIR / "reference_audit.csv"

FORBIDDEN_SOURCES = [
    "stage129_final_test_predictions.json",
    "part3c_outputs/analysis_ready_main_rule_a_stage125.csv",
    "part3c_outputs/audited_pairs_main_rule_a_stage125.csv",
    "part4_temporal_split_manifest_stage125.csv",
]

LEGACY_TREE = "project/outputs/09_report"

# Prose names used in the manuscript for the locked machine term names. The
# manuscript must name every continuous term and must keep the locked order
# within each sign group.
TERM_PROSE = {
    "log_total_assets": "log total assets",
    "leverage_ratio": "leverage ratio",
    "current_ratio": "current ratio",
    "roa_period_adjusted": "return on assets",
    "ocf_to_assets_period_adjusted": "cash-flow-to-assets",
    "asset_turnover_period_adjusted": "asset turnover",
    "operating_margin_period_adjusted": "operating margin",
    "financial_expense_to_assets_period_adjusted": "financial-expense-to-assets",
    "accumulated_loss_to_capital_ratio": "accumulated-loss-to-capital",
}

# Words that turn an otherwise prohibited phrase into an explicit disclaimer.
NEGATION_MARKERS = (
    "no ", "not ", "never", "cannot", "does not", "do not", "is not", "are not",
    "without", "neither", "nor ", "avoid", "absent", "deny", "denies",
    "rather than", "instead of",
)


def is_negated(text: str, index: int, window: int = 90) -> bool:
    """True when a negation marker precedes `index` within `window` characters."""
    lead = text[max(0, index - window): index].lower()
    return any(marker in lead for marker in NEGATION_MARKERS)


# Claims that may never appear anywhere in the manuscript except as an explicit
# disclaimer (i.e. under a negation).
PROHIBITED_PHRASES = [
    "statistically significant",
    "significant at",
    "p < 0.05",
    "p<0.05",
    "p-value of",
    "outperform",
    "superior to",
    "best model",
    "state of the art",
    "state-of-the-art performance",
    "ready for deployment",
    "deployment-ready",
    "production-ready",
    "clinically ready",
    "causes ",
    "causal effect",
    "causal impact",
    "well calibrated",
    "well-calibrated",
    "stable performance",
    "external validation",
    "independent validation",
    "first study",
    "the full test suite passes",
    "all tests pass",
    "verified point-in-time availability",
    "observed filing date",
]

#: Overclaiming that must not survive anywhere, in any form. Unlike
#: PROHIBITED_PHRASES these are not rescued by a negation: the wording itself is
#: what was removed, so a "we do not claim it is a screening aid" sentence is
#: still a sentence that puts the phrase in a reader's head.
BANNED_OUTRIGHT = [
    "genuinely point-in-time",
    "screening aid",
    "usable ranking",
    "the relevant kind of evidence",
    "we recommend",
    "should be deployed",
    "suitable for deployment",
    "fit for deployment",
    "ready for use",
    "can be used to decide",
]

#: The restrained framing the corrected manuscript must actually contain.
REQUIRED_RESTRAINT = [
    "observed risk ordering",
    "independent prospective validation",
    "neither deployment readiness nor decision utility",
    "prespecified four-month availability assumption",
]

#: Journal-facing prose must not carry repository audit mechanics.
FT_CONTROL_RE = re.compile(r"\bFT\d{2}\b")
SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b")

ABSTRACT_MIN, ABSTRACT_MAX = 250, 350

# Sections whose numeric content is bibliographic rather than scientific.
NUMERIC_SCAN_STOP = "## 16. References"

# Structural numbers that are not scientific quantities.
STRUCTURAL_NUMBERS = {
    "141",  # Article 141 of the Iranian Commercial Code
    "95",   # nominal interval level
    "10",   # top-10 per cent screening label
    "23",   # ICML'06 conference ordinal in a prose citation, if present
    # Data-availability paragraph only. Neither is a scientific quantity:
    "128",  # part of the deposited record's own title, "papermali Stage128 ..."
    "2026", # the calendar year the raw-evidence bundle was deposited
}

failures: list[str] = []
checks_run = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global checks_run
    checks_run += 1
    if not ok:
        failures.append(f"{label}: {detail}" if detail else label)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def section(text: str, heading: str) -> str:
    """Return the body of one '## ' section."""
    start = text.index(heading)
    rest = text[start + len(heading):]
    nxt = rest.find("\n## ")
    return rest if nxt == -1 else rest[:nxt]


def allowed_numeric_tokens() -> set[str]:
    tokens: set[str] = set(STRUCTURAL_NUMBERS)
    sources = [PKG / "manuscript_claim_freeze.md", PKG / "table_model_coefficients_and_odds_ratios.csv"]
    sources += sorted(TABLES.glob("*.csv"))
    for src in sources:
        tokens |= set(re.findall(r"\d+(?:\.\d+)?", src.read_text(encoding="utf-8")))
    return tokens


def main() -> int:
    draft = DRAFT.read_text(encoding="utf-8")
    low = draft.lower()

    # --- 3 / 18: no forbidden source referenced anywhere -------------------
    for bad in FORBIDDEN_SOURCES:
        check(f"forbidden source absent from manuscript ({bad})", bad not in draft)
    matrix_rows = list(csv.DictReader(MATRIX.open(encoding="utf-8")))
    for row in matrix_rows:
        for bad in FORBIDDEN_SOURCES:
            check(
                f"forbidden source absent from traceability matrix ({bad})",
                bad not in row["canonical_source_path"],
                row["claim_id"],
            )

    # --- 2: the legacy Stage123 tree is never used as a source ------------
    check(
        "legacy Stage123 tree is not a traceability source",
        all(LEGACY_TREE not in r["canonical_source_path"] for r in matrix_rows),
    )
    legacy_mentions = draft.count(LEGACY_TREE)
    check(
        "legacy Stage123 tree is mentioned only to mark it non-citable",
        legacy_mentions <= 1 and (legacy_mentions == 0 or "non-citable" in low),
        f"{legacy_mentions} mention(s)",
    )

    # --- 5: PR-AUC precedes ROC-AUC in the Abstract and in the Results ----
    for heading in ("## Structured Abstract", "## 10. Locked Final Test Results"):
        body = section(draft, heading)
        check(
            f"PR-AUC precedes ROC-AUC in {heading.strip('# ')}",
            "PR-AUC" in body and "ROC-AUC" in body and body.index("PR-AUC") < body.index("ROC-AUC"),
        )

    # --- 6: '12 positive observations' appears in three required places ---
    for heading in ("## Structured Abstract", "## 10. Locked Final Test Results", "## 13. Limitations"):
        body = section(draft, heading).lower()
        check(f"'12 positive observations' present in {heading.strip('# ')}", "12 positive observations" in body)

    # --- 7: the PR-AUC interval limitation appears in three places --------
    for heading in ("## Structured Abstract", "## 10. Locked Final Test Results", "## 13. Limitations"):
        body = section(draft, heading).lower()
        check(
            f"PR-AUC interval limitation present in {heading.strip('# ')}",
            ("interval is wide" in body or "wide" in body) and "lower bound" in body and "prevalence" in body,
        )

    # --- 8: calibration is described as not fully assessed ----------------
    check("calibration described as not fully assessed", "not fully assessed" in low)
    for phrase in ("well calibrated", "well-calibrated"):
        for m in re.finditer(re.escape(phrase), low):
            check("any mention of the model being calibrated is an explicit disclaimer",
                  is_negated(low, m.start()), low[max(0, m.start() - 70): m.start() + 30])

    # --- 9: Recall@10% and Lift@10% carry no invented interval ------------
    for metric in ("Recall@10%", "Lift@10%"):
        for m in re.finditer(re.escape(metric), draft):
            window = draft[m.start(): m.start() + 260]
            check(
                f"no interval attached to {metric}",
                "CI" not in window and "confidence interval" not in window.replace(
                    "no confidence interval", "").replace("No confidence interval", ""),
                window[:80],
            )
    check(
        "Recall@10% and Lift@10% are explicitly marked as point estimates without an interval",
        "point estimates, and no confidence interval is available for either" in draft,
    )

    # --- 10: prohibited claims -------------------------------------------
    for phrase in PROHIBITED_PHRASES:
        for m in re.finditer(re.escape(phrase), low):
            check(f"prohibited phrase {phrase!r} appears only as an explicit disclaimer",
                  is_negated(low, m.start()), low[max(0, m.start() - 70): m.start() + 40])

    # --- 11: no performance curve was created ----------------------------
    created = sorted(p.name for p in MS_DIR.iterdir() if p.suffix.lower() in {".svg", ".png", ".pdf", ".jpg", ".jpeg"})
    check("no figure file was created in the manuscript directory", created == [], str(created))
    for fig in ("figure_1_study_timeline_and_leakage_safe_design.svg",
                "figure_2_model_development_workflow.svg",
                "figure_3_coefficient_plot.svg"):
        check(f"figure cited by reference from the frozen package: {fig}", fig in draft)
    check("no fourth figure is introduced", "Figure 4" not in draft)

    # --- 12: coefficient terms remain in locked model order ---------------
    coef_rows = list(csv.DictReader((TABLES / "table_6_model_coefficients_and_odds_ratios.csv").open(encoding="utf-8")))
    continuous = [r for r in coef_rows if r["term_type"] == "standardized_continuous_feature"]
    interp = section(draft, "## 11. Model Interpretation")
    missing = [r["term"] for r in continuous if TERM_PROSE[r["term"]] not in interp]
    check("every continuous term is named in Model Interpretation", not missing, str(missing))
    # Within each sign group the manuscript must preserve the locked model order.
    pos_terms = [r["term"] for r in continuous if float(r["coefficient_beta"]) > 0]
    neg_terms = [r["term"] for r in continuous if float(r["coefficient_beta"]) < 0]
    for label, group in (("positive", pos_terms), ("negative", neg_terms)):
        idx = [interp.find(TERM_PROSE[t]) for t in group]
        check(
            f"{label}-sign continuous terms appear in locked model order",
            all(i >= 0 for i in idx) and idx == sorted(idx),
            str(group),
        )

    # --- 13: no coefficient p-value, interval or significance mark --------
    for token in ("p-value", "p value", "significance", "significant", "standard error", "std. err"):
        check(f"no {token!r} in Model Interpretation", token not in interp.lower()
              or "does not establish statistical significance" in interp
              or "no confidence interval, standard error, p-value or significance marker" in interp)

    # --- 14 / 15: citations and bibliography agree ------------------------
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", BIB.read_text(encoding="utf-8")))
    cited = set()
    for group in re.findall(r"\[@([^\]]+)\]", draft):
        for key in group.split(";"):
            cited.add(key.strip().lstrip("@"))
    check("every in-text citation resolves to a bibliography entry",
          not (cited - bib_keys), str(sorted(cited - bib_keys)))
    check("no uncited bibliography entry remains",
          not (bib_keys - cited), str(sorted(bib_keys - cited)))
    audit_keys = {r["citation_key"] for r in csv.DictReader(AUDIT.open(encoding="utf-8"))}
    check("reference audit covers every bibliography entry",
          audit_keys == bib_keys, str(sorted(bib_keys ^ audit_keys)))
    for row in csv.DictReader(AUDIT.open(encoding="utf-8")):
        check(f"reference verified: {row['citation_key']}", row["verification_status"].startswith("VERIFIED"))

    # --- 16 / 17: frozen package and pinned sources are byte-identical ----
    manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    for rel, meta in manifest["package_files"].items():
        path = PKG / rel
        check(f"Phase 1 package file unchanged: {rel}", path.exists() and sha256(path) == meta["sha256"])
    for rel, digest in manifest["source_sha256"].items():
        path = ROOT.parent / rel
        check(f"pinned protected source unchanged: {rel}", path.exists() and sha256(path) == digest)

    # --- 1: every scientific number is traceable --------------------------
    allowed = allowed_numeric_tokens()
    body = draft[: draft.index(NUMERIC_SCAN_STOP)]
    body = re.sub(r"^#+ .*$", "", body, flags=re.M)          # drop headings
    body = re.sub(r"`[^`]*`", "", body)                       # drop inline code / paths
    body = re.sub(r"\[@[^\]]+\]", "", body)                   # drop citations
    untraceable = []
    for tok in re.findall(r"\d+(?:\.\d+)?", body):
        if tok in allowed:
            continue
        if "." in tok and len(tok.split(".")[1]) >= 3:
            untraceable.append(tok)
        elif "." not in tok and int(tok) >= 20:
            untraceable.append(tok)
    check("every scientific number in the manuscript is traceable to a canonical source",
          not untraceable, str(sorted(set(untraceable))))

    # --- traceability matrix integrity ------------------------------------
    check("traceability matrix is non-empty", len(matrix_rows) > 0)
    for row in matrix_rows:
        check(f"traceability row has a 64-hex source digest: {row['claim_id']}",
              re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"]) is not None)
        path = ROOT.parent / row["canonical_source_path"]
        check(f"traceability source exists and matches its digest: {row['claim_id']}",
              path.exists() and sha256(path) == row["source_sha256"])

    # --- 19 / 20: no test-suite discussion in the scientific narrative ----
    for m in re.finditer(r"full repository test suite passes", low):
        check("any mention of the full test suite passing is an explicit disclaimer",
              is_negated(low, m.start()), low[max(0, m.start() - 70): m.start() + 40])
    limitations = section(draft, "## 13. Limitations").lower()
    for token in ("test suite", "test-suite", "pytest", "historical failures"):
        check(f"repository test mechanics absent from Limitations: {token!r}",
              token not in limitations)

    # --- abstract length ---------------------------------------------------
    abstract = re.sub(r"\[@[^\]]+\]", "", section(draft, "## Structured Abstract"))
    words = len(abstract.replace("**", "").split())
    check(f"abstract is {ABSTRACT_MIN}-{ABSTRACT_MAX} words",
          ABSTRACT_MIN <= words <= ABSTRACT_MAX, f"{words} words")
    keywords = [k for k in section(draft, "## Keywords").split(";") if k.strip()]
    check("5-8 keywords", 5 <= len(keywords) <= 8, str(len(keywords)))

    # --- overclaiming removed, restrained framing present ------------------
    for phrase in BANNED_OUTRIGHT:
        check(f"overclaiming phrase fully removed: {phrase!r}", phrase not in low)
    for phrase in REQUIRED_RESTRAINT:
        check(f"restrained framing present: {phrase!r}", phrase in low)
    check("the availability rule is described as an assumption or proxy",
          "prespecified proxy" in low or "availability assumption" in low)

    # --- Article 141 is attributed, never asserted as settled legal text ---
    for m in re.finditer(r"article 141", low):
        window = low[m.start(): m.start() + 400]
        check("every Article 141 mention is attributed to a cited study or "
              "explicitly declined, never stated as settled statute",
              "salehi2016" in window or "operationalis" in window
              or "do not restate" in window or "labelling route" in window
              or "labelled" in window,
              window[:120])
    check("the manuscript declines to restate the statute without a primary source",
          "we do not restate the statutory text" in low)

    # --- journal-facing narrative carries no repository audit mechanics ----
    narrative = draft[: draft.index(NUMERIC_SCAN_STOP)]
    check("no exact SHA-256 digest in the journal-facing narrative",
          not SHA256_RE.search(narrative),
          str(SHA256_RE.findall(narrative)[:3]))
    check("no FT-control enumeration in the journal-facing narrative",
          not FT_CONTROL_RE.search(narrative),
          str(FT_CONTROL_RE.findall(narrative)[:5]))

    # --- every cross-reference resolves ------------------------------------
    numbered = {m.group(1) for m in re.finditer(r"^## (\d+)\. ", draft, re.M)}
    subsections = {m.group(1) for m in re.finditer(r"^### (\d+\.\d+) ", draft, re.M)}
    for m in re.finditer(r"Section (\d+(?:\.\d+)?)", draft):
        ref = m.group(1)
        ok = ref in numbered if "." not in ref else ref in subsections
        check(f"cross-reference resolves: Section {ref}", ok)
    tables = {p.name for p in TABLES.iterdir() if p.suffix == ".csv"}
    table_nums = {re.match(r"table_(\d+)_", n).group(1) for n in tables}
    for m in re.finditer(r"Table (\d+)", draft):
        check(f"cross-reference resolves: Table {m.group(1)}",
              m.group(1) in table_nums)
    figures = {p.name for p in (PKG / "manuscript_figures").iterdir()}
    fig_nums = {re.match(r"figure_(\d+)_", n).group(1) for n in figures}
    for m in re.finditer(r"Figure (\d+)", draft):
        check(f"cross-reference resolves: Figure {m.group(1)}",
              m.group(1) in fig_nums)
    check("every frozen table is cited at least once",
          all(f"Table {n}" in draft for n in sorted(table_nums)),
          str(sorted(n for n in table_nums if f"Table {n}" not in draft)))
    check("every frozen figure is cited at least once",
          all(f"Figure {n}" in draft for n in sorted(fig_nums)))

    # --- end matter is not numbered as a results section -------------------
    check("table/figure callouts are unnumbered end matter",
          "## Table and Figure Captions/Callouts" in draft
          and "## 17." not in draft)

    # --- robustness ordering agrees across all three surfaces --------------
    robust = json.loads((ROOT.parent / "project/stage126/"
                         "stage126_m1_robustness_closure_synthesis_record.json"
                         ).read_text(encoding="utf-8"))
    src_ok = sorted(p["part_index"] for p in robust["part_summaries"]
                    if p["primary_ordering_preserved"])
    src_rev = sorted(p["part_index"] for p in robust["part_summaries"]
                     if not p["primary_ordering_preserved"])
    t5 = {r["item"]: r["status_or_finding"] for r in csv.DictReader(
        (TABLES / "table_5_robustness_and_block_dispositions.csv").open(
            encoding="utf-8"))}
    check("table 5 ordering matches the locked source",
          json.loads(t5["ordering_preserved_in_parts"]) == src_ok, str(src_ok))
    check("table 5 records the reversal explicitly",
          json.loads(t5["ordering_reversed_in_parts"]) == src_rev, str(src_rev))
    freeze = " ".join((PKG / "manuscript_claim_freeze.md").read_text(
        encoding="utf-8").split())
    check("claim freeze states the same preserved parts",
          "preserved in Parts 2, 3, 4, 5 and 6" in freeze)
    check("claim freeze names Part 1 as the sole reversal",
          "Part 1 is the sole reversal" in freeze)
    body8 = section(draft, "## 8. Development and Robustness Evidence")
    check("manuscript states the same preserved parts",
          "preserved in categories 2, 3, 4, 5 and 6" in body8)
    check("manuscript names the single reversal",
          "sole reversal" in body8)

    # --- development values are the locked strings, not recomputed ---------
    dev = {(r["model_family"], r["scope"]): r for r in csv.DictReader(
        (ROOT.parent / "project/stage126/stage126_m1_development_metrics.csv"
         ).open(encoding="utf-8"))}
    for family in ("regularized_logistic_regression", "random_forest", "xgboost"):
        value = dev[(family, "pooled_development_oof")]["pr_auc"]
        check(f"pooled development PR-AUC quoted verbatim for {family}",
              value in body8, value)

    # --- reporting guideline is adapted, not claimed as compliance ---------
    if "TRIPOD" in draft:
        check("TRIPOD is invoked via the verified 2024 update",
              "collins2024" in draft and "TRIPOD+AI" in draft)
        check("TRIPOD use is described as an adapted checklist",
              "adapted" in low and "checklist" in low)
        check("no formal TRIPOD compliance is claimed",
              "no claim of formal tripod+ai compliance is made" in low)

    # --- human-only metadata is carried as placeholders --------------------
    for item in ("Authors and author order", "Affiliations and corresponding",
                 "Funding", "Conflicts of interest",
                 "Ethics and data-governance", "Data-access mechanism"):
        check(f"human-only placeholder present: {item}", item in draft)
    check("placeholders are marked, not invented",
          draft.count("*[TO BE COMPLETED") >= 6)

    # --- Jalali labels are kept and explained, never converted -------------
    check("Jalali year labels are retained", "1393" in draft and "1400" in draft)
    check("the calendar choice is explained rather than converted",
          "Jalali (Solar Hijri)" in draft and "fiscal year-end" in low)

    print(f"checks run: {checks_run}")
    if failures:
        print(f"FAILED: {len(failures)}")
        for f in failures:
            print("  -", f)
        return 1
    print("manuscript acceptance checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
