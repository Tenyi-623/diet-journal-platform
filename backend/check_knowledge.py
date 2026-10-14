"""Integration checks against the running local API and PostgreSQL."""
import asyncio
import json
from pathlib import Path

import httpx

from .knowledge import connect, search_database


async def main():
    report = {'checks': [], 'queries': []}
    with connect() as conn:
        assert conn.execute('''SELECT count(*) AS n FROM kb_chunks ch JOIN kb_pages p
            ON p.document_id=ch.document_id AND p.pdf_page=ch.pdf_page
            WHERE p.status='quarantined' ''').fetchone()['n'] == 0
        assert conn.execute('SELECT count(*) AS n FROM kb_chunks WHERE vector_dims(embedding)<>2560').fetchone()['n'] == 0
        assert conn.execute("SELECT count(*) AS n FROM pg_indexes WHERE indexname='kb_chunks_embedding_hnsw'").fetchone()['n'] == 1
        sample = conn.execute('SELECT embedding::text AS vector FROM kb_chunks LIMIT 1').fetchone()
        assert sample
        assert search_database('nonexistent-model-fingerprint',json.loads(sample['vector']),5) == []
        report['checks'] += ['隔离页面无向量', '全部向量2560维', 'HNSW索引存在', '不混用其他模型集合']
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=300) as client:
        response = await client.get('/api/knowledge/documents')
        response.raise_for_status()
        docs = response.json()['documents']
        assert len(docs) == 5
        assert sum(d['status']=='ready' for d in docs) == 4
        assert sum(d['status']=='quarantined' for d in docs) == 1
        for body in ({'query':' '},{'query':'test','top_k':0}):
            assert (await client.post('/api/knowledge/search',json=body)).status_code == 422
        for query in ['糖尿病の食事療法における管理栄養士の役割は？',
                      '糖尿病患者的饮食治疗中，营养师有什么作用？',
                      'What is the role of a dietitian in dietary therapy for diabetes?',
                      '高血圧管理・治療ガイドライン2025の改訂ポイントは？']:
            r = await client.post('/api/knowledge/search',json={'query':query,'top_k':3})
            r.raise_for_status()
            rows = r.json()['results']
            assert len(rows) == 3
            assert all(x['pdf_page']>0 and x['content'] and x['citation'] for x in rows)
            expected = 'guideline_commentary' if query.startswith('高血圧') else 'guideline_chapter'
            assert rows[0]['source_kind'] == expected, (query, rows[0]['title'])
            report['queries'].append({'query':query,'top_results':[
                {k: row[k] for k in ('title','pdf_page','printed_page','similarity','citation')} for row in rows]})
        excluded = next(d['id'] for d in docs if d['source_kind']=='historical_guideline')
        r = await client.post('/api/knowledge/search',json={'query':'腎臓病の食事療法','document_id':excluded})
        r.raise_for_status()
        assert r.json()['results'] == []
        report['checks'] += ['五份文档状态正确', '无效输入422', '中英日查询返回相关来源', '隔离文档不能被指定检索']
    target = Path(__file__).resolve().parent.parent/'data/reports/retrieval_check.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    asyncio.run(main())
