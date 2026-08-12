#!/usr/bin/env python3
"""V4.3.1 Stage 6 — assemble, manifest, hash, verify, zip.

Mandated order:
  1 outputs written -> 2 QA + tests run -> 3 session manifest -> 4 SHA256SUMS
  -> 5 re-verify every hash -> 6 build ZIP -> 7 report ZIP SHA-256
SHA256SUMS.txt is generated only after the last file is final.
"""
import os, sys, csv, json, glob, shutil, hashlib, zipfile, datetime, subprocess, collections

OUT   = os.environ['OUTDIR']
PKG   = os.environ['PKGDIR']
DEST  = os.environ['DEST']
ARCHIVE = os.environ['ARCHIVE']
CANON   = os.environ['CANON']

DELIVER = [
    'README_FA.md', 'archive_identity.json', 'canonical_source_identity.json',
    'archive_file_inventory.csv', 'canonical_1331_coverage.csv',
    'audit_fields_extracted_v4_3_1.csv', 'audit_field_evidence_v4_3_1.csv',
    'audit_fields_missing_worklist_v4_3_1.csv', 'correction_selection_audit_v4_3_1.csv',
    'auditor_block_detection_audit_v4_3_1.csv', 'date_without_verified_opinion_review_v4_3_1.csv',
    'scope_and_correction_exceptions.csv', 'corrupt_and_error_files.csv',
    'qa_report_v4_3_1.json',
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def main():
    if os.path.isdir(PKG): shutil.rmtree(PKG)
    os.makedirs(PKG)

    # ---- 1. assemble ----
    for n in DELIVER:
        shutil.copy2(os.path.join(OUT, n), os.path.join(PKG, n))
    shutil.copytree(os.path.join(OUT, 'pilot_evidence'), os.path.join(PKG, 'pilot_evidence'))
    shutil.copytree(os.path.join(os.path.dirname(OUT), 'scripts'), os.path.join(PKG, 'scripts'),
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(os.path.join(os.path.dirname(OUT), 'tests'), os.path.join(PKG, 'tests'),
                    ignore=shutil.ignore_patterns('__pycache__'))

    qa = json.load(open(os.path.join(PKG, 'qa_report_v4_3_1.json')))
    tests_log = os.environ.get('TESTS_LOG', '')
    tests_passed = 'ALL TESTS PASSED' in open(tests_log).read() if tests_log and os.path.exists(tests_log) else None

    # ---- 3. session manifest (after outputs + QA, before hashing) ----
    inv = json.load(open(os.path.join(OUT, '_inv.json')))
    ext = list(csv.DictReader(open(os.path.join(PKG, 'audit_fields_extracted_v4_3_1.csv'),
                                   encoding='utf-8-sig')))
    manifest = dict(
        version='V4.3.1',
        mission='Local financial-statement archive audit & auditor-field extraction (correction run)',
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        supersedes=dict(
            version='V4.3',
            zip_name='papermali_m4_local_archive_audit_extraction_20260812T131104Z.zip',
            zip_sha256='a675cd984e30126070526f8f212ed676628013de651366c1a04b67a861dbb7af',
            zip_sha256_reverified_this_session=True),
        inputs=dict(
            archive_path=ARCHIVE, archive_sha256=sha256(ARCHIVE),
            canonical_path=CANON, canonical_sha256=sha256(CANON),
            access_note='Full Disk Access was granted before this run; the ORIGINAL archive in '
                        '~/Downloads was used as the authoritative source. Both inputs were '
                        'opened read-only and in memory.'),
        execution_order=[
            '1. s1_scan_extract.py  — scan 1628 payloads, detect auditor block, extract fields',
            '2. s2_match_outputs.py — correction gate, canonical matching, all CSV outputs',
            '3. s3_qa.py            — %d semantic QA checks' % len(qa['checks']),
            '4. tests/test_extraction_semantics.py — independent negative-control tests',
            '5. s5_docs.py          — identity files + README generated from the artefacts',
            '6. s6_package.py       — manifest, SHA256SUMS, verify, zip'],
        rule_changes_vs_v4_3=[
            'Correction selection now requires a proven-substantive payload; an invalid or '
            'non-substantive correction never displaces a healthy original.',
            'Opinion, heading and report date must all lie inside ONE detected auditor-report '
            'block on ONE sheet, whose start/end rows are recorded.',
            'The opinion PARAGRAPH decides the category; the heading only corroborates. '
            '"مبانی X" basis labels are never treated as the opinion.',
            'مقبول requires the complete fair-presentation formula, no exception clause, and no '
            'modified-opinion heading in the same report; contradictions yield UNVERIFIED.',
            'Report date must sit inside the block, anchored to تاریخ تهیه گزارش, with context '
            'and signature evidence recorded.',
            'Jalali check renamed to all_dates_pass_syntactic_jalali_bounds; no calendar-validity '
            'claim, no audit_lag_days.',
            'Structured field نظر حسابرس is recorded separately from free-text inference.'],
        counts=dict(
            nested_zip=json.load(open(os.path.join(PKG, 'archive_identity.json')))['nested_zip_count'],
            payloads=len(inv),
            payload_types=dict(collections.Counter(r['actual_file_type'] for r in inv)),
            canonical_rows=len(ext),
            rows_with_fiscal_year_end=qa['rows_with_fiscal_year_end'],
            rows_with_verified_opinion=qa['rows_with_verified_opinion'],
            rows_with_verified_report_date=qa['rows_with_verified_report_date'],
            opinion_distribution=qa['opinion_distribution'],
            field_level_missing=qa['field_level_missing']),
        qa_passed=qa['qa_passed'], qa_checks_total=len(qa['checks']),
        qa_checks_failed=qa['checks_failed'],
        independent_tests_passed=tests_passed,
        decision='V4_3_1_CORRECTION_PASS_OBSERVATIONAL_EXTRACTION_READY_FOR_SUPERVISORY_AUDIT'
                 if (qa['qa_passed'] and tests_passed) else 'V4_3_1_QA_FAILED',
        scientific_status='OBSERVATIONAL_TEXT_EXTRACTION_NOT_YET_ADMITTED_AS_LOCKED_M4_INPUT',
        prohibitions_observed=dict(
            git_commit_push_branch_pr_merge=False, github_modified=False,
            canonical_overwritten=False, source_archive_modified=False,
            source_archive_copied_into_package=False,
            m4_data_gate_executed_or_opened=False, modeling_executed=False,
            final_test_accessed=False, audit_lag_days_computed=False,
            going_concern_derived_from_text=False, missing_data_imputed=False,
            taxonomy_invented_or_inferred_from_frequency=False))
    json.dump(manifest, open(os.path.join(PKG, 'session_manifest.json'), 'w'),
              ensure_ascii=False, indent=2)

    # ---- 4. SHA256SUMS, generated last ----
    files = sorted(os.path.relpath(p, PKG)
                   for p in glob.glob(os.path.join(PKG, '**', '*'), recursive=True)
                   if os.path.isfile(p) and os.path.basename(p) != 'SHA256SUMS.txt')
    with open(os.path.join(PKG, 'SHA256SUMS.txt'), 'w', encoding='utf-8') as f:
        for rel in files:
            f.write('%s  %s\n' % (sha256(os.path.join(PKG, rel)), rel))

    # ---- 5. verify every recorded hash ----
    bad = []
    for line in open(os.path.join(PKG, 'SHA256SUMS.txt'), encoding='utf-8'):
        h, rel = line.rstrip('\n').split('  ', 1)
        if sha256(os.path.join(PKG, rel)) != h: bad.append(rel)
    if bad:
        print('HASH VERIFY FAILED:', bad); sys.exit(1)
    print('hash verify: %d files, all match' % len(files))

    # ---- 6. zip ----
    if os.path.exists(DEST): os.remove(DEST)
    with zipfile.ZipFile(DEST, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in files + ['SHA256SUMS.txt']:
            z.write(os.path.join(PKG, rel), rel)
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None, 'ZIP INTEGRITY FAILURE'
        n_in_zip = len(z.namelist())

    print('zip entries : %d' % n_in_zip)
    print('zip path    : %s' % DEST)
    print('zip bytes   : %d' % os.path.getsize(DEST))
    print('ZIP_SHA256  : %s' % sha256(DEST))
    print('decision    : %s' % manifest['decision'])


if __name__ == '__main__':
    main()
