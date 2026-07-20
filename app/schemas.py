"""
Schémas Pydantic : définissent la forme exacte des données qui entrent et sortent de l'API.

C'est le "garde-fou" mentionné dans le brief : FastAPI valide automatiquement chaque
requête entrante contre ces modèles. Si le plugin GLPI envoie un JSON malformé
(champ manquant, mauvais type), FastAPI répond 422 avec le détail de l'erreur
avant même que notre code métier ne soit exécuté.
"""

from pydantic import BaseModel, Field


# --- POST /api/chat ---


class ChatRequest(BaseModel):
    """Requête envoyée par le plugin GLPI (fetch JS) quand un employé pose une question."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Question posée par l'employé, en langage naturel.",
    )
    user_id: str | None = Field(
        default=None,
        description="Identifiant GLPI de l'utilisateur (optionnel, pour le contexte de trace Langfuse).",
    )
    session_id: str | None = Field(
        default=None,
        description="Identifiant de session/conversation côté plugin, pour regrouper les traces Langfuse.",
    )


class SourceTicket(BaseModel):
    """Un ticket GLPI similaire utilisé comme contexte pour générer la réponse."""

    ticket_id: int
    titre: str
    score: float = Field(
        ...,
        description="Score de pertinence du cross-encoder (reranking) — pas une similarité cosinus brute.",
    )


class ChatResponse(BaseModel):
    """Réponse renvoyée au plugin GLPI."""

    answer: str = Field(..., description="Réponse générée par le LLM à partir du contexte RAG.")
    sources: list[SourceTicket] = Field(
        default_factory=list,
        description="Tickets sources utilisés pour construire la réponse, pour traçabilité côté employé.",
    )
    generation_id: str | None = Field(
        default=None,
        description="ID de la génération côté Langfuse — à renvoyer tel quel via /api/feedback.",
    )


# --- POST /api/feedback ---


class FeedbackRequest(BaseModel):
    """Feedback utilisateur (👍/👎) envoyé par le plugin après affichage d'une réponse."""

    generation_id: str = Field(..., description="ID de génération Langfuse renvoyé par /api/chat.")
    score: int = Field(..., ge=0, le=1, description="1 = 👍 utile, 0 = 👎 pas utile.")
    comment: str | None = Field(default=None, max_length=1000, description="Commentaire libre optionnel.")


class FeedbackResponse(BaseModel):
    status: str = "ok"
