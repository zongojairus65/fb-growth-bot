"""
Templates de prompts. Chaque fonction retourne un prompt prêt à envoyer à Gemini,
en français, injecté avec les variables du profil / des données réelles.
"""


def diagnostic_prompt(username: str, niche_hint: str, stats: dict) -> str:
    """Remplace le 'scan IA' de Blow Up, mais basé sur de vraies stats Graph API
    au lieu d'un modèle propriétaire boîte noire."""
    return f"""Agis en tant qu'analyste de croissance Facebook.
Voici les statistiques réelles des 30 derniers posts du compte @{username} :
{stats}

Indice de niche fourni par l'utilisateur : {niche_hint}

Réponds UNIQUEMENT en JSON avec cette structure exacte :
{{
  "niche_detectee": "...",
  "resume": "2-3 phrases avec au moins un chiffre concret tiré des stats fournies",
  "hashtags": ["...", "...", "...", "..."],
  "points_forts": ["...", "...", "..."],
  "points_faibles": ["...", "...", "..."]
}}
Chaque point fort/faible doit s'appuyer sur une donnée réelle des stats, pas une généralité.
Ton direct, familier mais professionnel, comme un coach qui connaît vraiment le compte."""


def quiz_followup_prompt(reponses: dict) -> str:
    """Utilise les réponses du mini-quiz psychologique pour calibrer l'angle
    des futurs posts (au lieu de le deviner, comme demandé dans le Prompt 1)."""
    return f"""Voici les réponses d'un créateur à un mini-quiz sur ses blocages :
{reponses}

En une phrase, résume son principal frein psychologique actuel et le type de
message motivationnel qui résonnerait avec lui avant de lui proposer du contenu."""


def strategy_prompt(niche: str, audience: str, objectif: str) -> str:
    return f"""Agis en tant que stratège senior en croissance Facebook. Analyse ma
niche et mon audience, identifie mentalement les 7 tendances de contenu les plus
saturées sur Facebook (sans les lister séparément dans ta réponse), puis crée 10
idées de posts qui cassent intentionnellement ces tendances tout en restant
alignées avec les algorithmes de la plateforme.

Niche : {niche}
Audience : {audience}
Objectif : {objectif}

IMPORTANT — format de réponse strict :
Réponds UNIQUEMENT avec un tableau JSON contenant exactement 10 objets, rien
d'autre avant ou après (pas de liste de tendances séparée, pas de texte
d'introduction, pas de markdown). Chaque objet doit avoir exactement ces clés :
concept, hook, format, angle_psychologique, justification_engagement.

Exemple de structure attendue (juste la forme, pas le contenu) :
[{{"concept": "...", "hook": "...", "format": "...", "angle_psychologique": "...", "justification_engagement": "..."}}, ...]"""


def hooks_prompt(idee: str, audience: str, ton: str) -> str:
    return f"""Agis en tant que copywriter viral spécialisé dans l'engagement
Facebook. Génère 15 accroches d'ouverture à fort impact pour cette idée,
structurées en : curiosité, contrarian, tension émotionnelle, autorité, et
proximité. Chaque hook doit être optimisé pour arrêter le scroll dans le fil
Facebook, encourager les commentaires, et paraître naturel, conversationnel,
et natif de la plateforme. Classe les 5 hooks les plus forts à la fin.

Idée : {idee}
Audience : {audience}
Ton : {ton}"""


def format_adapter_prompt(idee: str, audience: str, objectif: str) -> str:
    return f"""Agis en tant que stratège de contenu Facebook. Transforme cette
idée en 4 formats optimisés : post texte long, post image (avec conseils de
superposition de texte), vidéo courte (Reels), et format partageable (conçu
pour les repartages et le partage en groupe). Pour chacun, fournis la
structure, les premières lignes, le formatage, la légende, et un appel à
l'action clair adapté à l'engagement Facebook.

Idée : {idee}
Audience : {audience}
Objectif : {objectif}"""


def retention_prompt(contenu: str, voix: str, audience: str) -> str:
    return f"""Agis en tant qu'expert en engagement et rétention Facebook.
Réécris ce contenu pour maximiser le taux de lecture complète, les
déclencheurs de commentaires, les partages, et les sauvegardes. Améliore le
rythme, supprime le superflu, renforce les accroches émotionnelles, et
assure-toi que chaque ligne pousse le lecteur à continuer. Optimise pour la
lisibilité mobile. Après la réécriture, explique les améliorations clés
apportées et pourquoi la nouvelle version performe mieux sur Facebook.

Contenu : {contenu}
Voix : {voix}
Audience : {audience}"""


def authority_prompt(contenu: str, audience: str, voix_marque: str) -> str:
    return f"""Agis en tant qu'expert en positionnement de marque pour
Facebook. Réécris mon contenu pour communiquer crédibilité, expertise, et
autorité sans paraître arrogant ou trop promotionnel. Évite le battage, les
clichés, et le langage de 'gourou'. Livre 3 variations : une minimaliste et
épurée, une axée narration, et une très soignée et professionnelle.

Contenu : {contenu}
Audience : {audience}
Voix de marque : {voix_marque}"""


def engagement_amplifier_prompt(contenu: str, audience: str, objectif: str) -> str:
    return f"""Agis en tant que stratège en engagement Facebook. Améliore ce
post pour maximiser les commentaires, les partages, et les interactions
significatives. Ajoute des déclencheurs de conversation naturels, des
questions ouvertes, et des invitations à donner son avis sans paraître forcé
ou putàclic. Suggère des déclencheurs psychologiques subtils, une structure
de post idéale, et 3 variations de questions à commentaires qui paraissent
organiques et propices à la discussion.

Contenu : {contenu}
Audience : {audience}
Objectif : {objectif}"""
