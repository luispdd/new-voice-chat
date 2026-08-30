# Spec 005: RAG Document Ingestion & Knowledge Retrieval

## Status: Implemented & Verified

## Overview
Provides Retrieval-Augmented Generation (RAG) capabilities allowing users to upload and attach text/markdown reference documents (`.txt`, `.md`) to specific chat sessions. Uploaded documents are parsed, chunked, and converted into dense vector embeddings using local FastEmbed inference (`BAAI/bge-small-en-v1.5`). During conversations with attached documents, relevant document chunks are automatically retrieved via cosine similarity and injected into the LLM system prompt context to ground the assistant's replies.

## Requirements

### 1. Document Ingestion & Validation
- **Supported File Types**: `.txt` and `.md` plain text files encoded in UTF-8. Non-text or unsupported file extensions are rejected with HTTP 400.
- **Session Scoping**: Documents are explicitly associated with a `session_id`.
- **Text Chunking**: Documents are split into overlapping text chunks (~150 words per chunk with a 25-word overlap) to preserve semantic context across chunk boundaries.
- **Embedding Generation**:
  - Employs `fastembed` (`BAAI/bge-small-en-v1.5`) as a lightweight, local ONNX-based embedding engine.
  - Generates 384-dimensional dense float vector embeddings for each chunk.
  - Asynchronous thread pool offloading (`asyncio.get_event_loop().run_in_executor`) to prevent blocking the FastAPI async event loop during CPU inference.
- **Persistence Schema**:
  - Saved in MongoDB `documents` collection:
    ```json
    {
      "_id": "uuid-string",
      "title": "filename.txt",
      "content": "raw content string",
      "session_id": "session-uuid",
      "chunks": [
        {
          "chunk_id": "uuid-string",
          "text": "chunk text content...",
          "embedding": [0.012, -0.045, ...],
          "metadata": { "chunk_index": 0 }
        }
      ],
      "created_at": "ISO-8601 timestamp"
    }
    ```

### 2. Session Lifecycle & Cascade Deletion
- **Indexing**: A dedicated index on `documents.session_id` enables fast lookup and efficient deletion.
- **Cascade Deletion**: When a session is deleted via `DELETE /api/sessions/{session_id}`, all associated documents in the `documents` collection are deleted concurrently with the session messages.
- **Session Document Querying**: Check for presence of documents via `session_has_documents(session_id)` and list documents via `get_session_documents(session_id)`.

### 3. Context Retrieval & Semantic Ranking
- **Query Embedding**: User input text is converted into a 384-dimensional query vector using FastEmbed.
- **Cosine Similarity Search**:
  - Evaluates dot-product / cosine similarity between the query embedding and chunk embeddings belonging to the target `session_id`.
  - Sorts chunks by similarity score in descending order.
  - Returns top-$K$ scoring chunks (default $K=3$).

### 4. Automatic Prompt Augmentation (Auto-RAG)
- **Auto-Activation**: RAG automatically activates when the active session contains one or more attached documents. No manual toggle is required by the user.
- **Prompt Injection**:
  - Formats retrieved chunks into context:
    ```
    Use the following knowledge context to answer:
    [document1.txt]: Relevant chunk text...

    [document2.md]: Another relevant chunk text...
    ```
  - Appends context to the centralized system prompt across all communication channels:
    - REST `/api/chat`
    - WebSocket `/ws/chat` (real-time voice & token streaming)

### 5. Frontend UI Integration
- **File Attachment**:
  - Attachment button (`pi-paperclip`) in the chat input bar allowing selection of `.txt` or `.md` files.
  - Hidden file input triggering `POST /api/sessions/{session_id}/documents`.
  - Loading spinner indicator during file upload and embedding generation.
- **Attached Document Counter**:
  - Header badge displaying the number of attached files for the active session (e.g. `2 docs`).
- **Session Switching**:
  - Switching sessions dynamically fetches and updates the active document list and badge count.
- **Chat Feedback**:
  - Assistant confirmation message inserted into chat history upon successful document ingestion.

## API Contracts

### `POST /api/sessions/{session_id}/documents`
- **Description**: Uploads and attaches a `.txt` or `.md` file to a chat session.
- **Content-Type**: `multipart/form-data` (`file: UploadFile`)
- **Response** (200 OK):
  ```json
  {
    "status": "ingested",
    "document": {
      "_id": "doc-uuid",
      "title": "notes.md",
      "session_id": "session-uuid",
      "chunk_count": 4
    }
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Unsupported file type, non-UTF-8 content, or empty file.
  - `404 Not Found`: Session does not exist.

### `GET /api/sessions/{session_id}/documents`
- **Description**: Retrieves all documents attached to a specific session.
- **Response** (200 OK):
  ```json
  {
    "documents": [
      {
        "_id": "doc-uuid",
        "title": "notes.md",
        "session_id": "session-uuid",
        "chunk_count": 4,
        "created_at": "2026-08-30T10:00:00Z"
      }
    ]
  }
  ```

### `POST /api/documents` (Legacy / Global)
- **Description**: Ingests raw text into a global knowledge base.
- **Request**: `{ "title": string, "content": string }`
- **Response**: `{ "status": "ingested", "document": Document }`
