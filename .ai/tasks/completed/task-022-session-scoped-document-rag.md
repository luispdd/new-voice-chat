# Task 022: Session-Scoped Document RAG

- **Status**: Completed
- **Target Component**: `apps/backend/services/rag.py`, `apps/backend/server.py`, `apps/backend/db/mongo.py`, `apps/frontend/`
- **Spec Reference**: [005-rag-knowledge-retrieval.md](../../specs/005-rag-knowledge-retrieval.md)

## Objective
Enable file attachment (`.txt`/`.md`) to chat sessions. Documents are chunked, embedded with FastEmbed, and stored with `session_id` scope. RAG auto-activates on every message when the session has documents. Deleting a session cascade-deletes its documents.
