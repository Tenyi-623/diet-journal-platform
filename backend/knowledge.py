"""PostgreSQL knowledge store. Only complete, compatible collections are searched."""
import os
import hashlib
import json
from pathlib import Path

import httpx
import psycopg
from psycopg.rows import dict_row

if __package__:
    from .config import settings
    from .embeddings import embed_texts
else:
    from config import settings
    from embeddings import embed_texts

PIPELINE_VERSION = 'page-text-v1-1000-150-query-instruction'
QUERY_INSTRUCTION = 'Instruct: Given a question about nutrition or dietary guidelines, retrieve relevant passages that answer the question.\nQuery: '


def connect():
    if not settings.database_url:
        raise ValueError('DATABASE_URL is not configured')
    return psycopg.connect(os.environ.get("APP_DATABASE_URL") or settings.database_url, connect_timeout=5, row_factory=dict_row)


def initialize():
    if settings.embedding_dim != 2560:
        raise ValueError('This schema requires EMBEDDING_DIM=2560; use a migration for other dimensions')
    with connect() as conn:
        conn.execute(Path(__file__).with_name('sql').joinpath('001_knowledge.sql').read_text())


async def model_identity(client: httpx.AsyncClient):
    response = await client.get(f'{settings.ollama_base_url}/api/tags')
    response.raise_for_status()
    for model in response.json()['models']:
        if model['name'] == settings.embedding_model:
            digest = model['digest']
            key = json.dumps([settings.embedding_model, digest, settings.embedding_dim, PIPELINE_VERSION])
            return digest, hashlib.sha256(key.encode()).hexdigest()
    raise ValueError('Configured embedding model is not installed')


def vector_literal(vector):
    return '[' + ','.join(str(v) for v in vector) + ']'


def inventory():
    with connect() as conn:
        version = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
        docs = conn.execute('''SELECT d.id, d.title, d.filename, d.publisher, d.edition,
            d.source_kind, d.warning, d.page_count, d.status, d.extraction_metadata, d.extraction_fingerprint,
            c.model, c.model_digest, c.pipeline_version,
            (SELECT count(*) FROM kb_chunks ch WHERE ch.document_id=d.id) AS chunks,
            (SELECT count(*) FROM kb_pages p WHERE p.document_id=d.id AND p.status='quarantined') AS quarantined_pages
            FROM kb_documents d JOIN kb_collections c ON c.id=d.collection_id ORDER BY d.id''').fetchall()
        return {'pgvector_version': version['extversion'] if version else None, 'documents': docs}


def search_database(fingerprint, vector, top_k, document_id=None, source_kinds=None):
    with connect() as conn:
        # Exact ranking of eligible rows prevents filtered HNSW searches from silently
        # returning too few matches. Appropriate for this initial small knowledge base.
        rows = conn.execute('''WITH eligible AS MATERIALIZED (
            SELECT ch.id AS chunk_id, ch.content, ch.embedding, ch.pdf_page,
                p.printed_page, d.id AS document_id, d.title, d.filename,
                d.publisher, d.edition, d.source_kind, d.warning, d.extraction_metadata
            FROM kb_chunks ch JOIN kb_documents d ON d.id=ch.document_id
            JOIN kb_pages p ON p.document_id=ch.document_id AND p.pdf_page=ch.pdf_page
            JOIN kb_collections c ON c.id=d.collection_id
            WHERE c.fingerprint=%s AND d.status='ready' AND d.enabled AND p.status='eligible'
              AND (%s::bigint IS NULL OR d.id=%s::bigint)
              AND (%s::text[] IS NULL OR d.source_kind=ANY(%s::text[]))
        ) SELECT *, 1 - (embedding <=> %s::halfvec(2560)) AS similarity
        FROM eligible ORDER BY embedding <=> %s::halfvec(2560), chunk_id LIMIT %s''',
        (fingerprint, document_id, document_id, source_kinds, source_kinds,
         vector_literal(vector), vector_literal(vector), top_k)).fetchall()
        for row in rows:
            del row['embedding']
            row['citation'] = f"{row['title']} — PDF第{row['pdf_page']}页"
            if row['printed_page']:
                row['citation'] += f"（印刷页码 {row['printed_page']}）"
            row['review_status'] = 'machine_extracted_not_clinically_reviewed'
        return rows


async def search(client, query, top_k=5, document_id=None, source_kinds=None):
    import asyncio
    _, fingerprint = await model_identity(client)
    vectors = await embed_texts(client, base_url=settings.ollama_base_url,
        model=settings.embedding_model, texts=[QUERY_INSTRUCTION + query],
        expected_dim=settings.embedding_dim)
    results = await asyncio.to_thread(search_database, fingerprint, vectors[0], top_k, document_id, source_kinds)
    return {'query': query, 'model': settings.embedding_model, 'results': results,
            'note': '仅返回候选原文；相似度不是医学可靠性评分。已标记的复杂表格与低质量页面不参与检索；OCR内容及数值仍需核对原始页面。'}
