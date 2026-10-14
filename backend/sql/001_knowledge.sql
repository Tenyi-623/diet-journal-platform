CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS kb_collections (
    id bigserial PRIMARY KEY,
    fingerprint text UNIQUE NOT NULL,
    model text NOT NULL,
    model_digest text NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions = 2560),
    pipeline_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS kb_documents (
    id bigserial PRIMARY KEY,
    collection_id bigint NOT NULL REFERENCES kb_collections(id),
    sha256 text NOT NULL,
    title text NOT NULL,
    filename text NOT NULL,
    source_path text NOT NULL,
    publisher text NOT NULL,
    edition text NOT NULL,
    source_kind text NOT NULL,
    warning text NOT NULL,
    page_count integer NOT NULL,
    status text NOT NULL CHECK (status IN ('importing','ready','quarantined')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(collection_id, sha256)
);
CREATE TABLE IF NOT EXISTS kb_pages (
    document_id bigint NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    pdf_page integer NOT NULL CHECK(pdf_page > 0),
    printed_page text,
    content text NOT NULL,
    status text NOT NULL CHECK(status IN ('eligible','quarantined')),
    reason text NOT NULL,
    PRIMARY KEY(document_id, pdf_page)
);
CREATE TABLE IF NOT EXISTS kb_chunks (
    id bigserial PRIMARY KEY,
    document_id bigint NOT NULL,
    pdf_page integer NOT NULL,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    embedding halfvec(2560) NOT NULL,
    FOREIGN KEY(document_id, pdf_page) REFERENCES kb_pages(document_id, pdf_page) ON DELETE CASCADE,
    UNIQUE(document_id, pdf_page, chunk_index)
);
CREATE INDEX IF NOT EXISTS kb_chunks_embedding_hnsw
ON kb_chunks USING hnsw (embedding halfvec_cosine_ops);
CREATE INDEX IF NOT EXISTS kb_documents_collection ON kb_documents(collection_id);
ALTER TABLE kb_documents ADD COLUMN IF NOT EXISTS extraction_fingerprint text;
ALTER TABLE kb_documents ADD COLUMN IF NOT EXISTS extraction_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE kb_pages ADD COLUMN IF NOT EXISTS extraction_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE kb_documents ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;
