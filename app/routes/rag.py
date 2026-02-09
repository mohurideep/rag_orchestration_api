import time
import re
from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.EmbeddingsProvider.embedding_provider import LocalEmbeddingProvider
from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.providers.LLMProvider.groq_llm_provider import GroqLLMProvider
from app.providers.StorageProvider.s3_provider import S3StorageProvider
from app.providers.Chunking.chunker import chunk_text

from app.utils.hybrid_merge import merge_results
from app.utils.prompt import build_grounded_prompt , build_doc_summary_prompt, build_query_guided_summary_prompt
from app.utils.registry import Registry
from app.utils.text_extract import extract_text
from app.utils.errors import ValidationError, NotFoundError

ns = Namespace("rag", description="RAG orchestration", path="/v1/rag")

@ns.route("/query")
class RagQuery(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 5)
        tenant = (getattr(g, "tenant", "") or "").strip()  # prefer tenant from header, fallback to payload
        if not tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)

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

@ns.route("/query_doc")
class RagQueryDoc(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        doc_id = (payload.get("doc_id") or "").strip()
        top_k = int(payload.get("top_k") or 5)

        tenant = (getattr(g, "tenant", "") or "").strip()  # prefer tenant from header, fallback to payload
        if not tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)
        
        if not query:
            raise ValidationError("MISSING_QUERY", "Request must include non-empty 'query'", 400)

        if not doc_id:
            raise ValidationError("MISSING_DOC_ID", "Request must include non-empty 'doc_id'", 400)
        
        t0 = time.time()

        # Embed Query
        t1 = time.time()
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(query)
        t_embed = int((time.time() - t1) * 1000)

        # Retreive ( filter by Doc_id)
        t2 = time.time()
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        bm25 = index.bm25_search(tenant=tenant, query=query, top_k=top_k, doc_id=doc_id)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k, doc_id=doc_id)
        merged = merge_results(bm25, vec, w_bm25=0.5, w_vec=0.5, top_k=top_k)
        t_retrieve = int((time.time() - t2) * 1000)

        if not merged:
            return {
                "status": "success",
                "query": query,
                "doc_id": doc_id,
                "tenant": tenant,
                "answer": "I don't Know",
                "citations_used": [],
                "retrieved_context": [],
                "timings_ms": {
                    "embed": t_embed,
                    "retrieve": t_retrieve,
                    "llm": 0,
                    "total": int((time.time() - t0) * 1000),
                },
            }, 200

        # Prompt + LLM
        prompt = build_grounded_prompt(user_query=query, contexts=merged)
        llm = GroqLLMProvider(g.cfg.groq_api_key, g.cfg.groq_model)
        llm_resp = llm.generate(prompt, max_tokens=500, temperature=0.2)
        answer = llm_resp["text"]

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
            "doc_id": doc_id,
            "tenant": tenant,
            "answer": answer,
            "citations_used": used_citations,
            "retrieved_context": all_citations,
            "timings_ms": {
                "embed": t_embed,
                "retrieve": t_retrieve,
                "llm": llm_resp["latency_ms"],
                "total": int((time.time() - t0) * 1000),
            },
        }, 200

@ns.route("/summary")
class RagSummary(Resource):
    def post(self):
        payload = request.get_json(silent=True) or {}

        doc_id = (payload.get("doc_id") or "").strip()
        user_query = (payload.get("query") or "").strip()  # optional query for query-guided summary

        tenant = (getattr(g, "tenant", "") or "").strip()  # prefer tenant from header, fallback to payload
        if not tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)
        
        if not doc_id:
            raise ValidationError("MISSING_DOC_ID", "Request must include non-empty 'doc_id'", 400)
        
        t0 = time.time()

        # 1) Load doc metadata ( tenant isolation)
        reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")
        record = reg.get(doc_id)
        if not record or record.get("tenant") != tenant:
            raise NotFoundError("DOCUMENT_NOT_FOUND", f"Document with id '{doc_id}' not found for this tenant", 404)
        
        # 2) Read file from S3 + extract text
        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        content = s3.read(record["s3_key"])
        filename = record["filename"]

        text = extract_text(filename, content)
        if not text.strip():
            raise ValidationError("EMPTY_TEXT", f"No extractable text found in document '{doc_id}'", 404)
        
        llm = GroqLLMProvider(g.cfg.groq_api_key, g.cfg.groq_model)

        # ======================
        # MODE A: Default summary (entire doc)
        # ======================
        if not user_query:
            max_chars = int(getattr(g.cfg, "summary_max_chars", 12000))
            batch_size = int(getattr(g.cfg, "summary_batch_size", 5))

            # if doc text small -> single prompt
            if len(text) <= max_chars:
                prompt = build_doc_summary_prompt(text)
                llm_resp = llm.generate(prompt, max_tokens=800, temperature=0.2)
                return {
                    "status": "success",
                    "tenant": tenant,
                    "doc_id": doc_id,
                    "mode": "default full document",
                    "summary" : llm_resp["text"],
                    "timing_ms": {
                        "llm": llm_resp["latency_ms"],
                        "total": int((time.time() - t0) * 1000),
                    }
                }, 200
            # if doc text large -> summarize all chunks , then summarize combined summaries
            chunks = chunk_text(text)
            if not chunks:
                raise ValidationError("EMPTY_CHUNKS", f"Failed to chunk document '{doc_id}' for summarization", 400)
            
            partials = []
            llm_total = 0
            #summarize chunks in batches
            for i in range(0, len(chunks), batch_size):
                batch = "\n\n".join(chunks[i:i+batch_size])
                prompt = build_doc_summary_prompt(batch)
                resp = llm.generate(prompt, max_tokens=600, temperature=0.2)
                llm_total += resp["latency_ms"]
                partials.append(resp["text"])

            # 3) Combine partial summaries
            if not partials:
                raise ValidationError("EMPTY_PARTIALS", f"Failed to generate partial summaries for document '{doc_id}'", 400)

            combined = "\n\n".join(partials)
            final_prompt = (
                    "You are a careful assistant.\n"
                    "Task: Combine partial summaries into ONE final summary for the full document.\n"
                    "Rules:\n"
                    "- Do not invent facts.\n"
                    "- Output:\n"
                    "  1) Executive summary (4-6 lines)\n"
                    "  2) Key bullets (8-12 bullets)\n\n"
                    f"Partial summaries:\n{combined}\n\n"
                    "Final summary:\n"
                )
            final_resp = llm.generate(final_prompt, max_tokens=800, temperature=0.2)
            llm_total += final_resp["latency_ms"]
            return {
                "status": "success",
                "tenant": tenant,
                "doc_id": doc_id,
                "mode": "default_full_document",
                "summary": final_resp["text"],
                "timing_ms": {
                    "llm": final_resp["latency_ms"],
                    "total": int((time.time() - t0) * 1000),
                }
            }, 200

        # ======================
        # MODE B: Query-guided summary (retrieval within a single doc)
        # ======================
        top_k = int(payload.get("top_k") or 5)

        t1 = time.time()
        embedder = LocalEmbeddingProvider(g.cfg.embed_model_name)
        qvec = embedder.embed_text(user_query)
        t_embed = int((time.time() - t1) * 1000)

        t2 = time.time()
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)

        bm25 = index.bm25_search(tenant=tenant, query=user_query, top_k=top_k, doc_id=doc_id)
        vec = index.vector_search(tenant=tenant, query_vec=qvec, top_k=top_k, doc_id=doc_id)
        merged = merge_results(bm25, vec, w_bm25=0.5, w_vec=0.5, top_k=top_k)
        t_retrieve = int((time.time() - t2) * 1000)

        if not merged:
            return {
                "status": "success",
                "query": user_query,
                "doc_id": doc_id,
                "tenant": tenant,
                "answer": "I don't Know",
                "citations_used": [],
                "retrieved_context": [],
                "timings_ms": {
                    "embed": t_embed,
                    "retrieve": t_retrieve,
                    "llm": 0,
                    "total": int((time.time() - t0) * 1000),
                },
            }, 200
        
        prompt = build_query_guided_summary_prompt(user_query, merged)
        llm_resp = llm.generate(prompt, max_tokens=700, temperature=0.2)
        summary = llm_resp["text"]

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
        used_refs = extract_used_refs(summary)
        used_citations = [ref for ref in used_refs if ref <= len(all_citations)]

        return {
            "status": "success",
            "doc_id": doc_id,
            "tenant": tenant,
            "mode": "query-guided",
            "query": user_query,
            "summary": summary,
            "citations_used": used_citations,
            "retrieved_context": all_citations,
            "timings_ms": {
                "embed": t_embed,
                "retrieve": t_retrieve,
                "llm": llm_resp["latency_ms"],
                "total": int((time.time() - t0) * 1000),
            },
        }, 200

def extract_used_refs(answer: str) -> set[int]:
    #finds [1][2] in the answer text
    refs = set()
    for match in re.findall(r'\[(\d+)\]', answer or ""):
        try:
            refs.add(int(match))
        except ValueError:
            pass
    return refs