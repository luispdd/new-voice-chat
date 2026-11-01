# Backend (FastAPI & Python 3.13) Instructions

## Standards & Constraints
- **Python Version**: `>=3.13` (CPython 3.13.5)
- **Package Manager**: Strictly use **`uv`** for managing dependencies and running virtual environments. Never use `pip` directly.
- **Root Directory**: `apps/backend/`

## Core Frameworks & Libraries
- **FastAPI, Uvicorn & Watchfiles**: Asynchronous web API with CORS and WebSocket support. `watchfiles` is required for event-driven file monitoring.
- **Pydantic**: Request and response schema validation.
- **Motor / PyMongo**: Async driver for MongoDB database operations.
- **OpenAI Python SDK**: Client for OpenAI-compatible endpoints (LM Studio, Ollama, OpenRouter, OpenAI).
- **sherpa-onnx (`sherpa-onnx`)**: Local CPU Speech-to-Text with the English-only Parakeet TDT 0.6b v2 INT8 model (`OfflineRecognizer.from_transducer`, `model_type="nemo_transducer"`).
- **Piper TTS (`piper-tts`) & ONNX Runtime**: Local neural voice synthesis with sentence streaming.
- **Audio Preprocessing**: `soundfile`, `pydub`, `numpy`, and `audioop-lts` (required for Python 3.13 compatibility).

## Key Patterns
1. **Piper Model Manager**: Download voice models via `hf_hub_download` from `rhasspy/piper-voices` with optimized ONNX thread sessions (`intra_op_num_threads=2`, `inter_op_num_threads=2`).
2. **STT Service Architecture**:
   - Always initialize and warm up the Parakeet `OfflineRecognizer` singleton (HF repo `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8`, downloaded with `hf_hub_download`) once in lifespan startup to avoid per-request model reloading. Serialize decoding with a lock.
   - Decode raw audio payloads via `pydub.AudioSegment.from_file` normalized to 16kHz mono `float32` arrays in `[-1.0, 1.0]` with DC offset removal.
   - Do not trim silence before inference (it clipped quiet speech onsets); skip decoding only for digital silence.
   - Transcribe the full utterance in a single `decode_stream` call, in a worker thread (`asyncio.to_thread`) when called from the event loop.
   - Streamed microphone audio arrives over `/ws/chat` as binary PCM frames; `UtteranceBuffer` (`services/stt_stream.py`) transcribes speculatively when the client sends `audio_pause` (700 ms of silence per the browser VAD) so the transcript is ready at end of turn. Never infer silence from RMS on the backend.
3. **Sentence-Level TTS Streaming**: Split incoming LLM token stream at sentence boundaries (`. ! ? \n`) and synthesize audio sentence-by-sentence to achieve low Time-to-First-Audio (TTFA).
4. **Lifespan Warmup**: Always warm up DB connections, tokenizer, and voice models in FastAPI's `lifespan` handler.
5. **Development Reload & CPU Optimization**:
   - Always install `watchfiles` so Uvicorn uses OS inotify events rather than polling via `StatReload`.
   - Always route server launches through backend configuration entrypoints so CLI arguments (`--engine`, `--model`, `--port`, `--host`, `--reload`) are properly parsed and reload monitoring is scoped to avoid scanning root `node_modules/`, `.venv/`, `.nx/`, or `.git/` directories (which contain 60,000+ files and spike idle CPU to 100%).
   - Keep `OMP_WAIT_POLICY=PASSIVE` for ONNX Runtime threads to prevent background spin-waiting when idle.
6. **Voice LLM System Prompt & TTS Text Sanitization**:
   - Apply a centralized voice-optimized system prompt that explicitly forbids emojis, ASCII emoticons, markdown formatting, bullet lists, and unreadable unicode across all chat endpoints.
   - Always route text through a TTS sanitization filter before voice synthesis to prevent vocalization of asterisks, emojis, hashtags, or formatting artifacts.

## Common CLI Commands
```bash
# Run server (standard) with optional engine / model overrides:
bun run backend --engine lmstudio --model gemma-3-4b-it

# Run server with auto-reload (scoped to apps/backend) and SSL:
bun run backend:dev --engine lmstudio --model gemma-3-4b-it

# Direct Python entrypoint:
PYTHONPATH=. uv run --project apps/backend python3 apps/backend/main.py --reload --engine lmstudio --model gemma-3-4b-it

# Add dependencies:
cd apps/backend && uv add <package-name>
```
