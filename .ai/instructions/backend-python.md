# Backend (FastAPI & Python 3.13) Instructions

## Standards & Constraints
- **Python Version**: `>=3.13` (CPython 3.13.5)
- **Package Manager**: Strictly use **`uv`** for managing dependencies and running virtual environments. Never use `pip` directly.
- **Root Directory**: `apps/backend/`

## Core Frameworks & Libraries
- **FastAPI, Uvicorn & Watchfiles**: Asynchronous web API with CORS and WebSocket support (`apps.backend.server:app`). `watchfiles` is required for event-driven file monitoring.
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
5. **Development Reload & CPU Optimization**:
   - Always install `watchfiles` in `apps/backend/pyproject.toml` so Uvicorn uses OS inotify events rather than polling via `StatReload`.
   - Always route server launches through `apps/backend/main.py` so CLI arguments (`--engine`, `--model`, `--port`, `--host`, `--reload`) are properly parsed by `config.py` and `reload_dirs=["apps/backend"]` is automatically applied to prevent Uvicorn from scanning root `node_modules/`, `.venv/`, `.nx/`, or `.git/` directories (which contain 60,000+ files and spike idle CPU to 100%).
   - Keep `OMP_WAIT_POLICY=PASSIVE` for ONNX Runtime threads to prevent background spin-waiting when idle.

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
