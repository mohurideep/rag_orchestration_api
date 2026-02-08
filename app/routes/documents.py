import uuid
from flask import g, request
from flask_restx import Namespace, Resource

from app.providers.StorageProvider.s3_provider import S3StorageProvider
from app.utils.registry import Registry
from app.utils.errors import ValidationError
from app.utils.quota_store import QuotaStore
from app.utils.size_fmt import bytes_to_mb

ns = Namespace("documents", description="Document upload & metadata", path="/v1/documents")

@ns.route("/")
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
        if len(files) > g.cfg.max_files_per_request:
            raise ValidationError("TOO_MANY_FILES", f"Upload must include at most {g.cfg.max_files_per_request} files", 400)

        # 4) validate and stage in memory
        total_bytes = 0
        pending = [] # list[(filename, content)]

        for f in files:
            if not f.filename:
                raise ValidationError("MISSING_FILENAME", "Uploaded file must have a filename", 400)
            
            content = f.read()
            size = len(content)
            size_to_mb = bytes_to_mb(size)
            max_size_to_mb = bytes_to_mb(g.cfg.max_single_file_bytes)
            if not content:
                raise ValidationError("EMPTY_FILE", "Uploaded file is empty", 400)

            if size > g.cfg.max_single_file_bytes:
                raise ValidationError("FILE_TOO_LARGE", f"Uploaded file {f.filename} is {size_to_mb} MB, must be at most {max_size_to_mb} MB.", 413)

            total_bytes += size
            if total_bytes > g.cfg.max_total_upload_bytes:
                raise ValidationError("UPLOAD_TOO_LARGE", f"Total upload size is {bytes_to_mb(total_bytes)} MB, must be at most {bytes_to_mb(g.cfg.max_total_upload_bytes)} MB", 413)

            pending.append((f.filename, content))

        # 5) per tenant quota check
        quota = QuotaStore(f"{g.cfg.local_storage_dir}/quota_store.json")
        decision = quota.check_and_consume(
            tenant=tenant,
            add_files=len(pending),
            add_bytes=total_bytes,
            max_files=g.cfg.tenant_daily_upload_files,
            max_bytes=g.cfg.tenant_daily_upload_bytes,
        )

        if not decision["allowed"]:
            raise ValidationError(decision["reason"], f"Tenant upload quota exceeded: {decision}", 429)

        # 6) upload and registry writes
        s3 = S3StorageProvider(g.cfg.s3_bucket, g.cfg.aws_region)
        reg = Registry(f"{g.cfg.local_storage_dir}/registry.json")

        
        uploaded = []
        for filename, content in pending:
            doc_id = str(uuid.uuid4())
            key = f"raw/{tenant}/{doc_id}/{filename}"

            s3.save(key, content)
            reg.put(doc_id, {"doc_id": doc_id, "filename": filename, "s3_key": key, "tenant": tenant})

            uploaded.append({"doc_id": doc_id, "filename": filename, "s3_key": key, "tenant": tenant})

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

        return {
            "status": "success",
            "tenant": tenant,
            "uploaded_files": uploaded,
            "limits": {
                "max_files_per_request": g.cfg.max_files_per_request,
                "max_total_upload_bytes": g.cfg.max_total_upload_bytes,
                "max_single_file_bytes": g.cfg.max_single_file_bytes,
                "tenant_daily_upload_files": g.cfg.tenant_daily_upload_files,
                "tenant_daily_upload_bytes": g.cfg.tenant_daily_upload_bytes
            },
            "quota_after": {
                "date": decision.get("date"),
                "files": decision.get("files_used"),
                "bytes": decision.get("bytes_used")
            }
        }, 201