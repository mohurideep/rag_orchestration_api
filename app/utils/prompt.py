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
        "If the answer is not in the context, say you don't know.\n"
        "Cite sources using [1], [2], etc.\n\n"
        f"User question:\n{user_query}\n\n"
        f"Context:\n{context_text}\n\n"
        "Answer:\n"
    )