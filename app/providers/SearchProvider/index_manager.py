from elasticsearch import Elasticsearch

class IndexManager:
    def __init__(self, client: Elasticsearch, index_name: str, embedding_dim: int):
        self.client = client
        self.index_name = index_name
        self.embedding_dim = embedding_dim

    
    def ensure_chunks_index(self) -> None:
        if self.client.indices.exists(index=self.index_name):
            return
        
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            },
            "mappings": {
                "properties": {
                    "tenant": {
                        "type": "keyword"
                    },
                    "scope": {
                        "type": "keyword"
                    },
                    "doc_id": {
                        "type": "keyword"
                    },
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "source": {
                        "type": "keyword"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "chunk_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim
                    }
                }
            }
        }

        self.client.indices.create(index=self.index_name, body=mapping)