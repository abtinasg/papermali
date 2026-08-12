"""papermali V4.3.1 — shared parsing / auditor-block library. READ-ONLY on all sources."""
import os,io,re,zipfile,hashlib,unicodedata,warnings
warnings.filterwarnings('ignore')
import pandas as pd

FA='۰۱۲۳۴۵۶۷۸۹'; AR='٠١٢٣٤٥٦٧٨٩'
MONTHS={'فروردین':1,'اردیبهشت':2,'خرداد':3,'تیر':4,'مرداد':5,'شهریور':6,'مهر':7,
        'آبان':8,'ابان':8,'اذر':9,'آذر':9,'دی':10,'بهمن':11,'اسفند':12}

def norm(s):
    s=unicodedata.normalize('NFC',str(s))
    for i,d in enumerate(FA): s=s.replace(d,str(i))
    for i,d in enumerate(AR): s=s.replace(d,str(i))
    s=s.replace('‌',' ').replace('‏','').replace('‎','')
    s=s.replace('\u00ac','').replace('\u00ad','')  # ¬ / soft-hyphen used as ZWNJ
    s=s.replace('ي','ی').replace('ك','ک').replace('ي','ی')
    s=s.replace('“','"').replace('”','"').replace('ـ','')
    return re.sub(r'\s+',' ',s).strip()

def zip_names(zf):
    for i in zf.infolist():
        n=i.filename
        if not (i.flag_bits&0x800):
            try: n=n.encode('cp437').decode('utf-8')
            except Exception: pass
        yield i,n

def ftype(b):
    if b[:8]==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': return 'OLE2_LEGACY_EXCEL'
    if b[:4]==b'PK\x03\x04': return 'OOXML_ZIP'
    l=b[:4096].lstrip().lower()
    if l[:5]==b'<html' or l[:9]==b'<!doctype' or l[:5]==b'<?xml' or b'<table' in l or b'<html' in l:
        return 'HTML_MISLABELED_XLSX'
    return 'UNKNOWN'

# ---------------- grid: (sheet,row,col,text) with REAL geometry for both formats ----
def grid(b,t):
    if t=='OLE2_LEGACY_EXCEL':
        try:
            xl=pd.ExcelFile(io.BytesIO(b)); out=[]
            for sn in xl.sheet_names:
                d=pd.read_excel(xl,sn,header=None)
                for r in range(d.shape[0]):
                    for c in range(d.shape[1]):
                        v=d.iat[r,c]
                        if isinstance(v,str) and v.strip(): out.append((str(sn),r+1,c+1,norm(v)))
            return out,'OK'
        except Exception as e: return [],'EXCEL_PARSE_FAIL:%s'%type(e).__name__
    if t=='HTML_MISLABELED_XLSX':
        try:
            txt=b.decode('utf-8','ignore'); out=[]
            tables=re.findall(r'<table[^>]*>(.*?)</table>',txt,re.S|re.I)
            for ti,tb in enumerate(tables,1):
                sheet='HTML_TABLE_%d'%ti
                for ri,tr in enumerate(re.findall(r'<tr[^>]*>(.*?)</tr>',tb,re.S|re.I),1):
                    for ci,cell in enumerate(re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tr,re.S|re.I),1):
                        v=norm(re.sub(r'<[^>]+>',' ',cell))
                        if v: out.append((sheet,ri,ci,v))
            if not out:
                body=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',txt)
                v=norm(re.sub(r'<[^>]+>',' ',body))
                if v: out=[('HTML_BODY',1,1,v)]
            return out,'OK'
        except Exception as e: return [],'HTML_PARSE_FAIL:%s'%type(e).__name__
    return [],'UNPARSEABLE_TYPE'

# ---------------- Jalali: SYNTAX + hard bounds only (no calendar authority) ---------
def jdate(s):
    s=norm(s)
    m=re.search(r'(?<!\d)(\d{1,2})\s*([\u0621-\u06CC]+)\s*(?:ماه\s*)?(1[34]\d{2})(?!\d)',s)
    if m and m.group(2) in MONTHS:
        return '%s/%02d/%02d'%(m.group(3),MONTHS[m.group(2)],int(m.group(1)))
    m=re.search(r'(?<!\d)(1[34]\d{2})[/\-](\d{1,2})[/\-](\d{1,2})(?!\d)',s)
    if m: return '%s/%02d/%02d'%(m.group(1),int(m.group(2)),int(m.group(3)))
    m=re.search(r'(?<!\d)(\d{1,2})[/\-](\d{1,2})[/\-](1[34]\d{2})(?!\d)',s)
    if m: return '%s/%02d/%02d'%(m.group(3),int(m.group(2)),int(m.group(1)))
    return ''

def syntactic_jalali_bounds_ok(d):
    """Syntax + CERTAIN bounds only. Deliberately NOT a calendar-validity claim:
    month<=6 -> 31 days, months 7..11 -> 30, month 12 -> 30 (29/30 unresolved)."""
    m=re.fullmatch(r'(1[34]\d{2})/(\d{2})/(\d{2})',d or '')
    if not m: return False
    y,mo,dd=int(m.group(1)),int(m.group(2)),int(m.group(3))
    if not 1<=mo<=12: return False
    lim=31 if mo<=6 else 30
    return 1<=dd<=lim

# ================= AUDITOR REPORT BLOCK DETECTION =================
def squash(s): return re.sub(r'\s+','',s or '')

AUD_TITLE_RE   = re.compile(r'گزارش\s*حسابرس(ی)?\s*(مستقل|مست_قل)')
AUD_TITLE_ALT  = re.compile(r'گزارش\s*(حسابرس\s*مستقل\s*و\s*)?بازرس\s*قانونی')
ADDRESSEE_RE   = re.compile(r'به\s*مجمع\s*عمومی\s*صاحبان\s*سهام')

# Short cells that mark structure INSIDE an auditor report (Format A/B/C).
BLOCK_MARKER_RES=[re.compile(p) for p in [
    r'^گزارش\s*نسبت\s*به\s*صورت\s*های\s*مالی$', r'^بند\s*مقدمه$',
    r'^بند\s*مسئولیت', r'^مسئولیت\s*(هیئت|هیات|حسابرس)',
    r'^(مبانی\s*)?اظهار\s*نظر', r'^(مبانی\s*)?عدم\s*اظهار\s*نظر$',
    r'^تاکید\s*بر\s*مط(الب|لب)\s*خاص$', r'^سایر\s*بندهای\s*توضیحی$',
    r'^گزارش\s*در\s*مورد\s*سایر', r'^تاریخ\s*تهیه\s*گزارش:?$',
    r'^موضوع\s*گزارش:?$', r'^مخاطب\s*گزارش:?$', r'^نظر\s*حسابرس\s*:?$',
    r'^شماره\s*بند$', r'^متن\s*کامل$', r'^امضا\s*کننده$', r'^شماره\s*عضویت$',
    r'^(موسسه|مؤسسه|سازمان)\s*حسابرسی', r'^سمت$',
]]
# Short cells that mark the START of the financial-statement grid (block end).
STMT_START_RES=[re.compile(p) for p in [
    r'^ترازنامه$', r'^ترازنامه\s*ها$', r'^صورت\s*وضعیت\s*مالی$',
    r'^صورت\s*سود\s*و\s*زیان$', r'^صورت\s*سود\s*و\s*زیان\s*جامع$',
    r'^صورت\s*جریان\s*(وجوه\s*نقد|های\s*نقدی)$', r'^صورت\s*تغییرات\s*در\s*حقوق\s*مالکانه$',
    r'^گردش\s*حساب\s*سود\s*(و\s*زیان\s*)?انباشته$', r'^درصد\s*تغییر$',
    r'^اطلاعات\s*و\s*صورت', r'^یادداشت\s*های\s*توضیحی$',
]]

def _is(res,v): return any(r.match(v) for r in res)

def detect_auditor_block(cells, max_head_len=60):
    """Locate ONE auditor-report block: (sheet,start_row,end_row,title_loc,title_text,diag).
    Returns (None, diag) when no provable block exists."""
    by_sheet={}
    for s,r,c,v in cells: by_sheet.setdefault(s,[]).append((r,c,v))
    best=None; diag={'title_candidates':0,'sheets_with_title':0}
    for s,items in by_sheet.items():
        titles=[(r,c,v) for r,c,v in items
                if len(v)<=200 and (AUD_TITLE_RE.search(v) or AUD_TITLE_ALT.search(v))]
        if not titles: continue
        diag['sheets_with_title']+=1; diag['title_candidates']+=len(titles)
        start_r,start_c,start_v=min(titles,key=lambda x:(x[0],x[1]))
        # financial-statement grid start strictly after the title
        fin=[r for r,c,v in items if r>start_r and len(v)<=45 and _is(STMT_START_RES,v)]
        # structural auditor markers strictly after the title
        marks=[r for r,c,v in items if r>=start_r and len(v)<=max_head_len and _is(BLOCK_MARKER_RES,v)]
        if not marks: continue
        fin_start=min(fin) if fin else None
        if fin_start is not None:
            inb=[r for r in marks if r<fin_start]
            if not inb: continue
            end_r=fin_start-1
        else:
            end_r=max(r for r,c,v in items)
        if end_r<=start_r: continue
        cand=(s,start_r,end_r,'%s!R%dC%d'%(s,start_r,start_c),start_v,len([r for r in marks if r<=end_r]))
        if best is None or cand[5]>best[5]: best=cand
    if best is None: return None,diag
    s,sr,er,tl,tv,nm=best
    diag['markers_in_block']=nm
    return {'sheet':s,'start':sr,'end':er,'title_loc':tl,'title_text':tv},diag

def block_cells(cells,blk):
    if not blk: return []
    return [(s,r,c,v) for s,r,c,v in cells
            if s==blk['sheet'] and blk['start']<=r<=blk['end']]

# ================= OPINION CLASSIFICATION (block-scoped, anchor-driven) =========
# Tests run on WHITESPACE-SQUASHED text: source spacing is erratic
# ("امکانپذیرنیست", "به نحو  مطلوب") and must never decide a category.
FAIR_SQ    = re.compile(r'ب[ه]?نحو[ه]?(مطلوب|منصفانه)نشانمی')
NOTFAIR_SQ = re.compile(r'ب[ه]?نحو[ه]?(مطلوب|منصفانه)نشاننمی')
EXCEPT_SQ  = re.compile(r'بهاستثنا|باستثنا|بااستثنا|بهاسثنا|بهاسثتنا|بهاستثای|بهاستثنائ|باسثنا|بهجز|بجز|بهغیراز|جزدرمورد|بهاستنثا')
# A DISCLAIMER conclusion is about the financial statements as a whole. The bare
# phrase "امکانپذیرنیست" is NOT enough: it also occurs in basis paragraphs about
# a single balance (e.g. determining a final tax liability).
DISCLAIM_SQ = re.compile(r'(اظهارنظر\w{0,12}(نسبتبه)?صورت(های)?مالی\w{0,40}(امکانپذیرنیست|امکانپذیرنمی|میسرنیست|میسرنگردید|مقدورنیست|مقدورنگردید)'
                         r'|(امکانپذیرنیست|میسرنیست|مقدورنیست)\w{0,0}$'
                         r'|نتوانستهاست\w{0,60}شواهدحسابرسیکافی\w{0,60}اظهارنظر'
                         r'|ازاظهارنظر\w{0,20}خودداری)')
# The standard "other information" paragraph disclaims assurance on the MD&A, not
# on the financial statements. It must never be read as an audit opinion.
OTHERINFO_SQ = re.compile(r'سایراطلاعات')
# A paragraph reporting ANOTHER auditor's report (prior year / other firm).
OTHERREP_SQ = re.compile(r'(مؤسسه|موسسه|سازمان)(حسابرسی)?دیگری|توسط(مؤسسه|موسسه)حسابرسیدیگر')
# A stub deferring the opinion to an attachment instead of stating it.
REFERRAL_SQ = re.compile(r'بهپیوست(ارائهشده|ایفاد|ارسالشده|میباشد|تقدیم|منضم)')

HEAD_PATS=[('عدم اظهارنظر',r'عدم\s*اظهار\s*نظر'),
           ('مردود',      r'اظهار\s*نظر\s*مردود'),
           ('مشروط',      r'اظهار\s*نظر\s*مشروط'),
           ('مقبول',      r'اظهار\s*نظر\s*مقبول'),
           ('_BARE_',     r'اظهار\s*نظر')]
# heading occupying its own cell
HEAD_CELL=[(c,re.compile(r'^(?P<b>مبانی\s*)?'+p+r'$')) for c,p in HEAD_PATS]
# heading written inline at the head of its own numbered paragraph
HEAD_INLINE=[(c,re.compile(r'^\d+\s*[.\-)]?\s*(?P<b>مبانی\s*)?'+p+r'(?![\u0600-\u06FF])')) for c,p in HEAD_PATS]

STRUCT_LABEL=re.compile(r'^نظر\s*حسابرس\s*:?$')
STRUCT_VALS={'مشروط':'مشروط','تعدیل نشده(مقبول)':'مقبول','مقبول':'مقبول',
             'مردود':'مردود','عدم اظهار نظر':'عدم اظهارنظر','عدم اظهارنظر':'عدم اظهارنظر'}

def _head_of(v,pats):
    vv=v.strip(' :.-')
    for cat,rx in pats:
        m=rx.match(vv)
        if m: return cat,bool(m.groupdict().get('b'))
    return None,False

def classify_paragraph(v):
    """Category from this paragraph's OWN decisive conclusion, else ('',reason)."""
    q=squash(v)
    # Order matters. Some payloads concatenate the opinion paragraph and the
    # "سایر اطلاعات" boilerplate into ONE cell, so the boilerplate guard must not
    # run before the decisive formulas or a real opinion is thrown away.
    if REFERRAL_SQ.search(q):   return '','REFERRAL_TO_ATTACHMENT'
    if NOTFAIR_SQ.search(q):    return 'مردود','ADVERSE_FORMULA'
    if FAIR_SQ.search(q):
        # a fair-presentation phrase quoted from ANOTHER firm's report is not ours
        if OTHERREP_SQ.search(q): return '','REFERENCE_TO_OTHER_REPORT'
        if EXCEPT_SQ.search(q): return 'مشروط','QUALIFIED_FAIR_WITH_EXCEPTION'
        return 'مقبول','UNQUALIFIED_FAIR_FORMULA'
    if OTHERINFO_SQ.search(q):  return '','OTHER_INFORMATION_BOILERPLATE_NOT_AN_OPINION'
    if OTHERREP_SQ.search(q):   return '','REFERENCE_TO_OTHER_REPORT'
    if DISCLAIM_SQ.search(q):   return 'عدم اظهارنظر','DISCLAIMER_FORMULA'
    return '',''

def extract_opinion(cells,blk):
    R=dict(opinion_category='',opinion_evidence_kind='',opinion_heading_location='',
           opinion_heading_text='',opinion_paragraph_location='',opinion_paragraph_text='',
           opinion_conflict='',opinion_reject_reason='')
    if not blk:
        R['opinion_reject_reason']='NO_AUDITOR_BLOCK_DETECTED'; return R
    bc=block_cells(cells,blk); SH=blk['sheet']
    idx={(r,c):v for _,r,c,v in bc}

    # ---- Format B: structured "نظر حسابرس" field (NOT free-text inference) ----
    for _,r,c,v in bc:
        if STRUCT_LABEL.match(v):
            for rr in range(r-2,r+3):
                for cc in range(1,8):
                    w=idx.get((rr,cc))
                    if w and w in STRUCT_VALS:
                        R.update(opinion_category=STRUCT_VALS[w],
                                 opinion_evidence_kind='STRUCTURED_FIELD_نظر_حسابرس',
                                 opinion_heading_location='%s!R%dC%d'%(SH,r,c),
                                 opinion_heading_text=v,
                                 opinion_paragraph_location='%s!R%dC%d'%(SH,rr,cc),
                                 opinion_paragraph_text=w)
                        return R

    paras=sorted([(r,c,v) for _,r,c,v in bc if len(v)>=40])
    # ---- anchors: heading cells, and headings written inline in a paragraph ----
    anchors=[]   # (row, col, text, category, is_basis, kind)
    for _,r,c,v in bc:
        if len(v)<=45:
            cat,isb=_head_of(v,HEAD_CELL)
            if cat: anchors.append((r,c,v,cat,isb,'HEADING_CELL'))
    for r,c,v in paras:
        cat,isb=_head_of(v,HEAD_INLINE)
        if cat: anchors.append((r,c,v[:120],cat,isb,'INLINE_HEADING'))
    # basis ("مبانی …") paragraphs state the REASONS, never the opinion itself
    basis_rows={r for r,c,v,cat,isb,k in anchors if isb and k=='INLINE_HEADING'}

    def para_after(row,col,kind):
        if kind=='INLINE_HEADING':
            return next(((r,c,v) for r,c,v in paras if r==row and c==col),None)
        for r,c,v in paras:
            if r>=row and r-row<=8 and r not in basis_rows: return (r,c,v)
        return None

    # ---- prefer a NON-basis anchor whose paragraph carries a decisive conclusion ----
    tried=[]
    for row,col,htxt,hcat,isb,kind in sorted(anchors,key=lambda a:(a[4],a[0])):
        if isb: continue
        p=para_after(row,col,kind)
        if not p: continue
        pcat,pkind=classify_paragraph(p[2])
        tried.append(pkind or 'NO_FORMULA')
        if not pcat: continue
        R.update(opinion_category=pcat,opinion_evidence_kind=pkind+'|'+kind,
                 opinion_heading_location='%s!R%dC%d'%(SH,row,col),opinion_heading_text=htxt,
                 opinion_paragraph_location='%s!R%dC%d'%(SH,p[0],p[1]),
                 opinion_paragraph_text=p[2])
        if hcat not in ('_BARE_',) and hcat!=pcat:
            R['opinion_conflict']='HEADING_%s_VS_PARAGRAPH_%s'%(hcat,pcat)
        mod={a[3] for a in anchors if a[3] in ('مشروط','مردود','عدم اظهارنظر')}
        if pcat=='مقبول' and mod:
            R['opinion_conflict']=(R['opinion_conflict'] or
                'MODIFIED_HEADING_%s_PRESENT_WITH_UNQUALIFIED_PARAGRAPH'%'/'.join(sorted(mod)))
            R['opinion_category']=''
            R['opinion_reject_reason']='UNQUALIFIED_BLOCKED_BY_MODIFIED_OPINION_HEADING_IN_SAME_REPORT'
        return R

    # ---- fallback: no usable heading anchor; require a decisive, non-basis paragraph ----
    cands=[]
    for r,c,v in paras:
        if r in basis_rows: continue
        cat,kind=classify_paragraph(v)
        if cat: cands.append((r,c,v,cat,kind))
    if cands:
        r,c,v,cat,kind=cands[0]
        R.update(opinion_category=cat,opinion_evidence_kind=kind+'|NO_HEADING_ANCHOR',
                 opinion_heading_location='ABSENT_IN_BLOCK',
                 opinion_paragraph_location='%s!R%dC%d'%(SH,r,c),opinion_paragraph_text=v)
        return R
    if anchors:
        row,col,htxt,hcat,isb,kind=sorted(anchors)[0]
        R.update(opinion_heading_location='%s!R%dC%d'%(SH,row,col),opinion_heading_text=htxt)
    R['opinion_reject_reason']=('NO_DECISIVE_OPINION_PARAGRAPH_IN_BLOCK'
                                +(';'+';'.join(sorted(set(t for t in tried if t))) if tried else ''))
    return R

# ================= AUDITOR REPORT DATE (block-scoped) =================
DATE_ANCHOR=re.compile(r'^تاریخ\s*تهیه\s*گزارش\s*:?$')
SIGN_RE=re.compile(r'(موسسه|مؤسسه|سازمان)\s*حسابرسی|امضا\s*کننده|شماره\s*عضویت|^سمت$')

def extract_report_date(cells,blk):
    R=dict(auditor_report_date='',auditor_report_date_location='',
           auditor_report_date_anchor_text='',auditor_report_date_context='',
           report_date_reject_reason='')
    if not blk:
        R['report_date_reject_reason']='NO_AUDITOR_BLOCK_DETECTED'; return R
    bc=block_cells(cells,blk)
    idx={(r,c):v for _,r,c,v in bc}
    anchors=[(r,c,v) for _,r,c,v in bc if DATE_ANCHOR.match(v.strip())]
    if not anchors:
        R['report_date_reject_reason']='NO_DATE_ANCHOR_IN_AUDITOR_BLOCK'; return R
    for r,c,v in sorted(anchors):
        # signature / audit-firm evidence tying the anchor to THIS report's closing
        sig=[(rr,cc,w) for (rr,cc),w in idx.items() if abs(rr-r)<=12 and SIGN_RE.search(w)]
        for cc in list(range(c-1,max(0,c-5),-1))+list(range(c+1,c+5)):
            cand=idx.get((r,cc))
            if not cand: continue
            d=jdate(cand)
            if d and syntactic_jalali_bounds_ok(d):
                ctx=[w for (rr,ccc),w in sorted(idx.items()) if abs(rr-r)<=2]
                R.update(auditor_report_date=d,
                         auditor_report_date_location='%s!R%dC%d'%(blk['sheet'],r,cc),
                         auditor_report_date_anchor_text='%s @ %s!R%dC%d'%(v,blk['sheet'],r,c),
                         auditor_report_date_context=' ~ '.join(ctx)[:600]
                            +(' || SIGNATURE:'+sig[0][2][:80] if sig else ' || SIGNATURE:NONE'))
                if not sig: R['report_date_reject_reason']='ACCEPTED_NO_SIGNATURE_MARKER_NEARBY'
                return R
    R['report_date_reject_reason']='DATE_ANCHOR_IN_BLOCK_BUT_NO_PARSEABLE_DATE_ADJACENT'
    return R

# ================= FISCAL YEAR END =================
FYE_RES=[re.compile(r'منتهی\s*به\s*:?\s*(1[34]\d{2})[/\-](\d{1,2})[/\-](\d{1,2})'),
         re.compile(r'منتهی\s*به\s*:?\s*(\d{1,2})[/\-](\d{1,2})[/\-](1[34]\d{2})'),
         re.compile(r'منتهی\s*به\s*:?\s*(\d{1,2})\s*([\u0621-\u06CC]+)\s*(?:ماه\s*)?(1[34]\d{2})')]
def extract_fye(cells):
    out=[]
    for s,r,c,v in cells:
        for m in FYE_RES[0].finditer(v): out.append(('%s/%02d/%02d'%(m.group(1),int(m.group(2)),int(m.group(3))),s,r,c,v))
        for m in FYE_RES[1].finditer(v): out.append(('%s/%02d/%02d'%(m.group(3),int(m.group(2)),int(m.group(1))),s,r,c,v))
        for m in FYE_RES[2].finditer(v):
            if m.group(2) in MONTHS: out.append(('%s/%02d/%02d'%(m.group(3),MONTHS[m.group(2)],int(m.group(1))),s,r,c,v))
    # explicit label "سال مالی منتهی به:" with the value in a neighbouring cell
    idx={(s,r,c):v for s,r,c,v in cells}
    for s,r,c,v in cells:
        if re.match(r'^سال\s*مالی\s*منتهی\s*به\s*:?$',v.strip()):
            for cc in list(range(c-1,max(0,c-8),-1))+list(range(c+1,c+8)):
                w=idx.get((s,r,cc))
                if w:
                    d=jdate(w)
                    if d: out.append((d,s,r,cc,'%s | anchor:%s'%(w,v))); break
    return out

COMPANY_RE=re.compile(r'شرکت\s+(.{2,60}?)\s*\(\s*سهامی')
def extract_company(cells):
    for s,r,c,v in cells:
        m=COMPANY_RE.search(v)
        if m: return m.group(1).strip(),'%s!R%dC%d'%(s,r,c)
    return '',''
