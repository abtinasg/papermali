#!/usr/bin/env python3
"""V4.3.1 independent tests — NEGATIVE CONTROLS.

These do not check that an evidence_location string exists or that a value is in
a controlled vocabulary. They construct documents that a naive extractor gets
WRONG and assert this extractor refuses them.

Run:  python tests/test_extraction_semantics.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import lib_extract as L

FAILS = []


def check(name, cond, detail=''):
    print(('  PASS  ' if cond else '  FAIL  ') + name + (('  <- ' + detail) if (detail and not cond) else ''))
    if not cond: FAILS.append(name)


def doc(rows, sheet='Sheet1'):
    """rows: list of (row, col, text) -> normalised cell grid"""
    return [(sheet, r, c, L.norm(t)) for r, c, t in rows]


# A minimal but REAL auditor-report skeleton: title, structural markers, then the
# financial-statement grid which terminates the block.
def report(body, tail_stmt=True, date_row=None):
    rows = [(9, 19, 'گزارش حسابرس مستقل و بازرس قانونی'),
            (12, 19, 'به مجمع عمومی صاحبان سهام'),
            (13, 14, 'گزارش نسبت به صورت های مالی'),
            (14, 14, 'بند مقدمه')]
    rows += body
    if date_row: rows += date_row
    if tail_stmt:
        rows += [(200, 1, 'درصد تغییر'), (200, 5, 'ترازنامه'), (201, 2, 'موجودی نقد')]
    return doc(rows)


FAIR = 'به نظر این موسسه، صورتهای مالی یاد شده در بالا، وضعیت مالی شرکت الف (سهامی عام) در تاریخ 29 اسفند 1395 و عملکرد مالی و جریانهای نقدی آن را برای سال مالی منتهی به تاریخ مزبور، از تمام جنبه های با اهمیت، طبق استانداردهای حسابداری، به نحو مطلوب نشان می دهد.'
QUAL = 'به نظر این موسسه، به استثنای آثار موارد مندرج در بندهای 4 و 5، صورتهای مالی یاد شده در بالا، وضعیت مالی شرکت الف (سهامی عام) در تاریخ 29 اسفند 1395 را از تمام جنبه های با اهمیت، طبق استانداردهای حسابداری، به نحو مطلوب نشان می دهد.'

print('--- opinion: negative controls ---')

# 1. an exception clause must forbid مقبول, even though "به نحو مطلوب" is present
c = L.extract_opinion(report([(30, 14, 'اظهار نظر'), (31, 2, QUAL)]), None)
blk, _ = L.detect_auditor_block(report([(30, 14, 'اظهار نظر'), (31, 2, QUAL)]))
c = L.extract_opinion(report([(30, 14, 'اظهار نظر'), (31, 2, QUAL)]), blk)
check('exception_clause_blocks_unqualified', c['opinion_category'] == 'مشروط', c['opinion_category'])

# 2. "مشروط نگردیده است" must NOT produce مشروط
NEG = ('اظهار نظر این موسسه در اثر مفاد بند فوق مشروط نگردیده است. این بند صرفا جهت '
       'اطلاع مجمع عمومی صاحبان سهام درج شده است و اثری بر اظهار نظر ندارد.')
cells = report([(30, 14, 'اظهار نظر'), (31, 2, FAIR), (34, 2, NEG)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('negated_qualification_not_read_as_qualified', c['opinion_category'] == 'مقبول', c['opinion_category'])

# 3. a referral stub must yield NO opinion
STUB = 'گزارش حسابرس و بازرس قانونی به پیوست ارائه شده است. مراتب جهت استحضار اعلام می گردد.'
cells = report([(20, 14, 'اظهار نظر'), (21, 2, STUB)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('referral_stub_yields_no_opinion', c['opinion_category'] == '' and 'REFERRAL' in c['opinion_reject_reason'],
      repr(c['opinion_category']) + c['opinion_reject_reason'])

# 4. another firm's prior-year opinion must not be adopted
OTHER = ('صورتهای مالی سال مالی منتهی به 30 اسفند 1391 شرکت، توسط مؤسسه حسابرسی دیگری '
         'مورد حسابرسی قرار گرفته و در گزارش مورخ 19 اردیبهشت 1392 آن مؤسسه، صورتهای مالی '
         'مزبور را به نحو مطلوب نشان می دهد اعلام کرده است.')
cells = report([(44, 14, 'سایر بندهای توضیحی'), (45, 2, OTHER)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('other_firms_report_not_adopted', c['opinion_category'] == '', c['opinion_category'])

# 5. the "سایر اطلاعات" boilerplate alone is not an opinion
BOIL = ('مسئولیت "سایر اطلاعات" با هیات مدیره شرکت است. اظهارنظر این موسسه نسبت به صورتهای '
        'مالی در برگیرنده اظهارنظر نسبت به "سایر اطلاعات" نیست و نسبت به آن هیچ اطمینانی اظهار نمی شود.')
cells = report([(41, 14, 'گزارش در مورد سایر اطلاعات'), (42, 2, BOIL)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('other_information_boilerplate_is_not_an_opinion', c['opinion_category'] == '', c['opinion_category'])

# 6. ...but an opinion CONCATENATED with that boilerplate must still be read
cells = report([(30, 14, 'اظهار نظر'), (31, 2, FAIR + ' 12. ' + BOIL)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('opinion_concatenated_with_boilerplate_still_read', c['opinion_category'] == 'مقبول', c['opinion_category'])

# 7. a "مبانی …" basis label must not outrank the real opinion heading (خوساز|1396)
cells = report([(29, 12, 'مبانی عدم اظهارنظر'), (30, 2, 'شرح مبانی و دلایل مربوطه در این بند تشریح شده است و اثر آن بر صورتهای مالی تعیین نگردید.'),
                (33, 12, 'اظهار نظر مشروط'), (35, 2, QUAL)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('basis_label_does_not_outrank_real_opinion_heading', c['opinion_category'] == 'مشروط', c['opinion_category'])

# 8. a clean unqualified paragraph under a مشروط heading is a contradiction -> UNVERIFIED
cells = report([(31, 14, 'اظهار نظر مشروط'), (32, 2, FAIR)])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('contradictory_heading_and_paragraph_yield_unverified',
      c['opinion_category'] == '' and 'BLOCKED' in c['opinion_reject_reason'], c['opinion_category'])

# 9. content OUTSIDE the auditor block must never be used
cells = doc([(9, 19, 'گزارش حسابرس مستقل و بازرس قانونی'), (12, 19, 'به مجمع عمومی صاحبان سهام'),
             (13, 14, 'گزارش نسبت به صورت های مالی'), (14, 14, 'بند مقدمه'),
             (15, 2, STUB),
             (30, 1, 'درصد تغییر'), (30, 5, 'ترازنامه'),
             (400, 14, 'اظهار نظر'), (401, 2, FAIR)])       # opinion AFTER the statements
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('opinion_outside_block_not_used', c['opinion_category'] == '', c['opinion_category'])

print('--- report date: negative controls ---')

DATE_OK = [(60, 24, 'تاریخ تهیه گزارش'), (60, 23, '20اردیبهشت1393'), (62, 4, 'موسسه حسابرسی نمونه')]
cells = report([(30, 14, 'اظهار نظر'), (31, 2, FAIR)], date_row=DATE_OK)
blk, _ = L.detect_auditor_block(cells); d = L.extract_report_date(cells, blk)
check('report_date_in_block_accepted', d['auditor_report_date'] == '1393/02/20', d['auditor_report_date'])
check('report_date_carries_anchor_and_context',
      'تاریخ تهیه گزارش' in d['auditor_report_date_anchor_text'] and d['auditor_report_date_context'].strip() != '')

# date anchor placed AFTER the financial statements (outside the block) must be refused
cells = doc([(9, 19, 'گزارش حسابرس مستقل و بازرس قانونی'), (12, 19, 'به مجمع عمومی صاحبان سهام'),
             (13, 14, 'گزارش نسبت به صورت های مالی'), (14, 14, 'بند مقدمه'), (15, 2, FAIR),
             (30, 1, 'درصد تغییر'), (30, 5, 'ترازنامه'),
             (500, 24, 'تاریخ تهیه گزارش'), (500, 23, '20اردیبهشت1393')])
blk, _ = L.detect_auditor_block(cells); d = L.extract_report_date(cells, blk)
check('report_date_outside_block_refused', d['auditor_report_date'] == '', d['auditor_report_date'])

# a meeting / publication date must not stand in for the auditor report date
cells = report([(30, 14, 'اظهار نظر'), (31, 2, FAIR)],
               date_row=[(60, 24, 'تاریخ مجمع'), (60, 23, '20اردیبهشت1393')])
blk, _ = L.detect_auditor_block(cells); d = L.extract_report_date(cells, blk)
check('meeting_date_not_used_as_report_date', d['auditor_report_date'] == '', d['auditor_report_date'])

print('--- source-text robustness (must NOT silently drop real data) ---')
for label, txt, want in [
        ('بنحو_variant',      FAIR.replace('به نحو', 'بنحو'), 'مقبول'),
        ('به_نحوه_variant',   FAIR.replace('به نحو', 'به نحوه'), 'مقبول'),
        ('اسثنای_typo',       QUAL.replace('به استثنای', 'به اسثنای'), 'مشروط'),
        ('soft_hyphen_except', QUAL.replace('به استثنای', 'به¬ استثنای'), 'مشروط')]:
    cells = report([(30, 14, 'اظهار نظر'), (31, 2, txt)])
    blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
    check('variant_' + label, c['opinion_category'] == want, c['opinion_category'])

print('--- jalali: syntax + hard bounds ONLY (no calendar authority claimed) ---')
check('rejects_month_13', not L.syntactic_jalali_bounds_ok('1395/13/01'))
check('rejects_day_32', not L.syntactic_jalali_bounds_ok('1395/01/32'))
check('rejects_day_31_in_month_7', not L.syntactic_jalali_bounds_ok('1395/07/31'))
check('accepts_1395_12_30_without_asserting_leap_year', L.syntactic_jalali_bounds_ok('1395/12/30'))
check('rejects_free_text', not L.syntactic_jalali_bounds_ok('حدود اسفند'))
check('parses_aazar_month_no_space', L.jdate('10آذر1394') == '1394/09/10', L.jdate('10آذر1394'))
check('parses_aaban_month_no_space', L.jdate('02آبان1392') == '1392/08/02', L.jdate('02آبان1392'))

print('--- structured field vs free text ---')
cells = doc([(9, 1, 'گزارش حسابرس مستقل و بازرس قانونی نسبت به صورتهای مالی'),
             (10, 23, 'موضوع گزارش:'), (12, 23, 'مخاطب گزارش:'),
             (13, 1, 'مشروط'), (14, 23, 'نظر حسابرس :'),
             (30, 1, 'درصد تغییر'), (30, 5, 'ترازنامه')])
blk, _ = L.detect_auditor_block(cells); c = L.extract_opinion(cells, blk)
check('structured_field_read_as_structured', c['opinion_category'] == 'مشروط'
      and c['opinion_evidence_kind'] == 'STRUCTURED_FIELD_نظر_حسابرس', c['opinion_evidence_kind'])

print('--- payload substance gate ---')
check('empty_html_has_no_block_and_no_cells', L.grid(b'<html><head></head><body></body></html>',
      'HTML_MISLABELED_XLSX')[0] == [])

print()
if FAILS:
    print('TESTS FAILED:', FAILS); sys.exit(1)
print('ALL TESTS PASSED')
