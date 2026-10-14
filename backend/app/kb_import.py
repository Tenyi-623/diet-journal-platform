"""Durable admin PDF imports processed by the existing single model worker."""

import asyncio
import logging
from pathlib import Path
import pymupdf
from psycopg.types.json import Jsonb
from backend.ingest import clean_text, chunk_text, page_reason, ingest
from .db import connect

logger = logging.getLogger(__name__)


def claim_upload():
    with connect() as c:
        c.execute("""UPDATE app_kb_uploads SET status='failed',error='导入中断，请重试',updated_at=now()
                  WHERE status='processing' AND lease_until<now() AND attempts>=2""")
        row = c.execute("""SELECT * FROM app_kb_uploads
             WHERE status='queued' OR (status='processing' AND lease_until<now() AND attempts<2)
             ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if row:
            c.execute(
                """UPDATE app_kb_uploads SET status='processing',attempts=attempts+1,
                      lease_until=now()+interval '30 minutes',updated_at=now() WHERE id=%s""",
                (row["id"],),
            )
        return row


def extract_upload(job):
    meta = job["metadata"]
    source = {
        **meta,
        "quarantine": meta["source_kind"] == "historical_guideline",
        "warning": meta["warning"] or "历史资料待核对，暂不参与检索",
    }
    pages = []
    path = Path(job["file_path"])
    with pymupdf.open(path) as pdf:
        if not pdf.is_pdf or pdf.needs_pass or not 1 <= len(pdf) <= 200:
            raise ValueError("仅支持未加密、1至200页的PDF")
        for number, page in enumerate(pdf, 1):
            text = clean_text(page.get_text(sort=False))
            reason = page_reason(text, source)
            pages.append(
                {
                    "pdf_page": number,
                    "printed_page": None,
                    "content": text,
                    "status": "quarantined" if reason else "eligible",
                    "reason": reason,
                }
            )
    if sum(len(p["content"]) for p in pages) > 350_000:
        raise ValueError("PDF文字过多，请拆分后上传")
    if (
        sum(
            len(list(chunk_text(p["content"])))
            for p in pages
            if p["status"] == "eligible"
        )
        > 500
    ):
        raise ValueError("PDF片段过多，请拆分后上传")
    return {
        **meta,
        "sha256": job["sha256"],
        "source_path": str(path),
        "pages": pages,
        "enabled": False,
        "extraction_metadata": {"pipeline": "admin-pdf-text-v1", "ocr": False},
    }


async def process_upload(job):
    try:
        doc = await asyncio.to_thread(extract_upload, job)

        def heartbeat(doc_id):
            with connect() as c:
                c.execute(
                    """UPDATE app_kb_uploads SET document_id=%s,lease_until=now()+interval '30 minutes',
                           updated_at=now() WHERE id=%s""",
                    (doc_id, job["id"]),
                )

        ids = await ingest([doc], initialize_schema=False, progress=heartbeat)
        with connect() as c:
            c.execute(
                """UPDATE app_kb_uploads SET status='ready',document_id=%s,error=NULL,
                      lease_until=NULL,updated_at=now() WHERE id=%s""",
                (ids[0], job["id"]),
            )
            c.execute(
                "INSERT INTO app_admin_audit(actor_id,action,target,detail) VALUES(%s,%s,%s,%s)",
                (
                    job["created_by"],
                    "knowledge.import",
                    str(ids[0]),
                    Jsonb({"upload_id": str(job["id"])}),
                ),
            )
    except Exception as exc:
        logger.exception("Knowledge upload failed: %s", job["id"])
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else "解析或模型向量化失败，请检查文件与模型服务后重试"
        )
        with connect() as c:
            c.execute(
                """UPDATE app_kb_uploads SET status='failed',error=%s,lease_until=NULL,
                      updated_at=now() WHERE id=%s""",
                (message[:400], job["id"]),
            )
