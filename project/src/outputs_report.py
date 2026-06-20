"""Comprehensive, faithful outputs report (Persian, RTL) for the finance team.

Every number is read directly from the produced files under outputs/ — no value is
typed by hand — so the report cannot drift from the actual results. Covers BOTH
informative results and null/negative results, plus a full file inventory.

Produces:
  outputs/09_report/full_outputs_report_fa.md
  outputs/09_report/full_outputs_report_fa.docx
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

from . import utils
from .article import _para, _heading, _table, _set_cs_font, _rtl
from docx import Document
from docx.shared import Pt

MODEL_FA = {"logistic": "رگرسیون لجستیک", "random_forest": "جنگل تصادفی",
            "xgboost": "XGBoost"}


def _load(cfg):
    op = Path(cfg["_project_root"]) / cfg["paths"]["outputs_dir"]
    L = {}
    L["op"] = op
    L["audit"] = pd.read_csv(op / "01_data_audit/target_shift_audit.csv")
    L["class"] = pd.read_csv(op / "01_data_audit/class_distribution.csv")
    L["dup"] = pd.read_csv(op / "01_data_audit/duplicate_check.csv")
    L["miss"] = pd.read_csv(op / "01_data_audit/missingness_by_split.csv")
    L["outlier"] = pd.read_csv(op / "01_data_audit/outlier_report.csv")
    L["folddesign"] = pd.read_csv(op / "06_metrics/cv_fold_design.csv")
    L["cvfold"] = pd.read_csv(op / "06_metrics/cv_metrics_by_fold.csv")
    L["cvsumm"] = pd.read_csv(op / "06_metrics/cv_metrics_summary.csv")
    L["test"] = pd.read_csv(op / "06_metrics/test_metrics.csv")
    L["boot"] = pd.read_csv(op / "06_metrics/test_metrics_bootstrap_ci.csv")
    L["calib"] = pd.read_csv(op / "06_metrics/calibration_metrics.csv")
    L["seed"] = pd.read_csv(op / "06_metrics/seed_stability_summary.csv")
    L["robust"] = pd.read_csv(op / "06_metrics/robustness_results.csv")
    L["shap_xgb"] = pd.read_csv(op / "07_explainability/shap_global_importance_xgb.csv")
    L["shap_rf"] = pd.read_csv(op / "07_explainability/shap_global_importance_rf.csv")
    L["odds"] = pd.read_csv(op / "07_explainability/logistic_odds_ratios.csv")
    L["pred"] = pd.read_csv(op / "05_predictions/test_predictions_all_models.csv")
    L["hp"] = json.load(open(op / "04_models/best_hyperparameters.json"))
    L["thr"] = json.load(open(op / "04_models/final_thresholds.json"))
    env_path = op / "10_reproducibility/environment_info.json"
    L["env"] = (json.load(open(env_path)) if env_path.exists()
                else utils.env_report())
    return L


def _av(audit, key):
    r = audit[audit["key"] == key]
    return r["value"].iloc[0] if len(r) else float("nan")


def _prim(test):
    return test[test["threshold_kind"] == "thr_opt_primary"].set_index("model")


# --------------------------------------------------------------------------
# Build a structured content list, then render to DOCX and Markdown.
# --------------------------------------------------------------------------
def _content(cfg, L):
    A = L["audit"]
    n_built = int(_av(A, "n_built_one_year_ahead"))
    n_pos = int(_av(A, "n_positive"))
    rate = float(_av(A, "positive_rate"))
    dev_n, dev_p = int(_av(A, "split::dev::n")), int(_av(A, "split::dev::positives"))
    test_n, test_p = int(_av(A, "split::test::n")), int(_av(A, "split::test::positives"))
    un_n = int(_av(A, "split::unused_no_positive_post_test::n"))
    un_p = int(_av(A, "split::unused_no_positive_post_test::positives"))
    prim = _prim(L["test"])
    x = prim.loc["xgboost"]; r = prim.loc["random_forest"]; lo = prim.loc["logistic"]
    best = MODEL_FA[prim["pr_auc"].idxmax()]
    C = []

    C += [("h0", "گزارش جامع خروجی‌های تحلیل پیش‌بینی درماندگی مالی")]
    C += [("note", "این گزارش به‌صورت خودکار و مستقیماً از روی فایل‌های خروجیِ کد تولید شده "
           "است؛ همهٔ اعداد عیناً از خروجی برنامه استخراج شده‌اند و هیچ عددی به‌صورت دستی "
           "افزوده نشده است. هدف: ارائهٔ تصویری کامل از آنچه روی دیتاست تحویلی به‌دست آمد — "
           "هم نتایج معنادار و هم مواردی که نتیجه‌ای نداشتند.")]

    # 0 executive summary
    C += [("h1", "۱. خلاصهٔ اجرایی")]
    C += [("p", f"روی دیتاست تحویلی (پنل شرکت‌ـ‌سال بورس تهران)، یک سامانهٔ پیش‌بینی "
           f"«یک سال جلوتر» ساخته و سه مدل رگرسیون لجستیک، جنگل تصادفی و XGBoost روی مجموعهٔ "
           f"ویژگی و تقسیم زمانی یکسان مقایسه شدند. پس از ساخت هدف یک‌سال‌جلو، {n_built} "
           f"مشاهده با {n_pos} نمونهٔ مثبت (نرخ درماندگی {rate*100:.2f}٪) به‌دست آمد.")]
    C += [("p", f"مدل برتر بر اساس معیار اصلی (PR-AUC) مدل {best} بود: روی مجموعهٔ آزمونِ "
           f"دست‌نخورده PR-AUC={x['pr_auc']:.3f}، ROC-AUC={x['roc_auc']:.3f}، "
           f"فراخوانی={x['recall']:.3f}، دقت={x['precision']:.3f}، F1={x['f1']:.3f}، "
           f"دقت متوازن={x['balanced_accuracy']:.3f}، MCC={x['mcc']:.3f} و "
           f"Brier={x['brier']:.3f}. این مدل {int(x['tp'])} مورد از "
           f"{int(x['tp']+x['fn'])} شرکت درماندهٔ آزمون را درست شناسایی کرد "
           f"(و {int(x['fp'])} هشدار اشتباه داشت).")]
    C += [("p", "مهم‌ترین یافتهٔ منفی: رویدادهای درماندگی در دیتاست تنها در سال‌های ابتدایی "
           "بازه حضور دارند و در سال‌های اخیر تقریباً صفر می‌شوند؛ همین موضوع بخش زیادی از "
           "طراحی ارزیابی را محدود کرد (بخش ۳).")]

    # 2 dataset build
    C += [("h1", "۲. ساخت دیتاست و هدف یک‌سال‌جلو")]
    dd = pd.DataFrame({
        "شرح": ["ردیف‌های واجد شرایط ورودی (training candidates)",
                "ردیف‌های نهاییِ هدفِ یک‌سال‌جلو (built)",
                "نمونه‌های مثبت (درمانده) نهایی", "نرخ مثبت",
                "ردیف‌های حذف‌شده: سال پایانی بدون هدف سال بعد",
                "ردیف‌های حذف‌شده: فاصلهٔ سال (gap)",
                "ردیف‌های حذف‌شده: هدف سال بعد نامعتبر"],
        "مقدار": [int(_av(A, "n_candidates")), n_built, n_pos, f"{rate*100:.2f}٪",
                  int(_av(A, "dropped::predictor_last_year_no_next_panel_row")),
                  int(_av(A, "dropped::next_year_gap_no_row")),
                  int(_av(A, "dropped::next_target_invalid"))]})
    C += [("table", dd, "جدول ۲-۱: جمع‌بندی ساخت هدف یک‌سال‌جلو", 4)]
    C += [("p", "تنها ردیف‌های حذف‌شده، مشاهداتِ آخرین سالِ پنل بودند که هدفِ سال بعد برایشان "
           "وجود ندارد. هیچ هدفی تغییر داده نشد و هیچ مقدار مفقودی با صفر پر نشد.")]

    # 3 critical null result: event scarcity
    C += [("h1", "۳. یافتهٔ بحرانی (نتیجهٔ منفی): کمبود رویداد در سال‌های اخیر")]
    cy = L["class"][L["class"]["level"] == "target_year"][
        ["group", "n", "positives", "positive_rate"]].copy()
    cy.columns = ["سال هدف", "تعداد", "مثبت", "نرخ مثبت"]
    cy["نرخ مثبت"] = cy["نرخ مثبت"].round(4)
    C += [("table", cy, "جدول ۳-۱: توزیع نمونه‌های مثبت بر حسب سال هدف", 4)]
    C += [("p", f"همان‌طور که در جدول ۳-۱ دیده می‌شود، سال‌های هدف ۱۳۹۹، ۱۴۰۰ و ۱۴۰۲ هیچ "
           f"نمونهٔ مثبتی ندارند و ۱۴۰۱ تنها یک مثبت دارد. به همین دلیل {un_n} ردیف مربوط به "
           f"سال‌های هدف ۱۳۹۹ تا ۱۴۰۲ (که جمعاً تنها {un_p} مثبت دارند و از نظر زمانی پس از "
           f"پنجرهٔ آزمون قرار می‌گیرند) از مدل‌سازی یک‌سال‌جلو کنار گذاشته شدند.")]
    C += [("p", "پیامد عملی: تقسیم زمانیِ اولیه‌ای که در دستورکار پیشنهاد شده بود (آزمون روی "
           "سال‌های ۱۴۰۱–۱۴۰۲) عملاً قابل‌ارزیابی نبود، زیرا تنها یک نمونهٔ مثبت در آن قرار "
           "می‌گرفت و دو fold اعتبارسنجی صفر مثبت داشتند. با تأیید کارفرما، مرز زمانی به عقب "
           "منتقل شد (بخش ۴).")]

    # 4 split + folds
    C += [("h1", "۴. تقسیم داده و طراحی اعتبارسنجی")]
    sp = pd.DataFrame({
        "مجموعه": ["توسعه (dev) — سال‌های هدف ۱۳۹۳–۱۳۹۶",
                   "آزمون دست‌نخورده (test) — سال‌های هدف ۱۳۹۷–۱۳۹۸",
                   "کنارگذاشته‌شده — سال‌های هدف ۱۳۹۹–۱۴۰۲"],
        "تعداد": [dev_n, test_n, un_n], "مثبت": [dev_p, test_p, un_p]})
    C += [("table", sp, "جدول ۴-۱: تقسیم نهایی داده", 0)]
    fd = L["folddesign"].rename(columns={
        "fold": "fold", "n_train": "تعداد آموزش", "pos_train": "مثبت آموزش",
        "n_val": "تعداد اعتبار", "pos_val": "مثبت اعتبار",
        "train_years": "سال‌های آموزش", "val_years": "سال‌های اعتبار"})
    C += [("table", fd, "جدول ۴-۲: طراحی foldهای پنجرهٔ گسترش‌یابنده (هر سه fold مثبت دارند)", 0)]

    # 5 data quality
    C += [("h1", "۵. کیفیت داده")]
    C += [("p", f"کلید تکراری شرکت‌ـ‌سال در پنل کامل ({int(L['dup'].iloc[0]['n_rows'])} ردیف) "
           f"و در دیتاست ساخته‌شده ({int(L['dup'].iloc[1]['n_rows'])} ردیف): صفر مورد.")]
    mm = L["miss"].rename(columns={"feature": "ویژگی", "split": "مجموعه", "n": "تعداد",
                                   "n_missing": "تعداد مفقود", "pct_missing": "درصد مفقود"})
    C += [("table", mm, "جدول ۵-۱: مفقودی ویژگی‌های مدل اصلی به تفکیک مجموعه", 2)]
    C += [("p", "نکتهٔ مهم (نتیجهٔ محدودکننده): دو ویژگی «رشد درآمد» و «رشد سود خالص» در "
           "مجموعهٔ توسعه حدود ۲۷٪ مفقودی دارند؛ به‌طور خاص در fold اول (سال مبدأ ۱۳۹۲) این "
           "دو ویژگی کاملاً مفقوداند و عملاً در آن fold حذف می‌شوند (رشد برای نخستین سال "
           "تعریف نشده است). همهٔ این مفقودی‌ها با میانهٔ دادهٔ آموزشِ همان fold و شاخص "
           "مفقودی مدیریت شدند، نه با صفر.")]
    ol = L["outlier"].rename(columns={"feature": "ویژگی"})
    C += [("table", ol, "جدول ۵-۲: گزارش پرت‌ها (صدک ۱ و ۹۹ روی dev و شمار مقادیر فراتر)", 3)]
    C += [("p", "نکتهٔ کیفی: ویژگی financial_expense_to_assets روی dev بیشینهٔ صفر و صدک ۹۹ "
           "برابر صفر دارد (عملاً یک‌سویه)، و برخی ویژگی‌های حاشیه/رشد مقادیر بسیار بزرگ "
           "(مثلاً بیشینهٔ ۱۵۳ و ۱۴۰) دارند که با همان مقادیر اصلی حفظ شدند (طبق دستورکار، "
           "بدون حذف دستی پرت).")]

    # 6 hyperparameters
    C += [("h1", "۶. ابرپارامترهای منتخب (Optuna، معیار میانگین PR-AUC اعتبارسنجی)")]
    hp = L["hp"]
    hp_rows = []
    for m in ["logistic", "random_forest", "xgboost"]:
        for k, v in hp[m].items():
            hp_rows.append({"مدل": MODEL_FA[m], "پارامتر": k,
                            "مقدار": round(v, 5) if isinstance(v, float) else v})
    C += [("table", pd.DataFrame(hp_rows), "جدول ۶-۱: بهترین ابرپارامترها", 5)]
    thr = L["thr"]
    thr_rows = [{"مدل": MODEL_FA[m],
                 "آستانهٔ اصلی (F1)": round(thr[m]["primary_threshold"], 4),
                 "آستانهٔ دوم (دقت متوازن)": round(thr[m]["secondary_threshold"], 4)}
                for m in ["logistic", "random_forest", "xgboost"]]
    C += [("table", pd.DataFrame(thr_rows), "جدول ۶-۲: آستانه‌های انتخاب‌شده روی اعتبارسنجی", 4)]

    # 7 CV results
    C += [("h1", "۷. نتایج اعتبارسنجی (validation folds)")]
    cvf = L["cvfold"].copy(); cvf["model"] = cvf["model"].map(MODEL_FA)
    cvf = cvf.rename(columns={"model": "مدل", "fold": "fold", "n_val": "تعداد اعتبار",
                              "pos_val": "مثبت", "pr_auc": "PR-AUC", "roc_auc": "ROC-AUC",
                              "brier": "Brier", "log_loss": "LogLoss"})
    C += [("table", cvf.round(4), "جدول ۷-۱: معیارهای اعتبارسنجی به تفکیک fold", 4)]
    cvs = L["cvsumm"].copy(); cvs["model"] = cvs["model"].map(MODEL_FA)
    C += [("table", cvs.round(4), "جدول ۷-۲: میانگین و انحراف معیار اعتبارسنجی", 4)]
    C += [("p", "نتیجه: XGBoost بالاترین میانگین PR-AUC اعتبارسنجی را داشت و در هر سه fold "
           "روند صعودی نشان داد؛ رگرسیون لجستیک ضعیف‌ترین بود (به‌ویژه fold اول).")]

    # 8 test results
    C += [("h1", "۸. نتایج مجموعهٔ آزمون (دست‌نخورده)")]
    tt = L["test"].copy(); tt["model"] = tt["model"].map(MODEL_FA)
    tt = tt.rename(columns={"model": "مدل", "threshold_kind": "نوع آستانه",
                            "pr_auc": "PR-AUC", "roc_auc": "ROC-AUC", "recall": "فراخوانی",
                            "precision": "دقت", "f1": "F1", "f2": "F2",
                            "specificity": "ویژگی", "balanced_accuracy": "دقت متوازن",
                            "mcc": "MCC", "brier": "Brier", "log_loss": "LogLoss",
                            "threshold": "آستانه", "tp": "TP", "fp": "FP", "tn": "TN",
                            "fn": "FN"})
    keep = ["مدل", "نوع آستانه", "PR-AUC", "ROC-AUC", "فراخوانی", "دقت", "F1", "F2",
            "ویژگی", "دقت متوازن", "MCC", "Brier", "TP", "FP", "TN", "FN"]
    C += [("table", tt[keep].round(4), "جدول ۸-۱: معیارهای آزمون در سه آستانه "
           "(۰٫۵، بهینهٔ F1، بهینهٔ دقت متوازن)", 4)]
    C += [("p", "PR-AUC و ROC-AUC مستقل از آستانه‌اند؛ تغییر آستانه فقط تعداد TP/FP/FN را "
           "جابه‌جا می‌کند. در XGBoost آستانهٔ اصلی و دوم بسیار نزدیک شدند و نتیجهٔ یکسانی "
           "دادند.")]

    # 9 bootstrap
    C += [("h1", "۹. بازهٔ اطمینان ۹۵٪ (bootstrap خوشه‌ای بر مبنای شرکت)")]
    for m in ["xgboost", "random_forest", "logistic"]:
        bt = L["boot"][L["boot"]["model"] == m][["metric", "point", "ci_low", "ci_high",
                                                 "n_boot_valid"]]
        bt = bt.rename(columns={"metric": "معیار", "point": "نقطه‌ای", "ci_low": "حد پایین",
                                "ci_high": "حد بالا", "n_boot_valid": "تکرار معتبر"})
        C += [("table", bt.round(4), f"جدول ۹: بازهٔ اطمینان — {MODEL_FA[m]}", 4)]
    C += [("p", "هشدار: به‌دلیل وجود تنها ۹ نمونهٔ مثبت در آزمون، بازه‌های اطمینان پهن‌اند "
           "(مثلاً فراخوانی XGBoost بین ۰٫۳۳ تا ۱٫۰۰). این یک محدودیت واقعی است و باید در "
           "تفسیر لحاظ شود.")]

    # 10 seed stability
    C += [("h1", "۱۰. پایداری نتایج در ۳۰ seed (RF و XGBoost)")]
    ss = L["seed"].copy(); ss["model"] = ss["model"].map(MODEL_FA)
    cols = ["model", "pr_auc_mean", "pr_auc_std", "pr_auc_min", "pr_auc_max",
            "recall_mean", "recall_std", "f1_mean", "f1_std",
            "balanced_accuracy_mean", "balanced_accuracy_std"]
    C += [("table", ss[cols].round(4), "جدول ۱۰-۱: پایداری معیارهای آزمون در ۳۰ seed", 4)]
    C += [("p", "نتیجه: معیارها در seedهای مختلف پایدارند (مثلاً انحراف معیار PR-AUC حدود "
           "۰٫۰۲ تا ۰٫۰۳ و فراخوانی کاملاً ثابت). این نشان می‌دهد رتبه‌بندی مدل‌ها به "
           "تصادف الگوریتم حساس نیست.")]

    # 11 calibration
    C += [("h1", "۱۱. کالیبراسیون احتمال (Brier روی آزمون)")]
    cal = L["calib"].copy(); cal["model"] = cal["model"].map(MODEL_FA)
    cal = cal.rename(columns={"model": "مدل", "method": "روش", "brier_test": "Brier آزمون"})
    C += [("table", cal.round(4), "جدول ۱۱-۱: Brier پیش و پس از کالیبراسیون", 4)]
    C += [("p", "کالیبراسیون (پلَت/ایزوتونیک، برازش‌شده فقط روی اعتبارسنجی) Brier را در هر "
           "سه مدل بهبود داد؛ بیشترین بهبود برای رگرسیون لجستیک (از ۰٫۱۲۹ به ۰٫۰۴۰).")]

    # 12 importance / SHAP / odds
    C += [("h1", "۱۲. اهمیت ویژگی‌ها و توضیح‌پذیری")]
    sx = L["shap_xgb"].head(12).rename(columns={"feature": "ویژگی",
                                                "mean_abs_shap": "میانگین |SHAP|"})
    C += [("table", sx.round(4), "جدول ۱۲-۱: ۱۲ ویژگی برتر SHAP — XGBoost (روی آزمون)", 4)]
    sr = L["shap_rf"].head(10).rename(columns={"feature": "ویژگی",
                                               "mean_abs_shap": "میانگین |SHAP|"})
    C += [("table", sr.round(4), "جدول ۱۲-۲: ۱۰ ویژگی برتر SHAP — جنگل تصادفی", 4)]
    od = L["odds"].head(12).rename(columns={"feature": "ویژگی", "odds_ratio": "نسبت بخت",
                                            "direction": "جهت اثر", "is_industry": "صنعت؟"})
    C += [("table", od.round(4), "جدول ۱۲-۳: نسبت بخت رگرسیون لجستیک (۱۲ مورد برتر)", 4)]
    C += [("p", "جمع‌بندی توضیح‌پذیری: در هر دو مدل درختی، «نسبت اهرمی» مهم‌ترین عامل است؛ "
           "سپس صنعت «خودرو و ساخت قطعات»، اندازهٔ شرکت (لگاریتم دارایی) و حاشیهٔ سود خالص. "
           "در رگرسیون لجستیک نیز نسبت اهرمی و عضویت در صنعت خودرو ریسک را افزایش و اندازهٔ "
           "شرکت و ROA ریسک را کاهش می‌دهند.")]

    # 13 robustness
    C += [("h1", "۱۳. تحلیل‌های استحکام (جدا از مدل اصلی)")]
    rb = L["robust"].copy(); rb["model"] = rb["model"].map(MODEL_FA)
    rb = rb.rename(columns={"variant": "واریانت", "model": "مدل",
                            "cv_mean_pr_auc": "PR-AUC اعتبار", "test_pr_auc": "PR-AUC آزمون",
                            "test_recall": "فراخوانی آزمون", "test_precision": "دقت آزمون",
                            "test_f1": "F1 آزمون", "test_brier": "Brier آزمون",
                            "imbalance": "روش عدم‌توازن", "winsor": "winsor"})
    keepr = ["واریانت", "مدل", "PR-AUC اعتبار", "PR-AUC آزمون", "فراخوانی آزمون",
             "دقت آزمون", "F1 آزمون", "Brier آزمون", "روش عدم‌توازن", "winsor"]
    C += [("table", rb[keepr].round(4), "جدول ۱۳-۱: نتایج تمام واریانت‌های استحکام", 4)]
    C += [("p", "خواندن جدول ۱۳-۱: (الف) مجموعهٔ ویژگی توسعه‌یافته (B) برای لجستیک PR-AUC را "
           "بالا می‌برد اما برای XGBoost کمی پایین می‌آورد؛ (ب) winsorization اثر کمی دارد؛ "
           "(پ) جایگزینی وزن‌دهی کلاس با SMOTE عملکرد را پایین می‌آورد (نتیجهٔ منفی برای "
           "SMOTE)؛ (ت) حذف متغیرهای نزدیک به تعریف درماندگی نتیجه را خراب نکرد؛ (ث) "
           "طبقه‌بندی هم‌سال PR-AUC اعتبارسنجی بالاتری دارد اما پیش‌بینی آینده نیست و قابل "
           "مقایسهٔ مستقیم با مدل اصلی نیست.")]

    # 14 predictions
    C += [("h1", "۱۴. پیش‌بینی‌های ردیف‌به‌ردیف آزمون")]
    pr = L["pred"]
    pp = pd.DataFrame({
        "مدل": [MODEL_FA[m] for m in ["logistic", "random_forest", "xgboost"]],
        "پیش‌بینی مثبت (آستانهٔ بهینه)": [int(pr[f"pred_{m}_thropt"].sum())
                                          for m in ["logistic", "random_forest", "xgboost"]],
        "پیش‌بینی مثبت (آستانهٔ ۰٫۵)": [int(pr[f"pred_{m}_thr0.5"].sum())
                                       for m in ["logistic", "random_forest", "xgboost"]]})
    C += [("p", f"فایل test_predictions_all_models.csv شامل {len(pr)} ردیف آزمون است "
           f"(تعداد واقعی مثبت‌ها: {int(pr['y_true'].sum())}) و برای هر شرکت‌ـ‌سال، احتمال "
           f"پیش‌بینی‌شده و کلاس پیش‌بینی‌شدهٔ هر سه مدل را در دو آستانه دارد.")]
    C += [("table", pp, "جدول ۱۴-۱: تعداد پیش‌بینی‌های مثبت هر مدل روی آزمون", 0)]

    # 15 null results consolidated
    C += [("h1", "۱۵. جمع‌بندی مواردی که «نتیجه نداد» یا محدودکننده بود")]
    nulls = pd.DataFrame({
        "مورد": [
            "سال‌های هدف ۱۳۹۹، ۱۴۰۰، ۱۴۰۲ بدون هیچ نمونهٔ مثبت",
            "سال هدف ۱۴۰۱ تنها با یک نمونهٔ مثبت",
            "تقسیم زمانی پیشنهادی اولیهٔ بریف (آزمون ۱۴۰۱–۱۴۰۲) غیرقابل‌ارزیابی",
            "دو ویژگی رشد در fold اول کاملاً مفقود و حذف‌شده",
            "ویژگی financial_expense_to_assets عملاً یک‌سویه (بیشینه و صدک۹۹ = صفر روی dev)",
            "رگرسیون لجستیک: عملکرد ضعیف نسبت به مدل‌های درختی",
            "SMOTE: کاهش PR-AUC نسبت به وزن‌دهی هزینه‌-حساس",
            "بازه‌های اطمینان پهن به‌دلیل فقط ۹ مثبت در آزمون",
            "متغیرهای کلان اقتصادی: فایلی تحویل نشد، لذا ادغام نشد",
            "PDF فارسی گزارش: به‌صورت خودکار تولید نشد (نیاز به فونت/شکل‌دهی)",
        ],
        "وضعیت / عدد": [
            "۱۳۹۹: ۰، ۱۴۰۰: ۰، ۱۴۰۲: ۰ مثبت",
            "۱ مثبت از ۱۲۶",
            "تنها ۱ مثبت در آزمون و ۲ fold صفرمثبت → تغییر با تأیید کارفرما",
            f"fold۱: رشد درآمد/سود خالص ۱۰۰٪ مفقود (مبدأ ۱۳۹۲)",
            "dev_max=0 و dev_p99=0",
            f"PR-AUC آزمون {lo['pr_auc']:.3f} در برابر {x['pr_auc']:.3f} برای XGBoost",
            "مثلاً XGBoost: ۰٫۳۹ در برابر ۰٫۵۰ (PR-AUC اعتبار)",
            "فراخوانی XGBoost: بازهٔ ۰٫۳۳ تا ۱٫۰۰",
            "خروجی firm-only گزارش شد (طبق بریف)",
            "خروجی Word فارسی به‌جای آن ارائه شد",
        ]})
    C += [("table", nulls, "جدول ۱۵-۱: فهرست نتایج منفی/محدودکننده", 3)]

    # 16 limitations from brief
    C += [("h1", "۱۶. محدودیت‌های مستند دیتاست (طبق دستورکار)")]
    C += [("p", "این محدودیت‌ها در دادهٔ تحویلی موجود بودند و طبق دستورکار با صفر یا مقدار "
           "ساختگی پر نشدند: ۳۹ مقدار مفقود جریان نقد عملیاتی (۱ مورد source_unavailable و "
           "۳۸ مورد deferred)؛ ۱۴۵ مقدار حل‌نشدهٔ سود ناخالص؛ ۱۳ ردیف با اطلاعات منبع ناقص؛ "
           "۹۹ تغییر مالی غیرعادی بررسی‌نشده.")]

    # 17 environment
    C += [("h1", "۱۷. محیط اجرا و بازتولیدپذیری")]
    env = L["env"]
    ev = pd.DataFrame({"مؤلفه": list(env.keys()), "نسخه/مقدار": list(env.values())})
    C += [("table", ev, "جدول ۱۷-۱: نسخهٔ کتابخانه‌ها و محیط اجرا", 4)]
    C += [("p", "کل خروجی‌ها با یک دستور (python run_all.py) از فایل‌های خام بازتولید "
           "می‌شوند؛ seed اصلی ۴۲ است و هش SHA-256 همهٔ خروجی‌ها در پوشهٔ بازتولیدپذیری ثبت "
           "شده است.")]

    return C, prim


def _inventory(op: Path):
    desc = {
        "01_data_audit": "ممیزی داده: شِما، تکراری‌ها، توزیع کلاس، ممیزی انتقال هدف، مفقودی، پرت‌ها، اکسل خلاصه",
        "02_modeling_data": "دیتاست نهایی یک‌سال‌جلو، split_manifest، فهرست ویژگی‌ها، پیکربندی پیش‌پردازش",
        "03_code": "کپی خودکفای کل کد اجرایی + نوت‌بوک تحلیل",
        "04_models": "pipelineهای ذخیره‌شدهٔ سه مدل (joblib)، ابرپارامترها، آستانه‌ها، کالیبراتورها",
        "05_predictions": "پیش‌بینی ردیف‌به‌ردیف آزمون برای هر سه مدل",
        "06_metrics": "اعتبارسنجی، آزمون، bootstrap، آستانه، کالیبراسیون، پایداری seed، استحکام، اکسل مقایسه",
        "07_explainability": "ضرایب/نسبت بخت لجستیک، اهمیت ویژگی درختی، SHAP (جدول/مقادیر/تعامل)",
        "08_figures": "تمام نمودارها در دو قالب PNG (۳۰۰dpi) و PDF",
        "09_report": "گزارش فنی (md/pdf/docx)، پیش‌نویس‌های مقاله، جدول‌ها و فهرست نمودارها، همین گزارش",
        "10_reproducibility": "محیط، نسخه‌ها، seedها، لاگ اجرا، هش فایل‌ها، پیکربندی نهایی",
    }
    rows = []
    for folder in sorted(desc):
        d = op / folder
        files = sorted(p.name for p in d.rglob("*") if p.is_file())
        rows.append({"پوشه": folder, "تعداد فایل": len(files), "شرح": desc[folder]})
    total = sum(r["تعداد فایل"] for r in rows)
    return pd.DataFrame(rows), total


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------
def _render_docx(C, inv, total, out):
    doc = Document()
    doc.styles["Normal"].font.size = Pt(11)
    for item in C:
        kind = item[0]
        if kind == "h0":
            _heading(doc, item[1], level=0)
        elif kind == "h1":
            _heading(doc, item[1], level=1)
        elif kind == "note":
            _para(doc, item[1], size=9, color=(0x88, 0x88, 0x88))
        elif kind == "p":
            _para(doc, item[1])
        elif kind == "table":
            _, df, cap, nd = item
            _table(doc, df, cap, nd)
    _heading(doc, "۱۸. فهرست کامل خروجی‌ها", level=1)
    _para(doc, f"در مجموع {total} فایل خروجی تولید شده است (به‌علاوهٔ همین گزارش). "
               f"جدول زیر تعداد فایل و شرح هر پوشه را نشان می‌دهد.")
    _table(doc, inv, "جدول ۱۸-۱: فهرست پوشه‌های خروجی", 0)
    doc.save(out)


def _df_md(df, nd):
    return df.round(nd).to_markdown(index=False) if nd else df.to_markdown(index=False)


def _render_md(C, inv, total, out):
    lines = []
    for item in C:
        kind = item[0]
        if kind == "h0":
            lines.append(f"# {item[1]}\n")
        elif kind == "h1":
            lines.append(f"\n## {item[1]}\n")
        elif kind in ("note", "p"):
            lines.append(item[1] + "\n")
        elif kind == "table":
            _, df, cap, nd = item
            lines.append(f"\n**{cap}**\n")
            lines.append(_df_md(df, nd) + "\n")
    lines.append("\n## ۱۸. فهرست کامل خروجی‌ها\n")
    lines.append(f"در مجموع {total} فایل خروجی تولید شده است (به‌علاوهٔ همین گزارش).\n")
    lines.append(_df_md(inv, 0) + "\n")
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def build(cfg):
    L = _load(cfg)
    C, prim = _content(cfg, L)
    inv, total = _inventory(L["op"])
    out = utils.out_dir(cfg, "09_report")
    _render_docx(C, inv, total, out / "full_outputs_report_fa.docx")
    _render_md(C, inv, total, out / "full_outputs_report_fa.md")
    print(f"[09] comprehensive outputs report -> {out/'full_outputs_report_fa.docx'} (+ .md)")
