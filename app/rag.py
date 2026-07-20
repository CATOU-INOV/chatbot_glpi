"""
Logique métier du RAG : retrieval hybride (chunké) + reranking dans Qdrant, puis
génération via Ollama.

Séparé de app/main.py pour que les routes FastAPI restent fines (juste de la
validation Pydantic + orchestration) et que cette logique soit testable seule,
sans avoir à monter un serveur HTTP.

Stratégie à deux étages, sur une collection chunkée (voir ingest_glpi.py — un
ticket produit un chunk "probleme" et un chunk "solution", indexés séparément) :

  1. Retrieval hybride — scan Qdrant large (rag_retrieval_top_k, ex: 25 CHUNKS,
     pas tickets) en fusionnant deux recherches Qdrant en une requête serveur :
       - dense  : similarité cosinus sur les embeddings bi-encoder (sens général)
       - sparse : BM25 (correspondance lexicale — bon sur les identifiants,
         codes d'erreur, numéros de ticket que le dense rate souvent)
     La fusion RRF (Reciprocal Rank Fusion) combine les deux classements sans
     avoir à calibrer un poids relatif entre scores dense et sparse, qui ne
     sont pas sur la même échelle.

  2. Regroupement anti-lenteur CPU — les 25 chunks retrouvés référencent souvent
     le même ticket deux fois (son chunk "probleme" ET son chunk "solution" ont
     pu matcher indépendamment). On déduplique par ticket_id et on reconstruit
     un document par ticket AVANT le reranking, pour ne jamais présenter au
     cross-encoder plus de paires que de tickets uniques trouvés (typiquement
     10-15 sur un scan de 25 chunks, jamais 25).

  3. Reranking — le cross-encoder relit chaque paire (question, TICKET
     reconstruit) *ensemble* et produit un score de pertinence bien plus
     fiable, au prix d'un coût par paire nettement plus élevé — d'où l'intérêt
     du regroupement de l'étape 2 pour limiter son volume d'entrée.
"""

from dataclasses import dataclass, field
from functools import lru_cache

import requests
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels
from sentence_transformers import CrossEncoder, SentenceTransformer

from app.config import Settings, get_settings
from app.schemas import SourceTicket

SYSTEM_PROMPT = """Tu es un assistant qui aide les employés de l'entreprise à résoudre leurs problèmes \
avec l'outil GLPI (helpdesk interne), en te basant sur des tickets similaires résolus par le passé.

Réponds uniquement à partir du contexte fourni (tickets + solutions). Si le contexte ne permet pas \
de répondre avec certitude, dis-le clairement plutôt que d'inventer une réponse. Sois concis et \
donne des étapes concrètes quand c'est possible.

Les tickets fournis sont des archives.
IMPORTANT : n'invente jamais de personne à contacter. Ne cite JAMAIS un prénom présent dans le \
contexte (client ou technicien) comme un contact actuel — ce sont des références archivées, pas des \
contacts valides.
IMPORTANT : si un ticket fourni est hors-sujet par rapport à la question, ignore-le."""


@dataclass
class RetrievedChunk:
    """Un chunk brut (problème ou solution) tel que renvoyé par le retrieval hybride."""

    payload: dict
    retrieval_score: float  # score de fusion RRF (étage 1) — pas directement comparable à un cosinus brut


@dataclass
class ReconstructedTicket:
    """
    Un ticket reconstruit à partir de ses chunks retrouvés, prêt pour le reranking.

    "Reconstruit" car un ticket dont seul le chunk "solution" a matché le
    retrieval doit quand même présenter son problème au cross-encoder (et
    inversement) — on rassemble tout ce qu'on sait du ticket à partir de
    n'importe lequel de ses chunks, puisque chaque chunk porte déjà titre et
    solution_finale dans son payload (voir build_chunks dans ingest_glpi.py).
    """

    ticket_id: int
    titre: str
    probleme_text: str
    solution_text: str
    best_retrieval_score: float
    matched_chunk_types: set[str] = field(default_factory=set)
    rerank_score: float | None = None  # score cross-encoder (étage 3), None avant reranking


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """Charge le modèle d'embedding dense (bi-encoder) une seule fois, puis le réutilise."""
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model_name)


@lru_cache
def get_sparse_model() -> SparseTextEmbedding:
    """Charge le modèle sparse BM25 une seule fois — même modèle qu'à l'ingestion."""
    settings = get_settings()
    return SparseTextEmbedding(model_name=settings.sparse_model_name)


@lru_cache
def get_reranker_model() -> CrossEncoder:
    """Charge le cross-encoder (étage 3, reranking) une seule fois — coûteux à instancier."""
    settings = get_settings()
    return CrossEncoder(settings.reranker_model_name)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def retrieve_candidates(question: str, settings: Settings) -> list[RetrievedChunk]:
    """
    Étage 1 : recherche hybride (dense + sparse, fusion RRF côté serveur Qdrant)
    sur les CHUNKS indexés, renvoie les rag_retrieval_top_k chunks les plus
    pertinents (scan large, peu coûteux — un chunk est un texte court, pas un
    ticket entier).
    """
    embedder = get_embedding_model()
    sparse_model = get_sparse_model()
    qdrant = get_qdrant_client()

    dense_vector = embedder.encode(question).tolist()
    sparse_vector = next(iter(sparse_model.embed([question])))

    points = qdrant.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            qmodels.Prefetch(
                query=dense_vector,
                using=settings.dense_vector_name,
                limit=settings.rag_retrieval_top_k,
            ),
            qmodels.Prefetch(
                query=qmodels.SparseVector(
                    indices=sparse_vector.indices.tolist(),
                    values=sparse_vector.values.tolist(),
                ),
                using=settings.sparse_vector_name,
                limit=settings.rag_retrieval_top_k,
            ),
        ],
        query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
        limit=settings.rag_retrieval_top_k,
    ).points

    return [
        RetrievedChunk(payload=point.payload or {}, retrieval_score=point.score)
        for point in points
    ]


def group_chunks_by_ticket(chunks: list[RetrievedChunk]) -> list[ReconstructedTicket]:
    """
    Étage 2 : déduplique les chunks par ticket_id et reconstruit un document
    complet par ticket unique — c'est le levier anti-lenteur CPU. Sur un scan
    de rag_retrieval_top_k chunks, le nombre de tickets uniques est presque
    toujours strictement inférieur (un même ticket matche souvent sur ses deux
    chunks à la fois), ce qui réduit d'autant le volume envoyé au reranking.

    Le "meilleur" score de retrieval d'un ticket (le plus haut parmi ses chunks
    matchés) est conservé pour information, mais n'est PAS ce qui décide du
    classement final — c'est le rôle du reranking à l'étage suivant.
    """
    by_ticket: dict[int, ReconstructedTicket] = {}

    for chunk in chunks:
        payload = chunk.payload
        ticket_id = payload.get("ticket_id")
        if ticket_id is None:
            continue

        if ticket_id not in by_ticket:
            titre = payload.get("titre", "")
            by_ticket[ticket_id] = ReconstructedTicket(
                ticket_id=ticket_id,
                titre=titre,
                # Filet de secours si seul le chunk "solution" matche (voir plus
                # bas) : au moins le titre est présent, jamais un problème vide.
                probleme_text=f"Titre: {titre}",
                solution_text=payload.get("solution_finale", ""),
                best_retrieval_score=chunk.retrieval_score,
            )

        ticket = by_ticket[ticket_id]
        ticket.matched_chunk_types.add(payload.get("chunk_type", ""))
        ticket.best_retrieval_score = max(ticket.best_retrieval_score, chunk.retrieval_score)

        # Le chunk "probleme" porte le texte titre+problème ; on le récupère du
        # chunk lui-même s'il a matché. Si seul le chunk "solution" a matché,
        # probleme_text reste vide — solution_finale (déjà présent sur tous les
        # chunks du ticket) suffit à donner un contexte utile au reranking.
        if payload.get("chunk_type") == "probleme":
            ticket.probleme_text = payload.get("text", "")

    return list(by_ticket.values())


def rerank_candidates(
    question: str, tickets: list[ReconstructedTicket], settings: Settings
) -> list[ReconstructedTicket]:
    """
    Étage 3 : fait rejouer chaque paire (question, TICKET reconstruit) par le
    cross-encoder, trie par score de pertinence décroissant, et ne garde que
    rag_rerank_top_k. Le nombre de paires ici est le nombre de tickets uniques
    après dédoublonnage (étage 2) — toujours ≤ rag_retrieval_top_k, souvent
    nettement moins.

    Si tickets est vide, renvoie une liste vide sans charger le modèle (évite
    un chargement coûteux pour rien si le retrieval n'a rien trouvé).
    """
    if not tickets:
        return []

    reranker = get_reranker_model()

    # probleme_text porte déjà "Titre: ...\nProblème: ..." depuis l'ingestion
    # (voir ingest_glpi.py::build_chunks) — ne pas re-préfixer ici, sous peine
    # de doubler artificiellement la longueur du texte envoyé au cross-encoder
    # et de biaiser le score en faveur des tickets les plus longs.
    pairs = [
        (question, f"{t.probleme_text}\n{t.solution_text}")
        for t in tickets
    ]
    scores = reranker.predict(pairs)

    for ticket, score in zip(tickets, scores):
        ticket.rerank_score = float(score)

    ranked = sorted(tickets, key=lambda t: t.rerank_score, reverse=True)
    return ranked[: settings.rag_rerank_top_k]


def build_context(tickets: list[ReconstructedTicket]) -> str:
    """Assemble les tickets retenus en un bloc de texte lisible, injecté dans le prompt LLM."""
    # probleme_text porte déjà "Titre: ...\nProblème: ..." (voir rerank_candidates
    # ci-dessus) — ne pas re-préfixer ici non plus, même raison.
    blocks = []
    for i, ticket in enumerate(tickets, start=1):
        blocks.append(
            f"--- Ticket {i} (pertinence={ticket.rerank_score:.3f}) ---\n"
            f"{ticket.probleme_text}\n"
            f"{ticket.solution_text}"
        )
    return "\n\n".join(blocks)


def tickets_to_sources(tickets: list[ReconstructedTicket]) -> list[SourceTicket]:
    """
    Convertit les tickets rerankés en SourceTicket pour la réponse API.

    Le score exposé à l'employé est le score de reranking (rerank_score), pas le
    score de fusion RRF du retrieval — c'est lui qui a réellement décidé du
    classement final, donc c'est le plus honnête à afficher pour la traçabilité.
    """
    return [
        SourceTicket(
            ticket_id=ticket.ticket_id,
            titre=ticket.titre,
            score=round(ticket.rerank_score, 3),
        )
        for ticket in tickets
    ]


def ask_ollama(question: str, context: str, settings: Settings) -> str:
    """Appelle l'API locale Ollama (/api/chat) avec le system prompt + contexte RAG + question."""
    prompt = f"Contexte (tickets GLPI similaires) :\n\n{context}\n\nQuestion de l'employé : {question}"

    response = requests.post(
        f"{settings.ollama_host}/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=settings.ollama_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def run_rag_pipeline(question: str) -> tuple[str, str, list[ReconstructedTicket]]:
    """
    Orchestration complète : question -> retrieval hybride Qdrant (chunks) ->
    dédoublonnage/reconstruction par ticket -> reranking cross-encoder (top 3)
    -> contexte -> réponse Ollama.

    Renvoie (answer, context, ranked_tickets) — le contexte et les tickets triés
    sont utiles à l'appelant (app/main.py) pour construire la trace Langfuse et la
    liste des sources sans refaire le pipeline.
    """
    settings = get_settings()

    chunks = retrieve_candidates(question, settings)
    reconstructed_tickets = group_chunks_by_ticket(chunks)
    top_tickets = rerank_candidates(question, reconstructed_tickets, settings)
    context = build_context(top_tickets)
    answer = ask_ollama(question, context, settings)

    return answer, context, top_tickets
