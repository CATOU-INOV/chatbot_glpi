"""
Configuration centralisée de l'API, chargée depuis les variables d'environnement (.env).

Utilise pydantic-settings : Pydantic valide chaque variable au démarrage de l'app
(types corrects, valeurs par défaut) au lieu de faire des os.environ.get() éparpillés
dans tout le code. Si une variable obligatoire manque, l'app refuse de démarrer avec
un message d'erreur clair plutôt que de planter plus tard au milieu d'une requête.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Qdrant (base vectorielle) ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "glpi_tickets"

    # --- Embeddings ---
    # Même modèle utilisé à l'ingestion et à la recherche : c'est obligatoire,
    # sinon les vecteurs comparés ne "parlent pas le même langage".
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # --- Recherche hybride (dense + sparse BM25) ---
    # Nom des deux named vectors dans la collection Qdrant (voir ensure_collection
    # dans ingest_glpi.py). Même modèle sparse à l'ingestion et à la recherche,
    # pour la même raison que l'embedding dense ci-dessus.
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "bm25"
    sparse_model_name: str = "Qdrant/bm25"

    # --- Ollama (LLM local) ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: int = 300

    # --- RAG : retrieval hybride (Qdrant dense+sparse) + reranking (cross-encoder) ---
    # Étage 1 (retrieval) : scan large et peu coûteux, fusion RRF de deux recherches
    # Qdrant en parallèle (dense cosinus + sparse BM25) — rapide mais approximatif,
    # au niveau du chunk (problème ou solution individuels, pas le ticket entier).
    rag_retrieval_top_k: int = 25

    # Étage 2 (reranking) : un cross-encoder relit chaque paire (question, TICKET
    # reconstruit — pas chunk) ensemble et donne un score de pertinence bien plus
    # fiable, mais plus coûteux. Les chunks du retrieval sont d'abord dédupliqués
    # par ticket_id avant reranking — sur un scan de 25 chunks, le nombre de
    # tickets uniques est presque toujours < 25 (souvent ~10-15 en pratique),
    # ce qui réduit d'autant le nombre de paires passées au cross-encoder.
    rag_rerank_top_k: int = 3
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Chunking (ingestion) ---
    # Longueur minimale du texte de solution nettoyé pour garder la ligne — en
    # dessous, la solution est probablement vide de contenu utile une fois le
    # HTML retiré (voir clean_html dans ingest_glpi.py).
    min_solution_length: int = 30

    # --- Langfuse (observabilité, self-host Docker) ---
    # Optionnels : si vides, le tracing est désactivé (no-op) sans casser l'API.
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3000"  # instance Docker locale par défaut

    # --- CORS (le plugin GLPI appelle l'API depuis le navigateur en JS/fetch) ---
    # A restreindre à l'URL réelle de l'instance GLPI en prod.
    cors_allow_origins: list[str] = ["*"]

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    """Instancie Settings une seule fois (cache) et la réutilise partout via injection de dépendance."""
    return Settings()
