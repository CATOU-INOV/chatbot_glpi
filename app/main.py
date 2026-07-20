"""
API FastAPI — passerelle entre le plugin GLPI et le pipeline RAG local (Qdrant + Ollama).

Lancement en dev :
    uvicorn app.main:app --reload --port 8000

Doc interactive auto-générée par FastAPI une fois lancé :
    http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.rag import run_rag_pipeline, tickets_to_sources
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from app.tracing import record_feedback, trace_chat_generation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("glpi-rag-api")

settings = get_settings()

app = FastAPI(
    title="GLPI RAG Gateway",
    description="API interne qui connecte le plugin GLPI au pipeline RAG local (Qdrant + Ollama).",
    version="0.1.0",
)

# Le plugin GLPI fait des requêtes fetch() JS depuis le navigateur -> CORS nécessaire.
# En prod, remplacer cors_allow_origins par l'URL exacte de l'instance GLPI (pas "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    """Ping simple pour vérifier que l'API tourne (utile pour le monitoring / le binôme au démarrage)."""
    return {
        "status": "ok",
        "langfuse_enabled": settings.langfuse_enabled,
        "ollama_model": settings.ollama_model,
        "qdrant_collection": settings.qdrant_collection,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Reçoit une question de l'interface GLPI, cherche le contexte sémantique dans Qdrant,
    génère une réponse via Ollama, et trace l'échange dans Langfuse.

    Le corps de la requête est validé par Pydantic (ChatRequest) avant même d'entrer
    dans cette fonction : question trop courte/longue -> 422 automatique.
    """
    try:
        answer, context, ranked_tickets = run_rag_pipeline(request.question)
    except Exception as exc:  # noqa: BLE001 — on veut logger + renvoyer une 502 propre au plugin
        logger.exception("Échec du pipeline RAG pour la question: %s", request.question)
        raise HTTPException(
            status_code=502,
            detail="Le service RAG (Qdrant ou Ollama) est indisponible. Réessayez dans quelques instants.",
        ) from exc

    generation_id = trace_chat_generation(
        question=request.question,
        answer=answer,
        context=context,
        model_name=settings.ollama_model,
        user_id=request.user_id,
        session_id=request.session_id,
    )

    return ChatResponse(
        answer=answer,
        sources=tickets_to_sources(ranked_tickets),
        generation_id=generation_id,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Reçoit le score 👍/👎 envoyé par le plugin GLPI après affichage d'une réponse,
    et l'attache à la génération correspondante dans Langfuse.
    """
    try:
        record_feedback(
            generation_id=request.generation_id,
            score=request.score,
            comment=request.comment,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec de l'enregistrement du feedback pour generation_id=%s", request.generation_id)
        raise HTTPException(status_code=502, detail="Impossible d'enregistrer le feedback.") from exc

    return FeedbackResponse()
