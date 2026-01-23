from flask import g
from flask_restx import Resource, Namespace
from elasticsearch import Elasticsearch


from app.providers.SearchProvider.es_client import ESClient
from app.utils.errors import UpstreamError

ns = Namespace("health", description="Health Check")

@ns.route("/")
@ns.route("")
class Health(Resource):
    def get(self):
        """Health check endpoint"""
        return {"status": "ok"}

@ns.route("/es")
@ns.route("/es/")
class HealthES(Resource):
    def get(self):
        """Health check for Elasticsearch."""
        es = ESClient(g.cfg.es_url)
        if not es.ping():
            raise UpstreamError("ES_UNAVAILABLE", "Elasticsearch is not reachable", 503)
        return {"status": "ok", "es": "reachable"}

@ns.route("/index")
class HealthIndex(Resource):
    def get(self):
        """Health check for Elasticsearch index."""
        es = Elasticsearch(g.cfg.es_url)
        exist = bool(es.indices.exists(index=g.cfg.index_chunks))
        if not exist:
            raise UpstreamError("ES_INDEX_MISSING", f"Elasticsearch index '{g.cfg.index_chunks}' does not exist", 503)
        return {"status": "ok", "index": g.cfg.index_chunks, "es_index": "exists"}