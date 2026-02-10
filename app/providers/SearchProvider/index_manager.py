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
                    "tenant": {"type": "keyword"},
                    "scope": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "chunk_text": {"type": "text", "analyzer": "standard"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine",
                        "index_options": {"type": "int8_hnsw", "m": 16, "ef_construction": 100},
                    },
                }
            },
        }

        self.client.indices.create(index=self.index_name, body=mapping)

    # Document index for metadata + doc_level vector search
    def ensure_doc_index(self, doc_index_name: str) -> None:
        if self.client.indices.exists(index=doc_index_name):
            return
        
        mapping = {
            "settings": {
                "index": {"number_of_shards": 1, "number_of_replicas": 0}
                },
                "mapping": {
                    "properties": {
                        "tenant": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "filename": {"type": "keyword"},
                        "s3_key": {"type": "keyword"},
                        "created_at": {"type": "date"},

                        # Typed metadata
                        "meta_typed": {
                            "properties": {
                                "has_payment_terms": {"type": "boolean"},
                                "effective_date": {"type": "date"},
                                "expiration_date": {"type": "date"},
                                "payment_days": {"type": "integer"},
                                "currency": {"type": "keyword"},
                            }
                        },
                        # ✅ Flexible metadata bag (new keys tomorrow without schema churn)
                        "meta_kv": {
                            "type": "nested",
                            "properties": {
                                "k": {"type": "keyword"},
                                "v_str": {"type": "keyword"},
                                "v_num": {"type": "double"},
                                "v_date": {"type": "date"},
                                "v_bool": {"type": "boolean"},
                            },
                        },
                        "doc_embedding": {
                            "type": "dense_vector",
                            "dims": self.embedding_dim,
                            "index": True,
                            "similarity": "cosine",
                            "index_options": {"type": "int8_hnsw", "m": 16, "ef_construction": 100},
                        },
                        #optional
                        "doc_text_preview": {"type": "text", "analyzer": "standard"},
                    }
                },
            }
        self.client.indices.create(index=doc_index_name, body=mapping)