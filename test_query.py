"""
question -> embed -> Qdrant top-5 -> Ollama (local) -> answer

100% local : aucune donnée ne sort vers un service cloud externe.
Nécessite Ollama installé et lancé (https://ollama.com), avec le modèle
OLLAMA_MODEL déjà téléchargé (`ollama pull qwen2.5:3b`).
"""

import os

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "glpi_tickets")

SYSTEM_PROMPT = """Tu es un assistant qui aide les employés de l'entreprise à résoudre leurs problèmes \
avec l'outil GLPI (helpdesk interne), en te basant sur des tickets similaires résolus par le passé.

Réponds uniquement à partir du contexte fourni (tickets + solutions). Si le contexte ne permet pas \
de répondre avec certitude, dis-le clairement plutôt que d'inventer une réponse. Sois concis et \
donne des étapes concrètes quand c'est possible."""


def search_similar_tickets(client: QdrantClient, model: SentenceTransformer, question: str, top_k: int = TOP_K):
    query_vector = model.encode(question).tolist()
    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
    ).points
    return results


def build_context(results) -> str:
    blocks = []
    for i, point in enumerate(results, start=1):
        payload = point.payload or {}
        blocks.append(
            f"--- Ticket {i} (score={point.score:.3f}) ---\n"
            f"Titre: {payload.get('titre', '')}\n"
            f"Problème: {payload.get('description', '')}\n"
            f"Solution: {payload.get('solution', '')}"
        )
    return "\n\n".join(blocks)


def ask_ollama(question: str, context: str) -> str:
    prompt = (
        f"Contexte (tickets GLPI similaires) :\n\n{context}\n\n"
        f"Question de l'employé : {question}"
    )
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def main():
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    question = input("Question : ").strip()
    if not question:
        print("Question vide, arrêt.")
        return

    results = search_similar_tickets(qdrant, embedder, question)
    if not results:
        print("Aucun ticket similaire trouvé dans la base.")
        return

    context = build_context(results)
    answer = ask_ollama(question, context)

    print("\n=== Réponse ===\n")
    print(answer)

    print("\n=== Tickets sources ===")
    for point in results:
        payload = point.payload or {}
        print(f"- ticket_id={payload.get('ticket_id')} (score={point.score:.3f}): {payload.get('titre')}")


if __name__ == "__main__":
    main()
