"""RAG (Retrieval-Augmented Generation) service.

Uses FastEmbed (BAAI/bge-small-en-v1.5, 384-dim ONNX) to embed document
chunks on ingestion and retrieve the most semantically relevant ones at query
time via in-process cosine similarity (compatible with self-hosted MongoDB).
"""

from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache
from typing import Any

import numpy as np
from fastembed import TextEmbedding

from apps.backend.db.mongo import get_db

# ---------------------------------------------------------------------------
# Embedding singleton
# ---------------------------------------------------------------------------

_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
_EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_embedding_model() -> TextEmbedding:
    """Return (and lazily initialize) the FastEmbed model singleton."""
    print(f"📦 Loading FastEmbed model '{_EMBEDDING_MODEL}'...")
    model = TextEmbedding(model_name=_EMBEDDING_MODEL)
    print("✅ FastEmbed model ready.")
    return model


def _embed_sync(texts: list[str]) -> list[list[float]]:
    """Generate embeddings synchronously (blocking). Must run in a thread."""
    model = _get_embedding_model()
    # fastembed returns a generator of np.ndarray
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Async wrapper: runs blocking FastEmbed inference in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_sync, texts)


# ---------------------------------------------------------------------------
# Cosine similarity helper
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def ingest_document(
    title: str,
    content: str,
    session_id: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Ingest a knowledge document into MongoDB with per-chunk embeddings.

    When *session_id* is provided the document is scoped to that chat session
    and will be returned only by searches filtered on the same session.
    """
    db = get_db()
    doc_id = str(uuid.uuid4())

    # Chunk the document (~150 words, 25-word overlap)
    words = content.split()
    chunk_size = 150
    overlap = 25
    chunk_texts: list[str] = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk_texts.append(" ".join(words[i : i + chunk_size]))

    if not chunk_texts:
        chunk_texts = [content]

    # Embed all chunks in a single batch call
    embeddings = await embed_texts(chunk_texts)

    chunks = [
        {
            "chunk_id": str(uuid.uuid4()),
            "text": text,
            "embedding": emb,
            "metadata": metadata or {},
        }
        for text, emb in zip(chunk_texts, embeddings)
    ]

    doc: dict[str, Any] = {
        "_id": doc_id,
        "title": title,
        "content": content,
        "chunks": chunks,
    }
    if session_id:
        doc["session_id"] = session_id

    await db.documents.insert_one(doc)
    return doc


async def search_relevant_chunks(
    query: str,
    session_id: str | None = None,
    limit: int = 3,
    fetch_limit: int = 200,
) -> list[dict[str, Any]]:
    """Retrieve the most semantically relevant document chunks for *query*.

    When *session_id* is provided, only documents scoped to that session are
    searched.  Otherwise all documents are considered.
    """
    if not query.strip():
        return []

    # Embed the query
    query_emb = (await embed_texts([query]))[0]

    db = get_db()
    projection = {"title": 1, "chunks.text": 1, "chunks.embedding": 1, "chunks.chunk_id": 1}
    query_filter: dict[str, Any] = {"session_id": session_id} if session_id else {}
    cursor = db.documents.find(query_filter, projection).limit(fetch_limit)

    scored: list[dict[str, Any]] = []
    query_terms = set(query.lower().split())

    async for doc in cursor:
        title = doc.get("title", "")
        for chunk in doc.get("chunks", []):
            text: str = chunk.get("text", "")
            emb: list[float] | None = chunk.get("embedding")

            if emb:
                score = _cosine_similarity(query_emb, emb)
            else:
                # Keyword-overlap fallback for pre-upgrade chunks
                words = set(text.lower().split())
                overlap_count = len(query_terms & words)
                score = overlap_count / max(len(query_terms), 1) * 0.5  # scale to <1

            scored.append({"text": text, "title": title, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


async def session_has_documents(session_id: str) -> bool:
    """Return True if at least one document is scoped to *session_id*."""
    db = get_db()
    doc = await db.documents.find_one({"session_id": session_id}, {"_id": 1})
    return doc is not None


async def get_session_documents(session_id: str) -> list[dict[str, Any]]:
    """Return lightweight document metadata for a session (no chunks)."""
    db = get_db()
    projection = {"_id": 1, "title": 1, "session_id": 1}
    cursor = db.documents.find({"session_id": session_id}, projection)
    docs: list[dict[str, Any]] = []
    async for doc in cursor:
        docs.append(doc)
    return docs


async def delete_session_documents(session_id: str) -> int:
    """Delete all documents scoped to *session_id*. Returns deleted count."""
    db = get_db()
    result = await db.documents.delete_many({"session_id": session_id})
    return result.deleted_count
