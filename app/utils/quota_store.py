import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

class QuotaStore:
    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text(json.dumps({}))

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    def get(self, tenant: str) -> Dict[str, Any]:
        data = json.loads(self.path.read_text())
        return data.get(tenant, {})
    
    def check_and_consume(self, tenant: str, add_files: int, add_bytes: int, max_files: int, max_bytes: int) -> Dict[str, Any]:
        data = json.loads(self.path.read_text())
        today = self._today()

        t = data.get(tenant, {})
        if t.get("date") != today:
            t = {"date": today, "files_used": 0, "bytes_used": 0}

        new_files = t["files_used"] + add_files
        new_bytes = t["bytes_used"] + add_bytes

        if new_files > max_files:
            return {"allowed": False, "reason": "FILE_QUOTA_EXCEEDED", "limit": max_files, "current": t["files_used"], "attempted": add_files}
        
        if new_bytes > max_bytes:
            return {"allowed": False, "reason": "BYTE_QUOTA_EXCEEDED", "limit": max_bytes, "current": t["bytes_used"], "attempted": add_bytes}
        
        # consume
        t["files_used"] = new_files
        t["bytes_used"] = new_bytes
        data[tenant] = t
        self.path.write_text(json.dumps(data))
        return {"allowed": True, "date": today, "files_used": new_files, "bytes_used": new_bytes}