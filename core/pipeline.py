from core.gemini_client import GeminiClient
from core import prompts
from core.scraper_client import ScraperClient
from facebook.graph_client import GraphClient
from onboarding.funnel import build_projection
from models import DiagnosticResult, EngagementProjection, DiagnosticRequest

GEMINI_PREMIUM = "gemini-3.5-flash"
GEMINI_FREE = "gemma-4-31b-it"


class GrowthPipeline:
    def __init__(self, gemini: GeminiClient, scraper: ScraperClient | None = None):
        self.gemini = gemini
        self.scraper = scraper

    async def run_diagnostic(self, req: DiagnosticRequest) -> DiagnosticResult:
        """Point d'entrée unique : route automatiquement vers le scraper
        (username seul) ou vers Graph API (page_id + token fournis)."""
        has_username = bool(req.fb_username)
        has_page_creds = bool(req.fb_page_id and req.fb_page_token)

        if has_username and has_page_creds:
            raise ValueError("Fournis soit un username, soit un couple page_id/token — pas les deux.")
        if not has_username and not has_page_creds:
            raise ValueError("Fournis un username OU un couple page_id/token.")

        if has_page_creds:
            return await self._diagnostic_via_page(req)
        return await self._diagnostic_via_scraper(req)

    async def _diagnostic_via_scraper(self, req: DiagnosticRequest) -> DiagnosticResult:
        if not self.scraper:
            raise RuntimeError("Scraper non configuré (SCRAPER_API_TOKEN manquant)")
        posts = await self.scraper.fetch_public_profile_posts(req.fb_username)
        stats_summary = self.scraper.summarize_stats(posts)
        prompt = prompts.diagnostic_prompt(req.fb_username, req.niche_hint, stats_summary)
        result = await self.gemini.generate_json(prompt, model=GEMINI_FREE)
        return DiagnosticResult(profile_id=req.profile_id, raw_stats=stats_summary, **result)

    async def _diagnostic_via_page(self, req: DiagnosticRequest) -> DiagnosticResult:
        """Instancie un GraphClient à la volée avec LE token de CET utilisateur
        (jamais une variable d'env globale — chaque utilisateur a le sien)."""
        graph = GraphClient(page_access_token=req.fb_page_token, page_id=req.fb_page_id)
        posts = await graph.get_recent_posts_stats()
        stats_summary = {
            "nb_posts_analyses": len(posts),
            "moyenne_impressions": await graph.average_reach(),
        }
        label = req.fb_username or req.fb_page_id
        prompt = prompts.diagnostic_prompt(label, req.niche_hint, stats_summary)
        result = await self.gemini.generate_json(prompt, model=GEMINI_FREE)
        return DiagnosticResult(profile_id=req.profile_id, raw_stats=stats_summary, **result)

    async def growth_projection(self, profile_id: int, avg_reach: int = 0) -> EngagementProjection:
        projection = build_projection(avg_reach)
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
