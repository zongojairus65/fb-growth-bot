"""
Client Graph API Facebook.

Rappel important : l'écriture (publication) n'est possible que sur une Page,
jamais sur un profil personnel, quel que soit le nombre de followers. Le token
utilisé ici doit être un token de PAGE longue durée, obtenu via un token
utilisateur avec les permissions : pages_manage_posts, pages_read_engagement,
pages_show_list.
"""

import httpx
from typing import Optional

GRAPH_URL = "https://graph.facebook.com/v20.0"


class GraphClient:
    def __init__(self, page_access_token: str, page_id: str):
        self.token = page_access_token
        self.page_id = page_id

    async def resolve_username(self, username: str) -> Optional[dict]:
        """Résout un vanity URL public en id/nom/catégorie, sans authentification.
        Sert uniquement à l'identification/affichage, jamais à l'écriture."""
        url = f"{GRAPH_URL}/{username}"
        params = {"fields": "id,name,category"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        return resp.json()

    async def get_recent_posts_stats(self, limit: int = 30) -> list[dict]:
        """Récupère les posts récents de la Page avec leurs insights de base,
        utilisés comme données réelles pour le prompt de diagnostic."""
        url = f"{GRAPH_URL}/{self.page_id}/posts"
        params = {
            "access_token": self.token,
            "fields": (
                "id,message,created_time,"
                "insights.metric(post_impressions,post_engaged_users)"
            ),
            "limit": limit,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"Graph API error: {resp.text}")
        return resp.json().get("data", [])

    async def average_reach(self) -> int:
        posts = await self.get_recent_posts_stats()
        if not posts:
            return 0
        total = 0
        count = 0
        for p in posts:
            for insight in p.get("insights", {}).get("data", []):
                if insight["name"] == "post_impressions":
                    total += insight["values"][0]["value"]
                    count += 1
        return int(total / count) if count else 0

    async def publish_text_post(self, message: str) -> dict:
        url = f"{GRAPH_URL}/{self.page_id}/feed"
        payload = {"message": message, "access_token": self.token}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, data=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Échec de publication: {resp.text}")
        return resp.json()

    async def publish_photo_post(self, image_url: str, caption: str = "") -> dict:
        url = f"{GRAPH_URL}/{self.page_id}/photos"
        payload = {"url": image_url, "caption": caption, "access_token": self.token}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Échec de publication photo: {resp.text}")
        return resp.json()
