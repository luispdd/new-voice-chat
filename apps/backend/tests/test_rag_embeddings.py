"""Tests for the FastEmbed-powered RAG service (session-scoped).

Uses mock MongoDB for async operations so no real MongoDB connection
is required. All embedding calls run the real fastembed model to verify
correct behaviour end-to-end.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db(documents: list[dict]) -> MagicMock:
    """Build a minimal async Motor db mock that supports find().limit()."""
    mock_db = MagicMock()

    async def _async_gen(docs):
        for doc in docs:
            yield doc

    # find() returns an object whose .limit() returns an async iterable
    def _find_side_effect(query_filter=None, projection=None):
        filtered = documents
        if query_filter:
            filtered = [
                d for d in documents
                if all(d.get(k) == v for k, v in query_filter.items())
            ]
        cursor_mock = MagicMock()
        cursor_mock.limit.return_value = _async_gen(filtered)
        # Make cursor itself async-iterable (for find without .limit())
        cursor_mock.__aiter__ = lambda self: _async_gen(filtered).__aiter__()
        cursor_mock.__anext__ = lambda self: _async_gen(filtered).__anext__()
        return cursor_mock

    mock_db.documents.find.side_effect = _find_side_effect
    mock_db.documents.find_one = AsyncMock(return_value=None)
    mock_db.documents.insert_one = AsyncMock(return_value=None)
    mock_db.documents.delete_many = AsyncMock(
        return_value=MagicMock(deleted_count=0)
    )
    return mock_db


# ---------------------------------------------------------------------------
# Embedding shape tests (real fastembed, no MongoDB)
# ---------------------------------------------------------------------------

class TestEmbedTexts(unittest.TestCase):
    def test_single_text_returns_384_dim(self):
        from apps.backend.services.rag import embed_texts
        result = asyncio.run(embed_texts(["Hello world"]))
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 384)

    def test_batch_returns_correct_count(self):
        from apps.backend.services.rag import embed_texts
        texts = ["first sentence", "second sentence", "third sentence"]
        result = asyncio.run(embed_texts(texts))
        self.assertEqual(len(result), 3)
        for emb in result:
            self.assertEqual(len(emb), 384)

    def test_values_are_floats(self):
        from apps.backend.services.rag import embed_texts
        result = asyncio.run(embed_texts(["sample text"]))
        for val in result[0]:
            self.assertIsInstance(val, float)


# ---------------------------------------------------------------------------
# Cosine similarity tests (no network/DB)
# ---------------------------------------------------------------------------

class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        from apps.backend.services.rag import _cosine_similarity
        v = [1.0, 0.0, 0.5]
        self.assertAlmostEqual(_cosine_similarity(v, v), 1.0, places=5)

    def test_opposite_vectors_score_minus_one(self):
        from apps.backend.services.rag import _cosine_similarity
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        self.assertAlmostEqual(_cosine_similarity(a, b), -1.0, places=5)

    def test_zero_vector_returns_zero(self):
        from apps.backend.services.rag import _cosine_similarity
        a = [0.0, 0.0]
        b = [1.0, 0.5]
        self.assertEqual(_cosine_similarity(a, b), 0.0)


# ---------------------------------------------------------------------------
# ingest_document tests (session-scoped)
# ---------------------------------------------------------------------------

class TestIngestDocument(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_ingest_stores_embeddings_in_chunks(self):
        """Each chunk in the persisted document must have an 'embedding' field."""
        mock_db = _make_mock_db([])

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import ingest_document
            doc = self._run(
                ingest_document(
                    title="Test Doc",
                    content="The quick brown fox jumps over the lazy dog. " * 10,
                )
            )

        mock_db.documents.insert_one.assert_called_once()
        inserted = mock_db.documents.insert_one.call_args[0][0]

        for chunk in inserted["chunks"]:
            self.assertIn("embedding", chunk)
            self.assertEqual(len(chunk["embedding"]), 384)

    def test_ingest_with_session_id_stores_it(self):
        """When session_id is provided, it must be stored on the document."""
        mock_db = _make_mock_db([])

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import ingest_document
            doc = self._run(
                ingest_document(
                    title="Scoped Doc",
                    content="Some content here.",
                    session_id="session-abc",
                )
            )

        inserted = mock_db.documents.insert_one.call_args[0][0]
        self.assertEqual(inserted["session_id"], "session-abc")

    def test_ingest_without_session_id_omits_field(self):
        """Without session_id, the field should not be present."""
        mock_db = _make_mock_db([])

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import ingest_document
            doc = self._run(ingest_document(title="Global", content="Global knowledge."))

        inserted = mock_db.documents.insert_one.call_args[0][0]
        self.assertNotIn("session_id", inserted)

    def test_ingest_short_content_produces_single_chunk(self):
        mock_db = _make_mock_db([])

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import ingest_document
            doc = self._run(ingest_document(title="Short", content="Short text."))

        inserted = mock_db.documents.insert_one.call_args[0][0]
        self.assertEqual(len(inserted["chunks"]), 1)


# ---------------------------------------------------------------------------
# search_relevant_chunks tests (session-scoped)
# ---------------------------------------------------------------------------

class TestSearchRelevantChunks(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def _make_db_with_embedded_doc(
        self, chunk_texts: list[str], title: str = "Doc", session_id: str | None = None
    ) -> MagicMock:
        """Pre-embed chunk_texts and return a mock DB containing them."""
        from apps.backend.services.rag import _embed_sync
        embeddings = _embed_sync(chunk_texts)
        doc: dict = {
            "_id": "test-id",
            "title": title,
            "chunks": [
                {"chunk_id": f"c{i}", "text": t, "embedding": e}
                for i, (t, e) in enumerate(zip(chunk_texts, embeddings))
            ],
        }
        if session_id:
            doc["session_id"] = session_id
        return _make_mock_db([doc])

    def test_returns_at_most_limit_results(self):
        mock_db = self._make_db_with_embedded_doc(
            ["Python is a programming language.", "Cats are mammals.", "Paris is in France."],
            session_id="s1",
        )
        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import search_relevant_chunks
            results = self._run(search_relevant_chunks("programming", session_id="s1", limit=2))

        self.assertLessEqual(len(results), 2)

    def test_semantic_similarity_cat_feline(self):
        """Query 'feline animal' should rank the cat chunk highest."""
        mock_db = self._make_db_with_embedded_doc(
            [
                "A cat is a small feline domestic animal.",
                "Python is a high-level programming language.",
                "The Eiffel Tower is located in Paris.",
            ],
            session_id="s1",
        )
        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import search_relevant_chunks
            results = self._run(search_relevant_chunks("feline animal", session_id="s1", limit=3))

        self.assertTrue(len(results) > 0)
        self.assertIn("cat", results[0]["text"].lower())

    def test_session_scoping_excludes_other_sessions(self):
        """Documents from other sessions should not appear in results."""
        from apps.backend.services.rag import _embed_sync

        embeddings_s1 = _embed_sync(["Cats are fluffy animals."])
        embeddings_s2 = _embed_sync(["Dogs are loyal pets."])

        docs = [
            {
                "_id": "doc-s1",
                "title": "Cat Doc",
                "session_id": "session-1",
                "chunks": [{"chunk_id": "c0", "text": "Cats are fluffy animals.", "embedding": embeddings_s1[0]}],
            },
            {
                "_id": "doc-s2",
                "title": "Dog Doc",
                "session_id": "session-2",
                "chunks": [{"chunk_id": "c1", "text": "Dogs are loyal pets.", "embedding": embeddings_s2[0]}],
            },
        ]
        mock_db = _make_mock_db(docs)

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import search_relevant_chunks
            results = self._run(search_relevant_chunks("pets animals", session_id="session-1", limit=5))

        # Only session-1 docs should appear
        for r in results:
            self.assertEqual(r["title"], "Cat Doc")

    def test_empty_query_returns_empty(self):
        mock_db = self._make_db_with_embedded_doc(["Some content"], session_id="s1")
        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import search_relevant_chunks
            results = self._run(search_relevant_chunks("   ", session_id="s1", limit=3))

        self.assertEqual(results, [])

    def test_results_sorted_by_descending_score(self):
        mock_db = self._make_db_with_embedded_doc(
            [
                "Deep learning is a subset of machine learning.",
                "Neural networks are used in deep learning.",
                "The weather today is sunny and warm.",
            ],
            session_id="s1",
        )
        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import search_relevant_chunks
            results = self._run(search_relevant_chunks("machine learning neural network", session_id="s1", limit=3))

        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ---------------------------------------------------------------------------
# session_has_documents / delete_session_documents tests
# ---------------------------------------------------------------------------

class TestSessionDocumentHelpers(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_session_has_documents_true(self):
        mock_db = MagicMock()
        mock_db.documents.find_one = AsyncMock(return_value={"_id": "doc1"})

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import session_has_documents
            result = self._run(session_has_documents("s1"))

        self.assertTrue(result)
        mock_db.documents.find_one.assert_called_once_with({"session_id": "s1"}, {"_id": 1})

    def test_session_has_documents_false(self):
        mock_db = MagicMock()
        mock_db.documents.find_one = AsyncMock(return_value=None)

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import session_has_documents
            result = self._run(session_has_documents("empty-session"))

        self.assertFalse(result)

    def test_delete_session_documents(self):
        mock_db = MagicMock()
        mock_db.documents.delete_many = AsyncMock(
            return_value=MagicMock(deleted_count=3)
        )

        with patch("apps.backend.services.rag.get_db", return_value=mock_db):
            from apps.backend.services.rag import delete_session_documents
            count = self._run(delete_session_documents("s1"))

        self.assertEqual(count, 3)
        mock_db.documents.delete_many.assert_called_once_with({"session_id": "s1"})


if __name__ == "__main__":
    unittest.main()
