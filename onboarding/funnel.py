"""
Reproduit le funnel psychologique observé dans Blow Up :
username -> scan animé -> résultats -> quiz de blocages -> projection de croissance.

Rien ici n'appelle Gemini pour le déroulé/UX — seul le quiz_followup_prompt
(dans core/prompts.py) utilise l'IA, sur les réponses une fois collectées.
"""

from models import EngagementProjection

SCAN_STEPS = [
    {"pct": 15, "label": "Récupération du profil public"},
    {"pct": 35, "label": "Lecture des statistiques de la Page"},
    {"pct": 60, "label": "Analyse des posts récents"},
    {"pct": 85, "label": "Analyse IA en cours"},
    {"pct": 100, "label": "Diagnostic prêt"},
]

QUIZ_QUESTIONS = [
    {
        "id": "frein_principal",
        "question": "Qu'est-ce qui t'empêche d'atteindre tes objectifs sur Facebook ?",
        "options": [
            "Je poste, mais personne ne réagit à mes posts",
            "Je manque d'idées de contenu",
            "J'ai du mal à poster régulièrement",
            "Je galère à convertir mon audience",
        ],
    },
    {
        "id": "rapport_echec",
        "question": "Quand un post ne marche pas, j'ai tendance à douter de moi",
        "type": "echelle",
        "options": ["Pas du tout", "Un peu", "Neutre", "Plutôt oui", "Totalement"],
    },
]


def build_projection(current_avg_reach: int) -> EngagementProjection:
    """Projection de croissance à partir de la portée moyenne réelle du compte
    (pas un chiffre inventé) — paliers x10 classiques type 1K/10K/100K."""
    base = max(current_avg_reach, 50)
    paliers = [
        {"label": "Aujourd'hui", "valeur": base},
        {"label": "1K", "valeur": 1000},
        {"label": "10K", "valeur": 10000},
        {"label": "100K", "valeur": 100000},
    ]
    return EngagementProjection(
        profile_id=0,
        palier_actuel=base,
        paliers=paliers,
        message_motivation=(
            "Personne ne perce du jour au lendemain. La différence entre "
            "les comptes qui stagnent et ceux qui percent, c'est la régularité "
            "d'un plan qu'on suit — c'est exactement ce qu'on va construire ensemble."
        ),
    )
