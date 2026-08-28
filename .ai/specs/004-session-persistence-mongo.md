# Spec 004: Chat Session Persistence with MongoDB & Motor

## Status: Implemented & Verified

## Overview
Stores user chat sessions, message histories, and document embeddings in MongoDB using Motor's asynchronous non-blocking driver.

## Requirements
1. **Containerized Database**:
   - Official `mongo:7.0` container managed via `docker-compose.yml` with persistent volume `voice_chat_mongodb_data`.
2. **Collections & Schemas**:
   - `sessions`: `{ _id: string, session_id: string, user_id: string, title: string, created_at: string, last_active: string }`
   - `messages`: `{ _id: string, message_id: string, session_id: string, role: "user" | "assistant", text: string, timestamp: string, audio_url?: string }`
   - `documents`: `{ _id: string, title: string, content: string, chunks: [ { chunk_id, text, metadata } ], created_at: string }`
3. **Indexing**:
   - Index on `sessions.last_active` for fast sorted drawer listing.
   - Compound index on `messages (session_id, timestamp)` for rapid conversation history loading.
4. **Lifecycle Management**:
   - Client connection initialized in FastAPI `lifespan` startup, closed on shutdown.

## API Contracts
- `GET /api/sessions`: Returns list of user sessions sorted by recent activity.
- `POST /api/sessions`: Creates a new session `{ title?: string, user_id?: string }`.
- `PATCH /api/sessions/{session_id}`: Updates session metadata, such as renaming `{ title: string }`.
- `GET /api/sessions/{session_id}/messages`: Returns chronological message list for session.
- `DELETE /api/sessions/{session_id}`: Cascading deletion of session and its messages.
