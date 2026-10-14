"""Auditable, resumable PDF ingestion. Run with --audit-only before importing."""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

import httpx
import pymupdf
from psycopg.types.json import Jsonb

from .config import settings
from .embeddings import embed_texts
from .knowledge import PIPELINE_VERSION, connect, initialize, model_identity, vector_literal

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'


def clean_text(text):
    text = text.replace('\x00', '').replace('\r', '\n')
    text = re.sub(r'[ \t\u3000]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def chunk_text(text, size=1000, overlap=150):
    if not 0 <= overlap < size:
        raise ValueError('Overlap must be smaller than chunk size')
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Prefer paragraph/sentence ends in the latter half of each window.
            choices = [text.rfind(mark, start + size // 2, end) for mark in ('\n', '。', '．')]
            boundary = max(choices)
            if boundary >= 0:
                end = boundary + 1
        value = text[start:end].strip()
        if value:
            yield value
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def page_reason(text, source):
    if source['quarantine']:
        return source['warning']
    compact = re.sub(r'\s', '', text)
    if len(compact) < 80:
        return '文字过少/封面/空白，未参与向量检索'
    bad = sum('\u0700' <= c <= '\u1fff' or c == '\ufffd' for c in compact)
    if bad / len(compact) > 0.015:
        return '疑似字体映射乱码，需人工核对'
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    digits = sum(c.isdigit() for c in compact) / len(compact)
    short = sum(len(l) < 16 for l in lines) / max(len(lines), 1)
    if source['source_kind'] == 'food_composition_reference':
        if ('食品番号' in text and ('索引番号' in text or '調理形態' in text)) or digits > 0.16 or (len(lines) > 40 and short > 0.55):
            return '疑似成分表/调理表/索引页，待结构化提取与数值核对'
    return ''


def extract(source, input_dir):
    path = input_dir / source['filename']
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    original = DATA / 'originals' / f"{checksum[:16]}_{path.name}"
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists():
        shutil.copy2(path, original)
    if source.get('repaired_pages'):
        repair_path = ROOT / source['repaired_pages']
        repair = json.loads(repair_path.read_text())
        if repair['metadata']['source_sha256'] != checksum:
            raise ValueError('Repaired text does not match source PDF checksum')
        pages = [dict(row, content=row['retrieval_content']) for row in repair['pages']]
        with pymupdf.open(path) as pdf:
            if [p['pdf_page'] for p in pages] != list(range(1, len(pdf)+1)):
                raise ValueError('Repaired pages are incomplete or out of order')
        result = dict(source, sha256=checksum, source_path=str(original), pages=pages,
            extraction_metadata=repair['metadata'] | {
                'artifact_sha256': hashlib.sha256(repair_path.read_bytes()).hexdigest()})
        out = DATA / 'extracted' / f'{checksum}.json'
        # Preserve the failed native extraction for comparison.
        if out.exists() and not out.with_suffix('.native.json').exists():
            shutil.copy2(out, out.with_suffix('.native.json'))
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    pages = []
    with pymupdf.open(path) as pdf:
        for number, page in enumerate(pdf, 1):
            # PDF content-stream order avoids row-wise merging of two-column articles.
            text = clean_text(page.get_text(sort=False))
            reason = page_reason(text, source)
            # Explicit printed-page offsets are known from the document, not inferred
            # from PDF metadata. PDF physical page remains the canonical reference.
            printed = source['printed_page_start']
            pages.append({'pdf_page': number,
                'printed_page': str(printed + number - 1) if printed is not None else None,
                'content': text, 'status': 'quarantined' if reason else 'eligible',
                'reason': reason})
    result = dict(source, sha256=checksum, source_path=str(original), pages=pages)
    out = DATA / 'extracted' / f'{checksum}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def write_report(documents):
    summaries = []
    for doc in documents:
        eligible = [p for p in doc['pages'] if p['status'] == 'eligible']
        summaries.append({k: doc[k] for k in ('title','filename','sha256','edition','source_kind','warning')} | {
            'pages': len(doc['pages']), 'eligible_pages': len(eligible),
            'quarantined_pages': len(doc['pages'])-len(eligible),
            'planned_chunks': sum(len(list(chunk_text(p['content']))) for p in eligible),
            'quarantine_reasons': dict(Counter(p['reason'] for p in doc['pages'] if p['reason']))})
    folder = DATA / 'reports'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'pdf_audit.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2))
    lines = ['# PDF 入库检查', '', '自动提取检查不等于逐页人工核对或医学审查。隔离页面不参与检索。', '',
        '| 文件 | 总页数 | 可提取候选页 | 隔离页 | 计划片段 |', '|---|---:|---:|---:|---:|']
    for d in summaries:
        lines.append(f"| {d['filename']} | {d['pages']} | {d['eligible_pages']} | {d['quarantined_pages']} | {d['planned_chunks']} |")
    for d in summaries:
        lines += ['', f"## {d['title']}", '', d['warning']]
    (folder / 'pdf_audit.md').write_text('\n'.join(lines)+'\n')
    return summaries


async def ingest(documents, *, initialize_schema=True, progress=None):
    if initialize_schema:
        initialize()
    document_ids = []
    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        digest, fingerprint = await model_identity(client)
        with connect() as conn:
            # One importer at a time; session lock survives per-batch commits.
            if not conn.execute('SELECT pg_try_advisory_lock(732104611) AS locked').fetchone()['locked']:
                raise RuntimeError('Another knowledge import is running')
            collection_id = conn.execute('''INSERT INTO kb_collections
                (fingerprint,model,model_digest,dimensions,pipeline_version) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(fingerprint) DO UPDATE SET fingerprint=EXCLUDED.fingerprint RETURNING id''',
                (fingerprint,settings.embedding_model,digest,settings.embedding_dim,PIPELINE_VERSION)).fetchone()['id']
            conn.commit()
            for doc in documents:
                active = [p for p in doc['pages'] if p['status'] == 'eligible']
                doc_id = conn.execute('''INSERT INTO kb_documents
                    (collection_id,sha256,title,filename,source_path,publisher,edition,source_kind,warning,page_count,status,enabled)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(collection_id,sha256) DO UPDATE SET warning=EXCLUDED.warning,
                        title=EXCLUDED.title,edition=EXCLUDED.edition,source_kind=EXCLUDED.source_kind,
                        publisher=EXCLUDED.publisher RETURNING id''',
                    (collection_id,doc['sha256'],doc['title'],doc['filename'],doc['source_path'],doc['publisher'],
                     doc['edition'],doc['source_kind'],doc['warning'],len(doc['pages']), 'importing' if active else 'quarantined',
                     doc.get('enabled', True))).fetchone()['id']
                document_ids.append(doc_id)
                conn.execute('UPDATE kb_documents SET status=%s WHERE id=%s', ('importing' if active else 'quarantined',doc_id))
                extraction_fingerprint = hashlib.sha256(json.dumps(
                    {'pages':doc['pages'], 'metadata':doc.get('extraction_metadata',{})},
                    ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                conn.execute('UPDATE kb_documents SET extraction_fingerprint=%s,extraction_metadata=%s WHERE id=%s',
                    (extraction_fingerprint,Jsonb(doc.get('extraction_metadata',{})),doc_id))
                for page in doc['pages']:
                    conn.execute('''INSERT INTO kb_pages(document_id,pdf_page,printed_page,content,status,reason)
                        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(document_id,pdf_page)
                        DO UPDATE SET content=EXCLUDED.content,status=EXCLUDED.status,reason=EXCLUDED.reason,
                            printed_page=EXCLUDED.printed_page''',
                        (doc_id,page['pdf_page'],page['printed_page'],page['content'],page['status'],page['reason']))
                    page_metadata = {k:v for k,v in page.items() if k not in
                        ('content','retrieval_content','pdf_page','printed_page','status','reason')}
                    conn.execute('UPDATE kb_pages SET extraction_metadata=%s WHERE document_id=%s AND pdf_page=%s',
                        (Jsonb(page_metadata),doc_id,page['pdf_page']))
                desired = {(p['pdf_page'],i):t for p in active for i,t in enumerate(chunk_text(p['content']))}
                existing = {(r['pdf_page'],r['chunk_index']):r['content'] for r in conn.execute(
                    'SELECT pdf_page,chunk_index,content FROM kb_chunks WHERE document_id=%s',(doc_id,)).fetchall()}
                # A same-PDF OCR repair can change text and eligibility. Reuse a vector
                # only when its actual chunk content is identical; remove stale rows.
                for key,content in list(existing.items()):
                    if desired.get(key) != content:
                        conn.execute('DELETE FROM kb_chunks WHERE document_id=%s AND pdf_page=%s AND chunk_index=%s',
                            (doc_id,*key))
                        del existing[key]
                pending = [(page,index,text) for (page,index),text in desired.items() if (page,index) not in existing]
                conn.commit()
                print(f"{doc['title']}: {len(pending)} pending chunks; {len(existing)} already stored",flush=True)
                for offset in range(0,len(pending),8):
                    batch = pending[offset:offset+8]
                    vectors = await embed_texts(client,base_url=settings.ollama_base_url,model=settings.embedding_model,
                        texts=[x[2] for x in batch],expected_dim=settings.embedding_dim)
                    for (page,index,content),vector in zip(batch,vectors):
                        conn.execute('''INSERT INTO kb_chunks(document_id,pdf_page,chunk_index,content,embedding)
                            VALUES (%s,%s,%s,%s,%s::halfvec(2560)) ON CONFLICT DO NOTHING''',
                            (doc_id,page,index,content,vector_literal(vector)))
                    conn.commit()
                    if progress:
                        progress(doc_id)
                    if offset % 80 == 0 or offset+8 >= len(pending):
                        print(f"  embedded {min(offset+8,len(pending))}/{len(pending)}",flush=True)
                # Detect a replaced model tag before publishing the document.
                if (await model_identity(client))[0] != digest:
                    raise RuntimeError('Embedding model changed during ingestion; document remains unpublished')
                conn.execute('UPDATE kb_documents SET status=%s WHERE id=%s',('ready' if active else 'quarantined',doc_id))
                conn.commit()
            conn.execute('ANALYZE kb_chunks')
    print('Import complete',flush=True)
    return document_ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir',type=Path,default=Path('/home/aitd/下载'))
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--only',help='Import only the source with this source_kind')
    args = parser.parse_args()
    sources = json.loads(Path(__file__).with_name('sources.json').read_text())
    documents = [extract(source,args.input_dir) for source in sources]
    print(json.dumps(write_report(documents),ensure_ascii=False,indent=2),flush=True)
    if not args.audit_only:
        selected = [d for d in documents if not args.only or d['source_kind']==args.only]
        if not selected:
            raise ValueError('No source matches --only')
        asyncio.run(ingest(selected))


if __name__ == '__main__':
    main()
