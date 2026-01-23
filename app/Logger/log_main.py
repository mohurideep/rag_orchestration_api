import json
import logging
import logging.handlers
import sys
from datetime import datetime,timezone

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage()
        }
        #attach structure extra if present
        for key in ("request_id", "path", "method", "status_code", "latency_ms", "error_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
    
def get_logger() -> logging.Logger:
    logger = logging.getLogger("rag_orchestration_api")
    logger.setLevel(logging.INFO)
    
    logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    logger.propagate = False
    return logger