# Spec 001: Core Text Chat & Multi-Provider LLM Streaming

## Status: Implemented & Verified

## Overview
Provides text-based conversation capabilities supporting real-time token streaming and flexible backend connectivity across local and cloud LLM providers (LM Studio, Ollama, OpenRouter, OpenAI).

## Requirements
1. **Multi-Provider Support**:
   - `openai`: Default engine running on `http://127.0.0.1:8888/v1` with default model `unsloth/qwen3.5-4B-GGUF` (also supports cloud OpenAI API `https://api.openai.com/v1` or any OpenAI-compatible server).
   - `lmstudio`: Local engine running on `http://127.0.0.1:1234/v1` (e.g. `google/gemma-3-4b-it-qat`).
   - `ollama`: Local engine on `http://127.0.0.1:11434/v1` (e.g. `llama3`).
   - `openrouter`: Multi-model aggregator (`https://openrouter.ai/api/v1`).
   - Default values can be overridden via CLI parameters (`--engine`, `--base-url`, `--model`, `--api-key`).
2. **Streaming Protocol**:
   - REST `/api/chat` with SSE (`text/event-stream`).
   - WebSocket `/ws/chat` for bi-directional live token streaming and simultaneous sentence-level voice synthesis.
3. **Prompt Design & Voice Constraints**:
   - System prompt tailored for voice-first interactions: concise, conversational, and natural phrasing.
   - Explicit negative instructions preventing the LLM from outputting:
     - Emojis (e.g. `😊`, `🚀`, `👍`) or ASCII emoticons (e.g. `:)`, `xD`, `<3`).
     - Markdown formatting like asterisks (`*`, `**`), underscores (`_`), hash headers (`#`), backticks (`` ` ``), bullet lists, or tables.
     - Unreadable unicode characters, decorative symbols, ASCII art, or code snippets unless requested.
   - Enforced consistently across REST `/api/chat` (including RAG context injection) and WebSocket `/ws/chat`.
4. **Error Handling & Provider Diagnostics**:
   - The backend must provide clean, user-friendly error messages indicating the service provider and the reason of the error when the LLM service is offline, unreachable, or encounters an issue.
   - Error messages yielded during streaming or REST chat must start with `[Error: ...]` to enable automatic frontend error styling (`is_error: true`), and are sanitized and narrated aloud via TTS for clear voice companion feedback.
5. **Conversation history & Context Window**:
   - The user can create, rename and delete conversations.
   - The conversations should be displayed in the sidebar.
   - The user can switch between conversations.
   - The user can view the conversation history.
   - **Context Window History**: The backend retrieves up to the latest **100 messages** (`limit=100`, ~50 conversational turns) from the active session to form the LLM conversation prompt context, optimizing memory retention while preserving low latency and staying within model context windows.
6. **UI**:
   - The user can switch between conversations.
   - The user can view the conversation history.
   - Both the list of conversation history and the messages list should be scrollable.
   - The last message should be always visible unless the user scroll to the previous messages.
   - **Dynamic LLM Settings Modal**:
     - The bottom-left sidebar footer (`sidebar-footer` / `.health-badge`) displaying the active `ENGINE (model)` is a clickable trigger that opens an LLM Configuration modal dialog.
     - The modal contains inputs for **Engine** (`openai`, `lmstudio`, `ollama`, `openrouter`), **Base URL**, **Model**, and **API Key** (`type="password"`).
     - Changes are persisted in MongoDB and applied immediately at runtime, and automatically restored on future application startups (unless overridden by explicit CLI parameters).
     - Once stored, the `api_key` is never sent back or displayed in the modal input; instead, a boolean `has_api_key` flag indicates whether a secret key is already saved, and leaving the password input blank on save preserves the existing stored key.
     - If on the first connection an authentication error occurs because an API key is required by the LLM server, the UI automatically opens the configuration modal displaying a prompt message asking the user to enter their API key.

## API Contracts
- `GET /api/settings/llm`: Returns active LLM configuration `{ engine: string, base_url: string, model: string, has_api_key: boolean, auth_error?: boolean, auth_message?: string | null }` (never exposes `api_key`).
- `PUT /api/settings/llm`: Updates and persists LLM configuration `{ engine: string, base_url: string, model: string, api_key?: string }` to MongoDB and reconfigures the backend LLM client at runtime.
- `GET /api/sessions`: List user sessions sorted by `last_active` descending.
- `POST /api/sessions`: Create a new session `{ title?: string, user_id?: string }`.
- `PATCH /api/sessions/{session_id}`: Update session metadata `{ title: string }`.
- `DELETE /api/sessions/{session_id}`: Cascade deletion of session, its messages, and attached documents.
- `GET /api/sessions/{session_id}/messages`: Fetch chronological messages for session.
- `POST /api/chat`:
  - Request: `{ session_id: string, text: string, stream?: boolean }`
  - Context Injection: Automatically retrieves and injects knowledge chunks when the target session has attached documents.
  - Response: `{ reply: string, message: Message }` or SSE stream of `{ token: string }`.
- `WebSocket /ws/chat`:
  - Inbound: `{ type: "text", session_id: string, text: string }`
  - Inbound audio (see Spec 002): `{ type: "audio_start", sample_rate: number }`, then binary frames (16-bit little-endian mono PCM), optional `{ type: "audio_pause" }` / `{ type: "audio_resume" }` hints, then `{ type: "audio_end" }`. Audio messages are handled before session resolution and never create a session.
  - Context Injection: Automatically retrieves and injects knowledge chunks when the target session has attached documents.
  - Outbound: `{ type: "token", token: string }`, `{ type: "done", full_text: string }`
  - Outbound audio: `{ type: "transcript", text: string }` in response to `audio_end` (`text` is empty when no speech was detected).
