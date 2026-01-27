import json
import time
import boto3
from app.utils.errors import UpstreamError


class BedrockLLMProvider:
    def __init__(self, region: str, model_id: str):
        if not model_id:
            raise UpstreamError("BEDROCK_MODEL_NOT_SET", "BEDROCK_Model_ID is not configured", 500)
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.2, top_p: float = 0.9) -> dict:
        """
        Returns: {"text": "....", latency_ms": int}
        
        """

        start = time.time()

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }

        try:
            resp = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(resp["body"].read())

            text = data["content"][0]["text"]
            latency_ms = int((time.time() - start) * 1000)
            return {"text": text, "latency_ms": latency_ms}


        except Exception as e:
            raise UpstreamError("BEDROCK_INVOKE_FAILED",f"Bedrock converse failed: {e}", 502)