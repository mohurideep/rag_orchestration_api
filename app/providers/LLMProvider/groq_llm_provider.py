import time
from groq import Groq

from app.utils.errors import UpstreamError

class GroqLLMProvider:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise UpstreamError("GROQ_KEY_NOT_SET", "GROQ_API_KEY is not configured", 500)
        if not model:
            raise UpstreamError("GROQ_MODEL_NOT_SET", "GROQ_MODEL is not configured", 500)
        
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 400, temperature: float = 0.2, top_p: float = 1.0) -> dict:
        """
        Returns: {"text": "generated text", "latency_ms": int}
        """

        start = time.time()

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False
            )

            #open-ai style respone
            text = completion.choices[0].message.content or ""
            latency_ms = int((time.time() - start) * 1000)
            return {"text": text, "latency_ms": latency_ms}
        except Exception as e:
            raise UpstreamError("GROQ_API_ERROR", f"Error communicating with Groq API: {str(e)}", 500)