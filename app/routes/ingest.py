import uuid
from flask import g
from flask_restx import Namespace, Resource

from app.utils.registry import Registry
from app.providers.StorageProvider.local_provider import LocalStorageProvider
from app.utils.text_extract import extract_text
from app.providers.Chunking.chunker import chunk_text
from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.Models.index_dto import ChunkIndexDTO
from app.utils.errors import ValidationError, NotFoundError

ns = Namespace("ingest", description="Ingest documents into the system")

@ns.route("/<string:doc_id>")
class IngestDoc(Resource):
    def post(self, doc_id: str):
        """Ingest a document by its ID: extract text, chunk, embed, and index."""
        # Retrieve document metadata
        reg= Registry(f"{g.cfg.local_storage_dir}/registry.json")
        record = reg.get(doc_id)
        if not record:
            raise NotFoundError("DOC_NOT_FOUND", f"Document with id {doc_id} not found", 404)
        
        storage = LocalStorageProvider(g.cfg.local_storage_dir)
        content = storage.read(record["path"])
        filename = record["filename"]

        text = extract_text(filename, content)
        if not text.strip():
            raise ValidationError("EMPTY__TEXT", f"Extracted text from document {doc_id} is empty", 400)
        
        chunks = chunk_text(text)
        if not chunks:
            raise ValidationError("EMPTY_CHUNKS", f"Chunked text from document {doc_id} is empty", 400)
        
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        # For now: single tenant + corpus scope
        tenant = "demo"
        scope = "corpus"

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
                vector=vec,
            )
            es_doc_id = index.upsert_chunk(dto)
            es_ids.append(es_doc_id)

        return {"status": "success", "doc_id": doc_id, "chunks_indexed": len(es_ids)}, 201