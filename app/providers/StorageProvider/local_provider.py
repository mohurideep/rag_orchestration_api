import os
from pathlib import Path

class LocalStorageProvider:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def save(self, doc_id: str, filename: str, content: bytes) -> str:
        doc_dir = self.base_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        path = doc_dir / filename
        path.write_bytes(content)
        return str(path)
    
    def read(self, path:str) -> bytes:
        return Path(path).read_bytes()

    def exists(self, path: str) -> bool:
        return Path(path).exists()