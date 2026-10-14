"""Combine Japanese OCR with recoverable native BIZ Gothic text lines."""
from collections import defaultdict, Counter
import csv
import hashlib
import json
from pathlib import Path
import re

import pymupdf
from fontTools.ttLib import TTFont

from .repair_dri import OUTPUT, SOURCE, ROOT, normalize_japanese


def restore_page(page, number, reference):
    native=[]
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines',[]):
            spans=line['spans']
            if not spans or not all(s['font'].startswith('BIZ') and ('Gothic' in s['font'] or 'S' in s['font']) for s in spans):
                continue
            chars=[c for s in spans for c in s['chars']]
            if not chars or any(not c.get('synthetic') and ord(c['c']) not in reference for c in chars):continue
            value=''.join(c['c'] if c.get('synthetic') else reference[ord(c['c'])] for c in chars).strip()
            rect=pymupdf.Rect(chars[0]['bbox'])
            for span in spans:
                for char in span['chars']:
                    box=pymupdf.Rect(char['bbox'])
                    if box.width<0.1:
                        box.x1=box.x0+span['size']
                    rect |= box
            if value:native.append((rect,value))
    # Native extraction splits some headings into several runs. Merge runs at the
    # same baseline before replacing OCR words that straddle a run boundary.
    merged=[]
    for rect,value in sorted(native,key=lambda item:(round(item[0].y0),item[0].x0)):
        if merged and abs(merged[-1][0].y0-rect.y0)<2 and rect.x0-merged[-1][0].x1<20:
            old_rect,old_value=merged.pop()
            merged.append((old_rect|rect,old_value+value))
        else:merged.append((rect,value))
    native=merged
    # Read reliable Latin/digit spans directly from the source. Use these to
    # detect OCR losses of decimal points, ranges and units in narrative lines.
    reliable=[]
    for span in page.get_texttrace():
        if span['font'] not in ('TimesNewRoman','Arial') or span['size']<8:
            continue
        run=[]
        for char in span['chars']:
            if char[0]==65533:
                if run:reliable.append(run);run=[]
            else:
                if run and abs(char[2][1]-run[-1][2][1])>2:
                    reliable.append(run);run=[]
                run.append(char)
        if run:reliable.append(run)
    lines=defaultdict(list)
    line_confidences=defaultdict(list)
    with (OUTPUT/'pages'/f'{number:04d}.tsv').open() as handle:
        for row in csv.DictReader(handle,delimiter='\t',quoting=csv.QUOTE_NONE):
            if row['level']!='5' or not row.get('text','').strip():continue
            box=pymupdf.Rect(int(row['left'])*72/400,int(row['top'])*72/400,
                (int(row['left'])+int(row['width']))*72/400,(int(row['top'])+int(row['height']))*72/400)
            center=(box.tl+box.br)/2
            if any(center in rect for rect,_ in native):continue
            key=(row['block_num'],row['par_num'],row['line_num'])
            lines[key].append((box,row['text']))
            line_confidences[key].append((float(row['conf']),len(row['text'])))
    ordered=[]
    low_quality_text=set()
    for key,items in lines.items():
        rect=pymupdf.Rect(items[0][0])
        for box,_ in items:rect|=box
        value=' '.join(t for _,t in sorted(items,key=lambda x:x[0].x0))
        confidences=line_confidences[key]
        if sum(c*n for c,n in confidences)/sum(n for _,n in confidences)<80:
            low_quality_text.add(normalize_japanese(value))
        ordered.append((rect,value))
    ordered.extend(native)
    ordered.sort(key=lambda item:(round(((item[0].y0+item[0].y1)/2)/6)*6,item[0].x0))
    content=normalize_japanese('\n'.join(text for _,text in ordered))
    retained=[]; rejected=[]
    for box,text in ordered:
        normalized=normalize_japanese(text)
        observed=Counter(re.findall(r'\d+(?:\.\d+)?',normalized))
        expected=Counter()
        expected_units=set()
        for run in reliable:
            # Tesseract line boxes describe ink; expand vertically for descenders.
            selected=[g for g in run if box.x0-1<=(g[3][0]+g[3][2])/2<=box.x1+1
                and box.y0-3<=(g[3][1]+g[3][3])/2<=box.y1+3]
            native_text=''.join(chr(g[0]) for g in selected)
            expected.update(re.findall(r'\d+(?:\.\d+)?',native_text))
            expected_units.update(re.findall(r'(?<![A-Za-z])(kg|mg|kcal|mmol|mEq|dL)(?![A-Za-z])',native_text))
        missing=expected-observed
        absent_units=[unit for unit in expected_units if unit not in normalized.replace(' ','')]
        if missing or absent_units or normalized in low_quality_text:
            rejected.append({'text':normalized,'native_numbers_missing_or_changed':list(missing.elements()),
                'native_units_missing_or_changed':absent_units,
                'low_line_confidence':normalized in low_quality_text})
        else:
            retained.append(normalized)
    retrieval_content='\n'.join(retained)
    printed=[text for box,text in native if box.y0>page.rect.height*.92 and re.fullmatch(r'[0-9０-９]{1,3}',text)]
    table_area=0
    try:
        for table in page.find_tables().tables:
            if table.row_count>=3 and table.col_count>=2:
                table_area+=pymupdf.Rect(table.bbox).get_area()
    except Exception as exc:
        raise RuntimeError(f'Table detection failed on page {number}') from exc
    return content, printed[-1] if len(printed)==1 else None, len(native),table_area/page.rect.get_area(), retrieval_content, rejected


def main():
    reference_file=ROOT/'.tools/fonts/BIZUDPGothic-Regular.ttf'
    font=TTFont(reference_file)
    reference={font.getGlyphID(g):chr(u) for u,g in font.getBestCmap().items()}
    ocr=json.loads((OUTPUT/'pages.json').read_text())
    metadata=ocr['metadata']|{'text_repair':'ocr-with-native-biz-gothic-lines-numeric-and-line-check-v3',
        'reference_font_sha256':hashlib.sha256(reference_file.read_bytes()).hexdigest(),
        'reference_font_url':'https://github.com/google/fonts/tree/main/ofl/bizudpgothic'}
    pages=[]
    with pymupdf.open(SOURCE) as pdf:
        for row,page in zip(ocr['pages'],pdf):
            text,printed,native,table_ratio,retrieval,rejected=restore_page(page,row['pdf_page'],reference)
            reason=''
            if len(re.sub(r'\s','',text))<80:reason='封面/空白/文字过少'
            elif row['mean_confidence']<85 or row['low_confidence_fraction']>.10:reason='OCR置信度偏低，需逐页复核'
            elif table_ratio>.12:reason='复杂表格页，保留OCR结果，待表格结构与数值核对'
            if len(re.sub(r'\s','',retrieval))<80:reason='数值校验后可检索文字过少'
            if row['pdf_page']<=12:reason='封面/名录/目录等前置页，不参与正文检索'
            if row['pdf_page']==486:reason='出版信息页，不参与正文检索'
            pages.append(row|{'content':text,'printed_page':printed or row['printed_page'],
                'native_lines_restored':native,'table_area_fraction':round(table_ratio,4),
                'retrieval_content':retrieval,'excluded_numeric_lines':rejected,
                'status':'quarantined' if reason else 'eligible','reason':reason})
            if len(pages)%50==0:print(f'Text quality check {len(pages)}/486',flush=True)
    data={'metadata':metadata,'pages':pages}
    (OUTPUT/'repaired-pages.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    (OUTPUT/'dietary-reference-intakes-2025-repaired.txt').write_text('\n\n'.join(
        f'=== PDF page {p["pdf_page"]}; {p["status"]} ===\n{p["content"]}' for p in pages))
    print('Eligible:',sum(p['status']=='eligible' for p in pages),'of',len(pages),flush=True)


if __name__=='__main__':main()
