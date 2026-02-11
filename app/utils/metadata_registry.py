import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

ALLOWED_TYPES = {"string", "number", "boolean", "date"}

class MetadataRegistry:
    """
    stores metadata field definitions ( schema registry) for meta_kv / meta_typed fields.
    This  does not change ES mapping.
    """
    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text(json.dumps({"fields": {}}))

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text())
    
    def _write(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def list_fields(self) -> List[Dict[str, Any]]:
        data = self._read()
        fields = data.get("fields", {})
        return [{"key": k, **v} for k, v in fields.items()]

    def get_field(self, key: str) -> Dict[str, Any]:
        data = self._read()
        return data.get("fields", {}).get(key, {})
    
    def register_field(self, key: str, field_type: str, description: str = "", indexed: bool = True) -> Dict[str, Any]:
        key = (key or "").strip()
        field_type = (field_type or "").strip().lower()

        if not key:
            raise ValueError("Field key cannot be empty.")
        if " " in key:
            raise ValueError("Field key cannot contain spaces.")
        if field_type not in ALLOWED_TYPES:
            raise ValueError(f"Field type must be one of: {ALLOWED_TYPES}")
        
        data = self._read()
        fields = data.setdefault("fields", {})

        now = datetime.now(timezone.utc).isoformat()
        existing = fields.get(key)

        fields[key] = {
            "type": field_type,
            "description": description or (existing or {}).get("description", ""),
            "indexed": bool(indexed),
            "created_at": (existing or {}).get("created_at", now),
            "updated_at": now,
        }

        self._write(data)
        return {"key": key, **fields[key]}