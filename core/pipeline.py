from core.gemini_client import GeminiClient
from core import prompts
from facebook.graph_client import GraphClient
from onboarding.funnel import build_projection
from models import DiagnosticResult, EngagementProjection

GEMINI_PREMIUM = "gemini-3.5-flash"
GEMINI_FREE = "gemma-4-31b-it"


class GrowthPipeline:
    def __init__(self, gemini: GeminiClient, graph: GraphClient):
        self.gemini = gemini
        self.graph = graph

    async def run_diagnostic(self, profile_id: int, username: str, niche_hint: str) -> DiagnosticResult:
        posts = await self.graph.get_recent_posts_stats()
        stats_summary = {
            "nb_posts_analyses": len(posts),
            "moyenne_impressions": await self.graph.average_reach(),
        }
        prompt = prompts.diagnostic_prompt(username, niche_hint, stats_summary)
        result = await self.gemini.generate_json(prompt, model=GEMINI_FREE)
        return DiagnosticResult(profile_id=profile_id, raw_stats=stats_summary, **result)

    async def growth_projection(self, profile_id: int) -> EngagementProjection:
        avg = await self.graph.average_reach()
        projection = build_projection(avg)
        projection.profile_id = profile_id
        return projection

    async def apply_quiz_context(self, reponses: dict) -> str:
        prompt = prompts.quiz_followup_prompt(reponses)
        return await self.gemini.generate(prompt, model=GEMINI_FREE, temperature=0.6)

    async def generate_strategy(self, niche: str, audience: str, objectif: str, contexte_psy: str = "") -> list[dict]:
        niche_enrichie = f"{niche}\nContexte psychologique du créateur : {contexte_psy}" if contexte_psy else niche
        prompt = prompts.strategy_prompt(niche_enrichie, audience, objectif)
        raw = await self.gemini.generate(prompt, model=GEMINI_PREMIUM)
        import json
        return json.loads(raw.strip().removeprefix("```json").removesuffix("```"))

    async def generate_hooks(self, idee: str, audience: str, ton: str) -> str:
        prompt = prompts.hooks_prompt(idee, audience, ton)
        return await self.gemini.generate(prompt, model=GEMINI_PREMIUM)

    async def adapt_formats(self, idee: str, audience: str, objectif: str) -> str:
        prompt = prompts.format_adapter_prompt(idee, audience, objectif)
        return await self.gemini.generate(prompt, model=GEMINI_PREMIUM)

    async def refine_full(self, contenu: str, voix: str, audience: str, objectif: str) -> dict:
        retenu = await self.gemini.generate(
            prompts.retention_prompt(contenu, voix, audience), model=GEMINI_PREMIUM
        )
        autorite = await self.gemini.generate(
            prompts.authority_prompt(retenu, audience, voix), model=GEMINI_PREMIUM
        )
        final = await self.gemini.generate(
            prompts.engagement_amplifier_prompt(autorite, audience, objectif), model=GEMINI_PREMIUM
        )
        return {"retention": retenu, "autorite": autorite, "final": final}
