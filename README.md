# RAG Orchestration API

A production-minded Retrieval-Augmented Generation (RAG) orchestration service built with Flask, Elasticsearch, and Groq. It handles document upload, ingestion, hybrid retrieval (BM25 + vector), and grounded answers with citations. Multi-tenant isolation is enforced via request headers.

**Highlights**
- Hybrid retrieval (BM25 + vector) with configurable `top_k`
- Multi-tenant document management with quotas and registry
- Chunking + embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`)
- Elasticsearch-backed chunk index
- Groq LLM generation with citation extraction
- Document summaries: full-document and query-guided
- S3-backed storage with local registry metadata
- Built-in health checks and seed endpoint

**Architecture**
- API: Flask + Flask-RESTX, Gunicorn
- Storage: S3 for raw files, local registry for metadata and quotas
- Retrieval: Elasticsearch index for chunk search (BM25 + vector)
- Embeddings: Local SentenceTransformers model
- LLM: Groq API

**Core Data Flow**
1. Upload documents to S3 via `/v1/documents` (tenant-scoped)
2. Ingest document(s) with `/v1/ingest` to extract, chunk, embed, and index
3. Query with `/v1/rag/query` or `/v1/rag/query_doc` for grounded answers
4. Summarize with `/v1/rag/summary` (full doc or query-guided)

**API Overview**
- `GET /v1/health`
- `GET /v1/health/es`
- `GET /v1/health/index`
- `POST /v1/documents` upload one or many files (multipart field `file`)
- `POST /v1/ingest` ingest all unindexed docs for a tenant
- `POST /v1/ingest/<doc_id>` ingest a single document
- `POST /v1/retrieve` hybrid retrieval (debug)
- `POST /v1/retrieve_debug/bm25` BM25 only (debug)
- `POST /v1/retrieve_debug/vector` vector only (debug)
- `POST /v1/rag/query` RAG answer over tenant corpus
- `POST /v1/rag/query_doc` RAG answer constrained to one document
- `POST /v1/rag/summary` document summary (full or query-guided)
- `GET /v1/chunks/<es_doc_id>` fetch a chunk by ES id (debug)
- `POST /v1/seed/chunk` seed one sample chunk into ES (debug)

**Interactive Docs**
- Swagger UI at `/docs`

**Quickstart (Docker)**
1. Ensure Docker is running.
2. Configure `.env` (see next section).
3. Start services:

```bash
docker compose up --build
```

API will be available at `http://localhost:8000`.

**Environment Variables**
The service reads configuration from `.env` and environment variables.

Required or commonly used:
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `S3_BUCKET`
- `AWS_REGION`
- `ES_URL` (default `http://localhost:9200`)
- `LOCAL_STORAGE_DIR` (default `/data`)
- `EMBED_MODEL_NAME` (default `sentence-transformers/all-MiniLM-L6-v2`)
- `ES_INDEX_CHUNKS` (default `rag_chunks`)
- `ES_INDEX_DOCS` (default `rag_documents`)
- `ES_EMBEDDING_DIM` (default `384`)

Quota and request limits:
- `MAX_REQUEST_BYTES`
- `MAX_FILES_PER_REQUEST`
- `MAX_TOTAL_UPLOAD_BYTES`
- `MAX_SINGLE_FILE_BYTES`
- `TENANT_DAILY_UPLOAD_BYTES`
- `TENANT_DAILY_UPLOAD_FILES`

Summarization controls:
- `SUMMARY_MAX_CHARS`
- `SUMMARY_BATCH_SIZE`

**Authentication / Tenancy**
Tenant scoping is enforced via the `X-Tenant-Id` header for these endpoints:
- `/v1/documents`
- `/v1/ingest`
- `/v1/rag/query`
- `/v1/rag/query_doc`
- `/v1/rag/summary`

**Usage Examples**

Upload one or more files:
```bash
curl -X POST http://localhost:8000/v1/documents \
  -H "X-Tenant-Id: demo" \
  -F "file=@sample.pdf"
```

Ingest all documents for a tenant:
```bash
curl -X POST http://localhost:8000/v1/ingest \
  -H "X-Tenant-Id: demo"
```

Ingest a single document:
```bash
curl -X POST http://localhost:8000/v1/ingest/<doc_id> \
  -H "X-Tenant-Id: demo"
```

RAG query (tenant corpus):
```bash
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" \
  -d '{"query":"What is the termination notice period?","top_k":5}'
```

RAG query within a document:
```bash
curl -X POST http://localhost:8000/v1/rag/query_doc \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" \
  -d '{"doc_id":"<doc_id>","query":"Summarize the payment terms","top_k":5}'
```

Full-document summary:
```bash
curl -X POST http://localhost:8000/v1/rag/summary \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" \
  -d '{"doc_id":"<doc_id>"}'
```

Query-guided summary:
```bash
curl -X POST http://localhost:8000/v1/rag/summary \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" \
  -d '{"doc_id":"<doc_id>","query":"Key obligations and penalties","top_k":5}'
```

Health checks:
```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/health/es
curl http://localhost:8000/v1/health/index
```

**Operational Notes**
- Elasticsearch indices are created at startup.
- Registry and quota state live under `LOCAL_STORAGE_DIR` (default `/data`).
- The Docker setup mounts AWS credentials from `${USERPROFILE}/.aws` into the container.

**Project Structure**
- `WebAPI.py` app factory and API wiring
- `app/routes/` HTTP endpoints
- `app/providers/` integrations (S3, ES, embeddings, LLM)
- `app/utils/` helpers (chunking, prompts, registry, quota, errors)

**License**
Add your license here.
