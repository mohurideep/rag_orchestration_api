from sentence_transformers  import SentenceTransformer

class LocalEmbeddingProvider:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)


    def embed_text(self, text: str) -> list[float]:
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return vec.astype(float).tolist()
