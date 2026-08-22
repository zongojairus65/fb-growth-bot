"""
Wrapper autour de l'API Gemini standard (endpoint generateContent).

Deux modèles utilisables selon le budget / la criticité de la tâche :
- "gemma-4-31b-it"   -> gratuit, bon pour les brouillons rapides et le quiz
- "gemini-3.5-flash" -> payant, meilleure qualité de rédaction FR pour les
                         prompts stratégiques (1, 2, 5, 6)

Vérifie toujours le nom exact du modèle dans Google AI Studio avant déploiement,
les noms de modèles évoluent régulièrement.
"""

import os
import httpx
from typing import Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquant dans l'environnement")
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        model: str = "gemma-4-31b-it",
        json_mode: bool = False,
        temperature: float = 0.9,
    ) -> str:
        url = f"{BASE_URL}/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Réponse Gemini inattendue: {data}")

    async def generate_json(self, prompt: str, model: str = "gemma-4-31b-it") -> dict:
        """Force une sortie JSON structurée, utile pour le diagnostic et les idées."""
        import json
        raw = await self.generate(prompt, model=model, json_mode=True, temperature=0.7)
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
