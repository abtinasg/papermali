#!/usr/bin/env python3
"""V4.3.1 Stage 2 — correction selection, canonical matching, and all CSV outputs.

READ-ONLY on the canonical population file.

Correction rule (V4.3.1): being labelled "اصلاحیه" is NOT sufficient to be
selected. The correction payload must first be proven substantive. An invalid or
non-substantive correction never displaces a healthy original.

No value is ever merged across two documents: every field of a canonical row
comes from ONE selected source document, so field-level provenance is exact.
Values the non-selected version carried are reported in the correction audit and
are deliberately NOT transferred.
"""
import os, re, csv, json, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_extract as L
import pandas as pd

OUT   = os.environ['OUTDIR']
CANON = os.environ['CANON']
V43   = os.environ.get('V43_EXTRACT', '')

FIELDS = ['fiscal_year_end', 'auditor_opinion_type', 'auditor_report_date']


def observed(rec, fy):
    """Which of the three fields this payload actually evidences, for THIS year."""
    fye = rec['fye_content'] if (rec['fye_content'] and rec['fye_content'].startswith(str(fy))) else ''
    return {'fiscal_year_end': fye,
            'auditor_opinion_type': rec['opinion_category'],
            'auditor_report_date': rec['auditor_report_date']}


def score(rec, fy):
    o = observed(rec, fy)
    return (-sum(1 for v in o.values() if v), rec['relative_path'])


def wcsv(name, rows, fields=None):
    p = os.path.join(OUT, name)
    fields = fields or (list(rows[0].keys()) if rows else ['note'])
    with open(p, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
    return p


def main():
    inv = json.load(open(os.path.join(OUT, '_inv.json')))
    corrupt = json.load(open(os.path.join(OUT, '_corrupt.json')))

    can = pd.read_csv(CANON, low_memory=False)
    can['ticker_n'] = can.ticker.map(L.norm)
    assert len(can) == 1331 and can.ticker.nunique() == 130, 'CANONICAL POPULATION MISMATCH'

    by = collections.defaultdict(list)
    for r in inv:
        if r['ticker_inferred'] and r['fiscal_year_inferred']:
            by[(r['ticker_inferred'], int(r['fiscal_year_inferred']))].append(r)

    cov, ext, ev, miss, exc, corr_audit, blk_audit, date_review = [], [], [], [], [], [], [], []

    for _, cr in can.iterrows():
        t, fy = cr.ticker_n, int(cr.fiscal_year)
        key = '%s|%d' % (cr.ticker, fy)
        files = by.get((t, fy), [])
        good = [f for f in files if f['parse_status'] == 'OK']
        sep = [f for f in good if f['scope_inferred'] == 'separate' and f['audited_marker'] != 'unaudited']
        con = [f for f in good if f['scope_inferred'] == 'consolidated']
        unaud = [f for f in good if f['audited_marker'] == 'unaudited']

        originals   = sorted([f for f in sep if f['correction_marker'] == 'original'],    key=lambda f: score(f, fy))
        corrections = sorted([f for f in sep if f['correction_marker'] == 'correction'], key=lambda f: score(f, fy))
        sub_corr = [c for c in corrections if c['payload_verdict'] == 'PAYLOAD_SUBSTANTIVE']

        chosen = None; role = ''; status = None; sel_note = ''
        if sep:
            if corrections and sub_corr:
                chosen, role = sub_corr[0], 'correction'
                status = 'MATCHED_SEPARATE_CORRECTION_SELECTED'
                sel_note = 'CORRECTION_PAYLOAD_SUBSTANTIVE_SELECTED'
            elif corrections and not sub_corr and originals:
                chosen, role = originals[0], 'original'
                status = 'MATCHED_SEPARATE_CORRECTION_REJECTED_ORIGINAL_RETAINED'
                sel_note = 'CORRECTION_PAYLOAD_INVALID_OR_NON_SUBSTANTIVE_ORIGINAL_RETAINED'
            elif corrections and not sub_corr and not originals:
                chosen, role = corrections[0], 'correction'
                status = 'ONLY_NON_SUBSTANTIVE_CORRECTION_AVAILABLE'
                sel_note = 'NO_ORIGINAL_TO_FALL_BACK_TO'
            else:
                chosen, role = originals[0], 'original'
                status = 'MATCHED_SEPARATE_VALID'
                sel_note = 'SINGLE_OR_BEST_ORIGINAL' if len(originals) == 1 else 'MULTIPLE_ORIGINALS_BEST_EVIDENCE_SELECTED'
        elif con:   status = 'ONLY_CONSOLIDATED_AVAILABLE'
        elif unaud: status = 'ONLY_UNAUDITED_AVAILABLE'
        elif files: status = 'CORRUPT_OR_ERROR_PAYLOAD'
        else:       status = 'NO_ARCHIVE_MATCH'

        # ---------- correction selection audit (every correction pair) ----------
        if corrections:
            alt = originals[0] if originals else None
            o_sel = observed(chosen, fy) if chosen else {k: '' for k in FIELDS}
            o_alt = observed(alt, fy) if alt else {k: '' for k in FIELDS}
            lost = [k for k in FIELDS if o_alt.get(k) and not o_sel.get(k)]
            reasons = []
            for k in lost:
                if k == 'auditor_opinion_type' and chosen and 'REFERRAL' in chosen['opinion_reject_reason']:
                    reasons.append('%s:CORRECTION_DEFERS_OPINION_TO_ATTACHMENT_NOT_TRANSFERRED' % k)
                elif role == 'correction':
                    reasons.append('%s:ABSENT_FROM_SUPERSEDING_CORRECTION_NOT_TRANSFERRED' % k)
                else:
                    reasons.append('%s:ABSENT_FROM_RETAINED_ORIGINAL' % k)
            for c in corrections:
                corr_audit.append(dict(
                    row_key=key, ticker=cr.ticker, fiscal_year=fy,
                    correction_path=c['relative_path'], correction_sha256=c['sha256'],
                    correction_byte_size=c['byte_size'], correction_cell_count=c['cell_count'],
                    correction_payload_verdict=c['payload_verdict'],
                    correction_verdict_reason=c['payload_verdict_reason'],
                    correction_opinion=c['opinion_category'] or 'UNVERIFIED',
                    correction_opinion_reject=c['opinion_reject_reason'],
                    original_path=alt['relative_path'] if alt else '',
                    original_sha256=alt['sha256'] if alt else '',
                    original_opinion=(alt['opinion_category'] or 'UNVERIFIED') if alt else '',
                    selected=('YES' if chosen and c['relative_path'] == chosen['relative_path'] else 'NO'),
                    selected_role=role, selection_status=status, selection_note=sel_note,
                    fields_in_original='|'.join(k for k in FIELDS if o_alt.get(k)),
                    fields_in_selected='|'.join(k for k in FIELDS if o_sel.get(k)),
                    fields_lost_vs_original='|'.join(lost),
                    field_loss_reason='|'.join(reasons),
                    decision_rationale=(
                        'Correction payload proven substantive; supersedes original. '
                        'Values absent from it are NOT back-filled from the original.'
                        if role == 'correction' and sub_corr else
                        'Correction payload failed the substantive-payload gate; healthy '
                        'original retained for its own observed fields only.')))

        # ---------- coverage ----------
        cov.append(dict(row_key=key, ticker=cr.ticker, fiscal_year=fy, coverage_status=status,
                        n_files_total=len(files), n_separate_audited=len(sep),
                        n_consolidated=len(con), n_unaudited=len(unaud),
                        n_corrections=len(corrections), n_corrections_substantive=len(sub_corr),
                        selected_role=role,
                        selected_source=chosen['relative_path'] if chosen else '',
                        selected_sha256=chosen['sha256'] if chosen else ''))

        if len(files) > 1:
            for f in files:
                exc.append(dict(row_key=key, relative_path=f['relative_path'],
                                scope=f['scope_inferred'], audited_marker=f['audited_marker'],
                                correction_marker=f['correction_marker'],
                                payload_verdict=f['payload_verdict'],
                                selected=('YES' if chosen and f['relative_path'] == chosen['relative_path'] else 'NO'),
                                exception_type=status, sha256=f['sha256']))

        # ---------- extraction + evidence ----------
        if chosen:
            o = observed(chosen, fy)
            fye, op, rd = o['fiscal_year_end'], o['auditor_opinion_type'], o['auditor_report_date']
            n_ok = sum(1 for v in o.values() if v)
            est = 'EXTRACTED_FULL' if n_ok == 3 else ('EXTRACTED_PARTIAL' if n_ok else 'UNVERIFIED')
            why = []
            if not fye:
                why.append('fiscal_year_end:' + ('FYE_PRESENT_BUT_DOES_NOT_MATCH_FISCAL_YEAR'
                                                 if chosen['fye_content'] else 'NOT_FOUND'))
            if not op:
                why.append('auditor_opinion_type:UNVERIFIED:' + (chosen['opinion_reject_reason'] or 'NO_AUDITOR_BLOCK'))
            if not rd:
                why.append('auditor_report_date:NOT_FOUND:' + (chosen['report_date_reject_reason'] or 'NO_AUDITOR_BLOCK'))

            ext.append(dict(
                row_key=key, ticker=cr.ticker, company_name=chosen['company_name'] or 'NOT_FOUND',
                fiscal_year=fy, fiscal_year_end=fye or 'NOT_FOUND',
                statement_scope=chosen['scope_inferred'], audit_status=chosen['audited_marker'],
                correction_status=chosen['correction_marker'], selected_role=role,
                coverage_status=status,
                auditor_opinion_type=op or 'UNVERIFIED',
                auditor_opinion_evidence_kind=chosen['opinion_evidence_kind'] or 'NONE',
                auditor_opinion_conflict=chosen['opinion_conflict'] or '',
                auditor_report_date=rd or 'NOT_FOUND',
                auditor_block_status=chosen['auditor_block_status'],
                source_relative_path=chosen['relative_path'], source_sha256=chosen['sha256'],
                source_file_type=chosen['actual_file_type'],
                extraction_status=est, missing_reason=';'.join(why),
                scientific_status='OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT'))

            ev.append(dict(
                row_key=key, ticker=cr.ticker, fiscal_year=fy,
                source_relative_path=chosen['relative_path'], source_sha256=chosen['sha256'],
                auditor_block_sheet=chosen['auditor_block_sheet'],
                auditor_block_start=chosen['auditor_block_start'],
                auditor_block_end=chosen['auditor_block_end'],
                auditor_block_title_location=chosen['auditor_block_title_loc'],
                auditor_block_title_text=chosen['auditor_block_title_text'],
                opinion_heading_location=chosen['opinion_heading_location'],
                opinion_heading_text=chosen['opinion_heading_text'],
                opinion_paragraph_location=chosen['opinion_paragraph_location'],
                opinion_paragraph_text=chosen['opinion_paragraph_text'],
                opinion_evidence_kind=chosen['opinion_evidence_kind'],
                opinion_conflict=chosen['opinion_conflict'],
                opinion_reject_reason=chosen['opinion_reject_reason'],
                auditor_report_date_location=chosen['auditor_report_date_location'],
                auditor_report_date_anchor_text=chosen['auditor_report_date_anchor_text'],
                auditor_report_date_context=chosen['auditor_report_date_context'],
                report_date_reject_reason=chosen['report_date_reject_reason'],
                fiscal_year_end_location=chosen['fye_loc'],
                fiscal_year_end_context=chosen['fye_context'],
                fiscal_year_end_all_candidates=chosen['fye_all_candidates']))

            blk_audit.append(dict(
                row_key=key, ticker=cr.ticker, fiscal_year=fy,
                source_relative_path=chosen['relative_path'], source_file_type=chosen['actual_file_type'],
                auditor_block_status=chosen['auditor_block_status'],
                auditor_block_sheet=chosen['auditor_block_sheet'],
                auditor_block_start=chosen['auditor_block_start'],
                auditor_block_end=chosen['auditor_block_end'],
                block_span_rows=((int(chosen['auditor_block_end']) - int(chosen['auditor_block_start']) + 1)
                                 if chosen['auditor_block_status'] == 'DETECTED' else ''),
                title_candidates_in_payload=chosen['auditor_block_title_candidates'],
                sheets_with_title=chosen['auditor_block_sheets_with_title'],
                structural_markers_in_block=chosen['auditor_block_markers'],
                opinion_in_block=('YES' if chosen['opinion_category'] else 'NO'),
                heading_and_paragraph_same_sheet=(
                    'YES' if (chosen['opinion_heading_location'].split('!')[0] ==
                              chosen['opinion_paragraph_location'].split('!')[0])
                    else ('N/A' if not chosen['opinion_category'] else 'NO')),
                date_in_block=('YES' if chosen['auditor_report_date'] else 'NO'),
                reject_reasons=';'.join(x for x in [chosen['opinion_reject_reason'],
                                                    chosen['report_date_reject_reason']] if x)))

            if rd and not op:
                date_review.append(dict(
                    row_key=key, ticker=cr.ticker, fiscal_year=fy,
                    auditor_report_date=rd,
                    auditor_report_date_location=chosen['auditor_report_date_location'],
                    auditor_report_date_anchor_text=chosen['auditor_report_date_anchor_text'],
                    auditor_report_date_context=chosen['auditor_report_date_context'],
                    auditor_block_sheet=chosen['auditor_block_sheet'],
                    auditor_block_start=chosen['auditor_block_start'],
                    auditor_block_end=chosen['auditor_block_end'],
                    date_inside_auditor_block='YES',
                    opinion_status='UNVERIFIED',
                    opinion_reject_reason=chosen['opinion_reject_reason'],
                    reviewer_conclusion=('DATE_BELONGS_TO_AUDITOR_BLOCK_OPINION_TEXT_DEFERRED_TO_ATTACHMENT'
                                         if 'REFERRAL' in chosen['opinion_reject_reason']
                                         else 'DATE_BELONGS_TO_AUDITOR_BLOCK_OPINION_NOT_PROVABLE'),
                    source_relative_path=chosen['relative_path'], source_sha256=chosen['sha256']))

            for fld, val in [('fiscal_year_end', fye), ('auditor_opinion_type', op), ('auditor_report_date', rd)]:
                if not val:
                    miss.append(dict(row_key=key, ticker=cr.ticker, fiscal_year=fy, missing_field=fld,
                                     coverage_status=status, source_file_type=chosen['actual_file_type'],
                                     source_relative_path=chosen['relative_path'],
                                     reason=('AUDITOR_REPORT_ABSENT_FROM_PAYLOAD'
                                             if chosen['auditor_block_status'] == 'NOT_DETECTED' and fld != 'fiscal_year_end'
                                             else (chosen['opinion_reject_reason'] if fld == 'auditor_opinion_type'
                                                   else (chosen['report_date_reject_reason'] if fld == 'auditor_report_date'
                                                         else 'NOT_PRESENT_IN_SOURCE'))) or 'NOT_PRESENT_IN_SOURCE',
                                     required_next_document='CODAL auditor report (گزارش حسابرس مستقل) for this ticker|fiscal_year'))
        else:
            ext.append(dict(row_key=key, ticker=cr.ticker, company_name='NOT_FOUND', fiscal_year=fy,
                            fiscal_year_end='NOT_FOUND', statement_scope='unknown', audit_status='unknown',
                            correction_status='unknown', selected_role='', coverage_status=status,
                            auditor_opinion_type='UNVERIFIED', auditor_opinion_evidence_kind='NONE',
                            auditor_opinion_conflict='', auditor_report_date='NOT_FOUND',
                            auditor_block_status='NO_SOURCE', source_relative_path='', source_sha256='',
                            source_file_type='', extraction_status='NO_VALID_SEPARATE_SOURCE',
                            missing_reason=status,
                            scientific_status='OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT'))
            for fld in FIELDS:
                miss.append(dict(row_key=key, ticker=cr.ticker, fiscal_year=fy, missing_field=fld,
                                 coverage_status=status, source_file_type='', source_relative_path='',
                                 reason=status,
                                 required_next_document='CODAL separate audited financial statements + auditor report'))

    # ------------------------------ write outputs ------------------------------
    INV_F = ['outer_archive', 'nested_archive', 'relative_path', 'filename', 'actual_file_type',
             'extension', 'byte_size', 'sha256', 'parse_status', 'error_status', 'cell_count',
             'payload_verdict', 'payload_verdict_reason', 'ticker_inferred', 'fiscal_year_inferred',
             'fiscal_year_end_from_filename', 'scope_inferred', 'audited_marker', 'correction_marker',
             'auditor_block_status', 'auditor_block_sheet', 'auditor_block_start', 'auditor_block_end',
             'fye_content', 'fye_loc', 'opinion_category', 'opinion_evidence_kind',
             'opinion_heading_location', 'opinion_paragraph_location', 'opinion_conflict',
             'opinion_reject_reason', 'auditor_report_date', 'auditor_report_date_location',
             'report_date_reject_reason', 'company_name']
    wcsv('archive_file_inventory.csv', inv, INV_F)
    wcsv('canonical_1331_coverage.csv', cov)
    wcsv('audit_fields_extracted_v4_3_1.csv', ext)
    wcsv('audit_field_evidence_v4_3_1.csv', ev)
    wcsv('audit_fields_missing_worklist_v4_3_1.csv', miss)
    wcsv('correction_selection_audit_v4_3_1.csv', corr_audit or
         [dict(row_key='', ticker='', fiscal_year='', correction_path='', selection_status='NONE')])
    wcsv('auditor_block_detection_audit_v4_3_1.csv', blk_audit)
    # The review table must also cover every row that V4.3 reported as
    # "date present but opinion unverified" (26 rows), showing how V4.3.1 resolved it.
    if V43 and os.path.exists(V43):
        v43 = {r['row_key']: r for r in csv.DictReader(open(V43, encoding='utf-8-sig'))}
        newmap = {e['row_key']: e for e in ext}
        seen = {d['row_key'] for d in date_review}
        for d in date_review:
            o = v43.get(d['row_key'], {})
            d['v43_opinion'] = o.get('auditor_opinion_normalized', 'N/A')
            d['v43_report_date'] = o.get('auditor_report_date', 'N/A')
            d['review_origin'] = 'V4_3_1_DATE_WITHOUT_VERIFIED_OPINION'
        for k, o in v43.items():
            if o['auditor_report_date'] != 'NOT_FOUND' and o['auditor_opinion_normalized'] == 'NOT_FOUND' \
               and k not in seen:
                n = newmap[k]
                date_review.append(dict(
                    row_key=k, ticker=n['ticker'], fiscal_year=n['fiscal_year'],
                    auditor_report_date=n['auditor_report_date'],
                    auditor_block_sheet=n['auditor_block_status'],
                    date_inside_auditor_block=('YES' if n['auditor_report_date'] != 'NOT_FOUND' else 'N/A'),
                    opinion_status=n['auditor_opinion_type'],
                    opinion_reject_reason=n['missing_reason'],
                    reviewer_conclusion='RESOLVED_IN_V4_3_1_OPINION_NOW_VERIFIED_IN_BLOCK'
                        if n['auditor_opinion_type'] != 'UNVERIFIED' else 'STILL_UNVERIFIED',
                    source_relative_path=n['source_relative_path'], source_sha256=n['source_sha256'],
                    v43_opinion=o['auditor_opinion_normalized'], v43_report_date=o['auditor_report_date'],
                    review_origin='V4_3_DATE_WITHOUT_VERIFIED_OPINION'))
    DR_F = ['row_key','ticker','fiscal_year','auditor_report_date','auditor_report_date_location',
            'auditor_report_date_anchor_text','auditor_report_date_context','auditor_block_sheet',
            'auditor_block_start','auditor_block_end','date_inside_auditor_block','opinion_status',
            'opinion_reject_reason','reviewer_conclusion','v43_opinion','v43_report_date',
            'review_origin','source_relative_path','source_sha256']
    wcsv('date_without_verified_opinion_review_v4_3_1.csv',
         [{k: d.get(k, '') for k in DR_F} for d in date_review] or
         [{k: '' for k in DR_F}], DR_F)
    wcsv('scope_and_correction_exceptions.csv', exc or
         [dict(row_key='', relative_path='', scope='', audited_marker='', correction_marker='',
               payload_verdict='', selected='', exception_type='NONE', sha256='')])
    wcsv('corrupt_and_error_files.csv', corrupt or
         [dict(relative_path='', issue='NONE', byte_size='', sha256='', detail='')])

    json.dump(dict(cov=cov, ext=ext, ev=ev, miss=miss, corr=corr_audit,
                   blk=blk_audit, date_review=date_review, exc=exc),
              open(os.path.join(OUT, '_stage2.json'), 'w'), ensure_ascii=False)

    cs = collections.Counter(c['coverage_status'] for c in cov)
    print('coverage:', dict(cs), 'sum', sum(cs.values()))
    print('opinion :', dict(collections.Counter(e['auditor_opinion_type'] for e in ext)))
    print('extract :', dict(collections.Counter(e['extraction_status'] for e in ext)))
    print('fye rows', sum(1 for e in ext if e['fiscal_year_end'] != 'NOT_FOUND'),
          '| date rows', sum(1 for e in ext if e['auditor_report_date'] != 'NOT_FOUND'),
          '| missing', len(miss), '| corrections audited', len(corr_audit),
          '| date-no-opinion', len(date_review))


if __name__ == '__main__':
    main()
