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
    embedding_dim: int
    local_storage_dir: str
    s3_bucket: str
    aws_region: str
    groq_api_key: str
    groq_model: str

def load_config() -> AppConfig:
    return AppConfig(
        env=os.getenv("APP_ENV", "local"),
        es_url=os.getenv("ES_URL", "http://localhost:9200"),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", ""),
        embed_model_name=os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"),
        index_chunks=os.getenv("ES_INDEX_CHUNKS", "rag_chunks"),
        embedding_dim=int(os.getenv("ES_EMBEDDING_DIM", 384)),
        local_storage_dir=os.getenv("LOCAL_STORAGE_DIR", "/data"),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        aws_region=os.getenv("AWS_REGION", "ap-southeast-2"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", ""),
    )