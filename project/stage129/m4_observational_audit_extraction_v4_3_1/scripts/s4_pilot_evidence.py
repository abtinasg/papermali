#!/usr/bin/env python3
"""V4.3.1 Stage 4 — pilot evidence dumps.

For each pilot case the FULL auditor-report block is written verbatim, so a
reviewer can see the decisive sentence in its own context. Nothing is truncated
before the phrase that determines the opinion. The source archive is not copied.
"""
import os, io, re, csv, sys, json, zipfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_extract as L

ARCHIVE = os.environ['ARCHIVE']
OUT     = os.environ['OUTDIR']
EVDIR   = os.path.join(OUT, 'pilot_evidence')
os.makedirs(EVDIR, exist_ok=True)

inv = json.load(open(os.path.join(OUT, '_inv.json')))
ext = {e['row_key']: e for e in csv.DictReader(
    open(os.path.join(OUT, 'audit_fields_extracted_v4_3_1.csv'), encoding='utf-8-sig'))}
evd = {e['row_key']: e for e in csv.DictReader(
    open(os.path.join(OUT, 'audit_field_evidence_v4_3_1.csv'), encoding='utf-8-sig'))}
byp = {r['relative_path']: r for r in inv}


def pick(wanted):
    """Choose pilot rows: (label, [row_keys or relative_paths])"""
    sel = []
    unq = [k for k, e in ext.items() if e['auditor_opinion_type'] == 'مقبول']
    qual = [k for k, e in ext.items() if e['auditor_opinion_type'] == 'مشروط']
    disc = [k for k, e in ext.items() if e['auditor_opinion_type'] == 'عدم اظهارنظر']
    advs = [k for k, e in ext.items() if e['auditor_opinion_type'] == 'مردود']
    sel += [('unqualified', k) for k in sorted(unq)[:4]]
    sel += [('qualified', k) for k in sorted(qual)[:4]]
    sel += [('disclaimer_in_canonical', k) for k in sorted(disc)]        # all
    sel += [('adverse_in_canonical', k) for k in sorted(advs)]           # all
    sel += [('named_case', k) for k in ['فنورد|1400', 'سخوز|1392', 'خوساز|1396', 'سقاین|1393', 'سآبیک|1392']]
    # remaining date-without-verified-opinion rows
    for d in csv.DictReader(open(os.path.join(OUT, 'date_without_verified_opinion_review_v4_3_1.csv'),
                                 encoding='utf-8-sig')):
        if d['review_origin'] == 'V4_3_1_DATE_WITHOUT_VERIFIED_OPINION':
            sel += [('date_without_verified_opinion', d['row_key'])]
    # HTML payloads with no auditor report at all
    html = [k for k, e in ext.items() if e['source_file_type'] == 'HTML_MISLABELED_XLSX'][:3]
    sel += [('html_no_auditor_report', k) for k in sorted(html)]
    return sel


def dump_block(fh, cells, blk, rec):
    fh.write('SOURCE            : %s\n' % rec['relative_path'])
    fh.write('SOURCE_SHA256     : %s\n' % rec['sha256'])
    fh.write('PAYLOAD_TYPE      : %s   BYTES: %d   CELLS: %d\n'
             % (rec['actual_file_type'], rec['byte_size'], rec['cell_count']))
    fh.write('PAYLOAD_VERDICT   : %s %s\n' % (rec['payload_verdict'], rec['payload_verdict_reason']))
    if blk:
        fh.write('AUDITOR_BLOCK     : sheet=%s rows %d..%d  (title @ %s)\n'
                 % (blk['sheet'], blk['start'], blk['end'], blk['title_loc']))
    else:
        fh.write('AUDITOR_BLOCK     : NOT_DETECTED (no auditor report in this payload)\n')
    fh.write('OPINION           : %s   kind=%s\n'
             % (rec['opinion_category'] or 'UNVERIFIED', rec['opinion_evidence_kind'] or '-'))
    if rec['opinion_reject_reason']:
        fh.write('OPINION_REJECT    : %s\n' % rec['opinion_reject_reason'])
    if rec['opinion_conflict']:
        fh.write('OPINION_CONFLICT  : %s\n' % rec['opinion_conflict'])
    fh.write('OPINION_HEADING   : %s  %r\n' % (rec['opinion_heading_location'], rec['opinion_heading_text']))
    fh.write('OPINION_PARAGRAPH : %s\n' % rec['opinion_paragraph_location'])
    fh.write('REPORT_DATE       : %s @ %s\n' % (rec['auditor_report_date'] or 'NOT_FOUND',
                                                rec['auditor_report_date_location'] or '-'))
    if rec['report_date_reject_reason']:
        fh.write('REPORT_DATE_NOTE  : %s\n' % rec['report_date_reject_reason'])
    fh.write('FISCAL_YEAR_END   : %s @ %s\n' % (rec['fye_content'] or 'NOT_FOUND', rec['fye_loc'] or '-'))
    fh.write('\n--- FULL OPINION PARAGRAPH (verbatim, untruncated) ---\n')
    fh.write((rec['opinion_paragraph_text'] or '(none)') + '\n')
    fh.write('\n--- AUDITOR REPORT BLOCK, VERBATIM ---\n')
    if blk:
        for s, r, c, v in L.block_cells(cells, blk):
            fh.write('%s!R%dC%d | %s\n' % (s, r, c, v))
    else:
        fh.write('(no auditor block; first 25 content cells of the payload follow)\n')
        for s, r, c, v in cells[:25]:
            fh.write('%s!R%dC%d | %s\n' % (s, r, c, v[:200]))


def main():
    sel = pick(None)
    # also include validated / rejected correction pairs
    corr = list(csv.DictReader(open(os.path.join(OUT, 'correction_selection_audit_v4_3_1.csv'),
                                    encoding='utf-8-sig')))
    valid_c = [c for c in corr if c['selected'] == 'YES' and c['correction_payload_verdict'] == 'PAYLOAD_SUBSTANTIVE'][:2]
    bad_c   = [c for c in corr if c['correction_payload_verdict'] != 'PAYLOAD_SUBSTANTIVE']

    paths = {}
    def add(rp, label, key):
        if rp: paths.setdefault(rp, (label, key))   # first label wins

    # Named regression cases first, and for each one EVERY payload of that
    # ticker|fiscal_year, so both versions of a correction pair are shown.
    NAMED = ['فنورد|1400', 'سخوز|1392', 'خوساز|1396', 'سقاین|1393', 'سآبیک|1392']
    for key in NAMED:
        tk, fy = key.rsplit('|', 1)
        tkn = L.norm(tk)
        for r in inv:
            if r['ticker_inferred'] == tkn and r['fiscal_year_inferred'] == fy:
                add(r['relative_path'], 'named_case_%s' % r['correction_marker'], key)
    for label, key in sel:
        e = ext.get(key)
        if e: add(e['source_relative_path'], label, key)
    for c in valid_c:
        add(c['correction_path'], 'correction_valid', c['row_key'])
    for c in bad_c:
        add(c['correction_path'], 'correction_invalid', c['row_key'])
        add(c['original_path'], 'correction_invalid_original_retained', c['row_key'])
    # the only disclaimer found anywhere in the archive (outside the canonical window)
    for r in inv:
        if r['opinion_category'] == 'عدم اظهارنظر':
            paths[r['relative_path']] = ('disclaimer_in_archive_outside_canonical',
                                         '%s|%s' % (r['ticker_inferred'], r['fiscal_year_inferred']))

    o = zipfile.ZipFile(ARCHIVE); n = 0; index = []
    for oi, on in L.zip_names(o):
        if oi.is_dir() or not on.lower().endswith('.zip'): continue
        try: z = zipfile.ZipFile(io.BytesIO(o.read(oi)))
        except Exception: continue
        for ii, inn in L.zip_names(z):
            rp = '%s!%s' % (on, inn)
            if rp not in paths: continue
            label, key = paths[rp]
            rec = byp[rp]
            b = z.read(ii)
            cells, _ = L.grid(b, rec['actual_file_type'])
            blk, _ = L.detect_auditor_block(cells)
            n += 1
            safe = re.sub(r'[^\w؀-ۿ|]+', '_', key).strip('_')
            fn = '%02d_%s_%s.txt' % (n, label, safe)
            with open(os.path.join(EVDIR, fn), 'w', encoding='utf-8') as fh:
                fh.write('PILOT EVIDENCE — papermali V4.3.1\n')
                fh.write('CASE              : %s\nROW_KEY           : %s\n' % (label, key))
                fh.write('=' * 78 + '\n')
                dump_block(fh, cells, blk, rec)
            index.append(dict(file=fn, case=label, row_key=key, source_relative_path=rp,
                              source_sha256=rec['sha256'],
                              opinion=rec['opinion_category'] or 'UNVERIFIED',
                              report_date=rec['auditor_report_date'] or 'NOT_FOUND',
                              fiscal_year_end=rec['fye_content'] or 'NOT_FOUND'))

    with open(os.path.join(EVDIR, 'INDEX.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(index[0].keys())); w.writeheader(); w.writerows(index)
    print('pilot evidence files:', n)
    print(collections.Counter(i['case'] for i in index))


if __name__ == '__main__':
    main()
