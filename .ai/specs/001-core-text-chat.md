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
3. **Prompt Design**:
   - System prompt tailored for voice-first interactions: concise, conversational, avoiding markdown bloat and unreadable tables.
4. **Error Handling**: Graceful fallback when the LLM service is offline or unreachable.

## API Contracts
- `POST /api/chat`:
  - Request: `{ session_id: string, text: string, stream?: boolean, with_rag?: boolean }`
  - Response: `{ reply: string, message: Message }` or SSE stream of `{ token: string }`.
- `WebSocket /ws/chat`:
  - Inbound: `{ type: "text", session_id: string, text: string }`
  - Outbound: `{ type: "token", token: string }`, `{ type: "done", full_text: string }`
