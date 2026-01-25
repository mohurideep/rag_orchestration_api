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