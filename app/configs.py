import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    env: str
    es_url: str
    bedrock_model_id: str
    embed_model_name: str
    index_chunks: str
    index_docs: str
    embedding_dim: int
    local_storage_dir: str
    s3_bucket: str
    aws_region: str
    groq_api_key: str
    groq_model: str
    max_request_bytes: int
    max_files_per_request: int
    max_total_upload_bytes: int
    max_single_file_bytes: int
    tenant_daily_upload_bytes: int
    tenant_daily_upload_files: int
    summary_max_chars: int
    summary_batch_size: int
    metadata_registry_path : str

def load_config() -> AppConfig:
    return AppConfig(
        env=os.getenv("APP_ENV", "local"),
        es_url=os.getenv("ES_URL", "http://localhost:9200"),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", ""),
        embed_model_name=os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"),
        index_chunks=os.getenv("ES_INDEX_CHUNKS", "rag_chunks"),
        index_docs=os.getenv("ES_INDEX_DOCS", "rag_documents"),
        embedding_dim=int(os.getenv("ES_EMBEDDING_DIM", 384)),
        local_storage_dir=os.getenv("LOCAL_STORAGE_DIR", "/data"),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        aws_region=os.getenv("AWS_REGION", "ap-southeast-2"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", ""),
        max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", 26214400)),
        max_files_per_request=int(os.getenv("MAX_FILES_PER_REQUEST", 10)),
        max_total_upload_bytes=int(os.getenv("MAX_TOTAL_UPLOAD_BYTES", 209715200)),
        max_single_file_bytes=int(os.getenv("MAX_SINGLE_FILE_BYTES", 10485760)),
        tenant_daily_upload_bytes=int(os.getenv("TENANT_DAILY_UPLOAD_BYTES", 104857600)),
        tenant_daily_upload_files=int(os.getenv("TENANT_DAILY_UPLOAD_FILES", 200)),
        summary_max_chars=int(os.getenv("SUMMARY_MAX_CHARS", 12000)),
        summary_batch_size=int(os.getenv("SUMMARY_BATCH_SIZE", 5)),
        metadata_registry_path=os.getenv("METADATA_REGISTRY_PATH", f"{os.getenv('LOCAL_STORAGE_DIR', '/data')}/metadata_registry.json"),
    )