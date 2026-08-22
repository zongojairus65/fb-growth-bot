"""
Client pour le scan de profils publics via une API Facebook sur RapidAPI —
utilisé uniquement pour le DIAGNOSTIC en lecture seule, jamais pour la
publication (qui reste strictement réservée à Graph API + Page).

RapidAPI utilise un système d'authentification par headers (pas de token
dans l'URL comme Apify) : X-RapidAPI-Key + X-RapidAPI-Host.

IMPORTANT : le format exact de l'endpoint et de la réponse JSON varie selon
l'API RapidAPI précise que tu as choisie (il en existe plusieurs pour
Facebook). Adapte RAPIDAPI_HOST, RAPIDAPI_ENDPOINT et le parsing de
summarize_stats() selon la doc de TON API spécifique.
"""

import os
import httpx
from typing import Optional

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "")  # ex: "facebook-scraper3.p.rapidapi.com"
RAPIDAPI_ENDPOINT = os.getenv("RAPIDAPI_ENDPOINT", "")  # ex: "/profile/posts"


class ScraperClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or RAPIDAPI_KEY
        self.host = host or RAPIDAPI_HOST
        self.endpoint = endpoint or RAPIDAPI_ENDPOINT
        if not self.api_key or not self.host:
            raise RuntimeError("RAPIDAPI_KEY et/ou RAPIDAPI_HOST manquants dans l'environnement")
        self.timeout = timeout
        self.base_url = f"https://{self.host}"

    async def fetch_public_profile_posts(self, username: str, limit: int = 20) -> list[dict]:
        """Récupère les posts publics récents d'un profil via RapidAPI."""
        url = f"{self.base_url}{self.endpoint}"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
        }
        # Les noms de paramètres varient selon l'API RapidAPI choisie —
        # vérifie dans l'onglet "Endpoints" de ta souscription RapidAPI
        # le nom exact attendu (souvent "username", "profile_url", ou "id").
        params = {"username": username, "limit": limit}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            raise RuntimeError(f"RapidAPI error {resp.status_code}: {resp.text}")

        data = resp.json()
        # Beaucoup d'API RapidAPI renvoient soit une liste directe, soit un
        # objet avec une clé "data"/"posts" — adapte selon ta réponse réelle.
        if isinstance(data, dict):
            return data.get("data") or data.get("posts") or []
        return data

    def summarize_stats(self, posts: list[dict]) -> dict:
        """Normalise les données scrapées en un format compatible avec
        diagnostic_prompt() — adapte les noms de clés (likes/comments) selon
        ce que ton API RapidAPI renvoie exactement."""
        if not posts:
            return {"nb_posts_analyses": 0, "moyenne_likes": 0, "moyenne_commentaires": 0}

        def get_likes(p: dict) -> int:
            return p.get("likes") or p.get("reactions_count") or p.get("like_count") or 0

        def get_comments(p: dict) -> int:
            return p.get("comments") or p.get("comments_count") or 0

        total_likes = sum(get_likes(p) for p in posts)
        total_comments = sum(get_comments(p) for p in posts)
        n = len(posts)
        return {
            "nb_posts_analyses": n,
            "moyenne_likes": int(total_likes / n),
            "moyenne_commentaires": int(total_comments / n),
            "note": "Données publiques (likes/commentaires) — pas d'impressions disponibles sans Page connectée",
        }
