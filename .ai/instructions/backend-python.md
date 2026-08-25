# Backend (FastAPI & Python 3.13) Instructions

## Standards & Constraints
- **Python Version**: `>=3.13` (CPython 3.13.5)
- **Package Manager**: Strictly use **`uv`** for managing dependencies and running virtual environments. Never use `pip` directly.
- **Root Directory**: `apps/backend/`

## Core Frameworks & Libraries
- **FastAPI & Uvicorn**: Asynchronous web API with CORS and WebSocket support (`apps.backend.server:app`).
- **Pydantic**: Request and response schema validation.
- **Motor / PyMongo**: Async driver for MongoDB database operations (`apps.backend.db.mongo`).
- **OpenAI Python SDK**: Client for OpenAI-compatible endpoints (LM Studio, Ollama, OpenRouter, OpenAI).
- **Moonshine ONNX (`useful-moonshine-onnx`)**: Fast local Speech-to-Text inference (`apps.backend.services.stt`).
- **Piper TTS (`piper-tts`) & ONNX Runtime**: Local neural voice synthesis with sentence streaming (`apps.backend.services.tts`).
- **Audio Preprocessing**: `soundfile`, `pydub`, `numpy`, and `audioop-lts` (required for Python 3.13 compatibility).

## Key Patterns
1. **Piper Model Manager**: Follow [`apps/backend/common/model_manager.py`](../../apps/backend/common/model_manager.py) to download voice models via `hf_hub_download` from `rhasspy/piper-voices` with optimized ONNX thread sessions (`intra_op_num_threads=2`, `inter_op_num_threads=2`).
2. **STT Normalization**: Convert incoming client audio bytes to 16kHz mono `float32` numpy arrays before feeding into Moonshine ONNX.
3. **Sentence-Level TTS Streaming**: Split incoming LLM token stream at sentence boundaries (`. ! ? \n`) and synthesize audio sentence-by-sentence to achieve low Time-to-First-Audio (TTFA).
4. **Lifespan Warmup**: Always warm up DB connections, tokenizer, and voice models in FastAPI's `lifespan` handler.

## Common CLI Commands
```bash
# Run server entrypoint
PYTHONPATH=. uv run --project apps/backend python3 apps/backend/main.py

# Run server in dev mode with auto-reload and SSL
PYTHONPATH=. uv run --project apps/backend uvicorn apps.backend.server:app --reload --port 8000 --ssl-certfile cert.pem --ssl-keyfile key.pem

# Add dependencies
cd apps/backend && uv add <package-name>
```
