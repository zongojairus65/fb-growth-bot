"""
Client pour facebook-scraper3 (RapidAPI) — diagnostic en lecture seule
sur profils publics, jamais pour la publication.

Endpoints confirmés :
- GET /profile/id?url=...                  -> résout un username en profile_id
- GET /profile/details_id?profile_id=...   -> bio, catégorie, followers (affine la niche)
- GET /profile/posts?profile_id=...        -> posts publics récents
- GET /profile/reels?reels_profile_id=...  -> reels publics récents (format d'ID à confirmer)
"""

import os
import httpx
from typing import Optional

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "facebook-scraper3.p.rapidapi.com")


class ScraperClient:
    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key or RAPIDAPI_KEY
        self.host = host or RAPIDAPI_HOST
        if not self.api_key:
            raise RuntimeError("RAPIDAPI_KEY manquant dans l'environnement")
        self.timeout = timeout
        self.base_url = f"https://{self.host}"

    def _headers(self) -> dict:
        return {
            "x-rapidapi-host": self.host,
            "x-rapidapi-key": self.api_key,
        }

    async def resolve_username_to_id(self, username: str) -> Optional[str]:
        """Résout un @username public en profile_id numérique."""
        url = f"{self.base_url}/profile/id"
        params = {"url": f"https://www.facebook.com/{username}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("id") or data.get("profile_id")

    async def fetch_profile_details(self, profile_id: str) -> dict:
        """Bio, catégorie, nombre de followers — sert à affiner automatiquement
        la niche au lieu de demander niche_hint à l'utilisateur.
        Endpoint confirmé: /profile/details_id (pas /profile/details)."""
        url = f"{self.base_url}/profile/details_id"
        params = {"profile_id": profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            return {}
        return resp.json()

    async def fetch_public_profile_posts(self, profile_id: str, limit: int = 20) -> list[dict]:
        """Liste les posts publics récents (hors reels)."""
        url = f"{self.base_url}/profile/posts"
        params = {"profile_id": profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"RapidAPI error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("results") or data.get("data") or data.get("posts") or []

    async def fetch_profile_reels(self, reels_profile_id: str, limit: int = 20) -> list[dict]:
        """Reels publics récents. ATTENTION: reels_profile_id semble être un
        format d'ID différent du profile_id numérique classique (voir note
        dans la doc RapidAPI — à confirmer par test avant usage en prod)."""
        url = f"{self.base_url}/profile/reels"
        params = {"reels_profile_id": reels_profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"RapidAPI error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("results") or data.get("data") or data.get("reels") or []

    def summarize_posts(self, posts: list[dict]) -> dict:
        if not posts:
            return {"nb_posts_analyses": 0, "moyenne_likes": 0, "moyenne_commentaires": 0}

        def get_likes(p: dict) -> int:
            return p.get("likes") or p.get("reactions_count") or 0

        def get_comments(p: dict) -> int:
            return p.get("comments") or p.get("comments_count") or 0

        total_likes = sum(get_likes(p) for p in posts)
        total_comments = sum(get_comments(p) for p in posts)
        n = len(posts)
        return {
            "nb_posts_analyses": n,
            "moyenne_likes": int(total_likes / n),
            "moyenne_commentaires": int(total_comments / n),
        }

    def summarize_reels(self, reels: list[dict]) -> dict:
        if not reels:
            return {"nb_reels_analyses": 0, "moyenne_vues_reels": 0, "moyenne_partages_reels": 0}

        def get_views(r: dict) -> int:
            return r.get("views") or r.get("play_count") or 0

        def get_shares(r: dict) -> int:
            return r.get("shares") or r.get("share_count") or 0

        total_views = sum(get_views(r) for r in reels)
        total_shares = sum(get_shares(r) for r in reels)
        n = len(reels)
        return {
            "nb_reels_analyses": n,
            "moyenne_vues_reels": int(total_views / n),
            "moyenne_partages_reels": int(total_shares / n),
        }

    def extract_niche_hint(self, details: dict) -> str:
        """Construit un niche_hint automatique à partir de la bio/catégorie,
        pour ne plus dépendre de la saisie manuelle de l'utilisateur."""
        bio = details.get("bio") or details.get("intro") or ""
        category = details.get("category") or ""
        parts = [p for p in [category, bio] if p]
        return " - ".join(parts) if parts else ""
