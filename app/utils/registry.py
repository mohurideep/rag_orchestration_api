#temporary json storage for the documents with metadata

import json
from pathlib import Path
from typing import Dict, Any

class Registry:
    def __init__(self, registry_path: str):
        self.path = Path(registry_path)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def put(self, doc_id: str, record: Dict[str, Any]) -> None:
        #store metadata for this document id
        data = json.loads(self.path.read_text())
        data[doc_id] = record #idempotent operation for data
        self.path.write_text(json.dumps(data))

    def get(self, doc_id: str) -> Dict[str, Any]:
        #reading metadata for this document id
        data = json.loads(self.path.read_text())
        return data.get(doc_id, {})