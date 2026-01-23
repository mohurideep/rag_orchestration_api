from elasticsearch import Elasticsearch
from app.Logger.log_main import get_logger

logger = get_logger()

class ESClient:
    def __init__(self, es_url : str):
        self.client = Elasticsearch(es_url)
    
    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception as e:
            logger.warning("Elasticsearch ping failed", extra={"error": str(e)})
            return False