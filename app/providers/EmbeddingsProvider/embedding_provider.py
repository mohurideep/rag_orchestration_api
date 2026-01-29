from sentence_transformers  import SentenceTransformer

_MODEL = None
_MODEL_NAME = None

class LocalEmbeddingProvider:
    def __init__(self, model_name: str):
        global _MODEL, _MODEL_NAME
        if _MODEL is None or _MODEL_NAME != model_name:
            _MODEL = SentenceTransformer(model_name)
            _MODEL_NAME = model_name
        self.model = _MODEL


    def embed_text(self, text: str) -> list[float]:
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return vec.astype(float).tolist()
