"""RAG (Retrieval-Augmented Generation) service for MongoDB documents."""

from typing import Any
import uuid
from apps.backend.db.mongo import get_db


async def ingest_document(title: str, content: str, metadata: dict | None = None) -> dict[str, Any]:
    """Ingest a knowledge document into MongoDB."""
    db = get_db()
    doc_id = str(uuid.uuid4())

    # Split into chunks of ~300 words
    words = content.split()
    chunks = []
    chunk_size = 150
    overlap = 25

    for i in range(0, len(words), chunk_size - overlap):
        chunk_text = " ".join(words[i : i + chunk_size])
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": chunk_text,
            "metadata": metadata or {},
        })

    doc = {
        "_id": doc_id,
        "title": title,
        "content": content,
        "chunks": chunks,
    }
    await db.documents.insert_one(doc)
    return doc


async def search_relevant_chunks(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search for relevant document chunks in MongoDB."""
    db = get_db()
    # Simple keyword/text matching fallback for MongoDB collections
    cursor = db.documents.find().limit(5)
    results = []
    query_terms = set(query.lower().split())

    async for doc in cursor:
        for chunk in doc.get("chunks", []):
            text = chunk.get("text", "")
            words = set(text.lower().split())
            score = len(query_terms.intersection(words))
            if score > 0:
                results.append({"text": text, "title": doc.get("title"), "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
