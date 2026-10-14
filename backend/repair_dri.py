"""Rebuild the broken PDF text layer with local Japanese OCR; resumable by page."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path('/home/aitd/下载/「日本人の食事摂取基準(2025年版)」策定検討会報告書(1).pdf')
OUTPUT = ROOT/'data/repair/dri2025'
ENGINE = ROOT/'.tools/ocr/root/usr/bin/tesseract'
TESSDATA = ROOT/'.tools/ocr/tessdata'
RECIPE = 'tesseract-5.3.4-jpn-best-eng-fast-400dpi-psm3-v1'


def normalize_japanese(text):
    # Remove OCR token spaces only between Japanese characters or punctuation.
    # Preserve Latin words, digits, decimal points, unit symbols and line breaks.
    jp = r'\u3000-\u30ff\u3400-\u9fff\uff01-\uff60'
    return re.sub(rf'(?<=[{jp}]) +(?=[{jp}])', '', text).strip()


def process_page(number):
    target = OUTPUT/'pages'/f'{number:04d}'
    meta = target.with_suffix('.json')
    if meta.exists() and target.with_suffix('.pdf').exists():
        return json.loads(meta.read_text())
    start = time.monotonic()
    with pymupdf.open(SOURCE) as document:
        page = document[number-1]
        pix = page.get_pixmap(dpi=400, colorspace=pymupdf.csGRAY)
        pix.save(str(target.with_suffix('.png')))
        width,height = pix.width,pix.height
    env = dict(os.environ,OMP_THREAD_LIMIT='1',
        LD_LIBRARY_PATH=str(ROOT/'.tools/ocr/root/usr/lib/aarch64-linux-gnu'))
    result = subprocess.run([str(ENGINE),str(target.with_suffix('.png')),str(target),
        '--tessdata-dir',str(TESSDATA),'-l','jpn+eng','--psm','3','txt','tsv','pdf'],
        env=env,capture_output=True,text=True,timeout=240)
    if result.returncode:
        raise RuntimeError(f'Page {number}: {result.stderr}')
    rows = list(csv.DictReader(target.with_suffix('.tsv').open(),delimiter='\t',quoting=csv.QUOTE_NONE))
    words = [r for r in rows if r['level']=='5' and r.get('text','').strip()]
    confidence = sum(float(w['conf'])*len(w['text']) for w in words)/max(sum(len(w['text']) for w in words),1)
    low_fraction = sum(len(w['text']) for w in words if float(w['conf'])<50)/max(sum(len(w['text']) for w in words),1)
    raw = target.with_suffix('.txt').read_text()
    text = normalize_japanese(raw)
    # OCR an actual footer, never invent printed pages from a constant offset.
    footers = [w['text'] for w in words if int(w['top'])>height*0.92 and re.fullmatch(r'\d{1,3}',w['text'])]
    printed = footers[-1] if len(footers)==1 else None
    page_data = {'pdf_page':number,'content':text,'printed_page':printed,
        'mean_confidence':round(confidence,2),'low_confidence_fraction':round(low_fraction,4),
        'seconds':round(time.monotonic()-start,2),'width':width,'height':height}
    meta.write_text(json.dumps(page_data,ensure_ascii=False,indent=2))
    # The generated PDF retains the rendered page; the temporary raster is redundant.
    target.with_suffix('.png').unlink()
    return page_data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=10)
    args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'pages').mkdir(exist_ok=True)
    metadata={'source_path':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'recipe':RECIPE,'model_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in TESSDATA.glob('*.traineddata')},
        'official_url':'https://www.mhlw.go.jp/content/10904750/001316585.pdf'}
    manifest=OUTPUT/'recipe.json'
    if manifest.exists() and json.loads(manifest.read_text())!=metadata:
        raise RuntimeError('OCR source or recipe changed; use a new output directory')
    manifest.write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    with pymupdf.open(SOURCE) as pdf: count=len(pdf)
    results=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks=[pool.submit(process_page,n) for n in range(1,count+1)]
        for task in as_completed(tasks):
            row=task.result();results.append(row)
            if len(results)%10==0 or len(results)==count:
                print(f'OCR {len(results)}/{count}; latest page {row["pdf_page"]}; confidence {row["mean_confidence"]}',flush=True)
    results.sort(key=lambda x:x['pdf_page'])
    repaired=pymupdf.open()
    for row in results:
        with pymupdf.open(OUTPUT/'pages'/f'{row["pdf_page"]:04d}.pdf') as page:
            repaired.insert_pdf(page)
    repaired.set_metadata({'title':'日本人の食事摂取基準2025 — OCR text repair',
        'subject':'Original page images with machine-recognized Japanese text; verify numerical values against images.'})
    repaired.save(OUTPUT/'dietary-reference-intakes-2025-ocr.pdf',garbage=4,deflate=True)
    (OUTPUT/'pages.json').write_text(json.dumps({'metadata':metadata,'pages':results},ensure_ascii=False,indent=2))
    (OUTPUT/'dietary-reference-intakes-2025.txt').write_text('\n\n'.join(
        f'=== PDF page {r["pdf_page"]} ===\n{r["content"]}' for r in results))
    print('OCR finished',flush=True)


if __name__=='__main__':
    main()
