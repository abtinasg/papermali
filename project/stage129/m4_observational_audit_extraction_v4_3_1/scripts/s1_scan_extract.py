#!/usr/bin/env python3
"""V4.3.1 Stage 1 — scan the source archive and extract audit fields per payload.

READ-ONLY: the outer archive is opened once, in memory; nothing is written to,
renamed in, or extracted into the source tree.

Every extracted value is block-scoped (see lib_extract.detect_auditor_block).
No value is inferred from a workbook-wide substring search.
"""
import os, io, re, sys, json, zipfile, hashlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_extract as L

ARCHIVE = os.environ['ARCHIVE']
OUT     = os.environ['OUTDIR']
os.makedirs(OUT, exist_ok=True)

FNAME = re.compile(r'^(?P<t>[^_]+)_(?P<y>\d{4})_(?P<m>\d{2})_(?P<d>\d{2})_'
                   r'(?P<scope>separate|consolidated)_')

# A payload is SUBSTANTIVE only if it is a real, parseable document carrying
# recognisable financial-report content. Size alone is never sufficient.
MIN_CELLS_SUBSTANTIVE = 20
MIN_BYTES_SUBSTANTIVE = 4096


def payload_verdict(rec, cells, blk):
    """Classify the payload itself, independent of which fields we managed to read."""
    if rec['parse_status'] != 'OK':
        return 'PAYLOAD_INVALID', 'PARSE_FAILED:' + (rec['error_status'] or '?')
    if not cells:
        return 'PAYLOAD_INVALID', 'ZERO_CONTENT_CELLS'
    if rec['byte_size'] < MIN_BYTES_SUBSTANTIVE:
        return 'PAYLOAD_NON_SUBSTANTIVE', 'SUSPICIOUS_SMALL_PAYLOAD:%d_bytes' % rec['byte_size']
    if len(cells) < MIN_CELLS_SUBSTANTIVE:
        return 'PAYLOAD_NON_SUBSTANTIVE', 'ONLY_%d_CELLS' % len(cells)
    has_stmt = any(len(v) <= 45 and L._is(L.STMT_START_RES, v) for _, _, _, v in cells)
    if not (blk or has_stmt or rec['fye_content']):
        return 'PAYLOAD_NON_SUBSTANTIVE', 'NO_AUDITOR_BLOCK_NO_STATEMENT_GRID_NO_FISCAL_YEAR_END'
    return 'PAYLOAD_SUBSTANTIVE', ''


def main():
    outer = zipfile.ZipFile(ARCHIVE)
    inv, corrupt = [], []
    n_nested = 0
    for oi, on in L.zip_names(outer):
        if oi.is_dir():
            continue
        if on.startswith('__MACOSX/') or os.path.basename(on).startswith('._'):
            continue
        data = outer.read(oi)
        if not on.lower().endswith('.zip'):
            corrupt.append(dict(relative_path=on, issue='TOP_LEVEL_NON_ZIP',
                                byte_size=len(data),
                                sha256=hashlib.sha256(data).hexdigest(), detail=''))
            continue
        try:
            inner = zipfile.ZipFile(io.BytesIO(data))
        except Exception as e:
            corrupt.append(dict(relative_path=on, issue='NESTED_ZIP_OPEN_ERROR',
                                byte_size=len(data),
                                sha256=hashlib.sha256(data).hexdigest(), detail=str(e)[:200]))
            continue
        n_nested += 1
        for ii, inn in L.zip_names(inner):
            if ii.is_dir() or '__MACOSX' in inn or os.path.basename(inn).startswith('._'):
                continue
            try:
                b = inner.read(ii); err = ''
            except Exception as e:
                b = b''; err = 'READ_ERROR:%s' % type(e).__name__
            t = L.ftype(b) if b else 'UNREADABLE'
            cells, pst = L.grid(b, t) if b else ([], 'UNREADABLE')
            base = L.norm(os.path.basename(inn))
            m = FNAME.match(base)

            rec = dict(
                outer_archive=os.path.basename(ARCHIVE), nested_archive=on,
                relative_path='%s!%s' % (on, inn), filename=os.path.basename(inn),
                actual_file_type=t, extension=os.path.splitext(inn)[1].lower(),
                byte_size=len(b), sha256=hashlib.sha256(b).hexdigest() if b else '',
                parse_status='OK' if pst == 'OK' else 'FAIL',
                error_status=err or (pst if pst != 'OK' else ''),
                cell_count=len(cells),
                ticker_inferred=L.norm(m.group('t')) if m else '',
                fiscal_year_inferred=m.group('y') if m else '',
                fiscal_year_end_from_filename=('%s/%s/%s' % (m.group('y'), m.group('m'), m.group('d'))) if m else '',
                scope_inferred=m.group('scope') if m else 'unknown',
                audited_marker=('unaudited' if 'حسابرسی نشده' in base
                                else ('audited' if 'حسابرسی شده' in base else 'unknown')),
                correction_marker=('correction' if ('اصلاحیه' in base or 'اصلاح شده' in base)
                                   else 'original'))

            # ---- auditor report block (single, provable, one sheet) ----
            blk, bdiag = L.detect_auditor_block(cells)
            rec.update(
                auditor_block_sheet=blk['sheet'] if blk else '',
                auditor_block_start=blk['start'] if blk else '',
                auditor_block_end=blk['end'] if blk else '',
                auditor_block_title_loc=blk['title_loc'] if blk else '',
                auditor_block_title_text=blk['title_text'][:300] if blk else '',
                auditor_block_status='DETECTED' if blk else 'NOT_DETECTED',
                auditor_block_title_candidates=bdiag.get('title_candidates', 0),
                auditor_block_sheets_with_title=bdiag.get('sheets_with_title', 0),
                auditor_block_markers=bdiag.get('markers_in_block', 0))

            # ---- fiscal year end ----
            fye_all = L.extract_fye(cells)
            fye_fn = rec['fiscal_year_end_from_filename']
            pick = next((x for x in fye_all if x[0] == fye_fn), None) or (fye_all[0] if fye_all else None)
            rec.update(
                fye_content=pick[0] if pick else '',
                fye_loc=('%s!R%dC%d' % (pick[1], pick[2], pick[3])) if pick else '',
                fye_context=pick[4][:600] if pick else '',
                fye_all_candidates='|'.join(sorted({x[0] for x in fye_all})),
                fye_agrees_with_filename=('YES' if pick and pick[0] == fye_fn
                                          else ('NO' if pick else 'NO_CONTENT_DATE')))

            # ---- opinion + report date, both block-scoped ----
            rec.update(L.extract_opinion(cells, blk))
            rec.update(L.extract_report_date(cells, blk))
            cn, cl = L.extract_company(cells)
            rec.update(company_name=cn, company_loc=cl)

            v, vr = payload_verdict(rec, cells, blk)
            rec.update(payload_verdict=v, payload_verdict_reason=vr)

            if v != 'PAYLOAD_SUBSTANTIVE':
                corrupt.append(dict(relative_path=rec['relative_path'],
                                    issue=v, byte_size=rec['byte_size'],
                                    sha256=rec['sha256'],
                                    detail='%s | %s' % (vr, rec['actual_file_type'])))
            inv.append(rec)

    json.dump(inv, open(os.path.join(OUT, '_inv.json'), 'w'), ensure_ascii=False)
    json.dump(corrupt, open(os.path.join(OUT, '_corrupt.json'), 'w'), ensure_ascii=False)

    print('nested_zip_count      %d' % n_nested)
    print('payload_count         %d' % len(inv))
    print('type                  %s' % dict(collections.Counter(r['actual_file_type'] for r in inv)))
    print('parse                 %s' % dict(collections.Counter(r['parse_status'] for r in inv)))
    print('payload_verdict       %s' % dict(collections.Counter(r['payload_verdict'] for r in inv)))
    print('auditor_block         %s' % dict(collections.Counter(r['auditor_block_status'] for r in inv)))
    print('opinion_evidence_kind %s' % dict(collections.Counter(
        r['opinion_evidence_kind'] for r in inv if r['opinion_category'])))
    print('opinion_category      %s' % dict(collections.Counter(
        r['opinion_category'] for r in inv if r['opinion_category'])))
    print('opinion_conflicts     %d' % sum(1 for r in inv if r['opinion_conflict']))
    print('report_date           %d' % sum(1 for r in inv if r['auditor_report_date']))
    print('fye                   %d' % sum(1 for r in inv if r['fye_content']))


if __name__ == '__main__':
    main()
