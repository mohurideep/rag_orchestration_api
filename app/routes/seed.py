#Test the search pipeline working at all
# POST /seed/chunk -> Create sample text -> Generate embedding -> Wrap in DTO -> Index into Elasticsearch -> Return IDs

import uuid
from flask import g
from flask_restx import Namespace, Resource, fields

from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.Models.index_dto import ChunkIndexDTO

ns = Namespace('seed', description='Seed data into Elasticsearch for testing the search pipeline', path='/v1/seed')

@ns.route('/chunk')
class SeedChunk(Resource):
    def post(self):
        # Hardcode sample chunk (Enterprise pattern: deterministic seed for health testing)
        text = "This is a sample clause about termination and notice period for 30 days"

        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        vec = embedder.embed_text(text)

        # wrap in DTO
        dto = ChunkIndexDTO(
            tenant="demo",
            scope="corpus",
            doc_id=str(uuid.uuid4()),
            chunk_id="c1",
            source="seed",
            created_at=ChunkIndexDTO.now_iso(),
            chunk_text=text,
            embedding=vec,
        )

        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)
        es_doc_id = index.upsert_chunk(dto)

        return {"status": "ok", "es_doc_id": es_doc_id, "doc_id": dto.doc_id, "chunk_id": dto.chunk_id}