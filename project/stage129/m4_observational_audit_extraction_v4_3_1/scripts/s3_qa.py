#!/usr/bin/env python3
"""V4.3.1 Stage 3 — QA. These checks test SEMANTICS, not the mere presence of an
evidence_location string or a controlled vocabulary."""
import os, re, csv, json, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_extract as L
import pandas as pd

OUT   = os.environ['OUTDIR']
CANON = os.environ['CANON']
V43   = os.environ.get('V43_EXTRACT', '')
R = lambda n: list(csv.DictReader(open(os.path.join(OUT, n), encoding='utf-8-sig')))

VOCAB = {'مقبول', 'مشروط', 'مردود', 'عدم اظهارنظر', 'UNVERIFIED'}
sq = L.squash


def main():
    inv  = json.load(open(os.path.join(OUT, '_inv.json')))
    ext  = R('audit_fields_extracted_v4_3_1.csv')
    ev   = {e['row_key']: e for e in R('audit_field_evidence_v4_3_1.csv')}
    cov  = R('canonical_1331_coverage.csv')
    miss = R('audit_fields_missing_worklist_v4_3_1.csv')
    corr = R('correction_selection_audit_v4_3_1.csv')
    blk  = R('auditor_block_detection_audit_v4_3_1.csv')
    drev = R('date_without_verified_opinion_review_v4_3_1.csv')
    invm = {r['relative_path']: r for r in inv}

    can = pd.read_csv(CANON, low_memory=False)
    withop   = [e for e in ext if e['auditor_opinion_type'] != 'UNVERIFIED']
    withdate = [e for e in ext if e['auditor_report_date'] != 'NOT_FOUND']
    withfye  = [e for e in ext if e['fiscal_year_end'] != 'NOT_FOUND']

    def in_block(loc, e):
        """location string must sit inside the recorded block of THIS row"""
        b = ev.get(e['row_key'])
        if not b or not loc or '!' not in loc: return False
        sheet, rc = loc.split('!', 1)
        m = re.match(r'R(\d+)C(\d+)$', rc)
        if not m: return False
        if sheet != b['auditor_block_sheet']: return False
        return int(b['auditor_block_start']) <= int(m.group(1)) <= int(b['auditor_block_end'])

    C = {}
    # ---------- population reconciliation ----------
    C['canonical_rows_1331'] = len(can) == 1331
    C['canonical_tickers_130'] = int(can.ticker.nunique()) == 130
    C['coverage_rows_1331'] = len(cov) == 1331
    C['extracted_rows_1331'] = len(ext) == 1331
    C['extract_key_unique'] = len({e['row_key'] for e in ext}) == 1331
    C['coverage_status_sums_to_1331'] = sum(collections.Counter(c['coverage_status'] for c in cov).values()) == 1331
    C['evidence_rows_reconcile_to_selected_sources'] = len(ev) == sum(1 for e in ext if e['source_relative_path'])
    C['block_audit_reconciles_to_selected_sources'] = len(blk) == sum(1 for e in ext if e['source_relative_path'])
    C['missing_worklist_reconciles_to_1331x3'] = len(miss) == 1331 * 3 - (len(withfye) + len(withop) + len(withdate))

    # ---------- source discipline ----------
    C['no_consolidated_used_as_separate'] = all(e['statement_scope'] != 'consolidated' for e in ext if e['source_relative_path'])
    C['no_unaudited_used'] = all(e['audit_status'] != 'unaudited' for e in ext if e['source_relative_path'])
    C['all_sources_have_sha256'] = all(e['source_sha256'] for e in ext if e['source_relative_path'])
    C['all_inventory_have_sha256'] = all(r['sha256'] for r in inv if r['byte_size'] > 0)
    C['opinion_vocabulary_controlled'] = all(e['auditor_opinion_type'] in VOCAB for e in ext)

    # ---------- correction selection (requirement 1) ----------
    C['no_selected_correction_is_non_substantive'] = all(
        c['correction_payload_verdict'] == 'PAYLOAD_SUBSTANTIVE'
        for c in corr if c.get('selected') == 'YES')
    C['no_selected_correction_has_suspicious_small_payload'] = all(
        'SUSPICIOUS_SMALL_PAYLOAD' not in (c.get('correction_verdict_reason') or '')
        for c in corr if c.get('selected') == 'YES')
    C['every_field_lost_to_a_correction_has_a_documented_reason'] = all(
        c.get('field_loss_reason') for c in corr
        if c.get('selected') == 'YES' and c.get('fields_lost_vs_original'))
    C['every_correction_pair_has_an_audit_row'] = all(
        c.get('selection_status') for c in corr if c.get('row_key'))

    # ---------- auditor block (requirement 2) ----------
    C['every_opinion_has_a_detected_auditor_block'] = all(
        ev[e['row_key']]['auditor_block_sheet'] and ev[e['row_key']]['auditor_block_start']
        for e in withop)
    C['every_opinion_paragraph_inside_its_block'] = all(
        in_block(ev[e['row_key']]['opinion_paragraph_location'], e) for e in withop)
    C['opinion_heading_and_paragraph_same_sheet'] = all(
        (ev[e['row_key']]['opinion_heading_location'] in ('', 'ABSENT_IN_BLOCK')) or
        (ev[e['row_key']]['opinion_heading_location'].split('!')[0] ==
         ev[e['row_key']]['opinion_paragraph_location'].split('!')[0]) for e in withop)
    C['opinion_heading_inside_its_block_when_present'] = all(
        ev[e['row_key']]['opinion_heading_location'] in ('', 'ABSENT_IN_BLOCK') or
        in_block(ev[e['row_key']]['opinion_heading_location'], e) for e in withop)

    # ---------- decisive evidence text (requirement 4) ----------
    C['every_opinion_has_non_empty_paragraph_text'] = all(
        len(ev[e['row_key']]['opinion_paragraph_text'].strip()) > 0 for e in withop)
    # مقبول must show the COMPLETE fair-presentation formula, untruncated
    C['unqualified_shows_complete_fair_presentation_phrase'] = all(
        L.FAIR_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text']))
        for e in withop if e['auditor_opinion_type'] == 'مقبول'
        and 'STRUCTURED_FIELD' not in e['auditor_opinion_evidence_kind'])
    # ...and must NOT carry an exception clause, nor a modified heading in the block
    C['unqualified_has_no_exception_clause'] = all(
        not L.EXCEPT_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text']))
        for e in withop if e['auditor_opinion_type'] == 'مقبول'
        and 'STRUCTURED_FIELD' not in e['auditor_opinion_evidence_kind'])
    C['no_unqualified_coexists_with_modified_heading'] = all(
        not re.match(r'^(مبانی\s*)?اظهار\s*نظر\s*(مشروط|مردود)$|^(مبانی\s*)?عدم\s*اظهار\s*نظر$',
                     (ev[e['row_key']]['opinion_heading_text'] or '').strip(' :.-'))
        for e in withop if e['auditor_opinion_type'] == 'مقبول')
    # مشروط must be evidenced, never taken from a bare substring or a negated one
    C['qualified_evidenced_by_formula_or_heading_not_substring'] = all(
        (L.FAIR_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text'])) and
         L.EXCEPT_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text'])))
        or 'STRUCTURED_FIELD' in e['auditor_opinion_evidence_kind']
        for e in withop if e['auditor_opinion_type'] == 'مشروط')
    C['no_opinion_from_negated_phrase'] = all(
        not re.search(r'مشروطنگردید|مشروطنشد|نگردیدهاست$', sq(ev[e['row_key']]['opinion_paragraph_text'])[-40:])
        for e in withop)
    C['no_opinion_taken_from_another_firms_report'] = all(
        not L.OTHERREP_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text'])) for e in withop)
    C['no_opinion_from_referral_stub'] = all(
        not L.REFERRAL_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text'])) for e in withop)
    C['disclaimer_shows_disclaimer_conclusion'] = all(
        L.DISCLAIM_SQ.search(sq(ev[e['row_key']]['opinion_paragraph_text']))
        for e in withop if e['auditor_opinion_type'] == 'عدم اظهارنظر'
        and 'STRUCTURED_FIELD' not in e['auditor_opinion_evidence_kind'])

    # ---------- report date (requirement 3) ----------
    C['every_report_date_inside_its_auditor_block'] = all(
        in_block(ev[e['row_key']]['auditor_report_date_location'], e) for e in withdate)
    C['every_report_date_has_anchor_text'] = all(
        'تاریخ تهیه گزارش' in (ev[e['row_key']]['auditor_report_date_anchor_text'] or '') for e in withdate)
    C['every_report_date_has_context'] = all(
        len((ev[e['row_key']]['auditor_report_date_context'] or '').strip()) > 0 for e in withdate)
    C['report_date_not_taken_from_statement_or_meeting_date'] = all(
        not re.search(r'تاریخ\s*(مجمع|انتشار|ارسال|تصویب)',
                      ev[e['row_key']]['auditor_report_date_anchor_text'] or '') for e in withdate)

    # ---------- fiscal year end + calendar (requirement 5) ----------
    C['all_dates_pass_syntactic_jalali_bounds'] = all(
        L.syntactic_jalali_bounds_ok(v)
        for e in ext for v in [e['fiscal_year_end'], e['auditor_report_date']] if v != 'NOT_FOUND')
    C['fiscal_year_end_matches_fiscal_year'] = all(
        e['fiscal_year_end'].startswith(str(e['fiscal_year'])) for e in withfye)
    C['every_fiscal_year_end_has_location_and_context'] = all(
        ev[e['row_key']]['fiscal_year_end_location'] and ev[e['row_key']]['fiscal_year_end_context']
        for e in withfye)

    # ---------- contract guards (requirement 7) ----------
    hdr = open(os.path.join(OUT, 'audit_fields_extracted_v4_3_1.csv'), encoding='utf-8-sig').readline()
    C['no_audit_lag_days_column'] = 'audit_lag' not in hdr.lower()
    C['no_going_concern_column'] = 'going_concern' not in hdr.lower()
    C['every_row_carries_not_admitted_to_M4_label'] = all(
        e['scientific_status'] == 'OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT'
        for e in ext)

    # ---------- V4.3 regression coverage ----------
    if V43 and os.path.exists(V43):
        v43 = {r['row_key']: r for r in csv.DictReader(open(V43, encoding='utf-8-sig'))}
        n26 = {k for k, o in v43.items()
               if o['auditor_report_date'] != 'NOT_FOUND' and o['auditor_opinion_normalized'] == 'NOT_FOUND'}
        C['all_v43_date_without_opinion_rows_reviewed'] = n26 <= {d['row_key'] for d in drev}
        C['all_v43_disclaimer_rows_rechecked'] = all(
            k in ev for k, o in v43.items() if o['auditor_opinion_normalized'].startswith('عدم'))

    # ---------- named regression cases ----------
    fn = next((e for e in ext if e['row_key'] == 'فنورد|1400'), None)
    C['fanavard_1400_original_retained_with_fye'] = bool(
        fn and fn['coverage_status'] == 'MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED'
        and fn['fiscal_year_end'] == '1400/12/29')
    sk = next((e for e in ext if e['row_key'] == 'سخوز|1392'), None)
    C['sakhoz_1392_opinion_not_guessed_from_either_version'] = bool(
        sk and sk['auditor_opinion_type'] == 'UNVERIFIED')
    kh = next((e for e in ext if e['row_key'] == 'خوساز|1396'), None)
    C['khosaz_1396_not_misread_as_disclaimer'] = bool(kh and kh['auditor_opinion_type'] == 'مشروط')

    failed = [k for k, v in C.items() if not v]
    qa = dict(
        generated_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        version='V4.3.1',
        canonical_rows=len(can), canonical_tickers=int(can.ticker.nunique()),
        archive_payloads_scanned=len(inv),
        payload_verdicts=dict(collections.Counter(r['payload_verdict'] for r in inv)),
        auditor_block_detection=dict(collections.Counter(r['auditor_block_status'] for r in inv)),
        coverage_status_counts=dict(collections.Counter(c['coverage_status'] for c in cov)),
        rows_with_fiscal_year_end=len(withfye),
        rows_with_verified_opinion=len(withop),
        rows_with_verified_report_date=len(withdate),
        opinion_distribution=dict(collections.Counter(e['auditor_opinion_type'] for e in ext)),
        opinion_evidence_kind=dict(collections.Counter(
            e['auditor_opinion_evidence_kind'] for e in withop)),
        extraction_status=dict(collections.Counter(e['extraction_status'] for e in ext)),
        field_level_missing=len(miss),
        correction_pairs_audited=len(corr),
        corrections_selected=sum(1 for c in corr if c.get('selected') == 'YES'),
        corrections_rejected_original_retained=sum(
            1 for c in cov if c['coverage_status'] == 'MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED'),
        date_without_verified_opinion_reviewed=len(drev),
        scientific_status='OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT',
        checks=C, checks_failed=failed, qa_passed=not failed)
    json.dump(qa, open(os.path.join(OUT, 'qa_report_v4_3_1.json'), 'w'), ensure_ascii=False, indent=2)

    for k, v in C.items():
        print(('  PASS  ' if v else '  FAIL  ') + k)
    print('\nQA_PASSED', qa['qa_passed'], '| failed:', failed)


if __name__ == '__main__':
    main()
