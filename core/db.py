"""
Connexion Postgres (Neon) via asyncpg, avec statement_cache_size=0 —
obligatoire avec le pooler PgBouncer de Neon en mode transaction.

Toutes les fonctions sont conçues pour ne JAMAIS lever d'exception vers
l'appelant — un échec de persistance ne doit jamais perturber la réponse
HTTP principale.
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
    """Endpoint de diagnostic isolé — expose l'erreur réelle de connexion
    plutôt que le message générique de get_pool()."""
    if not DATABASE_URL:
        return {"success": False, "error": "DATABASE_URL est vide ou absente de l'environnement"}
    try:
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        await conn.execute(
            "INSERT INTO generations (endpoint, request_params, result) VALUES ($1, $2, $3)",
            "test_connection",
            json.dumps({"test": True}),
            json.dumps({"ok": True}),
        )
        await conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}


async def create_profile(
    fb_username: str = "", fb_page_id: str = "", niche: str = "", audience: str = "", objectif: str = ""
) -> Optional[int]:
    """Crée un profil et retourne son id. Nécessaire avant tout diagnostic/
    stratégie, puisque diagnostics.profile_id et content_ideas.profile_id
    référencent profiles(id) via une contrainte de clé étrangère."""
    pool = await get_pool()
    if not pool:
        return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO profiles (fb_username, fb_page_id, niche, audience, objectif)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                fb_username, fb_page_id, niche, audience, objectif,
            )
            return row["id"] if row else None
    except Exception as e:
        print(f"[db] Échec de création de profil: {e}")
        return None


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


async def save_quiz_answer(profile_id: int, question_id: str, answer: str) -> None:
    pool = await get_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO quiz_answers (profile_id, question_id, answer) VALUES ($1, $2, $3)",
                profile_id, question_id, answer,
            )
    except Exception as e:
        print(f"[db] Échec de sauvegarde réponse quiz: {e}")


async def get_quiz_answers(profile_id: int) -> dict:
    """Retourne les réponses les plus récentes par question_id pour un profil
    (DISTINCT ON évite les doublons si l'utilisateur a répondu plusieurs fois)."""
    pool = await get_pool()
    if not pool:
        return {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT ON (question_id) question_id, answer
                   FROM quiz_answers
                   WHERE profile_id = $1
                   ORDER BY question_id, created_at DESC""",
                profile_id,
            )
            return {row["question_id"]: row["answer"] for row in rows}
    except Exception as e:
        print(f"[db] Échec de lecture réponses quiz: {e}")
        return {}
