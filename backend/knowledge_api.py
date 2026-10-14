"""Read-only knowledge search endpoints; ingestion stays an offline operation."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
import httpx
import psycopg

if __package__:
    from .knowledge import inventory, search
else:
    from knowledge import inventory, search

router = APIRouter(prefix='/api/knowledge', tags=['知识库'])
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: int | None = Field(default=None, gt=0)

    @field_validator('query')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('查询不能为空')
        return value.strip()


@router.get('/documents')
async def documents():
    try:
        return await asyncio.to_thread(inventory)
    except (psycopg.Error, ValueError):
        logger.exception('Knowledge database unavailable')
        raise HTTPException(status_code=503, detail='知识库尚未初始化或数据库不可用，请检查服务日志')


@router.post('/search')
async def search_knowledge(body: SearchRequest, request: Request):
    try:
        return await search(request.app.state.http_client,body.query,body.top_k,body.document_id)
    except psycopg.Error:
        logger.exception('Knowledge database search failed')
        raise HTTPException(status_code=503, detail='知识库数据库不可用，请检查服务日志')
    except (httpx.HTTPError, ValueError):
        logger.exception('Knowledge embedding failed')
        raise HTTPException(status_code=502, detail='知识库向量服务不可用或配置不匹配，请检查服务日志')
