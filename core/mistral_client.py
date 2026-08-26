"""
Wrapper autour de l'API Mistral (La Plateforme), utilisé comme repli quand
Gemini est en surcharge (503) ou timeout — même signature que GeminiClient
pour un remplacement transparent dans le pipeline.
"""

import os
import httpx
from typing import Optional

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
BASE_URL = "https://api.mistral.ai/v1/chat/completions"

MODEL_MISTRAL_SMALL = "mistral-small-4"
MODEL_MISTRAL_MEDIUM = "mistral-medium-3.5"


class MistralClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key or MISTRAL_API_KEY
        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY manquant dans l'environnement")
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        model: str = MODEL_MISTRAL_SMALL,
        temperature: float = 0.9,
        max_output_tokens: int = 4096,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(BASE_URL, headers=headers, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Mistral API error {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Réponse Mistral inattendue: {data}")
