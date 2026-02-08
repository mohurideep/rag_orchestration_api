from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.utils.errors import ValidationError
from app.utils.hybrid_merge import merge_results

from app.Logger.log_main import get_logger

ns = Namespace("retrieve", description="Hybrid retrieval (BM25 + vector)")
logger = get_logger()

@ns.route("/")
class Retrieve(Resource):
    def post(self):
        
        print("DEBUG raw body:", request.get_data(as_text=True))
        print("DEBUG json:", request.get_json(silent=True))
        print("DEBUG content-type:", request.content_type)


        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 8)
        tenant = payload.get("tenant") or "demo"
        logger.info("debug_retrieve_payload", extra={"content_type": request.content_type, "raw": request.get_data(as_text=True)})
        if not query:
            raise ValidationError("MISSING_QUERY", "Request must include non-empty 'query'", 400)

        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(query)

        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        bm25 = index.bm25_search(tenant=tenant, query=query, top_k=top_k)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k)

        merged = merge_results(bm25, vec, w_bm25=0.5, w_vec=0.5, top_k=top_k)

        return {
            "status": "success",
            "query": query,
            "top_k": top_k,
            "tenant": tenant,
            "results": merged,
        }
