from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.utils.errors import ValidationError

ns = Namespace("retrieve_debug", description="Debug retrieval components")

@ns.route("/bm25")
class DebugBM25(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 8)
        tenant = payload.get("tenant") or "demo"
        if not query:
            raise ValidationError("MISSING_QUERY", "query required", 400)

        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)
        bm25 = index.bm25_search(tenant=tenant, query=query, top_k=top_k)
        return {"status": "success", "tenant": tenant, "query": query, "bm25": bm25}

@ns.route("/vector")
class DebugVector(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 8)
        tenant = payload.get("tenant") or "demo"
        if not query:
            raise ValidationError("MISSING_QUERY", "query required", 400)

        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(query)

        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k)
        return {"status": "success", "tenant": tenant, "query": query, "vector": vec}
