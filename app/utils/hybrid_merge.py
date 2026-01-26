from typing import Dict, Any, List

def merge_results(bm25: List[Dict[str, Any]], vec: List[Dict[str, Any]], w_bm25: float = 0.5, w_vec: float = 0.5, top_k: int = 8):
    # normalize scores by max to reduce scale differences
    def norm(items):
        if not items:
            return {}
        mx = max(i["score"] for i in items) or 1.0
        return {i["es_id"]: i["score"] / mx for i in items}

    nb = norm(bm25)
    nv = norm(vec)

    merged: Dict[str, Dict[str, Any]] = {}

    # union of ids
    for r in bm25:
        merged[r["es_id"]] = {"es_id": r["es_id"], "source": r["source"], "bm25": r["score"], "vec": 0.0}
    for r in vec:
        if r["es_id"] not in merged:
            merged[r["es_id"]] = {"es_id": r["es_id"], "source": r["source"], "bm25": 0.0, "vec": r["score"]}
        else:
            merged[r["es_id"]]["vec"] = r["score"]

    # compute combined score using normalized values
    scored = []
    for es_id, item in merged.items():
        s = w_bm25 * nb.get(es_id, 0.0) + w_vec * nv.get(es_id, 0.0)
        item["hybrid_score"] = s
        scored.append(item)

    scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return scored[:top_k]
