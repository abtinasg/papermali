# بسته تحویل Stage121 به برنامه‌نویس

## فایل مرجع
- فایل مبنا: `financial_statements_article_panel_clean_completion_worklist_stage120_working_batch2_9of10_ocf_completed.xlsx`
- شیت مبنا: `modeling_target_ready_1392_1402`
- SHA-256 فایل مبنا: `e85e796ad12267666ed72b12dd99a0c706e30e0b14ce8b021f4f266f4c9e2825`

## فایل‌های اصلی برای برنامه‌نویسی
1. `modeling_training_candidates_stage121.csv`
   - 1,111 ردیف
   - فقط ردیف‌هایی که `usable_for_model_flag=1` و target معتبر 0/1 دارند.
   - توزیع target: کلاس 0 = 1,067، کلاس 1 = 44.
2. `modeling_all_rows_stage121.csv`
   - همه 1,331 ردیف، شامل ردیف‌های غیرقابل‌استفاده و targetهای مفقود برای قابلیت ردیابی.
3. `financial_distress_programmer_handoff_stage121_with_documented_limitations.xlsx`
   - همان داده‌ها به‌همراه Data Dictionary، Missing Data، QC، محدودیت‌ها و مانیفست منابع.

## قواعد مهم
- هیچ مقدار مفقودی در این مرحله با صفر، میانگین، میانه یا تخمین پر نشده است.
- هیچ scaling، normalization، winsorization، train/test split یا مدل‌سازی انجام نشده است.
- هرگونه imputation باید فقط روی داده آموزش و داخل هر fold انجام شود تا data leakage رخ ندهد.
- به‌دلیل نامتوازن‌بودن کلاس هدف، معیارهایی مانند PR-AUC، Recall، F1 و Balanced Accuracy در کنار ROC-AUC گزارش شوند.
- ساخت target سال بعد یا lag/lead هنوز انجام نشده و باید مطابق طرح پژوهش به‌صورت صریح در کد تعریف شود.
- split زمانی/شرکت‌محور باید قبل از مدل‌سازی نهایی مشخص شود؛ random split ساده ممکن است باعث نشت اطلاعات بین سال‌های یک شرکت شود.

## محدودیت‌های پذیرفته‌شده توسط کاربر
- 39 مقدار درون‌دامنه OCF مفقود است: خبهمن 1392 با `source_unavailable_codal` و 38 مورد دیگر deferred.
- 145 مقدار درون‌دامنه gross_profit حل‌نشده است.
- 13 ردیف provenance ناقص دارد.
- 99 تغییر مالی غیرعادی با منبع اصلی کنترل نشده است.

این بسته «قابل تحویل برای برنامه‌نویسی با محدودیت‌های مستند» است؛ نه دیتاست کاملاً تکمیل و منبع‌سنجی‌شده.
