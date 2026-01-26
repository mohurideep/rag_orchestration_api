from typing import List, Dict, Any

from elasticsearch import Elasticsearch
from app.Models.index_dto import ChunkIndexDTO

class ChunkIndex:
    def __init__(self, client: Elasticsearch, index_name: str):
        self.client = client
        self.index_name = index_name
        
    def upsert_chunk(self, dto: ChunkIndexDTO) -> str:
        doc_id = f"{dto.tenant}:{dto.doc_id}:{dto.chunk_id}"
        self.client.index(
            index=self.index_name,
            id=doc_id,
            document=dto.to_es_doc(),
            refresh=True
        )
        return doc_id
    
    def get_chunk(self, es_doc_id: str) -> dict:
        response = self.client.get(
            index=self.index_name,
            id=es_doc_id
        )
        return response['_source']
    
    def bm25_search(self, tenant :str, query : str, top_k: int= 8) -> List[Dict[str, Any]]:
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "filter": [{"term": {"tenant": tenant}}],
                    "must": [{"match": {"text": {"query": query}}}]
                }
            },
            "_source": {
                "excludes": ["embedding"]
            }
        }
        res = self.client.search( index=self.index_name, body=body)
        
        return [
            {
                "es_id": hit['_id'],
                "score": hit['_score'],
                "source": hit['_source']
            }
            for hit in res['hits']['hits']
        ]

    def vector_search(self, tenant: str, query_vec: List[float], top_k: int = 8) -> List[Dict[str, Any]]:
        body = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "filter": [{"term": {"tenant": tenant}}],
                        }
                    },
                    "script": {
                        "source": "cosineSimilarity(params.q, 'embedding') + 1.0",
                        "params": {"q": query_vec}
                    },
                }
            },
            "_source": {
                "excludes": ["embedding"]
            }
        }
        res = self.client.search(index=self.index_name, body=body)

        return [
            {
                "es_id": hit['_id'],
                "score": hit['_score'],
                "source": hit['_source']
            }
            for hit in res['hits']['hits']
        ]
