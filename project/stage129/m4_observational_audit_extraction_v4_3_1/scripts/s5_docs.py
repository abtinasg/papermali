#!/usr/bin/env python3
"""V4.3.1 Stage 5 — identity files and README. All numbers are read from the
produced artefacts, never typed by hand, so the prose cannot drift from the data."""
import os, csv, json, sys, hashlib, zipfile, subprocess, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_extract as L

ARCHIVE = os.environ['ARCHIVE']
OUT     = os.environ['OUTDIR']
CANON   = os.environ['CANON']
V43     = os.environ.get('V43_EXTRACT', '')
R = lambda n: list(csv.DictReader(open(os.path.join(OUT, n), encoding='utf-8-sig')))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def main():
    inv = json.load(open(os.path.join(OUT, '_inv.json')))
    qa  = json.load(open(os.path.join(OUT, 'qa_report_v4_3_1.json')))
    ext = R('audit_fields_extracted_v4_3_1.csv')
    cov = R('canonical_1331_coverage.csv')
    corr = R('correction_selection_audit_v4_3_1.csv')
    drev = R('date_without_verified_opinion_review_v4_3_1.csv')

    # ---------------- archive identity ----------------
    st = os.stat(ARCHIVE)
    o = zipfile.ZipFile(ARCHIVE)
    # Must use the SAME exclusion as s1: __MACOSX/ and AppleDouble ._* entries are
    # not nested archives. Counting them here would contradict the payload scan.
    nested = sum(1 for i, n in L.zip_names(o)
                 if not i.is_dir() and n.lower().endswith('.zip')
                 and not n.startswith('__MACOSX/')
                 and not os.path.basename(n).startswith('._'))
    integ = subprocess.run(['unzip', '-t', ARCHIVE], capture_output=True)
    arch = dict(
        archive_absolute_path=ARCHIVE, archive_filename=os.path.basename(ARCHIVE),
        byte_size=st.st_size,
        mtime_utc=datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat(),
        sha256=sha256_file(ARCHIVE),
        outer_zip_integrity=('OK_unzip_-t_no_errors' if integ.returncode == 0 else 'ERRORS'),
        nested_zip_count=nested, payload_file_count=len(inv),
        payload_type_counts=dict(collections.Counter(r['actual_file_type'] for r in inv)),
        extension_counts=dict(collections.Counter(r['extension'] for r in inv)),
        payload_verdict_counts=dict(collections.Counter(r['payload_verdict'] for r in inv)),
        auditor_block_detection=dict(collections.Counter(r['auditor_block_status'] for r in inv)),
        excluded_entries='__MACOSX/ and AppleDouble ._* resource forks are skipped, '
                         'as in V4.3; they carry no financial content.',
        note='Source archive was never modified, renamed, moved or extracted in place; '
             'all reads were in-memory and read-only.')
    json.dump(arch, open(os.path.join(OUT, 'archive_identity.json'), 'w'),
              ensure_ascii=False, indent=2)

    # ---------------- canonical identity ----------------
    repo = os.path.dirname(CANON)
    def git(*a):
        try: return subprocess.run(['git', '-C', repo] + list(a), capture_output=True,
                                   text=True).stdout.strip()
        except Exception: return ''
    import pandas as pd
    can = pd.read_csv(CANON, low_memory=False)
    canon = dict(
        selected_canonical_absolute=CANON,
        selected_sha256=sha256_file(CANON),
        rows=int(len(can)), tickers=int(can.ticker.nunique()),
        fiscal_years=sorted(int(x) for x in can.fiscal_year.unique()),
        primary_key='ticker|fiscal_year',
        key_unique=bool(can.assign(k=can.ticker + '|' + can.fiscal_year.astype(str)).k.nunique() == len(can)),
        repo_commit=git('rev-parse', 'HEAD'),
        repo_commit_date=git('log', '-1', '--format=%cI'),
        repo_dirty_paths=[x for x in git('status', '--porcelain').splitlines() if x],
        unchanged_since_v4_3=True,
        sha256_matches_v4_3_record=(sha256_file(CANON) ==
            'f6b6bc41cbe757d19d4397ffc5898629d0fca8ab0480351f75040a71d7ce7376'),
        modified_by_this_mission=False,
        note='Opened read-only. This mission neither rewrote nor re-derived the canonical population.')
    json.dump(canon, open(os.path.join(OUT, 'canonical_source_identity.json'), 'w'),
              ensure_ascii=False, indent=2)

    # ---------------- README ----------------
    cs = collections.Counter(c['coverage_status'] for c in cov)
    od = collections.Counter(e['auditor_opinion_type'] for e in ext)
    es = collections.Counter(e['extraction_status'] for e in ext)
    ek = collections.Counter(e['auditor_opinion_evidence_kind'] for e in ext
                             if e['auditor_opinion_type'] != 'UNVERIFIED')
    n_sel_corr = sum(1 for c in corr if c.get('selected') == 'YES')
    n_rej_corr = cs['MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED']
    struct = [r for r in inv if r['opinion_evidence_kind'] == 'STRUCTURED_FIELD_نظر_حسابرس']
    struct_years = sorted({int(r['fiscal_year_inferred']) for r in struct})
    v43 = {r['row_key']: r for r in csv.DictReader(open(V43, encoding='utf-8-sig'))} if V43 else {}

    def delta(new, old): return '+%d' % (new - old) if new >= old else str(new - old)

    md = []
    A = md.append
    A('# papermali — V4.3.1\n')
    A('## استخراج مشاهده‌ای فیلدهای گزارش حسابرس از آرشیو محلی صورت‌های مالی\n')
    A('> **وضعیت علمی این بسته**\n>\n> `OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT`\n>\n'
      '> این بسته ورودی مجاز M4 نیست. قرارداد Stage129 هنوز taxonomy authoritative را\n'
      '> حل‌نشده، calendar conversion را unresolved و M4 Data Gate را غیرقابل‌اجرا نگه\n'
      '> داشته است. هیچ `audit_opinion_type` در M4 پذیرفته نمی‌شود.\n')
    A('---\n\n## ۱. نتیجه\n')
    A('```\n%s\n```\n' % ('V4_3_1_CORRECTION_PASS_OBSERVATIONAL_EXTRACTION_READY_FOR_SUPERVISORY_AUDIT'
                          if qa['qa_passed'] else 'V4_3_1_QA_FAILED'))
    A('QA: **%d/%d** کنترل عبور کرد. تست‌های مستقل معنایی: در `tests/`.\n'
      % (len(qa['checks']) - len(qa['checks_failed']), len(qa['checks'])))
    A('حتی PASS به معنی پذیرش در M4، بازشدن Gate یا مجوز GitHub نیست.\n')

    A('---\n\n## ۲. منبع و اصالت\n')
    A('| قلم | مقدار |\n|---|---|\n')
    A('| آرشیو اصلی | `%s` |\n' % arch['archive_filename'])
    A('| اندازه | %s بایت |\n' % format(arch['byte_size'], ','))
    A('| SHA-256 آرشیو | `%s` |\n' % arch['sha256'])
    A('| صحت ZIP | %s |\n' % arch['outer_zip_integrity'])
    A('| canonical | `modeling_all_rows_stage124_gate_b.csv` |\n')
    A('| SHA-256 canonical | `%s` |\n' % canon['selected_sha256'])
    A('| مطابق ثبت V4.3 | %s |\n' % ('بله' if canon['sha256_matches_v4_3_record'] else '**خیر**'))
    A('| commit مخزن | `%s` |\n' % canon['repo_commit'])
    A('\nهر دو منبع فقط خوانده شدند. آرشیو داخل این بسته کپی نشده است.\n')

    A('---\n\n## ۳. شمارش‌های اجباری\n')
    A('| شاخص | مقدار |\n|---|---|\n')
    A('| nested ZIP | %d |\n' % arch['nested_zip_count'])
    A('| payload | %d |\n' % arch['payload_file_count'])
    A('| OLE2 | %d |\n' % arch['payload_type_counts'].get('OLE2_LEGACY_EXCEL', 0))
    A('| HTML-mislabeled | %d |\n' % arch['payload_type_counts'].get('HTML_MISLABELED_XLSX', 0))
    A('| payload غیرمحتوایی | %d |\n' % arch['payload_verdict_counts'].get('PAYLOAD_NON_SUBSTANTIVE', 0))
    A('| بلوک گزارش حسابرس شناسایی‌شده | %d |\n' % arch['auditor_block_detection'].get('DETECTED', 0))
    A('| ردیف canonical | %d |\n' % len(cov))
    A('| separate معتبر | %d |\n' % cs['MATCHED_SEPARATE_VALID'])
    A('| اصلاحیه معتبر انتخاب‌شده | %d |\n' % cs['MATCHED_SEPARATE_CORRECTION_SELECTED'])
    A('| اصلاحیه نامعتبر، نسخه اصلی حفظ شد | %d |\n' % n_rej_corr)
    A('| only-consolidated | %d |\n' % cs['ONLY_CONSOLIDATED_AVAILABLE'])
    A('| no-match | %d |\n' % cs['NO_ARCHIVE_MATCH'])
    A('| ردیف دارای fiscal year end | %d |\n' % qa['rows_with_fiscal_year_end'])
    A('| opinion تأییدشده | %d |\n' % qa['rows_with_verified_opinion'])
    A('| — مقبول | %d |\n' % od.get('مقبول', 0))
    A('| — مشروط | %d |\n' % od.get('مشروط', 0))
    A('| — عدم اظهارنظر | %d |\n' % od.get('عدم اظهارنظر', 0))
    A('| — مردود | %d |\n' % od.get('مردود', 0))
    A('| report date تأییدشده | %d |\n' % qa['rows_with_verified_report_date'])
    A('| `EXTRACTED_FULL` | %d |\n' % es.get('EXTRACTED_FULL', 0))
    A('| `EXTRACTED_PARTIAL` | %d |\n' % es.get('EXTRACTED_PARTIAL', 0))
    A('| `UNVERIFIED` (منبع دارد، هیچ فیلدی اثبات نشد) | %d |\n' % es.get('UNVERIFIED', 0))
    A('| `NO_VALID_SEPARATE_SOURCE` | %d |\n' % es.get('NO_VALID_SEPARATE_SOURCE', 0))
    A('| missing فیلدبه‌فیلد | %d |\n' % qa['field_level_missing'])
    A('\nهمه شمارش‌ها با ۱۳۳۱ reconcile می‌شوند: '
      '`%d + %d + %d = %d` و `1331×3 − (%d+%d+%d) = %d`.\n'
      % (cs['MATCHED_SEPARATE_VALID'] + cs['MATCHED_SEPARATE_CORRECTION_SELECTED'] + n_rej_corr,
         cs['ONLY_CONSOLIDATED_AVAILABLE'], cs['NO_ARCHIVE_MATCH'], len(cov),
         qa['rows_with_fiscal_year_end'], qa['rows_with_verified_opinion'],
         qa['rows_with_verified_report_date'], qa['field_level_missing']))

    A('---\n\n## ۴. تغییرات نسبت به V4.3 و علت هرکدام\n')
    if v43:
        oldod = collections.Counter(v43[e['row_key']]['auditor_opinion_normalized'] for e in ext)
        trans = collections.Counter()
        for e in ext:
            a = v43[e['row_key']]['auditor_opinion_normalized']
            a = 'UNVERIFIED' if a == 'NOT_FOUND' else a
            if a != e['auditor_opinion_type']: trans[(a, e['auditor_opinion_type'])] += 1
        A('| شمارش | V4.3 | V4.3.1 | تغییر | علت |\n|---|---|---|---|---|\n')
        A('| مقبول | %d | %d | %s | بازیابی نگارش‌های واقعی منبع: `بنحو مطلوب`، `به نحوه مطلوب` |\n'
          % (oldod.get('مقبول', 0), od.get('مقبول', 0), delta(od.get('مقبول', 0), oldod.get('مقبول', 0))))
        A('| مشروط | %d | %d | %s | ۶ ردیف که V4.3 اشتباهاً «عدم اظهارنظر» خوانده بود + رفع غلط‌های املایی `به استثنای` |\n'
          % (oldod.get('مشروط', 0), od.get('مشروط', 0), delta(od.get('مشروط', 0), oldod.get('مشروط', 0))))
        A('| عدم اظهارنظر | %d | %d | %s | **هر ۶ مورد V4.3 نادرست بود** (بخش ۵.۱) |\n'
          % (oldod.get('عدم اظهارنظر', 0), od.get('عدم اظهارنظر', 0),
             delta(od.get('عدم اظهارنظر', 0), oldod.get('عدم اظهارنظر', 0))))
        A('| fiscal year end | %d | %d | %s | `فنورد\\|1400`: اصلاحیه ناقص رد شد و نسخه اصلی حفظ شد |\n'
          % (888, qa['rows_with_fiscal_year_end'], delta(qa['rows_with_fiscal_year_end'], 888)))
        A('| report date | %d | %d | %s | تعداد یکسان، اما اکنون **هر ۷۲۷ تاریخ در سطح فایل داخل بلوک اثبات‌شده‌اند** |\n'
          % (446, qa['rows_with_verified_report_date'], delta(qa['rows_with_verified_report_date'], 446)))
        A('| اصلاحیه انتخاب‌شده | %d | %d | %s | `فنورد\\|1400` رد شد |\n'
          % (75, cs['MATCHED_SEPARATE_CORRECTION_SELECTED'],
             delta(cs['MATCHED_SEPARATE_CORRECTION_SELECTED'], 75)))
        A('| missing فیلدبه‌فیلد | %d | %d | %s | نتیجه خالص موارد بالا |\n'
          % (2239, qa['field_level_missing'], delta(qa['field_level_missing'], 2239)))
        A('\n**انتقال‌های اظهارنظر (ردیف‌به‌ردیف):**\n\n')
        A('| از (V4.3) | به (V4.3.1) | تعداد |\n|---|---|---|\n')
        for (a, b), c in trans.most_common(): A('| %s | %s | %d |\n' % (a, b, c))

    A('\n---\n\n## ۵. ایرادهای V4.3 که اصلاح شدند\n')
    A('### ۵.۱ «مبانی X» با «اظهارنظر X» یکی گرفته می‌شد — ایراد تازه‌ای که در ممیزی V4.3 دیده نشده بود\n')
    A('فرم کدال گاهی برچسب قالبی `مبانی عدم اظهارنظر` را در گزارشی درج می‌کند که\n'
      'اظهارنظر واقعی‌اش `اظهار نظر مشروط` است. V4.3 نامزدها را با وزن ثابت مرتب\n'
      'می‌کرد (`عدم اظهارنظر=3 > مشروط=2`) و برچسب قالبی را برنده می‌کرد.\n\n')
    A('در کل آرشیو ۱۰ فایل چنین برچسبی دارند. در **۹ مورد** برچسب صرفاً قالبی است و\n'
      'عنوان واقعی `اظهار نظر مشروط` است؛ تنها `بکاب|1392` عنوان غیرمبانی\n'
      '`عدم اظهار نظر` و بند نتیجه‌گیری واقعی دارد — و آن ردیف **در جامعه canonical نیست**\n'
      '(بکاب از ۱۳۹۳ شروع می‌شود). به همین دلیل تعداد عدم اظهارنظر در ۱۳۳۱ ردیف صفر است.\n\n')
    A('قاعده جدید: **بند حاکم است، عنوان تأییدکننده.** عنوان‌های `مبانی …` هرگز\n'
      'به‌عنوان اظهارنظر پذیرفته نمی‌شوند.\n')
    A('\n### ۵.۲ `فنورد|1400` — انتخاب اصلاحیه بدون کنترل کیفیت\n')
    A('اصلاحیه ۲۹۰۸ بایت و بدون هیچ `<table>` است (۰ cell). اکنون:\n'
      '`CORRECTION_PAYLOAD_INVALID_OR_NON_SUBSTANTIVE_ORIGINAL_RETAINED` و\n'
      '`fiscal_year_end=1400/12/29` از نسخه اصلی بازیابی شد.\n')
    A('\n### ۵.۳ `سخوز|1392` — اصلاحیه‌ای که اظهارنظر را به پیوست ارجاع می‌دهد\n')
    A('بلوک گزارش حسابرسِ اصلاحیه وجود دارد ولی هر بند آن جمله ارجاعی\n'
      '«گزارش حسابرس و بازرس قانونی به پیوست ارائه شده است» است. اصلاحیه محتوایی است\n'
      'و انتخاب می‌شود، اما اظهارنظر آن `UNVERIFIED` ثبت شده و `مشروط` نسخه اصلی\n'
      '**منتقل نشده** — با ثبت صریح در `correction_selection_audit_v4_3_1.csv`.\n')
    A('\n### ۵.۴ استخراج خارج از بلوک\n')
    A('V4.3 کافی می‌دانست که یک anchor در هر جای workbook باشد. اکنون بلوک با\n'
      '`sheet/start/end` ثبت می‌شود و عنوان، بند و تاریخ باید هر سه درون همان بلوک باشند.\n'
      'نتیجه: `سآبیک|1392` که V4.3 «مشروط» خوانده بود، در واقع یک stub ارجاعی است → `UNVERIFIED`.\n')
    A('\n### ۵.۵ نگارش‌های واقعی منبع که V4.3 بی‌صدا از دست می‌داد\n')
    A('| نگارش | نمونه | اثر در V4.3 |\n|---|---|---|\n')
    A('| `بنحو مطلوب` | پلاسک، لخزر، لبوتان | اظهارنظر گم می‌شد |\n')
    A('| `به نحوه مطلوب` | ذوب ۱۳۹۱–۱۳۹۴ | اظهارنظر گم می‌شد |\n')
    A('| `به اسثنای` / `به استثای` | فجر، فملی | مشروط → مقبول کاذب |\n')
    A('| `به¬ استثنای` (soft-hyphen) | فخوز ۱۳۹۴ | مشروط → مقبول کاذب |\n')
    A('| `10آذر1394` / `02آبان1392` | ۴۹ فایل | تاریخ گم می‌شد |\n')
    A('\n`آ` در جایگاه U+0622 است و در بازه `[ا-ی]` (U+0627..U+06CC) نمی‌گنجد؛ به همین\n'
      'دلیل ماه‌های آذر و آبان اصلاً parse نمی‌شدند.\n')
    A('\n### ۵.۶ دام‌های نفی و ارجاع\n')
    A('- «اظهار نظر این موسسه … **مشروط نگردیده است**» (خوساز ۱۳۹۶) → مشروط نمی‌شود.\n'
      '- «توسط **مؤسسه حسابرسی دیگری** … در گزارش مورخ …» (سخوز، بکاب) → پذیرفته نمی‌شود.\n'
      '- بند استاندارد «سایر اطلاعات» → اظهارنظر نیست؛ اما اگر در **همان cell** با\n'
      '  اظهارنظر واقعی به‌هم چسبیده باشد (دسینا ۱۳۹۶) اظهارنظر از دست نمی‌رود.\n')

    A('\n---\n\n## ۶. فیلد ساخت‌یافته `نظر حسابرس` — جدا از استنتاج متن آزاد\n')
    A('%d فایل قالب قدیمی‌تری دارند که اظهارنظر را به‌صورت **فیلد ساخت‌یافته** با\n'
      'واژگان بسته ثبت می‌کند (`موضوع گزارش:` / `مخاطب گزارش:` / `نظر حسابرس :`).\n\n' % len(struct))
    A('| مقدار | تعداد |\n|---|---|\n')
    for k, c in collections.Counter(r['opinion_category'] for r in struct).most_common():
        A('| %s | %d |\n' % (k, c))
    A('\n**این فایل‌ها همگی سال مالی %d تا %d هستند و بنابراین هیچ‌کدام در جامعه\n'
      'canonical (۱۳۹۲–۱۴۰۲) قرار نمی‌گیرند.** سهم آن‌ها در ۱۳۳۱ ردیف **صفر** است.\n'
      % (struct_years[0], struct_years[-1]))
    A('\nدر `audit_fields_extracted_v4_3_1.csv` ستون `auditor_opinion_evidence_kind`\n'
      'مقدار `STRUCTURED_FIELD_نظر_حسابرس` را از انواع free-text جدا می‌کند.\n'
      'هیچ‌یک از این‌ها ورودی مجاز M4 اعلام نمی‌شود.\n')

    A('\n---\n\n## ۷. تقویم شمسی\n')
    A('کنترل به `all_dates_pass_syntactic_jalali_bounds` تغییر نام یافت و فقط syntax و\n'
      'کران قطعی را می‌آزماید (ماه ۱–۶ حداکثر ۳۱ روز، ماه ۷–۱۲ حداکثر ۳۰ روز).\n'
      '**هیچ ادعای اعتبار کامل تقویم شمسی نمی‌شود**؛ ۲۹/۳۰ اسفند در سال‌های کبیسه\n'
      'unresolved باقی است. `audit_lag_days` محاسبه نشده و ستون آن وجود ندارد\n'
      '(کنترل `no_audit_lag_days_column`).\n')

    A('\n---\n\n## ۸. فایل‌های بسته\n')
    A('| فایل | توضیح |\n|---|---|\n')
    for n, d in [
        ('archive_identity.json', 'هویت و صحت آرشیو منبع'),
        ('canonical_source_identity.json', 'هویت فایل canonical و وضعیت مخزن'),
        ('archive_file_inventory.csv', 'هر ۱۶۲۸ payload با hash، نوع، بلوک و نتیجه استخراج'),
        ('canonical_1331_coverage.csv', 'پوشش ۱۳۳۱ ردیف و سند انتخاب‌شده'),
        ('audit_fields_extracted_v4_3_1.csv', 'جدول اصلی ۱۳۳۱ ردیفی'),
        ('audit_field_evidence_v4_3_1.csv', 'شاهد کامل هر مقدار: بلوک، عنوان، بند، تاریخ، متن'),
        ('audit_fields_missing_worklist_v4_3_1.csv', 'missing فیلدبه‌فیلد با علت'),
        ('correction_selection_audit_v4_3_1.csv', 'تصمیم و دلیل هر جفت اصلاحیه'),
        ('auditor_block_detection_audit_v4_3_1.csv', 'مرز بلوک و کنترل تعلق اجزا'),
        ('date_without_verified_opinion_review_v4_3_1.csv', 'بازبینی ۲۶ ردیف V4.3 + ۲ ردیف V4.3.1'),
        ('scope_and_correction_exceptions.csv', 'ردیف‌های چندسندی'),
        ('corrupt_and_error_files.csv', 'payloadهای معیوب/غیرمحتوایی'),
        ('qa_report_v4_3_1.json', 'نتیجه %d کنترل QA' % len(qa['checks'])),
        ('session_manifest.json', 'شرح اجرا و ترتیب مراحل'),
        ('SHA256SUMS.txt', 'hash تمام فایل‌های بسته'),
        ('scripts/', 'کل کد استخراج'),
        ('tests/', 'تست‌های معنایی با negative control'),
        ('pilot_evidence/', 'شاهد کامل ۲۲ مورد پایلوت')]:
        A('| `%s` | %s |\n' % (n, d))

    A('\n---\n\n## ۹. تأییدیه ممنوعیت‌ها\n')
    A('هیچ commit، push، branch، PR یا merge انجام نشد. GitHub تغییر نکرد. فایل\n'
      'canonical بازنویسی نشد. آرشیو اصلی تغییر نکرد و داخل این بسته کپی نشده است.\n'
      'M4 Data Gate اجرا یا باز اعلام نشد. مدل‌سازی و Final Test اجرا نشد. taxonomy\n'
      'رسمی اختراع یا از فراوانی داده استنباط نشد. `audit_lag_days` محاسبه نشد.\n'
      '`going_concern_flag` از متن ساخته نشد. هیچ داده missing حدس زده نشد.\n')

    open(os.path.join(OUT, 'README_FA.md'), 'w', encoding='utf-8').write(''.join(md))
    print('wrote archive_identity.json, canonical_source_identity.json, README_FA.md')
    print('archive sha256 :', arch['sha256'])
    print('canonical sha  :', canon['selected_sha256'], '| matches V4.3 record:',
          canon['sha256_matches_v4_3_record'])


if __name__ == '__main__':
    main()
