"""Reports (brief sections 9, 18-19) + final article-ready tables (Persian drafts)."""
from __future__ import annotations
import pandas as pd

from . import utils


def _fmt(df, cols=None, nd=3):
    d = df.copy()
    for c in (cols or d.select_dtypes("number").columns):
        d[c] = d[c].round(nd)
    return d


def _primary_table(state):
    tm = state["test_metrics"]
    return tm[tm["threshold_kind"] == "thr_opt_primary"][
        ["model", "pr_auc", "roc_auc", "recall", "precision", "f1", "f2",
         "specificity", "balanced_accuracy", "mcc", "brier", "log_loss",
         "tp", "fp", "tn", "fn"]].reset_index(drop=True)


def technical_report(state, cfg):
    out = utils.out_dir(cfg, "09_report")
    tables = utils.out_dir(cfg, "09_report")
    a = state["audit"]
    sc = a["split_counts"]
    prim = _fmt(_primary_table(state))
    cvfold = pd.DataFrame([r for m in state["tuning"].values() for r in m["fold_records"]])
    prim.to_csv(out / "table_1_test_metrics_primary.csv", index=False, encoding="utf-8-sig")

    md = []
    md.append("# Technical Modeling Report — Financial Distress Prediction (Stage121)\n")
    md.append("Models compared on an identical feature set: **Logistic Regression, "
              "Random Forest, XGBoost**. Main metric: **PR-AUC**. Forecast horizon: "
              "**one year ahead** (firm info at year *t* → distress at *t+1*).\n")
    md.append("## 1. Data & target\n")
    md.append(f"- One-year-ahead rows built: **{a['n_built']}**, positives "
              f"**{a['n_positive']}** ({a['positive_rate']*100:.2f}%).\n")
    md.append(f"- Only dropped predictors: {a['dropped']}.\n")
    md.append("- Target `distressed_target_reviewed` was never modified; year-*t* label "
              "is excluded from features.\n")
    md.append("## 2. Temporal split (approved revision)\n")
    md.append("Distress events exist only in target years 1393–1398, so the brief's "
              "original test window (1401–1402) contained a single positive and two "
              "validation folds with zero positives. With written approval the boundary "
              "was moved earlier:\n")
    for sp in ["dev", "test"]:
        if sp in sc:
            md.append(f"- **{sp}**: n={sc[sp]['n']}, positives={sc[sp]['positives']}\n")
    md.append("- Rows with target_year ≥ 1399 (zero positives, after the test window) "
              "are excluded from one-year-ahead modeling and documented.\n")
    md.append("## 3. Pipeline\n")
    md.append("- All preprocessing (median impute + missing indicators, RobustScaler for "
              "LR, one-hot industry) is fit on the training fold only — no leakage.\n")
    md.append("- Imbalance handled by cost-sensitive learning (class_weight / "
              "scale_pos_weight); SMOTE only in robustness.\n")
    md.append("- Hyperparameters tuned with Optuna on expanding-window folds; selection "
              "metric = mean validation PR-AUC. Thresholds chosen on validation only.\n")
    md.append("## 4. Cross-validation (validation folds)\n")
    md.append(_fmt(cvfold[["model", "fold", "n_val", "pos_val", "pr_auc", "roc_auc",
                           "brier"]]).to_markdown(index=False) + "\n")
    md.append("## 5. Test results (optimal threshold, primary = F1)\n")
    md.append(prim.to_markdown(index=False) + "\n")
    if "bootstrap" not in state:
        bp = pd.read_csv(utils.out_dir(cfg, "06_metrics") / "test_metrics_bootstrap_ci.csv")
        md.append("## 6. Test 95% cluster-bootstrap CIs (by ticker)\n")
        md.append(_fmt(bp).to_markdown(index=False) + "\n")
    if "seed_stability" in state and len(state["seed_stability"]):
        ss = state["seed_stability"].groupby("model")[["pr_auc", "recall", "f1",
             "balanced_accuracy", "brier"]].agg(["mean", "std"]).round(3)
        md.append("## 7. Seed stability (RF & XGBoost, 30 seeds)\n")
        md.append(ss.to_markdown() + "\n")
    if "calibration" in state:
        md.append("## 8. Calibration (Brier on test)\n")
        md.append(_fmt(state["calibration"]).to_markdown(index=False) + "\n")
    if "robustness" in state:
        md.append("## 9. Robustness (separate from main result)\n")
        md.append(_fmt(state["robustness"][["variant", "model", "cv_mean_pr_auc",
                  "test_pr_auc", "test_recall", "test_f1"]]).to_markdown(index=False) + "\n")
    md.append("## 10. Documented data limitations (brief)\n")
    md.append("- 39 missing `operating_cash_flow` (1 source_unavailable_codal, 38 "
              "deferred); 145 unresolved `gross_profit`; 13 incomplete provenance; "
              "99 unreviewed abnormal financial changes. None were zero-filled.\n")
    md.append("## 11. Caveats\n")
    md.append("- Only 9 positives in the test window → test metrics and bootstrap CIs are "
              "wide; PR-AUC on validation folds is the more stable selection signal.\n")
    (out / "technical_modeling_report.md").write_text("".join(md), encoding="utf-8")
    print(f"[09] technical report saved -> {out}")
    return prim


def article_drafts(state, cfg):
    out = utils.out_dir(cfg, "09_report")
    a = state["audit"]; sc = a["split_counts"]
    prim = _fmt(_primary_table(state))

    methods = f"""# روش‌شناسی (پیش‌نویس مقاله)

## داده و واحد مشاهده
واحد مشاهده شرکت‌ـ‌سال (`ticker × fiscal_year`) در بازهٔ ۱۳۹۲–۱۴۰۲ است. متغیر هدف
`distressed_target_reviewed` (۱=درمانده، ۰=غیردرمانده) بدون هیچ تغییری استفاده شد.

## افق پیش‌بینی یک‌سال‌جلو
برای پرهیز از look-ahead bias، با اطلاعات سال t درماندگی سال t+1 پیش‌بینی می‌شود. پس از
این انتقال، مجموعهٔ نهایی **{a['n_built']} ردیف** با **{a['n_positive']} نمونهٔ مثبت**
({a['positive_rate']*100:.2f}٪) به‌دست آمد. تنها ردیف‌های حذف‌شده، predictorهای سال ۱۴۰۲
(فاقد هدف ۱۴۰۳) بودند.

## تقسیم زمانی
چون رویدادهای درماندگی تنها در سال‌های هدف ۱۳۹۳–۱۳۹۸ حضور دارند، تقسیم زمانی به‌صورت
توسعه = سال‌های هدف ۱۳۹۳–۱۳۹۶ (n={sc.get('dev',{}).get('n','-')}،
مثبت={sc.get('dev',{}).get('positives','-')}) و آزمون دست‌نخورده = ۱۳۹۷–۱۳۹۸
(n={sc.get('test',{}).get('n','-')}، مثبت={sc.get('test',{}).get('positives','-')})
انجام شد. تنظیم ابرپارامترها با اعتبارسنجی پنجرهٔ گسترش‌یابنده و معیار میانگین PR-AUC.

## پیش‌پردازش و عدم‌توازن
جای‌گذاری میانه + شاخص مفقودی، RobustScaler برای رگرسیون لجستیک و One-Hot برای صنعت،
همگی فقط روی دادهٔ آموزش هر fold برازش شدند. عدم‌توازن با یادگیری هزینه‌-حساس
(`class_weight` و `scale_pos_weight`) مدیریت شد؛ SMOTE صرفاً در تحلیل استحکام.

## مدل‌ها و ارزیابی
سه مدل لجستیک، جنگل تصادفی و XGBoost روی feature set یکسان مقایسه شدند. معیار اصلی
PR-AUC و معیارهای مکمل ROC-AUC، Recall، Precision، F1/F2، ویژگی، دقت متوازن، MCC،
Brier و Log-Loss گزارش شد. آستانه فقط روی اعتبارسنجی و با بیشینه‌سازی F1 انتخاب شد. بازهٔ
اطمینان ۹۵٪ با bootstrap خوشه‌ای بر مبنای شرکت محاسبه شد. توضیح‌پذیری با SHAP (درختی، فقط
روی آزمون) و ضرایب/نسبت بخت برای لجستیک.
"""
    (out / "article_methods_draft_fa.md").write_text(methods, encoding="utf-8")

    best = prim.sort_values("pr_auc", ascending=False).iloc[0]["model"]
    results = f"""# یافته‌ها (پیش‌نویس مقاله)

جدول ۱ معیارهای آزمون سه مدل را در آستانهٔ بهینهٔ مبتنی بر اعتبارسنجی نشان می‌دهد. معیار
اصلی PR-AUC و Recall کلاس درمانده برجسته است.

{prim.to_markdown(index=False)}

بر اساس PR-AUC، مدل **{best}** بهترین عملکرد را داشت. به‌دلیل تعداد اندک نمونهٔ مثبت در
پنجرهٔ آزمون (۹ مورد)، بازه‌های اطمینان bootstrap پهن‌اند و نتایج باید با احتیاط تفسیر
شوند؛ سیگنال پایدارتر، PR-AUC اعتبارسنجی است. تحلیل‌های استحکام (Feature Set B، winsorization،
SMOTE، حذف متغیرهای نزدیک به تعریف، و طبقه‌بندی هم‌سال) جداگانه در فایل
`robustness_results.csv` گزارش شده‌اند و جایگزین مدل اصلی نیستند.

## محدودیت‌ها
۳۹ مقدار مفقود جریان نقد عملیاتی، ۱۴۵ مقدار حل‌نشدهٔ سود ناخالص، ۱۳ ردیف با provenance ناقص
و ۹۹ تغییر مالی غیرعادی بررسی‌نشده؛ هیچ‌کدام با صفر پر نشدند. تمرکز رویدادهای درماندگی در
سال‌های ابتدایی بازه، ارزیابی هم‌زمانی روی سال‌های اخیر را محدود می‌کند.
"""
    (out / "article_results_draft_fa.md").write_text(results, encoding="utf-8")
    print(f"[09] Persian article drafts saved -> {out}")


def run(state, cfg):
    technical_report(state, cfg)
    article_drafts(state, cfg)
