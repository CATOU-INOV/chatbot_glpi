"""
Snowflake (DEVELOPMENT.TCAT.V_RAG_TICKETS) -> Qdrant (glpi_tickets, hybride + chunké)

Pipeline per row:
  1. strip HTML (BeautifulSoup, double-pass — see clean_html) from titre/description/solution
  2. repair UTF-8/Latin-1 mojibake ("Ã©" -> "é") as a safety net — the real fix
     lives upstream in the Sling MariaDB->Snowflake connection charset, but this
     keeps ingestion robust even if that pipeline regresses
  3. anonymize emails and GLPI ticket references in the cleaned text
  4. skip the row if the cleaned solution is < settings.min_solution_length chars
  5. split each ticket into child chunks — "probleme" (titre + description) and
     "solution" (the validated solution). A "suivi" chunk type is reserved for
     followup comments once F_GLPI_ITILFOLLOWUPS is joined into the source view;
     no such rows exist yet, so none are emitted today.
  6. embed each chunk with both a dense model (all-MiniLM-L6-v2) and a sparse
     BM25 model (Qdrant/bm25, via fastembed) — hybrid search needs both.
  7. upsert into Qdrant, batched by 500, id = uuid5(f"{ticket_id}_{solution_rank}_{chunk_type}")
     (Qdrant point IDs must be an unsigned int or UUID; the composite key is
     kept in the payload as "composite_key" for traceability)

Chaque chunk porte, dans son payload :
  - ticket_id        : identifiant du ticket GLPI parent
  - chunk_type        : "probleme" | "solution" | "suivi"
  - text              : texte brut de CE chunk spécifique
  - solution_finale   : texte de la solution validée, dupliqué sur tous les
                         chunks d'un même ticket pour que le contexte envoyé à
                         Ollama reste complet même si un seul chunk "probleme"
                         remonte au retrieval (voir app/rag.py — reconstruction
                         par ticket_id après dédoublonnage)
"""

import os
import re
import sys
import uuid

import snowflake.connector
from bs4 import BeautifulSoup
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app.config import get_settings

settings = get_settings()

BATCH_SIZE = 500

SOURCE_TABLE = "DEVELOPMENT.TCAT.V_RAG_TICKETS"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# GLPI-style ticket references, e.g. "ticket #12345", "TICKET-12345", "inc12345"
TICKET_REF_RE = re.compile(r"\b(?:ticket|inc|req|glpi)[\s#_-]*\d{3,}\b", re.IGNORECASE)
# Real credentials found in solution text (e.g. account creation followups):
# "mot de passe : Azerty2024!", "password: hunter2". Requires an explicit
# ":"/"=" separator before the value — this is what distinguishes an actual
# credential from a sentence merely mentioning "mot de passe" conceptually
# ("changez votre mot de passe"), which must NOT be redacted or truncated.
PASSWORD_RE = re.compile(
    r"(?:mot\s*de\s*passe|mdp|password|pwd)(?:\s+est)?\s*[:=]\s*\S+",
    re.IGNORECASE,
)
# Technician signatures at the end of a solution ("Cordialement, Julien" /
# "Bonne journée, Camille"). These are archived staff names, not current
# contacts — left in the indexed text, the LLM tends to recommend contacting
# them by name (observed behavior with qwen2.5:3b, confirmed not reliably
# fixable via system prompt alone even with an explicit instruction). Only
# strips the name right after a known closing phrase — never touches a name
# elsewhere in the free text (e.g. a customer's own name in the problem
# description). Skips "<phrase> <Name> du service ..." — a role-qualified
# signature ("Camille du service clients") reads as a legitimate service
# identity rather than a specific person to redact.
SIGNATURE_RE = re.compile(
    r"(Cordialement|Bonne\s+journ[ée]e|Bien\s+[àa]\s+vous|Belle\s+journ[ée]e)"
    r"\s*[,:.]?\s+"
    r"[A-Z][a-zà-ÿ]+(?:-[A-Z][a-zà-ÿ]+)?\b"
    r"(?!\s+du\s+service)",
)
# GLPI form boilerplate: descriptions are submitted through a structured form
# ("Données du formulaire ... 1) Titre : ... 2) Urgence : ... N) Description :
# <free text> N+1) Pièce jointe : Pas de document rattaché") — the numbered
# field labels are near-identical across every ticket and carry no semantic
# signal, only diluting both the dense embedding and the BM25 sparse score.
# Extract just the free-text "Description" field, which is where the actual
# problem is described.
FORM_DESCRIPTION_RE = re.compile(
    r"Description\s*:\s*(.+?)(?=\s*\d+\)\s*Pi[eè]ce\s*jointe|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def fix_mojibake(text: str) -> str:
    """
    Repair the classic UTF-8-decoded-as-Latin-1 double-encoding bug (e.g. "Ã©" -> "é").

    Root cause historically lived in the Sling MariaDB->Snowflake connection (missing
    charset=utf8mb4 on the source), so once that's fixed upstream this becomes a no-op
    on clean data. Kept here as a safety net: if the round-trip isn't valid mojibake
    (e.g. the text is already correct UTF-8 with real accents), the encode/decode
    raises and we simply return the original text untouched.
    """
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def clean_html(raw_html: str | None) -> str:
    """
    Repair mojibake, decode HTML entities, strip tags, collapse whitespace.

    The source HTML is double-encoded: it contains numeric entities like "&#60;"
    which, once decoded, reveal *real* HTML tags ("<div>") rather than literal text.
    A single BeautifulSoup pass only performs the entity decoding — it doesn't
    re-parse its own output — so the newly-revealed tags are left behind as plain
    text. Parsing twice (decode entities, then strip the tags that decoding
    exposed) is required to get clean text out.
    """
    if not raw_html:
        return ""
    raw_html = fix_mojibake(raw_html)

    # First pass: decode HTML entities (&#60; -> <), which reveals real tags.
    first_pass = BeautifulSoup(raw_html, "html.parser").get_text()

    # Second pass: strip the tags that the first pass just revealed.
    text = BeautifulSoup(first_pass, "html.parser").get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def anonymize(text: str) -> str:
    """Replace emails, ticket references, and credentials with placeholders."""
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = TICKET_REF_RE.sub("[TICKET_REF]", text)
    text = PASSWORD_RE.sub("[PASSWORD]", text)
    return text


def redact_signatures(text: str) -> str:
    """
    Masque le prénom d'un technicien dans une signature de fin de solution
    ("Cordialement, Julien" -> "Cordialement [SIGNATURE]"), sans toucher au
    reste du texte. Ne s'applique volontairement qu'au texte de solution — le
    texte du problème initial est écrit par le client, pas par un technicien.
    """
    if not text:
        return text
    return SIGNATURE_RE.sub(lambda m: f"{m.group(1)} [SIGNATURE]", text)


def strip_form_boilerplate(text: str) -> str:
    """
    Extrait le champ "Description" libre d'une description GLPI structurée par
    formulaire, en retirant le squelette répétitif ("Données du formulaire",
    "1) Titre : ...", "2) Urgence : ...", "N+1) Pièce jointe : ...").

    Si le motif ne matche pas (texte déjà libre, ou forme de formulaire
    différente), le texte original est renvoyé intact — pas de perte
    silencieuse de contenu en cas de format inattendu.
    """
    if not text:
        return text
    match = FORM_DESCRIPTION_RE.search(text)
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    return text


def load_private_key_der(key_path: str, passphrase: str | None) -> bytes:
    """Read a PEM private key file and return DER bytes for the Snowflake connector."""
    with open(key_path, "rb") as f:
        pem_bytes = f.read()

    private_key = serialization.load_pem_private_key(
        pem_bytes,
        password=passphrase.encode() if passphrase else None,
        backend=default_backend(),
    )
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


def get_snowflake_connection():
    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")

    if key_path:
        passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None
        private_key_der = load_private_key_der(key_path, passphrase)
        return snowflake.connector.connect(
            user=os.environ["SNOWFLAKE_USER"],
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            private_key=private_key_der,
            database=os.environ.get("SNOWFLAKE_DATABASE", "DEVELOPMENT"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA", "TCAT"),
        )

    return snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        database=os.environ.get("SNOWFLAKE_DATABASE", "DEVELOPMENT"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "TCAT"),
    )


def fetch_rows(conn):
    limit = os.environ.get("INGEST_LIMIT")
    limit_clause = f"LIMIT {int(limit)}" if limit else ""

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT
            ticket_id,
            titre,
            description_html,
            solution_html,
            type_solution,
            solution_status,
            categorie_id,
            date_creation,
            solution_rank
        FROM {SOURCE_TABLE}
        {limit_clause}
        """
    )
    columns = [c[0].lower() for c in cursor.description]
    for row in cursor:
        yield dict(zip(columns, row))
    cursor.close()


def build_chunks(row: dict) -> list[dict] | None:
    """
    Découpe une ligne Snowflake nettoyée en chunks "enfants" indépendants.

    Renvoie None si la ligne doit être filtrée (solution trop courte une fois
    nettoyée). Sinon, renvoie une liste de 1 à N chunks — aujourd'hui toujours
    2 ("probleme" et "solution"), car la vue source n'expose pas encore les
    suivis GLPI (voir F_GLPI_ITILFOLLOWUPS, pas encore joint à V_RAG_TICKETS).

    Chaque chunk porte le texte du ticket ENTIER dans "solution_finale", pour
    que le contexte reconstruit côté RAG reste complet même si un seul chunk
    de ce ticket a été retrouvé par le retrieval (voir app/rag.py).
    """
    titre = anonymize(clean_html(row.get("titre")))
    description = anonymize(strip_form_boilerplate(clean_html(row.get("description_html"))))
    solution = redact_signatures(anonymize(clean_html(row.get("solution_html"))))

    if len(solution) < settings.min_solution_length:
        return None

    ticket_id = row["ticket_id"]
    solution_rank = row.get("solution_rank") or 0
    shared_payload = {
        "ticket_id": ticket_id,
        "solution_rank": solution_rank,
        "titre": titre,
        "solution_finale": solution,
        "type_solution": row.get("type_solution"),
        "solution_status": row.get("solution_status"),
        "categorie_id": row.get("categorie_id"),
        "date_creation": str(row.get("date_creation")) if row.get("date_creation") else None,
    }

    probleme_text = f"Titre: {titre}\nProblème: {description}"
    solution_text = f"Solution: {solution}"

    chunks = [
        {"chunk_type": "probleme", "text": probleme_text},
        {"chunk_type": "solution", "text": solution_text},
    ]

    out = []
    for chunk in chunks:
        # Qdrant point IDs must be an unsigned int or a UUID — derive a
        # deterministic UUID from the composite key so re-ingesting the same
        # ticket/solution/chunk triple overwrites the existing point instead
        # of duplicating it.
        composite_key = f"{ticket_id}_{solution_rank}_{chunk['chunk_type']}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, composite_key))
        out.append(
            {
                "id": point_id,
                "composite_key": composite_key,
                "text": chunk["text"],
                "chunk_type": chunk["chunk_type"],
                **shared_payload,
            }
        )
    return out


def ensure_collection(client: QdrantClient):
    """
    Crée la collection avec deux named vectors : un dense (bi-encoder, cosinus)
    et un sparse (BM25, pour la recherche hybride) — voir app/rag.py pour la
    requête de fusion des deux au moment du retrieval.
    """
    if client.collection_exists(settings.qdrant_collection):
        return

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            settings.dense_vector_name: qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            settings.sparse_vector_name: qmodels.SparseVectorParams(
                modifier=qmodels.Modifier.IDF,
            ),
        },
    )


def main():
    print("Connecting to Snowflake...", file=sys.stderr)
    conn = get_snowflake_connection()

    print(f"Loading dense embedding model {settings.embedding_model_name}...", file=sys.stderr)
    dense_model = SentenceTransformer(settings.embedding_model_name)

    print(f"Loading sparse embedding model {settings.sparse_model_name}...", file=sys.stderr)
    sparse_model = SparseTextEmbedding(model_name=settings.sparse_model_name)

    print(f"Connecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}...", file=sys.stderr)
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    ensure_collection(qdrant)

    batch_texts: list[str] = []
    batch_meta: list[dict] = []

    total_rows_seen = 0
    total_rows_skipped = 0
    total_chunks_ingested = 0

    def flush_batch():
        nonlocal batch_texts, batch_meta
        if not batch_texts:
            return

        dense_vectors = dense_model.encode(batch_texts, show_progress_bar=False)
        sparse_vectors = list(sparse_model.embed(batch_texts))

        points = [
            qmodels.PointStruct(
                id=meta["id"],
                vector={
                    settings.dense_vector_name: dense_vec.tolist(),
                    settings.sparse_vector_name: qmodels.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=meta,
            )
            for dense_vec, sparse_vec, meta in zip(dense_vectors, sparse_vectors, batch_meta)
        ]
        qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
        batch_texts = []
        batch_meta = []

    for row in tqdm(fetch_rows(conn), desc="Ingesting tickets"):
        total_rows_seen += 1

        chunks = build_chunks(row)
        if chunks is None:
            total_rows_skipped += 1
            continue

        for chunk_meta in chunks:
            batch_texts.append(chunk_meta["text"])
            batch_meta.append(chunk_meta)
            total_chunks_ingested += 1

            if len(batch_texts) >= BATCH_SIZE:
                flush_batch()

    flush_batch()
    conn.close()

    print(
        f"\nDone. Tickets seen: {total_rows_seen} | "
        f"Skipped (solution < {settings.min_solution_length} chars): {total_rows_skipped} | "
        f"Chunks ingested: {total_chunks_ingested}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
