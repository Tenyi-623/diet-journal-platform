"""Run from project root: backend/.venv/bin/python -m backend.smoke_test"""
import asyncio
import math

import httpx

from .main import app


async def main():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            response = await client.get('/api/health')
            response.raise_for_status()
            print('Health:', response.json(), flush=True)
            response = await client.post('/api/chat', json={'message': '请只回复：连接成功'})
            response.raise_for_status()
            assert response.json()['response'].strip(), 'Empty model response'
            print('Chat:', response.json(), flush=True)
            response = await client.post('/api/embed', json={
                'texts': ['これは日本語の検索テストです。', '这是中文检索测试。']
            })
            response.raise_for_status()
            data = response.json()
            assert len(data['embeddings']) == 2
            for vector in data['embeddings']:
                assert len(vector) == data['dimensions']
                assert all(math.isfinite(v) for v in vector)
                assert any(v != 0 for v in vector)
            print('Embedding:', data['model'], '2 vectors, dimensions:', data['dimensions'], flush=True)
            for payload in ({'texts': []}, {'texts': [' ']}):
                assert (await client.post('/api/embed', json=payload)).status_code == 422
            print('PASS: model inference and input validation', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
