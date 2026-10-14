"""Verify the repaired source matches stored chunks and is searchable with citations."""
import asyncio
import json
from pathlib import Path

import httpx

from .ingest import chunk_text
from .knowledge import connect

ROOT=Path(__file__).resolve().parent.parent


async def main():
    repair=json.loads((ROOT/'data/repair/dri2025/repaired-pages.json').read_text())
    desired={(p['pdf_page'],i):t for p in repair['pages'] if p['status']=='eligible'
        for i,t in enumerate(chunk_text(p['retrieval_content']))}
    with connect() as conn:
        doc=conn.execute("SELECT id,status,extraction_fingerprint FROM kb_documents WHERE source_kind='dietary_reference_intakes'").fetchone()
        assert doc['status']=='ready' and doc['extraction_fingerprint']
        rows=conn.execute('SELECT pdf_page,chunk_index,content FROM kb_chunks WHERE document_id=%s',(doc['id'],)).fetchall()
        assert {(r['pdf_page'],r['chunk_index']):r['content'] for r in rows}==desired
        assert conn.execute('SELECT count(*) AS n FROM kb_chunks WHERE document_id<>%s',(doc['id'],)).fetchone()['n']==628
        assert not conn.execute('SELECT id FROM kb_chunks WHERE document_id=%s AND pdf_page IN (1,21,293,486)',(doc['id'],)).fetchall()
    queries=[('日本人の食事摂取基準2025の対象となる人は？',13),
        ('ナトリウムの過剰摂取と高血圧の関係は？',418),
        ('カリウムとナトリウムの関係は？',266),
        ('日本人膳食摄入标准适用于哪些人？',13)]
    report={'chunks':len(rows),'other_chunks':628,'checks':['stored text equals screened repair',
        'excluded pages have no vectors','other source chunk count unchanged'],'queries':[]}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=300) as client:
        for query,expected_page in queries:
            response=await client.post('/api/knowledge/search',json={'query':query,'document_id':doc['id'],'top_k':3})
            response.raise_for_status()
            matches=response.json()['results']
            assert len(matches)==3 and matches[0]['pdf_page']==expected_page,(query,matches)
            assert all(m['extraction_metadata']['text_repair'].endswith('v3') for m in matches)
            report['queries'].append({'query':query,'matches':[
                {k:m[k] for k in ('pdf_page','printed_page','similarity','content','citation')} for m in matches]})
    (ROOT/'data/reports/dri2025_retrieval.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('PASS:',len(rows),'repaired chunks, 628 existing chunks; 4 retrieval cases with correct top page')


if __name__=='__main__':asyncio.run(main())
