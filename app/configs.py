import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    env: str
    es_url: str
    aws_region: str
    s3_bucket: str
    bedrock_model_id: str
    embed_model_name: str

def load_config() -> AppConfig:
    return AppConfig(
        env=os.getenv("APP_ENV", "local"),
        es_url=os.getenv("ES_URL", "http://localhost:9200"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", ""),
        embed_model_name=os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    )