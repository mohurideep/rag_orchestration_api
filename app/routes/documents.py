import uuid
from flask import g, request
from flask_restx import Namespace, Resource, fields

# from app.providers.StorageProvider.local_provider import LocalStorageProvider
from app.providers.StorageProvider.s3_provider import S3StorageProvider
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

        #for now: hardcoded tenant (Later: take from auth/header)
        tenant = "demo"

        #build deterministic S3 object key
        key = f"raw/{tenant}/{doc_id}/{f.filename}"

        #upload to s3
        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        s3.save(key, content)

        # storage = LocalStorageProvider(g.cfg.local_storage_dir)
        # saved_path = storage.save(doc_id, f.filename, content)

        reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")
        reg.put(doc_id, {"doc_id": doc_id, "filename": f.filename, "s3_key": key, "tenant": tenant})

        return {"status": "success", "doc_id": doc_id, "filename": f.filename, "s3_key": key, "tenant": tenant}, 201