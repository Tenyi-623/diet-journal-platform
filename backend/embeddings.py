"""Embedding client shared by online queries and future offline ingestion."""
import math

import httpx


async def embed_texts(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    model: str,
    texts: list[str],
    expected_dim: int,
) -> list[list[float]]:
    response = await client.post(
        f'{base_url}/api/embed',
        json={'model': model, 'input': texts, 'truncate': False},
    )
    response.raise_for_status()
    vectors = response.json().get('embeddings')
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise ValueError('Embedding service returned an unexpected vector count')
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != expected_dim:
            raise ValueError(f'Embedding dimension does not match configured {expected_dim}')
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vector):
            raise ValueError('Embedding contains invalid numeric values')
    return vectors
