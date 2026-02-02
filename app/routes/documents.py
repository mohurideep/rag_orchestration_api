import uuid
from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.StorageProvider.s3_provider import S3StorageProvider
from app.utils.registry import Registry
from app.utils.errors import ValidationError

ns = Namespace("documents", description="Document upload & metadata")

@ns.route("")
class UploadDocument(Resource):
    def post(self):
        # 1) Tenant from header
        tenant = (getattr(g, "tenant", "") or "").strip()
        if not tenant:
            raise ValidationError("MISSING_TENANT", "Request must include 'X-Tenant-Id' header", 400)

        # 2) validate file
        # if "file" not in request.files:
        #     raise ValidationError("MISSING_FILE", "upload must include multipart field 'file'", 400)

        # f = request.files["file"]
        # if not f.filename:
        #     raise ValidationError("MISSING_FILENAME", "uploaded file must have a filename", 400)
        # 2) parse multipart
        files = request.files.getlist("file")
        if not files :
            raise ValidationError("MISSING_FILE", "Upload must include multipart field 'file'", 400)

        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")

        uploaded = []

        for f in files:
            if not f.filename:
                raise ValidationError("MISSING_FILENAME", "Uploaded file must have a filename", 400)
            
            content = f.read()
            if not content:
                raise ValidationError("EMPTY_FILE", "Uploaded file is empty", 400)
            
            doc_id = str(uuid.uuid4())
            key = f"raw/{tenant}/{doc_id}/{f.filename}"

            s3.save(key, content)
            reg.put(doc_id, {"doc_id": doc_id, "filename": f.filename, "s3_key": key, "tenant": tenant})

            uploaded.append({"doc_id": doc_id, "filename": f.filename, "s3_key": key, "tenant": tenant})

        if not uploaded:
            raise ValidationError("UPLOAD_FAILED", "No files were uploaded", 400)

        # # 3) Generate document ID and S3 key
        # doc_id = str(uuid.uuid4())

        # # #for now: hardcoded tenant (Later: take from auth/header)
        # # tenant = "demo"
        # key = f"raw/{tenant}/{doc_id}/{f.filename}"

        # # 4)upload to s3
        # s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        # s3.save(key, content)

        # # storage = LocalStorageProvider(g.cfg.local_storage_dir)
        # # saved_path = storage.save(doc_id, f.filename, content)
        # # 5) Register document metadata
        # reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")
        # reg.put(doc_id, {"doc_id": doc_id, "filename": f.filename, "s3_key": key, "tenant": tenant})

        return {"status": "success", "tenant": tenant, "uploaded_files": uploaded}, 201