import uuid
from flask import g, request
from flask_restx import Namespace, Resource, fields

from app.providers.StorageProvider.local_provider import LocalStorageProvider
from app.utils.registry import Registry
from app.utils.errors import ValidationError

ns = Namespace("documents", description="Document upload & metadata")

@ns.route("")
class UploadDocument(Resource):
    def post(self):
        if "file" not in request.files:
            raise ValidationError("MISSING__FILE", "upload must include multipart field 'file'", 400)

        f = request.files["file"]
        if not f.filename:
            raise ValidationError("MISSING__FILENAME", "uploaded file must have a filename", 400)
        
        content = f.read()
        if not content:
            raise ValidationError("EMPTY__FILE", "uploaded file is empty", 400)
        
        doc_id = str(uuid.uuid4())
        storage = LocalStorageProvider(g.cfg.local_storage_dir)
        saved_path = storage.save(doc_id, f.filename, content)

        reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")
        reg.put(doc_id, {"doc_id": doc_id, "filename": f.filename, "path": saved_path})

        return {"status": "success", "doc_id": doc_id, "filename": f.filename}, 201