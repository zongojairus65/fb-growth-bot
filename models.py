from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Profile(BaseModel):
    id: Optional[int] = None
    fb_username: str          # vanity URL / handle, saisi par l'utilisateur (identification uniquement)
    fb_page_id: Optional[str] = None   # résolu via OAuth, seul champ qui autorise l'écriture
    niche: Optional[str] = None
    audience: Optional[str] = None
    objectif: Optional[str] = None


class QuizAnswer(BaseModel):
    profile_id: int
    question_id: str
    answer: str               # label choisi ou valeur d'échelle (1-5)


class DiagnosticResult(BaseModel):
    profile_id: int
    niche_detectee: str
    resume: str
    hashtags: list[str]
    points_forts: list[str]
    points_faibles: list[str]
    raw_stats: dict           # données brutes venant de Graph API (impressions, engagement, etc.)


class ContentIdea(BaseModel):
    id: Optional[int] = None
    profile_id: int
    concept: str
    hook: str
    format: str               # texte | image | video | lien
    angle_psychologique: str
    justification_engagement: str


class PostDraft(BaseModel):
    id: Optional[int] = None
    idea_id: int
    format: str
    contenu: str
    legende: Optional[str] = None
    cta: Optional[str] = None
    status: str = "brouillon"   # brouillon | pret | publie
    fb_post_id: Optional[str] = None
    posted_at: Optional[datetime] = None


class EngagementProjection(BaseModel):
    profile_id: int
    palier_actuel: int         # ex: vues moyennes actuelles
    paliers: list[dict]        # [{"label": "1K", "valeur": 1000}, ...]
    message_motivation: str
