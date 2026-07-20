"""
Intégration Langfuse (observabilité : traces + feedback utilisateur).

SDK Langfuse v4 (basé sur OpenTelemetry) — API par spans/observations, différente
des versions 2.x/3.x (pas de client.trace()/trace.generation() ici).

Design : si LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY ne sont pas définis dans .env,
get_langfuse_client() renvoie None et toutes les fonctions de ce module deviennent
des no-op silencieux. Ça permet de développer et tester l'API sans avoir Langfuse
lancé, et d'activer le tracing plus tard juste en remplissant le .env — sans toucher
au code de app/main.py ou app/rag.py.

Pour lancer Langfuse en local (self-host, pas cloud) :
  https://langfuse.com/self-hosting/docker-compose — un simple `docker compose up`
  suffit pour avoir l'UI sur http://localhost:3000, où on crée un projet et on
  récupère la paire de clés publique/secrète à mettre dans .env.
"""

from functools import lru_cache

from langfuse import Langfuse, propagate_attributes

from app.config import get_settings


@lru_cache
def get_langfuse_client() -> Langfuse | None:
    """Instancie le client Langfuse une seule fois, ou None si non configuré."""
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def trace_chat_generation(
    *,
    question: str,
    answer: str,
    context: str,
    model_name: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """
    Enregistre une trace complète d'une génération RAG dans Langfuse :
    la question, le contexte injecté, la réponse du LLM, et le modèle utilisé.

    Renvoie l'ID de trace Langfuse (à transmettre au plugin GLPI dans
    ChatResponse.generation_id), ou None si Langfuse n'est pas configuré —
    dans ce cas le plugin ne pourra simplement pas envoyer de feedback lié.
    """
    client = get_langfuse_client()
    if client is None:
        return None

    # propagate_attributes doit englober la création du span pour que user_id/
    # session_id soient attachés dès le départ (voir doc du SDK : les spans créés
    # avant l'entrée dans ce context manager ne sont pas mis à jour rétroactivement).
    with (
        propagate_attributes(user_id=user_id, session_id=session_id),
        client.start_as_current_observation(
            name="glpi-rag-chat",
            as_type="generation",
            model=model_name,
            input=[{"role": "user", "content": f"{context}\n\nQuestion: {question}"}],
            output=answer,
        ),
    ):
        trace_id = client.get_current_trace_id()

    # Envoie la trace immédiatement plutôt que d'attendre le flush périodique du
    # SDK — important dans une API HTTP où le process peut être court-lived.
    client.flush()
    return trace_id


def record_feedback(*, generation_id: str, score: int, comment: str | None = None) -> None:
    """
    Attache un score (1=👍, 0=👎) à la trace correspondante dans Langfuse.

    `generation_id` est en réalité le trace_id renvoyé par trace_chat_generation()
    (nommage aligné sur le vocabulaire du plugin GLPI / ChatResponse.generation_id).

    No-op si Langfuse n'est pas configuré — évite un crash de /api/feedback en dev.
    """
    client = get_langfuse_client()
    if client is None:
        return

    client.create_score(
        trace_id=generation_id,
        name="user-feedback",
        value=score,
        data_type="BOOLEAN",
        comment=comment,
    )
    client.flush()
