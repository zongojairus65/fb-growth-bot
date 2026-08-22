import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models import Profile, QuizAnswer
from core.gemini_client import GeminiClient
from facebook.graph_client import GraphClient
from core.pipeline import GrowthPipeline
from onboarding.funnel import SCAN_STEPS, QUIZ_QUESTIONS

load_dotenv()

app = FastAPI(title="FB Growth Bot")

gemini = GeminiClient()

graph = GraphClient(
    page_access_token=os.getenv("FB_PAGE_TOKEN", ""),
    page_id=os.getenv("FB_PAGE_ID", ""),
)
pipeline = GrowthPipeline(gemini, graph)


@app.get("/onboarding/scan-steps")
def get_scan_steps():
    return {"steps": SCAN_STEPS}


@app.get("/onboarding/quiz")
def get_quiz():
    return {"questions": QUIZ_QUESTIONS}


@app.post("/onboarding/quiz/answer")
async def submit_quiz_answer(answer: QuizAnswer):
    return {"status": "recu", "question_id": answer.question_id}


@app.post("/profile/{profile_id}/resolve-username")
async def resolve_username(profile_id: int, username: str):
    data = await graph.resolve_username(username)
    if not data:
        raise HTTPException(404, "Compte introuvable ou non public")
    return data


@app.post("/diagnostic/{profile_id}")
async def diagnostic(profile_id: int, username: str, niche_hint: str = ""):
    result = await pipeline.run_diagnostic(profile_id, username, niche_hint)
    return result


@app.get("/projection/{profile_id}")
async def projection(profile_id: int):
    return await pipeline.growth_projection(profile_id)


@app.post("/strategy")
async def strategy(niche: str, audience: str, objectif: str, contexte_psy: str = ""):
    ideas = await pipeline.generate_strategy(niche, audience, objectif, contexte_psy)
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
async def publish_text(message: str):
    result = await graph.publish_text_post(message)
    return result


@app.post("/publish/photo")
async def publish_photo(image_url: str, caption: str = ""):
    result = await graph.publish_photo_post(image_url, caption)
    return result
