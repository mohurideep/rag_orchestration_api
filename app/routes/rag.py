import time
from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.utils.hybrid_merge import merge_results
from app.utils.prompt import build_grounded_prompt
from app.providers.LLMProvider.bedrock_llm_provider import BedrockLLMProvider
from app.providers.LLMProvider.groq_llm_provider import GroqLLMProvider
from app.utils.errors import ValidationError

ns = Namespace("rag", description="RAG orchestration")

@ns.route("/query")
class RagQuery(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 5)
        tenant = payload.get("tenant") or "demo"

        if not query:
            raise ValidationError("MISSING_QUERY", "Request must include non-empty 'query'", 400)

        t0 = time.time()

        # Embedding (query)
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(query)
        t_embed = int((time.time() - t0) * 1000)

        # Retrieval
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        bm25 = index.bm25_search(tenant=tenant, query=query, top_k=top_k)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k)
        merged = merge_results(bm25, vec, w_bm25=0.5, w_vec=0.5, top_k=top_k)
        t_retrieve = int((time.time() - t0) * 1000) - t_embed

        # Prompt
        prompt = build_grounded_prompt(query, merged)

        # LLM (Bedrock)
        # llm = BedrockLLMProvider(g.cfg.aws_region, g.cfg.bedrock_model_id)
        # llm_resp = llm.generate(prompt, max_tokens=500, temperature=0.2)

        #LLM (Groq)
        llm = GroqLLMProvider(g.cfg.groq_api_key, g.cfg.groq_model)
        llm_resp = llm.generate(prompt, max_tokens=500, temperature=0.2)

        return {
            "status": "success",
            "query": query,
            "tenant": tenant,
            "answer": llm_resp["text"],
            "citations": [
                {
                    "ref": i + 1,
                    "es_id": item["es_id"],
                    "source": item["source"].get("source"),
                    "doc_id": item["source"].get("doc_id"),
                    "chunk_id": item["source"].get("chunk_id"),
                }
                for i, item in enumerate(merged)
            ],
            "timings_ms": {
                "embed": t_embed,
                "retrieve": t_retrieve,
                "llm": llm_resp["latency_ms"],
                "total": int((time.time() - t0) * 1000),
            },
        }
