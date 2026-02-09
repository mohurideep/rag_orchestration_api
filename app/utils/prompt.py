from typing import Any, Dict, List

def build_grounded_prompt(user_query: str, contexts: List[Dict[str, Any]]) -> str:
    
    """
    contexts item is from merged retrieval result:
    { es_id, source: {source, doc_id, chunk_id, chunk_text, ...}, ... }
    """
    citation_blocks= []
    for i, item in enumerate(contexts, start=1):
        src = item["source"]
        citation_blocks.append(
            f"[{i}] source= {src.get('source')} doc_id= {src.get('doc_id')} chunk_id= {src.get('chunk_id')} chunk_text= {src['chunk_text']}"
        )

    context_text = "\n\n".join(citation_blocks)

    return (
        "You are a careful assistant. Answer ONLY using the provided context.\n"
        "If the answer is not in the context, say you don't know and do not cite.\n"
        "Only cite when you actually used that chunk. Cite sources using [1], [2], etc.\n\n"
        f"User question:\n{user_query}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:\n"
    )

def build_doc_summary_prompt(doc_text: str) -> str:
    return (
        "You are a careful assistant. \n"
        "Task: Write a summary of the Full document. \n"
        "Rules:\n"
        "- Use ONLY the provided document text.\n"
        "- Do not invent facts.\n"
        "- Output format:\n"
        "  1) Executive summary (4-6 lines)\n"
        "  2) Key bullets (8-12 bullets)\n\n"
        f"Document Text:\n{doc_text}\n\n"
        "Summary:\n"
    )

def build_query_guided_summary_prompt(user_query: str, context: List[Dict[str, Any]]) -> str:
    citation_blocks = []
    for i, item in enumerate(context, start=1):
        src = item["source"]
        citation_blocks.append(
            f"[{i}] source= {src.get('source')} doc_id= {src.get('doc_id')}"
            f"chunk_id= {src.get('chunk_id')} chunk_text= {src['chunk_text']}"
        )
    context_text = "\n\n".join(citation_blocks)

    return (
        "You are a careful assistant.\n"
        "Task: Write a summary according to the user's instruction.\n"
        "Rules:\n"
        "- Use ONLY the provided context.\n"
        "- If the requested summary cannot be produced from the context, say you don't know.\n"
        "- Cite sources using [1], [2], etc.\n\n"
        f"User instruction:\n{user_query}\n\n"
        f"Context:\n{context_text}\n\n"
        "Summary:\n"
    )
