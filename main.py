import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models import Profile, QuizAnswer, DiagnosticRequest
from core.gemini_client import GeminiClient
from core.scraper_client import ScraperClient
from facebook.graph_client import GraphClient
from core.pipeline import GrowthPipeline
from core import db
from onboarding.funnel import SCAN_STEPS, QUIZ_QUESTIONS

load_dotenv()

app = FastAPI(title="FB Growth Bot")

gemini = GeminiClient()

try:
    scraper = ScraperClient()
except RuntimeError:
    scraper = None  # le bot fonctionne quand même, mais le mode "username seul" sera indisponible

pipeline = GrowthPipeline(gemini, scraper)


@app.get("/onboarding/scan-steps")
def get_scan_steps():
    return {"steps": SCAN_STEPS}


@app.get("/onboarding/quiz")
def get_quiz():
    return {"questions": QUIZ_QUESTIONS}


@app.post("/onboarding/quiz/answer")
async def submit_quiz_answer(answer: QuizAnswer):
    return {"status": "recu", "question_id": answer.question_id}


@app.post("/diagnostic")
async def diagnostic(req: DiagnosticRequest):
    """
    Diagnostic unique, deux chemins possibles selon ce que l'utilisateur fournit :
    - fb_username seul           -> scraper (rapide, léger, sans connexion)
    - fb_page_id + fb_page_token -> Graph API (plus riche, nécessite OAuth)
    """
    try:
        result = await pipeline.run_diagnostic(req)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    # La persistance ne doit JAMAIS faire échouer la réponse au client,
    # même si core/db.py a déjà ses propres try/except internes — défense
    # en profondeur après l'incident précédent.
    try:
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        await db.save_diagnostic(
            req.profile_id, req.fb_username or req.fb_page_id or "", req.niche_hint or "", result_dict
        )
    except Exception as e:
        print(f"[main] Sauvegarde diagnostic ignorée suite à une erreur: {e}")

    return result


@app.get("/projection/{profile_id}")
async def projection(profile_id: int, avg_reach: int = 0):
    return await pipeline.growth_projection(profile_id, avg_reach)


@app.post("/strategy")
async def strategy(profile_id: int, niche: str, audience: str, objectif: str, contexte_psy: str = ""):
    ideas = await pipeline.generate_strategy(niche, audience, objectif, contexte_psy)

    try:
        await db.save_strategy_ideas(profile_id, ideas)
    except Exception as e:
        print(f"[main] Sauvegarde stratégie ignorée suite à une erreur: {e}")

    return {"ideas": ideas}


@app.post("/hooks")
async def hooks(idee: str, audience: str, ton: str):
    result = await pipeline.generate_hooks(idee, audience, ton)
    return {"hooks": result}


@app.post("/formats")
async def formats(idee: str, audience: str, objectif: str):
    result = await pipeline.adapt_formats(idee, audience, objectif)
    return {"formats": result}


@app.post("/refine")
async def refine(contenu: str, voix: str, audience: str, objectif: str):
    result = await pipeline.refine_full(contenu, voix, audience, objectif)
    return result


@app.post("/publish/text")
async def publish_text(message: str, fb_page_id: str, fb_page_token: str):
    """Publication : chaque utilisateur fournit SA PROPRE Page + token — jamais une valeur globale."""
    graph = GraphClient(page_access_token=fb_page_token, page_id=fb_page_id)
    result = await graph.publish_text_post(message)
    return result


@app.post("/publish/photo")
async def publish_photo(image_url: str, fb_page_id: str, fb_page_token: str, caption: str = ""):
    graph = GraphClient(page_access_token=fb_page_token, page_id=fb_page_id)
    result = await graph.publish_photo_post(image_url, caption)
    return result


@app.get("/debug/db-test")
async def debug_db_test():
    """Test isolé de la persistance — utile à garder pour diagnostiquer
    rapidement en cas de nouveau problème de connexion DB."""
    return await db.test_connection()
