"""
Connexion Postgres (Neon) via asyncpg, avec statement_cache_size=0 —
obligatoire avec le pooler PgBouncer de Neon en mode transaction.

Toutes les fonctions sont conçues pour ne JAMAIS lever d'exception vers
l'appelant — un échec de persistance ne doit jamais perturber la réponse
HTTP principale. C'est le point qui semble avoir cassé /diagnostic la
dernière fois ; on le teste ici isolément avant de rebrancher.
"""

import os
import json
import asyncpg
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> Optional[asyncpg.Pool]:
    global _pool
    if not DATABASE_URL:
        return None
    if _pool is not None:
        return _pool
    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, statement_cache_size=0, min_size=1, max_size=5)
        return _pool
    except Exception as e:
        print(f"[db] Échec de connexion au pool: {e}")
        return None


async def test_connection() -> dict:
    """Endpoint de diagnostic isolé — vérifie juste que la connexion et une
    insertion basique fonctionnent, sans toucher au reste de l'app."""
    pool = await get_pool()
    if not pool:
        return {"success": False, "error": "Pool non disponible (DATABASE_URL manquant ou connexion échouée)"}
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO generations (endpoint, request_params, result) VALUES ($1, $2, $3)",
                "test_connection",
                json.dumps({"test": True}),
                json.dumps({"ok": True}),
            )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def save_generation(endpoint: str, request_params: dict, result) -> None:
    pool = await get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO generations (endpoint, request_params, result) VALUES ($1, $2, $3)",
                endpoint,
                json.dumps(request_params),
                json.dumps(result) if not isinstance(result, str) else json.dumps({"text": result}),
            )
    except Exception as e:
        print(f"[db] Échec de sauvegarde ({endpoint}): {e}")


async def save_diagnostic(profile_id: int, fb_username: str, niche_hint: str, result: dict) -> None:
    pool = await get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO diagnostics
                   (profile_id, niche_detectee, resume, hashtags, points_forts, points_faibles, raw_stats)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                profile_id,
                result.get("niche_detectee", ""),
                result.get("resume", ""),
                json.dumps(result.get("hashtags", [])),
                json.dumps(result.get("points_forts", [])),
                json.dumps(result.get("points_faibles", [])),
                json.dumps(result.get("raw_stats", {})),
            )
    except Exception as e:
        print(f"[db] Échec de sauvegarde diagnostic: {e}")


async def save_strategy_ideas(profile_id: int, ideas: list[dict]) -> None:
    pool = await get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            for idea in ideas:
                await conn.execute(
                    """INSERT INTO content_ideas
                       (profile_id, concept, hook, format, angle_psychologique, justification_engagement)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    profile_id,
                    idea.get("concept", ""),
                    idea.get("hook", ""),
                    idea.get("format", ""),
                    idea.get("angle_psychologique", ""),
                    idea.get("justification_engagement", ""),
                )
    except Exception as e:
        print(f"[db] Échec de sauvegarde stratégie: {e}")
