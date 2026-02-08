from flask import g
from flask_restx import Namespace, Resource


from app.providers.SearchProvider.es_client import ESClient
from app.providers.SearchProvider.similarity_index import ChunkIndex
from app.utils.errors import NotFoundError

ns = Namespace('chunks', description='Chunk debug endpoints', path='/v1/chunks')

@ns.route('/<string:es_doc_id>')
class GetChunk(Resource):
    def get(self, es_doc_id: str):
        es = ESClient(g.cfg.es_url)
        index = ChunkIndex(es.client, g.cfg.index_chunks)
        try:
            src = index.get_chunk(es_doc_id)
        except Exception:
            raise NotFoundError("CHUNK_NOT_FOUND", f"Chunk {es_doc_id} not found", 404)
        return {"es_doc_id": es_doc_id, "chunk": src}