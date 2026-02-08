import uuid
from flask import g
from flask_restx import Namespace, Resource

from app.utils.registry import Registry
from app.providers.StorageProvider.local_provider import LocalStorageProvider
from app.utils.text_extract import extract_text
from app.providers.Chunking.chunker import chunk_text
from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.StorageProvider.s3_provider import S3StorageProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.Models.index_dto import ChunkIndexDTO
from app.utils.errors import ValidationError, NotFoundError

ns = Namespace("ingest", description="Ingest documents into the system", path="/v1/ingest")

@ns.route("/<string:doc_id>")
class IngestDoc(Resource):
    def post(self, doc_id: str):
        """Ingest a document by its ID: extract text, chunk, embed, and index."""
        # Retrieve document metadata
        reg= Registry(f"{g.cfg.local_storage_dir}/registry.json")
        record = reg.get(doc_id)
        if not record:
            raise NotFoundError("DOC_NOT_FOUND", f"Document with id {doc_id} not found", 404)
        
        # storage = LocalStorageProvider(g.cfg.local_storage_dir)
        # content = storage.read(record["path"])
        # filename = record["filename"]

        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        content = s3.read(record["s3_key"])
        filename = record["filename"]
        request_tenant = (getattr(g, "tenant", "") or "").strip()
        if not request_tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)

        tenant = record.get("tenant") 
        if not tenant:
            raise ValidationError("MISSING_TENANT_IN_RECORD", f"Document record for id {doc_id} is missing tenant info", 500)
        
        if tenant != request_tenant:
            raise ValidationError("TENANT_MISMATCH", f"Document {doc_id} belongs to tenant {tenant}, not {request_tenant}", 403)

        text = extract_text(filename, content)
        if not text.strip():
            raise ValidationError("EMPTY_TEXT", f"Extracted text from document {doc_id} is empty", 400)
        scope = "corpus"

        chunks = chunk_text(text)
        if not chunks:
            raise ValidationError("EMPTY_CHUNKS", f"Chunked text from document {doc_id} is empty", 400)
        
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)


        es_ids = []
        for i, ch in enumerate(chunks, start=1):
            vec = embedder.embed_text(ch)
            dto = ChunkIndexDTO(
                tenant=tenant,
                scope=scope,
                doc_id=doc_id,
                chunk_id=f"c{i}",
                source=filename,
                created_at=ChunkIndexDTO.now_iso(),
                chunk_text=ch,
                embedding=vec,
            )
            es_doc_id = index.upsert_chunk(dto)
            es_ids.append(es_doc_id)

        return {"status": "success", "doc_id": doc_id, "chunks_indexed": len(es_ids)}, 201
    

@ns.route("/")
class IngestTenant(Resource):
    def post(self):
        """Ingest all unindexed documents for a tenant."""
        request_tenant = (getattr(g, "tenant", "") or "").strip()
        if not request_tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)

        reg= Registry(f"{g.cfg.local_storage_dir}/registry.json")
        records = reg.list_by_tenant(request_tenant)
        if not records:
            raise NotFoundError("NO_DOCS_FOUND", f"No documents found for tenant {request_tenant}", 404)
        
        # Create Heavy dependencies once
        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)
        scope = "corpus"

        summary = {
            "status": "success",
            "tenant": request_tenant,
            "docs_found": len(records),
            "ingested": [],
            "skipped": [],
            "failed": []
        }

        for record in records:
            doc_id = record["doc_id"]
            try:
                # check if document already indexed
                existing = index.count_chunks(request_tenant, scope, doc_id)
                if existing > 0:
                    summary["skipped"].append({"doc_id": doc_id, "reason": "already indexed", "existing_chunks": existing})
                    continue
                
                # Ingest pipeline
                content = s3.read(record["s3_key"])
                filename = record["filename"]

                text = extract_text(filename, content)
                if not text.strip():
                    raise ValidationError("EMPTY_TEXT", f"Extracted text from document {doc_id} is empty", 400)
                
                chunks = chunk_text(text)
                if not chunks:
                    raise ValidationError("EMPTY_CHUNKS", f"Chunked text from document {doc_id} is empty", 400)

                es_ids = []
                for i, ch in enumerate(chunks, start=1):
                    vec = embedder.embed_text(ch)
                    dto = ChunkIndexDTO(
                        tenant=request_tenant,
                        scope=scope,
                        doc_id=doc_id,
                        chunk_id=f"c{i}",
                        source=filename,
                        created_at=ChunkIndexDTO.now_iso(),
                        chunk_text=ch,
                        embedding=vec,
                    )
                    es_ids.append(index.upsert_chunk(dto))

                summary["ingested"].append({"doc_id": doc_id, "chunks_indexed": len(es_ids)})

            except Exception as e:
                summary["failed"].append({"doc_id": doc_id, "error": str(e)})
                
        # decide status code
        if summary["ingested"]:
            return summary, 201

        return {**summary, "status": "no_action", "message": f"All documents for tenant {request_tenant} are already indexed"}, 200