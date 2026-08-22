"""
Client pour facebook-scraper3 (RapidAPI) — diagnostic en lecture seule
sur profils publics, jamais pour la publication.

Endpoints confirmés par test réel :
- GET /profile/id?url=...                  -> résout un username en profile_id
- GET /profile/details_id?profile_id=...   -> bio, catégorie, about_public
- GET /profile/posts?profile_id=...        -> posts publics (results[].reactions_count, comments_count)
- GET /profile/reels?reels_profile_id=...  -> reels publics — accepte le même ID numérique
                                               simple que profile_id (confirmé avec =4)
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
        url = f"{self.base_url}/profile/id"
        params = {"url": f"https://www.facebook.com/{username}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("id") or data.get("profile_id")

    async def fetch_profile_details(self, profile_id: str) -> dict:
        url = f"{self.base_url}/profile/details_id"
        params = {"profile_id": profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            return {}
        return resp.json()

    async def fetch_public_profile_posts(self, profile_id: str, limit: int = 20) -> list[dict]:
        url = f"{self.base_url}/profile/posts"
        params = {"profile_id": profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"RapidAPI error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("results") or []

    async def fetch_profile_reels(self, reels_profile_id: str, limit: int = 20) -> list[dict]:
        """Confirmé : accepte le même ID numérique simple que profile_id
        (testé avec reels_profile_id=4)."""
        url = f"{self.base_url}/profile/reels"
        params = {"reels_profile_id": reels_profile_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"RapidAPI error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("results") or []

    def summarize_posts(self, posts: list[dict]) -> dict:
        """Champs confirmés par test réel : reactions_count, comments_count."""
        if not posts:
            return {"nb_posts_analyses": 0, "moyenne_likes": 0, "moyenne_commentaires": 0}

        total_likes = sum(p.get("reactions_count", 0) for p in posts)
        total_comments = sum(p.get("comments_count", 0) for p in posts)
        n = len(posts)
        return {
            "nb_posts_analyses": n,
            "moyenne_likes": int(total_likes / n),
            "moyenne_commentaires": int(total_comments / n),
        }

    def summarize_reels(self, reels: list[dict]) -> dict:
        """Champs confirmés par test réel : video_view_count, reshare_count."""
        if not reels:
            return {"nb_reels_analyses": 0, "moyenne_vues_reels": 0, "moyenne_partages_reels": 0}

        total_views = sum(r.get("video_view_count", 0) for r in reels)
        total_shares = sum(r.get("reshare_count", 0) for r in reels)
        n = len(reels)
        return {
            "nb_reels_analyses": n,
            "moyenne_vues_reels": int(total_views / n),
            "moyenne_partages_reels": int(total_shares / n),
        }

    def extract_niche_hint(self, details: dict) -> str:
        """Champs confirmés par test réel : intro (bio), influencer_category,
        about_public (liste de tags, dont l'activité/poste du profil).
        Pas de champ 'followers' disponible sur cet endpoint."""
        profile = details.get("profile", details)  # gère les deux formats (avec/sans clé racine "profile")
        intro = profile.get("intro", "")
        influencer_category = profile.get("influencer_category", "")
        about_tags = [
            item.get("text", "")
            for item in profile.get("about_public", [])
            if item.get("text")
        ]
        parts = [p for p in [influencer_category, intro, *about_tags] if p]
        return " - ".join(parts) if parts else ""
