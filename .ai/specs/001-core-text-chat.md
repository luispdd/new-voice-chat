# Spec 001: Core Text Chat & Multi-Provider LLM Streaming

## Status: Implemented & Verified

## Overview
Provides text-based conversation capabilities supporting real-time token streaming and flexible backend connectivity across local and cloud LLM providers (LM Studio, Ollama, OpenRouter, OpenAI).

## Requirements
1. **Multi-Provider Support**:
   - `lmstudio`: Default local engine running on `http://127.0.0.1:1234/v1` (e.g. `google/gemma-3-4b-it-qat`).
   - `ollama`: Local engine on `http://127.0.0.1:11434/v1` (e.g. `llama3`).
   - `openai`: Cloud OpenAI API (`https://api.openai.com/v1`).
   - `openrouter`: Multi-model aggregator (`https://openrouter.ai/api/v1`).
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
5. **Conversation history**:
   - The user can create, rename and delete conversations.
   - The conversations should be displayed in the sidebar.
   - The user can switch between conversations.
   - The user can view the conversation history.
6. **UI**:
   - The user can switch between conversations.
   - The user can view the conversation history.
   - Both the list of conversation history and the messages list should be scrollable.
   - The last message should be always visible unless the user scroll to the previous messages.

## API Contracts
- `POST /api/chat`:
  - Request: `{ session_id: string, text: string, stream?: boolean, with_rag?: boolean }`
  - Response: `{ reply: string, message: Message }` or SSE stream of `{ token: string }`.
- `WebSocket /ws/chat`:
  - Inbound: `{ type: "text", session_id: string, text: string }`
  - Outbound: `{ type: "token", token: string }`, `{ type: "done", full_text: string }`
