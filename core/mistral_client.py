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
        json_mode: bool = False,
    ) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(BASE_URL, headers=headers, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Mistral API error {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Réponse Mistral inattendue: {data}")

    async def generate_json(
        self, prompt: str, model: str = MODEL_MISTRAL_SMALL, max_output_tokens: int = 4096
    ) -> dict:
        """Repli JSON (objet) équivalent à GeminiClient.generate_json — utilise
        response_format=json_object (Mistral ne renvoie qu'un objet, jamais une
        liste nue, d'où l'instruction explicite dans le prompt côté appelant)."""
        import json
        raw = await self.generate(prompt, model=model, temperature=0.7, max_output_tokens=max_output_tokens, json_mode=True)
        raw = raw.strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError(f"Aucun JSON trouvé dans la réponse Mistral: {raw[:300]}")

        json_str = raw[start:end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON invalide extrait de la réponse Mistral: {e} — contenu: {json_str[:300]}")

    async def generate_json_list(
        self, prompt: str, model: str = MODEL_MISTRAL_MEDIUM, max_output_tokens: int = 8192
    ) -> list:
        """Repli JSON (liste) — Mistral en json_object mode ne peut renvoyer
        qu'un objet racine, donc on demande explicitement un objet
        {"items": [...]} dans le prompt et on déballe la clé ici."""
        import json
        raw = await self.generate(prompt, model=model, temperature=0.9, max_output_tokens=max_output_tokens, json_mode=True)
        raw = raw.strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError(f"Aucun JSON trouvé dans la réponse Mistral: {raw[:300]}")

        json_str = raw[start:end + 1]
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON invalide extrait de la réponse Mistral: {e} — contenu: {json_str[:300]}")

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, list):
                    return value
        raise RuntimeError(f"Impossible d'extraire une liste de la réponse Mistral: {json_str[:300]}")
