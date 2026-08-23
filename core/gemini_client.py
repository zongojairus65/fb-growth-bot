"""
Wrapper autour de l'API Gemini standard (endpoint generateContent).

Modèles disponibles, du moins cher au plus capable :
- "gemma-4-31b-it"        -> gratuit ; NE PAS utiliser en mode JSON strict
                             (le modèle ajoute du texte libre malgré responseMimeType)
- "gemini-3.1-flash-lite" -> payant, low-cost ; extraction/classification simple
- "gemini-3.5-flash-lite" -> payant, low-cost ; meilleur ratio prix/perf que 3.1,
                             confirmé pour l'extraction de données JSON fiable
- "gemini-3.5-flash"      -> payant, plus cher ; rédaction créative (stratégie/hooks)

Vérifie toujours le nom exact du modèle dans Google AI Studio avant déploiement,
les noms de modèles évoluent régulièrement.
"""

import os
import httpx
from typing import Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

MODEL_GEMMA_FREE = "gemma-4-31b-it"
MODEL_FLASH_LITE_31 = "gemini-3.1-flash-lite"
MODEL_FLASH_LITE_35 = "gemini-3.5-flash-lite"
MODEL_FLASH_35 = "gemini-3.5-flash"


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY manquant dans l'environnement")
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        model: str = MODEL_FLASH_LITE_35,
        json_mode: bool = False,
        temperature: float = 0.9,
        max_output_tokens: int = 4096,
    ) -> str:
        url = f"{BASE_URL}/{model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
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

    async def generate_json(
        self, prompt: str, model: str = MODEL_FLASH_LITE_35, max_output_tokens: int = 4096
    ) -> dict:
        """Force une sortie JSON structurée (objet). Défaut sur Flash-Lite (fiable
        en JSON), PAS Gemma qui ajoute du texte de raisonnement même avec
        responseMimeType=json. Extraction robuste (première { à dernière })
        en filet de sécurité contre le texte parasite."""
        import json
        raw = await self.generate(
            prompt, model=model, json_mode=True, temperature=0.7, max_output_tokens=max_output_tokens
        )
        raw = raw.strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError(f"Aucun JSON trouvé dans la réponse Gemini: {raw[:300]}")

        json_str = raw[start:end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON invalide extrait de la réponse Gemini: {e} — contenu: {json_str[:300]}")

    async def generate_json_list(
        self, prompt: str, model: str = MODEL_FLASH_35, max_output_tokens: int = 8192
    ) -> list:
        """Variante pour une sortie JSON en LISTE (ex: 10 idées de stratégie),
        qui a besoin de plus de tokens de sortie qu'un simple objet de diagnostic."""
        import json
        raw = await self.generate(
            prompt, model=model, json_mode=True, temperature=0.9, max_output_tokens=max_output_tokens
        )
        raw = raw.strip()

        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError(f"Aucune liste JSON trouvée dans la réponse Gemini: {raw[:300]}")

        json_str = raw[start:end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON invalide extrait de la réponse Gemini: {e} — contenu: {json_str[:300]}")
