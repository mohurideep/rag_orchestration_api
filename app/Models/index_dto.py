from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class ChunkIndexDTO:
    tenant : str
    scope : str
    doc_id : str
    chunk_id : str
    source : str
    created_at: str
    chunk_text: str
    embedding: List[float]

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def to_es_doc(self) -> Dict[str, Any]:
        return {
            "tenant": self.tenant,
            "scope": self.scope,
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "source": self.source,
            "created_at": self.created_at,
            "chunk_text": self.chunk_text,
            "embedding": self.embedding,
        }