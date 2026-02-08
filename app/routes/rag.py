import time
import re
from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.utils.hybrid_merge import merge_results
from app.utils.prompt import build_grounded_prompt
from app.providers.LLMProvider.groq_llm_provider import GroqLLMProvider
from app.utils.errors import ValidationError

ns = Namespace("rag", description="RAG orchestration", path="/v1/rag")

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
        t1 = time.time()
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(query)
        t_embed = int((time.time() - t1) * 1000)

        # Retrieval
        t2 = time.time()
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        bm25 = index.bm25_search(tenant=tenant, query=query, top_k=top_k)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k)
        merged = merge_results(bm25, vec, w_bm25=0.5, w_vec=0.5, top_k=top_k)
        t_retrieve = int((time.time() - t2) * 1000)

        # Prompt
        prompt = build_grounded_prompt(query, merged)

        # LLM (Bedrock)
        # llm = BedrockLLMProvider(g.cfg.aws_region, g.cfg.bedrock_model_id)
        # llm_resp = llm.generate(prompt, max_tokens=500, temperature=0.2)

        #LLM (Groq)
        llm = GroqLLMProvider(g.cfg.groq_api_key, g.cfg.groq_model)
        llm_resp = llm.generate(prompt, max_tokens=500, temperature=0.2)
        answer = llm_resp["text"]

        #build citation list
        all_citations = [
            {
                "ref": i + 1,
                "es_id": item["es_id"],
                "source": item["source"].get("source"),
                "doc_id": item["source"].get("doc_id"),
                "chunk_id": item["source"].get("chunk_id"),
            }
            for i, item in enumerate(merged)
        ]

        used_refs = extract_used_refs(answer)
        used_citations = [cite for cite in all_citations if cite["ref"] in used_refs]

        return {
            "status": "success",
            "query": query,
            "tenant": tenant,
            "answer": llm_resp["text"],
            "citations_used": used_citations,
            "retrieved_context": all_citations,
            "timings_ms": {
                "embed": t_embed,
                "retrieve": t_retrieve,
                "llm": llm_resp["latency_ms"],
                "total": int((time.time() - t0) * 1000),
            },
        }

def extract_used_refs(answer: str) -> set[int]:
    #finds [1][2] in the answer text
    refs = set()
    for match in re.findall(r'\[(\d+)\]', answer or ""):
        try:
            refs.add(int(match))
        except ValueError:
            pass
    return refs